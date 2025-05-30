"""
Asynchronous Loading Patterns for Social Download Manager v2.0

Implements loading state management for asynchronous repository operations.
Provides patterns for handling async repository operations in Qt UI, loading indicators,
and mechanisms to prevent UI freezing during long-running repository tasks.

Utilizes Qt's threading capabilities to maintain UI responsiveness while performing
repository operations in background threads.
"""

from typing import Dict, Any, List, Optional, Callable, Union, TypeVar, Generic
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import logging
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from PyQt6.QtCore import (
    QObject, pyqtSignal, QThread, QTimer, QMutex, QWaitCondition,
    QRunnable, QThreadPool, QPropertyAnimation, QEasingCurve
)
from PyQt6.QtWidgets import (
    QWidget, QProgressBar, QLabel, QVBoxLayout, QHBoxLayout,
    QFrame, QGraphicsOpacityEffect, QStackedWidget
)
from PyQt6.QtGui import QMovie, QPainter, QPen, QColor
from PyQt6.QtCore import Qt, QRect, QSize

from data.models.repositories import IRepository, IContentRepository
from data.models.repository_interfaces import IDownloadRepository
from data.models.base import BaseEntity, EntityId
from core.event_system import EventBus, Event, EventType, get_event_bus, publish_event
from .repository_state_sync import get_repository_state_manager
from .repository_event_integration import get_repository_event_manager, RepositoryEventType

T = TypeVar('T', bound=BaseEntity)
R = TypeVar('R')  # Return type for repository operations


class LoadingState(Enum):
    """States for loading operations"""
    IDLE = "idle"
    LOADING = "loading"
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"


