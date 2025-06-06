#!/usr/bin/env python3
"""
Task 11.1: URL Processing and Validation Testing
Test URL validation with real TikTok URLs and edge cases
"""

import sys
import re
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from platforms.tiktok.tiktok_handler import TikTokHandler
from data.models.validators import URLValidator

def test_url_patterns():
    """Test URL regex patterns directly"""
    print("🔍 Testing URL Regex Patterns")
    print("=" * 40)
    
    # URL patterns from TikTokHandler
    url_patterns = [
        r'https?://(www\.)?tiktok\.com/@[\w\.-]+/video/\d+',
        r'https?://(www\.)?tiktok\.com/@[\w\.-]+/video/\d+\?[\w=&]+',
        r'https?://(vm\.|vt\.)?tiktok\.com/\w+',
        r'https?://(www\.)?tiktok\.com/t/\w+',
        r'https?://(www\.)?tiktok\.com/@[\w\.-]+/video/\d+\?is_from_webapp=1',
    ]
    
    # Test URLs
    test_urls = [
        # Valid URLs (should match)
        ("https://www.tiktok.com/@dangbeo9/video/7512675061443071250", True, "Confirmed working URL"),
        ("https://tiktok.com/@dangbeo9/video/7512675061443071250", True, "Without www"),
        ("https://www.tiktok.com/@user.name/video/1234567890", True, "Username with dot"),
        ("https://www.tiktok.com/@user_name/video/1234567890", True, "Username with underscore"),
        ("https://www.tiktok.com/@user-name/video/1234567890", True, "Username with hyphen"),
        ("https://www.tiktok.com/@dangbeo9/video/7512675061443071250?is_from_webapp=1", True, "With webapp param"),
        ("https://www.tiktok.com/@user/video/123?param=value&other=test", True, "With multiple params"),
        ("https://vm.tiktok.com/ZMxxxxxx/", True, "Short URL vm.tiktok.com"),
        ("https://vt.tiktok.com/ZSxxxxxx/", True, "Short URL vt.tiktok.com"),
        ("https://www.tiktok.com/t/ZTxxxxxx/", True, "Mobile share URL"),
        
        # Invalid URLs (should NOT match)
        ("https://www.tiktok.com/@user/photo/1234567890", False, "Photo URL (unsupported)"),
        ("https://youtube.com/watch?v=abc123", False, "YouTube URL"),
        ("https://instagram.com/p/abc123/", False, "Instagram URL"),
        ("https://www.tiktok.com/@user", False, "Missing video path"),
        ("https://www.tiktok.com/@user/video/", False, "Missing video ID"),
        ("https://www.tiktok.com/", False, "TikTok homepage"),
        ("", False, "Empty string"),
        ("not_a_url", False, "Invalid format"),
        ("http://malicious-site.com", False, "Non-TikTok URL"),
        
        # Edge cases
        ("https://www.tiktok.com/@user123.test_name-abc/video/7512675061443071250", True, "Complex username"),
        ("https://www.tiktok.com/@a/video/1", True, "Minimal valid URL"),
        ("HTTPS://WWW.TIKTOK.COM/@USER/VIDEO/123", False, "Uppercase (case sensitive)"),
    ]
    
    total_tests = len(test_urls)
    passed_tests = 0
    
    for url, expected, description in test_urls:
        # Test against all patterns
        matches_any = False
        matching_pattern = None
        
        for pattern in url_patterns:
            if re.match(pattern, url):
                matches_any = True
                matching_pattern = pattern
                break
        
        result = matches_any
        status = "✅" if result == expected else "❌"
        pattern_info = f"(matched: {matching_pattern})" if matching_pattern else ""
        
        print(f"   {status} {description}")
        print(f"      URL: {url}")
        print(f"      Expected: {expected}, Got: {result} {pattern_info}")
        print()
        
        if result == expected:
            passed_tests += 1
    
    print(f"📊 URL Pattern Tests: {passed_tests}/{total_tests} passed")
    return passed_tests == total_tests

