"""
App Controller Test Utilities

Utility functions, mock factories, and helper classes for comprehensive
App Controller testing scenarios.
"""

import threading
import time
import logging
import asyncio
from typing import Dict, List, Any, Optional, Callable, Type, Union
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from dataclasses import dataclass
from enum import Enum
from contextlib import contextmanager
import random
import string

from core.app_controller import AppController, ControllerState, ControllerStatus
from core.event_system import Event, EventType, EventHandler
from core.services import ContentDTO, AnalyticsDTO, DownloadRequestDTO
from data.models import ContentStatus, PlatformType, ContentType


class TestScenario(Enum):
    """Predefined test scenarios"""
    BASIC_INITIALIZATION = "basic_initialization"
    RAPID_CYCLES = "rapid_cycles" 
    COMPONENT_FAILURES = "component_failures"
    MEMORY_PRESSURE = "memory_pressure"
    CONCURRENT_ACCESS = "concurrent_access"
    ERROR_CONDITIONS = "error_conditions"
    ASYNC_OPERATIONS = "async_operations"
    EVENT_CASCADES = "event_cascades"


@dataclass
class TestResult:
    """Test execution result"""
    scenario: TestScenario
    success: bool
    duration: float
    metrics: Dict[str, Any]
    errors: List[str]
    warnings: List[str]


class MockComponentFactory:
    """Factory for creating mock components for testing"""
    
    @staticmethod
    def create_basic_component(name: str, **kwargs) -> Mock:
        """Create a basic mock component"""
        component = Mock()
        component.name = name
        component.initialized = kwargs.get('initialized', False)
        component.disposed = kwargs.get('disposed', False)
        
        # Add common methods
        component.initialize = Mock(return_value=kwargs.get('init_result', True))
        component.cleanup = Mock()
        component.dispose = Mock()
        
        return component
    
    @staticmethod
    def create_failing_component(name: str, failure_type: str = "init") -> Mock:
        """Create a component that fails during specific operations"""
        component = MockComponentFactory.create_basic_component(name)
        
        if failure_type == "init":
            component.initialize = Mock(side_effect=Exception(f"{name} initialization failed"))
        elif failure_type == "cleanup":
            component.cleanup = Mock(side_effect=Exception(f"{name} cleanup failed"))
        elif failure_type == "dispose":
            component.dispose = Mock(side_effect=Exception(f"{name} disposal failed"))
        
        return component
    
    @staticmethod
    def create_hanging_component(name: str, hang_duration: float = 2.0) -> Mock:
        """Create a component that hangs during cleanup"""
        component = MockComponentFactory.create_basic_component(name)
        
        def hanging_cleanup():
            time.sleep(hang_duration)
        
        component.cleanup = hanging_cleanup
        return component
    
    @staticmethod
    def create_memory_intensive_component(name: str, size_mb: int = 10) -> Mock:
        """Create a component that uses significant memory"""
        component = MockComponentFactory.create_basic_component(name)
        
        # Create large data structure
        large_data = [f"data_{i}" * 1000 for i in range(size_mb * 100)]
        component.large_data = large_data
        
        return component
    
    @staticmethod
    def create_async_component(name: str, **kwargs) -> Mock:
        """Create a component with async operations"""
        component = MockComponentFactory.create_basic_component(name)
        
        # Add async methods
        component.async_initialize = AsyncMock(return_value=kwargs.get('init_result', True))
        component.async_cleanup = AsyncMock()
        component.process_async = AsyncMock(return_value=kwargs.get('process_result', "success"))
        
        return component


