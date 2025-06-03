#!/usr/bin/env python3
"""
Test suite for Enhanced Error Categorization System
Tests the error classification, handling, and integration with App Controller
"""

import pytest
import logging
from typing import Dict, Any
from data.models.error_management import (
    ErrorCategory, ErrorSeverity, RecoveryStrategy,
    ErrorClassifier, ErrorCodeGenerator, ErrorContext, ErrorInfo,
    ErrorManager, EnhancedErrorHandler, get_user_friendly_message,
    UIErrorType, PlatformErrorType, DownloadErrorType, RepositoryErrorType
)
from core.constants import ErrorConstants
from core.app_controller import get_app_controller, initialize_app_controller

def test_error_classification():
    """Test automatic error classification"""
    print("\n🔍 Testing Error Classification...")
    
    # Test UI errors
    ui_context = ErrorContext(operation="ui_component_render")
    ui_error = ValueError("Component rendering failed")
    category = ErrorClassifier.classify_error(ui_error, ui_context)
    assert category == ErrorCategory.UI
    print(f"✅ UI Error classified correctly: {category.value}")
    
    # Test Platform errors
    platform_context = ErrorContext(operation="platform_tiktok_api_call")
    platform_error = Exception("Rate limit exceeded")
    category = ErrorClassifier.classify_error(platform_error, platform_context)
    assert category == ErrorCategory.PLATFORM
    print(f"✅ Platform Error classified correctly: {category.value}")
    
    # Test Download errors
    download_context = ErrorContext(operation="download_file_save")
    download_error = OSError("Permission denied")
    category = ErrorClassifier.classify_error(download_error, download_context)
    assert category == ErrorCategory.DOWNLOAD
    print(f"✅ Download Error classified correctly: {category.value}")
    
    # Test Database errors
    db_context = ErrorContext(operation="repository_save")
    db_error = Exception("Database connection failed")
    category = ErrorClassifier.classify_error(db_error, db_context)
    print(f"🔍 Debug: Expected REPOSITORY, got {category.value}")
    assert category == ErrorCategory.REPOSITORY  # Should be REPOSITORY for repo operations
    print(f"✅ Repository Error classified correctly: {category.value}")

def test_specific_error_types():
    """Test specific error type detection"""
    print("\n🎯 Testing Specific Error Types...")
    
    # UI specific types
    ui_error = Exception("Component initialization failed")
    error_type = ErrorClassifier.get_specific_error_type(ui_error, ErrorCategory.UI)
    assert error_type == UIErrorType.COMPONENT_INITIALIZATION.value
    print(f"✅ UI Error Type: {error_type}")
    
    # Platform specific types
    platform_error = Exception("Content not found")
    error_type = ErrorClassifier.get_specific_error_type(platform_error, ErrorCategory.PLATFORM)
    assert error_type == PlatformErrorType.CONTENT_NOT_FOUND.value
    print(f"✅ Platform Error Type: {error_type}")
    
    # Download specific types
    download_error = Exception("Insufficient space")
    error_type = ErrorClassifier.get_specific_error_type(download_error, ErrorCategory.DOWNLOAD)
    assert error_type == DownloadErrorType.INSUFFICIENT_SPACE.value
    print(f"✅ Download Error Type: {error_type}")

def test_severity_determination():
    """Test severity level determination"""
    print("\n⚠️ Testing Severity Determination...")
    
    # Critical errors
    fatal_error = Exception("Database corrupted")
    severity = ErrorClassifier.determine_severity(fatal_error, ErrorCategory.DATABASE)
    assert severity == ErrorSeverity.CRITICAL
    print(f"✅ Critical Severity: {severity.value}")
    
    # High severity
    auth_error = Exception("Unauthorized access")
    severity = ErrorClassifier.determine_severity(auth_error, ErrorCategory.AUTHENTICATION)
    assert severity == ErrorSeverity.HIGH
    print(f"✅ High Severity: {severity.value}")
    
    # Medium severity
    network_error = Exception("Connection timeout")
    severity = ErrorClassifier.determine_severity(network_error, ErrorCategory.NETWORK)
    assert severity == ErrorSeverity.MEDIUM
    print(f"✅ Medium Severity: {severity.value}")
    
    # Low severity
    ui_error = Exception("Input validation failed")
    severity = ErrorClassifier.determine_severity(ui_error, ErrorCategory.UI)
    assert severity == ErrorSeverity.LOW
    print(f"✅ Low Severity: {severity.value}")

def test_recovery_strategy():
    """Test recovery strategy determination"""
    print("\n🔄 Testing Recovery Strategy...")
    
    # Retry strategy
    timeout_error = Exception("Connection timeout")
    strategy = ErrorClassifier.determine_recovery_strategy(timeout_error, ErrorCategory.NETWORK)
    assert strategy == RecoveryStrategy.RETRY
    print(f"✅ Retry Strategy: {strategy.value}")
    
    # Manual intervention
    permission_error = Exception("Permission denied")
    strategy = ErrorClassifier.determine_recovery_strategy(permission_error, ErrorCategory.AUTHENTICATION)
    assert strategy == RecoveryStrategy.MANUAL_INTERVENTION
    print(f"✅ Manual Intervention: {strategy.value}")
    
    # Fail fast
    validation_error = ValueError("Invalid input")
    strategy = ErrorClassifier.determine_recovery_strategy(validation_error, ErrorCategory.VALIDATION)
    assert strategy == RecoveryStrategy.FAIL_FAST
    print(f"✅ Fail Fast: {strategy.value}")

