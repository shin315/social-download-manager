"""
Database Exception Hierarchy

This module provides a comprehensive exception hierarchy for database operations,
including structured error codes, contextual information, and specialized exceptions
for different types of database failures.
"""

import sqlite3
from enum import Enum
from typing import Any, Dict, Optional, List, Union
from dataclasses import dataclass


class DatabaseErrorCode(Enum):
    """Structured error codes for database operations"""
    
    # Connection-related errors (1xx)
    CONNECTION_FAILED = "DB_001"
    CONNECTION_TIMEOUT = "DB_002"
    CONNECTION_POOL_EXHAUSTED = "DB_003"
    CONNECTION_INVALID = "DB_004"
    CONNECTION_CLOSED = "DB_005"
    
    # Transaction-related errors (2xx)
    TRANSACTION_FAILED = "DB_201"
    TRANSACTION_TIMEOUT = "DB_202"
    TRANSACTION_DEADLOCK = "DB_203"
    TRANSACTION_ROLLBACK = "DB_204"
    TRANSACTION_INVALID_STATE = "DB_205"
    SAVEPOINT_FAILED = "DB_206"
    
    # SQL execution errors (3xx)
    SQL_SYNTAX_ERROR = "DB_301"
    SQL_CONSTRAINT_VIOLATION = "DB_302"
    SQL_FOREIGN_KEY_VIOLATION = "DB_303"
    SQL_UNIQUE_CONSTRAINT_VIOLATION = "DB_304"
    SQL_NOT_NULL_CONSTRAINT_VIOLATION = "DB_305"
    SQL_CHECK_CONSTRAINT_VIOLATION = "DB_306"
    SQL_EXECUTION_FAILED = "DB_307"
    
    # Schema and migration errors (4xx)
    MIGRATION_FAILED = "DB_401"
    MIGRATION_VALIDATION_FAILED = "DB_402"
    MIGRATION_ROLLBACK_FAILED = "DB_403"
    SCHEMA_MISMATCH = "DB_404"
    TABLE_NOT_FOUND = "DB_405"
    COLUMN_NOT_FOUND = "DB_406"
    
    # Data integrity errors (5xx)
    DATA_VALIDATION_FAILED = "DB_501"
    DATA_CORRUPTION = "DB_502"
    DUPLICATE_ENTRY = "DB_503"
    FOREIGN_KEY_CONSTRAINT = "DB_504"
    
    # Repository and model errors (6xx)
    REPOSITORY_OPERATION_FAILED = "DB_601"
    MODEL_VALIDATION_FAILED = "DB_602"
    ENTITY_NOT_FOUND = "DB_603"
    ENTITY_ALREADY_EXISTS = "DB_604"
    
    # Performance and resource errors (7xx)
    QUERY_TIMEOUT = "DB_701"
    MEMORY_LIMIT_EXCEEDED = "DB_702"
    DISK_SPACE_INSUFFICIENT = "DB_703"
    LOCK_TIMEOUT = "DB_704"
    
    # Configuration and setup errors (8xx)
    CONFIGURATION_INVALID = "DB_801"
    DATABASE_NOT_FOUND = "DB_802"
    PERMISSIONS_DENIED = "DB_803"
    VERSION_MISMATCH = "DB_804"
    
    # Unknown and generic errors (9xx)
    UNKNOWN_ERROR = "DB_901"
    INTERNAL_ERROR = "DB_902"
    EXTERNAL_DEPENDENCY_FAILED = "DB_903"


@dataclass
class DatabaseErrorContext:
    """Contextual information for database errors"""
    
    operation: str
    table: Optional[str] = None
    query: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    connection_id: Optional[str] = None
    transaction_id: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    execution_time_ms: Optional[float] = None
    retry_count: Optional[int] = None
    additional_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for logging"""
        return {
            k: v for k, v in self.__dict__.items() 
            if v is not None
        }


class DatabaseError(Exception):
    """Base exception for all database-related errors"""
    
    def __init__(
        self,
        message: str,
        error_code: DatabaseErrorCode = DatabaseErrorCode.UNKNOWN_ERROR,
        context: Optional[DatabaseErrorContext] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or DatabaseErrorContext(operation="unknown")
        self.original_error = original_error
    
    def __str__(self) -> str:
        return f"[{self.error_code.value}] {self.message}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization"""
        result = {
            "error_code": self.error_code.value,
            "message": self.message,
            "context": self.context.to_dict()
        }
        
        if self.original_error:
            result["original_error"] = {
                "type": type(self.original_error).__name__,
                "message": str(self.original_error)
            }
        
        return result


# Connection-related exceptions
class ConnectionError(DatabaseError):
    """Base exception for connection-related errors"""
    pass


class ConnectionFailedError(ConnectionError):
    """Exception raised when database connection fails"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.CONNECTION_FAILED, context, original_error)


class ConnectionTimeoutError(ConnectionError):
    """Exception raised when connection times out"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.CONNECTION_TIMEOUT, context, original_error)


