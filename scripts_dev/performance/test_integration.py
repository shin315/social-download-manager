"""
Test Script for Optimized Event System Integration

This script tests the integration between the high-performance event system
and the existing adapter framework, verifying functionality and performance.
"""

import sys
import time
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
        OptimizedEventCoordinator,
        OptimizationLevel,
        get_optimized_coordinator,
        initialize_optimized_events
    )
    INTEGRATION_AVAILABLE = True
except ImportError as e:
    print(f"❌ Integration not available: {e}")
    INTEGRATION_AVAILABLE = False


def test_optimization_levels():
    """Test different optimization levels"""
    print("\n🧪 Testing Optimization Levels...")
    
    levels = [
        OptimizationLevel.DISABLED,
        OptimizationLevel.BASIC,
        OptimizationLevel.STANDARD,
        OptimizationLevel.AGGRESSIVE,
        OptimizationLevel.MAXIMUM
    ]
    
    results = {}
    
    for level in levels:
        print(f"\n📊 Testing {level} optimization level...")
        
        config = {
            "optimization_level": level,
            "enable_fallback": True,
            "enable_metrics": True
        }
        
        coordinator = OptimizedEventCoordinator(config)
        
        try:
            # Start coordinator
            success = coordinator.start()
            if not success:
                print(f"❌ Failed to start {level} coordinator")
                continue
            
            # Run benchmark
            benchmark_results = coordinator.benchmark_performance(num_events=1000)
            results[level] = benchmark_results
            
            # Get configuration
            config_info = coordinator.export_configuration()
            
            print(f"✅ {level}:")
            print(f"   Throughput: {benchmark_results.get('throughput_events_per_second', 0):.1f} events/sec")
            print(f"   Efficiency: {benchmark_results.get('processing_efficiency', 0):.1f}%")
            print(f"   Using optimized: {config_info['system_status']['using_optimized']}")
            
            # Stop coordinator
            coordinator.stop()
            
        except Exception as e:
            print(f"❌ Error testing {level}: {e}")
    
    return results


def test_backward_compatibility():
    """Test backward compatibility functions"""
    print("\n🔄 Testing Backward Compatibility...")
    
    try:
        # Test global coordinator access
        coordinator = get_optimized_coordinator()
        success = coordinator.start()
        
        if not success:
            print("❌ Failed to start global coordinator")
            return False
        
        # Test event emission with different formats
        test_cases = [
            {"event_type": "DATA_UPDATED", "source": "test", "data": {"test": 1}},
            {"event_type": "ui_update_required", "source": "test", "data": None},
            {"event_type": "CONTENT_URL_ENTERED", "source": "adapter", "data": {"url": "test"}},
        ]
        
        success_count = 0
        for i, case in enumerate(test_cases):
            success = coordinator.emit_event(**case)
            if success:
                success_count += 1
                print(f"✅ Event {i+1}: {case['event_type']} emitted successfully")
            else:
                print(f"❌ Event {i+1}: {case['event_type']} failed")
        
        # Test handler registration
        def test_handler(event):
            print(f"Handler received: {event}")
        
        handler_id = coordinator.register_handler("DATA_UPDATED", test_handler)
        if handler_id:
            print(f"✅ Handler registered with ID: {handler_id}")
            
            # Test unregistration
            unregister_success = coordinator.unregister_handler(handler_id)
            if unregister_success:
                print("✅ Handler unregistered successfully")
            else:
                print("❌ Handler unregistration failed")
        else:
            print("❌ Handler registration failed")
        
        coordinator.stop()
        
        print(f"\n📊 Compatibility Test Results:")
        print(f"   Events emitted: {success_count}/{len(test_cases)}")
        print(f"   Handler registration: {'✅' if handler_id else '❌'}")
        
        return success_count == len(test_cases) and handler_id is not None
        
    except Exception as e:
        print(f"❌ Backward compatibility test failed: {e}")
        return False


