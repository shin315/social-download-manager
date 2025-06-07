# ... existing code ...

# Add at the top of imports
try:
    from core.memory.advanced_memory_manager import get_memory_manager
    HAS_MEMORY_MANAGER = True
except ImportError:
    HAS_MEMORY_MANAGER = False

# ... existing code ...

class ThumbnailCacheManager:
    """
    Advanced multi-tier thumbnail caching system with memory management
    
    Provides three-tier caching:
    1. Memory Cache - Fastest access (LRU with size limit)
    2. QPixmapCache - Qt's built-in pixmap cache  
    3. Disk Cache - SQLite database with file storage
    
    Features:
    - Automatic cache size management
    - Thread-safe operations
    - Cache hit/miss statistics
    - Memory pressure handling
    - Background preloading
    """
    
    def __init__(self, 
                 memory_cache_size: int = 100,
                 disk_cache_size_mb: int = 500,
                 cache_dir: str = None):
        
        # Configuration
        self.memory_cache_size = memory_cache_size
        self.disk_cache_size_mb = disk_cache_size_mb
        self.cache_dir = cache_dir or self._get_default_cache_dir()
        
        # Initialize memory management integration
        if HAS_MEMORY_MANAGER:
            self.memory_manager = get_memory_manager()
            # Use the weak reference cache from memory manager
            self.memory_cache = self.memory_manager.cache
            # Set cache name for tracking
            self.memory_cache.name = "thumbnail_cache"
        else:
            # Fallback to OrderedDict-based LRU cache
            self.memory_cache = {}
            self._access_order = []
        
        # ... existing code ...
        
        # Memory management integration
        self._setup_memory_management()
    
    def _setup_memory_management(self):
        """Setup memory management integration"""
        if not HAS_MEMORY_MANAGER:
            return
        
        # Register cleanup callback for memory pressure
        self.memory_manager.profiler.add_alert_callback(self._handle_memory_alert)
        
        # Register automatic cleanup task
        self.memory_manager.cleanup_manager.register_cleanup_task(self._scheduled_cleanup)
        
        # Optimize Qt widgets for large data
        # Note: This would be called when widgets are created
        # self.memory_manager.qt_optimizer.optimize_widget_for_large_data(widget)
    
    def _handle_memory_alert(self, level, stats):
        """Handle memory pressure alerts"""
        from core.memory.advanced_memory_manager import MemoryAlert
        
        if level == MemoryAlert.HIGH or level == MemoryAlert.CRITICAL:
            # Clear memory cache during high memory pressure
            self._clear_memory_cache()
            print(f"🧹 Cleared thumbnail cache due to {level.value} memory pressure")
        
        elif level == MemoryAlert.MEDIUM:
            # Reduce cache size during medium pressure
            self._reduce_cache_size(factor=0.5)
            print(f"📉 Reduced thumbnail cache size due to {level.value} memory pressure")
    
    def _scheduled_cleanup(self):
        """Scheduled cleanup for dead references and unused items"""
        if HAS_MEMORY_MANAGER:
            # The weak reference cache automatically handles dead references
            self.memory_cache.cleanup_dead_refs()
        else:
            # Fallback cleanup for non-weak reference cache
            self._cleanup_memory_cache()
    
    def _clear_memory_cache(self):
        """Clear memory cache"""
        if HAS_MEMORY_MANAGER:
            self.memory_cache.clear()
        else:
            self.memory_cache.clear()
            self._access_order.clear()
        
        self.stats['memory_cache_clears'] += 1
    
    def _reduce_cache_size(self, factor: float = 0.5):
        """Reduce cache size by given factor"""
        if HAS_MEMORY_MANAGER:
            # Reduce max size of weak reference cache
            new_size = int(self.memory_cache.max_size * factor)
            self.memory_cache.max_size = max(10, new_size)  # Minimum 10 items
        else:
            # Reduce OrderedDict cache
            target_size = int(len(self.memory_cache) * factor)
            while len(self.memory_cache) > target_size and self._access_order:
                oldest_key = self._access_order.pop(0)
                self.memory_cache.pop(oldest_key, None)
    
    def get_thumbnail(self, video_id: str, size: Tuple[int, int] = None) -> Optional[QPixmap]:
        """
        Get thumbnail from cache hierarchy with memory management
        
        Args:
            video_id: Unique identifier for video
            size: Requested thumbnail size (width, height)
            
        Returns:
            QPixmap thumbnail or None if not available
        """
        
        if not video_id:
            return None
        
        size = size or (200, 150)
        cache_key = f"{video_id}_{size[0]}x{size[1]}"
        
        try:
            # 1. Check memory cache (fastest)
            if HAS_MEMORY_MANAGER:
                pixmap = self.memory_cache.get(cache_key)
                if pixmap and isinstance(pixmap, QPixmap):
                    self.stats['memory_hits'] += 1
                    return pixmap
            else:
                # Fallback memory cache
                if cache_key in self.memory_cache:
                    # Update access order
                    self._access_order.remove(cache_key)
                    self._access_order.append(cache_key)
                    self.stats['memory_hits'] += 1
                    return self.memory_cache[cache_key]
            
            # 2. Check QPixmapCache
            pixmap = QPixmapCache.find(cache_key)
            if pixmap and not pixmap.isNull():
                # Store in memory cache for faster access
                self._store_in_memory_cache(cache_key, pixmap)
                self.stats['qpixmap_hits'] += 1
                return pixmap
            
            # 3. Check disk cache
            pixmap = self.disk_cache.get_thumbnail(video_id, size)
            if pixmap and not pixmap.isNull():
                # Store in higher-level caches
                self._store_in_memory_cache(cache_key, pixmap)
                QPixmapCache.insert(cache_key, pixmap)
                self.stats['disk_hits'] += 1
                return pixmap
            
            # Cache miss
            self.stats['misses'] += 1
            return None
            
        except Exception as e:
            print(f"Error retrieving thumbnail: {e}")
            self.stats['errors'] += 1
            return None
    
    def _store_in_memory_cache(self, cache_key: str, pixmap: QPixmap):
        """Store pixmap in memory cache with memory management"""
        if not pixmap or pixmap.isNull():
            return
        
        if HAS_MEMORY_MANAGER:
            # Use weak reference cache
            self.memory_cache.set(cache_key, pixmap)
        else:
            # Fallback OrderedDict cache with LRU eviction
            if cache_key in self.memory_cache:
                self._access_order.remove(cache_key)
            elif len(self.memory_cache) >= self.memory_cache_size:
                # Evict oldest item
                oldest_key = self._access_order.pop(0)
                self.memory_cache.pop(oldest_key, None)
            
            self.memory_cache[cache_key] = pixmap
            self._access_order.append(cache_key)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics including memory management
        
        Returns:
            Dictionary with cache statistics
        """
        
        base_stats = {
            'memory_hits': self.stats['memory_hits'],
            'qpixmap_hits': self.stats['qpixmap_hits'], 
            'disk_hits': self.stats['disk_hits'],
            'misses': self.stats['misses'],
            'errors': self.stats['errors'],
            'generations': self.stats['generations'],
            'memory_cache_size': len(self.memory_cache) if not HAS_MEMORY_MANAGER else self.memory_cache.get_stats()['size'],
            'disk_cache_stats': self.disk_cache.get_stats(),
            'memory_cache_clears': self.stats.get('memory_cache_clears', 0)
        }
        
        # Add memory management stats if available
        if HAS_MEMORY_MANAGER:
            memory_stats = self.memory_manager.get_comprehensive_stats()
            base_stats.update({
                'memory_manager': {
                    'cache_stats': self.memory_cache.get_stats(),
                    'memory_usage_mb': memory_stats['current_memory']['rss_mb'],
                    'memory_percent': memory_stats['current_memory']['percent'],
                    'qt_objects': memory_stats['qt_objects']
                }
            })
        
        # Calculate hit rates
        total_requests = sum([
            base_stats['memory_hits'],
            base_stats['qpixmap_hits'], 
            base_stats['disk_hits'],
            base_stats['misses']
        ])
        
        if total_requests > 0:
            base_stats['total_hit_rate'] = (
                base_stats['memory_hits'] + 
                base_stats['qpixmap_hits'] + 
                base_stats['disk_hits']
            ) / total_requests
            base_stats['memory_hit_rate'] = base_stats['memory_hits'] / total_requests
        else:
            base_stats['total_hit_rate'] = 0.0
            base_stats['memory_hit_rate'] = 0.0
        
        return base_stats
    
    def clear_all_caches(self):
        """
        Clear all cache levels with memory management
        """
        
        # Clear memory cache
        self._clear_memory_cache()
        
        # Clear QPixmapCache
        QPixmapCache.clear()
        
        # Clear disk cache
        self.disk_cache.clear_cache()
        
        # Force garbage collection if memory manager available
        if HAS_MEMORY_MANAGER:
            self.memory_manager._force_garbage_collection()
        
        print("🧹 All thumbnail caches cleared")
    
    def optimize_for_large_collection(self, video_count: int):
        """
        Optimize cache settings for large video collections
        
        Args:
            video_count: Expected number of videos in collection
        """
        
        if video_count > 10000:
            # Increase cache sizes for large collections
            self.memory_cache_size = min(500, video_count // 20)
            
            if HAS_MEMORY_MANAGER:
                self.memory_cache.max_size = self.memory_cache_size
                # Notify memory manager about large collection
                self.memory_manager.optimize_for_large_collection(video_count)
            
            # Increase QPixmapCache limit
            QPixmapCache.setCacheLimit(min(100 * 1024, video_count * 10))  # 10KB per video estimate
            
            print(f"🔧 Optimized thumbnail cache for {video_count} videos")
    
    def create_cache_snapshot(self) -> Dict[str, Any]:
        """Create detailed cache snapshot for debugging"""
        
        snapshot = {
            'timestamp': time.time(),
            'cache_stats': self.get_cache_stats(),
            'memory_cache_keys': list(self.memory_cache._cache.keys()) if HAS_MEMORY_MANAGER else list(self.memory_cache.keys()),
            'qpixmap_cache_limit': QPixmapCache.cacheLimit(),
            'disk_cache_info': self.disk_cache.get_stats()
        }
        
        # Add memory management snapshot if available
        if HAS_MEMORY_MANAGER:
            snapshot['memory_snapshot'] = self.memory_manager.create_memory_snapshot()
        
        return snapshot

# ... existing code ... 