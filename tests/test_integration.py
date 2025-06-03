"""
Integration tests for App Controller

Tests the integration of App Controller with other system components
including configuration, events, and application lifecycle.
"""

import unittest
import sys
import os

# Add parent directory to path for imports  
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_utils import (
    IntegrationTestCase, ControllerTestFixture, TestEventHandler,
    MockComponent, MockEventBus, MockConfigManager,
    create_test_app_config, create_test_event,
    assert_event_published, get_published_events_by_type
)

from core.app_controller import AppController, ControllerState
from core.event_system import EventType, Event


class TestAppControllerIntegration(unittest.TestCase):
    """Integration tests for App Controller"""
    
    def setUp(self):
        """Set up integration test fixture"""
        self.integration_test = IntegrationTestCase()
        self.integration_test.setup()
        self.controller = self.integration_test.controller
        self.fixture = self.integration_test.fixture
        self.event_handler = self.integration_test.event_handler
    
    def tearDown(self):
        """Clean up after integration tests"""
        self.integration_test.teardown()
    
    def test_complete_application_lifecycle(self):
        """Test complete application lifecycle integration"""
        # Use the built-in lifecycle simulation
        self.integration_test.simulate_app_lifecycle()
        
        # Additional verification
        self.assertEqual(self.controller._state, ControllerState.SHUTDOWN)
        
        # Verify all expected event types were published
        expected_events = [EventType.APP_STARTUP, EventType.ERROR_OCCURRED, EventType.APP_SHUTDOWN]
        for event_type in expected_events:
            events = self.event_handler.get_events_by_type(event_type)
            self.assertGreater(len(events), 0, f"No {event_type} events received")
    
    def test_config_integration(self):
        """Test configuration system integration"""
        # Verify config access through controller
        config = self.controller.get_config()
        self.assertIsNotNone(config)
        self.assertEqual(config.app_name, "Test Social Download Manager")
        
        # Test config change event handling
        config_event = create_test_event(EventType.CONFIG_CHANGED, "test_config")
        self.fixture.mock_event_bus.publish(config_event)
        
        # Verify config manager reload was called
        self.assertTrue(self.fixture.mock_config_manager.load_called)
    
    def test_event_system_integration(self):
        """Test event system integration"""
        # Verify controller is registered as event handler
        self.assertIn(self.controller, self.fixture.mock_event_bus.handlers)
        
        # Test event publishing from controller
        test_data = {"test_key": "test_value"}
        self.controller._publish_event(EventType.UI_UPDATE_REQUIRED, test_data)
        
        # Verify event was published
        ui_events = get_published_events_by_type(self.fixture.mock_event_bus, EventType.UI_UPDATE_REQUIRED)
        self.assertEqual(len(ui_events), 1)
        self.assertEqual(ui_events[0].source, "app_controller")
        self.assertEqual(ui_events[0].data, test_data)
    
    def test_component_lifecycle_integration(self):
        """Test component lifecycle integration"""
        # Add components with different behaviors
        normal_comp = self.fixture.add_test_component("normal_component")
        failing_comp = MockComponent("failing_component", should_fail_cleanup=True)
        self.fixture.add_test_component("failing_component", failing_comp)
        
        # Verify components are registered
        self.assertEqual(self.controller.get_component("normal_component"), normal_comp)
        self.assertEqual(self.controller.get_component("failing_component"), failing_comp)
        
        # Shutdown controller (should handle failing cleanup gracefully)
        result = self.controller.shutdown()
        self.assertTrue(result)  # Should still succeed despite cleanup failure
        
        # Verify normal component was cleaned up
        self.assertTrue(normal_comp.cleanup_called)
        self.assertTrue(failing_comp.cleanup_called)
    
    def test_error_handling_integration(self):
        """Test error handling integration across components"""
        error_handler_called = False
        received_error = None
        received_context = None
        
        def test_error_handler(error, context):
            nonlocal error_handler_called, received_error, received_context
            error_handler_called = True
            received_error = error
            received_context = context
        
        # Add custom error handler
        self.fixture.add_error_handler(test_error_handler)
        
        # Simulate component error
        test_component = self.fixture.add_test_component("error_component")
        try:
            test_component.simulate_error()
        except RuntimeError as e:
            self.controller.handle_error(e, "component_error_test")
        
        # Verify error handling integration
        self.assertTrue(error_handler_called)
        self.assertIsInstance(received_error, RuntimeError)
        self.assertEqual(received_context, "component_error_test")
        
        # Verify error event was published
        error_events = self.event_handler.get_events_by_type(EventType.ERROR_OCCURRED)
        self.assertGreater(len(error_events), 0)
        
        error_event = error_events[-1]  # Get latest error event
        self.assertEqual(error_event.source, "app_controller")
        self.assertIn("error_type", error_event.data)
        self.assertIn("context", error_event.data)
        self.assertEqual(error_event.data["context"], "component_error_test")
    
    def test_multi_component_interaction(self):
        """Test interactions between multiple components"""
        # Add multiple components
        components = {}
        for i in range(3):
            comp_name = f"component_{i}"
            components[comp_name] = self.fixture.add_test_component(comp_name)
        
        # Verify all components are registered
        status = self.controller.get_status()
        for comp_name in components.keys():
            self.assertIn(comp_name, status.components_initialized)
        
        # Simulate component interactions through events
        for i, comp_name in enumerate(components.keys()):
            event_data = {"source_component": comp_name, "message": f"Hello from {comp_name}"}
            test_event = create_test_event(EventType.UI_UPDATE_REQUIRED, comp_name, event_data)
            self.fixture.mock_event_bus.publish(test_event)
        
        # Verify all interaction events were handled
        ui_events = self.event_handler.get_events_by_type(EventType.UI_UPDATE_REQUIRED)
        self.assertEqual(len(ui_events), 3)  # One from each component
    
    def test_concurrent_component_operations(self):
        """Test concurrent component operations"""
        import threading
        import time
        
        results = []
        
        def add_remove_components():
            for i in range(5):
                comp_name = f"thread_comp_{threading.current_thread().ident}_{i}"
                component = MockComponent(comp_name)
                
                # Register component
                result = self.controller.register_component(comp_name, component)
                results.append(("register", comp_name, result))
                
                # Brief pause
                time.sleep(0.001)
                
                # Unregister component
                result = self.controller.unregister_component(comp_name)
                results.append(("unregister", comp_name, result))
        
        # Run concurrent operations
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=add_remove_components)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify all operations completed successfully
        register_results = [r for r in results if r[0] == "register"]
        unregister_results = [r for r in results if r[0] == "unregister"]
        
        self.assertEqual(len(register_results), 15)  # 3 threads * 5 components
        self.assertEqual(len(unregister_results), 15)
        
        # All operations should have succeeded
        for operation, comp_name, result in results:
            self.assertTrue(result, f"{operation} failed for {comp_name}")
    
    def test_controller_state_consistency(self):
        """Test controller state consistency across operations"""
        # Verify initial state
        self.assertEqual(self.controller._state, ControllerState.READY)
        self.assertTrue(self.controller.is_ready())
        self.assertTrue(self.controller.is_running())
        
        # Add components and verify state consistency
        for i in range(5):
            self.fixture.add_test_component(f"state_test_comp_{i}")
            
            # State should remain consistent
            self.assertEqual(self.controller._state, ControllerState.READY)
            status = self.controller.get_status()
            self.assertEqual(status.state, ControllerState.READY)
        
        # Simulate error and verify state handling
        try:
            raise ValueError("Test state error")
        except ValueError as e:
            self.controller.handle_error(e, "state_test")
        
        # Controller should still be ready after handling error
        self.assertEqual(self.controller._state, ControllerState.READY)
    
    def test_event_propagation_chain(self):
        """Test event propagation through the system"""
        # Create a chain of event handlers
        chain_events = []
        test_fixture = self.fixture  # Capture fixture reference for handlers
        max_chain_length = 5  # Limit chain length to prevent infinite recursion
        
        class ChainEventHandler:
            def __init__(self, name):
                self.name = name
            
            def handle_event(self, event):
                chain_events.append((self.name, event.event_type, event.source))
                
                # Only propagate if we haven't reached max length and not an end event
                if (len(chain_events) < max_chain_length and 
                    event.source != "chain_end" and 
                    not event.source.startswith("chain_")):
                    
                    new_event = create_test_event(
                        EventType.UI_UPDATE_REQUIRED,
                        f"chain_{self.name}",
                        {"original_source": event.source, "chain_step": len(chain_events)}
                    )
                    test_fixture.mock_event_bus.publish(new_event)
        
        # Add chain handlers
        handler1 = ChainEventHandler("handler1")
        handler2 = ChainEventHandler("handler2")
        
        self.fixture.mock_event_bus.add_handler(handler1)
        self.fixture.mock_event_bus.add_handler(handler2)
        
        # Start the chain with a simple event
        initial_event = create_test_event(EventType.UI_UPDATE_REQUIRED, "chain_start")
        self.fixture.mock_event_bus.publish(initial_event)
        
        # Verify event propagation occurred but didn't go infinite
        self.assertGreater(len(chain_events), 0)
        self.assertLessEqual(len(chain_events), max_chain_length * 2)  # 2 handlers max
        
        # Verify we can still publish normal events
        end_event = create_test_event(EventType.UI_UPDATE_REQUIRED, "chain_end")
        initial_chain_length = len(chain_events)
        self.fixture.mock_event_bus.publish(end_event)
        
        # Verify end event was handled but didn't propagate
        chain_end_events = [e for e in chain_events if e[2] == "chain_end"]
        self.assertGreater(len(chain_end_events), 0)
        self.assertEqual(len(chain_events) - initial_chain_length, 2)  # 2 handlers handled end event


