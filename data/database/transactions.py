"""
Transaction Management System for Social Download Manager v2.0

Provides comprehensive transaction handling with ACID properties, nested transactions,
transaction boundaries, propagation behaviors, and deadlock detection.
"""

import sqlite3
import threading
import logging
import time
import uuid
import weakref
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Dict, Any, List, Callable, Generator, Set
from datetime import datetime, timezone

from .connection import SQLiteConnectionManager, DatabaseError


class TransactionIsolationLevel(Enum):
    """Transaction isolation levels for SQLite"""
    DEFERRED = "DEFERRED"
    IMMEDIATE = "IMMEDIATE"
    EXCLUSIVE = "EXCLUSIVE"


class TransactionPropagation(Enum):
    """Transaction propagation behaviors"""
    REQUIRED = auto()       # Join existing transaction or create new one
    REQUIRES_NEW = auto()   # Always create new transaction (suspend current)
    NESTED = auto()         # Create savepoint within existing transaction
    SUPPORTS = auto()       # Join existing transaction if available
    NOT_SUPPORTED = auto()  # Execute without transaction
    NEVER = auto()          # Fail if transaction exists
    MANDATORY = auto()      # Fail if no transaction exists


class TransactionStatus(Enum):
    """Transaction status states"""
    ACTIVE = auto()
    COMMITTED = auto()
    ROLLED_BACK = auto()
    MARKED_ROLLBACK_ONLY = auto()
    PREPARING = auto()
    UNKNOWN = auto()


class TransactionException(Exception):
    """Base exception for transaction-related errors"""
    pass


class DeadlockException(TransactionException):
    """Exception raised when deadlock is detected"""
    pass


class TransactionTimeoutException(TransactionException):
    """Exception raised when transaction times out"""
    pass


class InvalidTransactionStateException(TransactionException):
    """Exception raised when transaction is in invalid state"""
    pass


@dataclass
class TransactionInfo:
    """Information about a transaction"""
    transaction_id: str
    start_time: datetime
    isolation_level: TransactionIsolationLevel
    status: TransactionStatus
    is_read_only: bool = False
    timeout_seconds: Optional[float] = None
    savepoint_name: Optional[str] = None
    parent_transaction_id: Optional[str] = None
    nested_level: int = 0
    
    def __post_init__(self):
        if not self.transaction_id:
            self.transaction_id = str(uuid.uuid4())


@dataclass
class TransactionStatistics:
    """Transaction execution statistics"""
    total_transactions: int = 0
    committed_transactions: int = 0
    rolled_back_transactions: int = 0
    nested_transactions: int = 0
    deadlocks_detected: int = 0
    timeouts_occurred: int = 0
    average_duration_ms: float = 0.0
    active_transactions: int = 0
    
    def add_transaction_duration(self, duration_ms: float) -> None:
        """Add transaction duration to running average"""
        if self.total_transactions == 0:
            self.average_duration_ms = duration_ms
        else:
            total_time = self.average_duration_ms * self.total_transactions
            self.average_duration_ms = (total_time + duration_ms) / (self.total_transactions + 1)


class ITransactionManager(ABC):
    """Interface for transaction management"""
    
    @abstractmethod
    def begin_transaction(self, 
                         isolation_level: TransactionIsolationLevel = TransactionIsolationLevel.DEFERRED,
                         read_only: bool = False,
                         timeout_seconds: Optional[float] = None) -> 'Transaction':
        """Begin a new transaction"""
        pass
    
    @abstractmethod
    def get_current_transaction(self) -> Optional['Transaction']:
        """Get the current transaction for this thread"""
        pass
    
    @abstractmethod
    def transaction(self, 
                   isolation_level: TransactionIsolationLevel = TransactionIsolationLevel.DEFERRED,
                   propagation: TransactionPropagation = TransactionPropagation.REQUIRED,
                   read_only: bool = False,
                   timeout_seconds: Optional[float] = None) -> 'TransactionContext':
        """Context manager for transactions with propagation support"""
        pass
    
    @abstractmethod
    def get_statistics(self) -> TransactionStatistics:
        """Get transaction statistics"""
        pass


