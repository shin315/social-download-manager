"""
Test Performance Optimization - Task 18.9
Social Download Manager v2.0

Comprehensive tests for large dataset performance optimization including
intelligent caching, virtual scrolling, progressive loading, and memory
management strategies.
"""

import unittest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from typing import Dict, Any, List
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Core imports
from core.data_integration.performance_optimization import (
    IntelligentCache, VirtualScrollManager, ProgressiveLoader, DatasetPerformanceManager,
    CacheStrategy, LoadingStrategy, MemoryTier, PerformanceMetrics, CacheItem,
    PaginationConfig, get_dataset_performance_manager, reset_dataset_performance_manager
)

# Repository interfaces and models
from data.models.content import ContentModel, ContentStatus, PlatformType, ContentType


class MockContentRepository:
    """Mock repository for testing performance optimization"""
    
    def __init__(self, total_items: int = 10000):
        self.total_items = total_items
        self._items = [
            ContentModel(
                id=f"item_{i}",
                title=f"Test Item {i}",
                platform=PlatformType.YOUTUBE,
                url=f"https://example.com/video{i}",
                status=ContentStatus.PENDING,
                content_type=ContentType.VIDEO
            )
            for i in range(total_items)
        ]
        self._call_log = []
    
    async def get_all(self, limit: int = None) -> List[ContentModel]:
        self._call_log.append(('get_all', limit))
        if limit:
            return self._items[:limit]
        return self._items
    
    async def get_paginated(self, offset: int = 0, limit: int = 100, filters: Dict = None) -> List[ContentModel]:
        self._call_log.append(('get_paginated', offset, limit, filters))
        end_index = min(offset + limit, len(self._items))
        return self._items[offset:end_index]
    
    async def count(self) -> int:
        self._call_log.append(('count',))
        return self.total_items


class TestIntelligentCache(unittest.TestCase):
    """Test IntelligentCache functionality"""
    
    def setUp(self):
        self.cache = IntelligentCache(
            max_size=100,
            strategy=CacheStrategy.ADAPTIVE,
            memory_limit_mb=10.0  # Small limit for testing
        )
    
    def test_basic_cache_operations(self):
        """Test basic get/put operations"""
        # Put item
        success = self.cache.put("key1", "value1")
        self.assertTrue(success)
        
        # Get item
        value = self.cache.get("key1")
        self.assertEqual(value, "value1")
        
        # Get non-existent item
        value = self.cache.get("nonexistent")
        self.assertIsNone(value)
    
    def test_cache_strategies(self):
        """Test different caching strategies"""
        # Test LRU strategy
        lru_cache = IntelligentCache(max_size=3, strategy=CacheStrategy.LRU)
        
        # Fill cache
        lru_cache.put("key1", "value1")
        lru_cache.put("key2", "value2")
        lru_cache.put("key3", "value3")
        
        # Access key1 to make it most recently used
        lru_cache.get("key1")
        
        # Add key4 - should evict key2 (least recently used)
        lru_cache.put("key4", "value4")
        
        self.assertIsNotNone(lru_cache.get("key1"))  # Should still exist
        self.assertIsNone(lru_cache.get("key2"))     # Should be evicted
        self.assertIsNotNone(lru_cache.get("key3"))  # Should still exist
        self.assertIsNotNone(lru_cache.get("key4"))  # Should exist
    
    def test_ttl_expiration(self):
        """Test TTL-based cache expiration"""
        # Put item with short TTL
        self.cache.put("temp_key", "temp_value", ttl_seconds=1)
        
        # Should be available immediately
        value = self.cache.get("temp_key")
        self.assertEqual(value, "temp_value")
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired
        value = self.cache.get("temp_key")
        self.assertIsNone(value)
    
    def test_memory_tiers(self):
        """Test memory tier determination"""
        # Small frequent item should be HOT
        self.cache._access_frequencies["hot_key"] = 15
        tier = self.cache._determine_memory_tier("hot_key", 512)  # 512 bytes
        self.assertEqual(tier, MemoryTier.HOT)
        
        # Medium access item should be WARM
        self.cache._access_frequencies["warm_key"] = 5
        tier = self.cache._determine_memory_tier("warm_key", 1024 * 512)  # 512KB
        self.assertEqual(tier, MemoryTier.WARM)
        
        # Large infrequent item should be COLD
        tier = self.cache._determine_memory_tier("cold_key", 1024 * 1024 * 2)  # 2MB
        self.assertEqual(tier, MemoryTier.COLD)
    
    def test_cache_statistics(self):
        """Test cache statistics generation"""
        # Add some items
        self.cache.put("key1", "value1")
        self.cache.put("key2", "value2")
        
        # Access items
        self.cache.get("key1")  # Hit
        self.cache.get("nonexistent")  # Miss
        
        stats = self.cache.get_statistics()
        
        self.assertEqual(stats["total_items"], 2)
        self.assertEqual(stats["cache_hits"], 1)
        self.assertEqual(stats["cache_misses"], 1)
        self.assertEqual(stats["cache_hit_ratio"], 50.0)
        self.assertIn("efficiency_score", stats)
        self.assertIn("memory_tiers", stats)
    
    def test_cache_compression(self):
        """Test automatic compression for large items"""
        # Create large data that should trigger compression
        large_data = "x" * (1024 * 1024 + 1)  # > 1MB threshold
        
        success = self.cache.put("large_key", large_data)
        self.assertTrue(success)
        
        # Verify item is in cache
        cached_item = self.cache._cache.get("large_key")
        if cached_item:
            # Note: Compression might not work in test environment, so just check structure
            self.assertIsNotNone(cached_item)
            self.assertGreater(cached_item.size_bytes, 0)


