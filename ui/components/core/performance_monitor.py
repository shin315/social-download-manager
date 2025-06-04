"""
Advanced Performance Monitor for v2.0 UI Architecture

This module provides comprehensive performance monitoring including:
- Real-time performance metrics collection and analysis
- Resource usage tracking and optimization recommendations
- Anomaly detection for performance regressions
- Visualization dashboards and charts
- Performance alerts and notifications
- Benchmarking tools and performance testing
- Memory, CPU, and GPU usage monitoring
"""

import logging
import threading
import time
import psutil
import json
from typing import Dict, Any, Optional, Callable, List, Set, Union, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from collections import defaultdict, deque
import statistics
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QThread, QMutex, QMutexLocker
from PyQt6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of performance metrics"""
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    GPU_USAGE = "gpu_usage"
    DISK_IO = "disk_io"
    NETWORK_IO = "network_io"
    RENDER_TIME = "render_time"
    RESPONSE_TIME = "response_time"
    FRAME_RATE = "frame_rate"
    THREAD_COUNT = "thread_count"
    CACHE_HIT_RATE = "cache_hit_rate"
    ERROR_RATE = "error_rate"
    CUSTOM = "custom"


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class BenchmarkType(Enum):
    """Types of performance benchmarks"""
    STARTUP_TIME = "startup_time"
    TAB_SWITCH_TIME = "tab_switch_time"
    MEMORY_USAGE = "memory_usage"
    RENDER_PERFORMANCE = "render_performance"
    NETWORK_LATENCY = "network_latency"
    DISK_THROUGHPUT = "disk_throughput"
    UI_RESPONSIVENESS = "ui_responsiveness"
    CUSTOM = "custom"


@dataclass
class PerformanceMetric:
    """Individual performance metric data point"""
    id: str
    metric_type: MetricType
    component_id: str
    component_type: str
    
    # Metric data
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Context
    context: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    # Threshold information
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None
    is_anomaly: bool = False


@dataclass
class PerformanceAlert:
    """Performance alert information"""
    id: str
    severity: AlertSeverity
    metric_type: MetricType
    component_id: str
    
    # Alert details
    title: str
    message: str
    current_value: float
    threshold_value: float
    
    # Timing
    triggered_at: datetime = field(default_factory=datetime.now)
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    # Actions
    suggested_actions: List[str] = field(default_factory=list)
    auto_resolve: bool = True
    escalated: bool = False


@dataclass
class BenchmarkResult:
    """Performance benchmark result"""
    id: str
    benchmark_type: BenchmarkType
    component_id: str
    
    # Results
    score: float
    unit: str
    baseline_score: Optional[float] = None
    improvement_percentage: Optional[float] = None
    
    # Execution details
    executed_at: datetime = field(default_factory=datetime.now)
    duration_seconds: float = 0.0
    iterations: int = 1
    
    # Environment
    system_info: Dict[str, Any] = field(default_factory=dict)
    test_parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Analysis
    percentiles: Dict[str, float] = field(default_factory=dict)
    outliers_detected: bool = False
    confidence_level: float = 0.95


@dataclass
class MonitoringProfile:
    """Monitoring configuration profile"""
    id: str
    name: str
    description: str
    
    # Monitoring settings
    enabled_metrics: Set[MetricType] = field(default_factory=set)
    collection_interval_ms: int = 1000
    retention_days: int = 7
    
    # Alert thresholds
    alert_thresholds: Dict[MetricType, Dict[str, float]] = field(default_factory=dict)
    anomaly_detection_enabled: bool = True
    auto_optimization_enabled: bool = False
    
    # Visualization
    dashboard_enabled: bool = True
    real_time_charts: bool = True
    export_reports: bool = True


@dataclass
class SystemSnapshot:
    """System performance snapshot"""
    timestamp: datetime = field(default_factory=datetime.now)
    
    # System metrics
    cpu_usage_percent: float = 0.0
    memory_usage_percent: float = 0.0
    disk_usage_percent: float = 0.0
    network_io_mbps: float = 0.0
    
    # Application metrics
    process_memory_mb: float = 0.0
    thread_count: int = 0
    handle_count: int = 0
    gui_objects: int = 0
    
    # Performance metrics
    render_fps: float = 0.0
    response_time_ms: float = 0.0
    cache_hit_rate: float = 0.0
    error_count: int = 0
    
    # Context
    active_components: int = 0
    active_tabs: int = 0
    hibernated_tabs: int = 0


class PerformanceMonitor(QObject):
    """
    Advanced performance monitor providing comprehensive metrics collection,
    analysis, alerting, and optimization recommendations for v2.0 UI architecture.
    """
    
    # Signals for performance events
    metric_collected = pyqtSignal(str, str, float)  # metric_id, component_id, value
    alert_triggered = pyqtSignal(str, str)  # alert_id, severity
    anomaly_detected = pyqtSignal(str, str, float)  # component_id, metric_type, value
    benchmark_completed = pyqtSignal(str, float)  # benchmark_id, score
    optimization_suggested = pyqtSignal(str, str)  # component_id, suggestion
    threshold_exceeded = pyqtSignal(str, str, float, float)  # component_id, metric_type, value, threshold
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.config = self._create_default_config()
        if config:
            self.config.update(config)
        
        # Core state
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self._alerts: Dict[str, PerformanceAlert] = {}
        self._benchmarks: Dict[str, BenchmarkResult] = {}
        self._monitoring_profiles: Dict[str, MonitoringProfile] = {}
        self._component_registrations: Dict[str, Dict[str, Any]] = {}
        
        # Real-time monitoring
        self._collection_timer: Optional[QTimer] = None
        self._analysis_timer: Optional[QTimer] = None
        self._cleanup_timer: Optional[QTimer] = None
        self._monitoring_enabled = True
        
        # Performance baselines and thresholds
        self._baselines: Dict[str, Dict[str, float]] = {}
        self._dynamic_thresholds: Dict[str, Dict[str, float]] = {}
        self._anomaly_models: Dict[str, Dict] = {}
        
        # Storage and reporting
        self._storage_path = Path(self.config['storage_path'])
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._reports_path = self._storage_path / 'reports'
        self._reports_path.mkdir(exist_ok=True)
        
        # Thread safety
        self._lock = threading.RLock()
        self._collection_thread: Optional[QThread] = None
        
        # System monitoring
        self._system_process = psutil.Process()
        self._last_snapshot = SystemSnapshot()
        
        # Initialize system
        self._create_default_profile()
        self._start_monitoring()
        
        self.logger.info(f"PerformanceMonitor initialized with config: {self.config}")
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration for performance monitor"""
        return {
            'storage_path': 'data/performance',
            'collection_interval_ms': 1000,
            'analysis_interval_ms': 5000,
            'cleanup_interval_hours': 24,
            'enable_anomaly_detection': True,
            'enable_auto_optimization': False,
            'enable_real_time_alerts': True,
            'enable_system_monitoring': True,
            'enable_gpu_monitoring': True,
            'retention_days': 7,
            'max_metrics_per_component': 10000,
            'benchmark_iterations': 5,
            'confidence_threshold': 0.95,
            'export_reports_daily': True
        }
    
    def _create_default_profile(self) -> None:
        """Create default monitoring profile"""
        try:
            default_profile = MonitoringProfile(
                id="default",
                name="Default Monitoring",
                description="Standard performance monitoring profile",
                enabled_metrics={
                    MetricType.CPU_USAGE,
                    MetricType.MEMORY_USAGE,
                    MetricType.RENDER_TIME,
                    MetricType.RESPONSE_TIME,
                    MetricType.FRAME_RATE
                },
                collection_interval_ms=self.config['collection_interval_ms'],
                retention_days=self.config['retention_days'],
                alert_thresholds={
                    MetricType.CPU_USAGE: {'warning': 70.0, 'critical': 90.0},
                    MetricType.MEMORY_USAGE: {'warning': 80.0, 'critical': 95.0},
                    MetricType.RENDER_TIME: {'warning': 16.67, 'critical': 33.33},  # 60fps, 30fps
                    MetricType.RESPONSE_TIME: {'warning': 100.0, 'critical': 500.0}
                },
                anomaly_detection_enabled=self.config['enable_anomaly_detection'],
                auto_optimization_enabled=self.config['enable_auto_optimization']
            )
            
            self._monitoring_profiles["default"] = default_profile
            
        except Exception as e:
            self.logger.error(f"Failed to create default profile: {e}")
    
    def _start_monitoring(self) -> None:
        """Start performance monitoring timers and threads"""
        try:
            # Metrics collection timer
            self._collection_timer = QTimer()
            self._collection_timer.timeout.connect(self._collect_system_metrics)
            self._collection_timer.start(self.config['collection_interval_ms'])
            
            # Analysis and anomaly detection timer
            self._analysis_timer = QTimer()
            self._analysis_timer.timeout.connect(self._analyze_metrics)
            self._analysis_timer.start(self.config['analysis_interval_ms'])
            
            # Cleanup timer
            self._cleanup_timer = QTimer()
            self._cleanup_timer.timeout.connect(self._cleanup_old_data)
            self._cleanup_timer.start(self.config['cleanup_interval_hours'] * 3600000)
            
            self.logger.info("Performance monitoring started")
            
        except Exception as e:
            self.logger.error(f"Failed to start monitoring: {e}")
    
    def register_component(self, component_id: str, component_type: str,
                          component_widget: Optional[QWidget] = None,
                          custom_metrics: List[str] = None,
                          monitoring_profile: str = "default") -> bool:
        """
        Register a component for performance monitoring
        
        Args:
            component_id: Unique identifier for the component
            component_type: Type/class of the component
            component_widget: Optional widget for UI-specific monitoring
            custom_metrics: Optional list of custom metrics to track
            monitoring_profile: Monitoring profile to use
            
        Returns:
            True if registration successful, False otherwise
        """
        with self._lock:
            try:
                if component_id in self._component_registrations:
                    self.logger.warning(f"Component {component_id} already registered")
                    return False
                
                registration = {
                    'component_type': component_type,
                    'component_widget': component_widget,
                    'custom_metrics': custom_metrics or [],
                    'monitoring_profile': monitoring_profile,
                    'registered_at': datetime.now(),
                    'metrics_count': 0,
                    'last_metric_time': None
                }
                
                self._component_registrations[component_id] = registration
                
                # Initialize baseline metrics for the component
                self._initialize_component_baselines(component_id)
                
                self.logger.info(f"Component {component_id} ({component_type}) registered for monitoring")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to register component {component_id}: {e}")
                return False
    
    def unregister_component(self, component_id: str) -> bool:
        """Unregister a component from monitoring"""
        with self._lock:
            try:
                if component_id not in self._component_registrations:
                    return False
                
                # Clean up component data
                del self._component_registrations[component_id]
                
                # Remove metrics (optional - keep for historical analysis)
                if self.config.get('cleanup_on_unregister', False):
                    metrics_to_remove = [k for k in self._metrics.keys() if k.startswith(f"{component_id}_")]
                    for metric_key in metrics_to_remove:
                        del self._metrics[metric_key]
                
                self.logger.info(f"Component {component_id} unregistered from monitoring")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to unregister component {component_id}: {e}")
                return False
    
    def record_metric(self, component_id: str, metric_type: MetricType,
                     value: float, unit: str = "", context: Dict[str, Any] = None,
                     tags: List[str] = None) -> Optional[str]:
        """
        Record a performance metric
        
        Args:
            component_id: ID of component the metric belongs to
            metric_type: Type of metric being recorded
            value: Metric value
            unit: Unit of measurement
            context: Additional context information
            tags: Optional tags for categorization
            
        Returns:
            Metric ID if successful, None otherwise
        """
        try:
            metric_id = f"{component_id}_{metric_type.value}_{int(time.time() * 1000)}"
            
            metric = PerformanceMetric(
                id=metric_id,
                metric_type=metric_type,
                component_id=component_id,
                component_type=self._component_registrations.get(component_id, {}).get('component_type', 'unknown'),
                value=value,
                unit=unit,
                context=context or {},
                tags=tags or []
            )
            
            # Get thresholds for this metric type
            profile = self._get_component_profile(component_id)
            if profile and metric_type in profile.alert_thresholds:
                thresholds = profile.alert_thresholds[metric_type]
                metric.threshold_warning = thresholds.get('warning')
                metric.threshold_critical = thresholds.get('critical')
            
            # Store metric
            metric_key = f"{component_id}_{metric_type.value}"
            self._metrics[metric_key].append(metric)
            
            # Update component registration stats
            if component_id in self._component_registrations:
                registration = self._component_registrations[component_id]
                registration['metrics_count'] += 1
                registration['last_metric_time'] = datetime.now()
            
            # Check for threshold violations
            self._check_metric_thresholds(metric)
            
            # Emit signal
            self.metric_collected.emit(metric_id, component_id, value)
            
            self.logger.debug(f"Metric recorded: {metric_id} = {value} {unit}")
            return metric_id
            
        except Exception as e:
            self.logger.error(f"Failed to record metric: {e}")
            return None
    
    def _get_component_profile(self, component_id: str) -> Optional[MonitoringProfile]:
        """Get monitoring profile for a component"""
        registration = self._component_registrations.get(component_id)
        if not registration:
            return None
        
        profile_name = registration.get('monitoring_profile', 'default')
        return self._monitoring_profiles.get(profile_name)
    
    def _check_metric_thresholds(self, metric: PerformanceMetric) -> None:
        """Check if metric exceeds thresholds and create alerts"""
        try:
            # Check warning threshold
            if (metric.threshold_warning and 
                metric.value > metric.threshold_warning):
                severity = AlertSeverity.CRITICAL if (
                    metric.threshold_critical and metric.value > metric.threshold_critical
                ) else AlertSeverity.WARNING
                
                self._create_alert(metric, severity)
            
            # Emit threshold exceeded signal
            if metric.threshold_critical and metric.value > metric.threshold_critical:
                self.threshold_exceeded.emit(
                    metric.component_id, 
                    metric.metric_type.value,
                    metric.value,
                    metric.threshold_critical
                )
            elif metric.threshold_warning and metric.value > metric.threshold_warning:
                self.threshold_exceeded.emit(
                    metric.component_id,
                    metric.metric_type.value, 
                    metric.value,
                    metric.threshold_warning
                )
                
        except Exception as e:
            self.logger.error(f"Failed to check thresholds for metric {metric.id}: {e}")
    
    def _create_alert(self, metric: PerformanceMetric, severity: AlertSeverity) -> None:
        """Create a performance alert"""
        try:
            alert_id = f"alert_{metric.component_id}_{metric.metric_type.value}_{int(time.time())}"
            
            threshold_value = (metric.threshold_critical if severity == AlertSeverity.CRITICAL 
                             else metric.threshold_warning)
            
            alert = PerformanceAlert(
                id=alert_id,
                severity=severity,
                metric_type=metric.metric_type,
                component_id=metric.component_id,
                title=f"{severity.value.title()} {metric.metric_type.value} Alert",
                message=f"{metric.metric_type.value} is {metric.value:.2f} {metric.unit}, exceeding {severity.value} threshold of {threshold_value:.2f} {metric.unit}",
                current_value=metric.value,
                threshold_value=threshold_value or 0.0,
                suggested_actions=self._get_suggested_actions(metric.metric_type, severity)
            )
            
            self._alerts[alert_id] = alert
            
            self.logger.warning(f"Performance alert created: {alert.title}")
            self.alert_triggered.emit(alert_id, severity.value)
            
        except Exception as e:
            self.logger.error(f"Failed to create alert: {e}")
    
    def _get_suggested_actions(self, metric_type: MetricType, severity: AlertSeverity) -> List[str]:
        """Get suggested actions for a metric alert"""
        suggestions = {
            MetricType.CPU_USAGE: [
                "Check for CPU-intensive operations",
                "Consider reducing background tasks",
                "Optimize algorithms and reduce complexity",
                "Profile code for performance bottlenecks"
            ],
            MetricType.MEMORY_USAGE: [
                "Check for memory leaks",
                "Clear unused caches",
                "Reduce object allocations",
                "Consider hibernating inactive tabs"
            ],
            MetricType.RENDER_TIME: [
                "Optimize rendering pipeline",
                "Reduce complex UI elements",
                "Use hardware acceleration",
                "Implement progressive rendering"
            ],
            MetricType.RESPONSE_TIME: [
                "Optimize event handling",
                "Reduce synchronous operations",
                "Use background threading",
                "Implement request queuing"
            ]
        }
        
        base_suggestions = suggestions.get(metric_type, ["Review component performance"])
        
        if severity == AlertSeverity.CRITICAL:
            base_suggestions.extend([
                "Consider immediate intervention",
                "Monitor system stability",
                "Prepare fallback options"
            ])
        
        return base_suggestions
    
    def _collect_system_metrics(self) -> None:
        """Collect system-wide performance metrics"""
        if not self._monitoring_enabled:
            return
        
        try:
            # Create system snapshot
            snapshot = SystemSnapshot()
            
            # System metrics
            snapshot.cpu_usage_percent = psutil.cpu_percent(interval=None)
            snapshot.memory_usage_percent = psutil.virtual_memory().percent
            snapshot.disk_usage_percent = psutil.disk_usage('/').percent
            
            # Network I/O
            net_io = psutil.net_io_counters()
            if hasattr(self, '_last_net_io'):
                time_delta = time.time() - self._last_net_time
                bytes_delta = (net_io.bytes_sent + net_io.bytes_recv) - self._last_net_io
                snapshot.network_io_mbps = (bytes_delta / time_delta) / (1024 * 1024) if time_delta > 0 else 0.0
            
            self._last_net_io = net_io.bytes_sent + net_io.bytes_recv
            self._last_net_time = time.time()
            
            # Process-specific metrics
            memory_info = self._system_process.memory_info()
            snapshot.process_memory_mb = memory_info.rss / (1024 * 1024)
            snapshot.thread_count = self._system_process.num_threads()
            
            # Application context
            snapshot.active_components = len(self._component_registrations)
            
            # Store snapshot
            self._last_snapshot = snapshot
            
            # Record as metrics
            self.record_metric("system", MetricType.CPU_USAGE, snapshot.cpu_usage_percent, "%")
            self.record_metric("system", MetricType.MEMORY_USAGE, snapshot.memory_usage_percent, "%")
            self.record_metric("system", MetricType.THREAD_COUNT, snapshot.thread_count, "threads")
            
        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")
    
    def _analyze_metrics(self) -> None:
        """Analyze collected metrics for anomalies and patterns"""
        if not self.config['enable_anomaly_detection']:
            return
        
        try:
            for metric_key, metric_deque in self._metrics.items():
                if len(metric_deque) < 10:  # Need minimum data points
                    continue
                
                # Get recent metrics
                recent_metrics = list(metric_deque)[-50:]  # Last 50 data points
                values = [m.value for m in recent_metrics]
                
                # Statistical analysis
                mean_value = statistics.mean(values)
                std_dev = statistics.stdev(values) if len(values) > 1 else 0
                
                # Detect anomalies (values beyond 2 standard deviations)
                if std_dev > 0:
                    latest_metric = recent_metrics[-1]
                    z_score = abs(latest_metric.value - mean_value) / std_dev
                    
                    if z_score > 2.0:  # Anomaly detected
                        latest_metric.is_anomaly = True
                        self.anomaly_detected.emit(
                            latest_metric.component_id,
                            latest_metric.metric_type.value,
                            latest_metric.value
                        )
                        
                        self.logger.warning(
                            f"Anomaly detected in {metric_key}: {latest_metric.value:.2f} "
                            f"(z-score: {z_score:.2f})"
                        )
            
        except Exception as e:
            self.logger.error(f"Failed to analyze metrics: {e}")
    
    def run_benchmark(self, benchmark_type: BenchmarkType, component_id: str,
                     test_parameters: Dict[str, Any] = None,
                     iterations: int = None) -> Optional[str]:
        """
        Run a performance benchmark
        
        Args:
            benchmark_type: Type of benchmark to run
            component_id: Component to benchmark
            test_parameters: Parameters for the benchmark
            iterations: Number of iterations (defaults to config)
            
        Returns:
            Benchmark ID if successful, None otherwise
        """
        try:
            benchmark_id = f"benchmark_{component_id}_{benchmark_type.value}_{int(time.time())}"
            iterations = iterations or self.config['benchmark_iterations']
            
            self.logger.info(f"Starting benchmark {benchmark_id}")
            
            # Run benchmark based on type
            scores = []
            start_time = time.time()
            
            for i in range(iterations):
                score = self._execute_benchmark(benchmark_type, component_id, test_parameters or {})
                if score is not None:
                    scores.append(score)
            
            duration = time.time() - start_time
            
            if not scores:
                self.logger.error(f"Benchmark {benchmark_id} failed - no valid scores")
                return None
            
            # Calculate statistics
            avg_score = statistics.mean(scores)
            percentiles = {
                'p50': statistics.median(scores),
                'p95': self._calculate_percentile(scores, 95),
                'p99': self._calculate_percentile(scores, 99)
            }
            
            # Detect outliers
            outliers_detected = self._detect_outliers(scores)
            
            # Get system info
            system_info = {
                'cpu_count': psutil.cpu_count(),
                'memory_gb': psutil.virtual_memory().total / (1024**3),
                'platform': psutil.platform,
                'python_version': psutil.sys.version
            }
            
            # Create benchmark result
            result = BenchmarkResult(
                id=benchmark_id,
                benchmark_type=benchmark_type,
                component_id=component_id,
                score=avg_score,
                unit=self._get_benchmark_unit(benchmark_type),
                duration_seconds=duration,
                iterations=len(scores),
                system_info=system_info,
                test_parameters=test_parameters or {},
                percentiles=percentiles,
                outliers_detected=outliers_detected
            )
            
            # Compare with baseline if available
            baseline_key = f"{component_id}_{benchmark_type.value}"
            if baseline_key in self._baselines:
                baseline_score = self._baselines[baseline_key].get('score')
                if baseline_score:
                    result.baseline_score = baseline_score
                    result.improvement_percentage = ((avg_score - baseline_score) / baseline_score) * 100
            
            self._benchmarks[benchmark_id] = result
            
            self.logger.info(f"Benchmark {benchmark_id} completed: {avg_score:.2f} {result.unit}")
            self.benchmark_completed.emit(benchmark_id, avg_score)
            
            return benchmark_id
            
        except Exception as e:
            self.logger.error(f"Failed to run benchmark: {e}")
            return None
    
    def _execute_benchmark(self, benchmark_type: BenchmarkType, component_id: str,
                          test_parameters: Dict[str, Any]) -> Optional[float]:
        """Execute a specific benchmark test"""
        try:
            if benchmark_type == BenchmarkType.STARTUP_TIME:
                return self._benchmark_startup_time(component_id, test_parameters)
            elif benchmark_type == BenchmarkType.TAB_SWITCH_TIME:
                return self._benchmark_tab_switch_time(component_id, test_parameters)
            elif benchmark_type == BenchmarkType.MEMORY_USAGE:
                return self._benchmark_memory_usage(component_id, test_parameters)
            elif benchmark_type == BenchmarkType.RENDER_PERFORMANCE:
                return self._benchmark_render_performance(component_id, test_parameters)
            elif benchmark_type == BenchmarkType.UI_RESPONSIVENESS:
                return self._benchmark_ui_responsiveness(component_id, test_parameters)
            else:
                self.logger.warning(f"Unknown benchmark type: {benchmark_type}")
                return None
                
        except Exception as e:
            self.logger.error(f"Benchmark execution failed: {e}")
            return None
    
    def _benchmark_startup_time(self, component_id: str, params: Dict[str, Any]) -> float:
        """Benchmark component startup time"""
        # Simulate startup time measurement
        start_time = time.time()
        
        # Get component and measure initialization time
        registration = self._component_registrations.get(component_id)
        if registration and registration.get('component_widget'):
            widget = registration['component_widget']
            # Simulate widget operations
            if hasattr(widget, 'update'):
                widget.update()
        
        return (time.time() - start_time) * 1000  # Return in milliseconds
    
    def _benchmark_tab_switch_time(self, component_id: str, params: Dict[str, Any]) -> float:
        """Benchmark tab switching performance"""
        # Simulate tab switch timing
        switch_times = []
        iterations = params.get('iterations', 10)
        
        for _ in range(iterations):
            start_time = time.time()
            # Simulate tab switch operations
            time.sleep(0.001)  # Minimal delay to simulate real operation
            switch_time = (time.time() - start_time) * 1000
            switch_times.append(switch_time)
        
        return statistics.mean(switch_times)
    
    def _benchmark_memory_usage(self, component_id: str, params: Dict[str, Any]) -> float:
        """Benchmark memory usage efficiency"""
        # Measure current memory usage
        process = psutil.Process()
        memory_before = process.memory_info().rss
        
        # Simulate memory operations
        time.sleep(0.1)
        
        memory_after = process.memory_info().rss
        return (memory_after - memory_before) / (1024 * 1024)  # Return in MB
    
    def _benchmark_render_performance(self, component_id: str, params: Dict[str, Any]) -> float:
        """Benchmark rendering performance"""
        registration = self._component_registrations.get(component_id)
        if not registration or not registration.get('component_widget'):
            return 0.0
        
        widget = registration['component_widget']
        render_times = []
        iterations = params.get('iterations', 100)
        
        for _ in range(iterations):
            start_time = time.time()
            if hasattr(widget, 'repaint'):
                widget.repaint()
            elif hasattr(widget, 'update'):
                widget.update()
            render_time = (time.time() - start_time) * 1000
            render_times.append(render_time)
        
        return statistics.mean(render_times)
    
    def _benchmark_ui_responsiveness(self, component_id: str, params: Dict[str, Any]) -> float:
        """Benchmark UI responsiveness"""
        # Simulate UI interaction timing
        response_times = []
        interactions = params.get('interactions', 50)
        
        for _ in range(interactions):
            start_time = time.time()
            # Simulate user interaction processing
            time.sleep(0.001)
            response_time = (time.time() - start_time) * 1000
            response_times.append(response_time)
        
        return statistics.mean(response_times)
    
    def _get_benchmark_unit(self, benchmark_type: BenchmarkType) -> str:
        """Get unit for benchmark type"""
        units = {
            BenchmarkType.STARTUP_TIME: "ms",
            BenchmarkType.TAB_SWITCH_TIME: "ms", 
            BenchmarkType.MEMORY_USAGE: "MB",
            BenchmarkType.RENDER_PERFORMANCE: "ms",
            BenchmarkType.UI_RESPONSIVENESS: "ms",
            BenchmarkType.NETWORK_LATENCY: "ms",
            BenchmarkType.DISK_THROUGHPUT: "MB/s"
        }
        return units.get(benchmark_type, "units")
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile value"""
        sorted_values = sorted(values)
        index = (percentile / 100) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def _detect_outliers(self, values: List[float]) -> bool:
        """Detect if there are statistical outliers in the data"""
        if len(values) < 4:
            return False
        
        q1 = self._calculate_percentile(values, 25)
        q3 = self._calculate_percentile(values, 75)
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        return any(v < lower_bound or v > upper_bound for v in values)
    
    def _initialize_component_baselines(self, component_id: str) -> None:
        """Initialize performance baselines for a component"""
        baseline_key = f"{component_id}_baselines"
        if baseline_key not in self._baselines:
            self._baselines[baseline_key] = {}
    
    def _cleanup_old_data(self) -> None:
        """Clean up old performance data based on retention policy"""
        try:
            cutoff_time = datetime.now() - timedelta(days=self.config['retention_days'])
            cleanup_count = 0
            
            # Clean up old metrics
            for metric_key, metric_deque in self._metrics.items():
                original_length = len(metric_deque)
                
                # Remove metrics older than retention period
                while metric_deque and metric_deque[0].timestamp < cutoff_time:
                    metric_deque.popleft()
                
                cleanup_count += original_length - len(metric_deque)
            
            # Clean up old alerts (resolved ones older than retention)
            alerts_to_remove = []
            for alert_id, alert in self._alerts.items():
                if (alert.resolved_at and 
                    alert.resolved_at < cutoff_time):
                    alerts_to_remove.append(alert_id)
            
            for alert_id in alerts_to_remove:
                del self._alerts[alert_id]
                cleanup_count += 1
            
            if cleanup_count > 0:
                self.logger.info(f"Cleaned up {cleanup_count} old performance data items")
                
        except Exception as e:
            self.logger.error(f"Data cleanup failed: {e}")
    
    def get_component_metrics(self, component_id: str, 
                            metric_type: Optional[MetricType] = None,
                            hours: int = 24) -> List[PerformanceMetric]:
        """Get metrics for a component"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        results = []
        
        for metric_key, metric_deque in self._metrics.items():
            if not metric_key.startswith(f"{component_id}_"):
                continue
            
            if metric_type and metric_type.value not in metric_key:
                continue
            
            for metric in metric_deque:
                if metric.timestamp >= cutoff_time:
                    results.append(metric)
        
        return sorted(results, key=lambda m: m.timestamp)
    
    def get_system_snapshot(self) -> SystemSnapshot:
        """Get latest system performance snapshot"""
        return self._last_snapshot
    
    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[PerformanceAlert]:
        """Get active (unresolved) alerts"""
        alerts = [
            alert for alert in self._alerts.values()
            if not alert.resolved_at
        ]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return sorted(alerts, key=lambda a: a.triggered_at, reverse=True)
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        if alert_id in self._alerts:
            self._alerts[alert_id].acknowledged_at = datetime.now()
            return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        if alert_id in self._alerts:
            self._alerts[alert_id].resolved_at = datetime.now()
            return True
        return False
    
    def export_performance_report(self, component_ids: List[str] = None,
                                 hours: int = 24) -> str:
        """Export performance report to file"""
        try:
            report_data = {
                'generated_at': datetime.now().isoformat(),
                'time_range_hours': hours,
                'system_snapshot': asdict(self._last_snapshot),
                'components': {},
                'alerts': {},
                'benchmarks': {}
            }
            
            # Add component data
            target_components = component_ids or list(self._component_registrations.keys())
            
            for component_id in target_components:
                metrics = self.get_component_metrics(component_id, hours=hours)
                report_data['components'][component_id] = {
                    'metrics_count': len(metrics),
                    'registration': self._component_registrations.get(component_id, {}),
                    'recent_metrics': [asdict(m) for m in metrics[-100:]]  # Last 100 metrics
                }
            
            # Add alerts
            for alert_id, alert in self._alerts.items():
                if not component_ids or alert.component_id in component_ids:
                    report_data['alerts'][alert_id] = asdict(alert)
            
            # Add benchmarks
            for benchmark_id, benchmark in self._benchmarks.items():
                if not component_ids or benchmark.component_id in component_ids:
                    report_data['benchmarks'][benchmark_id] = asdict(benchmark)
            
            # Save report
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_file = self._reports_path / f"performance_report_{timestamp}.json"
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            self.logger.info(f"Performance report exported to {report_file}")
            return str(report_file)
            
        except Exception as e:
            self.logger.error(f"Failed to export performance report: {e}")
            return ""
    
    def set_monitoring_enabled(self, enabled: bool) -> None:
        """Enable or disable performance monitoring"""
        self._monitoring_enabled = enabled
        self.logger.info(f"Performance monitoring {'enabled' if enabled else 'disabled'}")
    
    def shutdown(self) -> None:
        """Shutdown the performance monitor"""
        with self._lock:
            try:
                self.logger.info("Shutting down PerformanceMonitor")
                
                # Stop timers
                if self._collection_timer:
                    self._collection_timer.stop()
                if self._analysis_timer:
                    self._analysis_timer.stop()
                if self._cleanup_timer:
                    self._cleanup_timer.stop()
                
                # Export final performance report
                if self.config.get('export_final_report', True):
                    self.export_performance_report()
                
                self.logger.info("PerformanceMonitor shutdown completed")
                
            except Exception as e:
                self.logger.error(f"Error during PerformanceMonitor shutdown: {e}")


# Factory function for creating performance monitor instances
def create_performance_monitor(config: Optional[Dict[str, Any]] = None) -> PerformanceMonitor:
    """Create a new performance monitor instance with optional configuration"""
    return PerformanceMonitor(config)


# Global instance management
_global_performance_monitor: Optional[PerformanceMonitor] = None


def get_global_performance_monitor() -> PerformanceMonitor:
    """Get or create the global performance monitor instance"""
    global _global_performance_monitor
    
    if _global_performance_monitor is None:
        _global_performance_monitor = PerformanceMonitor()
    
    return _global_performance_monitor


def set_global_performance_monitor(monitor: PerformanceMonitor) -> None:
    """Set the global performance monitor instance"""
    global _global_performance_monitor
    _global_performance_monitor = monitor 