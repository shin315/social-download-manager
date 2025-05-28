"""
Database Retry Policies and Recovery

This module provides comprehensive retry mechanisms for database operations including
exponential backoff, circuit breaker patterns, deadlock detection and recovery,
and intelligent retry policies for different types of failures.
"""

import random
import sqlite3
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Type, TypeVar, Union
import threading
import logging

from .exceptions import (
    DatabaseError, DatabaseErrorCode, DatabaseErrorContext,
    DeadlockError, LockTimeoutError, ConnectionTimeoutError,
    ConnectionPoolExhaustedError, QueryTimeoutError
)
from .logging import DatabaseLogger, LogLevel, OperationType

T = TypeVar('T')


class RetryStrategy(Enum):
    """Different retry strategies"""
    FIXED_DELAY = "fixed_delay"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    RANDOM_JITTER = "random_jitter"
    CUSTOM = "custom"


class CircuitBreakerState(Enum):
    """States of the circuit breaker"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing fast
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RetryConfig:
    """Configuration for retry policies"""
    
    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    backoff_multiplier: float = 2.0
    jitter: bool = True
    jitter_range: float = 0.1  # 10% jitter
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    
    # Specific error types to retry
    retryable_errors: Set[Type[Exception]] = field(default_factory=lambda: {
        DeadlockError,
        LockTimeoutError,
        ConnectionTimeoutError,
        ConnectionPoolExhaustedError,
        QueryTimeoutError,
        sqlite3.OperationalError,  # Database is locked
        sqlite3.DatabaseError     # Generic database errors
    })
    
    # Error types that should never be retried
    non_retryable_errors: Set[Type[Exception]] = field(default_factory=lambda: {
        sqlite3.IntegrityError,   # Constraint violations
        ValueError,
        TypeError
    })
    
    # Custom retry condition function
    custom_retry_condition: Optional[Callable[[Exception], bool]] = None


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    
    failure_threshold: int = 5      # Number of failures to open circuit
    recovery_timeout: float = 60.0  # Seconds before attempting recovery
    success_threshold: int = 3      # Successful calls needed to close circuit
    timeout: float = 30.0           # Operation timeout in seconds


@dataclass
class RetryAttempt:
    """Information about a retry attempt"""
    
    attempt_number: int
    delay: float
    error: Exception
    timestamp: datetime
    context: Optional[DatabaseErrorContext] = None


@dataclass
class RetryResult:
    """Result of retry operation"""
    
    success: bool
    result: Any = None
    total_attempts: int = 0
    total_time: float = 0.0
    attempts: List[RetryAttempt] = field(default_factory=list)
    final_error: Optional[Exception] = None


class RetryPolicy(ABC):
    """Abstract base class for retry policies"""
    
    def __init__(self, config: RetryConfig, logger: Optional[DatabaseLogger] = None):
        self.config = config
        self.logger = logger or DatabaseLogger("retry")
    
    @abstractmethod
    def calculate_delay(self, attempt: int, previous_delay: float) -> float:
        """Calculate delay for next retry attempt"""
        pass
    
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Determine if operation should be retried"""
        
        # Check maximum attempts
        if attempt >= self.config.max_attempts:
            return False
        
        # Check custom retry condition first
        if self.config.custom_retry_condition:
            return self.config.custom_retry_condition(error)
        
        # Check non-retryable errors
        for non_retryable_type in self.config.non_retryable_errors:
            if isinstance(error, non_retryable_type):
                return False
        
        # Check retryable errors
        for retryable_type in self.config.retryable_errors:
            if isinstance(error, retryable_type):
                return True
        
        # Check SQLite-specific errors
        if isinstance(error, sqlite3.Error):
            error_msg = str(error).lower()
            
            # Always retry these SQLite errors
            retryable_sqlite_patterns = [
                "database is locked",
                "database table is locked",
                "cannot start a transaction within a transaction",
                "disk i/o error",
                "attempt to write a readonly database"
            ]
            
            for pattern in retryable_sqlite_patterns:
                if pattern in error_msg:
                    return True
            
            # Never retry these SQLite errors
            non_retryable_sqlite_patterns = [
                "unique constraint failed",
                "not null constraint failed",
                "foreign key constraint failed",
                "check constraint failed",
                "syntax error",
                "no such table",
                "no such column"
            ]
            
            for pattern in non_retryable_sqlite_patterns:
                if pattern in error_msg:
                    return False
        
        # Default: don't retry unknown errors
        return False
    
    def add_jitter(self, delay: float) -> float:
        """Add jitter to delay to avoid thundering herd"""
        if not self.config.jitter:
            return delay
        
        jitter_amount = delay * self.config.jitter_range
        return delay + random.uniform(-jitter_amount, jitter_amount)
    
    def execute_with_retry(
        self,
        func: Callable[..., T],
        *args,
        operation_context: Optional[DatabaseErrorContext] = None,
        **kwargs
    ) -> RetryResult:
        """Execute function with retry logic"""
        
        start_time = time.time()
        attempts = []
        delay = self.config.base_delay
        
        for attempt in range(self.config.max_attempts):
            try:
                self.logger.log_operation(
                    level=LogLevel.DEBUG,
                    operation_type=OperationType.QUERY,
                    operation="retry_attempt",
                    message=f"Attempting operation (attempt {attempt + 1}/{self.config.max_attempts})",
                    connection_id=operation_context.connection_id if operation_context else None,
                    transaction_id=operation_context.transaction_id if operation_context else None
                )
                
                result = func(*args, **kwargs)
                
                total_time = time.time() - start_time
                
                self.logger.log_operation(
                    level=LogLevel.INFO,
                    operation_type=OperationType.QUERY,
                    operation="retry_success",
                    message=f"Operation succeeded after {attempt + 1} attempts in {total_time:.3f}s",
                    connection_id=operation_context.connection_id if operation_context else None,
                    transaction_id=operation_context.transaction_id if operation_context else None
                )
                
                return RetryResult(
                    success=True,
                    result=result,
                    total_attempts=attempt + 1,
                    total_time=total_time,
                    attempts=attempts
                )
                
            except Exception as error:
                attempt_info = RetryAttempt(
                    attempt_number=attempt + 1,
                    delay=delay,
                    error=error,
                    timestamp=datetime.now(),
                    context=operation_context
                )
                attempts.append(attempt_info)
                
                # Check if we should retry
                if not self.should_retry(error, attempt + 1):
                    self.logger.log_operation(
                        level=LogLevel.ERROR,
                        operation_type=OperationType.QUERY,
                        operation="retry_failed",
                        message=f"Operation failed permanently after {attempt + 1} attempts: {str(error)}",
                        connection_id=operation_context.connection_id if operation_context else None,
                        transaction_id=operation_context.transaction_id if operation_context else None,
                        error_code=error.error_code.value if isinstance(error, DatabaseError) else None,
                        error_context=error.context.to_dict() if isinstance(error, DatabaseError) else None
                    )
                    
                    break
                
                # If this is not the last attempt, wait and retry
                if attempt < self.config.max_attempts - 1:
                    actual_delay = self.add_jitter(delay)
                    
                    self.logger.log_operation(
                        level=LogLevel.WARN,
                        operation_type=OperationType.QUERY,
                        operation="retry_delay",
                        message=f"Operation failed (attempt {attempt + 1}), retrying in {actual_delay:.3f}s: {str(error)}",
                        connection_id=operation_context.connection_id if operation_context else None,
                        transaction_id=operation_context.transaction_id if operation_context else None,
                        error_code=error.error_code.value if isinstance(error, DatabaseError) else None
                    )
                    
                    time.sleep(actual_delay)
                    delay = self.calculate_delay(attempt + 1, delay)
        
        # All attempts failed
        total_time = time.time() - start_time
        final_error = attempts[-1].error if attempts else Exception("No attempts made")
        
        return RetryResult(
            success=False,
            total_attempts=len(attempts),
            total_time=total_time,
            attempts=attempts,
            final_error=final_error
        )


