#!/usr/bin/env python3
"""
Adapter Framework Error Handling Integration Test
================================================

This script demonstrates the integration of the enhanced error handling system
with the actual adapter framework, testing real-world error scenarios and
recovery mechanisms.
"""

import sys
import os
import time
import json
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.abspath('.'))

from scripts_dev.performance.error_handling_enhancer import (
    ErrorRecoveryOrchestrator, CircuitBreakerConfig, ErrorContext,
    ErrorType, ErrorSeverity, with_error_handling
)


class MockAdapterComponent:
    """Mock adapter component for testing error handling integration"""
    
    def __init__(self, name: str, failure_rate: float = 0.3):
        self.name = name
        self.failure_rate = failure_rate
        self.call_count = 0
        self.success_count = 0
        
    def process_data(self, data: dict):
        """Simulate data processing with potential failures"""
        self.call_count += 1
        
        import random
        if random.random() < self.failure_rate:
            if self.call_count % 4 == 0:
                raise ConnectionError(f"Network timeout in {self.name}")
            elif self.call_count % 3 == 0:
                raise ValueError(f"Invalid data format in {self.name}")
            else:
                raise RuntimeError(f"Processing error in {self.name}")
        
        self.success_count += 1
        return f"Processed by {self.name}: {data['id']}"
    
    def get_stats(self):
        """Get component statistics"""
        success_rate = self.success_count / self.call_count if self.call_count > 0 else 0
        return {
            'name': self.name,
            'total_calls': self.call_count,
            'successful_calls': self.success_count,
            'success_rate': success_rate,
            'failure_rate': self.failure_rate
        }


