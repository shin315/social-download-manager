#!/usr/bin/env python3
"""
Memory Management and Leak Prevention Framework - Task 21.4
Comprehensive memory management for PyQt6 applications with monitoring and optimization

Features:
- Memory usage monitoring and profiling
- PyQt6 memory leak detection and prevention
- Efficient video metadata caching strategies
- Automatic garbage collection optimization
- Memory pool management for large objects
- Parent-child widget relationship management
- Real-time memory alerts and recommendations
"""

import sys
import gc
import weakref
import threading
import time
import logging
import psutil
import tracemalloc
from typing import Dict, List, Any, Optional, Tuple, Callable, Union, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from pathlib import Path
import json

# PyQt6 imports for memory management
try:
    from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QThread, QMutex
    from PyQt6.QtWidgets import QWidget, QApplication
    from PyQt6.QtGui import QPixmap
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    print("Warning: PyQt6 not available, running in mock mode")

@dataclass
class MemorySnapshot:
    """Memory usage snapshot at a point in time"""
    timestamp: datetime
    rss_mb: float
    vms_mb: float
    percent: float
    available_mb: float
    python_objects: int
    pyqt_objects: int
    cached_videos: int
    cached_thumbnails: int
    gc_generation_counts: Tuple[int, int, int]
    peak_memory_mb: float = 0.0
    leaked_objects: int = 0
    

@dataclass
class MemoryLeakInfo:
    """Information about a detected memory leak"""
    object_type: str
    count: int
    size_bytes: int
    stack_trace: List[str]
    first_detected: datetime
    last_detected: datetime
    severity: str  # "low", "medium", "high", "critical"


@dataclass
class CacheConfig:
    """Configuration for memory caches"""
    max_video_metadata_mb: int = 100
    max_thumbnail_cache_mb: int = 50
    max_preview_cache_mb: int = 30
    cache_cleanup_interval_sec: int = 300
    cache_hit_ratio_threshold: float = 0.7
    enable_compression: bool = True
    enable_lru_eviction: bool = True


class MemoryPool:
    """Efficient memory pool for frequently allocated objects"""
    
    def __init__(self, object_type: type, initial_size: int = 10, max_size: int = 100):
        self.object_type = object_type
        self.max_size = max_size
        self.pool = deque()
        self.in_use = set()
        self.lock = threading.Lock()
        self.stats = {
            'allocated': 0,
            'reused': 0,
            'pool_hits': 0,
            'pool_misses': 0
        }
        
        # Pre-allocate initial objects
        for _ in range(initial_size):
            obj = self._create_object()
            self.pool.append(obj)
    
    def _create_object(self):
        """Create a new object instance"""
        return self.object_type()
    
    def acquire(self):
        """Get an object from the pool"""
        with self.lock:
            if self.pool:
                obj = self.pool.popleft()
                self.in_use.add(id(obj))
                self.stats['pool_hits'] += 1
                self.stats['reused'] += 1
                return obj
            else:
                obj = self._create_object()
                self.in_use.add(id(obj))
                self.stats['pool_misses'] += 1
                self.stats['allocated'] += 1
                return obj
    
    def release(self, obj):
        """Return an object to the pool"""
        with self.lock:
            obj_id = id(obj)
            if obj_id in self.in_use:
                self.in_use.remove(obj_id)
                if len(self.pool) < self.max_size:
                    # Reset object state if needed
                    if hasattr(obj, 'reset'):
                        obj.reset()
                    self.pool.append(obj)
                # If pool is full, let object be garbage collected
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        with self.lock:
            return {
                'pool_size': len(self.pool),
                'in_use': len(self.in_use),
                'total_allocated': self.stats['allocated'],
                'total_reused': self.stats['reused'],
                'hit_rate': self.stats['pool_hits'] / max(1, self.stats['pool_hits'] + self.stats['pool_misses']),
                'efficiency': self.stats['reused'] / max(1, self.stats['allocated'] + self.stats['reused'])
            }