class MockServiceFactory:
    """Factory for creating mock services for testing"""
    
    @staticmethod
    def create_content_service(**kwargs) -> AsyncMock:
        """Create a mock content service"""
        service = AsyncMock()
        
        # Setup default responses
        service.create_content.return_value = ContentDTO(
            id=kwargs.get('content_id', 1),
            url=kwargs.get('url', "https://test.com"),
            title=kwargs.get('title', "Test Content"),
            status=kwargs.get('status', ContentStatus.PENDING)
        )
        
        service.get_content_by_id.return_value = service.create_content.return_value
        service.get_content_by_url.return_value = service.create_content.return_value
        service.update_content.return_value = service.create_content.return_value
        service.delete_content.return_value = True
        
        # Configure failure scenarios if specified
        if kwargs.get('fail_create', False):
            service.create_content.side_effect = Exception("Create content failed")
        if kwargs.get('fail_update', False):
            service.update_content.side_effect = Exception("Update content failed")
        
        return service
    
    @staticmethod
    def create_analytics_service(**kwargs) -> AsyncMock:
        """Create a mock analytics service"""
        service = AsyncMock()
        
        # Setup default responses
        service.get_analytics_overview.return_value = AnalyticsDTO(
            total_downloads=kwargs.get('total_downloads', 100),
            successful_downloads=kwargs.get('successful_downloads', 95),
            failed_downloads=kwargs.get('failed_downloads', 5),
            success_rate=kwargs.get('success_rate', 95.0)
        )
        
        service.get_platform_statistics.return_value = {}
        service.get_download_trends.return_value = {}
        
        # Configure failure scenarios if specified
        if kwargs.get('fail_analytics', False):
            service.get_analytics_overview.side_effect = Exception("Analytics failed")
        
        return service
    
    @staticmethod
    def create_download_service(**kwargs) -> AsyncMock:
        """Create a mock download service"""
        service = AsyncMock()
        
        # Setup default responses
        service.start_download.return_value = ContentDTO(
            id=kwargs.get('content_id', 1),
            url=kwargs.get('url', "https://download.com"),
            status=kwargs.get('status', ContentStatus.DOWNLOADING)
        )
        
        service.get_download_progress.return_value = None
        service.cancel_download.return_value = True
        service.retry_download.return_value = True
        
        # Configure failure scenarios if specified
        if kwargs.get('fail_download', False):
            service.start_download.side_effect = Exception("Download failed")
        
        return service


class EventGenerator:
    """Utility for generating test events"""
    
    @staticmethod
    def generate_random_event(event_type: Optional[EventType] = None) -> Event:
        """Generate a random event for testing"""
        if event_type is None:
            event_type = random.choice(list(EventType))
        
        data = {
            "id": random.randint(1, 1000),
            "timestamp": time.time(),
            "test_data": ''.join(random.choices(string.ascii_letters, k=10))
        }
        
        return Event(event_type, data)
    
    @staticmethod
    def generate_event_sequence(count: int, event_types: Optional[List[EventType]] = None) -> List[Event]:
        """Generate a sequence of events"""
        if event_types is None:
            event_types = [EventType.CONTENT_CREATED, EventType.DOWNLOAD_STARTED, EventType.DOWNLOAD_COMPLETED]
        
        events = []
        for i in range(count):
            event_type = random.choice(event_types)
            event = EventGenerator.generate_random_event(event_type)
            events.append(event)
        
        return events
    
    @staticmethod
    def create_cascade_events() -> List[Event]:
        """Create events that trigger cascading effects"""
        return [
            Event(EventType.APP_STARTUP, {"version": "1.0.0"}),
            Event(EventType.CONTENT_CREATED, {"id": 1, "url": "https://test.com"}),
            Event(EventType.DOWNLOAD_STARTED, {"content_id": 1}),
            Event(EventType.DOWNLOAD_PROGRESS, {"content_id": 1, "progress": 50}),
            Event(EventType.DOWNLOAD_COMPLETED, {"content_id": 1, "file_path": "/test/file.mp4"})
        ]


