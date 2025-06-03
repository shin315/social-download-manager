#!/usr/bin/env python3
"""
Comprehensive Unit Tests for YouTube Handler

This module contains comprehensive unit tests for the YouTubeHandler
implementation, covering all aspects of the stub functionality.
"""

import sys
import asyncio
import unittest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from platforms.youtube.youtube_handler import YouTubeHandler
from platforms.base import (
    PlatformVideoInfo,
    VideoFormat,
    QualityLevel,
    DownloadResult,
    DownloadStatus,
    PlatformCapabilities,
    ContentType,
    PlatformType,
    PlatformContentError,
    PlatformFactory,
    create_handler_for_url,
    detect_platform,
    is_url_supported,
    get_supported_platforms
)


class TestYouTubeHandler(unittest.TestCase):
    """Test cases for YouTube Handler"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.handler = YouTubeHandler()
        self.valid_youtube_urls = [
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
        self.invalid_urls = [
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
    
    def test_initialization(self):
        """Test handler initialization"""
        handler = YouTubeHandler()
        self.assertEqual(handler.platform_type, PlatformType.YOUTUBE)
        self.assertIsNotNone(handler)
        
        # Test with platform type parameter
        handler2 = YouTubeHandler(platform_type=PlatformType.YOUTUBE)
        self.assertEqual(handler2.platform_type, PlatformType.YOUTUBE)
    
    def test_capabilities(self):
        """Test get_capabilities method"""
        capabilities = self.handler.get_capabilities()
        
        self.assertIsInstance(capabilities, PlatformCapabilities)
        self.assertTrue(capabilities.supports_video)
        self.assertTrue(capabilities.supports_audio)
        self.assertFalse(capabilities.requires_auth)
        self.assertTrue(capabilities.supports_quality_selection)
        self.assertTrue(capabilities.supports_thumbnails)
        self.assertTrue(capabilities.supports_metadata)
        self.assertFalse(capabilities.supports_playlists)  # Not implemented in stub
    
    def test_url_validation_valid_urls(self):
        """Test URL validation with valid YouTube URLs"""
        for url in self.valid_youtube_urls:
            with self.subTest(url=url):
                self.assertTrue(
                    self.handler.is_valid_url(url),
                    f"Should accept valid YouTube URL: {url}"
                )
    
    def test_url_validation_invalid_urls(self):
        """Test URL validation with invalid URLs"""
        for url in self.invalid_urls:
            with self.subTest(url=url):
                self.assertFalse(
                    self.handler.is_valid_url(url),
                    f"Should reject invalid URL: {url}"
                )
    
    def test_video_id_extraction(self):
        """Test video ID extraction"""
        test_cases = [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtube.com/watch?v=dQw4w9WgXcQ&t=42", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ?t=42", "dQw4w9WgXcQ"),
        ]
        
        for url, expected_id in test_cases:
            with self.subTest(url=url, expected=expected_id):
                extracted_id = self.handler.extract_video_id(url)
                self.assertEqual(
                    extracted_id, expected_id,
                    f"Should extract '{expected_id}' from {url}, got '{extracted_id}'"
                )
    
    def test_url_normalization(self):
        """Test URL normalization"""
        test_cases = [
            ("https://youtu.be/dQw4w9WgXcQ", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            ("https://youtube.com/embed/dQw4w9WgXcQ", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            ("https://youtube.com/watch?v=dQw4w9WgXcQ&t=42", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
        ]
        
        for url, expected in test_cases:
            with self.subTest(url=url, expected=expected):
                normalized = self.handler.normalize_url(url)
                self.assertEqual(
                    normalized, expected,
                    f"Should normalize '{url}' to '{expected}', got '{normalized}'"
                )
    
    def test_get_video_info_valid_url(self):
        """Test get_video_info with valid URL"""
        async def _async_test():
            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            video_info = await self.handler.get_video_info(url)
            
            self.assertIsInstance(video_info, PlatformVideoInfo)
            self.assertEqual(video_info.platform, PlatformType.YOUTUBE)
            self.assertEqual(video_info.platform_id, "dQw4w9WgXcQ")
            self.assertEqual(video_info.url, url)
            self.assertIn("Stub", video_info.title)
            self.assertGreater(len(video_info.formats), 0)
            self.assertEqual(video_info.content_type, ContentType.VIDEO)
            self.assertTrue(video_info.extra_data.get("stub_implementation"))
        
        asyncio.run(_async_test())
    
    def test_get_video_info_invalid_url(self):
        """Test get_video_info with invalid URL"""
        async def _async_test():
            invalid_url = "https://www.google.com"
            
            with self.assertRaises(PlatformContentError):
                await self.handler.get_video_info(invalid_url)
        
        asyncio.run(_async_test())
    
    def test_download_video_stub_behavior(self):
        """Test download_video stub behavior"""
        async def _async_test():
            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            output_path = Path("./downloads/test.mp4")
            
            result = await self.handler.download_video(url, output_path, quality=QualityLevel.HD)
            
            self.assertIsInstance(result, DownloadResult)
            self.assertFalse(result.success)
            self.assertIsNone(result.file_path)
            self.assertIn("not implemented", result.error_message.lower())
            self.assertIsInstance(result.video_info, PlatformVideoInfo)
        
        asyncio.run(_async_test())
    
    def test_platform_specific_info(self):
        """Test get_platform_specific_info"""
        info = self.handler.get_platform_specific_info()
        
        self.assertIsInstance(info, dict)
        self.assertEqual(info.get("platform"), "youtube")
        self.assertEqual(info.get("implementation_status"), "stub")
        self.assertIn("supported_features", info)
        self.assertIn("not_implemented", info)
        self.assertIn("future_features", info)
    
    def test_lifecycle_methods(self):
        """Test platform lifecycle methods"""
        async def _async_test():
            # These should execute without error
            await self.handler._initialize_platform()
            await self.handler._cleanup_platform()
        
        asyncio.run(_async_test())
    
    def test_video_formats_structure(self):
        """Test video formats structure"""
        async def _async_test():
            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            video_info = await self.handler.get_video_info(url)
            
            self.assertGreater(len(video_info.formats), 0)
            
            for fmt in video_info.formats:
                self.assertIsInstance(fmt, VideoFormat)
                self.assertIsNotNone(fmt.format_id)
                self.assertIn(fmt.quality, [QualityLevel.HD, QualityLevel.SD])
                self.assertEqual(fmt.ext, "mp4")
                self.assertIsNotNone(fmt.height)
                self.assertIsNotNone(fmt.width)
        
        asyncio.run(_async_test())


class TestYouTubeFactoryIntegration(unittest.TestCase):
    """Test YouTube Handler integration with platform factory"""
    
    def test_platform_detection(self):
        """Test platform detection for YouTube URLs"""
        test_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://youtube.com/embed/dQw4w9WgXcQ",
            "https://m.youtube.com/watch?v=dQw4w9WgXcQ"
        ]
        
        for url in test_urls:
            with self.subTest(url=url):
                detected = detect_platform(url)
                self.assertEqual(detected, PlatformType.YOUTUBE)
    
    def test_url_support(self):
        """Test URL support checking"""
        youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        non_youtube_url = "https://www.google.com"
        
        self.assertTrue(is_url_supported(youtube_url))
        self.assertFalse(is_url_supported(non_youtube_url))
    
    def test_supported_platforms_list(self):
        """Test that YouTube is in supported platforms"""
        supported = get_supported_platforms()
        self.assertIn(PlatformType.YOUTUBE, supported)
    
    def test_factory_handler_creation(self):
        """Test handler creation via factory"""
        factory = PlatformFactory()
        handler = factory.create_handler(PlatformType.YOUTUBE)
        
        self.assertIsInstance(handler, YouTubeHandler)
        self.assertEqual(handler.platform_type, PlatformType.YOUTUBE)
    
    def test_url_based_handler_creation(self):
        """Test handler creation from URL"""
        youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        handler = create_handler_for_url(youtube_url)
        
        self.assertIsInstance(handler, YouTubeHandler)
        self.assertEqual(handler.platform_type, PlatformType.YOUTUBE)
    
    def test_handler_functionality_integration(self):
        """Test handler functionality through factory"""
        youtube_url = "https://youtu.be/dQw4w9WgXcQ"
        handler = create_handler_for_url(youtube_url)
        
        # Test URL validation
        self.assertTrue(handler.is_valid_url(youtube_url))
        
        # Test capabilities
        capabilities = handler.get_capabilities()
        self.assertTrue(capabilities.supports_video)
    
    def test_platform_type_consistency(self):
        """Test platform type consistency"""
        test_url = "https://www.youtube.com/watch?v=test"
        
        handler = create_handler_for_url(test_url)
        detected_platform = detect_platform(test_url)
        
        self.assertEqual(handler.platform_type, detected_platform)
        self.assertEqual(detected_platform, PlatformType.YOUTUBE)


if __name__ == "__main__":
    unittest.main(verbosity=2) 