class FixedDelayRetryPolicy(RetryPolicy):
    """Fixed delay between retry attempts"""
    
    def calculate_delay(self, attempt: int, previous_delay: float) -> float:
        return min(self.config.base_delay, self.config.max_delay)


class ExponentialBackoffRetryPolicy(RetryPolicy):
    """Exponential backoff retry policy"""
    
    def calculate_delay(self, attempt: int, previous_delay: float) -> float:
        delay = self.config.base_delay * (self.config.backoff_multiplier ** (attempt - 1))
        return min(delay, self.config.max_delay)


class LinearBackoffRetryPolicy(RetryPolicy):
    """Linear backoff retry policy"""
    
    def calculate_delay(self, attempt: int, previous_delay: float) -> float:
        delay = self.config.base_delay * attempt
        return min(delay, self.config.max_delay)


class RandomJitterRetryPolicy(RetryPolicy):
    """Random jitter retry policy"""
    
    def calculate_delay(self, attempt: int, previous_delay: float) -> float:
        base_delay = random.uniform(self.config.base_delay, self.config.base_delay * 2)
        return min(base_delay, self.config.max_delay)


class CircuitBreaker:
    """Circuit breaker for database operations"""
    
    def __init__(
        self,
        config: CircuitBreakerConfig,
        logger: Optional[DatabaseLogger] = None
    ):
        self.config = config
        self.logger = logger or DatabaseLogger("circuit_breaker")
        
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.lock = threading.Lock()
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt to reset"""
        if self.state != CircuitBreakerState.OPEN:
            return False
        
        if self.last_failure_time is None:
            return True
        
        time_since_failure = datetime.now() - self.last_failure_time
        return time_since_failure.total_seconds() >= self.config.recovery_timeout
    
    def _record_success(self) -> None:
        """Record successful operation"""
        with self.lock:
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitBreakerState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    
                    self.logger.log_operation(
                        level=LogLevel.INFO,
                        operation_type=OperationType.CONNECTION,
                        operation="circuit_breaker_closed",
                        message="Circuit breaker closed - service recovered"
                    )
            else:
                self.failure_count = 0
    
    def _record_failure(self) -> None:
        """Record failed operation"""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.state == CircuitBreakerState.CLOSED:
                if self.failure_count >= self.config.failure_threshold:
                    self.state = CircuitBreakerState.OPEN
                    
                    self.logger.log_operation(
                        level=LogLevel.ERROR,
                        operation_type=OperationType.CONNECTION,
                        operation="circuit_breaker_opened",
                        message=f"Circuit breaker opened after {self.failure_count} failures"
                    )
            elif self.state == CircuitBreakerState.HALF_OPEN:
                self.state = CircuitBreakerState.OPEN
                self.success_count = 0
                
                self.logger.log_operation(
                    level=LogLevel.ERROR,
                    operation_type=OperationType.CONNECTION,
                    operation="circuit_breaker_reopened",
                    message="Circuit breaker reopened after failure during recovery test"
                )
    
    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function through circuit breaker"""
        
        with self.lock:
            if self.state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.success_count = 0
                    
                    self.logger.log_operation(
                        level=LogLevel.INFO,
                        operation_type=OperationType.CONNECTION,
                        operation="circuit_breaker_half_open",
                        message="Circuit breaker half-open - testing service recovery"
                    )
                else:
                    from .exceptions import ConnectionError
                    raise ConnectionError(
                        "Circuit breaker is open - service unavailable",
                        DatabaseErrorCode.CONNECTION_FAILED
                    )
        
        try:
            # Execute with timeout
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Check if operation took too long
            if execution_time > self.config.timeout:
                raise QueryTimeoutError(
                    f"Operation timed out after {execution_time:.2f}s (limit: {self.config.timeout}s)"
                )
            
            self._record_success()
            return result
            
        except Exception as error:
            self._record_failure()
            raise


