"""
Comprehensive tests for platform instantiation mechanism

Tests all aspects of the platform factory instantiation system including:
- Direct platform type instantiation
- URL-based auto-instantiation  
- Dependency injection (auth & config)
- Error handling and edge cases
- Performance and concurrency
- Integration with detection and registration
"""

import sys
import os
import unittest
import time
import threading
from unittest.mock import Mock, patch
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
from platforms.base.models import AuthenticationInfo, PlatformCapabilities
from platforms.base.enums import PlatformType, AuthType


class MockInstantiationHandler(AbstractPlatformHandler):
    """Mock platform handler for instantiation testing"""
    
    def __init__(self, platform_type: PlatformType, auth_info: Optional[AuthenticationInfo] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(platform_type, auth_info, config)
        self._capabilities = PlatformCapabilities(
            supports_video=True,
            supports_audio=True,
            supports_playlists=False,
            supports_live=True,
            supports_stories=False,
            requires_auth=auth_info is not None,
            supports_watermark_removal=True,
            supports_quality_selection=True,
            supports_thumbnails=True,
            supports_metadata=True,
            max_concurrent_downloads=5,
            rate_limit_requests=20,
            rate_limit_period=60
        )
        
        # Track instantiation for testing
        self.creation_time = time.time()
        self.instantiation_id = id(self)
    
    @property
    def auth_info(self) -> Optional[AuthenticationInfo]:
        return self._auth_info
    
    @property
    def config(self) -> Dict[str, Any]:
        return self._config
    
    def get_capabilities(self) -> PlatformCapabilities:
        return self._capabilities
    
    def is_valid_url(self, url: str) -> bool:
        return "instantiation-test.com" in url.lower()
    
    async def get_video_info(self, url: str) -> Dict[str, Any]:
        return {
            "title": "Instantiation Test Video",
            "duration": 180,
            "view_count": 2000,
            "like_count": 100,
            "platform": self.platform_type.name,
            "instantiation_id": self.instantiation_id
        }
    
    async def download_video(self, url: str, output_path: str, quality: str = "best") -> bool:
        return True
    
    @property
    def capabilities(self) -> PlatformCapabilities:
        return self._capabilities


class TestPlatformInstantiation(unittest.TestCase):
    """Test platform instantiation mechanisms"""
    
    def setUp(self):
        """Set up test environment"""
        self.registry = PlatformRegistry()
        self.factory = PlatformFactory(self.registry)
        self.mock_handler = MockInstantiationHandler
        self.test_platform = PlatformType.YOUTUBE  # Use YouTube for isolation
        
        # Register test handler
        self.registry.register(
            self.test_platform,
            self.mock_handler,
            url_patterns=["instantiation-test.com"]
        )
    
    def tearDown(self):
        """Clean up test environment"""
        self.registry.unregister(self.test_platform)
    
    def test_direct_instantiation_basic(self):
        """Test basic direct instantiation by platform type"""
        handler = self.factory.create_handler(self.test_platform)
        
        self.assertIsInstance(handler, MockInstantiationHandler)
        self.assertEqual(handler.platform_type, self.test_platform)
        self.assertIsNone(handler.auth_info)
        self.assertEqual(handler.config, {})
        self.assertIsNotNone(handler.instantiation_id)
    
    def test_direct_instantiation_with_auth(self):
        """Test direct instantiation with authentication info"""
        auth_info = AuthenticationInfo(
            auth_type=AuthType.OAUTH,
            credentials={
                "access_token": "test_token_123",
                "refresh_token": "refresh_token_456",
                "client_id": "test_client_id"
            }
        )
        
        handler = self.factory.create_handler(self.test_platform, auth_info=auth_info)
        
        self.assertIsInstance(handler, MockInstantiationHandler)
        self.assertEqual(handler.auth_info, auth_info)
        self.assertTrue(handler.capabilities.requires_auth)
        self.assertEqual(handler.auth_info.auth_type, AuthType.OAUTH)
        self.assertEqual(handler.auth_info.credentials["access_token"], "test_token_123")
    
    def test_direct_instantiation_with_config(self):
        """Test direct instantiation with configuration"""
        config = {
            "timeout": 45,
            "retries": 5,
            "quality_preference": "1080p",
            "download_path": "/custom/path"
        }
        
        handler = self.factory.create_handler(self.test_platform, config=config)
        
        self.assertEqual(handler.config, config)
        self.assertEqual(handler.config["timeout"], 45)
        self.assertEqual(handler.config["quality_preference"], "1080p")
    
    def test_direct_instantiation_with_auth_and_config(self):
        """Test direct instantiation with both auth and config"""
        auth_info = AuthenticationInfo(
            auth_type=AuthType.API_KEY,
            credentials={"api_key": "secret_key_789"}
        )
        config = {"max_downloads": 10, "concurrent": True}
        
        handler = self.factory.create_handler(
            self.test_platform, 
            auth_info=auth_info, 
            config=config
        )
        
        self.assertEqual(handler.auth_info, auth_info)
        self.assertEqual(handler.config, config)
        self.assertTrue(handler.capabilities.requires_auth)
    
    def test_url_based_instantiation_basic(self):
        """Test URL-based auto-instantiation"""
        test_url = "https://instantiation-test.com/video/123"
        
        handler = self.factory.create_handler_for_url(test_url)
        
        self.assertIsInstance(handler, MockInstantiationHandler)
        self.assertEqual(handler.platform_type, self.test_platform)
        self.assertTrue(handler.is_valid_url(test_url))
    
    def test_url_based_instantiation_with_auth(self):
        """Test URL-based instantiation with auth"""
        test_url = "https://instantiation-test.com/video/456"
        auth_info = AuthenticationInfo(
            auth_type=AuthType.SESSION,
            credentials={"session_id": "session_789"}
        )
        
        handler = self.factory.create_handler_for_url(test_url, auth_info=auth_info)
        
        self.assertEqual(handler.auth_info, auth_info)
        self.assertEqual(handler.auth_info.auth_type, AuthType.SESSION)
    
    def test_url_based_instantiation_with_config(self):
        """Test URL-based instantiation with config"""
        test_url = "https://instantiation-test.com/video/789"
        config = {"format": "mp4", "audio_only": False}
        
        handler = self.factory.create_handler_for_url(test_url, config=config)
        
        self.assertEqual(handler.config, config)
        self.assertEqual(handler.config["format"], "mp4")
    
    def test_global_instantiation_functions(self):
        """Test global convenience instantiation functions"""
        # Register globally for testing
        register_platform(
            PlatformType.TIKTOK,
            self.mock_handler,
            url_patterns=["global-test.com"]
        )
        
        try:
            # Test global direct instantiation
            handler1 = create_handler(PlatformType.TIKTOK)
            self.assertIsInstance(handler1, MockInstantiationHandler)
            self.assertEqual(handler1.platform_type, PlatformType.TIKTOK)
            
            # Test global URL-based instantiation
            handler2 = create_handler_for_url("https://global-test.com/video/123")
            self.assertIsInstance(handler2, MockInstantiationHandler)
            self.assertEqual(handler2.platform_type, PlatformType.TIKTOK)
            
            # Verify different instances
            self.assertNotEqual(handler1.instantiation_id, handler2.instantiation_id)
            
        finally:
            unregister_platform(PlatformType.TIKTOK)
    
    def test_instantiation_error_handling(self):
        """Test error handling in instantiation"""
        # Test unsupported platform
        with self.assertRaises(ValueError) as context:
            self.factory.create_handler(PlatformType.UNKNOWN)
        
        self.assertIn("Unsupported platform", str(context.exception))
        self.assertIn(PlatformType.UNKNOWN.display_name, str(context.exception))
        
        # Test unsupported URL
        with self.assertRaises(ValueError) as context:
            self.factory.create_handler_for_url("https://unsupported-platform.com/video/123")
        
        self.assertIn("Cannot detect platform from URL", str(context.exception))
    
    def test_instantiation_with_faulty_handler(self):
        """Test instantiation with problematic handler class"""
        class FaultyHandler(AbstractPlatformHandler):
            def __init__(self, platform_type, auth_info=None, config=None):
                # Intentionally cause an error during initialization
                raise RuntimeError("Handler initialization failed")
            
            def get_capabilities(self):
                return PlatformCapabilities()
            
            def is_valid_url(self, url):
                return False
            
            async def get_video_info(self, url):
                return {}
            
            async def download_video(self, url, output_path, quality="best"):
                return False
        
        # Register faulty handler
        self.registry.register(PlatformType.FACEBOOK, FaultyHandler)
        
        try:
            with self.assertRaises(RuntimeError) as context:
                self.factory.create_handler(PlatformType.FACEBOOK)
            
            self.assertIn("Handler initialization failed", str(context.exception))
        finally:
            self.registry.unregister(PlatformType.FACEBOOK)
    
    def test_concurrent_instantiation(self):
        """Test concurrent handler instantiation"""
        handler_instances = []
        instantiation_errors = []
        
        def create_handler_worker():
            try:
                handler = self.factory.create_handler(self.test_platform)
                handler_instances.append(handler)
            except Exception as e:
                instantiation_errors.append(e)
        
        # Create multiple threads for concurrent instantiation
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=create_handler_worker)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify results
        self.assertEqual(len(instantiation_errors), 0, f"Errors occurred: {instantiation_errors}")
        self.assertEqual(len(handler_instances), 10)
        
        # Verify all handlers are unique instances
        instantiation_ids = [h.instantiation_id for h in handler_instances]
        self.assertEqual(len(set(instantiation_ids)), 10, "All handlers should be unique instances")
        
        # Verify all handlers have same platform type
        for handler in handler_instances:
            self.assertEqual(handler.platform_type, self.test_platform)
    
    def test_instantiation_performance(self):
        """Test instantiation performance"""
        # Measure direct instantiation performance
        start_time = time.time()
        for _ in range(100):
            handler = self.factory.create_handler(self.test_platform)
            self.assertIsInstance(handler, MockInstantiationHandler)
        direct_time = time.time() - start_time
        
        # Measure URL-based instantiation performance
        test_url = "https://instantiation-test.com/video/perf_test"
        start_time = time.time()
        for _ in range(100):
            handler = self.factory.create_handler_for_url(test_url)
            self.assertIsInstance(handler, MockInstantiationHandler)
        url_time = time.time() - start_time
        
        # Verify performance expectations
        self.assertLess(direct_time, 1.0, f"Direct instantiation too slow: {direct_time:.3f}s for 100 calls")
        self.assertLess(url_time, 1.5, f"URL-based instantiation too slow: {url_time:.3f}s for 100 calls")
        
        # URL-based should be reasonably close to direct (detection overhead)
        # Avoid division by zero with minimum time
        min_direct_time = max(direct_time, 0.001)  # At least 1ms
        overhead_ratio = url_time / min_direct_time
        self.assertLess(overhead_ratio, 10.0, f"URL-based overhead too high: {overhead_ratio:.2f}x")
    
    def test_instantiation_with_different_auth_types(self):
        """Test instantiation with various authentication types"""
        auth_configs = [
            (AuthType.API_KEY, {"api_key": "test_api_key"}),
            (AuthType.OAUTH, {"access_token": "oauth_token", "refresh_token": "refresh"}),
            (AuthType.SESSION, {"session_id": "session_123"}),
            (AuthType.BEARER, {"bearer_token": "bearer_token_123"}),
            (AuthType.BASIC, {"username": "user", "password": "pass"})
        ]
        
        for auth_type, credentials in auth_configs:
            with self.subTest(auth_type=auth_type):
                auth_info = AuthenticationInfo(
                    auth_type=auth_type,
                    credentials=credentials
                )
                
                handler = self.factory.create_handler(self.test_platform, auth_info=auth_info)
                
                self.assertEqual(handler.auth_info.auth_type, auth_type)
                self.assertEqual(handler.auth_info.credentials, credentials)
                self.assertTrue(handler.capabilities.requires_auth)
    
    def test_instantiation_integration_with_capabilities(self):
        """Test instantiation integration with platform capabilities"""
        handler = self.factory.create_handler(self.test_platform)
        capabilities = handler.get_capabilities()
        
        # Verify capabilities structure
        self.assertIsInstance(capabilities, PlatformCapabilities)
        self.assertTrue(capabilities.supports_video)
        self.assertTrue(capabilities.supports_audio)
        self.assertEqual(capabilities.max_concurrent_downloads, 5)
        self.assertEqual(capabilities.rate_limit_requests, 20)
        
        # Test capabilities through factory
        factory_capabilities = self.factory.get_platform_capabilities(self.test_platform)
        self.assertEqual(capabilities.supports_video, factory_capabilities.supports_video)
        self.assertEqual(capabilities.max_concurrent_downloads, factory_capabilities.max_concurrent_downloads)
    
    def test_instantiation_state_isolation(self):
        """Test that instantiated handlers maintain independent state"""
        # Create multiple handlers with different configs
        config1 = {"quality": "720p", "audio": True}
        config2 = {"quality": "1080p", "audio": False}
        
        handler1 = self.factory.create_handler(self.test_platform, config=config1)
        handler2 = self.factory.create_handler(self.test_platform, config=config2)
        
        # Verify independence
        self.assertNotEqual(handler1.instantiation_id, handler2.instantiation_id)
        self.assertEqual(handler1.config["quality"], "720p")
        self.assertEqual(handler2.config["quality"], "1080p")
        self.assertTrue(handler1.config["audio"])
        self.assertFalse(handler2.config["audio"])
        
        # Verify changes to one don't affect the other
        handler1.config["modified"] = True
        self.assertNotIn("modified", handler2.config)


