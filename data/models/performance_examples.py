"""
Performance Optimization Examples for Social Download Manager v2.0

Demonstrates caching strategies, batch operations, query optimization,
and performance monitoring in real-world scenarios.
"""

import time
import logging
from typing import List
from datetime import datetime

from .base import EntityId
from .downloads import DownloadModel, DownloadSession, DownloadError, DownloadStatus
from .download_repositories import (
    get_download_repository, get_download_session_repository, get_download_error_repository
)
from .performance_optimizations import (
    LRUCache, TTLCache, RepositoryCache, BatchOperationManager,
    QueryOptimizer, PerformanceMonitor, PerformanceOptimizedRepository,
    CacheStrategy, performance_optimized, get_global_cache_provider,
    get_global_performance_monitor, get_global_query_optimizer
)


def example_basic_caching():
    """Example: Basic caching with LRU and TTL strategies"""
    print("=== Basic Caching Examples ===")
    
    # LRU Cache example
    print("\nLRU Cache:")
    lru_cache = LRUCache(max_size=5)
    
    # Add items
    for i in range(7):
        lru_cache.set(f"key_{i}", f"value_{i}")
        print(f"Added key_{i}")
    
    # Check what's in cache (should only have last 5)
    for i in range(7):
        value = lru_cache.get(f"key_{i}")
        print(f"key_{i}: {value}")
    
    print(f"LRU Stats: {lru_cache.get_stats()}")
    
    # TTL Cache example
    print("\nTTL Cache:")
    ttl_cache = TTLCache(default_ttl=2)  # 2 seconds TTL
    
    ttl_cache.set("temp_key", "temp_value")
    print(f"Immediately: {ttl_cache.get('temp_key')}")
    
    time.sleep(1)
    print(f"After 1s: {ttl_cache.get('temp_key')}")
    
    time.sleep(2)
    print(f"After 3s total: {ttl_cache.get('temp_key')}")
    
    print(f"TTL Stats: {ttl_cache.get_stats()}")


def example_repository_caching():
    """Example: Repository-level caching"""
    print("\n=== Repository Caching Examples ===")
    
    download_repo = get_download_repository()
    
    # Create cache
    cache_provider = LRUCache(max_size=100)
    repo_cache = RepositoryCache(cache_provider)
    
    # Create some test downloads
    downloads = []
    for i in range(3):
        download = DownloadModel(
            content_id=f"cache-test-{i:03d}",
            url=f"https://example.com/cache/video{i}.mp4",
            status=DownloadStatus.QUEUED,
            file_path=f"/downloads/cache/video{i}.mp4"
        )
        saved = download_repo.save(download)
        if saved:
            downloads.append(saved)
            # Cache the entity
            repo_cache.set_entity(saved)
    
    # Test cache hits
    print("Testing cache performance:")
    for download in downloads:
        start_time = time.time()
        
        # Cache hit
        cached_entity = repo_cache.get_entity("DownloadModel", download.id)
        cache_time = time.time() - start_time
        
        start_time = time.time()
        
        # Database hit
        db_entity = download_repo.find_by_id(download.id)
        db_time = time.time() - start_time
        
        print(f"Download {download.id}: Cache={cache_time:.6f}s, DB={db_time:.6f}s")
        print(f"  Cache hit: {cached_entity is not None}")
        print(f"  Speed improvement: {(db_time/cache_time):.1f}x faster" if cache_time > 0 else "  N/A")
    
    print(f"Cache Stats: {cache_provider.get_stats()}")