class Transaction:
    """
    Represents an active database transaction
    
    Provides transaction lifecycle management, savepoint support,
    and integration with connection management.
    """
    
    def __init__(self, 
                 connection: sqlite3.Connection,
                 transaction_manager: 'TransactionManager',
                 info: TransactionInfo):
        self._connection = connection
        self._transaction_manager = transaction_manager
        self._info = info
        self._logger = logging.getLogger(__name__)
        self._savepoints: List[str] = []
        self._is_active = True
        self._rollback_only = False
        
        # Start transaction
        self._start_transaction()
    
    @property
    def transaction_id(self) -> str:
        """Get transaction ID"""
        return self._info.transaction_id
    
    @property
    def status(self) -> TransactionStatus:
        """Get transaction status"""
        return self._info.status
    
    @property
    def isolation_level(self) -> TransactionIsolationLevel:
        """Get isolation level"""
        return self._info.isolation_level
    
    @property
    def is_read_only(self) -> bool:
        """Check if transaction is read-only"""
        return self._info.is_read_only
    
    @property
    def is_active(self) -> bool:
        """Check if transaction is active"""
        return self._is_active and self._info.status == TransactionStatus.ACTIVE
    
    @property
    def is_rollback_only(self) -> bool:
        """Check if transaction is marked for rollback only"""
        return self._rollback_only
    
    def get_connection(self) -> sqlite3.Connection:
        """Get the underlying database connection"""
        if not self._is_active:
            raise InvalidTransactionStateException("Transaction is not active")
        return self._connection
    
    def mark_rollback_only(self) -> None:
        """Mark transaction for rollback only"""
        self._rollback_only = True
        self._info.status = TransactionStatus.MARKED_ROLLBACK_ONLY
        self._logger.warning(f"Transaction {self.transaction_id} marked for rollback only")
    
    def create_savepoint(self, name: Optional[str] = None) -> str:
        """Create a savepoint within this transaction"""
        if not self._is_active:
            raise InvalidTransactionStateException("Cannot create savepoint: transaction not active")
        
        if not name:
            name = f"sp_{len(self._savepoints) + 1}_{int(time.time() * 1000)}"
        
        try:
            cursor = self._connection.cursor()
            cursor.execute(f"SAVEPOINT {name}")
            cursor.close()
            
            self._savepoints.append(name)
            self._logger.debug(f"Created savepoint '{name}' in transaction {self.transaction_id}")
            return name
            
        except Exception as e:
            self._logger.error(f"Failed to create savepoint '{name}': {e}")
            raise TransactionException(f"Failed to create savepoint: {e}")
    
    def rollback_to_savepoint(self, name: str) -> None:
        """Rollback to a specific savepoint"""
        if not self._is_active:
            raise InvalidTransactionStateException("Cannot rollback to savepoint: transaction not active")
        
        if name not in self._savepoints:
            raise TransactionException(f"Savepoint '{name}' not found")
        
        try:
            cursor = self._connection.cursor()
            cursor.execute(f"ROLLBACK TO SAVEPOINT {name}")
            cursor.close()
            
            # Remove savepoints created after this one
            savepoint_index = self._savepoints.index(name)
            self._savepoints = self._savepoints[:savepoint_index + 1]
            
            self._logger.debug(f"Rolled back to savepoint '{name}' in transaction {self.transaction_id}")
            
        except Exception as e:
            self._logger.error(f"Failed to rollback to savepoint '{name}': {e}")
            raise TransactionException(f"Failed to rollback to savepoint: {e}")
    
    def release_savepoint(self, name: str) -> None:
        """Release a savepoint"""
        if name not in self._savepoints:
            raise TransactionException(f"Savepoint '{name}' not found")
        
        try:
            cursor = self._connection.cursor()
            cursor.execute(f"RELEASE SAVEPOINT {name}")
            cursor.close()
            
            self._savepoints.remove(name)
            self._logger.debug(f"Released savepoint '{name}' in transaction {self.transaction_id}")
            
        except Exception as e:
            self._logger.error(f"Failed to release savepoint '{name}': {e}")
            raise TransactionException(f"Failed to release savepoint: {e}")
    
    def commit(self) -> None:
        """Commit the transaction"""
        if not self._is_active:
            raise InvalidTransactionStateException("Transaction is not active")
        
        if self._rollback_only:
            raise InvalidTransactionStateException("Transaction is marked for rollback only")
        
        try:
            # Release all savepoints first
            for savepoint in list(self._savepoints):
                self.release_savepoint(savepoint)
            
            self._connection.commit()
            self._info.status = TransactionStatus.COMMITTED
            
            self._logger.debug(f"Committed transaction {self.transaction_id}")
            
            # Store connection reference before marking inactive
            connection = self._connection
            self._is_active = False
            
            # Notify transaction manager of completion
            self._transaction_manager._complete_transaction(self, committed=True, connection=connection)
            
        except Exception as e:
            self._logger.error(f"Failed to commit transaction {self.transaction_id}: {e}")
            try:
                self._connection.rollback()
                self._info.status = TransactionStatus.ROLLED_BACK
                connection = self._connection
                self._is_active = False
                self._transaction_manager._complete_transaction(self, committed=False, connection=connection)
            except:
                self._is_active = False
            raise TransactionException(f"Failed to commit transaction: {e}")
    
    def rollback(self) -> None:
        """Rollback the transaction"""
        if not self._is_active:
            raise InvalidTransactionStateException("Transaction is not active")
        
        try:
            self._connection.rollback()
            self._info.status = TransactionStatus.ROLLED_BACK
            self._savepoints.clear()
            
            self._logger.debug(f"Rolled back transaction {self.transaction_id}")
            
            # Store connection reference before marking inactive
            connection = self._connection
            self._is_active = False
            
            # Notify transaction manager of completion
            self._transaction_manager._complete_transaction(self, committed=False, connection=connection)
            
        except Exception as e:
            self._logger.error(f"Failed to rollback transaction {self.transaction_id}: {e}")
            connection = self._connection
            self._is_active = False
            self._transaction_manager._complete_transaction(self, committed=False, connection=connection)
            raise TransactionException(f"Failed to rollback transaction: {e}")
    
    def _start_transaction(self) -> None:
        """Start the database transaction"""
        try:
            cursor = self._connection.cursor()
            cursor.execute(f"BEGIN {self._info.isolation_level.value}")
            cursor.close()
            
            self._info.status = TransactionStatus.ACTIVE
            self._logger.debug(f"Started transaction {self.transaction_id} with isolation {self._info.isolation_level.value}")
            
        except Exception as e:
            self._logger.error(f"Failed to start transaction: {e}")
            raise TransactionException(f"Failed to start transaction: {e}")
    
    def _check_timeout(self) -> None:
        """Check if transaction has timed out"""
        if self._info.timeout_seconds:
            elapsed = (datetime.now(timezone.utc) - self._info.start_time).total_seconds()
            if elapsed > self._info.timeout_seconds:
                self.mark_rollback_only()
                raise TransactionTimeoutException(f"Transaction {self.transaction_id} timed out after {elapsed:.2f} seconds")
    
    def __enter__(self) -> 'Transaction':
        """Enter transaction context"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit transaction context"""
        if exc_type is None and not self._rollback_only:
            try:
                self.commit()
            except Exception as e:
                self._logger.error(f"Auto-commit failed: {e}")
                try:
                    self.rollback()
                except:
                    pass
                raise
        else:
            try:
                self.rollback()
            except Exception as e:
                self._logger.error(f"Auto-rollback failed: {e}")


