"""
App Controller UI Integration Tests

Comprehensive testing framework for App Controller interactions with UI components,
configuration management, event flows, and edge cases.
"""

import pytest
import asyncio
import threading
import time
import logging
import gc
import weakref
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from queue import Queue, Empty

from core.app_controller import AppController, ControllerState, ControllerStatus, get_app_controller
from core.event_system import Event, EventType, EventHandler, get_event_bus
from core.config_manager import AppConfig, ConfigManager
from core.services import ContentDTO, AnalyticsDTO, DownloadRequestDTO

# Import test base classes
from .test_base import DatabaseTestCase, PerformanceTestCase


@dataclass
class UIComponentMock:
    """Mock UI component for testing controller interactions"""
    name: str
    component_id: str
    events_received: List[Event]
    state: Dict[str, Any]
    initialized: bool = False
    disposed: bool = False
    
    def __post_init__(self):
        self.events_received = []
        self.state = {}
    
    def handle_event(self, event: Event) -> None:
        """Handle events from controller"""
        self.events_received.append(event)
        
        # Simulate component state changes based on events
        if event.event_type == EventType.APP_STARTUP:
            self.state['app_ready'] = True
        elif event.event_type == EventType.CONTENT_CREATED:
            self.state['content_count'] = self.state.get('content_count', 0) + 1
        elif event.event_type == EventType.DOWNLOAD_STARTED:
            self.state['active_downloads'] = self.state.get('active_downloads', 0) + 1
    
    def initialize(self) -> bool:
        """Initialize mock component"""
        self.initialized = True
        return True
    
    def dispose(self) -> None:
        """Dispose mock component"""
        self.disposed = True
        self.events_received.clear()
        self.state.clear()


class MockUIComponentRegistry:
    """Registry for managing mock UI components"""
    
    def __init__(self):
        self.components: Dict[str, UIComponentMock] = {}
        self.event_handlers: Dict[EventType, List[UIComponentMock]] = {}
    
    def register_component(self, component: UIComponentMock) -> None:
        """Register a UI component"""
        self.components[component.component_id] = component
    
    def unregister_component(self, component_id: str) -> None:
        """Unregister a UI component"""
        if component_id in self.components:
            component = self.components[component_id]
            component.dispose()
            del self.components[component_id]
    
    def subscribe_to_events(self, component_id: str, event_types: List[EventType]) -> None:
        """Subscribe component to specific event types"""
        if component_id not in self.components:
            return
        
        component = self.components[component_id]
        for event_type in event_types:
            if event_type not in self.event_handlers:
                self.event_handlers[event_type] = []
            self.event_handlers[event_type].append(component)
    
    def broadcast_event(self, event: Event) -> None:
        """Broadcast event to subscribed components"""
        if event.event_type in self.event_handlers:
            for component in self.event_handlers[event.event_type]:
                component.handle_event(event)
    
    def get_component_states(self) -> Dict[str, Dict[str, Any]]:
        """Get all component states for testing"""
        return {
            comp_id: component.state
            for comp_id, component in self.components.items()
        }
    
    def clear_all(self) -> None:
        """Clear all components"""
        for component in self.components.values():
            component.dispose()
        self.components.clear()
        self.event_handlers.clear()