class AdapterErrorHandlingIntegration:
    """Integration test for adapter error handling"""
    
    def __init__(self):
        self.orchestrator = ErrorRecoveryOrchestrator()
        self.components = {}
        self.test_results = {}
        self.setup_error_handling()
    
    def setup_error_handling(self):
        """Setup error handling configuration for adapters"""
        # Configure circuit breakers for different adapter components
        adapter_configs = {
            'main_window_adapter': CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=10.0,
                half_open_max_calls=2
            ),
            'video_info_adapter': CircuitBreakerConfig(
                failure_threshold=2,
                recovery_timeout=15.0,
                half_open_max_calls=1
            ),
            'downloads_adapter': CircuitBreakerConfig(
                failure_threshold=4,
                recovery_timeout=20.0,
                half_open_max_calls=3
            )
        }
        
        for component_name, config in adapter_configs.items():
            self.orchestrator.register_circuit_breaker(component_name, config)
        
        # Register degradation strategies
        self.setup_degradation_strategies()
        
        # Register recovery chains
        self.setup_recovery_chains()
    
    def setup_degradation_strategies(self):
        """Setup graceful degradation strategies for each adapter"""
        
        def main_window_degradation(error_context: ErrorContext):
            return {
                'mode': 'readonly',
                'message': 'Main window in read-only mode due to system issues',
                'available_features': ['view_downloads', 'basic_info']
            }
        
        def video_info_degradation(error_context: ErrorContext):
            return {
                'mode': 'cached_data',
                'message': 'Showing cached video information',
                'data_freshness': 'stale'
            }
        
        def downloads_degradation(error_context: ErrorContext):
            return {
                'mode': 'queue_only',
                'message': 'Download queue available, processing paused',
                'queue_size': 10
            }
        
        degradation_strategies = {
            'main_window_adapter': main_window_degradation,
            'video_info_adapter': video_info_degradation,
            'downloads_adapter': downloads_degradation
        }
        
        for component, strategy in degradation_strategies.items():
            self.orchestrator.degradation_manager.register_strategy(
                component, strategy, priority=1
            )
    
    def setup_recovery_chains(self):
        """Setup recovery chains for complex error scenarios"""
        
        def reset_component_state(error_context: ErrorContext):
            """Recovery step: Reset component state"""
            component_name = error_context.component
            if component_name in self.components:
                # Reset failure rate to simulate recovery
                self.components[component_name].failure_rate *= 0.5
                return f"Reset state for {component_name}"
            return None
        
        def reinitialize_component(error_context: ErrorContext):
            """Recovery step: Reinitialize component"""
            component_name = error_context.component
            if component_name in self.components:
                # Simulate reinitialization
                self.components[component_name].call_count = 0
                self.components[component_name].success_count = 0
                return f"Reinitialized {component_name}"
            return None
        
        def fallback_to_basic_mode(error_context: ErrorContext):
            """Recovery step: Fallback to basic mode"""
            return f"Activated basic mode for {error_context.component}"
        
        # Register recovery chains
        recovery_chain = [reset_component_state, reinitialize_component, fallback_to_basic_mode]
        
        for component in ['main_window_adapter', 'video_info_adapter', 'downloads_adapter']:
            self.orchestrator.register_recovery_chain(component, recovery_chain)
    
    def create_test_components(self):
        """Create test adapter components"""
        self.components = {
            'main_window_adapter': MockAdapterComponent('MainWindowAdapter', 0.4),
            'video_info_adapter': MockAdapterComponent('VideoInfoAdapter', 0.3),
            'downloads_adapter': MockAdapterComponent('DownloadsAdapter', 0.2)
        }
    
    @with_error_handling(component="main_window_adapter", operation="process_video_data")
    def process_main_window_data(self, data: dict):
        """Process data through main window adapter with error handling"""
        return self.components['main_window_adapter'].process_data(data)
    
    @with_error_handling(component="video_info_adapter", operation="fetch_video_info")
    def fetch_video_info(self, data: dict):
        """Fetch video info with error handling"""
        return self.components['video_info_adapter'].process_data(data)
    
    @with_error_handling(component="downloads_adapter", operation="manage_download")
    def manage_download(self, data: dict):
        """Manage download with error handling"""
        return self.components['downloads_adapter'].process_data(data)
    
    def run_integration_test(self, num_iterations: int = 50):
        """Run comprehensive integration test"""
        print("=== Adapter Error Handling Integration Test ===\n")
        
        self.create_test_components()
        
        # Override the default orchestrator for decorated methods
        import scripts_dev.performance.error_handling_enhancer as ehe
        ehe._default_orchestrator = self.orchestrator
        
        start_time = time.time()
        test_data = [{'id': f'test_{i}', 'url': f'https://example.com/video_{i}'} 
                    for i in range(num_iterations)]
        
        results = {
            'main_window_adapter': {'success': 0, 'error': 0, 'degraded': 0},
            'video_info_adapter': {'success': 0, 'error': 0, 'degraded': 0},
            'downloads_adapter': {'success': 0, 'error': 0, 'degraded': 0}
        }
        
        # Test each adapter component
        for i, data in enumerate(test_data):
            print(f"Processing iteration {i+1}/{num_iterations}", end='\r')
            
            # Test main window adapter
            try:
                result = self.process_main_window_data(data)
                if isinstance(result, dict) and 'mode' in result:
                    results['main_window_adapter']['degraded'] += 1
                else:
                    results['main_window_adapter']['success'] += 1
            except Exception:
                results['main_window_adapter']['error'] += 1
            
            # Test video info adapter  
            try:
                result = self.fetch_video_info(data)
                if isinstance(result, dict) and 'mode' in result:
                    results['video_info_adapter']['degraded'] += 1
                else:
                    results['video_info_adapter']['success'] += 1
            except Exception:
                results['video_info_adapter']['error'] += 1
            
            # Test downloads adapter
            try:
                result = self.manage_download(data)
                if isinstance(result, dict) and 'mode' in result:
                    results['downloads_adapter']['degraded'] += 1
                else:
                    results['downloads_adapter']['success'] += 1
            except Exception:
                results['downloads_adapter']['error'] += 1
        
        test_duration = time.time() - start_time
        print(f"\nTest completed in {test_duration:.2f} seconds")
        
        return self.analyze_results(results, test_duration, num_iterations)
    
    def analyze_results(self, results: dict, test_duration: float, num_iterations: int):
        """Analyze and report test results"""
        
        print("\n=== Integration Test Results ===")
        
        total_operations = num_iterations * len(results)
        total_success = sum(r['success'] for r in results.values())
        total_degraded = sum(r['degraded'] for r in results.values())
        total_errors = sum(r['error'] for r in results.values())
        
        print(f"Total operations: {total_operations}")
        print(f"Successful operations: {total_success} ({total_success/total_operations*100:.1f}%)")
        print(f"Degraded operations: {total_degraded} ({total_degraded/total_operations*100:.1f}%)")
        print(f"Failed operations: {total_errors} ({total_errors/total_operations*100:.1f}%)")
        print(f"Effective recovery rate: {(total_success + total_degraded)/total_operations*100:.1f}%")
        
        print("\n=== Component-wise Results ===")
        for component, stats in results.items():
            total_component_ops = sum(stats.values())
            success_rate = stats['success'] / total_component_ops * 100 if total_component_ops > 0 else 0
            degradation_rate = stats['degraded'] / total_component_ops * 100 if total_component_ops > 0 else 0
            error_rate = stats['error'] / total_component_ops * 100 if total_component_ops > 0 else 0
            
            print(f"\n{component}:")
            print(f"  Success: {stats['success']} ({success_rate:.1f}%)")
            print(f"  Degraded: {stats['degraded']} ({degradation_rate:.1f}%)")
            print(f"  Errors: {stats['error']} ({error_rate:.1f}%)")
            
            # Show component mock stats
            if component in self.components:
                mock_stats = self.components[component].get_stats()
                print(f"  Mock stats: {mock_stats['success_rate']:.1f}% success rate from {mock_stats['total_calls']} calls")
        
        # Get system health report
        health_report = self.orchestrator.get_system_health()
        print(f"\n=== System Health ===")
        print(f"Health Score: {health_report['health_score']:.1f}/100")
        print(f"Active Errors: {health_report['active_errors']}")
        print(f"Total Errors Handled: {health_report['total_errors']}")
        
        if health_report['recommendations']:
            print(f"\nRecommendations:")
            for rec in health_report['recommendations']:
                print(f"  - {rec}")
        
        # Circuit breaker status
        print(f"\n=== Circuit Breaker Status ===")
        for name, cb_info in health_report['circuit_breakers'].items():
            print(f"{name}: {cb_info['state']} (failures: {cb_info['failure_count']})")
        
        # Performance metrics
        ops_per_second = total_operations / test_duration
        print(f"\n=== Performance Metrics ===")
        print(f"Operations per second: {ops_per_second:.1f}")
        print(f"Average operation time: {test_duration/total_operations*1000:.2f}ms")
        
        return {
            'total_operations': total_operations,
            'success_rate': total_success / total_operations,
            'degradation_rate': total_degraded / total_operations,
            'error_rate': total_errors / total_operations,
            'effective_recovery_rate': (total_success + total_degraded) / total_operations,
            'health_score': health_report['health_score'],
            'ops_per_second': ops_per_second,
            'test_duration': test_duration,
            'component_results': results,
            'health_report': health_report
        }
    
    def save_results(self, results: dict, filename: str = None):
        """Save test results to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scripts_dev/performance_results/adapter_error_handling_integration_{timestamp}.json"
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\nResults saved to: {filename}")
        return filename


def main():
    """Run the adapter error handling integration test"""
    integration_test = AdapterErrorHandlingIntegration()
    results = integration_test.run_integration_test(num_iterations=30)
    
    # Save results
    results_file = integration_test.save_results(results)
    
    # Summary
    print(f"\n{'='*60}")
    print("ADAPTER ERROR HANDLING INTEGRATION TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Effective Recovery Rate: {results['effective_recovery_rate']*100:.1f}%")
    print(f"System Health Score: {results['health_score']:.1f}/100")
    print(f"Performance: {results['ops_per_second']:.1f} ops/sec")
    print(f"Results saved to: {results_file}")
    
    return results


if __name__ == "__main__":
    main() 