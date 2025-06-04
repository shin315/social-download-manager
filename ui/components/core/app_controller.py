"""
Application Controller for Advanced V2.0 UI Architecture Integration
Task 36.9 - Central Controller for Tab Coordination and System-wide Events

Provides:
- Centralized event bus for application-wide messaging
- Global state management with change tracking
- Service locator pattern for component discovery
- Dependency injection system for controller services
- Debugging tools for controller visualization
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Callable, Type, TypeVar, Union, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from pathlib import Path
import json
import asyncio
from collections import defaultdict
import traceback

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QSettings
from PyQt6.QtWidgets import QApplication

# Import all our advanced managers
from .tab_lifecycle_manager import TabLifecycleManager, TabState, TabPriority
from .component_bus import ComponentBus, MessageType, MessagePriority, DeliveryMode
from .theme_manager import ThemeManager, ThemeVariant
from .state_manager import StateManager
from .performance_monitor import PerformanceMonitor
from .component_loader import ComponentLoader
from .i18n_manager import I18nManager
from .lifecycle_manager import LifecycleManager, InitializationStage, ShutdownStage


class AppMode(Enum):
    """Application operational modes"""
    STARTUP = auto()
    NORMAL = auto()
    MAINTENANCE = auto()
    RECOVERY = auto()
    SHUTDOWN = auto()


class ServiceScope(Enum):
    """Service lifecycle scopes"""
    SINGLETON = auto()    # One instance for the entire application
    TRANSIENT = auto()    # New instance each time
    SCOPED = auto()       # One instance per scope (e.g., per tab)


@dataclass
class ServiceDescriptor:
    """Service registration descriptor"""
    service_id: str
    service_type: Type
    scope: ServiceScope
    factory: Optional[Callable] = None
    singleton_instance: Optional[Any] = None
    dependencies: List[str] = field(default_factory=list)
    initialization_priority: int = 100
    auto_start: bool = True
    configuration: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AppConfiguration:
    """Application-wide configuration"""
    # Feature toggles
    enable_performance_monitoring: bool = True
    enable_advanced_theming: bool = True
    enable_tab_hibernation: bool = True
    enable_cross_tab_messaging: bool = True
    enable_state_snapshots: bool = True
    enable_dynamic_loading: bool = True
    enable_i18n: bool = True
    enable_splash_screen: bool = True
    
    # Performance settings
    max_parallel_tabs: int = 10
    tab_hibernation_threshold_minutes: int = 5
    memory_pressure_threshold_mb: int = 500
    performance_monitoring_interval_ms: int = 1000
    
    # UI settings
    default_theme: str = "light"
    default_language: str = "en_US"
    animation_duration_ms: int = 300
    startup_timeout_seconds: int = 30
    
    # Advanced settings
    enable_debug_mode: bool = False
    log_level: str = "INFO"
    session_persistence: bool = True
    crash_recovery: bool = True


@dataclass
class AppMetrics:
    """Application-wide metrics"""
    startup_time_ms: float = 0.0
    total_tabs_created: int = 0
    total_tabs_hibernated: int = 0
    total_messages_sent: int = 0
    total_state_snapshots: int = 0
    total_theme_switches: int = 0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    uptime_seconds: float = 0.0
    last_metrics_update: Optional[datetime] = None


T = TypeVar('T')


class AppController(QObject):
    """
    Central Application Controller for V2.0 UI Architecture
    
    Features:
    - Manages all advanced UI managers and their coordination
    - Provides service locator and dependency injection
    - Handles application-wide state and configuration
    - Coordinates cross-component communication
    - Monitors application health and performance
    - Manages application lifecycle and recovery
    """
    
    # Global application signals
    mode_changed = pyqtSignal(str, str)  # old_mode, new_mode
    service_registered = pyqtSignal(str, str)  # service_id, service_type
    service_started = pyqtSignal(str)  # service_id
    service_stopped = pyqtSignal(str)  # service_id
    configuration_changed = pyqtSignal(str, object)  # setting_name, new_value
    metrics_updated = pyqtSignal(AppMetrics)
    error_occurred = pyqtSignal(str, str, str)  # component, error_type, message
    recovery_started = pyqtSignal(str)  # recovery_reason
    
    def __init__(self, config: Optional[AppConfiguration] = None):
        super().__init__()
        
        # Core configuration
        self.config = config or AppConfiguration()
        self.app_mode = AppMode.STARTUP
        self.logger = logging.getLogger(__name__)
        
        # Service container
        self._services: Dict[str, ServiceDescriptor] = {}
        self._service_instances: Dict[str, Any] = {}
        self._service_scopes: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._initialization_lock = threading.RLock()
        
        # Core managers (initialized later)
        self.lifecycle_manager: Optional[LifecycleManager] = None
        self.tab_manager: Optional[TabLifecycleManager] = None
        self.component_bus: Optional[ComponentBus] = None
        self.theme_manager: Optional[ThemeManager] = None
        self.state_manager: Optional[StateManager] = None
        self.performance_monitor: Optional[PerformanceMonitor] = None
        self.component_loader: Optional[ComponentLoader] = None
        self.i18n_manager: Optional[I18nManager] = None
        
        # Application state
        self._startup_time: Optional[datetime] = None
        self._shutdown_time: Optional[datetime] = None
        self._metrics = AppMetrics()
        self._global_state: Dict[str, Any] = {}
        self._event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        
        # Monitoring and health
        self._health_check_timer = QTimer()
        self._health_check_timer.timeout.connect(self._perform_health_check)
        self._metrics_timer = QTimer()
        self._metrics_timer.timeout.connect(self._update_metrics)
        
        # Recovery and debugging
        self._recovery_handlers: Dict[str, Callable] = {}
        self._debug_enabled = self.config.enable_debug_mode
        self._error_history: List[Tuple[datetime, str, str, str]] = []
        
        self.logger.info("AppController initialized")
    
    def register_service(self, 
                        service_id: str,
                        service_type: Type[T],
                        scope: ServiceScope = ServiceScope.SINGLETON,
                        factory: Optional[Callable[[], T]] = None,
                        dependencies: Optional[List[str]] = None,
                        initialization_priority: int = 100,
                        auto_start: bool = True,
                        configuration: Optional[Dict[str, Any]] = None) -> bool:
        """
        Register a service in the dependency injection container
        
        Args:
            service_id: Unique identifier for the service
            service_type: Type of the service class
            scope: Lifecycle scope for the service
            factory: Factory function to create the service instance
            dependencies: List of service IDs this service depends on
            initialization_priority: Priority for initialization order (lower = earlier)
            auto_start: Whether to start the service automatically
            configuration: Service-specific configuration
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            with self._initialization_lock:
                if service_id in self._services:
                    self.logger.warning(f"Service {service_id} already registered")
                    return False
                
                descriptor = ServiceDescriptor(
                    service_id=service_id,
                    service_type=service_type,
                    scope=scope,
                    factory=factory,
                    dependencies=dependencies or [],
                    initialization_priority=initialization_priority,
                    auto_start=auto_start,
                    configuration=configuration or {}
                )
                
                self._services[service_id] = descriptor
                self.service_registered.emit(service_id, service_type.__name__)
                
                self.logger.info(f"Registered service: {service_id} ({service_type.__name__})")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to register service {service_id}: {e}")
            return False
    
    def get_service(self, service_id: str, scope_key: Optional[str] = None) -> Optional[Any]:
        """
        Get a service instance from the container
        
        Args:
            service_id: ID of the service to retrieve
            scope_key: Scope key for scoped services (e.g., tab ID)
            
        Returns:
            Service instance or None if not found
        """
        try:
            with self._initialization_lock:
                if service_id not in self._services:
                    self.logger.warning(f"Service {service_id} not registered")
                    return None
                
                descriptor = self._services[service_id]
                
                # Handle different scopes
                if descriptor.scope == ServiceScope.SINGLETON:
                    if descriptor.singleton_instance is None:
                        descriptor.singleton_instance = self._create_service_instance(descriptor)
                    return descriptor.singleton_instance
                
                elif descriptor.scope == ServiceScope.SCOPED:
                    if scope_key is None:
                        scope_key = "default"
                    
                    if scope_key not in self._service_scopes[service_id]:
                        self._service_scopes[service_id][scope_key] = self._create_service_instance(descriptor)
                    
                    return self._service_scopes[service_id][scope_key]
                
                elif descriptor.scope == ServiceScope.TRANSIENT:
                    return self._create_service_instance(descriptor)
                
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get service {service_id}: {e}")
            return None
    
    def _create_service_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Create a new service instance"""
        try:
            # Resolve dependencies first
            resolved_dependencies = {}
            for dep_id in descriptor.dependencies:
                dep_instance = self.get_service(dep_id)
                if dep_instance is None:
                    raise Exception(f"Dependency {dep_id} not available for {descriptor.service_id}")
                resolved_dependencies[dep_id] = dep_instance
            
            # Create instance
            if descriptor.factory:
                if descriptor.dependencies:
                    instance = descriptor.factory(**resolved_dependencies)
                else:
                    instance = descriptor.factory()
            else:
                if descriptor.configuration:
                    instance = descriptor.service_type(descriptor.configuration)
                else:
                    instance = descriptor.service_type()
            
            # Initialize if method exists
            if hasattr(instance, 'initialize'):
                instance.initialize()
            
            self.logger.info(f"Created service instance: {descriptor.service_id}")
            return instance
            
        except Exception as e:
            self.logger.error(f"Failed to create service instance {descriptor.service_id}: {e}")
            raise
    
    async def initialize(self) -> bool:
        """
        Initialize the AppController and all core managers
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            self._startup_time = datetime.now()
            self.app_mode = AppMode.STARTUP
            self.mode_changed.emit("uninitialized", "startup")
            
            self.logger.info("Starting AppController initialization...")
            
            # Initialize core managers in dependency order
            await self._initialize_core_managers()
            
            # Register core services
            self._register_core_services()
            
            # Initialize services with auto_start=True
            await self._initialize_auto_start_services()
            
            # Setup inter-manager communication
            self._setup_manager_communication()
            
            # Start monitoring
            self._start_monitoring()
            
            # Initialize global state
            self._initialize_global_state()
            
            # Change to normal mode
            self.app_mode = AppMode.NORMAL
            self.mode_changed.emit("startup", "normal")
            
            # Calculate startup time
            startup_duration = (datetime.now() - self._startup_time).total_seconds() * 1000
            self._metrics.startup_time_ms = startup_duration
            
            self.logger.info(f"AppController initialization completed in {startup_duration:.1f}ms")
            return True
            
        except Exception as e:
            self.logger.error(f"AppController initialization failed: {e}")
            self.logger.debug(traceback.format_exc())
            self.app_mode = AppMode.RECOVERY
            self.mode_changed.emit("startup", "recovery")
            return False
    
    async def _initialize_core_managers(self) -> None:
        """Initialize core managers in dependency order"""
        try:
            # 1. Lifecycle Manager (foundational)
            if self.config.enable_splash_screen:
                lifecycle_config = {
                    'show_splash_screen': True,
                    'max_parallel_workers': 4,
                    'session_file': 'data/session_state.json.gz'
                }
            else:
                lifecycle_config = {'show_splash_screen': False}
            
            self.lifecycle_manager = LifecycleManager(lifecycle_config)
            self.logger.info("Initialized LifecycleManager")
            
            # 2. Component Bus (communication backbone)
            if self.config.enable_cross_tab_messaging:
                bus_config = {
                    'max_queue_size': 10000,
                    'batch_size': 50,
                    'processing_interval_ms': 10
                }
                self.component_bus = ComponentBus(bus_config)
                self.logger.info("Initialized ComponentBus")
            
            # 3. Theme Manager (UI foundation)
            if self.config.enable_advanced_theming:
                theme_config = {
                    'default_theme': self.config.default_theme,
                    'enable_system_theme': True,
                    'animation_duration': self.config.animation_duration_ms
                }
                self.theme_manager = ThemeManager(theme_config)
                self.logger.info("Initialized ThemeManager")
            
            # 4. I18n Manager (localization)
            if self.config.enable_i18n:
                i18n_config = {
                    'default_locale': self.config.default_language,
                    'fallback_locale': 'en_US',
                    'auto_detect_locale': True
                }
                self.i18n_manager = I18nManager(i18n_config)
                self.logger.info("Initialized I18nManager")
            
            # 5. State Manager (state persistence)
            if self.config.enable_state_snapshots:
                state_config = {
                    'snapshot_interval': 300,  # 5 minutes
                    'max_snapshots': 10,
                    'enable_compression': True
                }
                self.state_manager = StateManager(state_config)
                self.logger.info("Initialized StateManager")
            
            # 6. Performance Monitor (monitoring)
            if self.config.enable_performance_monitoring:
                perf_config = {
                    'monitoring_interval': self.config.performance_monitoring_interval_ms,
                    'memory_threshold': self.config.memory_pressure_threshold_mb * 1024 * 1024,
                    'enable_real_time': True
                }
                self.performance_monitor = PerformanceMonitor(perf_config)
                self.logger.info("Initialized PerformanceMonitor")
            
            # 7. Component Loader (dynamic loading)
            if self.config.enable_dynamic_loading:
                loader_config = {
                    'enable_lazy_loading': True,
                    'cache_size': 100,
                    'preload_critical': True
                }
                self.component_loader = ComponentLoader(loader_config)
                self.logger.info("Initialized ComponentLoader")
            
            # 8. Tab Lifecycle Manager (tab management)
            if self.config.enable_tab_hibernation:
                tab_config = {
                    'hibernation_threshold': self.config.tab_hibernation_threshold_minutes * 60,
                    'max_hibernated_tabs': self.config.max_parallel_tabs,
                    'enable_automatic_hibernation': True,
                    'memory_pressure_threshold': 0.85
                }
                self.tab_manager = TabLifecycleManager(tab_config)
                self.logger.info("Initialized TabLifecycleManager")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize core managers: {e}")
            raise
    
    def _register_core_services(self) -> None:
        """Register core managers as services"""
        try:
            # Register all core managers as singleton services
            if self.lifecycle_manager:
                self.register_service(
                    'lifecycle_manager', 
                    LifecycleManager, 
                    ServiceScope.SINGLETON,
                    factory=lambda: self.lifecycle_manager,
                    initialization_priority=1
                )
            
            if self.component_bus:
                self.register_service(
                    'component_bus', 
                    ComponentBus, 
                    ServiceScope.SINGLETON,
                    factory=lambda: self.component_bus,
                    initialization_priority=2
                )
            
            if self.theme_manager:
                self.register_service(
                    'theme_manager', 
                    ThemeManager, 
                    ServiceScope.SINGLETON,
                    factory=lambda: self.theme_manager,
                    initialization_priority=3
                )
            
            if self.i18n_manager:
                self.register_service(
                    'i18n_manager', 
                    I18nManager, 
                    ServiceScope.SINGLETON,
                    factory=lambda: self.i18n_manager,
                    initialization_priority=4
                )
            
            if self.state_manager:
                self.register_service(
                    'state_manager', 
                    StateManager, 
                    ServiceScope.SINGLETON,
                    factory=lambda: self.state_manager,
                    initialization_priority=5
                )
            
            if self.performance_monitor:
                self.register_service(
                    'performance_monitor', 
                    PerformanceMonitor, 
                    ServiceScope.SINGLETON,
                    factory=lambda: self.performance_monitor,
                    initialization_priority=6
                )
            
            if self.component_loader:
                self.register_service(
                    'component_loader', 
                    ComponentLoader, 
                    ServiceScope.SINGLETON,
                    factory=lambda: self.component_loader,
                    initialization_priority=7
                )
            
            if self.tab_manager:
                self.register_service(
                    'tab_manager', 
                    TabLifecycleManager, 
                    ServiceScope.SINGLETON,
                    factory=lambda: self.tab_manager,
                    initialization_priority=8
                )
            
            self.logger.info("Registered all core services")
            
        except Exception as e:
            self.logger.error(f"Failed to register core services: {e}")
            raise
    
    async def _initialize_auto_start_services(self) -> None:
        """Initialize services marked for auto-start"""
        try:
            # Sort services by initialization priority
            auto_start_services = [
                (desc.initialization_priority, service_id, desc)
                for service_id, desc in self._services.items()
                if desc.auto_start
            ]
            auto_start_services.sort(key=lambda x: x[0])
            
            # Initialize in priority order
            for priority, service_id, descriptor in auto_start_services:
                try:
                    instance = self.get_service(service_id)
                    if instance and hasattr(instance, 'start'):
                        await instance.start() if asyncio.iscoroutinefunction(instance.start) else instance.start()
                    
                    self.service_started.emit(service_id)
                    self.logger.info(f"Started auto-start service: {service_id}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to start service {service_id}: {e}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize auto-start services: {e}")
            raise
    
    def _setup_manager_communication(self) -> None:
        """Setup communication between managers"""
        try:
            # Connect tab lifecycle events to other managers
            if self.tab_manager and self.component_bus:
                self.tab_manager.tab_hibernated.connect(
                    lambda tab_id: self.component_bus.handle_component_hibernation(tab_id)
                )
                self.tab_manager.tab_restored.connect(
                    lambda tab_id: self.component_bus.handle_component_restoration(tab_id)
                )
            
            # Connect theme changes to all managers
            if self.theme_manager:
                self.theme_manager.theme_changed.connect(self._handle_theme_change)
            
            # Connect performance alerts to tab manager
            if self.performance_monitor and self.tab_manager:
                self.performance_monitor.memory_pressure_detected.connect(
                    self.tab_manager.handle_memory_pressure
                )
            
            # Connect state snapshots to component bus
            if self.state_manager and self.component_bus:
                self.state_manager.snapshot_created.connect(
                    lambda snapshot_id: self.component_bus.broadcast(
                        "state_manager", "system", "snapshot_created", {"snapshot_id": snapshot_id}
                    )
                )
            
            self.logger.info("Setup manager communication")
            
        except Exception as e:
            self.logger.error(f"Failed to setup manager communication: {e}")
    
    def _start_monitoring(self) -> None:
        """Start application monitoring timers"""
        try:
            if self.config.enable_performance_monitoring:
                # Start health check timer (every 30 seconds)
                self._health_check_timer.start(30000)
                
                # Start metrics update timer (every 5 seconds)
                self._metrics_timer.start(5000)
                
                self.logger.info("Started application monitoring")
            
        except Exception as e:
            self.logger.error(f"Failed to start monitoring: {e}")
    
    def _initialize_global_state(self) -> None:
        """Initialize global application state"""
        try:
            self._global_state = {
                'app_version': '2.0.0',
                'startup_time': self._startup_time.isoformat() if self._startup_time else None,
                'current_mode': self.app_mode.name,
                'active_features': self._get_active_features(),
                'session_id': str(int(time.time())),
                'debug_mode': self._debug_enabled
            }
            
            self.logger.info("Initialized global state")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize global state: {e}")
    
    def _get_active_features(self) -> List[str]:
        """Get list of active features based on configuration"""
        active_features = []
        
        if self.config.enable_performance_monitoring:
            active_features.append('performance_monitoring')
        if self.config.enable_advanced_theming:
            active_features.append('advanced_theming')
        if self.config.enable_tab_hibernation:
            active_features.append('tab_hibernation')
        if self.config.enable_cross_tab_messaging:
            active_features.append('cross_tab_messaging')
        if self.config.enable_state_snapshots:
            active_features.append('state_snapshots')
        if self.config.enable_dynamic_loading:
            active_features.append('dynamic_loading')
        if self.config.enable_i18n:
            active_features.append('internationalization')
        
        return active_features
    
    def _handle_theme_change(self, old_theme: str, new_theme: str) -> None:
        """Handle theme change events"""
        try:
            # Broadcast theme change to all components
            if self.component_bus:
                self.component_bus.broadcast(
                    "theme_manager", "ui", "theme_changed",
                    {"old_theme": old_theme, "new_theme": new_theme}
                )
            
            # Update metrics
            self._metrics.total_theme_switches += 1
            
            self.logger.info(f"Theme changed from {old_theme} to {new_theme}")
            
        except Exception as e:
            self.logger.error(f"Failed to handle theme change: {e}")
    
    def _perform_health_check(self) -> None:
        """Perform application health check"""
        try:
            health_status = {
                'timestamp': datetime.now().isoformat(),
                'mode': self.app_mode.name,
                'managers_healthy': True,
                'memory_usage_mb': self._get_memory_usage_mb(),
                'active_tabs': self._get_active_tab_count(),
                'message_queue_size': self._get_message_queue_size()
            }
            
            # Check manager health
            if self.performance_monitor:
                health_status['performance_healthy'] = self.performance_monitor.is_healthy()
            
            if self.tab_manager:
                health_status['tab_manager_healthy'] = len(self.tab_manager.get_active_tabs()) < self.config.max_parallel_tabs
            
            # Log health status if debug enabled
            if self._debug_enabled:
                self.logger.debug(f"Health check: {health_status}")
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
    
    def _update_metrics(self) -> None:
        """Update application metrics"""
        try:
            if self._startup_time:
                self._metrics.uptime_seconds = (datetime.now() - self._startup_time).total_seconds()
            
            self._metrics.memory_usage_mb = self._get_memory_usage_mb()
            self._metrics.total_tabs_created = self._get_total_tabs_created()
            self._metrics.total_tabs_hibernated = self._get_total_tabs_hibernated()
            self._metrics.total_messages_sent = self._get_total_messages_sent()
            self._metrics.last_metrics_update = datetime.now()
            
            self.metrics_updated.emit(self._metrics)
            
        except Exception as e:
            self.logger.error(f"Failed to update metrics: {e}")
    
    def _get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB"""
        try:
            if self.performance_monitor:
                return self.performance_monitor.get_current_memory_usage() / (1024 * 1024)
            return 0.0
        except Exception:
            return 0.0
    
    def _get_active_tab_count(self) -> int:
        """Get number of active tabs"""
        try:
            if self.tab_manager:
                return len(self.tab_manager.get_active_tabs())
            return 0
        except Exception:
            return 0
    
    def _get_total_tabs_created(self) -> int:
        """Get total tabs created"""
        try:
            if self.tab_manager:
                return self.tab_manager.get_total_tabs_created()
            return 0
        except Exception:
            return 0
    
    def _get_total_tabs_hibernated(self) -> int:
        """Get total tabs hibernated"""
        try:
            if self.tab_manager:
                return self.tab_manager.get_total_tabs_hibernated()
            return 0
        except Exception:
            return 0
    
    def _get_total_messages_sent(self) -> int:
        """Get total messages sent through component bus"""
        try:
            if self.component_bus:
                return self.component_bus.get_total_messages_sent()
            return 0
        except Exception:
            return 0
    
    def _get_message_queue_size(self) -> int:
        """Get current message queue size"""
        try:
            if self.component_bus:
                return self.component_bus.get_queue_size()
            return 0
        except Exception:
            return 0
    
    async def shutdown(self, reason: str = "user_request") -> bool:
        """
        Shutdown the application gracefully
        
        Args:
            reason: Reason for shutdown
            
        Returns:
            True if shutdown successful, False otherwise
        """
        try:
            self._shutdown_time = datetime.now()
            self.app_mode = AppMode.SHUTDOWN
            self.mode_changed.emit("normal", "shutdown")
            
            self.logger.info(f"Starting application shutdown: {reason}")
            
            # Stop monitoring
            self._health_check_timer.stop()
            self._metrics_timer.stop()
            
            # Shutdown managers in reverse order
            if self.tab_manager:
                await self._safe_shutdown_manager(self.tab_manager, "TabLifecycleManager")
            
            if self.component_loader:
                await self._safe_shutdown_manager(self.component_loader, "ComponentLoader")
            
            if self.performance_monitor:
                await self._safe_shutdown_manager(self.performance_monitor, "PerformanceMonitor")
            
            if self.state_manager:
                await self._safe_shutdown_manager(self.state_manager, "StateManager")
            
            if self.i18n_manager:
                await self._safe_shutdown_manager(self.i18n_manager, "I18nManager")
            
            if self.theme_manager:
                await self._safe_shutdown_manager(self.theme_manager, "ThemeManager")
            
            if self.component_bus:
                await self._safe_shutdown_manager(self.component_bus, "ComponentBus")
            
            if self.lifecycle_manager:
                await self._safe_shutdown_manager(self.lifecycle_manager, "LifecycleManager")
            
            # Clear service instances
            self._service_instances.clear()
            self._service_scopes.clear()
            
            # Calculate shutdown time
            shutdown_duration = (datetime.now() - self._shutdown_time).total_seconds() * 1000
            
            self.logger.info(f"Application shutdown completed in {shutdown_duration:.1f}ms")
            return True
            
        except Exception as e:
            self.logger.error(f"Application shutdown failed: {e}")
            self.logger.debug(traceback.format_exc())
            return False
    
    async def _safe_shutdown_manager(self, manager: Any, manager_name: str) -> None:
        """Safely shutdown a manager"""
        try:
            if hasattr(manager, 'shutdown'):
                if asyncio.iscoroutinefunction(manager.shutdown):
                    await manager.shutdown()
                else:
                    manager.shutdown()
            self.logger.info(f"Shutdown {manager_name}")
        except Exception as e:
            self.logger.error(f"Failed to shutdown {manager_name}: {e}")
    
    def get_global_state(self, key: Optional[str] = None) -> Any:
        """Get global application state"""
        if key:
            return self._global_state.get(key)
        return self._global_state.copy()
    
    def set_global_state(self, key: str, value: Any) -> None:
        """Set global application state"""
        old_value = self._global_state.get(key)
        self._global_state[key] = value
        
        # Broadcast state change
        if self.component_bus:
            self.component_bus.broadcast(
                "app_controller", "system", "global_state_changed",
                {"key": key, "old_value": old_value, "new_value": value}
            )
    
    def get_metrics(self) -> AppMetrics:
        """Get current application metrics"""
        return self._metrics
    
    def get_configuration(self) -> AppConfiguration:
        """Get current application configuration"""
        return self.config
    
    def update_configuration(self, updates: Dict[str, Any]) -> bool:
        """Update application configuration"""
        try:
            for key, value in updates.items():
                if hasattr(self.config, key):
                    old_value = getattr(self.config, key)
                    setattr(self.config, key, value)
                    self.configuration_changed.emit(key, value)
                    self.logger.info(f"Configuration updated: {key} = {value} (was {old_value})")
                else:
                    self.logger.warning(f"Unknown configuration key: {key}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update configuration: {e}")
            return False
    
    def export_debug_info(self) -> Dict[str, Any]:
        """Export debug information for troubleshooting"""
        try:
            debug_info = {
                'timestamp': datetime.now().isoformat(),
                'app_mode': self.app_mode.name,
                'configuration': asdict(self.config),
                'metrics': asdict(self._metrics),
                'global_state': self._global_state.copy(),
                'registered_services': list(self._services.keys()),
                'active_service_instances': list(self._service_instances.keys()),
                'error_history': self._error_history[-10:],  # Last 10 errors
                'manager_status': self._get_manager_status()
            }
            
            return debug_info
            
        except Exception as e:
            self.logger.error(f"Failed to export debug info: {e}")
            return {}
    
    def _get_manager_status(self) -> Dict[str, str]:
        """Get status of all managers"""
        status = {}
        
        managers = [
            ('lifecycle_manager', self.lifecycle_manager),
            ('tab_manager', self.tab_manager),
            ('component_bus', self.component_bus),
            ('theme_manager', self.theme_manager),
            ('state_manager', self.state_manager),
            ('performance_monitor', self.performance_monitor),
            ('component_loader', self.component_loader),
            ('i18n_manager', self.i18n_manager)
        ]
        
        for name, manager in managers:
            if manager:
                if hasattr(manager, 'is_running') and callable(manager.is_running):
                    status[name] = "running" if manager.is_running() else "stopped"
                else:
                    status[name] = "active"
            else:
                status[name] = "not_initialized"
        
        return status


# Factory function for easy instantiation
def create_app_controller(config: Optional[AppConfiguration] = None) -> AppController:
    """
    Create a configured AppController instance
    
    Args:
        config: Application configuration
        
    Returns:
        Configured AppController instance
    """
    return AppController(config) 