class TestAppControllerUIIntegration(DatabaseTestCase):
    """Test App Controller integration with UI components"""
    
    def setUp(self):
        """Set up test environment"""
        super().setUp()
        self.controller = AppController()
        self.ui_registry = MockUIComponentRegistry()
        self.test_events: List[Event] = []
        
        # Create mock UI components
        self.main_window = UIComponentMock("MainWindow", "main_window")
        self.download_panel = UIComponentMock("DownloadPanel", "download_panel")
        self.settings_dialog = UIComponentMock("SettingsDialog", "settings_dialog")
        self.progress_bar = UIComponentMock("ProgressBar", "progress_bar")
        
        # Register components
        self.ui_registry.register_component(self.main_window)
        self.ui_registry.register_component(self.download_panel)
        self.ui_registry.register_component(self.settings_dialog)
        self.ui_registry.register_component(self.progress_bar)
        
        # Setup event subscriptions
        self.ui_registry.subscribe_to_events("main_window", [
            EventType.APP_STARTUP, EventType.APP_SHUTDOWN, EventType.ERROR_OCCURRED
        ])
        self.ui_registry.subscribe_to_events("download_panel", [
            EventType.CONTENT_CREATED, EventType.DOWNLOAD_STARTED, EventType.DOWNLOAD_COMPLETED
        ])
        self.ui_registry.subscribe_to_events("settings_dialog", [
            EventType.CONFIG_CHANGED
        ])
        self.ui_registry.subscribe_to_events("progress_bar", [
            EventType.DOWNLOAD_STARTED, EventType.DOWNLOAD_PROGRESS, EventType.DOWNLOAD_COMPLETED
        ])
    
    def tearDown(self):
        """Clean up test environment"""
        if self.controller and self.controller.is_ready():
            self.controller.shutdown()
        self.ui_registry.clear_all()
        super().tearDown()
    
    def test_ui_component_initialization_flow(self):
        """Test UI component initialization with controller"""
        # Setup event bus to broadcast to UI components
        event_bus = get_event_bus()
        original_publish = event_bus.publish
        
        def mock_publish(event: Event):
            self.test_events.append(event)
            self.ui_registry.broadcast_event(event)
            return original_publish(event)
        
        event_bus.publish = mock_publish
        
        # Initialize controller
        result = self.controller.initialize()
        self.assertTrue(result)
        
        # Check that main window received startup event
        startup_events = [e for e in self.main_window.events_received if e.event_type == EventType.APP_STARTUP]
        self.assertGreater(len(startup_events), 0, "Main window should receive startup event")
        self.assertTrue(self.main_window.state.get('app_ready', False))
        
        # Restore original publish
        event_bus.publish = original_publish
    
    @patch('core.services.get_content_service')
    async def test_content_creation_ui_flow(self, mock_get_service):
        """Test content creation flow with UI component updates"""
        # Setup controller and mock service
        self.controller.initialize()
        mock_content_service = AsyncMock()
        self.controller.register_component("content_service", mock_content_service)
        
        # Mock service response
        expected_content = ContentDTO(
            id=1,
            url="https://youtube.com/watch?v=test",
            title="Test Video",
            status="PENDING"
        )
        mock_content_service.create_content.return_value = expected_content
        
        # Setup event interception
        event_bus = self.controller.get_event_bus()
        original_publish = event_bus.publish
        
        def mock_publish(event: Event):
            self.test_events.append(event)
            self.ui_registry.broadcast_event(event)
            return original_publish(event)
        
        event_bus.publish = mock_publish
        
        # Create content
        result = await self.controller.create_content_from_url("https://youtube.com/watch?v=test")
        
        # Verify UI component received event
        content_events = [e for e in self.download_panel.events_received if e.event_type == EventType.CONTENT_CREATED]
        self.assertGreater(len(content_events), 0, "Download panel should receive content created event")
        self.assertEqual(self.download_panel.state.get('content_count', 0), 1)
        
        # Restore original publish
        event_bus.publish = original_publish
    
    def test_configuration_change_ui_propagation(self):
        """Test configuration changes propagate to UI components"""
        # Initialize controller
        self.controller.initialize()
        
        # Setup event interception
        event_bus = self.controller.get_event_bus()
        original_publish = event_bus.publish
        
        def mock_publish(event: Event):
            self.test_events.append(event)
            self.ui_registry.broadcast_event(event)
            return original_publish(event)
        
        event_bus.publish = mock_publish
        
        # Simulate configuration change
        config_event = Event(EventType.CONFIG_CHANGED, {
            "section": "ui",
            "changes": {"theme": "dark", "language": "en"}
        })
        event_bus.publish(config_event)
        
        # Verify settings dialog received the event
        config_events = [e for e in self.settings_dialog.events_received if e.event_type == EventType.CONFIG_CHANGED]
        self.assertGreater(len(config_events), 0, "Settings dialog should receive config change event")
        
        # Restore original publish
        event_bus.publish = original_publish
    
    def test_error_propagation_to_ui(self):
        """Test error events propagate to UI components correctly"""
        # Initialize controller
        self.controller.initialize()
        
        # Setup event interception
        event_bus = self.controller.get_event_bus()
        original_publish = event_bus.publish
        
        def mock_publish(event: Event):
            self.test_events.append(event)
            self.ui_registry.broadcast_event(event)
            return original_publish(event)
        
        event_bus.publish = mock_publish
        
        # Trigger error
        test_error = RuntimeError("Test UI error")
        self.controller.handle_error(test_error, "ui_interaction")
        
        # Verify main window received error event
        error_events = [e for e in self.main_window.events_received if e.event_type == EventType.ERROR_OCCURRED]
        self.assertGreater(len(error_events), 0, "Main window should receive error event")
        
        # Check error details
        error_event = error_events[0]
        self.assertIn("error_type", error_event.data)
        self.assertEqual(error_event.data["error_type"], "RuntimeError")
        self.assertEqual(error_event.data["context"], "ui_interaction")
        
        # Restore original publish
        event_bus.publish = original_publish
    
    def test_ui_component_lifecycle_management(self):
        """Test UI component lifecycle with controller"""
        # Initialize all components
        for component in self.ui_registry.components.values():
            result = component.initialize()
            self.assertTrue(result, f"Component {component.name} should initialize successfully")
            self.assertTrue(component.initialized)
        
        # Register components with controller
        for comp_id, component in self.ui_registry.components.items():
            self.controller.register_component(f"ui_{comp_id}", component)
        
        # Initialize controller
        self.controller.initialize()
        
        # Verify components are registered
        for comp_id in self.ui_registry.components.keys():
            registered_component = self.controller.get_component(f"ui_{comp_id}")
            self.assertIsNotNone(registered_component, f"Component ui_{comp_id} should be registered")
        
        # Shutdown controller
        self.controller.shutdown()
        
        # Verify components are disposed (if they were registered for cleanup)
        # Note: Currently controller doesn't auto-dispose components, but this tests the pattern
        status = self.controller.get_status()
        self.assertEqual(status.state, ControllerState.SHUTDOWN)


