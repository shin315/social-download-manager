#!/usr/bin/env python3
"""
Simple Test for Task 19 Error Handling System
Checks each component individually to identify any issues
"""

import sys
import traceback

def test_error_categorization():
    """Test error categorization components"""
    try:
        print("🔍 Testing Error Categorization...")
        from core.error_categorization import ErrorCategory, ErrorClassifier, ErrorInfo, ErrorContext
        
        # Test classification
        context = ErrorContext(operation="test_ui_operation")
        error = ValueError("Test error")
        category = ErrorClassifier.classify_error(error, context)
        
        print(f"  ✅ Error categorization working: {category}")
        return True
    except Exception as e:
        print(f"  ❌ Error categorization failed: {e}")
        traceback.print_exc()
        return False

def test_logging_strategy():
    """Test logging strategy components"""
    try:
        print("🔍 Testing Logging Strategy...")
        from core.logging_strategy import get_enhanced_logger
        
        logger = get_enhanced_logger("test")
        logger.info("Test log message")
        
        print("  ✅ Logging strategy working")
        return True
    except Exception as e:
        print(f"  ❌ Logging strategy failed: {e}")
        traceback.print_exc()
        return False

def test_user_feedback():
    """Test user feedback components"""
    try:
        print("🔍 Testing User Feedback...")
        from core.user_feedback import UserFeedbackManager, MessageDetailLevel, UserRole, UserContext, MessageType
        from core.error_categorization import ErrorCategory, ErrorInfo, ErrorContext, ErrorSeverity
        
        manager = UserFeedbackManager()
        
        # Create a simple error info
        context = ErrorContext(operation="test_operation")
        error_info = ErrorInfo(
            error_id="test123",
            error_code="TEST_ERR",
            message="Test error message",
            category=ErrorCategory.UI,
            severity=ErrorSeverity.MEDIUM,  # Use correct enum
            context=context
        )
        
        # Create user context
        user_context = UserContext(
            user_role=UserRole.END_USER,
            detail_level=MessageDetailLevel.STANDARD
        )
        
        message = manager.generate_user_message(  # Correct method signature
            error_info,
            user_context=user_context,
            message_type=MessageType.MODAL
        )
        
        print(f"  ✅ User feedback working: Generated message")
        return True
    except Exception as e:
        print(f"  ❌ User feedback failed: {e}")
        traceback.print_exc()
        return False

def test_recovery_procedures():
    """Test recovery procedures components"""
    try:
        print("🔍 Testing Recovery Procedures...")
        from core.recovery_strategies import RecoveryAction, RecoveryExecutor
        from core.recovery_engine import AutoRecoveryManager
        
        executor = RecoveryExecutor()
        manager = AutoRecoveryManager()
        
        print("  ✅ Recovery procedures working")
        return True
    except Exception as e:
        print(f"  ❌ Recovery procedures failed: {e}")
        traceback.print_exc()
        return False

def test_global_error_handlers():
    """Test global error handlers"""
    try:
        print("🔍 Testing Global Error Handlers...")
        from core.global_error_handler import GlobalErrorHandler
        
        handler = GlobalErrorHandler()
        
        print("  ✅ Global error handlers working")
        return True
    except Exception as e:
        print(f"  ❌ Global error handlers failed: {e}")
        traceback.print_exc()
        return False

def test_component_handlers():
    """Test component-specific handlers"""
    try:
        print("🔍 Testing Component Handlers...")
        from core.component_error_handlers import ComponentErrorHandler, ComponentErrorConfig
        from core.error_categorization import ErrorCategory
        
        # Create proper config object
        config = ComponentErrorConfig(
            component_name="test_component",
            error_category=ErrorCategory.UI,
            max_retries=3
        )
        handler = ComponentErrorHandler(config)
        
        print("  ✅ Component handlers working")
        return True
    except Exception as e:
        print(f"  ❌ Component handlers failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all component tests"""
    print("🚀 Starting Task 19 Error Handling System Check")
    print("=" * 60)
    
    tests = [
        test_error_categorization,
        test_logging_strategy,
        test_user_feedback,
        test_recovery_procedures,
        test_global_error_handlers,
        test_component_handlers,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()  # Empty line between tests
    
    print("=" * 60)
    print(f"📊 TASK 19 COMPONENT CHECK SUMMARY")
    print(f"Total Components: {total}")
    print(f"Working: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 All error handling components are working perfectly!")
        return True
    else:
        print("⚠️  Some components need attention.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 