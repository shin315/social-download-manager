#!/usr/bin/env python3
"""
Memory Management Optimization System for Adapter Framework
===========================================================

This module provides comprehensive memory management optimization including:
- Memory usage profiling and analysis
- Garbage collection optimization
- Object lifecycle management
- Memory leak detection and prevention
- Cache optimization with memory-aware policies
- Resource pooling and reuse strategies
- Memory usage monitoring and alerting
"""

import gc
import json
import logging
import os
import psutil
import sys
import threading
import time
import tracemalloc
import weakref
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union, Callable
import uuid

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class MemorySnapshot:
    """Memory usage snapshot at a specific point in time"""
    timestamp: datetime = field(default_factory=datetime.now)
    rss_mb: float = 0.0  # Resident Set Size
    vms_mb: float = 0.0  # Virtual Memory Size
    percent: float = 0.0  # Memory percentage
    available_mb: float = 0.0
    tracemalloc_current_mb: float = 0.0
    tracemalloc_peak_mb: float = 0.0
    gc_stats: Dict[str, Any] = field(default_factory=dict)
    object_counts: Dict[str, int] = field(default_factory=dict)
    thread_count: int = 0


@dataclass
class MemoryOptimizationConfig:
    """Configuration for memory optimization"""
    gc_threshold_0: int = 700
    gc_threshold_1: int = 10
    gc_threshold_2: int = 10
    max_cache_size_mb: float = 100.0
    memory_warning_threshold: float = 80.0  # Percentage
    memory_critical_threshold: float = 90.0  # Percentage
    snapshot_interval: int = 30  # seconds
    enable_tracemalloc: bool = True
    object_tracking_enabled: bool = True
    weak_reference_cleanup: bool = True