class TestControllerRecovery(unittest.TestCase):
    """Test controller recovery scenarios"""
    
    def setUp(self):
        """Set up recovery test fixture"""
        self.fixture = ControllerTestFixture()
    
    def tearDown(self):
        """Clean up after recovery tests"""
        self.fixture.teardown()
    
    def test_recovery_from_initialization_failure(self):
        """Test controller recovery from initialization failure"""
        # Create controller but don't initialize
        controller = self.fixture.setup(initialize_controller=False)
        
        # Simulate initialization failure
        import core.app_controller
        original_get_config = core.app_controller.get_config_manager
        
        def failing_get_config():
            raise RuntimeError("Config system failure")
        
        core.app_controller.get_config_manager = failing_get_config
        
        # Attempt initialization (should fail)
        result = controller.initialize()
        self.assertFalse(result)
        self.assertEqual(controller._state, ControllerState.ERROR)
        
        # Restore working config manager
        core.app_controller.get_config_manager = lambda: self.fixture.mock_config_manager
        
        # Controller should still be in error state and not retry automatically
        self.assertEqual(controller._state, ControllerState.ERROR)
        
        # Clean shutdown should still work
        result = controller.shutdown()
        self.assertTrue(result)
        
        # Restore original function
        core.app_controller.get_config_manager = original_get_config
    
    def test_graceful_degradation(self):
        """Test graceful degradation when components fail"""
        controller = self.fixture.setup()
        
        # Add components that will fail
        failing_comp = MockComponent("failing_comp", should_fail_cleanup=True)
        normal_comp = MockComponent("normal_comp")
        
        controller.register_component("failing", failing_comp)
        controller.register_component("normal", normal_comp)
        
        # Shutdown should handle failures gracefully
        result = controller.shutdown()
        self.assertTrue(result)  # Should succeed despite component failure
        
        # Both components should have had cleanup attempted
        self.assertTrue(failing_comp.cleanup_called)
        self.assertTrue(normal_comp.cleanup_called)
        
        # Controller should be in shutdown state
        self.assertEqual(controller._state, ControllerState.SHUTDOWN)


if __name__ == '__main__':
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Run integration tests
    unittest.main() 