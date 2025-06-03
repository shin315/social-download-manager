#!/usr/bin/env python3
"""
Baseline Metrics and Performance Criteria for v2.0 Integration Testing

This module defines and captures baseline performance metrics for validating
the integration between UI v1.2.1 and v2.0 architecture through Task 29 adapters
and Task 30 main entry point orchestration.
"""

import time
import psutil
import threading
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, NamedTuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from contextlib import contextmanager
import logging
import os
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6.QtWidgets import QApplication
from core.constants import AppConstants
from version import get_version_info


class MetricType:
    """Types of metrics we track"""
    STARTUP = "startup"
    RUNTIME = "runtime"
    MEMORY = "memory"
    UI_RESPONSE = "ui_response"
    ADAPTER_PERFORMANCE = "adapter_performance"
    ERROR_RECOVERY = "error_recovery"
    SHUTDOWN = "shutdown"


@dataclass
class BaselineTarget:
    """Baseline performance target with tolerance"""
    metric_name: str
    target_value: float
    unit: str
    tolerance_percent: float = 10.0  # Allow 10% variance by default
    critical_threshold: float = None  # Value that triggers failure
    warning_threshold: float = None   # Value that triggers warning
    
    def __post_init__(self):
        if self.critical_threshold is None:
            self.critical_threshold = self.target_value * (1 + self.tolerance_percent / 100)
        if self.warning_threshold is None:
            self.warning_threshold = self.target_value * (1 + self.tolerance_percent / 200)  # 5% by default
    
    def evaluate(self, actual_value: float) -> Tuple[str, str]:
        """Evaluate actual value against baseline target"""
        if actual_value <= self.target_value:
            return "PASS", f"✅ {actual_value:.2f}{self.unit} (Target: {self.target_value:.2f}{self.unit})"
        elif actual_value <= self.warning_threshold:
            return "WARNING", f"⚠️ {actual_value:.2f}{self.unit} (Target: {self.target_value:.2f}{self.unit})"
        elif actual_value <= self.critical_threshold:
            return "CRITICAL", f"❌ {actual_value:.2f}{self.unit} (Target: {self.target_value:.2f}{self.unit})"
        else:
            return "FAIL", f"💥 {actual_value:.2f}{self.unit} (Target: {self.target_value:.2f}{self.unit})"


@dataclass
class PerformanceMetric:
    """Individual performance metric measurement"""
    name: str
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)
    component: str = "unknown"
    metric_type: str = MetricType.RUNTIME
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'value': self.value,
            'unit': self.unit,
            'timestamp': self.timestamp.isoformat(),
            'component': self.component,
            'metric_type': self.metric_type,
            'context': self.context
        }


@dataclass
class BaselineMetricsReport:
    """Complete baseline metrics report"""
    test_session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    
    # Collected metrics
    startup_metrics: List[PerformanceMetric] = field(default_factory=list)
    runtime_metrics: List[PerformanceMetric] = field(default_factory=list)
    memory_metrics: List[PerformanceMetric] = field(default_factory=list)
    ui_response_metrics: List[PerformanceMetric] = field(default_factory=list)
    adapter_metrics: List[PerformanceMetric] = field(default_factory=list)
    error_recovery_metrics: List[PerformanceMetric] = field(default_factory=list)
    shutdown_metrics: List[PerformanceMetric] = field(default_factory=list)
    
    # Summary statistics
    summary: Dict[str, Any] = field(default_factory=dict)
    
    # Baseline comparisons
    baseline_evaluations: Dict[str, Tuple[str, str]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'test_session_id': self.test_session_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'startup_metrics': [m.to_dict() for m in self.startup_metrics],
            'runtime_metrics': [m.to_dict() for m in self.runtime_metrics],
            'memory_metrics': [m.to_dict() for m in self.memory_metrics],
            'ui_response_metrics': [m.to_dict() for m in self.ui_response_metrics],
            'adapter_metrics': [m.to_dict() for m in self.adapter_metrics],
            'error_recovery_metrics': [m.to_dict() for m in self.error_recovery_metrics],
            'shutdown_metrics': [m.to_dict() for m in self.shutdown_metrics],
            'summary': self.summary,
            'baseline_evaluations': self.baseline_evaluations
        }


