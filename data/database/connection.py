"""
Database Connection Manager for Social Download Manager v2.0

Provides connection management, pooling, and health checks for database operations.
Supports SQLite with connection pooling and proper resource management.
"""

import sqlite3
import threading
import logging
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Dict, Any, Generator
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
import queue


class ConnectionState(Enum):
    """Database connection states"""
    UNINITIALIZED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    DISCONNECTED = auto()
    ERROR = auto()


@dataclass
class ConnectionConfig:
    """Database connection configuration"""
    database_path: str
    max_pool_size: int = 10
    min_pool_size: int = 2
    connection_timeout: float = 30.0
    pool_timeout: float = 5.0
    max_retries: int = 3
    retry_delay: float = 1.0
    enable_wal_mode: bool = True
    enable_foreign_keys: bool = True
    page_size: int = 4096
    cache_size: int = -64000  # 64MB cache


@dataclass
class ConnectionStats:
    """Connection pool statistics"""
    active_connections: int = 0
    idle_connections: int = 0
    total_connections: int = 0
    max_connections_used: int = 0
    connection_requests: int = 0
    connection_timeouts: int = 0
    connection_errors: int = 0
    total_queries: int = 0


class DatabaseError(Exception):
    """Base exception for database errors"""
    pass


class ConnectionPoolError(DatabaseError):
    """Exception for connection pool related errors"""
    pass


class ConnectionTimeoutError(ConnectionPoolError):
    """Exception for connection timeout errors"""
    pass


class IConnectionManager(ABC):
    """Interface for database connection management"""
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the connection manager"""
        pass
    
    @abstractmethod
    def shutdown(self) -> bool:
        """Shutdown the connection manager"""
        pass
    
    @abstractmethod
    def get_connection(self) -> sqlite3.Connection:
        """Get a database connection from the pool"""
        pass
    
    @abstractmethod
    def return_connection(self, connection: sqlite3.Connection) -> None:
        """Return a connection to the pool"""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Check if the database is healthy"""
        pass
    
    @abstractmethod
    def get_stats(self) -> ConnectionStats:
        """Get connection pool statistics"""
        pass


