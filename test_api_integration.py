#!/usr/bin/env python3
"""
Task 11.2: TikTokHandler API Integration Testing
Test API authentication, data retrieval, and error handling
"""

import sys
import asyncio
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from platforms.tiktok.tiktok_handler import TikTokHandler
from platforms.base.enums import PlatformType

async def test_handler_initialization():
    """Test TikTokHandler initialization and capabilities"""
    print("🔧 Testing TikTokHandler Initialization")
    print("=" * 50)
    
    try:
        # Initialize handler
        handler = TikTokHandler()
        
        # Test basic properties
        print(f"✅ Handler initialized successfully")
        print(f"   Platform Type: {handler.platform_type}")
        
        # Test capabilities
        capabilities = handler.get_capabilities()
        print(f"✅ Platform capabilities:")
        print(f"   Supports Video: {capabilities.supports_video}")
        print(f"   Supports Audio: {capabilities.supports_audio}")
        print(f"   Requires Auth: {capabilities.requires_auth}")
        print(f"   Max Concurrent Downloads: {capabilities.max_concurrent_downloads}")
        print(f"   Rate Limit: {capabilities.rate_limit_requests}/{capabilities.rate_limit_period}s")
        
        # Test URL patterns
        print(f"✅ URL patterns configured: {len(handler._url_patterns)} patterns")
        
        return True, handler
        
    except Exception as e:
        print(f"❌ Handler initialization failed: {e}")
        return False, None

async def test_video_info_extraction(handler):
    """Test video information extraction with real URLs"""
    print("\n📡 Testing Video Info Extraction")
    print("=" * 50)
    
    test_urls = [
        ("https://www.tiktok.com/@dangbeo9/video/7512675061443071250", "Confirmed working URL"),
    ]
    
    successful_extractions = 0
    total_tests = len(test_urls)
    
    for url, description in test_urls:
        print(f"\n🎯 Testing: {description}")
        print(f"   URL: {url}")
        
        try:
            start_time = time.time()
            
            # Extract video info
            video_info = await handler.get_video_info(url)
            
            extraction_time = time.time() - start_time
            
            print(f"✅ Extraction successful in {extraction_time:.2f}s")
            print(f"   Title: {video_info.title}")
            print(f"   Creator: {video_info.creator}")
            print(f"   Duration: {video_info.duration}s")
            print(f"   View Count: {video_info.view_count:,}" if video_info.view_count else "   View Count: N/A")
            print(f"   Like Count: {video_info.like_count:,}" if video_info.like_count else "   Like Count: N/A")
            print(f"   Platform: {video_info.platform}")
            
            # Check upload date with different possible attribute names
            upload_date = getattr(video_info, 'upload_date', None) or getattr(video_info, 'timestamp', None)
            if upload_date:
                print(f"   Upload Date: {upload_date}")
            else:
                print("   Upload Date: N/A")
            
            # Test format availability
            if hasattr(video_info, 'formats') and video_info.formats:
                print(f"   Available Formats: {len(video_info.formats)}")
                
                # Show some format details
                for i, fmt in enumerate(video_info.formats[:3]):  # Show first 3 formats
                    quality = getattr(fmt, 'quality', 'Unknown')
                    format_id = getattr(fmt, 'format_id', 'Unknown')
                    ext = getattr(fmt, 'ext', 'Unknown')
                    print(f"     Format {i+1}: {quality} ({format_id}.{ext})")
                
                if len(video_info.formats) > 3:
                    print(f"     ... and {len(video_info.formats) - 3} more formats")
            
            # Test metadata extraction
            if hasattr(video_info, 'extra_data') and video_info.extra_data:
                print(f"   Extra Metadata Keys: {list(video_info.extra_data.keys())[:5]}")
                
                # Check for TikTok-specific data
                if 'music' in video_info.extra_data:
                    music = video_info.extra_data['music']
                    if music:
                        print(f"   Music Info: {music}")
                
                if 'hashtags' in video_info.extra_data:
                    hashtags = video_info.extra_data['hashtags'][:3]  # First 3
                    if hashtags:
                        print(f"   Hashtags: {hashtags}")
            
            successful_extractions += 1
            
        except Exception as e:
            print(f"❌ Extraction failed: {e}")
            print(f"   Error type: {type(e).__name__}")
            
            # Categorize error for better understanding
            error_msg = str(e).lower()
            if 'network' in error_msg or 'connection' in error_msg:
                print("   Category: Network/Connection issue")
            elif 'private' in error_msg:
                print("   Category: Private/Restricted content")
            elif 'not available' in error_msg:
                print("   Category: Content not available")
            elif 'rate' in error_msg:
                print("   Category: Rate limiting")
            else:
                print("   Category: Unknown/Other")
    
    print(f"\n📊 Video Info Extraction: {successful_extractions}/{total_tests} successful")
    return successful_extractions == total_tests

