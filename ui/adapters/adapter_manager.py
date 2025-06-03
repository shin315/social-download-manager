"""
Adapter Manager for Task 29.6 - App Controller Integration and Fallback Mechanisms

This module provides centralized management of UI adapters, handles integration
with the App Controller, and implements robust fallback mechanisms for handling
incompatibilities or failures during the v1.2.1 to v2.0 transition.
"""

import logging
import threading
import time
from typing import Dict, Any, Optional, List, Callable, Set, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime, timedelta
import weakref
import json
from abc import ABC, abstractmethod

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

# Import interfaces and adapters
from .interfaces import (
    IUIComponentAdapter, IMainWindowAdapter, IVideoInfoTabAdapter, 
    IDownloadedVideosTabAdapter, AdapterState, AdapterPriority, 
    AdapterConfig, AdapterMetrics, AdapterRegistration
)

# Import app controller
from core.app_controller import AppController, ControllerState

# Optional imports with fallback
try:
    from .main_window_adapter import MainWindowAdapter
    from .video_info_tab_adapter import VideoInfoTabAdapter
    from .downloaded_videos_tab_adapter import DownloadedVideosTabAdapter
    from .cross_component_coordinator import CrossComponentCoordinator
    ADAPTERS_AVAILABLE = True
except ImportError:
    ADAPTERS_AVAILABLE = False


class AdapterManagerState(Enum):
    """States for the Adapter Manager lifecycle"""
    UNINITIALIZED = auto()
    INITIALIZING = auto()
    READY = auto()
    RUNNING = auto()
    FALLBACK_MODE = auto()
    SHUTTING_DOWN = auto()
    SHUTDOWN = auto()
    ERROR = auto()


class FallbackStrategy(Enum):
    """Strategies for handling adapter failures"""
    GRACEFUL_DEGRADATION = auto()  # Fall back to v1.2.1 behavior
    RETRY_WITH_BACKOFF = auto()     # Retry initialization with exponential backoff
    SKIP_COMPONENT = auto()         # Skip the failed component
    FAIL_FAST = auto()             # Fail immediately
    MANUAL_INTERVENTION = auto()    # Wait for manual intervention


class FeatureDetectionMode(Enum):
    """Modes for detecting feature availability"""
    AUTOMATIC = auto()              # Automatic detection based on system state
    CONFIGURATION_BASED = auto()    # Based on configuration settings
    RUNTIME_TESTING = auto()        # Runtime testing of features
    HYBRID = auto()                # Combination of methods


@dataclass
class FallbackConfig:
    """Configuration for fallback behavior"""
    strategy: FallbackStrategy = FallbackStrategy.GRACEFUL_DEGRADATION
    max_retries: int = 3
    retry_delay_ms: int = 1000
    backoff_multiplier: float = 2.0
    timeout_seconds: int = 30
    enable_telemetry: bool = True
    log_fallbacks: bool = True
    notify_user: bool = False


@dataclass
class FeatureFlag:
    """Feature flag for controlling adapter behavior"""
    name: str
    enabled: bool
    description: str
    component: str
    v2_required: bool = False
    fallback_behavior: str = "v1_2_1"
    last_modified: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AdapterHealthMetrics:
    """Health metrics for adapters"""
    adapter_id: str
    is_healthy: bool
    last_health_check: datetime
    consecutive_failures: int = 0
    total_failures: int = 0
    total_operations: int = 0
    average_response_time_ms: float = 0.0
    error_rate_percent: float = 0.0
    memory_usage_mb: float = 0.0
    
    def update_metrics(self, success: bool, response_time_ms: float, memory_mb: float):
        """Update health metrics with operation result"""
        self.total_operations += 1
        self.last_health_check = datetime.now()
        self.memory_usage_mb = memory_mb
        
        if success:
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1
            self.total_failures += 1
        
        # Update average response time
        self.average_response_time_ms = (
            (self.average_response_time_ms * (self.total_operations - 1) + response_time_ms) 
            / self.total_operations
        )
        
        # Update error rate
        self.error_rate_percent = (self.total_failures / self.total_operations) * 100
        
        # Update health status
        self.is_healthy = (
            self.consecutive_failures < 3 and 
            self.error_rate_percent < 50 and 
            self.average_response_time_ms < 5000
        )


