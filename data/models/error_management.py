"""
Error Management System for Social Download Manager v2.0

Provides comprehensive error handling with domain-specific exceptions,
error recovery strategies, logging, and monitoring capabilities.
"""

import logging
import traceback
from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Optional, Dict, Any, List, Callable, Type
from datetime import datetime, timezone
from dataclasses import dataclass, field

from .base import EntityId, ModelError


class ErrorSeverity(Enum):
    """Error severity levels for classification"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification"""
    VALIDATION = "validation"
    DATABASE = "database"
    NETWORK = "network"
    BUSINESS_LOGIC = "business_logic"
    CONFIGURATION = "configuration"
    SECURITY = "security"
    RESOURCE = "resource"
    EXTERNAL_SERVICE = "external_service"
    UNKNOWN = "unknown"


class RecoveryStrategy(Enum):
    """Error recovery strategies"""
    RETRY = "retry"
    FALLBACK = "fallback"
    FAIL_FAST = "fail_fast"
    IGNORE = "ignore"
    MANUAL_INTERVENTION = "manual_intervention"


@dataclass
class ErrorContext:
    """Context information for error handling"""
    operation: str
    entity_id: Optional[EntityId] = None
    entity_type: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorInfo:
    """Comprehensive error information"""
    error_id: str
    error_code: str
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    context: ErrorContext
    original_exception: Optional[Exception] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    stack_trace: Optional[str] = None
    recovery_strategy: RecoveryStrategy = RecoveryStrategy.FAIL_FAST
    is_retryable: bool = False
    retry_count: int = 0
    max_retries: int = 3


class DomainError(ModelError):
    """Base class for domain-specific errors"""
    
    def __init__(self, message: str, error_info: ErrorInfo):
        super().__init__(message)
        self.error_info = error_info


class RepositoryValidationError(DomainError):
    """Validation errors in repository operations"""
    
    def __init__(self, message: str, field: str, value: Any, context: ErrorContext):
        error_info = ErrorInfo(
            error_id=f"VAL_{datetime.now().timestamp()}",
            error_code="VALIDATION_ERROR",
            message=message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            recovery_strategy=RecoveryStrategy.FAIL_FAST,
            is_retryable=False
        )
        error_info.additional_data = {"field": field, "value": str(value)}
        super().__init__(message, error_info)
        self.field = field
        self.value = value


class RepositoryDatabaseError(DomainError):
    """Database-related errors in repository operations"""
    
    def __init__(self, message: str, original_exception: Exception, context: ErrorContext):
        error_info = ErrorInfo(
            error_id=f"DB_{datetime.now().timestamp()}",
            error_code="DATABASE_ERROR",
            message=message,
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            context=context,
            original_exception=original_exception,
            stack_trace=traceback.format_exc(),
            recovery_strategy=RecoveryStrategy.RETRY,
            is_retryable=True,
            max_retries=3
        )
        super().__init__(message, error_info)


class RepositoryConnectionError(DomainError):
    """Database connection errors"""
    
    def __init__(self, message: str, original_exception: Exception, context: ErrorContext):
        error_info = ErrorInfo(
            error_id=f"CONN_{datetime.now().timestamp()}",
            error_code="CONNECTION_ERROR",
            message=message,
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.CRITICAL,
            context=context,
            original_exception=original_exception,
            stack_trace=traceback.format_exc(),
            recovery_strategy=RecoveryStrategy.RETRY,
            is_retryable=True,
            max_retries=5
        )
        super().__init__(message, error_info)


class RepositoryBusinessLogicError(DomainError):
    """Business logic constraint violations"""
    
    def __init__(self, message: str, constraint: str, context: ErrorContext):
        error_info = ErrorInfo(
            error_id=f"BL_{datetime.now().timestamp()}",
            error_code="BUSINESS_LOGIC_ERROR",
            message=message,
            category=ErrorCategory.BUSINESS_LOGIC,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            recovery_strategy=RecoveryStrategy.FAIL_FAST,
            is_retryable=False
        )
        error_info.additional_data = {"constraint": constraint}
        super().__init__(message, error_info)
        self.constraint = constraint


