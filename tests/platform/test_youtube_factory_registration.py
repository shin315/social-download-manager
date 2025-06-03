#!/usr/bin/env python3
"""
Test script for YouTube Handler platform factory registration

This script tests that the YouTubeHandler is properly registered
with the platform factory and can be created correctly.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import platforms module to trigger registration
import platforms
from platforms.base import (
    PlatformFactory,
    PlatformType,
    create_handler_for_url,
    detect_platform,
    is_url_supported,
    get_supported_platforms
)
from platforms.youtube.youtube_handler import YouTubeHandler


def test_youtube_factory_registration():
    """Test YouTube handler factory registration"""
    
    print("🧪 Testing YouTube Handler Factory Registration")
    print("=" * 55)
    
    tests_passed = 0
    total_tests = 0
    
    # Test 1: Platform detection
    print("\n1️⃣ Testing platform detection:")
    total_tests += 1
    try:
        test_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://youtube.com/embed/dQw4w9WgXcQ",
            "https://m.youtube.com/watch?v=dQw4w9WgXcQ"
        ]
        
        all_detected = True
        for url in test_urls:
            detected = detect_platform(url)
            if detected != PlatformType.YOUTUBE:
                print(f"  ❌ Failed to detect YouTube: {url} -> {detected}")
                all_detected = False
            else:
                print(f"  ✅ Detected: {url} -> {detected.display_name}")
        
        if all_detected:
            print("  ✅ PASS - All YouTube URLs detected correctly")
            tests_passed += 1
        else:
            print("  ❌ FAIL - Some URLs not detected as YouTube")
        
    except Exception as e:
        print(f"  ❌ FAIL - {e}")
    
    # Test 2: URL support check
    print("\n2️⃣ Testing URL support checking:")
    total_tests += 1
    try:
        youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        non_youtube_url = "https://www.google.com"
        
        youtube_supported = is_url_supported(youtube_url)
        non_youtube_supported = is_url_supported(non_youtube_url)
        
        if youtube_supported and not non_youtube_supported:
            print("  ✅ PASS - URL support detection working")
            print(f"    YouTube URL supported: {youtube_supported}")
            print(f"    Non-YouTube URL supported: {non_youtube_supported}")
            tests_passed += 1
        else:
            print(f"  ❌ FAIL - YouTube: {youtube_supported}, Non-YouTube: {non_youtube_supported}")
        
    except Exception as e:
        print(f"  ❌ FAIL - {e}")
    
    # Test 3: Supported platforms list
    print("\n3️⃣ Testing supported platforms list:")
    total_tests += 1
    try:
        supported_platforms = get_supported_platforms()
        
        if PlatformType.YOUTUBE in supported_platforms:
            print("  ✅ PASS - YouTube in supported platforms")
            print(f"    Supported platforms: {[p.display_name for p in supported_platforms]}")
            tests_passed += 1
        else:
            print(f"  ❌ FAIL - YouTube not in supported platforms: {[p.display_name for p in supported_platforms]}")
        
    except Exception as e:
        print(f"  ❌ FAIL - {e}")
    
    # Test 4: Handler creation via factory
    print("\n4️⃣ Testing handler creation via factory:")
    total_tests += 1
    try:
        factory = PlatformFactory()
        handler = factory.create_handler(PlatformType.YOUTUBE)
        
        if isinstance(handler, YouTubeHandler):
            print("  ✅ PASS - Factory creates YouTubeHandler instance")
            print(f"    Handler type: {type(handler).__name__}")
            tests_passed += 1
        else:
            print(f"  ❌ FAIL - Wrong handler type: {type(handler)}")
        
    except Exception as e:
        print(f"  ❌ FAIL - {e}")
    
    # Test 5: Handler creation from URL
    print("\n5️⃣ Testing handler creation from URL:")
    total_tests += 1
    try:
        youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        handler = create_handler_for_url(youtube_url)
        
        if isinstance(handler, YouTubeHandler):
            print("  ✅ PASS - Creates YouTubeHandler from URL")
            print(f"    Handler type: {type(handler).__name__}")
            print(f"    Platform type: {handler.platform_type.display_name}")
            tests_passed += 1
        else:
            print(f"  ❌ FAIL - Wrong handler type: {type(handler)}")
        
    except Exception as e:
        print(f"  ❌ FAIL - {e}")
    
    # Test 6: Handler functionality test
    print("\n6️⃣ Testing handler functionality:")
    total_tests += 1
    try:
        youtube_url = "https://youtu.be/dQw4w9WgXcQ"
        handler = create_handler_for_url(youtube_url)
        
        # Test URL validation
        is_valid = handler.is_valid_url(youtube_url)
        
        # Test capabilities
        capabilities = handler.get_capabilities()
        
        if is_valid and capabilities.supports_video:
            print("  ✅ PASS - Handler functionality working")
            print(f"    URL validation: {is_valid}")
            print(f"    Supports video: {capabilities.supports_video}")
            tests_passed += 1
        else:
            print(f"  ❌ FAIL - URL valid: {is_valid}, Supports video: {capabilities.supports_video}")
        
    except Exception as e:
        print(f"  ❌ FAIL - {e}")
    
    # Test 7: Platform type consistency
    print("\n7️⃣ Testing platform type consistency:")
    total_tests += 1
    try:
        handler = create_handler_for_url("https://www.youtube.com/watch?v=test")
        detected_platform = detect_platform("https://www.youtube.com/watch?v=test")
        
        if handler.platform_type == detected_platform == PlatformType.YOUTUBE:
            print("  ✅ PASS - Platform type consistency maintained")
            print(f"    Handler platform: {handler.platform_type.display_name}")
            print(f"    Detected platform: {detected_platform.display_name}")
            tests_passed += 1
        else:
            print(f"  ❌ FAIL - Inconsistent platform types")
        
    except Exception as e:
        print(f"  ❌ FAIL - {e}")
    
    # Final results
    print("\n" + "=" * 55)
    print("📊 Factory Registration Test Results:")
    print(f"  Tests Passed: {tests_passed}/{total_tests}")
    print(f"  Success Rate: {(tests_passed/total_tests*100):.1f}%")
    
    if tests_passed == total_tests:
        print("\n🏆 YOUTUBE HANDLER FACTORY REGISTRATION SUCCESS! ✅")
        print("  ✅ Platform detection working")
        print("  ✅ Factory registration confirmed")
        print("  ✅ Handler creation functional")
        print("  ✅ URL processing operational")
        return True
    else:
        print(f"\n❌ {total_tests - tests_passed} tests failed")
        return False


if __name__ == "__main__":
    success = test_youtube_factory_registration()
    sys.exit(0 if success else 1) 