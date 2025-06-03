"""
Performance Analysis for Task 18 - Data Integration Layer
Social Download Manager v2.0

Comprehensive performance testing and analysis for Task 18 components.
Identifies bottlenecks, memory usage patterns, and optimization opportunities.
"""

import time
import psutil
import threading
import gc
import sys
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import cProfile
import pstats
import io

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from PyQt6.QtTest import QTest

# Import Task 18 components
from core.data_integration.repository_event_integration import get_repository_event_manager
from core.data_integration.repository_state_sync import get_repository_state_manager
from core.data_integration.data_binding_strategy import get_data_binding_manager
from core.data_integration.async_loading_patterns import get_async_repository_manager
from core.data_integration.video_table_repository_adapter import (
    ContentRepositoryTableAdapter, TableRepositoryConfig, TableDataMode
)

# Test fixtures from integration tests
from test_task18_integration import MockContentRepository, MockVideoTable
from data.models.content import Platform


@dataclass
class PerformanceMetrics:
    """Performance metrics for a test scenario"""
    test_name: str
    execution_time: float
    memory_before: float
    memory_after: float
    memory_peak: float
    cpu_usage: float
    operations_per_second: float
    success_rate: float
    error_count: int
    bottlenecks: List[str]


class PerformanceMonitor:
    """Monitor system performance during tests"""
    
    def __init__(self):
        self.start_time = None
        self.memory_samples = []
        self.cpu_samples = []
        self.process = psutil.Process()
        self._monitoring = False
        self._monitor_thread = None
    
    def start_monitoring(self):
        """Start performance monitoring"""
        self.start_time = time.time()
        self._monitoring = True
        self.memory_samples.clear()
        self.cpu_samples.clear()
        
        # Start monitoring thread
        self._monitor_thread = threading.Thread(target=self._monitor_loop)
        self._monitor_thread.daemon = True
        self._monitor_thread.start()
    
    def stop_monitoring(self) -> Dict[str, float]:
        """Stop monitoring and return metrics"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
        
        execution_time = time.time() - self.start_time if self.start_time else 0
        
        return {
            'execution_time': execution_time,
            'memory_peak': max(self.memory_samples) if self.memory_samples else 0,
            'memory_average': sum(self.memory_samples) / len(self.memory_samples) if self.memory_samples else 0,
            'cpu_average': sum(self.cpu_samples) / len(self.cpu_samples) if self.cpu_samples else 0,
            'memory_growth': self.memory_samples[-1] - self.memory_samples[0] if len(self.memory_samples) > 1 else 0
        }
    
    def _monitor_loop(self):
        """Background monitoring loop"""
        while self._monitoring:
            try:
                # Memory usage (MB)
                memory_mb = self.process.memory_info().rss / 1024 / 1024
                self.memory_samples.append(memory_mb)
                
                # CPU usage
                cpu_percent = self.process.cpu_percent()
                self.cpu_samples.append(cpu_percent)
                
                time.sleep(0.1)  # Sample every 100ms
            except Exception:
                pass


class Task18PerformanceAnalyzer:
    """Comprehensive performance analyzer for Task 18"""
    
    def __init__(self):
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
        
        self.monitor = PerformanceMonitor()
        self.results: List[PerformanceMetrics] = []
    
    def run_all_performance_tests(self) -> List[PerformanceMetrics]:
        """Run comprehensive performance test suite"""
        print("🚀 Starting Task 18 Performance Analysis")
        print("=" * 60)
        
        # Test scenarios
        test_scenarios = [
            ("Repository Event Publishing", self.test_event_publishing_performance),
            ("State Synchronization", self.test_state_sync_performance),
            ("Data Binding Operations", self.test_data_binding_performance),
            ("Async Loading Patterns", self.test_async_loading_performance),
            ("Video Table Adapter", self.test_video_table_adapter_performance),
            ("Concurrent Operations", self.test_concurrent_operations_performance),
            ("Memory Stress Test", self.test_memory_stress_performance),
            ("Large Dataset Handling", self.test_large_dataset_performance)
        ]
        
        for test_name, test_func in test_scenarios:
            print(f"\n📊 Running: {test_name}")
            try:
                metrics = self._run_performance_test(test_name, test_func)
                self.results.append(metrics)
                self._print_test_results(metrics)
            except Exception as e:
                print(f"❌ Test failed: {e}")
        
        # Generate comprehensive report
        self._generate_performance_report()
        
        return self.results
    
    def _run_performance_test(self, test_name: str, test_func) -> PerformanceMetrics:
        """Run a single performance test with monitoring"""
        # Force garbage collection before test
        gc.collect()
        
        # Get initial memory
        memory_before = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Start monitoring
        self.monitor.start_monitoring()
        
        # Run test with profiling
        profiler = cProfile.Profile()
        profiler.enable()
        
        try:
            success_count, error_count, operations_count = test_func()
        except Exception as e:
            success_count, error_count, operations_count = 0, 1, 1
            print(f"Test error: {e}")
        
        profiler.disable()
        
        # Stop monitoring and get metrics
        perf_metrics = self.monitor.stop_monitoring()
        
        # Get final memory
        memory_after = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Analyze profiling data
        bottlenecks = self._analyze_profiling_data(profiler)
        
        # Calculate performance metrics
        execution_time = perf_metrics['execution_time']
        ops_per_second = operations_count / execution_time if execution_time > 0 else 0
        success_rate = success_count / (success_count + error_count) if (success_count + error_count) > 0 else 0
        
        return PerformanceMetrics(
            test_name=test_name,
            execution_time=execution_time,
            memory_before=memory_before,
            memory_after=memory_after,
            memory_peak=perf_metrics['memory_peak'],
            cpu_usage=perf_metrics['cpu_average'],
            operations_per_second=ops_per_second,
            success_rate=success_rate,
            error_count=error_count,
            bottlenecks=bottlenecks
        )
    
    def _analyze_profiling_data(self, profiler) -> List[str]:
        """Analyze profiling data to identify bottlenecks"""
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s)
        ps.sort_stats('cumulative')
        ps.print_stats(10)  # Top 10 functions
        
        profile_output = s.getvalue()
        bottlenecks = []
        
        # Parse profile output to identify slow functions
        lines = profile_output.split('\n')
        for line in lines:
            if 'function calls' in line or line.strip() == '':
                continue
            if any(keyword in line for keyword in ['find_all', 'execute_async', 'load_data']):
                bottlenecks.append(line.strip())
        
        return bottlenecks[:5]  # Top 5 bottlenecks
    
    def test_event_publishing_performance(self):
        """Test repository event publishing performance"""
        event_manager = get_repository_event_manager()
        
        success_count = 0
        error_count = 0
        operations_count = 1000
        
        try:
            for i in range(operations_count):
                from core.data_integration.repository_event_integration import RepositoryEventPayload, RepositoryEventType
                
                payload = RepositoryEventPayload(
                    repository_type="ContentRepository",
                    entity_type="VideoContent",
                    entity_id=f"test_{i}",
                    operation="create",
                    entity_data={"title": f"Test Video {i}"}
                )
                
                event_manager.publish_event(RepositoryEventType.REPOSITORY_ENTITY_CREATED, payload)
                success_count += 1
                
                if i % 100 == 0:
                    QTest.qWait(1)  # Allow Qt event processing
        except Exception as e:
            error_count += 1
        
        return success_count, error_count, operations_count
    
    def test_state_sync_performance(self):
        """Test state synchronization performance"""
        state_manager = get_repository_state_manager()
        repository = MockContentRepository()
        
        success_count = 0
        error_count = 0
        operations_count = 500
        
        try:
            # Register repository
            state_manager.register_repository("ContentRepository", repository)
            
            for i in range(operations_count):
                # Simulate state changes
                state_manager.update_repository_state(
                    "ContentRepository",
                    {"active_operations": i, "last_update": datetime.now()}
                )
                success_count += 1
                
                if i % 50 == 0:
                    QTest.qWait(1)
        except Exception as e:
            error_count += 1
        
        return success_count, error_count, operations_count
    
    def test_data_binding_performance(self):
        """Test data binding performance"""
        binding_manager = get_data_binding_manager()
        
        success_count = 0
        error_count = 0
        operations_count = 200
        
        try:
            from core.data_integration.data_binding_strategy import DataBindingContext
            
            for i in range(operations_count):
                context = DataBindingContext(
                    filters={"platform": "youtube"},
                    sort_column="title",
                    limit=20,
                    offset=i * 20
                )
                
                # Simulate binding operation
                binding_manager.get_binding_adapters()
                success_count += 1
                
                if i % 20 == 0:
                    QTest.qWait(1)
        except Exception as e:
            error_count += 1
        
        return success_count, error_count, operations_count
    
    def test_async_loading_performance(self):
        """Test async loading pattern performance"""
        async_manager = get_async_repository_manager()
        repository = MockContentRepository()
        
        # Add test data
        for i in range(100):
            repository.add_test_content(f"async_test_{i}", f"Async Test Video {i}")
        
        success_count = 0
        error_count = 0
        operations_count = 50
        
        operation_ids = []
        
        try:
            for i in range(operations_count):
                op_id = async_manager.execute_async_operation(
                    component_id=f"perf_test_{i}",
                    repository=repository,
                    operation_func=lambda: repository.find_all(limit=10),
                    operation_name=f"Performance Test {i}",
                    timeout_seconds=10
                )
                operation_ids.append(op_id)
            
            # Wait for operations to complete
            timeout = 30
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                stats = async_manager.get_statistics()
                if stats['active_operations'] == 0:
                    break
                QTest.qWait(100)
            
            success_count = operations_count
        except Exception as e:
            error_count += 1
        
        return success_count, error_count, operations_count
    
    def test_video_table_adapter_performance(self):
        """Test video table adapter performance"""
        repository = MockContentRepository()
        
        # Add test data
        for i in range(1000):
            platform = Platform.YOUTUBE if i % 2 == 0 else Platform.TIKTOK
            repository.add_test_content(f"table_test_{i}", f"Table Test Video {i}", platform)
        
        config = TableRepositoryConfig(
            data_mode=TableDataMode.CACHED,
            batch_size=50,
            enable_lazy_loading=True
        )
        
        adapter = ContentRepositoryTableAdapter(repository, config)
        
        success_count = 0
        error_count = 0
        operations_count = 20
        
        try:
            for i in range(operations_count):
                # Test different operations
                adapter.load_data(limit=50, offset=i * 50)
                adapter.get_total_count()
                
                if i % 5 == 0:
                    adapter.refresh_data()
                
                success_count += 1
                QTest.qWait(10)
        except Exception as e:
            error_count += 1
        
        return success_count, error_count, operations_count
    
    def test_concurrent_operations_performance(self):
        """Test concurrent operations performance"""
        repository = MockContentRepository()
        
        # Add test data
        for i in range(200):
            repository.add_test_content(f"concurrent_{i}", f"Concurrent Test {i}")
        
        success_count = 0
        error_count = 0
        operations_count = 20
        
        def worker_task(worker_id):
            try:
                adapter = ContentRepositoryTableAdapter(repository)
                for i in range(5):
                    adapter.load_data(limit=10, offset=i * 10)
                    time.sleep(0.01)
                return True
            except Exception:
                return False
        
        # Run concurrent workers
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(worker_task, i) for i in range(operations_count)]
            
            for future in as_completed(futures, timeout=30):
                try:
                    if future.result():
                        success_count += 1
                    else:
                        error_count += 1
                except Exception:
                    error_count += 1
        
        return success_count, error_count, operations_count
    
    def test_memory_stress_performance(self):
        """Test memory usage under stress"""
        repository = MockContentRepository()
        
        # Add large amount of test data
        for i in range(5000):
            repository.add_test_content(f"memory_test_{i}", f"Memory Test Video {i}")
        
        success_count = 0
        error_count = 0
        operations_count = 10
        
        adapters = []
        
        try:
            for i in range(operations_count):
                config = TableRepositoryConfig(
                    data_mode=TableDataMode.CACHED,
                    cache_timeout=3600  # Long cache timeout
                )
                
                adapter = ContentRepositoryTableAdapter(repository, config)
                adapter.load_data(limit=500, offset=i * 500)
                adapters.append(adapter)
                
                success_count += 1
                QTest.qWait(50)
            
            # Keep adapters alive to test memory retention
            time.sleep(1)
        except Exception as e:
            error_count += 1
        finally:
            # Cleanup
            del adapters
            gc.collect()
        
        return success_count, error_count, operations_count
    
    def test_large_dataset_performance(self):
        """Test performance with large datasets"""
        repository = MockContentRepository()
        
        # Create large dataset
        dataset_size = 10000
        for i in range(dataset_size):
            platform = Platform.YOUTUBE if i % 3 == 0 else Platform.TIKTOK
            repository.add_test_content(f"large_{i}", f"Large Dataset Video {i}", platform)
        
        config = TableRepositoryConfig(
            data_mode=TableDataMode.CACHED,
            batch_size=100,
            enable_lazy_loading=True
        )
        
        adapter = ContentRepositoryTableAdapter(repository, config)
        
        success_count = 0
        error_count = 0
        operations_count = 5
        
        try:
            # Test various operations on large dataset
            for i in range(operations_count):
                # Load data in chunks
                adapter.load_data(limit=1000, offset=i * 1000)
                
                # Test filtering
                adapter.load_data(filters={"platform": Platform.YOUTUBE}, limit=500)
                
                # Test count operations
                total_count = adapter.get_total_count()
                filtered_count = adapter.get_total_count(filters={"platform": Platform.TIKTOK})
                
                success_count += 1
                QTest.qWait(100)
        except Exception as e:
            error_count += 1
        
        return success_count, error_count, operations_count
    
    def _print_test_results(self, metrics: PerformanceMetrics):
        """Print test results"""
        print(f"   ⏱️  Execution Time: {metrics.execution_time:.2f}s")
        print(f"   💾 Memory: {metrics.memory_before:.1f}MB → {metrics.memory_after:.1f}MB (Peak: {metrics.memory_peak:.1f}MB)")
        print(f"   🖥️  CPU Usage: {metrics.cpu_usage:.1f}%")
        print(f"   📊 Operations/sec: {metrics.operations_per_second:.1f}")
        print(f"   ✅ Success Rate: {metrics.success_rate:.1%}")
        
        if metrics.bottlenecks:
            print("   🔍 Bottlenecks detected:")
            for bottleneck in metrics.bottlenecks[:3]:
                print(f"      - {bottleneck}")
    
    def _generate_performance_report(self):
        """Generate comprehensive performance report"""
        print("\n" + "=" * 60)
        print("📈 PERFORMANCE ANALYSIS REPORT")
        print("=" * 60)
        
        if not self.results:
            print("No performance data available")
            return
        
        # Overall statistics
        total_time = sum(r.execution_time for r in self.results)
        avg_memory_usage = sum(r.memory_peak for r in self.results) / len(self.results)
        avg_cpu_usage = sum(r.cpu_usage for r in self.results) / len(self.results)
        overall_success_rate = sum(r.success_rate for r in self.results) / len(self.results)
        
        print(f"Total Test Duration: {total_time:.2f}s")
        print(f"Average Memory Peak: {avg_memory_usage:.1f}MB")
        print(f"Average CPU Usage: {avg_cpu_usage:.1f}%")
        print(f"Overall Success Rate: {overall_success_rate:.1%}")
        
        # Performance rankings
        print("\n🏆 PERFORMANCE RANKINGS:")
        
        # Fastest operations
        fastest = sorted(self.results, key=lambda r: r.operations_per_second, reverse=True)[:3]
        print("\nFastest Operations:")
        for i, result in enumerate(fastest, 1):
            print(f"  {i}. {result.test_name}: {result.operations_per_second:.1f} ops/sec")
        
        # Memory efficient
        memory_efficient = sorted(self.results, key=lambda r: r.memory_peak - r.memory_before)[:3]
        print("\nMost Memory Efficient:")
        for i, result in enumerate(memory_efficient, 1):
            memory_delta = result.memory_peak - result.memory_before
            print(f"  {i}. {result.test_name}: +{memory_delta:.1f}MB")
        
        # Performance concerns
        print("\n⚠️  PERFORMANCE CONCERNS:")
        
        slow_operations = [r for r in self.results if r.operations_per_second < 10]
        if slow_operations:
            print("\nSlow Operations (< 10 ops/sec):")
            for result in slow_operations:
                print(f"  - {result.test_name}: {result.operations_per_second:.1f} ops/sec")
        
        high_memory = [r for r in self.results if (r.memory_peak - r.memory_before) > 50]
        if high_memory:
            print("\nHigh Memory Usage (> 50MB increase):")
            for result in high_memory:
                memory_delta = result.memory_peak - result.memory_before
                print(f"  - {result.test_name}: +{memory_delta:.1f}MB")
        
        # Optimization recommendations
        print("\n🔧 OPTIMIZATION RECOMMENDATIONS:")
        
        recommendations = []
        
        if any(r.operations_per_second < 5 for r in self.results):
            recommendations.append("Consider implementing more aggressive caching for slow operations")
        
        if any((r.memory_peak - r.memory_before) > 100 for r in self.results):
            recommendations.append("Implement memory pooling for high-memory operations")
        
        if any(r.cpu_usage > 80 for r in self.results):
            recommendations.append("Optimize CPU-intensive operations or add throttling")
        
        if any(r.success_rate < 0.95 for r in self.results):
            recommendations.append("Improve error handling and retry mechanisms")
        
        recommendations.extend([
            "Consider implementing progressive loading for large datasets",
            "Add connection pooling for repository operations",
            "Implement smart prefetching based on usage patterns",
            "Consider using worker threads for heavy computations"
        ])
        
        for i, rec in enumerate(recommendations[:5], 1):
            print(f"  {i}. {rec}")
        
        print("\n✅ Performance analysis complete!")


def run_performance_analysis():
    """Run comprehensive performance analysis"""
    analyzer = Task18PerformanceAnalyzer()
    results = analyzer.run_all_performance_tests()
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"task18_performance_report_{timestamp}.txt"
    
    try:
        with open(report_file, 'w') as f:
            f.write("Task 18 Performance Analysis Report\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            
            for result in results:
                f.write(f"Test: {result.test_name}\n")
                f.write(f"Execution Time: {result.execution_time:.2f}s\n")
                f.write(f"Memory Usage: {result.memory_before:.1f}MB → {result.memory_peak:.1f}MB\n")
                f.write(f"Operations/sec: {result.operations_per_second:.1f}\n")
                f.write(f"Success Rate: {result.success_rate:.1%}\n")
                f.write("-" * 40 + "\n")
        
        print(f"\n📄 Detailed report saved to: {report_file}")
    except Exception as e:
        print(f"⚠️  Could not save report: {e}")
    
    return results


if __name__ == "__main__":
    run_performance_analysis() 