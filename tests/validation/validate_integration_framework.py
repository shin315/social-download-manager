#!/usr/bin/env python3
"""
Integration Framework Validation Script
=======================================

Comprehensive validation of the integration testing framework for Task 20.
This script validates all components and ensures everything is working correctly.
"""

import sys
import traceback
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def validate_imports():
    """Validate all integration test imports."""
    print("📦 Validating imports...")
    
    try:
        from tests.integration_environment_setup import IntegrationTestEnvironment, IntegrationTestRunner
        from tests.integration_config import get_test_config, list_test_configs
        from tests.integration_test_runner import IntegrationTestExecutor, IntegrationTestReporter
        print("   ✓ Core framework imports successful")
        
        # Test config system
        configs = list_test_configs()
        config = get_test_config('quick')
        print(f"   ✓ Config system working - {len(configs)} configs available")
        
        return True
    except Exception as e:
        print(f"   ❌ Import validation failed: {e}")
        traceback.print_exc()
        return False

def validate_environment_setup():
    """Validate environment setup capabilities."""
    print("🏗️  Validating environment setup...")
    
    try:
        from tests.integration_environment_setup import IntegrationTestRunner
        
        with IntegrationTestRunner('framework_validation') as (env, env_info):
            # Check environment creation
            assert env_info['test_dir'] is not None
            assert len(env_info['databases']) >= 3  # v2_clean, v1_migration, corrupted
            assert len(env_info['mock_services']) >= 3  # tiktok, youtube, network
            assert len(env_info['config_files']) >= 2  # main, error_handling
            
            print(f"   ✓ Environment created at: {env_info['test_dir']}")
            print(f"   ✓ {len(env_info['databases'])} test databases created")
            print(f"   ✓ {len(env_info['mock_services'])} mock services configured")
            print(f"   ✓ {len(env_info['config_files'])} config files generated")
            
        print("   ✓ Environment setup and cleanup successful")
        return True
        
    except Exception as e:
        print(f"   ❌ Environment validation failed: {e}")
        traceback.print_exc()
        return False

def validate_test_configurations():
    """Validate test configuration system."""
    print("⚙️  Validating test configurations...")
    
    try:
        from tests.integration_config import get_test_config, list_test_configs
        
        configs = list_test_configs()
        expected_configs = ['quick', 'full', 'error_focused', 'performance', 'migration']
        
        for config_name in expected_configs:
            assert config_name in configs, f"Missing config: {config_name}"
            config = get_test_config(config_name)
            assert config.test_name is not None
            assert config.max_test_duration_minutes > 0
            
        print(f"   ✓ All {len(expected_configs)} configurations validated")
        return True
        
    except Exception as e:
        print(f"   ❌ Configuration validation failed: {e}")
        traceback.print_exc()
        return False

def validate_test_runner():
    """Validate test execution framework."""
    print("🏃 Validating test runner framework...")
    
    try:
        from tests.integration_test_runner import IntegrationTestExecutor
        from tests.integration_config import get_test_config
        
        # Create executor with quick config
        config = get_test_config('quick')
        executor = IntegrationTestExecutor('quick')
        
        assert executor.config.test_name == 'quick_integration'
        assert executor.config.max_test_duration_minutes == 10
        assert executor.execution_id is not None
        
        print("   ✓ Test executor creation successful")
        
        # Test environment info gathering
        env_info = executor._gather_environment_info()
        assert 'python_version' in env_info
        assert 'platform' in env_info
        assert 'test_config' in env_info
        
        print("   ✓ Environment info gathering successful")
        return True
        
    except Exception as e:
        print(f"   ❌ Test runner validation failed: {e}")
        traceback.print_exc()
        return False

def validate_performance_monitoring():
    """Validate performance monitoring capabilities."""
    print("📊 Validating performance monitoring...")
    
    try:
        from tests.test_performance_integration import PerformanceMonitor, PerformanceMetrics
        import time
        
        # Test performance monitor
        monitor = PerformanceMonitor()
        monitor.start_monitoring()
        time.sleep(0.1)  # Small delay
        execution_time, memory_usage, cpu_usage = monitor.stop_monitoring()
        
        assert execution_time > 0
        assert isinstance(memory_usage, (int, float))
        assert isinstance(cpu_usage, (int, float))
        
        print(f"   ✓ Performance monitoring working: {execution_time:.3f}s execution time")
        
        # Test performance metrics
        metrics = PerformanceMetrics(
            operation_name="test_operation",
            execution_time=execution_time,
            memory_usage_mb=abs(memory_usage),
            cpu_usage_percent=abs(cpu_usage),
            throughput_ops_per_sec=1.0 / execution_time if execution_time > 0 else 0,
            success_rate=100.0,
            error_count=0
        )
        
        metrics_dict = metrics.to_dict()
        assert 'operation_name' in metrics_dict
        assert 'execution_time' in metrics_dict
        
        print("   ✓ Performance metrics structure validated")
        return True
        
    except Exception as e:
        print(f"   ❌ Performance monitoring validation failed: {e}")
        traceback.print_exc()
        return False

def validate_documentation():
    """Validate documentation completeness."""
    print("📚 Validating documentation...")
    
    try:
        # Check test plan exists
        test_plan = PROJECT_ROOT / 'tests' / 'integration_test_plan.md'
        assert test_plan.exists(), "Integration test plan missing"
        
        # Check main runner script exists
        runner_script = PROJECT_ROOT / 'run_integration_tests.py'
        assert runner_script.exists(), "Main runner script missing"
        
        # Check key test files exist
        key_files = [
            'tests/integration_environment_setup.py',
            'tests/integration_config.py',
            'tests/integration_test_runner.py',
            'tests/test_component_interactions.py',
            'tests/test_end_to_end_scenarios.py',
            'tests/test_performance_integration.py',
            'tests/test_regression_integration.py'
        ]
        
        for file_path in key_files:
            file_obj = PROJECT_ROOT / file_path
            assert file_obj.exists(), f"Missing key file: {file_path}"
        
        print(f"   ✓ Test plan and {len(key_files)} key files validated")
        
        # Check test plan content
        with open(test_plan, 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'Integration Test Plan' in content
            assert 'sandwich' in content.lower()  # Testing approach
            assert 'CI-01' in content  # Component interaction tests
            assert 'E2E-01' in content  # End-to-end tests
        
        print("   ✓ Test plan content validated")
        return True
        
    except Exception as e:
        print(f"   ❌ Documentation validation failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Main validation function."""
    print("🚀 Task 20 Integration Testing Framework Validation")
    print("=" * 60)
    print()
    
    validations = [
        validate_imports,
        validate_environment_setup,
        validate_test_configurations,
        validate_test_runner,
        validate_performance_monitoring,
        validate_documentation
    ]
    
    passed = 0
    failed = 0
    
    for validation in validations:
        try:
            if validation():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"   ❌ Validation {validation.__name__} crashed: {e}")
            failed += 1
        print()
    
    print("📋 Validation Summary")
    print("-" * 30)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Success Rate: {(passed / (passed + failed) * 100):.1f}%")
    
    if failed == 0:
        print("\n🎉 ALL VALIDATIONS PASSED!")
        print("Task 20 Integration Testing Framework is READY! 🚀")
        return True
    else:
        print(f"\n⚠️  {failed} validations failed. Please review and fix issues.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 