"""
Unit tests for App Controller

Tests the App Controller's functionality including initialization, component management,
event handling, error handling, and lifecycle management.
"""

import unittest
import threading
import time
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.app_controller import (
    AppController, IAppController, ControllerState, ControllerStatus, ControllerError,
    get_app_controller, initialize_app_controller, shutdown_app_controller
)
from core.event_system import Event, EventType


class MockComponent:
    """Mock component for testing"""
    def __init__(self, name):
        self.name = name
        self.initialized = False
        self.cleanup_called = False
    
    def cleanup(self):
        self.cleanup_called = True


class TestAppController(unittest.TestCase):
    """Test cases for AppController class"""
    
    def setUp(self):
        """Set up test fixtures before each test method"""
        # Reset singleton for clean testing
        import core.app_controller
        core.app_controller._app_controller = None
        
        # Create fresh controller instance
        self.controller = AppController()
        
        # Mock dependencies
        self.mock_config_manager = Mock()
        self.mock_config = Mock()
        self.mock_config_manager.config = self.mock_config
        
        self.mock_event_bus = Mock()
    
    def tearDown(self):
        """Clean up after each test method"""
        if self.controller._state not in [ControllerState.SHUTDOWN, ControllerState.UNINITIALIZED]:
            self.controller.shutdown()
    
    def test_initial_state(self):
        """Test controller initial state"""
        self.assertEqual(self.controller._state, ControllerState.UNINITIALIZED)
        self.assertEqual(len(self.controller._components), 0)
        self.assertIsNone(self.controller._event_bus)
        self.assertIsNone(self.controller._config_manager)
        self.assertIsNone(self.controller._config)
    
    @patch('core.app_controller.get_config_manager')
    @patch('core.app_controller.get_event_bus')
    def test_successful_initialization(self, mock_get_event_bus, mock_get_config_manager):
        """Test successful controller initialization"""
        # Setup mocks
        mock_get_config_manager.return_value = self.mock_config_manager
        mock_get_event_bus.return_value = self.mock_event_bus
        
        # Initialize controller
        result = self.controller.initialize()
        
        # Verify results
        self.assertTrue(result)
        self.assertEqual(self.controller._state, ControllerState.READY)
        self.assertIsNotNone(self.controller._config_manager)
        self.assertIsNotNone(self.controller._event_bus)
        self.assertIsNotNone(self.controller._config)
        
        # Verify component registration
        self.assertIn("config_manager", self.controller._components)
        self.assertIn("event_bus", self.controller._components)
        
        # Verify event bus registration
        self.mock_event_bus.add_handler.assert_called_once_with(self.controller)
    
    @patch('core.app_controller.get_config_manager')
    def test_initialization_failure(self, mock_get_config_manager):
        """Test controller initialization failure"""
        # Setup mock to raise exception
        mock_get_config_manager.side_effect = Exception("Config error")
        
        # Initialize controller
        result = self.controller.initialize()
        
        # Verify failure
        self.assertFalse(result)
        self.assertEqual(self.controller._state, ControllerState.ERROR)
    
    def test_double_initialization(self):
        """Test that double initialization is handled gracefully"""
        with patch('core.app_controller.get_config_manager') as mock_get_config_manager, \
             patch('core.app_controller.get_event_bus') as mock_get_event_bus:
            
            mock_get_config_manager.return_value = self.mock_config_manager
            mock_get_event_bus.return_value = self.mock_event_bus
            
            # First initialization
            result1 = self.controller.initialize()
            self.assertTrue(result1)
            
            # Second initialization should return True but not re-initialize
            result2 = self.controller.initialize()
            self.assertTrue(result2)
            self.assertEqual(self.controller._state, ControllerState.READY)
    
    def test_component_registration(self):
        """Test component registration and retrieval"""
        component = MockComponent("test_component")
        
        # Register component
        result = self.controller.register_component("test", component)
        self.assertTrue(result)
        
        # Retrieve component
        retrieved = self.controller.get_component("test")
        self.assertEqual(retrieved, component)
        
        # Test non-existent component
        non_existent = self.controller.get_component("non_existent")
        self.assertIsNone(non_existent)
    
    def test_component_unregistration(self):
        """Test component unregistration"""
        component = MockComponent("test_component")
        
        # Register and unregister component
        self.controller.register_component("test", component)
        result = self.controller.unregister_component("test")
        self.assertTrue(result)
        
        # Verify component is gone
        retrieved = self.controller.get_component("test")
        self.assertIsNone(retrieved)
        
        # Test unregistering non-existent component
        result = self.controller.unregister_component("non_existent")
        self.assertFalse(result)
    
    def test_error_handling(self):
        """Test error handling functionality"""
        with patch.object(self.controller, '_event_bus') as mock_event_bus:
            error = ValueError("Test error")
            context = "test_context"
            
            # Handle error
            self.controller.handle_error(error, context)
            
            # Verify event was published
            mock_event_bus.publish.assert_called_once()
            published_event = mock_event_bus.publish.call_args[0][0]
            self.assertEqual(published_event.event_type, EventType.ERROR_OCCURRED)
            self.assertEqual(published_event.source, "app_controller")
            self.assertIn("error_type", published_event.data)
            self.assertIn("error_message", published_event.data)
            self.assertIn("context", published_event.data)
    
    def test_error_handler_registration(self):
        """Test custom error handler registration"""
        handler_called = False
        error_received = None
        context_received = None
        
        def test_handler(error, context):
            nonlocal handler_called, error_received, context_received
            handler_called = True
            error_received = error
            context_received = context
        
        # Register handler
        self.controller.add_error_handler(test_handler)
        
        # Trigger error
        test_error = RuntimeError("Test error")
        self.controller.handle_error(test_error, "test_context")
        
        # Verify handler was called
        self.assertTrue(handler_called)
        self.assertEqual(error_received, test_error)
        self.assertEqual(context_received, "test_context")
        
        # Test handler removal
        result = self.controller.remove_error_handler(test_handler)
        self.assertTrue(result)
        
        # Test removing non-existent handler
        result = self.controller.remove_error_handler(test_handler)
        self.assertFalse(result)
    
    def test_event_handling(self):
        """Test event handling functionality"""
        # Test CONFIG_CHANGED event
        config_event = Event(EventType.CONFIG_CHANGED, "test_source")
        with patch.object(self.controller, '_config_manager') as mock_config_manager:
            self.controller.handle_event(config_event)
            mock_config_manager._load_config.assert_called_once()
        
        # Test ERROR_OCCURRED event
        error_event = Event(EventType.ERROR_OCCURRED, "test_source", {"context": "test"})
        # Should not raise exception
        self.controller.handle_event(error_event)
    
    def test_status_retrieval(self):
        """Test status retrieval"""
        # Add some components
        self.controller.register_component("comp1", MockComponent("comp1"))
        self.controller.register_component("comp2", MockComponent("comp2"))
        
        status = self.controller.get_status()
        
        self.assertIsInstance(status, ControllerStatus)
        self.assertEqual(status.state, ControllerState.UNINITIALIZED)
        self.assertIn("comp1", status.components_initialized)
        self.assertIn("comp2", status.components_initialized)
        self.assertEqual(len(status.components_initialized), 2)
    
    def test_convenience_methods(self):
        """Test convenience methods"""
        # Test is_ready when uninitialized
        self.assertFalse(self.controller.is_ready())
        self.assertFalse(self.controller.is_running())
        
        # Test is_ready when ready
        self.controller._state = ControllerState.READY
        self.assertTrue(self.controller.is_ready())
        self.assertTrue(self.controller.is_running())
        
        # Test is_running when running
        self.controller._state = ControllerState.RUNNING
        self.assertFalse(self.controller.is_ready())
        self.assertTrue(self.controller.is_running())
    
    @patch('core.app_controller.get_config_manager')
    @patch('core.app_controller.get_event_bus')
    def test_shutdown(self, mock_get_event_bus, mock_get_config_manager):
        """Test controller shutdown"""
        # Setup mocks
        mock_get_config_manager.return_value = self.mock_config_manager
        mock_get_event_bus.return_value = self.mock_event_bus
        
        # Initialize controller
        self.controller.initialize()
        
        # Add component with cleanup method
        component = MockComponent("test")
        self.controller.register_component("test", component)
        
        # Shutdown controller
        result = self.controller.shutdown()
        
        # Verify shutdown
        self.assertTrue(result)
        self.assertEqual(self.controller._state, ControllerState.SHUTDOWN)
        self.assertTrue(component.cleanup_called)
        
        # Verify event bus cleanup
        self.mock_event_bus.remove_handler.assert_called_once_with(self.controller)
    
    def test_thread_safety(self):
        """Test thread safety of controller operations"""
        results = []
        
        def register_components():
            for i in range(10):
                component = MockComponent(f"comp_{i}")
                result = self.controller.register_component(f"comp_{i}", component)
                results.append(result)
        
        def unregister_components():
            for i in range(5, 15):  # Some overlap, some non-existent
                result = self.controller.unregister_component(f"comp_{i}")
                results.append(result)
        
        # Run operations in parallel
        threads = [
            threading.Thread(target=register_components),
            threading.Thread(target=unregister_components)
        ]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All operations should complete without exception
        self.assertEqual(len(results), 20)