class ConnectionPoolExhaustedError(ConnectionError):
    """Exception raised when connection pool is exhausted"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.CONNECTION_POOL_EXHAUSTED, context, original_error)


class ConnectionInvalidError(ConnectionError):
    """Exception raised when connection is invalid or corrupted"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.CONNECTION_INVALID, context, original_error)


class ConnectionClosedError(ConnectionError):
    """Exception raised when attempting to use a closed connection"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.CONNECTION_CLOSED, context, original_error)


# Transaction-related exceptions
class TransactionError(DatabaseError):
    """Base exception for transaction-related errors"""
    pass


class TransactionFailedError(TransactionError):
    """Exception raised when transaction fails"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.TRANSACTION_FAILED, context, original_error)


class TransactionTimeoutError(TransactionError):
    """Exception raised when transaction times out"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.TRANSACTION_TIMEOUT, context, original_error)


class DeadlockError(TransactionError):
    """Exception raised when deadlock is detected"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.TRANSACTION_DEADLOCK, context, original_error)


class TransactionRollbackError(TransactionError):
    """Exception raised when transaction rollback fails"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.TRANSACTION_ROLLBACK, context, original_error)


class InvalidTransactionStateError(TransactionError):
    """Exception raised when transaction is in invalid state"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.TRANSACTION_INVALID_STATE, context, original_error)


class SavepointError(TransactionError):
    """Exception raised when savepoint operations fail"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.SAVEPOINT_FAILED, context, original_error)


# SQL execution exceptions
class SQLError(DatabaseError):
    """Base exception for SQL execution errors"""
    pass


class SQLSyntaxError(SQLError):
    """Exception raised for SQL syntax errors"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.SQL_SYNTAX_ERROR, context, original_error)


class ConstraintViolationError(SQLError):
    """Exception raised for constraint violations"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.SQL_CONSTRAINT_VIOLATION, context, original_error)


class ForeignKeyViolationError(ConstraintViolationError):
    """Exception raised for foreign key constraint violations"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.SQL_FOREIGN_KEY_VIOLATION, context, original_error)


class UniqueConstraintViolationError(ConstraintViolationError):
    """Exception raised for unique constraint violations"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.SQL_UNIQUE_CONSTRAINT_VIOLATION, context, original_error)


class NotNullConstraintViolationError(ConstraintViolationError):
    """Exception raised for NOT NULL constraint violations"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.SQL_NOT_NULL_CONSTRAINT_VIOLATION, context, original_error)


class CheckConstraintViolationError(ConstraintViolationError):
    """Exception raised for CHECK constraint violations"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.SQL_CHECK_CONSTRAINT_VIOLATION, context, original_error)


class SQLExecutionError(SQLError):
    """Exception raised for general SQL execution failures"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.SQL_EXECUTION_FAILED, context, original_error)


# Schema and migration exceptions
class SchemaError(DatabaseError):
    """Base exception for schema-related errors"""
    pass


class MigrationError(SchemaError):
    """Exception raised for migration failures"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.MIGRATION_FAILED, context, original_error)


class MigrationValidationError(SchemaError):
    """Exception raised for migration validation failures"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.MIGRATION_VALIDATION_FAILED, context, original_error)


class MigrationRollbackError(SchemaError):
    """Exception raised for migration rollback failures"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.MIGRATION_ROLLBACK_FAILED, context, original_error)


class SchemaMismatchError(SchemaError):
    """Exception raised for schema mismatches"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.SCHEMA_MISMATCH, context, original_error)


class TableNotFoundError(SchemaError):
    """Exception raised when table is not found"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.TABLE_NOT_FOUND, context, original_error)


class ColumnNotFoundError(SchemaError):
    """Exception raised when column is not found"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.COLUMN_NOT_FOUND, context, original_error)


# Data integrity exceptions
class DataIntegrityError(DatabaseError):
    """Base exception for data integrity errors"""
    pass


class DataValidationError(DataIntegrityError):
    """Exception raised for data validation failures"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.DATA_VALIDATION_FAILED, context, original_error)


class DataCorruptionError(DataIntegrityError):
    """Exception raised for data corruption"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.DATA_CORRUPTION, context, original_error)


class DuplicateEntryError(DataIntegrityError):
    """Exception raised for duplicate entries"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.DUPLICATE_ENTRY, context, original_error)


# Repository and model exceptions
class RepositoryError(DatabaseError):
    """Base exception for repository operations"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.REPOSITORY_OPERATION_FAILED, context, original_error)


class ModelValidationError(DatabaseError):
    """Exception raised for model validation failures"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.MODEL_VALIDATION_FAILED, context, original_error)


class EntityNotFoundError(RepositoryError):
    """Exception raised when entity is not found"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.ENTITY_NOT_FOUND, context, original_error)


