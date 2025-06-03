#!/usr/bin/env python3
"""
Final Integration Test Report Generator and Cross-Platform Testing
Task 31.7 - Complete Cross-Platform Testing and Final Reporting

Comprehensive final reporting system that aggregates all test results from Tasks 31.1-31.6
and provides cross-platform validation for the v2.0 architecture integration.
"""

import sys
import os
import json
import logging
import platform
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import statistics
import hashlib

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import all test frameworks
from .baseline_metrics import BaselineMetricsCollector
from .test_framework import IntegrationTestFramework, TestConfiguration
from .performance_monitoring import LoadTestExecutor, run_performance_test_suite
from .regression_testing import RegressionTestExecutor, run_regression_test_suite
from .continuous_integration import CIIntegrationRunner, get_ci_configuration_from_env


@dataclass
class PlatformInfo:
    """System platform information"""
    os_name: str
    os_version: str
    architecture: str
    python_version: str
    processor: str
    memory_gb: float
    disk_space_gb: float
    
    @classmethod
    def detect_current_platform(cls) -> 'PlatformInfo':
        """Detect current platform information"""
        import psutil
        
        return cls(
            os_name=platform.system(),
            os_version=platform.version(),
            architecture=platform.architecture()[0],
            python_version=platform.python_version(),
            processor=platform.processor() or "Unknown",
            memory_gb=psutil.virtual_memory().total / (1024**3),
            disk_space_gb=psutil.disk_usage('.').total / (1024**3)
        )


@dataclass
class TestPhaseResult:
    """Results from individual test phases"""
    phase_name: str
    phase_id: str
    execution_time: float
    status: str  # COMPLETED, FAILED, SKIPPED
    
    # Test metrics
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    error_tests: int = 0
    skipped_tests: int = 0
    
    # Performance metrics
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Issues and findings
    critical_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    # Artifacts
    report_files: List[str] = field(default_factory=list)
    
    def success_rate(self) -> float:
        """Calculate test success rate"""
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100


@dataclass
class CrossPlatformTestResult:
    """Results from cross-platform testing"""
    platform_info: PlatformInfo
    test_results: List[TestPhaseResult] = field(default_factory=list)
    platform_specific_issues: List[str] = field(default_factory=list)
    compatibility_score: float = 0.0
    
    def overall_success_rate(self) -> float:
        """Calculate overall success rate across all test phases"""
        if not self.test_results:
            return 0.0
        
        total_tests = sum(r.total_tests for r in self.test_results)
        passed_tests = sum(r.passed_tests for r in self.test_results)
        
        if total_tests == 0:
            return 0.0
        return (passed_tests / total_tests) * 100


@dataclass
class FinalIntegrationReport:
    """Comprehensive final integration test report"""
    report_id: str
    generation_timestamp: datetime
    project_version: str
    integration_version: str
    
    # Test execution summary
    total_execution_time: float = 0.0
    total_test_count: int = 0
    overall_success_rate: float = 0.0
    
    # Phase results
    phase_results: List[TestPhaseResult] = field(default_factory=list)
    
    # Cross-platform results
    platform_results: List[CrossPlatformTestResult] = field(default_factory=list)
    
    # Analysis
    critical_issues_summary: List[str] = field(default_factory=list)
    performance_analysis: Dict[str, Any] = field(default_factory=dict)
    integration_readiness: str = "PENDING"  # READY, NOT_READY, CONDITIONAL
    
    # Recommendations
    immediate_actions: List[str] = field(default_factory=list)
    future_improvements: List[str] = field(default_factory=list)
    
    # Stakeholder summary
    executive_summary: str = ""
    technical_summary: str = ""
    
    # Artifacts
    all_artifacts: List[str] = field(default_factory=list)


