"""
Core Component Testing Framework

Provides comprehensive unit testing capabilities for UI components including:
- Test case management and execution
- Result collection and reporting
- Performance metrics tracking
- Test categorization and filtering
- Assertion utilities and verification helpers
"""

import time
import json
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable, Union, Type, Tuple
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtTest import QTest


class TestCategory(Enum):
    """Test categories for organization"""
    UNIT = "unit"
    WIDGET = "widget"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"
    ACCESSIBILITY = "accessibility"
    REGRESSION = "regression"
    SMOKE = "smoke"


class TestPriority(Enum):
    """Test priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class TestResult:
    """Result of a single test execution"""
    test_name: str
    category: TestCategory
    passed: bool
    message: str
    execution_time: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    error_details: Optional[str] = None
    expected_result: Any = None
    actual_result: Any = None
    assertions_count: int = 0
    priority: TestPriority = TestPriority.MEDIUM


@dataclass
class PerformanceTestResult:
    """Performance metrics for test execution"""
    test_name: str
    execution_time: float
    memory_usage: float
    cpu_usage: float
    render_time: Optional[float] = None
    initialization_time: Optional[float] = None
    response_time: Optional[float] = None
    throughput: Optional[float] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TestSuite:
    """Collection of test cases with metadata"""
    name: str
    description: str
    test_cases: List['ComponentTestCase'] = field(default_factory=list)
    category: TestCategory = TestCategory.UNIT
    priority: TestPriority = TestPriority.MEDIUM
    setup_function: Optional[Callable] = None
    teardown_function: Optional[Callable] = None
    tags: List[str] = field(default_factory=list)


class ComponentTestCase(ABC):
    """Base class for component test cases"""
    
    def __init__(self, name: str, description: str, 
                 category: TestCategory = TestCategory.UNIT,
                 priority: TestPriority = TestPriority.MEDIUM,
                 tags: Optional[List[str]] = None):
        self.name = name
        self.description = description
        self.category = category
        self.priority = priority
        self.tags = tags or []
        self.assertions_count = 0
        self.setup_complete = False
        self.teardown_complete = False
    
    def setup(self):
        """Setup method called before test execution"""
        self.setup_complete = True
    
    def teardown(self):
        """Teardown method called after test execution"""
        self.teardown_complete = True
    
    @abstractmethod
    def execute(self) -> TestResult:
        """Execute the test case and return result"""
        pass
    
    # Assertion helpers
    def assert_true(self, condition: bool, message: str = ""):
        """Assert that condition is true"""
        self.assertions_count += 1
        if not condition:
            raise AssertionError(f"Expected True, got False. {message}")
    
    def assert_false(self, condition: bool, message: str = ""):
        """Assert that condition is false"""
        self.assertions_count += 1
        if condition:
            raise AssertionError(f"Expected False, got True. {message}")
    
    def assert_equal(self, expected: Any, actual: Any, message: str = ""):
        """Assert that expected equals actual"""
        self.assertions_count += 1
        if expected != actual:
            raise AssertionError(f"Expected {expected}, got {actual}. {message}")
    
    def assert_not_equal(self, expected: Any, actual: Any, message: str = ""):
        """Assert that expected does not equal actual"""
        self.assertions_count += 1
        if expected == actual:
            raise AssertionError(f"Expected {expected} != {actual}. {message}")
    
    def assert_in(self, item: Any, container: Any, message: str = ""):
        """Assert that item is in container"""
        self.assertions_count += 1
        if item not in container:
            raise AssertionError(f"Expected {item} in {container}. {message}")
    
    def assert_not_in(self, item: Any, container: Any, message: str = ""):
        """Assert that item is not in container"""
        self.assertions_count += 1
        if item in container:
            raise AssertionError(f"Expected {item} not in {container}. {message}")
    
    def assert_is_none(self, value: Any, message: str = ""):
        """Assert that value is None"""
        self.assertions_count += 1
        if value is not None:
            raise AssertionError(f"Expected None, got {value}. {message}")
    
    def assert_is_not_none(self, value: Any, message: str = ""):
        """Assert that value is not None"""
        self.assertions_count += 1
        if value is None:
            raise AssertionError(f"Expected not None, got None. {message}")
    
    def assert_isinstance(self, obj: Any, expected_type: Type, message: str = ""):
        """Assert that object is instance of expected type"""
        self.assertions_count += 1
        if not isinstance(obj, expected_type):
            raise AssertionError(f"Expected {expected_type}, got {type(obj)}. {message}")
    
    def assert_raises(self, expected_exception: Type[Exception], callable_obj: Callable, *args, **kwargs):
        """Assert that callable raises expected exception"""
        self.assertions_count += 1
        try:
            callable_obj(*args, **kwargs)
            raise AssertionError(f"Expected {expected_exception.__name__} to be raised")
        except expected_exception:
            pass  # Expected behavior
        except Exception as e:
            raise AssertionError(f"Expected {expected_exception.__name__}, got {type(e).__name__}")


class ComponentTester:
    """
    Main component testing framework for executing and managing tests
    """
    
    def __init__(self):
        self._test_suites: Dict[str, TestSuite] = {}
        self._test_results: List[TestResult] = []
        self._performance_results: List[PerformanceTestResult] = []
        self._global_setup_functions: List[Callable] = []
        self._global_teardown_functions: List[Callable] = []
        
        # Test execution settings
        self.timeout_seconds = 30
        self.collect_performance_metrics = True
        self.verbose_output = True
        self.stop_on_failure = False
        
        # Application instance for widget testing
        self._app = None
        self._ensure_qapplication()
    
    def _ensure_qapplication(self):
        """Ensure QApplication exists for widget testing"""
        app = QApplication.instance()
        if app is None:
            self._app = QApplication([])
        else:
            self._app = app
    
    # =========================================================================
    # Test Suite Management
    # =========================================================================
    
    def add_test_suite(self, test_suite: TestSuite):
        """Add a test suite to the tester"""
        self._test_suites[test_suite.name] = test_suite
        
        if self.verbose_output:
            print(f"Added test suite: {test_suite.name} ({len(test_suite.test_cases)} tests)")
    
    def remove_test_suite(self, suite_name: str):
        """Remove a test suite"""
        if suite_name in self._test_suites:
            del self._test_suites[suite_name]
            
            if self.verbose_output:
                print(f"Removed test suite: {suite_name}")
    
    def add_test_case(self, suite_name: str, test_case: ComponentTestCase):
        """Add a test case to an existing suite"""
        if suite_name not in self._test_suites:
            # Create a new suite if it doesn't exist
            self._test_suites[suite_name] = TestSuite(
                name=suite_name,
                description=f"Auto-created suite for {suite_name}",
                category=test_case.category
            )
        
        self._test_suites[suite_name].test_cases.append(test_case)
        
        if self.verbose_output:
            print(f"Added test case '{test_case.name}' to suite '{suite_name}'")
    
    # =========================================================================
    # Global Setup/Teardown
    # =========================================================================
    
    def add_global_setup(self, setup_function: Callable):
        """Add a global setup function"""
        self._global_setup_functions.append(setup_function)
    
    def add_global_teardown(self, teardown_function: Callable):
        """Add a global teardown function"""
        self._global_teardown_functions.append(teardown_function)
    
    def _execute_global_setup(self):
        """Execute all global setup functions"""
        for setup_func in self._global_setup_functions:
            try:
                setup_func()
            except Exception as e:
                print(f"Global setup failed: {e}")
                raise
    
    def _execute_global_teardown(self):
        """Execute all global teardown functions"""
        for teardown_func in self._global_teardown_functions:
            try:
                teardown_func()
            except Exception as e:
                print(f"Global teardown failed: {e}")
    
    # =========================================================================
    # Test Execution
    # =========================================================================
    
    def run_test_case(self, test_case: ComponentTestCase) -> TestResult:
        """Execute a single test case"""
        start_time = time.time()
        
        try:
            # Setup
            test_case.setup()
            
            # Execute test
            result = test_case.execute()
            result.execution_time = time.time() - start_time
            result.assertions_count = test_case.assertions_count
            
            # Teardown
            test_case.teardown()
            
            if self.verbose_output:
                status = "PASS" if result.passed else "FAIL"
                print(f"  {status}: {result.test_name} ({result.execution_time:.3f}s)")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            result = TestResult(
                test_name=test_case.name,
                category=test_case.category,
                passed=False,
                message=str(e),
                execution_time=execution_time,
                error_details=traceback.format_exc(),
                assertions_count=test_case.assertions_count,
                priority=test_case.priority
            )
            
            if self.verbose_output:
                print(f"  FAIL: {test_case.name} ({execution_time:.3f}s) - {str(e)}")
            
            # Ensure teardown runs even on failure
            try:
                test_case.teardown()
            except:
                pass
            
            return result
    
    def run_test_suite(self, suite_name: str, 
                      category_filter: Optional[TestCategory] = None,
                      priority_filter: Optional[TestPriority] = None,
                      tag_filter: Optional[List[str]] = None) -> List[TestResult]:
        """Execute all tests in a suite with optional filtering"""
        if suite_name not in self._test_suites:
            raise ValueError(f"Test suite '{suite_name}' not found")
        
        suite = self._test_suites[suite_name]
        results = []
        
        if self.verbose_output:
            print(f"\n=== Running Test Suite: {suite.name} ===")
        
        # Execute suite setup
        if suite.setup_function:
            try:
                suite.setup_function()
            except Exception as e:
                print(f"Suite setup failed: {e}")
                return []
        
        # Filter test cases
        test_cases = self._filter_test_cases(
            suite.test_cases, category_filter, priority_filter, tag_filter
        )
        
        # Execute test cases
        for test_case in test_cases:
            result = self.run_test_case(test_case)
            results.append(result)
            self._test_results.append(result)
            
            # Stop on failure if configured
            if self.stop_on_failure and not result.passed:
                break
        
        # Execute suite teardown
        if suite.teardown_function:
            try:
                suite.teardown_function()
            except Exception as e:
                print(f"Suite teardown failed: {e}")
        
        # Print summary
        if self.verbose_output:
            passed = sum(1 for r in results if r.passed)
            total = len(results)
            print(f"Suite '{suite_name}' completed: {passed}/{total} tests passed")
        
        return results
    
    def run_all_tests(self, 
                     category_filter: Optional[TestCategory] = None,
                     priority_filter: Optional[TestPriority] = None,
                     tag_filter: Optional[List[str]] = None) -> Dict[str, List[TestResult]]:
        """Execute all test suites with optional filtering"""
        all_results = {}
        
        if self.verbose_output:
            print("=== Running All Test Suites ===")
        
        # Execute global setup
        self._execute_global_setup()
        
        try:
            for suite_name in self._test_suites:
                results = self.run_test_suite(
                    suite_name, category_filter, priority_filter, tag_filter
                )
                all_results[suite_name] = results
                
        finally:
            # Execute global teardown
            self._execute_global_teardown()
        
        # Print overall summary
        if self.verbose_output:
            self._print_overall_summary(all_results)
        
        return all_results
    
    def _filter_test_cases(self, test_cases: List[ComponentTestCase],
                          category_filter: Optional[TestCategory],
                          priority_filter: Optional[TestPriority],
                          tag_filter: Optional[List[str]]) -> List[ComponentTestCase]:
        """Filter test cases based on criteria"""
        filtered = test_cases
        
        if category_filter:
            filtered = [tc for tc in filtered if tc.category == category_filter]
        
        if priority_filter:
            filtered = [tc for tc in filtered if tc.priority == priority_filter]
        
        if tag_filter:
            filtered = [tc for tc in filtered 
                       if any(tag in tc.tags for tag in tag_filter)]
        
        return filtered
    
    def _print_overall_summary(self, results: Dict[str, List[TestResult]]):
        """Print overall test execution summary"""
        total_tests = sum(len(suite_results) for suite_results in results.values())
        total_passed = sum(
            sum(1 for r in suite_results if r.passed) 
            for suite_results in results.values()
        )
        total_failed = total_tests - total_passed
        
        print(f"\n=== Overall Test Summary ===")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {total_passed}")
        print(f"Failed: {total_failed}")
        print(f"Success Rate: {(total_passed/total_tests*100):.1f}%" if total_tests > 0 else "No tests")
        
        # Print failed tests
        if total_failed > 0:
            print(f"\n--- Failed Tests ---")
            for suite_name, suite_results in results.items():
                failed_tests = [r for r in suite_results if not r.passed]
                for result in failed_tests:
                    print(f"  {suite_name}.{result.test_name}: {result.message}")
    
    # =========================================================================
    # Performance Tracking
    # =========================================================================
    
    def add_performance_result(self, result: PerformanceTestResult):
        """Add a performance test result"""
        self._performance_results.append(result)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance testing summary"""
        if not self._performance_results:
            return {}
        
        execution_times = [r.execution_time for r in self._performance_results]
        memory_usage = [r.memory_usage for r in self._performance_results]
        
        return {
            'total_tests': len(self._performance_results),
            'avg_execution_time': sum(execution_times) / len(execution_times),
            'max_execution_time': max(execution_times),
            'min_execution_time': min(execution_times),
            'avg_memory_usage': sum(memory_usage) / len(memory_usage),
            'max_memory_usage': max(memory_usage),
            'slowest_tests': sorted(
                self._performance_results, 
                key=lambda x: x.execution_time, 
                reverse=True
            )[:5]
        }
    
    # =========================================================================
    # Results Management
    # =========================================================================
    
    def get_all_results(self) -> List[TestResult]:
        """Get all test results"""
        return self._test_results.copy()
    
    def get_results_by_category(self, category: TestCategory) -> List[TestResult]:
        """Get results filtered by category"""
        return [r for r in self._test_results if r.category == category]
    
    def get_failed_results(self) -> List[TestResult]:
        """Get all failed test results"""
        return [r for r in self._test_results if not r.passed]
    
    def clear_results(self):
        """Clear all test results"""
        self._test_results.clear()
        self._performance_results.clear()
    
    # =========================================================================
    # Reporting
    # =========================================================================
    
    def generate_report(self, format: str = "text") -> str:
        """Generate test report in specified format"""
        if format == "text":
            return self._generate_text_report()
        elif format == "json":
            return self._generate_json_report()
        else:
            raise ValueError(f"Unsupported report format: {format}")
    
    def _generate_text_report(self) -> str:
        """Generate text format report"""
        lines = []
        lines.append("Component Testing Report")
        lines.append("=" * 50)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Overall statistics
        total_tests = len(self._test_results)
        passed_tests = sum(1 for r in self._test_results if r.passed)
        failed_tests = total_tests - passed_tests
        
        lines.append("Overall Statistics:")
        lines.append(f"  Total Tests: {total_tests}")
        lines.append(f"  Passed: {passed_tests}")
        lines.append(f"  Failed: {failed_tests}")
        lines.append(f"  Success Rate: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "  Success Rate: N/A")
        lines.append("")
        
        # Category breakdown
        lines.append("Results by Category:")
        for category in TestCategory:
            category_results = self.get_results_by_category(category)
            if category_results:
                category_passed = sum(1 for r in category_results if r.passed)
                lines.append(f"  {category.value}: {category_passed}/{len(category_results)} passed")
        lines.append("")
        
        # Failed tests details
        failed_results = self.get_failed_results()
        if failed_results:
            lines.append("Failed Tests:")
            for result in failed_results:
                lines.append(f"  {result.test_name} ({result.category.value}):")
                lines.append(f"    Message: {result.message}")
                lines.append(f"    Execution Time: {result.execution_time:.3f}s")
                if result.error_details:
                    lines.append(f"    Error Details: {result.error_details}")
                lines.append("")
        
        # Performance summary
        perf_summary = self.get_performance_summary()
        if perf_summary:
            lines.append("Performance Summary:")
            lines.append(f"  Average Execution Time: {perf_summary['avg_execution_time']:.3f}s")
            lines.append(f"  Max Execution Time: {perf_summary['max_execution_time']:.3f}s")
            lines.append(f"  Average Memory Usage: {perf_summary['avg_memory_usage']:.2f}MB")
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_json_report(self) -> str:
        """Generate JSON format report"""
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_tests': len(self._test_results),
                'passed_tests': sum(1 for r in self._test_results if r.passed),
                'failed_tests': sum(1 for r in self._test_results if not r.passed),
                'success_rate': (sum(1 for r in self._test_results if r.passed) / len(self._test_results) * 100) if self._test_results else 0
            },
            'results_by_category': {},
            'test_results': [],
            'performance_summary': self.get_performance_summary()
        }
        
        # Category breakdown
        for category in TestCategory:
            category_results = self.get_results_by_category(category)
            if category_results:
                report_data['results_by_category'][category.value] = {
                    'total': len(category_results),
                    'passed': sum(1 for r in category_results if r.passed),
                    'failed': sum(1 for r in category_results if not r.passed)
                }
        
        # Individual test results
        for result in self._test_results:
            report_data['test_results'].append({
                'test_name': result.test_name,
                'category': result.category.value,
                'priority': result.priority.value,
                'passed': result.passed,
                'message': result.message,
                'execution_time': result.execution_time,
                'timestamp': result.timestamp,
                'assertions_count': result.assertions_count,
                'error_details': result.error_details
            })
        
        return json.dumps(report_data, indent=2, ensure_ascii=False)


# =============================================================================
# Convenience Functions
# =============================================================================

def create_simple_test_case(name: str, test_function: Callable, 
                           description: str = "",
                           category: TestCategory = TestCategory.UNIT) -> ComponentTestCase:
    """Create a simple test case from a function"""
    
    class SimpleTestCase(ComponentTestCase):
        def execute(self) -> TestResult:
            try:
                test_function()
                return TestResult(
                    test_name=self.name,
                    category=self.category,
                    passed=True,
                    message="Test passed",
                    execution_time=0.0,  # Will be set by runner
                    priority=self.priority
                )
            except Exception as e:
                return TestResult(
                    test_name=self.name,
                    category=self.category,
                    passed=False,
                    message=str(e),
                    execution_time=0.0,  # Will be set by runner
                    error_details=traceback.format_exc(),
                    priority=self.priority
                )
    
    return SimpleTestCase(name, description or f"Test: {name}", category)


def run_quick_test(test_function: Callable, test_name: str = "Quick Test") -> TestResult:
    """Run a quick test without full framework setup"""
    tester = ComponentTester()
    tester.verbose_output = False
    
    test_case = create_simple_test_case(test_name, test_function)
    return tester.run_test_case(test_case) 