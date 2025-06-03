#!/usr/bin/env python3
"""
Performance Monitoring and Load Testing Framework
Task 31.5 - Performance and Load Testing for v2.0 Integration

This module provides comprehensive performance monitoring, load testing, and stress testing
capabilities for validating the integration between UI v1.2.1 and v2.0 architecture.
"""

import time
import psutil
import threading
import asyncio
import multiprocessing
import json
import sqlite3
import logging
import concurrent.futures
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Callable, Union
from dataclasses import dataclass, field, asdict
from pathlib import Path
from contextlib import contextmanager, asynccontextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics
import sys
import os
import tempfile
import queue
import requests
from unittest.mock import Mock, patch

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import our baseline metrics system
from .baseline_metrics import BaselineMetricsCollector, baseline_metrics_session, MetricType, PerformanceMetric
from .test_framework import IntegrationTestFramework, TestConfiguration, TestResult

# PyQt6 imports for UI load testing
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QThread, pyqtSignal
from PyQt6.QtTest import QTest

# Import v2.0 components for testing
try:
    from core.main_entry_orchestrator import MainEntryOrchestrator, StartupMode
    from core.adapter_integration import get_integration_framework
    from core.error_management import get_error_manager
    CORE_COMPONENTS_AVAILABLE = True
except ImportError:
    CORE_COMPONENTS_AVAILABLE = False


class LoadTestScenario:
    """Types of load test scenarios"""
    STARTUP_STRESS = "startup_stress"
    CONCURRENT_DOWNLOADS = "concurrent_downloads"  
    UI_INTERACTION_BURST = "ui_interaction_burst"
    MEMORY_PRESSURE = "memory_pressure"
    ADAPTER_STRESS = "adapter_stress"
    ERROR_RECOVERY_LOAD = "error_recovery_load"
    SUSTAINED_OPERATION = "sustained_operation"
    PEAK_USAGE_SIMULATION = "peak_usage_simulation"


@dataclass
class LoadTestConfiguration:
    """Configuration for load testing scenarios"""
    scenario_name: str
    concurrent_users: int = 1
    test_duration_seconds: float = 60.0
    ramp_up_time_seconds: float = 10.0
    ramp_down_time_seconds: float = 5.0
    
    # Operation frequencies (operations per second)
    download_frequency: float = 0.1  # 1 download per 10 seconds
    ui_interaction_frequency: float = 2.0  # 2 UI actions per second
    theme_switch_frequency: float = 0.05  # 1 theme switch per 20 seconds
    
    # Resource thresholds
    max_memory_mb: float = 200.0
    max_cpu_percent: float = 50.0
    max_response_time_ms: float = 1000.0
    
    # Error injection
    enable_error_injection: bool = False
    error_rate: float = 0.05  # 5% error rate
    
    # Monitoring settings
    monitoring_interval_ms: float = 100.0
    detailed_metrics: bool = True


@dataclass
class LoadTestMetrics:
    """Metrics collected during load testing"""
    scenario_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    
    # Performance metrics
    response_times_ms: List[float] = field(default_factory=list)
    memory_usage_mb: List[float] = field(default_factory=list)
    cpu_usage_percent: List[float] = field(default_factory=list)
    
    # Operation metrics
    successful_operations: int = 0
    failed_operations: int = 0
    total_operations: int = 0
    
    # Throughput metrics
    operations_per_second: float = 0.0
    peak_operations_per_second: float = 0.0
    
    # Error metrics
    error_count: int = 0
    error_types: Dict[str, int] = field(default_factory=dict)
    
    # Resource metrics
    peak_memory_mb: float = 0.0
    peak_cpu_percent: float = 0.0
    average_memory_mb: float = 0.0
    average_cpu_percent: float = 0.0
    
    def calculate_statistics(self):
        """Calculate performance statistics"""
        if self.response_times_ms:
            self.avg_response_time_ms = statistics.mean(self.response_times_ms)
            self.median_response_time_ms = statistics.median(self.response_times_ms)
            self.p95_response_time_ms = self._percentile(self.response_times_ms, 95)
            self.p99_response_time_ms = self._percentile(self.response_times_ms, 99)
        
        if self.memory_usage_mb:
            self.peak_memory_mb = max(self.memory_usage_mb)
            self.average_memory_mb = statistics.mean(self.memory_usage_mb)
        
        if self.cpu_usage_percent:
            self.peak_cpu_percent = max(self.cpu_usage_percent)
            self.average_cpu_percent = statistics.mean(self.cpu_usage_percent)
        
        # Calculate throughput
        duration = (self.end_time - self.start_time).total_seconds() if self.end_time else 0
        if duration > 0:
            self.operations_per_second = self.total_operations / duration
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of data"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int((percentile / 100.0) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        self.calculate_statistics()
        return asdict(self)


