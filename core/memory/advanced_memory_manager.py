"""
Advanced Memory Management System

Comprehensive memory optimization for large video collections including:
- WeakValueDictionary for automatic thumbnail cleanup
- Video frame buffer recycling and pooling
- Qt QObject parent-child memory management
- PyQtGraph data handling optimizations
- Real-time memory monitoring and alerts
- Automatic cleanup scheduling

Part of Task 15.4 - Memory Management
"""

import os
import gc
import sys
import time
import weakref
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Set, Union
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum

# Qt imports
try:
    from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QThread
    from PyQt6.QtGui import QPixmap
    from PyQt6.QtWidgets import QApplication
    HAS_QT = True
except ImportError:
    HAS_QT = False
    print("PyQt6 not available - Qt memory management disabled")

# PyQtGraph imports for data optimization
try:
    import pyqtgraph as pg
    import numpy as np
    HAS_PYQTGRAPH = True
except ImportError:
    HAS_PYQTGRAPH = False
    print("PyQtGraph not available - data optimization disabled")


class MemoryAlert(Enum):
    """Memory alert levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MemoryStats:
    """Memory usage statistics"""
    
    rss_mb: float                    # Resident Set Size in MB
    vms_mb: float                   # Virtual Memory Size in MB
    percent: float                  # Memory usage percentage
    available_mb: float             # Available memory in MB
    cache_size_mb: float           # Cache size in MB
    buffer_count: int              # Active buffer count
    weak_ref_count: int            # Active weak references
    qt_object_count: int           # Qt objects count
    gc_collections: int            # Garbage collections performed
    timestamp: datetime            # When stats were collected


class WeakReferenceCache:
    """
    Advanced caching system using weak references for automatic cleanup
    
    Uses WeakValueDictionary to allow automatic garbage collection
    of cached items when no strong references remain
    """
    
    def __init__(self, name: str = "cache", max_size: int = 1000):
        self.name = name
        self.max_size = max_size
        self._cache = weakref.WeakValueDictionary()
        self._access_times = {}
        self._lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'cleanups': 0
        }
    
    def get(self, key: str, default=None):
        """Get item from cache"""
        with self._lock:
            try:
                item = self._cache[key]
                self._access_times[key] = time.time()
                self._stats['hits'] += 1
                return item
            except KeyError:
                self._stats['misses'] += 1
                return default
    
    def set(self, key: str, value: Any) -> bool:
        """Set item in cache"""
        with self._lock:
            # Check size limit
            if len(self._cache) >= self.max_size:
                self._evict_lru()
            
            try:
                self._cache[key] = value
                self._access_times[key] = time.time()
                return True
            except TypeError:
                # Value doesn't support weak references
                return False
    
    def delete(self, key: str) -> bool:
        """Delete item from cache"""
        with self._lock:
            try:
                del self._cache[key]
                self._access_times.pop(key, None)
                return True
            except KeyError:
                return False
    
    def _evict_lru(self):
        """Evict least recently used item"""
        if not self._access_times:
            return
        
        # Find oldest accessed item
        oldest_key = min(self._access_times.keys(), 
                        key=lambda k: self._access_times[k])
        
        self.delete(oldest_key)
        self._stats['evictions'] += 1
    
    def cleanup_dead_refs(self):
        """Clean up dead weak references"""
        with self._lock:
            # WeakValueDictionary automatically removes dead references
            # Clean up access times for dead keys
            dead_keys = []
            for key in self._access_times:
                if key not in self._cache:
                    dead_keys.append(key)
            
            for key in dead_keys:
                del self._access_times[key]
            
            if dead_keys:
                self._stats['cleanups'] += len(dead_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            return {
                'name': self.name,
                'size': len(self._cache),
                'max_size': self.max_size,
                'hit_rate': self._stats['hits'] / (self._stats['hits'] + self._stats['misses']) if (self._stats['hits'] + self._stats['misses']) > 0 else 0,
                **self._stats
            }
    
    def clear(self):
        """Clear all cached items"""
        with self._lock:
            self._cache.clear()
            self._access_times.clear()


class VideoFrameBufferPool:
    """
    Video frame buffer recycling system for memory efficiency
    
    Maintains a pool of reusable frame buffers to prevent
    constant allocation/deallocation of large video frames
    """
    
    def __init__(self, max_pool_size: int = 50):
        self.max_pool_size = max_pool_size
        self._buffer_pools = defaultdict(deque)  # Size -> deque of buffers
        self._active_buffers = weakref.WeakSet()
        self._lock = threading.RLock()
        self._stats = {
            'allocations': 0,
            'recycled': 0,
            'peak_active': 0,
            'total_size_mb': 0
        }
    
    def get_buffer(self, width: int, height: int, channels: int = 3) -> Optional['VideoFrameBuffer']:
        """Get a frame buffer from pool or create new one"""
        buffer_size = width * height * channels
        size_key = (width, height, channels)
        
        with self._lock:
            # Try to reuse existing buffer
            if size_key in self._buffer_pools and self._buffer_pools[size_key]:
                buffer = self._buffer_pools[size_key].popleft()
                buffer._reset()
                self._active_buffers.add(buffer)
                self._stats['recycled'] += 1
                return buffer
            
            # Create new buffer
            if HAS_PYQTGRAPH:
                buffer = PyQtGraphFrameBuffer(width, height, channels)
            else:
                buffer = BasicFrameBuffer(width, height, channels)
            
            self._active_buffers.add(buffer)
            self._stats['allocations'] += 1
            self._stats['peak_active'] = max(self._stats['peak_active'], len(self._active_buffers))
            
            return buffer
    
    def return_buffer(self, buffer: 'VideoFrameBuffer'):
        """Return buffer to pool for reuse"""
        if not buffer or not hasattr(buffer, '_size_key'):
            return
        
        with self._lock:
            size_key = buffer._size_key
            
            # Only keep buffer if pool not full
            if len(self._buffer_pools[size_key]) < self.max_pool_size:
                buffer._prepare_for_reuse()
                self._buffer_pools[size_key].append(buffer)
            
            # Remove from active set
            self._active_buffers.discard(buffer)
    
    def cleanup_pools(self):
        """Clean up empty pools and limit pool sizes"""
        with self._lock:
            # Remove empty pools
            empty_keys = [k for k, v in self._buffer_pools.items() if not v]
            for key in empty_keys:
                del self._buffer_pools[key]
            
            # Limit pool sizes
            for size_key, pool in self._buffer_pools.items():
                while len(pool) > self.max_pool_size:
                    pool.popleft()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get buffer pool statistics"""
        with self._lock:
            total_pooled = sum(len(pool) for pool in self._buffer_pools.values())
            return {
                'active_buffers': len(self._active_buffers),
                'pooled_buffers': total_pooled,
                'pool_types': len(self._buffer_pools),
                'max_pool_size': self.max_pool_size,
                **self._stats
            }


