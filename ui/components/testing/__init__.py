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

# UI Components Testing Framework
# Task 22.2 - UI Responsiveness Testing Infrastructure

"""
UI Testing Framework for Social Download Manager v2.0

This package provides comprehensive testing infrastructure for UI components,
including responsiveness testing, performance monitoring, and accessibility validation.
"""

from .ui_test_base import UITestBase
from .performance_monitor import UIPerformanceMonitor
from .accessibility_checker import AccessibilityChecker
from .responsiveness_tester import ResponsivenessTester

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
    'RenderingProfiler',

    'UITestBase',
    'UIPerformanceMonitor', 
    'AccessibilityChecker',
    'ResponsivenessTester'
]

__version__ = '2.0.0'
__task__ = '22.2 - UI Responsiveness Testing' 