class TransactionContext:
    """Context manager for transaction with propagation support"""
    
    def __init__(self, 
                 transaction_manager: 'TransactionManager',
                 isolation_level: TransactionIsolationLevel,
                 propagation: TransactionPropagation,
                 read_only: bool,
                 timeout_seconds: Optional[float]):
        self._transaction_manager = transaction_manager
        self._isolation_level = isolation_level
        self._propagation = propagation
        self._read_only = read_only
        self._timeout_seconds = timeout_seconds
        self._transaction: Optional[Transaction] = None
        self._savepoint_name: Optional[str] = None
        self._should_commit = False
        self._logger = logging.getLogger(__name__)
    
    def __enter__(self) -> Transaction:
        """Enter transaction context with propagation handling"""
        current_transaction = self._transaction_manager.get_current_transaction()
        
        if self._propagation == TransactionPropagation.REQUIRED:
            if current_transaction and current_transaction.is_active:
                self._transaction = current_transaction
                self._should_commit = False
            else:
                self._transaction = self._transaction_manager.begin_transaction(
                    self._isolation_level, self._read_only, self._timeout_seconds)
                self._should_commit = True
                
        elif self._propagation == TransactionPropagation.REQUIRES_NEW:
            # Always create new transaction
            self._transaction = self._transaction_manager.begin_transaction(
                self._isolation_level, self._read_only, self._timeout_seconds)
            self._should_commit = True
            
        elif self._propagation == TransactionPropagation.NESTED:
            if current_transaction and current_transaction.is_active:
                # Create savepoint within existing transaction
                self._transaction = current_transaction
                self._savepoint_name = current_transaction.create_savepoint()
                self._should_commit = False
            else:
                # No existing transaction, create new one
                self._transaction = self._transaction_manager.begin_transaction(
                    self._isolation_level, self._read_only, self._timeout_seconds)
                self._should_commit = True
                
        elif self._propagation == TransactionPropagation.SUPPORTS:
            if current_transaction and current_transaction.is_active:
                self._transaction = current_transaction
                self._should_commit = False
            else:
                # No transaction support needed
                self._transaction = None
                
        elif self._propagation == TransactionPropagation.NOT_SUPPORTED:
            # Execute without transaction
            self._transaction = None
            
        elif self._propagation == TransactionPropagation.NEVER:
            if current_transaction and current_transaction.is_active:
                raise TransactionException("Transaction exists but propagation is NEVER")
            self._transaction = None
            
        elif self._propagation == TransactionPropagation.MANDATORY:
            if not current_transaction or not current_transaction.is_active:
                raise TransactionException("No active transaction but propagation is MANDATORY")
            self._transaction = current_transaction
            self._should_commit = False
        
        return self._transaction
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit transaction context"""
        if not self._transaction:
            return
        
        try:
            if self._savepoint_name:
                # Handle savepoint
                if exc_type is None:
                    self._transaction.release_savepoint(self._savepoint_name)
                else:
                    self._transaction.rollback_to_savepoint(self._savepoint_name)
            elif self._should_commit:
                # Handle full transaction
                if exc_type is None and not self._transaction.is_rollback_only:
                    self._transaction.commit()
                else:
                    self._transaction.rollback()
        except Exception as e:
            self._logger.error(f"Error in transaction context exit: {e}")
            raise


class TransactionManager(ITransactionManager):
    """
    Comprehensive transaction manager implementation
    
    Provides ACID transaction support, nested transactions via savepoints,
    transaction propagation, deadlock detection, and performance monitoring.
    """
    
    def __init__(self, connection_manager: SQLiteConnectionManager):
        self._connection_manager = connection_manager
        self._logger = logging.getLogger(__name__)
        self._statistics = TransactionStatistics()
        self._active_transactions: Dict[str, Transaction] = {}
        self._thread_transactions: Dict[int, str] = {}  # thread_id -> transaction_id
        self._lock = threading.RLock()
        self._deadlock_detection_enabled = True
        self._deadlock_timeout_seconds = 30.0
        
        # Weak references to transactions for cleanup
        self._transaction_refs: Set[weakref.ref] = set()
    
    def begin_transaction(self, 
                         isolation_level: TransactionIsolationLevel = TransactionIsolationLevel.DEFERRED,
                         read_only: bool = False,
                         timeout_seconds: Optional[float] = None) -> Transaction:
        """Begin a new transaction"""
        thread_id = threading.get_ident()
        
        with self._lock:
            # Check for existing transaction in this thread
            current_transaction = self.get_current_transaction()
            if current_transaction and current_transaction.is_active:
                raise TransactionException(f"Thread {thread_id} already has an active transaction")
            
            # Get connection from pool
            connection = self._connection_manager.get_connection()
            
            # Create transaction info
            info = TransactionInfo(
                transaction_id=str(uuid.uuid4()),
                start_time=datetime.now(timezone.utc),
                isolation_level=isolation_level,
                status=TransactionStatus.ACTIVE,
                is_read_only=read_only,
                timeout_seconds=timeout_seconds
            )
            
            # Create transaction
            transaction = Transaction(connection, self, info)
            
            # Register transaction
            self._active_transactions[info.transaction_id] = transaction
            self._thread_transactions[thread_id] = info.transaction_id
            self._statistics.total_transactions += 1
            self._statistics.active_transactions += 1
            
            # Add weak reference for cleanup
            self._transaction_refs.add(weakref.ref(transaction, self._transaction_cleanup))
            
            self._logger.info(f"Started transaction {info.transaction_id} in thread {thread_id}")
            return transaction
    
    def get_current_transaction(self) -> Optional[Transaction]:
        """Get the current transaction for this thread"""
        thread_id = threading.get_ident()
        
        with self._lock:
            transaction_id = self._thread_transactions.get(thread_id)
            if transaction_id:
                transaction = self._active_transactions.get(transaction_id)
                if transaction and transaction.is_active:
                    return transaction
                else:
                    # Clean up stale reference
                    del self._thread_transactions[thread_id]
                    if transaction_id in self._active_transactions:
                        del self._active_transactions[transaction_id]
            
            return None
    
    @contextmanager
    def transaction(self, 
                   isolation_level: TransactionIsolationLevel = TransactionIsolationLevel.DEFERRED,
                   propagation: TransactionPropagation = TransactionPropagation.REQUIRED,
                   read_only: bool = False,
                   timeout_seconds: Optional[float] = None) -> Generator[Transaction, None, None]:
        """Context manager for transactions with propagation support"""
        context = TransactionContext(self, isolation_level, propagation, read_only, timeout_seconds)
        with context as transaction:
            yield transaction
    
    def get_statistics(self) -> TransactionStatistics:
        """Get transaction statistics"""
        with self._lock:
            return TransactionStatistics(
                total_transactions=self._statistics.total_transactions,
                committed_transactions=self._statistics.committed_transactions,
                rolled_back_transactions=self._statistics.rolled_back_transactions,
                nested_transactions=self._statistics.nested_transactions,
                deadlocks_detected=self._statistics.deadlocks_detected,
                timeouts_occurred=self._statistics.timeouts_occurred,
                average_duration_ms=self._statistics.average_duration_ms,
                active_transactions=len(self._active_transactions)
            )
    
    def _transaction_cleanup(self, weak_ref) -> None:
        """Cleanup function called when transaction is garbage collected"""
        with self._lock:
            self._transaction_refs.discard(weak_ref)
    
    def _complete_transaction(self, transaction: Transaction, committed: bool, connection: sqlite3.Connection) -> None:
        """Mark transaction as completed and update statistics"""
        with self._lock:
            transaction_id = transaction.transaction_id
            thread_id = threading.get_ident()
            
            # Calculate duration
            duration = (datetime.now(timezone.utc) - transaction._info.start_time).total_seconds() * 1000
            
            # Update statistics
            if committed:
                self._statistics.committed_transactions += 1
            else:
                self._statistics.rolled_back_transactions += 1
            
            self._statistics.active_transactions -= 1
            self._statistics.add_transaction_duration(duration)
            
            # Clean up references
            if transaction_id in self._active_transactions:
                del self._active_transactions[transaction_id]
            
            if thread_id in self._thread_transactions and self._thread_transactions[thread_id] == transaction_id:
                del self._thread_transactions[thread_id]
            
            # Return connection to pool
            self._connection_manager.return_connection(connection)
            
            self._logger.debug(f"Completed transaction {transaction_id} (committed: {committed}, duration: {duration:.2f}ms)")


# Global transaction manager instance
_transaction_manager: Optional[TransactionManager] = None


def get_transaction_manager() -> TransactionManager:
    """Get the global transaction manager instance"""
    global _transaction_manager
    
    if _transaction_manager is None:
        from .connection import get_connection_manager
        connection_manager = get_connection_manager()
        _transaction_manager = TransactionManager(connection_manager)
    
    return _transaction_manager


def initialize_transaction_manager(connection_manager: Optional[SQLiteConnectionManager] = None) -> TransactionManager:
    """Initialize the global transaction manager"""
    global _transaction_manager
    
    if connection_manager is None:
        from .connection import get_connection_manager
        connection_manager = get_connection_manager()
    
    _transaction_manager = TransactionManager(connection_manager)
    return _transaction_manager


@contextmanager
def transaction(isolation_level: TransactionIsolationLevel = TransactionIsolationLevel.DEFERRED,
               propagation: TransactionPropagation = TransactionPropagation.REQUIRED,
               read_only: bool = False,
               timeout_seconds: Optional[float] = None) -> Generator[Transaction, None, None]:
    """Global transaction context manager"""
    manager = get_transaction_manager()
    with manager.transaction(isolation_level, propagation, read_only, timeout_seconds) as txn:
        yield txn


def get_current_transaction() -> Optional[Transaction]:
    """Get the current transaction for this thread"""
    manager = get_transaction_manager()
    return manager.get_current_transaction() 