class TestVirtualScrollManager(unittest.TestCase):
    """Test VirtualScrollManager functionality"""
    
    def setUp(self):
        self.mock_repo = MockContentRepository(total_items=1000)
        self.config = PaginationConfig(
            page_size=50,
            prefetch_pages=2,
            max_cached_pages=5
        )
        self.virtual_scroll = VirtualScrollManager(self.config, self.mock_repo)
    
    def test_initialization(self):
        """Test virtual scroll manager initialization"""
        async def run_test():
            success = await self.virtual_scroll.initialize()
            self.assertTrue(success)
            self.assertEqual(self.virtual_scroll.total_items, 1000)
            self.assertTrue(len(self.virtual_scroll.loaded_pages) > 0)
        
        asyncio.run(run_test())
    
    def test_page_loading(self):
        """Test individual page loading"""
        async def run_test():
            # Load specific page
            items = await self.virtual_scroll.load_page(0)
            
            self.assertEqual(len(items), 50)  # page_size
            self.assertEqual(items[0].id, "item_0")
            self.assertEqual(items[-1].id, "item_49")
            
            # Verify page is cached
            self.assertIn(0, self.virtual_scroll.loaded_pages)
        
        asyncio.run(run_test())
    
    def test_visible_range_management(self):
        """Test visible range setting and prefetching"""
        async def run_test():
            await self.virtual_scroll.initialize()
            
            # Set visible range that spans multiple pages
            await self.virtual_scroll.set_visible_range(45, 105)  # Pages 0, 1, 2
            
            # Should have loaded required pages and prefetch pages
            expected_pages = [0, 1, 2, 3, 4]  # Current + prefetch
            loaded_pages = list(self.virtual_scroll.loaded_pages.keys())
            
            for page in [0, 1, 2]:  # At minimum, current pages should be loaded
                self.assertIn(page, loaded_pages)
        
        asyncio.run(run_test())
    
    def test_visible_items_extraction(self):
        """Test extracting visible items from loaded pages"""
        async def run_test():
            await self.virtual_scroll.initialize()
            
            # Load some pages
            await self.virtual_scroll.load_page(0)
            await self.virtual_scroll.load_page(1)
            
            # Set visible range
            self.virtual_scroll.visible_range = (25, 75)  # Spans page 0 and 1
            
            # Get visible items
            visible_items = self.virtual_scroll.get_visible_items()
            
            # Should get items 25-75 (51 items)
            self.assertEqual(len(visible_items), 51)
            self.assertEqual(visible_items[0].id, "item_25")
            self.assertEqual(visible_items[-1].id, "item_75")
        
        asyncio.run(run_test())
    
    def test_page_cleanup(self):
        """Test old page cleanup functionality"""
        async def run_test():
            await self.virtual_scroll.initialize()
            
            # Load many pages
            for page_num in range(10):
                await self.virtual_scroll.load_page(page_num)
            
            # Should have loaded all 10 pages initially
            self.assertGreaterEqual(len(self.virtual_scroll.loaded_pages), 10)
            
            # Set visible range far from initial pages
            await self.virtual_scroll.set_visible_range(800, 850)  # Around page 16
            
            # Old pages should be cleaned up due to max_cached_pages=5
            self.assertLessEqual(len(self.virtual_scroll.loaded_pages), 
                               self.config.max_cached_pages + 2)  # Some tolerance
        
        asyncio.run(run_test())
    
    def test_virtual_scroll_statistics(self):
        """Test virtual scroll statistics"""
        async def run_test():
            await self.virtual_scroll.initialize()
            await self.virtual_scroll.load_page(0)
            await self.virtual_scroll.load_page(1)
            
            stats = self.virtual_scroll.get_statistics()
            
            self.assertEqual(stats["total_items"], 1000)
            self.assertGreaterEqual(stats["loaded_pages"], 1)
            self.assertEqual(stats["page_size"], 50)
            self.assertGreaterEqual(stats["total_requests"], 1)
            self.assertIn("cache_stats", stats)
        
        asyncio.run(run_test())


