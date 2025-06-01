#!/usr/bin/env python3
"""
Integration Test Runner and Reporting System
===========================================

Comprehensive test execution framework for integration testing with detailed
reporting, coverage analysis, and result documentation.
"""

import sys
import os
import time
import json
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import argparse

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tests.integration_config import (
    get_test_config, list_test_configs, 
    IntegrationTestConfig, config_manager
)


@dataclass
class TestResult:
    """Individual test result data structure."""
    test_name: str
    test_class: str
    test_file: str
    status: str  # "passed", "failed", "skipped", "error"
    duration: float
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


@dataclass
class TestSuiteResult:
    """Test suite execution result."""
    suite_name: str
    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration: float
    coverage_percentage: float
    test_results: List[TestResult]
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed / self.total_tests) * 100


@dataclass
class IntegrationTestReport:
    """Complete integration test execution report."""
    execution_id: str
    start_time: datetime
    end_time: datetime
    total_duration: float
    config_name: str
    environment_info: Dict[str, Any]
    suite_results: List[TestSuiteResult]
    overall_summary: Dict[str, Any]
    recommendations: List[str]
    
    @property
    def overall_success_rate(self) -> float:
        """Calculate overall success rate."""
        total_tests = sum(suite.total_tests for suite in self.suite_results)
        total_passed = sum(suite.passed for suite in self.suite_results)
        if total_tests == 0:
            return 0.0
        return (total_passed / total_tests) * 100