def test_tiktok_handler_validation():
    """Test TikTokHandler URL validation"""
    print("\n🎯 Testing TikTokHandler URL Validation")
    print("=" * 40)
    
    handler = TikTokHandler()
    
    test_urls = [
        # Valid URLs
        ("https://www.tiktok.com/@dangbeo9/video/7512675061443071250", True, "Confirmed working URL"),
        ("https://www.tiktok.com/@user/video/1234567890", True, "Standard format"),
        ("https://vm.tiktok.com/ZMxxxxxx/", True, "Short URL"),
        ("https://www.tiktok.com/t/ZTxxxxxx/", True, "Mobile share URL"),
        
        # Invalid URLs
        ("https://www.tiktok.com/@user/photo/1234567890", False, "Photo URL (explicitly unsupported)"),
        ("https://youtube.com/watch?v=abc123", False, "YouTube URL"),
        ("", False, "Empty string"),
        (None, False, "None value"),
        
        # Edge cases
        ("https://www.tiktok.com/@user/video/", False, "Missing video ID"),
        ("https://www.tiktok.com/@user", False, "Missing video path"),
    ]
    
    total_tests = len(test_urls)
    passed_tests = 0
    
    for url, expected, description in test_urls:
        try:
            result = handler.is_valid_url(url)
            status = "✅" if result == expected else "❌"
            
            print(f"   {status} {description}")
            print(f"      URL: {url}")
            print(f"      Expected: {expected}, Got: {result}")
            print()
            
            if result == expected:
                passed_tests += 1
                
        except Exception as e:
            print(f"   ❌ {description} - Exception: {e}")
            print(f"      URL: {url}")
            print()
    
    print(f"📊 TikTokHandler Tests: {passed_tests}/{total_tests} passed")
    return passed_tests == total_tests

def test_url_validator_class():
    """Test URLValidator class from validators.py"""
    print("\n🔧 Testing URLValidator Class")
    print("=" * 40)
    
    test_urls = [
        # TikTok URLs
        ("https://www.tiktok.com/@dangbeo9/video/7512675061443071250", "tiktok", True, "Confirmed working URL"),
        ("https://vm.tiktok.com/ZMxxxxxx/", "tiktok", True, "Short TikTok URL"),
        
        # Other platforms (should fail for TikTok validation)
        ("https://youtube.com/watch?v=abc123", "tiktok", False, "YouTube URL tested as TikTok"),
        
        # Invalid
        ("", "tiktok", False, "Empty URL"),
        ("not_a_url", "tiktok", False, "Invalid format"),
    ]
    
    total_tests = len(test_urls)
    passed_tests = 0
    
    for url, platform, expected, description in test_urls:
        try:
            # Test platform URL validation
            if expected:
                result_url = URLValidator.validate_platform_url(url, platform)
                result = result_url == url  # Should return same URL if valid
            else:
                try:
                    URLValidator.validate_platform_url(url, platform)
                    result = True  # If no exception, it's valid
                except:
                    result = False  # Exception means invalid
            
            status = "✅" if result == expected else "❌"
            
            print(f"   {status} {description}")
            print(f"      URL: {url}")
            print(f"      Platform: {platform}")
            print(f"      Expected: {expected}, Got: {result}")
            print()
            
            if result == expected:
                passed_tests += 1
                
        except Exception as e:
            print(f"   ❌ {description} - Exception: {e}")
            print(f"      URL: {url}")
            print()
    
    print(f"📊 URLValidator Tests: {passed_tests}/{total_tests} passed")
    return passed_tests == total_tests

