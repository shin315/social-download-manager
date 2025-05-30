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
    """Enhanced error categories for comprehensive application error classification"""
    # Core system errors
    VALIDATION = "validation"
    DATABASE = "database"
    NETWORK = "network"
    BUSINESS_LOGIC = "business_logic"
    CONFIGURATION = "configuration"
    SECURITY = "security"
    RESOURCE = "resource"
    EXTERNAL_SERVICE = "external_service"
    
    # Application-specific categories
    UI = "ui"                           # User interface and component errors
    PLATFORM = "platform"              # TikTok, YouTube API errors
    DOWNLOAD = "download"               # File download and management errors
    REPOSITORY = "repository"           # Data layer and repository errors
    SERVICE = "service"                 # Business service layer errors
    AUTHENTICATION = "authentication"   # Auth and session errors
    PERMISSION = "permission"           # Access control errors
    FILE_SYSTEM = "file_system"        # File I/O operations
    PARSING = "parsing"                 # Data parsing and format errors
    INTEGRATION = "integration"        # Inter-component communication errors
    
    # Special categories
    UNKNOWN = "unknown"
    FATAL = "fatal"                     # Unrecoverable system errors


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
    """Comprehensive error information with enhanced categorization"""
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
    
    # Enhanced categorization fields
    error_type: Optional[str] = None  # Specific error type from the type enums
    component: Optional[str] = None   # Component where error occurred
    user_message: Optional[str] = None  # User-friendly error message
    technical_details: Optional[Dict[str, Any]] = field(default_factory=dict)


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


class EnhancedErrorHandler(IErrorHandler):
    """Enhanced error handler using the new classification system"""
    
    def can_handle(self, error: Exception, context: ErrorContext) -> bool:
        return True  # Can handle any error using classification
    
    def handle_error(self, error: Exception, context: ErrorContext) -> ErrorInfo:
        """Handle error using enhanced classification system"""
        # Classify the error automatically
        category = ErrorClassifier.classify_error(error, context)
        error_type = ErrorClassifier.get_specific_error_type(error, category)
        severity = ErrorClassifier.determine_severity(error, category)
        recovery_strategy = ErrorClassifier.determine_recovery_strategy(error, category)
        
        # Generate error code
        error_code = ErrorCodeGenerator.generate_code(category, error_type)
        
        # Generate error ID
        error_id = f"{category.value.upper()}_{datetime.now().timestamp()}"
        
        # Get user-friendly message
        user_message = get_user_friendly_message(category, error_type)
        
        # Determine if retryable
        is_retryable = recovery_strategy in [RecoveryStrategy.RETRY, RecoveryStrategy.FALLBACK]
        max_retries = 3 if is_retryable else 0
        
        # Extract component from context if available
        component = context.additional_data.get('component', None)
        
        return ErrorInfo(
            error_id=error_id,
            error_code=error_code,
            message=str(error),
            category=category,
            severity=severity,
            context=context,
            original_exception=error,
            stack_trace=traceback.format_exc(),
            recovery_strategy=recovery_strategy,
            is_retryable=is_retryable,
            max_retries=max_retries,
            error_type=error_type,
            component=component,
            user_message=user_message,
            technical_details={
                'error_class': type(error).__name__,
                'error_module': getattr(type(error), '__module__', 'unknown'),
                'classification_reason': f"Classified as {category.value} based on context and error content"
            }
        )


