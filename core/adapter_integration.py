"""
Adapter Integration Framework for Social Download Manager v2.0

This module provides the integration framework for connecting Task 29 UI adapters
with the v2.0 architecture. It manages adapter lifecycle, fallback mechanisms,
performance monitoring, and provides a clean interface for the main entry point.
"""

import logging
import threading
import weakref
from typing import Dict, Any, List, Optional, Callable, Union, Type
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from abc import ABC, abstractmethod
from contextlib import contextmanager
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication, QMainWindow

# Import v2.0 core components
from .app_controller import AppController, get_app_controller
from .event_system import EventBus, Event, EventType, EventHandler, get_event_bus
from .config_manager import ConfigManager, get_config_manager

# Import Task 29 adapter components
from ui.adapters import (
    IUIComponentAdapter, AdapterState, AdapterConfig, AdapterMetrics,
    MainWindowAdapter, VideoInfoTabAdapter, DownloadedVideosTabAdapter,
    EventBridgeCoordinator, get_global_coordinator,
    create_main_window_adapter, create_video_info_tab_adapter, 
    create_downloaded_videos_tab_adapter
)


class IntegrationState(Enum):
    """States for adapter integration framework"""
    UNINITIALIZED = auto()
    INITIALIZING = auto()
    ACTIVE = auto()
    DEGRADED = auto()
    FALLBACK = auto()
    SHUTTING_DOWN = auto()
    SHUTDOWN = auto()
    ERROR = auto()


class IntegrationMode(Enum):
    """Integration operation modes"""
    FULL_V2 = "full_v2"                    # Full v2.0 + adapters
    DEGRADED_V2 = "degraded_v2"            # v2.0 core + minimal adapters
    FALLBACK_V1 = "fallback_v1"            # v1.2.1 only, no adapters
    HYBRID = "hybrid"                       # Mixed mode with selective features


@dataclass
class IntegrationConfig:
    """Configuration for adapter integration framework"""
    # Core settings
    enable_adapter_integration: bool = True
    enable_performance_monitoring: bool = True
    enable_fallback_mode: bool = True
    
    # Timeout settings
    adapter_initialization_timeout: float = 5.0
    component_startup_timeout: float = 10.0
    shutdown_timeout: float = 3.0
    
    # Retry settings
    max_adapter_retries: int = 3
    retry_delay: float = 1.0
    
    # Feature flags
    feature_flags: Dict[str, bool] = field(default_factory=lambda: {
        "use_main_window_adapter": True,
        "use_video_info_adapter": True,
        "use_downloaded_videos_adapter": True,
        "enable_cross_component_coordination": True,
        "enable_event_bridging": True,
        "enable_performance_metrics": True,
        "allow_degraded_mode": True,
        "enable_automatic_fallback": True
    })
    
    # Performance thresholds
    performance_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "max_initialization_time": 250.0,  # ms
        "max_adapter_response_time": 100.0,  # ms
        "max_memory_usage": 64.0,  # MB
        "min_success_rate": 0.95  # 95%
    })


@dataclass
class IntegrationMetrics:
    """Metrics for adapter integration framework"""
    initialization_time: float = 0.0
    adapters_initialized: int = 0
    adapters_failed: int = 0
    current_mode: IntegrationMode = IntegrationMode.FULL_V2
    memory_usage: float = 0.0
    success_rate: float = 1.0
    last_error: Optional[str] = None
    error_count: int = 0
    uptime: timedelta = field(default_factory=lambda: timedelta())
    performance_issues: List[str] = field(default_factory=list)


class AdapterIntegrationError(Exception):
    """Exception raised by adapter integration operations"""
    pass


class IAdapterIntegrationFramework(ABC):
    """Interface for adapter integration framework"""
    
    @abstractmethod
    def initialize(self, config: IntegrationConfig) -> bool:
        """Initialize the integration framework"""
        pass
    
    @abstractmethod
    def register_adapter(self, adapter_id: str, adapter: IUIComponentAdapter) -> bool:
        """Register an adapter with the framework"""
        pass
    
    @abstractmethod
    def start_integration(self) -> bool:
        """Start the adapter integration process"""
        pass
    
    @abstractmethod
    def get_integration_status(self) -> IntegrationState:
        """Get current integration status"""
        pass
    
    @abstractmethod
    def shutdown(self) -> bool:
        """Shutdown the integration framework"""
        pass