class TestDataGenerator:
    """Utility for generating test data"""
    
    @staticmethod
    def generate_content_dto(**kwargs) -> ContentDTO:
        """Generate a ContentDTO for testing"""
        return ContentDTO(
            id=kwargs.get('id', random.randint(1, 1000)),
            url=kwargs.get('url', f"https://test{random.randint(1, 100)}.com"),
            platform=kwargs.get('platform', random.choice(list(PlatformType))),
            content_type=kwargs.get('content_type', random.choice(list(ContentType))),
            title=kwargs.get('title', f"Test Content {random.randint(1, 100)}"),
            author=kwargs.get('author', f"Test Author {random.randint(1, 50)}"),
            status=kwargs.get('status', random.choice(list(ContentStatus)))
        )
    
    @staticmethod
    def generate_multiple_content(count: int, **kwargs) -> List[ContentDTO]:
        """Generate multiple ContentDTOs"""
        return [TestDataGenerator.generate_content_dto(**kwargs) for _ in range(count)]
    
    @staticmethod
    def generate_download_request(**kwargs) -> DownloadRequestDTO:
        """Generate a DownloadRequestDTO for testing"""
        return DownloadRequestDTO(
            url=kwargs.get('url', f"https://download{random.randint(1, 100)}.com"),
            platform=kwargs.get('platform', random.choice(list(PlatformType))),
            quality=kwargs.get('quality', random.choice(["720p", "1080p", "best"])),
            format_preference=kwargs.get('format', random.choice(["mp4", "mp3", "webm"]))
        )


class ControllerTestBuilder:
    """Builder pattern for creating complex controller test scenarios"""
    
    def __init__(self):
        self.controller: Optional[AppController] = None
        self.components: List[Mock] = []
        self.services: Dict[str, Mock] = {}
        self.event_handlers: List[EventHandler] = []
        self.configuration: Dict[str, Any] = {}
        self.test_scenario: Optional[TestScenario] = None
        self.expected_failures: List[str] = []
    
    def with_controller(self, controller: Optional[AppController] = None) -> 'ControllerTestBuilder':
        """Set the controller to test"""
        self.controller = controller or AppController()
        return self
    
    def with_component(self, name: str, component: Optional[Mock] = None, **kwargs) -> 'ControllerTestBuilder':
        """Add a component to the test setup"""
        if component is None:
            component = MockComponentFactory.create_basic_component(name, **kwargs)
        
        self.components.append((name, component))
        return self
    
    def with_failing_component(self, name: str, failure_type: str = "init") -> 'ControllerTestBuilder':
        """Add a failing component to the test setup"""
        component = MockComponentFactory.create_failing_component(name, failure_type)
        self.components.append((name, component))
        self.expected_failures.append(f"{name}_{failure_type}_failure")
        return self
    
    def with_service(self, service_type: str, service: Optional[Mock] = None, **kwargs) -> 'ControllerTestBuilder':
        """Add a service to the test setup"""
        if service is None:
            if service_type == "content":
                service = MockServiceFactory.create_content_service(**kwargs)
            elif service_type == "analytics":
                service = MockServiceFactory.create_analytics_service(**kwargs)
            elif service_type == "download":
                service = MockServiceFactory.create_download_service(**kwargs)
            else:
                service = AsyncMock()
        
        self.services[f"{service_type}_service"] = service
        return self
    
    def with_event_handler(self, handler: EventHandler) -> 'ControllerTestBuilder':
        """Add an event handler to the test setup"""
        self.event_handlers.append(handler)
        return self
    
    def with_configuration(self, **config) -> 'ControllerTestBuilder':
        """Set configuration for the test"""
        self.configuration.update(config)
        return self
    
    def with_scenario(self, scenario: TestScenario) -> 'ControllerTestBuilder':
        """Set the test scenario"""
        self.test_scenario = scenario
        return self
    
    def build(self) -> 'ControllerTestContext':
        """Build the test context"""
        return ControllerTestContext(
            controller=self.controller,
            components=self.components,
            services=self.services,
            event_handlers=self.event_handlers,
            configuration=self.configuration,
            test_scenario=self.test_scenario,
            expected_failures=self.expected_failures
        )


