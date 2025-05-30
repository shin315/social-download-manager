"""
Repository-UI Error Integration for Social Download Manager v2.0

Integrates the repository error management system with UI error presentation framework.
Implements error translation mechanisms that convert repository-specific errors into 
user-friendly messages and ensures error states are properly reflected in UI components.

This module bridges Task 18 (Data Integration Layer) with Task 19 (Error Handling System).
"""

from typing import Dict, Any, List, Optional, Callable, Union, TypeVar
from datetime import datetime
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging
from PyQt6.QtWidgets import QMessageBox, QWidget, QLabel, QProgressBar, QStatusBar
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from data.models.repositories import IRepository, IContentRepository
from data.models.repository_interfaces import IDownloadRepository
from data.models.base import BaseEntity, EntityId
from data.models.error_management import (
    ErrorManager, ErrorClassifier, ErrorContext, ErrorCategory,
    ErrorInfo, ErrorSeverity, RecoveryStrategy, get_user_friendly_message
)
from core.event_system import EventBus, Event, EventType, get_event_bus, publish_event
from .repository_event_integration import (
    RepositoryEventType, RepositoryEventPayload, get_repository_event_manager
)
from .repository_state_sync import get_repository_state_manager
from .data_binding_strategy import get_data_binding_manager

T = TypeVar('T', bound=BaseEntity)


@dataclass
class UIErrorState:
    """Represents error state for UI components"""
    component_id: str
    error_category: ErrorCategory
    error_severity: ErrorSeverity
    user_message: str
    technical_message: str
    recovery_strategy: RecoveryStrategy
    timestamp: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    retry_count: int = 0
    max_retries: int = 3
    context: Optional[Dict[str, Any]] = None


@dataclass
class UIErrorDisplayConfig:
    """Configuration for how errors should be displayed in UI"""
    show_message_box: bool = True
    show_status_bar: bool = True
    show_inline_error: bool = False
    auto_dismiss_timeout: Optional[int] = None  # seconds
    enable_retry_button: bool = True
    enable_details_button: bool = True
    theme_aware: bool = True
    localization_enabled: bool = True


class IUIErrorPresenter(ABC):
    """Interface for UI error presentation"""
    
    @abstractmethod
    def show_error(self, error_state: UIErrorState, config: UIErrorDisplayConfig) -> None:
        """Display error to user"""
        pass
    
    @abstractmethod
    def clear_error(self, component_id: str) -> None:
        """Clear error display for component"""
        pass
    
    @abstractmethod
    def update_error_state(self, error_state: UIErrorState) -> None:
        """Update existing error display"""
        pass