class VideoFrameBuffer:
    """Base class for video frame buffers"""
    
    def __init__(self, width: int, height: int, channels: int = 3):
        self.width = width
        self.height = height
        self.channels = channels
        self._size_key = (width, height, channels)
        self._data = None
        self._created_at = time.time()
    
    def _reset(self):
        """Reset buffer for reuse"""
        pass
    
    def _prepare_for_reuse(self):
        """Prepare buffer for return to pool"""
        if self._data is not None and hasattr(self._data, 'fill'):
            self._data.fill(0)  # Clear data
    
    def get_data(self):
        """Get buffer data"""
        return self._data
    
    def get_size_bytes(self) -> int:
        """Get buffer size in bytes"""
        return self.width * self.height * self.channels


class BasicFrameBuffer(VideoFrameBuffer):
    """Basic frame buffer using bytearray"""
    
    def __init__(self, width: int, height: int, channels: int = 3):
        super().__init__(width, height, channels)
        size = width * height * channels
        self._data = bytearray(size)
    
    def _reset(self):
        """Reset buffer for reuse"""
        if self._data:
            # Fast zero-fill
            self._data[:] = b'\x00' * len(self._data)


if HAS_PYQTGRAPH:
    class PyQtGraphFrameBuffer(VideoFrameBuffer):
        """Optimized frame buffer using PyQtGraph/NumPy arrays"""
        
        def __init__(self, width: int, height: int, channels: int = 3):
            super().__init__(width, height, channels)
            # Use NumPy for efficient memory management
            self._data = np.zeros((height, width, channels), dtype=np.uint8)
        
        def _reset(self):
            """Reset buffer for reuse"""
            if self._data is not None:
                self._data.fill(0)
        
        def get_downsampled(self, factor: int = 2):
            """Get downsampled version using PyQtGraph optimization"""
            if self._data is None or factor <= 1:
                return self._data
            
            # Use PyQtGraph's efficient downsampling
            return pg.downsample(self._data, factor, axis=(0, 1))
        
        def get_size_bytes(self) -> int:
            """Get buffer size in bytes"""
            return self._data.nbytes if self._data is not None else 0


