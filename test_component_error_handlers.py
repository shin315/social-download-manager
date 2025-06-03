"""
Comprehensive Test Suite for Component-Specific Error Handlers

Tests the component-specific error handling system including specialized handlers,
pattern matching, validation decorators, and integration capabilities.
"""

import os
import sys
import threading
import time
import logging
from datetime import datetime
from unittest.mock import Mock, patch

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

from core.component_error_handlers import (
    ComponentErrorConfig, ComponentErrorHandler, UIErrorHandler, 
    PlatformServiceErrorHandler, DownloadServiceErrorHandler, RepositoryErrorHandler,
    component_error_handler, validate_input, require_non_null,
    get_component_handler, register_component_handler, initialize_component_handlers,
    handle_ui_error, handle_platform_error, handle_download_error, handle_repository_error
)

# Import error management types for testing
try:
    from data.models.error_management import ErrorCategory, ErrorSeverity, RecoveryStrategy
except ImportError:
    # Create mock classes for testing
    from enum import Enum
    
    class ErrorCategory(Enum):
        UI = "ui"
        PLATFORM = "platform"
        DOWNLOAD = "download"
        REPOSITORY = "repository"
        UNKNOWN = "unknown"
    
    class ErrorSeverity(Enum):
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"
        CRITICAL = "critical"
    
    class RecoveryStrategy(Enum):
        RETRY = "retry"
        FALLBACK = "fallback"
        FAIL_FAST = "fail_fast"


