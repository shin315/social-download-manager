#!/usr/bin/env python3
"""
TikTok Performance Test Suite

This module provides performance benchmarking and load testing for TikTok handler.
"""

import asyncio
import logging
import sys
import time
import gc
import psutil
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

# Add the project root to sys.path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from platforms.tiktok import TikTokHandler
from platforms.base import QualityLevel

# Set up logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class PerformanceResult:
    """Performance test result"""
    test_name: str
    duration: float
    memory_used: float
    cpu_percent: float
    operations_per_second: float
    success_rate: float
    error_count: int


class PerformanceMonitor:
    """Monitor system performance during tests"""
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.start_memory = 0
        self.start_cpu_time = 0
        self.start_time = 0
    
    def start(self):
        """Start monitoring"""
        gc.collect()  # Clean up before starting
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.start_cpu_time = self.process.cpu_times().user
        self.start_time = time.time()
    
    def get_metrics(self) -> Dict[str, float]:
        """Get current performance metrics"""
        current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        current_cpu_time = self.process.cpu_times().user
        current_time = time.time()
        
        memory_used = current_memory - self.start_memory
        cpu_percent = self.process.cpu_percent()
        duration = current_time - self.start_time
        
        return {
            'memory_used': memory_used,
            'cpu_percent': cpu_percent,
            'duration': duration
        }


def test_handler_initialization_performance():
    """Test TikTok handler initialization performance"""
    
    print("🚀 Testing Handler Initialization Performance")
    print("=" * 45)
    
    monitor = PerformanceMonitor()
    monitor.start()
    
    initialization_count = 100
    start_time = time.time()
    errors = 0
    
    for i in range(initialization_count):
        try:
            handler = TikTokHandler()
            # Force initialization of internal components
            _ = handler.get_capabilities()
            del handler  # Clean up
        except Exception as e:
            errors += 1
            if errors == 1:  # Only print first error
                print(f"   Error during initialization: {e}")
    
    end_time = time.time()
    metrics = monitor.get_metrics()
    
    duration = end_time - start_time
    ops_per_second = initialization_count / duration
    success_rate = ((initialization_count - errors) / initialization_count) * 100
    
    print(f"   Initializations: {initialization_count}")
    print(f"   Duration: {duration:.3f}s")
    print(f"   Operations/sec: {ops_per_second:.1f}")
    print(f"   Memory used: {metrics['memory_used']:.1f} MB")
    print(f"   Success rate: {success_rate:.1f}%")
    
    # Performance thresholds
    acceptable_ops_per_sec = 50  # Should be able to init 50+ handlers per second
    acceptable_memory_mb = 100   # Should use less than 100MB
    
    performance_ok = (
        ops_per_second >= acceptable_ops_per_sec and
        metrics['memory_used'] <= acceptable_memory_mb and
        success_rate >= 95.0
    )
    
    status = "✅" if performance_ok else "❌"
    print(f"   {status} Performance acceptable: {performance_ok}")
    
    return PerformanceResult(
        test_name="Handler Initialization",
        duration=duration,
        memory_used=metrics['memory_used'],
        cpu_percent=metrics['cpu_percent'],
        operations_per_second=ops_per_second,
        success_rate=success_rate,
        error_count=errors
    )


