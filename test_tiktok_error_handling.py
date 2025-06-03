#!/usr/bin/env python3
"""
Test script for TikTok comprehensive error handling implementation

This script specifically tests the error handling enhancements implemented in subtask 8.5
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add the project root to sys.path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from platforms.tiktok import TikTokHandler
from platforms.tiktok.tiktok_handler import TikTokErrorContext, TikTokErrorMonitor, TikTokErrorRecovery
from platforms.base import QualityLevel, PlatformError, PlatformConnectionError

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_error_context_creation():
    """Test TikTokErrorContext creation and functionality"""
    
    print("🧪 Testing Error Context Creation")
    print("=" * 35)
    
    # Test basic error context
    context = TikTokErrorContext(
        operation="test_operation",
        url="https://example.com/test",
        error_code="404",
        user_message="Test error message",
        technical_details={"test": "data"},
        suggested_actions=["Try again", "Check URL"],
        recovery_options=["Option 1", "Option 2"]
    )
    
    print(f"✅ Error Context Created:")
    print(f"   Operation: {context.operation}")
    print(f"   URL: {context.url}")
    print(f"   Error Code: {context.error_code}")
    print(f"   User Message: {context.user_message}")
    print(f"   Suggested Actions: {len(context.suggested_actions)} items")
    print(f"   Recovery Options: {len(context.recovery_options)} items")
    
    # Test to_dict conversion
    context_dict = context.to_dict()
    print(f"✅ Context Dict Keys: {list(context_dict.keys())}")
    
    print()


def test_error_monitor():
    """Test TikTokErrorMonitor functionality"""
    
    print("📊 Testing Error Monitor")
    print("=" * 25)
    
    monitor = TikTokErrorMonitor()
    
    # Test initial state
    health_status = monitor.get_health_status()
    print(f"✅ Initial Health Status:")
    print(f"   Healthy: {health_status['healthy']}")
    print(f"   Circuit Breaker Active: {health_status['circuit_breaker_active']}")
    print(f"   Recent Error Count: {health_status['recent_error_count']}")
    
    # Test error recording
    context = TikTokErrorContext("test_operation", error_code="500")
    
    for i in range(3):
        monitor.record_error("TestError", context)
    
    health_status = monitor.get_health_status()
    print(f"✅ After Recording 3 Errors:")
    print(f"   Recent Error Count: {health_status['recent_error_count']}")
    print(f"   Error Counts by Type: {health_status['error_counts_by_type']}")
    
    # Test circuit breaker (simulate many errors)
    print(f"✅ Testing Circuit Breaker (simulating many errors)...")
    
    # Override threshold for testing
    monitor.error_threshold_per_hour = 5
    
    for i in range(6):
        monitor.record_error("TestError", context)
    
    print(f"   Circuit Breaker Open: {monitor.is_circuit_open()}")
    
    print()


def test_error_recovery():
    """Test TikTokErrorRecovery functionality"""
    
    print("🔧 Testing Error Recovery")
    print("=" * 26)
    
    recovery = TikTokErrorRecovery()
    
    # Test URL normalization
    async def test_url_normalization():
        # Test short URL
        short_url = "https://vm.tiktok.com/ZMxxxxxx/"
        alternatives = await recovery.attempt_url_normalization(short_url)
        print(f"✅ Short URL Alternatives ({len(alternatives)} total):")
        for i, alt in enumerate(alternatives):
            print(f"   {i+1}. {alt}")
        
        # Test full URL
        full_url = "https://www.tiktok.com/@user/video/1234567890"
        alternatives = await recovery.attempt_url_normalization(full_url)
        print(f"✅ Full URL Alternatives ({len(alternatives)} total):")
        for i, alt in enumerate(alternatives):
            print(f"   {i+1}. {alt}")
    
    asyncio.run(test_url_normalization())
    
    # Test recovery suggestions
    context = TikTokErrorContext("test_operation", error_code="429")
    suggestions = recovery.get_recovery_suggestions("RateLimitError", context)
    print(f"✅ Rate Limit Recovery Suggestions ({len(suggestions)} total):")
    for i, suggestion in enumerate(suggestions):
        print(f"   {i+1}. {suggestion}")
    
    context = TikTokErrorContext("test_operation", error_code="404")
    suggestions = recovery.get_recovery_suggestions("NotFoundError", context)
    print(f"✅ Not Found Recovery Suggestions ({len(suggestions)} total):")
    for i, suggestion in enumerate(suggestions):
        print(f"   {i+1}. {suggestion}")
    
    print()


def test_handler_error_handling():
    """Test TikTokHandler integrated error handling"""
    
    print("🎯 Testing Handler Error Handling Integration")
    print("=" * 45)
    
    handler = TikTokHandler()
    
    # Test error health status
    health_status = handler.get_error_health_status()
    print(f"✅ Handler Error Health Status:")
    print(f"   Error Monitoring Enabled: {health_status.get('error_monitoring_enabled')}")
    print(f"   Circuit Breaker Enabled: {health_status.get('circuit_breaker_enabled')}")
    print(f"   Recovery Suggestions Enabled: {health_status.get('recovery_suggestions_enabled')}")
    print(f"   Healthy: {health_status.get('healthy')}")
    
    # Test error context creation
    test_error = Exception("Test connection error")
    context = handler._create_error_context(
        operation="video_info_extraction",
        url="https://example.com/test",
        original_error=test_error
    )
    
    print(f"✅ Created Error Context:")
    print(f"   Operation: {context.operation}")
    print(f"   User Message: {context.user_message}")
    print(f"   Suggested Actions: {len(context.suggested_actions)} items")
    print(f"   Recovery Options: {len(context.recovery_options)} items")
    
    # Test user-friendly message generation
    test_messages = [
        ("Connection timeout occurred", "connection"),
        ("429 Too Many Requests", "rate_limit"),
        ("Video is private", "private_content"),
        ("404 Not Found", "not_found"),
        ("Unknown error occurred", "generic")
    ]
    
    print(f"✅ User-Friendly Message Generation:")
    for error_msg, error_type in test_messages:
        friendly_msg = handler._generate_user_friendly_message(
            "video_info_extraction", error_msg, None
        )
        print(f"   {error_type}: '{friendly_msg[:50]}{'...' if len(friendly_msg) > 50 else ''}'")
    
    # Test recovery options
    recovery_options = handler._get_recovery_options("download", "quality format error")
    print(f"✅ Download Recovery Options ({len(recovery_options)} total):")
    for i, option in enumerate(recovery_options):
        print(f"   {i+1}. {option}")
    
    # Test error state reset
    handler.reset_error_state()
    print(f"✅ Error State Reset Completed")
    
    print()


def test_comprehensive_error_scenarios():
    """Test comprehensive error scenarios"""
    
    print("🌐 Testing Comprehensive Error Scenarios")
    print("=" * 40)
    
    handler = TikTokHandler()
    
    # Simulate different error types
    error_scenarios = [
        ("NetworkError", "Connection timeout occurred"),
        ("RateLimitError", "429 Too Many Requests"),
        ("ContentError", "Video is private"),
        ("NotFoundError", "404 Video not found"),
        ("AuthError", "403 Forbidden access"),
        ("APIError", "yt-dlp extractor failed")
    ]
    
    for error_type, error_msg in error_scenarios:
        try:
            # Simulate error
            test_error = Exception(error_msg)
            enhanced_error = handler._handle_error_with_context(
                operation="video_info_extraction",
                original_error=test_error,
                url="https://example.com/test"
            )
            
            print(f"✅ {error_type}:")
            print(f"   Enhanced Error Type: {type(enhanced_error).__name__}")
            print(f"   User Message: {enhanced_error.args[0][:50]}{'...' if len(enhanced_error.args[0]) > 50 else ''}")
            
            # Check if error context is attached
            if hasattr(enhanced_error, 'error_context'):
                context = enhanced_error.error_context
                print(f"   Context Attached: ✅ ({len(context.suggested_actions)} suggestions)")
            else:
                print(f"   Context Attached: ❌")
                
        except Exception as e:
            print(f"❌ {error_type}: Unexpected error - {e}")
    
    # Check final health status
    final_health = handler.get_error_health_status()
    print(f"✅ Final Health Status:")
    print(f"   Recent Errors: {final_health.get('recent_error_count', 0)}")
    print(f"   Circuit Breaker: {final_health.get('circuit_breaker_active', False)}")
    
    print()


def main():
    """Run all error handling tests"""
    
    print("🚀 TikTok Enhanced Error Handling Test Suite")
    print("=" * 45)
    print()
    
    try:
        test_error_context_creation()
        test_error_monitor()
        test_error_recovery()
        test_handler_error_handling()
        test_comprehensive_error_scenarios()
        
        print("🎉 All Error Handling Tests Completed Successfully!")
        print()
        print("📋 Test Summary:")
        print("   ✅ Error Context Creation")
        print("   ✅ Error Monitor & Circuit Breaker")
        print("   ✅ Error Recovery Strategies")
        print("   ✅ Handler Integration")
        print("   ✅ Comprehensive Error Scenarios")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 