def example_batch_operations():
    """Example: Batch operations for improved performance"""
    print("\n=== Batch Operations Examples ===")
    
    download_repo = get_download_repository()
    batch_manager = BatchOperationManager(default_batch_size=3)
    
    # Create test data
    test_downloads = []
    for i in range(8):
        download = DownloadModel(
            content_id=f"batch-test-{i:03d}",
            url=f"https://example.com/batch/video{i}.mp4",
            status=DownloadStatus.QUEUED,
            file_path=f"/downloads/batch/video{i}.mp4"
        )
        test_downloads.append(download)
    
    # Individual saves timing
    print("Individual saves:")
    start_time = time.time()
    individual_results = []
    for download in test_downloads:
        saved = download_repo.save(download)
        if saved:
            individual_results.append(saved)
    individual_time = time.time() - start_time
    print(f"Individual saves: {len(individual_results)} items in {individual_time:.3f}s")
    
    # Cleanup for batch test
    for download in individual_results:
        download_repo.delete(download.id, soft_delete=False)
    
    # Batch saves timing
    print("\nBatch saves:")
    start_time = time.time()
    
    # Add operations to batch
    for download in test_downloads:
        batch_manager.add_operation("save", download)
    
    # Execute batch
    def batch_save_executor(batch_downloads: List[DownloadModel]) -> List[DownloadModel]:
        results = []
        for download in batch_downloads:
            saved = download_repo.save(download)
            if saved:
                results.append(saved)
        return results
    
    batch_results = batch_manager.execute_batch("save", batch_save_executor)
    batch_time = time.time() - start_time
    
    print(f"Batch saves: {len(batch_results)} items in {batch_time:.3f}s")
    print(f"Performance improvement: {(individual_time/batch_time):.1f}x faster" if batch_time > 0 else "N/A")


def example_query_optimization():
    """Example: Query optimization and analysis"""
    print("\n=== Query Optimization Examples ===")
    
    download_repo = get_download_repository()
    query_optimizer = QueryOptimizer()
    
    # Test queries with different complexity
    test_queries = [
        ("Simple query", "SELECT * FROM downloads WHERE status = ?", [DownloadStatus.QUEUED.value]),
        ("Complex query", 
         """SELECT d.*, s.started_at, s.progress 
            FROM downloads d 
            LEFT JOIN download_sessions s ON d.id = s.download_id 
            WHERE d.status IN (?, ?, ?) 
            ORDER BY d.created_at DESC 
            LIMIT 10""", 
         [DownloadStatus.DOWNLOADING.value, DownloadStatus.PROCESSING.value, DownloadStatus.QUEUED.value]),
        ("Aggregate query", 
         """SELECT status, COUNT(*) as count, AVG(file_size) as avg_size 
            FROM downloads 
            WHERE is_deleted = 0 
            GROUP BY status 
            ORDER BY count DESC""", 
         [])
    ]
    
    for query_name, query, params in test_queries:
        print(f"\n{query_name}:")
        
        # Analyze query
        analysis = query_optimizer.analyze_query(query)
        print(f"  Complexity: {analysis['estimated_complexity']}/10")
        print(f"  Has JOINs: {analysis['has_joins']}")
        print(f"  Has LIMIT: {analysis['has_limit']}")
        
        if analysis['recommendations']:
            print("  Recommendations:")
            for rec in analysis['recommendations']:
                print(f"    - {rec}")
        
        # Execute and time query
        start_time = time.time()
        try:
            results = download_repo.execute_query(query, params)
            execution_time = time.time() - start_time
            
            # Record performance
            from .performance_optimizations import QueryPerformanceInfo
            query_info = QueryPerformanceInfo(
                query=query,
                execution_time=execution_time,
                result_count=len(results),
                parameters=params
            )
            query_optimizer.record_query_performance(query_info)
            
            print(f"  Execution time: {execution_time:.3f}s")
            print(f"  Results: {len(results)} items")
            
        except Exception as e:
            print(f"  Error: {e}")
    
    # Show query statistics
    print(f"\nQuery Statistics: {query_optimizer.get_query_statistics()}")
    
    # Show slow queries
    slow_queries = query_optimizer.get_slow_queries(threshold=0.01)  # 10ms threshold
    if slow_queries:
        print(f"Slow queries ({len(slow_queries)}):")
        for i, slow_query in enumerate(slow_queries[:3]):  # Top 3
            print(f"  {i+1}. {slow_query.execution_time:.3f}s - {slow_query.query[:50]}...")