class ErrorManager:
    """Enhanced central error management system"""
    
    def __init__(self, use_enhanced_classification: bool = True):
        self._logger = logging.getLogger("ErrorManager")
        self._handlers: List[IErrorHandler] = []
        self._recovery_manager = ErrorRecoveryManager()
        self._error_statistics: Dict[str, int] = {}
        self._use_enhanced = use_enhanced_classification
        
        # Register handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self) -> None:
        """Register default error handlers"""
        if self._use_enhanced:
            # Use enhanced handler first
            self._handlers = [
                EnhancedErrorHandler(),
                ValidationErrorHandler(),
                DatabaseErrorHandler(),
                NetworkErrorHandler(),
                GenericErrorHandler()  # Fallback
            ]
        else:
            # Use legacy handlers
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
            f"Error {error_info.error_id} [{error_info.error_code}]: {error_info.message} "
            f"(Category: {error_info.category.value}, Severity: {error_info.severity.value}"
        )
        
        if error_info.component:
            log_message += f", Component: {error_info.component}"
        
        if error_info.error_type:
            log_message += f", Type: {error_info.error_type}"
        
        log_message += ")"
        
        # Add context information
        context_info = []
        if error_info.context.operation:
            context_info.append(f"Operation: {error_info.context.operation}")
        if error_info.context.entity_type:
            context_info.append(f"Entity: {error_info.context.entity_type}")
        if error_info.context.user_id:
            context_info.append(f"User: {error_info.context.user_id}")
        
        if context_info:
            log_message += f" | Context: {', '.join(context_info)}"
        
        # Log with appropriate level
        if error_info.severity == ErrorSeverity.CRITICAL:
            self._logger.critical(log_message, exc_info=error_info.original_exception)
        elif error_info.severity == ErrorSeverity.HIGH:
            self._logger.error(log_message, exc_info=error_info.original_exception)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            self._logger.warning(log_message)
        else:
            self._logger.info(log_message)
    
    def _update_statistics(self, error_info: ErrorInfo) -> None:
        """Update enhanced error statistics"""
        # Category statistics
        category_key = f"category_{error_info.category.value}"
        self._error_statistics[category_key] = self._error_statistics.get(category_key, 0) + 1
        
        # Severity statistics
        severity_key = f"severity_{error_info.severity.value}"
        self._error_statistics[severity_key] = self._error_statistics.get(severity_key, 0) + 1
        
        # Error code statistics
        code_key = f"code_{error_info.error_code}"
        self._error_statistics[code_key] = self._error_statistics.get(code_key, 0) + 1
        
        # Component statistics
        if error_info.component:
            component_key = f"component_{error_info.component}"
            self._error_statistics[component_key] = self._error_statistics.get(component_key, 0) + 1
        
        # Error type statistics
        if error_info.error_type:
            type_key = f"type_{error_info.error_type}"
            self._error_statistics[type_key] = self._error_statistics.get(type_key, 0) + 1
        
        # Recovery strategy statistics
        strategy_key = f"recovery_{error_info.recovery_strategy.value}"
        self._error_statistics[strategy_key] = self._error_statistics.get(strategy_key, 0) + 1
    
    def get_error_statistics(self) -> Dict[str, int]:
        """Get comprehensive error statistics"""
        return self._error_statistics.copy()
    
    def get_error_statistics_by_category(self) -> Dict[str, int]:
        """Get error statistics grouped by category"""
        return {k: v for k, v in self._error_statistics.items() if k.startswith('category_')}
    
    def get_error_statistics_by_component(self) -> Dict[str, int]:
        """Get error statistics grouped by component"""
        return {k: v for k, v in self._error_statistics.items() if k.startswith('component_')}
    
    def clear_statistics(self) -> None:
        """Clear error statistics"""
        self._error_statistics.clear()
    
    def should_retry(self, error_info: ErrorInfo) -> bool:
        """Check if operation should be retried"""
        return self._recovery_manager.should_retry(error_info)
    
    def execute_with_recovery(self, operation: Callable, context: ErrorContext) -> Any:
        """Execute operation with automatic error handling and recovery"""
        try:
            return operation()
        except Exception as e:
            error_info = self.handle_error(e, context)
            
            if error_info.recovery_strategy == RecoveryStrategy.RETRY and error_info.is_retryable:
                return self._recovery_manager.execute_with_retry(operation, context, error_info.max_retries)
            elif error_info.recovery_strategy == RecoveryStrategy.FAIL_FAST:
                raise e
            elif error_info.recovery_strategy == RecoveryStrategy.IGNORE:
                self._logger.info(f"Ignoring error as per recovery strategy: {error_info.message}")
                return None
            else:
                # Manual intervention or fallback required
                raise e


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


class UIErrorType(Enum):
    """Specific UI error types"""
    COMPONENT_INITIALIZATION = "component_initialization"
    EVENT_HANDLING = "event_handling"
    DATA_BINDING = "data_binding"
    USER_INPUT = "user_input"
    RENDERING = "rendering"
    STATE_MANAGEMENT = "state_management"
    NAVIGATION = "navigation"


class PlatformErrorType(Enum):
    """Platform-specific error types"""
    API_RATE_LIMIT = "api_rate_limit"
    API_AUTHENTICATION = "api_authentication"
    API_UNAVAILABLE = "api_unavailable"
    CONTENT_NOT_FOUND = "content_not_found"
    CONTENT_PRIVATE = "content_private"
    CONTENT_DELETED = "content_deleted"
    UNSUPPORTED_FORMAT = "unsupported_format"
    EXTRACTION_FAILED = "extraction_failed"