class QtMemoryOptimizer:
    """
    Qt-specific memory management utilities
    
    Leverages Qt's parent-child object system for efficient cleanup
    and provides utilities for managing Qt widgets and objects
    """
    
    def __init__(self):
        self._managed_objects = weakref.WeakSet()
        self._cleanup_callbacks = []
        self._stats = {
            'objects_managed': 0,
            'cleanups_performed': 0,
            'parent_child_optimizations': 0
        }
    
    def register_object(self, obj: Any, parent: Any = None):
        """Register Qt object for memory management"""
        if not HAS_QT:
            return
        
        if isinstance(obj, QObject):
            if parent and isinstance(parent, QObject):
                obj.setParent(parent)
                self._stats['parent_child_optimizations'] += 1
            
            self._managed_objects.add(obj)
            self._stats['objects_managed'] += 1
    
    def cleanup_object(self, obj: Any):
        """Safely cleanup Qt object"""
        if not HAS_QT or not isinstance(obj, QObject):
            return
        
        try:
            # Clear parent-child relationships
            if obj.parent():
                obj.setParent(None)
            
            # Delete children first
            for child in obj.children():
                child.setParent(None)
                child.deleteLater()
            
            # Delete object
            obj.deleteLater()
            self._stats['cleanups_performed'] += 1
            
        except Exception as e:
            print(f"Error cleaning up Qt object: {e}")
    
    def cleanup_pixmap_cache(self):
        """Clear Qt pixmap cache to free memory"""
        if HAS_QT:
            from PyQt6.QtGui import QPixmapCache
            QPixmapCache.clear()
    
    def optimize_widget_for_large_data(self, widget: Any):
        """Apply optimizations for widgets displaying large datasets"""
        if not HAS_QT or not isinstance(widget, QObject):
            return
        
        try:
            # Disable automatic updates during bulk operations
            if hasattr(widget, 'setUpdatesEnabled'):
                widget.setUpdatesEnabled(False)
            
            # Enable content optimization hints
            if hasattr(widget, 'setAttribute'):
                from PyQt6.QtCore import Qt
                widget.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
                widget.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        
        except Exception as e:
            print(f"Error optimizing widget: {e}")
    
    def get_qt_object_count(self) -> int:
        """Get count of managed Qt objects"""
        return len(self._managed_objects)


