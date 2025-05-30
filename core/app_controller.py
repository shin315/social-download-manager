"""
App Controller for Social Download Manager v2.0

Central coordinator for the application logic following clean architecture principles.
Acts as the interface adapter between the UI and business logic layers.
"""

import threading
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum, auto

from .event_system import EventBus, Event, EventType, EventHandler, get_event_bus
from .config_manager import ConfigManager, AppConfig, get_config_manager
from .constants import AppConstants, ErrorConstants

# Import service layer
from .services import (
    ServiceRegistry, get_service_registry,
    IContentService, IAnalyticsService, IDownloadService,
    ContentDTO, DownloadRequestDTO, AnalyticsDTO
)

# Import database manager for core systems integration
try:
    from data.database import get_connection_manager, initialize_database, shutdown_database
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False

# Import enhanced error management
try:
    from data.models.error_management import (
        ErrorManager, ErrorClassifier, ErrorContext, ErrorCategory, 
        ErrorSeverity, get_user_friendly_message
    )
    ERROR_MANAGEMENT_AVAILABLE = True
except ImportError:
    ERROR_MANAGEMENT_AVAILABLE = False


class ControllerState(Enum):
    """App Controller lifecycle states"""
    UNINITIALIZED = auto()
    INITIALIZING = auto()
    READY = auto()
    RUNNING = auto()
    PAUSED = auto()
    SHUTTING_DOWN = auto()
    SHUTDOWN = auto()
    ERROR = auto()


class ControllerError(Exception):
    """Custom exception for controller-related errors"""
    pass


@dataclass
class ControllerStatus:
    """Current status of the App Controller"""
    state: ControllerState
    components_initialized: List[str]
    active_operations: Dict[str, Any]
    last_error: Optional[str] = None
    uptime_seconds: float = 0.0
    services_registered: List[str] = None


