"""
Comprehensive Integration Tests for V2.0 UI Components

This test suite verifies that all 8 core V2.0 UI managers work correctly
both individually and when integrated together in the AppController.
"""

import pytest
import tempfile
import time
import gc
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtCore import QObject, QThread, QTimer, QCoreApplication
from PyQt6.QtWidgets import QApplication
from typing import Dict, List, Any

# Add the UI components to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'ui', 'components', 'core'))

from tab_lifecycle_manager import TabLifecycleManager, TabState, TabPriority
from component_bus import ComponentBus, MessageType, Priority, DeliveryMode
from theme_manager import ThemeManager, ThemeVariant
from app_controller import AppController, ServiceScope


class TestV2UIIntegration:
    """Integration tests for V2.0 UI system"""
    
    @pytest.fixture(autouse=True)
    def setup_qt_app(self):
        """Setup QApplication for tests"""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
        yield
        # Cleanup after each test
        if hasattr(self, '_temp_dirs'):
            for temp_dir in self._temp_dirs:
                try:
                    temp_dir.cleanup()
                except:
                    pass
    
    @pytest.fixture
    def temp_dir(self):
        """Provide temporary directory for each test"""
        if not hasattr(self, '_temp_dirs'):
            self._temp_dirs = []
        temp_dir = tempfile.TemporaryDirectory()
        self._temp_dirs.append(temp_dir)
        return temp_dir.name
    
    @pytest.fixture
    def lifecycle_manager(self, temp_dir):
        """Create TabLifecycleManager instance"""
        manager = TabLifecycleManager(state_dir=temp_dir)
        yield manager
        manager.shutdown()
    
    @pytest.fixture
    def component_bus(self):
        """Create ComponentBus instance"""
        bus = ComponentBus()
        yield bus
        bus.stop()
    
    @pytest.fixture
    def theme_manager(self, temp_dir):
        """Create ThemeManager instance"""
        manager = ThemeManager(config_dir=temp_dir)
        yield manager
        manager.cleanup()
    
    @pytest.fixture
    def app_controller(self, temp_dir):
        """Create AppController instance"""
        config = {
            'state_dir': temp_dir,
            'enable_performance_monitoring': True,
            'enable_hibernation': True,
            'enable_component_bus': True,
            'enable_theme_management': True
        }
        controller = AppController(config)
        yield controller
        controller.shutdown()


class TestTabLifecycleManager(TestV2UIIntegration):
    """Test TabLifecycleManager functionality"""
    
    def test_tab_creation_and_state_transitions(self, lifecycle_manager):
        """Test tab creation and basic state transitions"""
        # Create a new tab
        tab_id = "test_tab_1"
        tab_created = lifecycle_manager.create_tab(tab_id, priority=TabPriority.HIGH)
        
        assert tab_created
        assert lifecycle_manager.get_tab_state(tab_id) == TabState.INITIALIZING
        
        # Transition to active
        lifecycle_manager.activate_tab(tab_id)
        assert lifecycle_manager.get_tab_state(tab_id) == TabState.ACTIVE
        
        # Test hibernation
        lifecycle_manager.hibernate_tab(tab_id)
        assert lifecycle_manager.get_tab_state(tab_id) == TabState.HIBERNATED
        
        # Test restoration
        lifecycle_manager.restore_tab(tab_id)
        assert lifecycle_manager.get_tab_state(tab_id) == TabState.ACTIVE
    
    def test_tab_hibernation_with_state_persistence(self, lifecycle_manager):
        """Test tab hibernation saves and restores state properly"""
        tab_id = "hibernation_test"
        
        # Create and activate tab
        lifecycle_manager.create_tab(tab_id)
        lifecycle_manager.activate_tab(tab_id)
        
        # Add some state data
        test_state = {"user_input": "test data", "scroll_position": 150}
        lifecycle_manager.update_tab_state(tab_id, test_state)
        
        # Hibernate the tab
        lifecycle_manager.hibernate_tab(tab_id)
        
        # Verify state is preserved
        restored_state = lifecycle_manager.restore_tab(tab_id)
        assert restored_state is not None
        assert restored_state.get("user_input") == "test data"
        assert restored_state.get("scroll_position") == 150
    
    def test_memory_pressure_handling(self, lifecycle_manager):
        """Test automatic hibernation under memory pressure"""
        # Create multiple tabs with different priorities
        tab_ids = []
        for i in range(5):
            tab_id = f"memory_test_{i}"
            priority = TabPriority.LOW if i > 2 else TabPriority.HIGH
            lifecycle_manager.create_tab(tab_id, priority=priority)
            lifecycle_manager.activate_tab(tab_id)
            tab_ids.append(tab_id)
        
        # Simulate memory pressure
        lifecycle_manager._handle_memory_pressure(memory_usage=90.0)
        
        # Verify low priority tabs are hibernated first
        for i, tab_id in enumerate(tab_ids):
            state = lifecycle_manager.get_tab_state(tab_id)
            if i > 2:  # Low priority tabs
                assert state == TabState.HIBERNATED
            else:  # High priority tabs
                assert state == TabState.ACTIVE