class AdapterIntegrationFramework(QObject):
    """
    Main adapter integration framework implementation
    
    Manages the integration between Task 29 UI adapters and v2.0 architecture,
    providing lifecycle management, fallback mechanisms, and performance monitoring.
    
    Implements IAdapterIntegrationFramework and EventHandler interfaces manually 
    to avoid metaclass conflicts.
    """
    
    # Signals for framework events
    integration_started = pyqtSignal()
    integration_completed = pyqtSignal()
    integration_failed = pyqtSignal(str, str)  # error_type, error_message
    mode_changed = pyqtSignal(str)  # new_mode
    adapter_registered = pyqtSignal(str)  # adapter_id
    adapter_failed = pyqtSignal(str, str)  # adapter_id, error_message
    performance_warning = pyqtSignal(str, float)  # metric_name, value
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Core state
        self._state = IntegrationState.UNINITIALIZED
        self._mode = IntegrationMode.FULL_V2
        self._config = IntegrationConfig()
        self._metrics = IntegrationMetrics()
        self._start_time: Optional[datetime] = None
        self._lock = threading.RLock()
        
        # v2.0 architecture components
        self._app_controller: Optional[AppController] = None
        self._event_bus: Optional[EventBus] = None
        self._config_manager: Optional[ConfigManager] = None
        
        # Adapter management
        self._adapters: Dict[str, IUIComponentAdapter] = {}
        self._adapter_configs: Dict[str, AdapterConfig] = {}
        self._adapter_states: Dict[str, AdapterState] = {}
        self._adapter_errors: Dict[str, List[str]] = {}
        
        # Framework components
        self._coordinator: Optional[EventBridgeCoordinator] = None
        self._performance_monitor: Optional[QTimer] = None
        self._health_check_timer: Optional[QTimer] = None
        
        # Legacy component references
        self._qt_application: Optional[QApplication] = None
        self._main_window: Optional[QMainWindow] = None
        self._main_window_ref: Optional[weakref.ReferenceType] = None
        
        # Integration callbacks
        self._initialization_callbacks: List[Callable[[], bool]] = []
        self._shutdown_callbacks: List[Callable[[], bool]] = []
        self._error_handlers: List[Callable[[Exception, str], None]] = []
    
    def initialize(self, config: IntegrationConfig) -> bool:
        """
        Initialize the adapter integration framework
        
        Args:
            config: Integration configuration
            
        Returns:
            True if initialization successful, False otherwise
        """
        with self._lock:
            if self._state != IntegrationState.UNINITIALIZED:
                self.logger.warning(f"Framework already initialized (state: {self._state})")
                return self._state in [IntegrationState.ACTIVE, IntegrationState.DEGRADED]
            
            try:
                self._state = IntegrationState.INITIALIZING
                self._start_time = datetime.now()
                self._config = config
                
                self.logger.info("Initializing adapter integration framework...")
                
                # Initialize v2.0 architecture components
                if not self._initialize_v2_components():
                    raise AdapterIntegrationError("Failed to initialize v2.0 components")
                
                # Initialize framework components
                if not self._initialize_framework_components():
                    raise AdapterIntegrationError("Failed to initialize framework components")
                
                # Set up performance monitoring
                if self._config.enable_performance_monitoring:
                    self._setup_performance_monitoring()
                
                # Register event handlers
                self._register_event_handlers()
                
                self._state = IntegrationState.ACTIVE
                self._mode = IntegrationMode.FULL_V2
                
                initialization_time = (datetime.now() - self._start_time).total_seconds() * 1000
                self._metrics.initialization_time = initialization_time
                
                self.logger.info(f"Adapter integration framework initialized successfully in {initialization_time:.1f}ms")
                self.integration_started.emit()
                return True
                
            except Exception as e:
                self._state = IntegrationState.ERROR
                self._metrics.last_error = str(e)
                self._metrics.error_count += 1
                self.logger.error(f"Failed to initialize adapter integration framework: {e}")
                self.integration_failed.emit("initialization", str(e))
                
                # Attempt fallback initialization
                if self._config.enable_fallback_mode:
                    return self._initialize_fallback_mode()
                
                return False
    
    def _initialize_v2_components(self) -> bool:
        """Initialize v2.0 architecture components"""
        try:
            # Get App Controller
            self._app_controller = get_app_controller()
            if not self._app_controller:
                raise AdapterIntegrationError("App Controller not available")
            
            # Get Event Bus
            self._event_bus = get_event_bus()
            if not self._event_bus:
                raise AdapterIntegrationError("Event Bus not available")
            
            # Get Config Manager
            self._config_manager = get_config_manager()
            if not self._config_manager:
                raise AdapterIntegrationError("Config Manager not available")
            
            self.logger.info("v2.0 architecture components initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize v2.0 components: {e}")
            return False
    
    def _initialize_framework_components(self) -> bool:
        """Initialize framework-specific components"""
        try:
            # Initialize Event Bridge Coordinator
            if self._config.feature_flags.get("enable_event_bridging", True):
                self._coordinator = get_global_coordinator()
                if self._coordinator:
                    # Initialize coordinator with v2.0 components
                    coordinator_config = {
                        "app_controller": self._app_controller,
                        "event_bus": self._event_bus,
                        "enable_performance_monitoring": self._config.enable_performance_monitoring
                    }
                    self._coordinator.initialize(coordinator_config)
                    self.logger.info("Event Bridge Coordinator initialized")
                else:
                    self.logger.warning("Event Bridge Coordinator not available")
            
            self.logger.info("Framework components initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize framework components: {e}")
            return False
    
    def _setup_performance_monitoring(self) -> None:
        """Set up performance monitoring timers"""
        try:
            # Performance monitoring timer
            self._performance_monitor = QTimer()
            self._performance_monitor.timeout.connect(self._check_performance_metrics)
            self._performance_monitor.start(5000)  # Check every 5 seconds
            
            # Health check timer
            self._health_check_timer = QTimer()
            self._health_check_timer.timeout.connect(self._perform_health_check)
            self._health_check_timer.start(30000)  # Check every 30 seconds
            
            self.logger.info("Performance monitoring set up")
            
        except Exception as e:
            self.logger.error(f"Failed to set up performance monitoring: {e}")
    
    def register_adapter(self, adapter_id: str, adapter: IUIComponentAdapter) -> bool:
        """
        Register an adapter with the framework
        
        Args:
            adapter_id: Unique identifier for the adapter
            adapter: Adapter instance to register
            
        Returns:
            True if registration successful, False otherwise
        """
        with self._lock:
            try:
                if adapter_id in self._adapters:
                    self.logger.warning(f"Adapter {adapter_id} already registered")
                    return True
                
                # Create adapter configuration
                adapter_config = AdapterConfig(
                    adapter_id=adapter_id,
                    enable_performance_monitoring=self._config.enable_performance_monitoring,
                    enable_error_recovery=True,
                    max_retry_attempts=self._config.max_adapter_retries
                )
                
                # Store adapter and configuration
                self._adapters[adapter_id] = adapter
                self._adapter_configs[adapter_id] = adapter_config
                self._adapter_states[adapter_id] = AdapterState.UNINITIALIZED
                self._adapter_errors[adapter_id] = []
                
                self.logger.info(f"Adapter {adapter_id} registered successfully")
                self.adapter_registered.emit(adapter_id)
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to register adapter {adapter_id}: {e}")
                self.adapter_failed.emit(adapter_id, str(e))
                return False
    
    def start_integration(self) -> bool:
        """
        Start the adapter integration process
        
        Returns:
            True if integration started successfully, False otherwise
        """
        with self._lock:
            if self._state != IntegrationState.ACTIVE:
                self.logger.error(f"Cannot start integration in state {self._state}")
                return False
            
            try:
                self.logger.info("Starting adapter integration process...")
                
                # Initialize all registered adapters
                success_count = 0
                total_count = len(self._adapters)
                
                for adapter_id, adapter in self._adapters.items():
                    if self._initialize_adapter(adapter_id, adapter):
                        success_count += 1
                    else:
                        self._adapter_states[adapter_id] = AdapterState.ERROR
                
                # Update metrics
                self._metrics.adapters_initialized = success_count
                self._metrics.adapters_failed = total_count - success_count
                self._metrics.success_rate = success_count / total_count if total_count > 0 else 1.0
                
                # Determine integration mode based on success rate
                if self._metrics.success_rate >= self._config.performance_thresholds["min_success_rate"]:
                    self._mode = IntegrationMode.FULL_V2
                elif success_count > 0:
                    self._mode = IntegrationMode.DEGRADED_V2
                    self._state = IntegrationState.DEGRADED
                else:
                    return self._fallback_to_v1_mode()
                
                self._metrics.current_mode = self._mode
                
                # Initialize cross-component coordination
                if self._config.feature_flags.get("enable_cross_component_coordination", True):
                    self._initialize_cross_component_coordination()
                
                self.logger.info(f"Adapter integration completed: {success_count}/{total_count} adapters initialized")
                self.integration_completed.emit()
                
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to start adapter integration: {e}")
                self.integration_failed.emit("integration_start", str(e))
                return self._fallback_to_v1_mode()
    
    def _initialize_adapter(self, adapter_id: str, adapter: IUIComponentAdapter) -> bool:
        """Initialize a specific adapter"""
        try:
            self.logger.info(f"Initializing adapter: {adapter_id}")
            
            # Get adapter configuration
            adapter_config = self._adapter_configs[adapter_id]
            
            # Set adapter state
            self._adapter_states[adapter_id] = AdapterState.INITIALIZING
            
            # Initialize adapter with v2.0 components
            success = adapter.initialize(
                self._app_controller,
                self._event_bus,
                adapter_config
            )
            
            if success:
                self._adapter_states[adapter_id] = AdapterState.ACTIVE
                self.logger.info(f"Adapter {adapter_id} initialized successfully")
                return True
            else:
                self._adapter_states[adapter_id] = AdapterState.ERROR
                error_msg = f"Adapter {adapter_id} initialization failed"
                self._adapter_errors[adapter_id].append(error_msg)
                self.logger.error(error_msg)
                self.adapter_failed.emit(adapter_id, error_msg)
                return False
                
        except Exception as e:
            self._adapter_states[adapter_id] = AdapterState.ERROR
            error_msg = f"Exception during {adapter_id} initialization: {e}"
            self._adapter_errors[adapter_id].append(error_msg)
            self.logger.error(error_msg)
            self.adapter_failed.emit(adapter_id, str(e))
            return False
    
    def _initialize_cross_component_coordination(self) -> bool:
        """Initialize cross-component coordination"""
        try:
            if not self._coordinator:
                self.logger.warning("Event Bridge Coordinator not available for cross-component coordination")
                return False
            
            # Connect adapters to coordinator
            for adapter_id, adapter in self._adapters.items():
                if self._adapter_states[adapter_id] == AdapterState.ACTIVE:
                    self._coordinator.register_adapter(adapter_id, adapter)
            
            # Start coordination
            self._coordinator.start_coordination()
            
            self.logger.info("Cross-component coordination initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize cross-component coordination: {e}")
            return False
    
    def _fallback_to_v1_mode(self) -> bool:
        """Fallback to v1.2.1 only mode"""
        try:
            self.logger.warning("Falling back to v1.2.1 only mode")
            
            self._mode = IntegrationMode.FALLBACK_V1
            self._state = IntegrationState.FALLBACK
            self._metrics.current_mode = self._mode
            
            # Disable all adapters
            for adapter_id in self._adapters:
                self._adapter_states[adapter_id] = AdapterState.TERMINATED
            
            self.mode_changed.emit(self._mode.value)
            self.logger.info("Fallback to v1.2.1 mode completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to fallback to v1.2.1 mode: {e}")
            self._state = IntegrationState.ERROR
            return False
    
    def _initialize_fallback_mode(self) -> bool:
        """Initialize in fallback mode"""
        try:
            self.logger.info("Initializing in fallback mode...")
            
            self._state = IntegrationState.FALLBACK
            self._mode = IntegrationMode.FALLBACK_V1
            self._metrics.current_mode = self._mode
            
            # Minimal initialization for v1.2.1 compatibility
            self._start_time = datetime.now()
            
            self.logger.info("Fallback mode initialization completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize fallback mode: {e}")
            return False
    
    def attach_legacy_components(self, qt_app: QApplication, main_window: QMainWindow) -> bool:
        """
        Attach legacy UI components to adapters
        
        Args:
            qt_app: PyQt6 QApplication instance
            main_window: Legacy MainWindow instance
            
        Returns:
            True if attachment successful, False otherwise
        """
        with self._lock:
            try:
                self.logger.info("Attaching legacy UI components to adapters...")
                
                # Store references
                self._qt_application = qt_app
                self._main_window = main_window
                self._main_window_ref = weakref.ref(main_window)
                
                # Only attach if we're in integration mode
                if self._mode == IntegrationMode.FALLBACK_V1:
                    self.logger.info("In fallback mode, skipping adapter attachment")
                    return True
                
                # Attach main window to adapter
                if "main_window" in self._adapters:
                    main_window_adapter = self._adapters["main_window"]
                    if not main_window_adapter.attach_component(main_window):
                        self.logger.error("Failed to attach main window to adapter")
                        return False
                
                # Attach tab components
                if hasattr(main_window, 'video_info_tab') and "video_info" in self._adapters:
                    video_info_adapter = self._adapters["video_info"]
                    if not video_info_adapter.attach_component(main_window.video_info_tab):
                        self.logger.error("Failed to attach video info tab to adapter")
                
                if hasattr(main_window, 'downloaded_videos_tab') and "downloaded_videos" in self._adapters:
                    downloaded_videos_adapter = self._adapters["downloaded_videos"]
                    if not downloaded_videos_adapter.attach_component(main_window.downloaded_videos_tab):
                        self.logger.error("Failed to attach downloaded videos tab to adapter")
                
                self.logger.info("Legacy UI components attached successfully")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to attach legacy components: {e}")
                return False
    
    def get_integration_status(self) -> IntegrationState:
        """Get current integration status"""
        return self._state
    
    def get_integration_mode(self) -> IntegrationMode:
        """Get current integration mode"""
        return self._mode
    
    def get_metrics(self) -> IntegrationMetrics:
        """Get integration metrics"""
        with self._lock:
            if self._start_time:
                self._metrics.uptime = datetime.now() - self._start_time
            return self._metrics
    
    def get_adapter_state(self, adapter_id: str) -> Optional[AdapterState]:
        """Get state of a specific adapter"""
        return self._adapter_states.get(adapter_id)
    
    def get_all_adapter_states(self) -> Dict[str, AdapterState]:
        """Get states of all adapters"""
        return self._adapter_states.copy()
    
    def _check_performance_metrics(self) -> None:
        """Check performance metrics and issue warnings if needed"""
        try:
            # Check initialization time
            if (self._metrics.initialization_time > 
                self._config.performance_thresholds["max_initialization_time"]):
                self.performance_warning.emit("initialization_time", self._metrics.initialization_time)
            
            # Check success rate
            if (self._metrics.success_rate < 
                self._config.performance_thresholds["min_success_rate"]):
                self.performance_warning.emit("success_rate", self._metrics.success_rate)
                
        except Exception as e:
            self.logger.error(f"Error checking performance metrics: {e}")
    
    def _perform_health_check(self) -> None:
        """Perform health check on all adapters"""
        try:
            for adapter_id, adapter in self._adapters.items():
                if self._adapter_states[adapter_id] == AdapterState.ACTIVE:
                    # Basic health check - ensure adapter is still responsive
                    if hasattr(adapter, 'health_check'):
                        if not adapter.health_check():
                            self.logger.warning(f"Adapter {adapter_id} failed health check")
                            self._adapter_states[adapter_id] = AdapterState.ERROR
                            
        except Exception as e:
            self.logger.error(f"Error performing health check: {e}")
    
    def handle_event(self, event: Event) -> None:
        """Handle events from the v2.0 event system"""
        try:
            if event.event_type == EventType.APP_SHUTDOWN:
                self.shutdown()
            elif event.event_type == EventType.CONFIG_CHANGED:
                self._handle_config_change(event)
                
        except Exception as e:
            self.logger.error(f"Error handling event {event.event_type}: {e}")
    
    def _handle_config_change(self, event: Event) -> None:
        """Handle configuration change events"""
        try:
            # Reload configuration if needed
            config_data = event.data.get('config_data', {})
            if 'adapter_integration' in config_data:
                # Update configuration
                new_config = config_data['adapter_integration']
                self._update_configuration(new_config)
                
        except Exception as e:
            self.logger.error(f"Error handling config change: {e}")
    
    def _update_configuration(self, new_config: Dict[str, Any]) -> None:
        """Update framework configuration"""
        try:
            # Update feature flags
            if 'feature_flags' in new_config:
                self._config.feature_flags.update(new_config['feature_flags'])
            
            # Update performance thresholds
            if 'performance_thresholds' in new_config:
                self._config.performance_thresholds.update(new_config['performance_thresholds'])
                
            self.logger.info("Configuration updated")
            
        except Exception as e:
            self.logger.error(f"Error updating configuration: {e}")
    
    def _register_event_handlers(self) -> None:
        """Register event handlers with the event bus"""
        if self._event_bus:
            self._event_bus.add_handler(self)
    
    def shutdown(self) -> bool:
        """
        Shutdown the adapter integration framework
        
        Returns:
            True if shutdown successful, False otherwise
        """
        with self._lock:
            if self._state in [IntegrationState.SHUTTING_DOWN, IntegrationState.SHUTDOWN]:
                return True
            
            try:
                self.logger.info("Shutting down adapter integration framework...")
                self._state = IntegrationState.SHUTTING_DOWN
                
                # Stop timers
                if self._performance_monitor:
                    self._performance_monitor.stop()
                if self._health_check_timer:
                    self._health_check_timer.stop()
                
                # Shutdown adapters
                for adapter_id, adapter in self._adapters.items():
                    try:
                        if hasattr(adapter, 'shutdown'):
                            adapter.shutdown()
                        self._adapter_states[adapter_id] = AdapterState.TERMINATED
                    except Exception as e:
                        self.logger.error(f"Error shutting down adapter {adapter_id}: {e}")
                
                # Shutdown coordinator
                if self._coordinator:
                    try:
                        self._coordinator.shutdown()
                    except Exception as e:
                        self.logger.error(f"Error shutting down coordinator: {e}")
                
                # Execute shutdown callbacks
                for callback in self._shutdown_callbacks:
                    try:
                        callback()
                    except Exception as e:
                        self.logger.error(f"Error executing shutdown callback: {e}")
                
                self._state = IntegrationState.SHUTDOWN
                self.logger.info("Adapter integration framework shut down successfully")
                return True
                
            except Exception as e:
                self.logger.error(f"Error during shutdown: {e}")
                self._state = IntegrationState.ERROR
                return False