class RepositoryConfigurationError(DomainError):
    """Configuration-related errors"""
    
    def __init__(self, message: str, config_key: str, context: ErrorContext):
        error_info = ErrorInfo(
            error_id=f"CFG_{datetime.now().timestamp()}",
            error_code="CONFIGURATION_ERROR",
            message=message,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            context=context,
            recovery_strategy=RecoveryStrategy.MANUAL_INTERVENTION,
            is_retryable=False
        )
        error_info.additional_data = {"config_key": config_key}
        super().__init__(message, error_info)
        self.config_key = config_key


class RepositoryResourceError(DomainError):
    """Resource-related errors (disk space, memory, etc.)"""
    
    def __init__(self, message: str, resource_type: str, context: ErrorContext):
        error_info = ErrorInfo(
            error_id=f"RES_{datetime.now().timestamp()}",
            error_code="RESOURCE_ERROR",
            message=message,
            category=ErrorCategory.RESOURCE,
            severity=ErrorSeverity.HIGH,
            context=context,
            recovery_strategy=RecoveryStrategy.FALLBACK,
            is_retryable=True,
            max_retries=2
        )
        error_info.additional_data = {"resource_type": resource_type}
        super().__init__(message, error_info)
        self.resource_type = resource_type


class IErrorHandler(ABC):
    """Interface for error handling strategies"""
    
    @abstractmethod
    def can_handle(self, error: Exception, context: ErrorContext) -> bool:
        """Check if this handler can handle the error"""
        pass
    
    @abstractmethod
    def handle_error(self, error: Exception, context: ErrorContext) -> ErrorInfo:
        """Handle the error and return error information"""
        pass


class ValidationErrorHandler(IErrorHandler):
    """Handler for validation errors"""
    
    def can_handle(self, error: Exception, context: ErrorContext) -> bool:
        return isinstance(error, (ValueError, TypeError)) or "validation" in str(error).lower()
    
    def handle_error(self, error: Exception, context: ErrorContext) -> ErrorInfo:
        message = f"Validation error in {context.operation}: {str(error)}"
        
        return ErrorInfo(
            error_id=f"VAL_{datetime.now().timestamp()}",
            error_code="VALIDATION_ERROR",
            message=message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            original_exception=error,
            stack_trace=traceback.format_exc(),
            recovery_strategy=RecoveryStrategy.FAIL_FAST,
            is_retryable=False
        )


class DatabaseErrorHandler(IErrorHandler):
    """Handler for database errors"""
    
    def can_handle(self, error: Exception, context: ErrorContext) -> bool:
        import sqlite3
        return isinstance(error, sqlite3.Error) or "database" in str(error).lower()
    
    def handle_error(self, error: Exception, context: ErrorContext) -> ErrorInfo:
        import sqlite3
        
        message = f"Database error in {context.operation}: {str(error)}"
        severity = ErrorSeverity.HIGH
        recovery_strategy = RecoveryStrategy.RETRY
        is_retryable = True
        max_retries = 3
        
        # Classify specific database errors
        if isinstance(error, sqlite3.IntegrityError):
            severity = ErrorSeverity.MEDIUM
            recovery_strategy = RecoveryStrategy.FAIL_FAST
            is_retryable = False
        elif isinstance(error, sqlite3.OperationalError):
            if "database is locked" in str(error).lower():
                severity = ErrorSeverity.HIGH
                recovery_strategy = RecoveryStrategy.RETRY
                max_retries = 5
            elif "no such table" in str(error).lower():
                severity = ErrorSeverity.CRITICAL
                recovery_strategy = RecoveryStrategy.MANUAL_INTERVENTION
                is_retryable = False
        
        return ErrorInfo(
            error_id=f"DB_{datetime.now().timestamp()}",
            error_code="DATABASE_ERROR",
            message=message,
            category=ErrorCategory.DATABASE,
            severity=severity,
            context=context,
            original_exception=error,
            stack_trace=traceback.format_exc(),
            recovery_strategy=recovery_strategy,
            is_retryable=is_retryable,
            max_retries=max_retries
        )


class NetworkErrorHandler(IErrorHandler):
    """Handler for network-related errors"""
    
    def can_handle(self, error: Exception, context: ErrorContext) -> bool:
        network_indicators = ["connection", "timeout", "network", "http", "ssl", "tls"]
        error_str = str(error).lower()
        return any(indicator in error_str for indicator in network_indicators)
    
    def handle_error(self, error: Exception, context: ErrorContext) -> ErrorInfo:
        message = f"Network error in {context.operation}: {str(error)}"
        
        return ErrorInfo(
            error_id=f"NET_{datetime.now().timestamp()}",
            error_code="NETWORK_ERROR",
            message=message,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.HIGH,
            context=context,
            original_exception=error,
            stack_trace=traceback.format_exc(),
            recovery_strategy=RecoveryStrategy.RETRY,
            is_retryable=True,
            max_retries=3
        )