class TestComponentBus(TestV2UIIntegration):
    """Test ComponentBus messaging functionality"""
    
    def test_basic_message_publishing_and_subscription(self, component_bus):
        """Test basic publish/subscribe functionality"""
        messages_received = []
        
        def message_handler(message):
            messages_received.append(message)
        
        # Subscribe to messages
        component_bus.subscribe("test_component", "test_channel", message_handler)
        
        # Send a message
        component_bus.send_event("sender", "test_channel", "test_event", {"data": "test"})
        
        # Process messages
        component_bus.process_messages()
        
        # Verify message received
        assert len(messages_received) == 1
        assert messages_received[0].message_type == MessageType.EVENT
        assert messages_received[0].payload["data"] == "test"
    
    def test_request_response_pattern(self, component_bus):
        """Test request-response messaging pattern"""
        response_received = []
        
        def request_handler(message):
            # Send response back
            component_bus.send_response(
                "responder", message.sender_id, "response_data", 
                {"result": "success"}, message.correlation_id
            )
        
        def response_handler(message):
            response_received.append(message)
        
        # Subscribe to requests and responses
        component_bus.subscribe("responder", "request_channel", request_handler)
        component_bus.subscribe("requester", "response", response_handler)
        
        # Send request
        correlation_id = component_bus.send_request(
            "requester", "request_channel", "test_request", {"query": "test"}
        )
        
        # Process messages
        component_bus.process_messages()
        
        # Verify response received
        assert len(response_received) == 1
        assert response_received[0].correlation_id == correlation_id
        assert response_received[0].payload["result"] == "success"
    
    def test_message_priority_handling(self, component_bus):
        """Test that high priority messages are processed first"""
        messages_received = []
        
        def message_handler(message):
            messages_received.append(message.payload["priority"])
        
        component_bus.subscribe("test_component", "priority_test", message_handler)
        
        # Send messages with different priorities
        component_bus.send_event("sender", "priority_test", "low", {"priority": "low"}, Priority.LOW)
        component_bus.send_event("sender", "priority_test", "high", {"priority": "high"}, Priority.HIGH)
        component_bus.send_event("sender", "priority_test", "critical", {"priority": "critical"}, Priority.CRITICAL)
        
        # Process all messages
        component_bus.process_messages()
        
        # Verify messages processed in priority order
        assert messages_received == ["critical", "high", "low"]
    
    def test_hibernated_component_message_queuing(self, component_bus):
        """Test messages are queued for hibernated components"""
        messages_received = []
        
        def message_handler(message):
            messages_received.append(message)
        
        # Subscribe component and mark as hibernated
        component_bus.subscribe("hibernated_component", "test_channel", message_handler)
        component_bus.set_component_hibernated("hibernated_component", True)
        
        # Send messages while hibernated
        component_bus.send_event("sender", "test_channel", "hibernated_message", {"data": "test"})
        component_bus.process_messages()
        
        # Should receive no messages while hibernated
        assert len(messages_received) == 0
        
        # Wake up component
        component_bus.set_component_hibernated("hibernated_component", False)
        component_bus.process_messages()
        
        # Should now receive queued messages
        assert len(messages_received) == 1
        assert messages_received[0].payload["data"] == "test"


