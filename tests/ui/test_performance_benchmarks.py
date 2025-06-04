"""
Performance Benchmark Tests for V2.0 UI System

Dedicated performance testing suite that measures and validates performance
metrics for all V2.0 UI components under various load conditions.
"""

import pytest
import time
import gc
import os
import sys
import json
import tempfile
import statistics
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# Add the UI components to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'ui', 'components', 'core'))

from tab_lifecycle_manager import TabLifecycleManager, TabState, TabPriority
from component_bus import ComponentBus, MessageType, Priority
from theme_manager import ThemeManager, ThemeVariant
from app_controller import AppController


@dataclass
class PerformanceMetric:
    """Performance metric data structure"""
    name: str
    value: float
    unit: str
    threshold: float
    passed: bool
    description: str = ""


@dataclass
class BenchmarkResult:
    """Benchmark test result"""
    test_name: str
    metrics: List[PerformanceMetric]
    timestamp: float
    environment: Dict[str, Any]
    passed: bool


class PerformanceBenchmarkSuite:
    """Comprehensive performance benchmark suite"""
    
    def __init__(self):
        self.results: List[BenchmarkResult] = []
        self.baseline_metrics: Dict[str, float] = {
            'tab_creation_time_ms': 5.0,  # 5ms per tab
            'message_processing_time_ms': 0.1,  # 0.1ms per message
            'theme_switch_time_ms': 100.0,  # 100ms for theme switch
            'hibernation_time_ms': 50.0,  # 50ms to hibernate
            'memory_usage_mb_per_tab': 2.0,  # 2MB per tab
            'startup_time_ms': 1000.0,  # 1 second startup
            'shutdown_time_ms': 500.0,  # 500ms shutdown
        }
    
    @pytest.fixture(autouse=True)
    def setup_qt_app(self):
        """Setup QApplication for tests"""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
        yield
        
    @pytest.fixture
    def temp_dir(self):
        """Provide temporary directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    def measure_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0  # psutil not available
    
    def measure_execution_time(self, func, *args, **kwargs) -> Tuple[Any, float]:
        """Measure function execution time"""
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        return result, (end_time - start_time) * 1000  # Convert to milliseconds
    
    def create_performance_metric(self, name: str, value: float, unit: str, 
                                threshold: float, description: str = "") -> PerformanceMetric:
        """Create a performance metric"""
        passed = value <= threshold
        return PerformanceMetric(name, value, unit, threshold, passed, description)
    
    def record_benchmark_result(self, test_name: str, metrics: List[PerformanceMetric]):
        """Record benchmark result"""
        environment = {
            'python_version': sys.version,
            'platform': sys.platform,
            'memory_total_mb': self.measure_memory_usage()
        }
        
        passed = all(metric.passed for metric in metrics)
        result = BenchmarkResult(test_name, metrics, time.time(), environment, passed)
        self.results.append(result)
        
        # Print results
        print(f"\n{test_name} Benchmark Results:")
        for metric in metrics:
            status = "✅ PASS" if metric.passed else "❌ FAIL"
            print(f"  {metric.name}: {metric.value:.3f}{metric.unit} (threshold: {metric.threshold}{metric.unit}) {status}")
    
    def test_tab_lifecycle_performance(self, temp_dir):
        """Benchmark TabLifecycleManager performance"""
        manager = TabLifecycleManager(state_dir=temp_dir)
        metrics = []
        
        try:
            # Test tab creation performance
            tab_ids = []
            creation_times = []
            
            for i in range(100):
                tab_id = f"perf_tab_{i}"
                _, creation_time = self.measure_execution_time(
                    manager.create_tab, tab_id, priority=TabPriority.NORMAL
                )
                creation_times.append(creation_time)
                tab_ids.append(tab_id)
            
            avg_creation_time = statistics.mean(creation_times)
            metrics.append(self.create_performance_metric(
                "tab_creation_avg_time", avg_creation_time, "ms",
                self.baseline_metrics['tab_creation_time_ms'],
                "Average time to create a tab"
            ))
            
            # Test tab activation performance
            activation_times = []
            for tab_id in tab_ids[:50]:  # Test first 50
                _, activation_time = self.measure_execution_time(
                    manager.activate_tab, tab_id
                )
                activation_times.append(activation_time)
            
            avg_activation_time = statistics.mean(activation_times)
            metrics.append(self.create_performance_metric(
                "tab_activation_avg_time", avg_activation_time, "ms",
                self.baseline_metrics['tab_creation_time_ms'],
                "Average time to activate a tab"
            ))
            
            # Test hibernation performance
            hibernation_times = []
            for tab_id in tab_ids[:20]:  # Test first 20
                _, hibernation_time = self.measure_execution_time(
                    manager.hibernate_tab, tab_id
                )
                hibernation_times.append(hibernation_time)
            
            avg_hibernation_time = statistics.mean(hibernation_times)
            metrics.append(self.create_performance_metric(
                "tab_hibernation_avg_time", avg_hibernation_time, "ms",
                self.baseline_metrics['hibernation_time_ms'],
                "Average time to hibernate a tab"
            ))
            
            # Test memory usage
            initial_memory = self.measure_memory_usage()
            
            # Create more tabs to test memory scaling
            for i in range(100, 200):
                tab_id = f"memory_tab_{i}"
                manager.create_tab(tab_id)
                manager.activate_tab(tab_id)
            
            final_memory = self.measure_memory_usage()
            memory_per_tab = (final_memory - initial_memory) / 100
            
            metrics.append(self.create_performance_metric(
                "memory_usage_per_tab", memory_per_tab, "MB",
                self.baseline_metrics['memory_usage_mb_per_tab'],
                "Memory usage per tab"
            ))
            
        finally:
            manager.shutdown()
        
        self.record_benchmark_result("TabLifecycleManager Performance", metrics)
    
    def test_component_bus_performance(self):
        """Benchmark ComponentBus performance"""
        bus = ComponentBus()
        metrics = []
        
        try:
            # Test message processing performance
            messages_received = []
            
            def fast_handler(message):
                messages_received.append(message)
            
            # Subscribe multiple components
            for i in range(10):
                component_id = f"component_{i}"
                bus.subscribe(component_id, "benchmark_channel", fast_handler)
            
            # Benchmark message sending
            message_count = 1000
            start_time = time.perf_counter()
            
            for i in range(message_count):
                bus.send_event("sender", "benchmark_channel", f"event_{i}", {"index": i})
            
            send_time = (time.perf_counter() - start_time) * 1000
            
            # Benchmark message processing
            start_time = time.perf_counter()
            bus.process_messages()
            process_time = (time.perf_counter() - start_time) * 1000
            
            # Calculate metrics
            avg_send_time = send_time / message_count
            avg_process_time = process_time / len(messages_received)
            
            metrics.append(self.create_performance_metric(
                "message_send_avg_time", avg_send_time, "ms",
                self.baseline_metrics['message_processing_time_ms'],
                "Average time to send a message"
            ))
            
            metrics.append(self.create_performance_metric(
                "message_process_avg_time", avg_process_time, "ms",
                self.baseline_metrics['message_processing_time_ms'],
                "Average time to process a message"
            ))
            
            # Test throughput
            throughput = len(messages_received) / (process_time / 1000)  # messages per second
            metrics.append(self.create_performance_metric(
                "message_throughput", throughput, "msg/s",
                5000.0,  # 5000 messages per second threshold
                "Message processing throughput"
            ))
            
            # Test priority queue performance
            priority_times = []
            
            for _ in range(100):
                start_time = time.perf_counter()
                bus.send_event("sender", "priority_test", "high_priority", {}, Priority.HIGH)
                bus.send_event("sender", "priority_test", "low_priority", {}, Priority.LOW)
                priority_time = (time.perf_counter() - start_time) * 1000
                priority_times.append(priority_time)
            
            avg_priority_time = statistics.mean(priority_times)
            metrics.append(self.create_performance_metric(
                "priority_messaging_avg_time", avg_priority_time, "ms",
                1.0,  # 1ms threshold for priority messaging
                "Average time for priority message handling"
            ))
            
        finally:
            bus.stop()
        
        self.record_benchmark_result("ComponentBus Performance", metrics)
    
    def test_theme_manager_performance(self, temp_dir):
        """Benchmark ThemeManager performance"""
        manager = ThemeManager(config_dir=temp_dir)
        metrics = []
        
        try:
            # Test theme switching performance
            themes = [ThemeVariant.LIGHT, ThemeVariant.DARK, ThemeVariant.HIGH_CONTRAST]
            switch_times = []
            
            for _ in range(50):
                for theme in themes:
                    _, switch_time = self.measure_execution_time(
                        manager.switch_theme, theme
                    )
                    switch_times.append(switch_time)
            
            avg_switch_time = statistics.mean(switch_times)
            metrics.append(self.create_performance_metric(
                "theme_switch_avg_time", avg_switch_time, "ms",
                self.baseline_metrics['theme_switch_time_ms'],
                "Average theme switching time"
            ))
            
            # Test token retrieval performance
            token_times = []
            
            for _ in range(1000):
                start_time = time.perf_counter()
                manager.get_token("colors", "primary")
                manager.get_token("fonts", "body")
                manager.get_token("spacing", "medium")
                token_time = (time.perf_counter() - start_time) * 1000
                token_times.append(token_time)
            
            avg_token_time = statistics.mean(token_times)
            metrics.append(self.create_performance_metric(
                "token_retrieval_avg_time", avg_token_time, "ms",
                0.01,  # 0.01ms threshold for token retrieval
                "Average token retrieval time"
            ))
            
            # Test component override performance
            override_times = []
            
            for i in range(100):
                component_id = f"test_component_{i}"
                overrides = {
                    "colors": {"primary": "#ff0000", "secondary": "#00ff00"},
                    "fonts": {"body": "Arial", "heading": "Helvetica"}
                }
                
                _, override_time = self.measure_execution_time(
                    manager.register_component_override, component_id, overrides
                )
                override_times.append(override_time)
            
            avg_override_time = statistics.mean(override_times)
            metrics.append(self.create_performance_metric(
                "component_override_avg_time", avg_override_time, "ms",
                1.0,  # 1ms threshold for component override
                "Average component override registration time"
            ))
            
        finally:
            manager.cleanup()
        
        self.record_benchmark_result("ThemeManager Performance", metrics)
    
    def test_app_controller_performance(self, temp_dir):
        """Benchmark AppController performance"""
        config = {
            'state_dir': temp_dir,
            'enable_performance_monitoring': True,
            'enable_hibernation': True,
            'enable_component_bus': True,
            'enable_theme_management': True
        }
        
        metrics = []
        
        # Test initialization performance
        _, init_time = self.measure_execution_time(
            AppController, config
        )
        
        metrics.append(self.create_performance_metric(
            "app_controller_init_time", init_time, "ms",
            self.baseline_metrics['startup_time_ms'],
            "AppController initialization time"
        ))
        
        controller = AppController(config)
        
        try:
            # Test service retrieval performance
            service_times = []
            service_names = ['tab_lifecycle_manager', 'component_bus', 'theme_manager']
            
            for _ in range(1000):
                start_time = time.perf_counter()
                for service_name in service_names:
                    controller.get_service(service_name)
                service_time = (time.perf_counter() - start_time) * 1000
                service_times.append(service_time)
            
            avg_service_time = statistics.mean(service_times)
            metrics.append(self.create_performance_metric(
                "service_retrieval_avg_time", avg_service_time, "ms",
                0.1,  # 0.1ms threshold for service retrieval
                "Average service retrieval time"
            ))
            
            # Test global state management performance
            state_times = []
            
            for i in range(1000):
                key = f"test_key_{i}"
                value = f"test_value_{i}"
                
                start_time = time.perf_counter()
                controller.set_global_state(key, value)
                retrieved_value = controller.get_global_state(key)
                state_time = (time.perf_counter() - start_time) * 1000
                state_times.append(state_time)
                
                assert retrieved_value == value
            
            avg_state_time = statistics.mean(state_times)
            metrics.append(self.create_performance_metric(
                "global_state_avg_time", avg_state_time, "ms",
                0.05,  # 0.05ms threshold for state operations
                "Average global state operation time"
            ))
            
            # Test configuration update performance
            config_times = []
            
            for i in range(100):
                new_config = {
                    f'test_option_{i}': f'test_value_{i}',
                    'hibernation_threshold': 300 + i
                }
                
                _, config_time = self.measure_execution_time(
                    controller.update_configuration, new_config
                )
                config_times.append(config_time)
            
            avg_config_time = statistics.mean(config_times)
            metrics.append(self.create_performance_metric(
                "config_update_avg_time", avg_config_time, "ms",
                10.0,  # 10ms threshold for config updates
                "Average configuration update time"
            ))
            
        finally:
            # Test shutdown performance
            _, shutdown_time = self.measure_execution_time(
                controller.shutdown
            )
            
            metrics.append(self.create_performance_metric(
                "app_controller_shutdown_time", shutdown_time, "ms",
                self.baseline_metrics['shutdown_time_ms'],
                "AppController shutdown time"
            ))
        
        self.record_benchmark_result("AppController Performance", metrics)
    
    def test_integrated_system_performance(self, temp_dir):
        """Benchmark integrated system performance under load"""
        config = {
            'state_dir': temp_dir,
            'enable_performance_monitoring': True,
            'enable_hibernation': True,
            'enable_component_bus': True,
            'enable_theme_management': True
        }
        
        controller = AppController(config)
        metrics = []
        
        try:
            # Get all managers
            lifecycle_manager = controller.get_service('tab_lifecycle_manager')
            component_bus = controller.get_service('component_bus')
            theme_manager = controller.get_service('theme_manager')
            
            initial_memory = self.measure_memory_usage()
            
            # Simulate realistic workload
            start_time = time.perf_counter()
            
            # Create tabs and simulate user interactions
            tab_ids = []
            for i in range(50):
                tab_id = f"workload_tab_{i}"
                lifecycle_manager.create_tab(tab_id, priority=TabPriority.NORMAL)
                lifecycle_manager.activate_tab(tab_id)
                tab_ids.append(tab_id)
                
                # Add some state to tabs
                lifecycle_manager.update_tab_state(tab_id, {
                    'user_data': f'data_{i}',
                    'scroll_position': i * 100,
                    'form_values': {'field1': f'value_{i}', 'field2': f'other_{i}'}
                })
                
                # Send some messages
                component_bus.send_event("workload_test", "user_action", f"action_{i}", 
                                       {"tab_id": tab_id, "action": "scroll"})
                
                # Occasionally switch themes
                if i % 10 == 0:
                    theme_manager.switch_theme(ThemeVariant.DARK if i % 20 == 0 else ThemeVariant.LIGHT)
            
            # Process all messages
            component_bus.process_messages()
            
            # Simulate hibernation of some tabs
            for i, tab_id in enumerate(tab_ids):
                if i % 3 == 0:  # Hibernate every 3rd tab
                    lifecycle_manager.hibernate_tab(tab_id)
            
            # Test recovery of hibernated tabs
            hibernated_tabs = [tab_id for i, tab_id in enumerate(tab_ids) if i % 3 == 0]
            for tab_id in hibernated_tabs[:10]:  # Restore first 10
                lifecycle_manager.restore_tab(tab_id)
            
            workload_time = (time.perf_counter() - start_time) * 1000
            final_memory = self.measure_memory_usage()
            
            # Calculate metrics
            total_memory_usage = final_memory - initial_memory
            memory_per_tab = total_memory_usage / len(tab_ids)
            
            metrics.append(self.create_performance_metric(
                "integrated_workload_time", workload_time, "ms",
                10000.0,  # 10 second threshold for workload
                "Time to complete integrated workload"
            ))
            
            metrics.append(self.create_performance_metric(
                "integrated_memory_per_tab", memory_per_tab, "MB",
                self.baseline_metrics['memory_usage_mb_per_tab'] * 2,  # Allow 2x for integrated system
                "Memory usage per tab in integrated system"
            ))
            
            metrics.append(self.create_performance_metric(
                "integrated_total_memory", total_memory_usage, "MB",
                200.0,  # 200MB threshold for 50 tabs
                "Total memory usage for integrated workload"
            ))
            
            # Test system responsiveness under load
            responsiveness_times = []
            
            for _ in range(10):
                start_time = time.perf_counter()
                
                # Perform various operations
                controller.get_global_state("test_key")
                theme_manager.get_token("colors", "primary")
                lifecycle_manager.get_active_tabs()
                component_bus.send_event("test", "responsiveness", "ping", {})
                component_bus.process_messages()
                
                responsiveness_time = (time.perf_counter() - start_time) * 1000
                responsiveness_times.append(responsiveness_time)
            
            avg_responsiveness = statistics.mean(responsiveness_times)
            metrics.append(self.create_performance_metric(
                "system_responsiveness", avg_responsiveness, "ms",
                50.0,  # 50ms threshold for system responsiveness
                "Average system responsiveness under load"
            ))
            
        finally:
            controller.shutdown()
        
        self.record_benchmark_result("Integrated System Performance", metrics)
    
    def generate_performance_report(self) -> str:
        """Generate comprehensive performance report"""
        report = ["V2.0 UI System Performance Benchmark Report", "=" * 50, ""]
        
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results if result.passed)
        
        report.append(f"Total Tests: {total_tests}")
        report.append(f"Passed: {passed_tests}")
        report.append(f"Failed: {total_tests - passed_tests}")
        report.append(f"Success Rate: {(passed_tests / total_tests * 100):.1f}%")
        report.append("")
        
        for result in self.results:
            status = "✅ PASSED" if result.passed else "❌ FAILED"
            report.append(f"{result.test_name}: {status}")
            
            for metric in result.metrics:
                metric_status = "✅" if metric.passed else "❌"
                report.append(f"  {metric_status} {metric.name}: {metric.value:.3f}{metric.unit} "
                            f"(threshold: {metric.threshold}{metric.unit})")
            report.append("")
        
        return "\n".join(report)
    
    def save_results_to_file(self, filepath: str):
        """Save benchmark results to JSON file"""
        results_data = []
        
        for result in self.results:
            result_data = {
                'test_name': result.test_name,
                'timestamp': result.timestamp,
                'passed': result.passed,
                'environment': result.environment,
                'metrics': [
                    {
                        'name': metric.name,
                        'value': metric.value,
                        'unit': metric.unit,
                        'threshold': metric.threshold,
                        'passed': metric.passed,
                        'description': metric.description
                    }
                    for metric in result.metrics
                ]
            }
            results_data.append(result_data)
        
        with open(filepath, 'w') as f:
            json.dump(results_data, f, indent=2)


# Test class that pytest will discover
class TestPerformanceBenchmarks(PerformanceBenchmarkSuite):
    """Performance benchmark tests for pytest"""
    
    def test_run_all_benchmarks(self, temp_dir):
        """Run all performance benchmarks"""
        print("\n🚀 Starting V2.0 UI System Performance Benchmarks...")
        
        # Run all benchmark tests
        self.test_tab_lifecycle_performance(temp_dir)
        self.test_component_bus_performance()
        self.test_theme_manager_performance(temp_dir)
        self.test_app_controller_performance(temp_dir)
        self.test_integrated_system_performance(temp_dir)
        
        # Generate and display report
        report = self.generate_performance_report()
        print("\n" + report)
        
        # Save results
        results_file = os.path.join(temp_dir, "performance_results.json")
        self.save_results_to_file(results_file)
        print(f"\n📊 Results saved to: {results_file}")
        
        # Assert that all tests passed
        failed_tests = [result for result in self.results if not result.passed]
        if failed_tests:
            failed_names = [result.test_name for result in failed_tests]
            pytest.fail(f"Performance benchmarks failed: {failed_names}")


if __name__ == "__main__":
    # Run benchmarks directly
    suite = PerformanceBenchmarkSuite()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        if not QApplication.instance():
            app = QApplication([])
        
        print("🚀 Running V2.0 UI System Performance Benchmarks...")
        
        suite.test_tab_lifecycle_performance(temp_dir)
        suite.test_component_bus_performance()
        suite.test_theme_manager_performance(temp_dir)
        suite.test_app_controller_performance(temp_dir)
        suite.test_integrated_system_performance(temp_dir)
        
        print("\n" + suite.generate_performance_report())
        
        results_file = "performance_results.json"
        suite.save_results_to_file(results_file)
        print(f"\n📊 Results saved to: {results_file}") 