# Global framework instance
_integration_framework: Optional[AdapterIntegrationFramework] = None
_framework_lock = threading.Lock()


def get_integration_framework() -> AdapterIntegrationFramework:
    """Get the global adapter integration framework instance (singleton)"""
    global _integration_framework
    
    with _framework_lock:
        if _integration_framework is None:
            _integration_framework = AdapterIntegrationFramework()
        
        return _integration_framework


def initialize_integration_framework(config: IntegrationConfig) -> bool:
    """Initialize the global adapter integration framework"""
    framework = get_integration_framework()
    return framework.initialize(config)


def create_default_integration_config() -> IntegrationConfig:
    """Create default integration configuration"""
    return IntegrationConfig()


@contextmanager
def integration_context(config: Optional[IntegrationConfig] = None):
    """Context manager for adapter integration"""
    if config is None:
        config = create_default_integration_config()
    
    framework = get_integration_framework()
    
    try:
        # Initialize framework
        if not framework.initialize(config):
            raise AdapterIntegrationError("Failed to initialize integration framework")
        
        yield framework
        
    finally:
        # Cleanup
        framework.shutdown()


# Convenience functions for adapter creation and registration
def setup_standard_adapters(framework: AdapterIntegrationFramework) -> bool:
    """Set up the standard set of Task 29 adapters"""
    try:
        # Create and register main window adapter
        main_window_adapter = create_main_window_adapter()
        if not framework.register_adapter("main_window", main_window_adapter):
            return False
        
        # Create and register video info adapter
        video_info_adapter = create_video_info_tab_adapter()
        if not framework.register_adapter("video_info", video_info_adapter):
            return False
        
        # Create and register downloaded videos adapter
        downloaded_videos_adapter = create_downloaded_videos_tab_adapter()
        if not framework.register_adapter("downloaded_videos", downloaded_videos_adapter):
            return False
        
        return True
        
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to set up standard adapters: {e}")
        return False


def get_integration_status() -> IntegrationState:
    """Get current integration framework status"""
    framework = get_integration_framework()
    return framework.get_integration_status()


def get_integration_metrics() -> IntegrationMetrics:
    """Get integration framework metrics"""
    framework = get_integration_framework()
    return framework.get_metrics() 