class LoadingPriority(Enum):
    """Priority levels for loading operations"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class LoadingOperation:
    """Represents a loading operation"""
    operation_id: str
    component_id: str
    repository_type: str
    operation_name: str
    priority: LoadingPriority
    state: LoadingState = LoadingState.IDLE
    progress: float = 0.0  # 0.0 to 1.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[Any] = None
    context: Optional[Dict[str, Any]] = None
    cancellable: bool = True
    timeout_seconds: Optional[int] = None


@dataclass
class LoadingConfig:
    """Configuration for loading behavior"""
    show_progress_bar: bool = True
    show_loading_text: bool = True
    show_cancel_button: bool = False
    show_spinner: bool = True
    overlay_ui: bool = False
    dim_background: bool = False
    minimum_display_time: int = 500  # milliseconds
    auto_hide_on_success: bool = True
    auto_hide_delay: int = 1000  # milliseconds
    theme_aware: bool = True
    animation_enabled: bool = True


class ILoadingIndicator(ABC):
    """Interface for loading indicators"""
    
    @abstractmethod
    def show_loading(self, operation: LoadingOperation, config: LoadingConfig) -> None:
        """Show loading indicator"""
        pass
    
    @abstractmethod
    def update_progress(self, operation_id: str, progress: float, message: Optional[str] = None) -> None:
        """Update loading progress"""
        pass
    
    @abstractmethod
    def hide_loading(self, operation_id: str) -> None:
        """Hide loading indicator"""
        pass
    
    @abstractmethod
    def show_error(self, operation_id: str, error_message: str) -> None:
        """Show error state"""
        pass


class RepositoryWorker(QObject):
    """Worker for executing repository operations in background thread"""
    
    # Signals for operation lifecycle
    operation_started = pyqtSignal(str)  # operation_id
    operation_progress = pyqtSignal(str, float, str)  # operation_id, progress, message
    operation_completed = pyqtSignal(str, object)  # operation_id, result
    operation_failed = pyqtSignal(str, str)  # operation_id, error_message
    operation_cancelled = pyqtSignal(str)  # operation_id
    
    def __init__(self):
        super().__init__()
        self._logger = logging.getLogger(__name__)
        self._cancelled_operations: set = set()
        self._mutex = QMutex()
    
    def execute_repository_operation(self, operation: LoadingOperation,
                                   repository: IRepository,
                                   operation_func: Callable,
                                   *args, **kwargs) -> None:
        """Execute repository operation with progress tracking"""
        operation_id = operation.operation_id
        
        try:
            # Check if operation was cancelled before starting
            with QMutex():
                if operation_id in self._cancelled_operations:
                    self.operation_cancelled.emit(operation_id)
                    return
            
            # Emit started signal
            self.operation_started.emit(operation_id)
            
            # Setup progress callback
            def progress_callback(progress: float, message: str = ""):
                # Check for cancellation
                with QMutex():
                    if operation_id in self._cancelled_operations:
                        raise InterruptedError("Operation cancelled")
                
                self.operation_progress.emit(operation_id, progress, message)
            
            # Add progress callback to kwargs if operation supports it
            if 'progress_callback' in operation_func.__code__.co_varnames:
                kwargs['progress_callback'] = progress_callback
            
            # Execute the operation
            result = operation_func(*args, **kwargs)
            
            # Check for cancellation after completion
            with QMutex():
                if operation_id in self._cancelled_operations:
                    self.operation_cancelled.emit(operation_id)
                    return
            
            # Emit completion signal
            self.operation_completed.emit(operation_id, result)
            
        except InterruptedError:
            self.operation_cancelled.emit(operation_id)
        except Exception as e:
            self._logger.error(f"Repository operation {operation_id} failed: {e}")
            self.operation_failed.emit(operation_id, str(e))
        finally:
            # Cleanup
            with QMutex():
                self._cancelled_operations.discard(operation_id)
    
    def cancel_operation(self, operation_id: str) -> None:
        """Cancel a running operation"""
        with QMutex():
            self._cancelled_operations.add(operation_id)


class QtLoadingIndicator(QWidget, ILoadingIndicator):
    """Qt-based loading indicator with progress bar and spinner"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._logger = logging.getLogger(__name__)
        
        # Active loading operations
        self._active_operations: Dict[str, LoadingOperation] = {}
        self._loading_widgets: Dict[str, QWidget] = {}
        
        # UI components
        self._setup_ui()
        
        # Animation support
        self._opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self._opacity_effect)
        self._fade_animation = QPropertyAnimation(self._opacity_effect, b"opacity")
        
        # Timer for minimum display time
        self._display_timers: Dict[str, QTimer] = {}
        
        # Initially hidden
        self.hide()
    
    def _setup_ui(self) -> None:
        """Setup the loading indicator UI"""
        self.setFixedSize(300, 100)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Background frame
        self.background_frame = QFrame()
        self.background_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(45, 45, 45, 200);
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 50);
            }
        """)
        layout.addWidget(self.background_frame)
        
        # Content layout
        content_layout = QVBoxLayout(self.background_frame)
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(8)
        
        # Loading text
        self.loading_label = QLabel("Loading...")
        self.loading_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.loading_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid rgba(255, 255, 255, 100);
                border-radius: 5px;
                text-align: center;
                background-color: rgba(255, 255, 255, 50);
                color: white;
            }
            QProgressBar::chunk {
                background-color: #0078d7;
                border-radius: 3px;
            }
        """)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        content_layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 180);
                font-size: 11px;
            }
        """)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.status_label)
    
    def show_loading(self, operation: LoadingOperation, config: LoadingConfig) -> None:
        """Show loading indicator for operation"""
        try:
            operation_id = operation.operation_id
            self._active_operations[operation_id] = operation
            
            # Update UI based on operation
            self.loading_label.setText(f"Loading {operation.operation_name}...")
            self.progress_bar.setValue(0)
            self.status_label.setText("")
            
            # Configure visibility based on config
            self.progress_bar.setVisible(config.show_progress_bar)
            self.loading_label.setVisible(config.show_loading_text)
            self.status_label.setVisible(True)
            
            # Apply theme if configured
            if config.theme_aware:
                self._apply_theme()
            
            # Position the widget
            self._position_widget()
            
            # Show with animation if enabled
            if config.animation_enabled:
                self._show_with_animation()
            else:
                self.show()
            
            # Setup minimum display timer
            if config.minimum_display_time > 0:
                timer = QTimer()
                timer.setSingleShot(True)
                timer.timeout.connect(lambda: self._enable_hide(operation_id))
                timer.start(config.minimum_display_time)
                self._display_timers[operation_id] = timer
            
            self._logger.debug(f"Showing loading indicator for operation: {operation_id}")
            
        except Exception as e:
            self._logger.error(f"Error showing loading indicator: {e}")
    
    def update_progress(self, operation_id: str, progress: float, message: Optional[str] = None) -> None:
        """Update loading progress"""
        try:
            if operation_id not in self._active_operations:
                return
            
            # Update progress bar
            progress_percent = int(progress * 100)
            self.progress_bar.setValue(progress_percent)
            
            # Update status message
            if message:
                self.status_label.setText(message)
            
            # Update operation record
            operation = self._active_operations[operation_id]
            operation.progress = progress
            
            self._logger.debug(f"Updated progress for {operation_id}: {progress_percent}%")
            
        except Exception as e:
            self._logger.error(f"Error updating progress: {e}")
    
    def hide_loading(self, operation_id: str) -> None:
        """Hide loading indicator"""
        try:
            if operation_id not in self._active_operations:
                return
            
            # Check if minimum display time has passed
            if operation_id in self._display_timers:
                timer = self._display_timers[operation_id]
                if timer.isActive():
                    # Schedule hide after timer completes
                    timer.timeout.connect(lambda: self._do_hide_loading(operation_id))
                    return
            
            self._do_hide_loading(operation_id)
            
        except Exception as e:
            self._logger.error(f"Error hiding loading indicator: {e}")
    
    def show_error(self, operation_id: str, error_message: str) -> None:
        """Show error state"""
        try:
            if operation_id not in self._active_operations:
                return
            
            # Update UI to show error
            self.loading_label.setText("Error occurred")
            self.status_label.setText(error_message)
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 2px solid rgba(255, 100, 100, 100);
                    border-radius: 5px;
                    text-align: center;
                    background-color: rgba(255, 100, 100, 50);
                    color: white;
                }
                QProgressBar::chunk {
                    background-color: #d73502;
                    border-radius: 3px;
                }
            """)
            
            # Auto-hide after delay
            QTimer.singleShot(3000, lambda: self.hide_loading(operation_id))
            
        except Exception as e:
            self._logger.error(f"Error showing error state: {e}")
    
    def _do_hide_loading(self, operation_id: str) -> None:
        """Actually hide the loading indicator"""
        # Cleanup operation
        if operation_id in self._active_operations:
            del self._active_operations[operation_id]
        
        if operation_id in self._display_timers:
            del self._display_timers[operation_id]
        
        # Hide if no more active operations
        if not self._active_operations:
            self._hide_with_animation()
    
    def _enable_hide(self, operation_id: str) -> None:
        """Enable hiding after minimum display time"""
        if operation_id in self._display_timers:
            del self._display_timers[operation_id]
    
    def _position_widget(self) -> None:
        """Position the loading widget in the center of parent"""
        if self.parent():
            parent_rect = self.parent().rect()
            self.move(
                parent_rect.center().x() - self.width() // 2,
                parent_rect.center().y() - self.height() // 2
            )
    
    def _apply_theme(self) -> None:
        """Apply current theme to the loading indicator"""
        # Theme detection and application would go here
        pass
    
    def _show_with_animation(self) -> None:
        """Show widget with fade-in animation"""
        self.show()
        self._fade_animation.setDuration(300)
        self._fade_animation.setStartValue(0.0)
        self._fade_animation.setEndValue(1.0)
        self._fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_animation.start()
    
    def _hide_with_animation(self) -> None:
        """Hide widget with fade-out animation"""
        self._fade_animation.setDuration(200)
        self._fade_animation.setStartValue(1.0)
        self._fade_animation.setEndValue(0.0)
        self._fade_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_animation.finished.connect(self.hide)
        self._fade_animation.start()


