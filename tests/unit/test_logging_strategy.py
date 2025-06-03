"""
Comprehensive Test Suite for Logging Strategy Implementation

Tests the enhanced logging strategy, configuration, and integration with error management.
"""

import os
import sys
import json
import tempfile
import shutil
import logging
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

from core.logging_strategy import (
    LoggingStrategy, SensitiveDataFilter, PerformanceMetrics, LogEntry,
    LogLevel, LogDestination, SensitiveDataType, StructuredFormatter,
    get_logging_strategy, setup_enhanced_logging, get_enhanced_logger,
    log_error_with_context, log_operation_start, log_operation_end
)
from core.logging_config import LoggingConfig, ComponentLoggerConfig
from data.models.error_management import (
    ErrorInfo, ErrorCategory, ErrorSeverity, ErrorContext, RecoveryStrategy,
    setup_error_logging_strategy, log_error_recovery_attempt,
    error_handling_context
)


class TestLoggingStrategy:
    """Test suite for logging strategy implementation"""
    
    def __init__(self):
        self.test_results = []
        self.temp_dir = None
        self.original_cwd = os.getcwd()
    
    def setup_test_environment(self):
        """Setup test environment with temporary directory"""
        self.temp_dir = tempfile.mkdtemp()
        os.chdir(self.temp_dir)
        print(f"Test environment setup in: {self.temp_dir}")
    
    def cleanup_test_environment(self):
        """Cleanup test environment"""
        os.chdir(self.original_cwd)
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
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
    
    def test_sensitive_data_filter(self):
        """Test sensitive data filtering"""
        try:
            filter_obj = SensitiveDataFilter()
            
            # Test password filtering
            message_with_password = "User login failed with password=secret123"
            filtered = filter_obj.filter_message(message_with_password)
            
            if "[PASSWORD_REDACTED]" in filtered and "secret123" not in filtered:
                self.log_test_result("Sensitive Data Filter - Password", True)
            else:
                self.log_test_result("Sensitive Data Filter - Password", False, f"Expected redaction, got: {filtered}")
            
            # Test API key filtering
            message_with_api_key = "API call failed with api_key=abc123xyz789"
            filtered = filter_obj.filter_message(message_with_api_key)
            
            if "[API_KEY_REDACTED]" in filtered and "abc123xyz789" not in filtered:
                self.log_test_result("Sensitive Data Filter - API Key", True)
            else:
                self.log_test_result("Sensitive Data Filter - API Key", False, f"Expected redaction, got: {filtered}")
            
            # Test context filtering
            context = {
                "user_id": "12345",
                "password": "secret",
                "api_key": "key123",
                "normal_data": "this should remain"
            }
            filtered_context = filter_obj.filter_context(context)
            
            if (filtered_context["password"] == "[REDACTED]" and 
                filtered_context["api_key"] == "[REDACTED]" and
                filtered_context["normal_data"] == "this should remain"):
                self.log_test_result("Sensitive Data Filter - Context", True)
            else:
                self.log_test_result("Sensitive Data Filter - Context", False, f"Context filtering failed: {filtered_context}")
        
        except Exception as e:
            self.log_test_result("Sensitive Data Filter", False, f"Exception: {str(e)}")
    
    def test_performance_metrics(self):
        """Test performance metrics tracking"""
        try:
            metrics = PerformanceMetrics()
            
            # Test timing
            metrics.start()
            time.sleep(0.1)  # 100ms
            metrics.stop()
            
            result = metrics.get_metrics()
            
            if 'execution_time_ms' in result and result['execution_time_ms'] >= 100:
                self.log_test_result("Performance Metrics - Timing", True, f"Execution time: {result['execution_time_ms']}ms")
            else:
                self.log_test_result("Performance Metrics - Timing", False, f"Unexpected timing result: {result}")
        
        except Exception as e:
            self.log_test_result("Performance Metrics", False, f"Exception: {str(e)}")
    
    def test_log_entry_serialization(self):
        """Test log entry serialization"""
        try:
            entry = LogEntry(
                timestamp="2024-01-01T12:00:00Z",
                level="ERROR",
                logger_name="test",
                message="Test message",
                request_id="req-123",
                component="test_component",
                error_category="UI",
                tags=["test", "error"]
            )
            
            # Test dictionary conversion
            entry_dict = entry.to_dict()
            if isinstance(entry_dict, dict) and entry_dict['message'] == "Test message":
                self.log_test_result("Log Entry - Dict Conversion", True)
            else:
                self.log_test_result("Log Entry - Dict Conversion", False, "Dict conversion failed")
            
            # Test JSON serialization
            entry_json = entry.to_json()
            parsed = json.loads(entry_json)
            if parsed['message'] == "Test message" and parsed['error_category'] == "UI":
                self.log_test_result("Log Entry - JSON Serialization", True)
            else:
                self.log_test_result("Log Entry - JSON Serialization", False, "JSON serialization failed")
        
        except Exception as e:
            self.log_test_result("Log Entry Serialization", False, f"Exception: {str(e)}")
    
    def test_structured_formatter(self):
        """Test structured formatter"""
        try:
            formatter = StructuredFormatter(include_context=True, include_performance=True)
            
            # Create a mock log record
            record = logging.LogRecord(
                name="test_logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=100,
                msg="Test error message",
                args=(),
                exc_info=None
            )
            
            # Add custom attributes
            record.component = "test_component"
            record.error_category = "UI"
            record.context = {"user_id": "123", "operation": "test"}
            
            formatted = formatter.format(record)
            parsed = json.loads(formatted)
            
            if (parsed['message'] == "Test error message" and 
                parsed['component'] == "test_component" and
                parsed['error_category'] == "UI"):
                self.log_test_result("Structured Formatter", True)
            else:
                self.log_test_result("Structured Formatter", False, f"Formatting failed: {parsed}")
        
        except Exception as e:
            self.log_test_result("Structured Formatter", False, f"Exception: {str(e)}")
    
    def test_logging_configuration(self):
        """Test logging configuration"""
        try:
            # Test development config
            dev_config = LoggingConfig.get_development_config()
            if (dev_config['level'] == 'DEBUG' and 
                len(dev_config['destinations']) > 0 and
                dev_config['include_context'] == True):
                self.log_test_result("Logging Config - Development", True)
            else:
                self.log_test_result("Logging Config - Development", False, "Development config validation failed")
            
            # Test production config
            prod_config = LoggingConfig.get_production_config()
            if (prod_config['level'] == 'INFO' and 
                prod_config['async_logging'] == True):
                self.log_test_result("Logging Config - Production", True)
            else:
                self.log_test_result("Logging Config - Production", False, "Production config validation failed")
            
            # Test config validation
            valid_config = LoggingConfig.get_minimal_config()
            if LoggingConfig.validate_config(valid_config):
                self.log_test_result("Logging Config - Validation", True)
            else:
                self.log_test_result("Logging Config - Validation", False, "Config validation failed")
        
        except Exception as e:
            self.log_test_result("Logging Configuration", False, f"Exception: {str(e)}")
    
    def test_logging_strategy_setup(self):
        """Test logging strategy setup and basic functionality"""
        try:
            # Test with minimal config to avoid file system issues
            config = {
                'level': 'INFO',
                'destinations': [
                    {
                        'type': 'console',
                        'level': 'INFO'
                    }
                ],
                'format': 'structured',
                'include_context': True,
                'include_performance': False,
                'async_logging': False,
                'sensitive_data_protection': True
            }
            
            strategy = LoggingStrategy(config)
            
            if strategy and len(strategy.handlers) > 0:
                self.log_test_result("Logging Strategy - Setup", True)
            else:
                self.log_test_result("Logging Strategy - Setup", False, "Strategy setup failed")
            
            # Test logger creation
            logger = strategy.get_logger("test_logger")
            if logger and logger.name == "test_logger":
                self.log_test_result("Logging Strategy - Logger Creation", True)
            else:
                self.log_test_result("Logging Strategy - Logger Creation", False, "Logger creation failed")
        
        except Exception as e:
            self.log_test_result("Logging Strategy Setup", False, f"Exception: {str(e)}")
    
    def test_error_logging_integration(self):
        """Test integration with error management system"""
        try:
            # Create test error info
            context = ErrorContext(
                operation="test_operation",
                entity_type="test_entity",
                user_id="test_user"
            )
            
            error_info = ErrorInfo(
                error_id="test_error_123",
                error_code="TEST_ERROR",
                message="Test error message",
                category=ErrorCategory.UI,
                severity=ErrorSeverity.HIGH,
                context=context,
                recovery_strategy=RecoveryStrategy.RETRY,
                component="test_component"
            )
            
            # Test error logging (this will use fallback if enhanced logging not available)
            from data.models.error_management import EnhancedErrorLogger
            logger = EnhancedErrorLogger(use_enhanced_logging=False)  # Use fallback
            
            # This should not raise an exception
            logger.log_error(error_info, {"additional": "context"})
            self.log_test_result("Error Logging Integration", True)
        
        except Exception as e:
            self.log_test_result("Error Logging Integration", False, f"Exception: {str(e)}")
    
    def test_error_recovery_logging(self):
        """Test error recovery logging functions"""
        try:
            # Create test error info
            context = ErrorContext(operation="test_recovery")
            error_info = ErrorInfo(
                error_id="recovery_test_123",
                error_code="RECOVERY_TEST",
                message="Recovery test error",
                category=ErrorCategory.PLATFORM,
                severity=ErrorSeverity.MEDIUM,
                context=context,
                recovery_strategy=RecoveryStrategy.RETRY
            )
            
            # Test recovery logging functions (should use fallback)
            log_error_recovery_attempt(error_info, "retry", 1)
            log_error_recovery_attempt(error_info, "retry", 2)
            
            # These should not raise exceptions
            self.log_test_result("Error Recovery Logging", True)
        
        except Exception as e:
            self.log_test_result("Error Recovery Logging", False, f"Exception: {str(e)}")
    
    def test_context_manager(self):
        """Test error handling context manager"""
        try:
            # Test successful operation
            with error_handling_context("test_operation", "test_component", "test_user"):
                time.sleep(0.01)  # Simulate some work
            
            # Test operation with exception
            try:
                with error_handling_context("failing_operation", "test_component"):
                    raise ValueError("Test exception")
            except ValueError:
                pass  # Expected
            
            self.log_test_result("Context Manager", True)
        
        except Exception as e:
            self.log_test_result("Context Manager", False, f"Exception: {str(e)}")
    
    def test_component_logger_config(self):
        """Test component-specific logger configurations"""
        try:
            ui_config = ComponentLoggerConfig.get_ui_logger_config()
            platform_config = ComponentLoggerConfig.get_platform_logger_config()
            
            if (ui_config['name'] == 'ui' and 
                platform_config['name'] == 'platform' and
                'tags' in ui_config and 'tags' in platform_config):
                self.log_test_result("Component Logger Config", True)
            else:
                self.log_test_result("Component Logger Config", False, "Component config validation failed")
        
        except Exception as e:
            self.log_test_result("Component Logger Config", False, f"Exception: {str(e)}")
    
    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting Logging Strategy Test Suite")
        print("=" * 60)
        
        self.setup_test_environment()
        
        try:
            # Run individual tests
            self.test_sensitive_data_filter()
            self.test_performance_metrics()
            self.test_log_entry_serialization()
            self.test_structured_formatter()
            self.test_logging_configuration()
            self.test_logging_strategy_setup()
            self.test_error_logging_integration()
            self.test_error_recovery_logging()
            self.test_context_manager()
            self.test_component_logger_config()
            
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
    test_suite = TestLoggingStrategy()
    success = test_suite.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed! Logging strategy implementation is working correctly.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please review the implementation.")
        return 1


if __name__ == "__main__":
    exit(main()) 