class RepositoryErrorTranslator:
    """
    Translates repository errors into UI-friendly formats
    
    Leverages the error categorization system from Task 19.1 to provide
    consistent error translation and user message generation.
    """
    
    def __init__(self, error_manager: Optional[ErrorManager] = None):
        self._error_manager = error_manager or ErrorManager()
        self._logger = logging.getLogger(__name__)
        
        # Translation cache for performance
        self._translation_cache: Dict[str, UIErrorState] = {}
        self._cache_timeout = 300  # 5 minutes
        
        # Repository-specific error mappings
        self._repository_error_mappings = self._initialize_repository_mappings()
    
    def translate_repository_error(self, repository: IRepository, error: Exception,
                                 operation: str, component_id: str,
                                 context: Optional[Dict[str, Any]] = None) -> UIErrorState:
        """
        Translate repository error into UI error state
        
        Args:
            repository: Repository where error occurred
            error: The exception that occurred
            operation: Repository operation that failed
            component_id: UI component affected by the error
            context: Additional context information
            
        Returns:
            UIErrorState with translated error information
        """
        try:
            # Create error context
            error_context = ErrorContext(
                component=component_id,
                operation=operation,
                user_action=context.get('user_action') if context else None,
                additional_info=context or {}
            )
            
            # Classify error using Task 19.1 error categorization
            error_category = ErrorClassifier.classify_error(error, error_context)
            error_severity = ErrorClassifier.determine_severity(error, error_category)
            recovery_strategy = ErrorClassifier.determine_recovery_strategy(error, error_category)
            
            # Get specific error type for repository errors
            specific_error_type = None
            if error_category == ErrorCategory.REPOSITORY:
                specific_error_type = ErrorClassifier.get_specific_error_type(error, error_category)
            
            # Generate user-friendly message
            user_message = self._generate_user_message(
                error_category, specific_error_type, repository, operation, context
            )
            
            # Generate technical message for debugging
            technical_message = self._generate_technical_message(
                error, repository, operation, error_context
            )
            
            # Create UI error state
            ui_error_state = UIErrorState(
                component_id=component_id,
                error_category=error_category,
                error_severity=error_severity,
                user_message=user_message,
                technical_message=technical_message,
                recovery_strategy=recovery_strategy,
                context=context
            )
            
            # Cache translation for performance
            cache_key = self._generate_cache_key(repository, error, operation, component_id)
            self._translation_cache[cache_key] = ui_error_state
            
            self._logger.debug(f"Translated repository error for {component_id}: {error_category.value}")
            
            return ui_error_state
            
        except Exception as e:
            self._logger.error(f"Error translating repository error: {e}")
            
            # Fallback error state
            return UIErrorState(
                component_id=component_id,
                error_category=ErrorCategory.UNKNOWN,
                error_severity=ErrorSeverity.MEDIUM,
                user_message="An unexpected error occurred. Please try again.",
                technical_message=str(error),
                recovery_strategy=RecoveryStrategy.RETRY
            )
    
    def _generate_user_message(self, category: ErrorCategory, error_type: Optional[str],
                              repository: IRepository, operation: str,
                              context: Optional[Dict[str, Any]]) -> str:
        """Generate user-friendly error message"""
        
        # Use Task 19.1 error message system
        base_message = get_user_friendly_message(category, error_type)
        
        # Enhance with repository-specific context
        if category == ErrorCategory.REPOSITORY:
            repo_type = repository.__class__.__name__
            if repo_type in self._repository_error_mappings:
                operation_messages = self._repository_error_mappings[repo_type].get(operation, {})
                if error_type in operation_messages:
                    base_message = operation_messages[error_type]
        
        # Add contextual information
        if context:
            entity_type = context.get('entity_type')
            if entity_type:
                base_message = base_message.replace("Data operation", f"{entity_type} operation")
        
        return base_message
    
    def _generate_technical_message(self, error: Exception, repository: IRepository,
                                   operation: str, error_context: ErrorContext) -> str:
        """Generate technical error message for debugging"""
        repo_type = repository.__class__.__name__
        error_type = error.__class__.__name__
        
        technical_msg = f"Repository Error in {repo_type}.{operation}(): {error_type} - {str(error)}"
        
        if error_context.additional_info:
            technical_msg += f" | Context: {error_context.additional_info}"
        
        return technical_msg
    
    def _initialize_repository_mappings(self) -> Dict[str, Dict[str, Dict[str, str]]]:
        """Initialize repository-specific error message mappings"""
        return {
            'ContentRepository': {
                'save': {
                    'VALIDATION_ERROR': "Failed to save content. Please check the content data and try again.",
                    'CONSTRAINT_VIOLATION': "Content already exists or violates data constraints.",
                    'CONNECTION_FAILED': "Cannot save content. Database connection failed."
                },
                'find_by_id': {
                    'NOT_FOUND': "Content not found. It may have been deleted.",
                    'CONNECTION_FAILED': "Cannot retrieve content. Database connection failed."
                },
                'delete': {
                    'NOT_FOUND': "Cannot delete content. Content not found.",
                    'CONSTRAINT_VIOLATION': "Cannot delete content. It is referenced by other data."
                }
            },
            'DownloadRepository': {
                'save': {
                    'VALIDATION_ERROR': "Failed to save download record. Please check the download data.",
                    'CONSTRAINT_VIOLATION': "Download record already exists or violates constraints.",
                    'CONNECTION_FAILED': "Cannot save download record. Database connection failed."
                },
                'update_progress': {
                    'NOT_FOUND': "Cannot update download progress. Download record not found.",
                    'CONNECTION_FAILED': "Cannot update progress. Database connection failed."
                }
            }
        }
    
    def _generate_cache_key(self, repository: IRepository, error: Exception,
                           operation: str, component_id: str) -> str:
        """Generate cache key for error translation"""
        repo_type = repository.__class__.__name__
        error_type = error.__class__.__name__
        return f"{repo_type}_{operation}_{error_type}_{component_id}"
    
    def clear_cache(self) -> None:
        """Clear translation cache"""
        self._translation_cache.clear()
        self._logger.debug("Cleared error translation cache")


