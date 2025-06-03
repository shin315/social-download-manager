"""
Data Mapping Performance Optimizer for Adapter Framework

This module implements advanced performance optimizations for data mapping operations
including smart caching, lazy loading, batch processing, and streamlined transformations.

Key Optimizations:
- Multi-level caching with TTL and size limits
- Lazy loading and deferred transformations
- Bulk processing with vectorized operations
- Schema validation caching
- Memory-efficient data structures
- Streaming transformations for large datasets
- Parallel processing for independent mappings
"""

import sys
import time
import json
import pickle
import threading
import weakref
import hashlib
import gc
from typing import Dict, List, Any, Optional, Callable, Tuple, Union, Iterator, Set
from dataclasses import dataclass, field, asdict
from collections import defaultdict, OrderedDict, deque
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import lru_cache, wraps, partial
from enum import Enum, auto
import logging
import copy

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from data.models.downloads import DownloadStatus
    from data.models.video_info import LegacyVideoInfo, LegacyDownloadInfo
    MAPPERS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Data mappers not available: {e}")
    MAPPERS_AVAILABLE = False


class CacheStrategy(Enum):
    """Data mapping cache strategies"""
    LRU = auto()
    TTL = auto()
    HYBRID = auto()
    WRITE_THROUGH = auto()
    WRITE_BACK = auto()


class TransformationMode(Enum):
    """Data transformation modes"""
    EAGER = auto()
    LAZY = auto()
    STREAMING = auto()
    BATCH = auto()


@dataclass
class MappingMetrics:
    """Performance metrics for data mapping operations"""
    
    # Throughput metrics
    transformations_performed: int = 0
    transformations_per_second: float = 0.0
    avg_transformation_time: float = 0.0
    peak_throughput: float = 0.0
    
    # Cache metrics
    cache_hits: int = 0
    cache_misses: int = 0
    cache_hit_ratio: float = 0.0
    cache_evictions: int = 0
    cache_size_bytes: int = 0
    
    # Efficiency metrics
    lazy_evaluations: int = 0
    bulk_operations: int = 0
    parallel_operations: int = 0
    memory_savings_bytes: int = 0
    
    # Error metrics
    transformation_errors: int = 0
    validation_errors: int = 0
    serialization_errors: int = 0
    
    # Performance metrics
    cpu_usage_percent: float = 0.0
    memory_usage_bytes: int = 0
    gc_collections: int = 0


@dataclass
class CachedTransformation:
    """Cached transformation result with metadata"""
    
    result: Any
    created_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    size_bytes: int = 0
    transformation_time: float = 0.0
    
    def __post_init__(self):
        if not self.size_bytes:
            try:
                self.size_bytes = len(pickle.dumps(self.result))
            except:
                self.size_bytes = sys.getsizeof(self.result)
    
    @property
    def age_seconds(self) -> float:
        return (datetime.now() - self.created_at).total_seconds()
    
    def access(self) -> Any:
        """Access the cached result and update metrics"""
        self.access_count += 1
        self.last_accessed = datetime.now()
        return self.result