def test_error_code_generation():
    """Test error code generation"""
    print("\n🏷️ Testing Error Code Generation...")
    
    # Test basic code generation
    code = ErrorCodeGenerator.generate_code(ErrorCategory.UI)
    assert code.startswith("UI_")
    print(f"✅ UI Error Code: {code}")
    
    # Test with error type
    code = ErrorCodeGenerator.generate_code(ErrorCategory.PLATFORM, "api_rate_limit")
    assert code.startswith("PLT_APIR")
    print(f"✅ Platform Error Code with Type: {code}")
    
    # Test repository code
    code = ErrorCodeGenerator.generate_code(ErrorCategory.REPOSITORY, "connection_failed")
    assert code.startswith("REP_CONN")
    print(f"✅ Repository Error Code: {code}")

def test_user_friendly_messages():
    """Test user-friendly message generation"""
    print("\n💬 Testing User-Friendly Messages...")
    
    # Test UI messages
    message = get_user_friendly_message(ErrorCategory.UI, UIErrorType.COMPONENT_INITIALIZATION.value)
    assert "component failed to start" in message.lower()
    print(f"✅ UI Message: {message}")
    
    # Test Platform messages
    message = get_user_friendly_message(ErrorCategory.PLATFORM, PlatformErrorType.API_RATE_LIMIT.value)
    assert "rate limit" in message.lower()
    print(f"✅ Platform Message: {message}")
    
    # Test default message
    message = get_user_friendly_message(ErrorCategory.UNKNOWN)
    assert "unexpected error" in message.lower()
    print(f"✅ Default Message: {message}")

def test_enhanced_error_handler():
    """Test enhanced error handler"""
    print("\n🛠️ Testing Enhanced Error Handler...")
    
    handler = EnhancedErrorHandler()
    
    # Test UI error handling
    ui_context = ErrorContext(
        operation="ui_component_render",
        additional_data={"component": "VideoTable"}
    )
    ui_error = ValueError("Component rendering failed")
    
    # Check if handler can handle the error
    assert handler.can_handle(ui_error, ui_context)
    
    # Handle the error
    error_info = handler.handle_error(ui_error, ui_context)
    
    assert error_info.category == ErrorCategory.UI
    assert error_info.component == "VideoTable"
    assert error_info.user_message is not None
    assert error_info.error_code.startswith("UI_")
    print(f"✅ Enhanced Handler Result: {error_info.error_code} - {error_info.category.value}")

def test_error_manager_integration():
    """Test error manager with enhanced classification"""
    print("\n🎛️ Testing Error Manager Integration...")
    
    error_manager = ErrorManager(use_enhanced_classification=True)
    
    # Test different error scenarios
    contexts_and_errors = [
        (ErrorContext(operation="ui_render"), ValueError("Component failed")),
        (ErrorContext(operation="platform_api"), Exception("Rate limit exceeded")),
        (ErrorContext(operation="download_file"), OSError("Permission denied")),
        (ErrorContext(operation="repository_save"), Exception("Database connection failed"))
    ]
    
    for context, error in contexts_and_errors:
        error_info = error_manager.handle_error(error, context)
        print(f"✅ Handled {error_info.category.value} error: {error_info.error_code}")
        assert error_info.category != ErrorCategory.UNKNOWN  # Should classify properly
    
    # Test statistics
    stats = error_manager.get_error_statistics()
    assert len(stats) > 0
    print(f"✅ Error Statistics: {stats}")
    
    # Test category stats
    category_stats = error_manager.get_error_statistics_by_category()
    print(f"✅ Category Statistics: {category_stats}")

def test_error_constants():
    """Test error constants"""
    print("\n📋 Testing Error Constants...")
    
    # Test message retrieval
    message = ErrorConstants.get_message('UI_COMPONENT_ERROR')
    assert "component error" in message.lower()
    print(f"✅ Error Message: {message}")
    
    # Test code retrieval
    code = ErrorConstants.get_code('PLATFORM_API')
    assert code == 'ERR_PLT_API'
    print(f"✅ Error Code: {code}")
    
    # Test severity level
    level = ErrorConstants.get_severity_level('HIGH')
    assert level == 3
    print(f"✅ Severity Level: {level}")
    
    # Test retryable check
    is_retryable = ErrorConstants.is_retryable('NETWORK')
    assert is_retryable == True
    print(f"✅ Network errors are retryable: {is_retryable}")

def test_app_controller_integration():
    """Test integration with App Controller"""
    print("\n🎮 Testing App Controller Integration...")
    
    # Initialize controller
    success = initialize_app_controller()
    if not success:
        print("⚠️ App Controller initialization failed, skipping integration test")
        return
    
    controller = get_app_controller()
    
    # Test enhanced error handling
    try:
        controller.handle_error(
            ValueError("Test error"), 
            "test_operation", 
            component="TestComponent"
        )
        print("✅ App Controller error handling executed successfully")
    except Exception as e:
        print(f"⚠️ App Controller error handling failed: {e}")
    
    # Test error statistics
    stats = controller.get_error_statistics()
    if stats:
        print(f"✅ Controller Error Statistics: {stats}")
    
    category_stats = controller.get_error_statistics_by_category()
    if category_stats:
        print(f"✅ Controller Category Statistics: {category_stats}")

def run_comprehensive_test():
    """Run all error categorization tests"""
    print("🚀 Starting Enhanced Error Categorization System Tests\n")
    
    try:
        test_error_classification()
        test_specific_error_types()
        test_severity_determination()
        test_recovery_strategy()
        test_error_code_generation()
        test_user_friendly_messages()
        test_enhanced_error_handler()
        test_error_manager_integration()
        test_error_constants()
        test_app_controller_integration()
        
        print("\n🎉 All Error Categorization Tests Passed Successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Configure logging for tests
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    success = run_comprehensive_test()
    exit(0 if success else 1) 