class TestSingletonFunctions(unittest.TestCase):
    """Test singleton access functions"""
    
    def setUp(self):
        """Reset singleton for clean testing"""
        import core.app_controller
        core.app_controller._app_controller = None
    
    def tearDown(self):
        """Cleanup after tests"""
        shutdown_app_controller()
    
    def test_get_app_controller_singleton(self):
        """Test that get_app_controller returns same instance"""
        controller1 = get_app_controller()
        controller2 = get_app_controller()
        
        self.assertIs(controller1, controller2)
        self.assertIsInstance(controller1, AppController)
    
    @patch('core.app_controller.get_config_manager')
    @patch('core.app_controller.get_event_bus')
    def test_initialize_app_controller(self, mock_get_event_bus, mock_get_config_manager):
        """Test global controller initialization"""
        # Setup mocks
        mock_config_manager = Mock()
        mock_config = Mock()
        mock_config_manager.config = mock_config
        mock_get_config_manager.return_value = mock_config_manager
        mock_get_event_bus.return_value = Mock()
        
        # Initialize
        result = initialize_app_controller()
        
        self.assertTrue(result)
        controller = get_app_controller()
        self.assertEqual(controller._state, ControllerState.READY)
    
    def test_shutdown_app_controller(self):
        """Test global controller shutdown"""
        # Get controller instance
        controller = get_app_controller()
        
        # Shutdown
        result = shutdown_app_controller()
        
        self.assertTrue(result)
        
        # New instance should be created next time
        new_controller = get_app_controller()
        self.assertIsNot(controller, new_controller)


if __name__ == '__main__':
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Run tests
    unittest.main() 