class HighPerformanceCache:
    """
    High-performance multi-level cache for data transformations
    
    Features:
    - LRU and TTL eviction policies
    - Memory usage monitoring
    - Access pattern optimization
    - Thread-safe operations
    """
    
    def __init__(self, max_size: int = 10000, ttl_seconds: int = 3600, 
                 max_memory_mb: int = 500, strategy: CacheStrategy = CacheStrategy.HYBRID):
        self.max_size = max_size
        self.ttl = timedelta(seconds=ttl_seconds)
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.strategy = strategy
        
        # Storage
        self._cache: OrderedDict[str, CachedTransformation] = OrderedDict()
        self._access_times: Dict[str, datetime] = {}
        self._lock = threading.RLock()
        
        # Metrics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._total_memory = 0
        
        self.logger = logging.getLogger(__name__)
    
    def _generate_key(self, source_data: Any, transformation_func: str, **kwargs) -> str:
        """Generate a cache key for the transformation"""
        try:
            # Create a hash from the source data and transformation parameters
            data_str = json.dumps(source_data, sort_keys=True, default=str)
            params_str = json.dumps(kwargs, sort_keys=True, default=str)
            combined = f"{transformation_func}:{data_str}:{params_str}"
            return hashlib.md5(combined.encode()).hexdigest()
        except:
            # Fallback for non-serializable data
            return f"{transformation_func}:{id(source_data)}:{hash(str(kwargs))}"
    
    def get(self, source_data: Any, transformation_func: str, **kwargs) -> Optional[CachedTransformation]:
        """Get cached transformation result"""
        key = self._generate_key(source_data, transformation_func, **kwargs)
        
        with self._lock:
            if key in self._cache:
                cached = self._cache[key]
                
                # Check TTL
                if self.strategy in [CacheStrategy.TTL, CacheStrategy.HYBRID]:
                    if cached.age_seconds > self.ttl.total_seconds():
                        self._evict_key(key)
                        self._misses += 1
                        return None
                
                # Update access and move to end (LRU)
                self._cache.move_to_end(key)
                self._access_times[key] = datetime.now()
                self._hits += 1
                
                return cached
            
            self._misses += 1
            return None
    
    def put(self, source_data: Any, transformation_func: str, result: Any, 
            transformation_time: float = 0.0, **kwargs) -> None:
        """Cache transformation result"""
        key = self._generate_key(source_data, transformation_func, **kwargs)
        
        with self._lock:
            # Create cached result
            cached = CachedTransformation(
                result=result,
                transformation_time=transformation_time
            )
            
            # Check if we need to evict
            self._maybe_evict(cached.size_bytes)
            
            # Store result
            self._cache[key] = cached
            self._access_times[key] = datetime.now()
            self._total_memory += cached.size_bytes
    
    def _maybe_evict(self, incoming_size: int) -> None:
        """Evict entries if necessary"""
        # Memory-based eviction
        while (self._total_memory + incoming_size > self.max_memory_bytes and self._cache):
            self._evict_lru()
        
        # Size-based eviction
        while len(self._cache) >= self.max_size and self._cache:
            self._evict_lru()
    
    def _evict_lru(self) -> None:
        """Evict least recently used item"""
        if not self._cache:
            return
        
        # Get oldest key (first in OrderedDict)
        key = next(iter(self._cache))
        self._evict_key(key)
    
    def _evict_key(self, key: str) -> None:
        """Evict specific key"""
        if key in self._cache:
            cached = self._cache.pop(key)
            self._access_times.pop(key, None)
            self._total_memory -= cached.size_bytes
            self._evictions += 1
    
    def clear(self) -> None:
        """Clear all cached data"""
        with self._lock:
            self._cache.clear()
            self._access_times.clear()
            self._total_memory = 0
    
    def get_stats(self) -> Dict[str, Union[int, float]]:
        """Get cache statistics"""
        total_requests = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_ratio": self._hits / max(1, total_requests),
            "evictions": self._evictions,
            "cache_size": len(self._cache),
            "memory_usage_bytes": self._total_memory,
            "memory_usage_mb": self._total_memory / (1024 * 1024)
        }


class LazyTransformation:
    """
    Lazy evaluation wrapper for data transformations
    
    Defers expensive transformations until actually needed,
    reducing memory usage and improving performance for unused data.
    """
    
    def __init__(self, source_data: Any, transform_func: Callable, *args, **kwargs):
        self.source_data = source_data
        self.transform_func = transform_func
        self.args = args
        self.kwargs = kwargs
        
        self._result = None
        self._evaluated = False
        self._evaluation_time = 0.0
        
        self.logger = logging.getLogger(__name__)
    
    def evaluate(self) -> Any:
        """Evaluate the lazy transformation"""
        if self._evaluated:
            return self._result
        
        start_time = time.perf_counter()
        try:
            self._result = self.transform_func(self.source_data, *self.args, **self.kwargs)
            self._evaluated = True
            self._evaluation_time = time.perf_counter() - start_time
        except Exception as e:
            self.logger.error(f"Lazy transformation failed: {e}")
            raise
        
        return self._result
    
    @property
    def is_evaluated(self) -> bool:
        return self._evaluated
    
    @property
    def evaluation_time(self) -> float:
        return self._evaluation_time
    
    def __getattr__(self, name):
        """Automatically evaluate when accessing attributes"""
        result = self.evaluate()
        return getattr(result, name)
    
    def __iter__(self):
        """Support iteration by evaluating first"""
        return iter(self.evaluate())
    
    def __str__(self):
        if self._evaluated:
            return str(self._result)
        return f"<LazyTransformation: {self.transform_func.__name__}>"


