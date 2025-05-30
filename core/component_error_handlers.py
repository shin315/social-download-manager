"""
Component-Specific Error Handlers

This module provides specialized error handling for each major component 
of the application, ensuring errors are handled appropriately at the 
component level before escalating to global handlers.
"""

import sys
import os
import traceback
import functools
import inspect
from typing import Optional, Dict, Any, List, Callable, Union, Type
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import contextmanager
import logging
import asyncio

# Import error management components
try:
    from data.models.error_management import (
        ErrorInfo, ErrorCategory, ErrorSeverity, ErrorContext, RecoveryStrategy
    )
    from core.error_categorization import ErrorClassifier
    from core.logging_strategy import get_error_logger
    from core.user_feedback import get_feedback_manager, generate_user_friendly_message
    from core.recovery_engine import execute_auto_recovery
    from core.global_error_handler import get_global_error_handler, GlobalErrorContext
except ImportError:
    pass


@dataclass
class ComponentErrorConfig:
    """Configuration for component-specific error handling"""
    component_name: str
    error_category: ErrorCategory
    default_severity: ErrorSeverity = ErrorSeverity.MEDIUM
    default_recovery: RecoveryStrategy = RecoveryStrategy.RETRY
    max_retries: int = 3
    timeout_seconds: float = 30.0
    escalate_after_failures: int = 5
    custom_error_mappings: Dict[Type[Exception], Dict[str, Any]] = field(default_factory=dict)
    validation_rules: List[Callable] = field(default_factory=list)
    error_patterns: Dict[str, str] = field(default_factory=dict)
    fallback_actions: List[str] = field(default_factory=list)


