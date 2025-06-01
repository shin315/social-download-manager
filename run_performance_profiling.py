#!/usr/bin/env python3
"""
Performance Profiling and Benchmarking Script for Social Download Manager v2.0

This script provides comprehensive performance analysis including:
- Application profiling (CPU, memory, I/O)
- Baseline establishment and comparison with v1.2.1
- Bottleneck identification and hotspot analysis
- Performance metrics collection and reporting

Usage:
    python run_performance_profiling.py --establish-baseline
    python run_performance_profiling.py --profile-current
    python run_performance_profiling.py --compare-versions
    python run_performance_profiling.py --full-analysis
"""

import sys
import argparse
import time
import json
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from scripts.performance import ApplicationProfiler, BenchmarkManager, ProfilerType
    from scripts.performance.profiler import SystemSnapshot
    from scripts.performance.benchmarks import PerformanceMetrics, BenchmarkComparison
except ImportError as e:
    print(f"Error importing performance modules: {e}")
    print("Installing required dependencies...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    # Try importing again
    from scripts.performance import ApplicationProfiler, BenchmarkManager, ProfilerType
    from scripts.performance.profiler import SystemSnapshot
    from scripts.performance.benchmarks import PerformanceMetrics, BenchmarkComparison


def profile_application_startup():
    """Profile application startup process"""
    print("🚀 Profiling Application Startup...")
    
    profiler = ApplicationProfiler()
    
    # Profile CPU usage during startup
    with profiler.profile_context("startup_cpu", ProfilerType.CPU):
        # Import and initialize main application components
        try:
            # Test v2.0 startup
            from main_v2 import setup_application
            setup_result = setup_application()
            print(f"  ✅ v2.0 setup result: {setup_result}")
        except Exception as e:
            print(f"  ❌ Error during v2.0 startup: {e}")
    
    # Profile system resources during startup
    with profiler.profile_context("startup_system", ProfilerType.SYSTEM_RESOURCES):
        time.sleep(3)  # Monitor for 3 seconds
        
    return profiler


def profile_application_components():
    """Profile individual application components"""
    print("🔧 Profiling Application Components...")
    
    profiler = ApplicationProfiler()
    
    # Profile configuration loading
    print("  📋 Profiling configuration loading...")
    with profiler.profile_context("config_loading", ProfilerType.CPU):
        try:
            from core.config_manager import get_config_manager, get_config
            config_manager = get_config_manager()
            config = get_config()
            print(f"    Config loaded: {config.app_name if config else 'Failed'}")
        except Exception as e:
            print(f"    Error loading config: {e}")
    
    # Profile event system
    print("  📡 Profiling event system...")
    with profiler.profile_context("event_system", ProfilerType.CPU):
        try:
            from core.event_system import get_event_bus, publish_event, EventType
            event_bus = get_event_bus()
            # Test event publishing
            for i in range(100):
                publish_event(EventType.APPLICATION_START, {"test": i})
            print(f"    Event system active: {event_bus.get_total_subscribers()} subscribers")
        except Exception as e:
            print(f"    Error testing event system: {e}")
    
    # Profile app controller
    print("  🎮 Profiling app controller...")
    with profiler.profile_context("app_controller", ProfilerType.CPU):
        try:
            from core.app_controller import get_app_controller, initialize_app_controller
            controller = get_app_controller()
            if controller:
                status = controller.get_status()
                print(f"    Controller status: {status.state.name}")
            else:
                print("    Controller not initialized")
        except Exception as e:
            print(f"    Error testing app controller: {e}")
    
    return profiler


def analyze_memory_usage():
    """Analyze memory usage patterns"""
    print("💾 Analyzing Memory Usage...")
    
    profiler = ApplicationProfiler()
    
    # Monitor memory during normal operations
    profiler.start_system_monitoring(interval=0.5)
    
    try:
        # Simulate typical application usage
        print("  🔄 Simulating typical application usage...")
        
        # Test configuration operations
        for i in range(10):
            try:
                from core.config_manager import get_config
                config = get_config()
                time.sleep(0.1)
            except Exception:
                pass
        
        # Test event operations
        for i in range(50):
            try:
                from core.event_system import publish_event, EventType
                publish_event(EventType.APPLICATION_START, {"iteration": i})
                time.sleep(0.05)
            except Exception:
                pass
        
        # Let it run for a bit to collect data
        time.sleep(5)
        
    finally:
        profiler.stop_system_monitoring()
    
    # Analyze memory patterns
    if profiler.system_snapshots:
        memory_values = [s.memory_used_mb for s in profiler.system_snapshots]
        cpu_values = [s.cpu_percent for s in profiler.system_snapshots]
        
        print(f"  📊 Memory Analysis:")
        print(f"    Peak Memory: {max(memory_values):.1f} MB")
        print(f"    Average Memory: {sum(memory_values)/len(memory_values):.1f} MB")
        print(f"    Memory Range: {max(memory_values) - min(memory_values):.1f} MB")
        print(f"  📊 CPU Analysis:")
        print(f"    Peak CPU: {max(cpu_values):.1f}%")
        print(f"    Average CPU: {sum(cpu_values)/len(cpu_values):.1f}%")
    
    return profiler


def identify_performance_bottlenecks():
    """Identify performance bottlenecks in the application"""
    print("🔍 Identifying Performance Bottlenecks...")
    
    profiler = ApplicationProfiler()
    
    bottlenecks = []
    
    # Test import times
    print("  📦 Testing import performance...")
    import_times = {}
    
    modules_to_test = [
        'core.config_manager',
        'core.event_system', 
        'core.app_controller',
        'core.constants',
        'version',
    ]
    
    for module in modules_to_test:
        start_time = time.time()
        try:
            __import__(module)
            import_time = time.time() - start_time
            import_times[module] = import_time
            if import_time > 0.1:  # Flag imports taking >100ms
                bottlenecks.append(f"Slow import: {module} ({import_time*1000:.1f}ms)")
        except Exception as e:
            print(f"    ❌ Failed to import {module}: {e}")
    
    # Show import analysis
    print(f"  📊 Import Analysis:")
    for module, import_time in sorted(import_times.items(), key=lambda x: x[1], reverse=True):
        status = "⚠️" if import_time > 0.1 else "✅"
        print(f"    {status} {module}: {import_time*1000:.1f}ms")
    
    # Test initialization times
    print("  🚀 Testing initialization performance...")
    init_times = {}
    
    # Test app controller initialization
    start_time = time.time()
    try:
        from core.app_controller import initialize_app_controller, shutdown_app_controller
        result = initialize_app_controller()
        init_time = time.time() - start_time
        init_times['app_controller'] = init_time
        if init_time > 0.5:  # Flag initialization taking >500ms
            bottlenecks.append(f"Slow app controller init: {init_time*1000:.1f}ms")
        
        # Cleanup
        shutdown_app_controller()
    except Exception as e:
        print(f"    ❌ App controller init failed: {e}")
    
    # Show initialization analysis
    print(f"  📊 Initialization Analysis:")
    for component, init_time in sorted(init_times.items(), key=lambda x: x[1], reverse=True):
        status = "⚠️" if init_time > 0.5 else "✅"
        print(f"    {status} {component}: {init_time*1000:.1f}ms")
    
    # Summary
    if bottlenecks:
        print(f"  🚨 Identified {len(bottlenecks)} potential bottlenecks:")
        for bottleneck in bottlenecks:
            print(f"    • {bottleneck}")
    else:
        print(f"  ✅ No significant bottlenecks identified")
    
    return bottlenecks


def run_comprehensive_benchmark():
    """Run comprehensive performance benchmark"""
    print("📊 Running Comprehensive Performance Benchmark...")
    
    benchmark_manager = BenchmarkManager()
    
    # Establish v1.2.1 baseline if not exists
    print("  📈 Checking v1.2.1 baseline...")
    baseline_v1 = benchmark_manager.load_baseline("v1.2.1")
    if not baseline_v1:
        print("  🔧 Establishing v1.2.1 baseline...")
        baseline_v1 = benchmark_manager.establish_baseline("v1.2.1")
    else:
        print("  ✅ v1.2.1 baseline found")
    
    # Run v2.0 benchmark
    print("  🚀 Running v2.0 benchmark...")
    current_v2 = benchmark_manager.run_benchmark("v2.0")
    
    # Compare versions
    print("  ⚖️ Comparing performance...")
    comparison = benchmark_manager.compare_with_baseline("v1.2.1", "v2.0")
    
    # Print comparison results
    print("\n" + "="*60)
    print(comparison.summary)
    print("="*60)
    
    # Save detailed results
    results_dir = Path("scripts/performance_results")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    comparison_file = results_dir / f"benchmark_comparison_{int(time.time())}.json"
    comparison_data = {
        'baseline': baseline_v1.to_dict(),
        'current': current_v2.to_dict(),
        'improvements': comparison.improvement_percent,
        'regressions': comparison.regression_percent,
        'overall_improvement': comparison.overall_improvement,
        'summary': comparison.summary
    }
    
    with open(comparison_file, 'w') as f:
        json.dump(comparison_data, f, indent=2)
    
    print(f"\n📄 Detailed results saved: {comparison_file}")
    
    return comparison


def generate_performance_report():
    """Generate comprehensive performance report"""
    print("📋 Generating Performance Report...")
    
    report_content = []
    report_content.append("# Social Download Manager v2.0 Performance Analysis Report")
    report_content.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    report_content.append("")
    
    # Run all analysis components
    print("  🔄 Running startup profiling...")
    startup_profiler = profile_application_startup()
    
    print("  🔄 Running component profiling...")  
    component_profiler = profile_application_components()
    
    print("  🔄 Running memory analysis...")
    memory_profiler = analyze_memory_usage()
    
    print("  🔄 Identifying bottlenecks...")
    bottlenecks = identify_performance_bottlenecks()
    
    print("  🔄 Running benchmark comparison...")
    comparison = run_comprehensive_benchmark()
    
    # Build report
    report_content.append("## Executive Summary")
    if comparison.overall_improvement > 0:
        report_content.append(f"✅ **Overall Performance Improvement: +{comparison.overall_improvement:.1f}%**")
    else:
        report_content.append(f"❌ **Overall Performance Regression: {comparison.overall_improvement:.1f}%**")
    report_content.append("")
    
    report_content.append("## Key Findings")
    if comparison.improvement_percent:
        report_content.append("### 🚀 Improvements")
        for metric, percent in comparison.improvement_percent.items():
            report_content.append(f"- {metric.replace('_', ' ').title()}: +{percent:.1f}%")
        report_content.append("")
    
    if comparison.regression_percent:
        report_content.append("### ⚠️ Regressions")
        for metric, percent in comparison.regression_percent.items():
            report_content.append(f"- {metric.replace('_', ' ').title()}: -{percent:.1f}%")
        report_content.append("")
    
    if bottlenecks:
        report_content.append("### 🔍 Identified Bottlenecks")
        for bottleneck in bottlenecks:
            report_content.append(f"- {bottleneck}")
        report_content.append("")
    
    # Memory analysis
    if memory_profiler.system_snapshots:
        memory_values = [s.memory_used_mb for s in memory_profiler.system_snapshots]
        cpu_values = [s.cpu_percent for s in memory_profiler.system_snapshots]
        
        report_content.append("### 💾 Resource Usage Analysis")
        report_content.append(f"- Peak Memory Usage: {max(memory_values):.1f} MB")
        report_content.append(f"- Average Memory Usage: {sum(memory_values)/len(memory_values):.1f} MB")
        report_content.append(f"- Peak CPU Usage: {max(cpu_values):.1f}%")
        report_content.append(f"- Average CPU Usage: {sum(cpu_values)/len(cpu_values):.1f}%")
        report_content.append("")
    
    report_content.append("## Recommendations")
    report_content.append("Based on the performance analysis, the following optimizations are recommended:")
    report_content.append("")
    
    if bottlenecks:
        report_content.append("### Priority 1: Address Bottlenecks")
        for bottleneck in bottlenecks:
            report_content.append(f"- Optimize: {bottleneck}")
        report_content.append("")
    
    if comparison.regression_percent:
        report_content.append("### Priority 2: Fix Regressions")
        for metric in comparison.regression_percent.keys():
            report_content.append(f"- Investigate regression in {metric.replace('_', ' ')}")
        report_content.append("")
    
    report_content.append("### General Optimizations")
    report_content.append("- Implement database query optimization (Task 21.2)")
    report_content.append("- Optimize UI rendering for large datasets (Task 21.3)")
    report_content.append("- Implement memory management improvements (Task 21.4)")
    report_content.append("- Add platform-specific optimizations (Task 21.5)")
    
    # Save report
    reports_dir = Path("scripts/performance_results")
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    report_file = reports_dir / f"performance_report_{int(time.time())}.md"
    with open(report_file, 'w') as f:
        f.write("\n".join(report_content))
    
    print(f"📄 Performance report saved: {report_file}")
    
    return report_file


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Performance Profiling and Benchmarking for Social Download Manager v2.0")
    
    parser.add_argument("--establish-baseline", action="store_true",
                       help="Establish v1.2.1 baseline metrics")
    parser.add_argument("--profile-current", action="store_true",
                       help="Profile current v2.0 application")
    parser.add_argument("--compare-versions", action="store_true",
                       help="Compare v2.0 with v1.2.1 baseline")
    parser.add_argument("--full-analysis", action="store_true",
                       help="Run complete performance analysis and generate report")
    parser.add_argument("--bottlenecks-only", action="store_true",
                       help="Only identify performance bottlenecks")
    
    args = parser.parse_args()
    
    print("🚀 Social Download Manager v2.0 Performance Profiling")
    print("=" * 60)
    
    try:
        if args.establish_baseline:
            benchmark_manager = BenchmarkManager()
            benchmark_manager.establish_baseline("v1.2.1", force=True)
            
        elif args.profile_current:
            profile_application_startup()
            profile_application_components()
            analyze_memory_usage()
            
        elif args.compare_versions:
            run_comprehensive_benchmark()
            
        elif args.bottlenecks_only:
            identify_performance_bottlenecks()
            
        elif args.full_analysis:
            generate_performance_report()
            
        else:
            # Default: run bottleneck identification
            print("No specific action specified. Running bottleneck identification...")
            identify_performance_bottlenecks()
            print("\nUse --help to see all available options.")
    
    except KeyboardInterrupt:
        print("\n\n⏹️ Performance profiling interrupted by user")
        return 1
    
    except Exception as e:
        print(f"\n❌ Error during performance profiling: {e}")
        return 1
    
    print("\n✅ Performance profiling completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main()) 