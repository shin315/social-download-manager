"""
MainWindow Adapter for UI v1.2.1 to v2.0 Architecture Bridge

This module contains the adapter implementation that bridges the legacy MainWindow
component with the new v2.0 architecture systems (App Controller, Event System,
Repository Layer), maintaining the familiar UI while leveraging modern architecture.
"""

import logging
import weakref
from typing import Any, Dict, List, Optional, Callable, Set
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer
from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtGui import QAction

# Import v2.0 architecture components
from core.app_controller import AppController
from core.event_system import EventBus, EventType, Event
from data.repositories.base_repository import IRepository

# Import adapter interfaces and components
from .interfaces import (
    IMainWindowAdapter, AdapterState, AdapterConfig, AdapterMetrics,
    AdapterPriority
)
from .event_proxy import (
    EventBridgeCoordinator, EventTranslator, LegacyEventHandler,
    get_global_coordinator
)
from .data_mappers import get_config_mapper


class MainWindowAdapterError(Exception):
    """Exception raised by MainWindow adapter operations"""
    pass


class MainWindowAdapter(QObject, IMainWindowAdapter):
    """
    Adapter that bridges the legacy MainWindow with v2.0 architecture systems.
    
    This adapter maintains the existing MainWindow UI and behavior while
    connecting it to the App Controller, Event System, and Repository Layer
    for improved performance and maintainability.
    """
    
    # Signals for adapter events
    adapter_initialized = pyqtSignal()
    adapter_error = pyqtSignal(str, str)  # error_type, error_message
    theme_change_requested = pyqtSignal(str)  # theme_name
    language_change_requested = pyqtSignal(str)  # language_code
    output_folder_changed = pyqtSignal(str)  # folder_path
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Core adapter state
        self._state = AdapterState.UNINITIALIZED
        self._config = AdapterConfig()
        self._metrics = AdapterMetrics()
        
        # v2.0 architecture components
        self._app_controller: Optional[AppController] = None
        self._event_bus: Optional[EventBus] = None
        self._event_translator: Optional[EventTranslator] = None
        self._legacy_handler: Optional[LegacyEventHandler] = None
        
        # Legacy component reference
        self._main_window: Optional[QMainWindow] = None
        self._main_window_ref: Optional[weakref.ReferenceType] = None
        
        # Configuration and state management
        self._config_mapper = get_config_mapper()
        self._original_methods: Dict[str, Callable] = {}
        self._proxy_connections: List[Any] = []
        
        # Feature flags and preferences
        self._feature_flags = {
            "use_v2_config_management": True,
            "use_v2_theme_system": True,
            "use_v2_language_system": True,
            "enable_event_bridging": True,
            "enable_performance_monitoring": True
        }
        
        # Performance monitoring
        self._start_time: Optional[datetime] = None
        self._method_call_counts: Dict[str, int] = {}
        self._last_error: Optional[str] = None
        
        # Status tracking
        self._initialization_attempts = 0
        self._max_initialization_attempts = 3
        
        self.logger.debug("MainWindow adapter created")
    
    def initialize(self, 
                  app_controller: AppController,
                  event_bus: EventBus,
                  config: AdapterConfig) -> bool:
        """
        Initialize the adapter with v2.0 architecture components.
        
        Args:
            app_controller: The v2.0 App Controller instance
            event_bus: The v2.0 Event Bus instance
            config: Adapter configuration
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            self._initialization_attempts += 1
            self._state = AdapterState.INITIALIZING
            self._start_time = datetime.now()
            
            # Store v2.0 components
            self._app_controller = app_controller
            self._event_bus = event_bus
            self._config = config
            
            # Initialize event system integration
            if not self._initialize_event_system():
                raise MainWindowAdapterError("Failed to initialize event system integration")
            
            # Set up performance monitoring if enabled
            if self._config.performance_monitoring:
                self._setup_performance_monitoring()
            
            self._state = AdapterState.ACTIVE
            self.logger.info("MainWindow adapter initialized successfully")
            self.adapter_initialized.emit()
            return True
            
        except Exception as e:
            self._state = AdapterState.ERROR
            self._last_error = str(e)
            self.logger.error(f"Failed to initialize MainWindow adapter: {e}")
            self.adapter_error.emit("initialization", str(e))
            
            # Retry logic
            if self._initialization_attempts < self._max_initialization_attempts:
                self.logger.info(f"Retrying initialization (attempt {self._initialization_attempts + 1})")
                QTimer.singleShot(1000, lambda: self.initialize(app_controller, event_bus, config))
            
            return False
    
    def attach_component(self, component: QObject) -> bool:
        """
        Attach the legacy MainWindow component to this adapter.
        
        Args:
            component: The legacy MainWindow instance
            
        Returns:
            True if attachment successful, False otherwise
        """
        try:
            if not isinstance(component, QMainWindow):
                raise MainWindowAdapterError(f"Expected QMainWindow, got {type(component)}")
            
            self._main_window = component
            self._main_window_ref = weakref.ref(component)
            
            # Set up method proxying for key MainWindow methods
            if not self._setup_method_proxying():
                raise MainWindowAdapterError("Failed to set up method proxying")
            
            # Set up signal connections for events
            if not self._setup_signal_connections():
                raise MainWindowAdapterError("Failed to set up signal connections")
            
            # Set up menu and status bar integration
            if not self.setup_menu_integration():
                raise MainWindowAdapterError("Failed to set up menu integration")
            
            if not self.setup_status_bar_integration():
                raise MainWindowAdapterError("Failed to set up status bar integration")
            
            # Load and apply configuration
            if self._feature_flags["use_v2_config_management"]:
                self._apply_v2_configuration()
            
            self.logger.info("MainWindow component attached successfully")
            return True
            
        except Exception as e:
            self._last_error = str(e)
            self.logger.error(f"Failed to attach MainWindow component: {e}")
            self.adapter_error.emit("attachment", str(e))
            return False
    
    def detach_component(self) -> bool:
        """
        Detach the legacy MainWindow component from this adapter.
        
        Returns:
            True if detachment successful, False otherwise
        """
        try:
            if self._main_window:
                # Restore original methods
                self._restore_original_methods()
                
                # Disconnect signals
                self._disconnect_signals()
                
                # Clear references
                self._main_window = None
                self._main_window_ref = None
            
            self.logger.info("MainWindow component detached successfully")
            return True
            
        except Exception as e:
            self._last_error = str(e)
            self.logger.error(f"Failed to detach MainWindow component: {e}")
            self.adapter_error.emit("detachment", str(e))
            return False
    
    def update(self, data: Dict[str, Any]) -> bool:
        """
        Update the adapter with new data or state.
        
        Args:
            data: Data to update the adapter with
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            # Update configuration if provided
            if "config" in data:
                config_data = data["config"]
                if self._config_mapper.validate_v2_data(config_data):
                    self._apply_configuration_update(config_data)
            
            # Update feature flags if provided
            if "feature_flags" in data:
                self._feature_flags.update(data["feature_flags"])
                self.logger.debug(f"Updated feature flags: {data['feature_flags']}")
            
            # Update metrics if provided
            if "metrics" in data:
                metrics_data = data["metrics"]
                self._metrics.events_processed += metrics_data.get("events_processed", 0)
                self._metrics.events_failed += metrics_data.get("events_failed", 0)
            
            return True
            
        except Exception as e:
            self._last_error = str(e)
            self.logger.error(f"Failed to update adapter: {e}")
            self.adapter_error.emit("update", str(e))
            return False
    
    def shutdown(self) -> bool:
        """
        Shutdown the adapter gracefully.
        
        Returns:
            True if shutdown successful, False otherwise
        """
        try:
            self._state = AdapterState.SHUTTING_DOWN
            
            # Detach component
            self.detach_component()
            
            # Clean up event system
            if self._event_translator:
                self._event_translator.cleanup()
            
            if self._legacy_handler:
                self._legacy_handler.disconnect_all()
            
            # Clean up references
            self._app_controller = None
            self._event_bus = None
            self._event_translator = None
            self._legacy_handler = None
            
            self._state = AdapterState.TERMINATED
            self.logger.info("MainWindow adapter shutdown successfully")
            return True
            
        except Exception as e:
            self._state = AdapterState.ERROR
            self._last_error = str(e)
            self.logger.error(f"Failed to shutdown adapter: {e}")
            self.adapter_error.emit("shutdown", str(e))
            return False
    
    def get_state(self) -> AdapterState:
        """Get the current state of the adapter."""
        return self._state
    
    def get_metrics(self) -> AdapterMetrics:
        """Get performance metrics for the adapter."""
        if self._start_time:
            self._metrics.uptime_seconds = int((datetime.now() - self._start_time).total_seconds())
        
        self._metrics.last_error = self._last_error
        self._metrics.memory_usage_mb = self._get_memory_usage()
        
        return self._metrics
    
    def handle_error(self, error: Exception, context: str) -> bool:
        """
        Handle errors that occur in the adapter.
        
        Args:
            error: The exception that occurred
            context: Context information about where the error occurred
            
        Returns:
            True if error was handled successfully, False otherwise
        """
        try:
            self._last_error = f"{context}: {str(error)}"
            self._metrics.events_failed += 1
            
            self.logger.error(f"Adapter error in {context}: {error}")
            self.adapter_error.emit(context, str(error))
            
            # Implement error recovery strategies
            if "initialization" in context and self._initialization_attempts < self._max_initialization_attempts:
                self.logger.info("Attempting error recovery through reinitialization")
                return True
            
            # For other errors, try to maintain functionality
            if self._config.enable_fallback:
                self.logger.info("Enabling fallback mode due to error")
                self._enable_fallback_mode()
                return True
            
            return False
            
        except Exception as e:
            self.logger.critical(f"Failed to handle error: {e}")
            return False
    
    def setup_menu_integration(self) -> bool:
        """
        Set up integration between MainWindow menus and v2.0 systems.
        
        Returns:
            True if setup successful, False otherwise
        """
        try:
            if not self._main_window:
                return False
            
            # Get menu bar
            menu_bar = self._main_window.menuBar()
            if not menu_bar:
                return False
            
            # Hook into theme menu actions
            if self._feature_flags["use_v2_theme_system"]:
                self._setup_theme_menu_integration(menu_bar)
            
            # Hook into language menu actions
            if self._feature_flags["use_v2_language_system"]:
                self._setup_language_menu_integration(menu_bar)
            
            # Hook into file menu actions
            self._setup_file_menu_integration(menu_bar)
            
            self.logger.debug("Menu integration set up successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set up menu integration: {e}")
            return False
    
    def setup_status_bar_integration(self) -> bool:
        """
        Set up integration between status bar and v2.0 event system.
        
        Returns:
            True if setup successful, False otherwise
        """
        try:
            if not self._main_window or not self._event_translator:
                return False
            
            status_bar = self._main_window.statusBar()
            if not status_bar:
                return False
            
            # Register for status update events
            self._event_translator.register_v2_handler(
                EventType.STATUS_UPDATED,
                self._handle_status_update
            )
            
            self._event_translator.register_v2_handler(
                EventType.DOWNLOAD_PROGRESS_UPDATED,
                self._handle_download_progress_status
            )
            
            self._event_translator.register_v2_handler(
                EventType.ERROR_OCCURRED,
                self._handle_error_status
            )
            
            self.logger.debug("Status bar integration set up successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set up status bar integration: {e}")
            return False
    
    def handle_theme_change(self, theme: str) -> bool:
        """
        Handle theme changes through the v2.0 configuration system.
        
        Args:
            theme: Theme name (e.g., "dark", "light")
            
        Returns:
            True if theme change handled successfully, False otherwise
        """
        try:
            if not self._app_controller:
                # Fallback to direct theme change
                if hasattr(self._main_window, 'set_theme'):
                    self._main_window.set_theme(theme)
                return True
            
            # Use v2.0 configuration system
            config_update = {
                "app": {
                    "theme": theme
                }
            }
            
            # Emit configuration update event
            if self._event_translator:
                self._event_translator.emit_v2_event(
                    EventType.CONFIGURATION_UPDATED,
                    config_update
                )
            
            # Also emit legacy event for backward compatibility
            self.theme_change_requested.emit(theme)
            
            self.logger.debug(f"Theme change handled: {theme}")
            self._method_call_counts["handle_theme_change"] = self._method_call_counts.get("handle_theme_change", 0) + 1
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to handle theme change: {e}")
            return False
    
    def handle_language_change(self, language: str) -> bool:
        """
        Handle language changes through the v2.0 configuration system.
        
        Args:
            language: Language code (e.g., "en", "vi")
            
        Returns:
            True if language change handled successfully, False otherwise
        """
        try:
            if not self._app_controller:
                # Fallback to direct language change
                if hasattr(self._main_window, 'set_language'):
                    self._main_window.set_language(language)
                return True
            
            # Use v2.0 configuration system
            config_update = {
                "app": {
                    "language": language
                }
            }
            
            # Emit configuration update event
            if self._event_translator:
                self._event_translator.emit_v2_event(
                    EventType.CONFIGURATION_UPDATED,
                    config_update
                )
            
            # Also emit legacy event for backward compatibility
            self.language_change_requested.emit(language)
            
            self.logger.debug(f"Language change handled: {language}")
            self._method_call_counts["handle_language_change"] = self._method_call_counts.get("handle_language_change", 0) + 1
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to handle language change: {e}")
            return False
    
    def _initialize_event_system(self) -> bool:
        """Initialize event system integration"""
        try:
            if not self._feature_flags["enable_event_bridging"]:
                return True
            
            # Get global event bridge coordinator
            coordinator = get_global_coordinator()
            
            # Initialize coordinator with v2.0 event bus
            if not coordinator.initialize(self._event_bus):
                raise MainWindowAdapterError("Failed to initialize event bridge coordinator")
            
            # Create event translator
            self._event_translator = EventTranslator(coordinator)
            
            # Create legacy event handler
            self._legacy_handler = LegacyEventHandler(coordinator)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize event system: {e}")
            return False
    
    def _setup_method_proxying(self) -> bool:
        """Set up method proxying for key MainWindow methods"""
        try:
            if not self._main_window:
                return False
            
            # Methods to proxy for v2.0 integration
            methods_to_proxy = [
                'set_theme',
                'set_language',
                'set_output_folder',
                'save_config',
                'load_config'
            ]
            
            for method_name in methods_to_proxy:
                if hasattr(self._main_window, method_name):
                    original_method = getattr(self._main_window, method_name)
                    self._original_methods[method_name] = original_method
                    
                    # Create proxy method
                    proxy_method = self._create_proxy_method(method_name, original_method)
                    setattr(self._main_window, method_name, proxy_method)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set up method proxying: {e}")
            return False
    
    def _create_proxy_method(self, method_name: str, original_method: Callable) -> Callable:
        """Create a proxy method that adds v2.0 integration"""
        def proxy_method(*args, **kwargs):
            try:
                # Track method calls
                self._method_call_counts[method_name] = self._method_call_counts.get(method_name, 0) + 1
                
                # Pre-processing for specific methods
                if method_name == 'set_theme' and args:
                    theme = args[0]
                    self.handle_theme_change(theme)
                elif method_name == 'set_language' and args:
                    language = args[0]
                    self.handle_language_change(language)
                elif method_name == 'set_output_folder' and args:
                    folder = args[0]
                    self._handle_output_folder_change(folder)
                
                # Call original method
                result = original_method(*args, **kwargs)
                
                # Post-processing
                if self._config.log_events:
                    self.logger.debug(f"Proxied method call: {method_name} with args: {args}")
                
                return result
                
            except Exception as e:
                self.logger.error(f"Error in proxy method {method_name}: {e}")
                self.handle_error(e, f"proxy_method_{method_name}")
                return None
        
        return proxy_method
    
    def _setup_signal_connections(self) -> bool:
        """Set up signal connections for legacy events"""
        try:
            if not self._main_window or not self._legacy_handler:
                return False
            
            # Connect theme change signal if available
            if hasattr(self._main_window, 'theme_change_requested'):
                self._legacy_handler.connect_signal(
                    self._main_window.theme_change_requested,
                    "theme_changed",
                    lambda theme: theme
                )
            
            # Connect language change signal if available
            if hasattr(self._main_window, 'language_changed'):
                self._legacy_handler.connect_signal(
                    self._main_window.language_changed,
                    "language_changed"
                )
            
            # Connect output folder change signal if available
            if hasattr(self._main_window, 'output_folder_changed'):
                self._legacy_handler.connect_signal(
                    self._main_window.output_folder_changed,
                    "output_folder_changed",
                    lambda folder: folder
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set up signal connections: {e}")
            return False
    
    def _setup_theme_menu_integration(self, menu_bar) -> None:
        """Set up theme menu integration with v2.0 theme system"""
        # Find theme/appearance menu
        for action in menu_bar.actions():
            menu = action.menu()
            if menu and "appearance" in action.text().lower():
                for theme_action in menu.actions():
                    if theme_action.isCheckable():
                        # Override action trigger to use v2.0 system
                        theme_action.triggered.disconnect()  # Disconnect existing handlers
                        theme_name = "light" if "light" in theme_action.text().lower() else "dark"
                        theme_action.triggered.connect(lambda checked, theme=theme_name: self.handle_theme_change(theme))
    
    def _setup_language_menu_integration(self, menu_bar) -> None:
        """Set up language menu integration with v2.0 language system"""
        # Find language menu
        for action in menu_bar.actions():
            menu = action.menu()
            if menu and "language" in action.text().lower():
                for lang_action in menu.actions():
                    if lang_action.isCheckable():
                        # Override action trigger to use v2.0 system
                        lang_action.triggered.disconnect()  # Disconnect existing handlers
                        lang_code = lang_action.data() if lang_action.data() else "en"
                        lang_action.triggered.connect(lambda checked, lang=lang_code: self.handle_language_change(lang))
    
    def _setup_file_menu_integration(self, menu_bar) -> None:
        """Set up file menu integration with v2.0 systems"""
        # Find file menu
        for action in menu_bar.actions():
            menu = action.menu()
            if menu and "file" in action.text().lower():
                for file_action in menu.actions():
                    if "folder" in file_action.text().lower():
                        # Add event emission for output folder changes
                        original_trigger = file_action.triggered
                        def enhanced_trigger(checked):
                            original_trigger.emit(checked)
                            # Emit v2.0 event if folder changed
                            if hasattr(self._main_window, 'output_folder'):
                                self._handle_output_folder_change(self._main_window.output_folder)
                        
                        file_action.triggered.disconnect()
                        file_action.triggered.connect(enhanced_trigger)
    
    def _handle_output_folder_change(self, folder: str) -> None:
        """Handle output folder change through v2.0 system"""
        try:
            if self._event_translator:
                config_update = {
                    "download": {
                        "output_folder": folder
                    }
                }
                self._event_translator.emit_v2_event(
                    EventType.CONFIGURATION_UPDATED,
                    config_update
                )
            
            self.output_folder_changed.emit(folder)
            
        except Exception as e:
            self.logger.error(f"Failed to handle output folder change: {e}")
    
    def _handle_status_update(self, event_data: Any) -> None:
        """Handle status update events from v2.0 system"""
        try:
            if self._main_window and hasattr(self._main_window, 'status_bar'):
                status_bar = self._main_window.status_bar
                if status_bar and isinstance(event_data, dict):
                    message = event_data.get('message', str(event_data))
                    status_bar.showMessage(message)
                    
        except Exception as e:
            self.logger.error(f"Failed to handle status update: {e}")
    
    def _handle_download_progress_status(self, event_data: Any) -> None:
        """Handle download progress status updates"""
        try:
            if self._main_window and hasattr(self._main_window, 'status_bar'):
                status_bar = self._main_window.status_bar
                if status_bar and isinstance(event_data, dict):
                    progress = event_data.get('progress', 0)
                    message = f"Download progress: {progress}%"
                    status_bar.showMessage(message)
                    
        except Exception as e:
            self.logger.error(f"Failed to handle download progress status: {e}")
    
    def _handle_error_status(self, event_data: Any) -> None:
        """Handle error status updates"""
        try:
            if self._main_window and hasattr(self._main_window, 'status_bar'):
                status_bar = self._main_window.status_bar
                if status_bar and isinstance(event_data, dict):
                    error_message = event_data.get('message', 'An error occurred')
                    status_bar.showMessage(f"Error: {error_message}")
                    
        except Exception as e:
            self.logger.error(f"Failed to handle error status: {e}")
    
    def _apply_v2_configuration(self) -> None:
        """Apply configuration from v2.0 configuration system"""
        try:
            if not self._app_controller:
                return
            
            # Get configuration from v2.0 system
            config = self._app_controller.get_configuration()
            if config:
                # Apply theme
                theme = config.get("app", {}).get("theme", "dark")
                if hasattr(self._main_window, 'set_theme'):
                    self._main_window.set_theme(theme)
                
                # Apply language
                language = config.get("app", {}).get("language", "en")
                if hasattr(self._main_window, 'set_language'):
                    self._main_window.set_language(language)
                
                # Apply output folder
                output_folder = config.get("download", {}).get("output_folder", "")
                if output_folder and hasattr(self._main_window, 'output_folder'):
                    self._main_window.output_folder = output_folder
                    
        except Exception as e:
            self.logger.error(f"Failed to apply v2.0 configuration: {e}")
    
    def _apply_configuration_update(self, config_data: Dict[str, Any]) -> None:
        """Apply a configuration update"""
        try:
            app_config = config_data.get("app", {})
            
            # Handle theme updates
            if "theme" in app_config:
                theme = app_config["theme"]
                if hasattr(self._main_window, 'set_theme'):
                    self._main_window.set_theme(theme)
            
            # Handle language updates
            if "language" in app_config:
                language = app_config["language"]
                if hasattr(self._main_window, 'set_language'):
                    self._main_window.set_language(language)
            
            # Handle download config updates
            download_config = config_data.get("download", {})
            if "output_folder" in download_config:
                folder = download_config["output_folder"]
                if hasattr(self._main_window, 'output_folder'):
                    self._main_window.output_folder = folder
                    
        except Exception as e:
            self.logger.error(f"Failed to apply configuration update: {e}")
    
    def _setup_performance_monitoring(self) -> None:
        """Set up performance monitoring"""
        try:
            if not self._config.performance_monitoring:
                return
            
            # Create timer for periodic metrics collection
            self._metrics_timer = QTimer()
            self._metrics_timer.timeout.connect(self._collect_metrics)
            self._metrics_timer.start(5000)  # Collect every 5 seconds
            
        except Exception as e:
            self.logger.error(f"Failed to set up performance monitoring: {e}")
    
    def _collect_metrics(self) -> None:
        """Collect performance metrics"""
        try:
            # Update uptime
            if self._start_time:
                uptime = (datetime.now() - self._start_time).total_seconds()
                self._metrics.uptime_seconds = int(uptime)
            
            # Update memory usage
            self._metrics.memory_usage_mb = self._get_memory_usage()
            
            # Calculate average response time (simplified)
            total_calls = sum(self._method_call_counts.values())
            if total_calls > 0:
                self._metrics.average_response_time_ms = uptime * 1000 / total_calls
                
        except Exception as e:
            self.logger.error(f"Failed to collect metrics: {e}")
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0
        except Exception:
            return 0.0
    
    def _enable_fallback_mode(self) -> None:
        """Enable fallback mode for error recovery"""
        try:
            # Disable v2.0 features and fall back to legacy behavior
            self._feature_flags["use_v2_config_management"] = False
            self._feature_flags["use_v2_theme_system"] = False
            self._feature_flags["use_v2_language_system"] = False
            self._feature_flags["enable_event_bridging"] = False
            
            self.logger.warning("Fallback mode enabled due to errors")
            
        except Exception as e:
            self.logger.error(f"Failed to enable fallback mode: {e}")
    
    def _restore_original_methods(self) -> None:
        """Restore original methods that were proxied"""
        try:
            for method_name, original_method in self._original_methods.items():
                if self._main_window and hasattr(self._main_window, method_name):
                    setattr(self._main_window, method_name, original_method)
            
            self._original_methods.clear()
            
        except Exception as e:
            self.logger.error(f"Failed to restore original methods: {e}")
    
    def _disconnect_signals(self) -> None:
        """Disconnect all signal connections"""
        try:
            for connection in self._proxy_connections:
                try:
                    connection.disconnect()
                except Exception:
                    pass  # Connection might already be disconnected
            
            self._proxy_connections.clear()
            
        except Exception as e:
            self.logger.error(f"Failed to disconnect signals: {e}")


# Factory function for easy adapter creation
def create_main_window_adapter() -> MainWindowAdapter:
    """Create a MainWindow adapter instance"""
    return MainWindowAdapter()


# Global adapter instance
_global_main_window_adapter: Optional[MainWindowAdapter] = None


def get_global_main_window_adapter() -> MainWindowAdapter:
    """Get the global MainWindow adapter instance"""
    global _global_main_window_adapter
    if _global_main_window_adapter is None:
        _global_main_window_adapter = MainWindowAdapter()
    return _global_main_window_adapter 