@dataclass
class PerformanceTestResult:
    """Result of performance testing execution"""
    test_name: str
    scenario: str
    configuration: LoadTestConfiguration
    metrics: LoadTestMetrics
    baseline_comparison: Dict[str, Any] = field(default_factory=dict)
    issues_found: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def evaluate_performance(self, baseline_targets: Dict[str, Any]) -> str:
        """Evaluate performance against baseline targets"""
        issues = []
        
        # Check response time
        if hasattr(self.metrics, 'avg_response_time_ms'):
            target_response_time = baseline_targets.get('ui_response_time', 100.0)
            if self.metrics.avg_response_time_ms > target_response_time:
                issues.append(f"Average response time {self.metrics.avg_response_time_ms:.2f}ms exceeds target {target_response_time}ms")
        
        # Check memory usage
        if self.metrics.peak_memory_mb > baseline_targets.get('max_memory_mb', 100.0):
            issues.append(f"Peak memory usage {self.metrics.peak_memory_mb:.2f}MB exceeds target")
        
        # Check CPU usage
        if self.metrics.peak_cpu_percent > baseline_targets.get('max_cpu_percent', 50.0):
            issues.append(f"Peak CPU usage {self.metrics.peak_cpu_percent:.2f}% exceeds target")
        
        # Check error rate
        error_rate = self.metrics.error_count / max(self.metrics.total_operations, 1)
        if error_rate > 0.05:  # 5% error threshold
            issues.append(f"Error rate {error_rate:.2%} exceeds 5% threshold")
        
        self.issues_found = issues
        
        if not issues:
            return "PASS"
        elif len(issues) <= 2:
            return "WARNING"
        else:
            return "FAIL"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'test_name': self.test_name,
            'scenario': self.scenario,
            'configuration': asdict(self.configuration),
            'metrics': self.metrics.to_dict(),
            'baseline_comparison': self.baseline_comparison,
            'issues_found': self.issues_found,
            'recommendations': self.recommendations
        }