class TestThemeManager(TestV2UIIntegration):
    """Test ThemeManager functionality"""
    
    def test_theme_switching(self, theme_manager):
        """Test switching between different theme variants"""
        # Start with light theme
        assert theme_manager.current_variant == ThemeVariant.LIGHT
        
        # Switch to dark theme
        theme_manager.switch_theme(ThemeVariant.DARK)
        assert theme_manager.current_variant == ThemeVariant.DARK
        
        # Verify theme tokens changed
        dark_bg = theme_manager.get_token("colors", "background")
        assert dark_bg != "#ffffff"  # Should not be light theme color
        
        # Switch to high contrast
        theme_manager.switch_theme(ThemeVariant.HIGH_CONTRAST)
        assert theme_manager.current_variant == ThemeVariant.HIGH_CONTRAST
    
    def test_component_theme_overrides(self, theme_manager):
        """Test component-specific theme overrides"""
        component_id = "test_component"
        
        # Register component with overrides
        overrides = {
            "colors": {
                "primary": "#ff0000",  # Red override
                "background": "#000000"  # Black override
            }
        }
        theme_manager.register_component_override(component_id, overrides)
        
        # Get component-specific tokens
        primary_color = theme_manager.get_component_token(component_id, "colors", "primary")
        bg_color = theme_manager.get_component_token(component_id, "colors", "background")
        
        assert primary_color == "#ff0000"
        assert bg_color == "#000000"
    
    def test_theme_persistence(self, theme_manager, temp_dir):
        """Test theme preferences are saved and restored"""
        # Switch to dark theme
        theme_manager.switch_theme(ThemeVariant.DARK)
        
        # Save preferences
        theme_manager.save_preferences()
        
        # Create new theme manager instance
        new_theme_manager = ThemeManager(config_dir=temp_dir)
        
        # Should restore dark theme
        assert new_theme_manager.current_variant == ThemeVariant.DARK


class TestAppControllerIntegration(TestV2UIIntegration):
    """Test AppController integration of all components"""
    
    def test_app_controller_initialization(self, app_controller):
        """Test AppController properly initializes all managers"""
        # Verify all services are registered
        assert app_controller.get_service('tab_lifecycle_manager') is not None
        assert app_controller.get_service('component_bus') is not None
        assert app_controller.get_service('theme_manager') is not None
    
    def test_cross_component_communication(self, app_controller):
        """Test components can communicate through the app controller"""
        messages_received = []
        
        # Get managers
        bus = app_controller.get_service('component_bus')
        lifecycle_manager = app_controller.get_service('tab_lifecycle_manager')
        
        def tab_event_handler(message):
            messages_received.append(message)
        
        # Subscribe to tab events
        bus.subscribe("test_listener", "tab_events", tab_event_handler)
        
        # Create a tab (should trigger events)
        lifecycle_manager.create_tab("integration_test")
        lifecycle_manager.activate_tab("integration_test")
        
        # Process messages
        bus.process_messages()
        
        # Should receive tab lifecycle events
        assert len(messages_received) > 0
    
    def test_global_state_management(self, app_controller):
        """Test global state management across components"""
        # Set global state
        app_controller.set_global_state("test_key", "test_value")
        
        # Verify state is accessible
        assert app_controller.get_global_state("test_key") == "test_value"
        
        # Test state change notifications
        change_notifications = []
        
        def state_change_handler(key, old_value, new_value):
            change_notifications.append((key, old_value, new_value))
        
        app_controller.global_state_changed.connect(state_change_handler)
        
        # Change state
        app_controller.set_global_state("test_key", "new_value")
        
        # Verify notification
        assert len(change_notifications) == 1
        assert change_notifications[0] == ("test_key", "test_value", "new_value")
    
    def test_service_dependency_injection(self, app_controller):
        """Test service dependency injection system"""
        # Register a test service with dependencies
        class TestService:
            def __init__(self, component_bus, theme_manager):
                self.bus = component_bus
                self.theme_manager = theme_manager
        
        # Register service
        app_controller.register_service(
            'test_service', TestService, ServiceScope.SINGLETON,
            dependencies=['component_bus', 'theme_manager']
        )
        
        # Get service - should be injected with dependencies
        service = app_controller.get_service('test_service')
        assert service is not None
        assert hasattr(service, 'bus')
        assert hasattr(service, 'theme_manager')
    
    def test_health_monitoring(self, app_controller):
        """Test health monitoring system"""
        # Start monitoring
        app_controller.start_monitoring()
        
        # Wait for health checks
        time.sleep(0.1)
        
        # Verify health status
        health_status = app_controller.get_health_status()
        assert health_status is not None
        assert 'overall_health' in health_status
        assert 'service_health' in health_status