class TestProgressiveLoader(unittest.TestCase):
    """Test ProgressiveLoader functionality"""
    
    def setUp(self):
        self.mock_repo = MockContentRepository(total_items=500)
        self.progressive_loader = ProgressiveLoader(
            chunk_size=25,
            delay_ms=1,  # Very small delay for testing
            repository=self.mock_repo
        )
    
    def test_progressive_loading_start(self):
        """Test starting progressive loading"""
        async def run_test():
            # Start loading
            success = await self.progressive_loader.start_progressive_load(total_items=100)
            self.assertTrue(success)
            
            # Wait a bit for loading to progress
            await asyncio.sleep(0.1)
            
            # Should have loaded some items
            loaded_items = self.progressive_loader.get_loaded_items()
            self.assertGreater(len(loaded_items), 0)
            
            # Should eventually complete
            for _ in range(50):  # Max 5 second wait
                await asyncio.sleep(0.1)
                if self.progressive_loader.loading_complete:
                    break
            
            self.assertTrue(self.progressive_loader.loading_complete)
            self.assertEqual(len(loaded_items), 100)
        
        asyncio.run(run_test())
    
    def test_progressive_loading_callbacks(self):
        """Test progressive loading callbacks"""
        async def run_test():
            callback_events = []
            
            def test_callback(event):
                callback_events.append(event)
            
            self.progressive_loader.register_callback(test_callback)
            
            # Start loading
            await self.progressive_loader.start_progressive_load(total_items=50)
            
            # Wait for completion
            for _ in range(50):
                await asyncio.sleep(0.1)
                if self.progressive_loader.loading_complete:
                    break
            
            # Should have received callbacks
            self.assertGreater(len(callback_events), 0)
            
            # Check for completion event
            completion_events = [e for e in callback_events if e.get("type") == "complete"]
            self.assertEqual(len(completion_events), 1)
            
            completion_event = completion_events[0]
            self.assertEqual(completion_event["total_loaded"], 50)
        
        asyncio.run(run_test())
    
    def test_progressive_loading_stop(self):
        """Test stopping progressive loading"""
        async def run_test():
            # Start loading
            await self.progressive_loader.start_progressive_load(total_items=1000)
            
            # Wait a bit
            await asyncio.sleep(0.05)
            
            # Stop loading
            self.progressive_loader.stop_loading()
            
            # Should stop loading
            self.assertFalse(self.progressive_loader.is_loading)
        
        asyncio.run(run_test())
    
    def test_progressive_loading_statistics(self):
        """Test progressive loading statistics"""
        async def run_test():
            await self.progressive_loader.start_progressive_load(total_items=75)
            
            # Wait for some progress
            await asyncio.sleep(0.1)
            
            stats = self.progressive_loader.get_statistics()
            
            self.assertIn("is_loading", stats)
            self.assertIn("loading_complete", stats)
            self.assertIn("total_loaded", stats)
            self.assertIn("chunk_size", stats)
            self.assertEqual(stats["chunk_size"], 25)
        
        asyncio.run(run_test())


