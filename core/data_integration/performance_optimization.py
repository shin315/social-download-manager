"""
Performance Optimization for Large Dataset Management
Social Download Manager v2.0

This module provides comprehensive performance optimization patterns for handling
large repository datasets efficiently, including lazy loading, virtual scrolling,
intelligent caching, and memory optimization strategies.

Builds on Task 18.1-18.8 components for optimal performance.
"""

import asyncio
import logging
import threading
import time
from typing import Dict, List, Optional, Any, Callable, Generator, Union, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
from collections import OrderedDict, deque
from threading import Lock, RLock
import weakref
import gc
import sys
from functools import lru_cache, wraps
import pickle

# Core imports
try:
    from data.models.repositories import IContentRepository
    from data.models.content import ContentModel, ContentStatus, PlatformType
    from core.event_system import get_event_bus, EventType, Event
    
    # Task 19 Error Handling Integration
    from data.models.error_management import ErrorInfo, ErrorCategory, ErrorSeverity, ErrorContext
    from core.component_error_handlers import ComponentErrorHandler, ComponentErrorConfig
    from core.logging_strategy import get_enhanced_logger, log_error_with_context
    
    # Task 18 Data Integration Components
    from core.data_integration.data_binding_strategy import get_data_binding_manager
    from core.data_integration.repository_state_sync import get_repository_state_manager
    from core.data_integration.video_table_repository_adapter import get_video_table_adapter
    from core.data_integration.async_loading_patterns import get_async_repository_manager
    
    PERFORMANCE_OPTIMIZATION_AVAILABLE = True
except ImportError as e:
    PERFORMANCE_OPTIMIZATION_AVAILABLE = False
    logging.warning(f"Performance optimization dependencies not available: {e}")
    # Fallback imports
    from typing import Any as ErrorCategory, Any as ErrorSeverity, Any as ErrorContext
    from data.models.content import ContentModel, ContentStatus, PlatformType
    from core.event_system import get_event_bus, EventType, Event
    IContentRepository = None


class CacheStrategy(Enum):
    """Caching strategies for performance optimization"""
    LRU = "lru"                    # Least Recently Used
    LFU = "lfu"                    # Least Frequently Used  
    TTL = "ttl"                    # Time To Live
    ADAPTIVE = "adaptive"          # Adaptive based on usage patterns
    HIERARCHICAL = "hierarchical"  # Multi-level caching


class LoadingStrategy(Enum):
    """Loading strategies for large datasets"""
    LAZY = "lazy"                  # Load only when needed
    EAGER = "eager"                # Load everything upfront
    PROGRESSIVE = "progressive"    # Load in chunks progressively
    PREDICTIVE = "predictive"      # Predict and pre-load likely needed data
    VIRTUAL = "virtual"            # Virtual scrolling/pagination


class MemoryTier(Enum):
    """Memory tier levels for optimization"""
    HOT = "hot"                    # Frequently accessed data (in memory)
    WARM = "warm"                  # Moderately accessed data (compressed in memory)
    COLD = "cold"                  # Rarely accessed data (disk cache)


@dataclass
class PerformanceMetrics:
    """Performance tracking metrics"""
    cache_hits: int = 0
    cache_misses: int = 0
    cache_evictions: int = 0
    memory_usage_mb: float = 0.0
    avg_load_time_ms: float = 0.0
    peak_memory_mb: float = 0.0
    total_requests: int = 0
    concurrent_requests: int = 0
    items_loaded: int = 0
    items_cached: int = 0
    compression_ratio: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)
    
    @property
    def cache_hit_ratio(self) -> float:
        """Calculate cache hit ratio"""
        total = self.cache_hits + self.cache_misses
        return (self.cache_hits / total * 100) if total > 0 else 0.0
    
    @property
    def efficiency_score(self) -> float:
        """Calculate overall efficiency score (0-100)"""
        hit_ratio_score = min(self.cache_hit_ratio, 100) * 0.4
        memory_score = max(0, 100 - (self.memory_usage_mb / 1024 * 100)) * 0.3  # Penalty for high memory
        load_time_score = max(0, 100 - (self.avg_load_time_ms / 1000 * 100)) * 0.3  # Penalty for slow loading
        return hit_ratio_score + memory_score + load_time_score


