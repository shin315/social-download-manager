"""
Comprehensive tests for platform registration system

Tests all aspects of the platform factory registration system including:
- Basic registration/unregistration
- Global convenience functions  
- Decorator-based registration
- Custom detection callbacks
- Error handling
- Platform capabilities integration
- Performance testing
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch
from typing import Optional, Dict, Any, List

# Add current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from platforms.base.factory import (
    PlatformRegistry, PlatformFactory, register_platform, unregister_platform,
    create_handler, create_handler_for_url, detect_platform, is_url_supported,
    get_supported_platforms, get_platform_capabilities, PlatformHandler,
    discover_handlers, get_factory_info
)
from platforms.base.platform_handler import AbstractPlatformHandler
from platforms.base.models import AuthenticationInfo, PlatformCapabilities
from platforms.base.enums import PlatformType, AuthType


class MockPlatformHandler(AbstractPlatformHandler):
    """Mock platform handler for testing"""
    
    def __init__(self, platform_type: PlatformType, auth_info: Optional[AuthenticationInfo] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(platform_type, auth_info, config)
        self._capabilities = PlatformCapabilities(
            supports_video=True,
            supports_audio=True,
            supports_playlists=True,
            supports_live=False,
            supports_stories=False,
            requires_auth=False,
            supports_watermark_removal=False,
            supports_quality_selection=True,
            supports_thumbnails=True,
            supports_metadata=True,
            max_concurrent_downloads=3,
            rate_limit_requests=10,
            rate_limit_period=60
        )
    
    @property
    def auth_info(self) -> Optional[AuthenticationInfo]:
        """Get authentication info"""
        return self._auth_info
    
    @property
    def config(self) -> Dict[str, Any]:
        """Get configuration"""
        return self._config
    
    def get_capabilities(self) -> PlatformCapabilities:
        """Get platform capabilities"""
        return self._capabilities
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid for this platform"""
        return "test-platform.com" in url.lower()
    
    async def get_video_info(self, url: str) -> Dict[str, Any]:
        """Get video information from URL"""
        # Return simplified dict for testing (not full PlatformVideoInfo)
        return {
            "title": "Test Video",
            "duration": 120,
            "view_count": 1000,
            "like_count": 50
        }
    
    async def download_video(self, url: str, output_path: str, quality: str = "best") -> bool:
        """Download video from URL"""
        return True
    
    @property
    def capabilities(self) -> PlatformCapabilities:
        """Get platform capabilities (legacy property)"""
        return self._capabilities


class TestPlatformRegistry(unittest.TestCase):
    """Test PlatformRegistry functionality"""
    
    def setUp(self):
        """Set up test registry"""
        self.registry = PlatformRegistry()
        self.mock_handler = MockPlatformHandler
        self.test_platform = PlatformType.TIKTOK  # Using existing enum value
    
    def test_basic_registration(self):
        """Test basic handler registration"""
        # Register handler
        self.registry.register(
            self.test_platform,
            self.mock_handler,
            url_patterns=["test-platform.com"],
            detection_callback=lambda url: "test-platform.com" in url.lower()
        )
        
        # Verify registration
        handler_class = self.registry.get_handler_class(self.test_platform)
        self.assertEqual(handler_class, self.mock_handler)
        
        registered_platforms = self.registry.get_registered_platforms()
        self.assertIn(self.test_platform, registered_platforms)
        
        # Test platform support
        self.assertTrue(self.registry.is_supported(self.test_platform))
        self.assertFalse(self.registry.is_supported(PlatformType.UNKNOWN))
    
    def test_registration_validation(self):
        """Test registration validation"""
        # Test invalid handler class
        class InvalidHandler:
            pass
        
        with self.assertRaises(TypeError):
            self.registry.register(self.test_platform, InvalidHandler)
    
    def test_unregistration(self):
        """Test handler unregistration"""
        # Register first
        self.registry.register(self.test_platform, self.mock_handler)
        self.assertTrue(self.registry.is_supported(self.test_platform))
        
        # Unregister
        result = self.registry.unregister(self.test_platform)
        self.assertTrue(result)
        self.assertFalse(self.registry.is_supported(self.test_platform))
        
        # Unregister non-existent
        result = self.registry.unregister(PlatformType.UNKNOWN)
        self.assertFalse(result)
    
    def test_platform_detection_callback(self):
        """Test custom detection callback"""
        def custom_callback(url: str) -> bool:
            return "custom-test.com" in url.lower()
        
        self.registry.register(
            self.test_platform,
            self.mock_handler,
            detection_callback=custom_callback
        )
        
        # Test detection
        detected = self.registry.detect_platform("https://custom-test.com/video/123")
        self.assertEqual(detected, self.test_platform)
        
        # Test non-matching URL
        detected = self.registry.detect_platform("https://other-site.com/video/123")
        self.assertEqual(detected, PlatformType.UNKNOWN)
    
    def test_platform_detection_patterns(self):
        """Test URL pattern matching"""
        self.registry.register(
            self.test_platform,
            self.mock_handler,
            url_patterns=["test-platform.com", "tp.com"]
        )
        
        # Test pattern matching
        detected = self.registry.detect_platform("https://test-platform.com/video/123")
        self.assertEqual(detected, self.test_platform)
        
        detected = self.registry.detect_platform("https://www.tp.com/video/123")
        self.assertEqual(detected, self.test_platform)
    
    def test_url_support_checking(self):
        """Test URL support checking"""
        self.registry.register(
            self.test_platform,
            self.mock_handler,
            url_patterns=["test-platform.com"]
        )
        
        self.assertTrue(self.registry.is_url_supported("https://test-platform.com/video/123"))
        self.assertFalse(self.registry.is_url_supported("https://unsupported-site.com/video/123"))
    
    def test_detection_callback_error_handling(self):
        """Test error handling in detection callbacks"""
        def faulty_callback(url: str) -> bool:
            raise Exception("Callback error")
        
        self.registry.register(
            self.test_platform,
            self.mock_handler,
            detection_callback=faulty_callback
        )
        
        # Should not raise exception, should fall back to other methods
        detected = self.registry.detect_platform("https://test-platform.com/video/123")
        # Should use enum fallback since patterns weren't provided
        self.assertIsInstance(detected, PlatformType)