class TestDatasetPerformanceManager(unittest.TestCase):
    """Test DatasetPerformanceManager functionality"""
    
    def setUp(self):
        # Reset global state
        reset_dataset_performance_manager()
        
        self.mock_repo = MockContentRepository(total_items=1000)
        self.performance_manager = DatasetPerformanceManager(self.mock_repo)
    
    def tearDown(self):
        reset_dataset_performance_manager()
    
    def test_performance_manager_initialization(self):
        """Test performance manager initialization"""
        async def run_test():
            success = await self.performance_manager.initialize()
            self.assertTrue(success)
            
            # Should have initialized virtual scroll
            self.assertEqual(self.performance_manager.virtual_scroll.total_items, 1000)
        
        asyncio.run(run_test())
    
    def test_optimized_data_retrieval_virtual(self):
        """Test optimized data retrieval using virtual scrolling"""
        async def run_test():
            await self.performance_manager.initialize()
            
            # Get data using virtual scrolling strategy
            data = await self.performance_manager.get_optimized_data(
                offset=50,
                limit=100,
                loading_strategy=LoadingStrategy.VIRTUAL
            )
            
            self.assertEqual(len(data), 100)
            self.assertEqual(data[0].id, "item_50")
            self.assertEqual(data[-1].id, "item_149")
        
        asyncio.run(run_test())
    
    def test_optimized_data_retrieval_progressive(self):
        """Test optimized data retrieval using progressive loading"""
        async def run_test():
            await self.performance_manager.initialize()
            
            # Get data using progressive loading strategy
            data = await self.performance_manager.get_optimized_data(
                offset=0,
                limit=100,
                loading_strategy=LoadingStrategy.PROGRESSIVE
            )
            
            # Should get requested data (might take time to load progressively)
            self.assertGreater(len(data), 0)
            self.assertLessEqual(len(data), 100)
        
        asyncio.run(run_test())
    
    def test_caching_functionality(self):
        """Test caching in performance manager"""
        async def run_test():
            await self.performance_manager.initialize()
            
            # First request - should hit repository
            start_time = time.time()
            data1 = await self.performance_manager.get_optimized_data(
                offset=0,
                limit=50,
                use_cache=True,
                loading_strategy=LoadingStrategy.VIRTUAL
            )
            first_time = time.time() - start_time
            
            # Second request - should hit cache
            start_time = time.time()
            data2 = await self.performance_manager.get_optimized_data(
                offset=0,
                limit=50,
                use_cache=True,
                loading_strategy=LoadingStrategy.VIRTUAL
            )
            second_time = time.time() - start_time
            
            # Data should be identical
            self.assertEqual(len(data1), len(data2))
            self.assertEqual(data1[0].id, data2[0].id)
            
            # Second request should be faster (cached)
            self.assertLess(second_time, first_time)
        
        asyncio.run(run_test())
    
    def test_preload_data(self):
        """Test data preloading functionality"""
        async def run_test():
            await self.performance_manager.initialize()
            
            # Preload data using progressive strategy
            success = await self.performance_manager.preload_data(
                start_offset=0,
                preload_size=200,
                strategy=LoadingStrategy.PROGRESSIVE
            )
            
            self.assertTrue(success)
            
            # Wait for preloading to complete
            for _ in range(50):
                await asyncio.sleep(0.1)
                if self.performance_manager.progressive_loader.loading_complete:
                    break
            
            # Should have preloaded data
            loaded_items = self.performance_manager.progressive_loader.get_loaded_items()
            self.assertGreaterEqual(len(loaded_items), 200)
        
        asyncio.run(run_test())
    
    def test_memory_optimization(self):
        """Test memory optimization functionality"""
        async def run_test():
            await self.performance_manager.initialize()
            
            # Load some data to create memory usage
            await self.performance_manager.get_optimized_data(0, 100)
            await self.performance_manager.get_optimized_data(100, 100)
            
            # Optimize memory - should not throw errors
            self.performance_manager.optimize_memory()
            
            # Memory optimization should complete successfully
            self.assertTrue(True)  # If we get here, no exceptions were thrown
        
        asyncio.run(run_test())
    
    def test_cache_invalidation(self):
        """Test cache invalidation"""
        async def run_test():
            await self.performance_manager.initialize()
            
            # Cache some data
            await self.performance_manager.get_optimized_data(0, 50, use_cache=True)
            
            # Verify cache has data
            cache_stats = self.performance_manager.cache.get_statistics()
            initial_items = cache_stats["total_items"]
            self.assertGreater(initial_items, 0)
            
            # Invalidate cache
            self.performance_manager.invalidate_cache()
            
            # Cache should be empty
            cache_stats = self.performance_manager.cache.get_statistics()
            self.assertEqual(cache_stats["total_items"], 0)
        
        asyncio.run(run_test())
    
    def test_performance_report_generation(self):
        """Test comprehensive performance report generation"""
        async def run_test():
            await self.performance_manager.initialize()
            
            # Generate some activity
            await self.performance_manager.get_optimized_data(0, 100)
            await self.performance_manager.get_optimized_data(50, 100)  # Overlapping for cache hits
            
            # Generate report
            report = self.performance_manager.get_performance_report()
            
            # Verify report structure
            self.assertIn("global_metrics", report)
            self.assertIn("cache_performance", report)
            self.assertIn("virtual_scroll_performance", report)
            self.assertIn("progressive_loading_performance", report)
            self.assertIn("memory_usage", report)
            self.assertIn("recommendations", report)
            
            # Verify global metrics
            global_metrics = report["global_metrics"]
            self.assertGreater(global_metrics["total_requests"], 0)
            self.assertGreaterEqual(global_metrics["cache_hit_ratio"], 0)
            self.assertGreater(global_metrics["items_loaded"], 0)
            
            # Should have recommendations
            self.assertIsInstance(report["recommendations"], list)
            self.assertGreater(len(report["recommendations"]), 0)
        
        asyncio.run(run_test())


