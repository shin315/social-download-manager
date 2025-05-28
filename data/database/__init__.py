"""
Database layer for Social Download Manager v2.0

Provides database connection management, connection pooling, transaction management,
comprehensive error handling, logging, retry policies, and monitoring capabilities.
"""

from .connection import (
    ConnectionState, ConnectionConfig, ConnectionStats,
    DatabaseError, ConnectionPoolError, ConnectionTimeoutError,
    IConnectionManager, SQLiteConnectionManager,
    get_connection_manager, initialize_database, shutdown_database,
    get_connection, return_connection,
    database_connection, database_transaction
)

from .transactions import (
    # Enums and types
    TransactionIsolationLevel, TransactionPropagation, TransactionStatus,
    
    # Exceptions
    TransactionException, DeadlockException, TransactionTimeoutException,
    InvalidTransactionStateException,
    
    # Core classes
    TransactionInfo, TransactionStatistics,
    ITransactionManager, Transaction, TransactionManager,
    
    # Global functions
    get_transaction_manager, initialize_transaction_manager,
    transaction, get_current_transaction
)

# Enhanced error handling and exceptions
from .exceptions import (
    # Error codes and context
    DatabaseErrorCode, DatabaseErrorContext,
    
    # Base exceptions
    DatabaseError, ConnectionError, TransactionError, SQLError,
    SchemaError, DataIntegrityError, PerformanceError, ConfigurationError,
    
    # Connection exceptions
    ConnectionFailedError, ConnectionTimeoutError, ConnectionPoolExhaustedError,
    ConnectionInvalidError, ConnectionClosedError,
    
    # Transaction exceptions  
    TransactionFailedError, TransactionTimeoutError, DeadlockError,
    TransactionRollbackError, InvalidTransactionStateError, SavepointError,
    
    # SQL execution exceptions
    SQLSyntaxError, ConstraintViolationError, ForeignKeyViolationError,
    UniqueConstraintViolationError, NotNullConstraintViolationError,
    CheckConstraintViolationError, SQLExecutionError,
    
    # Schema and migration exceptions
    MigrationError, MigrationValidationError, MigrationRollbackError,
    SchemaMismatchError, TableNotFoundError, ColumnNotFoundError,
    
    # Data integrity exceptions
    DataValidationError, DataCorruptionError, DuplicateEntryError,
    
    # Repository and model exceptions
    RepositoryError, ModelValidationError, EntityNotFoundError, EntityAlreadyExistsError,
    
    # Performance exceptions
    QueryTimeoutError, MemoryLimitExceededError, DiskSpaceInsufficientError, LockTimeoutError,
    
    # Configuration exceptions
    InvalidConfigurationError, DatabaseNotFoundError, PermissionsDeniedError, VersionMismatchError,
    
    # Utility functions
    parse_sqlite_error, create_error_context
)

# Comprehensive logging framework
from .logging import (
    # Enums and types
    LogLevel, OperationType,
    
    # Data classes
    QueryMetrics, DatabaseLogEntry,
    
    # Main logger class
    DatabaseLogger,
    
    # Context managers and decorators
    log_query_execution, log_transaction_execution, log_database_operation,
    
    # Global functions
    get_default_logger, configure_default_logger
)

# Retry policies and recovery
from .retry import (
    # Enums and types
    RetryStrategy, CircuitBreakerState,
    
    # Configuration classes
    RetryConfig, CircuitBreakerConfig,
    
    # Result classes
    RetryAttempt, RetryResult,
    
    # Retry policy implementations
    RetryPolicy, FixedDelayRetryPolicy, ExponentialBackoffRetryPolicy,
    LinearBackoffRetryPolicy, RandomJitterRetryPolicy,
    
    # Circuit breaker and deadlock detection
    CircuitBreaker, DeadlockDetector,
    
    # Decorators and utilities
    retry_database_operation,
    
    # Global functions
    get_default_circuit_breaker, get_default_deadlock_detector,
    configure_default_retry_policies
)

# Monitoring and observability
from .monitoring import (
    # Enums and types
    HealthStatus, AlertLevel,
    
    # Data classes
    HealthCheckResult, Alert,
    
    # Health check implementations
    HealthCheck, DatabaseConnectionHealthCheck,
    
    # Global functions
    get_default_monitor, configure_monitoring
)

# Migration system
from .migrations import (
    Migration, MigrationDirection, MigrationStatus,
    MigrationRecord, MigrationError, MigrationValidationError, MigrationExecutionError,
    IMigrationEngine, SQLiteMigrationEngine, create_migration_engine
) 