class GenericErrorHandler(IErrorHandler):
    """Fallback handler for unclassified errors"""
    
    def can_handle(self, error: Exception, context: ErrorContext) -> bool:
        return True  # Handles any error as fallback
    
    def handle_error(self, error: Exception, context: ErrorContext) -> ErrorInfo:
        message = f"Unexpected error in {context.operation}: {str(error)}"
        
        return ErrorInfo(
            error_id=f"GEN_{datetime.now().timestamp()}",
            error_code="GENERIC_ERROR",
            message=message,
            category=ErrorCategory.UNKNOWN,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            original_exception=error,
            stack_trace=traceback.format_exc(),
            recovery_strategy=RecoveryStrategy.FAIL_FAST,
            is_retryable=False
        )


class ErrorRecoveryManager:
    """Manages error recovery strategies and retry logic"""
    
    def __init__(self):
        self._logger = logging.getLogger("ErrorRecovery")
        self._retry_counts: Dict[str, int] = {}
    
    def should_retry(self, error_info: ErrorInfo) -> bool:
        """Determine if an operation should be retried"""
        if not error_info.is_retryable:
            return False
        
        key = f"{error_info.context.operation}_{error_info.error_code}"
        current_count = self._retry_counts.get(key, 0)
        
        return current_count < error_info.max_retries
    
    def increment_retry_count(self, error_info: ErrorInfo) -> None:
        """Increment retry count for an operation"""
        key = f"{error_info.context.operation}_{error_info.error_code}"
        self._retry_counts[key] = self._retry_counts.get(key, 0) + 1
    
    def reset_retry_count(self, operation: str, error_code: str) -> None:
        """Reset retry count for an operation"""
        key = f"{operation}_{error_code}"
        self._retry_counts.pop(key, None)
    
    def execute_with_retry(self, operation: Callable, error_context: ErrorContext, 
                          max_retries: int = 3) -> Any:
        """Execute operation with automatic retry on retryable errors"""
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                result = operation()
                # Reset retry count on success
                if last_error:
                    self.reset_retry_count(error_context.operation, "RETRY_OPERATION")
                return result
                
            except Exception as e:
                last_error = e
                self._logger.warning(f"Operation {error_context.operation} failed on attempt {attempt + 1}: {e}")
                
                if attempt < max_retries:
                    # Wait before retry (exponential backoff)
                    import time
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
                else:
                    # Max retries exceeded
                    break
        
        # All retries failed
        raise RepositoryDatabaseError(
            f"Operation {error_context.operation} failed after {max_retries + 1} attempts",
            last_error,
            error_context
        )


