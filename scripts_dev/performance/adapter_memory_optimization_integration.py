#!/usr/bin/env python3
"""
Adapter Framework Memory Optimization Integration Test
=====================================================

This script tests memory optimization effectiveness within the adapter framework,
simulating real-world usage patterns and measuring optimization results.
"""

import gc
import json
import logging
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

from scripts_dev.performance.memory_management_optimizer import (
    MemoryOptimizationOrchestrator, MemoryOptimizationConfig,
    memory_optimization_context
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class AdapterSimulationConfig:
    """Configuration for adapter simulation"""
    num_video_items: int = 500
    num_concurrent_adapters: int = 4
    adapter_operations_per_cycle: int = 100
    memory_stress_cycles: int = 3
    cache_test_items: int = 200
    large_object_size_mb: float = 5.0


class MockVideoAdapter:
    """Mock video adapter component for memory testing"""
    
    def __init__(self, adapter_id: str):
        self.adapter_id = adapter_id
        self.video_cache = {}
        self.metadata_cache = {}
        self.download_history = []
        self.event_listeners = []
        self.processed_count = 0
        
    def process_video_data(self, video_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate video data processing"""
        self.processed_count += 1
        
        # Simulate memory allocation
        processed_data = {
            'id': video_data['id'],
            'title': video_data.get('title', 'Unknown'),
            'processed_at': datetime.now(),
            'adapter_id': self.adapter_id,
            'metadata': {
                'duration': video_data.get('duration', 0),
                'size': video_data.get('size', 0),
                'thumbnails': [f"thumb_{i}.jpg" for i in range(10)],
                'chapters': [f"Chapter {i}" for i in range(20)]
            },
            'processing_result': {
                'status': 'success',
                'extracted_info': {f"info_{i}": f"value_{i}" for i in range(50)},
                'temp_data': [i for i in range(100)]  # Temporary data that should be cleaned
            }
        }
        
        # Store in caches (potential memory leak source)
        self.video_cache[video_data['id']] = processed_data
        self.metadata_cache[video_data['id']] = processed_data['metadata']
        
        # Add to history (another potential memory growth point)
        self.download_history.append({
            'video_id': video_data['id'],
            'timestamp': datetime.now(),
            'size': video_data.get('size', 0)
        })
        
        return processed_data
    
    def add_event_listener(self, listener_func):
        """Add event listener (potential memory leak if not cleaned)"""
        self.event_listeners.append(listener_func)
    
    def clear_caches(self):
        """Clear caches to free memory"""
        self.video_cache.clear()
        self.metadata_cache.clear()
        # Keep only recent history
        if len(self.download_history) > 100:
            self.download_history = self.download_history[-50:]
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get adapter memory usage stats"""
        return {
            'adapter_id': self.adapter_id,
            'processed_count': self.processed_count,
            'video_cache_size': len(self.video_cache),
            'metadata_cache_size': len(self.metadata_cache),
            'history_size': len(self.download_history),
            'event_listeners': len(self.event_listeners)
        }


class VideoDataWrapper:
    """Wrapper for video data that can be weakly referenced"""
    def __init__(self, video_data: Dict[str, Any]):
        self.data = video_data
        self.id = video_data['id']
        self.created_at = datetime.now()
    
    def get_data(self) -> Dict[str, Any]:
        return self.data

    def __repr__(self):
        return f"VideoDataWrapper(id={self.id})"


class AdapterMemoryOptimizationTester:
    """Integration tester for adapter memory optimization"""
    
    def __init__(self, config: AdapterSimulationConfig = None):
        self.config = config or AdapterSimulationConfig()
        self.adapters = []
        self.test_results = {}
        self.large_objects = []  # For memory stress testing
        
        # Memory optimization config
        self.memory_config = MemoryOptimizationConfig(
            max_cache_size_mb=75.0,
            memory_warning_threshold=70.0,
            memory_critical_threshold=85.0,
            snapshot_interval=2,  # Faster for testing
            gc_threshold_0=500,  # More aggressive GC
            gc_threshold_1=8,
            gc_threshold_2=8
        )
    
    def setup_adapters(self):
        """Setup mock adapter components"""
        logger.info(f"Setting up {self.config.num_concurrent_adapters} mock adapters")
        
        for i in range(self.config.num_concurrent_adapters):
            adapter = MockVideoAdapter(f"adapter_{i}")
            self.adapters.append(adapter)
        
        logger.info(f"Created {len(self.adapters)} adapter instances")
    
    def generate_test_video_data(self) -> List[Dict[str, Any]]:
        """Generate test video data"""
        video_data = []
        for i in range(self.config.num_video_items):
            video_data.append({
                'id': f'video_{i}',
                'title': f'Test Video {i}',
                'url': f'https://example.com/video_{i}',
                'duration': 120 + (i % 300),
                'size': 1024 * 1024 * (5 + (i % 20))  # 5-25MB
            })
        return video_data
    
    def create_memory_stress_objects(self):
        """Create large objects to stress memory"""
        logger.info("Creating memory stress objects")
        
        for i in range(int(self.config.large_object_size_mb)):
            # Create 1MB objects
            large_object = [j for j in range(262144)]  # ~1MB of integers
            self.large_objects.append(large_object)
        
        logger.info(f"Created {len(self.large_objects)} large objects (~{self.config.large_object_size_mb}MB)")
    
    def simulate_adapter_workload(self, orchestrator: MemoryOptimizationOrchestrator) -> Dict[str, Any]:
        """Simulate realistic adapter workload"""
        logger.info("Simulating adapter workload")
        
        video_data = self.generate_test_video_data()
        start_time = time.time()
        total_processed = 0
        
        def adapter_worker(adapter: MockVideoAdapter, videos: List[Dict[str, Any]]):
            worker_processed = 0
            for video in videos:
                try:
                    # Create wrapper for weak reference
                    video_wrapper = VideoDataWrapper(video)
                    
                    # Register wrapper object with lifecycle manager
                    orchestrator.lifecycle_manager.register_object(
                        video_wrapper, category=f"adapter_{adapter.adapter_id}"
                    )
                    
                    # Process video
                    result = adapter.process_video_data(video)
                    
                    # Store in orchestrator cache
                    orchestrator.cache.put(f"{adapter.adapter_id}_{video['id']}", result)
                    
                    worker_processed += 1
                    
                    # Simulate some processing delay
                    time.sleep(0.001)
                    
                except Exception as e:
                    logger.error(f"Error processing video {video['id']}: {e}")
            
            return worker_processed
        
        # Distribute videos across adapters
        videos_per_adapter = len(video_data) // len(self.adapters)
        
        with ThreadPoolExecutor(max_workers=len(self.adapters)) as executor:
            futures = []
            for i, adapter in enumerate(self.adapters):
                start_idx = i * videos_per_adapter
                end_idx = start_idx + videos_per_adapter
                adapter_videos = video_data[start_idx:end_idx]
                
                future = executor.submit(adapter_worker, adapter, adapter_videos)
                futures.append(future)
            
            # Collect results
            for future in futures:
                total_processed += future.result()
        
        workload_time = time.time() - start_time
        
        return {
            'total_processed': total_processed,
            'workload_time': workload_time,
            'processing_rate': total_processed / workload_time,
            'adapter_stats': [adapter.get_memory_stats() for adapter in self.adapters]
        }
    
    def run_memory_stress_test(self, orchestrator: MemoryOptimizationOrchestrator) -> Dict[str, Any]:
        """Run memory stress test with optimization cycles"""
        logger.info("Running memory stress test")
        
        stress_results = []
        
        for cycle in range(self.config.memory_stress_cycles):
            logger.info(f"Stress test cycle {cycle + 1}/{self.config.memory_stress_cycles}")
            
            # Take snapshot before stress
            before_snapshot = orchestrator.profiler.take_snapshot()
            
            # Create memory stress
            self.create_memory_stress_objects()
            
            # Simulate heavy adapter usage
            workload_result = self.simulate_adapter_workload(orchestrator)
            
            # Add more stress with cache operations
            for i in range(self.config.cache_test_items):
                large_cache_item = {
                    'id': f'large_item_{i}',
                    'data': [j for j in range(10000)],  # ~40KB
                    'metadata': {f'meta_{j}': f'value_{j}' for j in range(100)}
                }
                orchestrator.cache.put(f'stress_cache_{i}', large_cache_item)
            
            # Take snapshot after stress
            after_stress_snapshot = orchestrator.profiler.take_snapshot()
            
            # Run optimization cycle
            optimization_result = orchestrator.run_memory_optimization_cycle()
            
            # Take snapshot after optimization
            after_optimization_snapshot = orchestrator.profiler.take_snapshot()
            
            # Clear stress objects
            self.large_objects.clear()
            
            # Clean adapter caches
            for adapter in self.adapters:
                adapter.clear_caches()
            
            # Cleanup lifecycle manager
            for adapter in self.adapters:
                orchestrator.lifecycle_manager.cleanup_category(f"adapter_{adapter.adapter_id}")
            
            cycle_result = {
                'cycle': cycle + 1,
                'memory_before_stress_mb': before_snapshot.rss_mb,
                'memory_after_stress_mb': after_stress_snapshot.rss_mb,
                'memory_after_optimization_mb': after_optimization_snapshot.rss_mb,
                'stress_memory_increase_mb': after_stress_snapshot.rss_mb - before_snapshot.rss_mb,
                'optimization_memory_saved_mb': after_stress_snapshot.rss_mb - after_optimization_snapshot.rss_mb,
                'workload_result': workload_result,
                'optimization_result': optimization_result
            }
            
            stress_results.append(cycle_result)
            
            logger.info(f"Cycle {cycle + 1}: Stress +{cycle_result['stress_memory_increase_mb']:.1f}MB, "
                       f"Optimization -{cycle_result['optimization_memory_saved_mb']:.1f}MB")
            
            # Wait a bit between cycles
            time.sleep(2)
        
        return {
            'stress_cycles': stress_results,
            'total_stress_memory_mb': sum(r['stress_memory_increase_mb'] for r in stress_results),
            'total_optimization_saved_mb': sum(r['optimization_memory_saved_mb'] for r in stress_results),
            'average_optimization_effectiveness': sum(
                r['optimization_memory_saved_mb'] / max(r['stress_memory_increase_mb'], 1) 
                for r in stress_results
            ) / len(stress_results)
        }
    
    def run_comprehensive_memory_test(self) -> Dict[str, Any]:
        """Run comprehensive memory optimization test"""
        logger.info("Starting comprehensive adapter memory optimization test")
        
        self.setup_adapters()
        
        with memory_optimization_context(self.memory_config) as orchestrator:
            # Initial memory state
            initial_snapshot = orchestrator.profiler.take_snapshot()
            logger.info(f"Initial memory: {initial_snapshot.rss_mb:.1f}MB ({initial_snapshot.percent:.1f}%)")
            
            # Run stress test with optimization
            stress_test_results = self.run_memory_stress_test(orchestrator)
            
            # Wait for profiling data
            time.sleep(5)
            
            # Final memory state
            final_snapshot = orchestrator.profiler.take_snapshot()
            
            # Get comprehensive report
            comprehensive_report = orchestrator.get_comprehensive_report()
            
            # Calculate overall results
            overall_results = {
                'test_duration': (final_snapshot.timestamp - initial_snapshot.timestamp).total_seconds(),
                'initial_memory_mb': initial_snapshot.rss_mb,
                'final_memory_mb': final_snapshot.rss_mb,
                'net_memory_change_mb': final_snapshot.rss_mb - initial_snapshot.rss_mb,
                'peak_memory_usage_mb': max(
                    snapshot.rss_mb for snapshot in orchestrator.profiler.snapshots
                ),
                'stress_test_results': stress_test_results,
                'comprehensive_report': comprehensive_report,
                'adapter_final_stats': [adapter.get_memory_stats() for adapter in self.adapters]
            }
            
            return overall_results
    
    def analyze_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze test results and generate insights"""
        
        analysis = {
            'memory_efficiency': {
                'net_memory_change_mb': results['net_memory_change_mb'],
                'peak_memory_usage_mb': results['peak_memory_usage_mb'],
                'optimization_effectiveness': results['stress_test_results']['average_optimization_effectiveness'],
                'total_memory_saved_mb': results['stress_test_results']['total_optimization_saved_mb']
            },
            'performance_metrics': {
                'test_duration': results['test_duration'],
                'optimization_cycles': len(results['comprehensive_report']['recent_optimizations']),
                'average_optimization_time': results['comprehensive_report']['average_optimization_time'],
                'cache_utilization': results['comprehensive_report']['cache_performance']['utilization_percent']
            },
            'adapter_performance': {
                'total_adapters': len(results['adapter_final_stats']),
                'total_processed_items': sum(
                    adapter['processed_count'] for adapter in results['adapter_final_stats']
                ),
                'average_cache_size': sum(
                    adapter['video_cache_size'] for adapter in results['adapter_final_stats']
                ) / len(results['adapter_final_stats'])
            },
            'optimization_insights': [],
            'recommendations': []
        }
        
        # Generate insights
        if results['net_memory_change_mb'] < 0:
            analysis['optimization_insights'].append(
                f"Net memory reduction of {abs(results['net_memory_change_mb']):.1f}MB achieved"
            )
        else:
            analysis['optimization_insights'].append(
                f"Net memory increase of {results['net_memory_change_mb']:.1f}MB - investigate memory leaks"
            )
        
        effectiveness = results['stress_test_results']['average_optimization_effectiveness']
        if effectiveness > 0.8:
            analysis['optimization_insights'].append("Excellent optimization effectiveness (>80%)")
        elif effectiveness > 0.5:
            analysis['optimization_insights'].append("Good optimization effectiveness (50-80%)")
        else:
            analysis['optimization_insights'].append("Poor optimization effectiveness (<50%)")
        
        # Generate recommendations
        if analysis['performance_metrics']['cache_utilization'] > 80:
            analysis['recommendations'].append("Consider increasing cache size or improving eviction policies")
        
        if analysis['performance_metrics']['average_optimization_time'] > 1.0:
            analysis['recommendations'].append("Optimization cycles taking too long - consider tuning GC settings")
        
        if analysis['adapter_performance']['average_cache_size'] > 200:
            analysis['recommendations'].append("Adapter caches growing large - implement more aggressive cleanup")
        
        return analysis
    
    def save_results(self, results: Dict[str, Any], filename: str = None) -> str:
        """Save test results to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scripts_dev/performance_results/adapter_memory_optimization_{timestamp}.json"
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Results saved to: {filename}")
        return filename


def main():
    """Run adapter memory optimization integration test"""
    print("=== Adapter Memory Optimization Integration Test ===\n")
    
    # Configure test
    config = AdapterSimulationConfig(
        num_video_items=300,
        num_concurrent_adapters=3,
        memory_stress_cycles=2,
        cache_test_items=150,
        large_object_size_mb=10.0
    )
    
    # Run test
    tester = AdapterMemoryOptimizationTester(config)
    results = tester.run_comprehensive_memory_test()
    
    # Analyze results
    analysis = tester.analyze_results(results)
    
    # Save results
    results_with_analysis = {**results, 'analysis': analysis}
    results_file = tester.save_results(results_with_analysis)
    
    # Display summary
    print(f"\n{'='*60}")
    print("ADAPTER MEMORY OPTIMIZATION TEST SUMMARY")
    print(f"{'='*60}")
    
    memory_efficiency = analysis['memory_efficiency']
    performance_metrics = analysis['performance_metrics']
    
    print(f"Net Memory Change: {memory_efficiency['net_memory_change_mb']:+.1f}MB")
    print(f"Peak Memory Usage: {memory_efficiency['peak_memory_usage_mb']:.1f}MB")
    print(f"Total Memory Saved: {memory_efficiency['total_memory_saved_mb']:.1f}MB")
    print(f"Optimization Effectiveness: {memory_efficiency['optimization_effectiveness']*100:.1f}%")
    
    print(f"\nPerformance Metrics:")
    print(f"  Test Duration: {performance_metrics['test_duration']:.1f}s")
    print(f"  Optimization Cycles: {performance_metrics['optimization_cycles']}")
    print(f"  Average Optimization Time: {performance_metrics['average_optimization_time']:.2f}s")
    print(f"  Cache Utilization: {performance_metrics['cache_utilization']:.1f}%")
    
    print(f"\nAdapter Performance:")
    adapter_perf = analysis['adapter_performance']
    print(f"  Adapters Tested: {adapter_perf['total_adapters']}")
    print(f"  Items Processed: {adapter_perf['total_processed_items']}")
    print(f"  Average Cache Size: {adapter_perf['average_cache_size']:.0f} items")
    
    print(f"\nOptimization Insights:")
    for insight in analysis['optimization_insights']:
        print(f"  - {insight}")
    
    if analysis['recommendations']:
        print(f"\nRecommendations:")
        for rec in analysis['recommendations']:
            print(f"  - {rec}")
    
    print(f"\nResults saved to: {results_file}")
    
    return results_with_analysis


if __name__ == "__main__":
    main() 