class MemoryProfiler:
    """Advanced memory profiling and analysis"""
    
    def __init__(self, config: MemoryOptimizationConfig):
        self.config = config
        self.snapshots = deque(maxlen=1000)
        self.memory_alerts = deque(maxlen=100)
        self.is_profiling = False
        self.profile_thread = None
        self.lock = threading.RLock()
        
        if self.config.enable_tracemalloc:
            tracemalloc.start()
    
    def start_profiling(self):
        """Start continuous memory profiling"""
        if self.is_profiling:
            return
        
        self.is_profiling = True
        self.profile_thread = threading.Thread(target=self._profiling_loop, daemon=True)
        self.profile_thread.start()
        logger.info("Memory profiling started")
    
    def stop_profiling(self):
        """Stop memory profiling"""
        self.is_profiling = False
        if self.profile_thread:
            self.profile_thread.join(timeout=5.0)
        logger.info("Memory profiling stopped")
    
    def _profiling_loop(self):
        """Main profiling loop"""
        while self.is_profiling:
            try:
                snapshot = self.take_snapshot()
                self._analyze_snapshot(snapshot)
                time.sleep(self.config.snapshot_interval)
            except Exception as e:
                logger.error(f"Error in profiling loop: {e}")
                time.sleep(5)
    
    def take_snapshot(self) -> MemorySnapshot:
        """Take a memory usage snapshot"""
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_percent = process.memory_percent()
        system_memory = psutil.virtual_memory()
        
        snapshot = MemorySnapshot(
            rss_mb=memory_info.rss / 1024 / 1024,
            vms_mb=memory_info.vms / 1024 / 1024,
            percent=memory_percent,
            available_mb=system_memory.available / 1024 / 1024,
            thread_count=threading.active_count()
        )
        
        # Tracemalloc stats
        if self.config.enable_tracemalloc:
            current, peak = tracemalloc.get_traced_memory()
            snapshot.tracemalloc_current_mb = current / 1024 / 1024
            snapshot.tracemalloc_peak_mb = peak / 1024 / 1024
        
        # Garbage collection stats
        snapshot.gc_stats = {
            'counts': gc.get_count(),
            'stats': gc.get_stats(),
            'threshold': gc.get_threshold()
        }
        
        # Object counting
        if self.config.object_tracking_enabled:
            snapshot.object_counts = self._count_objects()
        
        with self.lock:
            self.snapshots.append(snapshot)
        
        return snapshot
    
    def _count_objects(self) -> Dict[str, int]:
        """Count objects by type"""
        counts = defaultdict(int)
        for obj in gc.get_objects():
            obj_type = type(obj).__name__
            counts[obj_type] += 1
        
        # Return top 20 most common object types
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True)[:20])
    
    def _analyze_snapshot(self, snapshot: MemorySnapshot):
        """Analyze snapshot for potential issues"""
        if snapshot.percent > self.config.memory_critical_threshold:
            alert = {
                'level': 'CRITICAL',
                'message': f'Memory usage critical: {snapshot.percent:.1f}%',
                'timestamp': snapshot.timestamp,
                'details': snapshot
            }
            self.memory_alerts.append(alert)
            logger.critical(alert['message'])
        elif snapshot.percent > self.config.memory_warning_threshold:
            alert = {
                'level': 'WARNING',
                'message': f'Memory usage high: {snapshot.percent:.1f}%',
                'timestamp': snapshot.timestamp,
                'details': snapshot
            }
            self.memory_alerts.append(alert)
            logger.warning(alert['message'])
    
    def get_memory_trend(self, duration_minutes: int = 30) -> Dict[str, Any]:
        """Get memory usage trend over specified duration"""
        cutoff = datetime.now() - timedelta(minutes=duration_minutes)
        recent_snapshots = [s for s in self.snapshots if s.timestamp >= cutoff]
        
        if len(recent_snapshots) < 2:
            return {'error': 'Insufficient data for trend analysis'}
        
        first_snapshot = recent_snapshots[0]
        last_snapshot = recent_snapshots[-1]
        
        return {
            'duration_minutes': duration_minutes,
            'snapshots_count': len(recent_snapshots),
            'memory_change_mb': last_snapshot.rss_mb - first_snapshot.rss_mb,
            'memory_change_percent': last_snapshot.percent - first_snapshot.percent,
            'peak_memory_mb': max(s.rss_mb for s in recent_snapshots),
            'average_memory_mb': sum(s.rss_mb for s in recent_snapshots) / len(recent_snapshots),
            'gc_collections': sum(sum(s.gc_stats.get('counts', [])) for s in recent_snapshots)
        }
    
    def detect_memory_leaks(self) -> List[Dict[str, Any]]:
        """Detect potential memory leaks"""
        leaks = []
        
        if len(self.snapshots) < 10:
            return leaks
        
        # Check for consistent memory growth
        recent_snapshots = list(self.snapshots)[-10:]
        memory_values = [s.rss_mb for s in recent_snapshots]
        
        # Simple linear regression to detect trend
        n = len(memory_values)
        x_sum = sum(range(n))
        y_sum = sum(memory_values)
        xy_sum = sum(i * memory_values[i] for i in range(n))
        x2_sum = sum(i * i for i in range(n))
        
        slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum)
        
        if slope > 1.0:  # Memory growing by > 1MB per snapshot
            leaks.append({
                'type': 'consistent_growth',
                'severity': 'high' if slope > 5.0 else 'medium',
                'growth_rate_mb_per_snapshot': slope,
                'estimated_growth_mb_per_hour': slope * (3600 / self.config.snapshot_interval)
            })
        
        # Check for object count growth
        if len(recent_snapshots) >= 5:
            first_counts = recent_snapshots[0].object_counts
            last_counts = recent_snapshots[-1].object_counts
            
            for obj_type, last_count in last_counts.items():
                first_count = first_counts.get(obj_type, 0)
                if last_count > first_count * 2 and last_count > 1000:
                    leaks.append({
                        'type': 'object_growth',
                        'object_type': obj_type,
                        'growth_factor': last_count / max(first_count, 1),
                        'current_count': last_count
                    })
        
        return leaks