def example_performance_monitoring():
    """Example: Performance monitoring and metrics"""
    print("\n=== Performance Monitoring Examples ===")
    
    monitor = PerformanceMonitor()
    download_repo = get_download_repository()
    
    # Simulate various operations with monitoring
    operations = [
        ("save_download", lambda: download_repo.save(DownloadModel(
            content_id=f"monitor-test-{int(time.time())}",
            url="https://example.com/monitor/test.mp4",
            status=DownloadStatus.QUEUED,
            file_path="/downloads/monitor/test.mp4"
        ))),
        ("find_all_downloads", lambda: download_repo.find_all()),
        ("find_active_downloads", lambda: download_repo.find_active_downloads()),
        ("get_statistics", lambda: download_repo.get_download_statistics())
    ]
    
    for operation_name, operation_func in operations:
        try:
            with monitor.measure_operation(operation_name, "DownloadModel"):
                result = operation_func()
                print(f"{operation_name}: {'Success' if result else 'No result'}")
        except Exception as e:
            print(f"{operation_name}: Error - {e}")
    
    # Record some custom metrics
    from .performance_optimizations import PerformanceMetricType
    monitor.record_metric(PerformanceMetricType.CACHE_HIT_RATE, 85.5, "cache_test")
    monitor.record_metric(PerformanceMetricType.BATCH_SIZE, 50, "bulk_save")
    
    # Get metrics summary
    print("\nPerformance Metrics Summary:")
    summary = monitor.get_metrics_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    # Get operation-specific metrics
    query_metrics = monitor.get_metrics_summary(
        metric_type=PerformanceMetricType.QUERY_TIME,
        operation="find_all_downloads"
    )
    print(f"\nFind All Downloads Metrics: {query_metrics}")


@performance_optimized(
    cache_strategy=CacheStrategy.LRU,
    cache_size=200,
    enable_batch_operations=True,
    enable_query_optimization=True
)
class OptimizedDownloadRepository:
    """Example of optimized repository using decorator"""
    
    def __init__(self, base_repo):
        self.base_repo = base_repo
    
    def __getattr__(self, name):
        # Delegate to base repository for methods not overridden
        return getattr(self.base_repo, name)


def example_optimized_repository():
    """Example: Using performance-optimized repository wrapper"""
    print("\n=== Optimized Repository Examples ===")
    
    base_repo = get_download_repository()
    cache_provider = LRUCache(max_size=100)
    
    # Create optimized repository
    optimized_repo = PerformanceOptimizedRepository(
        base_repository=base_repo,
        cache_provider=cache_provider,
        enable_query_optimization=True,
        enable_batch_operations=True
    )
    
    # Test cached operations
    test_downloads = []
    for i in range(3):
        download = DownloadModel(
            content_id=f"optimized-test-{i:03d}",
            url=f"https://example.com/optimized/video{i}.mp4",
            status=DownloadStatus.QUEUED,
            file_path=f"/downloads/optimized/video{i}.mp4"
        )
        saved = optimized_repo.save_with_cache_invalidation(download)
        if saved:
            test_downloads.append(saved)
    
    print(f"Created {len(test_downloads)} test downloads")
    
    # Test cache performance
    print("\nTesting cache performance:")
    for download in test_downloads:
        # First call - cache miss
        start_time = time.time()
        result1 = optimized_repo.find_by_id_cached(download.id)
        time1 = time.time() - start_time
        
        # Second call - cache hit
        start_time = time.time()
        result2 = optimized_repo.find_by_id_cached(download.id)
        time2 = time.time() - start_time
        
        print(f"  Download {download.id}:")
        print(f"    Cache miss: {time1:.6f}s")
        print(f"    Cache hit: {time2:.6f}s")
        print(f"    Improvement: {(time1/time2):.1f}x faster" if time2 > 0 else "    N/A")
    
    # Test bulk operations
    print("\nTesting bulk operations:")
    bulk_downloads = []
    for i in range(5):
        download = DownloadModel(
            content_id=f"bulk-optimized-{i:03d}",
            url=f"https://example.com/bulk-opt/video{i}.mp4",
            status=DownloadStatus.QUEUED,
            file_path=f"/downloads/bulk-opt/video{i}.mp4"
        )
        bulk_downloads.append(download)
    
    start_time = time.time()
    bulk_results = optimized_repo.bulk_save(bulk_downloads, batch_size=2)
    bulk_time = time.time() - start_time
    
    print(f"Bulk saved {len(bulk_results)} downloads in {bulk_time:.3f}s")
    
    # Get performance report
    print("\nPerformance Report:")
    report = optimized_repo.get_performance_report()
    for section, data in report.items():
        if isinstance(data, dict):
            print(f"  {section}:")
            for key, value in data.items():
                print(f"    {key}: {value}")
        else:
            print(f"  {section}: {data}")