def test_url_validation_performance():
    """Test URL validation performance with large batches"""
    
    print("\n🔗 Testing URL Validation Performance")
    print("=" * 38)
    
    handler = TikTokHandler()
    monitor = PerformanceMonitor()
    monitor.start()
    
    # Create test URLs
    test_urls = [
        "https://www.tiktok.com/@user/video/1234567890",
        "https://vm.tiktok.com/ZMxxxxxx/",
        "https://youtube.com/watch?v=abc123",  # Invalid
        "https://www.tiktok.com/@user/photo/123",  # Invalid
        "https://tiktok.com/@user.name_123/video/9876543210",
        "",  # Invalid
        "https://vt.tiktok.com/ZSxxxxxx/",
        "not_a_url",  # Invalid
        "https://www.tiktok.com/t/ZTxxxxxx/",
        "https://instagram.com/p/abc123/"  # Invalid
    ]
    
    # Multiply to create larger test set
    batch_size = 1000
    url_batch = (test_urls * (batch_size // len(test_urls) + 1))[:batch_size]
    
    start_time = time.time()
    valid_count = 0
    errors = 0
    
    for url in url_batch:
        try:
            if handler.is_valid_url(url):
                valid_count += 1
        except Exception as e:
            errors += 1
    
    end_time = time.time()
    metrics = monitor.get_metrics()
    
    duration = end_time - start_time
    ops_per_second = batch_size / duration
    success_rate = ((batch_size - errors) / batch_size) * 100
    
    print(f"   URL validations: {batch_size}")
    print(f"   Valid URLs: {valid_count}")
    print(f"   Duration: {duration:.3f}s")
    print(f"   Operations/sec: {ops_per_second:.1f}")
    print(f"   Memory used: {metrics['memory_used']:.1f} MB")
    print(f"   Success rate: {success_rate:.1f}%")
    
    # Performance thresholds
    acceptable_ops_per_sec = 1000  # Should validate 1000+ URLs per second
    acceptable_memory_mb = 50      # Should use less than 50MB
    
    performance_ok = (
        ops_per_second >= acceptable_ops_per_sec and
        metrics['memory_used'] <= acceptable_memory_mb and
        success_rate >= 95.0
    )
    
    status = "✅" if performance_ok else "❌"
    print(f"   {status} Performance acceptable: {performance_ok}")
    
    return PerformanceResult(
        test_name="URL Validation",
        duration=duration,
        memory_used=metrics['memory_used'],
        cpu_percent=metrics['cpu_percent'],
        operations_per_second=ops_per_second,
        success_rate=success_rate,
        error_count=errors
    )


async def test_concurrent_handler_operations():
    """Test concurrent handler operations"""
    
    print("\n🔄 Testing Concurrent Handler Operations")
    print("=" * 40)
    
    monitor = PerformanceMonitor()
    monitor.start()
    
    concurrent_handlers = 10
    operations_per_handler = 20
    
    async def handler_workload(handler_id: int):
        """Workload for each handler"""
        handler = TikTokHandler()
        errors = 0
        
        test_urls = [
            "https://www.tiktok.com/@user/video/1234567890",
            "https://vm.tiktok.com/ZMxxxxxx/",
            "https://vt.tiktok.com/ZSxxxxxx/",
            "https://www.tiktok.com/t/ZTxxxxxx/"
        ]
        
        for i in range(operations_per_handler):
            try:
                # Mix of operations
                url = test_urls[i % len(test_urls)]
                handler.is_valid_url(url)
                handler.get_capabilities()
                handler.get_session_info()
                
                # Simulate some async work
                await asyncio.sleep(0.001)
                
            except Exception as e:
                errors += 1
        
        return handler_id, errors
    
    start_time = time.time()
    
    # Run concurrent handlers
    tasks = [handler_workload(i) for i in range(concurrent_handlers)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    end_time = time.time()
    metrics = monitor.get_metrics()
    
    # Analyze results
    total_operations = concurrent_handlers * operations_per_handler * 3  # 3 ops per iteration
    total_errors = sum(r[1] if isinstance(r, tuple) else 1 for r in results)
    exception_count = sum(1 for r in results if isinstance(r, Exception))
    
    duration = end_time - start_time
    ops_per_second = total_operations / duration
    success_rate = ((total_operations - total_errors) / total_operations) * 100
    
    print(f"   Concurrent handlers: {concurrent_handlers}")
    print(f"   Operations per handler: {operations_per_handler}")
    print(f"   Total operations: {total_operations}")
    print(f"   Duration: {duration:.3f}s")
    print(f"   Operations/sec: {ops_per_second:.1f}")
    print(f"   Memory used: {metrics['memory_used']:.1f} MB")
    print(f"   Success rate: {success_rate:.1f}%")
    print(f"   Exceptions: {exception_count}")
    
    # Performance thresholds
    acceptable_ops_per_sec = 100  # Should handle 100+ concurrent ops per second
    acceptable_memory_mb = 200    # Should use less than 200MB for concurrent ops
    
    performance_ok = (
        ops_per_second >= acceptable_ops_per_sec and
        metrics['memory_used'] <= acceptable_memory_mb and
        success_rate >= 90.0 and
        exception_count == 0
    )
    
    status = "✅" if performance_ok else "❌"
    print(f"   {status} Performance acceptable: {performance_ok}")
    
    return PerformanceResult(
        test_name="Concurrent Operations",
        duration=duration,
        memory_used=metrics['memory_used'],
        cpu_percent=metrics['cpu_percent'],
        operations_per_second=ops_per_second,
        success_rate=success_rate,
        error_count=total_errors + exception_count
    )


def test_memory_usage_over_time():
    """Test memory usage over extended operations"""
    
    print("\n💾 Testing Memory Usage Over Time")
    print("=" * 35)
    
    monitor = PerformanceMonitor()
    monitor.start()
    
    handler = TikTokHandler()
    operations_count = 500
    memory_samples = []
    
    start_time = time.time()
    
    for i in range(operations_count):
        try:
            # Perform various operations
            handler.is_valid_url(f"https://www.tiktok.com/@user/video/{i}")
            handler.get_capabilities()
            handler.get_session_info()
            
            # Sample memory every 50 operations
            if i % 50 == 0:
                current_memory = monitor.process.memory_info().rss / 1024 / 1024
                memory_samples.append(current_memory)
                
            # Simulate session state changes
            if i % 100 == 0:
                handler.clear_session()
                
        except Exception as e:
            print(f"   Error at operation {i}: {e}")
    
    end_time = time.time()
    final_metrics = monitor.get_metrics()
    
    duration = end_time - start_time
    ops_per_second = operations_count / duration
    
    # Analyze memory trends
    memory_growth = memory_samples[-1] - memory_samples[0] if len(memory_samples) > 1 else 0
    max_memory = max(memory_samples) if memory_samples else 0
    avg_memory = sum(memory_samples) / len(memory_samples) if memory_samples else 0
    
    print(f"   Operations: {operations_count}")
    print(f"   Duration: {duration:.3f}s")
    print(f"   Operations/sec: {ops_per_second:.1f}")
    print(f"   Memory growth: {memory_growth:.1f} MB")
    print(f"   Max memory: {max_memory:.1f} MB")
    print(f"   Avg memory: {avg_memory:.1f} MB")
    print(f"   Final memory used: {final_metrics['memory_used']:.1f} MB")
    
    # Performance thresholds
    acceptable_memory_growth = 50   # Should not grow more than 50MB
    acceptable_max_memory = 200     # Should not exceed 200MB peak
    
    performance_ok = (
        memory_growth <= acceptable_memory_growth and
        max_memory <= acceptable_max_memory and
        ops_per_second >= 50
    )
    
    status = "✅" if performance_ok else "❌"
    print(f"   {status} Performance acceptable: {performance_ok}")
    
    return PerformanceResult(
        test_name="Memory Usage Over Time",
        duration=duration,
        memory_used=final_metrics['memory_used'],
        cpu_percent=final_metrics['cpu_percent'],
        operations_per_second=ops_per_second,
        success_rate=100.0,  # No error tracking in this test
        error_count=0
    )


async def test_performance_benchmarks():
    """Run all performance benchmark tests"""
    
    print("⚡ TikTok Handler Performance Benchmarks")
    print("=" * 42)
    
    results = []
    
    # Run performance tests
    try:
        # Test 1: Handler Initialization
        result1 = test_handler_initialization_performance()
        results.append(result1)
        
        # Test 2: URL Validation
        result2 = test_url_validation_performance()
        results.append(result2)
        
        # Test 3: Concurrent Operations
        result3 = await test_concurrent_handler_operations()
        results.append(result3)
        
        # Test 4: Memory Usage
        result4 = test_memory_usage_over_time()
        results.append(result4)
        
    except Exception as e:
        print(f"❌ Performance benchmark failed: {e}")
        return False
    
    # Performance summary
    print(f"\n📊 Performance Summary")
    print("=" * 23)
    
    acceptable_results = 0
    total_tests = len(results)
    
    for result in results:
        # Determine if result is acceptable based on basic criteria
        is_acceptable = (
            result.success_rate >= 90.0 and
            result.memory_used <= 200.0 and
            result.error_count <= (result.operations_per_second * 0.05)  # 5% error tolerance
        )
        
        status = "✅" if is_acceptable else "❌"
        print(f"   {status} {result.test_name}:")
        print(f"      Duration: {result.duration:.3f}s")
        print(f"      Ops/sec: {result.operations_per_second:.1f}")
        print(f"      Memory: {result.memory_used:.1f} MB")
        print(f"      Success: {result.success_rate:.1f}%")
        print(f"      Errors: {result.error_count}")
        
        if is_acceptable:
            acceptable_results += 1
    
    overall_success = acceptable_results == total_tests
    
    print(f"\n🎯 Overall Performance: {acceptable_results}/{total_tests} tests acceptable")
    
    if overall_success:
        print("✅ All performance benchmarks passed!")
        print("TikTok handler performance is within acceptable limits.")
    else:
        print("⚠️ Some performance tests did not meet benchmarks.")
        print("Consider optimization for production use.")
    
    return overall_success


async def test_load_conditions():
    """Test handler behavior under load conditions"""
    
    print("\n🏋️ Testing Load Conditions")
    print("=" * 27)
    
    monitor = PerformanceMonitor()
    monitor.start()
    
    print("   Simulating high load scenario...")
    
    # Create multiple handlers for load testing
    handler_count = 20
    handlers = []
    
    start_time = time.time()
    
    try:
        # Create handlers
        for i in range(handler_count):
            handler = TikTokHandler({
                'rate_limit': {'enabled': True, 'min_request_interval': 0.01}
            })
            handlers.append(handler)
        
        # Simulate heavy concurrent usage
        async def heavy_workload(handler, worker_id):
            operations = 50
            errors = 0
            
            for i in range(operations):
                try:
                    # Mix of operations
                    handler.is_valid_url(f"https://www.tiktok.com/@user{worker_id}/video/{i}")
                    handler.get_capabilities()
                    session_info = handler.get_session_info()
                    
                    # Simulate some processing time
                    await asyncio.sleep(0.002)
                    
                    # Occasional session management
                    if i % 25 == 0:
                        handler.clear_session()
                        
                except Exception as e:
                    errors += 1
            
            return worker_id, errors
        
        # Execute heavy workload
        tasks = [heavy_workload(handler, i) for i, handler in enumerate(handlers)]
        workload_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        metrics = monitor.get_metrics()
        
        # Analyze load test results
        total_operations = handler_count * 50 * 3  # 3 operations per iteration
        total_errors = sum(r[1] if isinstance(r, tuple) else 1 for r in workload_results)
        exception_count = sum(1 for r in workload_results if isinstance(r, Exception))
        
        duration = end_time - start_time
        ops_per_second = total_operations / duration
        success_rate = ((total_operations - total_errors) / total_operations) * 100
        
        print(f"   Load test duration: {duration:.3f}s")
        print(f"   Concurrent handlers: {handler_count}")
        print(f"   Total operations: {total_operations}")
        print(f"   Operations/sec: {ops_per_second:.1f}")
        print(f"   Memory used: {metrics['memory_used']:.1f} MB")
        print(f"   CPU usage: {metrics['cpu_percent']:.1f}%")
        print(f"   Success rate: {success_rate:.1f}%")
        print(f"   Total errors: {total_errors}")
        print(f"   Exceptions: {exception_count}")
        
        # Load test criteria
        acceptable_ops_per_sec = 50   # Should handle at least 50 ops/sec under load
        acceptable_memory_mb = 500    # Should use less than 500MB under load
        acceptable_success_rate = 85  # Should maintain 85% success rate under load
        
        load_test_passed = (
            ops_per_second >= acceptable_ops_per_sec and
            metrics['memory_used'] <= acceptable_memory_mb and
            success_rate >= acceptable_success_rate and
            exception_count <= 5  # Allow some exceptions under heavy load
        )
        
        status = "✅" if load_test_passed else "❌"
        print(f"   {status} Load test passed: {load_test_passed}")
        
        return load_test_passed
        
    except Exception as e:
        print(f"   ❌ Load test failed with error: {e}")
        return False
    finally:
        # Clean up handlers
        for handler in handlers:
            try:
                handler.clear_session()
            except:
                pass


def main():
    """Main performance test function"""
    try:
        return asyncio.run(test_performance_benchmarks())
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 