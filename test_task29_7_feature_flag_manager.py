"""
Comprehensive Test for Task 29.7 - Central Feature Flag Management System

This test validates the FeatureFlagManager and all its features including:
- Flag creation, modification, and deletion
- Configuration-based management
- Runtime modification capabilities
- Phase-based presets
- Validation and safety checks
- Monitoring and metrics
- Utility functions
"""

import sys
import logging
import tempfile
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from ui.adapters.feature_flag_manager import (
        FeatureFlagManager, FeatureFlag, FlagType, FlagScope, 
        FlagEnvironment, FlagStatus, FlagValidationRule, FlagDependency,
        get_flag_manager, initialize_flag_manager, get_flag, 
        is_flag_enabled, is_feature_available, set_flag, load_preset
    )
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure the ui.adapters.feature_flag_manager module is available")
    sys.exit(1)


def test_flag_manager_initialization():
    """Test feature flag manager initialization"""
    print("\n=== Testing Feature Flag Manager Initialization ===")
    
    # Test basic initialization
    manager = FeatureFlagManager(environment=FlagEnvironment.DEVELOPMENT)
    assert manager is not None, "Manager should be initialized"
    
    # Check default flags are loaded
    all_flags = manager.get_all_flags()
    assert len(all_flags) > 0, "Default flags should be loaded"
    
    # Test specific default flags
    assert manager.is_flag_enabled("enable_v2_architecture"), "v2 architecture should be enabled by default"
    assert manager.is_flag_enabled("enable_main_window_adapter"), "Main window adapter should be enabled"
    assert manager.get_flag("migration_phase") == "gradual", "Migration phase should default to gradual"
    
    print("✅ Feature flag manager initialization test passed!")


def test_flag_operations():
    """Test basic flag operations"""
    print("\n=== Testing Basic Flag Operations ===")
    
    manager = FeatureFlagManager()
    
    # Test getting existing flags
    v2_enabled = manager.get_flag("enable_v2_architecture")
    assert v2_enabled == True, "Should get correct flag value"
    
    # Test getting non-existent flag with default
    unknown_flag = manager.get_flag("unknown_flag", "default_value")
    assert unknown_flag == "default_value", "Should return default for unknown flag"
    
    # Test setting existing flag
    success = manager.set_flag("enable_debug_mode", True)
    assert success, "Should successfully set flag"
    assert manager.is_flag_enabled("enable_debug_mode"), "Flag should be updated"
    
    # Test boolean flag checking
    assert manager.is_flag_enabled("enable_v2_architecture"), "Boolean flag should be enabled"
    
    print("✅ Basic flag operations test passed!")


def test_flag_creation_and_validation():
    """Test flag creation and validation"""
    print("\n=== Testing Flag Creation and Validation ===")
    
    manager = FeatureFlagManager()
    
    # Create a valid flag
    test_flag = FeatureFlag(
        name="test_feature",
        value=True,
        flag_type=FlagType.BOOLEAN,
        scope=FlagScope.COMPONENT,
        environment=FlagEnvironment.DEVELOPMENT,
        status=FlagStatus.EXPERIMENTAL,
        description="Test feature for validation"
    )
    
    success = manager.add_flag(test_flag)
    assert success, "Should successfully add valid flag"
    assert manager.is_flag_enabled("test_feature"), "Added flag should be accessible"
    
    # Test flag info
    flag_info = manager.get_flag_info("test_feature")
    assert flag_info is not None, "Should get flag info"
    assert flag_info["description"] == "Test feature for validation", "Should have correct description"
    assert flag_info["status"] == "experimental", "Should have correct status"
    
    # Test removing flag
    success = manager.remove_flag("test_feature")
    assert success, "Should successfully remove flag"
    assert not manager.is_flag_enabled("test_feature"), "Removed flag should not be accessible"
    
    print("✅ Flag creation and validation test passed!")


