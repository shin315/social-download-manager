"""
Performance Optimizations for Social Download Manager v2.0

Provides caching, query optimization, connection pooling, batch operations,
and performance monitoring for repository operations.
"""

import logging
import hashlib
import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict, OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable, TypeVar, Generic, Type, Tuple, Set
from functools import wraps
from enum import Enum

from .base import BaseEntity, EntityId
from .repositories import IRepository, QueryBuilder

T = TypeVar('T', bound=BaseEntity)


class CacheStrategy(Enum):
    """Cache strategies for different entity types"""
    LRU = "lru"
    TTL = "ttl"
    LFU = "lfu"
    WRITE_THROUGH = "write_through"
    WRITE_BACK = "write_back"


class PerformanceMetricType(Enum):
    """Types of performance metrics to track"""
    QUERY_TIME = "query_time"
    CACHE_HIT_RATE = "cache_hit_rate"
    CONNECTION_USAGE = "connection_usage"
    BATCH_SIZE = "batch_size"
    MEMORY_USAGE = "memory_usage"


@dataclass
class PerformanceMetric:
    """Performance metric data"""
    metric_type: PerformanceMetricType
    value: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    operation: str = ""
    entity_type: str = ""
    additional_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryPerformanceInfo:
    """Query performance information"""
    query: str
    execution_time: float
    result_count: int
    cache_hit: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    parameters: List[Any] = field(default_factory=list)


class ICacheProvider(ABC):
    """Interface for cache providers"""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all cache entries"""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        pass


class LRUCache(ICacheProvider):
    """LRU (Least Recently Used) cache implementation"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: OrderedDict = OrderedDict()
        self.hits = 0
        self.misses = 0
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self.cache:
                # Move to end (most recently used)
                value = self.cache.pop(key)
                self.cache[key] = value
                self.hits += 1
                return value
            else:
                self.misses += 1
                return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        with self._lock:
            if key in self.cache:
                # Update existing
                self.cache.pop(key)
            elif len(self.cache) >= self.max_size:
                # Remove oldest item
                self.cache.popitem(last=False)
            
            self.cache[key] = value
    
    def delete(self, key: str) -> bool:
        with self._lock:
            return self.cache.pop(key, None) is not None
    
    def clear(self) -> None:
        with self._lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0
            
            return {
                "cache_type": "LRU",
                "size": len(self.cache),
                "max_size": self.max_size,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": hit_rate,
                "utilization": (len(self.cache) / self.max_size * 100)
            }


class TTLCache(ICacheProvider):
    """TTL (Time To Live) cache implementation"""
    
    def __init__(self, default_ttl: int = 3600):  # 1 hour default
        self.default_ttl = default_ttl
        self.cache: Dict[str, Tuple[Any, datetime]] = {}
        self.hits = 0
        self.misses = 0
        self._lock = threading.RLock()
    
    def _is_expired(self, expiry_time: datetime) -> bool:
        return datetime.now(timezone.utc) > expiry_time
    
    def _cleanup_expired(self) -> None:
        """Remove expired entries"""
        current_time = datetime.now(timezone.utc)
        expired_keys = [
            key for key, (_, expiry) in self.cache.items()
            if current_time > expiry
        ]
        for key in expired_keys:
            del self.cache[key]
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self.cache:
                value, expiry_time = self.cache[key]
                if not self._is_expired(expiry_time):
                    self.hits += 1
                    return value
                else:
                    del self.cache[key]
            
            self.misses += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        with self._lock:
            ttl = ttl or self.default_ttl
            expiry_time = datetime.now(timezone.utc) + timedelta(seconds=ttl)
            self.cache[key] = (value, expiry_time)
            
            # Periodically cleanup expired entries
            if len(self.cache) % 100 == 0:
                self._cleanup_expired()
    
    def delete(self, key: str) -> bool:
        with self._lock:
            return self.cache.pop(key, None) is not None
    
    def clear(self) -> None:
        with self._lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            self._cleanup_expired()
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0
            
            return {
                "cache_type": "TTL",
                "size": len(self.cache),
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": hit_rate,
                "default_ttl": self.default_ttl
            }