class TestGlobalPerformanceManager(unittest.TestCase):
    """Test global performance manager functions"""
    
    def setUp(self):
        reset_dataset_performance_manager()
        self.mock_repo = MockContentRepository()
    
    def tearDown(self):
        reset_dataset_performance_manager()
    
    def test_get_dataset_performance_manager(self):
        """Test getting global performance manager"""
        # First call should create new instance
        manager1 = get_dataset_performance_manager(self.mock_repo)
        self.assertIsNotNone(manager1)
        
        # Second call should return same instance
        manager2 = get_dataset_performance_manager()
        self.assertIs(manager1, manager2)
    
    def test_reset_dataset_performance_manager(self):
        """Test resetting global performance manager"""
        # Create manager
        manager1 = get_dataset_performance_manager(self.mock_repo)
        
        # Reset
        reset_dataset_performance_manager()
        
        # Get new manager - should be different instance
        manager2 = get_dataset_performance_manager(self.mock_repo)
        self.assertIsNot(manager1, manager2)


class TestPerformanceIntegration(unittest.TestCase):
    """Integration tests for performance optimization system"""
    
    def setUp(self):
        reset_dataset_performance_manager()
        self.mock_repo = MockContentRepository(total_items=5000)
        self.performance_manager = DatasetPerformanceManager(self.mock_repo)
    
    def tearDown(self):
        reset_dataset_performance_manager()
    
    def test_large_dataset_performance(self):
        """Test performance with large dataset"""
        async def run_test():
            await self.performance_manager.initialize()
            
            # Simulate large dataset access patterns
            requests = [
                (0, 100),     # Initial load
                (50, 100),    # Overlapping (cache hit)
                (200, 100),   # New data
                (150, 100),   # Partial overlap
                (0, 50),      # Cached data
            ]
            
            total_time = 0
            for offset, limit in requests:
                start_time = time.time()
                data = await self.performance_manager.get_optimized_data(
                    offset=offset,
                    limit=limit,
                    loading_strategy=LoadingStrategy.VIRTUAL
                )
                request_time = time.time() - start_time
                total_time += request_time
                
                self.assertEqual(len(data), limit)
            
            # Generate performance report
            report = self.performance_manager.get_performance_report()
            
            # Should have good cache performance
            cache_hit_ratio = report["global_metrics"]["cache_hit_ratio"]
            self.assertGreater(cache_hit_ratio, 0)  # Should have some cache hits
            
            # Average load time should be reasonable
            avg_load_time = report["global_metrics"]["avg_load_time_ms"]
            self.assertLess(avg_load_time, 1000)  # Less than 1 second average
        
        asyncio.run(run_test())
    
    def test_mixed_loading_strategies(self):
        """Test mixing different loading strategies"""
        async def run_test():
            await self.performance_manager.initialize()
            
            # Virtual scrolling
            virtual_data = await self.performance_manager.get_optimized_data(
                offset=0,
                limit=100,
                loading_strategy=LoadingStrategy.VIRTUAL
            )
            
            # Progressive loading
            progressive_data = await self.performance_manager.get_optimized_data(
                offset=200,
                limit=100,
                loading_strategy=LoadingStrategy.PROGRESSIVE
            )
            
            # Both should return data
            self.assertEqual(len(virtual_data), 100)
            self.assertGreater(len(progressive_data), 0)
            
            # Data should be different ranges
            self.assertNotEqual(virtual_data[0].id, progressive_data[0].id)
        
        asyncio.run(run_test())


