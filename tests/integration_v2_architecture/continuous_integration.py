#!/usr/bin/env python3
"""
Continuous Integration Monitoring for v2.0 Integration Testing
Task 31.5 - Performance Monitoring and Continuous Integration

This module provides CI/CD integration capabilities for automated performance monitoring,
regression detection, and integration test execution in continuous integration pipelines.
"""

import os
import sys
import time
import json
import subprocess
import logging
import threading
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import sqlite3
import tempfile
import concurrent.futures

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import our test frameworks
from .performance_monitoring import LoadTestExecutor, LoadTestConfiguration, LoadTestScenario
from .test_framework import IntegrationTestFramework, TestConfiguration
from .baseline_metrics import BaselineMetricsCollector


@dataclass
class CIConfiguration:
    """Configuration for CI/CD integration"""
    # CI environment settings
    ci_provider: str = "github"  # github, gitlab, jenkins, etc.
    branch_name: str = "main"
    commit_hash: str = ""
    pr_number: Optional[str] = None
    
    # Test execution settings
    quick_mode: bool = False  # Run reduced test suite for PRs
    full_regression: bool = False  # Run complete regression suite
    performance_baseline_required: bool = True
    
    # Performance thresholds for CI
    max_startup_time_ms: float = 300.0  # Stricter than dev
    max_memory_usage_mb: float = 80.0   # Stricter than dev
    max_ui_response_ms: float = 150.0   # Stricter than dev
    
    # Failure thresholds
    max_allowed_failures: int = 0  # Zero tolerance in CI
    max_performance_regression: float = 0.10  # 10% regression allowed
    
    # Reporting
    generate_artifacts: bool = True
    upload_results: bool = True
    fail_on_performance_regression: bool = True


@dataclass
class CITestReport:
    """CI test execution report"""
    ci_job_id: str
    branch: str
    commit_hash: str
    start_time: datetime
    end_time: Optional[datetime] = None
    
    # Test results
    integration_tests_passed: bool = False
    performance_tests_passed: bool = False
    baseline_comparison_passed: bool = False
    
    # Metrics
    total_test_duration_seconds: float = 0.0
    integration_test_count: int = 0
    integration_failures: int = 0
    performance_test_count: int = 0
    performance_failures: int = 0
    
    # Performance data
    startup_time_ms: float = 0.0
    peak_memory_mb: float = 0.0
    average_response_time_ms: float = 0.0
    
    # Regression analysis
    performance_regression_detected: bool = False
    regression_details: List[str] = field(default_factory=list)
    
    # Artifacts
    artifacts_generated: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'ci_job_id': self.ci_job_id,
            'branch': self.branch,
            'commit_hash': self.commit_hash,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'integration_tests_passed': self.integration_tests_passed,
            'performance_tests_passed': self.performance_tests_passed,
            'baseline_comparison_passed': self.baseline_comparison_passed,
            'total_test_duration_seconds': self.total_test_duration_seconds,
            'integration_test_count': self.integration_test_count,
            'integration_failures': self.integration_failures,
            'performance_test_count': self.performance_test_count,
            'performance_failures': self.performance_failures,
            'startup_time_ms': self.startup_time_ms,
            'peak_memory_mb': self.peak_memory_mb,
            'average_response_time_ms': self.average_response_time_ms,
            'performance_regression_detected': self.performance_regression_detected,
            'regression_details': self.regression_details,
            'artifacts_generated': self.artifacts_generated
        }