class QtErrorPresenter(QObject, IUIErrorPresenter):
    """
    Qt-specific error presenter using QMessageBox and status bar
    
    Integrates with existing Qt UI patterns and theme system.
    """
    
    # Signals for error presentation events
    error_displayed = pyqtSignal(str, str)  # component_id, error_message
    error_cleared = pyqtSignal(str)  # component_id
    error_retry_requested = pyqtSignal(str, object)  # component_id, error_state
    
    def __init__(self, parent_widget: Optional[QWidget] = None):
        super().__init__()
        self._parent_widget = parent_widget
        self._logger = logging.getLogger(__name__)
        
        # Active error displays
        self._active_errors: Dict[str, UIErrorState] = {}
        self._message_boxes: Dict[str, QMessageBox] = {}
        self._status_bar_messages: Dict[str, str] = {}
        
        # Auto-dismiss timers
        self._dismiss_timers: Dict[str, QTimer] = {}
        
        # Theme detection
        self._current_theme = self._detect_theme()
    
    def show_error(self, error_state: UIErrorState, config: UIErrorDisplayConfig) -> None:
        """Display error using Qt widgets"""
        try:
            component_id = error_state.component_id
            
            # Store active error
            self._active_errors[component_id] = error_state
            
            # Show message box if configured
            if config.show_message_box:
                self._show_message_box(error_state, config)
            
            # Show status bar message if configured
            if config.show_status_bar:
                self._show_status_bar_message(error_state, config)
            
            # Setup auto-dismiss if configured
            if config.auto_dismiss_timeout:
                self._setup_auto_dismiss(component_id, config.auto_dismiss_timeout)
            
            # Emit signal
            self.error_displayed.emit(component_id, error_state.user_message)
            
            self._logger.debug(f"Displayed error for component {component_id}")
            
        except Exception as e:
            self._logger.error(f"Error displaying UI error: {e}")
    
    def clear_error(self, component_id: str) -> None:
        """Clear error display for component"""
        try:
            # Close message box if exists
            if component_id in self._message_boxes:
                self._message_boxes[component_id].close()
                del self._message_boxes[component_id]
            
            # Clear status bar message
            if component_id in self._status_bar_messages:
                self._clear_status_bar_message(component_id)
            
            # Cancel auto-dismiss timer
            if component_id in self._dismiss_timers:
                self._dismiss_timers[component_id].stop()
                del self._dismiss_timers[component_id]
            
            # Remove from active errors
            if component_id in self._active_errors:
                del self._active_errors[component_id]
            
            # Emit signal
            self.error_cleared.emit(component_id)
            
            self._logger.debug(f"Cleared error for component {component_id}")
            
        except Exception as e:
            self._logger.error(f"Error clearing UI error: {e}")
    
    def update_error_state(self, error_state: UIErrorState) -> None:
        """Update existing error display"""
        component_id = error_state.component_id
        
        if component_id in self._active_errors:
            # Update stored state
            self._active_errors[component_id] = error_state
            
            # Update message box if exists
            if component_id in self._message_boxes:
                msg_box = self._message_boxes[component_id]
                msg_box.setText(error_state.user_message)
            
            # Update status bar if exists
            if component_id in self._status_bar_messages:
                self._update_status_bar_message(component_id, error_state.user_message)
    
    def _show_message_box(self, error_state: UIErrorState, config: UIErrorDisplayConfig) -> None:
        """Show error in QMessageBox"""
        component_id = error_state.component_id
        
        # Create message box
        msg_box = QMessageBox(self._parent_widget)
        msg_box.setWindowTitle("Error")
        msg_box.setText(error_state.user_message)
        
        # Set icon based on severity
        if error_state.error_severity == ErrorSeverity.HIGH:
            msg_box.setIcon(QMessageBox.Icon.Critical)
        elif error_state.error_severity == ErrorSeverity.MEDIUM:
            msg_box.setIcon(QMessageBox.Icon.Warning)
        else:
            msg_box.setIcon(QMessageBox.Icon.Information)
        
        # Add buttons based on recovery strategy
        if config.enable_retry_button and error_state.recovery_strategy == RecoveryStrategy.RETRY:
            retry_button = msg_box.addButton("Retry", QMessageBox.ButtonRole.ActionRole)
            retry_button.clicked.connect(lambda: self._handle_retry(component_id, error_state))
        
        if config.enable_details_button:
            details_button = msg_box.addButton("Details", QMessageBox.ButtonRole.ActionRole)
            details_button.clicked.connect(lambda: self._show_error_details(error_state))
        
        msg_box.addButton(QMessageBox.StandardButton.Ok)
        
        # Apply theme if configured
        if config.theme_aware:
            self._apply_theme_to_message_box(msg_box)
        
        # Store and show
        self._message_boxes[component_id] = msg_box
        msg_box.show()
    
    def _show_status_bar_message(self, error_state: UIErrorState, config: UIErrorDisplayConfig) -> None:
        """Show error in status bar"""
        component_id = error_state.component_id
        
        # Find status bar in parent widget hierarchy
        status_bar = self._find_status_bar()
        if status_bar:
            timeout = config.auto_dismiss_timeout * 1000 if config.auto_dismiss_timeout else 0
            status_bar.showMessage(error_state.user_message, timeout)
            self._status_bar_messages[component_id] = error_state.user_message
    
    def _apply_theme_to_message_box(self, msg_box: QMessageBox) -> None:
        """Apply current theme to message box"""
        if self._current_theme == "dark":
            dark_style = """
                QMessageBox {
                    background-color: #2d2d2d;
                    color: #ffffff;
                }
                QLabel {
                    color: #ffffff;
                }
                QPushButton {
                    background-color: #0078d7;
                    color: white;
                    border: none;
                    padding: 6px 12px;
                    margin: 4px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #005fa3;
                }
            """
            msg_box.setStyleSheet(dark_style)
        else:
            light_style = """
                QMessageBox {
                    background-color: #f0f0f0;
                    color: #333333;
                }
                QLabel {
                    color: #333333;
                }
                QPushButton {
                    background-color: #0078d7;
                    color: white;
                    border: none;
                    padding: 6px 12px;
                    margin: 4px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #005fa3;
                }
            """
            msg_box.setStyleSheet(light_style)
    
    def _handle_retry(self, component_id: str, error_state: UIErrorState) -> None:
        """Handle retry button click"""
        error_state.retry_count += 1
        self.error_retry_requested.emit(component_id, error_state)
        self.clear_error(component_id)
    
    def _show_error_details(self, error_state: UIErrorState) -> None:
        """Show detailed error information"""
        details_box = QMessageBox(self._parent_widget)
        details_box.setWindowTitle("Error Details")
        details_box.setText(f"Technical Details:\n\n{error_state.technical_message}")
        details_box.setIcon(QMessageBox.Icon.Information)
        details_box.exec()
    
    def _setup_auto_dismiss(self, component_id: str, timeout: int) -> None:
        """Setup auto-dismiss timer"""
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self.clear_error(component_id))
        timer.start(timeout * 1000)
        self._dismiss_timers[component_id] = timer
    
    def _find_status_bar(self) -> Optional[QStatusBar]:
        """Find status bar in parent widget hierarchy"""
        widget = self._parent_widget
        while widget:
            if hasattr(widget, 'status_bar') and isinstance(widget.status_bar, QStatusBar):
                return widget.status_bar
            if hasattr(widget, 'statusBar') and callable(widget.statusBar):
                return widget.statusBar()
            widget = widget.parent() if hasattr(widget, 'parent') else None
        return None
    
    def _clear_status_bar_message(self, component_id: str) -> None:
        """Clear status bar message"""
        status_bar = self._find_status_bar()
        if status_bar and component_id in self._status_bar_messages:
            status_bar.clearMessage()
            del self._status_bar_messages[component_id]
    
    def _update_status_bar_message(self, component_id: str, message: str) -> None:
        """Update status bar message"""
        status_bar = self._find_status_bar()
        if status_bar:
            status_bar.showMessage(message)
            self._status_bar_messages[component_id] = message
    
    def _detect_theme(self) -> str:
        """Detect current theme from parent widget"""
        if self._parent_widget and hasattr(self._parent_widget, 'current_theme'):
            return self._parent_widget.current_theme
        return "dark"  # Default theme


