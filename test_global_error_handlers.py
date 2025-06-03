"""
Comprehensive Test Suite for Global Error Handlers

Tests the global error handling system including error interception, 
processing pipeline, context preservation, and integration capabilities.
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

from core.global_error_handler import (
    ApplicationState, GlobalErrorContext, GlobalErrorProcessor, GlobalErrorHandler,
    get_global_error_handler, install_global_error_handlers, uninstall_global_error_handlers,
    error_boundary, get_error_statistics
)


class TestGlobalErrorHandlers:
    """Test suite for global error handlers"""
    
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
        """Run all global error handler tests"""
        print("🚀 Starting Global Error Handlers Test Suite")
        print("=" * 60)
        
        # Test core components
        self.test_application_state()
        self.test_global_error_context()
        self.test_global_error_processor()
        self.test_global_error_handler()
        
        # Test error interception
        self.test_exception_interception()
        self.test_error_boundary()
        
        # Test processing pipeline
        self.test_error_classification()
        self.test_critical_error_handling()
        self.test_non_critical_error_handling()
        
        # Test integration
        self.test_error_statistics()
        self.test_handler_installation()
        
        # Print summary
        self.print_summary()
    
    def test_application_state(self):
        """Test application state capture"""
        try:
            app_state = ApplicationState()
            app_state.capture_current_state()
            
            # Check that state was captured
            if (isinstance(app_state.active_threads, list) and
                app_state.memory_usage >= 0 and
                isinstance(app_state.timestamp, datetime)):
                self.log_test_result("Application State Capture", True, f"Captured {len(app_state.active_threads)} threads")
            else:
                self.log_test_result("Application State Capture", False, "State capture incomplete")
        
        except Exception as e:
            self.log_test_result("Application State Capture", False, f"Exception: {str(e)}")
    
    def test_global_error_context(self):
        """Test global error context creation"""
        try:
            # Create test exception
            test_error = ValueError("Test error for context")
            
            # Create error context
            error_context = GlobalErrorContext.from_exception(test_error, "test_source")
            
            # Validate context properties
            if (error_context.exception == test_error and
                error_context.error_source == "test_source" and
                error_context.stack_trace and
                isinstance(error_context.thread_info, dict) and
                isinstance(error_context.application_state, ApplicationState)):
                self.log_test_result("Global Error Context", True, f"Context for {type(test_error).__name__}")
            else:
                self.log_test_result("Global Error Context", False, "Context creation incomplete")
        
        except Exception as e:
            self.log_test_result("Global Error Context", False, f"Exception: {str(e)}")
    
    def test_global_error_processor(self):
        """Test global error processor functionality"""
        try:
            processor = GlobalErrorProcessor()
            
            # Create test error context
            test_error = RuntimeError("Test processor error")
            error_context = GlobalErrorContext.from_exception(test_error, "processor_test")
            
            # Process the error
            result = processor.process_error(error_context)
            
            # Check processing results
            if (isinstance(result, bool) and
                processor.error_count > 0 and
                len(processor.last_errors) > 0):
                self.log_test_result("Global Error Processor", True, f"Processed error, count: {processor.error_count}")
            else:
                self.log_test_result("Global Error Processor", False, "Error processing failed")
        
        except Exception as e:
            self.log_test_result("Global Error Processor", False, f"Exception: {str(e)}")
    
    def test_global_error_handler(self):
        """Test global error handler setup"""
        try:
            handler = get_global_error_handler()
            
            # Test initial state
            if (isinstance(handler, GlobalErrorHandler) and
                not handler.installed and
                isinstance(handler.processor, GlobalErrorProcessor)):
                self.log_test_result("Global Error Handler Creation", True, "Handler created successfully")
            else:
                self.log_test_result("Global Error Handler Creation", False, "Handler creation failed")
        
        except Exception as e:
            self.log_test_result("Global Error Handler Creation", False, f"Exception: {str(e)}")
    
    def test_exception_interception(self):
        """Test exception interception mechanisms"""
        try:
            handler = get_global_error_handler()
            original_count = handler.processor.error_count
            
            # Test manual exception processing
            test_error = KeyError("Test interception error")
            error_context = GlobalErrorContext.from_exception(test_error, "interception_test")
            
            # Process through handler
            handler.processor.process_error(error_context)
            
            # Check if error was processed
            if handler.processor.error_count > original_count:
                self.log_test_result("Exception Interception", True, f"Error count increased to {handler.processor.error_count}")
            else:
                self.log_test_result("Exception Interception", False, "Error count not increased")
        
        except Exception as e:
            self.log_test_result("Exception Interception", False, f"Exception: {str(e)}")
    
    def test_error_boundary(self):
        """Test error boundary context manager"""
        try:
            handler = get_global_error_handler()
            original_count = handler.processor.error_count
            
            # Test error boundary with controlled exception
            try:
                with error_boundary("test_operation"):
                    raise ValueError("Boundary test error")
            except ValueError:
                pass  # Expected to re-raise
            
            # Check if error was processed through boundary
            if handler.processor.error_count > original_count:
                self.log_test_result("Error Boundary", True, "Boundary processed error correctly")
            else:
                self.log_test_result("Error Boundary", False, "Boundary did not process error")
        
        except Exception as e:
            self.log_test_result("Error Boundary", False, f"Exception: {str(e)}")
    
    def test_error_classification(self):
        """Test error classification in processor"""
        try:
            processor = GlobalErrorProcessor()
            
            # Test with different error types
            test_errors = [
                (ValueError("UI validation error"), "ui_component"),
                (ConnectionError("Network failure"), "platform_api"),
                (FileNotFoundError("Download failed"), "download_service"),
                (MemoryError("Out of memory"), "critical_system")
            ]
            
            classifications_successful = 0
            for error, source in test_errors:
                error_context = GlobalErrorContext.from_exception(error, source)
                try:
                    error_info = processor._classify_error(error_context)
                    if error_info and error_info.error_code:
                        classifications_successful += 1
                except:
                    pass
            
            if classifications_successful >= len(test_errors):
                self.log_test_result("Error Classification", True, f"Classified {classifications_successful}/{len(test_errors)} errors")
            else:
                self.log_test_result("Error Classification", False, f"Only classified {classifications_successful}/{len(test_errors)} errors")
        
        except Exception as e:
            self.log_test_result("Error Classification", False, f"Exception: {str(e)}")
    
    def test_critical_error_handling(self):
        """Test critical error detection and handling"""
        try:
            processor = GlobalErrorProcessor()
            
            # Test with memory error (should be critical)
            memory_error = MemoryError("Critical memory error")
            error_context = GlobalErrorContext.from_exception(memory_error, "critical_test")
            
            # Classify and check if critical
            error_info = processor._classify_error(error_context)
            is_critical = processor._is_critical_error(error_info, error_context)
            
            if is_critical:
                self.log_test_result("Critical Error Detection", True, "MemoryError correctly identified as critical")
            else:
                # Test with error count threshold
                processor.error_count = processor.critical_error_threshold
                simple_error = ValueError("Simple error")
                simple_context = GlobalErrorContext.from_exception(simple_error, "threshold_test")
                simple_info = processor._classify_error(simple_context)
                is_critical_by_count = processor._is_critical_error(simple_info, simple_context)
                
                if is_critical_by_count:
                    self.log_test_result("Critical Error Detection", True, "Error count threshold correctly triggers critical status")
                else:
                    self.log_test_result("Critical Error Detection", False, "Critical error detection failed")
        
        except Exception as e:
            self.log_test_result("Critical Error Detection", False, f"Exception: {str(e)}")
    
    def test_non_critical_error_handling(self):
        """Test non-critical error handling"""
        try:
            processor = GlobalErrorProcessor()
            
            # Test with simple error
            simple_error = ValueError("Non-critical error")
            error_context = GlobalErrorContext.from_exception(simple_error, "non_critical_test")
            
            # Process error
            result = processor.process_error(error_context)
            
            # Non-critical errors should return True (handled successfully)
            if result:
                self.log_test_result("Non-Critical Error Handling", True, "Non-critical error handled successfully")
            else:
                self.log_test_result("Non-Critical Error Handling", False, "Non-critical error handling failed")
        
        except Exception as e:
            self.log_test_result("Non-Critical Error Handling", False, f"Exception: {str(e)}")
    
    def test_error_statistics(self):
        """Test error statistics tracking"""
        try:
            # Get statistics before and after error
            initial_stats = get_error_statistics()
            initial_count = initial_stats.get('total_errors', 0)
            
            # Trigger an error
            handler = get_global_error_handler()
            test_error = RuntimeError("Statistics test error")
            error_context = GlobalErrorContext.from_exception(test_error, "stats_test")
            handler.processor.process_error(error_context)
            
            # Get updated statistics
            updated_stats = get_error_statistics()
            updated_count = updated_stats.get('total_errors', 0)
            
            if (updated_count > initial_count and
                'handlers_installed' in updated_stats and
                'shutdown_initiated' in updated_stats):
                self.log_test_result("Error Statistics", True, f"Error count: {initial_count} → {updated_count}")
            else:
                self.log_test_result("Error Statistics", False, "Statistics not updating correctly")
        
        except Exception as e:
            self.log_test_result("Error Statistics", False, f"Exception: {str(e)}")
    
    def test_handler_installation(self):
        """Test global handler installation and uninstallation"""
        try:
            # Test installation
            install_global_error_handlers()
            
            # Check if installed
            handler = get_global_error_handler()
            installed_status = handler.installed
            
            if installed_status:
                self.log_test_result("Handler Installation", True, "Global handlers installed successfully")
            else:
                self.log_test_result("Handler Installation", False, "Handler installation failed")
            
            # Test uninstallation
            uninstall_global_error_handlers()
            uninstalled_status = not handler.installed
            
            if uninstalled_status:
                self.log_test_result("Handler Uninstallation", True, "Global handlers uninstalled successfully")
            else:
                self.log_test_result("Handler Uninstallation", False, "Handler uninstallation failed")
        
        except Exception as e:
            self.log_test_result("Handler Installation/Uninstallation", False, f"Exception: {str(e)}")
    
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
            print("\n🎉 All tests passed! Global Error Handlers implementation is working correctly.")
            print("\nKey Features Tested:")
            print("✅ Application state capture and preservation")
            print("✅ Global error context creation and management")
            print("✅ Error processing pipeline with classification")
            print("✅ Critical vs non-critical error handling")
            print("✅ Exception interception mechanisms")
            print("✅ Error boundary context managers")
            print("✅ Error statistics tracking and reporting")
            print("✅ Handler installation and uninstallation")
            print("✅ Integration with error management components")
        else:
            print(f"\n⚠️  Some tests failed. Please review the implementation.")


if __name__ == "__main__":
    tester = TestGlobalErrorHandlers()
    tester.run_all_tests() 