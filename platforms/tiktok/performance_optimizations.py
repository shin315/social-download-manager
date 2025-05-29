"""
TikTok Handler Performance Optimizations

This module contains performance enhancements for the TikTok platform handler,
including caching strategies, connection pooling, and memory optimizations.
"""

import asyncio
import logging
import time
import threading
import weakref
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Callable, Union
import hashlib
import json
import re
import os
from pathlib import Path

# Import for performance monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with TTL support"""
    value: Any
    created_at: datetime
    ttl_seconds: int
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        return datetime.now() - self.created_at > timedelta(seconds=self.ttl_seconds)
    
    def access(self) -> Any:
        """Mark entry as accessed and return value"""
        self.access_count += 1
        self.last_accessed = datetime.now()
        return self.value


class TikTokPerformanceCache:
    """High-performance caching system with TTL and LRU eviction"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._access_order: List[str] = []
        
        # Performance metrics
        self.hit_count = 0
        self.miss_count = 0
        self.eviction_count = 0
        
        # Background cleanup
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_data = f"{prefix}:{repr(args)}:{repr(sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()[:16]
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if entry.is_expired:
                    del self._cache[key]
                    self._access_order.remove(key)
                    self.miss_count += 1
                    return None
                
                # Update access order for LRU
                if key in self._access_order:
                    self._access_order.remove(key)
                self._access_order.append(key)
                
                self.hit_count += 1
                return entry.access()
            
            self.miss_count += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        with self._lock:
            ttl = ttl or self.default_ttl
            entry = CacheEntry(value, datetime.now(), ttl)
            
            # Remove existing entry from access order
            if key in self._cache:
                self._access_order.remove(key)
            
            self._cache[key] = entry
            self._access_order.append(key)
            
            # Evict if necessary
            self._evict_if_needed()
            
            # Periodic cleanup
            self._cleanup_if_needed()
    
    def _evict_if_needed(self) -> None:
        """Evict least recently used entries if cache is full"""
        while len(self._cache) > self.max_size:
            if not self._access_order:
                break
            
            lru_key = self._access_order.pop(0)
            if lru_key in self._cache:
                del self._cache[lru_key]
                self.eviction_count += 1
    
    def _cleanup_if_needed(self) -> None:
        """Cleanup expired entries periodically"""
        now = time.time()
        if now - self._last_cleanup > self._cleanup_interval:
            self._cleanup_expired()
            self._last_cleanup = now
    
    def _cleanup_expired(self) -> None:
        """Remove all expired entries"""
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired
        ]
        
        for key in expired_keys:
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total_requests = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'size': len(self._cache),
            'max_size': self.max_size,
            'hit_count': self.hit_count,
            'miss_count': self.miss_count,
            'hit_rate_percent': round(hit_rate, 2),
            'eviction_count': self.eviction_count,
            'memory_usage_estimate': sum(
                len(str(entry.value)) for entry in self._cache.values()
            )
        }


class RegexCache:
    """Cache for compiled regex patterns"""
    
    def __init__(self):
        self._patterns: Dict[str, re.Pattern] = {}
        self._lock = threading.Lock()
    
    def get_pattern(self, pattern_str: str, flags: int = 0) -> re.Pattern:
        """Get compiled regex pattern (cached)"""
        cache_key = f"{pattern_str}:{flags}"
        
        if cache_key not in self._patterns:
            with self._lock:
                if cache_key not in self._patterns:
                    self._patterns[cache_key] = re.compile(pattern_str, flags)
        
        return self._patterns[cache_key]
    
    def clear(self) -> None:
        """Clear all cached patterns"""
        with self._lock:
            self._patterns.clear()


class ConnectionPool:
    """Simple connection pool for HTTP requests"""
    
    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        self._sessions: List[Any] = []
        self._in_use: Set[Any] = set()
        self._lock = threading.Lock()
        
        # Create initial sessions
        try:
            import requests
            for _ in range(min(3, max_connections)):
                session = requests.Session()
                # Configure for optimal performance
                session.headers.update({
                    'Connection': 'keep-alive',
                    'Keep-Alive': 'timeout=30, max=10'
                })
                adapter = requests.adapters.HTTPAdapter(
                    pool_connections=10,
                    pool_maxsize=20,
                    max_retries=3
                )
                session.mount('http://', adapter)
                session.mount('https://', adapter)
                self._sessions.append(session)
        except ImportError:
            logger.warning("requests library not available for connection pooling")
    
    def get_session(self):
        """Get an available session from the pool"""
        with self._lock:
            # Find available session
            for session in self._sessions:
                if session not in self._in_use:
                    self._in_use.add(session)
                    return session
            
            # Create new session if under limit
            if len(self._sessions) < self.max_connections:
                try:
                    import requests
                    session = requests.Session()
                    session.headers.update({
                        'Connection': 'keep-alive',
                        'Keep-Alive': 'timeout=30, max=10'
                    })
                    self._sessions.append(session)
                    self._in_use.add(session)
                    return session
                except ImportError:
                    pass
            
            # Return first available (may block)
            return self._sessions[0] if self._sessions else None
    
    def return_session(self, session):
        """Return session to the pool"""
        with self._lock:
            self._in_use.discard(session)


class PerformanceMonitor:
    """Real-time performance monitoring"""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self.operation_counts: Dict[str, int] = {}
        self._lock = threading.Lock()
        self.start_time = time.time()
    
    def record_operation(self, operation: str, duration: float) -> None:
        """Record operation performance"""
        with self._lock:
            if operation not in self.metrics:
                self.metrics[operation] = []
            self.metrics[operation].append(duration)
            
            # Keep only last 100 measurements
            if len(self.metrics[operation]) > 100:
                self.metrics[operation] = self.metrics[operation][-100:]
            
            self.operation_counts[operation] = self.operation_counts.get(operation, 0) + 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        with self._lock:
            stats = {
                'uptime_seconds': time.time() - self.start_time,
                'operation_counts': self.operation_counts.copy(),
                'operation_stats': {}
            }
            
            for operation, times in self.metrics.items():
                if times:
                    stats['operation_stats'][operation] = {
                        'count': len(times),
                        'avg_duration': sum(times) / len(times),
                        'min_duration': min(times),
                        'max_duration': max(times),
                        'total_duration': sum(times)
                    }
            
            # Add system metrics if available
            if PSUTIL_AVAILABLE:
                process = psutil.Process()
                stats['system'] = {
                    'cpu_percent': process.cpu_percent(),
                    'memory_mb': process.memory_info().rss / 1024 / 1024,
                    'memory_percent': process.memory_percent(),
                    'open_files': len(process.open_files()),
                    'threads': process.num_threads()
                }
            
            return stats


class AsyncTaskPool:
    """Pool for managing async task execution"""
    
    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_tasks: Set[asyncio.Task] = set()
        self._completed_count = 0
        self._failed_count = 0
    
    async def submit(self, coro) -> Any:
        """Submit coroutine for execution"""
        async with self._semaphore:
            task = asyncio.create_task(coro)
            self._active_tasks.add(task)
            
            try:
                result = await task
                self._completed_count += 1
                return result
            except Exception as e:
                self._failed_count += 1
                raise
            finally:
                self._active_tasks.discard(task)
    
    async def submit_many(self, coros: List) -> List[Any]:
        """Submit multiple coroutines for concurrent execution"""
        tasks = [self.submit(coro) for coro in coros]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get task pool statistics"""
        return {
            'max_concurrent': self.max_concurrent,
            'active_tasks': len(self._active_tasks),
            'completed_count': self._completed_count,
            'failed_count': self._failed_count,
            'available_slots': self.max_concurrent - len(self._active_tasks)
        }