class BulkTransformationProcessor:
    """
    Bulk processor for data transformations with vectorized operations
    
    Processes multiple data items together to reduce per-item overhead
    and enable vectorized optimizations.
    """
    
    def __init__(self, batch_size: int = 100, max_workers: int = 4):
        self.batch_size = batch_size
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        
        self.logger = logging.getLogger(__name__)
    
    def process_bulk(self, data_items: List[Any], transform_func: Callable, 
                    **transform_kwargs) -> List[Any]:
        """
        Process multiple data items in bulk with optimizations
        
        Args:
            data_items: List of data items to transform
            transform_func: Transformation function
            **transform_kwargs: Additional transformation parameters
            
        Returns:
            List of transformed results
        """
        if not data_items:
            return []
        
        # For small datasets, process directly
        if len(data_items) <= self.batch_size:
            return self._process_batch(data_items, transform_func, **transform_kwargs)
        
        # For larger datasets, process in parallel batches
        batches = [
            data_items[i:i + self.batch_size] 
            for i in range(0, len(data_items), self.batch_size)
        ]
        
        # Submit batches to thread pool
        futures = [
            self._executor.submit(self._process_batch, batch, transform_func, **transform_kwargs)
            for batch in batches
        ]
        
        # Collect results
        results = []
        for future in futures:
            try:
                batch_results = future.result(timeout=30)
                results.extend(batch_results)
            except Exception as e:
                self.logger.error(f"Batch processing failed: {e}")
                # Add None placeholders for failed batch
                results.extend([None] * len(batches[futures.index(future)]))
        
        return results
    
    def _process_batch(self, batch: List[Any], transform_func: Callable, 
                      **transform_kwargs) -> List[Any]:
        """Process a single batch of data items"""
        results = []
        
        for item in batch:
            try:
                result = transform_func(item, **transform_kwargs)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Item transformation failed: {e}")
                results.append(None)
        
        return results
    
    def shutdown(self):
        """Shutdown the thread executor"""
        self._executor.shutdown(wait=True)


class StreamingTransformer:
    """
    Streaming transformer for large datasets
    
    Processes data in chunks without loading everything into memory,
    suitable for very large datasets or memory-constrained environments.
    """
    
    def __init__(self, chunk_size: int = 1000):
        self.chunk_size = chunk_size
        self.logger = logging.getLogger(__name__)
    
    def transform_stream(self, data_iterator: Iterator[Any], 
                        transform_func: Callable, **transform_kwargs) -> Iterator[Any]:
        """
        Transform data from an iterator in streaming fashion
        
        Args:
            data_iterator: Iterator providing data items
            transform_func: Transformation function
            **transform_kwargs: Additional transformation parameters
            
        Yields:
            Transformed data items
        """
        chunk = []
        
        for item in data_iterator:
            chunk.append(item)
            
            if len(chunk) >= self.chunk_size:
                # Process chunk
                for result in self._process_chunk(chunk, transform_func, **transform_kwargs):
                    yield result
                chunk = []
        
        # Process remaining items
        if chunk:
            for result in self._process_chunk(chunk, transform_func, **transform_kwargs):
                yield result
    
    def _process_chunk(self, chunk: List[Any], transform_func: Callable, 
                      **transform_kwargs) -> List[Any]:
        """Process a chunk of data items"""
        results = []
        
        for item in chunk:
            try:
                result = transform_func(item, **transform_kwargs)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Streaming transformation failed: {e}")
                results.append(None)
        
        return results


