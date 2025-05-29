"""
Component Testing Framework

Comprehensive testing utilities for UI components including:
- Unit testing for component logic
- Widget testing for UI interactions  
- Integration testing for component interactions
- Performance testing and benchmarking
- Mock utilities and test data generation
- Automated test discovery and execution
"""

from .component_tester import (
    ComponentTester, TestResult, TestSuite, TestCategory,
    ComponentTestCase, PerformanceTestResult
)
from .widget_tester import (
    WidgetTester, WidgetTestCase, InteractionTest,
    RenderingTest, ValidationTest
)
from .integration_tester import (
    IntegrationTester, IntegrationTestCase, ComponentInteractionTest,
    StateConsistencyTest, EventFlowTest
)
from .mock_utilities import (
    MockComponent, MockDataGenerator, TestDataFactory,
    MockEventBus, MockThemeManager
)
from .test_runner import (
    ComponentTestRunner, TestReport, TestConfiguration,
    execute_test_suite, discover_tests, generate_test_report
)
from .performance_tester import (
    PerformanceTester, PerformanceMetrics, BenchmarkTest,
    MemoryProfiler, RenderingProfiler
)

__all__ = [
    # Core testing framework
    'ComponentTester',
    'TestResult', 
    'TestSuite',
    'TestCategory',
    'ComponentTestCase',
    'PerformanceTestResult',
    
    # Widget testing
    'WidgetTester',
    'WidgetTestCase',
    'InteractionTest',
    'RenderingTest', 
    'ValidationTest',
    
    # Integration testing
    'IntegrationTester',
    'IntegrationTestCase',
    'ComponentInteractionTest',
    'StateConsistencyTest',
    'EventFlowTest',
    
    # Mock utilities
    'MockComponent',
    'MockDataGenerator',
    'TestDataFactory',
    'MockEventBus',
    'MockThemeManager',
    
    # Test execution
    'ComponentTestRunner',
    'TestReport',
    'TestConfiguration',
    'execute_test_suite',
    'discover_tests',
    'generate_test_report',
    
    # Performance testing
    'PerformanceTester',
    'PerformanceMetrics',
    'BenchmarkTest',
    'MemoryProfiler',
    'RenderingProfiler'
] 