class TestInstantiationIntegration(unittest.TestCase):
    """Test instantiation integration with other components"""
    
    def test_end_to_end_workflow(self):
        """Test complete end-to-end instantiation workflow"""
        # Register a handler with all components
        @PlatformHandler(
            PlatformType.LINKEDIN,
            url_patterns=["e2e-test.com"],
            auto_register=True
        )
        class E2ETestHandler(MockInstantiationHandler):
            pass
        
        try:
            # Test detection
            detected = detect_platform("https://e2e-test.com/video/workflow")
            self.assertEqual(detected, PlatformType.LINKEDIN)
            
            # Test support checking
            self.assertTrue(is_url_supported("https://e2e-test.com/video/workflow"))
            
            # Test instantiation
            handler = create_handler_for_url("https://e2e-test.com/video/workflow")
            self.assertIsInstance(handler, E2ETestHandler)
            self.assertEqual(handler.platform_type, PlatformType.LINKEDIN)
            
            # Test capabilities
            capabilities = get_platform_capabilities(PlatformType.LINKEDIN)
            self.assertIsNotNone(capabilities)
            self.assertTrue(capabilities.supports_video)
            
        finally:
            unregister_platform(PlatformType.LINKEDIN)
    
    def test_factory_info_integration(self):
        """Test factory info includes instantiation details"""
        info = get_factory_info()
        
        self.assertIn('supported_platforms', info)
        self.assertIn('total_handlers', info)
        self.assertIn('platform_details', info)
        
        # Should include our test platform after registration
        register_platform(PlatformType.TWITCH, MockInstantiationHandler)
        
        try:
            updated_info = get_factory_info()
            supported_platform_names = [p.value if hasattr(p, 'value') else str(p) for p in updated_info['supported_platforms']]
            self.assertIn(PlatformType.TWITCH.value, supported_platform_names)
            self.assertIn(PlatformType.TWITCH.value, updated_info['platform_details'])
        finally:
            unregister_platform(PlatformType.TWITCH)


if __name__ == '__main__':
    unittest.main() 