class RepositoryCache:
    """Repository-specific caching layer"""
    
    def __init__(self, cache_provider: ICacheProvider):
        self.cache_provider = cache_provider
        self._logger = logging.getLogger("RepositoryCache")
    
    def _make_key(self, operation: str, entity_type: str, *args) -> str:
        """Generate cache key for operation"""
        key_parts = [operation, entity_type] + [str(arg) for arg in args]
        key_string = ":".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get_entity(self, entity_type: str, entity_id: EntityId) -> Optional[BaseEntity]:
        """Get entity from cache"""
        key = self._make_key("entity", entity_type, entity_id)
        return self.cache_provider.get(key)
    
    def set_entity(self, entity: BaseEntity, ttl: Optional[int] = None) -> None:
        """Set entity in cache"""
        key = self._make_key("entity", entity.__class__.__name__, entity.id)
        self.cache_provider.set(key, entity, ttl)
    
    def get_query_result(self, query: str, params: List[Any]) -> Optional[List[BaseEntity]]:
        """Get query result from cache"""
        key = self._make_key("query", query, *params)
        return self.cache_provider.get(key)
    
    def set_query_result(self, query: str, params: List[Any], 
                        result: List[BaseEntity], ttl: Optional[int] = None) -> None:
        """Set query result in cache"""
        key = self._make_key("query", query, *params)
        self.cache_provider.set(key, result, ttl)
    
    def invalidate_entity(self, entity_type: str, entity_id: EntityId) -> None:
        """Invalidate entity cache"""
        key = self._make_key("entity", entity_type, entity_id)
        self.cache_provider.delete(key)
    
    def invalidate_entity_queries(self, entity_type: str) -> None:
        """Invalidate all queries for entity type"""
        # Note: This is a simplified approach. In production, you'd want 
        # more sophisticated cache invalidation strategies
        self._logger.info(f"Invalidating caches for entity type: {entity_type}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.cache_provider.get_stats()


class BatchOperationManager:
    """Manages batch operations for improved performance"""
    
    def __init__(self, default_batch_size: int = 100):
        self.default_batch_size = default_batch_size
        self._batch_operations: Dict[str, List[Any]] = defaultdict(list)
        self._logger = logging.getLogger("BatchOperationManager")
    
    def add_operation(self, operation_type: str, operation_data: Any) -> None:
        """Add operation to batch"""
        self._batch_operations[operation_type].append(operation_data)
    
    def execute_batch(self, operation_type: str, 
                     executor_func: Callable[[List[Any]], Any],
                     batch_size: Optional[int] = None) -> List[Any]:
        """Execute batch operations"""
        batch_size = batch_size or self.default_batch_size
        operations = self._batch_operations.get(operation_type, [])
        
        if not operations:
            return []
        
        results = []
        for i in range(0, len(operations), batch_size):
            batch = operations[i:i + batch_size]
            try:
                batch_result = executor_func(batch)
                results.extend(batch_result if isinstance(batch_result, list) else [batch_result])
            except Exception as e:
                self._logger.error(f"Batch operation failed for {operation_type}: {e}")
                # Optionally retry individual operations
                for operation in batch:
                    try:
                        result = executor_func([operation])
                        results.extend(result if isinstance(result, list) else [result])
                    except Exception as individual_error:
                        self._logger.error(f"Individual operation failed: {individual_error}")
        
        # Clear processed operations
        self._batch_operations[operation_type] = []
        return results
    
    def get_pending_count(self, operation_type: str) -> int:
        """Get count of pending operations"""
        return len(self._batch_operations.get(operation_type, []))
    
    def clear_pending(self, operation_type: str) -> None:
        """Clear pending operations"""
        self._batch_operations[operation_type] = []


class QueryOptimizer:
    """Optimizes database queries for better performance"""
    
    def __init__(self):
        self._query_stats: Dict[str, List[QueryPerformanceInfo]] = defaultdict(list)
        self._slow_query_threshold = 1.0  # 1 second
        self._logger = logging.getLogger("QueryOptimizer")
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze query for optimization opportunities"""
        analysis = {
            "has_index_hints": "INDEXED BY" in query.upper(),
            "has_joins": any(join_type in query.upper() for join_type in ["JOIN", "LEFT JOIN", "INNER JOIN"]),
            "has_subqueries": "(" in query and "SELECT" in query.upper(),
            "has_order_by": "ORDER BY" in query.upper(),
            "has_limit": "LIMIT" in query.upper(),
            "has_group_by": "GROUP BY" in query.upper(),
            "estimated_complexity": self._estimate_complexity(query)
        }
        
        recommendations = []
        
        # Basic optimization recommendations
        if not analysis["has_limit"] and not analysis["has_group_by"]:
            recommendations.append("Consider adding LIMIT clause to prevent large result sets")
        
        if analysis["has_joins"] and not analysis["has_index_hints"]:
            recommendations.append("Consider adding index hints for join operations")
        
        if analysis["estimated_complexity"] > 5:
            recommendations.append("Query appears complex, consider breaking into smaller queries")
        
        analysis["recommendations"] = recommendations
        return analysis
    
    def _estimate_complexity(self, query: str) -> int:
        """Estimate query complexity score (1-10)"""
        complexity = 1
        query_upper = query.upper()
        
        # Count complexity factors
        complexity += query_upper.count("JOIN")
        complexity += query_upper.count("SUBQUERY") * 2
        complexity += query_upper.count("UNION") * 2
        complexity += query_upper.count("GROUP BY")
        complexity += query_upper.count("HAVING")
        complexity += query_upper.count("ORDER BY")
        
        return min(complexity, 10)
    
    def record_query_performance(self, query_info: QueryPerformanceInfo) -> None:
        """Record query performance information"""
        query_hash = hashlib.md5(query_info.query.encode()).hexdigest()
        self._query_stats[query_hash].append(query_info)
        
        # Log slow queries
        if query_info.execution_time > self._slow_query_threshold:
            self._logger.warning(
                f"Slow query detected: {query_info.execution_time:.3f}s - {query_info.query[:100]}..."
            )
    
    def get_slow_queries(self, threshold: Optional[float] = None) -> List[QueryPerformanceInfo]:
        """Get slow queries above threshold"""
        threshold = threshold or self._slow_query_threshold
        slow_queries = []
        
        for query_list in self._query_stats.values():
            for query_info in query_list:
                if query_info.execution_time > threshold:
                    slow_queries.append(query_info)
        
        return sorted(slow_queries, key=lambda x: x.execution_time, reverse=True)
    
    def get_query_statistics(self) -> Dict[str, Any]:
        """Get comprehensive query statistics"""
        all_queries = []
        for query_list in self._query_stats.values():
            all_queries.extend(query_list)
        
        if not all_queries:
            return {"total_queries": 0}
        
        execution_times = [q.execution_time for q in all_queries]
        cache_hits = sum(1 for q in all_queries if q.cache_hit)
        
        return {
            "total_queries": len(all_queries),
            "cache_hit_rate": (cache_hits / len(all_queries) * 100),
            "avg_execution_time": sum(execution_times) / len(execution_times),
            "max_execution_time": max(execution_times),
            "min_execution_time": min(execution_times),
            "slow_queries_count": len([t for t in execution_times if t > self._slow_query_threshold])
        }


class PerformanceMonitor:
    """Monitors and tracks repository performance metrics"""
    
    def __init__(self):
        self._metrics: List[PerformanceMetric] = []
        self._operation_timers: Dict[str, float] = {}
        self._logger = logging.getLogger("PerformanceMonitor")
    
    @contextmanager
    def measure_operation(self, operation: str, entity_type: str = ""):
        """Context manager to measure operation performance"""
        start_time = time.time()
        try:
            yield
        finally:
            execution_time = time.time() - start_time
            self.record_metric(
                PerformanceMetricType.QUERY_TIME,
                execution_time,
                operation,
                entity_type
            )
    
    def record_metric(self, metric_type: PerformanceMetricType, value: float,
                     operation: str = "", entity_type: str = "",
                     additional_data: Optional[Dict[str, Any]] = None) -> None:
        """Record a performance metric"""
        metric = PerformanceMetric(
            metric_type=metric_type,
            value=value,
            operation=operation,
            entity_type=entity_type,
            additional_data=additional_data or {}
        )
        self._metrics.append(metric)
        
        # Log significant metrics
        if metric_type == PerformanceMetricType.QUERY_TIME and value > 1.0:
            self._logger.warning(f"Slow operation '{operation}': {value:.3f}s")
    
    def get_metrics_summary(self, 
                           metric_type: Optional[PerformanceMetricType] = None,
                           operation: Optional[str] = None,
                           hours: int = 24) -> Dict[str, Any]:
        """Get summary of performance metrics"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # Filter metrics
        filtered_metrics = [
            m for m in self._metrics
            if m.timestamp > cutoff_time
            and (metric_type is None or m.metric_type == metric_type)
            and (operation is None or m.operation == operation)
        ]
        
        if not filtered_metrics:
            return {"message": "No metrics found for the specified criteria"}
        
        values = [m.value for m in filtered_metrics]
        
        return {
            "metric_type": metric_type.value if metric_type else "all",
            "operation": operation or "all",
            "time_range_hours": hours,
            "count": len(filtered_metrics),
            "avg_value": sum(values) / len(values),
            "max_value": max(values),
            "min_value": min(values),
            "total_value": sum(values)
        }
    
    def clear_old_metrics(self, hours: int = 168) -> int:  # 1 week default
        """Clear metrics older than specified hours"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        initial_count = len(self._metrics)
        
        self._metrics = [m for m in self._metrics if m.timestamp > cutoff_time]
        
        removed_count = initial_count - len(self._metrics)
        if removed_count > 0:
            self._logger.info(f"Cleaned up {removed_count} old metrics")
        
        return removed_count


class PerformanceOptimizedRepository(Generic[T]):
    """Repository mixin providing performance optimizations"""
    
    def __init__(self, base_repository: IRepository[T],
                 cache_provider: Optional[ICacheProvider] = None,
                 enable_query_optimization: bool = True,
                 enable_batch_operations: bool = True):
        self.base_repository = base_repository
        self.cache = RepositoryCache(cache_provider or LRUCache()) if cache_provider else None
        self.batch_manager = BatchOperationManager() if enable_batch_operations else None
        self.query_optimizer = QueryOptimizer() if enable_query_optimization else None
        self.performance_monitor = PerformanceMonitor()
        self._logger = logging.getLogger("PerformanceOptimizedRepository")
    
    def find_by_id_cached(self, entity_id: EntityId, ttl: Optional[int] = 3600) -> Optional[T]:
        """Find entity by ID with caching"""
        if not self.cache:
            return self.base_repository.find_by_id(entity_id)
        
        # Try cache first
        entity_type = getattr(self.base_repository, '_entity_class', T).__name__
        cached_entity = self.cache.get_entity(entity_type, entity_id)
        
        if cached_entity:
            self.performance_monitor.record_metric(
                PerformanceMetricType.CACHE_HIT_RATE, 1.0, "find_by_id", entity_type
            )
            return cached_entity
        
        # Cache miss - fetch from database
        with self.performance_monitor.measure_operation("find_by_id_db", entity_type):
            entity = self.base_repository.find_by_id(entity_id)
        
        if entity:
            self.cache.set_entity(entity, ttl)
        
        self.performance_monitor.record_metric(
            PerformanceMetricType.CACHE_HIT_RATE, 0.0, "find_by_id", entity_type
        )
        
        return entity
    
    def save_with_cache_invalidation(self, entity: T) -> Optional[T]:
        """Save entity and invalidate related cache entries"""
        entity_type = entity.__class__.__name__
        
        with self.performance_monitor.measure_operation("save", entity_type):
            result = self.base_repository.save(entity)
        
        if result and self.cache:
            # Invalidate entity cache
            self.cache.invalidate_entity(entity_type, entity.id)
            # Invalidate related query caches
            self.cache.invalidate_entity_queries(entity_type)
        
        return result
    
    def bulk_save(self, entities: List[T], batch_size: int = 100) -> List[T]:
        """Bulk save entities with batching"""
        if not self.batch_manager:
            return [self.save_with_cache_invalidation(entity) for entity in entities]
        
        entity_type = entities[0].__class__.__name__ if entities else "Unknown"
        
        def batch_save_executor(batch_entities: List[T]) -> List[T]:
            results = []
            for entity in batch_entities:
                result = self.base_repository.save(entity)
                if result:
                    results.append(result)
            return results
        
        with self.performance_monitor.measure_operation("bulk_save", entity_type):
            # Add to batch
            for entity in entities:
                self.batch_manager.add_operation("save", entity)
            
            # Execute batch
            results = self.batch_manager.execute_batch("save", batch_save_executor, batch_size)
        
        # Invalidate caches
        if self.cache and results:
            for entity in results:
                self.cache.invalidate_entity(entity_type, entity.id)
            self.cache.invalidate_entity_queries(entity_type)
        
        self.performance_monitor.record_metric(
            PerformanceMetricType.BATCH_SIZE, len(entities), "bulk_save", entity_type
        )
        
        return results
    
    def execute_optimized_query(self, query: str, params: List[Any] = None,
                               use_cache: bool = True, ttl: Optional[int] = 1800) -> List[T]:
        """Execute query with optimization and caching"""
        params = params or []
        
        # Check cache first
        if use_cache and self.cache:
            cached_result = self.cache.get_query_result(query, params)
            if cached_result is not None:
                self.performance_monitor.record_metric(
                    PerformanceMetricType.CACHE_HIT_RATE, 1.0, "query", "cached"
                )
                return cached_result
        
        # Analyze query if optimizer available
        if self.query_optimizer:
            analysis = self.query_optimizer.analyze_query(query)
            if analysis.get("recommendations"):
                self._logger.info(f"Query optimization suggestions: {analysis['recommendations']}")
        
        # Execute query with performance monitoring
        start_time = time.time()
        result = self.base_repository.execute_query(query, params)
        execution_time = time.time() - start_time
        
        # Record performance information
        if self.query_optimizer:
            query_info = QueryPerformanceInfo(
                query=query,
                execution_time=execution_time,
                result_count=len(result),
                cache_hit=False,
                parameters=params
            )
            self.query_optimizer.record_query_performance(query_info)
        
        # Cache result if applicable
        if use_cache and self.cache and result:
            self.cache.set_query_result(query, params, result, ttl)
        
        self.performance_monitor.record_metric(
            PerformanceMetricType.QUERY_TIME, execution_time, "query", "optimized"
        )
        
        if not use_cache or not self.cache:
            self.performance_monitor.record_metric(
                PerformanceMetricType.CACHE_HIT_RATE, 0.0, "query", "uncached"
            )
        
        return result
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "performance_metrics": self.performance_monitor.get_metrics_summary(),
        }
        
        if self.cache:
            report["cache_statistics"] = self.cache.get_stats()
        
        if self.query_optimizer:
            report["query_statistics"] = self.query_optimizer.get_query_statistics()
            report["slow_queries"] = [
                {
                    "query": q.query[:100] + "..." if len(q.query) > 100 else q.query,
                    "execution_time": q.execution_time,
                    "result_count": q.result_count
                }
                for q in self.query_optimizer.get_slow_queries()[:10]  # Top 10 slow queries
            ]
        
        if self.batch_manager:
            report["batch_operations"] = {
                operation_type: self.batch_manager.get_pending_count(operation_type)
                for operation_type in ["save", "update", "delete"]
            }
        
        return report


# Global performance instances
_global_cache_provider: Optional[ICacheProvider] = None
_global_query_optimizer: Optional[QueryOptimizer] = None
_global_performance_monitor: Optional[PerformanceMonitor] = None


def get_global_cache_provider() -> ICacheProvider:
    """Get or create global cache provider"""
    global _global_cache_provider
    if _global_cache_provider is None:
        _global_cache_provider = LRUCache(max_size=5000)
    return _global_cache_provider


def set_global_cache_provider(cache_provider: ICacheProvider) -> None:
    """Set global cache provider"""
    global _global_cache_provider
    _global_cache_provider = cache_provider


def get_global_query_optimizer() -> QueryOptimizer:
    """Get or create global query optimizer"""
    global _global_query_optimizer
    if _global_query_optimizer is None:
        _global_query_optimizer = QueryOptimizer()
    return _global_query_optimizer


def get_global_performance_monitor() -> PerformanceMonitor:
    """Get or create global performance monitor"""
    global _global_performance_monitor
    if _global_performance_monitor is None:
        _global_performance_monitor = PerformanceMonitor()
    return _global_performance_monitor


def performance_optimized(cache_strategy: CacheStrategy = CacheStrategy.LRU,
                         cache_size: int = 1000,
                         cache_ttl: int = 3600,
                         enable_batch_operations: bool = True,
                         enable_query_optimization: bool = True):
    """
    Decorator to add performance optimizations to repository methods
    
    Args:
        cache_strategy: Caching strategy to use
        cache_size: Maximum cache size for LRU cache
        cache_ttl: Time to live for TTL cache
        enable_batch_operations: Enable batch operation support
        enable_query_optimization: Enable query optimization
    """
    def decorator(repository_class):
        class OptimizedRepository(repository_class):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                
                # Setup cache provider
                if cache_strategy == CacheStrategy.LRU:
                    cache_provider = LRUCache(max_size=cache_size)
                elif cache_strategy == CacheStrategy.TTL:
                    cache_provider = TTLCache(default_ttl=cache_ttl)
                else:
                    cache_provider = get_global_cache_provider()
                
                # Initialize performance optimization components
                self._perf_optimizer = PerformanceOptimizedRepository(
                    self,  # Use self as base repository
                    cache_provider=cache_provider,
                    enable_query_optimization=enable_query_optimization,
                    enable_batch_operations=enable_batch_operations
                )
            
            def find_by_id(self, entity_id, *args, **kwargs):
                return self._perf_optimizer.find_by_id_cached(entity_id, cache_ttl)
            
            def save(self, entity, *args, **kwargs):
                return self._perf_optimizer.save_with_cache_invalidation(entity)
            
            def execute_query(self, query, params=None, *args, **kwargs):
                return self._perf_optimizer.execute_optimized_query(query, params)
            
            def get_performance_report(self):
                return self._perf_optimizer.get_performance_report()
        
        return OptimizedRepository
    
    return decorator 