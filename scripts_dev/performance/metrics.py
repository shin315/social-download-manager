"""
Performance Metrics Collection for Social Download Manager v2.0

Provides real-time metrics collection and analysis capabilities.
"""

import time
import threading
from enum import Enum
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from collections import deque

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class MetricType(Enum):
    """Types of metrics that can be collected"""
    TIMING = "timing"
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    RATE = "rate"


@dataclass
class MetricData:
    """Container for metric data"""
    name: str
    metric_type: MetricType
    value: float
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)
    unit: str = ""


class MetricsCollector:
    """
    Real-time metrics collection for performance monitoring
    """
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.metrics: Dict[str, deque] = {}
        self.counters: Dict[str, float] = {}
        self.gauges: Dict[str, float] = {}
        self.timers: Dict[str, List[float]] = {}
        
        self._lock = threading.Lock()
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
    
    def record_timing(self, name: str, duration: float, tags: Optional[Dict[str, str]] = None):
        """Record a timing metric"""
        metric = MetricData(
            name=name,
            metric_type=MetricType.TIMING,
            value=duration,
            timestamp=time.time(),
            tags=tags or {},
            unit="seconds"
        )
        self._store_metric(metric)
    
    def increment_counter(self, name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None):
        """Increment a counter metric"""
        with self._lock:
            self.counters[name] = self.counters.get(name, 0) + value
        
        metric = MetricData(
            name=name,
            metric_type=MetricType.COUNTER,
            value=self.counters[name],
            timestamp=time.time(),
            tags=tags or {}
        )
        self._store_metric(metric)
    
    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Set a gauge metric"""
        with self._lock:
            self.gauges[name] = value
        
        metric = MetricData(
            name=name,
            metric_type=MetricType.GAUGE,
            value=value,
            timestamp=time.time(),
            tags=tags or {}
        )
        self._store_metric(metric)
    
    def record_rate(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a rate metric"""
        metric = MetricData(
            name=name,
            metric_type=MetricType.RATE,
            value=value,
            timestamp=time.time(),
            tags=tags or {},
            unit="per_second"
        )
        self._store_metric(metric)
    
    def _store_metric(self, metric: MetricData):
        """Store metric in history"""
        with self._lock:
            if metric.name not in self.metrics:
                self.metrics[metric.name] = deque(maxlen=self.max_history)
            
            self.metrics[metric.name].append(metric)
    
    def get_metric_history(self, name: str) -> List[MetricData]:
        """Get metric history"""
        with self._lock:
            if name in self.metrics:
                return list(self.metrics[name])
            return []
    
    def get_latest_value(self, name: str) -> Optional[float]:
        """Get latest value for a metric"""
        history = self.get_metric_history(name)
        if history:
            return history[-1].value
        return None
    
    def get_average(self, name: str, window_seconds: Optional[float] = None) -> Optional[float]:
        """Get average value for a metric over a time window"""
        history = self.get_metric_history(name)
        if not history:
            return None
        
        if window_seconds:
            cutoff_time = time.time() - window_seconds
            history = [m for m in history if m.timestamp >= cutoff_time]
        
        if not history:
            return None
        
        return sum(m.value for m in history) / len(history)
    
    def get_max(self, name: str, window_seconds: Optional[float] = None) -> Optional[float]:
        """Get maximum value for a metric over a time window"""
        history = self.get_metric_history(name)
        if not history:
            return None
        
        if window_seconds:
            cutoff_time = time.time() - window_seconds
            history = [m for m in history if m.timestamp >= cutoff_time]
        
        if not history:
            return None
        
        return max(m.value for m in history)
    
    def get_summary_stats(self, name: str) -> Dict[str, float]:
        """Get summary statistics for a metric"""
        history = self.get_metric_history(name)
        if not history:
            return {}
        
        values = [m.value for m in history]
        
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'latest': values[-1],
            'first': values[0]
        }
    
    def start_system_monitoring(self, interval: float = 1.0):
        """Start automatic system metrics collection"""
        if not HAS_PSUTIL:
            print("psutil not available - system monitoring disabled")
            return
        
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_system_metrics,
            args=(interval,)
        )
        self._monitor_thread.daemon = True
        self._monitor_thread.start()
    
    def stop_system_monitoring(self):
        """Stop automatic system metrics collection"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
    
    def _monitor_system_metrics(self, interval: float):
        """Background thread for collecting system metrics"""
        while self._running:
            try:
                # CPU metrics
                cpu_percent = psutil.cpu_percent(interval=0.1)
                self.set_gauge("system.cpu_percent", cpu_percent)
                
                # Memory metrics
                memory = psutil.virtual_memory()
                self.set_gauge("system.memory_percent", memory.percent)
                self.set_gauge("system.memory_used_mb", memory.used / (1024 * 1024))
                self.set_gauge("system.memory_available_mb", memory.available / (1024 * 1024))
                
                # Disk I/O metrics
                disk_io = psutil.disk_io_counters()
                if disk_io:
                    self.set_gauge("system.disk_read_mb", disk_io.read_bytes / (1024 * 1024))
                    self.set_gauge("system.disk_write_mb", disk_io.write_bytes / (1024 * 1024))
                
                # Network I/O metrics
                network_io = psutil.net_io_counters()
                if network_io:
                    self.set_gauge("system.network_sent_mb", network_io.bytes_sent / (1024 * 1024))
                    self.set_gauge("system.network_recv_mb", network_io.bytes_recv / (1024 * 1024))
                
                # Process metrics
                self.set_gauge("system.thread_count", threading.active_count())
                self.set_gauge("system.process_count", len(psutil.pids()))
                
            except Exception as e:
                print(f"Error collecting system metrics: {e}")
            
            time.sleep(interval)
    
    def export_metrics(self) -> Dict[str, Any]:
        """Export all metrics as a dictionary"""
        with self._lock:
            return {
                'metrics_history': {
                    name: [
                        {
                            'value': m.value,
                            'timestamp': m.timestamp,
                            'type': m.metric_type.value,
                            'tags': m.tags,
                            'unit': m.unit
                        }
                        for m in metrics
                    ]
                    for name, metrics in self.metrics.items()
                },
                'current_counters': dict(self.counters),
                'current_gauges': dict(self.gauges),
                'summary_stats': {
                    name: self.get_summary_stats(name)
                    for name in self.metrics.keys()
                }
            }
    
    def clear_metrics(self):
        """Clear all stored metrics"""
        with self._lock:
            self.metrics.clear()
            self.counters.clear()
            self.gauges.clear()
            self.timers.clear()


# Context manager for timing operations
class TimingContext:
    """Context manager for timing code blocks"""
    
    def __init__(self, collector: MetricsCollector, name: str, tags: Optional[Dict[str, str]] = None):
        self.collector = collector
        self.name = name
        self.tags = tags or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.collector.record_timing(self.name, duration, self.tags)


# Decorator for timing functions
def timed_operation(collector: MetricsCollector, name: Optional[str] = None, tags: Optional[Dict[str, str]] = None):
    """Decorator for timing function execution"""
    def decorator(func: Callable) -> Callable:
        metric_name = name or f"function.{func.__name__}"
        
        def wrapper(*args, **kwargs):
            with TimingContext(collector, metric_name, tags):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator 