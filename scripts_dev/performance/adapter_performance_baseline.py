"""
Adapter Framework Performance Baseline Measurement Tool

This module provides comprehensive performance measurement and baseline establishment
for the adapter framework optimization project (Task 34.1).

Features:
- Memory usage tracking and profiling
- CPU utilization monitoring  
- Event system performance measurement
- Data mapping efficiency analysis
- Adapter-specific performance metrics
- Comprehensive reporting and visualization
"""

import os
import sys
import time
import psutil
import gc
import json
import threading
import tracemalloc
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
import logging
from contextlib import contextmanager
import cProfile
import pstats
import io
from collections import defaultdict, deque
import weakref

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# NOTE: Task 35 - Adapter framework removed after v2.0 migration completion
# Performance baseline testing for adapters is no longer applicable
# try:
#     from ui.adapters import (
#         MainWindowAdapter, VideoInfoTabAdapter, DownloadedVideosTabAdapter,
#         EventBridgeCoordinator, get_global_coordinator
#     )
# except ImportError as e:
#     print(f"Warning: Could not import adapter components: {e}")
#     print("Some functionality may be limited")

print("WARNING: Adapter performance baseline is disabled after Task 35")
print("Adapter framework has been removed in v2.0 migration completion")

# Placeholder implementations for compatibility
class MainWindowAdapter:
    pass

class VideoInfoTabAdapter:
    pass

class DownloadedVideosTabAdapter:
    pass

class EventBridgeCoordinator:
    pass

def get_global_coordinator():
    return None


@dataclass
class PerformanceMetrics:
    """Container for comprehensive performance metrics"""
    
    # Timing metrics (milliseconds)
    initialization_time: float = 0.0
    event_processing_time: float = 0.0
    data_mapping_time: float = 0.0
    state_sync_time: float = 0.0
    total_operation_time: float = 0.0
    
    # Memory metrics (bytes)
    memory_usage_start: int = 0
    memory_usage_peak: int = 0
    memory_usage_end: int = 0
    memory_allocated: int = 0
    memory_deallocated: int = 0
    
    # CPU metrics (percentage)
    cpu_usage_avg: float = 0.0
    cpu_usage_peak: float = 0.0
    cpu_time_user: float = 0.0
    cpu_time_system: float = 0.0
    
    # Event system metrics
    events_processed: int = 0
    event_translation_time: float = 0.0
    event_cache_hits: int = 0
    event_cache_misses: int = 0
    event_errors: int = 0
    
    # Data mapping metrics
    mappings_performed: int = 0
    mapping_cache_hits: int = 0
    mapping_cache_misses: int = 0
    data_serialization_time: float = 0.0
    data_deserialization_time: float = 0.0
    
    # Adapter-specific metrics
    adapter_call_counts: Dict[str, int] = field(default_factory=dict)
    adapter_response_times: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))
    adapter_error_counts: Dict[str, int] = field(default_factory=dict)
    
    # System resource metrics
    thread_count: int = 0
    file_handles: int = 0
    network_connections: int = 0
    
    # Quality metrics
    success_rate: float = 100.0
    error_rate: float = 0.0
    reliability_score: float = 100.0
    
    # Test metadata
    test_start_time: datetime = field(default_factory=datetime.now)
    test_duration: float = 0.0
    test_conditions: Dict[str, Any] = field(default_factory=dict)
    environment_info: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class AdapterBenchmark:
    """Individual adapter performance benchmark"""
    
    adapter_name: str
    adapter_type: str
    
    # Performance measurements
    startup_time: float = 0.0
    method_call_times: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))
    memory_footprint: int = 0
    event_throughput: float = 0.0
    data_processing_rate: float = 0.0
    
    # Resource usage
    cpu_usage: float = 0.0
    memory_allocations: int = 0
    gc_collections: int = 0
    
    # Quality metrics
    errors_encountered: int = 0
    recovery_attempts: int = 0
    stability_score: float = 100.0


