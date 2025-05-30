"""
Demonstration of Enhanced Logging Strategy

This script demonstrates the comprehensive logging strategy implementation
with various scenarios including error handling, performance monitoring,
and sensitive data protection.
"""

import os
import sys
import time
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

from core.logging_strategy import (
    setup_enhanced_logging, get_enhanced_logger, log_error_with_context,
    log_operation_start, log_operation_end, log_performance_metrics
)
from core.logging_config import LoggingConfig
from data.models.error_management import (
    ErrorInfo, ErrorCategory, ErrorSeverity, ErrorContext, RecoveryStrategy,
    error_handling_context, log_error_recovery_attempt, log_error_recovery_success
)


def demo_basic_logging():
    """Demonstrate basic enhanced logging"""
    print("\n🔍 Demo 1: Basic Enhanced Logging")
    print("-" * 40)
    
    # Setup enhanced logging with development config
    config = LoggingConfig.get_development_config()
    # Use console only for demo
    config['destinations'] = [{'type': 'console', 'level': 'INFO'}]
    config['async_logging'] = False
    
    strategy = setup_enhanced_logging(config)
    logger = get_enhanced_logger("demo")
    
    # Basic logging with context
    extra = {
        'component': 'demo_module',
        'operation': 'basic_logging_demo',
        'context': {'demo_type': 'basic', 'user_id': 'demo_user'},
        'tags': ['demo', 'basic_logging']
    }
    
    logger.info("Starting basic logging demonstration", extra=extra)
    logger.warning("This is a warning message with context", extra=extra)
    
    print("✅ Basic logging completed")


def demo_sensitive_data_protection():
    """Demonstrate sensitive data protection"""
    print("\n🔒 Demo 2: Sensitive Data Protection")
    print("-" * 40)
    
    logger = get_enhanced_logger("security_demo")
    
    # Log messages with sensitive data
    extra = {
        'component': 'security_module',
        'operation': 'login_attempt',
        'context': {
            'username': 'john_doe',
            'password': 'secret123',  # This should be redacted
            'api_key': 'sk-1234567890abcdef',  # This should be redacted
            'email': 'john@example.com',  # This should be redacted
            'session_data': 'normal_data'
        },
        'tags': ['security', 'login']
    }
    
    logger.warning("Login attempt with sensitive data", extra=extra)
    
    # Direct message with sensitive data
    logger.error("API call failed with api_key=sk-abcdef123456 and password=mysecret")
    
    print("✅ Sensitive data protection demonstrated")


def demo_error_logging_integration():
    """Demonstrate error logging integration"""
    print("\n❌ Demo 3: Error Logging Integration")
    print("-" * 40)
    
    # Create error context
    context = ErrorContext(
        operation="file_download",
        entity_type="video",
        entity_id="video_123",
        user_id="demo_user",
        session_id="session_456"
    )
    
    # Create error info
    error_info = ErrorInfo(
        error_id="ERR_DEMO_001",
        error_code="DOWNLOAD_FAILED",
        message="Failed to download video due to network timeout",
        category=ErrorCategory.DOWNLOAD,
        severity=ErrorSeverity.HIGH,
        context=context,
        recovery_strategy=RecoveryStrategy.RETRY,
        component="download_service",
        error_type="NETWORK_TIMEOUT"
    )
    
    # Log error with enhanced context
    additional_context = {
        'file_size': '50MB',
        'download_url': 'https://example.com/video.mp4',
        'retry_count': 2,
        'timeout_duration': '30s'
    }
    
    log_error_with_context("download_service", error_info, additional_context)
    
    print("✅ Error logging integration demonstrated")


def demo_performance_monitoring():
    """Demonstrate performance monitoring"""
    print("\n⚡ Demo 4: Performance Monitoring")
    print("-" * 40)
    
    # Simulate operation with performance tracking
    start_time = time.time()
    
    # Simulate some work
    time.sleep(0.1)  # 100ms operation
    
    end_time = time.time()
    execution_time = (end_time - start_time) * 1000
    
    # Log performance metrics
    metrics = {
        'execution_time_ms': execution_time,
        'memory_usage_mb': 45.2,
        'cpu_usage_percent': 12.5,
        'operation_type': 'video_processing',
        'file_size_mb': 25.8
    }
    
    log_performance_metrics("video_processor", "process_video", metrics, "media_service")
    
    print(f"✅ Performance monitoring demonstrated (Operation took {execution_time:.1f}ms)")


def demo_error_recovery_logging():
    """Demonstrate error recovery logging"""
    print("\n🔄 Demo 5: Error Recovery Logging")
    print("-" * 40)
    
    # Create error for recovery demonstration
    context = ErrorContext(operation="api_call", entity_type="platform_request")
    error_info = ErrorInfo(
        error_id="ERR_RECOVERY_001",
        error_code="API_RATE_LIMIT",
        message="API rate limit exceeded",
        category=ErrorCategory.PLATFORM,
        severity=ErrorSeverity.MEDIUM,
        context=context,
        recovery_strategy=RecoveryStrategy.RETRY,
        component="platform_handler"
    )
    
    # Simulate recovery attempts
    for attempt in range(1, 4):
        log_error_recovery_attempt(error_info, "exponential_backoff", attempt)
        time.sleep(0.05)  # Simulate retry delay
        
        if attempt == 3:  # Success on third attempt
            log_error_recovery_success(error_info, "exponential_backoff", attempt)
            break
    
    print("✅ Error recovery logging demonstrated")