class VideoMetadataCache:
    """Efficient cache for video metadata with memory management"""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.cache = {}
        self.access_times = {}
        self.lock = threading.Lock()
        self.current_size_mb = 0.0
        self.stats = defaultdict(int)
        
    def get(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get video metadata from cache"""
        with self.lock:
            if video_id in self.cache:
                self.access_times[video_id] = time.time()
                self.stats['hits'] += 1
                return self.cache[video_id].copy()
            else:
                self.stats['misses'] += 1
                return None
    
    def put(self, video_id: str, metadata: Dict[str, Any]):
        """Store video metadata in cache"""
        with self.lock:
            # Estimate size
            estimated_size_mb = len(str(metadata)) / (1024 * 1024)
            
            # Check if we need to evict items
            while (self.current_size_mb + estimated_size_mb > self.config.max_video_metadata_mb 
                   and self.cache):
                self._evict_lru_item()
            
            # Store item
            self.cache[video_id] = metadata.copy()
            self.access_times[video_id] = time.time()
            self.current_size_mb += estimated_size_mb
            self.stats['stores'] += 1
    
    def _evict_lru_item(self):
        """Evict least recently used item"""
        if not self.access_times:
            return
            
        lru_id = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        self.remove(lru_id)
        self.stats['evictions'] += 1
    
    def remove(self, video_id: str):
        """Remove item from cache"""
        if video_id in self.cache:
            # Estimate size for removal
            estimated_size_mb = len(str(self.cache[video_id])) / (1024 * 1024)
            del self.cache[video_id]
            del self.access_times[video_id]
            self.current_size_mb = max(0, self.current_size_mb - estimated_size_mb)
    
    def clear(self):
        """Clear entire cache"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
            self.current_size_mb = 0.0
            self.stats['clears'] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            total_requests = self.stats['hits'] + self.stats['misses']
            hit_rate = self.stats['hits'] / max(1, total_requests)
            
            return {
                'size_mb': round(self.current_size_mb, 2),
                'items': len(self.cache),
                'hit_rate': round(hit_rate, 3),
                'hits': self.stats['hits'],
                'misses': self.stats['misses'],
                'stores': self.stats['stores'],
                'evictions': self.stats['evictions'],
                'clears': self.stats['clears']
            }


class PyQt6MemoryTracker:
    """Track PyQt6 objects and detect memory leaks"""
    
    def __init__(self):
        self.tracked_objects = weakref.WeakSet()
        self.object_counts = defaultdict(int)
        self.object_creation_times = {}
        self.potential_leaks = []
        self.lock = threading.Lock()
        
    def track_object(self, obj, obj_type: str = None):
        """Add object to tracking"""
        if not PYQT6_AVAILABLE:
            return
            
        with self.lock:
            if isinstance(obj, (QObject, QWidget)):
                self.tracked_objects.add(obj)
                obj_type = obj_type or type(obj).__name__
                self.object_counts[obj_type] += 1
                self.object_creation_times[id(obj)] = time.time()
    
    def check_for_leaks(self) -> List[MemoryLeakInfo]:
        """Check for potential memory leaks"""
        if not PYQT6_AVAILABLE:
            return []
            
        with self.lock:
            current_time = time.time()
            leaks = []
            
            # Check for objects that have been alive too long
            long_lived_threshold = 3600  # 1 hour
            
            for obj in self.tracked_objects:
                obj_id = id(obj)
                if obj_id in self.object_creation_times:
                    age = current_time - self.object_creation_times[obj_id]
                    if age > long_lived_threshold:
                        leak_info = MemoryLeakInfo(
                            object_type=type(obj).__name__,
                            count=1,
                            size_bytes=sys.getsizeof(obj),
                            stack_trace=[],
                            first_detected=datetime.fromtimestamp(self.object_creation_times[obj_id]),
                            last_detected=datetime.now(),
                            severity="medium" if age < 7200 else "high"
                        )
                        leaks.append(leak_info)
            
            return leaks
    
    def get_object_counts(self) -> Dict[str, int]:
        """Get current object counts by type"""
        with self.lock:
            # Update counts based on live objects
            live_counts = defaultdict(int)
            for obj in self.tracked_objects:
                obj_type = type(obj).__name__
                live_counts[obj_type] += 1
            return dict(live_counts)


class MemoryMonitor:
    """Real-time memory monitoring and alerting"""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.snapshots = deque(maxlen=1000)  # Keep last 1000 snapshots
        self.alerts = deque(maxlen=100)      # Keep last 100 alerts
        self.is_monitoring = False
        self.monitor_thread = None
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        
        # Memory thresholds
        self.warning_threshold_mb = 1000   # 1GB
        self.critical_threshold_mb = 2000  # 2GB
        self.leak_detection_window = 300   # 5 minutes
        
        # Initialize PyQt6 tracker
        self.pyqt_tracker = PyQt6MemoryTracker()
        
        # Initialize caches
        self.video_cache = VideoMetadataCache(config)
        
        # Initialize memory pools
        self.memory_pools = {}
        
    def start_monitoring(self, interval_seconds: float = 5.0):
        """Start memory monitoring"""
        if self.is_monitoring:
            return
            
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop, 
            args=(interval_seconds,),
            daemon=True
        )
        self.monitor_thread.start()
        self.logger.info(f"Memory monitoring started (interval: {interval_seconds}s)")
    
    def stop_monitoring(self):
        """Stop memory monitoring"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        self.logger.info("Memory monitoring stopped")
    
    def _monitor_loop(self, interval: float):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                snapshot = self._take_snapshot()
                self._check_thresholds(snapshot)
                self._check_memory_leaks()
                time.sleep(interval)
            except Exception as e:
                self.logger.error(f"Error in memory monitoring: {e}")
                time.sleep(interval)
    
    def _take_snapshot(self) -> MemorySnapshot:
        """Take a memory usage snapshot"""
        # Get system memory info
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_percent = process.memory_percent()
        
        # Get system memory
        system_memory = psutil.virtual_memory()
        
        # Get Python object counts
        python_objects = len(gc.get_objects())
        
        # Get PyQt6 object counts
        pyqt_objects = sum(self.pyqt_tracker.get_object_counts().values())
        
        # Get cache info
        video_cache_stats = self.video_cache.get_stats()
        
        # Get garbage collection stats
        gc_stats = gc.get_stats()
        generation_counts = tuple(stat.get('collections', 0) for stat in gc_stats)
        
        snapshot = MemorySnapshot(
            timestamp=datetime.now(),
            rss_mb=memory_info.rss / (1024 * 1024),
            vms_mb=memory_info.vms / (1024 * 1024),
            percent=memory_percent,
            available_mb=system_memory.available / (1024 * 1024),
            python_objects=python_objects,
            pyqt_objects=pyqt_objects,
            cached_videos=video_cache_stats['items'],
            cached_thumbnails=0,  # Would be implemented with thumbnail cache
            gc_generation_counts=generation_counts
        )
        
        with self.lock:
            self.snapshots.append(snapshot)
            
        return snapshot
    
    def _check_thresholds(self, snapshot: MemorySnapshot):
        """Check memory usage against thresholds"""
        if snapshot.rss_mb > self.critical_threshold_mb:
            self._create_alert("critical", f"Memory usage critical: {snapshot.rss_mb:.1f}MB")
            self._trigger_emergency_cleanup()
        elif snapshot.rss_mb > self.warning_threshold_mb:
            self._create_alert("warning", f"Memory usage high: {snapshot.rss_mb:.1f}MB")
            self._trigger_cleanup()
    
    def _check_memory_leaks(self):
        """Check for potential memory leaks"""
        if len(self.snapshots) < 10:
            return
            
        with self.lock:
            recent_snapshots = list(self.snapshots)[-10:]
            
        # Check for consistent memory growth
        memory_growth = recent_snapshots[-1].rss_mb - recent_snapshots[0].rss_mb
        time_span = (recent_snapshots[-1].timestamp - recent_snapshots[0].timestamp).total_seconds()
        
        if memory_growth > 50 and time_span > 60:  # 50MB growth in 1+ minutes
            growth_rate = memory_growth / (time_span / 60)  # MB per minute
            self._create_alert("warning", f"Potential memory leak detected: {growth_rate:.1f}MB/min growth")
        
        # Check PyQt6 object leaks
        pyqt_leaks = self.pyqt_tracker.check_for_leaks()
        for leak in pyqt_leaks:
            self._create_alert("medium", f"PyQt6 leak: {leak.object_type} object alive for {leak.severity}")
    
    def _create_alert(self, severity: str, message: str):
        """Create a memory alert"""
        alert = {
            'timestamp': datetime.now(),
            'severity': severity,
            'message': message
        }
        
        with self.lock:
            self.alerts.append(alert)
        
        self.logger.warning(f"Memory Alert [{severity.upper()}]: {message}")
    
    def _trigger_cleanup(self):
        """Trigger standard memory cleanup"""
        self.logger.info("Triggering memory cleanup")
        
        # Clear caches partially
        if self.video_cache.get_stats()['size_mb'] > self.config.max_video_metadata_mb * 0.8:
            # Clear 25% of cache
            items_to_remove = len(self.video_cache.cache) // 4
            for _ in range(items_to_remove):
                self.video_cache._evict_lru_item()
        
        # Force garbage collection
        collected = gc.collect()
        self.logger.info(f"Garbage collection freed {collected} objects")
    
    def _trigger_emergency_cleanup(self):
        """Trigger emergency memory cleanup"""
        self.logger.warning("Triggering emergency memory cleanup")
        
        # Clear all caches
        self.video_cache.clear()
        
        # Force aggressive garbage collection
        for generation in range(3):
            collected = gc.collect(generation)
            self.logger.info(f"GC generation {generation}: freed {collected} objects")
        
        # Clear memory pools
        for pool in self.memory_pools.values():
            pool.pool.clear()
    
    def get_memory_report(self) -> Dict[str, Any]:
        """Generate comprehensive memory report"""
        with self.lock:
            if not self.snapshots:
                return {"error": "No memory snapshots available"}
            
            latest = self.snapshots[-1]
            
            # Calculate trends
            if len(self.snapshots) >= 2:
                previous = self.snapshots[-2]
                memory_trend = latest.rss_mb - previous.rss_mb
                object_trend = latest.python_objects - previous.python_objects
            else:
                memory_trend = 0
                object_trend = 0
            
            # Get peak memory
            peak_memory = max(s.rss_mb for s in self.snapshots)
            
            report = {
                'timestamp': latest.timestamp.isoformat(),
                'current_memory': {
                    'rss_mb': round(latest.rss_mb, 2),
                    'vms_mb': round(latest.vms_mb, 2),
                    'percent': round(latest.percent, 1),
                    'available_mb': round(latest.available_mb, 2)
                },
                'trends': {
                    'memory_change_mb': round(memory_trend, 2),
                    'object_change': object_trend,
                    'peak_memory_mb': round(peak_memory, 2)
                },
                'objects': {
                    'python_objects': latest.python_objects,
                    'pyqt_objects': latest.pyqt_objects,
                    'pyqt_breakdown': self.pyqt_tracker.get_object_counts()
                },
                'caches': {
                    'video_metadata': self.video_cache.get_stats()
                },
                'memory_pools': {name: pool.get_stats() for name, pool in self.memory_pools.items()},
                'alerts': {
                    'recent_count': len([a for a in self.alerts if (datetime.now() - a['timestamp']).total_seconds() < 300]),
                    'critical_count': len([a for a in self.alerts if a['severity'] == 'critical']),
                    'latest_alerts': [
                        {
                            'timestamp': a['timestamp'].isoformat(),
                            'severity': a['severity'],
                            'message': a['message']
                        } for a in list(self.alerts)[-5:]  # Last 5 alerts
                    ]
                },
                'gc_stats': {
                    'generation_counts': latest.gc_generation_counts,
                    'thresholds': gc.get_threshold()
                }
            }
            
        return report


class MemoryManager:
    """Main memory management coordinator"""
    
    def __init__(self, config: CacheConfig = None):
        self.config = config or CacheConfig()
        self.monitor = MemoryMonitor(self.config)
        self.logger = logging.getLogger(__name__)
        self.is_initialized = False
        
        # Enable tracemalloc for detailed memory tracking
        if not tracemalloc.is_tracing():
            tracemalloc.start(25)  # Keep 25 frames
    
    def initialize(self):
        """Initialize memory management system"""
        if self.is_initialized:
            return
            
        self.logger.info("Initializing memory management system")
        
        # Configure garbage collection
        gc.set_threshold(700, 10, 10)  # More aggressive GC
        
        # Start monitoring
        self.monitor.start_monitoring(interval_seconds=5.0)
        
        # Register cleanup handlers
        if PYQT6_AVAILABLE:
            self._setup_pyqt_cleanup()
        
        self.is_initialized = True
        self.logger.info("Memory management system initialized")
    
    def _setup_pyqt_cleanup(self):
        """Setup PyQt6-specific cleanup handlers"""
        # This would be implemented with actual PyQt6 application instance
        pass
    
    def track_pyqt_object(self, obj, obj_type: str = None):
        """Track a PyQt6 object for memory management"""
        self.monitor.pyqt_tracker.track_object(obj, obj_type)
    
    def get_video_cache(self) -> VideoMetadataCache:
        """Get video metadata cache"""
        return self.monitor.video_cache
    
    def create_memory_pool(self, name: str, object_type: type, initial_size: int = 10, max_size: int = 100):
        """Create a memory pool for efficient object reuse"""
        pool = MemoryPool(object_type, initial_size, max_size)
        self.monitor.memory_pools[name] = pool
        return pool
    
    def force_cleanup(self):
        """Force immediate memory cleanup"""
        self.monitor._trigger_cleanup()
    
    def emergency_cleanup(self):
        """Force emergency memory cleanup"""
        self.monitor._trigger_emergency_cleanup()
    
    def get_memory_report(self) -> Dict[str, Any]:
        """Get comprehensive memory report"""
        return self.monitor.get_memory_report()
    
    def shutdown(self):
        """Shutdown memory management system"""
        self.logger.info("Shutting down memory management system")
        self.monitor.stop_monitoring()
        self.monitor.video_cache.clear()
        
        # Clear memory pools
        for pool in self.monitor.memory_pools.values():
            pool.pool.clear()
        
        # Final garbage collection
        gc.collect()
        
        self.is_initialized = False


# Factory function
def create_memory_manager(config: CacheConfig = None) -> MemoryManager:
    """Create and initialize memory manager"""
    manager = MemoryManager(config)
    manager.initialize()
    return manager


# Decorator for automatic memory management
def memory_managed(func):
    """Decorator to add automatic memory management to functions"""
    def wrapper(*args, **kwargs):
        # Take snapshot before
        initial_objects = len(gc.get_objects())
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            # Cleanup after
            final_objects = len(gc.get_objects())
            if final_objects > initial_objects + 1000:  # Significant object growth
                gc.collect()
    
    return wrapper 