class PerformanceMonitor:
    """Real-time performance monitoring system"""
    
    def __init__(self, monitoring_interval_ms: float = 100.0):
        self.monitoring_interval = monitoring_interval_ms / 1000.0
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.metrics_queue = queue.Queue()
        self.process = psutil.Process()
        
        # Metrics storage
        self.timestamps: List[datetime] = []
        self.memory_usage: List[float] = []
        self.cpu_usage: List[float] = []
        self.thread_count: List[int] = []
        
        self.logger = logging.getLogger(__name__)
    
    def start_monitoring(self):
        """Start real-time performance monitoring"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        self.logger.info("Performance monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                timestamp = datetime.now()
                memory_mb = self.process.memory_info().rss / (1024 * 1024)
                cpu_percent = self.process.cpu_percent()
                thread_count = self.process.num_threads()
                
                self.timestamps.append(timestamp)
                self.memory_usage.append(memory_mb)
                self.cpu_usage.append(cpu_percent)
                self.thread_count.append(thread_count)
                
                # Add to queue for real-time access
                self.metrics_queue.put({
                    'timestamp': timestamp,
                    'memory_mb': memory_mb,
                    'cpu_percent': cpu_percent,
                    'thread_count': thread_count
                })
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")
                break
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        if not self.memory_usage:
            return {}
        
        return {
            'current_memory_mb': self.memory_usage[-1],
            'current_cpu_percent': self.cpu_usage[-1],
            'current_thread_count': self.thread_count[-1],
            'peak_memory_mb': max(self.memory_usage),
            'peak_cpu_percent': max(self.cpu_usage),
            'average_memory_mb': statistics.mean(self.memory_usage),
            'average_cpu_percent': statistics.mean(self.cpu_usage),
            'monitoring_duration_seconds': len(self.memory_usage) * self.monitoring_interval
        }
    
    def get_metrics_history(self) -> Dict[str, List]:
        """Get complete metrics history"""
        return {
            'timestamps': [t.isoformat() for t in self.timestamps],
            'memory_usage_mb': self.memory_usage.copy(),
            'cpu_usage_percent': self.cpu_usage.copy(),
            'thread_count': self.thread_count.copy()
        }


class LoadTestExecutor:
    """Executes various load testing scenarios"""
    
    def __init__(self, test_framework: IntegrationTestFramework = None):
        self.test_framework = test_framework or IntegrationTestFramework()
        self.performance_monitor = PerformanceMonitor()
        self.logger = logging.getLogger(__name__)
        
        # Test state
        self.active_tests: Dict[str, Any] = {}
        self.test_results: List[PerformanceTestResult] = []
        
        # Mock data for testing
        self.mock_video_urls = [
            "https://example.com/video1.mp4",
            "https://example.com/video2.mp4", 
            "https://example.com/video3.mp4",
            "https://example.com/video4.mp4",
            "https://example.com/video5.mp4"
        ]
    
    def execute_startup_stress_test(self, config: LoadTestConfiguration) -> PerformanceTestResult:
        """Test rapid application startup/shutdown cycles"""
        self.logger.info(f"Starting startup stress test with {config.concurrent_users} concurrent startups")
        
        metrics = LoadTestMetrics(
            scenario_name=config.scenario_name,
            start_time=datetime.now()
        )
        
        self.performance_monitor.start_monitoring()
        
        try:
            startup_times = []
            
            for cycle in range(config.concurrent_users):
                start_time = time.perf_counter()
                
                try:
                    # Simulate startup process
                    with self.test_framework.test_session(f"startup_stress_{cycle}"):
                        # Test main entry point startup
                        result = self.test_framework.test_main_entry_point_startup()
                        
                        startup_duration = (time.perf_counter() - start_time) * 1000
                        startup_times.append(startup_duration)
                        
                        if result.status == "PASS":
                            metrics.successful_operations += 1
                        else:
                            metrics.failed_operations += 1
                            metrics.error_count += 1
                            error_type = result.error_message or "startup_failure"
                            metrics.error_types[error_type] = metrics.error_types.get(error_type, 0) + 1
                        
                        metrics.total_operations += 1
                        
                except Exception as e:
                    self.logger.error(f"Startup stress test cycle {cycle} failed: {e}")
                    metrics.failed_operations += 1
                    metrics.error_count += 1
                    metrics.error_types["exception"] = metrics.error_types.get("exception", 0) + 1
                    metrics.total_operations += 1
                
                # Brief pause between cycles
                time.sleep(0.1)
            
            metrics.response_times_ms = startup_times
            
        finally:
            self.performance_monitor.stop_monitoring()
            metrics.end_time = datetime.now()
        
        # Get performance data
        perf_data = self.performance_monitor.get_current_metrics()
        metrics.memory_usage_mb = self.performance_monitor.memory_usage.copy()
        metrics.cpu_usage_percent = self.performance_monitor.cpu_usage.copy()
        
        # Create result
        result = PerformanceTestResult(
            test_name="startup_stress_test",
            scenario=config.scenario_name,
            configuration=config,
            metrics=metrics
        )
        
        # Evaluate performance
        baseline_targets = {
            'ui_response_time': 400.0,  # Allow 400ms for startup under stress
            'max_memory_mb': config.max_memory_mb,
            'max_cpu_percent': config.max_cpu_percent
        }
        result.evaluate_performance(baseline_targets)
        
        self.test_results.append(result)
        return result
    
    def execute_concurrent_downloads_test(self, config: LoadTestConfiguration) -> PerformanceTestResult:
        """Test concurrent download operations"""
        self.logger.info(f"Starting concurrent downloads test with {config.concurrent_users} concurrent downloads")
        
        metrics = LoadTestMetrics(
            scenario_name=config.scenario_name,
            start_time=datetime.now()
        )
        
        self.performance_monitor.start_monitoring()
        
        try:
            download_times = []
            
            def simulate_download(download_id: int) -> Tuple[bool, float]:
                """Simulate a download operation"""
                start_time = time.perf_counter()
                
                try:
                    # Simulate download process
                    video_url = self.mock_video_urls[download_id % len(self.mock_video_urls)]
                    
                    # Simulate network delay
                    time.sleep(0.1 + (download_id * 0.01))  # Variable delay
                    
                    # Simulate processing
                    time.sleep(0.05)
                    
                    duration = (time.perf_counter() - start_time) * 1000
                    return True, duration
                    
                except Exception as e:
                    duration = (time.perf_counter() - start_time) * 1000
                    self.logger.error(f"Download {download_id} failed: {e}")
                    return False, duration
            
            # Execute concurrent downloads
            with ThreadPoolExecutor(max_workers=config.concurrent_users) as executor:
                futures = []
                for i in range(config.concurrent_users):
                    future = executor.submit(simulate_download, i)
                    futures.append(future)
                
                for future in as_completed(futures):
                    success, duration = future.result()
                    download_times.append(duration)
                    
                    if success:
                        metrics.successful_operations += 1
                    else:
                        metrics.failed_operations += 1
                        metrics.error_count += 1
                        metrics.error_types["download_failure"] = metrics.error_types.get("download_failure", 0) + 1
                    
                    metrics.total_operations += 1
            
            metrics.response_times_ms = download_times
            
        finally:
            self.performance_monitor.stop_monitoring()
            metrics.end_time = datetime.now()
        
        # Get performance data
        metrics.memory_usage_mb = self.performance_monitor.memory_usage.copy()
        metrics.cpu_usage_percent = self.performance_monitor.cpu_usage.copy()
        
        # Create result
        result = PerformanceTestResult(
            test_name="concurrent_downloads_test",
            scenario=config.scenario_name,
            configuration=config,
            metrics=metrics
        )
        
        # Evaluate performance
        baseline_targets = {
            'ui_response_time': 200.0,  # 200ms for download operations
            'max_memory_mb': config.max_memory_mb,
            'max_cpu_percent': config.max_cpu_percent
        }
        result.evaluate_performance(baseline_targets)
        
        self.test_results.append(result)
        return result
    
    def execute_ui_interaction_burst_test(self, config: LoadTestConfiguration) -> PerformanceTestResult:
        """Test rapid UI interactions"""
        self.logger.info(f"Starting UI interaction burst test")
        
        metrics = LoadTestMetrics(
            scenario_name=config.scenario_name,
            start_time=datetime.now()
        )
        
        self.performance_monitor.start_monitoring()
        
        try:
            interaction_times = []
            
            # Simulate rapid UI interactions
            test_duration = config.test_duration_seconds
            interaction_interval = 1.0 / config.ui_interaction_frequency
            
            end_time = time.time() + test_duration
            
            while time.time() < end_time:
                start_time = time.perf_counter()
                
                try:
                    # Simulate UI interactions
                    actions = [
                        "tab_switch",
                        "theme_change",
                        "menu_click",
                        "button_click",
                        "text_input"
                    ]
                    
                    action = actions[metrics.total_operations % len(actions)]
                    
                    # Simulate action processing time
                    if action == "theme_change":
                        time.sleep(0.01)  # Theme changes take slightly longer
                    else:
                        time.sleep(0.005)  # Quick UI actions
                    
                    duration = (time.perf_counter() - start_time) * 1000
                    interaction_times.append(duration)
                    
                    metrics.successful_operations += 1
                    metrics.total_operations += 1
                    
                except Exception as e:
                    duration = (time.perf_counter() - start_time) * 1000
                    interaction_times.append(duration)
                    
                    metrics.failed_operations += 1
                    metrics.error_count += 1
                    metrics.error_types["ui_interaction_failure"] = metrics.error_types.get("ui_interaction_failure", 0) + 1
                    metrics.total_operations += 1
                
                # Wait for next interaction
                time.sleep(interaction_interval)
            
            metrics.response_times_ms = interaction_times
            
        finally:
            self.performance_monitor.stop_monitoring()
            metrics.end_time = datetime.now()
        
        # Get performance data
        metrics.memory_usage_mb = self.performance_monitor.memory_usage.copy()
        metrics.cpu_usage_percent = self.performance_monitor.cpu_usage.copy()
        
        # Create result
        result = PerformanceTestResult(
            test_name="ui_interaction_burst_test",
            scenario=config.scenario_name,
            configuration=config,
            metrics=metrics
        )
        
        # Evaluate performance
        baseline_targets = {
            'ui_response_time': 50.0,  # 50ms for UI interactions
            'max_memory_mb': config.max_memory_mb,
            'max_cpu_percent': config.max_cpu_percent
        }
        result.evaluate_performance(baseline_targets)
        
        self.test_results.append(result)
        return result
    
    def execute_memory_pressure_test(self, config: LoadTestConfiguration) -> PerformanceTestResult:
        """Test system behavior under memory pressure"""
        self.logger.info(f"Starting memory pressure test")
        
        metrics = LoadTestMetrics(
            scenario_name=config.scenario_name,
            start_time=datetime.now()
        )
        
        self.performance_monitor.start_monitoring()
        
        try:
            # Simulate memory pressure by creating large data structures
            memory_allocations = []
            
            test_duration = config.test_duration_seconds
            end_time = time.time() + test_duration
            
            while time.time() < end_time:
                start_time = time.perf_counter()
                
                try:
                    # Allocate memory (simulate loading large video metadata)
                    allocation_size = 1024 * 1024  # 1MB chunks
                    data = bytearray(allocation_size)
                    memory_allocations.append(data)
                    
                    # Simulate some processing
                    time.sleep(0.01)
                    
                    # Periodically release some memory
                    if len(memory_allocations) > 50:  # Keep around 50MB allocated
                        memory_allocations.pop(0)
                    
                    duration = (time.perf_counter() - start_time) * 1000
                    metrics.response_times_ms.append(duration)
                    
                    metrics.successful_operations += 1
                    metrics.total_operations += 1
                    
                    # Check if we're approaching memory limits
                    current_memory = self.performance_monitor.process.memory_info().rss / (1024 * 1024)
                    if current_memory > config.max_memory_mb:
                        self.logger.warning(f"Memory usage {current_memory:.2f}MB exceeds limit {config.max_memory_mb}MB")
                        break
                    
                except Exception as e:
                    self.logger.error(f"Memory pressure test error: {e}")
                    metrics.failed_operations += 1
                    metrics.error_count += 1
                    metrics.error_types["memory_error"] = metrics.error_types.get("memory_error", 0) + 1
                    metrics.total_operations += 1
                
                time.sleep(0.1)  # Brief pause
            
        finally:
            # Cleanup memory allocations
            memory_allocations.clear()
            
            self.performance_monitor.stop_monitoring()
            metrics.end_time = datetime.now()
        
        # Get performance data
        metrics.memory_usage_mb = self.performance_monitor.memory_usage.copy()
        metrics.cpu_usage_percent = self.performance_monitor.cpu_usage.copy()
        
        # Create result
        result = PerformanceTestResult(
            test_name="memory_pressure_test",
            scenario=config.scenario_name,
            configuration=config,
            metrics=metrics
        )
        
        # Evaluate performance
        baseline_targets = {
            'ui_response_time': 100.0,
            'max_memory_mb': config.max_memory_mb,
            'max_cpu_percent': config.max_cpu_percent
        }
        result.evaluate_performance(baseline_targets)
        
        self.test_results.append(result)
        return result
    
    def execute_sustained_operation_test(self, config: LoadTestConfiguration) -> PerformanceTestResult:
        """Test system stability over extended operation"""
        self.logger.info(f"Starting sustained operation test for {config.test_duration_seconds} seconds")
        
        metrics = LoadTestMetrics(
            scenario_name=config.scenario_name,
            start_time=datetime.now()
        )
        
        self.performance_monitor.start_monitoring()
        
        try:
            operation_times = []
            
            # Run sustained operations
            test_duration = config.test_duration_seconds
            end_time = time.time() + test_duration
            
            while time.time() < end_time:
                start_time = time.perf_counter()
                
                try:
                    # Mix of operations to simulate real usage
                    operation_type = metrics.total_operations % 4
                    
                    if operation_type == 0:
                        # Simulate download check
                        time.sleep(0.02)
                    elif operation_type == 1:
                        # Simulate UI update
                        time.sleep(0.005)
                    elif operation_type == 2:
                        # Simulate file operation
                        time.sleep(0.015)
                    else:
                        # Simulate network request
                        time.sleep(0.03)
                    
                    duration = (time.perf_counter() - start_time) * 1000
                    operation_times.append(duration)
                    
                    metrics.successful_operations += 1
                    metrics.total_operations += 1
                    
                except Exception as e:
                    duration = (time.perf_counter() - start_time) * 1000
                    operation_times.append(duration)
                    
                    self.logger.error(f"Sustained operation error: {e}")
                    metrics.failed_operations += 1
                    metrics.error_count += 1
                    metrics.error_types["operation_error"] = metrics.error_types.get("operation_error", 0) + 1
                    metrics.total_operations += 1
                
                # Variable pause to simulate real usage patterns
                pause_time = 0.1 + (0.05 * (metrics.total_operations % 10))  # 0.1-0.6s pause
                time.sleep(pause_time)
            
            metrics.response_times_ms = operation_times
            
        finally:
            self.performance_monitor.stop_monitoring()
            metrics.end_time = datetime.now()
        
        # Get performance data
        metrics.memory_usage_mb = self.performance_monitor.memory_usage.copy()
        metrics.cpu_usage_percent = self.performance_monitor.cpu_usage.copy()
        
        # Create result
        result = PerformanceTestResult(
            test_name="sustained_operation_test",
            scenario=config.scenario_name,
            configuration=config,
            metrics=metrics
        )
        
        # Evaluate performance
        baseline_targets = {
            'ui_response_time': 100.0,
            'max_memory_mb': config.max_memory_mb,
            'max_cpu_percent': config.max_cpu_percent
        }
        result.evaluate_performance(baseline_targets)
        
        self.test_results.append(result)
        return result
    
    def execute_load_test_scenario(self, config: LoadTestConfiguration) -> PerformanceTestResult:
        """Execute a specific load test scenario"""
        scenario_map = {
            LoadTestScenario.STARTUP_STRESS: self.execute_startup_stress_test,
            LoadTestScenario.CONCURRENT_DOWNLOADS: self.execute_concurrent_downloads_test,
            LoadTestScenario.UI_INTERACTION_BURST: self.execute_ui_interaction_burst_test,
            LoadTestScenario.MEMORY_PRESSURE: self.execute_memory_pressure_test,
            LoadTestScenario.SUSTAINED_OPERATION: self.execute_sustained_operation_test
        }
        
        test_method = scenario_map.get(config.scenario_name)
        if not test_method:
            raise ValueError(f"Unknown load test scenario: {config.scenario_name}")
        
        self.logger.info(f"Executing load test scenario: {config.scenario_name}")
        result = test_method(config)
        
        self.logger.info(f"Load test scenario {config.scenario_name} completed")
        return result
    
    def run_comprehensive_load_test_suite(self) -> List[PerformanceTestResult]:
        """Run complete suite of load tests"""
        self.logger.info("Starting comprehensive load test suite")
        
        test_configs = [
            # Startup stress test
            LoadTestConfiguration(
                scenario_name=LoadTestScenario.STARTUP_STRESS,
                concurrent_users=5,
                test_duration_seconds=30.0,
                max_memory_mb=150.0,
                max_cpu_percent=80.0
            ),
            
            # Concurrent downloads test
            LoadTestConfiguration(
                scenario_name=LoadTestScenario.CONCURRENT_DOWNLOADS,
                concurrent_users=3,
                test_duration_seconds=60.0,
                max_memory_mb=200.0,
                max_cpu_percent=60.0
            ),
            
            # UI interaction burst test
            LoadTestConfiguration(
                scenario_name=LoadTestScenario.UI_INTERACTION_BURST,
                ui_interaction_frequency=5.0,  # 5 interactions per second
                test_duration_seconds=30.0,
                max_memory_mb=120.0,
                max_cpu_percent=40.0
            ),
            
            # Memory pressure test
            LoadTestConfiguration(
                scenario_name=LoadTestScenario.MEMORY_PRESSURE,
                test_duration_seconds=60.0,
                max_memory_mb=250.0,  # Allow higher memory for pressure test
                max_cpu_percent=50.0
            ),
            
            # Sustained operation test
            LoadTestConfiguration(
                scenario_name=LoadTestScenario.SUSTAINED_OPERATION,
                test_duration_seconds=120.0,  # 2 minute sustained test
                max_memory_mb=150.0,
                max_cpu_percent=30.0
            )
        ]
        
        results = []
        
        for config in test_configs:
            try:
                result = self.execute_load_test_scenario(config)
                results.append(result)
                
                # Brief pause between tests
                time.sleep(5.0)
                
            except Exception as e:
                self.logger.error(f"Load test {config.scenario_name} failed: {e}")
                # Continue with other tests
        
        self.logger.info(f"Comprehensive load test suite completed: {len(results)} tests executed")
        return results
    
    def generate_performance_report(self, results: List[PerformanceTestResult]) -> Dict[str, Any]:
        """Generate comprehensive performance test report"""
        if not results:
            return {"error": "No test results to report"}
        
        report = {
            "summary": {
                "total_tests": len(results),
                "passed_tests": len([r for r in results if r.evaluate_performance({}) == "PASS"]),
                "warning_tests": len([r for r in results if r.evaluate_performance({}) == "WARNING"]),
                "failed_tests": len([r for r in results if r.evaluate_performance({}) == "FAIL"]),
                "test_execution_time": datetime.now().isoformat(),
                "total_operations": sum(r.metrics.total_operations for r in results),
                "total_errors": sum(r.metrics.error_count for r in results)
            },
            "detailed_results": [r.to_dict() for r in results],
            "performance_analysis": {
                "average_response_time_ms": statistics.mean([
                    getattr(r.metrics, 'avg_response_time_ms', 0) for r in results if hasattr(r.metrics, 'avg_response_time_ms')
                ]) if results else 0,
                "peak_memory_usage_mb": max([r.metrics.peak_memory_mb for r in results]),
                "peak_cpu_usage_percent": max([r.metrics.peak_cpu_percent for r in results]),
                "overall_error_rate": sum(r.metrics.error_count for r in results) / max(sum(r.metrics.total_operations for r in results), 1)
            },
            "recommendations": self._generate_performance_recommendations(results)
        }
        
        return report
    
    def _generate_performance_recommendations(self, results: List[PerformanceTestResult]) -> List[str]:
        """Generate performance improvement recommendations"""
        recommendations = []
        
        # Analyze response times
        avg_response_times = [getattr(r.metrics, 'avg_response_time_ms', 0) for r in results if hasattr(r.metrics, 'avg_response_time_ms')]
        if avg_response_times and max(avg_response_times) > 200:
            recommendations.append("Consider optimizing UI response times - some operations exceed 200ms")
        
        # Analyze memory usage
        peak_memories = [r.metrics.peak_memory_mb for r in results]
        if peak_memories and max(peak_memories) > 200:
            recommendations.append("Monitor memory usage - peak consumption exceeds 200MB")
        
        # Analyze error rates
        total_operations = sum(r.metrics.total_operations for r in results)
        total_errors = sum(r.metrics.error_count for r in results)
        if total_operations > 0 and (total_errors / total_operations) > 0.05:
            recommendations.append("Error rate exceeds 5% - investigate error handling mechanisms")
        
        # Analyze CPU usage
        peak_cpu_usage = [r.metrics.peak_cpu_percent for r in results]
        if peak_cpu_usage and max(peak_cpu_usage) > 70:
            recommendations.append("CPU usage spikes detected - consider optimizing compute-intensive operations")
        
        if not recommendations:
            recommendations.append("Performance metrics are within acceptable ranges")
        
        return recommendations
    
    def save_performance_report(self, report: Dict[str, Any], output_path: Path = None) -> Path:
        """Save performance test report to file"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path(f"tests/reports/performance_test_report_{timestamp}.json")
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save as JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"Performance test report saved to: {output_path}")
        return output_path


