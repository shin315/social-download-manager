"""
Global Error Handler System

This module provides centralized error handling mechanisms to catch and process
unhandled errors across the entire application, ensuring consistent logging,
user feedback, and recovery procedures.
"""

import sys
import os
import threading
import traceback
import tkinter as tk
from typing import Optional, Dict, Any, List, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import contextmanager
import logging
import json
import gc

# Import error management components
try:
    from data.models.error_management import (
        ErrorInfo, ErrorCategory, ErrorSeverity, ErrorContext, RecoveryStrategy
    )
    from core.error_categorization import ErrorClassifier
    from core.logging_strategy import EnhancedErrorLogger, get_error_logger
    from core.user_feedback import get_feedback_manager, generate_user_friendly_message, UserRole
    from core.recovery_engine import execute_auto_recovery
except ImportError:
    # Fallback for testing
    pass


@dataclass
class ApplicationState:
    """Snapshot of application state at error time"""
    timestamp: datetime = field(default_factory=datetime.now)
    active_threads: List[str] = field(default_factory=list)
    memory_usage: float = 0.0
    open_windows: List[str] = field(default_factory=list)
    current_operation: Optional[str] = None
    user_context: Dict[str, Any] = field(default_factory=dict)
    component_states: Dict[str, Any] = field(default_factory=dict)
    
    def capture_current_state(self):
        """Capture current application state"""
        # Capture threading information
        self.active_threads = [t.name for t in threading.enumerate() if t.is_alive()]
        
        # Capture memory usage
        try:
            import psutil
            process = psutil.Process(os.getpid())
            self.memory_usage = process.memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            self.memory_usage = 0.0
        
        # Capture GUI state if available
        try:
            import tkinter as tk
            root = tk._default_root
            if root:
                self.open_windows = [str(child) for child in root.winfo_children()]
        except:
            pass


@dataclass
class GlobalErrorContext:
    """Enhanced error context with application state"""
    exception: Exception
    stack_trace: str
    thread_info: Dict[str, Any]
    application_state: ApplicationState
    error_source: str = "unknown"
    user_action_sequence: List[str] = field(default_factory=list)
    component_context: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_exception(cls, exc: Exception, source: str = "global") -> 'GlobalErrorContext':
        """Create error context from exception"""
        return cls(
            exception=exc,
            stack_trace=traceback.format_exc(),
            thread_info={
                'thread_name': threading.current_thread().name,
                'thread_id': threading.get_ident(),
                'is_main_thread': threading.current_thread() is threading.main_thread()
            },
            application_state=ApplicationState(),
            error_source=source
        )