class AsyncRepositoryManager(QObject):
    """
    Manager for asynchronous repository operations
    
    Coordinates between repository operations, worker threads, and UI loading indicators
    to provide seamless async operation handling.
    """
    
    # Signals for async operation lifecycle
    operation_queued = pyqtSignal(str, str)  # operation_id, component_id
    operation_started = pyqtSignal(str, str)  # operation_id, component_id
    operation_progress = pyqtSignal(str, float, str)  # operation_id, progress, message
    operation_completed = pyqtSignal(str, object)  # operation_id, result
    operation_failed = pyqtSignal(str, str)  # operation_id, error_message
    operation_cancelled = pyqtSignal(str)  # operation_id
    
    def __init__(self, max_workers: int = 4):
        super().__init__()
        
        # Core components
        self._logger = logging.getLogger(__name__)
        self._thread_pool = QThreadPool()
        self._thread_pool.setMaxThreadCount(max_workers)
        
        # Operation management
        self._active_operations: Dict[str, LoadingOperation] = {}
        self._operation_queue: List[LoadingOperation] = []
        self._workers: Dict[str, RepositoryWorker] = {}
        self._worker_threads: Dict[str, QThread] = {}
        
        # Loading indicators
        self._loading_indicators: Dict[str, ILoadingIndicator] = {}
        self._default_loading_config = LoadingConfig()
        self._component_configs: Dict[str, LoadingConfig] = {}
        
        # Integration with other systems
        self._repository_state_manager = get_repository_state_manager()
        self._repository_event_manager = get_repository_event_manager()
        
        # Operation ID counter
        self._operation_counter = 0
        self._operation_lock = threading.Lock()
    
    def register_loading_indicator(self, component_id: str, indicator: ILoadingIndicator) -> None:
        """Register loading indicator for a component"""
        self._loading_indicators[component_id] = indicator
        self._logger.debug(f"Registered loading indicator for component: {component_id}")
    
    def register_loading_config(self, component_id: str, config: LoadingConfig) -> None:
        """Register loading configuration for a component"""
        self._component_configs[component_id] = config
        self._logger.debug(f"Registered loading config for component: {component_id}")
    
    def execute_async_operation(self, component_id: str, repository: IRepository,
                              operation_func: Callable, operation_name: str,
                              priority: LoadingPriority = LoadingPriority.NORMAL,
                              timeout_seconds: Optional[int] = None,
                              context: Optional[Dict[str, Any]] = None,
                              *args, **kwargs) -> str:
        """
        Execute repository operation asynchronously
        
        Args:
            component_id: UI component requesting the operation
            repository: Repository instance
            operation_func: Function to execute
            operation_name: Human-readable operation name
            priority: Operation priority
            timeout_seconds: Operation timeout
            context: Additional context
            *args, **kwargs: Arguments for operation_func
            
        Returns:
            Operation ID for tracking
        """
        try:
            # Generate operation ID
            with self._operation_lock:
                self._operation_counter += 1
                operation_id = f"{component_id}_{self._operation_counter}_{int(datetime.now().timestamp())}"
            
            # Create operation record
            operation = LoadingOperation(
                operation_id=operation_id,
                component_id=component_id,
                repository_type=repository.__class__.__name__,
                operation_name=operation_name,
                priority=priority,
                timeout_seconds=timeout_seconds,
                context=context
            )
            
            # Store operation
            self._active_operations[operation_id] = operation
            
            # Get loading configuration
            loading_config = self._component_configs.get(component_id, self._default_loading_config)
            
            # Show loading indicator
            if component_id in self._loading_indicators:
                indicator = self._loading_indicators[component_id]
                indicator.show_loading(operation, loading_config)
            
            # Create and configure worker
            worker = RepositoryWorker()
            worker_thread = QThread()
            
            # Move worker to thread
            worker.moveToThread(worker_thread)
            
            # Connect worker signals
            worker.operation_started.connect(self._handle_operation_started)
            worker.operation_progress.connect(self._handle_operation_progress)
            worker.operation_completed.connect(self._handle_operation_completed)
            worker.operation_failed.connect(self._handle_operation_failed)
            worker.operation_cancelled.connect(self._handle_operation_cancelled)
            
            # Connect thread signals
            worker_thread.started.connect(
                lambda: worker.execute_repository_operation(
                    operation, repository, operation_func, *args, **kwargs
                )
            )
            worker_thread.finished.connect(worker_thread.deleteLater)
            worker_thread.finished.connect(worker.deleteLater)
            
            # Store worker and thread
            self._workers[operation_id] = worker
            self._worker_threads[operation_id] = worker_thread
            
            # Start operation
            operation.start_time = datetime.now()
            operation.state = LoadingState.LOADING
            worker_thread.start()
            
            # Emit queued signal
            self.operation_queued.emit(operation_id, component_id)
            
            # Setup timeout if specified
            if timeout_seconds:
                QTimer.singleShot(
                    timeout_seconds * 1000,
                    lambda: self.cancel_operation(operation_id)
                )
            
            self._logger.info(f"Started async operation: {operation_id} ({operation_name})")
            
            return operation_id
            
        except Exception as e:
            self._logger.error(f"Error starting async operation: {e}")
            raise
    
    def cancel_operation(self, operation_id: str) -> bool:
        """Cancel a running operation"""
        try:
            if operation_id not in self._active_operations:
                return False
            
            operation = self._active_operations[operation_id]
            
            if not operation.cancellable:
                self._logger.warning(f"Operation {operation_id} is not cancellable")
                return False
            
            # Cancel worker
            if operation_id in self._workers:
                worker = self._workers[operation_id]
                worker.cancel_operation(operation_id)
            
            # Stop thread
            if operation_id in self._worker_threads:
                thread = self._worker_threads[operation_id]
                thread.quit()
                thread.wait(5000)  # Wait up to 5 seconds
            
            # Update operation state
            operation.state = LoadingState.CANCELLED
            operation.end_time = datetime.now()
            
            self._logger.info(f"Cancelled operation: {operation_id}")
            return True
            
        except Exception as e:
            self._logger.error(f"Error cancelling operation {operation_id}: {e}")
            return False
    
    def get_operation_status(self, operation_id: str) -> Optional[LoadingOperation]:
        """Get status of an operation"""
        return self._active_operations.get(operation_id)
    
    def get_active_operations(self, component_id: Optional[str] = None) -> List[LoadingOperation]:
        """Get list of active operations, optionally filtered by component"""
        operations = list(self._active_operations.values())
        
        if component_id:
            operations = [op for op in operations if op.component_id == component_id]
        
        return operations
    
    # Signal handlers
    def _handle_operation_started(self, operation_id: str) -> None:
        """Handle operation started signal"""
        if operation_id in self._active_operations:
            operation = self._active_operations[operation_id]
            self.operation_started.emit(operation_id, operation.component_id)
    
    def _handle_operation_progress(self, operation_id: str, progress: float, message: str) -> None:
        """Handle operation progress signal"""
        if operation_id in self._active_operations:
            operation = self._active_operations[operation_id]
            operation.progress = progress
            
            # Update loading indicator
            component_id = operation.component_id
            if component_id in self._loading_indicators:
                indicator = self._loading_indicators[component_id]
                indicator.update_progress(operation_id, progress, message)
            
            self.operation_progress.emit(operation_id, progress, message)
    
    def _handle_operation_completed(self, operation_id: str, result: Any) -> None:
        """Handle operation completed signal"""
        try:
            if operation_id not in self._active_operations:
                return
            
            operation = self._active_operations[operation_id]
            operation.state = LoadingState.SUCCESS
            operation.end_time = datetime.now()
            operation.result = result
            
            # Hide loading indicator
            component_id = operation.component_id
            if component_id in self._loading_indicators:
                indicator = self._loading_indicators[component_id]
                indicator.hide_loading(operation_id)
            
            # Emit completion signal
            self.operation_completed.emit(operation_id, result)
            
            # Cleanup
            self._cleanup_operation(operation_id)
            
            self._logger.info(f"Completed operation: {operation_id}")
            
        except Exception as e:
            self._logger.error(f"Error handling operation completion: {e}")
    
    def _handle_operation_failed(self, operation_id: str, error_message: str) -> None:
        """Handle operation failed signal"""
        try:
            if operation_id not in self._active_operations:
                return
            
            operation = self._active_operations[operation_id]
            operation.state = LoadingState.ERROR
            operation.end_time = datetime.now()
            operation.error_message = error_message
            
            # Show error in loading indicator
            component_id = operation.component_id
            if component_id in self._loading_indicators:
                indicator = self._loading_indicators[component_id]
                indicator.show_error(operation_id, error_message)
            
            # Emit failure signal
            self.operation_failed.emit(operation_id, error_message)
            
            # Cleanup
            self._cleanup_operation(operation_id)
            
            self._logger.error(f"Operation failed: {operation_id} - {error_message}")
            
        except Exception as e:
            self._logger.error(f"Error handling operation failure: {e}")
    
    def _handle_operation_cancelled(self, operation_id: str) -> None:
        """Handle operation cancelled signal"""
        try:
            if operation_id not in self._active_operations:
                return
            
            operation = self._active_operations[operation_id]
            operation.state = LoadingState.CANCELLED
            operation.end_time = datetime.now()
            
            # Hide loading indicator
            component_id = operation.component_id
            if component_id in self._loading_indicators:
                indicator = self._loading_indicators[component_id]
                indicator.hide_loading(operation_id)
            
            # Emit cancellation signal
            self.operation_cancelled.emit(operation_id)
            
            # Cleanup
            self._cleanup_operation(operation_id)
            
            self._logger.info(f"Operation cancelled: {operation_id}")
            
        except Exception as e:
            self._logger.error(f"Error handling operation cancellation: {e}")
    
    def _cleanup_operation(self, operation_id: str) -> None:
        """Cleanup operation resources"""
        # Remove from active operations
        if operation_id in self._active_operations:
            del self._active_operations[operation_id]
        
        # Cleanup worker and thread
        if operation_id in self._workers:
            del self._workers[operation_id]
        
        if operation_id in self._worker_threads:
            del self._worker_threads[operation_id]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get async operation statistics"""
        active_ops = list(self._active_operations.values())
        
        return {
            'active_operations': len(active_ops),
            'thread_pool_active_threads': self._thread_pool.activeThreadCount(),
            'thread_pool_max_threads': self._thread_pool.maxThreadCount(),
            'operations_by_state': {
                state.value: sum(1 for op in active_ops if op.state == state)
                for state in LoadingState
            },
            'operations_by_component': {
                comp_id: sum(1 for op in active_ops if op.component_id == comp_id)
                for comp_id in set(op.component_id for op in active_ops)
            },
            'registered_indicators': len(self._loading_indicators),
            'registered_configs': len(self._component_configs)
        }


# Global async repository manager instance
_async_repository_manager: Optional[AsyncRepositoryManager] = None


def get_async_repository_manager() -> AsyncRepositoryManager:
    """Get the global async repository manager instance"""
    global _async_repository_manager
    if _async_repository_manager is None:
        _async_repository_manager = AsyncRepositoryManager()
    return _async_repository_manager


def execute_async_repository_operation(component_id: str, repository: IRepository,
                                     operation_func: Callable, operation_name: str,
                                     **kwargs) -> str:
    """Convenience function to execute async repository operation"""
    manager = get_async_repository_manager()
    return manager.execute_async_operation(
        component_id, repository, operation_func, operation_name, **kwargs
    )


def register_component_loading(component_id: str, indicator: ILoadingIndicator,
                             config: Optional[LoadingConfig] = None) -> None:
    """Convenience function to register component loading"""
    manager = get_async_repository_manager()
    manager.register_loading_indicator(component_id, indicator)
    
    if config:
        manager.register_loading_config(component_id, config)


# =============================================================================
# Utility Functions and Helpers
# =============================================================================

def create_loading_config(show_progress_bar: bool = True,
                         show_loading_text: bool = True,
                         show_cancel_button: bool = False,
                         minimum_display_time: int = 500,
                         **kwargs) -> LoadingConfig:
    """Create loading configuration"""
    return LoadingConfig(
        show_progress_bar=show_progress_bar,
        show_loading_text=show_loading_text,
        show_cancel_button=show_cancel_button,
        minimum_display_time=minimum_display_time,
        **kwargs
    )


def create_qt_loading_indicator(parent: QWidget) -> QtLoadingIndicator:
    """Create Qt loading indicator"""
    return QtLoadingIndicator(parent)


# =============================================================================
# Documentation and Usage Examples
# =============================================================================

"""
Asynchronous Loading Patterns Implementation Guide