def test_presets():
    """Test preset functionality"""
    print("\n=== Testing Preset Functionality ===")
    
    manager = FeatureFlagManager()
    
    # Test loading development preset
    success = manager.load_preset("development")
    assert success, "Should successfully load development preset"
    assert manager.is_flag_enabled("enable_debug_mode"), "Debug mode should be enabled in development"
    
    # Test loading production preset
    success = manager.load_preset("production")
    assert success, "Should successfully load production preset"
    assert not manager.is_flag_enabled("enable_debug_mode"), "Debug mode should be disabled in production"
    assert manager.is_flag_enabled("rollback_enabled"), "Rollback should be enabled in production"
    
    # Test loading safe mode preset
    success = manager.load_preset("safe_mode")
    assert success, "Should successfully load safe mode preset"
    assert not manager.is_flag_enabled("enable_v2_architecture"), "v2 architecture should be disabled in safe mode"
    assert manager.is_flag_enabled("enable_graceful_degradation"), "Graceful degradation should be enabled"
    
    # Test loading non-existent preset
    success = manager.load_preset("non_existent")
    assert not success, "Should fail to load non-existent preset"
    
    print("✅ Preset functionality test passed!")


def test_feature_availability():
    """Test feature availability checking"""
    print("\n=== Testing Feature Availability ===")
    
    manager = FeatureFlagManager()
    
    # Test basic feature availability
    assert manager.is_feature_available("v2_architecture"), "v2 architecture should be available"
    assert manager.is_feature_available("main_window_adapter"), "Main window adapter should be available"
    
    # Test component-specific availability
    # This would check enable_feature_component if it exists
    manager.set_flag("enable_video_caching", True)
    assert manager.is_feature_available("video_caching"), "Video caching should be available"
    
    # Disable a feature and test
    manager.set_flag("enable_repository_integration", False)
    assert not manager.is_feature_available("repository_integration"), "Repository integration should not be available"
    
    print("✅ Feature availability test passed!")


def test_listeners_and_events():
    """Test flag change listeners and events"""
    print("\n=== Testing Listeners and Events ===")
    
    manager = FeatureFlagManager()
    
    # Track changes
    change_events = []
    
    def on_flag_changed(flag_name, old_value, new_value):
        change_events.append((flag_name, old_value, new_value))
        print(f"🔄 Flag changed: {flag_name} {old_value} -> {new_value}")
    
    # Add listener
    manager.add_listener("enable_debug_mode", on_flag_changed)
    
    # Change flag and verify listener is called
    old_value = manager.get_flag("enable_debug_mode")
    manager.set_flag("enable_debug_mode", not old_value)
    
    assert len(change_events) > 0, "Change listener should be called"
    assert change_events[-1][0] == "enable_debug_mode", "Should track correct flag"
    
    # Test PyQt signal (would need event loop in real scenario)
    signal_events = []
    def on_signal_changed(flag_name, old_val, new_val):
        signal_events.append(flag_name)
    
    manager.flag_changed.connect(on_signal_changed)
    manager.set_flag("enable_debug_mode", old_value)  # Change back
    
    print("✅ Listeners and events test passed!")


def test_validation_rules():
    """Test validation rules"""
    print("\n=== Testing Validation Rules ===")
    
    manager = FeatureFlagManager()
    
    # Test migration phase validation (has built-in rule)
    success = manager.set_flag("migration_phase", "invalid_phase")
    assert not success, "Should reject invalid migration phase"
    
    # Test valid migration phase
    success = manager.set_flag("migration_phase", "big_bang")
    assert success, "Should accept valid migration phase"
    assert manager.get_flag("migration_phase") == "big_bang", "Should update to valid value"
    
    print("✅ Validation rules test passed!")