def demo_context_manager():
    """Demonstrate error handling context manager"""
    print("\n🎯 Demo 6: Context Manager")
    print("-" * 40)
    
    # Successful operation
    try:
        with error_handling_context("data_processing", "analytics_service", "demo_user"):
            time.sleep(0.05)  # Simulate work
            print("  Processing data successfully...")
    except Exception as e:
        print(f"  Unexpected error: {e}")
    
    # Operation with error
    try:
        with error_handling_context("risky_operation", "test_service"):
            time.sleep(0.02)  # Simulate some work
            raise ValueError("Simulated error for demonstration")
    except ValueError as e:
        print(f"  Expected error caught: {e}")
    
    print("✅ Context manager demonstrated")


def demo_structured_logging():
    """Demonstrate structured logging output"""
    print("\n📋 Demo 7: Structured Logging")
    print("-" * 40)
    
    logger = get_enhanced_logger("structured_demo")
    
    # Complex structured log entry
    extra = {
        'request_id': 'req_demo_123',
        'session_id': 'sess_demo_456',
        'user_id': 'user_demo_789',
        'component': 'user_interface',
        'operation': 'video_download_request',
        'error_category': 'UI',
        'error_type': 'VALIDATION_ERROR',
        'error_code': 'UI_VALID_001',
        'severity': 'medium',
        'recovery_strategy': 'user_input',
        'context': {
            'form_data': {
                'url': 'https://example.com/video',
                'quality': '1080p',
                'format': 'mp4'
            },
            'validation_errors': ['Invalid URL format', 'Unsupported quality'],
            'user_agent': 'Mozilla/5.0...',
            'timestamp': datetime.now().isoformat()
        },
        'performance_metrics': {
            'validation_time_ms': 15.2,
            'form_render_time_ms': 45.8
        },
        'tags': ['ui', 'validation', 'user_input', 'demo']
    }
    
    logger.error("Form validation failed for video download request", extra=extra)
    
    print("✅ Structured logging demonstrated")


def demo_component_specific_logging():
    """Demonstrate component-specific logging"""
    print("\n🧩 Demo 8: Component-Specific Logging")
    print("-" * 40)
    
    # UI Component logging
    ui_logger = get_enhanced_logger("ui_component")
    ui_extra = {
        'component': 'main_window',
        'operation': 'button_click',
        'context': {'button_id': 'download_btn', 'user_action': 'click'},
        'tags': ['ui', 'user_interaction']
    }
    ui_logger.info("User clicked download button", extra=ui_extra)
    
    # Platform Handler logging
    platform_logger = get_enhanced_logger("platform_handler")
    platform_extra = {
        'component': 'tiktok_handler',
        'operation': 'api_request',
        'context': {'endpoint': '/video/info', 'video_id': 'tk123'},
        'tags': ['platform', 'api', 'tiktok']
    }
    platform_logger.info("Making API request to TikTok", extra=platform_extra)
    
    # Download Service logging
    download_logger = get_enhanced_logger("download_service")
    download_extra = {
        'component': 'file_downloader',
        'operation': 'download_progress',
        'context': {'progress': '75%', 'speed': '2.5MB/s'},
        'performance_metrics': {'bytes_downloaded': 37500000, 'time_elapsed_s': 15},
        'tags': ['download', 'progress', 'file_system']
    }
    download_logger.info("Download progress update", extra=download_extra)
    
    print("✅ Component-specific logging demonstrated")


def main():
    """Main demonstration"""
    print("🚀 Enhanced Logging Strategy Demonstration")
    print("=" * 60)
    print("This demo shows the comprehensive logging capabilities")
    print("including error handling, performance monitoring, and data protection.")
    print("=" * 60)
    
    try:
        # Run all demonstrations
        demo_basic_logging()
        demo_sensitive_data_protection()
        demo_error_logging_integration()
        demo_performance_monitoring()
        demo_error_recovery_logging()
        demo_context_manager()
        demo_structured_logging()
        demo_component_specific_logging()
        
        print("\n" + "=" * 60)
        print("🎉 All logging demonstrations completed successfully!")
        print("=" * 60)
        print("\nKey Features Demonstrated:")
        print("✅ Structured JSON logging with comprehensive context")
        print("✅ Sensitive data protection and redaction")
        print("✅ Error categorization and severity handling")
        print("✅ Performance metrics tracking")
        print("✅ Error recovery logging")
        print("✅ Context managers for operation tracking")
        print("✅ Component-specific logging configurations")
        print("✅ Integration with error management system")
        
        print("\nLogging Strategy Benefits:")
        print("🔍 Enhanced debugging with detailed context")
        print("📊 Performance monitoring and optimization")
        print("🔒 Security through sensitive data protection")
        print("📈 Error trend analysis and monitoring")
        print("🎯 Component-specific insights")
        print("⚡ Asynchronous logging for performance")
        print("🔄 Automatic error recovery tracking")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 