class TestAppControllerConfigurationScenarios(DatabaseTestCase):
    """Test App Controller with various configuration scenarios"""
    
    def setUp(self):
        """Set up test environment"""
        super().setUp()
        self.controller = AppController()
        self.mock_configs: List[AppConfig] = []
    
    def tearDown(self):
        """Clean up test environment"""
        if self.controller and self.controller.is_ready():
            self.controller.shutdown()
        super().tearDown()
    
    def create_test_config(self, **overrides) -> AppConfig:
        """Create test configuration with overrides"""
        config_data = {
            "app": {
                "name": "TestApp",
                "version": "1.0.0",
                "environment": "test"
            },
            "database": {
                "url": ":memory:",
                "pool_size": 5
            },
            "download": {
                "max_concurrent": 3,
                "timeout": 30
            },
            "ui": {
                "theme": "light",
                "language": "en"
            }
        }
        
        # Apply overrides
        for key, value in overrides.items():
            if "." in key:
                section, setting = key.split(".", 1)
                if section not in config_data:
                    config_data[section] = {}
                config_data[section][setting] = value
            else:
                config_data[key] = value
        
        mock_config = Mock(spec=AppConfig)
        mock_config.app = Mock(**config_data.get("app", {}))
        mock_config.database = Mock(**config_data.get("database", {}))
        mock_config.download = Mock(**config_data.get("download", {}))
        mock_config.ui = Mock(**config_data.get("ui", {}))
        
        return mock_config
    
    @patch('core.app_controller.get_config_manager')
    @patch('core.app_controller.get_event_bus')
    def test_development_environment_config(self, mock_get_event_bus, mock_get_config_manager):
        """Test controller with development environment configuration"""
        # Create development config
        dev_config = self.create_test_config(**{
            "app.environment": "development",
            "app.debug": True,
            "database.log_queries": True,
            "download.max_concurrent": 1
        })
        
        mock_config_manager = Mock()
        mock_config_manager.config = dev_config
        mock_get_config_manager.return_value = mock_config_manager
        mock_get_event_bus.return_value = Mock()
        
        # Initialize controller
        result = self.controller.initialize()
        self.assertTrue(result)
        
        # Verify development-specific behavior
        config = self.controller.get_config()
        self.assertEqual(config.app.environment, "development")
        self.assertTrue(config.app.debug)
    
    @patch('core.app_controller.get_config_manager')
    @patch('core.app_controller.get_event_bus')
    def test_production_environment_config(self, mock_get_event_bus, mock_get_config_manager):
        """Test controller with production environment configuration"""
        # Create production config
        prod_config = self.create_test_config(**{
            "app.environment": "production",
            "app.debug": False,
            "database.log_queries": False,
            "download.max_concurrent": 10
        })
        
        mock_config_manager = Mock()
        mock_config_manager.config = prod_config
        mock_get_config_manager.return_value = mock_config_manager
        mock_get_event_bus.return_value = Mock()
        
        # Initialize controller
        result = self.controller.initialize()
        self.assertTrue(result)
        
        # Verify production-specific behavior
        config = self.controller.get_config()
        self.assertEqual(config.app.environment, "production")
        self.assertFalse(config.app.debug)
    
    @patch('core.app_controller.get_config_manager')
    @patch('core.app_controller.get_event_bus') 
    def test_invalid_configuration_handling(self, mock_get_event_bus, mock_get_config_manager):
        """Test controller behavior with invalid configuration"""
        # Create config manager that raises exception
        mock_config_manager = Mock()
        mock_config_manager.config = None
        mock_get_config_manager.return_value = mock_config_manager
        mock_get_event_bus.return_value = Mock()
        
        # Simulate config access failure
        def config_side_effect():
            raise ValueError("Invalid configuration")
        
        type(mock_config_manager).config = property(config_side_effect)
        
        # Initialize controller should handle gracefully
        result = self.controller.initialize()
        
        # Should fail gracefully without crashing
        self.assertFalse(result)
        self.assertEqual(self.controller._state, ControllerState.ERROR)
    
    def test_configuration_reload_scenario(self):
        """Test configuration reload during runtime"""
        # Initialize controller
        self.controller.initialize()
        
        # Simulate configuration change event
        original_handler = self.controller._handle_config_changed
        config_reloaded = False
        
        def mock_config_handler(event):
            nonlocal config_reloaded
            config_reloaded = True
            return original_handler(event)
        
        self.controller._handle_config_changed = mock_config_handler
        
        # Send config change event
        config_event = Event(EventType.CONFIG_CHANGED, {
            "section": "download",
            "changes": {"max_concurrent": 5}
        })
        self.controller.handle_event(config_event)
        
        # Verify config change was handled
        self.assertTrue(config_reloaded)