class TestPlatformFactory(unittest.TestCase):
    """Test PlatformFactory functionality"""
    
    def setUp(self):
        """Set up test factory"""
        self.registry = PlatformRegistry()
        self.factory = PlatformFactory(self.registry)
        self.mock_handler = MockPlatformHandler
        self.test_platform = PlatformType.TIKTOK
        
        # Register test handler
        self.registry.register(self.test_platform, self.mock_handler)
    
    def test_handler_creation(self):
        """Test handler creation"""
        handler = self.factory.create_handler(self.test_platform)
        self.assertIsInstance(handler, MockPlatformHandler)
        self.assertEqual(handler.platform_type, self.test_platform)
    
    def test_handler_creation_with_auth(self):
        """Test handler creation with authentication"""
        auth_info = AuthenticationInfo(
            auth_type=AuthType.API_KEY,
            credentials={"username": "test_user", "password": "test_pass", "api_key": "test_key"}
        )
        
        handler = self.factory.create_handler(self.test_platform, auth_info=auth_info)
        self.assertEqual(handler.auth_info, auth_info)
    
    def test_handler_creation_with_config(self):
        """Test handler creation with configuration"""
        config = {"timeout": 30, "retries": 3}
        
        handler = self.factory.create_handler(self.test_platform, config=config)
        self.assertEqual(handler.config, config)
    
    def test_unsupported_platform_error(self):
        """Test error for unsupported platform"""
        with self.assertRaises(ValueError) as context:
            self.factory.create_handler(PlatformType.UNKNOWN)
        
        self.assertIn("Unsupported platform", str(context.exception))
    
    def test_handler_creation_from_url(self):
        """Test handler creation from URL"""
        # Register with URL pattern
        self.registry.register(
            self.test_platform,
            self.mock_handler,
            url_patterns=["test-platform.com"]
        )
        
        handler = self.factory.create_handler_for_url("https://test-platform.com/video/123")
        self.assertIsInstance(handler, MockPlatformHandler)
        self.assertEqual(handler.platform_type, self.test_platform)
    
    def test_unsupported_url_error(self):
        """Test error for unsupported URL"""
        with self.assertRaises(ValueError) as context:
            self.factory.create_handler_for_url("https://unsupported-site.com/video/123")
        
        self.assertIn("Cannot detect platform from URL", str(context.exception))
    
    def test_factory_info(self):
        """Test factory information retrieval"""
        platforms = self.factory.get_supported_platforms()
        self.assertIn(self.test_platform, platforms)
        
        # Note: These URL checks will fallback to enum detection since we didn't register patterns in setUp
        detected = self.factory.detect_platform("https://tiktok.com/video/123")
        self.assertEqual(detected, PlatformType.TIKTOK)