async def test_error_handling(handler):
    """Test error handling with various problematic URLs"""
    print("\n⚠️  Testing Error Handling")
    print("=" * 50)
    
    error_test_cases = [
        ("https://www.tiktok.com/@nonexistentuser123456/video/0000000000000000000", "Non-existent video"),
        ("https://www.tiktok.com/@user/photo/1234567890", "Photo URL (unsupported)"),
        ("https://www.tiktok.com/@user/video/", "Malformed URL (missing ID)"),
        ("", "Empty URL"),
        ("https://youtube.com/watch?v=invalid", "Wrong platform"),
    ]
    
    handled_errors = 0
    total_error_tests = len(error_test_cases)
    
    for url, description in error_test_cases:
        print(f"\n🎯 Testing: {description}")
        print(f"   URL: {url}")
        
        try:
            video_info = await handler.get_video_info(url)
            print(f"⚠️  Unexpected success - should have failed")
            
        except Exception as e:
            print(f"✅ Expected error caught: {type(e).__name__}")
            print(f"   Message: {str(e)}")
            handled_errors += 1
    
    print(f"\n📊 Error Handling: {handled_errors}/{total_error_tests} errors properly handled")
    return handled_errors == total_error_tests

async def test_authentication_config(handler):
    """Test authentication configuration"""
    print("\n🔐 Testing Authentication Configuration")
    print("=" * 50)
    
    # Check if handler has auth info
    has_auth = hasattr(handler, '_auth_info') and handler._auth_info is not None
    print(f"✅ Authentication Info Present: {has_auth}")
    
    # Check if authentication is required
    capabilities = handler.get_capabilities()
    auth_required = capabilities.requires_auth
    print(f"✅ Authentication Required: {auth_required}")
    
    if not auth_required:
        print("✅ TikTok handler works without authentication (using yt-dlp)")
        print("   This is expected for public content extraction")
    else:
        print("⚠️  Authentication is required but may not be configured")
    
    return True

async def main():
    """Run all TikTokHandler API integration tests"""
    print("🧪 Task 11.2: TikTokHandler API Integration Testing")
    print("=" * 70)
    print()
    
    # Track overall results
    test_results = []
    
    # Test 1: Handler initialization
    init_success, handler = await test_handler_initialization()
    test_results.append(("Handler Initialization", init_success))
    
    if not init_success:
        print("\n❌ Cannot proceed without handler initialization")
        return False
    
    # Test 2: Authentication configuration
    auth_success = await test_authentication_config(handler)
    test_results.append(("Authentication Configuration", auth_success))
    
    # Test 3: Video info extraction
    extraction_success = await test_video_info_extraction(handler)
    test_results.append(("Video Info Extraction", extraction_success))
    
    # Test 4: Error handling
    error_handling_success = await test_error_handling(handler)
    test_results.append(("Error Handling", error_handling_success))
    
    print("\n" + "="*70)
    print("📋 FINAL RESULTS")
    print("=" * 70)
    
    all_passed = True
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if not result:
            all_passed = False
    
    print("\n" + "="*70)
    if all_passed:
        print("🎉 ALL API INTEGRATION TESTS PASSED!")
        print("   TikTokHandler is ready for production use")
    else:
        print("⚠️  Some API integration tests failed")
        print("   Review the specific test failures above")
    
    print("="*70)
    return all_passed

if __name__ == "__main__":
    asyncio.run(main()) 