def example_global_performance_management():
    """Example: Global performance management"""
    print("\n=== Global Performance Management ===")
    
    # Get global instances
    global_cache = get_global_cache_provider()
    global_monitor = get_global_performance_monitor()
    global_optimizer = get_global_query_optimizer()
    
    print("Global instances initialized:")
    print(f"  Cache: {type(global_cache).__name__}")
    print(f"  Monitor: {type(global_monitor).__name__}")
    print(f"  Optimizer: {type(global_optimizer).__name__}")
    
    # Use global cache
    global_cache.set("global_test_key", "global_test_value")
    value = global_cache.get("global_test_key")
    print(f"Global cache test: {value}")
    
    # Global cache stats
    cache_stats = global_cache.get_stats()
    print(f"Global cache stats: {cache_stats}")
    
    # Global monitor metrics
    from .performance_optimizations import PerformanceMetricType
    global_monitor.record_metric(
        PerformanceMetricType.MEMORY_USAGE, 
        75.5, 
        "global_test", 
        "system"
    )
    
    monitor_summary = global_monitor.get_metrics_summary()
    print(f"Global monitor summary: {monitor_summary}")
    
    # Cleanup old metrics
    cleaned_count = global_monitor.clear_old_metrics(hours=0)  # Clear all for demo
    print(f"Cleaned {cleaned_count} old metrics")


def example_cache_invalidation_strategies():
    """Example: Cache invalidation strategies"""
    print("\n=== Cache Invalidation Examples ===")
    
    cache_provider = LRUCache(max_size=50)
    repo_cache = RepositoryCache(cache_provider)
    download_repo = get_download_repository()
    
    # Create and cache some entities
    test_download = DownloadModel(
        content_id="invalidation-test",
        url="https://example.com/invalidation/test.mp4",
        status=DownloadStatus.QUEUED,
        file_path="/downloads/invalidation/test.mp4"
    )
    
    saved_download = download_repo.save(test_download)
    if saved_download:
        # Cache the entity
        repo_cache.set_entity(saved_download)
        print(f"Cached download {saved_download.id}")
        
        # Verify cache hit
        cached = repo_cache.get_entity("DownloadModel", saved_download.id)
        print(f"Cache hit: {cached is not None}")
        
        # Invalidate cache
        repo_cache.invalidate_entity("DownloadModel", saved_download.id)
        print("Invalidated cache entry")
        
        # Verify cache miss
        cached_after = repo_cache.get_entity("DownloadModel", saved_download.id)
        print(f"Cache hit after invalidation: {cached_after is not None}")
        
        # Test query cache invalidation
        query = "SELECT * FROM downloads WHERE status = ?"
        params = [DownloadStatus.QUEUED.value]
        
        # Cache query result
        query_result = download_repo.execute_query(query, params)
        repo_cache.set_query_result(query, params, query_result)
        print(f"Cached query result: {len(query_result)} items")
        
        # Get cached result
        cached_query = repo_cache.get_query_result(query, params)
        print(f"Retrieved cached query: {len(cached_query) if cached_query else 0} items")
        
        # Invalidate entity queries
        repo_cache.invalidate_entity_queries("DownloadModel")
        print("Invalidated entity queries")


def run_all_performance_examples():
    """Run all performance optimization examples"""
    print("=== Performance Optimization Examples for Social Download Manager ===\n")
    
    examples = [
        ("Basic Caching", example_basic_caching),
        ("Repository Caching", example_repository_caching),
        ("Batch Operations", example_batch_operations),
        ("Query Optimization", example_query_optimization),
        ("Performance Monitoring", example_performance_monitoring),
        ("Optimized Repository", example_optimized_repository),
        ("Global Performance Management", example_global_performance_management),
        ("Cache Invalidation Strategies", example_cache_invalidation_strategies)
    ]
    
    for name, example_func in examples:
        try:
            print(f"\n{'='*50}")
            print(f"{name}")
            print(f"{'='*50}")
            example_func()
            print(f"\n{name} completed successfully!")
        except Exception as e:
            logging.error(f"Example '{name}' failed: {e}", exc_info=True)
            print(f"\nExample '{name}' failed: {e}")
        
        print()  # Add spacing between examples
    
    print("All performance optimization examples completed!")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    run_all_performance_examples() 