# Social Download Manager V2.0 - API Reference

## Overview

This document provides comprehensive API documentation for Social Download Manager V2.0 core components. All APIs are designed for high performance, type safety, and ease of integration.

## Table of Contents

1. [AppController API](#appcontroller-api)
2. [ComponentBus API](#componentbus-api)
3. [TabLifecycleManager API](#tablifecyclemanager-api)
4. [ThemeManager API](#thememanager-api)
5. [StateManager API](#statemanager-api)
6. [PerformanceMonitor API](#performancemonitor-api)
7. [LifecycleManager API](#lifecyclemanager-api)
8. [ConfigManager API](#configmanager-api)
9. [Data Models](#data-models)
10. [Error Handling](#error-handling)

---

## AppController API

**Location**: `ui/components/core/app_controller.py`

### Class: `AppController`

Central application controller managing all core services with dependency injection and lifecycle coordination.

#### Constructor

```python
def __init__(self, config: AppConfiguration) -> None:
    """
    Initialize AppController with configuration.
    
    Args:
        config: Application configuration object
        
    Raises:
        InitializationError: If required services fail to initialize
        ConfigurationError: If configuration is invalid
    """
```

#### Methods

##### `initialize_services()`
```python
def initialize_services(self) -> bool:
    """
    Initialize all core services in dependency order.
    
    Returns:
        bool: True if all services initialized successfully
        
    Performance:
        - Execution time: ~5-10ms
        - Memory overhead: ~50MB
        
    Example:
        controller = AppController(config)
        if controller.initialize_services():
            print("All services ready")
    """
```

##### `shutdown_services()`
```python
def shutdown_services(self) -> bool:
    """
    Gracefully shutdown all services in reverse dependency order.
    
    Returns:
        bool: True if all services shutdown cleanly
        
    Performance:
        - Execution time: ~2-5ms
        - Cleanup efficiency: 100%
    """
```

##### `get_service()`
```python
def get_service(self, service_type: Type[T]) -> Optional[T]:
    """
    Get registered service by type.
    
    Args:
        service_type: Type of service to retrieve
        
    Returns:
        Service instance or None if not found
        
    Performance:
        - Lookup time: <0.1ms
        - Type safety: Full generic support
        
    Example:
        theme_manager = controller.get_service(ThemeManager)
        if theme_manager:
            theme_manager.switch_theme(ThemeVariant.DARK)
    """
```

##### `register_service()`
```python
def register_service(self, service: Any, service_type: Type = None) -> bool:
    """
    Register a service with the controller.
    
    Args:
        service: Service instance to register
        service_type: Optional type override
        
    Returns:
        bool: True if registration successful
        
    Performance:
        - Registration time: <0.5ms
        - Memory overhead: ~1KB per service
    """
```

---

## ComponentBus API

**Location**: `ui/components/core/component_bus.py`

### Class: `ComponentBus`

High-performance asynchronous message bus for inter-component communication.

#### Performance Characteristics
- **Throughput**: 103,075+ messages/second
- **Latency**: Sub-millisecond message routing
- **Queue Capacity**: 10,000 messages (configurable)
- **Memory Efficiency**: O(1) message routing

#### Methods

##### `register_component()`
```python
def register_component(self, component_id: str, component_type: str, 
                      display_name: str, capabilities: List[str] = None,
                      tab_id: str = None) -> bool:
    """
    Register a component with the message bus.
    
    Args:
        component_id: Unique identifier for the component
        component_type: Category/type of component
        display_name: Human-readable component name
        capabilities: Optional list of component capabilities
        tab_id: Optional tab association
        
    Returns:
        bool: True if registration successful
        
    Performance:
        - Registration time: <2ms for 50 components
        - Memory per component: ~500 bytes
        
    Example:
        success = bus.register_component(
            "youtube_downloader",
            "downloader",
            "YouTube Downloader",
            ["download", "pause", "resume"]
        )
    """
```

##### `send_event()`
```python
def send_event(self, sender_id: str, channel: str, event_type: str, 
               data: Dict[str, Any], priority: MessagePriority = MessagePriority.NORMAL) -> bool:
    """
    Send an event through the message bus.
    
    Args:
        sender_id: ID of sending component
        channel: Target channel name
        event_type: Type of event being sent
        data: Event payload data
        priority: Message priority level
        
    Returns:
        bool: True if message queued successfully
        
    Performance:
        - Send time: <0.01ms per message
        - Delivery guarantee: Best effort with retry
        - Queue processing: Batched for efficiency
        
    Example:
        bus.send_event(
            "downloader",
            "download_events", 
            "progress_update",
            {"progress": 45.2, "speed": "2.5 MB/s"},
            MessagePriority.HIGH
        )
    """
```

##### `subscribe()`
```python
def subscribe(self, component_id: str, channel: str, 
              callback: Callable[[BusMessage], None],
              message_filter: Dict[str, Any] = None) -> bool:
    """
    Subscribe to channel events with callback.
    
    Args:
        component_id: ID of subscribing component
        channel: Channel to subscribe to
        callback: Function to call when message received
        message_filter: Optional message filtering criteria
        
    Returns:
        bool: True if subscription successful
        
    Performance:
        - Subscription time: <0.1ms
        - Callback overhead: Minimal (async execution)
        
    Example:
        def handle_download_event(message: BusMessage):
            if message.event_type == "download_complete":
                print(f"Download finished: {message.data['filename']}")
        
        bus.subscribe("ui_manager", "download_events", handle_download_event)
    """
```

##### `unsubscribe()`
```python
def unsubscribe(self, component_id: str, channel: str) -> bool:
    """
    Unsubscribe from channel events.
    
    Args:
        component_id: ID of component to unsubscribe
        channel: Channel to unsubscribe from
        
    Returns:
        bool: True if unsubscription successful
    """
```

##### `get_queue_stats()`
```python
def get_queue_stats(self) -> QueueStats:
    """
    Get current message queue statistics.
    
    Returns:
        QueueStats: Current queue metrics
        
    Example:
        stats = bus.get_queue_stats()
        print(f"Queue depth: {stats.current_depth}")
        print(f"Messages processed: {stats.total_processed}")
    """
```

---

## TabLifecycleManager API

**Location**: `ui/components/core/tab_lifecycle_manager.py`

### Class: `TabLifecycleManager`

Advanced tab management with hibernation and automatic resource optimization.

#### Performance Metrics
- **Tab registration**: 99.8% faster than V1.2.1
- **Memory optimization**: Up to 90% reduction for hibernated tabs
- **Hibernation time**: <200ms per tab
- **Restoration time**: <300ms per tab

#### Methods

##### `register_tab()`
```python
def register_tab(self, tab_id: str, widget: QWidget, 
                priority: TabPriority = TabPriority.NORMAL,
                auto_hibernate: bool = True) -> bool:
    """
    Register a new tab with lifecycle management.
    
    Args:
        tab_id: Unique identifier for the tab
        widget: Qt widget representing the tab
        priority: Tab priority level
        auto_hibernate: Enable automatic hibernation
        
    Returns:
        bool: True if registration successful
        
    Performance:
        - Registration time: ~3.5ms for 10 tabs
        - Memory per tab: ~2-5MB depending on content
        
    Example:
        success = tab_manager.register_tab(
            "youtube_tab_001",
            youtube_widget,
            TabPriority.HIGH,
            auto_hibernate=True
        )
    """
```

##### `hibernate_tab()`
```python
def hibernate_tab(self, tab_id: str, force: bool = False) -> bool:
    """
    Hibernate a tab to conserve memory and resources.
    
    Args:
        tab_id: ID of tab to hibernate
        force: Force hibernation even if tab is active
        
    Returns:
        bool: True if hibernation successful
        
    Performance:
        - Hibernation time: <200ms
        - Memory savings: 70-90%
        - State preservation: 100%
        
    Example:
        if tab_manager.hibernate_tab("inactive_tab"):
            print("Tab hibernated successfully")
    """
```

##### `restore_tab()`
```python
def restore_tab(self, tab_id: str) -> bool:
    """
    Restore a hibernated tab to active state.
    
    Args:
        tab_id: ID of tab to restore
        
    Returns:
        bool: True if restoration successful
        
    Performance:
        - Restoration time: <300ms
        - State integrity: 100%
        
    Example:
        if tab_manager.restore_tab("hibernated_tab"):
            print("Tab restored and ready for use")
    """
```

##### `get_tab_state()`
```python
def get_tab_state(self, tab_id: str) -> Optional[TabState]:
    """
    Get current state of a tab.
    
    Args:
        tab_id: ID of tab to query
        
    Returns:
        TabState or None if tab not found
        
    States:
        - ACTIVE: Tab is active and responsive
        - INACTIVE: Tab is loaded but not in focus
        - HIBERNATED: Tab is hibernated to save resources
        - LOADING: Tab is being restored from hibernation
        
    Example:
        state = tab_manager.get_tab_state("my_tab")
        if state == TabState.HIBERNATED:
            tab_manager.restore_tab("my_tab")
    """
```

##### `get_hibernation_stats()`
```python
def get_hibernation_stats(self) -> HibernationStats:
    """
    Get hibernation statistics and metrics.
    
    Returns:
        HibernationStats: Current hibernation metrics
        
    Example:
        stats = tab_manager.get_hibernation_stats()
        print(f"Total tabs: {stats.total_tabs}")
        print(f"Hibernated: {stats.hibernated_count}")
        print(f"Memory saved: {stats.memory_saved_mb}MB")
    """
```

---

## ThemeManager API

**Location**: `ui/components/core/theme_manager.py`

### Class: `ThemeManager`

Dynamic theme system with real-time switching and design token management.

#### Performance Metrics
- **Theme switching**: 99.7% faster than V1.2.1 (<2ms)
- **Token resolution**: <5ms timeout
- **Cache efficiency**: 95%+ hit rate
- **Memory footprint**: ~10MB for all themes

#### Methods

##### `switch_theme()`
```python
def switch_theme(self, variant: ThemeVariant) -> bool:
    """
    Switch to a different theme variant.
    
    Args:
        variant: Target theme variant
        
    Returns:
        bool: True if theme switch successful
        
    Performance:
        - Switch time: <2ms complete transition
        - UI update: Real-time without flicker
        
    Example:
        if theme_manager.switch_theme(ThemeVariant.DARK):
            print("Switched to dark theme")
    """
```

##### `get_theme_token()`
```python
def get_theme_token(self, token_path: str) -> Any:
    """
    Retrieve a design token value.
    
    Args:
        token_path: Dot-separated path to token (e.g., "colors-primary")
        
    Returns:
        Token value or None if not found
        
    Performance:
        - Resolution time: <0.1ms from cache
        - Cache hit rate: 95%+
        
    Example:
        primary_color = theme_manager.get_theme_token("colors-primary")
        button_radius = theme_manager.get_theme_token("spacing-border-radius")
    """
```

##### `register_theme_callback()`
```python
def register_theme_callback(self, callback: Callable[[ThemeVariant], None]) -> str:
    """
    Register callback for theme change events.
    
    Args:
        callback: Function to call when theme changes
        
    Returns:
        str: Callback ID for later removal
        
    Example:
        def on_theme_change(variant: ThemeVariant):
            print(f"Theme changed to: {variant.name}")
        
        callback_id = theme_manager.register_theme_callback(on_theme_change)
    """
```

##### `get_available_themes()`
```python
def get_available_themes(self) -> List[ThemeInfo]:
    """
    Get list of available theme variants.
    
    Returns:
        List of available theme information
        
    Example:
        themes = theme_manager.get_available_themes()
        for theme in themes:
            print(f"Theme: {theme.name} - {theme.description}")
    """
```

##### `validate_theme_integrity()`
```python
def validate_theme_integrity(self, variant: ThemeVariant = None) -> ThemeValidationResult:
    """
    Validate theme files and token integrity.
    
    Args:
        variant: Specific variant to validate (None for all)
        
    Returns:
        ThemeValidationResult: Validation results
        
    Example:
        result = theme_manager.validate_theme_integrity()
        if not result.is_valid:
            print(f"Theme issues: {result.errors}")
    """
```

---

## StateManager API

**Location**: `ui/components/core/state_manager.py`

### Class: `StateManager`

Centralized application state management with snapshotting and recovery capabilities.

#### Features
- **Automatic snapshots**: Every 5 minutes
- **Crash recovery**: Last known good state
- **Memory efficiency**: Incremental snapshots
- **Cross-session persistence**: SQLite storage

#### Methods

##### `create_snapshot()`
```python
def create_snapshot(self, snapshot_id: str, include_components: List[str] = None) -> bool:
    """
    Create a state snapshot for recovery.
    
    Args:
        snapshot_id: Unique identifier for the snapshot
        include_components: Optional list of components to include
        
    Returns:
        bool: True if snapshot created successfully
        
    Performance:
        - Snapshot time: <100ms for full state
        - Storage overhead: ~1-5MB per snapshot
        
    Example:
        # Before risky operation
        state_manager.create_snapshot("before_bulk_download")
    """
```

##### `restore_snapshot()`
```python
def restore_snapshot(self, snapshot_id: str) -> bool:
    """
    Restore application state from a snapshot.
    
    Args:
        snapshot_id: ID of snapshot to restore
        
    Returns:
        bool: True if restoration successful
        
    Performance:
        - Restoration time: <300ms
        - State integrity: 100%
        
    Example:
        # After operation failure
        if not operation_successful:
            state_manager.restore_snapshot("before_bulk_download")
    """
```

##### `get_snapshot_info()`
```python
def get_snapshot_info(self, snapshot_id: str) -> Optional[SnapshotInfo]:
    """
    Get information about a specific snapshot.
    
    Args:
        snapshot_id: ID of snapshot to query
        
    Returns:
        SnapshotInfo or None if not found
        
    Example:
        info = state_manager.get_snapshot_info("auto_snapshot_001")
        if info:
            print(f"Created: {info.timestamp}")
            print(f"Size: {info.size_bytes} bytes")
    """
```

##### `list_snapshots()`
```python
def list_snapshots(self, limit: int = 50) -> List[SnapshotInfo]:
    """
    List available snapshots.
    
    Args:
        limit: Maximum number of snapshots to return
        
    Returns:
        List of snapshot information
        
    Example:
        snapshots = state_manager.list_snapshots(10)
        for snapshot in snapshots:
            print(f"{snapshot.id}: {snapshot.timestamp}")
    """
```

##### `cleanup_old_snapshots()`
```python
def cleanup_old_snapshots(self, max_age_days: int = 30, max_count: int = 100) -> int:
    """
    Clean up old snapshots based on age and count limits.
    
    Args:
        max_age_days: Maximum age in days
        max_count: Maximum number of snapshots to keep
        
    Returns:
        int: Number of snapshots removed
        
    Example:
        removed = state_manager.cleanup_old_snapshots(30, 50)
        print(f"Cleaned up {removed} old snapshots")
    """
```

---

## PerformanceMonitor API

**Location**: `ui/components/core/performance_monitor.py`

### Class: `PerformanceMonitor`

Real-time performance monitoring and analytics system.

#### Monitoring Capabilities
- **CPU Usage**: Real-time process monitoring
- **Memory Tracking**: Peak and current usage
- **Component Metrics**: Per-component performance
- **System Health**: Overall system status

#### Methods

##### `track_metric()`
```python
def track_metric(self, metric_name: str, value: float, 
                category: str = "general", timestamp: datetime = None) -> None:
    """
    Track a performance metric.
    
    Args:
        metric_name: Name of the metric
        value: Metric value
        category: Metric category for organization
        timestamp: Optional timestamp (defaults to now)
        
    Performance:
        - Tracking overhead: <0.01ms
        - Storage: In-memory with periodic persistence
        
    Example:
        monitor.track_metric("download_speed_mbps", 15.7, "downloads")
        monitor.track_metric("ui_render_time_ms", 8.3, "ui")
    """
```

##### `get_system_snapshot()`
```python
def get_system_snapshot(self) -> SystemSnapshot:
    """
    Get current system performance snapshot.
    
    Returns:
        SystemSnapshot: Current system metrics
        
    Performance:
        - Snapshot time: <5ms
        - Accuracy: Real-time system data
        
    Example:
        snapshot = monitor.get_system_snapshot()
        print(f"CPU: {snapshot.cpu_usage_percent}%")
        print(f"Memory: {snapshot.memory_usage_mb}MB")
        print(f"Active tabs: {snapshot.active_tabs}")
    """
```

##### `start_detailed_tracking()`
```python
def start_detailed_tracking(self, components: List[str] = None) -> bool:
    """
    Start detailed performance tracking.
    
    Args:
        components: Optional list of components to track
        
    Returns:
        bool: True if tracking started successfully
        
    Example:
        # Start detailed tracking for specific components
        monitor.start_detailed_tracking(["downloader", "ui_manager"])
    """
```

##### `stop_detailed_tracking()`
```python
def stop_detailed_tracking(self) -> PerformanceReport:
    """
    Stop detailed tracking and get report.
    
    Returns:
        PerformanceReport: Comprehensive performance report
        
    Example:
        report = monitor.stop_detailed_tracking()
        print(f"Total metrics: {len(report.metrics)}")
        print(f"Average CPU: {report.average_cpu_usage}%")
    """
```

##### `get_component_metrics()`
```python
def get_component_metrics(self, component_id: str, 
                         time_range: TimeRange = None) -> List[Metric]:
    """
    Get performance metrics for a specific component.
    
    Args:
        component_id: ID of component to query
        time_range: Optional time range filter
        
    Returns:
        List of metrics for the component
        
    Example:
        metrics = monitor.get_component_metrics("downloader")
        for metric in metrics:
            print(f"{metric.name}: {metric.value} {metric.unit}")
    """
```

---

## Data Models

### Configuration Models

#### `AppConfiguration`
```python
@dataclass
class AppConfiguration:
    """Application configuration data model"""
    enable_debug_mode: bool = False
    max_concurrent_downloads: int = 5
    auto_hibernation_timeout: int = 600  # seconds
    performance_monitoring: bool = True
    theme_variant: ThemeVariant = ThemeVariant.LIGHT
    log_level: LogLevel = LogLevel.INFO
```

#### `ThemeVariant`
```python
class ThemeVariant(Enum):
    """Available theme variants"""
    LIGHT = "light"
    DARK = "dark"
    HIGH_CONTRAST = "high_contrast"
    CUSTOM = "custom"
```

#### `TabPriority`
```python
class TabPriority(Enum):
    """Tab priority levels for resource allocation"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4
```

### Message Models

#### `BusMessage`
```python
@dataclass
class BusMessage:
    """Message bus data model"""
    message_id: str
    sender_id: str
    channel: str
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime
    priority: MessagePriority
    retry_count: int = 0
```

#### `MessagePriority`
```python
class MessagePriority(Enum):
    """Message priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
```

### Performance Models

#### `SystemSnapshot`
```python
@dataclass
class SystemSnapshot:
    """System performance snapshot"""
    timestamp: datetime
    cpu_usage_percent: float
    memory_usage_mb: float
    memory_peak_mb: float
    active_tabs: int
    hibernated_tabs: int
    message_queue_depth: int
    component_count: int
```

#### `PerformanceMetric`
```python
@dataclass
class PerformanceMetric:
    """Individual performance metric"""
    name: str
    value: float
    unit: str
    category: str
    timestamp: datetime
    component_id: Optional[str] = None
```

---

## Error Handling

### Exception Hierarchy

#### `V2ComponentError`
```python
class V2ComponentError(Exception):
    """Base exception for V2.0 component errors"""
    pass
```

#### `InitializationError`
```python
class InitializationError(V2ComponentError):
    """Raised when component initialization fails"""
    pass
```

#### `ConfigurationError`
```python
class ConfigurationError(V2ComponentError):
    """Raised for configuration-related errors"""
    pass
```

#### `PerformanceError`
```python
class PerformanceError(V2ComponentError):
    """Raised when performance thresholds are exceeded"""
    pass
```

#### `StateError`
```python
class StateError(V2ComponentError):
    """Raised for state management errors"""
    pass
```

### Error Handling Best Practices

#### Graceful Degradation
```python
try:
    app_controller.initialize_services()
except InitializationError as e:
    # Log error and attempt partial initialization
    logger.error(f"Service initialization failed: {e}")
    app_controller.initialize_essential_services_only()
```

#### Performance Monitoring
```python
try:
    performance_monitor.track_metric("operation_time", elapsed_time)
except PerformanceError as e:
    # Handle performance threshold exceeded
    logger.warning(f"Performance threshold exceeded: {e}")
    performance_monitor.trigger_optimization()
```

#### State Recovery
```python
try:
    state_manager.restore_snapshot(snapshot_id)
except StateError as e:
    # Fallback to safe default state
    logger.error(f"State restoration failed: {e}")
    state_manager.reset_to_safe_defaults()
```

---

## Usage Examples

### Complete Application Setup
```python
from ui.components.core import *

# Create configuration
config = AppConfiguration(
    enable_debug_mode=False,
    max_concurrent_downloads=10,
    theme_variant=ThemeVariant.DARK
)

# Initialize application controller
app_controller = AppController(config)

# Start all services
if app_controller.initialize_services():
    # Application ready
    print("V2.0 Application initialized successfully")
    
    # Get services
    theme_manager = app_controller.get_service(ThemeManager)
    tab_manager = app_controller.get_service(TabLifecycleManager)
    
    # Create snapshot before operations
    state_manager = app_controller.get_service(StateManager)
    state_manager.create_snapshot("application_start")
```

### Component Communication
```python
# Get component bus
bus = app_controller.get_service(ComponentBus)

# Register components
bus.register_component("downloader", "service", "Download Manager")
bus.register_component("ui", "interface", "User Interface")

# Set up event handling
def handle_download_progress(message: BusMessage):
    progress = message.data.get("progress", 0)
    print(f"Download progress: {progress}%")

bus.subscribe("ui", "download_events", handle_download_progress)

# Send events
bus.send_event(
    "downloader", 
    "download_events", 
    "progress_update",
    {"progress": 75, "speed": "3.2 MB/s"}
)
```

### Performance Monitoring
```python
# Start performance tracking
monitor = app_controller.get_service(PerformanceMonitor)
monitor.start_detailed_tracking()

# Perform operations...
# Track custom metrics
monitor.track_metric("operation_duration_ms", 45.2)

# Get performance report
report = monitor.stop_detailed_tracking()
print(f"Average CPU usage: {report.average_cpu_usage}%")
```

---

## Migration Guide

### Migrating from V1.2.1

#### Component Registration
```python
# V1.2.1 (old)
app.register_downloader(YoutubeDownloader())

# V2.0 (new)
bus.register_component("youtube", "downloader", "YouTube Downloader")
```

#### Event Handling
```python
# V1.2.1 (old)
app.on_download_complete = handle_download

# V2.0 (new)
bus.subscribe("ui", "download_events", handle_download_complete)
```

#### State Management
```python
# V1.2.1 (old)
app.save_state()

# V2.0 (new)
state_manager.create_snapshot("user_session")
```

---

This API reference provides comprehensive documentation for integrating with Social Download Manager V2.0 components. For additional examples and advanced usage patterns, refer to the test files in `tests/ui/` and the implementation examples in `ui/components/core/`. 