class ErrorManager:
    """Central error management system for repositories"""
    
    def __init__(self):
        self._logger = logging.getLogger("ErrorManager")
        self._handlers: List[IErrorHandler] = []
        self._recovery_manager = ErrorRecoveryManager()
        self._error_statistics: Dict[str, int] = {}
        
        # Register default handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self) -> None:
        """Register default error handlers"""
        self._handlers = [
            ValidationErrorHandler(),
            DatabaseErrorHandler(),
            NetworkErrorHandler(),
            GenericErrorHandler()  # Must be last (fallback)
        ]
    
    def add_handler(self, handler: IErrorHandler) -> None:
        """Add a custom error handler"""
        # Insert before the generic handler
        self._handlers.insert(-1, handler)
    
    def handle_error(self, error: Exception, context: ErrorContext) -> ErrorInfo:
        """Handle an error and return detailed error information"""
        # Find appropriate handler
        handler = None
        for h in self._handlers:
            if h.can_handle(error, context):
                handler = h
                break
        
        if not handler:
            handler = self._handlers[-1]  # Use generic handler as fallback
        
        # Handle the error
        error_info = handler.handle_error(error, context)
        
        # Log the error
        self._log_error(error_info)
        
        # Update statistics
        self._update_statistics(error_info)
        
        return error_info
    
    def _log_error(self, error_info: ErrorInfo) -> None:
        """Log error with appropriate level based on severity"""
        log_message = (
            f"Error {error_info.error_id}: {error_info.message} "
            f"(Category: {error_info.category.value}, Severity: {error_info.severity.value})"
        )
        
        if error_info.severity == ErrorSeverity.CRITICAL:
            self._logger.critical(log_message, exc_info=error_info.original_exception)
        elif error_info.severity == ErrorSeverity.HIGH:
            self._logger.error(log_message, exc_info=error_info.original_exception)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            self._logger.warning(log_message)
        else:
            self._logger.info(log_message)
    
    def _update_statistics(self, error_info: ErrorInfo) -> None:
        """Update error statistics"""
        category_key = f"category_{error_info.category.value}"
        severity_key = f"severity_{error_info.severity.value}"
        code_key = f"code_{error_info.error_code}"
        
        self._error_statistics[category_key] = self._error_statistics.get(category_key, 0) + 1
        self._error_statistics[severity_key] = self._error_statistics.get(severity_key, 0) + 1
        self._error_statistics[code_key] = self._error_statistics.get(code_key, 0) + 1
    
    def get_error_statistics(self) -> Dict[str, int]:
        """Get error statistics"""
        return self._error_statistics.copy()
    
    def clear_statistics(self) -> None:
        """Clear error statistics"""
        self._error_statistics.clear()
    
    def should_retry(self, error_info: ErrorInfo) -> bool:
        """Check if operation should be retried"""
        return self._recovery_manager.should_retry(error_info)
    
    def execute_with_retry(self, operation: Callable, context: ErrorContext, 
                          max_retries: int = 3) -> Any:
        """Execute operation with automatic retry"""
        return self._recovery_manager.execute_with_retry(operation, context, max_retries)


# Global error manager instance
_error_manager: Optional[ErrorManager] = None


def get_error_manager() -> ErrorManager:
    """Get the global error manager instance"""
    global _error_manager
    if _error_manager is None:
        _error_manager = ErrorManager()
    return _error_manager


# Decorator for automatic error handling
def handle_repository_errors(operation_name: str = None):
    """
    Decorator for automatic error handling in repository methods
    
    Args:
        operation_name: Name of the operation for error context
    """
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            # Create error context
            context = ErrorContext(
                operation=operation_name or func.__name__,
                entity_type=getattr(self, '_entity_class', {}).get('__name__', 'Unknown') if hasattr(self, '_entity_class') else 'Unknown'
            )
            
            # Add entity ID if first argument looks like an ID
            if args and isinstance(args[0], (int, str)):
                context.entity_id = args[0]
            
            try:
                return func(self, *args, **kwargs)
                
            except DomainError:
                # Re-raise domain errors (already handled)
                raise
                
            except Exception as e:
                # Handle and translate generic exceptions
                error_manager = get_error_manager()
                error_info = error_manager.handle_error(e, context)
                
                # Raise appropriate domain exception
                if error_info.category == ErrorCategory.VALIDATION:
                    raise RepositoryValidationError(error_info.message, "unknown", None, context)
                elif error_info.category == ErrorCategory.DATABASE:
                    raise RepositoryDatabaseError(error_info.message, e, context)
                elif error_info.category == ErrorCategory.NETWORK:
                    raise RepositoryConnectionError(error_info.message, e, context)
                else:
                    raise RepositoryDatabaseError(error_info.message, e, context)
        
        return wrapper
    return decorator


# Context manager for error handling
class ErrorHandlingContext:
    """Context manager for error handling in repository operations"""
    
    def __init__(self, operation: str, entity_id: Optional[EntityId] = None, 
                 entity_type: Optional[str] = None):
        self.context = ErrorContext(
            operation=operation,
            entity_id=entity_id,
            entity_type=entity_type
        )
        self.error_manager = get_error_manager()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type and not issubclass(exc_type, DomainError):
            # Handle and translate generic exceptions
            error_info = self.error_manager.handle_error(exc_val, self.context)
            
            # Suppress original exception and raise domain exception
            if error_info.category == ErrorCategory.DATABASE:
                raise RepositoryDatabaseError(error_info.message, exc_val, self.context) from exc_val
            elif error_info.category == ErrorCategory.VALIDATION:
                raise RepositoryValidationError(error_info.message, "unknown", None, self.context) from exc_val
            else:
                raise RepositoryDatabaseError(error_info.message, exc_val, self.context) from exc_val
        
        return False  # Don't suppress domain errors 