class GarbageCollectionOptimizer:
    """Garbage collection optimization and tuning"""
    
    def __init__(self, config: MemoryOptimizationConfig):
        self.config = config
        self.original_threshold = gc.get_threshold()
        self.gc_stats_history = deque(maxlen=100)
        
    def optimize_gc_settings(self):
        """Optimize garbage collection settings"""
        logger.info("Optimizing garbage collection settings")
        
        # Set optimized thresholds
        gc.set_threshold(
            self.config.gc_threshold_0,
            self.config.gc_threshold_1,
            self.config.gc_threshold_2
        )
        
        # Enable garbage collection debugging if needed
        # gc.set_debug(gc.DEBUG_STATS)
        
        logger.info(f"GC thresholds set to: {gc.get_threshold()}")
    
    def force_full_gc(self) -> Dict[str, Any]:
        """Force full garbage collection and return stats"""
        logger.info("Forcing full garbage collection")
        
        before_stats = self._get_gc_stats()
        
        # Collect all generations
        collected = []
        for generation in range(3):
            collected.append(gc.collect(generation))
        
        after_stats = self._get_gc_stats()
        
        result = {
            'timestamp': datetime.now(),
            'objects_collected': collected,
            'total_collected': sum(collected),
            'before_stats': before_stats,
            'after_stats': after_stats
        }
        
        self.gc_stats_history.append(result)
        logger.info(f"GC completed, collected {sum(collected)} objects")
        
        return result
    
    def _get_gc_stats(self) -> Dict[str, Any]:
        """Get current garbage collection statistics"""
        return {
            'counts': gc.get_count(),
            'stats': gc.get_stats(),
            'threshold': gc.get_threshold(),
            'objects': len(gc.get_objects())
        }
    
    def get_gc_recommendations(self) -> List[str]:
        """Get GC optimization recommendations"""
        recommendations = []
        
        if len(self.gc_stats_history) >= 5:
            recent_collections = list(self.gc_stats_history)[-5:]
            avg_collected = sum(sum(gc['objects_collected']) for gc in recent_collections) / 5
            
            if avg_collected > 1000:
                recommendations.append("Consider increasing GC threshold 0 to reduce collection frequency")
            elif avg_collected < 100:
                recommendations.append("Consider decreasing GC threshold 0 to collect more aggressively")
        
        current_counts = gc.get_count()
        thresholds = gc.get_threshold()
        
        for i, (count, threshold) in enumerate(zip(current_counts, thresholds)):
            if count > threshold * 0.8:
                recommendations.append(f"Generation {i} is near threshold ({count}/{threshold})")
        
        return recommendations
    
    def restore_original_settings(self):
        """Restore original GC settings"""
        gc.set_threshold(*self.original_threshold)
        logger.info(f"GC thresholds restored to: {gc.get_threshold()}")


