"""
App Controller Edge Cases and Lifecycle Transition Tests

Comprehensive testing framework for edge cases, unusual state transitions,
thread safety stress tests, and resource leak detection.
"""

import pytest
import asyncio
import threading
import time
import logging
import gc
import weakref
try:
    import resource
except ImportError:
    resource = None  # Not available on Windows
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue, Empty
import signal
import sys

from core.app_controller import AppController, ControllerState, ControllerStatus, ControllerError, get_app_controller
from core.event_system import Event, EventType, EventHandler
from core.services import ContentDTO, AnalyticsDTO

# Import test base classes
from .test_base import DatabaseTestCase, PerformanceTestCase


class TestAppControllerEdgeCases(DatabaseTestCase):
    """Test App Controller edge cases and unusual scenarios"""
    
    def setUp(self):
        """Set up test environment"""
        super().setUp()
        self.controller = AppController()
        self.leaked_objects: List[weakref.ref] = []
    
    def tearDown(self):
        """Clean up test environment"""
        if self.controller and self.controller.is_ready():
            self.controller.shutdown()
        super().tearDown()
    
    def test_rapid_initialization_shutdown_cycles(self):
        """Test rapid initialization and shutdown cycles"""
        cycle_count = 20
        success_count = 0
        
        for i in range(cycle_count):
            controller = AppController()
            
            # Initialize
            init_result = controller.initialize()
            if init_result:
                success_count += 1
                
                # Verify state
                self.assertEqual(controller._state, ControllerState.READY)
                
                # Register a component
                test_component = Mock()
                controller.register_component(f"test_{i}", test_component)
                
                # Shutdown immediately
                shutdown_result = controller.shutdown()
                self.assertTrue(shutdown_result, f"Shutdown {i} should succeed")
                self.assertEqual(controller._state, ControllerState.SHUTDOWN)
        
        # Most cycles should succeed
        success_rate = success_count / cycle_count
        self.assertGreater(success_rate, 0.8, f"Success rate should be > 80%, got {success_rate:.2%}")
        
        print(f"Rapid cycles: {success_count}/{cycle_count} successful ({success_rate:.2%})")
    
    def test_initialization_with_component_failures(self):
        """Test initialization when components fail to initialize"""
        controller = AppController()
        
        # Mock components that fail during initialization
        failing_component = Mock()
        failing_component.initialize = Mock(side_effect=Exception("Component initialization failed"))
        
        working_component = Mock()
        working_component.initialize = Mock(return_value=True)
        
        # Register components before initialization
        controller.register_component("failing", failing_component)
        controller.register_component("working", working_component)
        
        # Controller should still initialize even if some components fail
        with patch('core.app_controller.get_config_manager') as mock_config, \
             patch('core.app_controller.get_event_bus') as mock_event_bus:
            
            mock_config.return_value = Mock()
            mock_config.return_value.config = Mock()
            mock_event_bus.return_value = Mock()
            
            # Initialize controller
            result = controller.initialize()
            
            # Should succeed despite component failures
            self.assertTrue(result)
            self.assertEqual(controller._state, ControllerState.READY)
    
    def test_shutdown_with_hanging_components(self):
        """Test shutdown when components hang during cleanup"""
        self.controller.initialize()
        
        # Create component that hangs during cleanup
        hanging_component = Mock()
        
        def hanging_cleanup():
            time.sleep(2)  # Simulate hanging operation
        
        hanging_component.cleanup = hanging_cleanup
        
        # Create normal component
        normal_component = Mock()
        normal_component.cleanup = Mock()
        
        # Register components
        self.controller.register_component("hanging", hanging_component)
        self.controller.register_component("normal", normal_component)
        
        # Shutdown should complete even with hanging components
        start_time = time.time()
        result = self.controller.shutdown()
        end_time = time.time()
        
        shutdown_time = end_time - start_time
        
        # Should complete within reasonable time (not hang forever)
        self.assertTrue(result)
        self.assertLess(shutdown_time, 5.0, "Shutdown should not hang indefinitely")
        self.assertEqual(self.controller._state, ControllerState.SHUTDOWN)
    
    def test_concurrent_state_transitions(self):
        """Test concurrent state transitions from multiple threads"""
        controller = AppController()
        results = Queue()
        num_threads = 10
        
        def initialize_controller(thread_id):
            try:
                result = controller.initialize()
                results.put(("init", thread_id, result, controller._state))
            except Exception as e:
                results.put(("init_error", thread_id, str(e), controller._state))
        
        def shutdown_controller(thread_id):
            try:
                time.sleep(0.1)  # Wait for initialization attempts
                result = controller.shutdown()
                results.put(("shutdown", thread_id, result, controller._state))
            except Exception as e:
                results.put(("shutdown_error", thread_id, str(e), controller._state))
        
        # Start multiple initialization threads
        threads = []
        for i in range(num_threads // 2):
            thread = threading.Thread(target=initialize_controller, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Start multiple shutdown threads
        for i in range(num_threads // 2, num_threads):
            thread = threading.Thread(target=shutdown_controller, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join(timeout=5)
        
        # Collect results
        all_results = []
        try:
            while True:
                result = results.get_nowait()
                all_results.append(result)
        except Empty:
            pass
        
        # Analyze results
        init_successes = [r for r in all_results if r[0] == "init" and r[2] is True]
        shutdown_successes = [r for r in all_results if r[0] == "shutdown" and r[2] is True]
        errors = [r for r in all_results if "_error" in r[0]]
        
        print(f"Concurrent transitions: {len(init_successes)} init success, {len(shutdown_successes)} shutdown success, {len(errors)} errors")
        
        # Should handle concurrent access gracefully
        self.assertLessEqual(len(errors), num_threads // 2, "Should handle concurrent access with minimal errors")
        
        # At least one operation should succeed
        self.assertGreater(len(init_successes) + len(shutdown_successes), 0, "At least one operation should succeed")
    
    def test_error_during_event_handling(self):
        """Test error handling when event handlers raise exceptions"""
        self.controller.initialize()
        event_bus = self.controller.get_event_bus()
        
        error_count = 0
        
        # Create handler that sometimes fails
        class UnreliableHandler(EventHandler):
            def __init__(self):
                self.call_count = 0
                
            def handle_event(self, event: Event):
                self.call_count += 1
                if self.call_count % 3 == 0:  # Fail every 3rd call
                    raise RuntimeError(f"Handler failure #{self.call_count}")
        
        unreliable_handler = UnreliableHandler()
        event_bus.add_handler(unreliable_handler)
        
        # Send multiple events
        for i in range(10):
            event = Event(EventType.CONTENT_CREATED, {"id": i})
            try:
                event_bus.publish(event)
            except Exception as e:
                error_count += 1
        
        # Event system should be resilient to handler failures
        self.assertLess(error_count, 10, "Event system should handle some handler failures gracefully")
        
        # Controller should still be functional
        self.assertEqual(self.controller._state, ControllerState.READY)
        
        # Cleanup
        event_bus.remove_handler(unreliable_handler)
    
    def test_memory_leak_detection(self):
        """Test for memory leaks in controller operations"""
        initial_objects = len(gc.get_objects())
        
        # Perform operations that might leak memory
        for i in range(100):
            controller = AppController()
            controller.initialize()
            
            # Register components
            for j in range(10):
                component = Mock()
                self.leaked_objects.append(weakref.ref(component))
                controller.register_component(f"comp_{j}", component)
            
            # Handle events
            event_bus = controller.get_event_bus()
            for k in range(10):
                event = Event(EventType.CONTENT_CREATED, {"id": k})
                event_bus.publish(event)
            
            # Shutdown
            controller.shutdown()
        
        # Force garbage collection
        gc.collect()
        
        # Check for leaked objects
        leaked_count = sum(1 for ref in self.leaked_objects if ref() is not None)
        final_objects = len(gc.get_objects())
        object_increase = final_objects - initial_objects
        
        print(f"Memory leak check: {leaked_count} leaked objects, {object_increase} object increase")
        
        # Memory leak assertions
        self.assertLess(leaked_count / len(self.leaked_objects), 0.1, "Less than 10% of objects should be leaked")
        self.assertLess(object_increase, 1000, "Object count increase should be reasonable")
    
    def test_signal_handling_during_operations(self):
        """Test signal handling during controller operations"""
        if sys.platform == "win32":
            self.skipTest("Signal handling test not applicable on Windows")
            return
        
        self.controller.initialize()
        
        # Setup signal handler
        signal_received = False
        
        def signal_handler(signum, frame):
            nonlocal signal_received
            signal_received = True
        
        original_handler = signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Start long-running operation
            event_bus = self.controller.get_event_bus()
            
            # Send signal during operation
            import os
            os.kill(os.getpid(), signal.SIGTERM)
            
            # Small delay to allow signal processing
            time.sleep(0.1)
            
            # Verify signal was received
            self.assertTrue(signal_received, "Signal should have been received")
            
            # Controller should still be operational
            self.assertEqual(self.controller._state, ControllerState.READY)
            
        finally:
            # Restore original signal handler
            signal.signal(signal.SIGTERM, original_handler)
    
    def test_resource_exhaustion_scenarios(self):
        """Test behavior under resource exhaustion"""
        # Test with limited thread resources
        original_threading_limit = threading.active_count()
        
        threads = []
        max_threads = 50
        
        def dummy_worker():
            time.sleep(0.5)
        
        try:
            # Create many threads to exhaust resources
            for i in range(max_threads):
                thread = threading.Thread(target=dummy_worker)
                threads.append(thread)
                thread.start()
            
            # Try to initialize controller under resource pressure
            controller = AppController()
            result = controller.initialize()
            
            # Should handle resource pressure gracefully
            if result:
                self.assertEqual(controller._state, ControllerState.READY)
                controller.shutdown()
            else:
                # Should fail gracefully, not crash
                self.assertEqual(controller._state, ControllerState.ERROR)
            
        except Exception as e:
            # Should not raise unhandled exceptions
            self.fail(f"Resource exhaustion should be handled gracefully, but got: {e}")
        
        finally:
            # Cleanup threads
            for thread in threads:
                thread.join(timeout=1)


class TestAppControllerThreadSafetyStress(PerformanceTestCase):
    """Stress tests for thread safety and concurrent operations"""
    
    def setUp(self):
        """Set up stress test environment"""
        super().setUp()
        self.controller = AppController()
        self.stress_results: Dict[str, Any] = {}
    
    def tearDown(self):
        """Clean up stress test environment"""
        if self.controller and self.controller.is_ready():
            self.controller.shutdown()
        super().tearDown()
    
    def test_concurrent_component_operations(self):
        """Stress test concurrent component registration/unregistration"""
        self.controller.initialize()
        
        num_threads = 20
        operations_per_thread = 50
        results = Queue()
        
        def component_operations(thread_id):
            successes = 0
            failures = 0
            
            for i in range(operations_per_thread):
                try:
                    component_name = f"thread_{thread_id}_comp_{i}"
                    component = Mock()
                    component.name = component_name
                    
                    # Register component
                    reg_result = self.controller.register_component(component_name, component)
                    if reg_result:
                        successes += 1
                        
                        # Brief operation
                        time.sleep(0.001)
                        
                        # Unregister component
                        unreg_result = self.controller.unregister_component(component_name)
                        if not unreg_result:
                            failures += 1
                    else:
                        failures += 1
                        
                except Exception as e:
                    failures += 1
            
            results.put((thread_id, successes, failures))
        
        # Start concurrent threads
        threads = []
        start_time = time.time()
        
        for thread_id in range(num_threads):
            thread = threading.Thread(target=component_operations, args=(thread_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=30)
        
        end_time = time.time()
        
        # Collect results
        total_successes = 0
        total_failures = 0
        
        try:
            while True:
                thread_id, successes, failures = results.get_nowait()
                total_successes += successes
                total_failures += failures
        except Empty:
            pass
        
        total_operations = total_successes + total_failures
        success_rate = total_successes / total_operations if total_operations > 0 else 0
        operations_per_second = total_operations / (end_time - start_time)
        
        self.stress_results["concurrent_components"] = {
            "total_operations": total_operations,
            "success_rate": success_rate,
            "operations_per_second": operations_per_second,
            "duration": end_time - start_time
        }
        
        print(f"Concurrent component operations: {total_operations} ops, {success_rate:.2%} success rate, {operations_per_second:.1f} ops/sec")
        
        # Stress test assertions
        self.assertGreater(success_rate, 0.95, "Success rate should be > 95% under stress")
        self.assertGreater(operations_per_second, 100, "Should handle > 100 operations per second")
    
    def test_concurrent_event_publishing(self):
        """Stress test concurrent event publishing"""
        self.controller.initialize()
        event_bus = self.controller.get_event_bus()
        
        num_threads = 15
        events_per_thread = 100
        results = Queue()
        
        # Add event handlers to increase processing load
        class LoadHandler(EventHandler):
            def __init__(self, handler_id):
                self.handler_id = handler_id
                self.event_count = 0
                
            def handle_event(self, event: Event):
                self.event_count += 1
                # Simulate processing time
                time.sleep(0.0001)
        
        handlers = []
        for i in range(5):
            handler = LoadHandler(i)
            handlers.append(handler)
            event_bus.add_handler(handler)
        
        def publish_events(thread_id):
            successes = 0
            failures = 0
            
            for i in range(events_per_thread):
                try:
                    event = Event(EventType.CONTENT_CREATED, {
                        "thread_id": thread_id,
                        "event_id": i,
                        "timestamp": time.time()
                    })
                    
                    event_bus.publish(event)
                    successes += 1
                    
                except Exception as e:
                    failures += 1
            
            results.put((thread_id, successes, failures))
        
        # Start concurrent event publishing
        threads = []
        start_time = time.time()
        
        for thread_id in range(num_threads):
            thread = threading.Thread(target=publish_events, args=(thread_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=30)
        
        end_time = time.time()
        
        # Collect results
        total_successes = 0
        total_failures = 0
        
        try:
            while True:
                thread_id, successes, failures = results.get_nowait()
                total_successes += successes
                total_failures += failures
        except Empty:
            pass
        
        # Get handler statistics
        total_handled_events = sum(handler.event_count for handler in handlers)
        
        total_published = total_successes + total_failures
        success_rate = total_successes / total_published if total_published > 0 else 0
        events_per_second = total_published / (end_time - start_time)
        
        self.stress_results["concurrent_events"] = {
            "total_published": total_published,
            "total_handled": total_handled_events,
            "success_rate": success_rate,
            "events_per_second": events_per_second,
            "duration": end_time - start_time
        }
        
        print(f"Concurrent event publishing: {total_published} published, {total_handled_events} handled, {success_rate:.2%} success rate, {events_per_second:.1f} events/sec")
        
        # Cleanup handlers
        for handler in handlers:
            event_bus.remove_handler(handler)
        
        # Stress test assertions
        self.assertGreater(success_rate, 0.98, "Event publishing success rate should be > 98%")
        self.assertGreater(events_per_second, 200, "Should handle > 200 events per second")
    
    async def test_concurrent_async_operations(self):
        """Stress test concurrent async operations through controller"""
        self.controller.initialize()
        
        # Mock async services
        mock_content_service = AsyncMock()
        mock_analytics_service = AsyncMock()
        mock_download_service = AsyncMock()
        
        self.controller.register_component("content_service", mock_content_service)
        self.controller.register_component("analytics_service", mock_analytics_service)
        self.controller.register_component("download_service", mock_download_service)
        
        # Setup mock responses
        mock_content_service.create_content.return_value = ContentDTO(
            id=1, url="https://test.com", title="Test"
        )
        mock_analytics_service.get_analytics_overview.return_value = AnalyticsDTO(
            total_downloads=100
        )
        mock_download_service.start_download.return_value = ContentDTO(
            id=2, url="https://download.com", status="DOWNLOADING"
        )
        
        num_concurrent = 50
        operations_per_type = 10
        
        async def async_operations():
            tasks = []
            
            # Create content operations
            for i in range(operations_per_type):
                task = self.controller.create_content_from_url(f"https://test{i}.com")
                tasks.append(task)
            
            # Analytics operations
            for i in range(operations_per_type):
                task = self.controller.get_analytics_overview()
                tasks.append(task)
            
            # Download operations
            for i in range(operations_per_type):
                task = self.controller.start_download(f"https://download{i}.com")
                tasks.append(task)
            
            # Execute all tasks concurrently
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            # Analyze results
            successes = sum(1 for result in results if not isinstance(result, Exception))
            failures = sum(1 for result in results if isinstance(result, Exception))
            
            return successes, failures, end_time - start_time
        
        # Run async stress test
        successes, failures, duration = await async_operations()
        
        total_operations = successes + failures
        success_rate = successes / total_operations if total_operations > 0 else 0
        operations_per_second = total_operations / duration
        
        self.stress_results["concurrent_async"] = {
            "total_operations": total_operations,
            "success_rate": success_rate,
            "operations_per_second": operations_per_second,
            "duration": duration
        }
        
        print(f"Concurrent async operations: {total_operations} ops, {success_rate:.2%} success rate, {operations_per_second:.1f} ops/sec")
        
        # Stress test assertions
        self.assertGreater(success_rate, 0.90, "Async operation success rate should be > 90%")
        self.assertGreater(operations_per_second, 50, "Should handle > 50 async operations per second")
    
    def test_memory_pressure_stress(self):
        """Stress test under memory pressure"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Initialize controller
        self.controller.initialize()
        
        # Create memory pressure
        large_objects = []
        for i in range(100):
            # Create large mock objects
            large_data = [Mock() for _ in range(1000)]
            large_objects.append(large_data)
            
            # Register as components
            self.controller.register_component(f"large_comp_{i}", large_data)
            
            # Publish events
            event_bus = self.controller.get_event_bus()
            for j in range(10):
                event = Event(EventType.CONTENT_CREATED, {"data": large_data[:10]})
                event_bus.publish(event)
        
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - initial_memory
        
        # Test controller operations under memory pressure
        operations_successful = 0
        total_operations = 100
        
        for i in range(total_operations):
            try:
                # Test component operations
                test_comp = Mock()
                reg_result = self.controller.register_component(f"test_comp_{i}", test_comp)
                if reg_result:
                    unreg_result = self.controller.unregister_component(f"test_comp_{i}")
                    if unreg_result:
                        operations_successful += 1
                
                # Test event operations
                event = Event(EventType.CONTENT_CREATED, {"id": i})
                event_bus.publish(event)
                
            except Exception:
                pass
        
        # Cleanup
        for i in range(100):
            self.controller.unregister_component(f"large_comp_{i}")
        
        gc.collect()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        success_rate = operations_successful / total_operations
        
        self.stress_results["memory_pressure"] = {
            "initial_memory_mb": initial_memory,
            "peak_memory_mb": peak_memory,
            "final_memory_mb": final_memory,
            "memory_increase_mb": memory_increase,
            "operations_success_rate": success_rate
        }
        
        print(f"Memory pressure stress: {memory_increase:.1f}MB increase, {success_rate:.2%} operation success rate")
        
        # Memory pressure assertions
        self.assertLess(memory_increase, 500, "Memory increase should be manageable")
        self.assertGreater(success_rate, 0.8, "Operations should still succeed under memory pressure")


if __name__ == "__main__":
    # Configure logging for tests
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"]) 