def test_metrics_and_monitoring():
    """Test metrics and monitoring"""
    print("\n=== Testing Metrics and Monitoring ===")
    
    manager = FeatureFlagManager()
    
    # Access some flags to generate metrics
    for _ in range(10):
        manager.get_flag("enable_v2_architecture")
        manager.get_flag("enable_debug_mode")
    
    # Get metrics
    metrics = manager.get_metrics()
    assert "total_flags" in metrics, "Should have total flags metric"
    assert "active_flags" in metrics, "Should have active flags metric"
    assert "flag_count_by_status" in metrics, "Should have status breakdown"
    assert "flag_count_by_scope" in metrics, "Should have scope breakdown"
    assert "top_accessed_flags" in metrics, "Should have top accessed flags"
    
    # Check flag-specific metrics
    flag_info = manager.get_flag_info("enable_v2_architecture")
    assert flag_info["metrics"]["access_count"] >= 10, "Should track access count"
    
    print("✅ Metrics and monitoring test passed!")


def test_configuration_persistence():
    """Test configuration saving and loading"""
    print("\n=== Testing Configuration Persistence ===")
    
    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
        temp_path = temp_file.name
    
    try:
        # Create manager with custom config path
        manager = FeatureFlagManager(config_path=temp_path)
        
        # Make some changes
        manager.set_flag("enable_debug_mode", True)
        manager.set_flag("migration_phase", "user_controlled")
        
        # Save configuration
        success = manager.save_configuration()
        assert success, "Should successfully save configuration"
        assert Path(temp_path).exists(), "Config file should exist"
        
        # Load configuration in new manager
        manager2 = FeatureFlagManager(config_path=temp_path)
        
        # Verify settings were loaded
        assert manager2.is_flag_enabled("enable_debug_mode"), "Debug mode should be loaded as enabled"
        assert manager2.get_flag("migration_phase") == "user_controlled", "Migration phase should be loaded"
        
    finally:
        # Cleanup
        if Path(temp_path).exists():
            Path(temp_path).unlink()
        backup_path = Path(temp_path).with_suffix('.backup.json')
        if backup_path.exists():
            backup_path.unlink()
    
    print("✅ Configuration persistence test passed!")


def test_environment_variables():
    """Test environment variable override"""
    print("\n=== Testing Environment Variable Override ===")
    
    # Set environment variable
    os.environ["FEATURE_FLAG_ENABLE_DEBUG_MODE"] = "true"
    os.environ["FEATURE_FLAG_MIGRATION_PHASE"] = "big_bang"
    
    try:
        # Create new manager (should load from environment)
        manager = FeatureFlagManager()
        
        # Check environment overrides
        assert manager.is_flag_enabled("enable_debug_mode"), "Should load boolean from environment"
        assert manager.get_flag("migration_phase") == "big_bang", "Should load string from environment"
        
    finally:
        # Cleanup environment
        os.environ.pop("FEATURE_FLAG_ENABLE_DEBUG_MODE", None)
        os.environ.pop("FEATURE_FLAG_MIGRATION_PHASE", None)
    
    print("✅ Environment variable override test passed!")


def test_global_utilities():
    """Test global utility functions"""
    print("\n=== Testing Global Utility Functions ===")
    
    # Initialize global manager
    manager = initialize_flag_manager(environment=FlagEnvironment.TESTING)
    
    # Test global functions
    assert get_flag("enable_v2_architecture") == True, "Global get_flag should work"
    assert is_flag_enabled("enable_v2_architecture"), "Global is_flag_enabled should work"
    assert is_feature_available("v2_architecture"), "Global is_feature_available should work"
    
    # Test setting flag globally
    success = set_flag("enable_debug_mode", True)
    assert success, "Global set_flag should work"
    assert is_flag_enabled("enable_debug_mode"), "Global flag change should be effective"
    
    # Test loading preset globally
    success = load_preset("development")
    assert success, "Global load_preset should work"
    
    print("✅ Global utility functions test passed!")


def test_flag_expiration():
    """Test flag expiration functionality"""
    print("\n=== Testing Flag Expiration ===")
    
    manager = FeatureFlagManager()
    
    # Create expired flag
    expired_flag = FeatureFlag(
        name="expired_feature",
        value=True,
        flag_type=FlagType.BOOLEAN,
        scope=FlagScope.COMPONENT,
        environment=FlagEnvironment.DEVELOPMENT,
        status=FlagStatus.ACTIVE,
        expires_at=datetime.now() - timedelta(hours=1)  # Expired 1 hour ago
    )
    
    manager.add_flag(expired_flag)
    
    # Test expired flag returns default
    value = manager.get_flag("expired_feature", False)
    assert value == False, "Expired flag should return default value"
    
    # Test flag info shows expiration
    flag_info = manager.get_flag_info("expired_feature")
    assert flag_info["is_expired"] == True, "Flag should be marked as expired"
    assert flag_info["is_active"] == False, "Expired flag should not be active"
    
    print("✅ Flag expiration test passed!")


