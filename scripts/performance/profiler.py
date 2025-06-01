"""
Application Profiler for Social Download Manager v2.0

Provides comprehensive profiling capabilities using multiple Python profiling tools.
"""

import cProfile
import pstats
import io
import time
import threading
import functools
import gc
from enum import Enum
from typing import Dict, Any, Optional, Callable, List, Union
from pathlib import Path
from dataclasses import dataclass, field
from contextlib import contextmanager

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    from memory_profiler import profile as memory_profile
    from memory_profiler import LineProfiler as MemoryLineProfiler
    HAS_MEMORY_PROFILER = True
except ImportError:
    HAS_MEMORY_PROFILER = False

try:
    from line_profiler import LineProfiler
    HAS_LINE_PROFILER = True
except ImportError:
    HAS_LINE_PROFILER = False


class ProfilerType(Enum):
    """Types of profiling available"""
    CPU = "cpu"
    MEMORY = "memory"
    LINE_BY_LINE = "line_by_line"
    SYSTEM_RESOURCES = "system_resources"
    IO_OPERATIONS = "io_operations"


@dataclass
class ProfileSession:
    """Represents a profiling session"""
    session_id: str
    profiler_type: ProfilerType
    start_time: float
    end_time: Optional[float] = None
    output_file: Optional[Path] = None
    stats: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemSnapshot:
    """System resource snapshot"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_sent_mb: float
    network_recv_mb: float
    thread_count: int
    process_count: int


class ApplicationProfiler:
    """
    Comprehensive application profiler for performance analysis
    """
    
    def __init__(self, output_dir: Union[str, Path] = "scripts/performance_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.active_sessions: Dict[str, ProfileSession] = {}
        self.system_snapshots: List[SystemSnapshot] = []
        self.baseline_metrics: Optional[Dict[str, Any]] = None
        
        # Initialize profilers
        self._cpu_profiler: Optional[cProfile.Profile] = None
        self._memory_profiler: Optional[MemoryLineProfiler] = None
        self._line_profiler: Optional[LineProfiler] = None
        
        # System monitoring
        self._monitoring_active = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_interval = 1.0  # seconds
        
        # Performance tracking
        self.performance_history: List[Dict[str, Any]] = []
    
    def start_session(self, session_id: str, profiler_type: ProfilerType, 
                     metadata: Optional[Dict[str, Any]] = None) -> ProfileSession:
        """Start a new profiling session"""
        if session_id in self.active_sessions:
            raise ValueError(f"Session {session_id} already active")
        
        session = ProfileSession(
            session_id=session_id,
            profiler_type=profiler_type,
            start_time=time.time(),
            metadata=metadata or {}
        )
        
        # Initialize appropriate profiler
        if profiler_type == ProfilerType.CPU:
            self._cpu_profiler = cProfile.Profile()
            self._cpu_profiler.enable()
            
        elif profiler_type == ProfilerType.MEMORY and HAS_MEMORY_PROFILER:
            self._memory_profiler = MemoryLineProfiler()
            
        elif profiler_type == ProfilerType.LINE_BY_LINE and HAS_LINE_PROFILER:
            self._line_profiler = LineProfiler()
            
        elif profiler_type == ProfilerType.SYSTEM_RESOURCES:
            self.start_system_monitoring()
        
        self.active_sessions[session_id] = session
        return session
    
    def end_session(self, session_id: str) -> ProfileSession:
        """End a profiling session and save results"""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.active_sessions[session_id]
        session.end_time = time.time()
        
        # Save profiling results
        if session.profiler_type == ProfilerType.CPU and self._cpu_profiler:
            self._cpu_profiler.disable()
            session.output_file = self._save_cpu_profile(session)
            
        elif session.profiler_type == ProfilerType.MEMORY and self._memory_profiler:
            session.output_file = self._save_memory_profile(session)
            
        elif session.profiler_type == ProfilerType.LINE_BY_LINE and self._line_profiler:
            session.output_file = self._save_line_profile(session)
            
        elif session.profiler_type == ProfilerType.SYSTEM_RESOURCES:
            self.stop_system_monitoring()
            session.output_file = self._save_system_profile(session)
        
        # Cleanup
        del self.active_sessions[session_id]
        self._cleanup_profilers()
        
        return session
    
    @contextmanager
    def profile_context(self, session_id: str, profiler_type: ProfilerType,
                       metadata: Optional[Dict[str, Any]] = None):
        """Context manager for profiling code blocks"""
        session = self.start_session(session_id, profiler_type, metadata)
        try:
            yield session
        finally:
            self.end_session(session_id)
    
    def profile_function(self, profiler_type: ProfilerType = ProfilerType.CPU):
        """Decorator for profiling functions"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                session_id = f"{func.__name__}_{int(time.time())}"
                with self.profile_context(session_id, profiler_type):
                    return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def start_system_monitoring(self, interval: float = 1.0):
        """Start continuous system resource monitoring"""
        if not HAS_PSUTIL:
            print("psutil not available - system monitoring disabled")
            return
            
        self._monitor_interval = interval
        self._monitoring_active = True
        self._monitor_thread = threading.Thread(target=self._monitor_system_resources)
        self._monitor_thread.daemon = True
        self._monitor_thread.start()
    
    def stop_system_monitoring(self):
        """Stop system resource monitoring"""
        self._monitoring_active = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
    
    def _monitor_system_resources(self):
        """Background thread for monitoring system resources"""
        if not HAS_PSUTIL:
            return
            
        while self._monitoring_active:
            try:
                # Get system stats
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()
                disk_io = psutil.disk_io_counters()
                network_io = psutil.net_io_counters()
                
                snapshot = SystemSnapshot(
                    timestamp=time.time(),
                    cpu_percent=cpu_percent,
                    memory_percent=memory.percent,
                    memory_used_mb=memory.used / (1024 * 1024),
                    memory_available_mb=memory.available / (1024 * 1024),
                    disk_io_read_mb=disk_io.read_bytes / (1024 * 1024) if disk_io else 0,
                    disk_io_write_mb=disk_io.write_bytes / (1024 * 1024) if disk_io else 0,
                    network_sent_mb=network_io.bytes_sent / (1024 * 1024) if network_io else 0,
                    network_recv_mb=network_io.bytes_recv / (1024 * 1024) if network_io else 0,
                    thread_count=threading.active_count(),
                    process_count=len(psutil.pids())
                )
                
                self.system_snapshots.append(snapshot)
                
                # Keep only last 1000 snapshots to prevent memory issues
                if len(self.system_snapshots) > 1000:
                    self.system_snapshots = self.system_snapshots[-1000:]
                
            except Exception as e:
                print(f"Error monitoring system resources: {e}")
            
            time.sleep(self._monitor_interval)
    
    def _save_cpu_profile(self, session: ProfileSession) -> Path:
        """Save CPU profiling results"""
        if not self._cpu_profiler:
            return None
            
        output_file = self.output_dir / f"cpu_profile_{session.session_id}.prof"
        
        # Save raw profile data
        self._cpu_profiler.dump_stats(str(output_file))
        
        # Save text report
        stats_file = self.output_dir / f"cpu_stats_{session.session_id}.txt"
        with open(stats_file, 'w') as f:
            stats = pstats.Stats(self._cpu_profiler, stream=f)
            stats.sort_stats('cumulative')
            stats.print_stats(50)  # Top 50 functions
            stats.print_callers(20)  # Top 20 callers
            stats.print_callees(20)  # Top 20 callees
        
        return output_file
    
    def _save_memory_profile(self, session: ProfileSession) -> Path:
        """Save memory profiling results"""
        output_file = self.output_dir / f"memory_profile_{session.session_id}.txt"
        
        # Memory profiling would need to be done differently
        # This is a placeholder for actual memory profiling implementation
        with open(output_file, 'w') as f:
            f.write(f"Memory profiling session: {session.session_id}\n")
            f.write(f"Duration: {session.end_time - session.start_time:.2f}s\n")
            f.write("Memory profiling data would be saved here\n")
        
        return output_file
    
    def _save_line_profile(self, session: ProfileSession) -> Path:
        """Save line-by-line profiling results"""
        if not self._line_profiler:
            return None
            
        output_file = self.output_dir / f"line_profile_{session.session_id}.txt"
        
        with open(output_file, 'w') as f:
            self._line_profiler.print_stats(stream=f)
        
        return output_file
    
    def _save_system_profile(self, session: ProfileSession) -> Path:
        """Save system resource profiling results"""
        output_file = self.output_dir / f"system_profile_{session.session_id}.json"
        
        import json
        
        # Convert snapshots to JSON-serializable format
        snapshots_data = []
        for snapshot in self.system_snapshots:
            snapshots_data.append({
                'timestamp': snapshot.timestamp,
                'cpu_percent': snapshot.cpu_percent,
                'memory_percent': snapshot.memory_percent,
                'memory_used_mb': snapshot.memory_used_mb,
                'memory_available_mb': snapshot.memory_available_mb,
                'disk_io_read_mb': snapshot.disk_io_read_mb,
                'disk_io_write_mb': snapshot.disk_io_write_mb,
                'network_sent_mb': snapshot.network_sent_mb,
                'network_recv_mb': snapshot.network_recv_mb,
                'thread_count': snapshot.thread_count,
                'process_count': snapshot.process_count
            })
        
        data = {
            'session_id': session.session_id,
            'start_time': session.start_time,
            'end_time': session.end_time,
            'duration': session.end_time - session.start_time,
            'snapshots': snapshots_data,
            'summary': self._calculate_system_summary()
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        return output_file
    
    def _calculate_system_summary(self) -> Dict[str, Any]:
        """Calculate summary statistics from system snapshots"""
        if not self.system_snapshots:
            return {}
        
        cpu_values = [s.cpu_percent for s in self.system_snapshots]
        memory_values = [s.memory_percent for s in self.system_snapshots]
        memory_used_values = [s.memory_used_mb for s in self.system_snapshots]
        
        return {
            'cpu_avg': sum(cpu_values) / len(cpu_values),
            'cpu_max': max(cpu_values),
            'cpu_min': min(cpu_values),
            'memory_avg': sum(memory_values) / len(memory_values),
            'memory_max': max(memory_values),
            'memory_min': min(memory_values),
            'memory_used_avg_mb': sum(memory_used_values) / len(memory_used_values),
            'memory_used_max_mb': max(memory_used_values),
            'memory_used_min_mb': min(memory_used_values),
            'total_snapshots': len(self.system_snapshots)
        }
    
    def _cleanup_profilers(self):
        """Cleanup profiler instances"""
        self._cpu_profiler = None
        self._memory_profiler = None
        self._line_profiler = None
    
    def get_session_results(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get results for a completed session"""
        # Implementation would load and parse saved profile data
        pass
    
    def compare_with_baseline(self, session_id: str) -> Dict[str, Any]:
        """Compare session results with baseline metrics"""
        # Implementation would compare current results with baseline
        pass
    
    def generate_hotspots_report(self, session_id: str) -> List[Dict[str, Any]]:
        """Generate report of performance hotspots"""
        # Implementation would analyze profile data for bottlenecks
        pass

class BenchmarkManager:
    """Manages benchmark comparisons between versions."""
    
    def __init__(self):
        self.v121_baseline = {
            'startup_time': 3.2,
            'ui_load_time': 4.1,
            'avg_cpu_percent': 18.5,
            'memory_usage_mb': 125.0,
            'database_query_time': 0.045,
            'download_speed_mbps': 2.8,
            'ui_response_time_ms': 150.0,
            'memory_leak_rate_mb_per_hour': 2.5
        }
    
    def compare_metrics(self, baseline_data: Dict[str, float], 
                       current_data: Dict[str, float]) -> Dict[str, Any]:
        """Compare current metrics with baseline data."""
        comparisons = {}
        
        for metric_name in baseline_data:
            if metric_name in current_data:
                baseline_value = baseline_data[metric_name]
                current_value = current_data[metric_name]
                
                if baseline_value > 0:
                    improvement_percent = ((baseline_value - current_value) / baseline_value) * 100
                else:
                    improvement_percent = 0.0
                
                comparisons[metric_name] = {
                    'baseline': baseline_value,
                    'current': current_value,
                    'improvement_percent': improvement_percent,
                    'status': 'IMPROVED' if improvement_percent > 5 else ('DEGRADED' if improvement_percent < -5 else 'STABLE')
                }
        
        return comparisons
    
    def get_v121_baseline(self) -> Dict[str, float]:
        """Get v1.2.1 baseline metrics."""
        return self.v121_baseline.copy()

class MetricsCollector:
    """Simple metrics collector for validation."""
    
    def __init__(self):
        self.metrics = {}
        
    def record_metric(self, name: str, value: float):
        """Record a metric value."""
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append(value)
    
    def get_average(self, name: str) -> float:
        """Get average value for a metric."""
        if name in self.metrics and self.metrics[name]:
            return sum(self.metrics[name]) / len(self.metrics[name])
        return 0.0
    
    def get_all_metrics(self) -> Dict[str, List[float]]:
        """Get all collected metrics."""
        return self.metrics.copy() 