class TestPerformanceBenchmarks(TestV2UIIntegration):
    """Performance benchmarks for V2.0 UI components"""
    
    def test_tab_creation_performance(self, lifecycle_manager):
        """Benchmark tab creation performance"""
        start_time = time.perf_counter()
        
        # Create 100 tabs
        for i in range(100):
            tab_id = f"perf_tab_{i}"
            lifecycle_manager.create_tab(tab_id)
            lifecycle_manager.activate_tab(tab_id)
        
        end_time = time.perf_counter()
        creation_time = end_time - start_time
        
        # Should create 100 tabs in less than 1 second
        assert creation_time < 1.0
        print(f"Created 100 tabs in {creation_time:.3f} seconds")
    
    def test_message_processing_performance(self, component_bus):
        """Benchmark message processing performance"""
        messages_received = []
        
        def fast_handler(message):
            messages_received.append(message)
        
        component_bus.subscribe("benchmark_component", "benchmark_channel", fast_handler)
        
        start_time = time.perf_counter()
        
        # Send 1000 messages
        for i in range(1000):
            component_bus.send_event("sender", "benchmark_channel", f"message_{i}", {"index": i})
        
        # Process all messages
        component_bus.process_messages()
        
        end_time = time.perf_counter()
        processing_time = end_time - start_time
        
        # Should process 1000 messages quickly
        assert len(messages_received) == 1000
        assert processing_time < 0.5  # Less than 500ms
        print(f"Processed 1000 messages in {processing_time:.3f} seconds")
    
    def test_theme_switching_performance(self, theme_manager):
        """Benchmark theme switching performance"""
        start_time = time.perf_counter()
        
        # Switch themes multiple times
        themes = [ThemeVariant.LIGHT, ThemeVariant.DARK, ThemeVariant.HIGH_CONTRAST]
        for _ in range(10):
            for theme in themes:
                theme_manager.switch_theme(theme)
        
        end_time = time.perf_counter()
        switching_time = end_time - start_time
        
        # Should switch themes quickly
        assert switching_time < 1.0  # Less than 1 second for 30 switches
        print(f"Performed 30 theme switches in {switching_time:.3f} seconds")
    
    def test_memory_usage_monitoring(self, app_controller):
        """Monitor memory usage of the integrated system"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform various operations
        lifecycle_manager = app_controller.get_service('tab_lifecycle_manager')
        component_bus = app_controller.get_service('component_bus')
        theme_manager = app_controller.get_service('theme_manager')
        
        # Create tabs, send messages, switch themes
        for i in range(50):
            tab_id = f"memory_test_{i}"
            lifecycle_manager.create_tab(tab_id)
            lifecycle_manager.activate_tab(tab_id)
            
            component_bus.send_event("test", "memory_channel", f"event_{i}", {"data": f"test_{i}"})
            
            if i % 10 == 0:
                theme_manager.switch_theme(ThemeVariant.DARK if i % 20 == 0 else ThemeVariant.LIGHT)
        
        component_bus.process_messages()
        
        # Force garbage collection
        gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"Memory usage: {initial_memory:.1f}MB → {final_memory:.1f}MB (Δ{memory_increase:.1f}MB)")
        
        # Memory increase should be reasonable (less than 50MB for this test)
        assert memory_increase < 50


class TestErrorHandlingAndRecovery(TestV2UIIntegration):
    """Test error handling and recovery mechanisms"""
    
    def test_tab_crash_recovery(self, lifecycle_manager):
        """Test recovery from tab crashes"""
        tab_id = "crash_test_tab"
        
        # Create tab and add state
        lifecycle_manager.create_tab(tab_id)
        lifecycle_manager.activate_tab(tab_id)
        lifecycle_manager.update_tab_state(tab_id, {"important_data": "must_preserve"})
        
        # Simulate crash by forcing tab to error state
        lifecycle_manager._set_tab_state(tab_id, TabState.ERROR)
        
        # Attempt recovery
        recovered = lifecycle_manager.recover_tab(tab_id)
        assert recovered
        
        # Verify state is preserved
        state = lifecycle_manager.get_tab_data(tab_id)
        assert state.get("important_data") == "must_preserve"
    
    def test_component_bus_error_handling(self, component_bus):
        """Test component bus handles errors gracefully"""
        error_count = 0
        
        def failing_handler(message):
            nonlocal error_count
            error_count += 1
            raise ValueError("Simulated handler error")
        
        def working_handler(message):
            # This should still work despite other handler failing
            pass
        
        # Subscribe both handlers
        component_bus.subscribe("failing_component", "test_channel", failing_handler)
        component_bus.subscribe("working_component", "test_channel", working_handler)
        
        # Send message
        component_bus.send_event("sender", "test_channel", "test_event", {"data": "test"})
        
        # Process messages - should not crash despite handler error
        component_bus.process_messages()
        
        # Verify error was handled
        assert error_count == 1
    
    def test_theme_manager_fallback(self, theme_manager):
        """Test theme manager falls back gracefully on errors"""
        # Try to switch to invalid theme
        original_theme = theme_manager.current_variant
        
        # This should fail gracefully and maintain current theme
        success = theme_manager.switch_theme("INVALID_THEME")
        assert not success
        assert theme_manager.current_variant == original_theme
    
    def test_app_controller_service_recovery(self, app_controller):
        """Test app controller can recover from service failures"""
        # Get a service
        original_service = app_controller.get_service('component_bus')
        assert original_service is not None
        
        # Simulate service failure by removing it
        app_controller._services.pop('component_bus', None)
        
        # Try to get service again - should recreate
        recovered_service = app_controller.get_service('component_bus')
        assert recovered_service is not None


# Test utilities and helpers
class MockTab:
    """Mock tab for testing"""
    def __init__(self, tab_id: str):
        self.id = tab_id
        self.state = {}
        self.active = False
    
    def save_state(self):
        return self.state.copy()
    
    def restore_state(self, state):
        self.state = state.copy()


class TestUtilities:
    """Test utilities and helpers"""
    
    @staticmethod
    def create_test_configuration(temp_dir: str) -> Dict[str, Any]:
        """Create test configuration for components"""
        return {
            'state_dir': temp_dir,
            'enable_performance_monitoring': True,
            'enable_hibernation': True,
            'hibernation_threshold': 1,  # 1 second for testing
            'enable_component_bus': True,
            'message_processing_interval': 10,  # 10ms for testing
            'enable_theme_management': True,
            'theme_config_dir': temp_dir
        }
    
    @staticmethod
    def wait_for_condition(condition_func, timeout: float = 5.0, interval: float = 0.1) -> bool:
        """Wait for a condition to become true"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if condition_func():
                return True
            time.sleep(interval)
        return False
    
    @staticmethod
    def measure_performance(func, *args, **kwargs):
        """Measure function execution time and memory usage"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        
        final_memory = process.memory_info().rss
        
        return {
            'result': result,
            'execution_time': end_time - start_time,
            'memory_delta': final_memory - initial_memory,
            'initial_memory': initial_memory,
            'final_memory': final_memory
        }


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"]) 