class EntityAlreadyExistsError(RepositoryError):
    """Exception raised when entity already exists"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.ENTITY_ALREADY_EXISTS, context, original_error)


# Performance and resource exceptions
class PerformanceError(DatabaseError):
    """Base exception for performance-related errors"""
    pass


class QueryTimeoutError(PerformanceError):
    """Exception raised when query times out"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.QUERY_TIMEOUT, context, original_error)


class MemoryLimitExceededError(PerformanceError):
    """Exception raised when memory limit is exceeded"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.MEMORY_LIMIT_EXCEEDED, context, original_error)


class DiskSpaceInsufficientError(PerformanceError):
    """Exception raised when disk space is insufficient"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.DISK_SPACE_INSUFFICIENT, context, original_error)


class LockTimeoutError(PerformanceError):
    """Exception raised when lock timeout occurs"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.LOCK_TIMEOUT, context, original_error)


# Configuration exceptions
class ConfigurationError(DatabaseError):
    """Base exception for configuration errors"""
    pass


class InvalidConfigurationError(ConfigurationError):
    """Exception raised for invalid configuration"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.CONFIGURATION_INVALID, context, original_error)


class DatabaseNotFoundError(ConfigurationError):
    """Exception raised when database file is not found"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.DATABASE_NOT_FOUND, context, original_error)


class PermissionsDeniedError(ConfigurationError):
    """Exception raised when database permissions are denied"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.PERMISSIONS_DENIED, context, original_error)


class VersionMismatchError(ConfigurationError):
    """Exception raised for version mismatches"""
    
    def __init__(self, message: str, context: Optional[DatabaseErrorContext] = None, original_error: Optional[Exception] = None):
        super().__init__(message, DatabaseErrorCode.VERSION_MISMATCH, context, original_error)


def parse_sqlite_error(
    error: sqlite3.Error,
    operation: str,
    context: Optional[DatabaseErrorContext] = None
) -> DatabaseError:
    """
    Parse SQLite error and convert to appropriate DatabaseError subclass
    
    Args:
        error: The original SQLite error
        operation: The operation that caused the error
        context: Additional context information
        
    Returns:
        Appropriate DatabaseError subclass
    """
    
    error_message = str(error).lower()
    
    if context is None:
        context = DatabaseErrorContext(operation=operation)
    else:
        context.operation = operation
    
    # Connection errors
    if "database is locked" in error_message:
        return LockTimeoutError("Database is locked", context, error)
    elif "no such table" in error_message:
        return TableNotFoundError(f"Table not found during {operation}", context, error)
    elif "no such column" in error_message:
        return ColumnNotFoundError(f"Column not found during {operation}", context, error)
    
    # Constraint violations
    elif "unique constraint failed" in error_message:
        return UniqueConstraintViolationError(f"Unique constraint violation during {operation}", context, error)
    elif "not null constraint failed" in error_message:
        return NotNullConstraintViolationError(f"NOT NULL constraint violation during {operation}", context, error)
    elif "foreign key constraint failed" in error_message:
        return ForeignKeyViolationError(f"Foreign key constraint violation during {operation}", context, error)
    elif "check constraint failed" in error_message:
        return CheckConstraintViolationError(f"CHECK constraint violation during {operation}", context, error)
    elif "constraint failed" in error_message:
        return ConstraintViolationError(f"Constraint violation during {operation}", context, error)
    
    # SQL syntax errors
    elif "syntax error" in error_message:
        return SQLSyntaxError(f"SQL syntax error during {operation}", context, error)
    
    # Transaction errors
    elif "deadlock" in error_message:
        return DeadlockError(f"Deadlock detected during {operation}", context, error)
    
    # Disk and I/O errors
    elif "disk" in error_message and ("full" in error_message or "space" in error_message):
        return DiskSpaceInsufficientError(f"Insufficient disk space during {operation}", context, error)
    elif "permission denied" in error_message:
        return PermissionsDeniedError(f"Permission denied during {operation}", context, error)
    elif "database disk image is malformed" in error_message:
        return DataCorruptionError(f"Database corruption detected during {operation}", context, error)
    
    # Generic SQL execution error
    return SQLExecutionError(f"SQL execution failed during {operation}: {error}", context, error)


def create_error_context(
    operation: str,
    table: Optional[str] = None,
    query: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
    transaction_id: Optional[str] = None,
    execution_time_ms: Optional[float] = None,
    **kwargs
) -> DatabaseErrorContext:
    """
    Convenience function to create DatabaseErrorContext
    
    Args:
        operation: The database operation being performed
        table: The table involved in the operation
        query: The SQL query being executed
        parameters: Query parameters
        connection_id: Database connection identifier
        transaction_id: Transaction identifier
        execution_time_ms: Query execution time in milliseconds
        **kwargs: Additional context data
        
    Returns:
        DatabaseErrorContext instance
    """
    
    return DatabaseErrorContext(
        operation=operation,
        table=table,
        query=query,
        parameters=parameters,
        connection_id=connection_id,
        transaction_id=transaction_id,
        execution_time_ms=execution_time_ms,
        additional_data=kwargs if kwargs else None
    ) 