class DownloadErrorType(Enum):
    """Download-specific error types"""
    INSUFFICIENT_SPACE = "insufficient_space"
    PERMISSION_DENIED = "permission_denied"
    NETWORK_TIMEOUT = "network_timeout"
    CORRUPTED_FILE = "corrupted_file"
    INVALID_URL = "invalid_url"
    DOWNLOAD_INTERRUPTED = "download_interrupted"
    QUEUE_FULL = "queue_full"
    DUPLICATE_DOWNLOAD = "duplicate_download"


class RepositoryErrorType(Enum):
    """Repository layer error types"""
    CONNECTION_FAILED = "connection_failed"
    TRANSACTION_FAILED = "transaction_failed"
    CONSTRAINT_VIOLATION = "constraint_violation"
    DATA_CORRUPTION = "data_corruption"
    MIGRATION_FAILED = "migration_failed"
    QUERY_TIMEOUT = "query_timeout"
    DEADLOCK = "deadlock"


class ServiceErrorType(Enum):
    """Service layer error types"""
    INVALID_OPERATION = "invalid_operation"
    DEPENDENCY_UNAVAILABLE = "dependency_unavailable"
    OPERATION_TIMEOUT = "operation_timeout"
    BUSINESS_RULE_VIOLATION = "business_rule_violation"
    CONCURRENT_MODIFICATION = "concurrent_modification"


