"""
Test utilities for Social Download Manager v2.0

Provides helper functions, mock objects, and test fixtures for testing components.
"""

import threading
import time
from unittest.mock import Mock, MagicMock
from typing import Dict, Any, Optional, List
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.app_controller import AppController, ControllerState
from core.event_system import Event, EventType, EventHandler
from core.config_manager import AppConfig, PlatformConfig, DatabaseConfig, UIConfig, DownloadConfig


class MockEventBus:
    """Mock event bus for testing"""
    
    def __init__(self):
        self.events_published = []
        self.handlers = []
        self.subscribers = {}
    
    def add_handler(self, handler):
        """Add event handler"""
        self.handlers.append(handler)
    
    def remove_handler(self, handler):
        """Remove event handler"""
        if handler in self.handlers:
            self.handlers.remove(handler)
            return True
        return False
    
    def publish(self, event):
        """Publish event to all handlers"""
        self.events_published.append(event)
        for handler in self.handlers:
            handler.handle_event(event)
    
    def subscribe(self, event_type, callback):
        """Subscribe to specific event type"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
    
    def get_total_subscribers(self):
        """Get total number of subscribers"""
        return sum(len(subs) for subs in self.subscribers.values())
    
    def clear_events(self):
        """Clear published events history"""
        self.events_published.clear()


class MockConfigManager:
    """Mock configuration manager for testing"""
    
    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or self._create_default_config()
        self.config_path = Mock()
        self.config_path.exists.return_value = True
        self.save_called = False
        self.load_called = False
    
    def _create_default_config(self) -> AppConfig:
        """Create default test configuration"""
        return AppConfig(
            version="2.0.0-test",
            app_name="Test Social Download Manager",
            platforms={
                "tiktok": PlatformConfig(enabled=True),
                "youtube": PlatformConfig(enabled=False)
            },
            database=DatabaseConfig(path="test.db"),
            ui=UIConfig(theme="light", language="en"),
            downloads=DownloadConfig(default_directory="test_downloads")
        )
    
    def save_config(self):
        """Mock save config"""
        self.save_called = True
        return True
    
    def _load_config(self):
        """Mock load config"""
        self.load_called = True


class MockComponent:
    """Mock component for testing controller integration"""
    
    def __init__(self, name: str, should_fail_cleanup: bool = False):
        self.name = name
        self.initialized = False
        self.cleanup_called = False
        self.should_fail_cleanup = should_fail_cleanup
        self.error_count = 0
    
    def initialize(self):
        """Mock initialization"""
        self.initialized = True
        return True
    
    def cleanup(self):
        """Mock cleanup"""
        self.cleanup_called = True
        if self.should_fail_cleanup:
            raise RuntimeError(f"Cleanup failed for {self.name}")
    
    def simulate_error(self):
        """Simulate an error in the component"""
        self.error_count += 1
        raise RuntimeError(f"Simulated error in {self.name}")


class TestEventHandler(EventHandler):
    """Test event handler that tracks received events"""
    
    def __init__(self):
        self.events_received = []
        self.event_counts = {}
    
    def handle_event(self, event: Event):
        """Handle and track events"""
        self.events_received.append(event)
        event_type = event.event_type
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
    
    def get_events_by_type(self, event_type: EventType) -> List[Event]:
        """Get all events of specific type"""
        return [e for e in self.events_received if e.event_type == event_type]
    
    def clear_events(self):
        """Clear received events"""
        self.events_received.clear()
        self.event_counts.clear()


class ControllerTestFixture:
    """Test fixture for controller testing"""
    
    def __init__(self):
        self.controller = None
        self.mock_config_manager = None
        self.mock_event_bus = None
        self.test_components = {}
        self.error_handlers = []
    
    def setup(self, initialize_controller: bool = True) -> AppController:
        """Setup test controller with mocks"""
        # Reset singleton
        import core.app_controller
        core.app_controller._app_controller = None
        
        # Create controller
        self.controller = AppController()
        
        # Setup mocks (use existing ones if already created)
        if not self.mock_config_manager:
            self.mock_config_manager = MockConfigManager()
        if not self.mock_event_bus:
            self.mock_event_bus = MockEventBus()
        
        if initialize_controller:
            # Mock the get functions
            import core.app_controller
            original_get_config = core.app_controller.get_config_manager
            original_get_event = core.app_controller.get_event_bus
            
            core.app_controller.get_config_manager = lambda: self.mock_config_manager
            core.app_controller.get_event_bus = lambda: self.mock_event_bus
            
            # Initialize controller
            result = self.controller.initialize()
            if not result:
                raise RuntimeError("Failed to initialize test controller")
            
            # Restore original functions
            core.app_controller.get_config_manager = original_get_config
            core.app_controller.get_event_bus = original_get_event
        
        return self.controller
    
    def add_test_component(self, name: str, component: Optional[MockComponent] = None) -> MockComponent:
        """Add a test component to the controller"""
        if component is None:
            component = MockComponent(name)
        
        self.test_components[name] = component
        if self.controller:
            self.controller.register_component(name, component)
        
        return component
    
    def add_error_handler(self, handler):
        """Add error handler to controller"""
        if self.controller:
            self.controller.add_error_handler(handler)
            self.error_handlers.append(handler)
    
    def teardown(self):
        """Cleanup test fixture"""
        if self.controller and self.controller._state not in [ControllerState.SHUTDOWN, ControllerState.UNINITIALIZED]:
            self.controller.shutdown()
        
        # Reset singleton
        import core.app_controller
        core.app_controller._app_controller = None
        
        self.test_components.clear()
        self.error_handlers.clear()


def wait_for_condition(condition_func, timeout: float = 1.0, check_interval: float = 0.01) -> bool:
    """
    Wait for a condition to become true within timeout
    
    Args:
        condition_func: Function that returns bool
        timeout: Maximum time to wait in seconds
        check_interval: How often to check the condition
        
    Returns:
        True if condition became true, False if timeout
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        if condition_func():
            return True
        time.sleep(check_interval)
    return False