class TestGlobalConvenienceFunctions(unittest.TestCase):
    """Test global convenience functions"""
    
    def setUp(self):
        """Set up for global function tests"""
        self.mock_handler = MockPlatformHandler
        self.test_platform = PlatformType.YOUTUBE  # Use different platform for isolation
    
    def tearDown(self):
        """Clean up after tests"""
        unregister_platform(self.test_platform)
    
    def test_global_registration(self):
        """Test global register/unregister functions"""
        # Register globally
        register_platform(
            self.test_platform,
            self.mock_handler,
            url_patterns=["test-global.com"]
        )
        
        # Check registration
        platforms = get_supported_platforms()
        self.assertIn(self.test_platform, platforms)
        
        # Test detection
        detected = detect_platform("https://test-global.com/video/123")
        self.assertEqual(detected, self.test_platform)
        
        # Test URL support
        self.assertTrue(is_url_supported("https://test-global.com/video/123"))
        
        # Unregister
        result = unregister_platform(self.test_platform)
        self.assertTrue(result)
        
        platforms = get_supported_platforms()
        self.assertNotIn(self.test_platform, platforms)
    
    def test_global_handler_creation(self):
        """Test global handler creation functions"""
        register_platform(self.test_platform, self.mock_handler)
        
        # Create handler by platform type
        handler = create_handler(self.test_platform)
        self.assertIsInstance(handler, MockPlatformHandler)
        
        # Create handler by URL (need to register with pattern)
        register_platform(
            self.test_platform,
            self.mock_handler,
            url_patterns=["test-global.com"]
        )
        
        handler = create_handler_for_url("https://test-global.com/video/123")
        self.assertIsInstance(handler, MockPlatformHandler)
    
    def test_global_capabilities(self):
        """Test global capabilities function"""
        register_platform(self.test_platform, self.mock_handler)
        
        capabilities = get_platform_capabilities(self.test_platform)
        self.assertIsInstance(capabilities, PlatformCapabilities)
        self.assertTrue(capabilities.supports_video)


class TestPlatformHandlerDecorator(unittest.TestCase):
    """Test @PlatformHandler decorator"""
    
    def setUp(self):
        """Set up for decorator tests"""
        self.test_platform = PlatformType.INSTAGRAM  # Use different platform for isolation
    
    def tearDown(self):
        """Clean up after tests"""
        unregister_platform(self.test_platform)
    
    def test_decorator_registration(self):
        """Test decorator-based registration"""
        @PlatformHandler(self.test_platform, url_patterns=["test-decorator.com"])
        class DecoratorTestHandler(MockPlatformHandler):
            pass
        
        # Check if registered
        platforms = get_supported_platforms()
        self.assertIn(self.test_platform, platforms)
        
        # Test handler creation
        handler = create_handler(self.test_platform)
        self.assertIsInstance(handler, DecoratorTestHandler)
    
    def test_decorator_with_detection_callback(self):
        """Test decorator with custom detection callback"""
        def custom_detection(url: str) -> bool:
            return "decorator-test.com" in url.lower()
        
        @PlatformHandler(self.test_platform, detection_callback=custom_detection)
        class CallbackTestHandler(MockPlatformHandler):
            pass
        
        # Test detection
        detected = detect_platform("https://decorator-test.com/video/123")
        self.assertEqual(detected, self.test_platform)
    
    def test_decorator_auto_register_false(self):
        """Test decorator with auto_register=False"""
        @PlatformHandler(self.test_platform, auto_register=False)
        class NoAutoRegisterHandler(MockPlatformHandler):
            pass
        
        # Should not be automatically registered
        platforms = get_supported_platforms()
        self.assertNotIn(self.test_platform, platforms)


class TestPerformance(unittest.TestCase):
    """Test performance aspects of registration system"""
    
    def test_detection_performance(self):
        """Test detection performance"""
        import time
        
        registry = PlatformRegistry()
        registry.register(
            PlatformType.TIKTOK,
            MockPlatformHandler,
            url_patterns=["tiktok.com"]
        )
        
        url = "https://www.tiktok.com/@user/video/123456789"
        
        # Test detection speed
        start_time = time.time()
        for _ in range(1000):
            registry.detect_platform(url)
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 1000
        self.assertLess(avg_time, 0.001)  # Should be less than 1ms per detection
    
    def test_multiple_registrations_performance(self):
        """Test performance with multiple registered platforms"""
        registry = PlatformRegistry()
        
        # Register multiple platforms
        platforms = [PlatformType.TIKTOK, PlatformType.YOUTUBE, PlatformType.INSTAGRAM]
        for platform in platforms:
            registry.register(
                platform,
                MockPlatformHandler,
                url_patterns=[f"{platform.name.lower()}.com"]
            )
        
        # Test detection with many registered platforms
        import time
        start_time = time.time()
        
        for _ in range(100):
            for platform in platforms:
                url = f"https://{platform.name.lower()}.com/video/123"
                detected = registry.detect_platform(url)
                self.assertEqual(detected, platform)
        
        end_time = time.time()
        total_time = end_time - start_time
        self.assertLess(total_time, 1.0)  # Should complete in less than 1 second


class TestFactoryInfo(unittest.TestCase):
    """Test factory information functionality"""
    
    def test_factory_info_structure(self):
        """Test factory info structure"""
        info = get_factory_info()
        
        self.assertIsInstance(info, dict)
        self.assertIn('supported_platforms', info)
        self.assertIn('total_handlers', info)
        self.assertIn('platform_details', info)
        
        # Test info content
        self.assertIsInstance(info['supported_platforms'], list)
        self.assertIsInstance(info['total_handlers'], int)
        self.assertIsInstance(info['platform_details'], dict)


if __name__ == '__main__':
    unittest.main() 