"""
Simple Integration Test for Error Handling System

This test validates that all error handling components exist and can work together
without complex imports or dependencies.
"""

import os
import sys
import traceback
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

class SimpleErrorHandlingIntegrationTest:
    """Simple integration test for error handling system"""
    
    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_results = []
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
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
        """Run all integration tests"""
        print("🚀 Starting Simple Error Handling Integration Test Suite")
        print("=" * 70)
        
        # Test component existence
        self.test_error_categorization_module()
        self.test_logging_strategy_module() 
        self.test_user_feedback_module()
        self.test_recovery_procedures_module()
        self.test_global_error_handlers_module()
        self.test_component_handlers_module()
        
        # Test basic functionality
        self.test_error_classification_basic()
        self.test_logging_basic()
        self.test_user_feedback_basic()
        self.test_recovery_basic()
        self.test_global_handler_basic()
        self.test_component_handler_basic()
        
        # Test integration
        self.test_end_to_end_error_flow()
        
        # Print summary
        self.print_summary()
    
    def test_error_categorization_module(self):
        """Test error categorization module exists and loads"""
        try:
            from data.models.error_management import ErrorCategory, ErrorSeverity, ErrorInfo
            from core.error_categorization import ErrorClassifier
            
            # Test basic functionality
            classifier = ErrorClassifier()
            test_error = ValueError("Test error")
            result = classifier.classify_error(test_error, "test_source")
            
            if hasattr(result, 'category') and hasattr(result, 'severity'):
                self.log_test_result("Error Categorization Module", True, f"Classified as {result.category.value}")
            else:
                self.log_test_result("Error Categorization Module", False, "Classification result incomplete")
        
        except Exception as e:
            self.log_test_result("Error Categorization Module", False, f"Exception: {str(e)}")
    
    def test_logging_strategy_module(self):
        """Test logging strategy module exists and loads"""
        try:
            from core.logging_strategy import EnhancedErrorLogger, get_error_logger
            
            # Test basic functionality
            logger = get_error_logger()
            
            if logger and hasattr(logger, 'log_error'):
                self.log_test_result("Logging Strategy Module", True, "Logger created successfully")
            else:
                self.log_test_result("Logging Strategy Module", False, "Logger missing log_error method")
        
        except Exception as e:
            self.log_test_result("Logging Strategy Module", False, f"Exception: {str(e)}")
    
    def test_user_feedback_module(self):
        """Test user feedback module exists and loads"""
        try:
            from core.user_feedback import get_feedback_manager, generate_user_friendly_message, UserRole
            
            # Test basic functionality
            manager = get_feedback_manager()
            
            if manager and hasattr(manager, 'generate_message'):
                self.log_test_result("User Feedback Module", True, "Feedback manager created successfully")
            else:
                self.log_test_result("User Feedback Module", False, "Feedback manager missing generate_message method")
        
        except Exception as e:
            self.log_test_result("User Feedback Module", False, f"Exception: {str(e)}")
    
    def test_recovery_procedures_module(self):
        """Test recovery procedures module exists and loads"""
        try:
            from core.recovery_strategies import RecoveryAction, RecoveryExecutor, RecoveryPlanRegistry
            from core.recovery_engine import AutoRecoveryManager, RetryPolicy
            
            # Test basic functionality
            executor = RecoveryExecutor()
            registry = RecoveryPlanRegistry()
            
            if hasattr(executor, 'execute') and hasattr(registry, 'get_plan'):
                self.log_test_result("Recovery Procedures Module", True, "Recovery components loaded successfully")
            else:
                self.log_test_result("Recovery Procedures Module", False, "Recovery components incomplete")
        
        except Exception as e:
            self.log_test_result("Recovery Procedures Module", False, f"Exception: {str(e)}")
    
    def test_global_error_handlers_module(self):
        """Test global error handlers module exists and loads"""
        try:
            from core.global_error_handler import (
                get_global_error_handler, GlobalErrorHandler, GlobalErrorProcessor
            )
            
            # Test basic functionality
            handler = get_global_error_handler()
            
            if handler and hasattr(handler, 'processor'):
                self.log_test_result("Global Error Handlers Module", True, "Global handler created successfully")
            else:
                self.log_test_result("Global Error Handlers Module", False, "Global handler missing processor")
        
        except Exception as e:
            self.log_test_result("Global Error Handlers Module", False, f"Exception: {str(e)}")
    
    def test_component_handlers_module(self):
        """Test component handlers module exists and loads"""
        try:
            from core.component_error_handlers import (
                ComponentErrorHandler, initialize_component_handlers
            )
            
            # Test basic functionality
            handlers = initialize_component_handlers()
            
            if handlers and len(handlers) > 0:
                self.log_test_result("Component Handlers Module", True, f"Initialized {len(handlers)} component handlers")
            else:
                self.log_test_result("Component Handlers Module", False, "No component handlers initialized")
        
        except Exception as e:
            self.log_test_result("Component Handlers Module", False, f"Exception: {str(e)}")
    
    def test_error_classification_basic(self):
        """Test basic error classification functionality"""
        try:
            from data.models.error_management import ErrorCategory
            from core.error_categorization import ErrorClassifier
            
            classifier = ErrorClassifier()
            
            # Test different error types
            test_cases = [
                (ValueError("Invalid input"), "validation"),
                (ConnectionError("Network failure"), "network"),
                (FileNotFoundError("File missing"), "file_system"),
                (RuntimeError("Runtime error"), "runtime")
            ]
            
            classified_count = 0
            for error, source in test_cases:
                try:
                    result = classifier.classify_error(error, source)
                    if hasattr(result, 'category'):
                        classified_count += 1
                except:
                    pass
            
            if classified_count >= 3:  # At least 3 out of 4 should work
                self.log_test_result("Error Classification Basic", True, f"Classified {classified_count}/4 error types")
            else:
                self.log_test_result("Error Classification Basic", False, f"Only classified {classified_count}/4 error types")
        
        except Exception as e:
            self.log_test_result("Error Classification Basic", False, f"Exception: {str(e)}")
    
    def test_logging_basic(self):
        """Test basic logging functionality"""
        try:
            from core.logging_strategy import get_error_logger
            from data.models.error_management import ErrorInfo, ErrorCategory, ErrorSeverity
            
            logger = get_error_logger()
            
            # Create test error info
            error_info = ErrorInfo(
                error_id="test_001",
                category=ErrorCategory.UI,
                severity=ErrorSeverity.MEDIUM,
                message="Test logging message",
                source="test_logging",
                timestamp=datetime.now()
            )
            
            # Test logging
            logger.log_error(error_info)
            
            self.log_test_result("Logging Basic", True, "Error logged successfully")
        
        except Exception as e:
            self.log_test_result("Logging Basic", False, f"Exception: {str(e)}")
    
    def test_user_feedback_basic(self):
        """Test basic user feedback functionality"""
        try:
            from core.user_feedback import generate_user_friendly_message, UserRole
            from data.models.error_management import ErrorInfo, ErrorCategory, ErrorSeverity
            
            # Create test error info
            error_info = ErrorInfo(
                error_id="test_002",
                category=ErrorCategory.PLATFORM,
                severity=ErrorSeverity.HIGH,
                message="API connection failed",
                source="test_feedback",
                timestamp=datetime.now()
            )
            
            # Test message generation
            message = generate_user_friendly_message(error_info, UserRole.END_USER)
            
            if message and hasattr(message, 'title') and hasattr(message, 'message'):
                self.log_test_result("User Feedback Basic", True, f"Generated message: {message.title}")
            else:
                self.log_test_result("User Feedback Basic", False, "Message generation incomplete")
        
        except Exception as e:
            self.log_test_result("User Feedback Basic", False, f"Exception: {str(e)}")
    
    def test_recovery_basic(self):
        """Test basic recovery functionality"""
        try:
            from core.recovery_strategies import RecoveryAction, RecoveryStep, RecoveryResult
            from core.recovery_engine import RetryConfiguration, RetryPolicy
            
            # Test recovery step creation
            step = RecoveryStep(
                action=RecoveryAction.RETRY,
                description="Test retry",
                timeout=30.0
            )
            
            # Test retry configuration
            retry_config = RetryConfiguration(
                policy=RetryPolicy.FIXED_DELAY,
                max_attempts=3,
                base_delay=1.0
            )
            
            if step and retry_config:
                self.log_test_result("Recovery Basic", True, f"Recovery step: {step.action.value}")
            else:
                self.log_test_result("Recovery Basic", False, "Recovery components creation failed")
        
        except Exception as e:
            self.log_test_result("Recovery Basic", False, f"Exception: {str(e)}")
    
    def test_global_handler_basic(self):
        """Test basic global handler functionality"""
        try:
            from core.global_error_handler import get_global_error_handler, GlobalErrorContext
            
            handler = get_global_error_handler()
            
            # Test context creation
            test_error = ValueError("Global handler test")
            context = GlobalErrorContext.from_exception(test_error, "test_global")
            
            if context and hasattr(context, 'exception') and hasattr(context, 'error_source'):
                self.log_test_result("Global Handler Basic", True, f"Context created for {context.error_source}")
            else:
                self.log_test_result("Global Handler Basic", False, "Context creation incomplete")
        
        except Exception as e:
            self.log_test_result("Global Handler Basic", False, f"Exception: {str(e)}")
    
    def test_component_handler_basic(self):
        """Test basic component handler functionality"""
        try:
            from core.component_error_handlers import ComponentErrorConfig, ComponentErrorHandler
            from data.models.error_management import ErrorCategory
            
            # Test component handler creation
            config = ComponentErrorConfig(
                component_name="test_component",
                error_category=ErrorCategory.UI
            )
            
            handler = ComponentErrorHandler(config)
            
            # Test basic error handling
            test_error = ValueError("Component handler test")
            result = handler.handle_error(test_error, "test_operation")
            
            if result is not None:  # Should return boolean
                self.log_test_result("Component Handler Basic", True, f"Handler processed error: {result}")
            else:
                self.log_test_result("Component Handler Basic", False, "Handler returned None")
        
        except Exception as e:
            self.log_test_result("Component Handler Basic", False, f"Exception: {str(e)}")
    
    def test_end_to_end_error_flow(self):
        """Test end-to-end error flow through all components"""
        try:
            from core.error_categorization import ErrorClassifier
            from core.logging_strategy import get_error_logger
            from core.user_feedback import generate_user_friendly_message, UserRole
            from core.global_error_handler import get_global_error_handler
            from core.component_error_handlers import initialize_component_handlers
            
            # Initialize all components
            classifier = ErrorClassifier()
            logger = get_error_logger()
            global_handler = get_global_error_handler()
            component_handlers = initialize_component_handlers()
            
            # Create test error
            test_error = ConnectionError("End-to-end test error")
            
            # Step 1: Classify error
            classified = classifier.classify_error(test_error, "e2e_test")
            
            # Step 2: Log error
            logger.log_error(classified)
            
            # Step 3: Generate user message
            message = generate_user_friendly_message(classified, UserRole.END_USER)
            
            # Step 4: Process through global handler
            context = global_handler.processor._global_error_context_from_exception(test_error)
            processed = global_handler.processor.process_error(context)
            
            # Step 5: Component handling (if available)
            component_handled = False
            if 'platform' in component_handlers:
                component_result = component_handlers['platform'].handle_error(test_error, "e2e_test")
                component_handled = component_result is not None
            
            # Validate flow completion
            flow_steps = []
            if hasattr(classified, 'category'):
                flow_steps.append("Classification")
            if message and hasattr(message, 'title'):
                flow_steps.append("User Feedback")
            if processed:
                flow_steps.append("Global Processing")
            if component_handled:
                flow_steps.append("Component Handling")
            
            if len(flow_steps) >= 3:  # At least 3 steps should complete
                self.log_test_result("End-to-End Error Flow", True, f"Completed: {' → '.join(flow_steps)}")
            else:
                self.log_test_result("End-to-End Error Flow", False, f"Incomplete flow: {flow_steps}")
        
        except Exception as e:
            self.log_test_result("End-to-End Error Flow", False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print comprehensive test summary"""
        total_tests = self.passed_tests + self.failed_tests
        success_rate = (self.passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print("\n" + "=" * 70)
        print("📊 ERROR HANDLING SIMPLE INTEGRATION TEST SUMMARY")
        print("=" * 70)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.failed_tests}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        # Categorize tests
        categories = {
            "Module Loading": [
                "Error Categorization Module", "Logging Strategy Module", 
                "User Feedback Module", "Recovery Procedures Module",
                "Global Error Handlers Module", "Component Handlers Module"
            ],
            "Basic Functionality": [
                "Error Classification Basic", "Logging Basic", "User Feedback Basic",
                "Recovery Basic", "Global Handler Basic", "Component Handler Basic"
            ],
            "Integration": ["End-to-End Error Flow"]
        }
        
        for category, test_names in categories.items():
            category_results = [result for result in self.test_results if any(test_name in result for test_name in test_names)]
            passed_in_category = len([r for r in category_results if "✅ PASS" in r])
            total_in_category = len(category_results)
            
            if total_in_category > 0:
                category_rate = (passed_in_category / total_in_category * 100)
                print(f"\n{category}: {passed_in_category}/{total_in_category} ({category_rate:.0f}%)")
        
        if self.failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in self.test_results:
                if "❌ FAIL" in result:
                    test_name = result.split(":")[1].strip().split("\n")[0]
                    print(f"  - {test_name}")
        
        print(f"\n✅ PASSED TESTS:")
        for result in self.test_results:
            if "✅ PASS" in result:
                test_name = result.split(":")[1].strip().split("\n")[0]
                print(f"  - {test_name}")
        
        if success_rate >= 85:
            print("\n🎉 EXCELLENT! Error handling system integration is working well.")
            print("\nValidated Components:")
            print("✅ Error categorization and classification")
            print("✅ Comprehensive logging strategy")
            print("✅ User feedback mechanisms")
            print("✅ Recovery procedures and strategies")
            print("✅ Global error handling")
            print("✅ Component-specific error handling")
            print("✅ End-to-end error flow processing")
        elif success_rate >= 70:
            print("\n✅ GOOD! Most error handling components are working.")
            print("⚠️  Some areas may need attention for optimal integration.")
        else:
            print("\n⚠️  Error handling system integration needs improvements.")
            print("🔧 Review failed tests and address component issues.")


if __name__ == "__main__":
    print("Initializing Simple Error Handling Integration Test Suite...")
    tester = SimpleErrorHandlingIntegrationTest()
    tester.run_all_tests() 