@dataclass
class CacheItem:
    """Cache item with metadata"""
    key: str
    data: Any
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)
    ttl_seconds: Optional[int] = None
    memory_tier: MemoryTier = MemoryTier.HOT
    compressed: bool = False
    size_bytes: int = 0
    
    @property
    def is_expired(self) -> bool:
        """Check if item has expired based on TTL"""
        if self.ttl_seconds is None:
            return False
        elapsed = (datetime.now() - self.created_at).total_seconds()
        return elapsed > self.ttl_seconds
    
    @property
    def age_seconds(self) -> float:
        """Get age of cache item in seconds"""
        return (datetime.now() - self.created_at).total_seconds()
    
    def touch(self):
        """Update access information"""
        self.access_count += 1
        self.last_accessed = datetime.now()


class IntelligentCache:
    """
    Intelligent multi-tier cache with adaptive strategies
    Supports LRU, LFU, TTL, and adaptive caching patterns
    """
    
    def __init__(self, 
                 max_size: int = 10000,
                 strategy: CacheStrategy = CacheStrategy.ADAPTIVE,
                 default_ttl_seconds: Optional[int] = 3600,  # 1 hour
                 memory_limit_mb: float = 512.0,
                 compression_threshold_bytes: int = 1024 * 1024):  # 1MB
        
        self.max_size = max_size
        self.strategy = strategy
        self.default_ttl_seconds = default_ttl_seconds
        self.memory_limit_mb = memory_limit_mb
        self.compression_threshold_bytes = compression_threshold_bytes
        
        # Cache storage
        self._cache: OrderedDict[str, CacheItem] = OrderedDict()
        self._access_frequencies: Dict[str, int] = {}
        self._lock = RLock()
        
        # Performance tracking
        self.metrics = PerformanceMetrics()
        
        # Error handling
        if PERFORMANCE_OPTIMIZATION_AVAILABLE:
            self.error_handler = ComponentErrorHandler(
                ComponentErrorConfig(
                    component_name="IntelligentCache",
                    error_category=ErrorCategory.PERFORMANCE,
                    default_severity=ErrorSeverity.MEDIUM,
                    max_retries=2
                )
            )
            self.logger = get_enhanced_logger("IntelligentCache")
        else:
            self.error_handler = None
            self.logger = logging.getLogger(__name__)
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache with intelligent access tracking"""
        try:
            with self._lock:
                if key not in self._cache:
                    self.metrics.cache_misses += 1
                    return None
                
                item = self._cache[key]
                
                # Check expiration
                if item.is_expired:
                    self._remove_item(key)
                    self.metrics.cache_misses += 1
                    return None
                
                # Update access patterns
                item.touch()
                self._access_frequencies[key] = self._access_frequencies.get(key, 0) + 1
                
                # Move to end for LRU (most recently used)
                self._cache.move_to_end(key)
                
                self.metrics.cache_hits += 1
                return item.data
                
        except Exception as e:
            if self.error_handler:
                self.error_handler.handle_error(e, operation="cache_get", context={"key": key})
            return None
    
    def put(self, key: str, data: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Put item into cache with intelligent placement"""
        try:
            with self._lock:
                # Calculate data size
                try:
                    size_bytes = sys.getsizeof(pickle.dumps(data))
                except:
                    size_bytes = sys.getsizeof(data)
                
                # Check if we need compression
                compressed = False
                if size_bytes > self.compression_threshold_bytes:
                    try:
                        import gzip
                        compressed_data = gzip.compress(pickle.dumps(data))
                        if len(compressed_data) < size_bytes * 0.8:  # 20% compression benefit
                            data = compressed_data
                            compressed = True
                            size_bytes = len(compressed_data)
                    except:
                        pass  # Compression failed, use original data
                
                # Determine memory tier
                memory_tier = self._determine_memory_tier(key, size_bytes)
                
                # Create cache item
                item = CacheItem(
                    key=key,
                    data=data,
                    ttl_seconds=ttl_seconds or self.default_ttl_seconds,
                    memory_tier=memory_tier,
                    compressed=compressed,
                    size_bytes=size_bytes
                )
                
                # Remove existing item if present
                if key in self._cache:
                    self._remove_item(key)
                
                # Check capacity and evict if necessary
                self._ensure_capacity()
                
                # Add new item
                self._cache[key] = item
                self.metrics.items_cached += 1
                
                # Update memory usage
                self._update_memory_metrics()
                
                return True
                
        except Exception as e:
            if self.error_handler:
                self.error_handler.handle_error(e, operation="cache_put", context={"key": key})
            return False
    
    def _determine_memory_tier(self, key: str, size_bytes: int) -> MemoryTier:
        """Determine appropriate memory tier for cache item"""
        frequency = self._access_frequencies.get(key, 0)
        
        if frequency > 10 or size_bytes < 1024:  # Small or frequently accessed
            return MemoryTier.HOT
        elif frequency > 2 or size_bytes < 1024 * 1024:  # Medium access or size
            return MemoryTier.WARM
        else:
            return MemoryTier.COLD
    
    def _ensure_capacity(self):
        """Ensure cache doesn't exceed capacity limits"""
        while len(self._cache) >= self.max_size:
            self._evict_item()
        
        # Check memory usage
        current_memory_mb = self._calculate_memory_usage_mb()
        while current_memory_mb > self.memory_limit_mb and self._cache:
            self._evict_item()
            current_memory_mb = self._calculate_memory_usage_mb()
    
    def _evict_item(self):
        """Evict item based on caching strategy"""
        if not self._cache:
            return
        
        evict_key = None
        
        if self.strategy == CacheStrategy.LRU:
            # Remove least recently used (first item)
            evict_key = next(iter(self._cache))
        
        elif self.strategy == CacheStrategy.LFU:
            # Remove least frequently used
            min_freq = float('inf')
            for key, item in self._cache.items():
                freq = self._access_frequencies.get(key, 0)
                if freq < min_freq:
                    min_freq = freq
                    evict_key = key
        
        elif self.strategy == CacheStrategy.TTL:
            # Remove expired items first, then oldest
            oldest_key = None
            oldest_time = datetime.now()
            
            for key, item in self._cache.items():
                if item.is_expired:
                    evict_key = key
                    break
                if item.created_at < oldest_time:
                    oldest_time = item.created_at
                    oldest_key = key
            
            if evict_key is None:
                evict_key = oldest_key
        
        elif self.strategy == CacheStrategy.ADAPTIVE:
            # Adaptive strategy combining frequency, recency, and size
            best_score = float('-inf')
            
            for key, item in self._cache.items():
                if item.is_expired:
                    evict_key = key
                    break
                
                frequency = self._access_frequencies.get(key, 0)
                recency_score = 1.0 / (item.age_seconds + 1)
                size_penalty = item.size_bytes / (1024 * 1024)  # MB penalty
                
                # Higher score = keep longer
                score = frequency * 0.4 + recency_score * 0.4 - size_penalty * 0.2
                
                if score < best_score:
                    best_score = score
                    evict_key = key
        
        if evict_key:
            self._remove_item(evict_key)
            self.metrics.cache_evictions += 1
    
    def _remove_item(self, key: str):
        """Remove item from cache"""
        if key in self._cache:
            del self._cache[key]
        if key in self._access_frequencies:
            del self._access_frequencies[key]
    
    def _calculate_memory_usage_mb(self) -> float:
        """Calculate current memory usage in MB"""
        total_bytes = sum(item.size_bytes for item in self._cache.values())
        return total_bytes / (1024 * 1024)
    
    def _update_memory_metrics(self):
        """Update memory usage metrics"""
        current_mb = self._calculate_memory_usage_mb()
        self.metrics.memory_usage_mb = current_mb
        self.metrics.peak_memory_mb = max(self.metrics.peak_memory_mb, current_mb)
    
    def clear(self):
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._access_frequencies.clear()
            self.metrics = PerformanceMetrics()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            self._update_memory_metrics()
            
            return {
                "total_items": len(self._cache),
                "memory_usage_mb": self.metrics.memory_usage_mb,
                "cache_hit_ratio": self.metrics.cache_hit_ratio,
                "efficiency_score": self.metrics.efficiency_score,
                "cache_hits": self.metrics.cache_hits,
                "cache_misses": self.metrics.cache_misses,
                "cache_evictions": self.metrics.cache_evictions,
                "strategy": self.strategy.value,
                "memory_tiers": {
                    tier.value: sum(1 for item in self._cache.values() if item.memory_tier == tier)
                    for tier in MemoryTier
                }
            }