class ObjectLifecycleManager:
    """Manage object lifecycles and prevent memory leaks"""
    
    def __init__(self):
        self.tracked_objects = weakref.WeakValueDictionary()
        self.object_registry = defaultdict(list)
        self.cleanup_callbacks = defaultdict(list)
        self.lock = threading.RLock()
    
    def register_object(self, obj: Any, category: str = "default", 
                       cleanup_callback: Optional[Callable] = None) -> str:
        """Register an object for lifecycle tracking"""
        obj_id = str(uuid.uuid4())
        
        with self.lock:
            self.tracked_objects[obj_id] = obj
            self.object_registry[category].append(obj_id)
            
            if cleanup_callback:
                self.cleanup_callbacks[obj_id].append(cleanup_callback)
        
        return obj_id
    
    def unregister_object(self, obj_id: str):
        """Unregister an object and run cleanup callbacks"""
        with self.lock:
            # Run cleanup callbacks
            for callback in self.cleanup_callbacks.get(obj_id, []):
                try:
                    callback()
                except Exception as e:
                    logger.error(f"Error in cleanup callback: {e}")
            
            # Remove from registry
            for category_objects in self.object_registry.values():
                if obj_id in category_objects:
                    category_objects.remove(obj_id)
            
            # Remove callbacks
            self.cleanup_callbacks.pop(obj_id, None)
            
            # Object will be removed from tracked_objects automatically
            # when it's garbage collected (weak reference)
    
    def cleanup_category(self, category: str):
        """Cleanup all objects in a category"""
        with self.lock:
            obj_ids = self.object_registry.get(category, []).copy()
            
        for obj_id in obj_ids:
            self.unregister_object(obj_id)
        
        logger.info(f"Cleaned up {len(obj_ids)} objects in category '{category}'")
    
    def get_object_stats(self) -> Dict[str, Any]:
        """Get object lifecycle statistics"""
        with self.lock:
            return {
                'total_tracked_objects': len(self.tracked_objects),
                'objects_by_category': {
                    category: len(obj_ids) 
                    for category, obj_ids in self.object_registry.items()
                },
                'objects_with_callbacks': len(self.cleanup_callbacks)
            }


