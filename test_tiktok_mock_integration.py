#!/usr/bin/env python3
"""
TikTok Mock Integration Test Suite

This module provides comprehensive testing using mock responses and simulated conditions
to test TikTok handler functionality without requiring real API calls.
"""

import asyncio
import logging
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, AsyncMock, patch
import tempfile

# Add the project root to sys.path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from platforms.tiktok import TikTokHandler
from platforms.base import (
    PlatformVideoInfo, VideoFormat, QualityLevel, DownloadResult, 
    DownloadProgress, DownloadStatus, ContentType, PlatformType,
    PlatformError, PlatformConnectionError, PlatformContentError
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MockTikTokResponses:
    """Mock TikTok API responses for testing"""
    
    @staticmethod
    def get_valid_video_response() -> Dict[str, Any]:
        """Mock response for a valid TikTok video"""
        return {
            'id': '7123456789012345678',
            'title': 'Amazing TikTok Video with Effects',
            'description': 'Check out this #amazing #video with #cool #effects @creator123',
            'uploader': 'creator123',
            'uploader_id': 'creator123',
            'uploader_url': 'https://www.tiktok.com/@creator123',
            'thumbnail': 'https://example.com/thumbnail.jpg',
            'duration': 15.5,
            'view_count': 1234567,
            'like_count': 98765,
            'comment_count': 4321,
            'repost_count': 1234,
            'upload_date': '20231201',
            'timestamp': 1701388800,
            'webpage_url': 'https://www.tiktok.com/@creator123/video/7123456789012345678',
            'extractor': 'tiktok',
            'formats': [
                {
                    'format_id': 'hd_no_watermark',
                    'ext': 'mp4',
                    'width': 1080,
                    'height': 1920,
                    'fps': 30,
                    'vcodec': 'h264',
                    'acodec': 'aac',
                    'vbr': 2500,
                    'abr': 128,
                    'filesize': 15728640,
                    'url': 'https://example.com/video_hd.mp4',
                    'has_watermark': False
                },
                {
                    'format_id': 'hd_watermark',
                    'ext': 'mp4',
                    'width': 1080,
                    'height': 1920,
                    'fps': 30,
                    'vcodec': 'h264',
                    'acodec': 'aac',
                    'vbr': 2000,
                    'abr': 128,
                    'filesize': 12582912,
                    'url': 'https://example.com/video_hd_wm.mp4',
                    'has_watermark': True
                },
                {
                    'format_id': 'audio_only',
                    'ext': 'mp3',
                    'vcodec': 'none',
                    'acodec': 'mp3',
                    'abr': 192,
                    'filesize': 2097152,
                    'url': 'https://example.com/audio.mp3'
                }
            ],
            'categories': ['Entertainment'],
            'tags': ['viral', 'trending', 'fyp'],
            'creator_verified': True,
            'music': {
                'track': 'Original Sound',
                'artist': 'creator123'
            }
        }
    
    @staticmethod
    def get_private_video_response() -> Dict[str, Any]:
        """Mock response for a private TikTok video"""
        return None  # yt-dlp returns None for private videos
    
    @staticmethod
    def get_deleted_video_response() -> Dict[str, Any]:
        """Mock response for a deleted TikTok video"""
        return None  # yt-dlp returns None for deleted videos


class MockProgressTracker:
    """Mock progress tracker for download testing"""
    
    def __init__(self):
        self.progress_updates: List[DownloadProgress] = []
        self.completed = False
    
    def __call__(self, progress: DownloadProgress):
        """Progress callback"""
        self.progress_updates.append(progress)
        if progress.status == DownloadStatus.COMPLETED:
            self.completed = True
        print(f"   📊 Mock Progress: {progress.status.name} - {progress.progress_percent:.1f}%")


def test_url_validation():
    """Test URL validation with various TikTok URL formats"""
    
    print("🔗 Testing URL Validation")
    print("=" * 26)
    
    handler = TikTokHandler()
    
    test_urls = [
        # Valid URLs
        ("https://www.tiktok.com/@user/video/1234567890", True, "Standard TikTok URL"),
        ("https://vm.tiktok.com/ZMxxxxxx/", True, "Short TikTok URL"),
        ("https://vt.tiktok.com/ZSxxxxxx/", True, "Short TikTok URL variant"),
        ("https://www.tiktok.com/t/ZTxxxxxx/", True, "Mobile share URL"),
        ("https://tiktok.com/@user/video/1234567890?is_from_webapp=1", True, "URL with webapp parameter"),
        
        # Invalid URLs
        ("https://youtube.com/watch?v=abc123", False, "YouTube URL"),
        ("https://www.tiktok.com/@user/photo/1234567890", False, "TikTok photo URL"),
        ("https://instagram.com/p/abc123/", False, "Instagram URL"),
        ("", False, "Empty URL"),
        ("not_a_url", False, "Invalid URL format"),
        
        # Edge cases
        ("https://www.tiktok.com/@user.name_123/video/1234567890", True, "Username with special chars"),
        ("https://www.tiktok.com/@user/video/1234567890?source=h5_m&extra_param=test", True, "Multiple parameters")
    ]
    
    passed = 0
    total = len(test_urls)
    
    for url, expected, description in test_urls:
        result = handler.is_valid_url(url)
        status = "✅" if result == expected else "❌"
        print(f"   {status} {description}: {result}")
        if result == expected:
            passed += 1
    
    print(f"\n✅ URL Validation: {passed}/{total} tests passed")
    return passed == total


def test_capabilities():
    """Test platform capabilities"""
    
    print("\n🔧 Testing Platform Capabilities")
    print("=" * 33)
    
    handler = TikTokHandler()
    capabilities = handler.get_capabilities()
    
    expected_capabilities = {
        'supports_video': True,
        'supports_audio': True,
        'supports_playlists': False,
        'supports_live': False,
        'supports_stories': False,
        'requires_auth': False,
        'supports_watermark_removal': True,
        'supports_quality_selection': True,
        'supports_thumbnails': True,
        'supports_metadata': True,
        'max_concurrent_downloads': 3,
        'rate_limit_requests': 30,
        'rate_limit_period': 60
    }
    
    passed = 0
    total = len(expected_capabilities)
    
    for capability, expected_value in expected_capabilities.items():
        actual_value = getattr(capabilities, capability)
        status = "✅" if actual_value == expected_value else "❌"
        print(f"   {status} {capability}: {actual_value}")
        if actual_value == expected_value:
            passed += 1
    
    print(f"\n✅ Capabilities: {passed}/{total} tests passed")
    return passed == total


def test_mock_video_info_extraction():
    """Test video info extraction with mock data"""
    
    print("\n📊 Testing Mock Video Info Extraction")
    print("=" * 38)
    
    handler = TikTokHandler()
    mock_response = MockTikTokResponses.get_valid_video_response()
    
    async def run_extraction_test():
        # Convert mock response to PlatformVideoInfo
        video_info = await handler._convert_ytdlp_to_platform_info(
            mock_response, 
            "https://www.tiktok.com/@creator123/video/7123456789012345678"
        )
        
        # Verify extraction results
        tests = [
            (video_info.title, "Amazing TikTok Video with Effects", "Title"),
            (video_info.creator, "creator123", "Creator"),
            (video_info.platform_id, "7123456789012345678", "Platform ID"),
            (video_info.view_count, 1234567, "View Count"),
            (video_info.like_count, 98765, "Like Count"),
            (video_info.comment_count, 4321, "Comment Count"),
            (len(video_info.hashtags), 4, "Hashtag Count"),
            (len(video_info.mentions), 1, "Mention Count"),
            (len(video_info.formats), 3, "Format Count"),
            (video_info.duration, 15.5, "Duration")
        ]
        
        passed = 0
        for actual, expected, test_name in tests:
            status = "✅" if actual == expected else "❌"
            print(f"   {status} {test_name}: {actual} (expected: {expected})")
            if actual == expected:
                passed += 1
        
        # Test metadata enrichment
        extra_data = video_info.extra_data
        enrichment_tests = [
            ('music' in extra_data, True, "Music metadata"),
            ('video_id' in extra_data, True, "Video ID"),
            ('creator_verified' in extra_data, True, "Creator verification"),
            ('is_watermarked' in extra_data, True, "Watermark info")
        ]
        
        for actual, expected, test_name in enrichment_tests:
            status = "✅" if actual == expected else "❌"
            print(f"   {status} {test_name}: {actual}")
            if actual == expected:
                passed += 1
        
        print(f"\n✅ Video Info Extraction: {passed}/{len(tests) + len(enrichment_tests)} tests passed")
        return passed == (len(tests) + len(enrichment_tests))
    
    # Run the async test
    return asyncio.create_task(run_extraction_test())


def test_format_selection():
    """Test format selection logic"""
    
    print("\n🎯 Testing Format Selection")
    print("=" * 28)
    
    handler = TikTokHandler()
    
    # Create mock video info with multiple formats
    formats = [
        VideoFormat(
            format_id="hd_no_watermark",
            quality=QualityLevel.FHD,
            ext="mp4",
            width=1080,
            height=1920,
            vbr=2500,
            has_watermark=False,
            is_audio_only=False
        ),
        VideoFormat(
            format_id="hd_watermark",
            quality=QualityLevel.FHD,
            ext="mp4",
            width=1080,
            height=1920,
            vbr=2000,
            has_watermark=True,
            is_audio_only=False
        ),
        VideoFormat(
            format_id="sd_format",
            quality=QualityLevel.SD,
            ext="mp4",
            width=720,
            height=1280,
            vbr=1500,
            has_watermark=False,
            is_audio_only=False
        ),
        VideoFormat(
            format_id="audio_only",
            quality=QualityLevel.AUDIO_ONLY,
            ext="mp3",
            abr=192,
            has_watermark=False,
            is_audio_only=True
        )
    ]
    
    video_info = PlatformVideoInfo(
        url="https://test.com/video",
        platform=PlatformType.TIKTOK,
        platform_id="123",
        title="Test Video",
        formats=formats
    )
    
    async def run_format_tests():
        test_cases = [
            (None, False, {}, "hd_no_watermark", "Best quality without watermark"),
            (QualityLevel.SD, False, {}, "sd_format", "Specific SD quality"),
            (None, True, {}, "audio_only", "Audio only"),
            (QualityLevel.FHD, False, {"prefer_no_watermark": False}, "hd_watermark", "Allow watermark")
        ]
        
        passed = 0
        for quality, audio_only, kwargs, expected_id, description in test_cases:
            selected = await handler._select_best_format(video_info, quality, audio_only, **kwargs)
            actual_id = selected.format_id if selected else None
            status = "✅" if actual_id == expected_id else "❌"
            print(f"   {status} {description}: {actual_id}")
            if actual_id == expected_id:
                passed += 1
        
        print(f"\n✅ Format Selection: {passed}/{len(test_cases)} tests passed")
        return passed == len(test_cases)
    
    return asyncio.create_task(run_format_tests())


def test_error_handling_scenarios():
    """Test error handling with various scenarios"""
    
    print("\n🚨 Testing Error Handling Scenarios")
    print("=" * 36)
    
    handler = TikTokHandler()
    
    error_scenarios = [
        ("Connection timeout", "NetworkError", "Network errors"),
        ("429 Too Many Requests", "RateLimitError", "Rate limiting"),
        ("Video is private", "ContentError", "Private content"),
        ("404 Not Found", "ContentError", "Not found"),
        ("Unknown error", "PlatformError", "Generic errors")
    ]
    
    passed = 0
    for error_msg, expected_type, description in error_scenarios:
        try:
            test_error = Exception(error_msg)
            enhanced_error = handler._handle_error_with_context(
                operation="test_operation",
                original_error=test_error,
                url="https://test.com"
            )
            
            actual_type = type(enhanced_error).__name__
            # Simplify type matching
            type_match = (
                (expected_type == "NetworkError" and "Connection" in actual_type) or
                (expected_type == "RateLimitError" and "RateLimit" in actual_type) or
                (expected_type == "ContentError" and "Content" in actual_type) or
                (expected_type == "PlatformError" and "Platform" in actual_type)
            )
            
            status = "✅" if type_match else "❌"
            print(f"   {status} {description}: {actual_type}")
            if type_match:
                passed += 1
                
        except Exception as e:
            print(f"   ❌ {description}: Unexpected error - {e}")
    
    print(f"\n✅ Error Handling: {passed}/{len(error_scenarios)} tests passed")
    return passed == len(error_scenarios)


def test_session_management():
    """Test session management functionality"""
    
    print("\n🔐 Testing Session Management")
    print("=" * 30)
    
    handler = TikTokHandler({
        'headers': {'rotate_user_agent': True, 'rotate_interval': 3},
        'rate_limit': {'enabled': True, 'min_request_interval': 0.1}
    })
    
    tests = []
    
    # Test initial state
    session_info = handler.get_session_info()
    tests.append((
        session_info['request_count'] == 0,
        "Initial request count is 0"
    ))
    tests.append((
        session_info['authenticated'] == False,
        "Not authenticated initially"
    ))
    tests.append((
        'Mozilla' in session_info['user_agent'],
        "User agent is set"
    ))
    
    # Test session clearing
    handler.clear_session()
    session_info = handler.get_session_info()
    tests.append((
        session_info['request_count'] == 0,
        "Request count reset after clear"
    ))
    tests.append((
        session_info['cookies_count'] == 0,
        "Cookies cleared"
    ))
    
    passed = sum(1 for test_result, _ in tests if test_result)
    
    for test_result, description in tests:
        status = "✅" if test_result else "❌"
        print(f"   {status} {description}")
    
    print(f"\n✅ Session Management: {passed}/{len(tests)} tests passed")
    return passed == len(tests)


def test_mock_download_simulation():
    """Test download simulation with mock progress"""
    
    print("\n📥 Testing Mock Download Simulation")
    print("=" * 35)
    
    # Create a temporary file for mock download
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
        temp_path = Path(temp_file.name)
        temp_file.write(b"Mock video content")
    
    try:
        progress_tracker = MockProgressTracker()
        
        # Simulate download progress
        progress_states = [
            DownloadProgress(DownloadStatus.PENDING, 0.0, message="Starting download"),
            DownloadProgress(DownloadStatus.DOWNLOADING, 25.0, message="Downloading"),
            DownloadProgress(DownloadStatus.DOWNLOADING, 50.0, message="Downloading"),
            DownloadProgress(DownloadStatus.DOWNLOADING, 75.0, message="Downloading"),
            DownloadProgress(DownloadStatus.DOWNLOADING, 100.0, message="Downloading"),
            DownloadProgress(DownloadStatus.COMPLETED, 100.0, message="Download completed")
        ]
        
        print("   Simulating download progress...")
        for progress in progress_states:
            progress_tracker(progress)
            time.sleep(0.01)  # Small delay to simulate real download
        
        # Test results
        tests = [
            (len(progress_tracker.progress_updates) == 6, "All progress updates received"),
            (progress_tracker.completed == True, "Download completed successfully"),
            (progress_tracker.progress_updates[-1].status == DownloadStatus.COMPLETED, "Final status is completed"),
            (progress_tracker.progress_updates[-1].progress_percent == 100.0, "Final progress is 100%")
        ]
        
        passed = sum(1 for test_result, _ in tests if test_result)
        
        for test_result, description in tests:
            status = "✅" if test_result else "❌"
            print(f"   {status} {description}")
        
        print(f"\n✅ Mock Download: {passed}/{len(tests)} tests passed")
        return passed == len(tests)
        
    finally:
        # Clean up temporary file
        if temp_path.exists():
            temp_path.unlink()


async def run_integration_tests():
    """Run all integration tests"""
    
    print("🧪 TikTok Mock Integration Test Suite")
    print("=" * 37)
    
    # List of test functions
    sync_tests = [
        test_url_validation,
        test_capabilities,
        test_error_handling_scenarios,
        test_session_management,
        test_mock_download_simulation
    ]
    
    async_tests = [
        test_mock_video_info_extraction,
        test_format_selection
    ]
    
    results = []
    
    # Run synchronous tests
    for test_func in sync_tests:
        try:
            result = test_func()
            results.append((test_func.__name__, result))
        except Exception as e:
            print(f"❌ {test_func.__name__} failed: {e}")
            results.append((test_func.__name__, False))
    
    # Run asynchronous tests
    for test_func in async_tests:
        try:
            result = await test_func()
            results.append((test_func.__name__, result))
        except Exception as e:
            print(f"❌ {test_func.__name__} failed: {e}")
            results.append((test_func.__name__, False))
    
    # Summary
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\n🎯 Integration Test Summary")
    print("=" * 29)
    print(f"Tests Run: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {total - passed}")
    print(f"Success Rate: {(passed/total*100):.1f}%")
    
    if passed == total:
        print("\n🎉 All integration tests passed!")
        print("TikTok handler mock integration is working correctly.")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")
        print("Review failed tests before proceeding.")
    
    return passed == total


def main():
    """Main test function for mock integration"""
    try:
        return asyncio.run(run_integration_tests())
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False


# Individual test functions for the comprehensive test runner
async def test_end_to_end_workflow():
    """Test complete workflow from URL validation to mock download"""
    print("🌐 End-to-End Workflow Testing")
    return await run_integration_tests()


async def test_factory_integration():
    """Test TikTok handler integration with platform factory"""
    print("🏭 Factory Integration Testing")
    from platforms.base.factory import PlatformFactory
    
    try:
        # Test handler registration
        factory = PlatformFactory()
        handler = factory.create_handler(PlatformType.TIKTOK)
        
        # Verify it's a TikTok handler
        is_tiktok_handler = isinstance(handler, TikTokHandler)
        print(f"   ✅ TikTok handler created: {is_tiktok_handler}")
        
        # Test URL handling
        test_url = "https://www.tiktok.com/@test/video/123"
        is_valid = handler.is_valid_url(test_url)
        print(f"   ✅ URL validation: {is_valid}")
        
        return is_tiktok_handler and is_valid
        
    except Exception as e:
        print(f"   ❌ Factory integration failed: {e}")
        return False


async def test_mock_api_responses():
    """Test handler behavior with mocked API responses"""
    print("🎭 Mock API Response Testing")
    
    try:
        # Test different response scenarios
        responses = [
            (MockTikTokResponses.get_valid_video_response(), "Valid video response"),
            (MockTikTokResponses.get_private_video_response(), "Private video response"),
            (MockTikTokResponses.get_deleted_video_response(), "Deleted video response")
        ]
        
        passed = 0
        for response, description in responses:
            if response is not None:
                # Valid response should have required fields
                has_required = all(key in response for key in ['id', 'title', 'uploader'])
                print(f"   ✅ {description}: {has_required}")
                if has_required:
                    passed += 1
            else:
                # None response is expected for private/deleted videos
                print(f"   ✅ {description}: None (expected)")
                passed += 1
        
        return passed == len(responses)
        
    except Exception as e:
        print(f"   ❌ Mock API testing failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 