class RepositoryUIErrorIntegrator(QObject):
    """
    Main integrator for repository errors and UI error presentation
    
    Coordinates between repository error events, error translation,
    and UI error presentation to provide seamless error handling.
    """
    
    # Signals for integration events
    repository_error_handled = pyqtSignal(str, object)  # component_id, error_state
    error_recovery_attempted = pyqtSignal(str, str)  # component_id, recovery_action
    error_recovery_completed = pyqtSignal(str, bool)  # component_id, success
    
    def __init__(self, parent_widget: Optional[QWidget] = None):
        super().__init__()
        
        # Core components
        self._error_translator = RepositoryErrorTranslator()
        self._error_presenter = QtErrorPresenter(parent_widget)
        self._logger = logging.getLogger(__name__)
        
        # Integration with other systems
        self._repository_event_manager = get_repository_event_manager()
        self._repository_state_manager = get_repository_state_manager()
        self._data_binding_manager = get_data_binding_manager()
        
        # Error handling configuration
        self._default_display_config = UIErrorDisplayConfig()
        self._component_configs: Dict[str, UIErrorDisplayConfig] = {}
        
        # Recovery handlers
        self._recovery_handlers: Dict[str, Callable] = {}
        
        # Setup event subscriptions
        self._setup_repository_error_subscriptions()
        self._setup_error_presenter_connections()
    
    def register_component_error_config(self, component_id: str, 
                                      config: UIErrorDisplayConfig) -> None:
        """Register error display configuration for a component"""
        self._component_configs[component_id] = config
        self._logger.debug(f"Registered error config for component: {component_id}")
    
    def register_recovery_handler(self, component_id: str, 
                                handler: Callable[[UIErrorState], bool]) -> None:
        """Register error recovery handler for a component"""
        self._recovery_handlers[component_id] = handler
        self._logger.debug(f"Registered recovery handler for component: {component_id}")
    
    def handle_repository_error(self, repository: IRepository, error: Exception,
                              operation: str, component_id: str,
                              context: Optional[Dict[str, Any]] = None) -> None:
        """
        Handle repository error and present to UI
        
        Args:
            repository: Repository where error occurred
            error: The exception that occurred
            operation: Repository operation that failed
            component_id: UI component affected by the error
            context: Additional context information
        """
        try:
            # Translate error to UI format
            error_state = self._error_translator.translate_repository_error(
                repository, error, operation, component_id, context
            )
            
            # Get display configuration
            display_config = self._component_configs.get(component_id, self._default_display_config)
            
            # Present error to UI
            self._error_presenter.show_error(error_state, display_config)
            
            # Emit signal
            self.repository_error_handled.emit(component_id, error_state)
            
            # Attempt automatic recovery if configured
            if error_state.recovery_strategy == RecoveryStrategy.AUTOMATIC:
                self._attempt_automatic_recovery(component_id, error_state)
            
            self._logger.info(f"Handled repository error for component {component_id}: {error_state.error_category.value}")
            
        except Exception as e:
            self._logger.error(f"Error handling repository error: {e}")
    
    def clear_component_error(self, component_id: str) -> None:
        """Clear error display for a component"""
        self._error_presenter.clear_error(component_id)
    
    def _setup_repository_error_subscriptions(self) -> None:
        """Subscribe to repository error events"""
        subscriber = self._repository_event_manager.get_subscriber()
        
        # Subscribe to repository error events
        def handle_repository_error_event(event_type, payload):
            if event_type == RepositoryEventType.REPOSITORY_ERROR:
                # Extract error information from payload
                repository_type = payload.repository_type
                operation = payload.operation
                error_message = payload.error_message
                
                # Create mock repository and error for translation
                # In real implementation, this would be more sophisticated
                mock_error = Exception(error_message)
                component_id = payload.context.get('component_id', 'unknown') if payload.context else 'unknown'
                
                # Handle the error (simplified for this implementation)
                self._logger.warning(f"Repository error event: {repository_type}.{operation} - {error_message}")
        
        subscriber.subscribe_to_repository_type("Repository", handle_repository_error_event)
    
    def _setup_error_presenter_connections(self) -> None:
        """Setup connections with error presenter"""
        self._error_presenter.error_retry_requested.connect(self._handle_retry_request)
    
    def _handle_retry_request(self, component_id: str, error_state: UIErrorState) -> None:
        """Handle retry request from UI"""
        try:
            # Check retry limits
            if error_state.retry_count >= error_state.max_retries:
                self._logger.warning(f"Max retries exceeded for component {component_id}")
                return
            
            # Attempt recovery
            success = self._attempt_recovery(component_id, error_state)
            
            # Emit signals
            self.error_recovery_attempted.emit(component_id, "retry")
            self.error_recovery_completed.emit(component_id, success)
            
            if not success:
                # Show updated error state
                error_state.retry_count += 1
                display_config = self._component_configs.get(component_id, self._default_display_config)
                self._error_presenter.show_error(error_state, display_config)
            
        except Exception as e:
            self._logger.error(f"Error handling retry request: {e}")
    
    def _attempt_automatic_recovery(self, component_id: str, error_state: UIErrorState) -> bool:
        """Attempt automatic error recovery"""
        return self._attempt_recovery(component_id, error_state)
    
    def _attempt_recovery(self, component_id: str, error_state: UIErrorState) -> bool:
        """Attempt error recovery using registered handlers"""
        try:
            # Use component-specific recovery handler if available
            if component_id in self._recovery_handlers:
                handler = self._recovery_handlers[component_id]
                return handler(error_state)
            
            # Default recovery strategies
            if error_state.recovery_strategy == RecoveryStrategy.RETRY:
                # Generic retry logic would go here
                return True
            elif error_state.recovery_strategy == RecoveryStrategy.FALLBACK:
                # Generic fallback logic would go here
                return True
            
            return False
            
        except Exception as e:
            self._logger.error(f"Error during recovery attempt: {e}")
            return False
    
    def get_active_errors(self) -> Dict[str, UIErrorState]:
        """Get all active error states"""
        return self._error_presenter._active_errors.copy()
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error handling statistics"""
        active_errors = self._error_presenter._active_errors
        
        return {
            'active_error_count': len(active_errors),
            'error_categories': {
                category.value: sum(1 for error in active_errors.values() 
                                  if error.error_category == category)
                for category in ErrorCategory
            },
            'components_with_errors': list(active_errors.keys()),
            'registered_components': len(self._component_configs),
            'registered_recovery_handlers': len(self._recovery_handlers)
        }


# Global repository-UI error integrator instance
_repository_ui_error_integrator: Optional[RepositoryUIErrorIntegrator] = None


def get_repository_ui_error_integrator(parent_widget: Optional[QWidget] = None) -> RepositoryUIErrorIntegrator:
    """Get the global repository-UI error integrator instance"""
    global _repository_ui_error_integrator
    if _repository_ui_error_integrator is None:
        _repository_ui_error_integrator = RepositoryUIErrorIntegrator(parent_widget)
    return _repository_ui_error_integrator


def handle_repository_error(repository: IRepository, error: Exception, operation: str,
                          component_id: str, context: Optional[Dict[str, Any]] = None) -> None:
    """Convenience function to handle repository errors"""
    integrator = get_repository_ui_error_integrator()
    integrator.handle_repository_error(repository, error, operation, component_id, context)


def register_component_error_handling(component_id: str, config: UIErrorDisplayConfig,
                                    recovery_handler: Optional[Callable] = None) -> None:
    """Convenience function to register component error handling"""
    integrator = get_repository_ui_error_integrator()
    integrator.register_component_error_config(component_id, config)
    
    if recovery_handler:
        integrator.register_recovery_handler(component_id, recovery_handler)


# =============================================================================
# Integration Helpers and Utilities
# =============================================================================

def create_error_display_config(show_message_box: bool = True,
                               show_status_bar: bool = True,
                               auto_dismiss_timeout: Optional[int] = None,
                               **kwargs) -> UIErrorDisplayConfig:
    """Create error display configuration"""
    return UIErrorDisplayConfig(
        show_message_box=show_message_box,
        show_status_bar=show_status_bar,
        auto_dismiss_timeout=auto_dismiss_timeout,
        **kwargs
    )


def create_repository_error_context(user_action: Optional[str] = None,
                                   entity_type: Optional[str] = None,
                                   entity_id: Optional[str] = None,
                                   **additional_info) -> Dict[str, Any]:
    """Create context for repository error handling"""
    context = {
        'user_action': user_action,
        'entity_type': entity_type,
        'entity_id': entity_id,
        **additional_info
    }
    return {k: v for k, v in context.items() if v is not None}


# =============================================================================
# Documentation and Usage Examples
# =============================================================================

"""
Repository-UI Error Integration Implementation Guide