async def test_real_url_info_extraction():
    """Test actual info extraction with confirmed working URL"""
    print("\n🚀 Testing Real URL Info Extraction")
    print("=" * 40)
    
    handler = TikTokHandler()
    confirmed_url = "https://www.tiktok.com/@dangbeo9/video/7512675061443071250"
    
    print(f"Testing with confirmed working URL: {confirmed_url}")
    
    try:
        # First validate the URL
        is_valid = handler.is_valid_url(confirmed_url)
        print(f"✅ URL Validation: {is_valid}")
        
        if not is_valid:
            print("❌ URL validation failed - cannot proceed with info extraction")
            return False
        
        # Try to extract info (this will test the full pipeline)
        print("📡 Attempting to extract video info...")
        
        try:
            video_info = await handler.get_video_info(confirmed_url)
            
            print("✅ Video info extraction successful!")
            print(f"   Title: {video_info.title}")
            print(f"   Creator: {video_info.creator}")
            print(f"   Duration: {video_info.duration}s")
            print(f"   Platform: {video_info.platform}")
            
            # Check available formats/qualities
            if hasattr(video_info, 'quality_levels'):
                print(f"   Quality levels available: {len(video_info.quality_levels)}")
            elif hasattr(video_info, 'formats') and video_info.formats:
                print(f"   Formats available: {len(video_info.formats)}")
            else:
                print("   Video info extracted successfully (format details vary)")
            
            return True
            
        except Exception as e:
            print(f"❌ Video info extraction failed: {e}")
            print("   This could be due to:")
            print("   - Network connectivity issues")
            print("   - TikTok API changes")
            print("   - Rate limiting")
            print("   - Video no longer available")
            return False
    
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False

def test_edge_case_urls():
    """Test edge case URLs that might cause issues"""
    print("\n🔬 Testing Edge Case URLs")
    print("=" * 40)
    
    handler = TikTokHandler()
    
    edge_cases = [
        # Very long URLs
        ("https://www.tiktok.com/@" + "a" * 50 + "/video/7512675061443071250", "Very long username"),
        
        # URLs with many parameters
        ("https://www.tiktok.com/@dangbeo9/video/7512675061443071250?param1=value1&param2=value2&param3=value3&is_from_webapp=1&source=h5_m", "Many parameters"),
        
        # URLs with fragments
        ("https://www.tiktok.com/@dangbeo9/video/7512675061443071250#fragment", "With fragment"),
        
        # Case variations
        ("https://www.tiktok.com/@DangBeo9/video/7512675061443071250", "Mixed case username"),
        
        # Unicode in username (might not be valid but test handling)
        ("https://www.tiktok.com/@dàng🎵/video/7512675061443071250", "Unicode username"),
        
        # Malformed but close
        ("https://www.tiktok.com/@dangbeo9/video/7512675061443071250/", "Trailing slash"),
        ("https://www.tiktok.com/@dangbeo9/video/7512675061443071250?", "Trailing question mark"),
    ]
    
    total_tests = len(edge_cases)
    passed_tests = 0
    
    for url, description in edge_cases:
        try:
            result = handler.is_valid_url(url)
            print(f"   {'✅' if result else '❌'} {description}")
            print(f"      URL: {url}")
            print(f"      Result: {result}")
            print()
            
            # For edge cases, we just need to ensure no crashes
            passed_tests += 1
            
        except Exception as e:
            print(f"   ❌ {description} - Exception: {e}")
            print(f"      URL: {url}")
            print()
    
    print(f"📊 Edge Case Tests: {passed_tests}/{total_tests} completed without crashes")
    return passed_tests == total_tests

async def main():
    """Run all URL validation tests"""
    print("🧪 Task 11.1: URL Processing and Validation Testing")
    print("=" * 60)
    print()
    
    # Track overall results
    all_tests_passed = True
    
    # Run test suites
    tests = [
        ("URL Pattern Tests", test_url_patterns()),
        ("TikTokHandler Tests", test_tiktok_handler_validation()),
        ("URLValidator Tests", test_url_validator_class()),
        ("Edge Case Tests", test_edge_case_urls()),
    ]
    
    # Run async test
    print("\n" + "="*60)
    real_url_test = await test_real_url_info_extraction()
    tests.append(("Real URL Info Extraction", real_url_test))
    
    print("\n" + "="*60)
    print("📋 FINAL RESULTS")
    print("=" * 60)
    
    for test_name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if not result:
            all_tests_passed = False
    
    print("\n" + "="*60)
    if all_tests_passed:
        print("🎉 ALL TESTS PASSED! URL validation is working correctly.")
    else:
        print("⚠️  Some tests failed. Review the implementation.")
    
    print("="*60)
    return all_tests_passed

if __name__ == "__main__":
    asyncio.run(main()) 