def run_performance_test_suite(config: TestConfiguration = None) -> Dict[str, Any]:
    """Main entry point for performance testing"""
    # Setup test framework
    test_framework = IntegrationTestFramework(config or TestConfiguration())
    
    # Create load test executor
    executor = LoadTestExecutor(test_framework)
    
    # Run comprehensive load tests
    results = executor.run_comprehensive_load_test_suite()
    
    # Generate and save report
    report = executor.generate_performance_report(results)
    report_path = executor.save_performance_report(report)
    
    print(f"\n{'='*60}")
    print(f"PERFORMANCE TEST SUITE COMPLETED")
    print(f"{'='*60}")
    print(f"Total Tests: {report['summary']['total_tests']}")
    print(f"Passed: {report['summary']['passed_tests']}")
    print(f"Warning: {report['summary']['warning_tests']}")
    print(f"Failed: {report['summary']['failed_tests']}")
    print(f"Total Operations: {report['summary']['total_operations']}")
    print(f"Total Errors: {report['summary']['total_errors']}")
    print(f"Peak Memory: {report['performance_analysis']['peak_memory_usage_mb']:.2f}MB")
    print(f"Peak CPU: {report['performance_analysis']['peak_cpu_usage_percent']:.2f}%")
    print(f"Report: {report_path}")
    print(f"{'='*60}\n")
    
    return report


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run performance tests
    try:
        report = run_performance_test_suite()
        
        # Print recommendations
        print("Performance Recommendations:")
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"  {i}. {rec}")
        
        # Exit with appropriate code
        failed_tests = report['summary']['failed_tests']
        sys.exit(0 if failed_tests == 0 else 1)
        
    except Exception as e:
        print(f"Performance test execution failed: {e}")
        sys.exit(2) 