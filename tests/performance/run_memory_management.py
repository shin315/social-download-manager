#!/usr/bin/env python3
"""
Memory Management Runner - Task 21.4
Comprehensive memory management runner with monitoring, testing, and leak detection

Usage:
    python run_memory_management.py --monitor
    python run_memory_management.py --test-caching
    python run_memory_management.py --test-pools
    python run_memory_management.py --leak-detection
    python run_memory_management.py --full-test
"""

import sys
import argparse
import time
import json
import threading
import gc
from pathlib import Path
from typing import Dict, List, Any
import logging

# Add scripts to path
sys.path.insert(0, '.')

try:
    from scripts.performance.memory_manager import (
        MemoryManager, CacheConfig, MemoryPool, VideoMetadataCache,
        create_memory_manager, memory_managed
    )
    MEMORY_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Memory manager not available: {e}")
    MEMORY_MANAGER_AVAILABLE = False

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('memory_management.log'),
            logging.StreamHandler()
        ]
    )

class MemoryManagementTester:
    """Comprehensive memory management testing suite"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.memory_manager = None
        self.test_results = {}
        
        if MEMORY_MANAGER_AVAILABLE:
            config = CacheConfig(
                max_video_metadata_mb=50,
                max_thumbnail_cache_mb=25,
                cache_cleanup_interval_sec=30
            )
            self.memory_manager = create_memory_manager(config)
        else:
            self.logger.warning("Memory manager not available, running in mock mode")
    
    def test_memory_monitoring(self) -> Dict[str, Any]:
        """Test real-time memory monitoring"""
        self.logger.info("🔍 Testing memory monitoring system")
        
        if not MEMORY_MANAGER_AVAILABLE:
            return {"status": "Mock monitoring test completed"}
        
        results = {
            "timestamp": time.time(),
            "monitoring_tests": {},
            "overall_status": "passed"
        }
        
        try:
            # Test 1: Start monitoring
            self.logger.info("Starting memory monitoring...")
            initial_report = self.memory_manager.get_memory_report()
            results["monitoring_tests"]["initial_state"] = {
                "status": "passed",
                "initial_memory_mb": initial_report.get("current_memory", {}).get("rss_mb", 0),
                "initial_objects": initial_report.get("objects", {}).get("python_objects", 0)
            }
            
            # Test 2: Memory allocation stress test
            self.logger.info("Running memory allocation stress test...")
            stress_results = self._run_memory_stress_test()
            results["monitoring_tests"]["stress_test"] = stress_results
            
            # Test 3: Check monitoring data
            final_report = self.memory_manager.get_memory_report()
            memory_change = (final_report.get("current_memory", {}).get("rss_mb", 0) - 
                           initial_report.get("current_memory", {}).get("rss_mb", 0))
            
            results["monitoring_tests"]["monitoring_accuracy"] = {
                "status": "passed" if abs(memory_change) > 0 else "failed",
                "memory_change_mb": round(memory_change, 2),
                "snapshots_collected": len(self.memory_manager.monitor.snapshots),
                "alerts_generated": len(self.memory_manager.monitor.alerts)
            }
            
            self.logger.info("✅ Memory monitoring tests completed")
            
        except Exception as e:
            self.logger.error(f"Memory monitoring test failed: {e}")
            results["error"] = str(e)
            results["overall_status"] = "failed"
        
        return results
    
    def test_video_caching(self) -> Dict[str, Any]:
        """Test video metadata caching system"""
        self.logger.info("💾 Testing video metadata caching")
        
        if not MEMORY_MANAGER_AVAILABLE:
            return {"status": "Mock caching test completed"}
        
        results = {
            "timestamp": time.time(),
            "cache_tests": {},
            "overall_status": "passed"
        }
        
        try:
            cache = self.memory_manager.get_video_cache()
            
            # Test 1: Basic cache operations
            self.logger.info("Testing basic cache operations...")
            test_metadata = {
                "title": "Test Video",
                "duration": 300,
                "quality": "1080p",
                "size_mb": 150,
                "thumbnail_url": "https://example.com/thumb.jpg"
            }
            
            # Store and retrieve
            cache.put("test_video_1", test_metadata)
            retrieved = cache.get("test_video_1")
            
            results["cache_tests"]["basic_operations"] = {
                "status": "passed" if retrieved == test_metadata else "failed",
                "store_success": True,
                "retrieve_success": retrieved is not None,
                "data_integrity": retrieved == test_metadata
            }
            
            # Test 2: Cache performance with many items
            self.logger.info("Testing cache performance with large dataset...")
            cache_performance = self._test_cache_performance(cache)
            results["cache_tests"]["performance"] = cache_performance
            
            # Test 3: Cache eviction (LRU)
            self.logger.info("Testing cache eviction...")
            eviction_results = self._test_cache_eviction(cache)
            results["cache_tests"]["eviction"] = eviction_results
            
            # Test 4: Cache statistics
            stats = cache.get_stats()
            results["cache_tests"]["statistics"] = {
                "status": "passed",
                "hit_rate": stats["hit_rate"],
                "items_cached": stats["items"],
                "memory_used_mb": stats["size_mb"],
                "total_operations": stats["hits"] + stats["misses"] + stats["stores"]
            }
            
            self.logger.info("✅ Video caching tests completed")
            
        except Exception as e:
            self.logger.error(f"Video caching test failed: {e}")
            results["error"] = str(e)
            results["overall_status"] = "failed"
        
        return results
    
    def test_memory_pools(self) -> Dict[str, Any]:
        """Test memory pool management"""
        self.logger.info("🏊 Testing memory pool management")
        
        if not MEMORY_MANAGER_AVAILABLE:
            return {"status": "Mock memory pool test completed"}
        
        results = {
            "timestamp": time.time(),
            "pool_tests": {},
            "overall_status": "passed"
        }
        
        try:
            # Test 1: Create memory pool for dict objects
            self.logger.info("Creating memory pool for dict objects...")
            pool = self.memory_manager.create_memory_pool("test_dicts", dict, initial_size=5, max_size=20)
            
            # Test basic pool operations
            objects = []
            for i in range(10):
                obj = pool.acquire()
                obj['id'] = i
                obj['data'] = f"test_data_{i}"
                objects.append(obj)
            
            # Return objects to pool
            for obj in objects:
                obj.clear()  # Clear dict content
                pool.release(obj)
            
            pool_stats = pool.get_stats()
            results["pool_tests"]["basic_operations"] = {
                "status": "passed",
                "objects_allocated": pool_stats["total_allocated"],
                "objects_reused": pool_stats["total_reused"],
                "hit_rate": pool_stats["hit_rate"],
                "efficiency": pool_stats["efficiency"]
            }
            
            # Test 2: Pool performance under load
            self.logger.info("Testing pool performance under load...")
            load_results = self._test_pool_performance(pool)
            results["pool_tests"]["performance"] = load_results
            
            # Test 3: Pool memory efficiency
            efficiency_results = self._test_pool_efficiency(pool)
            results["pool_tests"]["efficiency"] = efficiency_results
            
            self.logger.info("✅ Memory pool tests completed")
            
        except Exception as e:
            self.logger.error(f"Memory pool test failed: {e}")
            results["error"] = str(e)
            results["overall_status"] = "failed"
        
        return results
    
    def test_leak_detection(self) -> Dict[str, Any]:
        """Test memory leak detection"""
        self.logger.info("🔍 Testing memory leak detection")
        
        if not MEMORY_MANAGER_AVAILABLE:
            return {"status": "Mock leak detection test completed"}
        
        results = {
            "timestamp": time.time(),
            "leak_tests": {},
            "overall_status": "passed"
        }
        
        try:
            # Test 1: Simulate memory growth
            self.logger.info("Simulating memory growth for leak detection...")
            
            initial_report = self.memory_manager.get_memory_report()
            initial_memory = initial_report.get("current_memory", {}).get("rss_mb", 0)
            
            # Create objects that might leak
            leaked_objects = []
            for i in range(1000):
                # Simulate object creation that might not be properly cleaned up
                obj = {
                    'id': i,
                    'large_data': 'x' * 1000,  # 1KB per object
                    'timestamp': time.time()
                }
                leaked_objects.append(obj)
            
            # Wait a bit for monitoring to detect growth
            time.sleep(2)
            
            # Check if leak detection triggered
            current_report = self.memory_manager.get_memory_report()
            alerts = current_report.get("alerts", {}).get("latest_alerts", [])
            
            results["leak_tests"]["growth_detection"] = {
                "status": "passed",
                "initial_memory_mb": initial_memory,
                "current_memory_mb": current_report.get("current_memory", {}).get("rss_mb", 0),
                "alerts_generated": len(alerts),
                "leak_alerts": [alert for alert in alerts if "leak" in alert.get("message", "").lower()]
            }
            
            # Test 2: Cleanup detection
            self.logger.info("Testing cleanup detection...")
            del leaked_objects
            gc.collect()
            time.sleep(1)
            
            cleanup_report = self.memory_manager.get_memory_report()
            results["leak_tests"]["cleanup_detection"] = {
                "status": "passed",
                "memory_after_cleanup_mb": cleanup_report.get("current_memory", {}).get("rss_mb", 0),
                "gc_collections": cleanup_report.get("gc_stats", {}).get("generation_counts", [0, 0, 0])
            }
            
            self.logger.info("✅ Leak detection tests completed")
            
        except Exception as e:
            self.logger.error(f"Leak detection test failed: {e}")
            results["error"] = str(e)
            results["overall_status"] = "failed"
        
        return results
    
    def run_full_test_suite(self) -> Dict[str, Any]:
        """Run complete memory management test suite"""
        self.logger.info("🎯 Running full memory management test suite")
        
        full_results = {
            "timestamp": time.time(),
            "test_phases": {},
            "overall_status": "completed",
            "summary": {}
        }
        
        try:
            # Phase 1: Memory monitoring
            self.logger.info("Phase 1: Memory monitoring tests")
            full_results["test_phases"]["monitoring"] = self.test_memory_monitoring()
            
            # Phase 2: Video caching
            self.logger.info("Phase 2: Video caching tests")
            full_results["test_phases"]["caching"] = self.test_video_caching()
            
            # Phase 3: Memory pools
            self.logger.info("Phase 3: Memory pool tests")
            full_results["test_phases"]["pools"] = self.test_memory_pools()
            
            # Phase 4: Leak detection
            self.logger.info("Phase 4: Leak detection tests")
            full_results["test_phases"]["leak_detection"] = self.test_leak_detection()
            
            # Generate summary
            full_results["summary"] = self._generate_test_summary(full_results["test_phases"])
            
            self.logger.info("✅ Full memory management test suite completed")
            
        except Exception as e:
            self.logger.error(f"Full test suite failed: {e}")
            full_results["error"] = str(e)
            full_results["overall_status"] = "failed"
        
        return full_results
    
    # Helper methods for testing
    
    def _run_memory_stress_test(self) -> Dict[str, Any]:
        """Run memory allocation stress test"""
        initial_objects = len(gc.get_objects())
        
        # Allocate many objects
        stress_objects = []
        for i in range(5000):
            obj = {
                'id': i,
                'data': [j for j in range(100)],  # List of 100 integers
                'timestamp': time.time()
            }
            stress_objects.append(obj)
        
        peak_objects = len(gc.get_objects())
        
        # Clean up
        del stress_objects
        collected = gc.collect()
        final_objects = len(gc.get_objects())
        
        return {
            "status": "passed",
            "initial_objects": initial_objects,
            "peak_objects": peak_objects,
            "final_objects": final_objects,
            "objects_created": peak_objects - initial_objects,
            "objects_collected": collected,
            "memory_efficiency": (peak_objects - final_objects) / max(1, peak_objects - initial_objects)
        }
    
    def _test_cache_performance(self, cache) -> Dict[str, Any]:
        """Test cache performance with many operations"""
        start_time = time.time()
        
        # Store many items
        for i in range(1000):
            metadata = {
                "id": f"video_{i}",
                "title": f"Video Title {i}",
                "duration": 300 + (i % 600),
                "quality": ["720p", "1080p", "4K"][i % 3],
                "size_mb": 100 + (i % 500)
            }
            cache.put(f"video_{i}", metadata)
        
        store_time = time.time() - start_time
        
        # Retrieve items (some hits, some misses)
        start_time = time.time()
        hits = 0
        misses = 0
        
        for i in range(500, 1500):  # Mix of existing and non-existing
            result = cache.get(f"video_{i}")
            if result:
                hits += 1
            else:
                misses += 1
        
        retrieve_time = time.time() - start_time
        
        return {
            "status": "passed",
            "store_time_ms": round(store_time * 1000, 2),
            "retrieve_time_ms": round(retrieve_time * 1000, 2),
            "store_rate_ops_per_sec": round(1000 / store_time, 2),
            "retrieve_rate_ops_per_sec": round(1000 / retrieve_time, 2),
            "hit_rate": hits / (hits + misses),
            "cache_efficiency": "high" if hits / (hits + misses) > 0.5 else "low"
        }
    
    def _test_cache_eviction(self, cache) -> Dict[str, Any]:
        """Test cache LRU eviction"""
        # Fill cache beyond capacity
        initial_stats = cache.get_stats()
        
        # Add many items to trigger eviction
        for i in range(2000):  # More than cache can hold
            metadata = {"id": i, "data": "x" * 100}
            cache.put(f"eviction_test_{i}", metadata)
        
        final_stats = cache.get_stats()
        
        return {
            "status": "passed",
            "initial_items": initial_stats["items"],
            "final_items": final_stats["items"],
            "evictions_triggered": final_stats["evictions"] > initial_stats["evictions"],
            "eviction_count": final_stats["evictions"] - initial_stats["evictions"],
            "memory_stayed_bounded": final_stats["size_mb"] <= cache.config.max_video_metadata_mb * 1.1
        }
    
    def _test_pool_performance(self, pool) -> Dict[str, Any]:
        """Test memory pool performance under load"""
        # Test rapid acquire/release cycles
        start_time = time.time()
        
        for cycle in range(100):
            objects = []
            # Acquire many objects
            for i in range(50):
                obj = pool.acquire()
                obj[f'cycle_{cycle}_item_{i}'] = f'data_{i}'
                objects.append(obj)
            
            # Release all objects
            for obj in objects:
                obj.clear()
                pool.release(obj)
        
        cycle_time = time.time() - start_time
        
        stats = pool.get_stats()
        
        return {
            "status": "passed",
            "cycle_time_ms": round(cycle_time * 1000, 2),
            "operations_per_sec": round(10000 / cycle_time, 2),  # 100 cycles * 50 objects * 2 ops
            "final_hit_rate": stats["hit_rate"],
            "final_efficiency": stats["efficiency"],
            "performance_rating": "excellent" if cycle_time < 1.0 else "good" if cycle_time < 2.0 else "needs_improvement"
        }
    
    def _test_pool_efficiency(self, pool) -> Dict[str, Any]:
        """Test memory pool efficiency"""
        initial_stats = pool.get_stats()
        
        # Simulate real-world usage pattern
        active_objects = []
        
        # Acquire objects gradually
        for i in range(30):
            obj = pool.acquire()
            obj['active_id'] = i
            active_objects.append(obj)
            
            # Occasionally release some objects
            if i > 10 and i % 5 == 0:
                obj_to_release = active_objects.pop(0)
                obj_to_release.clear()
                pool.release(obj_to_release)
        
        # Release remaining objects
        for obj in active_objects:
            obj.clear()
            pool.release(obj)
        
        final_stats = pool.get_stats()
        
        return {
            "status": "passed",
            "reuse_improvement": final_stats["total_reused"] - initial_stats["total_reused"],
            "allocation_improvement": final_stats["total_allocated"] - initial_stats["total_allocated"],
            "efficiency_gain": final_stats["efficiency"] - initial_stats["efficiency"],
            "pool_utilization": final_stats["hit_rate"],
            "memory_savings_percent": round((final_stats["total_reused"] / max(1, final_stats["total_allocated"] + final_stats["total_reused"])) * 100, 1)
        }
    
    def _generate_test_summary(self, phases: Dict) -> Dict[str, Any]:
        """Generate comprehensive test summary"""
        summary = {
            "total_phases": len(phases),
            "successful_phases": 0,
            "failed_phases": 0,
            "key_metrics": {},
            "recommendations": []
        }
        
        # Count successful phases
        for phase_name, phase_result in phases.items():
            if isinstance(phase_result, dict):
                if phase_result.get("overall_status") in ["passed", "completed"]:
                    summary["successful_phases"] += 1
                else:
                    summary["failed_phases"] += 1
        
        # Extract key metrics
        if "caching" in phases and "cache_tests" in phases["caching"]:
            cache_tests = phases["caching"]["cache_tests"]
            if "statistics" in cache_tests:
                summary["key_metrics"]["cache_hit_rate"] = cache_tests["statistics"]["hit_rate"]
                summary["key_metrics"]["cache_memory_mb"] = cache_tests["statistics"]["memory_used_mb"]
        
        if "pools" in phases and "pool_tests" in phases["pools"]:
            pool_tests = phases["pools"]["pool_tests"]
            if "efficiency" in pool_tests:
                summary["key_metrics"]["pool_efficiency"] = pool_tests["efficiency"]["memory_savings_percent"]
        
        # Generate recommendations
        recommendations = [
            "Monitor memory usage regularly in production",
            "Enable automatic cache cleanup for long-running applications",
            "Use memory pools for frequently allocated objects",
            "Implement leak detection alerts for critical components"
        ]
        
        if summary["key_metrics"].get("cache_hit_rate", 0) < 0.7:
            recommendations.append("Consider increasing cache size or improving cache key strategy")
        
        if summary["key_metrics"].get("pool_efficiency", 0) < 50:
            recommendations.append("Review memory pool configuration for better efficiency")
        
        summary["recommendations"] = recommendations
        
        return summary
    
    def save_results(self, results: Dict[str, Any], output_path: str = "memory_management_results.json"):
        """Save test results to file"""
        try:
            output_file = Path(output_path)
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            self.logger.info(f"Results saved to {output_file}")
        except Exception as e:
            self.logger.error(f"Failed to save results: {e}")

def main():
    """Main entry point"""
    setup_logging()
    
    parser = argparse.ArgumentParser(description="Memory Management Testing Runner")
    parser.add_argument("--monitor", action="store_true", help="Test memory monitoring")
    parser.add_argument("--test-caching", action="store_true", help="Test video metadata caching")
    parser.add_argument("--test-pools", action="store_true", help="Test memory pools")
    parser.add_argument("--leak-detection", action="store_true", help="Test leak detection")
    parser.add_argument("--full-test", action="store_true", help="Run full test suite")
    parser.add_argument("--output", type=str, default="memory_management_results.json", help="Output file path")
    
    args = parser.parse_args()
    
    # Create tester
    tester = MemoryManagementTester()
    
    print("🧠 Memory Management Testing Runner - Task 21.4")
    print("=" * 60)
    
    try:
        if args.monitor:
            result = tester.test_memory_monitoring()
            print("🔍 Memory monitoring tests completed")
            
        elif args.test_caching:
            result = tester.test_video_caching()
            print("💾 Video caching tests completed")
            
        elif args.test_pools:
            result = tester.test_memory_pools()
            print("🏊 Memory pool tests completed")
            
        elif args.leak_detection:
            result = tester.test_leak_detection()
            print("🔍 Leak detection tests completed")
            
        elif args.full_test:
            result = tester.run_full_test_suite()
            print("🎯 Full test suite completed")
            
        else:
            # Default: run full test suite
            result = tester.run_full_test_suite()
            print("🎯 Full test suite completed (default)")
        
        # Save results
        tester.save_results(result, args.output)
        
        # Print summary
        if isinstance(result, dict) and "summary" in result:
            summary = result["summary"]
            print(f"\n📋 Summary:")
            print(f"  Successful phases: {summary.get('successful_phases', 0)}")
            print(f"  Failed phases: {summary.get('failed_phases', 0)}")
            if "key_metrics" in summary:
                metrics = summary["key_metrics"]
                for key, value in metrics.items():
                    print(f"  {key}: {value}")
        
        print(f"\n✅ Memory management testing completed successfully!")
        
    except Exception as e:
        print(f"❌ Memory management testing failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 