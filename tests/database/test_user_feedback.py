"""
Comprehensive Test Suite for User Feedback Mechanisms

Tests the user feedback system including message generation, templates,
UI components, and integration with error management.
"""

import os
import sys
import json
import tempfile
import shutil
import tkinter as tk
from unittest.mock import Mock, patch
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

from core.user_feedback import (
    UserMessage, MessageType, UserRole, MessageDetailLevel, UserContext,
    MessageTemplate, UserFeedbackManager, generate_user_friendly_message,
    get_error_recovery_suggestions, get_feedback_manager
)
from ui.components.error_feedback import (
    ErrorMessageDialog, ErrorToastNotification, InlineErrorDisplay,
    ErrorBanner, ErrorFeedbackManager, show_error_dialog
)
from data.models.error_management import (
    ErrorInfo, ErrorCategory, ErrorSeverity, ErrorContext, RecoveryStrategy
)


class TestUserFeedback:
    """Test suite for user feedback mechanisms"""
    
    def __init__(self):
        self.test_results = []
        self.root = None
    
    def setup_test_environment(self):
        """Setup test environment"""
        # Create tkinter root for UI tests (but don't show it)
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the window
        print("Test environment setup complete")
    
    def cleanup_test_environment(self):
        """Cleanup test environment"""
        if self.root:
            self.root.destroy()
        print("Test environment cleaned up")
    
    def log_test_result(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            'test': test_name,
            'status': status,
            'success': success,
            'details': details
        }
        self.test_results.append(result)
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
    
    def test_user_message_creation(self):
        """Test UserMessage dataclass creation and properties"""
        try:
            message = UserMessage(
                title="Test Error",
                message="This is a test error message",
                action_text="Try again",
                error_code="TEST_001",
                severity_icon="⚠️",
                severity_color="#FF9800",
                contact_support=True,
                retry_available=True
            )
            
            if (message.title == "Test Error" and 
                message.message == "This is a test error message" and
                message.contact_support == True and
                message.retry_available == True):
                self.log_test_result("User Message Creation", True)
            else:
                self.log_test_result("User Message Creation", False, "Message properties not set correctly")
        
        except Exception as e:
            self.log_test_result("User Message Creation", False, f"Exception: {str(e)}")
    
    def test_user_context(self):
        """Test UserContext configuration"""
        try:
            context = UserContext(
                user_role=UserRole.POWER_USER,
                detail_level=MessageDetailLevel.DETAILED,
                language="en",
                accessibility_mode=True
            )
            
            if (context.user_role == UserRole.POWER_USER and
                context.detail_level == MessageDetailLevel.DETAILED and
                context.accessibility_mode == True):
                self.log_test_result("User Context", True)
            else:
                self.log_test_result("User Context", False, "Context properties not set correctly")
        
        except Exception as e:
            self.log_test_result("User Context", False, f"Exception: {str(e)}")
    
    def test_message_template_generation(self):
        """Test message template generation for different categories"""
        try:
            # Test UI error template
            ui_template = MessageTemplate(ErrorCategory.UI)
            
            error_context = ErrorContext(operation="button_click")
            error_info = ErrorInfo(
                error_id="UI_TEST_001",
                error_code="UI_COMPONENT_ERROR",
                message="Button click failed",
                category=ErrorCategory.UI,
                severity=ErrorSeverity.MEDIUM,
                context=error_context,
                recovery_strategy=RecoveryStrategy.RETRY
            )
            
            user_context = UserContext(detail_level=MessageDetailLevel.STANDARD)
            message = ui_template.generate_message(error_info, user_context)
            
            if (message.title == "Interface Issue" and
                "user interface" in message.message.lower() and
                message.retry_available == True):
                self.log_test_result("Message Template - UI Category", True)
            else:
                self.log_test_result("Message Template - UI Category", False, f"Template generation failed: {message.title}")
            
            # Test Platform error template
            platform_template = MessageTemplate(ErrorCategory.PLATFORM)
            platform_error = ErrorInfo(
                error_id="PLT_TEST_001",
                error_code="API_ERROR",
                message="API call failed",
                category=ErrorCategory.PLATFORM,
                severity=ErrorSeverity.HIGH,
                context=error_context,
                recovery_strategy=RecoveryStrategy.RETRY
            )
            
            platform_message = platform_template.generate_message(platform_error, user_context)
            
            if (platform_message.title == "Service Connection Issue" and
                "video platform" in platform_message.message.lower()):
                self.log_test_result("Message Template - Platform Category", True)
            else:
                self.log_test_result("Message Template - Platform Category", False, "Platform template failed")
        
        except Exception as e:
            self.log_test_result("Message Template Generation", False, f"Exception: {str(e)}")
    
    def test_technical_details_generation(self):
        """Test technical details generation for different user roles"""
        try:
            template = MessageTemplate(ErrorCategory.DOWNLOAD)
            
            error_info = ErrorInfo(
                error_id="DWN_TEST_001",
                error_code="DOWNLOAD_FAILED",
                message="Download failed",
                category=ErrorCategory.DOWNLOAD,
                severity=ErrorSeverity.HIGH,
                context=ErrorContext(operation="file_download"),
                recovery_strategy=RecoveryStrategy.RETRY,
                component="download_service",
                error_type="NETWORK_TIMEOUT"
            )
            
            # Test for end user (should not show technical details)
            end_user_context = UserContext(
                user_role=UserRole.END_USER,
                detail_level=MessageDetailLevel.STANDARD
            )
            end_user_message = template.generate_message(error_info, end_user_context)
            
            # Test for developer (should show technical details)
            dev_context = UserContext(
                user_role=UserRole.DEVELOPER,
                detail_level=MessageDetailLevel.DETAILED
            )
            dev_message = template.generate_message(error_info, dev_context)
            
            if (end_user_message.technical_details is None and
                dev_message.technical_details is not None and
                "DWN_TEST_001" in dev_message.technical_details):
                self.log_test_result("Technical Details Generation", True)
            else:
                self.log_test_result("Technical Details Generation", False, 
                                   f"End user: {end_user_message.technical_details}, Dev: {dev_message.technical_details}")
        
        except Exception as e:
            self.log_test_result("Technical Details Generation", False, f"Exception: {str(e)}")
    
    def test_user_feedback_manager(self):
        """Test UserFeedbackManager functionality"""
        try:
            manager = UserFeedbackManager()
            
            # Test message generation
            error_info = ErrorInfo(
                error_id="MGR_TEST_001",
                error_code="MANAGER_TEST",
                message="Manager test error",
                category=ErrorCategory.SERVICE,
                severity=ErrorSeverity.MEDIUM,
                context=ErrorContext(operation="test_operation"),
                recovery_strategy=RecoveryStrategy.RETRY
            )
            
            user_context = UserContext(user_role=UserRole.END_USER)
            message = manager.generate_user_message(error_info, user_context, MessageType.MODAL)
            
            if (message.title == "Service Error" and
                "service" in message.message.lower()):
                self.log_test_result("User Feedback Manager - Message Generation", True)
            else:
                self.log_test_result("User Feedback Manager - Message Generation", False, "Message generation failed")
            
            # Test recovery suggestions
            suggestions = manager.get_recovery_suggestions(error_info)
            
            if isinstance(suggestions, list) and len(suggestions) > 0:
                self.log_test_result("User Feedback Manager - Recovery Suggestions", True, f"Got {len(suggestions)} suggestions")
            else:
                self.log_test_result("User Feedback Manager - Recovery Suggestions", False, "No suggestions generated")
        
        except Exception as e:
            self.log_test_result("User Feedback Manager", False, f"Exception: {str(e)}")
    
    def test_convenience_functions(self):
        """Test convenience functions"""
        try:
            error_info = ErrorInfo(
                error_id="CONV_TEST_001",
                error_code="CONVENIENCE_TEST",
                message="Convenience function test",
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.HIGH,
                context=ErrorContext(operation="login"),
                recovery_strategy=RecoveryStrategy.MANUAL_INTERVENTION
            )
            
            # Test generate_user_friendly_message
            message = generate_user_friendly_message(
                error_info,
                UserRole.POWER_USER,
                MessageDetailLevel.DETAILED,
                MessageType.TOAST
            )
            
            if (message.title == "Authentication Required" and
                "log in" in message.message.lower()):
                self.log_test_result("Convenience Functions - Message Generation", True)
            else:
                self.log_test_result("Convenience Functions - Message Generation", False, "Function failed")
            
            # Test get_error_recovery_suggestions
            suggestions = get_error_recovery_suggestions(error_info)
            
            if isinstance(suggestions, list):
                self.log_test_result("Convenience Functions - Recovery Suggestions", True)
            else:
                self.log_test_result("Convenience Functions - Recovery Suggestions", False, "Function failed")
        
        except Exception as e:
            self.log_test_result("Convenience Functions", False, f"Exception: {str(e)}")
    
    def test_accessibility_formatting(self):
        """Test accessibility formatting"""
        try:
            manager = UserFeedbackManager()
            
            error_info = ErrorInfo(
                error_id="ACC_TEST_001",
                error_code="ACCESSIBILITY_TEST",
                message="Accessibility test error",
                category=ErrorCategory.UI,
                severity=ErrorSeverity.HIGH,
                context=ErrorContext(operation="form_validation"),
                recovery_strategy=RecoveryStrategy.FAIL_FAST
            )
            
            message = manager.generate_user_message(error_info)
            accessible_format = manager.format_for_accessibility(message)
            
            if (isinstance(accessible_format, dict) and
                "aria_label" in accessible_format and
                "role" in accessible_format and
                accessible_format["role"] == "alert"):
                self.log_test_result("Accessibility Formatting", True)
            else:
                self.log_test_result("Accessibility Formatting", False, f"Format: {accessible_format}")
        
        except Exception as e:
            self.log_test_result("Accessibility Formatting", False, f"Exception: {str(e)}")
    
    def test_ui_component_creation(self):
        """Test UI component creation (without showing them)"""
        try:
            if not self.root:
                self.log_test_result("UI Component Creation", False, "No tkinter root available")
                return
            
            # Create test error info
            error_info = ErrorInfo(
                error_id="UI_COMP_TEST_001",
                error_code="UI_COMPONENT_TEST",
                message="UI component test error",
                category=ErrorCategory.DOWNLOAD,
                severity=ErrorSeverity.MEDIUM,
                context=ErrorContext(operation="file_download"),
                recovery_strategy=RecoveryStrategy.RETRY
            )
            
            # Generate user message
            user_message = generate_user_friendly_message(error_info)
            
            # Test ErrorMessageDialog creation (don't show)
            dialog = ErrorMessageDialog(self.root, user_message)
            if dialog.user_message.title == user_message.title:
                self.log_test_result("UI Component - Error Dialog Creation", True)
            else:
                self.log_test_result("UI Component - Error Dialog Creation", False, "Dialog creation failed")
            
            # Test ErrorToastNotification creation
            toast = ErrorToastNotification(self.root, user_message)
            if toast.user_message.message == user_message.message:
                self.log_test_result("UI Component - Toast Creation", True)
            else:
                self.log_test_result("UI Component - Toast Creation", False, "Toast creation failed")
            
            # Test InlineErrorDisplay creation
            inline = InlineErrorDisplay(self.root, user_message)
            if inline.user_message == user_message:
                self.log_test_result("UI Component - Inline Display Creation", True)
            else:
                self.log_test_result("UI Component - Inline Display Creation", False, "Inline creation failed")
            
            # Test ErrorBanner creation
            banner = ErrorBanner(self.root, user_message)
            if banner.user_message == user_message:
                self.log_test_result("UI Component - Banner Creation", True)
            else:
                self.log_test_result("UI Component - Banner Creation", False, "Banner creation failed")
        
        except Exception as e:
            self.log_test_result("UI Component Creation", False, f"Exception: {str(e)}")
    
    def test_error_feedback_manager_ui(self):
        """Test ErrorFeedbackManager UI functionality"""
        try:
            if not self.root:
                self.log_test_result("Error Feedback Manager UI", False, "No tkinter root available")
                return
            
            manager = ErrorFeedbackManager(self.root)
            
            error_info = ErrorInfo(
                error_id="EFM_TEST_001",
                error_code="EFM_UI_TEST",
                message="Error feedback manager test",
                category=ErrorCategory.PLATFORM,
                severity=ErrorSeverity.HIGH,
                context=ErrorContext(operation="api_call"),
                recovery_strategy=RecoveryStrategy.RETRY
            )
            
            # Test that manager can be created and methods exist
            if (hasattr(manager, 'show_error') and
                hasattr(manager, 'hide_error') and
                hasattr(manager, 'hide_all_errors')):
                self.log_test_result("Error Feedback Manager UI - Interface", True)
            else:
                self.log_test_result("Error Feedback Manager UI - Interface", False, "Missing methods")
            
            # Test active displays tracking
            initial_count = len(manager.active_displays)
            if initial_count == 0:
                self.log_test_result("Error Feedback Manager UI - State Tracking", True)
            else:
                self.log_test_result("Error Feedback Manager UI - State Tracking", False, f"Initial count: {initial_count}")
        
        except Exception as e:
            self.log_test_result("Error Feedback Manager UI", False, f"Exception: {str(e)}")
    
    def test_message_customization(self):
        """Test message customization for different error types and operations"""
        try:
            template = MessageTemplate(ErrorCategory.DOWNLOAD)
            
            # Test with specific error type
            error_info = ErrorInfo(
                error_id="CUST_TEST_001",
                error_code="NETWORK_TIMEOUT",
                message="Connection timed out",
                category=ErrorCategory.DOWNLOAD,
                severity=ErrorSeverity.MEDIUM,
                context=ErrorContext(operation="download"),
                recovery_strategy=RecoveryStrategy.RETRY,
                error_type="NETWORK_TIMEOUT"
            )
            
            user_context = UserContext()
            message = template.generate_message(error_info, user_context)
            
            # Check if message was customized for network timeout
            customized = "connection timed out" in message.message.lower()
            
            if customized:
                self.log_test_result("Message Customization - Error Type", True)
            else:
                self.log_test_result("Message Customization - Error Type", False, f"Message: {message.message}")
            
            # Test operation context addition
            if "while downloading" in message.message:
                self.log_test_result("Message Customization - Operation Context", True)
            else:
                self.log_test_result("Message Customization - Operation Context", False, "No operation context added")
        
        except Exception as e:
            self.log_test_result("Message Customization", False, f"Exception: {str(e)}")
    
    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting User Feedback Mechanisms Test Suite")
        print("=" * 60)
        
        self.setup_test_environment()
        
        try:
            # Run individual tests
            self.test_user_message_creation()
            self.test_user_context()
            self.test_message_template_generation()
            self.test_technical_details_generation()
            self.test_user_feedback_manager()
            self.test_convenience_functions()
            self.test_accessibility_formatting()
            self.test_ui_component_creation()
            self.test_error_feedback_manager_ui()
            self.test_message_customization()
            
        finally:
            self.cleanup_test_environment()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['test']}: {result['details']}")
        
        print("\n✅ PASSED TESTS:")
        for result in self.test_results:
            if result['success']:
                print(f"  - {result['test']}")
        
        return passed_tests == total_tests


def main():
    """Main test execution"""
    test_suite = TestUserFeedback()
    success = test_suite.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed! User Feedback Mechanisms implementation is working correctly.")
        print("\nKey Features Tested:")
        print("✅ User message creation and properties")
        print("✅ User context configuration")
        print("✅ Message template generation for all error categories")
        print("✅ Technical details generation based on user roles")
        print("✅ User feedback manager functionality")
        print("✅ Convenience functions for easy integration")
        print("✅ Accessibility formatting support")
        print("✅ UI component creation and management")
        print("✅ Message customization for different error types")
        print("✅ Operation context integration")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please review the implementation.")
        return 1


if __name__ == "__main__":
    exit(main()) 