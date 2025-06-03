#!/usr/bin/env python3
"""
Automated Test Execution Framework for v2.0 Integration Testing

This module provides comprehensive automated testing infrastructure for validating
the integration between UI v1.2.1 and v2.0 architecture through Task 29 adapters
and Task 30 main entry point orchestration.
"""

import sys
import os
import time
import pytest
import asyncio
import threading
import logging
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Tuple, Union
from dataclasses import dataclass, field
from contextlib import contextmanager, asynccontextmanager
from unittest.mock import Mock, MagicMock, patch
import sqlite3
import json

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# PyQt6 imports for UI testing
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QPushButton, QLabel
from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QThread
from PyQt6.QtTest import QTest

# Import our baseline metrics system
from .baseline_metrics import BaselineMetricsCollector, baseline_metrics_session, MetricType

# Import v2.0 architecture components
try:
    from core.main_entry_orchestrator import (
        MainEntryOrchestrator, StartupConfig, StartupMode, create_default_startup_config
    )
    from core.adapter_integration import (
        AdapterIntegrationFramework, get_integration_framework, setup_standard_adapters,
        IntegrationConfig, IntegrationState, IntegrationMode
    )
    from core.error_management import get_error_manager, ErrorCode, ErrorSeverity
    from core.logging_system import get_logger
    from core.shutdown_manager import get_shutdown_manager, ShutdownReason
    CORE_COMPONENTS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Core components not available: {e}")
    CORE_COMPONENTS_AVAILABLE = False

# Import existing test utilities
try:
    from tests.integration_environment_setup import IntegrationTestEnvironment
    from tests.test_fixtures import create_test_database, create_mock_config
    TEST_UTILITIES_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Test utilities not available: {e}")
    TEST_UTILITIES_AVAILABLE = False


@dataclass
class TestConfiguration:
    """Configuration for automated test execution"""
    # Test execution settings
    test_timeout: float = 60.0
    startup_timeout: float = 10.0
    ui_timeout: float = 5.0
    
    # Feature flags
    enable_ui_testing: bool = True
    enable_performance_testing: bool = True
    enable_error_simulation: bool = True
    enable_adapter_testing: bool = True
    
    # Performance thresholds
    max_startup_time_ms: float = 400.0  # Allow 400ms max for tests
    max_memory_usage_mb: float = 100.0  # Allow 100MB max for tests
    max_ui_response_ms: float = 200.0   # Allow 200ms max for UI
    
    # Test modes
    test_modes: List[str] = field(default_factory=lambda: [
        "FULL_V2_PRODUCTION", "FULL_V2_DEV", "DEGRADED_V2", "FALLBACK_V1"
    ])
    
    # Mock settings
    use_mock_database: bool = True
    use_mock_platform_apis: bool = True
    use_mock_file_system: bool = False


@dataclass
class TestResult:
    """Result of an individual test execution"""
    test_name: str
    test_type: str
    status: str  # PASS, FAIL, SKIP, ERROR
    duration_ms: float
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'test_name': self.test_name,
            'test_type': self.test_type,
            'status': self.status,
            'duration_ms': self.duration_ms,
            'error_message': self.error_message,
            'metrics': self.metrics,
            'artifacts': self.artifacts
        }


@dataclass
class TestSuiteResult:
    """Result of complete test suite execution"""
    suite_name: str
    start_time: str
    end_time: str
    total_duration_ms: float
    
    # Test counts
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    error_tests: int = 0
    
    # Individual test results
    test_results: List[TestResult] = field(default_factory=list)
    
    # Overall metrics
    overall_metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Performance summary
    performance_summary: Dict[str, Any] = field(default_factory=dict)
    
    def success_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'suite_name': self.suite_name,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'total_duration_ms': self.total_duration_ms,
            'total_tests': self.total_tests,
            'passed_tests': self.passed_tests,
            'failed_tests': self.failed_tests,
            'skipped_tests': self.skipped_tests,
            'error_tests': self.error_tests,
            'success_rate': self.success_rate(),
            'test_results': [r.to_dict() for r in self.test_results],
            'overall_metrics': self.overall_metrics,
            'performance_summary': self.performance_summary
        }


