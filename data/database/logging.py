"""
Database Logging Framework

This module provides comprehensive logging for database operations including
performance monitoring, structured logging, query analysis, and contextual information
for troubleshooting and observability.
"""

import json
import logging
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable
from functools import wraps
import threading
from pathlib import Path

from .exceptions import DatabaseError, DatabaseErrorContext


class LogLevel(Enum):
    """Database-specific log levels"""
    TRACE = "TRACE"      # Detailed execution flow
    DEBUG = "DEBUG"      # Debug information
    INFO = "INFO"        # General information
    WARN = "WARN"        # Warning conditions
    ERROR = "ERROR"      # Error conditions
    CRITICAL = "CRITICAL" # Critical failures


class OperationType(Enum):
    """Types of database operations for categorization"""
    QUERY = "QUERY"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    TRANSACTION = "TRANSACTION"
    CONNECTION = "CONNECTION"
    MIGRATION = "MIGRATION"
    SCHEMA = "SCHEMA"
    MAINTENANCE = "MAINTENANCE"


@dataclass
class QueryMetrics:
    """Metrics for database query performance"""
    
    query_hash: str
    execution_time_ms: float
    rows_affected: Optional[int] = None
    rows_returned: Optional[int] = None
    memory_usage_mb: Optional[float] = None
    cpu_time_ms: Optional[float] = None
    io_reads: Optional[int] = None
    io_writes: Optional[int] = None
    cache_hits: Optional[int] = None
    cache_misses: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class DatabaseLogEntry:
    """Structured database log entry"""
    
    timestamp: datetime
    level: LogLevel
    operation_type: OperationType
    operation: str
    message: str
    
    # Context information
    connection_id: Optional[str] = None
    transaction_id: Optional[str] = None
    thread_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Query information
    table: Optional[str] = None
    query: Optional[str] = None
    query_hash: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    
    # Performance metrics
    metrics: Optional[QueryMetrics] = None
    
    # Error information
    error_code: Optional[str] = None
    error_context: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None
    
    # Additional metadata
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "operation_type": self.operation_type.value,
            "operation": self.operation,
            "message": self.message
        }
        
        # Add non-None fields
        for field in ["connection_id", "transaction_id", "thread_id", "session_id",
                     "table", "query", "query_hash", "parameters", "error_code",
                     "error_context", "stack_trace", "metadata"]:
            value = getattr(self, field)
            if value is not None:
                result[field] = value
        
        # Add metrics if present
        if self.metrics:
            result["metrics"] = self.metrics.to_dict()
        
        return result