class MemoryOptimizedProcessor:
    """Memory-efficient data processing utilities"""
    
    @staticmethod
    def lazy_json_parse(data: Union[str, bytes], target_keys: Optional[Set[str]] = None) -> Dict[str, Any]:
        """Parse JSON with memory optimization for large objects"""
        if isinstance(data, bytes):
            data = data.decode('utf-8')
        
        # For small data, use standard JSON parsing
        if len(data) < 10000:
            return json.loads(data)
        
        # For large data, use streaming approach if specific keys needed
        if target_keys:
            result = {}
            try:
                full_data = json.loads(data)
                for key in target_keys:
                    if key in full_data:
                        result[key] = full_data[key]
                return result
            except:
                return json.loads(data)  # Fallback to full parsing
        
        return json.loads(data)
    
    @staticmethod
    def batch_process(items: List[Any], batch_size: int = 100) -> List[List[Any]]:
        """Split items into memory-efficient batches"""
        return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
    
    @staticmethod
    def optimize_string_list(strings: List[str]) -> List[str]:
        """Optimize memory usage for string lists"""
        # Remove duplicates while preserving order
        seen = set()
        result = []
        for s in strings:
            if s not in seen:
                seen.add(s)
                result.append(s.strip())
        return result


class TikTokOptimizedOperations:
    """Optimized operations for common TikTok handler tasks"""
    
    def __init__(self):
        self.cache = TikTokPerformanceCache()
        self.regex_cache = RegexCache()
        self.connection_pool = ConnectionPool()
        self.performance_monitor = PerformanceMonitor()
        self.task_pool = AsyncTaskPool()
        
        # Pre-compile frequently used regex patterns
        self._precompile_patterns()
    
    def _precompile_patterns(self) -> None:
        """Pre-compile commonly used regex patterns"""
        patterns = [
            r'#[\w\u4e00-\u9fff]+',  # Hashtags
            r'@[\w\.-]+',            # Mentions
            r'https?://[^\s]+',      # URLs
            r'\d+',                  # Numbers
        ]
        
        for pattern in patterns:
            self.regex_cache.get_pattern(pattern)
    
    async def extract_metadata_optimized(
        self, 
        result: Dict[str, Any], 
        url: str,
        cache_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Optimized metadata extraction with caching"""
        start_time = time.time()
        
        # Check cache first
        if cache_key:
            cached = self.cache.get(cache_key)
            if cached:
                self.performance_monitor.record_operation('metadata_cache_hit', time.time() - start_time)
                return cached
        
        # Process with memory optimization
        target_keys = {
            'id', 'title', 'description', 'uploader', 'duration',
            'view_count', 'like_count', 'upload_date', 'formats',
            'thumbnail', 'creator', 'hashtags', 'music'
        }
        
        # Use optimized JSON processing for large results
        if len(str(result)) > 50000:
            result = MemoryOptimizedProcessor.lazy_json_parse(
                json.dumps(result), target_keys
            )
        
        # Extract hashtags and mentions efficiently
        description = result.get('description', '') or ''
        title = result.get('title', '') or ''
        combined_text = f"{title} {description}"
        
        hashtag_pattern = self.regex_cache.get_pattern(r'#[\w\u4e00-\u9fff]+')
        mention_pattern = self.regex_cache.get_pattern(r'@[\w\.-]+')
        
        hashtags = [
            match.group()[1:].lower() 
            for match in hashtag_pattern.finditer(combined_text)
        ]
        mentions = [
            match.group()[1:].lower() 
            for match in mention_pattern.finditer(combined_text)
        ]
        
        # Optimize lists
        hashtags = MemoryOptimizedProcessor.optimize_string_list(hashtags)
        mentions = MemoryOptimizedProcessor.optimize_string_list(mentions)
        
        # Build optimized metadata
        metadata = {
            'url': url,
            'id': result.get('id', ''),
            'title': title,
            'description': description,
            'creator': result.get('uploader', ''),
            'duration': result.get('duration'),
            'view_count': result.get('view_count', 0),
            'like_count': result.get('like_count', 0),
            'hashtags': hashtags,
            'mentions': mentions,
            'formats': result.get('formats', [])
        }
        
        # Cache result
        if cache_key:
            self.cache.set(cache_key, metadata, ttl=1800)  # 30 minutes
        
        duration = time.time() - start_time
        self.performance_monitor.record_operation('metadata_extraction', duration)
        
        return metadata
    
    async def process_formats_batch(self, formats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process video formats in optimized batches"""
        start_time = time.time()
        
        if not formats:
            return []
        
        # Process in batches for memory efficiency
        batches = MemoryOptimizedProcessor.batch_process(formats, batch_size=50)
        processed_formats = []
        
        for batch in batches:
            # Process batch concurrently
            tasks = [self._process_single_format(fmt) for fmt in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions and add successful results
            for result in batch_results:
                if not isinstance(result, Exception) and result:
                    processed_formats.append(result)
        
        duration = time.time() - start_time
        self.performance_monitor.record_operation('format_processing', duration)
        
        return processed_formats
    
    async def _process_single_format(self, fmt: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single format entry"""
        try:
            return {
                'format_id': fmt.get('format_id', ''),
                'url': fmt.get('url', ''),
                'quality': self._map_quality_optimized(fmt),
                'filesize': fmt.get('filesize'),
                'ext': fmt.get('ext', 'mp4')
            }
        except Exception:
            return None
    
    def _map_quality_optimized(self, fmt: Dict[str, Any]) -> str:
        """Optimized quality mapping with caching"""
        height = fmt.get('height', 0) or 0
        width = fmt.get('width', 0) or 0
        
        # Use cached quality mappings
        cache_key = f"quality_{height}_{width}"
        cached_quality = self.cache.get(cache_key)
        if cached_quality:
            return cached_quality
        
        # Determine quality
        if height >= 1080 or width >= 1920:
            quality = 'HD'
        elif height >= 720 or width >= 1280:
            quality = 'SD'
        elif height >= 480 or width >= 854:
            quality = 'LD'
        else:
            quality = 'MOBILE'
        
        # Cache result
        self.cache.set(cache_key, quality, ttl=3600)  # 1 hour
        return quality
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        return {
            'cache_stats': self.cache.get_stats(),
            'performance_stats': self.performance_monitor.get_stats(),
            'task_pool_stats': self.task_pool.get_stats(),
            'regex_cache_size': len(self.regex_cache._patterns),
            'connection_pool_size': len(self.connection_pool._sessions)
        }
    
    def cleanup(self) -> None:
        """Cleanup resources"""
        self.cache.clear()
        self.regex_cache.clear()


# Global instance for reuse
_optimized_operations = None

def get_optimized_operations() -> TikTokOptimizedOperations:
    """Get global optimized operations instance"""
    global _optimized_operations
    if _optimized_operations is None:
        _optimized_operations = TikTokOptimizedOperations()
    return _optimized_operations 