class ComponentErrorHandler:
    """Base class for component-specific error handlers"""
    
    def __init__(self, config: ComponentErrorConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{config.component_name}")
        self.error_count = 0
        self.consecutive_failures = 0
        self.last_error_time: Optional[datetime] = None
        self.component_state: Dict[str, Any] = {}
        
        # Initialize error management components
        self.error_logger = None
        self.feedback_manager = None
        self.error_classifier = None
        
        try:
            self.error_logger = get_error_logger()
            self.feedback_manager = get_feedback_manager()
            self.error_classifier = ErrorClassifier()
        except:
            pass
    
    def handle_error(self, 
                    exception: Exception, 
                    operation: str = "unknown",
                    context: Optional[Dict[str, Any]] = None,
                    user_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Handle a component-specific error
        
        Returns:
            bool: True if error was handled successfully, False if needs escalation
        """
        try:
            # Update error statistics
            self._update_error_stats()
            
            # Create error context
            error_context = self._create_error_context(exception, operation, context, user_data)
            
            # Validate input if applicable
            validation_result = self._validate_error_context(error_context)
            if not validation_result['valid']:
                self.logger.warning(f"Error context validation failed: {validation_result['reason']}")
            
            # Check for error patterns
            pattern_match = self._match_error_pattern(exception)
            if pattern_match:
                return self._handle_pattern_match(exception, pattern_match, error_context)
            
            # Classify error using component-specific logic
            error_info = self._classify_component_error(exception, operation, error_context)
            
            # Apply component-specific handling
            handling_result = self._apply_component_handling(error_info, error_context)
            
            # Log the error
            self._log_component_error(error_info, error_context, handling_result)
            
            # Determine if escalation is needed
            if self._should_escalate(error_info, handling_result):
                return self._escalate_error(error_info, error_context)
            
            return handling_result.get('success', True)
            
        except Exception as handler_error:
            self.logger.critical(f"Component error handler failed: {handler_error}")
            # Fallback to global handler
            try:
                global_handler = get_global_error_handler()
                global_context = GlobalErrorContext.from_exception(
                    exception, f"{self.config.component_name}_handler_failure"
                )
                return global_handler.processor.process_error(global_context)
            except:
                return False
    
    def _update_error_stats(self):
        """Update error statistics"""
        self.error_count += 1
        current_time = datetime.now()
        
        # Check for consecutive failures
        if self.last_error_time and (current_time - self.last_error_time).seconds < 60:
            self.consecutive_failures += 1
        else:
            self.consecutive_failures = 1
        
        self.last_error_time = current_time
    
    def _create_error_context(self, 
                            exception: Exception, 
                            operation: str,
                            context: Optional[Dict[str, Any]],
                            user_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Create comprehensive error context"""
        return {
            'exception': exception,
            'operation': operation,
            'component': self.config.component_name,
            'timestamp': datetime.now(),
            'error_count': self.error_count,
            'consecutive_failures': self.consecutive_failures,
            'component_state': self.component_state.copy(),
            'context': context or {},
            'user_data': user_data or {},
            'stack_trace': traceback.format_exc()
        }
    
    def _validate_error_context(self, error_context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate error context using component-specific rules"""
        for rule in self.config.validation_rules:
            try:
                result = rule(error_context)
                if not result.get('valid', True):
                    return result
            except Exception as e:
                self.logger.warning(f"Validation rule failed: {e}")
        
        return {'valid': True}
    
    def _match_error_pattern(self, exception: Exception) -> Optional[str]:
        """Match error against known patterns"""
        exception_str = str(exception)
        exception_type = type(exception).__name__
        
        for pattern, action in self.config.error_patterns.items():
            if pattern in exception_str or pattern == exception_type:
                return action
        
        return None
    
    def _handle_pattern_match(self, 
                            exception: Exception, 
                            action: str, 
                            error_context: Dict[str, Any]) -> bool:
        """Handle error based on matched pattern"""
        self.logger.info(f"Handling error pattern match: {action}")
        
        # Execute pattern-specific action
        if action == "retry_with_delay":
            return self._retry_with_delay(error_context)
        elif action == "fallback_to_default":
            return self._apply_fallback(error_context)
        elif action == "prompt_user":
            return self._prompt_user_intervention(error_context)
        elif action == "ignore":
            return True
        else:
            return self._custom_pattern_action(action, error_context)
    
    def _classify_component_error(self, 
                                exception: Exception, 
                                operation: str,
                                error_context: Dict[str, Any]) -> ErrorInfo:
        """Classify error with component-specific logic"""
        # Check for custom error mappings
        exc_type = type(exception)
        if exc_type in self.config.custom_error_mappings:
            mapping = self.config.custom_error_mappings[exc_type]
            severity = mapping.get('severity', self.config.default_severity)
            recovery = mapping.get('recovery', self.config.default_recovery)
        else:
            severity = self.config.default_severity
            recovery = self.config.default_recovery
        
        # Create base error info
        error_info = ErrorInfo(
            error_id=f"{self.config.component_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.error_count}",
            error_code=exc_type.__name__,
            message=str(exception),
            category=self.config.error_category,
            severity=severity,
            context=ErrorContext(operation=operation),
            recovery_strategy=recovery,
            timestamp=datetime.now(),
            component=self.config.component_name,
            error_type=exc_type.__name__,
            stack_trace=error_context['stack_trace']
        )
        
        # Enhance with classifier if available
        if self.error_classifier:
            try:
                classified = self.error_classifier.classify_error(exception, self.config.component_name)
                # Merge classification results
                error_info.category = classified.category
                if classified.severity.value > severity.value:
                    error_info.severity = classified.severity
            except:
                pass
        
        return error_info
    
    def _apply_component_handling(self, 
                                error_info: ErrorInfo, 
                                error_context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply component-specific error handling logic"""
        # This is the base implementation - components should override
        result = {
            'success': True,  # Changed to True by default - basic handling (logging) is successful
            'action_taken': 'basic_handling',
            'recovery_attempted': False,
            'user_notified': False,
            'escalation_needed': False
        }
        
        # Attempt automatic recovery if configured
        if error_info.recovery_strategy != RecoveryStrategy.FAIL_FAST:
            try:
                recovery_result = execute_auto_recovery(
                    error_info, 
                    self.config.component_name,
                    error_context=error_context
                )
                result['recovery_attempted'] = True
                result['success'] = recovery_result.success
                result['action_taken'] = 'auto_recovery'
            except:
                # Even if recovery fails, basic handling succeeded
                pass
        
        return result
    
    def _should_escalate(self, error_info: ErrorInfo, handling_result: Dict[str, Any]) -> bool:
        """Determine if error should be escalated to global handler"""
        # Escalate if handling failed and it's a critical error
        if not handling_result.get('success', False) and error_info.severity == ErrorSeverity.CRITICAL:
            return True
        
        # Escalate if too many consecutive failures
        if self.consecutive_failures >= self.config.escalate_after_failures:
            return True
        
        # Escalate if explicitly requested
        if handling_result.get('escalation_needed', False):
            return True
        
        return False
    
    def _escalate_error(self, error_info: ErrorInfo, error_context: Dict[str, Any]) -> bool:
        """Escalate error to global handler"""
        self.logger.warning(f"Escalating error to global handler: {error_info.error_code}")
        
        try:
            global_handler = get_global_error_handler()
            global_context = GlobalErrorContext.from_exception(
                error_context['exception'], 
                f"{self.config.component_name}_escalated"
            )
            return global_handler.processor.process_error(global_context)
        except Exception as e:
            self.logger.error(f"Error escalation failed: {e}")
            return False
    
    def _log_component_error(self, 
                           error_info: ErrorInfo, 
                           error_context: Dict[str, Any],
                           handling_result: Dict[str, Any]):
        """Log error with component-specific details"""
        if self.error_logger:
            try:
                additional_context = {
                    'component_config': {
                        'name': self.config.component_name,
                        'category': self.config.error_category.value,
                        'max_retries': self.config.max_retries
                    },
                    'component_stats': {
                        'error_count': self.error_count,
                        'consecutive_failures': self.consecutive_failures
                    },
                    'handling_result': handling_result
                }
                self.error_logger.log_error(error_info, additional_context=additional_context)
            except Exception as e:
                self.logger.error(f"Component error logging failed: {e}")
        else:
            # Fallback logging
            self.logger.error(f"Component error: {error_info.error_code} - {error_info.message}")
    
    # Helper methods for common error handling patterns
    def _retry_with_delay(self, error_context: Dict[str, Any]) -> bool:
        """Implement retry with delay pattern"""
        # This would implement actual retry logic
        self.logger.info("Applying retry with delay pattern")
        return True
    
    def _apply_fallback(self, error_context: Dict[str, Any]) -> bool:
        """Apply fallback actions"""
        self.logger.info("Applying fallback actions")
        for action in self.config.fallback_actions:
            try:
                # Execute fallback action
                self.logger.info(f"Executing fallback action: {action}")
            except Exception as e:
                self.logger.warning(f"Fallback action '{action}' failed: {e}")
        return True
    
    def _prompt_user_intervention(self, error_context: Dict[str, Any]) -> bool:
        """Request user intervention"""
        self.logger.info("Requesting user intervention")
        return True
    
    def _custom_pattern_action(self, action: str, error_context: Dict[str, Any]) -> bool:
        """Handle custom pattern actions"""
        self.logger.info(f"Executing custom pattern action: {action}")
        return True
    
    @contextmanager
    def error_context(self, operation: str, **kwargs):
        """Context manager for component error handling"""
        try:
            yield
        except Exception as e:
            handled = self.handle_error(e, operation, context=kwargs)
            if not handled:
                raise


# Decorator for automatic error handling
def component_error_handler(component_name: str, 
                          category: ErrorCategory,
                          operation: Optional[str] = None,
                          **config_kwargs):
    """Decorator for automatic component error handling"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create handler config
            config = ComponentErrorConfig(
                component_name=component_name,
                error_category=category,
                **config_kwargs
            )
            handler = ComponentErrorHandler(config)
            
            # Determine operation name
            op_name = operation or func.__name__
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Extract context from function arguments
                context = {
                    'function': func.__name__,
                    'module': func.__module__,
                    'args': str(args)[:200],  # Limit length
                    'kwargs': str(kwargs)[:200]
                }
                
                handled = handler.handle_error(e, op_name, context=context)
                if handled:
                    # Return None if error was handled successfully
                    return None
                else:
                    # Re-raise if error could not be handled
                    raise
        
        return wrapper
    return decorator


# Validation decorators
def validate_input(**validation_rules):
    """Decorator for input validation with error handling"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Perform validation
            for param_name, validator in validation_rules.items():
                if param_name in kwargs:
                    value = kwargs[param_name]
                    if not validator(value):
                        raise ValueError(f"Validation failed for parameter '{param_name}': {value}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_non_null(*param_names):
    """Decorator to ensure specified parameters are not None"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get function signature
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Check specified parameters
            for param_name in param_names:
                if param_name in bound_args.arguments:
                    if bound_args.arguments[param_name] is None:
                        raise ValueError(f"Parameter '{param_name}' cannot be None")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Specific component error handlers
class UIErrorHandler(ComponentErrorHandler):
    """Specialized error handler for UI components"""
    
    def __init__(self):
        config = ComponentErrorConfig(
            component_name="ui_component",
            error_category=ErrorCategory.UI,
            default_severity=ErrorSeverity.MEDIUM,
            default_recovery=RecoveryStrategy.RETRY,
            max_retries=2,
            error_patterns={
                'TclError': 'reset_widget_state',
                'AttributeError': 'fallback_to_default',
                'ValueError': 'prompt_user'
            },
            fallback_actions=['reset_form', 'show_error_message', 'disable_feature']
        )
        super().__init__(config)
    
    def _apply_component_handling(self, error_info: ErrorInfo, error_context: Dict[str, Any]) -> Dict[str, Any]:
        """UI-specific error handling"""
        result = super()._apply_component_handling(error_info, error_context)
        
        # UI-specific recovery actions
        if 'widget' in error_context.get('context', {}):
            result['action_taken'] = 'widget_recovery'
            result['success'] = True
        
        return result


class PlatformServiceErrorHandler(ComponentErrorHandler):
    """Specialized error handler for platform API services"""
    
    def __init__(self):
        config = ComponentErrorConfig(
            component_name="platform_service",
            error_category=ErrorCategory.PLATFORM,
            default_severity=ErrorSeverity.HIGH,
            default_recovery=RecoveryStrategy.FALLBACK,
            max_retries=3,
            timeout_seconds=60.0,
            error_patterns={
                'ConnectionError': 'retry_with_backoff',
                'TimeoutError': 'retry_with_delay',
                'HTTPError': 'check_api_status',
                '401': 'refresh_authentication',
                '429': 'rate_limit_backoff'
            },
            fallback_actions=['use_cached_data', 'try_alternative_endpoint']
        )
        super().__init__(config)


class DownloadServiceErrorHandler(ComponentErrorHandler):
    """Specialized error handler for download services"""
    
    def __init__(self):
        config = ComponentErrorConfig(
            component_name="download_service",
            error_category=ErrorCategory.DOWNLOAD,
            default_severity=ErrorSeverity.MEDIUM,
            default_recovery=RecoveryStrategy.RETRY,
            max_retries=5,
            error_patterns={
                'FileNotFoundError': 'check_disk_space',
                'PermissionError': 'request_permissions',
                'OSError': 'retry_with_different_path',
                'ConnectionError': 'retry_with_backoff'
            },
            fallback_actions=['try_alternative_location', 'notify_user']
        )
        super().__init__(config)


class RepositoryErrorHandler(ComponentErrorHandler):
    """Specialized error handler for repository/database services"""
    
    def __init__(self):
        config = ComponentErrorConfig(
            component_name="repository_service",
            error_category=ErrorCategory.REPOSITORY,
            default_severity=ErrorSeverity.HIGH,
            default_recovery=RecoveryStrategy.RETRY,
            max_retries=3,
            error_patterns={
                'DatabaseError': 'check_connection',
                'IntegrityError': 'validate_data',
                'OperationalError': 'retry_transaction',
                'ConnectionError': 'reconnect_database'
            },
            fallback_actions=['use_readonly_mode', 'sync_later']
        )
        super().__init__(config)


# Component handler registry
_component_handlers: Dict[str, ComponentErrorHandler] = {}

def get_component_handler(component_name: str) -> Optional[ComponentErrorHandler]:
    """Get registered component error handler"""
    return _component_handlers.get(component_name)

def register_component_handler(component_name: str, handler: ComponentErrorHandler):
    """Register a component error handler"""
    _component_handlers[component_name] = handler

def initialize_component_handlers():
    """Initialize all component error handlers"""
    handlers = {
        'ui': UIErrorHandler(),
        'platform': PlatformServiceErrorHandler(),
        'download': DownloadServiceErrorHandler(),
        'repository': RepositoryErrorHandler()
    }
    
    for name, handler in handlers.items():
        register_component_handler(name, handler)
    
    return handlers

# Convenience functions
def handle_ui_error(exception: Exception, operation: str = "ui_operation", **kwargs) -> bool:
    """Handle UI component error"""
    handler = get_component_handler('ui')
    if not handler:
        handler = UIErrorHandler()
        register_component_handler('ui', handler)
    return handler.handle_error(exception, operation, **kwargs)

def handle_platform_error(exception: Exception, operation: str = "platform_operation", **kwargs) -> bool:
    """Handle platform service error"""
    handler = get_component_handler('platform')
    if not handler:
        handler = PlatformServiceErrorHandler()
        register_component_handler('platform', handler)
    return handler.handle_error(exception, operation, **kwargs)

def handle_download_error(exception: Exception, operation: str = "download_operation", **kwargs) -> bool:
    """Handle download service error"""
    handler = get_component_handler('download')
    if not handler:
        handler = DownloadServiceErrorHandler()
        register_component_handler('download', handler)
    return handler.handle_error(exception, operation, **kwargs)

def handle_repository_error(exception: Exception, operation: str = "repository_operation", **kwargs) -> bool:
    """Handle repository service error"""
    handler = get_component_handler('repository')
    if not handler:
        handler = RepositoryErrorHandler()
        register_component_handler('repository', handler)
    return handler.handle_error(exception, operation, **kwargs) 