class IntegrationTestExecutor:
    """Executes integration tests and generates comprehensive reports."""
    
    def __init__(self, config_name: str = "full"):
        self.config = get_test_config(config_name)
        self.config_name = config_name
        self.execution_id = f"integration_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for test execution."""
        logger = logging.getLogger(f"integration_test_executor")
        logger.setLevel(getattr(logging, self.config.log_level))
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler
        log_file = PROJECT_ROOT / 'tests' / 'logs' / f'{self.execution_id}.log'
        log_file.parent.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger
    
    def run_all_integration_tests(self) -> IntegrationTestReport:
        """Run all integration test suites and generate comprehensive report."""
        self.logger.info(f"Starting integration test execution: {self.execution_id}")
        start_time = datetime.now()
        
        # Test suites to execute
        test_suites = [
            {
                'name': 'Component Interactions',
                'file': 'tests/test_component_interactions.py',
                'description': 'Tests component interface interactions and data flow'
            },
            {
                'name': 'End-to-End Scenarios',
                'file': 'tests/test_end_to_end_scenarios.py',
                'description': 'Tests complete user workflows and business processes'
            }
        ]
        
        suite_results = []
        environment_info = self._gather_environment_info()
        
        for suite_info in test_suites:
            self.logger.info(f"Executing test suite: {suite_info['name']}")
            suite_result = self._execute_test_suite(suite_info)
            suite_results.append(suite_result)
            
            # Log suite results
            self.logger.info(
                f"Suite '{suite_info['name']}' completed: "
                f"{suite_result.passed}/{suite_result.total_tests} passed "
                f"({suite_result.success_rate:.1f}%)"
            )
        
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        # Generate overall summary
        overall_summary = self._generate_overall_summary(suite_results)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(suite_results, overall_summary)
        
        # Create comprehensive report
        report = IntegrationTestReport(
            execution_id=self.execution_id,
            start_time=start_time,
            end_time=end_time,
            total_duration=total_duration,
            config_name=self.config_name,
            environment_info=environment_info,
            suite_results=suite_results,
            overall_summary=overall_summary,
            recommendations=recommendations
        )
        
        self.logger.info(f"Integration test execution completed: {self.execution_id}")
        return report
    
    def _execute_test_suite(self, suite_info: Dict[str, str]) -> TestSuiteResult:
        """Execute a single test suite and collect results."""
        start_time = time.time()
        
        # Prepare pytest command
        pytest_cmd = [
            sys.executable, '-m', 'pytest',
            suite_info['file'],
            '-v',
            '--tb=short',
            '--json-report',
            f'--json-report-file=tests/reports/{self.execution_id}_{suite_info["name"].lower().replace(" ", "_")}.json',
            '--cov=core',
            '--cov=platforms',
            '--cov=data',
            '--cov=ui',
            '--cov-report=json',
            f'--cov-report=html:tests/reports/coverage_{self.execution_id}_{suite_info["name"].lower().replace(" ", "_")}',
            '--timeout=300'
        ]
        
        # Add configuration-specific options
        if self.config.parallel_execution:
            pytest_cmd.extend(['-n', 'auto'])
        
        try:
            # Execute pytest
            result = subprocess.run(
                pytest_cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=self.config.max_test_duration_minutes * 60
            )
            
            duration = time.time() - start_time
            
            # Parse results
            test_results = self._parse_pytest_results(suite_info, result)
            coverage_percentage = self._extract_coverage_percentage(suite_info)
            
            # Calculate summary statistics
            total_tests = len(test_results)
            passed = sum(1 for t in test_results if t.status == "passed")
            failed = sum(1 for t in test_results if t.status == "failed")
            skipped = sum(1 for t in test_results if t.status == "skipped")
            errors = sum(1 for t in test_results if t.status == "error")
            
            return TestSuiteResult(
                suite_name=suite_info['name'],
                total_tests=total_tests,
                passed=passed,
                failed=failed,
                skipped=skipped,
                errors=errors,
                duration=duration,
                coverage_percentage=coverage_percentage,
                test_results=test_results
            )
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"Test suite '{suite_info['name']}' timed out")
            return TestSuiteResult(
                suite_name=suite_info['name'],
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                duration=self.config.max_test_duration_minutes * 60,
                coverage_percentage=0.0,
                test_results=[
                    TestResult(
                        test_name="timeout_error",
                        test_class="TestSuite",
                        test_file=suite_info['file'],
                        status="error",
                        duration=self.config.max_test_duration_minutes * 60,
                        error_message="Test suite execution timed out"
                    )
                ]
            )
        
        except Exception as e:
            self.logger.error(f"Error executing test suite '{suite_info['name']}': {e}")
            return TestSuiteResult(
                suite_name=suite_info['name'],
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                duration=time.time() - start_time,
                coverage_percentage=0.0,
                test_results=[
                    TestResult(
                        test_name="execution_error",
                        test_class="TestSuite",
                        test_file=suite_info['file'],
                        status="error",
                        duration=time.time() - start_time,
                        error_message=str(e)
                    )
                ]
            )
    
    def _parse_pytest_results(self, suite_info: Dict[str, str], result: subprocess.CompletedProcess) -> List[TestResult]:
        """Parse pytest execution results."""
        test_results = []
        
        # Try to parse JSON report if available
        json_report_file = PROJECT_ROOT / 'tests' / 'reports' / f'{self.execution_id}_{suite_info["name"].lower().replace(" ", "_")}.json'
        
        if json_report_file.exists():
            try:
                with open(json_report_file, 'r') as f:
                    json_data = json.load(f)
                
                for test in json_data.get('tests', []):
                    test_results.append(TestResult(
                        test_name=test.get('nodeid', '').split('::')[-1],
                        test_class=test.get('nodeid', '').split('::')[-2] if '::' in test.get('nodeid', '') else 'Unknown',
                        test_file=suite_info['file'],
                        status=test.get('outcome', 'unknown'),
                        duration=test.get('duration', 0.0),
                        error_message=test.get('call', {}).get('longrepr', None) if test.get('outcome') in ['failed', 'error'] else None
                    ))
                    
            except Exception as e:
                self.logger.warning(f"Could not parse JSON report: {e}")
        
        # Fallback: parse from stdout/stderr
        if not test_results:
            test_results = self._parse_pytest_output(suite_info, result.stdout, result.stderr)
        
        return test_results
    
    def _parse_pytest_output(self, suite_info: Dict[str, str], stdout: str, stderr: str) -> List[TestResult]:
        """Parse pytest output when JSON report is not available."""
        test_results = []
        
        # Simple parsing - in real implementation, this would be more sophisticated
        lines = stdout.split('\n')
        for line in lines:
            if '::' in line and any(status in line for status in ['PASSED', 'FAILED', 'SKIPPED', 'ERROR']):
                parts = line.split()
                if len(parts) >= 2:
                    test_name = parts[0].split('::')[-1]
                    status = parts[1].lower()
                    
                    test_results.append(TestResult(
                        test_name=test_name,
                        test_class='Unknown',
                        test_file=suite_info['file'],
                        status=status,
                        duration=0.0
                    ))
        
        # If no tests found, create a placeholder
        if not test_results:
            test_results.append(TestResult(
                test_name="no_tests_detected",
                test_class="Unknown",
                test_file=suite_info['file'],
                status="skipped",
                duration=0.0,
                error_message="No tests detected or parsed"
            ))
        
        return test_results
    
    def _extract_coverage_percentage(self, suite_info: Dict[str, str]) -> float:
        """Extract coverage percentage from coverage report."""
        # Try to read coverage.json if available
        coverage_file = PROJECT_ROOT / 'coverage.json'
        if coverage_file.exists():
            try:
                with open(coverage_file, 'r') as f:
                    coverage_data = json.load(f)
                return coverage_data.get('totals', {}).get('percent_covered', 0.0)
            except Exception:
                pass
        
        return 0.0  # Default if coverage not available
    
    def _gather_environment_info(self) -> Dict[str, Any]:
        """Gather environment information for the report."""
        return {
            'python_version': sys.version,
            'platform': sys.platform,
            'working_directory': str(PROJECT_ROOT),
            'test_config': asdict(self.config),
            'timestamp': datetime.now().isoformat(),
            'execution_id': self.execution_id
        }
    
    def _generate_overall_summary(self, suite_results: List[TestSuiteResult]) -> Dict[str, Any]:
        """Generate overall test execution summary."""
        total_tests = sum(suite.total_tests for suite in suite_results)
        total_passed = sum(suite.passed for suite in suite_results)
        total_failed = sum(suite.failed for suite in suite_results)
        total_skipped = sum(suite.skipped for suite in suite_results)
        total_errors = sum(suite.errors for suite in suite_results)
        total_duration = sum(suite.duration for suite in suite_results)
        avg_coverage = sum(suite.coverage_percentage for suite in suite_results) / len(suite_results) if suite_results else 0.0
        
        return {
            'total_tests': total_tests,
            'total_passed': total_passed,
            'total_failed': total_failed,
            'total_skipped': total_skipped,
            'total_errors': total_errors,
            'total_duration': total_duration,
            'overall_success_rate': (total_passed / total_tests * 100) if total_tests > 0 else 0.0,
            'average_coverage': avg_coverage,
            'suites_executed': len(suite_results),
            'execution_status': 'SUCCESS' if total_failed == 0 and total_errors == 0 else 'FAILURE'
        }
    
    def _generate_recommendations(self, suite_results: List[TestSuiteResult], summary: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        # Coverage recommendations
        if summary['average_coverage'] < 80:
            recommendations.append(
                f"Test coverage is {summary['average_coverage']:.1f}%. "
                "Consider adding more tests to reach 80%+ coverage."
            )
        
        # Failed tests recommendations
        if summary['total_failed'] > 0:
            recommendations.append(
                f"{summary['total_failed']} tests failed. "
                "Review failed tests and fix underlying issues."
            )
        
        # Skipped tests recommendations
        if summary['total_skipped'] > summary['total_tests'] * 0.3:
            recommendations.append(
                f"{summary['total_skipped']} tests were skipped. "
                "Consider implementing missing components to enable more tests."
            )
        
        # Performance recommendations
        if summary['total_duration'] > self.config.max_test_duration_minutes * 60 * 0.8:
            recommendations.append(
                "Test execution is approaching timeout limits. "
                "Consider optimizing test performance or increasing timeout."
            )
        
        # Success recommendations
        if summary['execution_status'] == 'SUCCESS':
            recommendations.append(
                "All tests passed successfully! "
                "Consider adding more edge case tests and increasing coverage."
            )
        
        return recommendations


class IntegrationTestReporter:
    """Generates detailed reports from integration test results."""
    
    def __init__(self, report: IntegrationTestReport):
        self.report = report
        self.output_dir = PROJECT_ROOT / 'tests' / 'reports'
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_html_report(self) -> str:
        """Generate comprehensive HTML report."""
        html_content = self._generate_html_content()
        
        report_file = self.output_dir / f'{self.report.execution_id}_integration_report.html'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(report_file)
    
    def generate_json_report(self) -> str:
        """Generate JSON report for programmatic access."""
        report_data = asdict(self.report)
        
        report_file = self.output_dir / f'{self.report.execution_id}_integration_report.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        return str(report_file)
    
    def generate_summary_report(self) -> str:
        """Generate concise summary report."""
        summary_lines = [
            f"Integration Test Execution Report",
            f"=" * 50,
            f"Execution ID: {self.report.execution_id}",
            f"Configuration: {self.report.config_name}",
            f"Start Time: {self.report.start_time}",
            f"Duration: {self.report.total_duration:.2f} seconds",
            f"",
            f"Overall Results:",
            f"  Total Tests: {self.report.overall_summary['total_tests']}",
            f"  Passed: {self.report.overall_summary['total_passed']}",
            f"  Failed: {self.report.overall_summary['total_failed']}",
            f"  Skipped: {self.report.overall_summary['total_skipped']}",
            f"  Errors: {self.report.overall_summary['total_errors']}",
            f"  Success Rate: {self.report.overall_success_rate:.1f}%",
            f"  Average Coverage: {self.report.overall_summary['average_coverage']:.1f}%",
            f"",
            f"Test Suites:",
        ]
        
        for suite in self.report.suite_results:
            summary_lines.extend([
                f"  {suite.suite_name}:",
                f"    Tests: {suite.total_tests} | Passed: {suite.passed} | Failed: {suite.failed}",
                f"    Success Rate: {suite.success_rate:.1f}% | Coverage: {suite.coverage_percentage:.1f}%",
                f"    Duration: {suite.duration:.2f}s",
                f""
            ])
        
        if self.report.recommendations:
            summary_lines.extend([
                f"Recommendations:",
                *[f"  - {rec}" for rec in self.report.recommendations],
                f""
            ])
        
        summary_content = '\n'.join(summary_lines)
        
        report_file = self.output_dir / f'{self.report.execution_id}_summary.txt'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(summary_content)
        
        return str(report_file)
    
    def _generate_html_content(self) -> str:
        """Generate HTML content for the report."""
        # Simplified HTML template - in real implementation, this would be more sophisticated
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Integration Test Report - {self.report.execution_id}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .summary {{ margin: 20px 0; }}
                .suite {{ margin: 20px 0; border: 1px solid #ddd; padding: 15px; border-radius: 5px; }}
                .passed {{ color: green; }}
                .failed {{ color: red; }}
                .skipped {{ color: orange; }}
                .error {{ color: darkred; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Integration Test Report</h1>
                <p><strong>Execution ID:</strong> {self.report.execution_id}</p>
                <p><strong>Configuration:</strong> {self.report.config_name}</p>
                <p><strong>Execution Time:</strong> {self.report.start_time} - {self.report.end_time}</p>
                <p><strong>Duration:</strong> {self.report.total_duration:.2f} seconds</p>
            </div>
            
            <div class="summary">
                <h2>Overall Summary</h2>
                <p><strong>Success Rate:</strong> {self.report.overall_success_rate:.1f}%</p>
                <p><strong>Total Tests:</strong> {self.report.overall_summary['total_tests']}</p>
                <p><strong>Passed:</strong> <span class="passed">{self.report.overall_summary['total_passed']}</span></p>
                <p><strong>Failed:</strong> <span class="failed">{self.report.overall_summary['total_failed']}</span></p>
                <p><strong>Skipped:</strong> <span class="skipped">{self.report.overall_summary['total_skipped']}</span></p>
                <p><strong>Errors:</strong> <span class="error">{self.report.overall_summary['total_errors']}</span></p>
            </div>
            
            <h2>Test Suites</h2>
            {self._generate_suite_html()}
            
            {self._generate_recommendations_html()}
        </body>
        </html>
        """
        
        return html_template
    
    def _generate_suite_html(self) -> str:
        """Generate HTML for test suites."""
        suite_html = ""
        for suite in self.report.suite_results:
            suite_html += f"""
            <div class="suite">
                <h3>{suite.suite_name}</h3>
                <p><strong>Success Rate:</strong> {suite.success_rate:.1f}%</p>
                <p><strong>Coverage:</strong> {suite.coverage_percentage:.1f}%</p>
                <p><strong>Duration:</strong> {suite.duration:.2f}s</p>
                <p><strong>Tests:</strong> {suite.total_tests} total, 
                   <span class="passed">{suite.passed} passed</span>, 
                   <span class="failed">{suite.failed} failed</span>, 
                   <span class="skipped">{suite.skipped} skipped</span>, 
                   <span class="error">{suite.errors} errors</span></p>
            </div>
            """
        return suite_html
    
    def _generate_recommendations_html(self) -> str:
        """Generate HTML for recommendations."""
        if not self.report.recommendations:
            return ""
        
        rec_html = "<h2>Recommendations</h2><ul>"
        for rec in self.report.recommendations:
            rec_html += f"<li>{rec}</li>"
        rec_html += "</ul>"
        
        return rec_html


def main():
    """Main entry point for integration test execution."""
    parser = argparse.ArgumentParser(description='Run integration tests with comprehensive reporting')
    parser.add_argument('--config', '-c', default='full', choices=list_test_configs(),
                       help='Test configuration to use')
    parser.add_argument('--output-format', '-f', choices=['html', 'json', 'summary', 'all'], 
                       default='all', help='Report output format')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Create test executor
    executor = IntegrationTestExecutor(args.config)
    
    print(f"Starting integration test execution with config: {args.config}")
    print(f"Execution ID: {executor.execution_id}")
    
    # Run tests
    report = executor.run_all_integration_tests()
    
    # Generate reports
    reporter = IntegrationTestReporter(report)
    
    generated_reports = []
    
    if args.output_format in ['html', 'all']:
        html_report = reporter.generate_html_report()
        generated_reports.append(f"HTML Report: {html_report}")
    
    if args.output_format in ['json', 'all']:
        json_report = reporter.generate_json_report()
        generated_reports.append(f"JSON Report: {json_report}")
    
    if args.output_format in ['summary', 'all']:
        summary_report = reporter.generate_summary_report()
        generated_reports.append(f"Summary Report: {summary_report}")
    
    # Print results
    print(f"\nIntegration Test Execution Completed!")
    print(f"Overall Success Rate: {report.overall_success_rate:.1f}%")
    print(f"Total Duration: {report.total_duration:.2f} seconds")
    print(f"\nGenerated Reports:")
    for report_path in generated_reports:
        print(f"  {report_path}")
    
    # Exit with appropriate code
    exit_code = 0 if report.overall_summary['execution_status'] == 'SUCCESS' else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main() 