class SQLiteConnectionManager(IConnectionManager):
    """
    SQLite connection manager with connection pooling
    
    Features:
    - Connection pooling for performance
    - Health monitoring
    - Automatic retry logic
    - WAL mode for better concurrency
    - Proper resource cleanup
    """
    
    def __init__(self, config: ConnectionConfig):
        self._config = config
        self._state = ConnectionState.UNINITIALIZED
        self._connection_pool: queue.Queue = queue.Queue(maxsize=config.max_pool_size)
        self._active_connections: Dict[int, sqlite3.Connection] = {}
        self._stats = ConnectionStats()
        self._lock = threading.RLock()
        self._logger = logging.getLogger(__name__)
        self._shutdown_event = threading.Event()
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate configuration parameters"""
        if self._config.max_pool_size < 1:
            raise ValueError("max_pool_size must be at least 1")
        
        if self._config.min_pool_size < 0:
            raise ValueError("min_pool_size cannot be negative")
        
        if self._config.min_pool_size > self._config.max_pool_size:
            raise ValueError("min_pool_size cannot exceed max_pool_size")
        
        if self._config.connection_timeout <= 0:
            raise ValueError("connection_timeout must be positive")
    
    def initialize(self) -> bool:
        """Initialize the connection manager and create initial connections"""
        with self._lock:
            if self._state != ConnectionState.UNINITIALIZED:
                self._logger.warning(f"Connection manager already initialized (state: {self._state})")
                return self._state == ConnectionState.CONNECTED
            
            try:
                self._state = ConnectionState.CONNECTING
                self._logger.info(f"Initializing SQLite connection manager for {self._config.database_path}")
                
                # Ensure database directory exists
                db_path = Path(self._config.database_path)
                db_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Create initial pool connections
                self._create_initial_connections()
                
                # Test database health
                if not self.health_check():
                    raise DatabaseError("Database health check failed during initialization")
                
                self._state = ConnectionState.CONNECTED
                self._logger.info("SQLite connection manager initialized successfully")
                return True
                
            except Exception as e:
                self._state = ConnectionState.ERROR
                self._logger.error(f"Failed to initialize connection manager: {e}")
                self._cleanup_connections()
                return False
    
    def _create_initial_connections(self) -> None:
        """Create initial connections for the pool"""
        for i in range(self._config.min_pool_size):
            try:
                connection = self._create_connection()
                self._connection_pool.put(connection, block=False)
                self._stats.total_connections += 1
                self._stats.idle_connections += 1
            except Exception as e:
                self._logger.error(f"Failed to create initial connection {i}: {e}")
                raise DatabaseError(f"Failed to create initial connections: {e}")
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection with optimized settings"""
        try:
            # Connect with timeout
            connection = sqlite3.connect(
                self._config.database_path,
                timeout=self._config.connection_timeout,
                check_same_thread=False  # Allow sharing between threads
            )
            
            # Configure connection
            self._configure_connection(connection)
            
            return connection
            
        except Exception as e:
            self._stats.connection_errors += 1
            raise DatabaseError(f"Failed to create database connection: {e}")
    
    def _configure_connection(self, connection: sqlite3.Connection) -> None:
        """Configure connection with optimal settings"""
        # Set row factory to enable column name access
        connection.row_factory = sqlite3.Row
        
        cursor = connection.cursor()
        
        try:
            # Set page size FIRST - must be done before any other operations
            cursor.execute(f"PRAGMA page_size = {self._config.page_size}")
            
            # Enable foreign key constraints
            if self._config.enable_foreign_keys:
                cursor.execute("PRAGMA foreign_keys = ON")
            
            # Enable WAL mode for better concurrency
            if self._config.enable_wal_mode:
                cursor.execute("PRAGMA journal_mode = WAL")
            
            # Set cache size
            cursor.execute(f"PRAGMA cache_size = {self._config.cache_size}")
            
            # Set synchronous mode for better performance
            cursor.execute("PRAGMA synchronous = NORMAL")
            
            # Set temp store to memory
            cursor.execute("PRAGMA temp_store = MEMORY")
            
            connection.commit()
            
        finally:
            cursor.close()
    
    def get_connection(self) -> sqlite3.Connection:
        """Get a connection from the pool with timeout handling"""
        if self._state != ConnectionState.CONNECTED:
            raise ConnectionPoolError(f"Connection manager not ready (state: {self._state})")
        
        if self._shutdown_event.is_set():
            raise ConnectionPoolError("Connection manager is shutting down")
        
        self._stats.connection_requests += 1
        
        try:
            # Try to get existing connection from pool
            try:
                connection = self._connection_pool.get(timeout=self._config.pool_timeout)
                
                # Validate connection is still alive
                if self._is_connection_alive(connection):
                    with self._lock:
                        conn_id = id(connection)
                        self._active_connections[conn_id] = connection
                        self._stats.active_connections += 1
                        self._stats.idle_connections -= 1
                        self._stats.max_connections_used = max(
                            self._stats.max_connections_used,
                            self._stats.active_connections
                        )
                    return connection
                else:
                    # Connection is dead, close it and create new one
                    self._close_connection(connection)
                    self._stats.total_connections -= 1
                    
            except queue.Empty:
                # No connections available in pool
                pass
            
            # Create new connection if pool not at max capacity
            with self._lock:
                if self._stats.total_connections < self._config.max_pool_size:
                    connection = self._create_connection()
                    conn_id = id(connection)
                    self._active_connections[conn_id] = connection
                    self._stats.total_connections += 1
                    self._stats.active_connections += 1
                    self._stats.max_connections_used = max(
                        self._stats.max_connections_used,
                        self._stats.active_connections
                    )
                    return connection
                else:
                    # Pool is at max capacity, wait for connection
                    self._stats.connection_timeouts += 1
                    raise ConnectionTimeoutError(
                        f"Connection pool exhausted. Max size: {self._config.max_pool_size}"
                    )
                    
        except Exception as e:
            self._stats.connection_errors += 1
            if isinstance(e, (ConnectionPoolError, ConnectionTimeoutError)):
                raise
            raise ConnectionPoolError(f"Failed to get connection: {e}")
    
    def return_connection(self, connection: sqlite3.Connection) -> None:
        """Return a connection to the pool"""
        if not connection:
            return
        
        conn_id = id(connection)
        
        with self._lock:
            if conn_id not in self._active_connections:
                self._logger.warning("Attempting to return unknown connection")
                return
            
            # Remove from active connections
            del self._active_connections[conn_id]
            self._stats.active_connections -= 1
            
            # Check if connection is still alive
            if self._is_connection_alive(connection):
                try:
                    # Rollback any uncommitted transactions
                    connection.rollback()
                    
                    # Return to pool if not shutting down
                    if not self._shutdown_event.is_set():
                        self._connection_pool.put(connection, block=False)
                        self._stats.idle_connections += 1
                    else:
                        self._close_connection(connection)
                        self._stats.total_connections -= 1
                        
                except queue.Full:
                    # Pool is full, close the connection
                    self._close_connection(connection)
                    self._stats.total_connections -= 1
                except Exception as e:
                    self._logger.error(f"Error returning connection to pool: {e}")
                    self._close_connection(connection)
                    self._stats.total_connections -= 1
            else:
                # Connection is dead, close it
                self._close_connection(connection)
                self._stats.total_connections -= 1
    
    def _is_connection_alive(self, connection: sqlite3.Connection) -> bool:
        """Check if a connection is still alive"""
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            return True
        except Exception:
            return False
    
    def _close_connection(self, connection: sqlite3.Connection) -> None:
        """Safely close a database connection"""
        try:
            connection.close()
        except Exception as e:
            self._logger.warning(f"Error closing connection: {e}")
    
    def health_check(self) -> bool:
        """Perform a health check on the database"""
        try:
            # Allow health check during initialization process
            if self._state in [ConnectionState.UNINITIALIZED, ConnectionState.DISCONNECTED, ConnectionState.ERROR]:
                return False
            
            # For CONNECTING state, create a temporary connection instead of using pool
            if self._state == ConnectionState.CONNECTING:
                try:
                    temp_conn = self._create_connection()
                    cursor = temp_conn.cursor()
                    cursor.execute("SELECT sqlite_version(), datetime('now')")
                    result = cursor.fetchone()
                    cursor.close()
                    temp_conn.close()
                    
                    if result:
                        version, timestamp = result
                        self._logger.debug(f"Database health check passed. SQLite version: {version}, Time: {timestamp}")
                        return True
                    else:
                        self._logger.error("Health check failed: No result from test query")
                        return False
                except Exception as e:
                    self._logger.error(f"Health check failed during initialization: {e}")
                    return False
            
            # Normal health check for connected state
            connection = self.get_connection()
            try:
                cursor = connection.cursor()
                cursor.execute("SELECT sqlite_version(), datetime('now')")
                result = cursor.fetchone()
                cursor.close()
                
                if result:
                    version, timestamp = result
                    self._logger.debug(f"Database health check passed. SQLite version: {version}, Time: {timestamp}")
                    return True
                else:
                    self._logger.error("Health check failed: No result from test query")
                    return False
                    
            finally:
                self.return_connection(connection)
                
        except Exception as e:
            self._logger.error(f"Database health check failed: {e}")
            return False
    
    def get_stats(self) -> ConnectionStats:
        """Get current connection pool statistics"""
        with self._lock:
            return ConnectionStats(
                active_connections=self._stats.active_connections,
                idle_connections=self._stats.idle_connections,
                total_connections=self._stats.total_connections,
                max_connections_used=self._stats.max_connections_used,
                connection_requests=self._stats.connection_requests,
                connection_timeouts=self._stats.connection_timeouts,
                connection_errors=self._stats.connection_errors,
                total_queries=self._stats.total_queries
            )
    
    def shutdown(self) -> bool:
        """Shutdown the connection manager and cleanup resources"""
        with self._lock:
            if self._state in [ConnectionState.DISCONNECTED, ConnectionState.UNINITIALIZED]:
                return True
            
            try:
                self._logger.info("Shutting down connection manager...")
                self._shutdown_event.set()
                self._state = ConnectionState.DISCONNECTED
                
                # Close all active connections
                for conn_id, connection in list(self._active_connections.items()):
                    self._logger.debug(f"Closing active connection {conn_id}")
                    self._close_connection(connection)
                
                self._active_connections.clear()
                
                # Close all pooled connections
                self._cleanup_connections()
                
                self._logger.info("Connection manager shutdown complete")
                return True
                
            except Exception as e:
                self._logger.error(f"Error during shutdown: {e}")
                return False
    
    def _cleanup_connections(self) -> None:
        """Cleanup all connections in the pool"""
        while True:
            try:
                connection = self._connection_pool.get_nowait()
                self._close_connection(connection)
            except queue.Empty:
                break
            except Exception as e:
                self._logger.error(f"Error cleaning up connection: {e}")
        
        # Reset stats
        self._stats.active_connections = 0
        self._stats.idle_connections = 0
        self._stats.total_connections = 0
    
    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for getting and returning connections"""
        conn = self.get_connection()
        try:
            yield conn
        finally:
            self.return_connection(conn)
    
    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for database transactions"""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self.return_connection(conn)