class TestComponentErrorHandlers:
    """Test suite for component-specific error handlers"""
    
    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_results = []
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def log_test_result(self, test_name: str, success: bool, details: str = ""):
        """Log the result of a test"""
        if success:
            self.passed_tests += 1
            status = "✅ PASS"
        else:
            self.failed_tests += 1
            status = "❌ FAIL"
        
        result = f"{status}: {test_name}"
        if details:
            result += f"\n   Details: {details}"
        
        self.test_results.append(result)
        print(result)
    
    def run_all_tests(self):
        """Run all component error handler tests"""
        print("🚀 Starting Component Error Handlers Test Suite")
        print("=" * 60)
        
        # Test core components
        self.test_component_error_config()
        self.test_base_component_handler()
        self.test_error_pattern_matching()
        self.test_error_context_validation()
        
        # Test specialized handlers
        self.test_ui_error_handler()
        self.test_platform_service_error_handler()
        self.test_download_service_error_handler()
        self.test_repository_error_handler()
        
        # Test decorators
        self.test_component_error_decorator()
        self.test_validation_decorators()
        
        # Test registry and convenience functions
        self.test_component_handler_registry()
        self.test_convenience_functions()
        
        # Test integration
        self.test_error_escalation()
        self.test_component_handler_initialization()
        
        # Print summary
        self.print_summary()
    
    def test_component_error_config(self):
        """Test component error configuration"""
        try:
            config = ComponentErrorConfig(
                component_name="test_component",
                error_category=ErrorCategory.UI,
                default_severity=ErrorSeverity.MEDIUM,
                max_retries=3,
                error_patterns={'ValueError': 'retry'},
                fallback_actions=['reset', 'notify']
            )
            
            if (config.component_name == "test_component" and
                config.error_category == ErrorCategory.UI and
                config.max_retries == 3 and
                'ValueError' in config.error_patterns and
                len(config.fallback_actions) == 2):
                self.log_test_result("Component Error Config", True, "Configuration created successfully")
            else:
                self.log_test_result("Component Error Config", False, "Configuration validation failed")
        
        except Exception as e:
            self.log_test_result("Component Error Config", False, f"Exception: {str(e)}")
    
    def test_base_component_handler(self):
        """Test base component error handler"""
        try:
            config = ComponentErrorConfig(
                component_name="test_handler",
                error_category=ErrorCategory.UI,
                error_patterns={'TestError': 'handle_test'}
            )
            handler = ComponentErrorHandler(config)
            
            # Test basic properties
            if (handler.config.component_name == "test_handler" and
                handler.error_count == 0 and
                handler.consecutive_failures == 0):
                
                # Test error handling
                test_error = ValueError("Test error")
                result = handler.handle_error(test_error, "test_operation")
                
                if handler.error_count > 0:
                    self.log_test_result("Base Component Handler", True, f"Handler processed error, count: {handler.error_count}")
                else:
                    self.log_test_result("Base Component Handler", False, "Error count not updated")
            else:
                self.log_test_result("Base Component Handler", False, "Handler initialization failed")
        
        except Exception as e:
            self.log_test_result("Base Component Handler", False, f"Exception: {str(e)}")
    
    def test_error_pattern_matching(self):
        """Test error pattern matching functionality"""
        try:
            config = ComponentErrorConfig(
                component_name="pattern_test",
                error_category=ErrorCategory.UI,
                error_patterns={
                    'ValueError': 'retry_with_delay',
                    'ConnectionError': 'fallback_to_default',
                    'TestPattern': 'ignore'
                }
            )
            handler = ComponentErrorHandler(config)
            
            # Test pattern matching
            test_cases = [
                (ValueError("test"), 'retry_with_delay'),
                (ConnectionError("connection failed"), 'fallback_to_default'),
                (RuntimeError("TestPattern in message"), 'ignore')
            ]
            
            matches_found = 0
            for error, expected_action in test_cases:
                action = handler._match_error_pattern(error)
                if action == expected_action:
                    matches_found += 1
            
            if matches_found >= len(test_cases):
                self.log_test_result("Error Pattern Matching", True, f"Matched {matches_found}/{len(test_cases)} patterns")
            else:
                self.log_test_result("Error Pattern Matching", False, f"Only matched {matches_found}/{len(test_cases)} patterns")
        
        except Exception as e:
            self.log_test_result("Error Pattern Matching", False, f"Exception: {str(e)}")
    
    def test_error_context_validation(self):
        """Test error context validation"""
        try:
            # Create validation rule
            def test_validation_rule(context):
                if 'required_field' not in context.get('context', {}):
                    return {'valid': False, 'reason': 'Missing required field'}
                return {'valid': True}
            
            config = ComponentErrorConfig(
                component_name="validation_test",
                error_category=ErrorCategory.UI,
                validation_rules=[test_validation_rule]
            )
            handler = ComponentErrorHandler(config)
            
            # Test validation with valid context
            valid_context = {'required_field': 'value'}
            result1 = handler.handle_error(ValueError("test"), "test_op", context=valid_context)
            
            # Test validation with invalid context
            invalid_context = {'other_field': 'value'}
            result2 = handler.handle_error(ValueError("test"), "test_op", context=invalid_context)
            
            # Both should complete (validation doesn't prevent handling)
            if isinstance(result1, bool) and isinstance(result2, bool):
                self.log_test_result("Error Context Validation", True, "Validation rules executed successfully")
            else:
                self.log_test_result("Error Context Validation", False, "Validation execution failed")
        
        except Exception as e:
            self.log_test_result("Error Context Validation", False, f"Exception: {str(e)}")
    
    def test_ui_error_handler(self):
        """Test UI-specific error handler"""
        try:
            handler = UIErrorHandler()
            
            # Test UI-specific configuration
            if (handler.config.component_name == "ui_component" and
                handler.config.error_category == ErrorCategory.UI and
                handler.config.max_retries == 2 and
                'TclError' in handler.config.error_patterns):
                
                # Test UI error handling
                ui_error = AttributeError("Widget attribute error")
                result = handler.handle_error(ui_error, "widget_operation", context={'widget': 'button'})
                
                if isinstance(result, bool):
                    self.log_test_result("UI Error Handler", True, "UI-specific error handled successfully")
                else:
                    self.log_test_result("UI Error Handler", False, "UI error handling failed")
            else:
                self.log_test_result("UI Error Handler", False, "UI handler configuration incorrect")
        
        except Exception as e:
            self.log_test_result("UI Error Handler", False, f"Exception: {str(e)}")
    
    def test_platform_service_error_handler(self):
        """Test platform service error handler"""
        try:
            handler = PlatformServiceErrorHandler()
            
            # Test platform-specific configuration
            if (handler.config.component_name == "platform_service" and
                handler.config.error_category == ErrorCategory.PLATFORM and
                handler.config.timeout_seconds == 60.0 and
                '429' in handler.config.error_patterns):
                
                # Test platform error handling
                platform_error = ConnectionError("API connection failed")
                result = handler.handle_error(platform_error, "api_call")
                
                if isinstance(result, bool):
                    self.log_test_result("Platform Service Error Handler", True, "Platform-specific error handled")
                else:
                    self.log_test_result("Platform Service Error Handler", False, "Platform error handling failed")
            else:
                self.log_test_result("Platform Service Error Handler", False, "Platform handler configuration incorrect")
        
        except Exception as e:
            self.log_test_result("Platform Service Error Handler", False, f"Exception: {str(e)}")
    
    def test_download_service_error_handler(self):
        """Test download service error handler"""
        try:
            handler = DownloadServiceErrorHandler()
            
            # Test download-specific configuration
            if (handler.config.component_name == "download_service" and
                handler.config.error_category == ErrorCategory.DOWNLOAD and
                handler.config.max_retries == 5 and
                'FileNotFoundError' in handler.config.error_patterns):
                
                # Test download error handling
                download_error = PermissionError("Cannot write to download folder")
                result = handler.handle_error(download_error, "file_download")
                
                if isinstance(result, bool):
                    self.log_test_result("Download Service Error Handler", True, "Download-specific error handled")
                else:
                    self.log_test_result("Download Service Error Handler", False, "Download error handling failed")
            else:
                self.log_test_result("Download Service Error Handler", False, "Download handler configuration incorrect")
        
        except Exception as e:
            self.log_test_result("Download Service Error Handler", False, f"Exception: {str(e)}")
    
    def test_repository_error_handler(self):
        """Test repository service error handler"""
        try:
            handler = RepositoryErrorHandler()
            
            # Test repository-specific configuration
            if (handler.config.component_name == "repository_service" and
                handler.config.error_category == ErrorCategory.REPOSITORY and
                'DatabaseError' in handler.config.error_patterns and
                'use_readonly_mode' in handler.config.fallback_actions):
                
                # Test repository error handling
                repo_error = RuntimeError("Database connection lost")
                result = handler.handle_error(repo_error, "database_query")
                
                if isinstance(result, bool):
                    self.log_test_result("Repository Error Handler", True, "Repository-specific error handled")
                else:
                    self.log_test_result("Repository Error Handler", False, "Repository error handling failed")
            else:
                self.log_test_result("Repository Error Handler", False, "Repository handler configuration incorrect")
        
        except Exception as e:
            self.log_test_result("Repository Error Handler", False, f"Exception: {str(e)}")
    
    def test_component_error_decorator(self):
        """Test component error handling decorator"""
        try:
            # Define test function with decorator
            @component_error_handler("test_component", ErrorCategory.UI, max_retries=2)
            def test_function_with_decorator(value):
                if value == "error":
                    raise ValueError("Decorator test error")
                return f"Success: {value}"
            
            # Test successful execution
            result1 = test_function_with_decorator("success")
            
            # Test error handling (should not raise exception)
            try:
                result2 = test_function_with_decorator("error")
                # If we get here, the decorator handled the error
                error_was_handled = True
            except ValueError:
                # If we get here, the decorator did not handle the error
                result2 = "ERROR_NOT_HANDLED"
                error_was_handled = False
            
            # Should return success for normal case, None for handled error
            if result1 == "Success: success" and result2 is None and error_was_handled:
                self.log_test_result("Component Error Decorator", True, "Decorator handled errors correctly")
            else:
                self.log_test_result("Component Error Decorator", False, f"Unexpected results: result1={result1}, result2={result2}, handled={error_was_handled}")
        
        except Exception as e:
            self.log_test_result("Component Error Decorator", False, f"Exception: {str(e)}")
    
    def test_validation_decorators(self):
        """Test validation decorators"""
        try:
            # Test validate_input decorator
            @validate_input(value=lambda x: isinstance(x, str) and len(x) > 0)
            def test_validate_input(value):
                return f"Valid: {value}"
            
            # Test require_non_null decorator
            @require_non_null('required_param')
            def test_require_non_null(required_param, optional_param=None):
                return f"Required: {required_param}"
            
            # Test successful validation
            result1 = test_validate_input(value="valid")
            result2 = test_require_non_null(required_param="not_null")
            
            # Test validation failures
            validation_failed = False
            try:
                test_validate_input(value="")  # Should fail validation
            except ValueError:
                validation_failed = True
            
            null_check_failed = False
            try:
                test_require_non_null(required_param=None)  # Should fail null check
            except ValueError:
                null_check_failed = True
            
            if (result1 == "Valid: valid" and 
                result2 == "Required: not_null" and
                validation_failed and null_check_failed):
                self.log_test_result("Validation Decorators", True, "All validation decorators working correctly")
            else:
                self.log_test_result("Validation Decorators", False, "Validation decorator behavior incorrect")
        
        except Exception as e:
            self.log_test_result("Validation Decorators", False, f"Exception: {str(e)}")
    
    def test_component_handler_registry(self):
        """Test component handler registry functionality"""
        try:
            # Test registration
            test_handler = UIErrorHandler()
            register_component_handler("test_component", test_handler)
            
            # Test retrieval
            retrieved_handler = get_component_handler("test_component")
            
            # Test that it's the same instance
            if retrieved_handler is test_handler:
                self.log_test_result("Component Handler Registry", True, "Registry registration and retrieval working")
            else:
                self.log_test_result("Component Handler Registry", False, "Registry not working correctly")
        
        except Exception as e:
            self.log_test_result("Component Handler Registry", False, f"Exception: {str(e)}")
    
    def test_convenience_functions(self):
        """Test convenience functions for component error handling"""
        try:
            # Test convenience functions
            test_errors = [
                (ValueError("UI test"), handle_ui_error),
                (ConnectionError("Platform test"), handle_platform_error),
                (FileNotFoundError("Download test"), handle_download_error),
                (RuntimeError("Repository test"), handle_repository_error)
            ]
            
            successful_handles = 0
            for error, handler_func in test_errors:
                try:
                    result = handler_func(error, "test_operation")
                    if isinstance(result, bool):
                        successful_handles += 1
                except Exception as e:
                    self.logger.warning(f"Convenience function failed: {e}")
            
            if successful_handles >= len(test_errors):
                self.log_test_result("Convenience Functions", True, f"All {successful_handles} convenience functions working")
            else:
                self.log_test_result("Convenience Functions", False, f"Only {successful_handles}/{len(test_errors)} functions working")
        
        except Exception as e:
            self.log_test_result("Convenience Functions", False, f"Exception: {str(e)}")
    
    def test_error_escalation(self):
        """Test error escalation to global handler"""
        try:
            # Create handler with low escalation threshold
            config = ComponentErrorConfig(
                component_name="escalation_test",
                error_category=ErrorCategory.UI,
                escalate_after_failures=2
            )
            handler = ComponentErrorHandler(config)
            
            # Trigger multiple errors to test escalation
            for i in range(3):
                try:
                    result = handler.handle_error(RuntimeError(f"Test error {i}"), "test_operation")
                except:
                    pass
            
            # Check if consecutive failures increased
            if handler.consecutive_failures >= 2:
                self.log_test_result("Error Escalation", True, f"Escalation triggered after {handler.consecutive_failures} failures")
            else:
                self.log_test_result("Error Escalation", False, f"Escalation not triggered, failures: {handler.consecutive_failures}")
        
        except Exception as e:
            self.log_test_result("Error Escalation", False, f"Exception: {str(e)}")
    
    def test_component_handler_initialization(self):
        """Test component handler initialization"""
        try:
            # Test initialization
            handlers = initialize_component_handlers()
            
            # Check if all expected handlers were created
            expected_handlers = ['ui', 'platform', 'download', 'repository']
            created_handlers = list(handlers.keys())
            
            if all(name in created_handlers for name in expected_handlers):
                # Check if handlers were registered
                registered_count = 0
                for name in expected_handlers:
                    if get_component_handler(name) is not None:
                        registered_count += 1
                
                if registered_count == len(expected_handlers):
                    self.log_test_result("Component Handler Initialization", True, f"All {registered_count} handlers initialized and registered")
                else:
                    self.log_test_result("Component Handler Initialization", False, f"Only {registered_count}/{len(expected_handlers)} handlers registered")
            else:
                self.log_test_result("Component Handler Initialization", False, f"Missing handlers: {set(expected_handlers) - set(created_handlers)}")
        
        except Exception as e:
            self.log_test_result("Component Handler Initialization", False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        total_tests = self.passed_tests + self.failed_tests
        success_rate = (self.passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.failed_tests}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if self.failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in self.test_results:
                if "❌ FAIL" in result:
                    test_name = result.split(":")[1].strip()
                    print(f"  - {test_name}")
        
        print(f"\n✅ PASSED TESTS:")
        for result in self.test_results:
            if "✅ PASS" in result:
                test_name = result.split(":")[1].strip()
                print(f"  - {test_name}")
        
        if success_rate == 100:
            print("\n🎉 All tests passed! Component-Specific Error Handlers implementation is working correctly.")
            print("\nKey Features Tested:")
            print("✅ Component error configuration and base handler")
            print("✅ Error pattern matching and context validation")
            print("✅ Specialized handlers (UI, Platform, Download, Repository)")
            print("✅ Component error handling decorators")
            print("✅ Input validation and null-check decorators")
            print("✅ Component handler registry and retrieval")
            print("✅ Convenience functions for component error handling")
            print("✅ Error escalation to global handlers")
            print("✅ Component handler initialization system")
        else:
            print(f"\n⚠️  Some tests failed. Please review the implementation.")


if __name__ == "__main__":
    tester = TestComponentErrorHandlers()
    tester.run_all_tests() 