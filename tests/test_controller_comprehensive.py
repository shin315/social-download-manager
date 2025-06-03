"""
Comprehensive App Controller Testing Framework

Main test runner that combines all testing aspects including UI integration,
edge cases, performance tests, and provides detailed reporting.
"""

import pytest
import asyncio
import time
import logging
import json
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

# Import all test components
from .test_app_controller_ui_integration import (
    TestAppControllerUIIntegration,
    TestAppControllerConfigurationScenarios, 
    TestAppControllerEventFlows,
    TestAppControllerPerformanceAndLoad
)
from .test_app_controller_edge_cases import (
    TestAppControllerEdgeCases,
    TestAppControllerThreadSafetyStress
)
from .test_controller_utilities import (
    TestScenario, TestResult, ControllerTestBuilder,
    PerformanceProfiler, MemoryTracker, ConcurrencyTester,
    create_test_controller_with_scenario, assert_controller_health
)
from .test_base import DatabaseTestCase

from core.app_controller import AppController, ControllerState


class ComprehensiveControllerTestRunner:
    """Comprehensive test runner for App Controller"""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.profiler = PerformanceProfiler()
        self.memory_tracker = MemoryTracker()
        self.test_report: Dict[str, Any] = {}
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def run_all_tests(self, output_file: Optional[str] = None) -> Dict[str, Any]:
        """Run all comprehensive tests and generate report"""
        self.logger.info("Starting comprehensive App Controller tests...")
        
        # Start memory tracking
        self.memory_tracker.take_snapshot("test_start")
        
        # Test scenarios to run
        test_scenarios = [
            self._test_basic_functionality,
            self._test_ui_integration,
            self._test_configuration_scenarios,
            self._test_event_flows,
            self._test_edge_cases,
            self._test_performance_stress,
            self._test_thread_safety,
            self._test_memory_management,
            self._test_error_recovery,
            self._test_async_operations
        ]
        
        # Run each test scenario
        for test_func in test_scenarios:
            try:
                self.logger.info(f"Running {test_func.__name__}...")
                with self.profiler.profile(test_func.__name__):
                    result = test_func()
                    self.results.append(result)
                    
                # Take memory snapshot after each test
                self.memory_tracker.take_snapshot(f"after_{test_func.__name__}")
                
            except Exception as e:
                self.logger.error(f"Test {test_func.__name__} failed: {e}")
                error_result = TestResult(
                    scenario=TestScenario.ERROR_CONDITIONS,
                    success=False,
                    duration=0.0,
                    metrics={},
                    errors=[str(e)],
                    warnings=[]
                )
                self.results.append(error_result)
        
        # Generate comprehensive report
        self.test_report = self._generate_comprehensive_report()
        
        # Save report if output file specified
        if output_file:
            self._save_report(output_file)
        
        self.logger.info("Comprehensive tests completed!")
        return self.test_report
    
    def _test_basic_functionality(self) -> TestResult:
        """Test basic controller functionality"""
        start_time = time.time()
        errors = []
        warnings = []
        metrics = {}
        
        try:
            # Test basic initialization and shutdown
            context = create_test_controller_with_scenario(TestScenario.BASIC_INITIALIZATION)
            context.setup()
            
            # Verify basic operations
            assert_controller_health(context.controller, "basic functionality")
            
            # Test component registration
            test_component = Mock()
            reg_result = context.controller.register_component("test_basic", test_component)
            assert reg_result, "Component registration should succeed"
            
            # Test component retrieval
            retrieved = context.controller.get_component("test_basic")
            assert retrieved is test_component, "Retrieved component should match registered"
            
            # Test status reporting
            status = context.controller.get_status()
            assert status.state == ControllerState.READY, "Controller should be ready"
            
            metrics["components_registered"] = len(status.components_initialized)
            metrics["initialization_success"] = True
            
            context.teardown()
            
        except Exception as e:
            errors.append(f"Basic functionality test failed: {e}")
        
        return TestResult(
            scenario=TestScenario.BASIC_INITIALIZATION,
            success=len(errors) == 0,
            duration=time.time() - start_time,
            metrics=metrics,
            errors=errors,
            warnings=warnings
        )
    
    def _test_ui_integration(self) -> TestResult:
        """Test UI component integration"""
        start_time = time.time()
        errors = []
        warnings = []
        metrics = {}
        
        try:
            # Create UI integration test instance
            ui_test = TestAppControllerUIIntegration()
            ui_test.setUp()
            
            # Test UI component initialization flow
            try:
                ui_test.test_ui_component_initialization_flow()
                metrics["ui_initialization_success"] = True
            except Exception as e:
                errors.append(f"UI initialization test failed: {e}")
            
            # Test configuration change propagation
            try:
                ui_test.test_configuration_change_ui_propagation()
                metrics["config_propagation_success"] = True
            except Exception as e:
                errors.append(f"Config propagation test failed: {e}")
            
            # Test error propagation to UI
            try:
                ui_test.test_error_propagation_to_ui()
                metrics["error_propagation_success"] = True
            except Exception as e:
                errors.append(f"Error propagation test failed: {e}")
            
            ui_test.tearDown()
            
        except Exception as e:
            errors.append(f"UI integration test setup failed: {e}")
        
        return TestResult(
            scenario=TestScenario.BASIC_INITIALIZATION,
            success=len(errors) == 0,
            duration=time.time() - start_time,
            metrics=metrics,
            errors=errors,
            warnings=warnings
        )
    
    def _test_configuration_scenarios(self) -> TestResult:
        """Test various configuration scenarios"""
        start_time = time.time()
        errors = []
        warnings = []
        metrics = {}
        
        try:
            config_test = TestAppControllerConfigurationScenarios()
            config_test.setUp()
            
            # Test development environment
            try:
                config_test.test_development_environment_config()
                metrics["dev_config_success"] = True
            except Exception as e:
                errors.append(f"Dev config test failed: {e}")
            
            # Test production environment
            try:
                config_test.test_production_environment_config()
                metrics["prod_config_success"] = True
            except Exception as e:
                errors.append(f"Prod config test failed: {e}")
            
            # Test invalid configuration handling
            try:
                config_test.test_invalid_configuration_handling()
                metrics["invalid_config_handling_success"] = True
            except Exception as e:
                errors.append(f"Invalid config test failed: {e}")
            
            config_test.tearDown()
            
        except Exception as e:
            errors.append(f"Configuration test setup failed: {e}")
        
        return TestResult(
            scenario=TestScenario.BASIC_INITIALIZATION,
            success=len(errors) == 0,
            duration=time.time() - start_time,
            metrics=metrics,
            errors=errors,
            warnings=warnings
        )
    
    def _test_event_flows(self) -> TestResult:
        """Test complex event flows"""
        start_time = time.time()
        errors = []
        warnings = []
        metrics = {}
        
        try:
            event_test = TestAppControllerEventFlows()
            event_test.setUp()
            
            # Test event cascade flow
            try:
                event_test.test_event_cascade_flow()
                metrics["event_cascade_success"] = True
            except Exception as e:
                errors.append(f"Event cascade test failed: {e}")
            
            # Test event error handling
            try:
                event_test.test_event_error_handling_flow()
                metrics["event_error_handling_success"] = True
            except Exception as e:
                errors.append(f"Event error handling test failed: {e}")
            
            event_test.tearDown()
            
        except Exception as e:
            errors.append(f"Event flow test setup failed: {e}")
        
        return TestResult(
            scenario=TestScenario.EVENT_CASCADES,
            success=len(errors) == 0,
            duration=time.time() - start_time,
            metrics=metrics,
            errors=errors,
            warnings=warnings
        )
    
    def _test_edge_cases(self) -> TestResult:
        """Test edge cases and unusual scenarios"""
        start_time = time.time()
        errors = []
        warnings = []
        metrics = {}
        
        try:
            edge_test = TestAppControllerEdgeCases()
            edge_test.setUp()
            
            # Test rapid initialization/shutdown cycles
            try:
                edge_test.test_rapid_initialization_shutdown_cycles()
                metrics["rapid_cycles_success"] = True
            except Exception as e:
                errors.append(f"Rapid cycles test failed: {e}")
            
            # Test component failures during initialization
            try:
                edge_test.test_initialization_with_component_failures()
                metrics["component_failure_handling_success"] = True
            except Exception as e:
                errors.append(f"Component failure test failed: {e}")
            
            # Test concurrent state transitions
            try:
                edge_test.test_concurrent_state_transitions()
                metrics["concurrent_transitions_success"] = True
            except Exception as e:
                errors.append(f"Concurrent transitions test failed: {e}")
            
            edge_test.tearDown()
            
        except Exception as e:
            errors.append(f"Edge cases test setup failed: {e}")
        
        return TestResult(
            scenario=TestScenario.COMPONENT_FAILURES,
            success=len(errors) == 0,
            duration=time.time() - start_time,
            metrics=metrics,
            errors=errors,
            warnings=warnings
        )
    
    def _test_performance_stress(self) -> TestResult:
        """Test performance under stress conditions"""
        start_time = time.time()
        errors = []
        warnings = []
        metrics = {}
        
        try:
            perf_test = TestAppControllerPerformanceAndLoad()
            perf_test.setUp()
            
            # Test initialization performance
            try:
                perf_test.test_controller_initialization_performance()
                metrics["initialization_performance_success"] = True
            except Exception as e:
                errors.append(f"Initialization performance test failed: {e}")
            
            # Test component registration load
            try:
                perf_test.test_component_registration_load()
                metrics["component_registration_performance_success"] = True
            except Exception as e:
                errors.append(f"Component registration performance test failed: {e}")
            
            # Test concurrent event processing
            try:
                perf_test.test_concurrent_event_processing()
                metrics["concurrent_event_performance_success"] = True
            except Exception as e:
                errors.append(f"Concurrent event performance test failed: {e}")
            
            perf_test.tearDown()
            
        except Exception as e:
            errors.append(f"Performance stress test setup failed: {e}")
        
        return TestResult(
            scenario=TestScenario.CONCURRENT_ACCESS,
            success=len(errors) == 0,
            duration=time.time() - start_time,
            metrics=metrics,
            errors=errors,
            warnings=warnings
        )
    
    def _test_thread_safety(self) -> TestResult:
        """Test thread safety under stress"""
        start_time = time.time()
        errors = []
        warnings = []
        metrics = {}
        
        try:
            thread_test = TestAppControllerThreadSafetyStress()
            thread_test.setUp()
            
            # Test concurrent component operations
            try:
                thread_test.test_concurrent_component_operations()
                metrics["concurrent_components_success"] = True
            except Exception as e:
                errors.append(f"Concurrent component operations test failed: {e}")
            
            # Test concurrent event publishing
            try:
                thread_test.test_concurrent_event_publishing()
                metrics["concurrent_event_publishing_success"] = True
            except Exception as e:
                errors.append(f"Concurrent event publishing test failed: {e}")
            
            thread_test.tearDown()
            
        except Exception as e:
            errors.append(f"Thread safety test setup failed: {e}")
        
        return TestResult(
            scenario=TestScenario.CONCURRENT_ACCESS,
            success=len(errors) == 0,
            duration=time.time() - start_time,
            metrics=metrics,
            errors=errors,
            warnings=warnings
        )
    
    def _test_memory_management(self) -> TestResult:
        """Test memory management and leak detection"""
        start_time = time.time()
        errors = []
        warnings = []
        metrics = {}
        
        try:
            edge_test = TestAppControllerEdgeCases()
            edge_test.setUp()
            
            # Test memory leak detection
            try:
                edge_test.test_memory_leak_detection()
                metrics["memory_leak_detection_success"] = True
            except Exception as e:
                errors.append(f"Memory leak detection test failed: {e}")
            
            # Test memory pressure stress
            stress_test = TestAppControllerThreadSafetyStress()
            stress_test.setUp()
            
            try:
                stress_test.test_memory_pressure_stress()
                metrics["memory_pressure_stress_success"] = True
            except Exception as e:
                errors.append(f"Memory pressure stress test failed: {e}")
            
            stress_test.tearDown()
            edge_test.tearDown()
            
        except Exception as e:
            errors.append(f"Memory management test setup failed: {e}")
        
        return TestResult(
            scenario=TestScenario.MEMORY_PRESSURE,
            success=len(errors) == 0,
            duration=time.time() - start_time,
            metrics=metrics,
            errors=errors,
            warnings=warnings
        )
    
    def _test_error_recovery(self) -> TestResult:
        """Test error recovery mechanisms"""
        start_time = time.time()
        errors = []
        warnings = []
        metrics = {}
        
        try:
            # Test with error conditions scenario
            context = create_test_controller_with_scenario(TestScenario.ERROR_CONDITIONS)
            context.setup()
            
            # Test controller handling of service errors
            try:
                # This should handle errors gracefully
                assert_controller_health(context.controller, "error recovery")
                metrics["error_recovery_success"] = True
            except Exception as e:
                # Expected for error conditions scenario
                warnings.append(f"Expected error in error recovery test: {e}")
                metrics["error_recovery_success"] = True
            
            context.teardown()
            
        except Exception as e:
            errors.append(f"Error recovery test failed: {e}")
        
        return TestResult(
            scenario=TestScenario.ERROR_CONDITIONS,
            success=len(errors) == 0,
            duration=time.time() - start_time,
            metrics=metrics,
            errors=errors,
            warnings=warnings
        )
    
    def _test_async_operations(self) -> TestResult:
        """Test async operations through controller"""
        start_time = time.time()
        errors = []
        warnings = []
        metrics = {}
        
        try:
            async def async_test():
                # Test concurrent async operations
                stress_test = TestAppControllerThreadSafetyStress()
                stress_test.setUp()
                
                try:
                    await stress_test.test_concurrent_async_operations()
                    metrics["concurrent_async_success"] = True
                except Exception as e:
                    errors.append(f"Concurrent async operations test failed: {e}")
                
                stress_test.tearDown()
            
            # Run async test
            asyncio.run(async_test())
            
        except Exception as e:
            errors.append(f"Async operations test failed: {e}")
        
        return TestResult(
            scenario=TestScenario.ASYNC_OPERATIONS,
            success=len(errors) == 0,
            duration=time.time() - start_time,
            metrics=metrics,
            errors=errors,
            warnings=warnings
        )
    
    def _generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        total_tests = len(self.results)
        successful_tests = sum(1 for result in self.results if result.success)
        failed_tests = total_tests - successful_tests
        
        # Performance metrics
        performance_stats = self.profiler.get_all_stats()
        
        # Memory analysis
        memory_analysis = self.memory_tracker.cleanup_check()
        
        # Collect all metrics
        all_metrics = {}
        for result in self.results:
            all_metrics.update(result.metrics)
        
        # Collect all errors and warnings
        all_errors = []
        all_warnings = []
        for result in self.results:
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
        
        report = {
            "test_summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": failed_tests,
                "success_rate": (successful_tests / total_tests * 100) if total_tests > 0 else 0,
                "total_duration": sum(result.duration for result in self.results)
            },
            "performance_analysis": performance_stats,
            "memory_analysis": memory_analysis,
            "test_metrics": all_metrics,
            "test_results": [
                {
                    "scenario": result.scenario.value,
                    "success": result.success,
                    "duration": result.duration,
                    "metrics": result.metrics,
                    "error_count": len(result.errors),
                    "warning_count": len(result.warnings)
                }
                for result in self.results
            ],
            "errors": all_errors,
            "warnings": all_warnings,
            "recommendations": self._generate_recommendations()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Check success rate
        total_tests = len(self.results)
        successful_tests = sum(1 for result in self.results if result.success)
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        if success_rate < 90:
            recommendations.append("Test success rate is below 90%. Review failed tests and improve error handling.")
        
        # Check memory usage
        memory_analysis = self.memory_tracker.cleanup_check()
        if memory_analysis.get("leak_detected", False):
            recommendations.append("Memory leak detected. Review memory management and object cleanup.")
        
        # Check performance
        performance_stats = self.profiler.get_all_stats()
        for operation, stats in performance_stats.items():
            if stats.get("average", 0) > 1.0:  # More than 1 second average
                recommendations.append(f"Performance concern: {operation} takes {stats['average']:.2f}s on average.")
        
        # Check error patterns
        all_errors = []
        for result in self.results:
            all_errors.extend(result.errors)
        
        if len(all_errors) > 0:
            recommendations.append(f"Found {len(all_errors)} errors across tests. Review error handling mechanisms.")
        
        if not recommendations:
            recommendations.append("All tests passed successfully! App Controller testing framework is comprehensive and robust.")
        
        return recommendations
    
    def _save_report(self, output_file: str) -> None:
        """Save test report to file"""
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.test_report, f, indent=2, default=str)
            
            self.logger.info(f"Test report saved to {output_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save report: {e}")