class ErrorClassifier:
    """Utility class for automatically classifying errors"""
    
    @staticmethod
    def classify_error(error: Exception, context: ErrorContext) -> ErrorCategory:
        """
        Automatically classify an error based on its type and context
        
        Args:
            error: The exception that occurred
            context: Context where the error occurred
            
        Returns:
            Appropriate ErrorCategory
        """
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        operation = context.operation.lower()
        
        # UI errors
        if any(keyword in operation for keyword in ['ui', 'component', 'widget', 'render']):
            return ErrorCategory.UI
        
        # Platform errors
        if any(keyword in operation for keyword in ['platform', 'tiktok', 'youtube', 'api']):
            return ErrorCategory.PLATFORM
        
        # Repository errors - Check before download since repository operations can contain "save"
        if any(keyword in operation for keyword in ['repository', 'repo', 'data']):
            return ErrorCategory.REPOSITORY
        
        # Download errors  
        if any(keyword in operation for keyword in ['download', 'file', 'save']):
            return ErrorCategory.DOWNLOAD
        
        # Database errors
        if any(keyword in error_str for keyword in ['database', 'sql', 'connection', 'transaction']):
            return ErrorCategory.DATABASE
        
        # Network errors
        if any(keyword in error_str for keyword in ['network', 'timeout', 'connection', 'http']):
            return ErrorCategory.NETWORK
        
        # Validation errors
        if any(keyword in error_type for keyword in ['value', 'type', 'assertion']):
            return ErrorCategory.VALIDATION
        
        # File system errors
        if any(keyword in error_str for keyword in ['permission', 'file not found', 'disk']):
            return ErrorCategory.FILE_SYSTEM
        
        # Authentication errors
        if any(keyword in error_str for keyword in ['auth', 'login', 'token', 'unauthorized']):
            return ErrorCategory.AUTHENTICATION
        
        # Configuration errors
        if any(keyword in operation for keyword in ['config', 'setting', 'init']):
            return ErrorCategory.CONFIGURATION
        
        return ErrorCategory.UNKNOWN
    
    @staticmethod
    def get_specific_error_type(error: Exception, category: ErrorCategory) -> Optional[str]:
        """
        Get specific error type based on category
        
        Args:
            error: The exception that occurred
            category: The error category
            
        Returns:
            Specific error type string or None
        """
        error_str = str(error).lower()
        
        if category == ErrorCategory.UI:
            if 'component' in error_str:
                return UIErrorType.COMPONENT_INITIALIZATION.value
            elif 'event' in error_str:
                return UIErrorType.EVENT_HANDLING.value
            elif 'render' in error_str:
                return UIErrorType.RENDERING.value
            elif 'state' in error_str:
                return UIErrorType.STATE_MANAGEMENT.value
                
        elif category == ErrorCategory.PLATFORM:
            if 'rate limit' in error_str:
                return PlatformErrorType.API_RATE_LIMIT.value
            elif 'not found' in error_str:
                return PlatformErrorType.CONTENT_NOT_FOUND.value
            elif 'private' in error_str:
                return PlatformErrorType.CONTENT_PRIVATE.value
            elif 'auth' in error_str:
                return PlatformErrorType.API_AUTHENTICATION.value
                
        elif category == ErrorCategory.DOWNLOAD:
            if 'space' in error_str:
                return DownloadErrorType.INSUFFICIENT_SPACE.value
            elif 'permission' in error_str:
                return DownloadErrorType.PERMISSION_DENIED.value
            elif 'timeout' in error_str:
                return DownloadErrorType.NETWORK_TIMEOUT.value
            elif 'corrupt' in error_str:
                return DownloadErrorType.CORRUPTED_FILE.value
                
        elif category == ErrorCategory.REPOSITORY:
            if 'connection' in error_str:
                return RepositoryErrorType.CONNECTION_FAILED.value
            elif 'deadlock' in error_str:
                return RepositoryErrorType.DEADLOCK.value
            elif 'constraint' in error_str:
                return RepositoryErrorType.CONSTRAINT_VIOLATION.value
                
        return None
    
    @staticmethod
    def determine_severity(error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """
        Determine error severity based on error type and category
        
        Args:
            error: The exception that occurred
            category: The error category
            
        Returns:
            Appropriate ErrorSeverity
        """
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # Critical errors that require immediate attention
        if category == ErrorCategory.FATAL:
            return ErrorSeverity.CRITICAL
        if any(keyword in error_str for keyword in ['corrupt', 'disk full', 'deadlock']):
            return ErrorSeverity.CRITICAL
        
        # High severity errors
        if category in [ErrorCategory.DATABASE, ErrorCategory.SECURITY, ErrorCategory.AUTHENTICATION]:
            return ErrorSeverity.HIGH
        if any(keyword in error_str for keyword in ['permission denied', 'unauthorized']):
            return ErrorSeverity.HIGH
        
        # Medium severity errors
        if category in [ErrorCategory.NETWORK, ErrorCategory.PLATFORM, ErrorCategory.DOWNLOAD]:
            return ErrorSeverity.MEDIUM
        if 'timeout' in error_str:
            return ErrorSeverity.MEDIUM
        
        # Low severity errors
        if category in [ErrorCategory.UI, ErrorCategory.VALIDATION]:
            return ErrorSeverity.LOW
        
        # Default to medium for unknown categories
        return ErrorSeverity.MEDIUM
    
    @staticmethod
    def determine_recovery_strategy(error: Exception, category: ErrorCategory) -> RecoveryStrategy:
        """
        Determine recovery strategy based on error type and category
        
        Args:
            error: The exception that occurred
            category: The error category
            
        Returns:
            Appropriate RecoveryStrategy
        """
        error_str = str(error).lower()
        
        # Retryable errors
        if any(keyword in error_str for keyword in ['timeout', 'connection', 'rate limit']):
            return RecoveryStrategy.RETRY
        if category in [ErrorCategory.NETWORK, ErrorCategory.PLATFORM]:
            return RecoveryStrategy.RETRY
        
        # Fallback strategies
        if category in [ErrorCategory.DOWNLOAD, ErrorCategory.EXTERNAL_SERVICE]:
            return RecoveryStrategy.FALLBACK
        
        # Manual intervention required
        if any(keyword in error_str for keyword in ['corrupt', 'permission', 'disk full']):
            return RecoveryStrategy.MANUAL_INTERVENTION
        if category in [ErrorCategory.SECURITY, ErrorCategory.AUTHENTICATION]:
            return RecoveryStrategy.MANUAL_INTERVENTION
        
        # Ignore minor UI errors
        if category == ErrorCategory.UI and 'warning' in error_str:
            return RecoveryStrategy.IGNORE
        
        # Default to fail fast
        return RecoveryStrategy.FAIL_FAST


class ErrorCodeGenerator:
    """Utility for generating standardized error codes"""
    
    _category_prefixes = {
        ErrorCategory.UI: "UI",
        ErrorCategory.PLATFORM: "PLT",
        ErrorCategory.DOWNLOAD: "DWN", 
        ErrorCategory.REPOSITORY: "REP",
        ErrorCategory.SERVICE: "SVC",
        ErrorCategory.DATABASE: "DB",
        ErrorCategory.NETWORK: "NET",
        ErrorCategory.VALIDATION: "VAL",
        ErrorCategory.AUTHENTICATION: "AUTH",
        ErrorCategory.PERMISSION: "PERM",
        ErrorCategory.FILE_SYSTEM: "FS",
        ErrorCategory.CONFIGURATION: "CFG",
        ErrorCategory.UNKNOWN: "UNK",
        ErrorCategory.FATAL: "FATAL"
    }
    
    @classmethod
    def generate_code(cls, category: ErrorCategory, error_type: Optional[str] = None) -> str:
        """
        Generate a standardized error code
        
        Args:
            category: Error category
            error_type: Specific error type
            
        Returns:
            Standardized error code
        """
        prefix = cls._category_prefixes.get(category, "UNK")
        timestamp = int(datetime.now().timestamp() * 1000) % 10000  # Last 4 digits
        
        if error_type:
            # Convert error type to short code
            type_code = error_type.upper().replace("_", "")[:4]
            return f"{prefix}_{type_code}_{timestamp}"
        
        return f"{prefix}_{timestamp}"


# Error message templates for user-friendly messages
ERROR_MESSAGES = {
    ErrorCategory.UI: {
        UIErrorType.COMPONENT_INITIALIZATION: "A component failed to start properly. Please restart the application.",
        UIErrorType.USER_INPUT: "Invalid input provided. Please check your input and try again.",
        UIErrorType.RENDERING: "Display issue occurred. Please refresh the interface.",
        UIErrorType.STATE_MANAGEMENT: "Interface state error. Please restart the application.",
    },
    ErrorCategory.PLATFORM: {
        PlatformErrorType.API_RATE_LIMIT: "Rate limit exceeded. Please wait before trying again.",
        PlatformErrorType.CONTENT_NOT_FOUND: "Content not found or may have been removed.",
        PlatformErrorType.CONTENT_PRIVATE: "Content is private and cannot be accessed.",
        PlatformErrorType.API_AUTHENTICATION: "Authentication failed. Please check your credentials.",
    },
    ErrorCategory.DOWNLOAD: {
        DownloadErrorType.INSUFFICIENT_SPACE: "Not enough disk space. Please free up space and try again.",
        DownloadErrorType.PERMISSION_DENIED: "Permission denied. Please check file permissions.",
        DownloadErrorType.NETWORK_TIMEOUT: "Download timed out. Please check your internet connection.",
        DownloadErrorType.CORRUPTED_FILE: "Downloaded file is corrupted. Please try downloading again.",
    },
    ErrorCategory.REPOSITORY: {
        RepositoryErrorType.CONNECTION_FAILED: "Database connection failed. Please try again later.",
        RepositoryErrorType.TRANSACTION_FAILED: "Data operation failed. Please try again.",
        RepositoryErrorType.DATA_CORRUPTION: "Data integrity issue detected. Please contact support.",
    }
}


def get_user_friendly_message(category: ErrorCategory, error_type: Optional[str] = None) -> str:
    """
    Get user-friendly error message
    
    Args:
        category: Error category
        error_type: Specific error type
        
    Returns:
        User-friendly error message
    """
    if category in ERROR_MESSAGES and error_type:
        # Convert string back to enum if needed
        for type_enum in [UIErrorType, PlatformErrorType, DownloadErrorType, RepositoryErrorType]:
            try:
                error_enum = type_enum(error_type)
                return ERROR_MESSAGES[category].get(error_enum, "An unexpected error occurred.")
            except ValueError:
                continue
    
    # Default messages by category
    default_messages = {
        ErrorCategory.UI: "A user interface error occurred. Please try again.",
        ErrorCategory.PLATFORM: "Platform service error. Please try again later.",
        ErrorCategory.DOWNLOAD: "Download error occurred. Please check your connection and try again.",
        ErrorCategory.REPOSITORY: "Data operation failed. Please try again.",
        ErrorCategory.SERVICE: "Service error occurred. Please try again later.",
        ErrorCategory.NETWORK: "Network error. Please check your internet connection.",
        ErrorCategory.VALIDATION: "Invalid input provided. Please check and try again.",
        ErrorCategory.AUTHENTICATION: "Authentication failed. Please check your credentials.",
        ErrorCategory.DATABASE: "Database error occurred. Please try again later.",
        ErrorCategory.UNKNOWN: "An unexpected error occurred. Please try again.",
    }
    
    return default_messages.get(category, "An error occurred. Please try again.") 