class MemoryAwareCache:
    """Memory-aware cache with intelligent eviction policies"""
    
    def __init__(self, max_size_mb: float = 50.0):
        self.max_size_mb = max_size_mb
        self.cache = {}
        self.access_times = {}
        self.access_counts = defaultdict(int)
        self.size_estimates = {}
        self.lock = threading.RLock()
    
    def put(self, key: str, value: Any):
        """Store value in cache"""
        with self.lock:
            size_estimate = self._estimate_size(value)
            
            # Check if we need to evict items
            self._ensure_capacity(size_estimate)
            
            self.cache[key] = value
            self.access_times[key] = time.time()
            self.access_counts[key] += 1
            self.size_estimates[key] = size_estimate
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self.lock:
            if key in self.cache:
                self.access_times[key] = time.time()
                self.access_counts[key] += 1
                return self.cache[key]
            return None
    
    def remove(self, key: str):
        """Remove item from cache"""
        with self.lock:
            self.cache.pop(key, None)
            self.access_times.pop(key, None)
            self.access_counts.pop(key, None)
            self.size_estimates.pop(key, None)
    
    def clear(self):
        """Clear entire cache"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
            self.access_counts.clear()
            self.size_estimates.clear()
    
    def _estimate_size(self, obj: Any) -> float:
        """Estimate object size in MB"""
        try:
            return sys.getsizeof(obj) / 1024 / 1024
        except:
            return 0.1  # Default estimate
    
    def _ensure_capacity(self, new_item_size: float):
        """Ensure cache has capacity for new item"""
        current_size = sum(self.size_estimates.values())
        
        while current_size + new_item_size > self.max_size_mb and self.cache:
            # Use LFU (Least Frequently Used) eviction
            lfu_key = min(self.access_counts.keys(), key=lambda k: self.access_counts[k])
            
            logger.debug(f"Evicting cache item: {lfu_key}")
            current_size -= self.size_estimates.get(lfu_key, 0)
            self.remove(lfu_key)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            return {
                'total_items': len(self.cache),
                'estimated_size_mb': sum(self.size_estimates.values()),
                'max_size_mb': self.max_size_mb,
                'utilization_percent': (sum(self.size_estimates.values()) / self.max_size_mb) * 100,
                'average_access_count': sum(self.access_counts.values()) / len(self.access_counts) if self.access_counts else 0
            }


class MemoryOptimizationOrchestrator:
    """Main orchestrator for memory optimization"""
    
    def __init__(self, config: MemoryOptimizationConfig = None):
        self.config = config or MemoryOptimizationConfig()
        self.profiler = MemoryProfiler(self.config)
        self.gc_optimizer = GarbageCollectionOptimizer(self.config)
        self.lifecycle_manager = ObjectLifecycleManager()
        self.cache = MemoryAwareCache(self.config.max_cache_size_mb)
        self.optimization_history = deque(maxlen=100)
        
    def start_optimization(self):
        """Start memory optimization"""
        logger.info("Starting memory optimization")
        
        # Start profiling
        self.profiler.start_profiling()
        
        # Optimize GC settings
        self.gc_optimizer.optimize_gc_settings()
        
        # Take initial snapshot
        initial_snapshot = self.profiler.take_snapshot()
        logger.info(f"Initial memory usage: {initial_snapshot.rss_mb:.1f}MB ({initial_snapshot.percent:.1f}%)")
        
        return initial_snapshot
    
    def stop_optimization(self):
        """Stop memory optimization and restore settings"""
        logger.info("Stopping memory optimization")
        
        self.profiler.stop_profiling()
        self.gc_optimizer.restore_original_settings()
        
        final_snapshot = self.profiler.take_snapshot()
        logger.info(f"Final memory usage: {final_snapshot.rss_mb:.1f}MB ({final_snapshot.percent:.1f}%)")
        
        return final_snapshot
    
    def run_memory_optimization_cycle(self) -> Dict[str, Any]:
        """Run a complete memory optimization cycle"""
        logger.info("Running memory optimization cycle")
        
        start_time = time.time()
        before_snapshot = self.profiler.take_snapshot()
        
        optimizations_performed = []
        
        # 1. Force garbage collection
        gc_result = self.gc_optimizer.force_full_gc()
        optimizations_performed.append("garbage_collection")
        
        # 2. Clean up weak references
        if self.config.weak_reference_cleanup:
            initial_tracked = len(self.lifecycle_manager.tracked_objects)
            # Trigger weakref cleanup by accessing the dictionary
            list(self.lifecycle_manager.tracked_objects.keys())
            final_tracked = len(self.lifecycle_manager.tracked_objects)
            logger.info(f"Weak reference cleanup: {initial_tracked - final_tracked} objects cleaned")
            optimizations_performed.append("weak_reference_cleanup")
        
        # 3. Cache optimization
        cache_stats_before = self.cache.get_stats()
        if cache_stats_before['utilization_percent'] > 80:
            # Clear old cache items
            self.cache.clear()
            logger.info("Cache cleared due to high utilization")
            optimizations_performed.append("cache_clear")
        
        # 4. Detect memory leaks
        memory_leaks = self.profiler.detect_memory_leaks()
        if memory_leaks:
            logger.warning(f"Detected {len(memory_leaks)} potential memory leaks")
        
        after_snapshot = self.profiler.take_snapshot()
        optimization_time = time.time() - start_time
        
        memory_saved = before_snapshot.rss_mb - after_snapshot.rss_mb
        
        result = {
            'timestamp': datetime.now(),
            'optimization_time': optimization_time,
            'optimizations_performed': optimizations_performed,
            'memory_before_mb': before_snapshot.rss_mb,
            'memory_after_mb': after_snapshot.rss_mb,
            'memory_saved_mb': memory_saved,
            'memory_saved_percent': (memory_saved / before_snapshot.rss_mb) * 100 if before_snapshot.rss_mb > 0 else 0,
            'gc_result': gc_result,
            'memory_leaks_detected': len(memory_leaks),
            'memory_leaks': memory_leaks,
            'cache_stats': self.cache.get_stats(),
            'object_stats': self.lifecycle_manager.get_object_stats()
        }
        
        self.optimization_history.append(result)
        
        logger.info(f"Memory optimization completed: {memory_saved:.1f}MB saved ({optimization_time:.2f}s)")
        
        return result
    
    def get_comprehensive_report(self) -> Dict[str, Any]:
        """Get comprehensive memory optimization report"""
        current_snapshot = self.profiler.take_snapshot()
        memory_trend = self.profiler.get_memory_trend(60)  # Last hour
        gc_recommendations = self.gc_optimizer.get_gc_recommendations()
        
        return {
            'timestamp': datetime.now(),
            'current_memory_usage': {
                'rss_mb': current_snapshot.rss_mb,
                'percent': current_snapshot.percent,
                'tracemalloc_current_mb': current_snapshot.tracemalloc_current_mb,
                'tracemalloc_peak_mb': current_snapshot.tracemalloc_peak_mb
            },
            'memory_trend': memory_trend,
            'optimization_cycles_run': len(self.optimization_history),
            'total_memory_saved_mb': sum(opt['memory_saved_mb'] for opt in self.optimization_history),
            'average_optimization_time': sum(opt['optimization_time'] for opt in self.optimization_history) / len(self.optimization_history) if self.optimization_history else 0,
            'gc_recommendations': gc_recommendations,
            'cache_performance': self.cache.get_stats(),
            'object_lifecycle_stats': self.lifecycle_manager.get_object_stats(),
            'memory_alerts': list(self.profiler.memory_alerts),
            'recent_optimizations': list(self.optimization_history)[-5:]  # Last 5 optimizations
        }


@contextmanager
def memory_optimization_context(config: MemoryOptimizationConfig = None):
    """Context manager for memory optimization"""
    orchestrator = MemoryOptimizationOrchestrator(config)
    
    try:
        initial_snapshot = orchestrator.start_optimization()
        yield orchestrator
    finally:
        final_snapshot = orchestrator.stop_optimization()
        
        memory_change = final_snapshot.rss_mb - initial_snapshot.rss_mb
        logger.info(f"Memory optimization context ended. Net change: {memory_change:+.1f}MB")


def main():
    """Demonstrate memory optimization system"""
    print("=== Memory Management Optimization System Demo ===\n")
    
    config = MemoryOptimizationConfig(
        max_cache_size_mb=50.0,
        memory_warning_threshold=75.0,
        snapshot_interval=5
    )
    
    with memory_optimization_context(config) as orchestrator:
        # Simulate some memory-intensive operations
        print("Simulating memory usage...")
        
        # Create some test data
        test_data = []
        for i in range(1000):
            test_data.append([j for j in range(100)])  # Lists of 100 integers
            
            # Register some objects
            orchestrator.lifecycle_manager.register_object(
                test_data[-1], 
                category="test_data"
            )
            
            # Use cache
            orchestrator.cache.put(f"key_{i}", test_data[-1])
        
        print("Running optimization cycle...")
        optimization_result = orchestrator.run_memory_optimization_cycle()
        
        # Wait a bit for profiling
        time.sleep(10)
        
        # Clean up test data
        print("Cleaning up test data...")
        orchestrator.lifecycle_manager.cleanup_category("test_data")
        del test_data
        
        # Run another optimization cycle
        final_optimization = orchestrator.run_memory_optimization_cycle()
        
        # Get comprehensive report
        report = orchestrator.get_comprehensive_report()
    
    # Display results
    print("\n=== Memory Optimization Results ===")
    print(f"Memory saved in first cycle: {optimization_result['memory_saved_mb']:.1f}MB")
    print(f"Memory saved in final cycle: {final_optimization['memory_saved_mb']:.1f}MB")
    print(f"Total optimization cycles: {report['optimization_cycles_run']}")
    print(f"Total memory saved: {report['total_memory_saved_mb']:.1f}MB")
    print(f"Average optimization time: {report['average_optimization_time']:.2f}s")
    
    if report['gc_recommendations']:
        print(f"\nGC Recommendations:")
        for rec in report['gc_recommendations']:
            print(f"  - {rec}")
    
    return {
        'optimization_result': optimization_result,
        'final_optimization': final_optimization,
        'comprehensive_report': report
    }


if __name__ == "__main__":
    main() 