class TestAppControllerEventFlows(DatabaseTestCase):
    """Test complex event flows through the App Controller"""
    
    def setUp(self):
        """Set up test environment"""
        super().setUp()
        self.controller = AppController()
        self.event_log: List[Dict[str, Any]] = []
        self.event_handlers: List[Callable] = []
    
    def tearDown(self):
        """Clean up test environment"""
        if self.controller and self.controller.is_ready():
            self.controller.shutdown()
        super().tearDown()
    
    def create_event_logger(self, name: str) -> Callable:
        """Create an event logger function"""
        def log_event(event: Event):
            self.event_log.append({
                "handler": name,
                "event_type": event.event_type,
                "data": event.data,
                "timestamp": time.time()
            })
        return log_event
    
    def test_event_cascade_flow(self):
        """Test cascading event flows through controller"""
        # Initialize controller
        self.controller.initialize()
        event_bus = self.controller.get_event_bus()
        
        # Setup event handlers
        startup_logger = self.create_event_logger("startup_handler")
        content_logger = self.create_event_logger("content_handler")
        error_logger = self.create_event_logger("error_handler")
        
        # Create mock event handlers
        class StartupHandler(EventHandler):
            def handle_event(self, event: Event):
                startup_logger(event)
                if event.event_type == EventType.APP_STARTUP:
                    # Trigger secondary event
                    content_event = Event(EventType.CONTENT_CREATED, {"id": 1})
                    event_bus.publish(content_event)
        
        class ContentHandler(EventHandler):
            def handle_event(self, event: Event):
                content_logger(event)
                if event.event_type == EventType.CONTENT_CREATED:
                    # Trigger tertiary event
                    download_event = Event(EventType.DOWNLOAD_STARTED, {"content_id": event.data.get("id")})
                    event_bus.publish(download_event)
        
        # Register handlers
        startup_handler = StartupHandler()
        content_handler = ContentHandler()
        event_bus.add_handler(startup_handler)
        event_bus.add_handler(content_handler)
        
        # Clear initial events and trigger cascade
        self.event_log.clear()
        startup_event = Event(EventType.APP_STARTUP, {"version": "1.0.0"})
        event_bus.publish(startup_event)
        
        # Allow event processing
        time.sleep(0.1)
        
        # Verify event cascade
        event_types = [entry["event_type"] for entry in self.event_log]
        self.assertIn(EventType.APP_STARTUP, event_types)
        self.assertIn(EventType.CONTENT_CREATED, event_types)
        self.assertIn(EventType.DOWNLOAD_STARTED, event_types)
        
        # Cleanup
        event_bus.remove_handler(startup_handler)
        event_bus.remove_handler(content_handler)
    
    def test_event_error_handling_flow(self):
        """Test error handling in event flows"""
        # Initialize controller
        self.controller.initialize()
        event_bus = self.controller.get_event_bus()
        
        # Create handler that raises exception
        class ErrorHandler(EventHandler):
            def handle_event(self, event: Event):
                if event.event_type == EventType.CONTENT_CREATED:
                    raise RuntimeError("Handler error")
        
        error_handler = ErrorHandler()
        event_bus.add_handler(error_handler)
        
        # Trigger event that causes error
        content_event = Event(EventType.CONTENT_CREATED, {"id": 1})
        
        # Should not crash the event system
        try:
            event_bus.publish(content_event)
            # Event system should handle the error gracefully
        except Exception as e:
            self.fail(f"Event system should handle handler errors gracefully, but got: {e}")
        
        # Cleanup
        event_bus.remove_handler(error_handler)
    
    async def test_async_event_handling_flow(self):
        """Test asynchronous event handling flows"""
        # Initialize controller
        self.controller.initialize()
        
        # Test async operations through controller
        mock_content_service = AsyncMock()
        mock_content_service.create_content.return_value = ContentDTO(
            id=1,
            url="https://test.com",
            title="Test"
        )
        self.controller.register_component("content_service", mock_content_service)
        
        # Setup event logging
        event_bus = self.controller.get_event_bus()
        original_publish = event_bus.publish
        
        def log_publish(event: Event):
            self.event_log.append({
                "event_type": event.event_type,
                "data": event.data,
                "timestamp": time.time()
            })
            return original_publish(event)
        
        event_bus.publish = log_publish
        
        # Trigger async operation
        result = await self.controller.create_content_from_url("https://test.com")
        
        # Verify async operation completed and events were published
        self.assertIsNotNone(result)
        content_events = [entry for entry in self.event_log if entry["event_type"] == EventType.CONTENT_CREATED]
        self.assertGreater(len(content_events), 0)
        
        # Restore original publish
        event_bus.publish = original_publish