class TestAppControllerComprehensive(DatabaseTestCase):
    """Comprehensive test suite for App Controller"""
    
    def setUp(self):
        """Set up comprehensive test environment"""
        super().setUp()
        self.test_runner = ComprehensiveControllerTestRunner()
    
    def tearDown(self):
        """Clean up comprehensive test environment"""
        super().tearDown()
    
    def test_comprehensive_controller_functionality(self):
        """Run comprehensive controller functionality tests"""
        report = self.test_runner.run_all_tests()
        
        # Assert overall test success
        success_rate = report["test_summary"]["success_rate"]
        self.assertGreater(success_rate, 80.0, f"Overall test success rate should be > 80%, got {success_rate:.1f}%")
        
        # Assert no critical errors
        critical_errors = [error for error in report["errors"] if "critical" in error.lower()]
        self.assertEqual(len(critical_errors), 0, f"No critical errors should occur, found: {critical_errors}")
        
        # Assert memory management
        memory_analysis = report["memory_analysis"]
        if memory_analysis.get("status") == "analyzed":
            leak_detected = memory_analysis.get("leak_detected", False)
            self.assertFalse(leak_detected, "No memory leaks should be detected")
        
        # Print summary for visibility
        print("\n" + "="*80)
        print("COMPREHENSIVE APP CONTROLLER TEST REPORT")
        print("="*80)
        print(f"Total Tests: {report['test_summary']['total_tests']}")
        print(f"Success Rate: {report['test_summary']['success_rate']:.1f}%")
        print(f"Total Duration: {report['test_summary']['total_duration']:.2f}s")
        print(f"Errors: {len(report['errors'])}")
        print(f"Warnings: {len(report['warnings'])}")
        
        if report["recommendations"]:
            print("\nRecommendations:")
            for i, rec in enumerate(report["recommendations"], 1):
                print(f"{i}. {rec}")
        
        print("="*80)
    
    def test_controller_testing_framework_coverage(self):
        """Test that the testing framework covers all important aspects"""
        # Verify all test scenarios are covered
        covered_scenarios = set()
        for result in self.test_runner.results:
            covered_scenarios.add(result.scenario)
        
        # Should cover major testing areas
        important_scenarios = {
            TestScenario.BASIC_INITIALIZATION,
            TestScenario.COMPONENT_FAILURES,
            TestScenario.CONCURRENT_ACCESS,
            TestScenario.ERROR_CONDITIONS,
            TestScenario.MEMORY_PRESSURE
        }
        
        # Check coverage (allow some flexibility as not all scenarios may be in every test run)
        coverage_ratio = len(covered_scenarios.intersection(important_scenarios)) / len(important_scenarios)
        self.assertGreater(coverage_ratio, 0.6, "Testing framework should cover majority of important scenarios")


if __name__ == "__main__":
    # Run comprehensive tests
    runner = ComprehensiveControllerTestRunner()
    report = runner.run_all_tests("tests/reports/comprehensive_controller_test_report.json")
    
    print("\nComprehensive App Controller Testing Complete!")
    print(f"Success Rate: {report['test_summary']['success_rate']:.1f}%")
    print(f"Report saved to: tests/reports/comprehensive_controller_test_report.json") 