class IFallbackManager(ABC):
    """Interface for fallback management"""
    
    @abstractmethod
    def handle_adapter_failure(self, adapter_id: str, error: Exception, context: str) -> bool:
        """Handle adapter failure with appropriate fallback strategy"""
        pass
    
    @abstractmethod
    def is_feature_available(self, feature_name: str) -> bool:
        """Check if a feature is available"""
        pass
    
    @abstractmethod
    def get_fallback_behavior(self, component: str, feature: str) -> str:
        """Get fallback behavior for a component/feature combination"""
        pass


class FallbackManager(QObject, IFallbackManager):
    """
    Manager for handling fallback scenarios during adapter operation
    """
    
    # Signals
    fallback_triggered = pyqtSignal(str, str, str)  # adapter_id, reason, strategy
    feature_degraded = pyqtSignal(str, str)         # feature_name, reason
    recovery_attempted = pyqtSignal(str, int)       # adapter_id, attempt_number
    
    def __init__(self, config: FallbackConfig):
        super().__init__()
        self.config = config
        self._logger = logging.getLogger(__name__)
        self._feature_flags: Dict[str, FeatureFlag] = {}
        self._fallback_history: List[Dict[str, Any]] = []
        self._recovery_timers: Dict[str, QTimer] = {}
        self._component_states: Dict[str, str] = {}
        
        # Initialize default feature flags
        self._initialize_default_features()
    
    def _initialize_default_features(self):
        """Initialize default feature flags"""
        default_features = [
            FeatureFlag(
                name="main_window_v2_integration",
                enabled=True,
                description="MainWindow integration with v2.0 systems",
                component="main_window",
                v2_required=True,
                fallback_behavior="direct_v1_2_1"
            ),
            FeatureFlag(
                name="video_info_enhanced_metadata",
                enabled=True,
                description="Enhanced video metadata display",
                component="video_info_tab",
                v2_required=False,
                fallback_behavior="basic_metadata"
            ),
            FeatureFlag(
                name="download_progress_streaming",
                enabled=True,
                description="Real-time download progress streaming",
                component="downloaded_videos_tab",
                v2_required=True,
                fallback_behavior="polling_updates"
            ),
            FeatureFlag(
                name="cross_component_events",
                enabled=True,
                description="Cross-component event coordination",
                component="event_coordinator",
                v2_required=True,
                fallback_behavior="direct_signals"
            )
        ]
        
        for feature in default_features:
            self._feature_flags[feature.name] = feature
    
    def handle_adapter_failure(self, adapter_id: str, error: Exception, context: str) -> bool:
        """Handle adapter failure with appropriate fallback strategy"""
        self._logger.error(f"Adapter failure: {adapter_id} - {error} (Context: {context})")
        
        # Record fallback event
        fallback_event = {
            "adapter_id": adapter_id,
            "error": str(error),
            "context": context,
            "timestamp": datetime.now(),
            "strategy": self.config.strategy.name
        }
        self._fallback_history.append(fallback_event)
        
        # Emit signal
        self.fallback_triggered.emit(adapter_id, str(error), self.config.strategy.name)
        
        try:
            if self.config.strategy == FallbackStrategy.GRACEFUL_DEGRADATION:
                return self._handle_graceful_degradation(adapter_id, error, context)
            elif self.config.strategy == FallbackStrategy.RETRY_WITH_BACKOFF:
                return self._handle_retry_with_backoff(adapter_id, error, context)
            elif self.config.strategy == FallbackStrategy.SKIP_COMPONENT:
                return self._handle_skip_component(adapter_id, error, context)
            elif self.config.strategy == FallbackStrategy.FAIL_FAST:
                return False
            elif self.config.strategy == FallbackStrategy.MANUAL_INTERVENTION:
                return self._handle_manual_intervention(adapter_id, error, context)
            
        except Exception as fallback_error:
            self._logger.error(f"Fallback handling failed: {fallback_error}")
            return False
        
        return False
    
    def _handle_graceful_degradation(self, adapter_id: str, error: Exception, context: str) -> bool:
        """Handle graceful degradation to v1.2.1 behavior"""
        self._logger.info(f"Gracefully degrading {adapter_id} to v1.2.1 behavior")
        
        # Update component state
        self._component_states[adapter_id] = "degraded"
        
        # Disable v2-dependent features for this component
        for feature_name, feature in self._feature_flags.items():
            if feature.component == adapter_id and feature.v2_required:
                feature.enabled = False
                self.feature_degraded.emit(feature_name, f"Adapter {adapter_id} degraded")
        
        return True
    
    def _handle_retry_with_backoff(self, adapter_id: str, error: Exception, context: str) -> bool:
        """Handle retry with exponential backoff"""
        retry_count = self._get_retry_count(adapter_id)
        
        if retry_count >= self.config.max_retries:
            self._logger.warning(f"Max retries exceeded for {adapter_id}, falling back to degraded mode")
            return self._handle_graceful_degradation(adapter_id, error, context)
        
        # Calculate delay with exponential backoff
        delay_ms = self.config.retry_delay_ms * (self.config.backoff_multiplier ** retry_count)
        
        self._logger.info(f"Scheduling retry {retry_count + 1} for {adapter_id} in {delay_ms}ms")
        
        # Schedule retry
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._attempt_recovery(adapter_id))
        timer.start(int(delay_ms))
        
        self._recovery_timers[adapter_id] = timer
        self.recovery_attempted.emit(adapter_id, retry_count + 1)
        
        return True
    
    def _handle_skip_component(self, adapter_id: str, error: Exception, context: str) -> bool:
        """Skip the failed component"""
        self._logger.info(f"Skipping component {adapter_id} due to failure")
        self._component_states[adapter_id] = "skipped"
        return True
    
    def _handle_manual_intervention(self, adapter_id: str, error: Exception, context: str) -> bool:
        """Wait for manual intervention"""
        self._logger.warning(f"Manual intervention required for {adapter_id}")
        self._component_states[adapter_id] = "manual_intervention_required"
        # In a real implementation, this might open a dialog or notification
        return True
    
    def _get_retry_count(self, adapter_id: str) -> int:
        """Get current retry count for an adapter"""
        # Count retry attempts from fallback history
        return len([
            event for event in self._fallback_history
            if event["adapter_id"] == adapter_id and 
               event["strategy"] == FallbackStrategy.RETRY_WITH_BACKOFF.name
        ])
    
    def _attempt_recovery(self, adapter_id: str):
        """Attempt to recover a failed adapter"""
        self._logger.info(f"Attempting recovery for {adapter_id}")
        # This would be implemented to retry adapter initialization
        # For now, we'll just log the attempt
        pass
    
    def is_feature_available(self, feature_name: str) -> bool:
        """Check if a feature is available"""
        if feature_name not in self._feature_flags:
            return False
        
        feature = self._feature_flags[feature_name]
        
        # Check if feature is enabled
        if not feature.enabled:
            return False
        
        # Check if component is in good state
        component_state = self._component_states.get(feature.component, "unknown")
        if component_state in ["degraded", "skipped", "manual_intervention_required"]:
            return not feature.v2_required
        
        return True
    
    def get_fallback_behavior(self, component: str, feature: str) -> str:
        """Get fallback behavior for a component/feature combination"""
        feature_key = f"{component}_{feature}"
        
        if feature_key in self._feature_flags:
            return self._feature_flags[feature_key].fallback_behavior
        
        # Default fallback behavior
        return "v1_2_1"
    
    def get_fallback_history(self) -> List[Dict[str, Any]]:
        """Get history of fallback events"""
        return self._fallback_history.copy()
    
    def clear_fallback_history(self):
        """Clear fallback history"""
        self._fallback_history.clear()
    
    def update_feature_flag(self, name: str, enabled: bool, reason: str = ""):
        """Update a feature flag"""
        if name in self._feature_flags:
            self._feature_flags[name].enabled = enabled
            self._feature_flags[name].last_modified = datetime.now()
            if reason:
                self._feature_flags[name].metadata["last_change_reason"] = reason
    
    def get_feature_flags(self) -> Dict[str, FeatureFlag]:
        """Get all feature flags"""
        return self._feature_flags.copy()


