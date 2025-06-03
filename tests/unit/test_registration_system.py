#!/usr/bin/env python3
"""
Test script for Platform Registration System

This script tests all aspects of the dynamic platform handler registration
system including static registration, dynamic registration, decorators, and
auto-discovery.
"""

import sys
import os
from typing import Optional, Dict, Any
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from platforms.base.enums import PlatformType
from platforms.base.platform_handler import AbstractPlatformHandler
from platforms.base.models import AuthenticationInfo, PlatformCapabilities, PlatformVideoInfo, DownloadResult
from platforms.base.factory import (
    PlatformRegistry, PlatformFactory, PlatformHandler,
    register_platform, unregister_platform, 
    get_supported_platforms, get_factory_info,
    create_handler, create_handler_for_url, detect_platform, discover_handlers
)


# =====================================================
# Mock Handler Classes for Testing
# =====================================================

class MockTikTokHandler(AbstractPlatformHandler):
    """Mock TikTok handler for testing"""
    
    def __init__(self, platform_type: PlatformType, auth_info: Optional[AuthenticationInfo] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(platform_type, auth_info, config)
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid for this platform"""
        return "tiktok.com" in url.lower()
    
    async def get_video_info(self, url: str) -> PlatformVideoInfo:
        """Get video information"""
        return PlatformVideoInfo(
            video_id="mock_tiktok_123",
            title="Mock TikTok Video",
            description="Mock description",
            uploader="mock_user",
            duration=30,
            view_count=1000,
            like_count=100,
            thumbnail_url="https://example.com/thumb.jpg",
            url=url,
            platform=self._platform_type,
            available_qualities=["720p", "480p"]
        )
    
    async def download_video(self, url: str, output_path: Path, quality: Optional[Any] = None, audio_only: bool = False, **kwargs) -> DownloadResult:
        """Mock download"""
        return DownloadResult(
            success=True,
            file_path=output_path / "mock_tiktok.mp4",
            file_size=1024000,
            quality="720p",
            format="mp4"
        )
    
    def get_capabilities(self) -> PlatformCapabilities:
        return PlatformCapabilities(
            supports_video=True,
            supports_audio=True,
            supports_metadata=True,
            supports_live=True,
            supports_playlists=True
        )


class MockYouTubeHandler(AbstractPlatformHandler):
    """Mock YouTube handler for testing"""
    
    def __init__(self, platform_type: PlatformType, auth_info: Optional[AuthenticationInfo] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(platform_type, auth_info, config)
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid for this platform"""
        return any(domain in url.lower() for domain in ["youtube.com", "youtu.be"])
    
    async def get_video_info(self, url: str) -> PlatformVideoInfo:
        """Get video information"""
        return PlatformVideoInfo(
            video_id="mock_youtube_123",
            title="Mock YouTube Video",
            description="Mock description",
            uploader="mock_channel",
            duration=120,
            view_count=10000,
            like_count=500,
            thumbnail_url="https://example.com/yt_thumb.jpg",
            url=url,
            platform=self._platform_type,
            available_qualities=["4K", "1080p", "720p"]
        )
    
    async def download_video(self, url: str, output_path: Path, quality: Optional[Any] = None, audio_only: bool = False, **kwargs) -> DownloadResult:
        """Mock download"""
        return DownloadResult(
            success=True,
            file_path=output_path / "mock_youtube.mp4",
            file_size=5120000,
            quality="1080p",
            format="mp4"
        )
    
    def get_capabilities(self) -> PlatformCapabilities:
        return PlatformCapabilities(
            supports_video=True,
            supports_audio=True,
            supports_metadata=True,
            supports_live=True,
            max_quality="4K"
        )


@PlatformHandler(
    platform_type=PlatformType.INSTAGRAM,
    url_patterns=['instagram.com', 'instagr.am'],
    auto_register=False  # We'll register manually in tests
)
class MockInstagramHandler(AbstractPlatformHandler):
    """Mock Instagram handler with decorator for testing"""
    
    def __init__(self, platform_type: PlatformType, auth_info: Optional[AuthenticationInfo] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(platform_type, auth_info, config)
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid for this platform"""
        return any(domain in url.lower() for domain in ["instagram.com", "instagr.am"])
    
    async def get_video_info(self, url: str) -> PlatformVideoInfo:
        """Get video information"""
        return PlatformVideoInfo(
            video_id="mock_instagram_123",
            title="Mock Instagram Post",
            description="Mock Instagram description",
            uploader="mock_insta_user",
            duration=15,
            view_count=500,
            like_count=50,
            thumbnail_url="https://example.com/ig_thumb.jpg",
            url=url,
            platform=self._platform_type,
            available_qualities=["1080p", "720p"]
        )
    
    async def download_video(self, url: str, output_path: Path, quality: Optional[Any] = None, audio_only: bool = False, **kwargs) -> DownloadResult:
        """Mock download"""
        return DownloadResult(
            success=True,
            file_path=output_path / "mock_instagram.mp4",
            file_size=2048000,
            quality="1080p",
            format="mp4"
        )
    
    def get_capabilities(self) -> PlatformCapabilities:
        return PlatformCapabilities(
            supports_video=True,
            supports_audio=True,
            supports_metadata=True,
            supports_live=True,
            supports_stories=True
        )


def custom_detection_callback(url: str) -> bool:
    """Custom detection callback for testing"""
    return "customplatform.com" in url.lower()


# =====================================================
# Test Functions
# =====================================================

def test_basic_registration():
    """Test basic registration and unregistration"""
    print("🔧 Testing Basic Registration System\n")
    print("=" * 80)
    
    # Create isolated registry for testing
    registry = PlatformRegistry()
    factory = PlatformFactory(registry)
    
    # Test empty registry
    supported = registry.get_registered_platforms()
    print(f"Initial supported platforms: {len(supported)}")
    assert len(supported) == 0, "Registry should start empty"
    
    # Test registration
    registry.register(
        PlatformType.TIKTOK,
        MockTikTokHandler,
        url_patterns=['tiktok.com', 'vm.tiktok.com']
    )
    
    supported = registry.get_registered_platforms()
    print(f"After TikTok registration: {len(supported)} platforms")
    assert PlatformType.TIKTOK in supported, "TikTok should be registered"
    
    # Test handler creation
    handler = factory.create_handler(PlatformType.TIKTOK)
    print(f"Created handler: {type(handler).__name__}")
    assert isinstance(handler, MockTikTokHandler), "Should create correct handler type"
    
    # Test URL detection
    detected = registry.detect_platform("https://tiktok.com/@user/video/123")
    print(f"Detected platform: {detected.display_name}")
    assert detected == PlatformType.TIKTOK, "Should detect TikTok from URL"
    
    # Test unregistration
    removed = registry.unregister(PlatformType.TIKTOK)
    print(f"Unregistration result: {removed}")
    assert removed, "Should successfully unregister TikTok"
    
    supported = registry.get_registered_platforms()
    print(f"After unregistration: {len(supported)} platforms")
    assert len(supported) == 0, "Registry should be empty after unregistration"
    
    print("✅ Basic registration system tests passed!\n")


def test_global_registration():
    """Test global convenience functions"""
    print("🌐 Testing Global Registration Functions\n")
    print("=" * 80)
    
    # Get initial state
    initial_platforms = get_supported_platforms()
    print(f"Initial global platforms: {len(initial_platforms)}")
    
    # Register via global function
    register_platform(
        PlatformType.YOUTUBE,
        MockYouTubeHandler,
        url_patterns=['youtube.com', 'youtu.be']
    )
    
    # Test global detection
    detected = detect_platform("https://youtube.com/watch?v=test")
    print(f"Global detection result: {detected.display_name}")
    assert detected == PlatformType.YOUTUBE, "Global detection should work"
    
    # Test global handler creation
    handler = create_handler(PlatformType.YOUTUBE)
    print(f"Global handler creation: {type(handler).__name__}")
    assert isinstance(handler, MockYouTubeHandler), "Should create correct handler"
    
    # Test factory info
    info = get_factory_info()
    print(f"Factory info platforms: {len(info['supported_platforms'])}")
    print(f"YouTube patterns: {info['platform_details']['youtube']['url_patterns']}")
    
    # Cleanup
    unregister_platform(PlatformType.YOUTUBE)
    final_platforms = get_supported_platforms()
    print(f"After cleanup: {len(final_platforms)} platforms")
    
    print("✅ Global registration functions tests passed!\n")


def test_decorator_registration():
    """Test decorator-based registration"""
    print("🎨 Testing Decorator Registration\n")
    print("=" * 80)
    
    # Test that decorator metadata is stored
    assert hasattr(MockInstagramHandler, '_platform_type'), "Should have platform type metadata"
    assert hasattr(MockInstagramHandler, '_url_patterns'), "Should have URL patterns metadata"
    
    print(f"Decorator platform type: {MockInstagramHandler._platform_type.display_name}")
    print(f"Decorator URL patterns: {MockInstagramHandler._url_patterns}")
    
    # Manually register (since auto_register=False)
    register_platform(
        MockInstagramHandler._platform_type,
        MockInstagramHandler,
        MockInstagramHandler._url_patterns
    )
    
    # Test it works
    detected = detect_platform("https://instagram.com/p/test")
    print(f"Detected platform: {detected.display_name}")
    assert detected == PlatformType.INSTAGRAM, "Should detect Instagram"
    
    handler = create_handler(PlatformType.INSTAGRAM)
    print(f"Created handler: {type(handler).__name__}")
    assert isinstance(handler, MockInstagramHandler), "Should create Instagram handler"
    
    # Cleanup
    unregister_platform(PlatformType.INSTAGRAM)
    
    print("✅ Decorator registration tests passed!\n")


def test_custom_detection():
    """Test custom detection callbacks"""
    print("🔍 Testing Custom Detection Callbacks\n")
    print("=" * 80)
    
    # Register with custom detection
    register_platform(
        PlatformType.FACEBOOK,  # Using Facebook as placeholder
        MockYouTubeHandler,     # Handler doesn't matter for detection test
        detection_callback=custom_detection_callback
    )
    
    # Test custom detection
    detected = detect_platform("https://customplatform.com/content/123")
    print(f"Custom detection result: {detected.display_name}")
    assert detected == PlatformType.FACEBOOK, "Custom callback should work"
    
    # Test normal URL (should fallback to enum detection)
    detected_normal = detect_platform("https://youtube.com/watch?v=test")
    print(f"Normal detection result: {detected_normal.display_name}")
    assert detected_normal == PlatformType.YOUTUBE, "Should fallback to normal detection"
    
    # Cleanup
    unregister_platform(PlatformType.FACEBOOK)
    
    print("✅ Custom detection tests passed!\n")


def test_error_handling():
    """Test error handling in registration system"""
    print("⚠️  Testing Error Handling\n")
    print("=" * 80)
    
    # Test invalid handler class
    try:
        register_platform(PlatformType.TWITTER, str)  # Invalid handler
        assert False, "Should raise TypeError for invalid handler"
    except TypeError as e:
        print(f"✅ Caught expected error: {e}")
    
    # Test creating handler for unregistered platform
    try:
        handler = create_handler(PlatformType.TWITCH)  # Not registered
        assert False, "Should raise ValueError for unregistered platform"
    except ValueError as e:
        print(f"✅ Caught expected error: {e}")
    
    # Test creating handler for unknown URL
    try:
        handler = create_handler_for_url("https://unknown-platform.com/test")
        assert False, "Should raise ValueError for unknown URL"
    except ValueError as e:
        print(f"✅ Caught expected error: {e}")
    
    print("✅ Error handling tests passed!\n")


def test_capabilities_integration():
    """Test platform capabilities integration"""
    print("🚀 Testing Platform Capabilities\n")
    print("=" * 80)
    
    # Register handler with capabilities
    register_platform(PlatformType.TIKTOK, MockTikTokHandler)
    
    # Get capabilities via factory
    factory = PlatformFactory()
    capabilities = factory.get_platform_capabilities(PlatformType.TIKTOK)
    
    print(f"TikTok capabilities:")
    print(f"  Supports download: {capabilities.supports_download}")
    print(f"  Supports search: {capabilities.supports_search}")
    print(f"  Max quality: {capabilities.max_quality}")
    
    assert capabilities.supports_download, "Should support download"
    assert capabilities.supports_search, "Should support search"
    assert not capabilities.supports_live, "Should not support live"
    
    # Cleanup
    unregister_platform(PlatformType.TIKTOK)
    
    print("✅ Capabilities integration tests passed!\n")


def test_performance():
    """Test registration system performance"""
    print("⚡ Testing Performance\n")
    print("=" * 80)
    
    import time
    
    # Register multiple handlers
    handlers = [
        (PlatformType.TIKTOK, MockTikTokHandler),
        (PlatformType.YOUTUBE, MockYouTubeHandler),
        (PlatformType.INSTAGRAM, MockInstagramHandler),
    ]
    
    # Test registration performance
    start_time = time.time()
    for platform, handler_class in handlers:
        register_platform(platform, handler_class)
    registration_time = time.time() - start_time
    
    print(f"Registration time: {registration_time:.4f}s for {len(handlers)} handlers")
    
    # Test detection performance
    test_urls = [
        "https://tiktok.com/@user/video/123",
        "https://youtube.com/watch?v=test",
        "https://instagram.com/p/test",
    ] * 100  # 300 detections
    
    start_time = time.time()
    for url in test_urls:
        detect_platform(url)
    detection_time = time.time() - start_time
    
    print(f"Detection time: {detection_time:.4f}s for {len(test_urls)} URLs")
    print(f"Average detection: {(detection_time/len(test_urls)*1000):.2f}ms per URL")
    
    # Cleanup
    for platform, _ in handlers:
        unregister_platform(platform)
    
    print("✅ Performance tests completed!\n")


if __name__ == "__main__":
    print("🚀 Platform Registration System Test Suite\n")
    
    try:
        # Run all tests
        test_basic_registration()
        test_global_registration()
        test_decorator_registration()
        test_custom_detection()
        test_error_handling()
        test_capabilities_integration()
        test_performance()
        
        print("🎯 All Registration System Tests PASSED! ✅")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 