class CIPerformanceTracker:
    """Tracks performance metrics across CI builds"""
    
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or Path("tests/ci_performance_history.db")
        self.logger = logging.getLogger(__name__)
        self._init_database()
    
    def _init_database(self):
        """Initialize performance tracking database"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ci_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    branch TEXT NOT NULL,
                    commit_hash TEXT NOT NULL,
                    startup_time_ms REAL,
                    peak_memory_mb REAL,
                    average_response_time_ms REAL,
                    test_success_rate REAL,
                    total_test_duration_seconds REAL,
                    integration_tests_passed INTEGER,
                    performance_tests_passed INTEGER,
                    metadata TEXT
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ci_performance_branch_time 
                ON ci_performance(branch, timestamp)
            """)
    
    def record_ci_metrics(self, report: CITestReport):
        """Record CI test metrics in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO ci_performance (
                    timestamp, branch, commit_hash, startup_time_ms, peak_memory_mb,
                    average_response_time_ms, test_success_rate, total_test_duration_seconds,
                    integration_tests_passed, performance_tests_passed, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report.start_time.isoformat(),
                report.branch,
                report.commit_hash,
                report.startup_time_ms,
                report.peak_memory_mb,
                report.average_response_time_ms,
                1.0 - (report.integration_failures + report.performance_failures) / max(report.integration_test_count + report.performance_test_count, 1),
                report.total_test_duration_seconds,
                1 if report.integration_tests_passed else 0,
                1 if report.performance_tests_passed else 0,
                json.dumps(report.to_dict())
            ))
    
    def get_baseline_metrics(self, branch: str = "main", days_back: int = 30) -> Dict[str, Any]:
        """Get baseline performance metrics for comparison"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    AVG(startup_time_ms) as avg_startup_time,
                    AVG(peak_memory_mb) as avg_memory,
                    AVG(average_response_time_ms) as avg_response_time,
                    AVG(test_success_rate) as avg_success_rate,
                    MIN(startup_time_ms) as min_startup_time,
                    MAX(peak_memory_mb) as max_memory,
                    COUNT(*) as sample_count
                FROM ci_performance 
                WHERE branch = ? AND timestamp >= ? AND timestamp <= ?
                AND integration_tests_passed = 1 AND performance_tests_passed = 1
            """, (branch, start_date.isoformat(), end_date.isoformat()))
            
            row = cursor.fetchone()
            
            if row and row[6] > 0:  # sample_count > 0
                return {
                    'avg_startup_time_ms': row[0] or 0,
                    'avg_memory_mb': row[1] or 0,
                    'avg_response_time_ms': row[2] or 0,
                    'avg_success_rate': row[3] or 0,
                    'min_startup_time_ms': row[4] or 0,
                    'max_memory_mb': row[5] or 0,
                    'sample_count': row[6],
                    'baseline_period_days': days_back
                }
            
            return {}
    
    def detect_performance_regression(self, current_report: CITestReport, 
                                    baseline_metrics: Dict[str, Any],
                                    regression_threshold: float = 0.10) -> Tuple[bool, List[str]]:
        """Detect performance regression compared to baseline"""
        if not baseline_metrics:
            return False, ["No baseline metrics available for comparison"]
        
        regressions = []
        
        # Check startup time regression
        if baseline_metrics.get('avg_startup_time_ms', 0) > 0:
            baseline_startup = baseline_metrics['avg_startup_time_ms']
            current_startup = current_report.startup_time_ms
            
            if current_startup > baseline_startup * (1 + regression_threshold):
                regression_pct = ((current_startup - baseline_startup) / baseline_startup) * 100
                regressions.append(f"Startup time regression: {current_startup:.2f}ms vs baseline {baseline_startup:.2f}ms (+{regression_pct:.1f}%)")
        
        # Check memory usage regression
        if baseline_metrics.get('avg_memory_mb', 0) > 0:
            baseline_memory = baseline_metrics['avg_memory_mb']
            current_memory = current_report.peak_memory_mb
            
            if current_memory > baseline_memory * (1 + regression_threshold):
                regression_pct = ((current_memory - baseline_memory) / baseline_memory) * 100
                regressions.append(f"Memory usage regression: {current_memory:.2f}MB vs baseline {baseline_memory:.2f}MB (+{regression_pct:.1f}%)")
        
        # Check response time regression
        if baseline_metrics.get('avg_response_time_ms', 0) > 0:
            baseline_response = baseline_metrics['avg_response_time_ms']
            current_response = current_report.average_response_time_ms
            
            if current_response > baseline_response * (1 + regression_threshold):
                regression_pct = ((current_response - baseline_response) / baseline_response) * 100
                regressions.append(f"Response time regression: {current_response:.2f}ms vs baseline {baseline_response:.2f}ms (+{regression_pct:.1f}%)")
        
        return len(regressions) > 0, regressions


class CIIntegrationRunner:
    """Main CI integration test runner"""
    
    def __init__(self, config: CIConfiguration):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.performance_tracker = CIPerformanceTracker()
        
        # Test frameworks
        self.test_framework = IntegrationTestFramework(TestConfiguration(
            test_timeout=30.0 if config.quick_mode else 60.0,
            enable_performance_testing=True,
            max_startup_time_ms=config.max_startup_time_ms,
            max_memory_usage_mb=config.max_memory_usage_mb,
            max_ui_response_ms=config.max_ui_response_ms
        ))
        
        self.load_test_executor = LoadTestExecutor(self.test_framework)
        
        # CI report
        self.ci_report = CITestReport(
            ci_job_id=os.environ.get('CI_JOB_ID', f'local_{int(time.time())}'),
            branch=config.branch_name,
            commit_hash=config.commit_hash,
            start_time=datetime.now()
        )
    
    def run_ci_test_suite(self) -> CITestReport:
        """Run complete CI test suite"""
        self.logger.info(f"Starting CI test suite for {self.config.branch_name}@{self.config.commit_hash}")
        
        try:
            # Step 1: Run integration tests
            self.logger.info("Running integration tests...")
            integration_success = self._run_integration_tests()
            self.ci_report.integration_tests_passed = integration_success
            
            # Step 2: Run performance tests (if integration passed or forced)
            if integration_success or not self.config.quick_mode:
                self.logger.info("Running performance tests...")
                performance_success = self._run_performance_tests()
                self.ci_report.performance_tests_passed = performance_success
            else:
                self.logger.warning("Skipping performance tests due to integration test failures")
                self.ci_report.performance_tests_passed = False
            
            # Step 3: Baseline comparison and regression detection
            if self.config.performance_baseline_required:
                self.logger.info("Running baseline comparison...")
                baseline_success = self._run_baseline_comparison()
                self.ci_report.baseline_comparison_passed = baseline_success
            
            # Step 4: Generate artifacts
            if self.config.generate_artifacts:
                self._generate_ci_artifacts()
            
            # Record metrics
            self.performance_tracker.record_ci_metrics(self.ci_report)
            
        except Exception as e:
            self.logger.error(f"CI test suite failed with exception: {e}")
            self.ci_report.integration_tests_passed = False
            self.ci_report.performance_tests_passed = False
            self.ci_report.baseline_comparison_passed = False
        
        finally:
            self.ci_report.end_time = datetime.now()
            self.ci_report.total_test_duration_seconds = (
                self.ci_report.end_time - self.ci_report.start_time
            ).total_seconds()
        
        self._print_ci_summary()
        return self.ci_report
    
    def _run_integration_tests(self) -> bool:
        """Run integration test suite"""
        try:
            # Use existing test framework
            suite_result = self.test_framework.run_comprehensive_test_suite()
            
            self.ci_report.integration_test_count = suite_result.total_tests
            self.ci_report.integration_failures = suite_result.failed_tests + suite_result.error_tests
            
            # Update performance metrics from integration tests
            if suite_result.performance_summary:
                self.ci_report.startup_time_ms = suite_result.performance_summary.get('startup_time_ms', 0)
                self.ci_report.peak_memory_mb = suite_result.performance_summary.get('peak_memory_mb', 0)
                self.ci_report.average_response_time_ms = suite_result.performance_summary.get('avg_response_time_ms', 0)
            
            # Generate integration test report
            report_path = self.test_framework.save_test_report(suite_result)
            self.ci_report.artifacts_generated.append(str(report_path))
            
            # Evaluate success
            success = (suite_result.failed_tests + suite_result.error_tests) <= self.config.max_allowed_failures
            
            self.logger.info(f"Integration tests: {suite_result.passed_tests}/{suite_result.total_tests} passed")
            return success
            
        except Exception as e:
            self.logger.error(f"Integration test execution failed: {e}")
            return False
    
    def _run_performance_tests(self) -> bool:
        """Run performance test suite"""
        try:
            # Configure load tests based on CI mode
            if self.config.quick_mode:
                # Quick mode: run subset of performance tests
                test_configs = [
                    LoadTestConfiguration(
                        scenario_name=LoadTestScenario.STARTUP_STRESS,
                        concurrent_users=2,
                        test_duration_seconds=15.0,
                        max_memory_mb=self.config.max_memory_usage_mb,
                        max_cpu_percent=60.0
                    ),
                    LoadTestConfiguration(
                        scenario_name=LoadTestScenario.UI_INTERACTION_BURST,
                        ui_interaction_frequency=3.0,
                        test_duration_seconds=10.0,
                        max_memory_mb=self.config.max_memory_usage_mb,
                        max_cpu_percent=40.0
                    )
                ]
            else:
                # Full mode: run complete performance suite
                test_configs = None  # Use default comprehensive suite
            
            if test_configs:
                # Run custom test configuration
                results = []
                for config in test_configs:
                    result = self.load_test_executor.execute_load_test_scenario(config)
                    results.append(result)
            else:
                # Run full suite
                results = self.load_test_executor.run_comprehensive_load_test_suite()
            
            self.ci_report.performance_test_count = len(results)
            
            # Evaluate performance test results
            performance_failures = 0
            for result in results:
                baseline_targets = {
                    'ui_response_time': self.config.max_ui_response_ms,
                    'max_memory_mb': self.config.max_memory_usage_mb,
                    'max_cpu_percent': 60.0
                }
                
                if result.evaluate_performance(baseline_targets) == "FAIL":
                    performance_failures += 1
            
            self.ci_report.performance_failures = performance_failures
            
            # Update performance metrics from load tests
            if results:
                self.ci_report.peak_memory_mb = max(
                    self.ci_report.peak_memory_mb,
                    max(r.metrics.peak_memory_mb for r in results)
                )
                
                avg_response_times = [
                    getattr(r.metrics, 'avg_response_time_ms', 0) for r in results 
                    if hasattr(r.metrics, 'avg_response_time_ms')
                ]
                if avg_response_times:
                    self.ci_report.average_response_time_ms = sum(avg_response_times) / len(avg_response_times)
            
            # Generate performance test report
            report = self.load_test_executor.generate_performance_report(results)
            report_path = self.load_test_executor.save_performance_report(report)
            self.ci_report.artifacts_generated.append(str(report_path))
            
            success = performance_failures <= self.config.max_allowed_failures
            self.logger.info(f"Performance tests: {len(results) - performance_failures}/{len(results)} passed")
            return success
            
        except Exception as e:
            self.logger.error(f"Performance test execution failed: {e}")
            return False
    
    def _run_baseline_comparison(self) -> bool:
        """Run baseline comparison and regression detection"""
        try:
            # Get baseline metrics
            baseline_metrics = self.performance_tracker.get_baseline_metrics(
                branch="main",  # Always compare against main branch
                days_back=30
            )
            
            if not baseline_metrics:
                self.logger.warning("No baseline metrics available for comparison")
                return not self.config.performance_baseline_required  # Pass if not required
            
            # Detect regression
            has_regression, regression_details = self.performance_tracker.detect_performance_regression(
                self.ci_report,
                baseline_metrics,
                self.config.max_performance_regression
            )
            
            self.ci_report.performance_regression_detected = has_regression
            self.ci_report.regression_details = regression_details
            
            if has_regression:
                self.logger.warning("Performance regression detected:")
                for detail in regression_details:
                    self.logger.warning(f"  - {detail}")
                
                return not self.config.fail_on_performance_regression
            else:
                self.logger.info("No performance regression detected")
                return True
                
        except Exception as e:
            self.logger.error(f"Baseline comparison failed: {e}")
            return False
    
    def _generate_ci_artifacts(self):
        """Generate CI artifacts and reports"""
        try:
            # Generate CI summary report
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ci_report_path = Path(f"tests/reports/ci_report_{timestamp}.json")
            ci_report_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(ci_report_path, 'w', encoding='utf-8') as f:
                json.dump(self.ci_report.to_dict(), f, indent=2, default=str)
            
            self.ci_report.artifacts_generated.append(str(ci_report_path))
            
            # Generate performance trend analysis if enough data
            baseline_metrics = self.performance_tracker.get_baseline_metrics(
                branch=self.config.branch_name,
                days_back=90
            )
            
            if baseline_metrics and baseline_metrics.get('sample_count', 0) >= 5:
                trend_report = {
                    'current_metrics': {
                        'startup_time_ms': self.ci_report.startup_time_ms,
                        'peak_memory_mb': self.ci_report.peak_memory_mb,
                        'average_response_time_ms': self.ci_report.average_response_time_ms
                    },
                    'baseline_metrics': baseline_metrics,
                    'trend_analysis': {
                        'startup_time_trend': 'stable',  # Could implement actual trend analysis
                        'memory_usage_trend': 'stable',
                        'response_time_trend': 'stable'
                    }
                }
                
                trend_report_path = Path(f"tests/reports/performance_trend_{timestamp}.json")
                with open(trend_report_path, 'w', encoding='utf-8') as f:
                    json.dump(trend_report, f, indent=2, default=str)
                
                self.ci_report.artifacts_generated.append(str(trend_report_path))
            
            self.logger.info(f"Generated {len(self.ci_report.artifacts_generated)} CI artifacts")
            
        except Exception as e:
            self.logger.error(f"Failed to generate CI artifacts: {e}")
    
    def _print_ci_summary(self):
        """Print CI test summary"""
        report = self.ci_report
        
        print(f"\n{'='*60}")
        print(f"CI TEST SUITE SUMMARY")
        print(f"{'='*60}")
        print(f"Branch: {report.branch}")
        print(f"Commit: {report.commit_hash}")
        print(f"Duration: {report.total_test_duration_seconds:.2f}s")
        print(f"")
        print(f"Integration Tests: {'✅ PASS' if report.integration_tests_passed else '❌ FAIL'}")
        print(f"  - Tests Run: {report.integration_test_count}")
        print(f"  - Failures: {report.integration_failures}")
        print(f"")
        print(f"Performance Tests: {'✅ PASS' if report.performance_tests_passed else '❌ FAIL'}")
        print(f"  - Tests Run: {report.performance_test_count}")
        print(f"  - Failures: {report.performance_failures}")
        print(f"")
        print(f"Baseline Comparison: {'✅ PASS' if report.baseline_comparison_passed else '❌ FAIL'}")
        
        if report.performance_regression_detected:
            print(f"Performance Regression: {'⚠️ DETECTED'}")
            for detail in report.regression_details:
                print(f"  - {detail}")
        else:
            print(f"Performance Regression: {'✅ NONE'}")
        
        print(f"")
        print(f"Performance Metrics:")
        print(f"  - Startup Time: {report.startup_time_ms:.2f}ms")
        print(f"  - Peak Memory: {report.peak_memory_mb:.2f}MB")
        print(f"  - Avg Response: {report.average_response_time_ms:.2f}ms")
        print(f"")
        print(f"Artifacts: {len(report.artifacts_generated)} generated")
        print(f"{'='*60}")
        
        # Overall CI result
        overall_success = (
            report.integration_tests_passed and 
            report.performance_tests_passed and 
            report.baseline_comparison_passed
        )
        
        if overall_success:
            print(f"🎉 CI SUITE: PASS")
        else:
            print(f"💥 CI SUITE: FAIL")
        
        print(f"{'='*60}\n")


def get_ci_configuration_from_env() -> CIConfiguration:
    """Extract CI configuration from environment variables"""
    return CIConfiguration(
        ci_provider=os.environ.get('CI_PROVIDER', 'github'),
        branch_name=os.environ.get('CI_BRANCH', os.environ.get('GITHUB_REF_NAME', 'main')),
        commit_hash=os.environ.get('CI_COMMIT_SHA', os.environ.get('GITHUB_SHA', 'unknown')),
        pr_number=os.environ.get('PR_NUMBER', os.environ.get('GITHUB_PR_NUMBER')),
        quick_mode=os.environ.get('CI_QUICK_MODE', 'false').lower() == 'true',
        full_regression=os.environ.get('CI_FULL_REGRESSION', 'false').lower() == 'true',
        performance_baseline_required=os.environ.get('CI_BASELINE_REQUIRED', 'true').lower() == 'true',
        max_startup_time_ms=float(os.environ.get('CI_MAX_STARTUP_MS', '300')),
        max_memory_usage_mb=float(os.environ.get('CI_MAX_MEMORY_MB', '80')),
        max_ui_response_ms=float(os.environ.get('CI_MAX_RESPONSE_MS', '150')),
        max_allowed_failures=int(os.environ.get('CI_MAX_FAILURES', '0')),
        max_performance_regression=float(os.environ.get('CI_MAX_REGRESSION', '0.10')),
        generate_artifacts=os.environ.get('CI_GENERATE_ARTIFACTS', 'true').lower() == 'true',
        upload_results=os.environ.get('CI_UPLOAD_RESULTS', 'true').lower() == 'true',
        fail_on_performance_regression=os.environ.get('CI_FAIL_ON_REGRESSION', 'true').lower() == 'true'
    )


def main():
    """Main entry point for CI test execution"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Get CI configuration
    config = get_ci_configuration_from_env()
    
    # Create CI runner
    runner = CIIntegrationRunner(config)
    
    # Run CI test suite
    report = runner.run_ci_test_suite()
    
    # Determine exit code
    overall_success = (
        report.integration_tests_passed and 
        report.performance_tests_passed and 
        report.baseline_comparison_passed
    )
    
    sys.exit(0 if overall_success else 1)


if __name__ == "__main__":
    main() 