@dataclass
class ControllerTestContext:
    """Context for controller testing"""
    controller: AppController
    components: List[tuple]
    services: Dict[str, Mock]
    event_handlers: List[EventHandler]
    configuration: Dict[str, Any]
    test_scenario: Optional[TestScenario]
    expected_failures: List[str]
    
    def setup(self) -> None:
        """Setup the test context"""
        # Register components
        for name, component in self.components:
            self.controller.register_component(name, component)
        
        # Register services
        for service_name, service in self.services.items():
            self.controller.register_component(service_name, service)
        
        # Initialize controller
        with self._mock_dependencies():
            self.controller.initialize()
        
        # Add event handlers
        if self.controller.get_event_bus():
            for handler in self.event_handlers:
                self.controller.get_event_bus().add_handler(handler)
    
    def teardown(self) -> None:
        """Teardown the test context"""
        # Remove event handlers
        if self.controller.get_event_bus():
            for handler in self.event_handlers:
                try:
                    self.controller.get_event_bus().remove_handler(handler)
                except:
                    pass
        
        # Shutdown controller
        if self.controller.is_ready():
            self.controller.shutdown()
    
    @contextmanager
    def _mock_dependencies(self):
        """Mock external dependencies for testing"""
        with patch('core.app_controller.get_config_manager') as mock_config, \
             patch('core.app_controller.get_event_bus') as mock_event_bus:
            
            # Setup mock config
            mock_config_manager = Mock()
            mock_config_manager.config = Mock()
            for key, value in self.configuration.items():
                setattr(mock_config_manager.config, key, value)
            mock_config.return_value = mock_config_manager
            
            # Setup mock event bus
            mock_event_bus.return_value = Mock()
            
            yield


class PerformanceProfiler:
    """Utility for profiling controller performance"""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self.start_times: Dict[str, float] = {}
    
    def start(self, operation: str) -> None:
        """Start timing an operation"""
        self.start_times[operation] = time.perf_counter()
    
    def stop(self, operation: str) -> float:
        """Stop timing an operation and return duration"""
        if operation not in self.start_times:
            return 0.0
        
        duration = time.perf_counter() - self.start_times[operation]
        
        if operation not in self.metrics:
            self.metrics[operation] = []
        
        self.metrics[operation].append(duration)
        del self.start_times[operation]
        
        return duration
    
    def get_stats(self, operation: str) -> Dict[str, float]:
        """Get statistics for an operation"""
        if operation not in self.metrics or not self.metrics[operation]:
            return {}
        
        times = self.metrics[operation]
        return {
            "count": len(times),
            "total": sum(times),
            "average": sum(times) / len(times),
            "min": min(times),
            "max": max(times),
            "median": sorted(times)[len(times) // 2]
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all operations"""
        return {op: self.get_stats(op) for op in self.metrics.keys()}
    
    @contextmanager
    def profile(self, operation: str):
        """Context manager for profiling operations"""
        self.start(operation)
        try:
            yield
        finally:
            self.stop(operation)


class ConcurrencyTester:
    """Utility for testing concurrent operations"""
    
    @staticmethod
    def run_concurrent_operations(operations: List[Callable], max_workers: int = 10, timeout: float = 30.0) -> List[Any]:
        """Run operations concurrently and return results"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all operations
            future_to_op = {executor.submit(op): op for op in operations}
            
            # Collect results
            for future in as_completed(future_to_op, timeout=timeout):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append(e)
        
        return results
    
    @staticmethod
    async def run_concurrent_async_operations(operations: List[Callable], timeout: float = 30.0) -> List[Any]:
        """Run async operations concurrently and return results"""
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*[op() for op in operations], return_exceptions=True),
                timeout=timeout
            )
            return results
        except asyncio.TimeoutError:
            return [TimeoutError("Operation timed out")]