class DeadlockDetector:
    """Deadlock detection and recovery mechanism"""
    
    def __init__(self, logger: Optional[DatabaseLogger] = None):
        self.logger = logger or DatabaseLogger("deadlock_detector")
        self.active_transactions: Dict[str, Set[str]] = {}  # transaction_id -> tables
        self.transaction_waits: Dict[str, str] = {}  # transaction_id -> waiting_for_transaction_id
        self.lock = threading.Lock()
    
    def register_transaction(self, transaction_id: str) -> None:
        """Register a new transaction"""
        with self.lock:
            self.active_transactions[transaction_id] = set()
    
    def unregister_transaction(self, transaction_id: str) -> None:
        """Unregister a completed transaction"""
        with self.lock:
            self.active_transactions.pop(transaction_id, None)
            self.transaction_waits.pop(transaction_id, None)
            
            # Remove any waits for this transaction
            self.transaction_waits = {
                tid: waiting_for for tid, waiting_for in self.transaction_waits.items()
                if waiting_for != transaction_id
            }
    
    def register_table_access(self, transaction_id: str, table: str) -> None:
        """Register table access by transaction"""
        with self.lock:
            if transaction_id in self.active_transactions:
                self.active_transactions[transaction_id].add(table)
    
    def register_wait(self, transaction_id: str, waiting_for_transaction: str) -> None:
        """Register that a transaction is waiting for another"""
        with self.lock:
            self.transaction_waits[transaction_id] = waiting_for_transaction
            
            # Check for deadlock
            if self._detect_deadlock_cycle(transaction_id):
                self.logger.log_operation(
                    level=LogLevel.ERROR,
                    operation_type=OperationType.TRANSACTION,
                    operation="deadlock_detected",
                    message=f"Deadlock detected involving transaction {transaction_id}",
                    transaction_id=transaction_id
                )
                
                raise DeadlockError(
                    f"Deadlock detected involving transaction {transaction_id}",
                    context=DatabaseErrorContext(
                        operation="deadlock_detection",
                        transaction_id=transaction_id
                    )
                )
    
    def _detect_deadlock_cycle(self, start_transaction: str) -> bool:
        """Detect if there's a deadlock cycle starting from given transaction"""
        visited = set()
        current = start_transaction
        
        while current and current not in visited:
            visited.add(current)
            current = self.transaction_waits.get(current)
            
            if current == start_transaction:
                return True  # Cycle detected
        
        return False
    
    def get_deadlock_info(self) -> Dict[str, Any]:
        """Get information about current transaction states"""
        with self.lock:
            return {
                "active_transactions": dict(self.active_transactions),
                "transaction_waits": dict(self.transaction_waits),
                "potential_deadlocks": self._find_all_cycles()
            }
    
    def _find_all_cycles(self) -> List[List[str]]:
        """Find all deadlock cycles"""
        cycles = []
        visited_global = set()
        
        for transaction_id in self.active_transactions:
            if transaction_id not in visited_global:
                visited_local = set()
                current = transaction_id
                path = []
                
                while current and current not in visited_local:
                    visited_local.add(current)
                    visited_global.add(current)
                    path.append(current)
                    current = self.transaction_waits.get(current)
                    
                    if current in path:
                        # Found cycle
                        cycle_start = path.index(current)
                        cycle = path[cycle_start:] + [current]
                        cycles.append(cycle)
                        break
        
        return cycles