class BaselineMetricsCollector:
    """Collects and manages baseline performance metrics"""
    
    def __init__(self, test_session_id: str = None):
        self.test_session_id = test_session_id or f"baseline_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.start_time = datetime.now()
        
        # Setup logging
        self.logger = logging.getLogger(f"baseline_metrics_{self.test_session_id}")
        
        # Metrics storage
        self.metrics: List[PerformanceMetric] = []
        self.continuous_monitors: Dict[str, threading.Thread] = {}
        self.monitor_stop_events: Dict[str, threading.Event] = {}
        
        # Baseline targets from Task 30 requirements
        self.baseline_targets = self._create_baseline_targets()
        
        # System info
        self.system_info = self._gather_system_info()
        
        # Process monitoring
        self.process = psutil.Process()
        
    def _create_baseline_targets(self) -> Dict[str, BaselineTarget]:
        """Create baseline targets based on Task 30 requirements"""
        return {
            # Task 30.1 Startup Performance Targets
            "total_startup_time": BaselineTarget(
                metric_name="total_startup_time",
                target_value=250.0,  # <250ms from Task 30.1
                unit="ms",
                tolerance_percent=20.0,  # Allow 20% variance for startup
                critical_threshold=400.0  # Hard fail at 400ms
            ),
            
            "initial_memory_usage": BaselineTarget(
                metric_name="initial_memory_usage",
                target_value=48.0,  # <48MB from Task 30.1
                unit="MB",
                tolerance_percent=15.0,
                critical_threshold=60.0  # Hard fail at 60MB
            ),
            
            "startup_cpu_peak": BaselineTarget(
                metric_name="startup_cpu_peak",
                target_value=80.0,  # <80% CPU during startup
                unit="%",
                tolerance_percent=25.0,
                critical_threshold=95.0
            ),
            
            # Runtime Performance Targets
            "ui_response_time": BaselineTarget(
                metric_name="ui_response_time",
                target_value=100.0,  # <100ms for UI actions
                unit="ms",
                tolerance_percent=50.0,  # UI can be more variable
                critical_threshold=300.0
            ),
            
            "adapter_overhead": BaselineTarget(
                metric_name="adapter_overhead",
                target_value=5.0,  # <5% overhead vs direct v1.2.1
                unit="%",
                tolerance_percent=100.0,  # Allow double for safety
                critical_threshold=15.0  # Hard fail at 15%
            ),
            
            "memory_stability": BaselineTarget(
                metric_name="memory_stability",
                target_value=5.0,  # <5MB growth over 30 minutes
                unit="MB",
                tolerance_percent=200.0,
                critical_threshold=20.0  # Hard fail at 20MB growth
            ),
            
            # Error Recovery Performance
            "error_recovery_time": BaselineTarget(
                metric_name="error_recovery_time",
                target_value=1000.0,  # <1s for non-critical errors
                unit="ms",
                tolerance_percent=100.0,
                critical_threshold=5000.0  # Hard fail at 5s
            ),
            
            # Shutdown Performance
            "shutdown_time": BaselineTarget(
                metric_name="shutdown_time",
                target_value=2000.0,  # <2s for graceful shutdown
                unit="ms",
                tolerance_percent=150.0,
                critical_threshold=10000.0  # Hard fail at 10s
            )
        }
    
    def _gather_system_info(self) -> Dict[str, Any]:
        """Gather system information for context"""
        return {
            'platform': sys.platform,
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            'cpu_count': psutil.cpu_count(),
            'total_memory_gb': psutil.virtual_memory().total / (1024**3),
            'available_memory_gb': psutil.virtual_memory().available / (1024**3),
            'disk_usage_percent': psutil.disk_usage('/').percent if sys.platform != 'win32' else psutil.disk_usage('C:').percent,
            'app_version': get_version_info().get('version', 'unknown')
        }
    
    def record_metric(self, name: str, value: float, unit: str, 
                     component: str = "unknown", metric_type: str = MetricType.RUNTIME,
                     context: Dict[str, Any] = None) -> None:
        """Record a performance metric"""
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            component=component,
            metric_type=metric_type,
            context=context or {}
        )
        
        self.metrics.append(metric)
        self.logger.debug(f"Recorded metric: {name} = {value}{unit} ({component})")
    
    @contextmanager
    def measure_startup_phase(self, phase_name: str, component: str = "main_orchestrator"):
        """Context manager to measure startup phase timing"""
        start_time = time.perf_counter()
        start_memory = self.process.memory_info().rss / (1024 * 1024)  # MB
        
        self.logger.info(f"Starting startup phase: {phase_name}")
        
        try:
            yield
            
            # Successful completion
            duration_ms = (time.perf_counter() - start_time) * 1000
            end_memory = self.process.memory_info().rss / (1024 * 1024)
            memory_delta = end_memory - start_memory
            
            self.record_metric(
                name=f"{phase_name}_duration",
                value=duration_ms,
                unit="ms",
                component=component,
                metric_type=MetricType.STARTUP,
                context={'phase': phase_name, 'memory_delta_mb': memory_delta}
            )
            
            self.logger.info(f"Completed startup phase: {phase_name} in {duration_ms:.2f}ms")
            
        except Exception as e:
            # Failed completion
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            self.record_metric(
                name=f"{phase_name}_failure_duration",
                value=duration_ms,
                unit="ms",
                component=component,
                metric_type=MetricType.STARTUP,
                context={'phase': phase_name, 'error': str(e)}
            )
            
            self.logger.error(f"Failed startup phase: {phase_name} after {duration_ms:.2f}ms: {e}")
            raise
    
    @contextmanager  
    def measure_ui_response(self, action_name: str, component: str = "ui"):
        """Context manager to measure UI response time"""
        start_time = time.perf_counter()
        
        try:
            yield
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            self.record_metric(
                name="ui_action_response_time",
                value=duration_ms,
                unit="ms",
                component=component,
                metric_type=MetricType.UI_RESPONSE,
                context={'action': action_name}
            )
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            self.record_metric(
                name="ui_action_failure_time",
                value=duration_ms,
                unit="ms",
                component=component,
                metric_type=MetricType.UI_RESPONSE,
                context={'action': action_name, 'error': str(e)}
            )
            raise
    
    @contextmanager
    def measure_adapter_performance(self, adapter_name: str, operation: str = "unknown"):
        """Context manager to measure adapter performance"""
        start_time = time.perf_counter()
        start_memory = self.process.memory_info().rss / (1024 * 1024)
        
        try:
            yield
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            end_memory = self.process.memory_info().rss / (1024 * 1024)
            memory_delta = end_memory - start_memory
            
            self.record_metric(
                name="adapter_operation_time",
                value=duration_ms,
                unit="ms",
                component=adapter_name,
                metric_type=MetricType.ADAPTER_PERFORMANCE,
                context={'operation': operation, 'memory_delta_mb': memory_delta}
            )
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            self.record_metric(
                name="adapter_operation_failure_time",
                value=duration_ms,
                unit="ms",
                component=adapter_name,
                metric_type=MetricType.ADAPTER_PERFORMANCE,
                context={'operation': operation, 'error': str(e)}
            )
            raise
    
    def start_continuous_memory_monitoring(self, interval_seconds: float = 5.0):
        """Start continuous memory usage monitoring"""
        stop_event = threading.Event()
        self.monitor_stop_events["memory"] = stop_event
        
        def monitor_memory():
            while not stop_event.is_set():
                try:
                    memory_mb = self.process.memory_info().rss / (1024 * 1024)
                    cpu_percent = self.process.cpu_percent()
                    
                    self.record_metric(
                        name="memory_usage",
                        value=memory_mb,
                        unit="MB",
                        component="system",
                        metric_type=MetricType.MEMORY,
                        context={'cpu_percent': cpu_percent}
                    )
                    
                    stop_event.wait(interval_seconds)
                    
                except Exception as e:
                    self.logger.error(f"Memory monitoring error: {e}")
                    break
        
        thread = threading.Thread(target=monitor_memory, daemon=True)
        thread.start()
        self.continuous_monitors["memory"] = thread
        
        self.logger.info("Started continuous memory monitoring")
    
    def stop_continuous_monitoring(self):
        """Stop all continuous monitoring threads"""
        for name, stop_event in self.monitor_stop_events.items():
            stop_event.set()
            self.logger.info(f"Stopped {name} monitoring")
        
        # Wait for threads to finish
        for name, thread in self.continuous_monitors.items():
            thread.join(timeout=5.0)
            if thread.is_alive():
                self.logger.warning(f"Thread {name} did not stop gracefully")
        
        self.continuous_monitors.clear()
        self.monitor_stop_events.clear()
    
    def generate_baseline_report(self) -> BaselineMetricsReport:
        """Generate comprehensive baseline metrics report"""
        end_time = datetime.now()
        
        # Categorize metrics
        report = BaselineMetricsReport(
            test_session_id=self.test_session_id,
            start_time=self.start_time,
            end_time=end_time
        )
        
        # Sort metrics by type
        for metric in self.metrics:
            if metric.metric_type == MetricType.STARTUP:
                report.startup_metrics.append(metric)
            elif metric.metric_type == MetricType.RUNTIME:
                report.runtime_metrics.append(metric)
            elif metric.metric_type == MetricType.MEMORY:
                report.memory_metrics.append(metric)
            elif metric.metric_type == MetricType.UI_RESPONSE:
                report.ui_response_metrics.append(metric)
            elif metric.metric_type == MetricType.ADAPTER_PERFORMANCE:
                report.adapter_metrics.append(metric)
            elif metric.metric_type == MetricType.ERROR_RECOVERY:
                report.error_recovery_metrics.append(metric)
            elif metric.metric_type == MetricType.SHUTDOWN:
                report.shutdown_metrics.append(metric)
        
        # Generate summary statistics
        report.summary = self._generate_summary_statistics()
        
        # Evaluate against baseline targets
        report.baseline_evaluations = self._evaluate_against_baselines()
        
        return report
    
    def _generate_summary_statistics(self) -> Dict[str, Any]:
        """Generate summary statistics from collected metrics"""
        stats = {
            'total_metrics_collected': len(self.metrics),
            'test_duration_seconds': (datetime.now() - self.start_time).total_seconds(),
            'system_info': self.system_info
        }
        
        # Calculate key aggregated metrics
        startup_times = [m.value for m in self.metrics if 'startup' in m.name and 'duration' in m.name]
        if startup_times:
            stats['total_startup_time_ms'] = sum(startup_times)
            stats['average_phase_time_ms'] = sum(startup_times) / len(startup_times)
        
        memory_metrics = [m.value for m in self.metrics if m.metric_type == MetricType.MEMORY]
        if memory_metrics:
            stats['initial_memory_mb'] = memory_metrics[0] if memory_metrics else 0
            stats['peak_memory_mb'] = max(memory_metrics)
            stats['memory_growth_mb'] = max(memory_metrics) - memory_metrics[0] if len(memory_metrics) > 1 else 0
        
        ui_response_times = [m.value for m in self.metrics if m.metric_type == MetricType.UI_RESPONSE and 'failure' not in m.name]
        if ui_response_times:
            stats['average_ui_response_ms'] = sum(ui_response_times) / len(ui_response_times)
            stats['max_ui_response_ms'] = max(ui_response_times)
        
        adapter_times = [m.value for m in self.metrics if m.metric_type == MetricType.ADAPTER_PERFORMANCE and 'failure' not in m.name]
        if adapter_times:
            stats['average_adapter_time_ms'] = sum(adapter_times) / len(adapter_times)
            stats['total_adapter_operations'] = len(adapter_times)
        
        return stats
    
    def _evaluate_against_baselines(self) -> Dict[str, Tuple[str, str]]:
        """Evaluate collected metrics against baseline targets"""
        evaluations = {}
        
        # Get summary for evaluation
        summary = self._generate_summary_statistics()
        
        # Evaluate startup time
        if 'total_startup_time_ms' in summary:
            target = self.baseline_targets['total_startup_time']
            status, message = target.evaluate(summary['total_startup_time_ms'])
            evaluations['total_startup_time'] = (status, message)
        
        # Evaluate memory usage
        if 'initial_memory_mb' in summary:
            target = self.baseline_targets['initial_memory_usage']
            status, message = target.evaluate(summary['initial_memory_mb'])
            evaluations['initial_memory_usage'] = (status, message)
        
        if 'memory_growth_mb' in summary:
            target = self.baseline_targets['memory_stability']
            status, message = target.evaluate(summary['memory_growth_mb'])
            evaluations['memory_stability'] = (status, message)
        
        # Evaluate UI response time
        if 'average_ui_response_ms' in summary:
            target = self.baseline_targets['ui_response_time']
            status, message = target.evaluate(summary['average_ui_response_ms'])
            evaluations['ui_response_time'] = (status, message)
        
        # Evaluate adapter performance
        if 'average_adapter_time_ms' in summary:
            # For adapter overhead, we need a comparison baseline
            # For now, assume direct v1.2.1 operation takes 50ms average
            direct_v1_baseline = 50.0
            overhead_percent = ((summary['average_adapter_time_ms'] - direct_v1_baseline) / direct_v1_baseline) * 100
            
            target = self.baseline_targets['adapter_overhead']
            status, message = target.evaluate(overhead_percent)
            evaluations['adapter_overhead'] = (status, message)
        
        return evaluations
    
    def save_report(self, report: BaselineMetricsReport, output_path: Path = None) -> Path:
        """Save baseline metrics report to file"""
        if output_path is None:
            output_path = Path(f"tests/reports/baseline_metrics_{self.test_session_id}.json")
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save as JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, indent=2, default=str)
        
        self.logger.info(f"Baseline metrics report saved to: {output_path}")
        return output_path