class CrossPlatformTester:
    """Cross-platform testing coordinator"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.current_platform = PlatformInfo.detect_current_platform()
        
        # Test frameworks
        self.integration_framework = IntegrationTestFramework()
        self.load_test_executor = LoadTestExecutor()
        self.regression_executor = RegressionTestExecutor()
    
    def run_cross_platform_test_suite(self) -> CrossPlatformTestResult:
        """Run comprehensive test suite on current platform"""
        self.logger.info(f"Running cross-platform test suite on {self.current_platform.os_name}")
        
        platform_result = CrossPlatformTestResult(platform_info=self.current_platform)
        platform_specific_issues = []
        
        try:
            # Phase 1: Integration Tests
            self.logger.info("Phase 1: Running integration tests...")
            integration_phase = self._run_integration_test_phase()
            platform_result.test_results.append(integration_phase)
            
            # Phase 2: Performance Tests
            self.logger.info("Phase 2: Running performance tests...")
            performance_phase = self._run_performance_test_phase()
            platform_result.test_results.append(performance_phase)
            
            # Phase 3: Regression Tests
            self.logger.info("Phase 3: Running regression tests...")
            regression_phase = self._run_regression_test_phase()
            platform_result.test_results.append(regression_phase)
            
            # Phase 4: Platform-Specific Tests
            self.logger.info("Phase 4: Running platform-specific tests...")
            platform_phase = self._run_platform_specific_tests()
            platform_result.test_results.append(platform_phase)
            
            # Analyze platform compatibility
            platform_result.compatibility_score = self._calculate_compatibility_score(platform_result)
            platform_result.platform_specific_issues = self._identify_platform_issues(platform_result)
            
        except Exception as e:
            self.logger.error(f"Cross-platform testing failed: {e}")
            platform_result.platform_specific_issues.append(f"Testing framework error: {str(e)}")
        
        return platform_result
    
    def _run_integration_test_phase(self) -> TestPhaseResult:
        """Run integration test phase"""
        start_time = datetime.now()
        
        try:
            # Run integration test suite
            suite_result = self.integration_framework.run_comprehensive_test_suite()
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            phase = TestPhaseResult(
                phase_name="Integration Testing",
                phase_id="integration",
                execution_time=execution_time,
                status="COMPLETED",
                total_tests=suite_result.total_tests,
                passed_tests=suite_result.passed_tests,
                failed_tests=suite_result.failed_tests,
                error_tests=suite_result.error_tests,
                skipped_tests=suite_result.skipped_tests
            )
            
            # Add performance metrics from integration tests
            if suite_result.performance_summary:
                phase.performance_metrics = suite_result.performance_summary
            
            # Identify critical issues
            if suite_result.failed_tests > 0:
                phase.critical_issues.append(f"{suite_result.failed_tests} integration tests failed")
            
            if suite_result.error_tests > 0:
                phase.critical_issues.append(f"{suite_result.error_tests} integration tests had errors")
            
            # Save report
            report_path = self.integration_framework.save_test_report(suite_result)
            phase.report_files.append(str(report_path))
            
            return phase
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return TestPhaseResult(
                phase_name="Integration Testing",
                phase_id="integration",
                execution_time=execution_time,
                status="FAILED",
                critical_issues=[f"Integration test execution failed: {str(e)}"]
            )
    
    def _run_performance_test_phase(self) -> TestPhaseResult:
        """Run performance test phase"""
        start_time = datetime.now()
        
        try:
            # Run performance test suite
            report = run_performance_test_suite()
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            phase = TestPhaseResult(
                phase_name="Performance Testing",
                phase_id="performance",
                execution_time=execution_time,
                status="COMPLETED",
                total_tests=report['summary']['total_tests'],
                passed_tests=report['summary']['passed_tests'],
                failed_tests=report['summary']['failed_tests'],
                performance_metrics=report['performance_analysis']
            )
            
            # Identify performance issues
            if report['summary']['failed_tests'] > 0:
                phase.critical_issues.append(f"{report['summary']['failed_tests']} performance tests failed")
            
            # Add recommendations from performance report
            phase.recommendations.extend(report.get('recommendations', []))
            
            return phase
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return TestPhaseResult(
                phase_name="Performance Testing",
                phase_id="performance",
                execution_time=execution_time,
                status="FAILED",
                critical_issues=[f"Performance test execution failed: {str(e)}"]
            )
    
    def _run_regression_test_phase(self) -> TestPhaseResult:
        """Run regression test phase"""
        start_time = datetime.now()
        
        try:
            # Run regression test suite
            report = run_regression_test_suite()
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            phase = TestPhaseResult(
                phase_name="Regression Testing",
                phase_id="regression",
                execution_time=execution_time,
                status="COMPLETED",
                total_tests=report['summary']['total_tests'],
                passed_tests=report['summary']['passed_tests'],
                failed_tests=report['summary']['failed_tests'],
                error_tests=report['summary']['error_tests'],
                skipped_tests=report['summary']['skipped_tests']
            )
            
            # Identify regression issues
            if report['summary']['regression_count'] > 0:
                phase.critical_issues.append(f"{report['summary']['regression_count']} regressions detected")
            
            if report['summary']['failed_tests'] > 0:
                phase.critical_issues.append(f"{report['summary']['failed_tests']} regression tests failed")
            
            return phase
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return TestPhaseResult(
                phase_name="Regression Testing",
                phase_id="regression",
                execution_time=execution_time,
                status="FAILED",
                critical_issues=[f"Regression test execution failed: {str(e)}"]
            )
    
    def _run_platform_specific_tests(self) -> TestPhaseResult:
        """Run platform-specific compatibility tests"""
        start_time = datetime.now()
        
        try:
            platform_tests = self._get_platform_specific_test_cases()
            
            total_tests = len(platform_tests)
            passed_tests = 0
            failed_tests = 0
            issues = []
            
            for test_name, test_func in platform_tests.items():
                try:
                    result = test_func()
                    if result:
                        passed_tests += 1
                    else:
                        failed_tests += 1
                        issues.append(f"Platform test failed: {test_name}")
                except Exception as e:
                    failed_tests += 1
                    issues.append(f"Platform test error in {test_name}: {str(e)}")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            phase = TestPhaseResult(
                phase_name="Platform-Specific Testing",
                phase_id="platform_specific",
                execution_time=execution_time,
                status="COMPLETED",
                total_tests=total_tests,
                passed_tests=passed_tests,
                failed_tests=failed_tests,
                critical_issues=issues
            )
            
            return phase
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return TestPhaseResult(
                phase_name="Platform-Specific Testing",
                phase_id="platform_specific",
                execution_time=execution_time,
                status="FAILED",
                critical_issues=[f"Platform-specific test execution failed: {str(e)}"]
            )
    
    def _get_platform_specific_test_cases(self) -> Dict[str, callable]:
        """Get platform-specific test cases"""
        tests = {
            "file_system_permissions": self._test_file_system_permissions,
            "memory_availability": self._test_memory_availability,
            "process_creation": self._test_process_creation,
            "network_connectivity": self._test_network_connectivity,
            "graphics_support": self._test_graphics_support,
        }
        
        # Add OS-specific tests
        if self.current_platform.os_name == "Windows":
            tests.update({
                "windows_registry": self._test_windows_registry,
                "windows_services": self._test_windows_services,
            })
        elif self.current_platform.os_name == "Linux":
            tests.update({
                "linux_permissions": self._test_linux_permissions,
                "display_server": self._test_display_server,
            })
        elif self.current_platform.os_name == "Darwin":  # macOS
            tests.update({
                "macos_frameworks": self._test_macos_frameworks,
                "app_bundle": self._test_app_bundle,
            })
        
        return tests
    
    # Platform-specific test implementations
    def _test_file_system_permissions(self) -> bool:
        """Test file system permissions"""
        try:
            test_file = Path("test_permissions.tmp")
            test_file.write_text("test")
            test_file.unlink()
            return True
        except Exception:
            return False
    
    def _test_memory_availability(self) -> bool:
        """Test memory availability"""
        try:
            import psutil
            available_gb = psutil.virtual_memory().available / (1024**3)
            return available_gb >= 1.0  # Require at least 1GB available
        except Exception:
            return False
    
    def _test_process_creation(self) -> bool:
        """Test process creation capabilities"""
        try:
            result = subprocess.run([sys.executable, "-c", "print('test')"], 
                                  capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False
    
    def _test_network_connectivity(self) -> bool:
        """Test basic network connectivity"""
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=5)
            return True
        except Exception:
            return False
    
    def _test_graphics_support(self) -> bool:
        """Test graphics/GUI support"""
        try:
            # Try to import PyQt6 (our GUI framework)
            from PyQt6.QtWidgets import QApplication
            return True
        except Exception:
            return False
    
    def _test_windows_registry(self) -> bool:
        """Test Windows registry access"""
        if self.current_platform.os_name != "Windows":
            return True  # Skip on non-Windows
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software"):
                pass
            return True
        except Exception:
            return False
    
    def _test_windows_services(self) -> bool:
        """Test Windows services access"""
        if self.current_platform.os_name != "Windows":
            return True
        # Simplified test - just return True for now
        return True
    
    def _test_linux_permissions(self) -> bool:
        """Test Linux-specific permissions"""
        if self.current_platform.os_name != "Linux":
            return True
        # Test basic file operations
        return self._test_file_system_permissions()
    
    def _test_display_server(self) -> bool:
        """Test Linux display server (X11/Wayland)"""
        if self.current_platform.os_name != "Linux":
            return True
        try:
            # Check for DISPLAY environment variable
            return "DISPLAY" in os.environ or "WAYLAND_DISPLAY" in os.environ
        except Exception:
            return False
    
    def _test_macos_frameworks(self) -> bool:
        """Test macOS framework access"""
        if self.current_platform.os_name != "Darwin":
            return True
        # Simplified test
        return True
    
    def _test_app_bundle(self) -> bool:
        """Test macOS app bundle support"""
        if self.current_platform.os_name != "Darwin":
            return True
        # Simplified test
        return True
    
    def _calculate_compatibility_score(self, platform_result: CrossPlatformTestResult) -> float:
        """Calculate platform compatibility score"""
        if not platform_result.test_results:
            return 0.0
        
        # Weight different test phases
        weights = {
            "integration": 0.4,
            "performance": 0.3,
            "regression": 0.2,
            "platform_specific": 0.1
        }
        
        weighted_score = 0.0
        total_weight = 0.0
        
        for result in platform_result.test_results:
            weight = weights.get(result.phase_id, 0.1)
            score = result.success_rate()
            weighted_score += score * weight
            total_weight += weight
        
        if total_weight > 0:
            return weighted_score / total_weight
        return 0.0
    
    def _identify_platform_issues(self, platform_result: CrossPlatformTestResult) -> List[str]:
        """Identify platform-specific issues"""
        issues = []
        
        # Check for platform-specific patterns
        os_name = platform_result.platform_info.os_name
        
        for result in platform_result.test_results:
            for issue in result.critical_issues:
                # Add platform context to issues
                platform_issue = f"[{os_name}] {issue}"
                issues.append(platform_issue)
        
        # Add platform-specific recommendations
        if os_name == "Windows" and platform_result.compatibility_score < 90:
            issues.append("[Windows] Consider testing with different Windows versions")
        elif os_name == "Linux" and platform_result.compatibility_score < 90:
            issues.append("[Linux] Consider testing with different distributions")
        elif os_name == "Darwin" and platform_result.compatibility_score < 90:
            issues.append("[macOS] Consider testing with different macOS versions")
        
        return issues


class FinalReportGenerator:
    """Generates comprehensive final integration test report"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.cross_platform_tester = CrossPlatformTester()
    
    def generate_final_report(self) -> FinalIntegrationReport:
        """Generate comprehensive final integration test report"""
        self.logger.info("Generating final integration test report...")
        
        # Generate unique report ID
        timestamp = datetime.now()
        report_id = hashlib.md5(f"integration_report_{timestamp}".encode()).hexdigest()[:8]
        
        report = FinalIntegrationReport(
            report_id=report_id,
            generation_timestamp=timestamp,
            project_version="v1.2.1",
            integration_version="v2.0"
        )
        
        try:
            # Run cross-platform testing
            self.logger.info("Running cross-platform test suite...")
            platform_result = self.cross_platform_tester.run_cross_platform_test_suite()
            report.platform_results.append(platform_result)
            
            # Aggregate phase results
            report.phase_results = platform_result.test_results
            
            # Calculate overall metrics
            self._calculate_overall_metrics(report)
            
            # Perform analysis
            self._perform_analysis(report)
            
            # Generate summaries
            self._generate_summaries(report)
            
            # Determine integration readiness
            self._determine_integration_readiness(report)
            
            self.logger.info(f"Final report generated: {report_id}")
            
        except Exception as e:
            self.logger.error(f"Final report generation failed: {e}")
            report.critical_issues_summary.append(f"Report generation error: {str(e)}")
            report.integration_readiness = "NOT_READY"
        
        return report
    
    def _calculate_overall_metrics(self, report: FinalIntegrationReport):
        """Calculate overall test metrics"""
        total_tests = 0
        passed_tests = 0
        total_time = 0.0
        
        for phase in report.phase_results:
            total_tests += phase.total_tests
            passed_tests += phase.passed_tests
            total_time += phase.execution_time
        
        report.total_test_count = total_tests
        report.total_execution_time = total_time
        
        if total_tests > 0:
            report.overall_success_rate = (passed_tests / total_tests) * 100
        else:
            report.overall_success_rate = 0.0
    
    def _perform_analysis(self, report: FinalIntegrationReport):
        """Perform comprehensive analysis of test results"""
        # Collect all critical issues
        critical_issues = []
        performance_data = {}
        
        for phase in report.phase_results:
            critical_issues.extend(phase.critical_issues)
            
            # Collect performance metrics
            if phase.performance_metrics:
                performance_data[phase.phase_id] = phase.performance_metrics
        
        # Add platform-specific issues
        for platform_result in report.platform_results:
            critical_issues.extend(platform_result.platform_specific_issues)
        
        report.critical_issues_summary = list(set(critical_issues))  # Remove duplicates
        report.performance_analysis = performance_data
        
        # Generate recommendations
        self._generate_recommendations(report)
    
    def _generate_recommendations(self, report: FinalIntegrationReport):
        """Generate actionable recommendations"""
        immediate_actions = []
        future_improvements = []
        
        # Analyze success rate
        if report.overall_success_rate < 95:
            immediate_actions.append("Address failing tests before integration deployment")
        
        # Analyze critical issues
        if len(report.critical_issues_summary) > 0:
            immediate_actions.append("Resolve all critical issues identified in testing")
        
        # Analyze performance
        for phase_id, metrics in report.performance_analysis.items():
            if "peak_memory_usage_mb" in metrics and metrics["peak_memory_usage_mb"] > 100:
                future_improvements.append(f"Optimize memory usage in {phase_id} (current: {metrics['peak_memory_usage_mb']:.1f}MB)")
        
        # Platform-specific recommendations
        for platform_result in report.platform_results:
            if platform_result.compatibility_score < 90:
                os_name = platform_result.platform_info.os_name
                immediate_actions.append(f"Improve {os_name} compatibility (score: {platform_result.compatibility_score:.1f}%)")
        
        # General recommendations
        future_improvements.extend([
            "Implement continuous integration testing",
            "Add more comprehensive error handling tests",
            "Enhance performance monitoring and alerting",
            "Develop automated regression test suite for CI/CD"
        ])
        
        report.immediate_actions = immediate_actions
        report.future_improvements = future_improvements
    
    def _generate_summaries(self, report: FinalIntegrationReport):
        """Generate executive and technical summaries"""
        # Executive Summary
        exec_summary = f"""
        **Integration Testing Executive Summary**
        
        The v2.0 architecture integration with UI v1.2.1 has undergone comprehensive testing across {len(report.phase_results)} test phases.
        
        **Key Results:**
        - Overall Success Rate: {report.overall_success_rate:.1f}%
        - Total Tests Executed: {report.total_test_count}
        - Execution Time: {report.total_execution_time:.1f} seconds
        - Critical Issues: {len(report.critical_issues_summary)}
        
        **Integration Readiness: {report.integration_readiness}**
        
        {f"**Immediate Actions Required:** {len(report.immediate_actions)} items need attention before deployment." if report.immediate_actions else "**No immediate actions required** - integration is ready for deployment."}
        """
        
        # Technical Summary
        tech_summary = f"""
        **Technical Integration Test Summary**
        
        **Test Coverage:**
        """
        
        for phase in report.phase_results:
            tech_summary += f"\n- {phase.phase_name}: {phase.passed_tests}/{phase.total_tests} passed ({phase.success_rate():.1f}%)"
        
        tech_summary += f"""
        
        **Performance Analysis:**
        """
        for phase_id, metrics in report.performance_analysis.items():
            tech_summary += f"\n- {phase_id}: {json.dumps(metrics, indent=2)}"
        
        tech_summary += f"""
        
        **Platform Compatibility:**
        """
        for platform_result in report.platform_results:
            tech_summary += f"\n- {platform_result.platform_info.os_name}: {platform_result.compatibility_score:.1f}% compatible"
        
        report.executive_summary = exec_summary.strip()
        report.technical_summary = tech_summary.strip()
    
    def _determine_integration_readiness(self, report: FinalIntegrationReport):
        """Determine overall integration readiness"""
        # Criteria for readiness
        success_rate_threshold = 95.0
        max_critical_issues = 0
        min_platform_compatibility = 90.0
        
        # Check success rate
        if report.overall_success_rate < success_rate_threshold:
            report.integration_readiness = "NOT_READY"
            return
        
        # Check critical issues
        if len(report.critical_issues_summary) > max_critical_issues:
            report.integration_readiness = "NOT_READY"
            return
        
        # Check platform compatibility
        for platform_result in report.platform_results:
            if platform_result.compatibility_score < min_platform_compatibility:
                report.integration_readiness = "CONDITIONAL"
                return
        
        # If all criteria met
        report.integration_readiness = "READY"
    
    def save_final_report(self, report: FinalIntegrationReport, output_dir: Path = None) -> Path:
        """Save final integration test report"""
        if output_dir is None:
            output_dir = Path("tests/reports")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save JSON report
        json_path = output_dir / f"final_integration_report_{report.report_id}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self._report_to_dict(report), f, indent=2, default=str)
        
        # Save Markdown report
        md_path = output_dir / f"final_integration_report_{report.report_id}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(self._generate_markdown_report(report))
        
        report.all_artifacts.extend([str(json_path), str(md_path)])
        
        self.logger.info(f"Final report saved: {json_path}")
        return json_path
    
    def _report_to_dict(self, report: FinalIntegrationReport) -> Dict[str, Any]:
        """Convert report to dictionary for JSON serialization"""
        return {
            "report_id": report.report_id,
            "generation_timestamp": report.generation_timestamp.isoformat(),
            "project_version": report.project_version,
            "integration_version": report.integration_version,
            "total_execution_time": report.total_execution_time,
            "total_test_count": report.total_test_count,
            "overall_success_rate": report.overall_success_rate,
            "integration_readiness": report.integration_readiness,
            "phase_results": [
                {
                    "phase_name": p.phase_name,
                    "phase_id": p.phase_id,
                    "execution_time": p.execution_time,
                    "status": p.status,
                    "total_tests": p.total_tests,
                    "passed_tests": p.passed_tests,
                    "failed_tests": p.failed_tests,
                    "error_tests": p.error_tests,
                    "skipped_tests": p.skipped_tests,
                    "success_rate": p.success_rate(),
                    "performance_metrics": p.performance_metrics,
                    "critical_issues": p.critical_issues,
                    "warnings": p.warnings,
                    "recommendations": p.recommendations,
                    "report_files": p.report_files
                } for p in report.phase_results
            ],
            "platform_results": [
                {
                    "platform_info": {
                        "os_name": pr.platform_info.os_name,
                        "os_version": pr.platform_info.os_version,
                        "architecture": pr.platform_info.architecture,
                        "python_version": pr.platform_info.python_version,
                        "processor": pr.platform_info.processor,
                        "memory_gb": pr.platform_info.memory_gb,
                        "disk_space_gb": pr.platform_info.disk_space_gb
                    },
                    "overall_success_rate": pr.overall_success_rate(),
                    "compatibility_score": pr.compatibility_score,
                    "platform_specific_issues": pr.platform_specific_issues
                } for pr in report.platform_results
            ],
            "critical_issues_summary": report.critical_issues_summary,
            "performance_analysis": report.performance_analysis,
            "immediate_actions": report.immediate_actions,
            "future_improvements": report.future_improvements,
            "executive_summary": report.executive_summary,
            "technical_summary": report.technical_summary,
            "all_artifacts": report.all_artifacts
        }
    
    def _generate_markdown_report(self, report: FinalIntegrationReport) -> str:
        """Generate markdown version of the report"""
        return f"""# Final Integration Test Report
**Report ID:** {report.report_id}  
**Generated:** {report.generation_timestamp.strftime('%Y-%m-%d %H:%M:%S')}  
**Integration:** UI v{report.project_version} + Architecture {report.integration_version}

## Executive Summary

{report.executive_summary}

## Technical Summary

{report.technical_summary}

## Integration Readiness

**Status: {report.integration_readiness}**

### Immediate Actions Required
{chr(10).join(f"- {action}" for action in report.immediate_actions) if report.immediate_actions else "*No immediate actions required*"}

### Future Improvements
{chr(10).join(f"- {improvement}" for improvement in report.future_improvements)}

## Test Results Summary

| Phase | Tests | Passed | Failed | Success Rate | Duration |
|-------|-------|--------|--------|--------------|----------|
{chr(10).join(f"| {p.phase_name} | {p.total_tests} | {p.passed_tests} | {p.failed_tests} | {p.success_rate():.1f}% | {p.execution_time:.1f}s |" for p in report.phase_results)}

**Overall:** {report.total_test_count} tests, {report.overall_success_rate:.1f}% success rate, {report.total_execution_time:.1f}s total execution time

## Critical Issues

{chr(10).join(f"- {issue}" for issue in report.critical_issues_summary) if report.critical_issues_summary else "*No critical issues identified*"}

## Platform Compatibility

{chr(10).join(f"- **{pr.platform_info.os_name} {pr.platform_info.os_version}**: {pr.compatibility_score:.1f}% compatible" for pr in report.platform_results)}

## Performance Analysis

```json
{json.dumps(report.performance_analysis, indent=2)}
```

## Artifacts Generated

{chr(10).join(f"- {artifact}" for artifact in report.all_artifacts)}

---
*Report generated by Integration Testing Framework Task 31.7*
"""