class MemoryProfiler:
    """
    Real-time memory monitoring and profiling system
    
    Tracks memory usage, provides alerts, and generates
    detailed memory reports for optimization
    """
    
    def __init__(self, alert_threshold: float = 85.0):
        self.alert_threshold = alert_threshold
        self._process = psutil.Process()
        self._history = deque(maxlen=1000)  # Keep last 1000 measurements
        self._alert_callbacks = []
        self._last_alert = None
        self._monitoring = False
        self._monitor_thread = None
        
    def start_monitoring(self, interval: float = 5.0):
        """Start continuous memory monitoring"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, 
            args=(interval,),
            daemon=True
        )
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop memory monitoring"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
    
    def _monitor_loop(self, interval: float):
        """Memory monitoring loop"""
        while self._monitoring:
            try:
                stats = self.get_current_stats()
                self._history.append(stats)
                
                # Check for alerts
                self._check_alerts(stats)
                
                time.sleep(interval)
                
            except Exception as e:
                print(f"Memory monitoring error: {e}")
                time.sleep(interval)
    
    def get_current_stats(self, 
                         cache: Optional[WeakReferenceCache] = None,
                         buffer_pool: Optional[VideoFrameBufferPool] = None,
                         qt_optimizer: Optional[QtMemoryOptimizer] = None) -> MemoryStats:
        """Get current memory statistics"""
        
        # System memory info
        memory_info = self._process.memory_info()
        system_memory = psutil.virtual_memory()
        
        # Cache stats
        cache_size_mb = 0
        if cache:
            cache_stats = cache.get_stats()
            # Estimate cache size (rough approximation)
            cache_size_mb = cache_stats['size'] * 0.1  # Assume 100KB per item
        
        # Buffer stats
        buffer_count = 0
        if buffer_pool:
            buffer_stats = buffer_pool.get_stats()
            buffer_count = buffer_stats['active_buffers']
        
        # Qt object count
        qt_object_count = 0
        if qt_optimizer:
            qt_object_count = qt_optimizer.get_qt_object_count()
        
        # Weak reference count (approximate)
        weak_ref_count = len([obj for obj in gc.get_objects() if type(obj) == weakref.ref])
        
        return MemoryStats(
            rss_mb=memory_info.rss / 1024 / 1024,
            vms_mb=memory_info.vms / 1024 / 1024,
            percent=system_memory.percent,
            available_mb=system_memory.available / 1024 / 1024,
            cache_size_mb=cache_size_mb,
            buffer_count=buffer_count,
            weak_ref_count=weak_ref_count,
            qt_object_count=qt_object_count,
            gc_collections=len(gc.get_stats()),
            timestamp=datetime.now()
        )
    
    def _check_alerts(self, stats: MemoryStats):
        """Check for memory alerts"""
        alert_level = None
        
        if stats.percent >= 95:
            alert_level = MemoryAlert.CRITICAL
        elif stats.percent >= 90:
            alert_level = MemoryAlert.HIGH
        elif stats.percent >= self.alert_threshold:
            alert_level = MemoryAlert.MEDIUM
        elif stats.percent >= 70:
            alert_level = MemoryAlert.LOW
        
        # Only alert if level changed or critical
        if alert_level and (alert_level != self._last_alert or alert_level == MemoryAlert.CRITICAL):
            self._trigger_alert(alert_level, stats)
            self._last_alert = alert_level
    
    def _trigger_alert(self, level: MemoryAlert, stats: MemoryStats):
        """Trigger memory alert"""
        for callback in self._alert_callbacks:
            try:
                callback(level, stats)
            except Exception as e:
                print(f"Error in alert callback: {e}")
    
    def add_alert_callback(self, callback: Callable[[MemoryAlert, MemoryStats], None]):
        """Add callback for memory alerts"""
        self._alert_callbacks.append(callback)
    
    def get_memory_report(self) -> Dict[str, Any]:
        """Generate comprehensive memory report"""
        if not self._history:
            return {'error': 'No memory data available'}
        
        recent_stats = list(self._history)[-100:]  # Last 100 measurements
        
        return {
            'current': recent_stats[-1] if recent_stats else None,
            'average_rss_mb': sum(s.rss_mb for s in recent_stats) / len(recent_stats),
            'peak_rss_mb': max(s.rss_mb for s in recent_stats),
            'average_percent': sum(s.percent for s in recent_stats) / len(recent_stats),
            'peak_percent': max(s.percent for s in recent_stats),
            'trend': 'increasing' if len(recent_stats) >= 2 and recent_stats[-1].rss_mb > recent_stats[0].rss_mb else 'stable',
            'measurements': len(recent_stats),
            'timespan_minutes': (recent_stats[-1].timestamp - recent_stats[0].timestamp).total_seconds() / 60 if len(recent_stats) >= 2 else 0
        }


class AutoCleanupManager:
    """
    Automatic memory cleanup scheduling system
    
    Coordinates garbage collection, cache cleanup, and buffer
    pool maintenance during idle periods
    """
    
    def __init__(self):
        self._cleanup_tasks = []
        self._timer = None
        self._is_running = False
        self._last_cleanup = datetime.now()
        self._cleanup_interval = 30.0  # seconds
        self._stats = {
            'cleanups_performed': 0,
            'objects_collected': 0,
            'memory_freed_mb': 0
        }
    
    def start_auto_cleanup(self, interval: float = 30.0):
        """Start automatic cleanup with specified interval"""
        if self._is_running:
            return
        
        self._cleanup_interval = interval
        self._is_running = True
        
        if HAS_QT:
            # Use Qt timer for GUI thread integration
            self._timer = QTimer()
            self._timer.timeout.connect(self._perform_cleanup)
            self._timer.start(int(interval * 1000))  # Convert to milliseconds
        else:
            # Use threading timer as fallback
            self._schedule_next_cleanup()
    
    def stop_auto_cleanup(self):
        """Stop automatic cleanup"""
        self._is_running = False
        if self._timer:
            if HAS_QT and hasattr(self._timer, 'stop'):
                self._timer.stop()
            self._timer = None
    
    def _schedule_next_cleanup(self):
        """Schedule next cleanup using threading timer"""
        if not self._is_running:
            return
        
        self._timer = threading.Timer(self._cleanup_interval, self._perform_cleanup)
        self._timer.daemon = True
        self._timer.start()
    
    def _perform_cleanup(self):
        """Perform scheduled cleanup tasks"""
        try:
            memory_before = self._get_memory_usage()
            objects_before = len(gc.get_objects())
            
            # Trigger garbage collection
            collected = gc.collect()
            
            # Execute registered cleanup tasks
            for task in self._cleanup_tasks:
                try:
                    task()
                except Exception as e:
                    print(f"Cleanup task error: {e}")
            
            # Update statistics
            memory_after = self._get_memory_usage()
            objects_after = len(gc.get_objects())
            
            self._stats['cleanups_performed'] += 1
            self._stats['objects_collected'] += (objects_before - objects_after) + collected
            self._stats['memory_freed_mb'] += max(0, memory_before - memory_after)
            
            self._last_cleanup = datetime.now()
            
            # Schedule next cleanup if using threading
            if not HAS_QT and self._is_running:
                self._schedule_next_cleanup()
                
        except Exception as e:
            print(f"Auto cleanup error: {e}")
    
    def register_cleanup_task(self, task: Callable[[], None]):
        """Register a cleanup task to be executed during auto cleanup"""
        self._cleanup_tasks.append(task)
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cleanup statistics"""
        return {
            'is_running': self._is_running,
            'interval_seconds': self._cleanup_interval,
            'last_cleanup': self._last_cleanup.isoformat(),
            'next_cleanup_in_seconds': max(0, self._cleanup_interval - (datetime.now() - self._last_cleanup).total_seconds()),
            **self._stats
        }


