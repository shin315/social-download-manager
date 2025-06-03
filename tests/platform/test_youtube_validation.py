#!/usr/bin/env python3
"""
Test script for YouTube URL validation logic

This script tests the YouTubeHandler's URL validation functionality
with various YouTube URL formats to ensure comprehensive coverage.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from platforms.youtube.youtube_handler import YouTubeHandler


def test_youtube_url_validation():
    """Test YouTube URL validation with various formats"""
    
    # Initialize handler
    handler = YouTubeHandler()
    
    # Test cases - valid URLs
    valid_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "https://www.youtube.com/v/dQw4w9WgXcQ",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
        "http://youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ?t=42",
    ]
    
    # Test cases - invalid URLs
    invalid_urls = [
        "",
        None,
        "https://www.google.com",
        "https://www.tiktok.com/@user/video/123",
        "https://facebook.com/video/123",
        "https://youtube.com",  # No video ID
        "https://youtube.com/watch",  # No video ID
        "https://youtube.com/watch?v=",  # Empty video ID
        "not_a_url",
        "ftp://youtube.com/watch?v=dQw4w9WgXcQ",
    ]
    
    print("🧪 Testing YouTube URL Validation Logic")
    print("=" * 50)
    
    # Test valid URLs
    print("\n✅ Testing Valid URLs:")
    all_valid_passed = True
    
    for url in valid_urls:
        try:
            result = handler.is_valid_url(url)
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {status} {url}")
            
            if not result:
                all_valid_passed = False
        except Exception as e:
            print(f"  ❌ ERROR {url} - {e}")
            all_valid_passed = False
    
    # Test invalid URLs  
    print("\n❌ Testing Invalid URLs:")
    all_invalid_passed = True
    
    for url in invalid_urls:
        try:
            result = handler.is_valid_url(url)
            status = "✅ PASS" if not result else "❌ FAIL"
            print(f"  {status} {url}")
            
            if result:  # Should be False for invalid URLs
                all_invalid_passed = False
        except Exception as e:
            print(f"  ❌ ERROR {url} - {e}")
            all_invalid_passed = False
    
    # Test video ID extraction
    print("\n🎯 Testing Video ID Extraction:")
    test_extraction_cases = [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtube.com/watch?v=dQw4w9WgXcQ&t=42", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ?t=42", "dQw4w9WgXcQ"),
    ]
    
    extraction_passed = True
    for url, expected_id in test_extraction_cases:
        try:
            extracted_id = handler.extract_video_id(url)
            status = "✅ PASS" if extracted_id == expected_id else "❌ FAIL"
            print(f"  {status} {url} -> {extracted_id} (expected: {expected_id})")
            
            if extracted_id != expected_id:
                extraction_passed = False
        except Exception as e:
            print(f"  ❌ ERROR {url} - {e}")
            extraction_passed = False
    
    # Test URL normalization
    print("\n🔧 Testing URL Normalization:")
    normalization_cases = [
        ("https://youtu.be/dQw4w9WgXcQ", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
        ("https://youtube.com/embed/dQw4w9WgXcQ", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
        ("https://youtube.com/watch?v=dQw4w9WgXcQ&t=42", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
    ]
    
    normalization_passed = True
    for url, expected_normalized in normalization_cases:
        try:
            normalized = handler.normalize_url(url)
            status = "✅ PASS" if normalized == expected_normalized else "❌ FAIL"
            print(f"  {status} {url}")
            print(f"    -> {normalized}")
            print(f"    Expected: {expected_normalized}")
            
            if normalized != expected_normalized:
                normalization_passed = False
        except Exception as e:
            print(f"  ❌ ERROR {url} - {e}")
            normalization_passed = False
    
    # Final results
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"  Valid URLs: {'✅ PASS' if all_valid_passed else '❌ FAIL'}")
    print(f"  Invalid URLs: {'✅ PASS' if all_invalid_passed else '❌ FAIL'}")
    print(f"  ID Extraction: {'✅ PASS' if extraction_passed else '❌ FAIL'}")
    print(f"  URL Normalization: {'✅ PASS' if normalization_passed else '❌ FAIL'}")
    
    overall_success = all_valid_passed and all_invalid_passed and extraction_passed and normalization_passed
    print(f"\n🏆 Overall: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    return overall_success


if __name__ == "__main__":
    success = test_youtube_url_validation()
    sys.exit(0 if success else 1) 