class IAppController(ABC):
    """Interface for the App Controller following clean architecture principles"""
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the controller and all dependencies"""
        pass
    
    @abstractmethod
    def shutdown(self) -> bool:
        """Gracefully shutdown the controller and cleanup resources"""
        pass
    
    @abstractmethod
    def get_status(self) -> ControllerStatus:
        """Get current controller status"""
        pass
    
    @abstractmethod
    def register_component(self, name: str, component: Any) -> bool:
        """Register a component with the controller"""
        pass
    
    @abstractmethod
    def unregister_component(self, name: str) -> bool:
        """Unregister a component from the controller"""
        pass
    
    @abstractmethod
    def get_component(self, name: str) -> Optional[Any]:
        """Get a registered component by name"""
        pass
    
    @abstractmethod
    def handle_error(self, error: Exception, context: str, component: Optional[str] = None) -> None:
        """Handle errors in a centralized way"""
        pass
    
    # Service accessor methods
    @abstractmethod
    def get_content_service(self) -> Optional[IContentService]:
        """Get content service instance"""
        pass
    
    @abstractmethod
    def get_analytics_service(self) -> Optional[IAnalyticsService]:
        """Get analytics service instance"""
        pass
    
    @abstractmethod
    def get_download_service(self) -> Optional[IDownloadService]:
        """Get download service instance"""
        pass


class AppController(IAppController, EventHandler):
    """
    Central App Controller implementing clean architecture principles
    
    Responsibilities:
    - Coordinate between UI and business logic layers
    - Manage application lifecycle
    - Handle inter-component communication via events
    - Provide centralized error handling with enhanced classification
    - Manage component registration and dependencies
    - Provide access to service layer
    """
    
    def __init__(self):
        self._state = ControllerState.UNINITIALIZED
        self._components: Dict[str, Any] = {}
        self._event_bus: Optional[EventBus] = None
        self._config_manager: Optional[ConfigManager] = None
        self._config: Optional[AppConfig] = None
        self._service_registry: Optional[ServiceRegistry] = None
        self._lock = threading.RLock()
        self._logger = logging.getLogger(__name__)
        self._startup_time: Optional[float] = None
        self._error_handlers: List[Callable[[Exception, str], None]] = []
        
        # Enhanced error management
        if ERROR_MANAGEMENT_AVAILABLE:
            self._error_manager = ErrorManager(use_enhanced_classification=True)
            self._logger.info("Enhanced error management system initialized")
        else:
            self._error_manager = None
            self._logger.warning("Enhanced error management not available, using basic error handling")
        
        # Component initialization order
        self._init_order = [
            "config_manager",
            "event_bus", 
            "database",
            "service_registry",
            "services",
            "platform_factory",
            "ui_manager"
        ]
    
    def initialize(self) -> bool:
        """
        Initialize the controller and all core dependencies
        
        Returns:
            True if initialization successful, False otherwise
        """
        with self._lock:
            if self._state != ControllerState.UNINITIALIZED:
                self._logger.warning(f"Controller already initialized (state: {self._state})")
                return self._state == ControllerState.READY
            
            try:
                self._state = ControllerState.INITIALIZING
                self._startup_time = threading.get_ident()  # Simple startup marker
                
                self._logger.info("Initializing App Controller...")
                
                # Initialize core systems
                if not self._initialize_core_systems():
                    raise ControllerError("Failed to initialize core systems")
                
                # Initialize service layer
                if not self._initialize_services():
                    raise ControllerError("Failed to initialize services")
                
                # Register with event system
                self._event_bus.add_handler(self)
                
                # Publish initialization complete event
                self._publish_event(
                    EventType.APP_STARTUP,
                    {"controller_state": self._state.name}
                )
                
                self._state = ControllerState.READY
                self._logger.info("App Controller initialized successfully")
                return True
                
            except Exception as e:
                self._state = ControllerState.ERROR
                self._logger.error(f"Failed to initialize App Controller: {e}")
                self.handle_error(e, "controller_initialization")
                return False
    
    def _initialize_core_systems(self) -> bool:
        """Initialize core application systems"""
        try:
            # Initialize configuration manager
            self._config_manager = get_config_manager()
            self._config = self._config_manager.config
            self.register_component("config_manager", self._config_manager)
            
            # Initialize event bus
            self._event_bus = get_event_bus()
            self.register_component("event_bus", self._event_bus)
            
            # Initialize database
            if DATABASE_AVAILABLE:
                connection_manager = get_connection_manager()
                initialize_database()
                self.register_component("database", connection_manager)
            
            self._logger.info("Core systems initialized successfully")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to initialize core systems: {e}")
            return False
    
    def _initialize_services(self) -> bool:
        """Initialize service layer and dependency injection"""
        try:
            # Get service registry
            self._service_registry = get_service_registry()
            self.register_component("service_registry", self._service_registry)
            
            # Configure default services
            # configure_services()  # TODO: Implement configure_services function
            
            # Register additional services with database components
            if DATABASE_AVAILABLE:
                # from .services import get_content_service, get_analytics_service, get_download_service
                
                # # Initialize services
                # content_service = get_content_service()
                # analytics_service = get_analytics_service()
                # download_service = get_download_service()
                
                # # Register as components for easy access
                # self.register_component("content_service", content_service)
                # self.register_component("analytics_service", analytics_service)
                # self.register_component("download_service", download_service)
                pass
            
            self._logger.info("Services initialized successfully")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to initialize services: {e}")
            return False
    
    def shutdown(self) -> bool:
        """
        Gracefully shutdown the controller and cleanup resources
        
        Returns:
            True if shutdown successful, False otherwise
        """
        with self._lock:
            if self._state in [ControllerState.SHUTDOWN, ControllerState.SHUTTING_DOWN]:
                return True
            
            try:
                self._state = ControllerState.SHUTTING_DOWN
                self._logger.info("Shutting down App Controller...")
                
                # Publish shutdown event
                if self._event_bus:
                    self._publish_event(
                        EventType.APP_SHUTDOWN,
                        {"controller_state": self._state.name}
                    )
                
                # Dispose services first
                if self._service_registry:
                    self._service_registry.dispose()
                
                # Cleanup components in reverse order
                for component_name in reversed(list(self._components.keys())):
                    self._cleanup_component(component_name)
                
                # Remove from event system
                if self._event_bus:
                    self._event_bus.remove_handler(self)
                
                # Shutdown database
                if DATABASE_AVAILABLE:
                    shutdown_database()
                
                self._state = ControllerState.SHUTDOWN
                self._logger.info("App Controller shutdown complete")
                return True
                
            except Exception as e:
                self._logger.error(f"Error during shutdown: {e}")
                self.handle_error(e, "controller_shutdown")
                return False
    
    def _cleanup_component(self, name: str) -> None:
        """Cleanup a specific component"""
        try:
            component = self._components.get(name)
            if component and hasattr(component, 'cleanup'):
                component.cleanup()
            self.unregister_component(name)
        except Exception as e:
            self._logger.error(f"Error cleaning up component {name}: {e}")
    
    def get_status(self) -> ControllerStatus:
        """Get current controller status"""
        with self._lock:
            services_registered = []
            if self._service_registry:
                services_registered = [
                    service_type.__name__ 
                    for service_type in self._service_registry.get_registered_services()
                ]
            
            return ControllerStatus(
                state=self._state,
                components_initialized=list(self._components.keys()),
                active_operations={},  # Will be populated by specific operations
                uptime_seconds=0.0 if not self._startup_time else threading.get_ident() - self._startup_time,
                services_registered=services_registered
            )
    
    def register_component(self, name: str, component: Any) -> bool:
        """
        Register a component with the controller
        
        Args:
            name: Component identifier
            component: Component instance
            
        Returns:
            True if registration successful
        """
        with self._lock:
            if name in self._components:
                self._logger.warning(f"Component {name} already registered, replacing...")
            
            self._components[name] = component
            self._logger.debug(f"Registered component: {name}")
            return True
    
    def unregister_component(self, name: str) -> bool:
        """
        Unregister a component from the controller
        
        Args:
            name: Component identifier
            
        Returns:
            True if component was found and removed
        """
        with self._lock:
            if name in self._components:
                del self._components[name]
                self._logger.debug(f"Unregistered component: {name}")
                return True
            return False
    
    def get_component(self, name: str) -> Optional[Any]:
        """
        Get a registered component by name
        
        Args:
            name: Component identifier
            
        Returns:
            Component instance or None if not found
        """
        with self._lock:
            return self._components.get(name)
    
    def handle_error(self, error: Exception, context: str, component: Optional[str] = None) -> None:
        """
        Enhanced error handling with classification and recovery
        
        Args:
            error: Exception that occurred
            context: Context where error occurred
            component: Component name where error occurred
        """
        if self._error_manager and ERROR_MANAGEMENT_AVAILABLE:
            # Use enhanced error handling
            error_context = ErrorContext(
                operation=context,
                additional_data={'component': component} if component else {}
            )
            
            try:
                error_info = self._error_manager.handle_error(error, error_context)
                
                # Create enhanced error data for event
                error_data = {
                    "error_id": error_info.error_id,
                    "error_code": error_info.error_code,
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "user_message": error_info.user_message,
                    "category": error_info.category.value,
                    "severity": error_info.severity.value,
                    "recovery_strategy": error_info.recovery_strategy.value,
                    "is_retryable": error_info.is_retryable,
                    "context": context,
                    "component": component,
                    "controller_state": self._state.name,
                    "timestamp": error_info.timestamp.isoformat()
                }
                
                # Log with enhanced details
                self._logger.error(
                    f"Enhanced Error [{error_info.error_code}]: {error_info.message} "
                    f"(Category: {error_info.category.value}, Severity: {error_info.severity.value})"
                )
                
                # Publish enhanced error event
                if self._event_bus:
                    self._publish_event(EventType.ERROR_OCCURRED, error_data)
                
                # Call registered error handlers with enhanced info
                for handler in self._error_handlers:
                    try:
                        handler(error, context)
                    except Exception as handler_error:
                        self._logger.error(f"Error in error handler: {handler_error}")
                
                # Handle recovery if strategy suggests it
                if error_info.recovery_strategy.value == 'ignore':
                    self._logger.info(f"Ignoring error as per recovery strategy: {error_info.message}")
                    return
                
            except Exception as e:
                self._logger.error(f"Error in enhanced error handling: {e}")
                # Fall back to basic error handling
                self._handle_error_basic(error, context, component)
        else:
            # Use basic error handling
            self._handle_error_basic(error, context, component)
    
    def _handle_error_basic(self, error: Exception, context: str, component: Optional[str] = None) -> None:
        """Basic error handling fallback"""
        error_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "component": component,
            "controller_state": self._state.name
        }
        
        # Log the error
        self._logger.error(f"Error in {context}: {error}")
        
        # Publish error event
        if self._event_bus:
            self._publish_event(EventType.ERROR_OCCURRED, error_data)
        
        # Call registered error handlers
        for handler in self._error_handlers:
            try:
                handler(error, context)
            except Exception as handler_error:
                self._logger.error(f"Error in error handler: {handler_error}")
    
    def add_error_handler(self, handler: Callable[[Exception, str], None]) -> None:
        """Add an error handler callback"""
        if handler not in self._error_handlers:
            self._error_handlers.append(handler)
    
    def remove_error_handler(self, handler: Callable[[Exception, str], None]) -> bool:
        """Remove an error handler callback"""
        try:
            self._error_handlers.remove(handler)
            return True
        except ValueError:
            return False
    
    # Service accessor methods
    
    def get_content_service(self) -> Optional[IContentService]:
        """Get content service instance"""
        if self._service_registry:
            return self._service_registry.try_get_service(IContentService)
        return self.get_component("content_service")
    
    def get_analytics_service(self) -> Optional[IAnalyticsService]:
        """Get analytics service instance"""
        if self._service_registry:
            return self._service_registry.try_get_service(IAnalyticsService)
        return self.get_component("analytics_service")
    
    def get_download_service(self) -> Optional[IDownloadService]:
        """Get download service instance"""
        if self._service_registry:
            return self._service_registry.try_get_service(IDownloadService)
        return self.get_component("download_service")
    
    # High-level business operations using services
    
    async def create_content_from_url(self, url: str, platform: Optional[str] = None) -> Optional[ContentDTO]:
        """
        Create content from URL using content service
        
        Args:
            url: Content URL
            platform: Optional platform hint
            
        Returns:
            Created content DTO or None if failed
        """
        try:
            content_service = self.get_content_service()
            if not content_service:
                self._logger.error("Content service not available")
                return None
            
            # Create content DTO with basic information
            from data.models import PlatformType
            platform_type = None
            if platform:
                try:
                    platform_type = PlatformType(platform.lower())
                except ValueError:
                    pass
            
            content_dto = ContentDTO(
                url=url,
                platform=platform_type,
                status=ContentStatus.PENDING
            )
            
            # Create content via service
            created_content = await content_service.create_content(content_dto)
            
            self._logger.info(f"Content created: {created_content.id} - {created_content.url}")
            
            # Publish event
            if self._event_bus:
                self._publish_event(
                    EventType.CONTENT_CREATED,
                    {"content_id": created_content.id, "url": created_content.url}
                )
            
            return created_content
            
        except Exception as e:
            self._logger.error(f"Failed to create content from URL: {e}")
            self.handle_error(e, "create_content_from_url")
            return None
    
    async def get_analytics_overview(self) -> Optional[AnalyticsDTO]:
        """
        Get analytics overview using analytics service
        
        Returns:
            Analytics DTO or None if failed
        """
        try:
            analytics_service = self.get_analytics_service()
            if not analytics_service:
                self._logger.error("Analytics service not available")
                return None
            
            analytics = await analytics_service.get_analytics_overview()
            return analytics
            
        except Exception as e:
            self._logger.error(f"Failed to get analytics overview: {e}")
            self.handle_error(e, "get_analytics_overview")
            return None
    
    async def start_download(self, url: str, options: Optional[Dict[str, Any]] = None) -> Optional[ContentDTO]:
        """
        Start download using download service
        
        Args:
            url: Content URL to download
            options: Download options
            
        Returns:
            Content DTO or None if failed
        """
        try:
            download_service = self.get_download_service()
            if not download_service:
                self._logger.error("Download service not available")
                return None
            
            # Create download request
            request = DownloadRequestDTO(
                url=url,
                **(options or {})
            )
            
            # Start download
            content = await download_service.start_download(request)
            
            self._logger.info(f"Download started for: {url}")
            
            # Publish event
            if self._event_bus:
                self._publish_event(
                    EventType.DOWNLOAD_STARTED,
                    {"url": url, "content_id": content.id}
                )
            
            return content
            
        except Exception as e:
            self._logger.error(f"Failed to start download: {e}")
            self.handle_error(e, "start_download")
            return None
    
    def handle_event(self, event: Event) -> None:
        """Handle events from the event bus"""
        try:
            if event.event_type == EventType.CONFIG_CHANGED:
                self._handle_config_changed(event)
            elif event.event_type == EventType.ERROR_OCCURRED:
                self._handle_error_event(event)
            # Add more event handlers as needed
            
        except Exception as e:
            self._logger.error(f"Error handling event {event.event_type}: {e}")
    
    def _handle_config_changed(self, event: Event) -> None:
        """Handle configuration change events"""
        self._logger.info("Configuration changed, reloading...")
        # TODO: Implement configuration reload logic
    
    def _handle_error_event(self, event: Event) -> None:
        """Handle error events"""
        error_data = event.data or {}
        self._logger.warning(f"Error event received: {error_data}")
    
    def _publish_event(self, event_type: EventType, data: Optional[Dict[str, Any]] = None) -> None:
        """Publish an event to the event bus"""
        if self._event_bus:
            event = Event(event_type, data)
            self._event_bus.publish(event)
    
    def is_ready(self) -> bool:
        """Check if controller is ready"""
        return self._state == ControllerState.READY
    
    def is_running(self) -> bool:
        """Check if controller is running"""
        return self._state == ControllerState.RUNNING
    
    def get_config(self) -> Optional[AppConfig]:
        """Get application configuration"""
        return self._config
    
    def get_event_bus(self) -> Optional[EventBus]:
        """Get event bus instance"""
        return self._event_bus
    
    def get_service_registry(self) -> Optional[ServiceRegistry]:
        """Get service registry instance"""
        return self._service_registry

    def get_error_statistics(self) -> Optional[Dict[str, int]]:
        """Get error statistics from the error manager"""
        if self._error_manager:
            return self._error_manager.get_error_statistics()
        return None
    
    def get_error_statistics_by_category(self) -> Optional[Dict[str, int]]:
        """Get error statistics grouped by category"""
        if self._error_manager:
            return self._error_manager.get_error_statistics_by_category()
        return None
    
    def get_error_statistics_by_component(self) -> Optional[Dict[str, int]]:
        """Get error statistics grouped by component"""
        if self._error_manager:
            return self._error_manager.get_error_statistics_by_component()
        return None
    
    def clear_error_statistics(self) -> None:
        """Clear error statistics"""
        if self._error_manager:
            self._error_manager.clear_statistics()
    
    def execute_with_error_recovery(self, operation: Callable, context: str, component: Optional[str] = None) -> Any:
        """Execute operation with automatic error handling and recovery"""
        if self._error_manager and ERROR_MANAGEMENT_AVAILABLE:
            error_context = ErrorContext(
                operation=context,
                additional_data={'component': component} if component else {}
            )
            try:
                return self._error_manager.execute_with_recovery(operation, error_context)
            except Exception as e:
                self.handle_error(e, context, component)
                raise
        else:
            # Basic execution without recovery
            try:
                return operation()
            except Exception as e:
                self.handle_error(e, context, component)
                raise


# Global controller instance
_app_controller: Optional[AppController] = None
_controller_lock = threading.Lock()


def get_app_controller() -> AppController:
    """
    Get the global app controller instance
    
    Returns:
        AppController instance
    """
    global _app_controller
    if _app_controller is None:
        with _controller_lock:
            if _app_controller is None:
                _app_controller = AppController()
    return _app_controller


def initialize_app_controller() -> bool:
    """
    Initialize the global app controller
    
    Returns:
        True if initialization successful
    """
    controller = get_app_controller()
    return controller.initialize()


def shutdown_app_controller() -> bool:
    """
    Shutdown the global app controller
    
    Returns:
        True if shutdown successful
    """
    global _app_controller
    if _app_controller:
        result = _app_controller.shutdown()
        _app_controller = None
        return result
    return True 