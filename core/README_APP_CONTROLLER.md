# App Controller Documentation

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [API Reference](#api-reference)
5. [Usage Examples](#usage-examples)
6. [Integration Guide](#integration-guide)
7. [Extension Guidelines](#extension-guidelines)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

## Overview

The App Controller is the central coordinator for the Social Download Manager application, implementing clean architecture principles. It acts as the interface adapter between the UI and business logic layers, providing:

- **Centralized component management** and lifecycle coordination
- **Event-driven communication** between application layers
- **Service layer integration** for business operations
- **Error handling and recovery** mechanisms
- **Configuration management** access
- **Thread-safe operations** for concurrent access

### Key Benefits

- ✅ **Clean separation of concerns** - UI, business logic, and data layers remain independent
- ✅ **Testable architecture** - All components can be mocked and tested in isolation
- ✅ **Extensible design** - Easy to add new components and services
- ✅ **Robust error handling** - Centralized error management with recovery strategies
- ✅ **Event-driven** - Loose coupling between components via event system

## Architecture

The App Controller follows **Clean Architecture** principles, positioned in the **Interface Adapters** layer:

```
┌─────────────────────────────────────────────────────────────┐
│                     External Interfaces                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │     UI      │  │  Database   │  │   External APIs     │  │
│  │ Components  │  │   Layer     │  │  (Platform APIs)    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                             │
┌─────────────────────────────────────────────────────────────┐
│                  Interface Adapters Layer                   │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              🎯 APP CONTROLLER                          │ │
│  │   • Component Lifecycle Management                     │ │
│  │   • Event Coordination & Communication                 │ │
│  │   • Service Layer Integration                          │ │
│  │   • Error Handling & Recovery                          │ │
│  │   • Configuration Management                           │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                             │
┌─────────────────────────────────────────────────────────────┐
│                   Application Core Layer                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Service   │  │   Domain    │  │    Use Cases        │  │
│  │   Layer     │  │   Models    │  │   (Business Logic)  │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Dependency Flow

The dependency rule ensures that arrows point **inward** toward the application core:

- **UI Components** → **App Controller** → **Services** → **Domain Models**
- **External APIs** → **Platform Adapters** → **Services** → **Use Cases**
- **Database** → **Repository Layer** → **Services** → **Domain Models**

## Core Components

### 1. AppController Class

The main controller implementation providing:

```python
class AppController(IAppController, EventHandler):
    """Central coordinator implementing clean architecture principles"""
    
    # Core responsibilities:
    # - Component lifecycle management
    # - Event system integration
    # - Service layer access
    # - Error handling and recovery
    # - Configuration management
```

### 2. ControllerState Enum

Manages controller lifecycle states:

```python
class ControllerState(Enum):
    UNINITIALIZED = auto()  # Initial state
    INITIALIZING = auto()   # During startup
    READY = auto()          # Fully operational
    RUNNING = auto()        # Processing operations
    PAUSED = auto()         # Temporarily suspended
    SHUTTING_DOWN = auto()  # During shutdown
    SHUTDOWN = auto()       # Fully shut down
    ERROR = auto()          # Error state requiring intervention
```

### 3. Component Registry

Thread-safe component management:

```python
# Internal component registry
self._components: Dict[str, Any] = {}
self._lock = threading.RLock()
```

### 4. Service Integration

Direct access to business services:

```python
# Service layer integration
self._service_registry: Optional[ServiceRegistry] = None

# Service accessors
def get_content_service(self) -> Optional[IContentService]
def get_analytics_service(self) -> Optional[IAnalyticsService]  
def get_download_service(self) -> Optional[IDownloadService]
```

## API Reference

### Initialization and Lifecycle

#### `initialize() -> bool`

Initializes the controller and all core dependencies.

```python
controller = get_app_controller()
success = controller.initialize()

if success:
    print("Controller ready for operations")
else:
    print("Initialization failed")
```

**Returns**: `True` if initialization successful, `False` otherwise

**Side Effects**:
- Initializes configuration manager
- Sets up event bus communication
- Connects to database (if available)
- Registers core services
- Publishes `APP_STARTUP` event

#### `shutdown() -> bool`

Gracefully shuts down the controller and cleans up resources.

```python
success = controller.shutdown()

if success:
    print("Controller shut down cleanly")
else:
    print("Shutdown encountered errors")
```

**Returns**: `True` if shutdown successful, `False` otherwise

**Side Effects**:
- Publishes `APP_SHUTDOWN` event
- Disposes all registered services
- Cleans up components in reverse order
- Disconnects from database
- Final state set to `SHUTDOWN`

#### `get_status() -> ControllerStatus`

Returns current controller status and statistics.

```python
status = controller.get_status()

print(f"State: {status.state}")
print(f"Components: {status.components_initialized}")
print(f"Uptime: {status.uptime_seconds:.1f}s")
print(f"Services: {status.services_registered}")
```

### Component Management

#### `register_component(name: str, component: Any) -> bool`

Registers a component with the controller.

```python
# Register UI component
ui_component = MyUIComponent()
success = controller.register_component("main_window", ui_component)

# Register custom service
custom_service = MyCustomService()
success = controller.register_component("custom_service", custom_service)
```

**Parameters**:
- `name`: Unique component identifier
- `component`: Component instance to register

**Returns**: `True` if registration successful

#### `unregister_component(name: str) -> bool`

Unregisters a component from the controller.

```python
success = controller.unregister_component("main_window")
```

**Returns**: `True` if component was found and removed

#### `get_component(name: str) -> Optional[Any]`

Retrieves a registered component by name.

```python
ui_component = controller.get_component("main_window")
if ui_component:
    ui_component.show_message("Controller is ready!")
```

**Returns**: Component instance or `None` if not found

### Service Access

#### `get_content_service() -> Optional[IContentService]`

Returns the content service for content operations.

```python
content_service = controller.get_content_service()
if content_service:
    content = await content_service.create_content(content_dto)
```

#### `get_analytics_service() -> Optional[IAnalyticsService]`

Returns the analytics service for statistics and reporting.

```python
analytics_service = controller.get_analytics_service()
if analytics_service:
    overview = await analytics_service.get_analytics_overview()
```

#### `get_download_service() -> Optional[IDownloadService]`

Returns the download service for download operations.

```python
download_service = controller.get_download_service()
if download_service:
    result = await download_service.start_download(request_dto)
```

### High-Level Business Operations

#### `create_content_from_url(url: str, platform: Optional[str] = None) -> Optional[ContentDTO]`

Creates content from URL using the content service.

```python
content = await controller.create_content_from_url(
    "https://www.tiktok.com/@user/video/123",
    platform="tiktok"
)

if content:
    print(f"Created content: {content.id}")
```

#### `get_analytics_overview() -> Optional[AnalyticsDTO]`

Gets analytics overview using the analytics service.

```python
analytics = await controller.get_analytics_overview()
if analytics:
    print(f"Total downloads: {analytics.total_downloads}")
```

#### `start_download(url: str, options: Optional[Dict[str, Any]] = None) -> Optional[ContentDTO]`

Starts download using the download service.

```python
content = await controller.start_download(
    "https://youtube.com/watch?v=123",
    options={"quality": "720p", "format": "mp4"}
)

if content:
    print(f"Download started: {content.id}")
```

### Error Handling

#### `handle_error(error: Exception, context: str) -> None`

Centralized error handling with logging and event publishing.

```python
try:
    # Some operation that might fail
    risky_operation()
except Exception as e:
    controller.handle_error(e, "risky_operation")
```

#### `add_error_handler(handler: Callable[[Exception, str], None]) -> None`

Adds custom error handler callback.

```python
def my_error_handler(error: Exception, context: str):
    print(f"Custom error handling: {error} in {context}")

controller.add_error_handler(my_error_handler)
```

### Event Handling

The controller implements `EventHandler` interface for event system integration:

```python
def handle_event(self, event: Event) -> None:
    """Handle events from the event bus"""
    if event.event_type == EventType.CONFIG_CHANGED:
        self._handle_config_changed(event)
    elif event.event_type == EventType.ERROR_OCCURRED:
        self._handle_error_event(event)
```

### Configuration Access

#### `get_config() -> Optional[AppConfig]`

Returns current application configuration.

```python
config = controller.get_config()
if config:
    print(f"Debug mode: {config.debug}")
    print(f"Max concurrent: {config.max_concurrent_downloads}")
```

## Usage Examples

### Basic Controller Setup

```python
from core.app_controller import get_app_controller, initialize_app_controller

# Initialize controller
success = initialize_app_controller()
if not success:
    print("Failed to initialize controller")
    exit(1)

# Get controller instance
controller = get_app_controller()

# Check status
status = controller.get_status()
print(f"Controller state: {status.state}")
```

### UI Component Integration

```python
from PyQt6.QtWidgets import QMainWindow
from core.app_controller import get_app_controller
from core.event_system import EventHandler, Event, EventType

class MainWindow(QMainWindow, EventHandler):
    """Main UI window with controller integration"""
    
    def __init__(self):
        super().__init__()
        self.controller = get_app_controller()
        
        # Register with controller
        self.controller.register_component("main_window", self)
        
        # Subscribe to events
        event_bus = self.controller.get_event_bus()
        if event_bus:
            event_bus.add_handler(self)
    
    def handle_event(self, event: Event):
        """Handle events from controller"""
        if event.event_type == EventType.DOWNLOAD_STARTED:
            self.update_download_status(event.data)
        elif event.event_type == EventType.ERROR_OCCURRED:
            self.show_error_message(event.data.get('error_message'))
    
    def closeEvent(self, event):
        """Clean shutdown when window closes"""
        # Unregister from controller
        self.controller.unregister_component("main_window")
        
        # Remove from event system
        event_bus = self.controller.get_event_bus()
        if event_bus:
            event_bus.remove_handler(self)
        
        super().closeEvent(event)
```

### Service Integration

```python
import asyncio
from core.app_controller import get_app_controller

async def download_content_example():
    """Example of using controller for content operations"""
    controller = get_app_controller()
    
    # Ensure controller is ready
    if not controller.is_ready():
        print("Controller not ready")
        return
    
    try:
        # Create content from URL
        content = await controller.create_content_from_url(
            "https://www.tiktok.com/@user/video/123456789",
            platform="tiktok"
        )
        
        if content:
            print(f"Content created: {content.title}")
            
            # Start download
            download_result = await controller.start_download(
                content.url,
                options={
                    "quality": "best",
                    "format": "mp4",
                    "output_dir": "./downloads"
                }
            )
            
            if download_result:
                print(f"Download started for: {download_result.title}")
            else:
                print("Failed to start download")
        else:
            print("Failed to create content")
            
    except Exception as e:
        print(f"Error during download: {e}")

# Run the example
asyncio.run(download_content_example())
```

### Custom Component Registration

```python
from core.app_controller import get_app_controller
from core.event_system import EventHandler, Event, EventType

class CustomAnalyticsComponent(EventHandler):
    """Custom component for analytics tracking"""
    
    def __init__(self):
        self.download_count = 0
        self.error_count = 0
        
    def handle_event(self, event: Event):
        """Track analytics events"""
        if event.event_type == EventType.DOWNLOAD_STARTED:
            self.download_count += 1
        elif event.event_type == EventType.ERROR_OCCURRED:
            self.error_count += 1
    
    def get_stats(self) -> dict:
        """Return current statistics"""
        return {
            "downloads": self.download_count,
            "errors": self.error_count,
            "success_rate": (
                (self.download_count - self.error_count) / max(self.download_count, 1) * 100
            )
        }
    
    def cleanup(self):
        """Cleanup when component is removed"""
        print("Analytics component shutting down")

# Register custom component
controller = get_app_controller()
analytics_comp = CustomAnalyticsComponent()

# Register with controller
controller.register_component("custom_analytics", analytics_comp)

# Register with event system
event_bus = controller.get_event_bus()
if event_bus:
    event_bus.add_handler(analytics_comp)

# Later, retrieve and use
analytics_comp = controller.get_component("custom_analytics")
if analytics_comp:
    stats = analytics_comp.get_stats()
    print(f"Success rate: {stats['success_rate']:.1f}%")
```

### Error Handling Integration

```python
from core.app_controller import get_app_controller

def setup_error_handling():
    """Setup custom error handling"""
    controller = get_app_controller()
    
    def ui_error_handler(error: Exception, context: str):
        """Custom error handler for UI notifications"""
        # Get UI component
        main_window = controller.get_component("main_window")
        if main_window and hasattr(main_window, 'show_error'):
            main_window.show_error(f"Error in {context}: {str(error)}")
    
    def log_error_handler(error: Exception, context: str):
        """Custom error handler for detailed logging"""
        import logging
        logger = logging.getLogger("app_errors")
        logger.error(f"Context: {context}, Error: {error}", exc_info=True)
    
    # Register error handlers
    controller.add_error_handler(ui_error_handler)
    controller.add_error_handler(log_error_handler)

# Setup error handling
setup_error_handling()
```

## Integration Guide

### Step 1: Controller Initialization

```python
# main.py or application entry point
from core.app_controller import initialize_app_controller, get_app_controller

def main():
    # Initialize controller first
    if not initialize_app_controller():
        print("Failed to initialize application controller")
        return 1
    
    # Get controller instance
    controller = get_app_controller()
    
    # Application is ready
    print("Application controller initialized successfully")
    return 0

if __name__ == "__main__":
    exit(main())
```

### Step 2: UI Component Integration

```python
# For Qt Applications
from PyQt6.QtWidgets import QApplication
from core.app_controller import get_app_controller

class Application(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        
        # Get controller
        self.controller = get_app_controller()
        
        # Register application with controller
        self.controller.register_component("qt_app", self)
        
    def closeEvent(self):
        """Clean shutdown"""
        # Shutdown controller
        self.controller.shutdown()
```

### Step 3: Service Layer Connection

The controller automatically connects to available services. To add custom services:

```python
from core.services import ServiceRegistry
from core.app_controller import get_app_controller

# Get service registry from controller
controller = get_app_controller()
service_registry = controller.get_service_registry()

if service_registry:
    # Register custom service
    service_registry.register_service(IMyCustomService, MyCustomServiceImpl())
    
    # Register as component for easy access
    controller.register_component("my_service", service_registry.get_service(IMyCustomService))
```

### Step 4: Event System Integration

```python
from core.event_system import Event, EventType
from core.app_controller import get_app_controller

def send_custom_event():
    """Example of sending custom events through controller"""
    controller = get_app_controller()
    event_bus = controller.get_event_bus()
    
    if event_bus:
        # Create custom event
        event = Event(
            EventType.CONTENT_CREATED,
            {
                "content_id": 123,
                "url": "https://example.com/video",
                "platform": "custom"
            }
        )
        
        # Publish through event bus
        event_bus.publish(event)
```

## Extension Guidelines

### Adding New Components

1. **Implement Required Interfaces**:

```python
class MyCustomComponent:
    """Custom component following controller patterns"""
    
    def initialize(self) -> bool:
        """Optional: Initialize component"""
        return True
    
    def cleanup(self) -> None:
        """Optional: Cleanup resources"""
        pass
```

2. **Register with Controller**:

```python
controller = get_app_controller()
component = MyCustomComponent()

# Initialize if needed
if hasattr(component, 'initialize'):
    if not component.initialize():
        print("Component initialization failed")
        return

# Register with controller
controller.register_component("my_component", component)
```

3. **Event Integration** (if needed):

```python
from core.event_system import EventHandler

class MyEventAwareComponent(EventHandler):
    """Component that responds to events"""
    
    def handle_event(self, event: Event):
        """Handle relevant events"""
        if event.event_type == EventType.CONFIG_CHANGED:
            self.reload_configuration()
```

### Adding New Services

1. **Define Service Interface**:

```python
from abc import ABC, abstractmethod

class IMyCustomService(ABC):
    """Interface for custom service"""
    
    @abstractmethod
    async def do_custom_operation(self, data: dict) -> bool:
        """Perform custom operation"""
        pass
```

2. **Implement Service**:

```python
class MyCustomService(IMyCustomService):
    """Custom service implementation"""
    
    async def do_custom_operation(self, data: dict) -> bool:
        """Implementation of custom operation"""
        # Service logic here
        return True
```

3. **Register with Service Registry**:

```python
from core.services import get_service_registry

service_registry = get_service_registry()
service_registry.register_service(IMyCustomService, MyCustomService())
```

4. **Add Controller Access Method**:

```python
# Extend AppController class (or create wrapper)
def get_my_custom_service(self) -> Optional[IMyCustomService]:
    """Get custom service instance"""
    if self._service_registry:
        return self._service_registry.try_get_service(IMyCustomService)
    return self.get_component("my_custom_service")
```

### Adding New Event Types

1. **Extend EventType Enum**:

```python
from core.event_system import EventType

# Add new event types to EventType enum in event_system.py
class EventType(Enum):
    # Existing events...
    MY_CUSTOM_EVENT = "my_custom_event"
    ANOTHER_CUSTOM_EVENT = "another_custom_event"
```

2. **Handle in Controller** (if needed):

```python
def handle_event(self, event: Event) -> None:
    """Extended event handling in AppController"""
    if event.event_type == EventType.MY_CUSTOM_EVENT:
        self._handle_my_custom_event(event)
    # ... existing handlers
    
def _handle_my_custom_event(self, event: Event) -> None:
    """Handle custom event"""
    # Custom event handling logic
    pass
```

## Best Practices

### 1. Component Lifecycle Management

```python
# ✅ DO: Proper component lifecycle
class MyComponent:
    def __init__(self):
        self.initialized = False
        self.resources = []
    
    def initialize(self) -> bool:
        """Initialize component resources"""
        try:
            # Setup resources
            self.resources = self._setup_resources()
            self.initialized = True
            return True
        except Exception as e:
            print(f"Failed to initialize: {e}")
            return False
    
    def cleanup(self) -> None:
        """Clean up resources"""
        for resource in self.resources:
            try:
                resource.close()
            except Exception as e:
                print(f"Error cleaning up resource: {e}")
        self.resources.clear()
        self.initialized = False

# ❌ DON'T: Skip cleanup or initialization
class BadComponent:
    def __init__(self):
        # Don't open resources in constructor
        self.file = open("some_file.txt")  # ❌ No cleanup
```

### 2. Error Handling

```python
# ✅ DO: Use controller error handling
async def safe_operation():
    controller = get_app_controller()
    try:
        result = await risky_operation()
        return result
    except Exception as e:
        controller.handle_error(e, "safe_operation")
        return None

# ❌ DON'T: Silent failures
async def unsafe_operation():
    try:
        return await risky_operation()
    except:
        return None  # ❌ Silent failure
```

### 3. Event Usage

```python
# ✅ DO: Use events for loose coupling
class UIComponent(EventHandler):
    def handle_event(self, event: Event):
        if event.event_type == EventType.DOWNLOAD_PROGRESS:
            self.update_progress(event.data.get('progress', 0))

# ❌ DON'T: Direct component coupling
class BadUIComponent:
    def __init__(self, download_service):
        self.download_service = download_service  # ❌ Tight coupling
        self.download_service.add_callback(self.update_progress)
```

### 4. Service Access

```python
# ✅ DO: Use controller service accessors
async def download_content(url: str):
    controller = get_app_controller()
    download_service = controller.get_download_service()
    
    if download_service:
        return await download_service.start_download(url)
    else:
        print("Download service not available")
        return None

# ❌ DON'T: Direct service instantiation
async def bad_download_content(url: str):
    service = DownloadService()  # ❌ Bypass controller
    return await service.start_download(url)
```

### 5. Thread Safety

```python
# ✅ DO: Use controller for thread-safe operations
def worker_thread():
    controller = get_app_controller()
    
    # Controller methods are thread-safe
    component = controller.get_component("shared_component")
    if component:
        component.do_work()

# ❌ DON'T: Access components directly across threads
shared_component = None  # ❌ Global state

def bad_worker_thread():
    global shared_component
    if shared_component:  # ❌ Not thread-safe
        shared_component.do_work()
```

## Troubleshooting

### Common Issues

#### 1. Controller Not Initializing

**Symptoms**: `initialize()` returns `False`

**Possible Causes**:
- Missing dependencies (config manager, event bus)
- Database connection failures
- Service registration failures

**Solutions**:
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check individual systems
try:
    from core.config_manager import get_config_manager
    config_manager = get_config_manager()
    print("Config manager: OK")
except Exception as e:
    print(f"Config manager failed: {e}")

try:
    from core.event_system import get_event_bus
    event_bus = get_event_bus()
    print("Event bus: OK")
except Exception as e:
    print(f"Event bus failed: {e}")
```

#### 2. Components Not Responding

**Symptoms**: Registered components not receiving events

**Possible Causes**:
- Component not registered with event bus
- Event handler not implemented correctly
- Event bus not initialized

**Solutions**:
```python
# Verify component registration
controller = get_app_controller()
component = controller.get_component("my_component")

if component:
    print("Component registered")
    
    # Check event handler registration
    event_bus = controller.get_event_bus()
    if event_bus and hasattr(component, 'handle_event'):
        event_bus.add_handler(component)
        print("Event handler registered")
```

#### 3. Service Not Available

**Symptoms**: `get_*_service()` returns `None`

**Possible Causes**:
- Service not registered
- Service registry not initialized
- Dependency injection failed

**Solutions**:
```python
# Check service registry
controller = get_app_controller()
service_registry = controller.get_service_registry()

if service_registry:
    # List registered services
    services = service_registry.get_registered_services()
    print(f"Registered services: {[s.__name__ for s in services]}")
else:
    print("Service registry not available")
```

#### 4. Memory Leaks

**Symptoms**: Memory usage increasing over time

**Possible Causes**:
- Components not properly cleaned up
- Event handlers not removed
- Circular references

**Solutions**:
```python
# Proper cleanup in component
class ProperComponent:
    def __init__(self):
        self.event_handlers = []
    
    def cleanup(self):
        # Remove event handlers
        controller = get_app_controller()
        event_bus = controller.get_event_bus()
        
        if event_bus:
            for handler in self.event_handlers:
                event_bus.remove_handler(handler)
        
        self.event_handlers.clear()
```

### Debug Helpers

```python
def debug_controller_state():
    """Debug helper to check controller state"""
    controller = get_app_controller()
    status = controller.get_status()
    
    print(f"Controller State: {status.state}")
    print(f"Components: {status.components_initialized}")
    print(f"Services: {status.services_registered}")
    print(f"Uptime: {status.uptime_seconds:.1f}s")
    
    # Check each component
    for component_name in status.components_initialized:
        component = controller.get_component(component_name)
        print(f"  {component_name}: {type(component).__name__}")

def debug_event_system():
    """Debug helper to check event system"""
    controller = get_app_controller()
    event_bus = controller.get_event_bus()
    
    if event_bus:
        print(f"Event bus active: {event_bus}")
        # Add more debugging as needed
    else:
        print("Event bus not available")
```

---

## Conclusion

The App Controller provides a robust, clean architecture foundation for the Social Download Manager application. By following the patterns and examples in this documentation, you can:

- Build maintainable, testable applications
- Ensure proper separation of concerns
- Handle errors gracefully
- Extend functionality without breaking existing code
- Maintain thread safety across concurrent operations

For additional examples and advanced usage patterns, refer to the test files in `tests/test_app_controller*.py` which demonstrate comprehensive controller usage scenarios. 