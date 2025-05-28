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

# Import database manager for core systems integration
try:
    from data.database import get_connection_manager, initialize_database, shutdown_database
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False


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
    def handle_error(self, error: Exception, context: str) -> None:
        """Handle errors in a centralized way"""
        pass


class AppController(IAppController, EventHandler):
    """
    Central App Controller implementing clean architecture principles
    
    Responsibilities:
    - Coordinate between UI and business logic layers
    - Manage application lifecycle
    - Handle inter-component communication via events
    - Provide centralized error handling
    - Manage component registration and dependencies
    """
    
    def __init__(self):
        self._state = ControllerState.UNINITIALIZED
        self._components: Dict[str, Any] = {}
        self._event_bus: Optional[EventBus] = None
        self._config_manager: Optional[ConfigManager] = None
        self._config: Optional[AppConfig] = None
        self._lock = threading.RLock()
        self._logger = logging.getLogger(__name__)
        self._startup_time: Optional[float] = None
        self._error_handlers: List[Callable[[Exception, str], None]] = []
        
        # Component initialization order
        self._init_order = [
            "config_manager",
            "event_bus", 
            "database",
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
                get_connection_manager()
                initialize_database()
            
            self._logger.info("Core systems initialized successfully")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to initialize core systems: {e}")
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
            return ControllerStatus(
                state=self._state,
                components_initialized=list(self._components.keys()),
                active_operations={},  # Will be populated by specific operations
                uptime_seconds=0.0 if not self._startup_time else threading.get_ident() - self._startup_time
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
    
    def handle_error(self, error: Exception, context: str) -> None:
        """
        Handle errors in a centralized way
        
        Args:
            error: Exception that occurred
            context: Context where error occurred
        """
        error_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
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
    
    def handle_event(self, event: Event) -> None:
        """
        Handle events from the event system
        
        Args:
            event: Event to handle
        """
        try:
            # Handle controller-specific events
            if event.event_type == EventType.CONFIG_CHANGED:
                self._handle_config_changed(event)
            elif event.event_type == EventType.ERROR_OCCURRED:
                self._handle_error_event(event)
            
        except Exception as e:
            self._logger.error(f"Error handling event {event.event_type}: {e}")
    
    def _handle_config_changed(self, event: Event) -> None:
        """Handle configuration change events"""
        self._logger.info("Configuration changed, reloading...")
        if self._config_manager:
            self._config_manager._load_config()
            self._config = self._config_manager.config
    
    def _handle_error_event(self, event: Event) -> None:
        """Handle error events"""
        if event.data:
            context = event.data.get("context", "unknown")
            self._logger.warning(f"Error event received from {context}")
    
    def _publish_event(self, event_type: EventType, data: Optional[Dict[str, Any]] = None) -> None:
        """Publish an event through the event system"""
        if self._event_bus:
            event = Event(event_type, "app_controller", data)
            self._event_bus.publish(event)
    
    # Convenience methods for common operations
    def is_ready(self) -> bool:
        """Check if controller is ready for operations"""
        return self._state == ControllerState.READY
    
    def is_running(self) -> bool:
        """Check if controller is in running state"""
        return self._state in [ControllerState.READY, ControllerState.RUNNING]
    
    def get_config(self) -> Optional[AppConfig]:
        """Get current application configuration"""
        return self._config
    
    def get_event_bus(self) -> Optional[EventBus]:
        """Get the event bus instance"""
        return self._event_bus


# Global controller instance
_app_controller: Optional[AppController] = None
_controller_lock = threading.Lock()


def get_app_controller() -> AppController:
    """
    Get the global App Controller instance (singleton)
    
    Returns:
        Global AppController instance
    """
    global _app_controller
    
    with _controller_lock:
        if _app_controller is None:
            _app_controller = AppController()
        return _app_controller


def initialize_app_controller() -> bool:
    """
    Initialize the global App Controller
    
    Returns:
        True if initialization successful
    """
    controller = get_app_controller()
    return controller.initialize()


def shutdown_app_controller() -> bool:
    """
    Shutdown the global App Controller
    
    Returns:
        True if shutdown successful
    """
    global _app_controller
    
    with _controller_lock:
        if _app_controller:
            result = _app_controller.shutdown()
            _app_controller = None
            return result
        return True 