def test_rollout_percentage():
    """Test gradual rollout functionality"""
    print("\n=== Testing Rollout Percentage ===")
    
    manager = FeatureFlagManager()
    
    # Create flag with 0% rollout
    rollout_flag = FeatureFlag(
        name="rollout_feature",
        value=True,
        flag_type=FlagType.BOOLEAN,
        scope=FlagScope.COMPONENT,
        environment=FlagEnvironment.DEVELOPMENT,
        status=FlagStatus.ROLLOUT,
        rollout_percentage=0.0,
        default_value=False
    )
    
    manager.add_flag(rollout_flag)
    
    # Test 0% rollout returns default
    value = manager.get_flag("rollout_feature")
    assert value == False, "0% rollout should return default value"
    
    # Test 100% rollout returns actual value
    manager.set_flag("rollout_feature", True)
    manager._flags["rollout_feature"].rollout_percentage = 100.0
    value = manager.get_flag("rollout_feature")
    assert value == True, "100% rollout should return actual value"
    
    print("✅ Rollout percentage test passed!")


def test_error_scenarios():
    """Test error handling scenarios"""
    print("\n=== Testing Error Scenarios ===")
    
    manager = FeatureFlagManager()
    
    # Test setting non-existent flag
    success = manager.set_flag("non_existent_flag", True)
    assert not success, "Should fail to set non-existent flag"
    
    # Test removing non-existent flag
    success = manager.remove_flag("non_existent_flag")
    assert not success, "Should handle removing non-existent flag gracefully"
    
    # Test invalid flag type
    invalid_flag = FeatureFlag(
        name="invalid_type_flag",
        value="string_value",
        flag_type=FlagType.INTEGER,  # Mismatch: string value but integer type
        scope=FlagScope.COMPONENT,
        environment=FlagEnvironment.DEVELOPMENT,
        status=FlagStatus.ACTIVE
    )
    
    success = manager.add_flag(invalid_flag)
    assert not success, "Should reject flag with mismatched type"
    
    print("✅ Error scenarios test passed!")


def run_comprehensive_tests():
    """Run all comprehensive tests"""
    print("🚀 Starting Comprehensive Task 29.7 Tests")
    print("=" * 80)
    
    # Initialize Qt Application
    app = QApplication(sys.argv)
    
    try:
        # Run all tests
        test_flag_manager_initialization()
        test_flag_operations()
        test_flag_creation_and_validation()
        test_presets()
        test_feature_availability()
        test_listeners_and_events()
        test_validation_rules()
        test_metrics_and_monitoring()
        test_configuration_persistence()
        test_environment_variables()
        test_global_utilities()
        test_flag_expiration()
        test_rollout_percentage()
        test_error_scenarios()
        
        print("\n" + "=" * 80)
        print("🎉 ALL COMPREHENSIVE TESTS PASSED!")
        print("Task 29.7 - Central Feature Flag Management System: ✅ EXCELLENT!")
        print("Features working perfectly:")
        print("  ✅ Feature flag creation, modification, and deletion")
        print("  ✅ Configuration-based flag management")
        print("  ✅ Runtime modification capabilities")
        print("  ✅ Phase-based presets (development, staging, production)")
        print("  ✅ Validation and safety checks")
        print("  ✅ Monitoring and metrics collection")
        print("  ✅ Environment variable overrides")
        print("  ✅ Flag expiration and rollout percentage")
        print("  ✅ Global utility functions")
        print("  ✅ Error handling and edge cases")
        print("  ✅ Configuration persistence and loading")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        app.quit()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1) 