# Global connection manager instance
_connection_manager: Optional[SQLiteConnectionManager] = None
_manager_lock = threading.Lock()


def get_connection_manager() -> SQLiteConnectionManager:
    """Get the global connection manager instance (singleton)"""
    global _connection_manager
    
    with _manager_lock:
        if _connection_manager is None:
            # Get database path from config
            from core.config_manager import get_config
            config = get_config()
            
            db_config = ConnectionConfig(
                database_path=config.database.path,
                max_pool_size=getattr(config.database, 'max_pool_size', 10),
                min_pool_size=getattr(config.database, 'min_pool_size', 2),
                connection_timeout=getattr(config.database, 'connection_timeout', 30.0),
                enable_wal_mode=getattr(config.database, 'enable_wal_mode', True),
                enable_foreign_keys=getattr(config.database, 'enable_foreign_keys', True)
            )
            
            _connection_manager = SQLiteConnectionManager(db_config)
        
        return _connection_manager


def initialize_database() -> bool:
    """Initialize the global database connection manager"""
    manager = get_connection_manager()
    return manager.initialize()


def shutdown_database() -> bool:
    """Shutdown the global database connection manager"""
    global _connection_manager
    
    with _manager_lock:
        if _connection_manager:
            result = _connection_manager.shutdown()
            _connection_manager = None
            return result
        return True


def get_connection() -> sqlite3.Connection:
    """Get a database connection from the global manager"""
    manager = get_connection_manager()
    return manager.get_connection()


def return_connection(connection: sqlite3.Connection) -> None:
    """Return a database connection to the global manager"""
    manager = get_connection_manager()
    manager.return_connection(connection)


@contextmanager
def database_connection() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database connections"""
    manager = get_connection_manager()
    with manager.connection() as conn:
        yield conn


@contextmanager
def database_transaction() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database transactions"""
    manager = get_connection_manager()
    with manager.transaction() as conn:
        yield conn 