class GlobalErrorProcessor:
    """Central processor for all unhandled errors"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_logger = None
        self.feedback_manager = None
        self.error_classifier = None
        self.error_count = 0
        self.critical_error_threshold = 5
        self.last_errors: List[GlobalErrorContext] = []
        self.max_error_history = 10
        self.shutdown_initiated = False
        
        # Initialize components if available
        try:
            self.error_logger = get_error_logger()
            self.feedback_manager = get_feedback_manager()
            self.error_classifier = ErrorClassifier()
        except:
            pass
    
    def process_error(self, error_context: GlobalErrorContext) -> bool:
        """
        Process an unhandled error through the complete pipeline
        
        Returns:
            bool: True if error was handled successfully, False if critical
        """
        try:
            # Capture application state
            error_context.application_state.capture_current_state()
            
            # Add to error history
            self._add_to_history(error_context)
            
            # Classify the error
            error_info = self._classify_error(error_context)
            
            # Log the error
            self._log_error(error_info, error_context)
            
            # Assess severity and determine response
            if self._is_critical_error(error_info, error_context):
                return self._handle_critical_error(error_info, error_context)
            else:
                return self._handle_non_critical_error(error_info, error_context)
        
        except Exception as e:
            # Last resort error handling
            self.logger.critical(f"Global error processor failed: {e}")
            self._emergency_log(error_context, e)
            return False
    
    def _classify_error(self, error_context: GlobalErrorContext) -> ErrorInfo:
        """Classify error using error categorization system"""
        exc = error_context.exception
        
        # Basic error info creation
        error_info = ErrorInfo(
            error_id=f"GLOBAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.error_count}",
            error_code=type(exc).__name__,
            message=str(exc),
            category=ErrorCategory.UNKNOWN,
            severity=ErrorSeverity.HIGH,
            context=ErrorContext(operation=error_context.error_source),
            recovery_strategy=RecoveryStrategy.FAIL_FAST,
            timestamp=datetime.now(),
            component=error_context.error_source,
            error_type=type(exc).__name__,
            stack_trace=error_context.stack_trace
        )
        
        # Use classifier if available
        if self.error_classifier:
            try:
                classified_info = self.error_classifier.classify_error(exc, error_context.error_source)
                # Merge classification results
                error_info.category = classified_info.category
                error_info.severity = classified_info.severity
                error_info.recovery_strategy = classified_info.recovery_strategy
            except:
                pass
        
        return error_info
    
    def _log_error(self, error_info: ErrorInfo, error_context: GlobalErrorContext):
        """Log error through enhanced logging system"""
        if self.error_logger:
            try:
                # Create detailed log entry
                log_data = {
                    'error_info': error_info.__dict__,
                    'thread_info': error_context.thread_info,
                    'application_state': {
                        'memory_usage': error_context.application_state.memory_usage,
                        'active_threads': error_context.application_state.active_threads,
                        'open_windows': error_context.application_state.open_windows
                    },
                    'error_count': self.error_count,
                    'error_history_length': len(self.last_errors)
                }
                
                self.error_logger.log_error(error_info, additional_context=log_data)
            except Exception as e:
                self.logger.error(f"Enhanced error logging failed: {e}")
                # Fallback to basic logging
                self.logger.error(f"Unhandled error: {error_context.exception}", exc_info=error_context.exception)
        else:
            # Fallback logging
            self.logger.error(f"Unhandled error: {error_context.exception}", exc_info=error_context.exception)
    
    def _is_critical_error(self, error_info: ErrorInfo, error_context: GlobalErrorContext) -> bool:
        """Determine if error is critical and requires immediate attention"""
        # Check error severity
        if error_info.severity == ErrorSeverity.CRITICAL:
            return True
        
        # Check error frequency
        if self.error_count >= self.critical_error_threshold:
            return True
        
        # Check for specific critical error types
        critical_types = {
            'MemoryError', 'SystemExit', 'KeyboardInterrupt',
            'SystemError', 'RecursionError'
        }
        if type(error_context.exception).__name__ in critical_types:
            return True
        
        # Check for main thread errors in UI applications
        if (error_context.thread_info['is_main_thread'] and 
            error_info.category == ErrorCategory.UI):
            return True
        
        return False
    
    def _handle_critical_error(self, error_info: ErrorInfo, error_context: GlobalErrorContext) -> bool:
        """Handle critical errors with emergency procedures"""
        self.logger.critical(f"Critical error detected: {error_info.error_code}")
        
        # Show critical error message to user
        try:
            if self.feedback_manager:
                message = generate_user_friendly_message(
                    error_info, 
                    UserRole.END_USER,
                    message_type='modal'
                )
                # In a real implementation, this would show a critical error dialog
                self.logger.critical(f"Critical error message: {message.title} - {message.message}")
        except:
            pass
        
        # Attempt emergency save/cleanup
        self._emergency_cleanup()
        
        # Consider graceful shutdown for repeated critical errors
        if self.error_count >= self.critical_error_threshold:
            self._initiate_graceful_shutdown()
            return False
        
        return True
    
    def _handle_non_critical_error(self, error_info: ErrorInfo, error_context: GlobalErrorContext) -> bool:
        """Handle non-critical errors with recovery attempts"""
        self.logger.warning(f"Non-critical error: {error_info.error_code}")
        
        # Show user notification
        try:
            if self.feedback_manager:
                message = generate_user_friendly_message(error_info, UserRole.END_USER)
                # In a real implementation, this might show a toast notification
                self.logger.info(f"User notification: {message.title}")
        except:
            pass
        
        # Attempt automatic recovery
        try:
            recovery_result = execute_auto_recovery(
                error_info, 
                error_context.error_source,
                error_context=error_context.__dict__
            )
            if recovery_result.success:
                self.logger.info(f"Automatic recovery successful for {error_info.error_code}")
                return True
        except:
            self.logger.warning("Automatic recovery failed or unavailable")
        
        return True
    
    def _add_to_history(self, error_context: GlobalErrorContext):
        """Add error to history for pattern analysis"""
        self.error_count += 1
        self.last_errors.append(error_context)
        
        # Maintain history size
        if len(self.last_errors) > self.max_error_history:
            self.last_errors.pop(0)
    
    def _emergency_log(self, error_context: GlobalErrorContext, processor_error: Exception):
        """Emergency logging when main processor fails"""
        try:
            with open('emergency_error.log', 'a') as f:
                f.write(f"\n{datetime.now().isoformat()}\n")
                f.write(f"ORIGINAL ERROR: {error_context.exception}\n")
                f.write(f"PROCESSOR ERROR: {processor_error}\n")
                f.write(f"STACK TRACE:\n{error_context.stack_trace}\n")
                f.write("-" * 50 + "\n")
        except:
            # Last resort - print to stderr
            print(f"EMERGENCY: {error_context.exception}", file=sys.stderr)
    
    def _emergency_cleanup(self):
        """Perform emergency cleanup operations"""
        try:
            # Force garbage collection
            gc.collect()
            
            # Close non-essential resources
            # (Implementation would depend on specific application resources)
            
            self.logger.info("Emergency cleanup completed")
        except Exception as e:
            self.logger.error(f"Emergency cleanup failed: {e}")
    
    def _initiate_graceful_shutdown(self):
        """Initiate graceful application shutdown"""
        if self.shutdown_initiated:
            return
        
        self.shutdown_initiated = True
        self.logger.critical("Initiating graceful shutdown due to repeated critical errors")
        
        try:
            # Save application state
            # Close resources gracefully
            # Notify user of shutdown
            
            # In a real implementation, this would trigger application shutdown
            pass
        except Exception as e:
            self.logger.error(f"Graceful shutdown failed: {e}")


class GlobalErrorHandler:
    """Main global error handler that sets up all error interception"""
    
    def __init__(self):
        self.processor = GlobalErrorProcessor()
        self.original_excepthook = None
        self.original_threading_excepthook = None
        self.tk_error_handler = None
        self.installed = False
        self.logger = logging.getLogger(__name__)
    
    def install(self):
        """Install global error handlers"""
        if self.installed:
            return
        
        # Install Python global exception handler
        self.original_excepthook = sys.excepthook
        sys.excepthook = self._global_exception_handler
        
        # Install threading exception handler (Python 3.8+)
        if hasattr(threading, 'excepthook'):
            self.original_threading_excepthook = threading.excepthook
            threading.excepthook = self._threading_exception_handler
        
        # Install Tkinter error handler
        try:
            import tkinter as tk
            root = tk._default_root
            if root:
                root.report_callback_exception = self._tk_exception_handler
        except:
            pass
        
        self.installed = True
        self.logger.info("Global error handlers installed successfully")
    
    def uninstall(self):
        """Uninstall global error handlers"""
        if not self.installed:
            return
        
        # Restore original handlers
        if self.original_excepthook:
            sys.excepthook = self.original_excepthook
        
        if self.original_threading_excepthook and hasattr(threading, 'excepthook'):
            threading.excepthook = self.original_threading_excepthook
        
        self.installed = False
        self.logger.info("Global error handlers uninstalled")
    
    def _global_exception_handler(self, exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions in main thread"""
        if exc_type is KeyboardInterrupt:
            # Allow keyboard interrupt to proceed normally
            if self.original_excepthook:
                self.original_excepthook(exc_type, exc_value, exc_traceback)
            return
        
        error_context = GlobalErrorContext.from_exception(exc_value, "main_thread")
        self.processor.process_error(error_context)
        
        # Call original handler if available
        if self.original_excepthook:
            self.original_excepthook(exc_type, exc_value, exc_traceback)
    
    def _threading_exception_handler(self, args):
        """Handle uncaught exceptions in threads"""
        exc_type, exc_value, exc_traceback, thread = args
        
        error_context = GlobalErrorContext.from_exception(exc_value, f"thread_{thread.name}")
        self.processor.process_error(error_context)
    
    def _tk_exception_handler(self, exc_type, exc_value, exc_traceback):
        """Handle Tkinter callback exceptions"""
        error_context = GlobalErrorContext.from_exception(exc_value, "tkinter_callback")
        self.processor.process_error(error_context)
    
    @contextmanager
    def error_boundary(self, operation_name: str = "unknown"):
        """Context manager for controlled error boundaries"""
        try:
            yield
        except Exception as e:
            error_context = GlobalErrorContext.from_exception(e, f"boundary_{operation_name}")
            self.processor.process_error(error_context)
            raise  # Re-raise after processing
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics and status"""
        return {
            'total_errors': self.processor.error_count,
            'recent_errors': len(self.processor.last_errors),
            'handlers_installed': self.installed,
            'shutdown_initiated': self.processor.shutdown_initiated,
            'last_error_time': (
                self.processor.last_errors[-1].application_state.timestamp.isoformat()
                if self.processor.last_errors else None
            )
        }


# Global error handler instance
_global_error_handler = None

def get_global_error_handler() -> GlobalErrorHandler:
    """Get the global error handler instance"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = GlobalErrorHandler()
    return _global_error_handler


def install_global_error_handlers():
    """Install global error handlers"""
    handler = get_global_error_handler()
    handler.install()


def uninstall_global_error_handlers():
    """Uninstall global error handlers"""
    handler = get_global_error_handler()
    handler.uninstall()


@contextmanager
def error_boundary(operation_name: str = "unknown"):
    """Context manager for controlled error boundaries"""
    handler = get_global_error_handler()
    with handler.error_boundary(operation_name):
        yield


def get_error_statistics() -> Dict[str, Any]:
    """Get global error statistics"""
    handler = get_global_error_handler()
    return handler.get_error_statistics() 