class MemoryTracker:
    """Utility for tracking memory usage during tests"""
    
    def __init__(self):
        self.snapshots: List[Dict[str, Any]] = []
        self.start_memory: Optional[float] = None
    
    def take_snapshot(self, label: str) -> Dict[str, Any]:
        """Take a memory usage snapshot"""
        try:
            import psutil
            import os
            import gc
            
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            snapshot = {
                "label": label,
                "timestamp": time.time(),
                "rss_mb": memory_info.rss / 1024 / 1024,
                "vms_mb": memory_info.vms / 1024 / 1024,
                "objects_count": len(gc.get_objects())
            }
            
            self.snapshots.append(snapshot)
            
            if self.start_memory is None:
                self.start_memory = snapshot["rss_mb"]
            
            return snapshot
            
        except ImportError:
            # psutil not available
            snapshot = {
                "label": label,
                "timestamp": time.time(),
                "rss_mb": 0,
                "vms_mb": 0,
                "objects_count": len(gc.get_objects()) if 'gc' in locals() else 0
            }
            self.snapshots.append(snapshot)
            return snapshot
    
    def get_memory_increase(self) -> float:
        """Get total memory increase since start"""
        if not self.snapshots or self.start_memory is None:
            return 0.0
        
        current_memory = self.snapshots[-1]["rss_mb"]
        return current_memory - self.start_memory
    
    def get_peak_memory(self) -> float:
        """Get peak memory usage"""
        if not self.snapshots:
            return 0.0
        
        return max(snapshot["rss_mb"] for snapshot in self.snapshots)
    
    def cleanup_check(self) -> Dict[str, Any]:
        """Check if memory was properly cleaned up"""
        if len(self.snapshots) < 2:
            return {"status": "insufficient_data"}
        
        start_memory = self.snapshots[0]["rss_mb"]
        end_memory = self.snapshots[-1]["rss_mb"]
        peak_memory = self.get_peak_memory()
        
        memory_retained = end_memory - start_memory
        cleanup_efficiency = 1.0 - (memory_retained / (peak_memory - start_memory)) if peak_memory > start_memory else 1.0
        
        return {
            "status": "analyzed",
            "start_memory_mb": start_memory,
            "end_memory_mb": end_memory,
            "peak_memory_mb": peak_memory,
            "memory_retained_mb": memory_retained,
            "cleanup_efficiency": cleanup_efficiency,
            "leak_detected": memory_retained > 10  # More than 10MB retained
        }


# Test utility functions

def create_test_controller_with_scenario(scenario: TestScenario) -> ControllerTestContext:
    """Create a controller with a predefined test scenario"""
    builder = ControllerTestBuilder().with_scenario(scenario)
    
    if scenario == TestScenario.BASIC_INITIALIZATION:
        builder.with_component("basic_comp").with_service("content")
    
    elif scenario == TestScenario.COMPONENT_FAILURES:
        builder.with_failing_component("failing_comp", "init")
        builder.with_component("working_comp")
    
    elif scenario == TestScenario.MEMORY_PRESSURE:
        for i in range(10):
            builder.with_component(f"memory_comp_{i}", 
                MockComponentFactory.create_memory_intensive_component(f"memory_comp_{i}"))
    
    elif scenario == TestScenario.CONCURRENT_ACCESS:
        builder.with_component("concurrent_comp")
        builder.with_service("content")
        builder.with_service("analytics")
    
    elif scenario == TestScenario.ERROR_CONDITIONS:
        builder.with_service("content", fail_create=True)
        builder.with_failing_component("error_comp", "cleanup")
    
    return builder.build()


def assert_controller_health(controller: AppController, context: str = "") -> None:
    """Assert that controller is in a healthy state"""
    assert controller is not None, f"Controller should not be None {context}"
    assert controller._state in [ControllerState.READY, ControllerState.RUNNING], \
        f"Controller should be in healthy state, got {controller._state} {context}"
    
    status = controller.get_status()
    assert status is not None, f"Controller status should be available {context}"
    assert len(status.components_initialized) > 0, f"Some components should be initialized {context}" 