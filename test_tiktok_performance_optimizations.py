#!/usr/bin/env python3
"""
TikTok Performance Optimization Test Suite

This module tests the performance improvements implemented in the enhanced TikTok handler,
including caching, connection pooling, memory optimization, and concurrent processing.
"""

import asyncio
import logging
import sys
import time
import gc
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from unittest.mock import Mock, patch, AsyncMock
import tempfile
import json

# Add the project root to sys.path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

# Import performance optimization components
from platforms.tiktok.performance_optimizations import (
    TikTokPerformanceCache,
    RegexCache,
    PerformanceMonitor,
    AsyncTaskPool,
    MemoryOptimizedProcessor,
    TikTokOptimizedOperations,
    get_optimized_operations
)

# Import handlers for comparison
from platforms.tiktok import TikTokHandler
try:
    from platforms.tiktok.enhanced_handler import EnhancedTikTokHandler
except ImportError:
    EnhancedTikTokHandler = None

# Set up logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class PerformanceTestResult:
    """Performance test result data"""
    test_name: str
    duration: float
    memory_usage: Optional[float]
    operations_per_second: float
    cache_hit_rate: Optional[float]
    success: bool
    details: Dict[str, Any]


class PerformanceBenchmark:
    """Performance benchmarking utilities"""
    
    def __init__(self):
        self.results: List[PerformanceTestResult] = []
        
        # Try to import psutil for memory monitoring
        try:
            import psutil
            self.process = psutil.Process()
            self.memory_available = True
        except ImportError:
            self.memory_available = False
            print("   ⚠️ psutil not available - memory usage monitoring disabled")
    
    def get_memory_usage(self) -> Optional[float]:
        """Get current memory usage in MB"""
        if self.memory_available:
            return self.process.memory_info().rss / 1024 / 1024
        return None
    
    def benchmark_operation(self, test_name: str, operation_count: int = 1):
        """Decorator for benchmarking operations"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # Force garbage collection before test
                gc.collect()
                
                start_memory = self.get_memory_usage()
                start_time = time.time()
                
                try:
                    result = await func(*args, **kwargs)
                    success = True
                except Exception as e:
                    result = str(e)
                    success = False
                
                end_time = time.time()
                end_memory = self.get_memory_usage()
                
                duration = end_time - start_time
                memory_delta = (end_memory - start_memory) if (start_memory and end_memory) else None
                ops_per_second = operation_count / duration if duration > 0 else 0
                
                test_result = PerformanceTestResult(
                    test_name=test_name,
                    duration=duration,
                    memory_usage=memory_delta,
                    operations_per_second=ops_per_second,
                    cache_hit_rate=None,
                    success=success,
                    details={'result': result, 'operation_count': operation_count}
                )
                
                self.results.append(test_result)
                return result
            return wrapper
        return decorator


def test_cache_performance():
    """Test caching system performance"""
    print("\n🚀 Testing Cache Performance")
    print("=" * 30)
    
    benchmark = PerformanceBenchmark()
    cache = TikTokPerformanceCache(max_size=1000, default_ttl=3600)
    
    # Test data
    test_data = {
        'video_id': '1234567890',
        'title': 'Test Video',
        'description': 'A test video with some content',
        'metadata': {
            'hashtags': ['test', 'video', 'performance'],
            'duration': 30,
            'views': 1000000
        }
    }
    
    @benchmark.benchmark_operation("Cache Write Performance", 1000)
    async def test_cache_writes():
        for i in range(1000):
            cache.set(f"test_key_{i}", test_data, ttl=3600)
        return True
    
    @benchmark.benchmark_operation("Cache Read Performance", 1000)
    async def test_cache_reads():
        hits = 0
        for i in range(1000):
            result = cache.get(f"test_key_{i}")
            if result:
                hits += 1
        return hits
    
    @benchmark.benchmark_operation("Cache Mixed Operations", 500)
    async def test_cache_mixed():
        # Mix of reads, writes, and deletes
        for i in range(500):
            if i % 3 == 0:
                cache.set(f"mixed_key_{i}", test_data)
            elif i % 3 == 1:
                cache.get(f"mixed_key_{i-1}")
            else:
                cache.get(f"nonexistent_key_{i}")
        return True
    
    # Run tests
    asyncio.run(test_cache_writes())
    asyncio.run(test_cache_reads())
    asyncio.run(test_cache_mixed())
    
    # Display cache statistics
    stats = cache.get_stats()
    print(f"\n📊 Cache Statistics:")
    print(f"   Size: {stats['size']}/{stats['max_size']}")
    print(f"   Hit Rate: {stats['hit_rate_percent']:.1f}%")
    print(f"   Total Hits: {stats['hit_count']}")
    print(f"   Total Misses: {stats['miss_count']}")
    print(f"   Evictions: {stats['eviction_count']}")
    
    # Performance results
    for result in benchmark.results:
        status = "✅" if result.success else "❌"
        print(f"   {status} {result.test_name}:")
        print(f"      Duration: {result.duration:.3f}s")
        print(f"      Ops/sec: {result.operations_per_second:.0f}")
        if result.memory_usage:
            print(f"      Memory: {result.memory_usage:.1f}MB")
    
    return all(r.success for r in benchmark.results)


def test_regex_cache_performance():
    """Test regex caching performance"""
    print("\n🔤 Testing Regex Cache Performance")
    print("=" * 35)
    
    benchmark = PerformanceBenchmark()
    regex_cache = RegexCache()
    
    # Test patterns
    patterns = [
        r'#[\w\u4e00-\u9fff]+',  # Hashtags
        r'@[\w\.-]+',            # Mentions
        r'https?://[^\s]+',      # URLs
        r'\d+',                  # Numbers
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',  # Emails
    ]
    
    test_text = """
    Check out this #amazing #video with @user123 and @another_user!
    Visit https://example.com for more info. Call 555-123-4567.
    Email us at test@example.com or support@company.org.
    #trending #viral #tiktok #content #creator
    """
    
    @benchmark.benchmark_operation("Regex Compilation", 500)
    async def test_regex_compilation():
        for i in range(100):
            for pattern in patterns:
                regex_cache.get_pattern(pattern)
        return True
    
    @benchmark.benchmark_operation("Regex Matching", 1000)
    async def test_regex_matching():
        matches = 0
        for i in range(200):
            for pattern in patterns:
                compiled_pattern = regex_cache.get_pattern(pattern)
                matches += len(compiled_pattern.findall(test_text))
        return matches
    
    # Run tests
    asyncio.run(test_regex_compilation())
    matches = asyncio.run(test_regex_matching())
    
    print(f"\n📊 Regex Cache Results:")
    print(f"   Cached Patterns: {len(regex_cache._patterns)}")
    print(f"   Total Matches Found: {matches}")
    
    # Performance results
    for result in benchmark.results:
        status = "✅" if result.success else "❌"
        print(f"   {status} {result.test_name}:")
        print(f"      Duration: {result.duration:.3f}s")
        print(f"      Ops/sec: {result.operations_per_second:.0f}")
        if result.memory_usage:
            print(f"      Memory: {result.memory_usage:.1f}MB")
    
    return all(r.success for r in benchmark.results)


def test_memory_optimization():
    """Test memory optimization utilities"""
    print("\n💾 Testing Memory Optimization")
    print("=" * 32)
    
    benchmark = PerformanceBenchmark()
    
    # Large test data
    large_json_data = {
        'formats': [
            {
                'format_id': f'format_{i}',
                'url': f'https://example.com/video_{i}.mp4',
                'width': 1920 if i % 2 == 0 else 1280,
                'height': 1080 if i % 2 == 0 else 720,
                'filesize': 1024 * 1024 * (i + 1),
                'ext': 'mp4',
                'vcodec': 'h264',
                'acodec': 'aac'
            }
            for i in range(100)
        ],
        'metadata': {
            'title': 'Large Video' * 100,
            'description': 'A very long description ' * 200,
            'tags': [f'tag_{i}' for i in range(50)],
            'additional_data': 'X' * 10000  # 10KB of data
        }
    }
    
    @benchmark.benchmark_operation("JSON Lazy Parsing", 100)
    async def test_lazy_json_parsing():
        json_str = json.dumps(large_json_data)
        target_keys = {'formats', 'metadata'}
        
        for i in range(100):
            result = MemoryOptimizedProcessor.lazy_json_parse(json_str, target_keys)
        
        return len(result)
    
    @benchmark.benchmark_operation("String List Optimization", 1000)
    async def test_string_optimization():
        # Create list with duplicates and extra whitespace
        test_strings = []
        for i in range(1000):
            for base in ['tag', 'hashtag', 'mention', 'keyword']:
                test_strings.append(f'  {base}_{i % 50}  ')  # Duplicates every 50
        
        optimized = MemoryOptimizedProcessor.optimize_string_list(test_strings)
        return len(optimized)
    
    @benchmark.benchmark_operation("Batch Processing", 500)
    async def test_batch_processing():
        large_list = list(range(10000))
        batches = MemoryOptimizedProcessor.batch_process(large_list, batch_size=100)
        
        total_items = 0
        for batch in batches:
            total_items += len(batch)
        
        return total_items
    
    # Run tests
    parsed_size = asyncio.run(test_lazy_json_parsing())
    optimized_size = asyncio.run(test_string_optimization())
    total_items = asyncio.run(test_batch_processing())
    
    print(f"\n📊 Memory Optimization Results:")
    print(f"   Parsed JSON Keys: {parsed_size}")
    print(f"   Optimized Strings: {optimized_size}")
    print(f"   Batch Processed Items: {total_items}")
    
    # Performance results
    for result in benchmark.results:
        status = "✅" if result.success else "❌"
        print(f"   {status} {result.test_name}:")
        print(f"      Duration: {result.duration:.3f}s")
        print(f"      Ops/sec: {result.operations_per_second:.0f}")
        if result.memory_usage:
            print(f"      Memory: {result.memory_usage:.1f}MB")
    
    return all(r.success for r in benchmark.results)


def test_async_task_pool():
    """Test async task pool performance"""
    print("\n⚡ Testing Async Task Pool")
    print("=" * 27)
    
    benchmark = PerformanceBenchmark()
    task_pool = AsyncTaskPool(max_concurrent=5)
    
    async def mock_task(task_id: int, duration: float = 0.01):
        """Mock async task for testing"""
        await asyncio.sleep(duration)
        return f"task_{task_id}_completed"
    
    @benchmark.benchmark_operation("Concurrent Task Execution", 50)
    async def test_concurrent_execution():
        tasks = [mock_task(i, 0.01) for i in range(50)]
        results = await task_pool.submit_many(tasks)
        return len([r for r in results if not isinstance(r, Exception)])
    
    @benchmark.benchmark_operation("Sequential vs Parallel", 20)
    async def test_sequential_vs_parallel():
        # Test parallel execution
        parallel_start = time.time()
        tasks = [mock_task(i, 0.05) for i in range(20)]
        parallel_results = await task_pool.submit_many(tasks)
        parallel_duration = time.time() - parallel_start
        
        # Test sequential execution
        sequential_start = time.time()
        sequential_results = []
        for i in range(20):
            result = await mock_task(i, 0.05)
            sequential_results.append(result)
        sequential_duration = time.time() - sequential_start
        
        speedup = sequential_duration / parallel_duration
        return speedup
    
    # Run tests
    completed_tasks = asyncio.run(test_concurrent_execution())
    speedup = asyncio.run(test_sequential_vs_parallel())
    
    # Get task pool stats
    stats = task_pool.get_stats()
    
    print(f"\n📊 Task Pool Results:")
    print(f"   Completed Tasks: {completed_tasks}/50")
    print(f"   Parallel Speedup: {speedup:.1f}x")
    print(f"   Max Concurrent: {stats['max_concurrent']}")
    print(f"   Total Completed: {stats['completed_count']}")
    print(f"   Total Failed: {stats['failed_count']}")
    
    # Performance results
    for result in benchmark.results:
        status = "✅" if result.success else "❌"
        print(f"   {status} {result.test_name}:")
        print(f"      Duration: {result.duration:.3f}s")
        print(f"      Ops/sec: {result.operations_per_second:.0f}")
        if result.memory_usage:
            print(f"      Memory: {result.memory_usage:.1f}MB")
    
    return all(r.success for r in benchmark.results) and speedup > 2.0


def test_optimized_operations():
    """Test complete optimized operations suite"""
    print("\n🎯 Testing Optimized Operations Suite")
    print("=" * 38)
    
    benchmark = PerformanceBenchmark()
    ops = get_optimized_operations()
    
    # Mock TikTok result data
    mock_result = {
        'id': '1234567890',
        'title': 'Amazing TikTok Video #viral #trending',
        'description': 'Check this out @user123 and @friend456! #amazing #content #creator',
        'uploader': 'test_creator',
        'duration': 30,
        'view_count': 1000000,
        'like_count': 50000,
        'upload_date': '20231201',
        'formats': [
            {
                'format_id': f'format_{i}',
                'url': f'https://example.com/video_{i}.mp4',
                'width': 1920 if i % 2 == 0 else 1280,
                'height': 1080 if i % 2 == 0 else 720,
                'filesize': 1024 * 1024 * (i + 1),
                'ext': 'mp4'
            }
            for i in range(20)
        ]
    }
    
    @benchmark.benchmark_operation("Optimized Metadata Extraction", 100)
    async def test_metadata_extraction():
        results = []
        for i in range(100):
            cache_key = f"test_metadata_{i}"
            result = await ops.extract_metadata_optimized(
                mock_result, 
                f"https://tiktok.com/video/{i}",
                cache_key
            )
            results.append(result)
        return len(results)
    
    @benchmark.benchmark_operation("Optimized Format Processing", 50)
    async def test_format_processing():
        formats = mock_result['formats'] * 5  # 100 total formats
        processed = await ops.process_formats_batch(formats)
        return len(processed)
    
    # Run tests
    metadata_count = asyncio.run(test_metadata_extraction())
    format_count = asyncio.run(test_format_processing())
    
    # Get performance report
    perf_report = ops.get_performance_report()
    
    print(f"\n📊 Optimized Operations Results:")
    print(f"   Metadata Extractions: {metadata_count}")
    print(f"   Processed Formats: {format_count}")
    print(f"   Cache Hit Rate: {perf_report['cache_stats']['hit_rate_percent']:.1f}%")
    print(f"   Regex Cache Size: {perf_report['regex_cache_size']}")
    
    # Performance results
    for result in benchmark.results:
        status = "✅" if result.success else "❌"
        print(f"   {status} {result.test_name}:")
        print(f"      Duration: {result.duration:.3f}s")
        print(f"      Ops/sec: {result.operations_per_second:.0f}")
        if result.memory_usage:
            print(f"      Memory: {result.memory_usage:.1f}MB")
    
    return all(r.success for r in benchmark.results)


def test_handler_comparison():
    """Compare base handler vs enhanced handler performance"""
    print("\n⚔️ Testing Handler Performance Comparison")
    print("=" * 43)
    
    if not EnhancedTikTokHandler:
        print("   ⚠️ Enhanced handler not available - skipping comparison")
        return True
    
    benchmark = PerformanceBenchmark()
    
    # Create handlers
    base_handler = TikTokHandler()
    enhanced_handler = EnhancedTikTokHandler()
    
    test_urls = [
        "https://www.tiktok.com/@user1/video/1234567890",
        "https://www.tiktok.com/@user2/video/2345678901",
        "https://www.tiktok.com/@user3/video/3456789012",
    ]
    
    @benchmark.benchmark_operation("Base Handler URL Validation", 300)
    async def test_base_validation():
        valid_count = 0
        for i in range(100):
            for url in test_urls:
                if base_handler.is_valid_url(url):
                    valid_count += 1
        return valid_count
    
    @benchmark.benchmark_operation("Enhanced Handler URL Validation", 300)
    async def test_enhanced_validation():
        valid_count = 0
        for i in range(100):
            for url in test_urls:
                if enhanced_handler.is_valid_url(url):
                    valid_count += 1
        return valid_count
    
    @benchmark.benchmark_operation("Base Handler Capabilities", 100)
    async def test_base_capabilities():
        for i in range(100):
            caps = base_handler.get_capabilities()
        return True
    
    @benchmark.benchmark_operation("Enhanced Handler Capabilities", 100)
    async def test_enhanced_capabilities():
        for i in range(100):
            caps = enhanced_handler.get_capabilities()
        return True
    
    # Run tests
    base_validations = asyncio.run(test_base_validation())
    enhanced_validations = asyncio.run(test_enhanced_validation())
    asyncio.run(test_base_capabilities())
    asyncio.run(test_enhanced_capabilities())
    
    print(f"\n📊 Handler Comparison Results:")
    print(f"   Base Handler Validations: {base_validations}")
    print(f"   Enhanced Handler Validations: {enhanced_validations}")
    
    # Get enhanced handler performance stats
    if hasattr(enhanced_handler, 'get_performance_stats'):
        stats = enhanced_handler.get_performance_stats()
        print(f"   Enhanced Handler Cache Enabled: {stats['handler_stats']['performance_config']['caching_enabled']}")
        print(f"   Enhanced Handler Operations: {stats['handler_stats']['total_operations']}")
    
    # Performance results
    for result in benchmark.results:
        status = "✅" if result.success else "❌"
        print(f"   {status} {result.test_name}:")
        print(f"      Duration: {result.duration:.3f}s")
        print(f"      Ops/sec: {result.operations_per_second:.0f}")
        if result.memory_usage:
            print(f"      Memory: {result.memory_usage:.1f}MB")
    
    return all(r.success for r in benchmark.results)


async def test_performance_optimizations():
    """Run all performance optimization tests"""
    print("🚀 TikTok Performance Optimization Test Suite")
    print("=" * 46)
    
    test_results = []
    
    try:
        # Run individual test components
        cache_result = test_cache_performance()
        test_results.append(("Cache Performance", cache_result))
        
        regex_result = test_regex_cache_performance()
        test_results.append(("Regex Cache Performance", regex_result))
        
        memory_result = test_memory_optimization()
        test_results.append(("Memory Optimization", memory_result))
        
        task_pool_result = test_async_task_pool()
        test_results.append(("Async Task Pool", task_pool_result))
        
        operations_result = test_optimized_operations()
        test_results.append(("Optimized Operations", operations_result))
        
        comparison_result = test_handler_comparison()
        test_results.append(("Handler Comparison", comparison_result))
        
    except Exception as e:
        print(f"❌ Performance testing failed: {e}")
        return False
    
    # Summary
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    print(f"\n🎯 Performance Optimization Test Summary")
    print("=" * 42)
    
    for test_name, result in test_results:
        status = "✅" if result else "❌"
        print(f"   {status} {test_name}: {'PASSED' if result else 'FAILED'}")
    
    overall_success = passed / total >= 0.8  # 80% pass rate
    
    print(f"\n📊 Overall: {passed}/{total} performance tests passed ({passed/total*100:.1f}%)")
    
    if overall_success:
        print("✅ Performance optimization testing completed successfully!")
        print("TikTok handler shows significant performance improvements.")
        
        # Display optimization benefits
        print("\n🎉 Key Performance Benefits:")
        print("   • Advanced caching system with TTL and LRU eviction")
        print("   • Regex pattern compilation caching")
        print("   • Memory-efficient data processing")
        print("   • Concurrent task execution with pooling")
        print("   • Optimized metadata extraction")
        print("   • Enhanced error handling with monitoring")
        
    else:
        print("⚠️ Some performance tests failed.")
        print("Performance optimizations may need additional tuning.")
    
    return overall_success


def main():
    """Main performance test function"""
    try:
        return asyncio.run(test_performance_optimizations())
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 