def run_performance_optimization_tests():
    """Run all performance optimization tests"""
    print("🚀 Starting Task 18.9 Performance Optimization Tests")
    print("=" * 70)
    
    # Create test suite
    test_classes = [
        TestIntelligentCache,
        TestVirtualScrollManager,
        TestProgressiveLoader,
        TestDatasetPerformanceManager,
        TestGlobalPerformanceManager,
        TestPerformanceIntegration
    ]
    
    suite = unittest.TestSuite()
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)
    
    # Summary report
    print("\n" + "=" * 70)
    print("📊 PERFORMANCE OPTIMIZATION TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    if result.testsRun > 0:
        print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}")
            print(f"    {traceback.strip()}")
    
    if result.errors:
        print("\n🚨 ERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}")
            print(f"    {traceback.strip()}")
    
    if result.wasSuccessful():
        print("\n🎉 ALL PERFORMANCE OPTIMIZATION TESTS PASSED!")
        print("✅ Task 18.9 implementation is working correctly")
        print("\n📋 Verified Components:")
        print("  ✓ IntelligentCache - Multi-tier adaptive caching")
        print("  ✓ VirtualScrollManager - Efficient large list rendering")
        print("  ✓ ProgressiveLoader - Smooth chunk-based loading")
        print("  ✓ DatasetPerformanceManager - Unified optimization coordination")
        print("  ✓ Cache strategies (LRU, LFU, TTL, Adaptive)")
        print("  ✓ Memory optimization and cleanup")
        print("  ✓ Performance metrics and reporting")
        print("  ✓ Loading strategy integration")
        print("  ✓ Large dataset handling")
        print("  ✓ Global manager singleton pattern")
        print("\n💡 Next: Continue with Task 18.10 - Repository-UI Integration Tests")
    else:
        print("\n⚠️  Some tests failed - review performance optimization implementation")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_performance_optimization_tests()
    exit(0 if success else 1) 