class AdapterPerformanceProfiler:
    """
    Comprehensive performance profiler for adapter framework components
    """
    
    def __init__(self, output_dir: str = "scripts_dev/performance_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up logging
        self.logger = self._setup_logging()
        
        # Performance tracking
        self.metrics = PerformanceMetrics()
        self.benchmarks: Dict[str, AdapterBenchmark] = {}
        self.profiler_data: Dict[str, Any] = {}
        
        # Monitoring state
        self._monitoring_active = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._cpu_samples: deque = deque(maxlen=1000)
        self._memory_samples: deque = deque(maxlen=1000)
        
        # Test adapters
        self._test_adapters: Dict[str, Any] = {}
        self._original_methods: Dict[str, Dict[str, Callable]] = defaultdict(dict)
        
        # System info
        self._collect_environment_info()
        
        self.logger.info("AdapterPerformanceProfiler initialized")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up performance profiler logging"""
        logger = logging.getLogger("adapter_performance")
        logger.setLevel(logging.DEBUG)
        
        # File handler
        log_file = self.output_dir / f"performance_baseline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler  
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def _collect_environment_info(self) -> None:
        """Collect system environment information"""
        try:
            self.metrics.environment_info = {
                "python_version": sys.version,
                "platform": sys.platform,
                "cpu_count": os.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "disk_space": psutil.disk_usage('/').total if os.name != 'nt' else psutil.disk_usage('C:').total,
                "hostname": os.uname().nodename if hasattr(os, 'uname') else 'Unknown',
                "timestamp": datetime.now().isoformat()
            }
            
            # Process info
            process = psutil.Process()
            self.metrics.environment_info.update({
                "process_id": process.pid,
                "process_name": process.name(),
                "process_threads": process.num_threads(),
                "process_memory": process.memory_info().rss
            })
            
        except Exception as e:
            self.logger.warning(f"Could not collect full environment info: {e}")
    
    def start_baseline_measurement(self) -> None:
        """Start comprehensive baseline measurement"""
        self.logger.info(">> Starting adapter framework performance baseline measurement")
        
        # Initialize metrics
        self.metrics.test_start_time = datetime.now()
        self.metrics.memory_usage_start = psutil.virtual_memory().used
        
        # Start memory and CPU monitoring
        self._start_resource_monitoring()
        
        # Enable tracemalloc for detailed memory tracking
        tracemalloc.start()
        
        # Trigger garbage collection for clean baseline
        gc.collect()
        
        self.logger.info("Baseline measurement started successfully")
    
    def _start_resource_monitoring(self) -> None:
        """Start background resource monitoring"""
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        self._monitor_thread = threading.Thread(target=self._monitor_resources, daemon=True)
        self._monitor_thread.start()
        
        self.logger.debug("Resource monitoring thread started")
    
    def _monitor_resources(self) -> None:
        """Background thread for continuous resource monitoring"""
        while self._monitoring_active:
            try:
                # Sample CPU and memory
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory_info = psutil.virtual_memory()
                
                self._cpu_samples.append((time.time(), cpu_percent))
                self._memory_samples.append((time.time(), memory_info.used))
                
                # Update peak values
                if cpu_percent > self.metrics.cpu_usage_peak:
                    self.metrics.cpu_usage_peak = cpu_percent
                
                if memory_info.used > self.metrics.memory_usage_peak:
                    self.metrics.memory_usage_peak = memory_info.used
                
                time.sleep(0.5)  # Sample every 500ms
                
            except Exception as e:
                self.logger.error(f"Error in resource monitoring: {e}")
                break
    
    @contextmanager
    def profile_operation(self, operation_name: str):
        """Context manager for profiling specific operations"""
        start_time = time.perf_counter()
        start_memory = psutil.virtual_memory().used
        
        # Start profiling
        profiler = cProfile.Profile()
        profiler.enable()
        
        try:
            self.logger.debug(f"Starting profiling for operation: {operation_name}")
            yield
            
        finally:
            # Stop profiling
            profiler.disable()
            
            # Calculate metrics
            end_time = time.perf_counter()
            end_memory = psutil.virtual_memory().used
            operation_time = (end_time - start_time) * 1000  # Convert to ms
            memory_delta = end_memory - start_memory
            
            # Store profiling data
            profiler_output = io.StringIO()
            stats = pstats.Stats(profiler, stream=profiler_output)
            stats.sort_stats('cumulative')
            stats.print_stats(20)  # Top 20 functions
            
            self.profiler_data[operation_name] = {
                "execution_time": operation_time,
                "memory_delta": memory_delta,
                "profile_output": profiler_output.getvalue(),
                "timestamp": datetime.now().isoformat()
            }
            
            self.logger.info(f"[OK] Operation '{operation_name}' completed in {operation_time:.2f}ms")
    
    def measure_adapter_initialization(self) -> None:
        """Measure adapter initialization performance"""
        self.logger.info("[*] Measuring adapter initialization performance...")
        
        with self.profile_operation("adapter_initialization"):
            start_time = time.perf_counter()
            
            try:
                # Test MainWindow adapter
                main_adapter_start = time.perf_counter()
                main_adapter = MainWindowAdapter()
                main_adapter_time = (time.perf_counter() - main_adapter_start) * 1000
                
                self.benchmarks["main_window"] = AdapterBenchmark(
                    adapter_name="MainWindowAdapter",
                    adapter_type="main_window",
                    startup_time=main_adapter_time
                )
                self._test_adapters["main_window"] = main_adapter
                
                # Test VideoInfoTab adapter
                video_adapter_start = time.perf_counter()
                video_adapter = VideoInfoTabAdapter()
                video_adapter_time = (time.perf_counter() - video_adapter_start) * 1000
                
                self.benchmarks["video_info_tab"] = AdapterBenchmark(
                    adapter_name="VideoInfoTabAdapter", 
                    adapter_type="video_info_tab",
                    startup_time=video_adapter_time
                )
                self._test_adapters["video_info_tab"] = video_adapter
                
                # Test DownloadedVideosTab adapter
                download_adapter_start = time.perf_counter()
                download_adapter = DownloadedVideosTabAdapter()
                download_adapter_time = (time.perf_counter() - download_adapter_start) * 1000
                
                self.benchmarks["downloaded_videos_tab"] = AdapterBenchmark(
                    adapter_name="DownloadedVideosTabAdapter",
                    adapter_type="downloaded_videos_tab", 
                    startup_time=download_adapter_time
                )
                self._test_adapters["downloaded_videos_tab"] = download_adapter
                
                total_init_time = (time.perf_counter() - start_time) * 1000
                self.metrics.initialization_time = total_init_time
                
                self.logger.info(f"[OK] Adapter initialization completed in {total_init_time:.2f}ms")
                
            except Exception as e:
                self.logger.error(f"[ERROR] Adapter initialization failed: {e}")
                self.metrics.error_rate += 1
    
    def measure_event_system_performance(self) -> None:
        """Measure event system performance"""
        self.logger.info("[*] Measuring event system performance...")
        
        with self.profile_operation("event_system_performance"):
            try:
                # Get event coordinator
                coordinator = get_global_coordinator()
                
                if not coordinator:
                    self.logger.warning("Event coordinator not available")
                    return
                
                # Test event processing performance
                event_start = time.perf_counter()
                
                # Simulate typical event processing
                test_events = [
                    ("video_download_started", {"video_id": "test_001", "url": "https://example.com"}),
                    ("video_download_progress", {"video_id": "test_001", "progress": 50}),
                    ("video_download_completed", {"video_id": "test_001", "file_path": "/downloads/test.mp4"}),
                    ("ui_tab_switched", {"from_tab": "video_info", "to_tab": "downloads"}),
                    ("configuration_changed", {"setting": "download_quality", "value": "1080p"})
                ]
                
                for event_name, event_data in test_events:
                    coordinator.emit_legacy_event(event_name, event_data)
                    self.metrics.events_processed += 1
                
                event_time = (time.perf_counter() - event_start) * 1000
                self.metrics.event_processing_time = event_time
                
                # Get event metrics from coordinator
                if hasattr(coordinator, 'get_metrics'):
                    event_metrics = coordinator.get_metrics()
                    self.metrics.event_cache_hits = event_metrics.get('cache_hits', 0)
                    self.metrics.event_errors = event_metrics.get('translation_errors', 0)
                
                self.logger.info(f"[OK] Event system performance measured: {event_time:.2f}ms for {len(test_events)} events")
                
            except Exception as e:
                self.logger.error(f"[ERROR] Event system measurement failed: {e}")
                self.metrics.error_rate += 1
    
    def measure_data_mapping_performance(self) -> None:
        """Measure data mapping performance"""
        self.logger.info("[*] Measuring data mapping performance...")
        
        with self.profile_operation("data_mapping_performance"):
            try:
                # Get data mappers
                video_mapper = get_video_mapper()
                download_mapper = get_download_mapper()
                
                # Test data for performance testing
                test_video_data = {
                    "url": "https://example.com/video/test",
                    "title": "Test Video Performance",
                    "creator": "Test Creator",
                    "duration": "300",
                    "quality": "1080p",
                    "format": "mp4",
                    "size": "100MB",
                    "hashtags": ["test", "performance"],
                    "platform": "youtube"
                }
                
                test_download_data = {
                    "video_url": "https://example.com/video/test",
                    "title": "Test Download Performance",
                    "creator": "Test Creator",
                    "quality": "1080p",
                    "format": "mp4",
                    "size": "100MB",
                    "status": "completed",
                    "date": "2024-01-01",
                    "platform": "youtube"
                }
                
                mapping_start = time.perf_counter()
                
                # Test video data mapping performance
                video_serialized = video_mapper.serialize_video_data(test_video_data)
                video_deserialized = video_mapper.deserialize_video_data(video_serialized)
                v2_video = video_mapper.map_to_v2(test_video_data)
                legacy_video = video_mapper.map_to_legacy(v2_video) if v2_video else None
                
                # Test download data mapping performance
                download_serialized = download_mapper.serialize_download_data(test_download_data)
                download_deserialized = download_mapper.deserialize_download_data(download_serialized)
                v2_download = download_mapper.map_to_v2(test_download_data)
                legacy_download = download_mapper.map_to_legacy(v2_download) if v2_download else None
                
                mapping_time = (time.perf_counter() - mapping_start) * 1000
                self.metrics.data_mapping_time = mapping_time
                self.metrics.mappings_performed = 8  # 8 operations performed
                
                self.logger.info(f"[OK] Data mapping performance measured: {mapping_time:.2f}ms for {self.metrics.mappings_performed} operations")
                
            except Exception as e:
                self.logger.error(f"[ERROR] Data mapping measurement failed: {e}")
                self.metrics.error_rate += 1
    
    def measure_memory_usage_patterns(self) -> None:
        """Measure detailed memory usage patterns"""
        self.logger.info("📊 Measuring memory usage patterns...")
        
        try:
            # Get current memory snapshot
            if tracemalloc.is_tracing():
                snapshot = tracemalloc.take_snapshot()
                top_stats = snapshot.statistics('lineno')
                
                # Analyze top memory consumers
                memory_analysis = {
                    "top_memory_consumers": [],
                    "total_memory_traced": sum(stat.size for stat in top_stats),
                    "memory_blocks": len(top_stats)
                }
                
                for stat in top_stats[:10]:  # Top 10 memory consumers
                    memory_analysis["top_memory_consumers"].append({
                        "file": stat.traceback.format()[-1] if stat.traceback else "Unknown",
                        "size_mb": stat.size / 1024 / 1024,
                        "count": stat.count
                    })
                
                self.profiler_data["memory_analysis"] = memory_analysis
            
            # Check for memory leaks
            gc.collect()  # Force garbage collection
            self.metrics.memory_usage_end = psutil.virtual_memory().used
            
            # Calculate memory delta
            memory_delta = self.metrics.memory_usage_end - self.metrics.memory_usage_start
            self.metrics.memory_allocated = max(0, memory_delta)
            
            self.logger.info(f"✅ Memory usage analysis completed. Delta: {memory_delta / 1024 / 1024:.2f}MB")
            
        except Exception as e:
            self.logger.error(f"❌ Memory analysis failed: {e}")
    
    def finish_baseline_measurement(self) -> None:
        """Complete baseline measurement and generate report"""
        self.logger.info("🏁 Finishing baseline measurement...")
        
        try:
            # Stop resource monitoring
            self._monitoring_active = False
            if self._monitor_thread and self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=2.0)
            
            # Calculate final metrics
            self.metrics.test_duration = (datetime.now() - self.metrics.test_start_time).total_seconds()
            
            # Calculate average CPU usage
            if self._cpu_samples:
                cpu_values = [sample[1] for sample in self._cpu_samples]
                self.metrics.cpu_usage_avg = sum(cpu_values) / len(cpu_values)
            
            # Calculate success rate
            total_operations = (self.metrics.events_processed + 
                              self.metrics.mappings_performed + 
                              len(self.benchmarks))
            
            if total_operations > 0:
                error_operations = self.metrics.error_rate
                self.metrics.success_rate = ((total_operations - error_operations) / total_operations) * 100
                self.metrics.reliability_score = max(0, 100 - (error_operations * 10))
            
            # Final memory measurement
            self.measure_memory_usage_patterns()
            
            # Stop memory tracing
            if tracemalloc.is_tracing():
                tracemalloc.stop()
            
            self.logger.info("✅ Baseline measurement completed successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Error finishing baseline measurement: {e}")
    
    def generate_baseline_report(self) -> Dict[str, Any]:
        """Generate comprehensive baseline performance report"""
        self.logger.info("📝 Generating baseline performance report...")
        
        report = {
            "metadata": {
                "report_type": "adapter_framework_baseline",
                "generated_at": datetime.now().isoformat(),
                "test_duration_seconds": self.metrics.test_duration,
                "environment": self.metrics.environment_info
            },
            
            "performance_summary": {
                "initialization_time_ms": self.metrics.initialization_time,
                "event_processing_time_ms": self.metrics.event_processing_time,
                "data_mapping_time_ms": self.metrics.data_mapping_time,
                "memory_usage_mb": {
                    "start": self.metrics.memory_usage_start / 1024 / 1024,
                    "peak": self.metrics.memory_usage_peak / 1024 / 1024,
                    "end": self.metrics.memory_usage_end / 1024 / 1024,
                    "allocated": self.metrics.memory_allocated / 1024 / 1024
                },
                "cpu_usage_percent": {
                    "average": self.metrics.cpu_usage_avg,
                    "peak": self.metrics.cpu_usage_peak
                },
                "success_rate_percent": self.metrics.success_rate,
                "reliability_score": self.metrics.reliability_score
            },
            
            "adapter_benchmarks": {},
            
            "event_system_metrics": {
                "events_processed": self.metrics.events_processed,
                "processing_time_ms": self.metrics.event_processing_time,
                "cache_hits": self.metrics.event_cache_hits,
                "cache_misses": self.metrics.event_cache_misses,
                "errors": self.metrics.event_errors,
                "throughput_events_per_second": (
                    self.metrics.events_processed / (self.metrics.event_processing_time / 1000)
                    if self.metrics.event_processing_time > 0 else 0
                )
            },
            
            "data_mapping_metrics": {
                "mappings_performed": self.metrics.mappings_performed,
                "processing_time_ms": self.metrics.data_mapping_time,
                "cache_hits": self.metrics.mapping_cache_hits,
                "cache_misses": self.metrics.mapping_cache_misses,
                "throughput_mappings_per_second": (
                    self.metrics.mappings_performed / (self.metrics.data_mapping_time / 1000)
                    if self.metrics.data_mapping_time > 0 else 0
                )
            },
            
            "profiling_data": self.profiler_data,
            
            "optimization_recommendations": []
        }
        
        # Add adapter benchmark details
        for adapter_id, benchmark in self.benchmarks.items():
            report["adapter_benchmarks"][adapter_id] = asdict(benchmark)
        
        # Generate optimization recommendations
        recommendations = self._generate_optimization_recommendations()
        report["optimization_recommendations"] = recommendations
        
        # Save report to file
        report_file = self.output_dir / f"adapter_baseline_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"📊 Baseline report saved to: {report_file}")
        
        return report
    
    def _generate_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Generate optimization recommendations based on baseline measurements"""
        recommendations = []
        
        # Check initialization time
        if self.metrics.initialization_time > 1000:  # > 1 second
            recommendations.append({
                "category": "initialization",
                "priority": "high",
                "issue": "Slow adapter initialization",
                "current_value": f"{self.metrics.initialization_time:.2f}ms",
                "target_value": "< 500ms",
                "recommendation": "Optimize adapter initialization by implementing lazy loading and reducing import overhead",
                "impact": "20-40% improvement in startup time"
            })
        
        # Check event processing performance
        if self.metrics.events_processed > 0:
            event_rate = self.metrics.events_processed / (self.metrics.event_processing_time / 1000)
            if event_rate < 100:  # < 100 events/second
                recommendations.append({
                    "category": "event_system",
                    "priority": "medium",
                    "issue": "Low event processing throughput",
                    "current_value": f"{event_rate:.1f} events/second",
                    "target_value": "> 200 events/second",
                    "recommendation": "Implement event batching and optimize event translation cache",
                    "impact": "50-100% improvement in event throughput"
                })
        
        # Check memory usage
        memory_allocated_mb = self.metrics.memory_allocated / 1024 / 1024
        if memory_allocated_mb > 100:  # > 100MB allocated
            recommendations.append({
                "category": "memory",
                "priority": "high",
                "issue": "High memory allocation",
                "current_value": f"{memory_allocated_mb:.1f}MB",
                "target_value": "< 50MB",
                "recommendation": "Implement object pooling and optimize data structure usage",
                "impact": "30-50% reduction in memory footprint"
            })
        
        # Check data mapping performance
        if self.metrics.mappings_performed > 0:
            mapping_rate = self.metrics.mappings_performed / (self.metrics.data_mapping_time / 1000)
            if mapping_rate < 500:  # < 500 mappings/second
                recommendations.append({
                    "category": "data_mapping", 
                    "priority": "medium",
                    "issue": "Slow data mapping performance",
                    "current_value": f"{mapping_rate:.1f} mappings/second",
                    "target_value": "> 1000 mappings/second",
                    "recommendation": "Implement mapping result caching and optimize serialization",
                    "impact": "40-60% improvement in data processing speed"
                })
        
        # Check error rate
        if self.metrics.error_rate > 0:
            recommendations.append({
                "category": "reliability",
                "priority": "critical",
                "issue": "Errors detected during baseline testing",
                "current_value": f"{self.metrics.error_rate} errors",
                "target_value": "0 errors",
                "recommendation": "Investigate and fix error sources, implement better error handling",
                "impact": "Improved stability and reliability"
            })
        
        return recommendations
    
    def print_summary(self) -> None:
        """Print a summary of the baseline measurement results"""
        try:
            print("\n" + "="*80)
            print("ADAPTER FRAMEWORK PERFORMANCE BASELINE SUMMARY")
            print("="*80)
            
            print("\n[INITIALIZATION PERFORMANCE]")
            print(f"  Total initialization time: {self.metrics.initialization_time:.2f}ms")
            
            for adapter_name, benchmark in self.benchmarks.items():
                print(f"  {benchmark.adapter_name}: {benchmark.startup_time:.2f}ms")
            
            print("\n[EVENT SYSTEM PERFORMANCE]")
            print(f"  Event processing time: {self.metrics.event_processing_time:.2f}ms")
            print(f"  Events processed: {self.metrics.events_processed}")
            print(f"  Event cache hits: {self.metrics.event_cache_hits}")
            
            print("\n[DATA MAPPING PERFORMANCE]")
            print(f"  Data mapping time: {self.metrics.data_mapping_time:.2f}ms")
            print(f"  Mappings performed: {self.metrics.mappings_performed}")
            
            print("\n[MEMORY USAGE]")
            print(f"  Peak memory: {self.metrics.memory_usage_peak / 1024 / 1024:.2f}MB")
            print(f"  Current memory: {self.metrics.memory_usage_end / 1024 / 1024:.2f}MB")
            print(f"  RSS memory: {psutil.Process().memory_info().rss / 1024 / 1024:.2f}MB")
            
            print("\n[OVERALL METRICS]")
            print(f"  Test duration: {self.metrics.test_duration:.2f}ms")
            print(f"  Success rate: {self.metrics.success_rate:.1f}%")
            print(f"  CPU usage: {self.metrics.cpu_usage_avg:.1f}%")
            print(f"  Error count: {self.metrics.error_rate}")
            
            print("\n" + "="*80)
            print("[RESULT] BASELINE MEASUREMENT COMPLETED")
            print("="*80 + "\n")
            
        except Exception as e:
            print(f"[ERROR] Failed to print summary: {e}")


def run_comprehensive_baseline() -> PerformanceMetrics:
    """
    Run comprehensive baseline measurement for adapter framework
    
    Returns:
        PerformanceMetrics: Complete performance baseline data
    """
    profiler = AdapterPerformanceProfiler()
    
    try:
        # Start baseline measurement
        profiler.start_baseline_measurement()
        
        # Run all measurement phases
        profiler.measure_adapter_initialization()
        profiler.measure_event_system_performance()  
        profiler.measure_data_mapping_performance()
        
        # Finish measurement
        profiler.finish_baseline_measurement()
        
        # Generate and save report
        report = profiler.generate_baseline_report()
        
        # Print summary
        profiler.print_summary()
        
        return profiler.metrics
        
    except Exception as e:
        profiler.logger.error(f"❌ Baseline measurement failed: {e}")
        raise


if __name__ == "__main__":
    print("🚀 Starting Adapter Framework Performance Baseline Measurement...")
    print("This will measure current performance to establish optimization targets.\n")
    
    try:
        metrics = run_comprehensive_baseline()
        print("\n✅ Baseline measurement completed successfully!")
        print("\n📁 Check scripts_dev/performance_results/ for detailed reports.")
        
    except Exception as e:
        print(f"\n❌ Baseline measurement failed: {e}")
        print("Check logs for details.")
        sys.exit(1) 