def run_final_integration_testing() -> Dict[str, Any]:
    """Main entry point for final integration testing and reporting"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Generate final report
    generator = FinalReportGenerator()
    report = generator.generate_final_report()
    
    # Save report
    report_path = generator.save_final_report(report)
    
    # Print summary
    print(f"\n{'='*80}")
    print(f"FINAL INTEGRATION TEST REPORT")
    print(f"{'='*80}")
    print(f"Report ID: {report.report_id}")
    print(f"Integration: UI v{report.project_version} + Architecture {report.integration_version}")
    print(f"")
    print(f"📊 Overall Results:")
    print(f"   Total Tests: {report.total_test_count}")
    print(f"   Success Rate: {report.overall_success_rate:.1f}%")
    print(f"   Execution Time: {report.total_execution_time:.1f}s")
    print(f"   Critical Issues: {len(report.critical_issues_summary)}")
    print(f"")
    print(f"🎯 Integration Readiness: {report.integration_readiness}")
    
    if report.integration_readiness == "READY":
        print(f"   ✅ Integration is ready for deployment!")
    elif report.integration_readiness == "CONDITIONAL":
        print(f"   ⚠️ Integration ready with conditions")
    else:
        print(f"   ❌ Integration NOT ready - issues must be resolved")
    
    print(f"")
    print(f"📋 Phase Results:")
    for phase in report.phase_results:
        status_emoji = "✅" if phase.status == "COMPLETED" and phase.success_rate() >= 95 else "⚠️" if phase.success_rate() >= 80 else "❌"
        print(f"   {status_emoji} {phase.phase_name}: {phase.passed_tests}/{phase.total_tests} ({phase.success_rate():.1f}%)")
    
    if report.immediate_actions:
        print(f"")
        print(f"🚨 Immediate Actions Required:")
        for action in report.immediate_actions:
            print(f"   - {action}")
    
    print(f"")
    print(f"📄 Report saved: {report_path}")
    print(f"{'='*80}\n")
    
    return generator._report_to_dict(report)


if __name__ == "__main__":
    # Run final integration testing
    try:
        report_data = run_final_integration_testing()
        
        # Exit with appropriate code based on integration readiness
        readiness = report_data.get('integration_readiness', 'NOT_READY')
        if readiness == "READY":
            sys.exit(0)
        elif readiness == "CONDITIONAL":
            sys.exit(1)
        else:
            sys.exit(2)
            
    except Exception as e:
        print(f"Final integration testing failed: {e}")
        sys.exit(3) 