@dataclass
class PaginationConfig:
    """Configuration for pagination and virtual scrolling"""
    page_size: int = 100
    prefetch_pages: int = 2           # Pages to prefetch ahead
    max_cached_pages: int = 10        # Maximum pages to keep in memory
    virtual_buffer_size: int = 1000   # Virtual scrolling buffer
    lazy_load_threshold: int = 50     # Items from end to trigger load
    progressive_chunk_size: int = 25  # Items per progressive load


class VirtualScrollManager:
    """
    Virtual scrolling manager for large datasets
    Provides efficient rendering of large lists without memory overhead
    """
    
    def __init__(self, 
                 config: PaginationConfig = None,
                 repository: Optional[IContentRepository] = None):
        
        self.config = config or PaginationConfig()
        self.repository = repository
        
        # Virtual scrolling state
        self.total_items: int = 0
        self.visible_range: Tuple[int, int] = (0, 0)
        self.loaded_pages: Dict[int, List[ContentModel]] = {}
        self.loading_pages: Set[int] = set()
        
        # Cache integration
        self.cache = IntelligentCache(
            max_size=self.config.max_cached_pages * self.config.page_size,
            strategy=CacheStrategy.ADAPTIVE
        )
        
        # Performance tracking
        self.metrics = PerformanceMetrics()
        self._lock = Lock()
        
        # Error handling
        if PERFORMANCE_OPTIMIZATION_AVAILABLE:
            self.error_handler = ComponentErrorHandler(
                ComponentErrorConfig(
                    component_name="VirtualScrollManager",
                    error_category=ErrorCategory.PERFORMANCE,
                    default_severity=ErrorSeverity.MEDIUM
                )
            )
            self.logger = get_enhanced_logger("VirtualScrollManager")
        else:
            self.error_handler = None
            self.logger = logging.getLogger(__name__)
    
    async def initialize(self) -> bool:
        """Initialize virtual scroll manager with total item count"""
        try:
            if self.repository:
                # Get total count efficiently
                total_count = await self._get_total_count()
                self.total_items = total_count
                
                # Pre-load first page
                await self.load_page(0)
                
                return True
            return False
            
        except Exception as e:
            if self.error_handler:
                self.error_handler.handle_error(e, operation="virtual_scroll_init")
            return False
    
    async def _get_total_count(self) -> int:
        """Get total item count from repository efficiently"""
        try:
            # Try to get count from cache first
            cached_count = self.cache.get("total_count")
            if cached_count is not None:
                return cached_count
            
            # Get count from repository
            if hasattr(self.repository, 'count'):
                count = await self.repository.count()
            else:
                # Fallback: estimate from first large query
                items = await self.repository.get_all(limit=10000)
                count = len(items)
            
            # Cache the count with short TTL
            self.cache.put("total_count", count, ttl_seconds=300)  # 5 minutes
            
            return count
            
        except Exception as e:
            self.logger.error(f"Error getting total count: {e}")
            return 0
    
    async def set_visible_range(self, start_index: int, end_index: int):
        """Set the currently visible range for virtual scrolling"""
        self.visible_range = (start_index, end_index)
        
        # Calculate required pages
        start_page = start_index // self.config.page_size
        end_page = end_index // self.config.page_size
        
        # Load required pages
        load_tasks = []
        for page_num in range(start_page, end_page + 1):
            if page_num not in self.loaded_pages and page_num not in self.loading_pages:
                load_tasks.append(self.load_page(page_num))
        
        # Prefetch next pages
        for i in range(1, self.config.prefetch_pages + 1):
            prefetch_page = end_page + i
            if (prefetch_page not in self.loaded_pages and 
                prefetch_page not in self.loading_pages and
                prefetch_page * self.config.page_size < self.total_items):
                load_tasks.append(self.load_page(prefetch_page))
        
        # Execute loads concurrently
        if load_tasks:
            await asyncio.gather(*load_tasks, return_exceptions=True)
        
        # Clean up old pages
        self._cleanup_old_pages(start_page, end_page)
    
    async def load_page(self, page_num: int) -> List[ContentModel]:
        """Load a specific page of data"""
        try:
            with self._lock:
                if page_num in self.loaded_pages:
                    return self.loaded_pages[page_num]
                
                if page_num in self.loading_pages:
                    return []  # Already loading
                
                self.loading_pages.add(page_num)
            
            # Check cache first
            cache_key = f"page_{page_num}"
            cached_page = self.cache.get(cache_key)
            if cached_page:
                with self._lock:
                    self.loaded_pages[page_num] = cached_page
                    self.loading_pages.discard(page_num)
                return cached_page
            
            # Load from repository
            start_time = time.time()
            offset = page_num * self.config.page_size
            
            if hasattr(self.repository, 'get_paginated'):
                items = await self.repository.get_paginated(
                    offset=offset,
                    limit=self.config.page_size
                )
            else:
                # Fallback: get all and slice
                all_items = await self.repository.get_all()
                items = all_items[offset:offset + self.config.page_size]
            
            load_time_ms = (time.time() - start_time) * 1000
            
            # Update metrics
            self.metrics.avg_load_time_ms = (
                (self.metrics.avg_load_time_ms * self.metrics.total_requests + load_time_ms) /
                (self.metrics.total_requests + 1)
            )
            self.metrics.total_requests += 1
            self.metrics.items_loaded += len(items)
            
            # Cache the page
            self.cache.put(cache_key, items, ttl_seconds=1800)  # 30 minutes
            
            # Store in memory
            with self._lock:
                self.loaded_pages[page_num] = items
                self.loading_pages.discard(page_num)
            
            return items
            
        except Exception as e:
            with self._lock:
                self.loading_pages.discard(page_num)
            
            if self.error_handler:
                self.error_handler.handle_error(
                    e,
                    operation="load_page",
                    context={"page_num": page_num}
                )
            return []
    
    def _cleanup_old_pages(self, current_start_page: int, current_end_page: int):
        """Clean up old pages outside the active range"""
        with self._lock:
            pages_to_remove = []
            
            for page_num in list(self.loaded_pages.keys()):
                distance_from_current = min(
                    abs(page_num - current_start_page),
                    abs(page_num - current_end_page)
                )
                
                # Remove pages that are far from current range
                if distance_from_current > self.config.prefetch_pages + 2:
                    pages_to_remove.append(page_num)
            
            # Keep only max_cached_pages
            if len(self.loaded_pages) > self.config.max_cached_pages:
                # Sort by distance from current range and remove furthest
                all_pages = list(self.loaded_pages.keys())
                all_pages.sort(key=lambda p: min(
                    abs(p - current_start_page),
                    abs(p - current_end_page)
                ))
                
                pages_to_remove.extend(
                    all_pages[self.config.max_cached_pages:]
                )
            
            # Remove pages
            for page_num in pages_to_remove:
                if page_num in self.loaded_pages:
                    del self.loaded_pages[page_num]
    
    def get_visible_items(self) -> List[ContentModel]:
        """Get items for the current visible range"""
        start_index, end_index = self.visible_range
        items = []
        
        start_page = start_index // self.config.page_size
        end_page = end_index // self.config.page_size
        
        with self._lock:
            for page_num in range(start_page, end_page + 1):
                if page_num in self.loaded_pages:
                    page_items = self.loaded_pages[page_num]
                    
                    # Calculate slice within page
                    page_start = page_num * self.config.page_size
                    page_end = page_start + len(page_items)
                    
                    # Determine overlap with visible range
                    overlap_start = max(start_index, page_start) - page_start
                    overlap_end = min(end_index + 1, page_end) - page_start
                    
                    if overlap_start < overlap_end:
                        items.extend(page_items[overlap_start:overlap_end])
        
        return items
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get virtual scrolling statistics"""
        with self._lock:
            cache_stats = self.cache.get_statistics()
            
            return {
                "total_items": self.total_items,
                "loaded_pages": len(self.loaded_pages),
                "visible_range": self.visible_range,
                "page_size": self.config.page_size,
                "avg_load_time_ms": self.metrics.avg_load_time_ms,
                "total_requests": self.metrics.total_requests,
                "items_loaded": self.metrics.items_loaded,
                "cache_stats": cache_stats
            }


class ProgressiveLoader:
    """
    Progressive loading manager for smooth user experience
    Loads data in small chunks to maintain UI responsiveness
    """
    
    def __init__(self,
                 chunk_size: int = 25,
                 delay_ms: int = 10,
                 repository: Optional[IContentRepository] = None):
        
        self.chunk_size = chunk_size
        self.delay_ms = delay_ms
        self.repository = repository
        
        # Loading state
        self.is_loading = False
        self.current_offset = 0
        self.total_loaded = 0
        self.loading_complete = False
        
        # Data storage
        self.loaded_items: List[ContentModel] = []
        self.loading_callbacks: List[Callable] = []
        
        # Performance tracking
        self.metrics = PerformanceMetrics()
        self._lock = Lock()
        
        self.logger = logging.getLogger(__name__)
    
    async def start_progressive_load(self, 
                                   total_items: Optional[int] = None,
                                   filters: Optional[Dict] = None) -> bool:
        """Start progressive loading process"""
        try:
            if self.is_loading:
                return False
            
            with self._lock:
                self.is_loading = True
                self.current_offset = 0
                self.total_loaded = 0
                self.loading_complete = False
                self.loaded_items.clear()
            
            # Start loading task
            asyncio.create_task(self._progressive_load_worker(total_items, filters))
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting progressive load: {e}")
            return False
    
    async def _progressive_load_worker(self, 
                                     total_items: Optional[int] = None,
                                     filters: Optional[Dict] = None):
        """Worker coroutine for progressive loading"""
        try:
            while self.is_loading:
                # Load next chunk
                start_time = time.time()
                
                if hasattr(self.repository, 'get_paginated'):
                    chunk = await self.repository.get_paginated(
                        offset=self.current_offset,
                        limit=self.chunk_size,
                        filters=filters
                    )
                else:
                    # Fallback: get all and slice
                    all_items = await self.repository.get_all()
                    chunk = all_items[self.current_offset:self.current_offset + self.chunk_size]
                
                load_time_ms = (time.time() - start_time) * 1000
                
                # Update metrics
                with self._lock:
                    self.metrics.avg_load_time_ms = (
                        (self.metrics.avg_load_time_ms * self.metrics.total_requests + load_time_ms) /
                        (self.metrics.total_requests + 1)
                    )
                    self.metrics.total_requests += 1
                    self.metrics.items_loaded += len(chunk)
                
                # Add to loaded items
                if chunk:
                    with self._lock:
                        self.loaded_items.extend(chunk)
                        self.current_offset += len(chunk)
                        self.total_loaded += len(chunk)
                    
                    # Notify callbacks
                    self._notify_progress(chunk)
                    
                    # Check completion
                    if (len(chunk) < self.chunk_size or 
                        (total_items and self.total_loaded >= total_items)):
                        break
                    
                    # Delay for UI responsiveness
                    await asyncio.sleep(self.delay_ms / 1000.0)
                else:
                    break
            
            # Mark as complete
            with self._lock:
                self.is_loading = False
                self.loading_complete = True
            
            self._notify_completion()
            
        except Exception as e:
            with self._lock:
                self.is_loading = False
            
            self.logger.error(f"Error in progressive loading: {e}")
            self._notify_error(e)
    
    def _notify_progress(self, chunk: List[ContentModel]):
        """Notify callbacks of loading progress"""
        for callback in self.loading_callbacks:
            try:
                callback({
                    "type": "progress",
                    "chunk": chunk,
                    "total_loaded": self.total_loaded,
                    "chunk_size": len(chunk)
                })
            except Exception as e:
                self.logger.error(f"Error in progress callback: {e}")
    
    def _notify_completion(self):
        """Notify callbacks of loading completion"""
        for callback in self.loading_callbacks:
            try:
                callback({
                    "type": "complete",
                    "total_loaded": self.total_loaded,
                    "all_items": self.loaded_items.copy()
                })
            except Exception as e:
                self.logger.error(f"Error in completion callback: {e}")
    
    def _notify_error(self, error: Exception):
        """Notify callbacks of loading error"""
        for callback in self.loading_callbacks:
            try:
                callback({
                    "type": "error",
                    "error": str(error),
                    "total_loaded": self.total_loaded
                })
            except Exception as e:
                self.logger.error(f"Error in error callback: {e}")
    
    def register_callback(self, callback: Callable):
        """Register progress callback"""
        self.loading_callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable):
        """Unregister progress callback"""
        try:
            self.loading_callbacks.remove(callback)
        except ValueError:
            pass
    
    def stop_loading(self):
        """Stop progressive loading"""
        with self._lock:
            self.is_loading = False
    
    def get_loaded_items(self) -> List[ContentModel]:
        """Get currently loaded items"""
        with self._lock:
            return self.loaded_items.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get progressive loading statistics"""
        with self._lock:
            return {
                "is_loading": self.is_loading,
                "loading_complete": self.loading_complete,
                "total_loaded": self.total_loaded,
                "current_offset": self.current_offset,
                "chunk_size": self.chunk_size,
                "avg_load_time_ms": self.metrics.avg_load_time_ms,
                "total_requests": self.metrics.total_requests
            }