# Global metrics collector instance
_metrics_collector: Optional[BaselineMetricsCollector] = None


def get_metrics_collector(test_session_id: str = None) -> BaselineMetricsCollector:
    """Get or create global metrics collector instance"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = BaselineMetricsCollector(test_session_id)
    return _metrics_collector


def reset_metrics_collector():
    """Reset global metrics collector"""
    global _metrics_collector
    if _metrics_collector:
        _metrics_collector.stop_continuous_monitoring()
    _metrics_collector = None


@contextmanager
def baseline_metrics_session(test_session_id: str = None):
    """Context manager for baseline metrics collection session"""
    collector = get_metrics_collector(test_session_id)
    
    # Start continuous monitoring
    collector.start_continuous_memory_monitoring()
    
    try:
        yield collector
    finally:
        # Stop monitoring and generate report
        collector.stop_continuous_monitoring()
        report = collector.generate_baseline_report()
        
        # Save report
        report_path = collector.save_report(report)
        
        # Reset for next session
        reset_metrics_collector()
        
        print(f"\n{'='*60}")
        print(f"BASELINE METRICS REPORT: {collector.test_session_id}")
        print(f"{'='*60}")
        print(f"Report saved to: {report_path}")
        
        # Print key baseline evaluations
        for metric_name, (status, message) in report.baseline_evaluations.items():
            print(f"{metric_name}: {message}")
        
        print(f"{'='*60}\n")


if __name__ == "__main__":
    # Example usage
    with baseline_metrics_session("example_test") as collector:
        # Simulate startup phases
        with collector.measure_startup_phase("constants_validation"):
            time.sleep(0.005)  # 5ms
        
        with collector.measure_startup_phase("core_foundation"):
            time.sleep(0.020)  # 20ms
        
        with collector.measure_startup_phase("data_layer"):
            time.sleep(0.030)  # 30ms
        
        # Simulate UI actions
        with collector.measure_ui_response("button_click"):
            time.sleep(0.050)  # 50ms
        
        # Simulate adapter operations
        with collector.measure_adapter_performance("main_window_adapter", "attach_component"):
            time.sleep(0.003)  # 3ms
        
        print("Baseline metrics collection example completed!") 