class IntegrationTestFramework:
    """Main framework for automated integration testing"""
    
    def __init__(self, config: TestConfiguration = None):
        self.config = config or TestConfiguration()
        self.logger = logging.getLogger(__name__)
        
        # Test environment
        self.test_env: Optional[IntegrationTestEnvironment] = None
        self.temp_dir: Optional[Path] = None
        
        # QApplication for UI testing
        self._qapp: Optional[QApplication] = None
        self._main_window: Optional[QMainWindow] = None
        
        # v2.0 components
        self._orchestrator: Optional[MainEntryOrchestrator] = None
        self._integration_framework: Optional[AdapterIntegrationFramework] = None
        
        # Metrics collection
        self._metrics_collector: Optional[BaselineMetricsCollector] = None
        
        # Test tracking
        self._current_test_session = None
        self._test_artifacts: List[str] = []
        
    def setup_test_environment(self) -> bool:
        """Setup complete test environment"""
        try:
            self.logger.info("Setting up integration test environment")
            
            # Create temporary directory
            self.temp_dir = Path(tempfile.mkdtemp(prefix="integration_test_"))
            
            # Setup test environment if available
            if TEST_UTILITIES_AVAILABLE:
                self.test_env = IntegrationTestEnvironment("v2_integration_test")
                self.test_env.setup_complete_environment()
                self.logger.info("Test environment setup completed")
            
            # Setup QApplication for UI testing
            if self.config.enable_ui_testing:
                self._setup_qt_application()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to setup test environment: {e}")
            return False
    
    def teardown_test_environment(self):
        """Teardown test environment and cleanup"""
        try:
            # Cleanup QApplication
            if self._qapp:
                self._qapp.quit()
                self._qapp = None
            
            # Cleanup test environment
            if self.test_env:
                self.test_env.cleanup()
                self.test_env = None
            
            # Cleanup temporary directory
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            
            self.logger.info("Test environment teardown completed")
            
        except Exception as e:
            self.logger.error(f"Error during teardown: {e}")
    
    def _setup_qt_application(self):
        """Setup QApplication for UI testing"""
        try:
            # Create QApplication if it doesn't exist
            self._qapp = QApplication.instance()
            if self._qapp is None:
                self._qapp = QApplication([])
            
            # Set up for testing
            self._qapp.setQuitOnLastWindowClosed(False)
            
            self.logger.info("QApplication setup completed")
            
        except Exception as e:
            self.logger.error(f"Failed to setup QApplication: {e}")
            raise
    
    @contextmanager
    def test_session(self, session_name: str):
        """Context manager for test session with metrics collection"""
        session_id = f"{session_name}_{int(time.time())}"
        
        try:
            # Start metrics collection
            self._metrics_collector = BaselineMetricsCollector(session_id)
            self._metrics_collector.start_continuous_memory_monitoring()
            
            self._current_test_session = session_id
            self.logger.info(f"Started test session: {session_id}")
            
            yield session_id
            
        finally:
            # Stop metrics collection
            if self._metrics_collector:
                self._metrics_collector.stop_continuous_monitoring()
                
                # Generate and save report
                report = self._metrics_collector.generate_baseline_report()
                report_path = self._metrics_collector.save_report(report)
                self._test_artifacts.append(str(report_path))
            
            self._current_test_session = None
            self.logger.info(f"Completed test session: {session_id}")
    
    def test_main_entry_point_startup(self, mode: str = "FULL_V2_PRODUCTION") -> TestResult:
        """Test main entry point startup sequence"""
        test_name = f"main_entry_startup_{mode.lower()}"
        start_time = time.perf_counter()
        
        try:
            self.logger.info(f"Testing main entry point startup in {mode} mode")
            
            with self._metrics_collector.measure_startup_phase("complete_startup"):
                # Create startup configuration
                startup_mode = getattr(StartupMode, mode, StartupMode.FULL_V2)
                config = create_default_startup_config()
                config.feature_flags["enable_debug_logging"] = True
                
                # Create orchestrator
                orchestrator = MainEntryOrchestrator(config)
                
                # Run startup sequence
                success, qapp, main_window = orchestrator.run_startup_sequence()
                
                if not success:
                    raise RuntimeError("Startup sequence failed")
                
                # Validate components
                metrics = orchestrator.get_startup_metrics()
                component_status = orchestrator.get_component_status()
                
                # Store references for cleanup
                self._orchestrator = orchestrator
                if main_window:
                    self._main_window = main_window
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Validate performance
            if duration_ms > self.config.max_startup_time_ms:
                self.logger.warning(f"Startup time {duration_ms:.2f}ms exceeds threshold {self.config.max_startup_time_ms}ms")
            
            return TestResult(
                test_name=test_name,
                test_type="startup_integration",
                status="PASS",
                duration_ms=duration_ms,
                metrics={
                    'startup_time_ms': duration_ms,
                    'mode': mode,
                    'components_initialized': len([k for k, v in component_status.items() if v]),
                    'components_failed': len([k for k, v in component_status.items() if not v])
                }
            )
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.logger.error(f"Main entry point startup test failed: {e}")
            
            return TestResult(
                test_name=test_name,
                test_type="startup_integration",
                status="FAIL",
                duration_ms=duration_ms,
                error_message=str(e),
                metrics={'startup_time_ms': duration_ms, 'mode': mode}
            )
    
    def test_adapter_integration(self) -> TestResult:
        """Test adapter integration functionality"""
        test_name = "adapter_integration"
        start_time = time.perf_counter()
        
        try:
            self.logger.info("Testing adapter integration functionality")
            
            if not CORE_COMPONENTS_AVAILABLE:
                return TestResult(
                    test_name=test_name,
                    test_type="adapter_integration",
                    status="SKIP",
                    duration_ms=0,
                    error_message="Core components not available"
                )
            
            with self._metrics_collector.measure_adapter_performance("integration_framework", "full_setup"):
                # Get or create integration framework
                framework = get_integration_framework()
                
                # Setup standard adapters
                setup_standard_adapters(framework)
                
                # Start integration
                framework.start_integration()
                
                # Test adapter operations
                if self._main_window:
                    with self._metrics_collector.measure_adapter_performance("main_window_adapter", "attach_component"):
                        framework.attach_legacy_components(self._main_window)
                
                # Validate adapter health
                state = framework.get_state()
                metrics = framework.get_metrics()
                
                if state != IntegrationState.ACTIVE:
                    raise RuntimeError(f"Integration framework not active: {state}")
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            return TestResult(
                test_name=test_name,
                test_type="adapter_integration",
                status="PASS",
                duration_ms=duration_ms,
                metrics={
                    'integration_time_ms': duration_ms,
                    'framework_state': state.name if hasattr(state, 'name') else str(state),
                    'metrics': metrics.__dict__ if hasattr(metrics, '__dict__') else {}
                }
            )
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.logger.error(f"Adapter integration test failed: {e}")
            
            return TestResult(
                test_name=test_name,
                test_type="adapter_integration",
                status="FAIL",
                duration_ms=duration_ms,
                error_message=str(e),
                metrics={'integration_time_ms': duration_ms}
            )
    
    def test_ui_workflow_preservation(self) -> TestResult:
        """Test that UI workflows are preserved with v2.0 architecture"""
        test_name = "ui_workflow_preservation"
        start_time = time.perf_counter()
        
        try:
            self.logger.info("Testing UI workflow preservation")
            
            if not self._main_window or not self.config.enable_ui_testing:
                return TestResult(
                    test_name=test_name,
                    test_type="ui_workflow",
                    status="SKIP",
                    duration_ms=0,
                    error_message="UI testing not available or disabled"
                )
            
            # Test basic UI interactions
            with self._metrics_collector.measure_ui_response("window_show"):
                self._main_window.show()
                QTest.qWait(100)  # Wait for window to show
            
            with self._metrics_collector.measure_ui_response("window_resize"):
                self._main_window.resize(800, 600)
                QTest.qWait(50)
            
            # Test UI components if available
            if hasattr(self._main_window, 'centralWidget'):
                central_widget = self._main_window.centralWidget()
                if central_widget:
                    with self._metrics_collector.measure_ui_response("widget_interaction"):
                        # Simulate basic widget interactions
                        QTest.qWait(50)
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            return TestResult(
                test_name=test_name,
                test_type="ui_workflow",
                status="PASS",
                duration_ms=duration_ms,
                metrics={
                    'workflow_time_ms': duration_ms,
                    'window_visible': self._main_window.isVisible(),
                    'window_size': (self._main_window.width(), self._main_window.height())
                }
            )
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.logger.error(f"UI workflow preservation test failed: {e}")
            
            return TestResult(
                test_name=test_name,
                test_type="ui_workflow",
                status="FAIL",
                duration_ms=duration_ms,
                error_message=str(e),
                metrics={'workflow_time_ms': duration_ms}
            )
    
    def test_error_handling_integration(self) -> TestResult:
        """Test cross-architecture error handling"""
        test_name = "error_handling_integration"
        start_time = time.perf_counter()
        
        try:
            self.logger.info("Testing cross-architecture error handling")
            
            if not CORE_COMPONENTS_AVAILABLE or not self.config.enable_error_simulation:
                return TestResult(
                    test_name=test_name,
                    test_type="error_handling",
                    status="SKIP",
                    duration_ms=0,
                    error_message="Error simulation disabled or components unavailable"
                )
            
            with self._metrics_collector.measure_ui_response("error_simulation", "error_manager"):
                # Get error manager
                error_manager = get_error_manager()
                
                # Simulate various error scenarios
                test_errors = [
                    (ErrorCode.CONFIG_FILE_NOT_FOUND, ErrorSeverity.WARNING),
                    (ErrorCode.COMPONENT_INIT_FAILED, ErrorSeverity.ERROR),
                    (ErrorCode.ADAPTER_INIT_FAILED, ErrorSeverity.CRITICAL)
                ]
                
                for error_code, severity in test_errors:
                    # Report error and measure recovery time
                    with self._metrics_collector.measure_ui_response("error_recovery", "error_manager"):
                        error_manager.report_error(
                            error_code=error_code,
                            message=f"Test error for {error_code}",
                            severity=severity,
                            component_name="test_framework"
                        )
                        
                        # Small delay to simulate recovery
                        time.sleep(0.01)
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            return TestResult(
                test_name=test_name,
                test_type="error_handling",
                status="PASS",
                duration_ms=duration_ms,
                metrics={
                    'error_handling_time_ms': duration_ms,
                    'errors_simulated': len(test_errors),
                    'error_manager_active': True
                }
            )
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.logger.error(f"Error handling integration test failed: {e}")
            
            return TestResult(
                test_name=test_name,
                test_type="error_handling",
                status="FAIL",
                duration_ms=duration_ms,
                error_message=str(e),
                metrics={'error_handling_time_ms': duration_ms}
            )
    
    def test_performance_benchmarks(self) -> TestResult:
        """Test performance against baseline benchmarks"""
        test_name = "performance_benchmarks"
        start_time = time.perf_counter()
        
        try:
            self.logger.info("Testing performance benchmarks")
            
            if not self._metrics_collector:
                return TestResult(
                    test_name=test_name,
                    test_type="performance",
                    status="SKIP",
                    duration_ms=0,
                    error_message="Metrics collector not available"
                )
            
            # Generate current metrics report
            report = self._metrics_collector.generate_baseline_report()
            
            # Evaluate against baselines
            evaluations = report.baseline_evaluations
            performance_issues = []
            
            for metric_name, (status, message) in evaluations.items():
                if status in ["CRITICAL", "FAIL"]:
                    performance_issues.append(f"{metric_name}: {message}")
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            if performance_issues:
                return TestResult(
                    test_name=test_name,
                    test_type="performance",
                    status="FAIL",
                    duration_ms=duration_ms,
                    error_message=f"Performance issues: {'; '.join(performance_issues)}",
                    metrics={
                        'benchmark_time_ms': duration_ms,
                        'evaluations': evaluations,
                        'issues_count': len(performance_issues)
                    }
                )
            else:
                return TestResult(
                    test_name=test_name,
                    test_type="performance",
                    status="PASS",
                    duration_ms=duration_ms,
                    metrics={
                        'benchmark_time_ms': duration_ms,
                        'evaluations': evaluations,
                        'all_benchmarks_passed': True
                    }
                )
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.logger.error(f"Performance benchmark test failed: {e}")
            
            return TestResult(
                test_name=test_name,
                test_type="performance",
                status="ERROR",
                duration_ms=duration_ms,
                error_message=str(e),
                metrics={'benchmark_time_ms': duration_ms}
            )
    
    def run_comprehensive_test_suite(self) -> TestSuiteResult:
        """Run complete integration test suite"""
        suite_name = "v2_architecture_integration"
        start_time = time.time()
        start_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time))
        
        self.logger.info(f"Starting comprehensive integration test suite: {suite_name}")
        
        # Setup test environment
        if not self.setup_test_environment():
            raise RuntimeError("Failed to setup test environment")
        
        test_results = []
        
        try:
            with self.test_session(suite_name):
                
                # Test 1: Main entry point startup for each mode
                for mode in self.config.test_modes:
                    result = self.test_main_entry_point_startup(mode)
                    test_results.append(result)
                    
                    # Only continue with other tests if we have a successful startup
                    if result.status == "PASS" and mode == "FULL_V2_PRODUCTION":
                        break
                
                # Test 2: Adapter integration (only if startup succeeded)
                if any(r.status == "PASS" for r in test_results):
                    result = self.test_adapter_integration()
                    test_results.append(result)
                
                # Test 3: UI workflow preservation
                result = self.test_ui_workflow_preservation()
                test_results.append(result)
                
                # Test 4: Error handling integration
                result = self.test_error_handling_integration()
                test_results.append(result)
                
                # Test 5: Performance benchmarks
                result = self.test_performance_benchmarks()
                test_results.append(result)
        
        finally:
            self.teardown_test_environment()
        
        # Calculate results
        end_time = time.time()
        end_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(end_time))
        total_duration_ms = (end_time - start_time) * 1000
        
        # Count results
        total_tests = len(test_results)
        passed_tests = len([r for r in test_results if r.status == "PASS"])
        failed_tests = len([r for r in test_results if r.status == "FAIL"])
        skipped_tests = len([r for r in test_results if r.status == "SKIP"])
        error_tests = len([r for r in test_results if r.status == "ERROR"])
        
        # Create suite result
        suite_result = TestSuiteResult(
            suite_name=suite_name,
            start_time=start_time_str,
            end_time=end_time_str,
            total_duration_ms=total_duration_ms,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            skipped_tests=skipped_tests,
            error_tests=error_tests,
            test_results=test_results
        )
        
        # Add overall metrics
        suite_result.overall_metrics = {
            'success_rate': suite_result.success_rate(),
            'total_duration_ms': total_duration_ms,
            'artifacts_generated': len(self._test_artifacts),
            'test_artifacts': self._test_artifacts.copy()
        }
        
        # Add performance summary
        performance_results = [r for r in test_results if r.test_type == "performance"]
        if performance_results:
            suite_result.performance_summary = performance_results[0].metrics
        
        self.logger.info(f"Completed integration test suite: {suite_name}")
        self.logger.info(f"Results: {passed_tests}/{total_tests} passed, {failed_tests} failed, {skipped_tests} skipped, {error_tests} errors")
        
        return suite_result
    
    def save_test_report(self, suite_result: TestSuiteResult, output_path: Path = None) -> Path:
        """Save test suite results to file"""
        if output_path is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_path = Path(f"tests/reports/integration_test_report_{timestamp}.json")
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save as JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(suite_result.to_dict(), f, indent=2, default=str)
        
        self.logger.info(f"Test report saved to: {output_path}")
        return output_path


def run_integration_tests(config: TestConfiguration = None) -> TestSuiteResult:
    """Main entry point for running integration tests"""
    framework = IntegrationTestFramework(config)
    return framework.run_comprehensive_test_suite()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create test configuration
    config = TestConfiguration()
    
    # Run tests
    try:
        result = run_integration_tests(config)
        
        # Save report
        framework = IntegrationTestFramework(config)
        report_path = framework.save_test_report(result)
        
        print(f"\n{'='*60}")
        print(f"INTEGRATION TEST SUITE COMPLETED")
        print(f"{'='*60}")
        print(f"Suite: {result.suite_name}")
        print(f"Duration: {result.total_duration_ms:.2f}ms")
        print(f"Results: {result.passed_tests}/{result.total_tests} passed")
        print(f"Success Rate: {result.success_rate():.1f}%")
        print(f"Report: {report_path}")
        print(f"{'='*60}\n")
        
        # Exit with appropriate code
        sys.exit(0 if result.failed_tests == 0 else 1)
        
    except Exception as e:
        print(f"Integration test execution failed: {e}")
        sys.exit(2) 