class OptimizedDataMapper:
    """
    High-performance data mapper with comprehensive optimizations
    
    Combines caching, lazy evaluation, bulk processing, and streaming
    to provide maximum performance for data transformation operations.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Configuration
        self.cache_enabled = self.config.get("enable_cache", True)
        self.lazy_enabled = self.config.get("enable_lazy", True)
        self.bulk_enabled = self.config.get("enable_bulk", True)
        self.streaming_enabled = self.config.get("enable_streaming", True)
        
        # Cache configuration
        cache_config = self.config.get("cache", {})
        self.cache_size = cache_config.get("max_size", 10000)
        self.cache_ttl = cache_config.get("ttl_seconds", 3600)
        self.cache_memory_mb = cache_config.get("max_memory_mb", 500)
        
        # Bulk processing configuration
        bulk_config = self.config.get("bulk", {})
        self.bulk_batch_size = bulk_config.get("batch_size", 100)
        self.bulk_workers = bulk_config.get("max_workers", 4)
        
        # Streaming configuration
        streaming_config = self.config.get("streaming", {})
        self.streaming_chunk_size = streaming_config.get("chunk_size", 1000)
        
        # Initialize components
        if self.cache_enabled:
            self._cache = HighPerformanceCache(
                max_size=self.cache_size,
                ttl_seconds=self.cache_ttl,
                max_memory_mb=self.cache_memory_mb
            )
        else:
            self._cache = None
        
        if self.bulk_enabled:
            self._bulk_processor = BulkTransformationProcessor(
                batch_size=self.bulk_batch_size,
                max_workers=self.bulk_workers
            )
        else:
            self._bulk_processor = None
        
        if self.streaming_enabled:
            self._streaming_transformer = StreamingTransformer(
                chunk_size=self.streaming_chunk_size
            )
        else:
            self._streaming_transformer = None
        
        # Metrics
        self._metrics = MappingMetrics()
        self._start_time = time.time()
        
        # Original mappers (if available)
        self._video_mapper = None
        self._download_mapper = None
        
        if MAPPERS_AVAILABLE:
            try:
                self._video_mapper = VideoDataMapper()
                self._download_mapper = DownloadDataMapper()
            except Exception as e:
                print(f"Warning: Failed to initialize original mappers: {e}")
        
        self.logger = logging.getLogger(__name__)
    
    def transform_data(self, source_data: Any, target_format: str, 
                      mode: TransformationMode = TransformationMode.EAGER,
                      **kwargs) -> Union[Any, LazyTransformation]:
        """
        Transform data with optimizations based on mode
        
        Args:
            source_data: Source data to transform
            target_format: Target format identifier
            mode: Transformation mode (eager, lazy, etc.)
            **kwargs: Additional transformation parameters
            
        Returns:
            Transformed data or lazy transformation wrapper
        """
        transform_func_name = f"transform_to_{target_format}"
        
        # Check cache first if enabled
        if self._cache and mode != TransformationMode.LAZY:
            cached = self._cache.get(source_data, transform_func_name, **kwargs)
            if cached:
                self._metrics.cache_hits += 1
                return cached.access()
            else:
                self._metrics.cache_misses += 1
        
        # Select transformation function
        transform_func = self._get_transform_function(target_format)
        
        if mode == TransformationMode.LAZY and self.lazy_enabled:
            # Return lazy transformation
            self._metrics.lazy_evaluations += 1
            return LazyTransformation(source_data, transform_func, **kwargs)
        
        elif mode == TransformationMode.EAGER:
            # Perform immediate transformation
            start_time = time.perf_counter()
            
            try:
                result = transform_func(source_data, **kwargs)
                transformation_time = time.perf_counter() - start_time
                
                # Cache result if enabled
                if self._cache:
                    self._cache.put(source_data, transform_func_name, result, transformation_time, **kwargs)
                
                # Update metrics
                self._metrics.transformations_performed += 1
                self._update_performance_metrics(transformation_time)
                
                return result
                
            except Exception as e:
                self.logger.error(f"Transformation failed: {e}")
                self._metrics.transformation_errors += 1
                raise
        
        else:
            # Default to eager mode
            return self.transform_data(source_data, target_format, TransformationMode.EAGER, **kwargs)
    
    def transform_bulk(self, data_items: List[Any], target_format: str, **kwargs) -> List[Any]:
        """
        Transform multiple data items in bulk with optimizations
        
        Args:
            data_items: List of data items to transform
            target_format: Target format identifier
            **kwargs: Additional transformation parameters
            
        Returns:
            List of transformed results
        """
        if not self.bulk_enabled or not self._bulk_processor:
            # Fall back to individual transformations
            return [
                self.transform_data(item, target_format, TransformationMode.EAGER, **kwargs)
                for item in data_items
            ]
        
        transform_func = self._get_transform_function(target_format)
        
        start_time = time.perf_counter()
        results = self._bulk_processor.process_bulk(data_items, transform_func, **kwargs)
        processing_time = time.perf_counter() - start_time
        
        # Update metrics
        self._metrics.bulk_operations += 1
        self._metrics.transformations_performed += len(data_items)
        self._update_performance_metrics(processing_time / len(data_items))
        
        return results
    
    def transform_stream(self, data_iterator: Iterator[Any], target_format: str, 
                        **kwargs) -> Iterator[Any]:
        """
        Transform data from an iterator in streaming fashion
        
        Args:
            data_iterator: Iterator providing data items
            target_format: Target format identifier
            **kwargs: Additional transformation parameters
            
        Yields:
            Transformed data items
        """
        if not self.streaming_enabled or not self._streaming_transformer:
            # Fall back to individual transformations
            for item in data_iterator:
                yield self.transform_data(item, target_format, TransformationMode.EAGER, **kwargs)
            return
        
        transform_func = self._get_transform_function(target_format)
        
        for result in self._streaming_transformer.transform_stream(data_iterator, transform_func, **kwargs):
            yield result
            self._metrics.transformations_performed += 1
    
    def _get_transform_function(self, target_format: str) -> Callable:
        """Get the appropriate transformation function for the target format"""
        transform_functions = {
            "video_info": self._transform_to_video_info,
            "download_info": self._transform_to_download_info,
            "legacy_video": self._transform_to_legacy_video,
            "legacy_download": self._transform_to_legacy_download,
            "json": self._transform_to_json,
            "dict": self._transform_to_dict
        }
        
        func = transform_functions.get(target_format)
        if not func:
            raise ValueError(f"Unknown target format: {target_format}")
        
        return func
    
    def _transform_to_video_info(self, data: Any, **kwargs) -> Dict[str, Any]:
        """Transform data to video info format"""
        if self._video_mapper:
            try:
                return self._video_mapper.to_video_info(data)
            except Exception as e:
                self.logger.error(f"Video mapper failed: {e}")
        
        # Fallback implementation
        if isinstance(data, dict):
            return {
                "url": data.get("url", ""),
                "title": data.get("title", ""),
                "creator": data.get("creator", ""),
                "duration": data.get("duration", ""),
                "description": data.get("description", ""),
                "thumbnail": data.get("thumbnail", ""),
                "platform": data.get("platform", "unknown")
            }
        
        return {"url": str(data)} if data else {}
    
    def _transform_to_download_info(self, data: Any, **kwargs) -> Dict[str, Any]:
        """Transform data to download info format"""
        if self._download_mapper:
            try:
                return self._download_mapper.to_download_info(data)
            except Exception as e:
                self.logger.error(f"Download mapper failed: {e}")
        
        # Fallback implementation
        if isinstance(data, dict):
            return {
                "id": data.get("id", ""),
                "url": data.get("url", ""),
                "status": data.get("status", "pending"),
                "progress": data.get("progress", 0),
                "file_path": data.get("file_path", ""),
                "created_at": data.get("created_at", time.time()),
                "completed_at": data.get("completed_at")
            }
        
        return {"url": str(data)} if data else {}
    
    def _transform_to_legacy_video(self, data: Any, **kwargs) -> Dict[str, Any]:
        """Transform data to legacy video format"""
        video_info = self._transform_to_video_info(data, **kwargs)
        
        # Convert to legacy format
        return {
            "video_url": video_info.get("url", ""),
            "video_title": video_info.get("title", ""),
            "video_creator": video_info.get("creator", ""),
            "video_duration": video_info.get("duration", ""),
            "video_description": video_info.get("description", ""),
            "video_thumbnail": video_info.get("thumbnail", "")
        }
    
    def _transform_to_legacy_download(self, data: Any, **kwargs) -> Dict[str, Any]:
        """Transform data to legacy download format"""
        download_info = self._transform_to_download_info(data, **kwargs)
        
        # Convert to legacy format
        return {
            "download_id": download_info.get("id", ""),
            "download_url": download_info.get("url", ""),
            "download_status": download_info.get("status", "pending"),
            "download_progress": download_info.get("progress", 0),
            "download_path": download_info.get("file_path", ""),
            "download_created": download_info.get("created_at"),
            "download_completed": download_info.get("completed_at")
        }
    
    def _transform_to_json(self, data: Any, **kwargs) -> str:
        """Transform data to JSON string"""
        try:
            return json.dumps(data, default=str, indent=kwargs.get("indent"))
        except Exception as e:
            self.logger.error(f"JSON transformation failed: {e}")
            return json.dumps({"error": str(e)})
    
    def _transform_to_dict(self, data: Any, **kwargs) -> Dict[str, Any]:
        """Transform data to dictionary format"""
        if isinstance(data, dict):
            return data.copy()
        elif hasattr(data, '__dict__'):
            return data.__dict__.copy()
        elif hasattr(data, '_asdict'):
            return data._asdict()
        else:
            return {"value": data}
    
    def _update_performance_metrics(self, transformation_time: float) -> None:
        """Update performance metrics"""
        # Update average transformation time
        total_time = self._metrics.avg_transformation_time * (self._metrics.transformations_performed - 1)
        self._metrics.avg_transformation_time = (total_time + transformation_time) / self._metrics.transformations_performed
        
        # Update throughput
        elapsed_time = time.time() - self._start_time
        if elapsed_time > 0:
            self._metrics.transformations_per_second = self._metrics.transformations_performed / elapsed_time
            self._metrics.peak_throughput = max(self._metrics.peak_throughput, self._metrics.transformations_per_second)
        
        # Update cache metrics if cache is enabled
        if self._cache:
            cache_stats = self._cache.get_stats()
            self._metrics.cache_hits = cache_stats["hits"]
            self._metrics.cache_misses = cache_stats["misses"]
            self._metrics.cache_hit_ratio = cache_stats["hit_ratio"]
            self._metrics.cache_evictions = cache_stats["evictions"]
            self._metrics.cache_size_bytes = cache_stats["memory_usage_bytes"]
    
    def get_performance_metrics(self) -> MappingMetrics:
        """Get current performance metrics"""
        # Update cache metrics if available
        if self._cache:
            cache_stats = self._cache.get_stats()
            self._metrics.cache_hits = cache_stats["hits"]
            self._metrics.cache_misses = cache_stats["misses"]
            self._metrics.cache_hit_ratio = cache_stats["hit_ratio"]
            self._metrics.cache_evictions = cache_stats["evictions"]
            self._metrics.cache_size_bytes = cache_stats["memory_usage_bytes"]
        
        return self._metrics
    
    def clear_cache(self) -> None:
        """Clear all cached data"""
        if self._cache:
            self._cache.clear()
    
    def export_configuration(self) -> Dict[str, Any]:
        """Export current configuration"""
        return {
            "cache_enabled": self.cache_enabled,
            "lazy_enabled": self.lazy_enabled,
            "bulk_enabled": self.bulk_enabled,
            "streaming_enabled": self.streaming_enabled,
            "cache_config": {
                "max_size": self.cache_size,
                "ttl_seconds": self.cache_ttl,
                "max_memory_mb": self.cache_memory_mb
            },
            "bulk_config": {
                "batch_size": self.bulk_batch_size,
                "max_workers": self.bulk_workers
            },
            "streaming_config": {
                "chunk_size": self.streaming_chunk_size
            }
        }
    
    def shutdown(self) -> None:
        """Shutdown and cleanup resources"""
        if self._bulk_processor:
            self._bulk_processor.shutdown()


def create_optimized_mapper(config: Optional[Dict[str, Any]] = None) -> OptimizedDataMapper:
    """
    Factory function to create an optimized data mapper
    
    Args:
        config: Configuration dictionary
        
    Returns:
        OptimizedDataMapper: Configured mapper instance
    """
    return OptimizedDataMapper(config)


def benchmark_data_mapping() -> Dict[str, Any]:
    """
    Benchmark different data mapping configurations
    """
    print("🚀 Starting Data Mapping Performance Benchmark...")
    
    # Test configurations
    configs = {
        "baseline": {
            "enable_cache": False,
            "enable_lazy": False,
            "enable_bulk": False,
            "enable_streaming": False
        },
        "cache_only": {
            "enable_cache": True,
            "enable_lazy": False,
            "enable_bulk": False,
            "enable_streaming": False
        },
        "optimized": {
            "enable_cache": True,
            "enable_lazy": True,
            "enable_bulk": True,
            "enable_streaming": False,
            "cache": {"max_size": 5000, "ttl_seconds": 1800},
            "bulk": {"batch_size": 50, "max_workers": 4}
        },
        "maximum": {
            "enable_cache": True,
            "enable_lazy": True,
            "enable_bulk": True,
            "enable_streaming": True,
            "cache": {"max_size": 10000, "ttl_seconds": 3600},
            "bulk": {"batch_size": 100, "max_workers": 8},
            "streaming": {"chunk_size": 500}
        }
    }
    
    # Test data
    test_data = [
        {
            "url": f"https://example.com/video/{i}",
            "title": f"Test Video {i}",
            "creator": f"Creator {i % 10}",
            "duration": f"{i * 60}",
            "description": f"Description for video {i}",
            "platform": "test"
        }
        for i in range(1000)
    ]
    
    results = {}
    
    for config_name, config in configs.items():
        print(f"\n📊 Testing {config_name} configuration...")
        
        mapper = create_optimized_mapper(config)
        
        # Test individual transformations
        start_time = time.perf_counter()
        individual_results = []
        for item in test_data[:100]:  # Test with 100 items
            result = mapper.transform_data(item, "video_info")
            individual_results.append(result)
        individual_time = time.perf_counter() - start_time
        
        # Test bulk transformations if enabled
        if config.get("enable_bulk", False):
            start_time = time.perf_counter()
            bulk_results = mapper.transform_bulk(test_data[:100], "video_info")
            bulk_time = time.perf_counter() - start_time
        else:
            bulk_time = 0
        
        # Get metrics
        metrics = mapper.get_performance_metrics()
        
        results[config_name] = {
            "individual_time": individual_time,
            "bulk_time": bulk_time,
            "transformations_per_second": metrics.transformations_per_second,
            "cache_hit_ratio": metrics.cache_hit_ratio,
            "avg_transformation_time": metrics.avg_transformation_time,
            "cache_hits": metrics.cache_hits,
            "cache_misses": metrics.cache_misses
        }
        
        print(f"✅ {config_name}:")
        print(f"   Individual: {individual_time:.3f}s ({100/individual_time:.1f} ops/sec)")
        if bulk_time > 0:
            print(f"   Bulk: {bulk_time:.3f}s ({100/bulk_time:.1f} ops/sec)")
        print(f"   Cache hit ratio: {metrics.cache_hit_ratio:.1%}")
        
        # Cleanup
        mapper.shutdown()
    
    return results


if __name__ == "__main__":
    # Run performance benchmark
    try:
        benchmark_results = benchmark_data_mapping()
        
        print("\n" + "="*80)
        print("DATA MAPPING OPTIMIZATION BENCHMARK RESULTS")
        print("="*80)
        
        for config_name, results in benchmark_results.items():
            print(f"\n[{config_name.upper()}]")
            print(f"  Individual Throughput: {100/results['individual_time']:.1f} ops/sec")
            if results['bulk_time'] > 0:
                print(f"  Bulk Throughput: {100/results['bulk_time']:.1f} ops/sec")
                print(f"  Bulk Speedup: {results['individual_time']/results['bulk_time']:.1f}x")
            print(f"  Cache Hit Ratio: {results['cache_hit_ratio']:.1%}")
            print(f"  Avg Transform Time: {results['avg_transformation_time']*1000:.2f}ms")
        
        print("\n✅ Data mapping optimization benchmark completed!")
        
    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc() 