def test_performance_metrics():
    """Test performance metrics collection"""
    print("\n📈 Testing Performance Metrics...")
    
    try:
        coordinator = get_optimized_coordinator({
            "optimization_level": OptimizationLevel.STANDARD,
            "enable_metrics": True
        })
        
        success = coordinator.start()
        if not success:
            print("❌ Failed to start coordinator for metrics test")
            return False
        
        # Emit some events
        for i in range(100):
            coordinator.emit_event("DATA_UPDATED", "metrics_test", {"id": i})
        
        # Wait a bit for processing
        time.sleep(0.5)
        
        # Get metrics
        metrics = coordinator.get_performance_metrics()
        metrics_history = coordinator.get_metrics_history()
        
        print("✅ Performance Metrics:")
        print(f"   System active: {metrics['system_info']['is_active']}")
        print(f"   Using optimized: {metrics['system_info']['using_optimized']}")
        print(f"   Metrics history entries: {len(metrics_history)}")
        
        if 'performance' in metrics and 'event_processing' in metrics['performance']:
            event_metrics = metrics['performance']['event_processing']
            print(f"   Events processed: {event_metrics.get('events_processed', 0)}")
            print(f"   Events per second: {event_metrics.get('events_per_second', 0):.1f}")
            print(f"   Queue depth: {event_metrics.get('queue_depth', 0)}")
        
        coordinator.stop()
        return True
        
    except Exception as e:
        print(f"❌ Performance metrics test failed: {e}")
        return False


def test_optimization_switching():
    """Test switching between optimization levels"""
    print("\n🔄 Testing Optimization Level Switching...")
    
    try:
        coordinator = get_optimized_coordinator({
            "optimization_level": OptimizationLevel.BASIC
        })
        
        success = coordinator.start()
        if not success:
            print("❌ Failed to start coordinator for switching test")
            return False
        
        # Test initial level
        config = coordinator.export_configuration()
        print(f"✅ Initial level: {config['optimization_level']}")
        
        # Switch to different levels
        switch_results = []
        for new_level in [OptimizationLevel.STANDARD, OptimizationLevel.AGGRESSIVE, OptimizationLevel.BASIC]:
            switch_success = coordinator.switch_optimization_level(new_level)
            switch_results.append(switch_success)
            if switch_success:
                print(f"✅ Switched to {new_level}")
            else:
                print(f"❌ Failed to switch to {new_level}")
        
        coordinator.stop()
        return all(switch_results)
        
    except Exception as e:
        print(f"❌ Optimization switching test failed: {e}")
        return False


def run_comprehensive_test():
    """Run all integration tests"""
    print("🚀 Starting Comprehensive Integration Test...")
    print("="*60)
    
    if not INTEGRATION_AVAILABLE:
        print("❌ Integration module not available - cannot run tests")
        return False
    
    test_results = {}
    
    # Run individual tests
    try:
        test_results["optimization_levels"] = test_optimization_levels()
        test_results["backward_compatibility"] = test_backward_compatibility()
        test_results["performance_metrics"] = test_performance_metrics()
        test_results["optimization_switching"] = test_optimization_switching()
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return False
    
    # Summary
    print("\n" + "="*60)
    print("📊 INTEGRATION TEST RESULTS SUMMARY")
    print("="*60)
    
    passed_tests = 0
    total_tests = 0
    
    for test_name, result in test_results.items():
        if test_name == "optimization_levels":
            # Special handling for optimization levels (returns dict)
            if isinstance(result, dict) and result:
                print(f"✅ {test_name}: {len(result)} levels tested")
                passed_tests += 1
            else:
                print(f"❌ {test_name}: Failed")
            total_tests += 1
        else:
            if result:
                print(f"✅ {test_name}: Passed")
                passed_tests += 1
            else:
                print(f"❌ {test_name}: Failed")
            total_tests += 1
    
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    print(f"\n🎯 Overall Success Rate: {success_rate:.1f}% ({passed_tests}/{total_tests})")
    
    if success_rate >= 75:
        print("🎉 Integration test PASSED! System ready for deployment.")
        return True
    else:
        print("❌ Integration test FAILED! Issues need to be resolved.")
        return False


if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1) 