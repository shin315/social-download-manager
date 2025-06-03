"""
Error Management System for Social Download Manager v2.0

This module provides comprehensive error handling, classification, logging,
and recovery mechanisms for the v2.0 architecture. It integrates with the
main entry orchestrator and adapter integration framework to provide unified
error management across all components.
"""

import sys
import os
import logging
import logging.handlers
import traceback
import threading
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Union, Type
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from contextlib import contextmanager

# PyQt6 imports for error dialogs
try:
    from PyQt6.QtWidgets import QApplication, QMessageBox, QDialog, QVBoxLayout, QLabel, QPushButton, QTextEdit
    from PyQt6.QtCore import QTimer, QThread, pyqtSignal
    from PyQt6.QtGui import QPixmap, QIcon
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False


class ErrorSeverity(Enum):
    """Error severity levels"""
    DEBUG = auto()          # Debug information, development only
    INFO = auto()           # Informational messages
    WARNING = auto()        # Warning conditions that don't affect functionality
    ERROR = auto()          # Error conditions that affect specific features
    CRITICAL = auto()       # Critical errors that affect core functionality
    FATAL = auto()          # Fatal errors that prevent application startup


class ErrorCategory(Enum):
    """Error categories for classification"""
    SYSTEM = "system"                   # System-level errors (OS, Python)
    DEPENDENCY = "dependency"           # Missing dependencies, imports
    CONFIGURATION = "configuration"    # Configuration issues
    INITIALIZATION = "initialization"  # Component initialization failures
    ADAPTER = "adapter"                # Adapter-related errors
    UI = "ui"                          # UI component errors
    NETWORK = "network"                # Network and API errors
    PLATFORM = "platform"             # Platform-specific errors
    DATABASE = "database"              # Database and data layer errors
    PERMISSION = "permission"          # File/system permission errors
    UNKNOWN = "unknown"                # Unclassified errors


class ErrorCode(Enum):
    """Standardized error codes"""
    # System errors (1000-1099)
    PYTHON_VERSION_TOO_OLD = 1001
    MISSING_SYSTEM_DEPENDENCY = 1002
    INSUFFICIENT_MEMORY = 1003
    PLATFORM_NOT_SUPPORTED = 1004
    
    # Import/Dependency errors (1100-1199)
    MISSING_REQUIRED_MODULE = 1101
    MODULE_VERSION_INCOMPATIBLE = 1102
    PYQT6_NOT_AVAILABLE = 1103
    CORE_MODULE_MISSING = 1104
    
    # Configuration errors (1200-1299)
    CONFIG_FILE_NOT_FOUND = 1201
    CONFIG_FILE_CORRUPT = 1202
    INVALID_CONFIG_VALUE = 1203
    CONFIG_PERMISSION_DENIED = 1204
    
    # Initialization errors (1300-1399)
    COMPONENT_INIT_FAILED = 1301
    DEPENDENCY_INIT_FAILED = 1302
    ORCHESTRATOR_INIT_FAILED = 1303
    ADAPTER_INIT_FAILED = 1304
    
    # Adapter errors (1400-1499)
    ADAPTER_NOT_FOUND = 1401
    ADAPTER_REGISTRATION_FAILED = 1402
    ADAPTER_ATTACH_FAILED = 1403
    ADAPTER_COMMUNICATION_FAILED = 1404
    
    # UI errors (1500-1599)
    QAPPLICATION_FAILED = 1501
    MAIN_WINDOW_FAILED = 1502
    UI_COMPONENT_FAILED = 1503
    UI_RESOURCE_MISSING = 1504
    
    # Network/Platform errors (1600-1699)
    NETWORK_CONNECTION_FAILED = 1601
    API_REQUEST_FAILED = 1602
    PLATFORM_API_ERROR = 1603
    AUTHENTICATION_FAILED = 1604
    
    # Database errors (1700-1799)
    DATABASE_CONNECTION_FAILED = 1701
    DATABASE_SCHEMA_ERROR = 1702
    DATABASE_PERMISSION_ERROR = 1703
    DATABASE_CORRUPTION = 1704