This module provides comprehensive async loading patterns for repository operations:

1. **Loading State Management**:
   - LoadingState enum for operation lifecycle tracking
   - LoadingOperation dataclass for operation metadata
   - Progress tracking with real-time updates

2. **Qt Threading Integration**:
   - RepositoryWorker for background operation execution
   - QThread-based operation isolation
   - Thread pool management for concurrent operations

3. **UI Loading Indicators**:
   - ILoadingIndicator interface for custom indicators
   - QtLoadingIndicator with progress bars and animations
   - Theme-aware styling and positioning

4. **Async Operation Management**:
   - AsyncRepositoryManager for centralized coordination
   - Operation queuing and priority handling
   - Timeout and cancellation support

Usage Example:

```python
from core.data_integration.async_loading_patterns import (
    get_async_repository_manager, create_qt_loading_indicator,
    create_loading_config, LoadingPriority
)

# Setup async loading for a component
async_manager = get_async_repository_manager()

# Create and register loading indicator
loading_indicator = create_qt_loading_indicator(video_table)
loading_config = create_loading_config(
    show_progress_bar=True,
    show_cancel_button=True,
    minimum_display_time=500
)

async_manager.register_loading_indicator("video_table", loading_indicator)
async_manager.register_loading_config("video_table", loading_config)

# Execute async repository operation
def load_videos_with_progress(progress_callback=None):
    videos = []
    total = 100
    
    for i in range(total):
        # Simulate work
        time.sleep(0.01)
        
        # Report progress
        if progress_callback:
            progress_callback(i / total, f"Loading video {i+1}/{total}")
        
        videos.append(f"video_{i}")
    
    return videos

# Start async operation
operation_id = async_manager.execute_async_operation(
    component_id="video_table",
    repository=content_repository,
    operation_func=load_videos_with_progress,
    operation_name="Load Videos",
    priority=LoadingPriority.HIGH,
    timeout_seconds=30
)

# Handle completion
def on_operation_completed(op_id, result):
    if op_id == operation_id:
        print(f"Loaded {len(result)} videos")

async_manager.operation_completed.connect(on_operation_completed)
```

This system ensures that all repository operations are performed asynchronously
without blocking the UI, while providing clear visual feedback to users.
""" 