class DatabaseLogger:
    """Enhanced database logger with structured logging and performance monitoring"""
    
    def __init__(
        self,
        name: str = "database",
        log_level: LogLevel = LogLevel.INFO,
        enable_performance_logging: bool = True,
        enable_query_logging: bool = True,
        log_file_path: Optional[str] = None,
        max_query_length: int = 1000,
        sensitive_patterns: Optional[List[str]] = None
    ):
        self.name = name
        self.log_level = log_level
        self.enable_performance_logging = enable_performance_logging
        self.enable_query_logging = enable_query_logging
        self.max_query_length = max_query_length
        self.sensitive_patterns = sensitive_patterns or ["password", "token", "secret", "key"]
        
        # Setup logger
        self._logger = logging.getLogger(f"database.{name}")
        self._logger.setLevel(getattr(logging, log_level.value))
        
        # Setup handlers
        self._setup_handlers(log_file_path)
        
        # Performance tracking
        self._query_stats: Dict[str, List[float]] = {}
        self._operation_counts: Dict[str, int] = {}
        self._lock = threading.Lock()
        
        # Session tracking
        self._current_session_id: Optional[str] = None
        
    def _setup_handlers(self, log_file_path: Optional[str]) -> None:
        """Setup logging handlers"""
        
        # Console handler with structured format
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self._logger.addHandler(console_handler)
        
        # File handler for structured JSON logs if specified
        if log_file_path:
            log_path = Path(log_file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_path)
            file_formatter = logging.Formatter('%(message)s')  # Raw JSON
            file_handler.setFormatter(file_formatter)
            self._logger.addHandler(file_handler)
    
    def _sanitize_query(self, query: str) -> str:
        """Remove sensitive information from query"""
        if not query:
            return query
        
        sanitized = query
        for pattern in self.sensitive_patterns:
            if pattern.lower() in query.lower():
                # Replace sensitive values with placeholder
                import re
                sanitized = re.sub(
                    rf"({pattern}\s*=\s*['\"])[^'\"]*(['\"])",
                    r"\1***\2",
                    sanitized,
                    flags=re.IGNORECASE
                )
        
        # Truncate if too long
        if len(sanitized) > self.max_query_length:
            sanitized = sanitized[:self.max_query_length] + "..."
        
        return sanitized
    
    def _generate_query_hash(self, query: str) -> str:
        """Generate hash for query pattern analysis"""
        import hashlib
        # Normalize query for pattern matching
        normalized = " ".join(query.split()).upper()
        return hashlib.md5(normalized.encode()).hexdigest()[:12]
    
    def _should_log(self, level: LogLevel) -> bool:
        """Check if message should be logged based on current log level"""
        level_hierarchy = {
            LogLevel.TRACE: 10,
            LogLevel.DEBUG: 20,
            LogLevel.INFO: 30,
            LogLevel.WARN: 40,
            LogLevel.ERROR: 50,
            LogLevel.CRITICAL: 60
        }
        return level_hierarchy[level] >= level_hierarchy[self.log_level]
    
    def log_entry(self, entry: DatabaseLogEntry) -> None:
        """Log a structured database entry"""
        if not self._should_log(entry.level):
            return
        
        # Convert to JSON for structured logging
        log_data = entry.to_dict()
        json_message = json.dumps(log_data, ensure_ascii=False, separators=(',', ':'))
        
        # Log using appropriate Python logging level
        python_level = getattr(logging, entry.level.value)
        self._logger.log(python_level, json_message)
    
    def log_operation(
        self,
        level: LogLevel,
        operation_type: OperationType,
        operation: str,
        message: str,
        **kwargs
    ) -> None:
        """Log a database operation with context"""
        
        entry = DatabaseLogEntry(
            timestamp=datetime.now(),
            level=level,
            operation_type=operation_type,
            operation=operation,
            message=message,
            thread_id=str(threading.current_thread().ident),
            session_id=self._current_session_id,
            **kwargs
        )
        
        self.log_entry(entry)
        
        # Update operation counts
        with self._lock:
            self._operation_counts[operation] = self._operation_counts.get(operation, 0) + 1
    
    def log_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        execution_time_ms: Optional[float] = None,
        rows_affected: Optional[int] = None,
        rows_returned: Optional[int] = None,
        connection_id: Optional[str] = None,
        transaction_id: Optional[str] = None,
        table: Optional[str] = None,
        error: Optional[Exception] = None
    ) -> None:
        """Log a database query with performance metrics"""
        
        if not self.enable_query_logging:
            return
        
        sanitized_query = self._sanitize_query(query)
        query_hash = self._generate_query_hash(query)
        
        # Determine log level
        if error:
            level = LogLevel.ERROR
            message = f"Query failed: {sanitized_query}"
        elif execution_time_ms and execution_time_ms > 1000:  # Slow query threshold
            level = LogLevel.WARN
            message = f"Slow query detected: {sanitized_query}"
        else:
            level = LogLevel.DEBUG
            message = f"Query executed: {sanitized_query}"
        
        # Create metrics if performance logging is enabled
        metrics = None
        if self.enable_performance_logging and execution_time_ms is not None:
            metrics = QueryMetrics(
                query_hash=query_hash,
                execution_time_ms=execution_time_ms,
                rows_affected=rows_affected,
                rows_returned=rows_returned
            )
            
            # Track query performance statistics
            with self._lock:
                if query_hash not in self._query_stats:
                    self._query_stats[query_hash] = []
                self._query_stats[query_hash].append(execution_time_ms)
        
        # Create error context if error occurred
        error_context = None
        error_code = None
        if error:
            if isinstance(error, DatabaseError):
                error_code = error.error_code.value
                error_context = error.context.to_dict()
            else:
                error_context = {"type": type(error).__name__, "message": str(error)}
        
        self.log_operation(
            level=level,
            operation_type=OperationType.QUERY,
            operation="execute_query",
            message=message,
            connection_id=connection_id,
            transaction_id=transaction_id,
            table=table,
            query=sanitized_query,
            query_hash=query_hash,
            parameters=parameters,
            metrics=metrics,
            error_code=error_code,
            error_context=error_context
        )
    
    def log_transaction(
        self,
        transaction_id: str,
        operation: str,
        message: str,
        level: LogLevel = LogLevel.INFO,
        connection_id: Optional[str] = None,
        duration_ms: Optional[float] = None,
        error: Optional[Exception] = None
    ) -> None:
        """Log transaction-related operations"""
        
        # Create metrics for transaction duration
        metrics = None
        if duration_ms is not None:
            metrics = QueryMetrics(
                query_hash=f"transaction_{operation}",
                execution_time_ms=duration_ms
            )
        
        # Handle error context
        error_context = None
        error_code = None
        if error:
            level = LogLevel.ERROR
            if isinstance(error, DatabaseError):
                error_code = error.error_code.value
                error_context = error.context.to_dict()
            else:
                error_context = {"type": type(error).__name__, "message": str(error)}
        
        self.log_operation(
            level=level,
            operation_type=OperationType.TRANSACTION,
            operation=operation,
            message=message,
            connection_id=connection_id,
            transaction_id=transaction_id,
            metrics=metrics,
            error_code=error_code,
            error_context=error_context
        )
    
    def log_connection(
        self,
        connection_id: str,
        operation: str,
        message: str,
        level: LogLevel = LogLevel.INFO,
        duration_ms: Optional[float] = None,
        error: Optional[Exception] = None
    ) -> None:
        """Log connection-related operations"""
        
        metrics = None
        if duration_ms is not None:
            metrics = QueryMetrics(
                query_hash=f"connection_{operation}",
                execution_time_ms=duration_ms
            )
        
        error_context = None
        error_code = None
        if error:
            level = LogLevel.ERROR
            if isinstance(error, DatabaseError):
                error_code = error.error_code.value
                error_context = error.context.to_dict()
            else:
                error_context = {"type": type(error).__name__, "message": str(error)}
        
        self.log_operation(
            level=level,
            operation_type=OperationType.CONNECTION,
            operation=operation,
            message=message,
            connection_id=connection_id,
            metrics=metrics,
            error_code=error_code,
            error_context=error_context
        )
    
    def log_error(
        self,
        error: Exception,
        operation: str,
        context: Optional[DatabaseErrorContext] = None,
        additional_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log database errors with full context"""
        
        error_context = None
        error_code = None
        
        if isinstance(error, DatabaseError):
            error_code = error.error_code.value
            error_context = error.context.to_dict()
        else:
            error_context = {"type": type(error).__name__, "message": str(error)}
        
        if context:
            error_context.update(context.to_dict())
        
        if additional_info:
            error_context.update(additional_info)
        
        # Determine operation type from context
        operation_type = OperationType.QUERY
        if context and context.operation:
            if "transaction" in context.operation.lower():
                operation_type = OperationType.TRANSACTION
            elif "connection" in context.operation.lower():
                operation_type = OperationType.CONNECTION
            elif "migration" in context.operation.lower():
                operation_type = OperationType.MIGRATION
        
        self.log_operation(
            level=LogLevel.ERROR,
            operation_type=operation_type,
            operation=operation,
            message=f"Database error in {operation}: {str(error)}",
            connection_id=context.connection_id if context else None,
            transaction_id=context.transaction_id if context else None,
            table=context.table if context else None,
            query=self._sanitize_query(context.query) if context and context.query else None,
            error_code=error_code,
            error_context=error_context
        )
    
    def set_session_id(self, session_id: str) -> None:
        """Set session ID for correlation"""
        self._current_session_id = session_id
    
    def get_query_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get query performance statistics"""
        with self._lock:
            stats = {}
            for query_hash, times in self._query_stats.items():
                if times:
                    stats[query_hash] = {
                        "count": len(times),
                        "avg_time_ms": sum(times) / len(times),
                        "min_time_ms": min(times),
                        "max_time_ms": max(times),
                        "total_time_ms": sum(times)
                    }
            return stats
    
    def get_operation_counts(self) -> Dict[str, int]:
        """Get operation counts"""
        with self._lock:
            return self._operation_counts.copy()
    
    def reset_statistics(self) -> None:
        """Reset performance statistics"""
        with self._lock:
            self._query_stats.clear()
            self._operation_counts.clear()


# Context managers for operation logging
@contextmanager
def log_query_execution(
    logger: DatabaseLogger,
    query: str,
    parameters: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
    transaction_id: Optional[str] = None,
    table: Optional[str] = None
):
    """Context manager for logging query execution with timing"""
    
    start_time = time.time()
    error = None
    rows_affected = None
    rows_returned = None
    
    try:
        yield
    except Exception as e:
        error = e
        raise
    finally:
        execution_time_ms = (time.time() - start_time) * 1000
        logger.log_query(
            query=query,
            parameters=parameters,
            execution_time_ms=execution_time_ms,
            rows_affected=rows_affected,
            rows_returned=rows_returned,
            connection_id=connection_id,
            transaction_id=transaction_id,
            table=table,
            error=error
        )


@contextmanager
def log_transaction_execution(
    logger: DatabaseLogger,
    transaction_id: str,
    operation: str,
    connection_id: Optional[str] = None
):
    """Context manager for logging transaction execution with timing"""
    
    start_time = time.time()
    error = None
    
    logger.log_transaction(
        transaction_id=transaction_id,
        operation=f"{operation}_start",
        message=f"Starting {operation}",
        connection_id=connection_id
    )
    
    try:
        yield
    except Exception as e:
        error = e
        raise
    finally:
        duration_ms = (time.time() - start_time) * 1000
        
        if error:
            logger.log_transaction(
                transaction_id=transaction_id,
                operation=f"{operation}_failed",
                message=f"Transaction {operation} failed: {str(error)}",
                connection_id=connection_id,
                duration_ms=duration_ms,
                error=error
            )
        else:
            logger.log_transaction(
                transaction_id=transaction_id,
                operation=f"{operation}_complete",
                message=f"Transaction {operation} completed successfully",
                connection_id=connection_id,
                duration_ms=duration_ms
            )


def log_database_operation(
    operation_type: OperationType,
    operation: str,
    logger: Optional[DatabaseLogger] = None
):
    """Decorator for logging database operations"""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get logger from arguments or use default
            used_logger = logger
            if not used_logger:
                # Try to get logger from self if it's a method
                if args and hasattr(args[0], '_logger') and isinstance(args[0]._logger, DatabaseLogger):
                    used_logger = args[0]._logger
                else:
                    # Create default logger
                    used_logger = DatabaseLogger("default")
            
            start_time = time.time()
            error = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                error = e
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                
                metrics = QueryMetrics(
                    query_hash=f"{func.__name__}_{operation}",
                    execution_time_ms=duration_ms
                )
                
                level = LogLevel.ERROR if error else LogLevel.INFO
                message = f"Operation {operation} completed"
                if error:
                    message = f"Operation {operation} failed: {str(error)}"
                
                used_logger.log_operation(
                    level=level,
                    operation_type=operation_type,
                    operation=operation,
                    message=message,
                    metrics=metrics,
                    error_code=error.error_code.value if isinstance(error, DatabaseError) else None,
                    error_context=error.context.to_dict() if isinstance(error, DatabaseError) else None
                )
        
        return wrapper
    return decorator


# Global logger instance
_default_logger: Optional[DatabaseLogger] = None


def get_default_logger() -> DatabaseLogger:
    """Get or create default database logger"""
    global _default_logger
    if _default_logger is None:
        _default_logger = DatabaseLogger("default")
    return _default_logger


def configure_default_logger(
    log_level: LogLevel = LogLevel.INFO,
    enable_performance_logging: bool = True,
    enable_query_logging: bool = True,
    log_file_path: Optional[str] = None
) -> DatabaseLogger:
    """Configure the default database logger"""
    global _default_logger
    _default_logger = DatabaseLogger(
        name="default",
        log_level=log_level,
        enable_performance_logging=enable_performance_logging,
        enable_query_logging=enable_query_logging,
        log_file_path=log_file_path
    )
    return _default_logger 