class AdvancedMemoryManager:
    """
    Central coordinator for all memory management systems
    
    Integrates weak reference caching, buffer pooling, Qt optimization,
    memory profiling, and automatic cleanup into a unified system
    """
    
    def __init__(self, 
                 cache_size: int = 1000,
                 buffer_pool_size: int = 50,
                 alert_threshold: float = 85.0,
                 cleanup_interval: float = 30.0):
        
        # Initialize components
        self.cache = WeakReferenceCache("main_cache", cache_size)
        self.buffer_pool = VideoFrameBufferPool(buffer_pool_size)
        self.qt_optimizer = QtMemoryOptimizer()
        self.profiler = MemoryProfiler(alert_threshold)
        self.cleanup_manager = AutoCleanupManager()
        
        # Configuration
        self._initialized = False
        self._config = {
            'cache_size': cache_size,
            'buffer_pool_size': buffer_pool_size,
            'alert_threshold': alert_threshold,
            'cleanup_interval': cleanup_interval
        }
        
        self._setup_integration()
    
    def _setup_integration(self):
        """Setup integration between components"""
        
        # Register cleanup tasks
        self.cleanup_manager.register_cleanup_task(self.cache.cleanup_dead_refs)
        self.cleanup_manager.register_cleanup_task(self.buffer_pool.cleanup_pools)
        self.cleanup_manager.register_cleanup_task(self.qt_optimizer.cleanup_pixmap_cache)
        self.cleanup_manager.register_cleanup_task(self._force_garbage_collection)
        
        # Setup memory alerts
        self.profiler.add_alert_callback(self._handle_memory_alert)
    
    def initialize(self):
        """Initialize and start all memory management systems"""
        if self._initialized:
            return
        
        try:
            # Start monitoring
            self.profiler.start_monitoring(interval=5.0)
            
            # Start auto cleanup
            self.cleanup_manager.start_auto_cleanup(self._config['cleanup_interval'])
            
            self._initialized = True
            print("✅ Advanced Memory Manager initialized successfully")
            
        except Exception as e:
            print(f"❌ Error initializing memory manager: {e}")
            raise
    
    def shutdown(self):
        """Shutdown all memory management systems"""
        try:
            self.profiler.stop_monitoring()
            self.cleanup_manager.stop_auto_cleanup()
            self.cache.clear()
            
            # Final cleanup
            self._force_garbage_collection()
            
            self._initialized = False
            print("✅ Advanced Memory Manager shutdown complete")
            
        except Exception as e:
            print(f"❌ Error during memory manager shutdown: {e}")
    
    def _force_garbage_collection(self):
        """Force comprehensive garbage collection"""
        # Multiple collection passes for thorough cleanup
        for _ in range(3):
            gc.collect()
    
    def _handle_memory_alert(self, level: MemoryAlert, stats: MemoryStats):
        """Handle memory alerts with appropriate responses"""
        
        if level == MemoryAlert.CRITICAL:
            print(f"🚨 CRITICAL MEMORY ALERT: {stats.percent:.1f}% used, {stats.rss_mb:.1f}MB RSS")
            # Aggressive cleanup
            self.cache.clear()
            self.buffer_pool.cleanup_pools()
            self.qt_optimizer.cleanup_pixmap_cache()
            self._force_garbage_collection()
            
        elif level == MemoryAlert.HIGH:
            print(f"⚠️ HIGH MEMORY USAGE: {stats.percent:.1f}% used")
            # Moderate cleanup
            self.cache.cleanup_dead_refs()
            self.buffer_pool.cleanup_pools()
            self._force_garbage_collection()
            
        elif level == MemoryAlert.MEDIUM:
            print(f"ℹ️ Elevated memory usage: {stats.percent:.1f}% used")
            # Light cleanup
            self.cache.cleanup_dead_refs()
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics from all components"""
        
        current_memory = self.profiler.get_current_stats(
            cache=self.cache,
            buffer_pool=self.buffer_pool,
            qt_optimizer=self.qt_optimizer
        )
        
        return {
            'memory_manager': {
                'initialized': self._initialized,
                'config': self._config
            },
            'current_memory': {
                'rss_mb': current_memory.rss_mb,
                'percent': current_memory.percent,
                'available_mb': current_memory.available_mb
            },
            'cache': self.cache.get_stats(),
            'buffer_pool': self.buffer_pool.get_stats(),
            'cleanup_manager': self.cleanup_manager.get_stats(),
            'memory_report': self.profiler.get_memory_report(),
            'qt_objects': self.qt_optimizer.get_qt_object_count(),
            'timestamp': datetime.now().isoformat()
        }
    
    def optimize_for_large_collection(self, expected_items: int):
        """Optimize settings for large video collections"""
        
        if expected_items > 10000:
            # Increase cache size and buffer pool for large collections
            self.cache.max_size = min(2000, expected_items // 5)
            self.buffer_pool.max_pool_size = min(100, expected_items // 100)
            
            # More frequent cleanup for large datasets
            self.cleanup_manager.stop_auto_cleanup()
            self.cleanup_manager.start_auto_cleanup(interval=15.0)
            
            print(f"🔧 Optimized for large collection: {expected_items} items")
    
    def create_memory_snapshot(self) -> Dict[str, Any]:
        """Create detailed memory usage snapshot"""
        
        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'process_info': {
                'pid': os.getpid(),
                'memory_info': dict(psutil.Process().memory_info()._asdict()),
                'memory_percent': psutil.Process().memory_percent()
            },
            'system_memory': dict(psutil.virtual_memory()._asdict()),
            'gc_stats': gc.get_stats(),
            'object_counts': {
                'total_objects': len(gc.get_objects()),
                'garbage_objects': len(gc.garbage),
                'weak_refs': len([obj for obj in gc.get_objects() if type(obj) == weakref.ref])
            },
            'components': self.get_comprehensive_stats()
        }
        
        return snapshot


# Global memory manager instance
_global_memory_manager: Optional[AdvancedMemoryManager] = None

def get_memory_manager() -> AdvancedMemoryManager:
    """Get global memory manager instance"""
    global _global_memory_manager
    
    if _global_memory_manager is None:
        _global_memory_manager = AdvancedMemoryManager()
        _global_memory_manager.initialize()
    
    return _global_memory_manager

def cleanup_memory_manager():
    """Cleanup global memory manager"""
    global _global_memory_manager
    
    if _global_memory_manager:
        _global_memory_manager.shutdown()
        _global_memory_manager = None 