class AdapterManager(QObject):
    """
    Centralized manager for UI adapters with App Controller integration
    """
    
    # Signals
    adapter_registered = pyqtSignal(str, str)      # adapter_id, adapter_type
    adapter_unregistered = pyqtSignal(str)         # adapter_id
    adapter_state_changed = pyqtSignal(str, str)   # adapter_id, new_state
    health_check_completed = pyqtSignal(str, bool) # adapter_id, is_healthy
    
    def __init__(self, app_controller: AppController, fallback_config: Optional[FallbackConfig] = None):
        super().__init__()
        self.app_controller = app_controller
        self._state = AdapterManagerState.UNINITIALIZED
        self._logger = logging.getLogger(__name__)
        
        # Adapter storage
        self._adapters: Dict[str, IUIComponentAdapter] = {}
        self._adapter_configs: Dict[str, AdapterConfig] = {}
        self._adapter_health: Dict[str, AdapterHealthMetrics] = {}
        self._component_mappings: Dict[str, str] = {}  # component_type -> adapter_id
        
        # Fallback management
        self.fallback_manager = FallbackManager(fallback_config or FallbackConfig())
        
        # Cross-component coordination
        self.coordinator: Optional[CrossComponentCoordinator] = None
        
        # Threading
        self._lock = threading.RLock()
        
        # Health check timer
        self._health_check_timer = QTimer()
        self._health_check_timer.timeout.connect(self._perform_health_checks)
        self._health_check_timer.start(30000)  # Check every 30 seconds
        
        # Connect fallback manager signals
        self.fallback_manager.fallback_triggered.connect(self._on_fallback_triggered)
        
        # Register with app controller
        self.app_controller.register_component("adapter_manager", self)
    
    def initialize(self) -> bool:
        """Initialize the Adapter Manager"""
        with self._lock:
            if self._state != AdapterManagerState.UNINITIALIZED:
                return self._state == AdapterManagerState.READY
            
            try:
                self._state = AdapterManagerState.INITIALIZING
                self._logger.info("Initializing Adapter Manager...")
                
                # Initialize cross-component coordinator
                if ADAPTERS_AVAILABLE:
                    self.coordinator = CrossComponentCoordinator()
                    if self.coordinator:
                        bridge_coordinator = self.app_controller.get_component("event_bridge")
                        core_bus = self.app_controller.get_event_bus()
                        component_bus = self.app_controller.get_component("component_event_bus")
                        
                        if core_bus:
                            self.coordinator.initialize(
                                bridge_coordinator=bridge_coordinator,
                                core_event_bus=core_bus,
                                component_event_bus=component_bus
                            )
                
                # Register default adapters if available
                if ADAPTERS_AVAILABLE:
                    self._register_default_adapters()
                
                self._state = AdapterManagerState.READY
                self._logger.info("Adapter Manager initialized successfully")
                return True
                
            except Exception as e:
                self._logger.error(f"Failed to initialize Adapter Manager: {e}")
                self._state = AdapterManagerState.ERROR
                return False
    
    def _register_default_adapters(self):
        """Register default adapter instances"""
        try:
            # Register MainWindow adapter
            main_adapter = MainWindowAdapter()
            self.register_adapter(
                adapter_id="main_window_adapter",
                adapter=main_adapter,
                component_type="MainWindow",
                priority=AdapterPriority.HIGH
            )
            
            # Register VideoInfoTab adapter
            video_adapter = VideoInfoTabAdapter()
            self.register_adapter(
                adapter_id="video_info_adapter",
                adapter=video_adapter,
                component_type="VideoInfoTab",
                priority=AdapterPriority.NORMAL
            )
            
            # Register DownloadedVideosTab adapter
            download_adapter = DownloadedVideosTabAdapter()
            self.register_adapter(
                adapter_id="downloaded_videos_adapter",
                adapter=download_adapter,
                component_type="DownloadedVideosTab",
                priority=AdapterPriority.NORMAL
            )
            
        except Exception as e:
            self._logger.warning(f"Failed to register some default adapters: {e}")
            # Continue with fallback behavior
    
    def register_adapter(self, 
                        adapter_id: str,
                        adapter: IUIComponentAdapter,
                        component_type: str,
                        priority: AdapterPriority = AdapterPriority.NORMAL,
                        config: Optional[AdapterConfig] = None) -> bool:
        """Register an adapter with the manager"""
        with self._lock:
            try:
                if adapter_id in self._adapters:
                    self._logger.warning(f"Adapter {adapter_id} already registered")
                    return False
                
                # Use default config if none provided
                if config is None:
                    config = AdapterConfig()
                
                # Initialize adapter
                if not self._initialize_adapter(adapter, config):
                    raise Exception(f"Failed to initialize adapter {adapter_id}")
                
                # Store adapter and config
                self._adapters[adapter_id] = adapter
                self._adapter_configs[adapter_id] = config
                self._component_mappings[component_type] = adapter_id
                
                # Initialize health metrics
                self._adapter_health[adapter_id] = AdapterHealthMetrics(
                    adapter_id=adapter_id,
                    is_healthy=True,
                    last_health_check=datetime.now()
                )
                
                # Register with coordinator if available
                if self.coordinator:
                    self.coordinator.register_component(adapter_id, adapter)
                
                self.adapter_registered.emit(adapter_id, component_type)
                self._logger.info(f"Successfully registered adapter: {adapter_id}")
                
                return True
                
            except Exception as e:
                self._logger.error(f"Failed to register adapter {adapter_id}: {e}")
                
                # Handle fallback
                if self.fallback_manager.handle_adapter_failure(adapter_id, e, "registration"):
                    self._logger.info(f"Fallback successful for {adapter_id}")
                    return True
                
                return False
    
    def _initialize_adapter(self, adapter: IUIComponentAdapter, config: AdapterConfig) -> bool:
        """Initialize an individual adapter"""
        try:
            return adapter.initialize(
                app_controller=self.app_controller,
                event_bus=self.app_controller.get_event_bus(),
                config=config
            )
        except Exception as e:
            self._logger.error(f"Adapter initialization failed: {e}")
            return False
    
    def unregister_adapter(self, adapter_id: str) -> bool:
        """Unregister an adapter"""
        with self._lock:
            if adapter_id not in self._adapters:
                return False
            
            try:
                adapter = self._adapters[adapter_id]
                
                # Shutdown adapter
                adapter.shutdown()
                
                # Unregister from coordinator
                if self.coordinator:
                    self.coordinator.unregister_component(adapter_id)
                
                # Clean up
                del self._adapters[adapter_id]
                del self._adapter_configs[adapter_id]
                del self._adapter_health[adapter_id]
                
                # Update component mappings
                self._component_mappings = {
                    k: v for k, v in self._component_mappings.items() 
                    if v != adapter_id
                }
                
                self.adapter_unregistered.emit(adapter_id)
                self._logger.info(f"Successfully unregistered adapter: {adapter_id}")
                
                return True
                
            except Exception as e:
                self._logger.error(f"Failed to unregister adapter {adapter_id}: {e}")
                return False
    
    def get_adapter(self, adapter_id: str) -> Optional[IUIComponentAdapter]:
        """Get an adapter by ID"""
        return self._adapters.get(adapter_id)
    
    def get_adapter_by_component_type(self, component_type: str) -> Optional[IUIComponentAdapter]:
        """Get adapter by component type"""
        adapter_id = self._component_mappings.get(component_type)
        return self._adapters.get(adapter_id) if adapter_id else None
    
    def get_all_adapters(self) -> Dict[str, IUIComponentAdapter]:
        """Get all registered adapters"""
        return self._adapters.copy()
    
    def get_adapter_health(self, adapter_id: str) -> Optional[AdapterHealthMetrics]:
        """Get health metrics for an adapter"""
        return self._adapter_health.get(adapter_id)
    
    def _perform_health_checks(self):
        """Perform health checks on all adapters"""
        with self._lock:
            for adapter_id, adapter in self._adapters.items():
                try:
                    # Simple health check - verify adapter state
                    is_healthy = adapter.get_state() == AdapterState.ACTIVE
                    
                    # Update health metrics
                    if adapter_id in self._adapter_health:
                        metrics = self._adapter_health[adapter_id]
                        metrics.update_metrics(is_healthy, 0.0, 0.0)  # Simplified for now
                        
                        self.health_check_completed.emit(adapter_id, is_healthy)
                        
                        # Handle unhealthy adapters
                        if not is_healthy and metrics.consecutive_failures >= 3:
                            self._handle_unhealthy_adapter(adapter_id)
                
                except Exception as e:
                    self._logger.error(f"Health check failed for {adapter_id}: {e}")
                    self._handle_unhealthy_adapter(adapter_id)
    
    def _handle_unhealthy_adapter(self, adapter_id: str):
        """Handle an unhealthy adapter"""
        self._logger.warning(f"Adapter {adapter_id} is unhealthy, triggering fallback")
        
        # Trigger fallback
        self.fallback_manager.handle_adapter_failure(
            adapter_id, 
            Exception("Health check failed"), 
            "health_monitoring"
        )
    
    def _on_fallback_triggered(self, adapter_id: str, reason: str, strategy: str):
        """Handle fallback triggered signal"""
        self._logger.info(f"Fallback triggered for {adapter_id}: {reason} (Strategy: {strategy})")
        self.adapter_state_changed.emit(adapter_id, "fallback")
    
    def shutdown(self) -> bool:
        """Shutdown the Adapter Manager"""
        with self._lock:
            try:
                self._state = AdapterManagerState.SHUTTING_DOWN
                
                # Stop health checks
                self._health_check_timer.stop()
                
                # Shutdown all adapters
                for adapter_id in list(self._adapters.keys()):
                    self.unregister_adapter(adapter_id)
                
                # Shutdown coordinator
                if self.coordinator:
                    self.coordinator.shutdown()
                
                self._state = AdapterManagerState.SHUTDOWN
                self._logger.info("Adapter Manager shutdown complete")
                
                return True
                
            except Exception as e:
                self._logger.error(f"Failed to shutdown Adapter Manager: {e}")
                self._state = AdapterManagerState.ERROR
                return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the Adapter Manager"""
        return {
            "state": self._state.name,
            "adapters_registered": len(self._adapters),
            "adapters": list(self._adapters.keys()),
            "component_mappings": self._component_mappings.copy(),
            "health_summary": {
                adapter_id: metrics.is_healthy 
                for adapter_id, metrics in self._adapter_health.items()
            },
            "fallback_history_count": len(self.fallback_manager.get_fallback_history()),
            "coordinator_available": self.coordinator is not None
        }
    
    def get_feature_availability(self) -> Dict[str, bool]:
        """Get availability status of all features"""
        return {
            feature_name: self.fallback_manager.is_feature_available(feature_name)
            for feature_name in self.fallback_manager.get_feature_flags().keys()
        }
    
    def execute_with_fallback(self, 
                             adapter_id: str, 
                             operation: Callable, 
                             fallback_operation: Optional[Callable] = None,
                             context: str = "") -> Any:
        """Execute an operation with automatic fallback handling"""
        try:
            # Check if adapter is available and healthy
            if adapter_id not in self._adapters:
                raise Exception(f"Adapter {adapter_id} not found")
            
            health = self._adapter_health.get(adapter_id)
            if health and not health.is_healthy:
                raise Exception(f"Adapter {adapter_id} is unhealthy")
            
            # Execute operation
            result = operation()
            
            # Update health metrics on success
            if health:
                health.update_metrics(True, 0.0, 0.0)  # Simplified
            
            return result
            
        except Exception as e:
            self._logger.error(f"Operation failed for {adapter_id}: {e}")
            
            # Update health metrics on failure
            if adapter_id in self._adapter_health:
                self._adapter_health[adapter_id].update_metrics(False, 0.0, 0.0)
            
            # Handle fallback
            if self.fallback_manager.handle_adapter_failure(adapter_id, e, context):
                if fallback_operation:
                    try:
                        return fallback_operation()
                    except Exception as fallback_error:
                        self._logger.error(f"Fallback operation also failed: {fallback_error}")
            
            raise e


# Singleton pattern for global access
_adapter_manager_instance: Optional[AdapterManager] = None


def get_adapter_manager() -> Optional[AdapterManager]:
    """Get the global adapter manager instance"""
    return _adapter_manager_instance


def initialize_adapter_manager(app_controller: AppController, 
                              fallback_config: Optional[FallbackConfig] = None) -> bool:
    """Initialize the global adapter manager"""
    global _adapter_manager_instance
    
    if _adapter_manager_instance is not None:
        return True
    
    try:
        _adapter_manager_instance = AdapterManager(app_controller, fallback_config)
        return _adapter_manager_instance.initialize()
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to initialize adapter manager: {e}")
        return False


def shutdown_adapter_manager() -> bool:
    """Shutdown the global adapter manager"""
    global _adapter_manager_instance
    
    if _adapter_manager_instance is None:
        return True
    
    try:
        result = _adapter_manager_instance.shutdown()
        _adapter_manager_instance = None
        return result
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to shutdown adapter manager: {e}")
        return False 