def retry_database_operation(
    retry_config: Optional[RetryConfig] = None,
    circuit_breaker: Optional[CircuitBreaker] = None,
    logger: Optional[DatabaseLogger] = None
):
    """Decorator for retrying database operations"""
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Create default retry config if not provided
            config = retry_config or RetryConfig()
            
            # Create retry policy based on strategy
            if config.strategy == RetryStrategy.FIXED_DELAY:
                policy = FixedDelayRetryPolicy(config, logger)
            elif config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
                policy = ExponentialBackoffRetryPolicy(config, logger)
            elif config.strategy == RetryStrategy.LINEAR_BACKOFF:
                policy = LinearBackoffRetryPolicy(config, logger)
            elif config.strategy == RetryStrategy.RANDOM_JITTER:
                policy = RandomJitterRetryPolicy(config, logger)
            else:
                policy = ExponentialBackoffRetryPolicy(config, logger)
            
            # Create operation context
            context = DatabaseErrorContext(operation=func.__name__)
            
            # Execute with circuit breaker if provided
            if circuit_breaker:
                def execute_with_breaker():
                    return circuit_breaker.call(func, *args, **kwargs)
                
                result = policy.execute_with_retry(execute_with_breaker, operation_context=context)
            else:
                result = policy.execute_with_retry(func, *args, **kwargs, operation_context=context)
            
            if result.success:
                return result.result
            else:
                raise result.final_error
        
        return wrapper
    return decorator


# Global instances
_default_circuit_breaker: Optional[CircuitBreaker] = None
_default_deadlock_detector: Optional[DeadlockDetector] = None


def get_default_circuit_breaker() -> CircuitBreaker:
    """Get or create default circuit breaker"""
    global _default_circuit_breaker
    if _default_circuit_breaker is None:
        _default_circuit_breaker = CircuitBreaker(CircuitBreakerConfig())
    return _default_circuit_breaker


def get_default_deadlock_detector() -> DeadlockDetector:
    """Get or create default deadlock detector"""
    global _default_deadlock_detector
    if _default_deadlock_detector is None:
        _default_deadlock_detector = DeadlockDetector()
    return _default_deadlock_detector


def configure_default_retry_policies(
    circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
    retry_config: Optional[RetryConfig] = None
) -> tuple[CircuitBreaker, RetryConfig]:
    """Configure default retry policies"""
    global _default_circuit_breaker
    
    if circuit_breaker_config:
        _default_circuit_breaker = CircuitBreaker(circuit_breaker_config)
    
    config = retry_config or RetryConfig()
    
    return get_default_circuit_breaker(), config 