class TestAppControllerPerformanceAndLoad(PerformanceTestCase):
    """Test App Controller performance and load scenarios"""
    
    def setUp(self):
        """Set up performance test environment"""
        super().setUp()
        self.controller = AppController()
        self.performance_metrics: Dict[str, List[float]] = {
            "initialization_time": [],
            "component_registration_time": [],
            "event_processing_time": [],
            "shutdown_time": []
        }
    
    def tearDown(self):
        """Clean up performance test environment"""
        if self.controller and self.controller.is_ready():
            self.controller.shutdown()
        super().tearDown()
    
    def test_controller_initialization_performance(self):
        """Test controller initialization performance"""
        initialization_times = []
        
        for i in range(10):
            # Create fresh controller
            controller = AppController()
            
            start_time = time.perf_counter()
            result = controller.initialize()
            end_time = time.perf_counter()
            
            self.assertTrue(result, f"Initialization {i} should succeed")
            
            initialization_time = end_time - start_time
            initialization_times.append(initialization_time)
            
            # Cleanup
            controller.shutdown()
        
        # Calculate performance metrics
        avg_time = sum(initialization_times) / len(initialization_times)
        max_time = max(initialization_times)
        
        self.performance_metrics["initialization_time"] = initialization_times
        
        # Performance assertions
        self.assertLess(avg_time, 1.0, "Average initialization should be under 1 second")
        self.assertLess(max_time, 2.0, "Max initialization should be under 2 seconds")
        
        print(f"Initialization Performance: avg={avg_time:.3f}s, max={max_time:.3f}s")
    
    def test_component_registration_load(self):
        """Test component registration under load"""
        self.controller.initialize()
        
        registration_times = []
        num_components = 100
        
        for i in range(num_components):
            component = Mock()
            component.name = f"test_component_{i}"
            
            start_time = time.perf_counter()
            result = self.controller.register_component(f"component_{i}", component)
            end_time = time.perf_counter()
            
            self.assertTrue(result, f"Component {i} registration should succeed")
            
            registration_time = end_time - start_time
            registration_times.append(registration_time)
        
        # Calculate performance metrics
        avg_time = sum(registration_times) / len(registration_times)
        total_time = sum(registration_times)
        
        self.performance_metrics["component_registration_time"] = registration_times
        
        # Performance assertions
        self.assertLess(avg_time, 0.01, "Average component registration should be under 10ms")
        self.assertLess(total_time, 1.0, f"Total time for {num_components} registrations should be under 1s")
        
        print(f"Component Registration Performance: avg={avg_time*1000:.3f}ms, total={total_time:.3f}s")
    
    def test_concurrent_event_processing(self):
        """Test event processing under concurrent load"""
        self.controller.initialize()
        event_bus = self.controller.get_event_bus()
        
        event_processing_times = []
        num_events = 50
        num_threads = 5
        
        def publish_events(thread_id: int, events_per_thread: int):
            thread_times = []
            for i in range(events_per_thread):
                event = Event(EventType.CONTENT_CREATED, {
                    "thread_id": thread_id,
                    "event_id": i,
                    "content_id": thread_id * events_per_thread + i
                })
                
                start_time = time.perf_counter()
                event_bus.publish(event)
                end_time = time.perf_counter()
                
                thread_times.append(end_time - start_time)
            
            event_processing_times.extend(thread_times)
        
        # Launch concurrent threads
        threads = []
        events_per_thread = num_events // num_threads
        
        for thread_id in range(num_threads):
            thread = threading.Thread(
                target=publish_events,
                args=(thread_id, events_per_thread)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)  # 10 second timeout
        
        # Calculate performance metrics
        avg_time = sum(event_processing_times) / len(event_processing_times)
        max_time = max(event_processing_times)
        
        self.performance_metrics["event_processing_time"] = event_processing_times
        
        # Performance assertions
        self.assertLess(avg_time, 0.001, "Average event processing should be under 1ms")
        self.assertLess(max_time, 0.01, "Max event processing should be under 10ms")
        
        print(f"Event Processing Performance: avg={avg_time*1000:.3f}ms, max={max_time*1000:.3f}ms")
    
    def test_memory_usage_during_operations(self):
        """Test memory usage during controller operations"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Get initial memory usage
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Initialize controller
        self.controller.initialize()
        
        # Register many components
        components = []
        for i in range(1000):
            component = Mock()
            component.name = f"component_{i}"
            components.append(component)
            self.controller.register_component(f"comp_{i}", component)
        
        # Publish many events
        event_bus = self.controller.get_event_bus()
        for i in range(1000):
            event = Event(EventType.CONTENT_CREATED, {"id": i})
            event_bus.publish(event)
        
        # Get peak memory usage
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Cleanup components
        for i in range(1000):
            self.controller.unregister_component(f"comp_{i}")
        
        # Force garbage collection
        gc.collect()
        
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        memory_increase = peak_memory - initial_memory
        memory_retained = final_memory - initial_memory
        
        print(f"Memory Usage: initial={initial_memory:.1f}MB, peak={peak_memory:.1f}MB, final={final_memory:.1f}MB")
        print(f"Memory Increase: {memory_increase:.1f}MB, Retained: {memory_retained:.1f}MB")
        
        # Memory assertions (reasonable limits)
        self.assertLess(memory_increase, 100, "Memory increase should be reasonable")
        self.assertLess(memory_retained, 20, "Memory retention after cleanup should be minimal")
    
    def test_shutdown_performance(self):
        """Test controller shutdown performance"""
        shutdown_times = []
        
        for i in range(5):
            # Initialize controller with components
            controller = AppController()
            controller.initialize()
            
            # Register components
            for j in range(20):
                component = Mock()
                component.cleanup = Mock()
                controller.register_component(f"comp_{j}", component)
            
            # Measure shutdown time
            start_time = time.perf_counter()
            result = controller.shutdown()
            end_time = time.perf_counter()
            
            self.assertTrue(result, f"Shutdown {i} should succeed")
            
            shutdown_time = end_time - start_time
            shutdown_times.append(shutdown_time)
        
        # Calculate performance metrics
        avg_time = sum(shutdown_times) / len(shutdown_times)
        max_time = max(shutdown_times)
        
        self.performance_metrics["shutdown_time"] = shutdown_times
        
        # Performance assertions
        self.assertLess(avg_time, 0.5, "Average shutdown should be under 500ms")
        self.assertLess(max_time, 1.0, "Max shutdown should be under 1 second")
        
        print(f"Shutdown Performance: avg={avg_time:.3f}s, max={max_time:.3f}s")


if __name__ == "__main__":
    # Configure logging for tests
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"]) 