@dataclass
class ErrorContext:
    """Context information for an error"""
    timestamp: datetime = field(default_factory=datetime.now)
    thread_id: int = field(default_factory=lambda: threading.get_ident())
    thread_name: str = field(default_factory=lambda: threading.current_thread().name)
    process_id: int = field(default_factory=os.getpid)
    
    # Component context
    component_name: Optional[str] = None
    operation_name: Optional[str] = None
    adapter_id: Optional[str] = None
    
    # System context
    python_version: str = field(default_factory=lambda: sys.version)
    platform: str = field(default_factory=lambda: sys.platform)
    working_directory: str = field(default_factory=lambda: os.getcwd())
    
    # Additional context
    user_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorInfo:
    """Complete error information"""
    # Basic error information
    error_code: ErrorCode
    severity: ErrorSeverity
    category: ErrorCategory
    message: str
    
    # Detailed information
    exception: Optional[Exception] = None
    traceback_str: Optional[str] = None
    context: ErrorContext = field(default_factory=ErrorContext)
    
    # Recovery information
    recovery_suggestions: List[str] = field(default_factory=list)
    can_continue: bool = True
    requires_restart: bool = False
    
    # Internal tracking
    error_id: str = field(default_factory=lambda: f"ERR_{int(time.time() * 1000)}")
    reported_count: int = 0
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)


class ErrorHandler:
    """Base class for error handlers"""
    
    def can_handle(self, error_info: ErrorInfo) -> bool:
        """Check if this handler can handle the error"""
        return True
    
    def handle_error(self, error_info: ErrorInfo) -> bool:
        """Handle the error, return True if handled successfully"""
        return False
    
    def get_priority(self) -> int:
        """Get handler priority (higher values processed first)"""
        return 0