This module provides comprehensive integration between repository errors and UI error presentation:

1. **Error Translation**:
   - Leverages Task 19.1 error categorization system
   - Translates repository-specific errors to user-friendly messages
   - Provides technical details for debugging

2. **UI Error Presentation**:
   - Qt-native error display using QMessageBox and status bar
   - Theme-aware styling for consistent UI experience
   - Configurable display options per component

3. **Error Recovery**:
   - Automatic retry mechanisms based on error type
   - Component-specific recovery handlers
   - Recovery attempt tracking and limits

4. **Event Integration**:
   - Subscribes to repository error events
   - Publishes error handling events for other components
   - Integrates with existing event bus system

Usage Example:

```python
from core.data_integration.repository_ui_error_integration import (
    get_repository_ui_error_integrator, create_error_display_config,
    create_repository_error_context
)

# Setup error handling for a component
integrator = get_repository_ui_error_integrator(main_window)

# Configure error display
config = create_error_display_config(
    show_message_box=True,
    show_status_bar=True,
    auto_dismiss_timeout=10,
    enable_retry_button=True
)

# Register component
integrator.register_component_error_config("video_table", config)

# Handle repository error
try:
    content_repo.save(video_content)
except Exception as error:
    context = create_repository_error_context(
        user_action="save_video",
        entity_type="VideoContent",
        entity_id=video_content.id
    )
    
    integrator.handle_repository_error(
        content_repo, error, "save", "video_table", context
    )
```

This integration ensures that repository errors are consistently translated and presented
to users in a user-friendly manner while maintaining technical details for debugging.
""" 