class DatasetPerformanceManager:
    """
    Main performance manager coordinating all optimization strategies
    Provides unified interface for large dataset performance optimization
    """
    
    def __init__(self, repository: Optional[IContentRepository] = None):
        self.repository = repository
        
        # Core optimization components
        self.cache = IntelligentCache(
            max_size=50000,
            strategy=CacheStrategy.ADAPTIVE,
            memory_limit_mb=1024.0  # 1GB cache limit
        )
        
        self.virtual_scroll = VirtualScrollManager(
            config=PaginationConfig(
                page_size=100,
                prefetch_pages=3,
                max_cached_pages=20
            ),
            repository=repository
        )
        
        self.progressive_loader = ProgressiveLoader(
            chunk_size=50,
            delay_ms=5,
            repository=repository
        )
        
        # Integration with Task 18 components
        try:
            if PERFORMANCE_OPTIMIZATION_AVAILABLE:
                self.data_binding_manager = get_data_binding_manager()
                self.state_manager = get_repository_state_manager()
                self.async_manager = get_async_repository_manager()
            else:
                self.data_binding_manager = None
                self.state_manager = None
                self.async_manager = None
        except:
            self.data_binding_manager = None
            self.state_manager = None
            self.async_manager = None
        
        # Performance monitoring
        self.global_metrics = PerformanceMetrics()
        self._lock = RLock()
        
        # Error handling
        if PERFORMANCE_OPTIMIZATION_AVAILABLE:
            self.error_handler = ComponentErrorHandler(
                ComponentErrorConfig(
                    component_name="DatasetPerformanceManager",
                    error_category=ErrorCategory.PERFORMANCE,
                    default_severity=ErrorSeverity.HIGH
                )
            )
            self.logger = get_enhanced_logger("DatasetPerformanceManager")
        else:
            self.error_handler = None
            self.logger = logging.getLogger(__name__)
    
    async def initialize(self) -> bool:
        """Initialize performance manager"""
        try:
            # Initialize virtual scrolling
            if self.repository:
                await self.virtual_scroll.initialize()
            
            self.logger.info("Dataset performance manager initialized successfully")
            return True
            
        except Exception as e:
            if self.error_handler:
                self.error_handler.handle_error(e, operation="performance_manager_init")
            return False
    
    async def get_optimized_data(self,
                                offset: int = 0,
                                limit: int = 100,
                                filters: Optional[Dict] = None,
                                sort_key: Optional[str] = None,
                                use_cache: bool = True,
                                loading_strategy: LoadingStrategy = LoadingStrategy.VIRTUAL) -> List[ContentModel]:
        """
        Get data using optimized loading strategy
        Combines caching, virtual scrolling, and progressive loading
        """
        try:
            start_time = time.time()
            
            # Generate cache key
            cache_key = f"data_{offset}_{limit}_{hash(str(filters))}_{sort_key}"
            
            # Try cache first if enabled
            if use_cache:
                cached_data = self.cache.get(cache_key)
                if cached_data:
                    self._update_global_metrics(
                        time.time() - start_time,
                        len(cached_data),
                        cache_hit=True
                    )
                    return cached_data
            
            # Choose loading strategy
            if loading_strategy == LoadingStrategy.VIRTUAL:
                # Use virtual scrolling
                await self.virtual_scroll.set_visible_range(offset, offset + limit - 1)
                data = self.virtual_scroll.get_visible_items()
                
            elif loading_strategy == LoadingStrategy.PROGRESSIVE:
                # Use progressive loading
                if not self.progressive_loader.loading_complete:
                    await self.progressive_loader.start_progressive_load(
                        total_items=offset + limit,
                        filters=filters
                    )
                
                all_items = self.progressive_loader.get_loaded_items()
                data = all_items[offset:offset + limit]
                
            else:
                # Default: direct repository access
                if hasattr(self.repository, 'get_paginated'):
                    data = await self.repository.get_paginated(
                        offset=offset,
                        limit=limit,
                        filters=filters
                    )
                else:
                    all_items = await self.repository.get_all()
                    data = all_items[offset:offset + limit]
            
            # Cache the result
            if use_cache and data:
                self.cache.put(cache_key, data, ttl_seconds=1800)  # 30 minutes
            
            # Update metrics
            self._update_global_metrics(
                time.time() - start_time,
                len(data),
                cache_hit=False
            )
            
            return data
            
        except Exception as e:
            if self.error_handler:
                self.error_handler.handle_error(
                    e,
                    operation="get_optimized_data",
                    context={"offset": offset, "limit": limit}
                )
            return []
    
    def _update_global_metrics(self, load_time_seconds: float, items_count: int, cache_hit: bool):
        """Update global performance metrics"""
        with self._lock:
            load_time_ms = load_time_seconds * 1000
            
            self.global_metrics.avg_load_time_ms = (
                (self.global_metrics.avg_load_time_ms * self.global_metrics.total_requests + load_time_ms) /
                (self.global_metrics.total_requests + 1)
            )
            
            self.global_metrics.total_requests += 1
            self.global_metrics.items_loaded += items_count
            
            if cache_hit:
                self.global_metrics.cache_hits += 1
            else:
                self.global_metrics.cache_misses += 1
    
    async def preload_data(self, 
                          start_offset: int = 0,
                          preload_size: int = 1000,
                          strategy: LoadingStrategy = LoadingStrategy.PROGRESSIVE) -> bool:
        """Preload data for better performance"""
        try:
            if strategy == LoadingStrategy.PROGRESSIVE:
                return await self.progressive_loader.start_progressive_load(
                    total_items=start_offset + preload_size
                )
            
            elif strategy == LoadingStrategy.VIRTUAL:
                # Preload multiple pages
                pages_to_load = (preload_size // self.virtual_scroll.config.page_size) + 1
                load_tasks = []
                
                for i in range(pages_to_load):
                    page_num = (start_offset // self.virtual_scroll.config.page_size) + i
                    load_tasks.append(self.virtual_scroll.load_page(page_num))
                
                await asyncio.gather(*load_tasks, return_exceptions=True)
                return True
            
            return False
            
        except Exception as e:
            if self.error_handler:
                self.error_handler.handle_error(e, operation="preload_data")
            return False
    
    def invalidate_cache(self, pattern: Optional[str] = None):
        """Invalidate cache entries"""
        if pattern:
            # TODO: Implement pattern-based cache invalidation
            pass
        else:
            self.cache.clear()
        
        self.logger.info("Cache invalidated")
    
    def optimize_memory(self):
        """Optimize memory usage"""
        try:
            # Force garbage collection
            gc.collect()
            
            # Clean up virtual scroll cache
            self.virtual_scroll._cleanup_old_pages(0, 0)
            
            # Clear progressive loader if complete
            if self.progressive_loader.loading_complete:
                self.progressive_loader.loaded_items.clear()
            
            self.logger.info("Memory optimization completed")
            
        except Exception as e:
            self.logger.error(f"Error during memory optimization: {e}")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        try:
            cache_stats = self.cache.get_statistics()
            virtual_scroll_stats = self.virtual_scroll.get_statistics()
            progressive_stats = self.progressive_loader.get_statistics()
            
            return {
                "global_metrics": {
                    "total_requests": self.global_metrics.total_requests,
                    "cache_hit_ratio": self.global_metrics.cache_hit_ratio,
                    "avg_load_time_ms": self.global_metrics.avg_load_time_ms,
                    "items_loaded": self.global_metrics.items_loaded,
                    "efficiency_score": self.global_metrics.efficiency_score
                },
                "cache_performance": cache_stats,
                "virtual_scroll_performance": virtual_scroll_stats,
                "progressive_loading_performance": progressive_stats,
                "memory_usage": {
                    "cache_memory_mb": cache_stats.get("memory_usage_mb", 0),
                    "virtual_scroll_pages": virtual_scroll_stats.get("loaded_pages", 0),
                    "progressive_items": progressive_stats.get("total_loaded", 0)
                },
                "recommendations": self._generate_performance_recommendations()
            }
            
        except Exception as e:
            self.logger.error(f"Error generating performance report: {e}")
            return {}
    
    def _generate_performance_recommendations(self) -> List[str]:
        """Generate performance optimization recommendations"""
        recommendations = []
        
        try:
            # Cache efficiency recommendations
            hit_ratio = self.global_metrics.cache_hit_ratio
            if hit_ratio < 70:
                recommendations.append("Consider increasing cache size or TTL for better hit ratio")
            
            # Load time recommendations
            avg_load_time = self.global_metrics.avg_load_time_ms
            if avg_load_time > 1000:
                recommendations.append("Load times are high - consider smaller page sizes or better indexing")
            
            # Memory recommendations
            cache_stats = self.cache.get_statistics()
            memory_usage = cache_stats.get("memory_usage_mb", 0)
            if memory_usage > 800:  # 80% of 1GB limit
                recommendations.append("High memory usage - consider reducing cache size or enabling compression")
            
            if not recommendations:
                recommendations.append("Performance is optimal - no changes needed")
            
        except Exception as e:
            recommendations.append(f"Error generating recommendations: {e}")
        
        return recommendations


# Global instance management
_dataset_performance_manager: Optional[DatasetPerformanceManager] = None


def get_dataset_performance_manager(repository: Optional[IContentRepository] = None) -> DatasetPerformanceManager:
    """
    Get or create the global DatasetPerformanceManager instance
    
    Args:
        repository: Repository instance for data access
        
    Returns:
        DatasetPerformanceManager instance
    """
    global _dataset_performance_manager
    
    if _dataset_performance_manager is None:
        _dataset_performance_manager = DatasetPerformanceManager(repository)
    
    return _dataset_performance_manager


def reset_dataset_performance_manager():
    """Reset the global dataset performance manager (for testing)"""
    global _dataset_performance_manager
    if _dataset_performance_manager:
        _dataset_performance_manager.cache.clear()
    _dataset_performance_manager = None 