class LoggingErrorHandler(ErrorHandler):
    """Error handler that logs errors"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def handle_error(self, error_info: ErrorInfo) -> bool:
        """Log the error with appropriate level"""
        level_map = {
            ErrorSeverity.DEBUG: logging.DEBUG,
            ErrorSeverity.INFO: logging.INFO,
            ErrorSeverity.WARNING: logging.WARNING,
            ErrorSeverity.ERROR: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL,
            ErrorSeverity.FATAL: logging.CRITICAL
        }
        
        level = level_map.get(error_info.severity, logging.ERROR)
        
        # Create detailed log message
        log_msg = f"[{error_info.error_code.name}] {error_info.message}"
        if error_info.context.component_name:
            log_msg += f" (Component: {error_info.context.component_name})"
        if error_info.context.operation_name:
            log_msg += f" (Operation: {error_info.context.operation_name})"
        
        self.logger.log(level, log_msg)
        
        # Log traceback for exceptions
        if error_info.exception and error_info.traceback_str:
            self.logger.log(level, f"Traceback:\n{error_info.traceback_str}")
        
        return True
    
    def get_priority(self) -> int:
        return 100  # High priority for logging


class DialogErrorHandler(ErrorHandler):
    """Error handler that shows dialogs to user"""
    
    def __init__(self, show_debug: bool = False, auto_close_timeout: int = 0):
        self.show_debug = show_debug
        self.auto_close_timeout = auto_close_timeout
    
    def can_handle(self, error_info: ErrorInfo) -> bool:
        """Only handle errors that should be shown to user"""
        if not PYQT6_AVAILABLE:
            return False
        
        # Don't show debug messages unless specifically enabled
        if error_info.severity == ErrorSeverity.DEBUG and not self.show_debug:
            return False
        
        # Only show errors of WARNING level and above
        return error_info.severity.value >= ErrorSeverity.WARNING.value
    
    def handle_error(self, error_info: ErrorInfo) -> bool:
        """Show error dialog to user"""
        try:
            # Ensure QApplication exists
            app = QApplication.instance()
            if app is None:
                return False
            
            # Create message box
            msgbox = QMessageBox()
            
            # Set icon based on severity
            if error_info.severity == ErrorSeverity.FATAL:
                msgbox.setIcon(QMessageBox.Icon.Critical)
                title = "Fatal Error"
            elif error_info.severity == ErrorSeverity.CRITICAL:
                msgbox.setIcon(QMessageBox.Icon.Critical)
                title = "Critical Error"
            elif error_info.severity == ErrorSeverity.ERROR:
                msgbox.setIcon(QMessageBox.Icon.Critical)
                title = "Error"
            else:
                msgbox.setIcon(QMessageBox.Icon.Warning)
                title = "Warning"
            
            msgbox.setWindowTitle(title)
            msgbox.setText(error_info.message)
            
            # Add detailed information
            details = f"Error Code: {error_info.error_code.name}\n"
            details += f"Category: {error_info.category.value}\n"
            details += f"Time: {error_info.context.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
            
            if error_info.context.component_name:
                details += f"Component: {error_info.context.component_name}\n"
            
            if error_info.recovery_suggestions:
                details += "\nSuggested Actions:\n"
                for i, suggestion in enumerate(error_info.recovery_suggestions, 1):
                    details += f"{i}. {suggestion}\n"
            
            if error_info.traceback_str and self.show_debug:
                details += f"\nTechnical Details:\n{error_info.traceback_str}"
            
            msgbox.setDetailedText(details)
            msgbox.setStandardButtons(QMessageBox.StandardButton.Ok)
            
            # Auto-close timer if specified
            if self.auto_close_timeout > 0:
                QTimer.singleShot(self.auto_close_timeout * 1000, msgbox.accept)
            
            msgbox.exec()
            return True
            
        except Exception as e:
            # Fallback - log the error in handling
            print(f"Failed to show error dialog: {e}")
            return False
    
    def get_priority(self) -> int:
        return 80  # Lower priority than logging


class ErrorManager:
    """
    Central error management system
    
    Provides unified error handling, classification, logging, and recovery
    mechanisms for the v2.0 architecture.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._lock = threading.RLock()
        
        # Error handlers
        self._handlers: List[ErrorHandler] = []
        
        # Error tracking
        self._error_history: List[ErrorInfo] = []
        self._error_counts: Dict[ErrorCode, int] = {}
        self._suppressed_errors: Dict[ErrorCode, datetime] = {}
        
        # Configuration
        self.max_history_size = 1000
        self.error_suppression_duration = timedelta(minutes=5)
        self.max_same_error_count = 10
        
        # Statistics
        self.total_errors = 0
        self.errors_by_severity: Dict[ErrorSeverity, int] = {severity: 0 for severity in ErrorSeverity}
        self.errors_by_category: Dict[ErrorCategory, int] = {category: 0 for category in ErrorCategory}
        
        # Setup default handlers
        self._setup_default_handlers()
    
    def _setup_default_handlers(self) -> None:
        """Set up default error handlers"""
        # Add logging handler
        self.add_handler(LoggingErrorHandler(self.logger))
        
        # Add dialog handler for user-facing errors
        self.add_handler(DialogErrorHandler(show_debug=False, auto_close_timeout=15))
    
    def add_handler(self, handler: ErrorHandler) -> None:
        """Add an error handler"""
        with self._lock:
            self._handlers.append(handler)
            # Sort by priority (highest first)
            self._handlers.sort(key=lambda h: h.get_priority(), reverse=True)
    
    def remove_handler(self, handler: ErrorHandler) -> None:
        """Remove an error handler"""
        with self._lock:
            if handler in self._handlers:
                self._handlers.remove(handler)
    
    def report_error(
        self,
        error_code: ErrorCode,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        category: Optional[ErrorCategory] = None,
        exception: Optional[Exception] = None,
        context: Optional[ErrorContext] = None,
        recovery_suggestions: Optional[List[str]] = None,
        can_continue: bool = True,
        requires_restart: bool = False
    ) -> ErrorInfo:
        """Report an error to the management system"""
        
        with self._lock:
            # Auto-detect category if not provided
            if category is None:
                category = self._auto_detect_category(error_code, exception)
            
            # Create context if not provided
            if context is None:
                context = ErrorContext()
            
            # Get traceback if exception provided
            traceback_str = None
            if exception:
                traceback_str = traceback.format_exception(type(exception), exception, exception.__traceback__)
                traceback_str = ''.join(traceback_str)
            
            # Create error info
            error_info = ErrorInfo(
                error_code=error_code,
                severity=severity,
                category=category,
                message=message,
                exception=exception,
                traceback_str=traceback_str,
                context=context,
                recovery_suggestions=recovery_suggestions or [],
                can_continue=can_continue,
                requires_restart=requires_restart
            )
            
            # Check if this error should be suppressed
            if self._should_suppress_error(error_info):
                return error_info
            
            # Update statistics
            self._update_statistics(error_info)
            
            # Add to history
            self._add_to_history(error_info)
            
            # Process through handlers
            self._process_error(error_info)
            
            return error_info
    
    def _auto_detect_category(self, error_code: ErrorCode, exception: Optional[Exception]) -> ErrorCategory:
        """Auto-detect error category based on error code and exception"""
        
        # Map error codes to categories
        code_category_map = {
            # System errors
            ErrorCode.PYTHON_VERSION_TOO_OLD: ErrorCategory.SYSTEM,
            ErrorCode.MISSING_SYSTEM_DEPENDENCY: ErrorCategory.SYSTEM,
            ErrorCode.INSUFFICIENT_MEMORY: ErrorCategory.SYSTEM,
            ErrorCode.PLATFORM_NOT_SUPPORTED: ErrorCategory.SYSTEM,
            
            # Dependency errors
            ErrorCode.MISSING_REQUIRED_MODULE: ErrorCategory.DEPENDENCY,
            ErrorCode.MODULE_VERSION_INCOMPATIBLE: ErrorCategory.DEPENDENCY,
            ErrorCode.PYQT6_NOT_AVAILABLE: ErrorCategory.DEPENDENCY,
            ErrorCode.CORE_MODULE_MISSING: ErrorCategory.DEPENDENCY,
            
            # Configuration errors
            ErrorCode.CONFIG_FILE_NOT_FOUND: ErrorCategory.CONFIGURATION,
            ErrorCode.CONFIG_FILE_CORRUPT: ErrorCategory.CONFIGURATION,
            ErrorCode.INVALID_CONFIG_VALUE: ErrorCategory.CONFIGURATION,
            ErrorCode.CONFIG_PERMISSION_DENIED: ErrorCategory.CONFIGURATION,
            
            # Initialization errors
            ErrorCode.COMPONENT_INIT_FAILED: ErrorCategory.INITIALIZATION,
            ErrorCode.DEPENDENCY_INIT_FAILED: ErrorCategory.INITIALIZATION,
            ErrorCode.ORCHESTRATOR_INIT_FAILED: ErrorCategory.INITIALIZATION,
            ErrorCode.ADAPTER_INIT_FAILED: ErrorCategory.INITIALIZATION,
            
            # Adapter errors
            ErrorCode.ADAPTER_NOT_FOUND: ErrorCategory.ADAPTER,
            ErrorCode.ADAPTER_REGISTRATION_FAILED: ErrorCategory.ADAPTER,
            ErrorCode.ADAPTER_ATTACH_FAILED: ErrorCategory.ADAPTER,
            ErrorCode.ADAPTER_COMMUNICATION_FAILED: ErrorCategory.ADAPTER,
            
            # UI errors
            ErrorCode.QAPPLICATION_FAILED: ErrorCategory.UI,
            ErrorCode.MAIN_WINDOW_FAILED: ErrorCategory.UI,
            ErrorCode.UI_COMPONENT_FAILED: ErrorCategory.UI,
            ErrorCode.UI_RESOURCE_MISSING: ErrorCategory.UI,
            
            # Network/Platform errors
            ErrorCode.NETWORK_CONNECTION_FAILED: ErrorCategory.NETWORK,
            ErrorCode.API_REQUEST_FAILED: ErrorCategory.NETWORK,
            ErrorCode.PLATFORM_API_ERROR: ErrorCategory.PLATFORM,
            ErrorCode.AUTHENTICATION_FAILED: ErrorCategory.NETWORK,
            
            # Database errors
            ErrorCode.DATABASE_CONNECTION_FAILED: ErrorCategory.DATABASE,
            ErrorCode.DATABASE_SCHEMA_ERROR: ErrorCategory.DATABASE,
            ErrorCode.DATABASE_PERMISSION_ERROR: ErrorCategory.DATABASE,
            ErrorCode.DATABASE_CORRUPTION: ErrorCategory.DATABASE,
        }
        
        category = code_category_map.get(error_code)
        if category:
            return category
        
        # Auto-detect from exception type
        if exception:
            if isinstance(exception, ImportError):
                return ErrorCategory.DEPENDENCY
            elif isinstance(exception, PermissionError):
                return ErrorCategory.PERMISSION
            elif isinstance(exception, FileNotFoundError):
                return ErrorCategory.CONFIGURATION
            elif isinstance(exception, ConnectionError):
                return ErrorCategory.NETWORK
        
        return ErrorCategory.UNKNOWN
    
    def _should_suppress_error(self, error_info: ErrorInfo) -> bool:
        """Check if this error should be suppressed due to frequency"""
        
        # Never suppress fatal or critical errors
        if error_info.severity in [ErrorSeverity.FATAL, ErrorSeverity.CRITICAL]:
            return False
        
        # Check error count
        count = self._error_counts.get(error_info.error_code, 0)
        if count >= self.max_same_error_count:
            # Check if suppression period has expired
            suppressed_time = self._suppressed_errors.get(error_info.error_code)
            if suppressed_time:
                if datetime.now() - suppressed_time < self.error_suppression_duration:
                    return True
                else:
                    # Reset suppression
                    del self._suppressed_errors[error_info.error_code]
                    self._error_counts[error_info.error_code] = 0
            else:
                # Start suppression
                self._suppressed_errors[error_info.error_code] = datetime.now()
                return True
        
        return False
    
    def _update_statistics(self, error_info: ErrorInfo) -> None:
        """Update error statistics"""
        self.total_errors += 1
        self.errors_by_severity[error_info.severity] += 1
        self.errors_by_category[error_info.category] += 1
        self._error_counts[error_info.error_code] = self._error_counts.get(error_info.error_code, 0) + 1
        
        # Update error info
        error_info.reported_count = self._error_counts[error_info.error_code]
        error_info.last_seen = datetime.now()
    
    def _add_to_history(self, error_info: ErrorInfo) -> None:
        """Add error to history with size management"""
        self._error_history.append(error_info)
        
        # Trim history if too large
        if len(self._error_history) > self.max_history_size:
            self._error_history = self._error_history[-self.max_history_size:]
    
    def _process_error(self, error_info: ErrorInfo) -> None:
        """Process error through all handlers"""
        for handler in self._handlers:
            try:
                if handler.can_handle(error_info):
                    handled = handler.handle_error(error_info)
                    if handled:
                        break  # Stop after first successful handler
            except Exception as e:
                # Log handler errors to prevent infinite recursion
                self.logger.error(f"Error in error handler {type(handler).__name__}: {e}")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics"""
        with self._lock:
            return {
                "total_errors": self.total_errors,
                "errors_by_severity": {severity.name: count for severity, count in self.errors_by_severity.items()},
                "errors_by_category": {category.value: count for category, count in self.errors_by_category.items()},
                "recent_errors": len([e for e in self._error_history if (datetime.now() - e.last_seen).seconds < 3600]),
                "suppressed_errors": len(self._suppressed_errors),
                "history_size": len(self._error_history)
            }
    
    def get_recent_errors(self, limit: int = 50) -> List[ErrorInfo]:
        """Get recent errors"""
        with self._lock:
            return self._error_history[-limit:]
    
    def clear_history(self) -> None:
        """Clear error history"""
        with self._lock:
            self._error_history.clear()
            self._error_counts.clear()
            self._suppressed_errors.clear()
            self.total_errors = 0
            self.errors_by_severity = {severity: 0 for severity in ErrorSeverity}
            self.errors_by_category = {category: 0 for category in ErrorCategory}


# Global error manager instance
_error_manager: Optional[ErrorManager] = None
_error_manager_lock = threading.Lock()


def get_error_manager() -> ErrorManager:
    """Get the global error manager instance (singleton)"""
    global _error_manager
    
    with _error_manager_lock:
        if _error_manager is None:
            _error_manager = ErrorManager()
        
        return _error_manager


def report_error(
    error_code: ErrorCode,
    message: str,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    category: Optional[ErrorCategory] = None,
    exception: Optional[Exception] = None,
    component_name: Optional[str] = None,
    operation_name: Optional[str] = None,
    recovery_suggestions: Optional[List[str]] = None,
    can_continue: bool = True,
    requires_restart: bool = False
) -> ErrorInfo:
    """Convenience function to report an error"""
    
    # Create context with component/operation info
    context = ErrorContext()
    if component_name:
        context.component_name = component_name
    if operation_name:
        context.operation_name = operation_name
    
    error_manager = get_error_manager()
    return error_manager.report_error(
        error_code=error_code,
        message=message,
        severity=severity,
        category=category,
        exception=exception,
        context=context,
        recovery_suggestions=recovery_suggestions,
        can_continue=can_continue,
        requires_restart=requires_restart
    )


# Common error reporting functions for convenience

def report_system_error(message: str, exception: Optional[Exception] = None) -> ErrorInfo:
    """Report a system-level error"""
    return report_error(
        error_code=ErrorCode.MISSING_SYSTEM_DEPENDENCY,
        message=message,
        severity=ErrorSeverity.CRITICAL,
        category=ErrorCategory.SYSTEM,
        exception=exception,
        requires_restart=True
    )


def report_dependency_error(module_name: str, exception: Optional[Exception] = None) -> ErrorInfo:
    """Report a missing dependency error"""
    return report_error(
        error_code=ErrorCode.MISSING_REQUIRED_MODULE,
        message=f"Required module '{module_name}' is not available",
        severity=ErrorSeverity.CRITICAL,
        category=ErrorCategory.DEPENDENCY,
        exception=exception,
        recovery_suggestions=[
            f"Install the module: pip install {module_name}",
            "Check if virtual environment is activated",
            "Verify requirements.txt is up to date"
        ],
        requires_restart=True
    )


def report_initialization_error(component_name: str, exception: Optional[Exception] = None) -> ErrorInfo:
    """Report a component initialization error"""
    return report_error(
        error_code=ErrorCode.COMPONENT_INIT_FAILED,
        message=f"Failed to initialize component: {component_name}",
        severity=ErrorSeverity.ERROR,
        category=ErrorCategory.INITIALIZATION,
        exception=exception,
        component_name=component_name,
        recovery_suggestions=[
            "Check component dependencies",
            "Verify configuration is correct",
            "Try running in fallback mode"
        ],
        can_continue=True
    )


def report_adapter_error(adapter_id: str, operation: str, exception: Optional[Exception] = None) -> ErrorInfo:
    """Report an adapter-related error"""
    context = ErrorContext()
    context.adapter_id = adapter_id
    context.operation_name = operation
    
    return report_error(
        error_code=ErrorCode.ADAPTER_COMMUNICATION_FAILED,
        message=f"Adapter '{adapter_id}' failed during '{operation}'",
        severity=ErrorSeverity.WARNING,
        category=ErrorCategory.ADAPTER,
        exception=exception,
        component_name="AdapterSystem",
        recovery_suggestions=[
            "Check adapter configuration",
            "Verify component compatibility",
            "Try disabling the adapter temporarily"
        ],
        can_continue=True
    )


@contextmanager
def error_context(component_name: str, operation_name: str):
    """Context manager for automatic error reporting"""
    try:
        yield
    except Exception as e:
        report_error(
            error_code=ErrorCode.COMPONENT_INIT_FAILED,
            message=f"Error in {component_name} during {operation_name}: {e}",
            severity=ErrorSeverity.ERROR,
            exception=e,
            component_name=component_name,
            operation_name=operation_name
        )
        raise 