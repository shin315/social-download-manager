"""
Simple Test Suite for User Feedback Core Mechanisms

Tests the core user feedback system without UI components to avoid circular imports.
"""

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

from core.user_feedback import (
    UserMessage, MessageType, UserRole, MessageDetailLevel, UserContext,
    MessageTemplate, UserFeedbackManager, generate_user_friendly_message,
    get_error_recovery_suggestions, get_feedback_manager
)
from data.models.error_management import (
    ErrorInfo, ErrorCategory, ErrorSeverity, ErrorContext, RecoveryStrategy
)


class TestUserFeedbackCore:
    """Test suite for core user feedback mechanisms"""
    
    def __init__(self):
        self.test_results = []
    
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
    
    def test_message_templates_all_categories(self):
        """Test message templates for all error categories"""
        try:
            categories_tested = 0
            categories_passed = 0
            
            # Test all major categories
            test_categories = [
                ErrorCategory.UI,
                ErrorCategory.PLATFORM,
                ErrorCategory.DOWNLOAD,
                ErrorCategory.REPOSITORY,
                ErrorCategory.SERVICE,
                ErrorCategory.AUTHENTICATION,
                ErrorCategory.PERMISSION,
                ErrorCategory.FILE_SYSTEM,
                ErrorCategory.PARSING,
                ErrorCategory.INTEGRATION,
                ErrorCategory.FATAL
            ]
            
            for category in test_categories:
                categories_tested += 1
                try:
                    template = MessageTemplate(category)
                    
                    error_info = ErrorInfo(
                        error_id=f"{category.value.upper()}_TEST_001",
                        error_code=f"{category.value.upper()}_ERROR",
                        message=f"Test {category.value} error",
                        category=category,
                        severity=ErrorSeverity.MEDIUM,
                        context=ErrorContext(operation="test_operation"),
                        recovery_strategy=RecoveryStrategy.RETRY
                    )
                    
                    user_context = UserContext(detail_level=MessageDetailLevel.STANDARD)
                    message = template.generate_message(error_info, user_context)
                    
                    if message.title and message.message and len(message.message) > 0:
                        categories_passed += 1
                    
                except Exception as e:
                    print(f"   Category {category.value} failed: {e}")
            
            if categories_passed == categories_tested:
                self.log_test_result("Message Templates - All Categories", True, f"All {categories_tested} categories passed")
            else:
                self.log_test_result("Message Templates - All Categories", False, f"Only {categories_passed}/{categories_tested} categories passed")
        
        except Exception as e:
            self.log_test_result("Message Templates - All Categories", False, f"Exception: {str(e)}")
    
    def test_detail_levels(self):
        """Test different detail levels for messages"""
        try:
            template = MessageTemplate(ErrorCategory.DOWNLOAD)
            
            error_info = ErrorInfo(
                error_id="DETAIL_TEST_001",
                error_code="DETAIL_TEST",
                message="Test detail levels",
                category=ErrorCategory.DOWNLOAD,
                severity=ErrorSeverity.HIGH,
                context=ErrorContext(operation="file_download"),
                recovery_strategy=RecoveryStrategy.RETRY
            )
            
            # Test all detail levels
            levels = [MessageDetailLevel.MINIMAL, MessageDetailLevel.STANDARD, MessageDetailLevel.DETAILED]
            level_results = {}
            
            for level in levels:
                user_context = UserContext(detail_level=level)
                message = template.generate_message(error_info, user_context)
                level_results[level.value] = len(message.message)
            
            # Detailed should generally be longer than standard, standard longer than minimal
            if (level_results['detailed'] >= level_results['standard'] and
                level_results['standard'] >= level_results['minimal']):
                self.log_test_result("Detail Levels", True, f"Lengths: {level_results}")
            else:
                self.log_test_result("Detail Levels", False, f"Unexpected lengths: {level_results}")
        
        except Exception as e:
            self.log_test_result("Detail Levels", False, f"Exception: {str(e)}")
    
    def test_technical_details_by_role(self):
        """Test technical details generation based on user roles"""
        try:
            template = MessageTemplate(ErrorCategory.SERVICE)
            
            error_info = ErrorInfo(
                error_id="TECH_TEST_001",
                error_code="TECH_DETAILS_TEST",
                message="Technical details test",
                category=ErrorCategory.SERVICE,
                severity=ErrorSeverity.HIGH,
                context=ErrorContext(operation="service_call"),
                recovery_strategy=RecoveryStrategy.RETRY,
                component="test_service",
                error_type="TIMEOUT"
            )
            
            # Test different user roles
            roles_to_test = [
                (UserRole.END_USER, False),  # Should not get technical details
                (UserRole.POWER_USER, False),  # Should not get technical details for standard level
                (UserRole.DEVELOPER, True),  # Should get technical details
                (UserRole.ADMINISTRATOR, True)  # Should get technical details
            ]
            
            all_passed = True
            for role, should_have_details in roles_to_test:
                user_context = UserContext(user_role=role, detail_level=MessageDetailLevel.STANDARD)
                message = template.generate_message(error_info, user_context)
                
                has_details = message.technical_details is not None
                if has_details != should_have_details:
                    all_passed = False
                    print(f"   Role {role.value}: expected {should_have_details}, got {has_details}")
            
            if all_passed:
                self.log_test_result("Technical Details by Role", True)
            else:
                self.log_test_result("Technical Details by Role", False, "Role-based technical details failed")
        
        except Exception as e:
            self.log_test_result("Technical Details by Role", False, f"Exception: {str(e)}")
    
    def test_user_feedback_manager(self):
        """Test UserFeedbackManager core functionality"""
        try:
            manager = UserFeedbackManager()
            
            # Test message generation
            error_info = ErrorInfo(
                error_id="MGR_TEST_001",
                error_code="MANAGER_TEST",
                message="Manager test error",
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.HIGH,
                context=ErrorContext(operation="login"),
                recovery_strategy=RecoveryStrategy.MANUAL_INTERVENTION
            )
            
            user_context = UserContext(user_role=UserRole.END_USER)
            message = manager.generate_user_message(error_info, user_context, MessageType.MODAL)
            
            print(f"   DEBUG: Generated message title: '{message.title}'")
            print(f"   DEBUG: Generated message text: '{message.message}'")
            print(f"   DEBUG: Expected title: 'Authentication Required'")
            
            if (message.title == "Authentication Required" and
                ("log in" in message.message.lower() or "sign" in message.message.lower())):
                self.log_test_result("User Feedback Manager - Message Generation", True)
            else:
                self.log_test_result("User Feedback Manager - Message Generation", False, f"Title: {message.title}, Message: {message.message}")
            
            # Test recovery suggestions
            suggestions = manager.get_recovery_suggestions(error_info)
            
            if isinstance(suggestions, list) and len(suggestions) > 0:
                self.log_test_result("User Feedback Manager - Recovery Suggestions", True, f"Got {len(suggestions)} suggestions")
            else:
                self.log_test_result("User Feedback Manager - Recovery Suggestions", False, "No suggestions generated")
            
            # Test accessibility formatting
            accessible_format = manager.format_for_accessibility(message)
            
            if (isinstance(accessible_format, dict) and
                "aria_label" in accessible_format and
                "role" in accessible_format):
                self.log_test_result("User Feedback Manager - Accessibility", True)
            else:
                self.log_test_result("User Feedback Manager - Accessibility", False, "Accessibility formatting failed")
        
        except Exception as e:
            self.log_test_result("User Feedback Manager", False, f"Exception: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def test_convenience_functions(self):
        """Test convenience functions"""
        try:
            error_info = ErrorInfo(
                error_id="CONV_TEST_001",
                error_code="CONVENIENCE_TEST",
                message="Convenience function test",
                category=ErrorCategory.PLATFORM,
                severity=ErrorSeverity.MEDIUM,
                context=ErrorContext(operation="api_call"),
                recovery_strategy=RecoveryStrategy.RETRY
            )
            
            # Test generate_user_friendly_message
            message = generate_user_friendly_message(
                error_info,
                UserRole.POWER_USER,
                MessageDetailLevel.DETAILED,
                MessageType.TOAST
            )
            
            if (message.title and message.message and
                "platform" in message.message.lower()):
                self.log_test_result("Convenience Functions - Message Generation", True)
            else:
                self.log_test_result("Convenience Functions - Message Generation", False, "Function failed")
            
            # Test get_error_recovery_suggestions
            suggestions = get_error_recovery_suggestions(error_info)
            
            if isinstance(suggestions, list) and len(suggestions) > 0:
                self.log_test_result("Convenience Functions - Recovery Suggestions", True, f"Got {len(suggestions)} suggestions")
            else:
                self.log_test_result("Convenience Functions - Recovery Suggestions", False, "Function failed")
        
        except Exception as e:
            self.log_test_result("Convenience Functions", False, f"Exception: {str(e)}")
    
    def test_message_customization(self):
        """Test message customization for specific error types"""
        try:
            template = MessageTemplate(ErrorCategory.NETWORK)
            
            # Test network timeout customization
            error_info = ErrorInfo(
                error_id="CUST_TEST_001",
                error_code="NETWORK_TIMEOUT",
                message="Connection timed out",
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.MEDIUM,
                context=ErrorContext(operation="download"),
                recovery_strategy=RecoveryStrategy.RETRY,
                error_type="NETWORK_TIMEOUT"
            )
            
            user_context = UserContext()
            message = template.generate_message(error_info, user_context)
            
            # Check if message was customized for network timeout
            customized = "connection timed out" in message.message.lower() or "timed out" in message.message.lower()
            
            if customized:
                self.log_test_result("Message Customization - Error Type", True)
            else:
                self.log_test_result("Message Customization - Error Type", False, f"Message: {message.message}")
            
            # Test operation context addition
            context_added = "while downloading" in message.message or "downloading" in message.message
            
            if context_added:
                self.log_test_result("Message Customization - Operation Context", True)
            else:
                self.log_test_result("Message Customization - Operation Context", False, "No operation context found")
        
        except Exception as e:
            self.log_test_result("Message Customization", False, f"Exception: {str(e)}")
    
    def test_severity_presentation(self):
        """Test severity-based presentation settings"""
        try:
            template = MessageTemplate(ErrorCategory.FATAL)
            
            severities = [
                (ErrorSeverity.LOW, "#2196F3"),
                (ErrorSeverity.MEDIUM, "#FF9800"), 
                (ErrorSeverity.HIGH, "#F44336"),
                (ErrorSeverity.CRITICAL, "#D32F2F")
            ]
            
            all_passed = True
            for severity, expected_color in severities:
                error_info = ErrorInfo(
                    error_id=f"SEV_TEST_{severity.value.upper()}",
                    error_code="SEVERITY_TEST",
                    message=f"Test {severity.value} severity",
                    category=ErrorCategory.FATAL,
                    severity=severity,
                    context=ErrorContext(operation="test"),
                    recovery_strategy=RecoveryStrategy.FAIL_FAST
                )
                
                user_context = UserContext()
                message = template.generate_message(error_info, user_context)
                
                if message.severity_color != expected_color:
                    all_passed = False
                    print(f"   Severity {severity.value}: expected {expected_color}, got {message.severity_color}")
            
            if all_passed:
                self.log_test_result("Severity Presentation", True)
            else:
                self.log_test_result("Severity Presentation", False, "Severity colors don't match")
        
        except Exception as e:
            self.log_test_result("Severity Presentation", False, f"Exception: {str(e)}")
    
    def test_global_feedback_manager(self):
        """Test global feedback manager instance"""
        try:
            manager1 = get_feedback_manager()
            manager2 = get_feedback_manager()
            
            # Should be the same instance (singleton pattern)
            if manager1 is manager2:
                self.log_test_result("Global Feedback Manager", True, "Singleton pattern working")
            else:
                self.log_test_result("Global Feedback Manager", False, "Not singleton")
        
        except Exception as e:
            self.log_test_result("Global Feedback Manager", False, f"Exception: {str(e)}")
    
    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting User Feedback Core Test Suite")
        print("=" * 60)
        
        # Run individual tests
        self.test_user_message_creation()
        self.test_user_context()
        self.test_message_templates_all_categories()
        self.test_detail_levels()
        self.test_technical_details_by_role()
        self.test_user_feedback_manager()
        self.test_convenience_functions()
        self.test_message_customization()
        self.test_severity_presentation()
        self.test_global_feedback_manager()
        
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
    test_suite = TestUserFeedbackCore()
    success = test_suite.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed! User Feedback Core implementation is working correctly.")
        print("\nKey Features Tested:")
        print("✅ User message creation and properties")
        print("✅ User context configuration")  
        print("✅ Message templates for all error categories")
        print("✅ Different detail levels (minimal, standard, detailed)")
        print("✅ Role-based technical details display")
        print("✅ User feedback manager functionality")
        print("✅ Convenience functions for easy integration")
        print("✅ Message customization for error types and operations")
        print("✅ Severity-based presentation (colors and icons)")
        print("✅ Global feedback manager singleton pattern")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please review the implementation.")
        return 1


if __name__ == "__main__":
    exit(main()) 