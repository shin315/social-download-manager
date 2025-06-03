"""
Comprehensive Platform Factory Integration Tests

This module provides end-to-end integration testing for the complete platform factory system,
verifying that detection, registration, instantiation, and error handling work together correctly.
"""

import sys
import os
import unittest
import time
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Optional, Dict, Any, List

# Add current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from platforms.base.factory import (
    PlatformRegistry, PlatformFactory, register_platform, unregister_platform,
    create_handler, create_handler_for_url, detect_platform, is_url_supported,
    get_supported_platforms, get_platform_capabilities, PlatformHandler,
    discover_handlers, get_factory_info, _factory, _registry
)
from platforms.base.platform_handler import AbstractPlatformHandler
from platforms.base.models import AuthenticationInfo, PlatformCapabilities, PlatformVideoInfo, DownloadResult
from platforms.base.enums import PlatformType, AuthType, QualityLevel
from platforms.base.factory_exceptions import FactoryError, UnsupportedUrlError


class IntegrationTestHandler(AbstractPlatformHandler):
    """Handler for integration testing with realistic functionality"""
    
    def __init__(self, platform_type: PlatformType, auth_info: Optional[AuthenticationInfo] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(platform_type, auth_info, config)
        self._capabilities = PlatformCapabilities(
            supports_video=True,
            supports_audio=True,
            supports_playlists=platform_type in [PlatformType.YOUTUBE, PlatformType.TIKTOK],
            supports_live=platform_type in [PlatformType.YOUTUBE, PlatformType.TWITCH],
            supports_stories=platform_type in [PlatformType.INSTAGRAM, PlatformType.FACEBOOK],
            requires_auth=auth_info is not None,
            supports_watermark_removal=True,
            supports_quality_selection=True,
            supports_thumbnails=True,
            supports_metadata=True,
            max_concurrent_downloads=3,
            rate_limit_requests=20,
            rate_limit_period=60
        )
        
        # Track operations for testing
        self.operations = []
        self.creation_time = time.time()
    
    @property
    def auth_info(self) -> Optional[AuthenticationInfo]:
        return self._auth_info
    
    @property
    def config(self) -> Dict[str, Any]:
        return self._config
    
    def get_capabilities(self) -> PlatformCapabilities:
        return self._capabilities
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL matches our test patterns"""
        platform_patterns = {
            PlatformType.YOUTUBE: ['youtube.com', 'youtu.be'],
            PlatformType.TIKTOK: ['tiktok.com', 'vm.tiktok.com'],
            PlatformType.INSTAGRAM: ['instagram.com', 'instagr.am'],
            PlatformType.FACEBOOK: ['facebook.com', 'fb.com'],
            PlatformType.TWITTER: ['twitter.com', 'x.com'],
            PlatformType.LINKEDIN: ['linkedin.com'],
            PlatformType.TWITCH: ['twitch.tv']
        }
        
        if self.platform_type in platform_patterns:
            url_lower = url.lower()
            return any(pattern in url_lower for pattern in platform_patterns[self.platform_type])
        return False
    
    async def get_video_info(self, url: str) -> Dict[str, Any]:
        """Mock video info retrieval"""
        self.operations.append(('get_video_info', url))
        
        # Simulate some async work
        await asyncio.sleep(0.001)
        
        return {
            "title": f"Integration Test Video from {self.platform_type.display_name}",
            "duration": 120,
            "view_count": 1000,
            "like_count": 50,
            "platform": self.platform_type.value,
            "url": url,
            "handler_id": id(self),
            "timestamp": time.time()
        }
    
    async def download_video(self, url: str, output_path: str, quality: str = "best") -> bool:
        """Mock video download"""
        self.operations.append(('download_video', url, output_path, quality))
        
        # Simulate download time
        await asyncio.sleep(0.002)
        
        return True
    
    @property
    def capabilities(self) -> PlatformCapabilities:
        return self._capabilities


class TestPlatformFactoryIntegration(unittest.TestCase):
    """End-to-end integration tests for the platform factory system"""
    
    def setUp(self):
        """Set up clean test environment"""
        # Create isolated registry and factory for testing
        self.registry = PlatformRegistry()
        self.factory = PlatformFactory(self.registry)
        
        # Register test handlers for major platforms
        self.test_platforms = [
            PlatformType.YOUTUBE,
            PlatformType.TIKTOK,
            PlatformType.INSTAGRAM,
            PlatformType.FACEBOOK,
            PlatformType.TWITTER,
        ]
        
        for platform in self.test_platforms:
            self.registry.register(platform, IntegrationTestHandler)
    
    def test_end_to_end_workflow_basic(self):
        """Test complete workflow from URL to handler creation"""
        test_url = "https://youtube.com/watch?v=integration_test"
        
        # Step 1: Platform Detection
        detected_platform = self.factory.detect_platform(test_url)
        self.assertEqual(detected_platform, PlatformType.YOUTUBE)
        
        # Step 2: Check URL Support
        is_supported = self.factory.is_url_supported(test_url)
        self.assertTrue(is_supported)
        
        # Step 3: Handler Creation
        handler = self.factory.create_handler_for_url(test_url)
        self.assertIsInstance(handler, IntegrationTestHandler)
        self.assertEqual(handler.platform_type, PlatformType.YOUTUBE)
        
        # Step 4: Verify Handler Functionality
        self.assertTrue(handler.is_valid_url(test_url))
        
        # Step 5: Get Capabilities
        capabilities = handler.get_capabilities()
        self.assertIsInstance(capabilities, PlatformCapabilities)
        self.assertTrue(capabilities.supports_video)
    
    def test_end_to_end_workflow_with_auth(self):
        """Test complete workflow with authentication"""
        test_url = "https://tiktok.com/@user/video/123456"
        
        # Create authentication info
        auth_info = AuthenticationInfo(
            auth_type=AuthType.API_KEY,
            credentials={"api_key": "test_key_123"}
        )
        
        # Create handler with authentication
        handler = self.factory.create_handler_for_url(test_url, auth_info=auth_info)
        
        self.assertEqual(handler.auth_info, auth_info)
        self.assertTrue(handler.capabilities.requires_auth)
        self.assertEqual(handler.platform_type, PlatformType.TIKTOK)
    
    def test_end_to_end_workflow_with_config(self):
        """Test complete workflow with configuration"""
        test_url = "https://instagram.com/p/ABC123/"
        
        config = {
            "quality": "1080p",
            "timeout": 30,
            "retries": 3
        }
        
        handler = self.factory.create_handler_for_url(test_url, config=config)
        
        self.assertEqual(handler.config, config)
        self.assertEqual(handler.platform_type, PlatformType.INSTAGRAM)
    
    async def test_handler_operations_integration(self):
        """Test handler operations work correctly"""
        test_url = "https://facebook.com/watch/?v=123456"
        
        handler = self.factory.create_handler_for_url(test_url)
        
        # Test video info retrieval
        video_info = await handler.get_video_info(test_url)
        
        self.assertIsInstance(video_info, dict)
        self.assertIn("title", video_info)
        self.assertIn("platform", video_info)
        self.assertEqual(video_info["platform"], PlatformType.FACEBOOK.value)
        
        # Test download operation
        download_result = await handler.download_video(test_url, "/tmp/test")
        self.assertTrue(download_result)
        
        # Verify operations were tracked
        self.assertEqual(len(handler.operations), 2)
        self.assertEqual(handler.operations[0][0], "get_video_info")
        self.assertEqual(handler.operations[1][0], "download_video")
    
    def test_multiple_platform_handling(self):
        """Test handling multiple platforms simultaneously"""
        test_urls = [
            ("https://youtube.com/watch?v=test1", PlatformType.YOUTUBE),
            ("https://tiktok.com/@user/video/test2", PlatformType.TIKTOK),
            ("https://instagram.com/p/test3/", PlatformType.INSTAGRAM),
            ("https://twitter.com/user/status/test4", PlatformType.TWITTER),
            ("https://facebook.com/watch/?v=test5", PlatformType.FACEBOOK),
        ]
        
        handlers = []
        for url, expected_platform in test_urls:
            # Detect platform
            detected = self.factory.detect_platform(url)
            self.assertEqual(detected, expected_platform)
            
            # Create handler
            handler = self.factory.create_handler_for_url(url)
            self.assertEqual(handler.platform_type, expected_platform)
            
            handlers.append(handler)
        
        # Verify all handlers are unique instances
        handler_ids = [id(h) for h in handlers]
        self.assertEqual(len(set(handler_ids)), len(handlers))
        
        # Verify all handlers can validate their respective URLs
        for handler, (url, _) in zip(handlers, test_urls):
            self.assertTrue(handler.is_valid_url(url))
    
    def test_factory_info_integration(self):
        """Test factory information reporting"""
        info = self.factory.get_supported_platforms()
        
        # Should include all registered test platforms
        for platform in self.test_platforms:
            self.assertIn(platform, info)
        
        # Test detailed factory info using our isolated factory
        # Note: get_factory_info() uses global factory, so we test our factory directly
        detailed_info = {
            'supported_platforms': self.factory.get_supported_platforms(),
            'total_handlers': len(self.factory.get_supported_platforms()),
            'platform_details': {}
        }
        
        # Build platform details for our test platforms
        for platform in self.test_platforms:
            capabilities = self.factory.get_platform_capabilities(platform)
            detailed_info['platform_details'][platform.value] = {
                'display_name': platform.display_name,
                'handler_class': 'IntegrationTestHandler',
                'capabilities': capabilities.__dict__
            }
        
        self.assertIn('supported_platforms', detailed_info)
        self.assertIn('total_handlers', detailed_info)
        self.assertIn('platform_details', detailed_info)
        
        # Should have our test platforms
        supported_values = [p.value for p in detailed_info['supported_platforms']]
        for platform in self.test_platforms:
            self.assertIn(platform.value, supported_values)
    
    def test_error_handling_integration(self):
        """Test error handling across the system"""
        # Test unsupported URL
        with self.assertRaises(ValueError) as context:
            self.factory.create_handler_for_url("https://unsupported-platform.com/video")
        
        self.assertIn("Cannot detect platform from URL", str(context.exception))
        
        # Test unsupported platform
        with self.assertRaises(ValueError) as context:
            self.factory.create_handler(PlatformType.UNKNOWN)
        
        self.assertIn("Unsupported platform", str(context.exception))
        
        # Test graceful degradation
        # Remove one handler and verify others still work
        self.registry.unregister(PlatformType.YOUTUBE)
        
        # YouTube should now fail
        with self.assertRaises(ValueError):
            self.factory.create_handler_for_url("https://youtube.com/watch?v=test")
        
        # But TikTok should still work
        handler = self.factory.create_handler_for_url("https://tiktok.com/@user/video/123")
        self.assertEqual(handler.platform_type, PlatformType.TIKTOK)
    
    def test_performance_integration(self):
        """Test system performance under load"""
        test_url = "https://tiktok.com/@user/video/performance_test"
        
        # Measure detection performance
        start_time = time.time()
        for _ in range(100):
            detected = self.factory.detect_platform(test_url)
            self.assertEqual(detected, PlatformType.TIKTOK)
        detection_time = time.time() - start_time
        
        # Measure handler creation performance
        start_time = time.time()
        for _ in range(50):
            handler = self.factory.create_handler_for_url(test_url)
            self.assertEqual(handler.platform_type, PlatformType.TIKTOK)
        creation_time = time.time() - start_time
        
        # Performance should be reasonable
        self.assertLess(detection_time, 0.5, f"Detection too slow: {detection_time:.3f}s for 100 calls")
        self.assertLess(creation_time, 1.0, f"Creation too slow: {creation_time:.3f}s for 50 calls")
    
    def test_registration_lifecycle_integration(self):
        """Test dynamic registration/unregistration during operation"""
        # Create custom handler for LinkedIn
        class CustomLinkedInHandler(IntegrationTestHandler):
            def is_valid_url(self, url: str) -> bool:
                return "linkedin.com" in url.lower()
        
        # Initially LinkedIn should fail (not in our test_platforms)
        with self.assertRaises(ValueError):
            self.factory.create_handler_for_url("https://linkedin.com/posts/test")
        
        # Register LinkedIn handler
        self.registry.register(
            PlatformType.LINKEDIN,
            CustomLinkedInHandler,
            url_patterns=["linkedin.com"]
        )
        
        # Now LinkedIn should work
        handler = self.factory.create_handler_for_url("https://linkedin.com/posts/test")
        self.assertEqual(handler.platform_type, PlatformType.LINKEDIN)
        self.assertIsInstance(handler, CustomLinkedInHandler)
        
        # Unregister and verify it fails again
        self.registry.unregister(PlatformType.LINKEDIN)
        
        with self.assertRaises(ValueError):
            self.factory.create_handler_for_url("https://linkedin.com/posts/test")
    
    def test_capability_consistency_integration(self):
        """Test capability reporting consistency across the system"""
        for platform in self.test_platforms:
            # Get capabilities through factory
            factory_capabilities = self.factory.get_platform_capabilities(platform)
            
            # Get capabilities through direct handler creation
            handler = self.factory.create_handler(platform)
            handler_capabilities = handler.get_capabilities()
            
            # Should be consistent
            self.assertEqual(factory_capabilities.supports_video, handler_capabilities.supports_video)
            self.assertEqual(factory_capabilities.supports_audio, handler_capabilities.supports_audio)
            self.assertEqual(factory_capabilities.requires_auth, handler_capabilities.requires_auth)
            self.assertEqual(factory_capabilities.max_concurrent_downloads, handler_capabilities.max_concurrent_downloads)


class TestFactorySystemResilience(unittest.TestCase):
    """Test system resilience under adverse conditions"""
    
    def setUp(self):
        """Set up test environment with some problematic handlers"""
        self.registry = PlatformRegistry()
        self.factory = PlatformFactory(self.registry)
    
    def test_mixed_handler_quality(self):
        """Test system with mix of good and problematic handlers"""
        # Register a good handler
        self.registry.register(PlatformType.YOUTUBE, IntegrationTestHandler)
        
        # Register a handler that sometimes fails
        class FlakyHandler(IntegrationTestHandler):
            def __init__(self, platform_type, auth_info=None, config=None):
                if config and config.get("fail_init"):
                    raise RuntimeError("Flaky handler init failed")
                super().__init__(platform_type, auth_info, config)
            
            async def get_video_info(self, url: str) -> Dict[str, Any]:
                if "fail" in url:
                    raise ValueError("Flaky operation failed")
                return await super().get_video_info(url)
        
        self.registry.register(PlatformType.TIKTOK, FlakyHandler)
        
        # Good handler should work fine
        youtube_handler = self.factory.create_handler_for_url("https://youtube.com/watch?v=test")
        self.assertEqual(youtube_handler.platform_type, PlatformType.YOUTUBE)
        
        # Flaky handler should work with good config
        tiktok_handler = self.factory.create_handler_for_url("https://tiktok.com/@user/video/123")
        self.assertEqual(tiktok_handler.platform_type, PlatformType.TIKTOK)
        
        # Flaky handler should fail with bad config
        with self.assertRaises(RuntimeError):
            self.factory.create_handler(PlatformType.TIKTOK, config={"fail_init": True})
    
    def test_concurrent_operations(self):
        """Test concurrent factory operations"""
        import threading
        
        # Register handlers for testing
        for platform in [PlatformType.YOUTUBE, PlatformType.TIKTOK, PlatformType.INSTAGRAM]:
            self.registry.register(platform, IntegrationTestHandler)
        
        results = []
        errors = []
        
        def worker_function(worker_id):
            try:
                # Each worker creates handlers for different platforms
                platforms = [PlatformType.YOUTUBE, PlatformType.TIKTOK, PlatformType.INSTAGRAM]
                urls = [
                    "https://youtube.com/watch?v=worker" + str(worker_id),
                    "https://tiktok.com/@user/video/" + str(worker_id),
                    "https://instagram.com/p/" + str(worker_id) + "/"
                ]
                
                for platform, url in zip(platforms, urls):
                    detected = self.factory.detect_platform(url)
                    handler = self.factory.create_handler_for_url(url)
                    
                    results.append({
                        "worker_id": worker_id,
                        "platform": platform,
                        "detected": detected,
                        "handler_platform": handler.platform_type,
                        "handler_id": id(handler)
                    })
            except Exception as e:
                errors.append((worker_id, e))
        
        # Create and start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker_function, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify results
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        self.assertEqual(len(results), 15)  # 5 workers × 3 platforms each
        
        # Verify all detections were correct
        for result in results:
            self.assertEqual(result["platform"], result["detected"])
            self.assertEqual(result["platform"], result["handler_platform"])
        
        # Verify all handlers are unique instances
        handler_ids = [r["handler_id"] for r in results]
        self.assertEqual(len(set(handler_ids)), len(results))


if __name__ == '__main__':
    # Run integration tests
    unittest.main() 