def simulate_concurrent_operations(operations: List[callable], num_threads: int = 5) -> List[Any]:
    """
    Simulate concurrent operations for testing thread safety
    
    Args:
        operations: List of callable operations to run
        num_threads: Number of threads to use
        
    Returns:
        List of results from operations
    """
    results = []
    exceptions = []
    
    def run_operations():
        try:
            for operation in operations:
                result = operation()
                results.append(result)
        except Exception as e:
            exceptions.append(e)
    
    threads = []
    for _ in range(num_threads):
        thread = threading.Thread(target=run_operations)
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    if exceptions:
        raise exceptions[0]  # Re-raise first exception
    
    return results


def create_test_event(event_type: EventType, source: str = "test", data: Optional[Dict[str, Any]] = None) -> Event:
    """Create a test event with optional data"""
    return Event(event_type, source, data)


def assert_event_published(event_bus: MockEventBus, event_type: EventType, source: Optional[str] = None) -> bool:
    """
    Assert that an event of specific type was published
    
    Args:
        event_bus: Mock event bus to check
        event_type: Expected event type
        source: Optional expected source
        
    Returns:
        True if event was found
    """
    for event in event_bus.events_published:
        if event.event_type == event_type:
            if source is None or event.source == source:
                return True
    return False


def get_published_events_by_type(event_bus: MockEventBus, event_type: EventType) -> List[Event]:
    """Get all published events of specific type"""
    return [e for e in event_bus.events_published if e.event_type == event_type]


class IntegrationTestCase:
    """Base class for integration tests"""
    
    def __init__(self):
        self.fixture = ControllerTestFixture()
        self.event_handler = TestEventHandler()
    
    def setup(self):
        """Setup integration test"""
        # Add event handler to mock event bus before controller initialization
        self.fixture.mock_event_bus = MockEventBus()
        self.fixture.mock_event_bus.add_handler(self.event_handler)
        
        # Now setup controller which will use the mock event bus with handler already attached
        self.controller = self.fixture.setup()
    
    def teardown(self):
        """Teardown integration test"""
        self.fixture.teardown()
    
    def simulate_app_lifecycle(self):
        """Simulate complete application lifecycle"""
        # Add some components
        comp1 = self.fixture.add_test_component("component1")
        comp2 = self.fixture.add_test_component("component2")
        
        # Verify initialization events
        startup_events = self.event_handler.get_events_by_type(EventType.APP_STARTUP)
        assert len(startup_events) > 0, "No startup events received"
        
        # Simulate some operations
        status = self.controller.get_status()
        assert status.state == ControllerState.READY
        
        # Simulate error
        try:
            comp1.simulate_error()
        except RuntimeError as e:
            self.controller.handle_error(e, "test_error_simulation")
        
        # Verify error events
        error_events = self.event_handler.get_events_by_type(EventType.ERROR_OCCURRED)
        assert len(error_events) > 0, "No error events received"
        
        # Shutdown
        self.controller.shutdown()
        
        # Verify cleanup
        assert comp1.cleanup_called, "Component 1 cleanup not called"
        assert comp2.cleanup_called, "Component 2 cleanup not called"
        
        # Verify shutdown events
        shutdown_events = self.event_handler.get_events_by_type(EventType.APP_SHUTDOWN)
        assert len(shutdown_events) > 0, "No shutdown events received"


# Test data factories
def create_test_platform_config(platform: str = "test_platform") -> PlatformConfig:
    """Create test platform configuration"""
    return PlatformConfig(
        enabled=True,
        max_concurrent_downloads=2,
        default_quality="720p",
        custom_settings={"test_setting": "test_value"}
    )


def create_test_app_config() -> AppConfig:
    """Create comprehensive test application configuration"""
    return AppConfig(
        version="2.0.0-test",
        app_name="Test App",
        platforms={
            "tiktok": create_test_platform_config("tiktok"),
            "youtube": create_test_platform_config("youtube")
        },
        database=DatabaseConfig(
            path="test.db",
            backup_enabled=True,
            backup_interval_days=1,
            max_backups=3
        ),
        ui=UIConfig(
            theme="dark",
            language="en",
            window_width=800,
            window_height=600,
            auto_save_settings=True
        ),
        downloads=DownloadConfig(
            default_directory="test_downloads",
            create_subdirectories=True,
            max_retries=2,
            timeout_seconds=10,
            parallel_downloads=2
        )
    ) 