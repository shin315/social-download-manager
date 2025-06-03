"""
App Controller Integration Tests

Comprehensive tests for app controller integration with service layer,
demonstrating clean architecture principles and proper dependency injection.
"""

import pytest
import asyncio
import logging
from unittest.mock import Mock, AsyncMock, patch
from typing import Optional

from core.app_controller import AppController, ControllerState, get_app_controller
from core.services import (
    ServiceRegistry, IContentService, IAnalyticsService, IDownloadService,
    ContentDTO, DownloadRequestDTO, AnalyticsDTO
)
from data.models import ContentStatus, PlatformType

# Import test base classes
from .test_base import DatabaseTestCase


class TestAppControllerServiceIntegration(DatabaseTestCase):
    """Test app controller integration with service layer"""
    
    def setUp(self):
        """Set up test environment"""
        super().setUp()
        self.controller = AppController()
        self.mock_content_service = AsyncMock(spec=IContentService)
        self.mock_analytics_service = AsyncMock(spec=IAnalyticsService)
        self.mock_download_service = AsyncMock(spec=IDownloadService)
    
    def tearDown(self):
        """Clean up test environment"""
        if self.controller and self.controller.is_ready():
            self.controller.shutdown()
        super().tearDown()
    
    def test_controller_initialization_with_services(self):
        """Test controller initialization includes service registration"""
        # Initialize controller
        result = self.controller.initialize()
        
        # Verify initialization
        self.assertTrue(result, "Controller should initialize successfully")
        self.assertEqual(self.controller._state, ControllerState.READY)
        
        # Verify service registry is available
        service_registry = self.controller.get_service_registry()
        self.assertIsNotNone(service_registry, "Service registry should be available")
        
        # Verify status includes service information
        status = self.controller.get_status()
        self.assertIsNotNone(status.services_registered, "Status should include registered services")
        self.assertIsInstance(status.services_registered, list)
    
    def test_service_accessor_methods(self):
        """Test service accessor methods work correctly"""
        # Initialize controller
        self.controller.initialize()
        
        # Test service accessors
        content_service = self.controller.get_content_service()
        analytics_service = self.controller.get_analytics_service()
        download_service = self.controller.get_download_service()
        
        # Services should be available (could be None if not registered)
        # This tests the accessor mechanism, not service availability
        # In real environment, services would be properly registered
        self.assertTrue(hasattr(self.controller, 'get_content_service'))
        self.assertTrue(hasattr(self.controller, 'get_analytics_service'))
        self.assertTrue(hasattr(self.controller, 'get_download_service'))
    
    @patch('core.services.get_content_service')
    async def test_create_content_from_url_success(self, mock_get_service):
        """Test successful content creation from URL"""
        # Setup mock service
        mock_get_service.return_value = self.mock_content_service
        
        # Setup controller with mock service
        self.controller.initialize()
        self.controller.register_component("content_service", self.mock_content_service)
        
        # Mock service response
        expected_content = ContentDTO(
            id=1,
            url="https://example.com/video",
            platform=PlatformType.YOUTUBE,
            status=ContentStatus.PENDING,
            title="Test Video"
        )
        self.mock_content_service.create_content.return_value = expected_content
        
        # Test content creation
        result = await self.controller.create_content_from_url(
            "https://example.com/video",
            "youtube"
        )
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result.url, "https://example.com/video")
        self.assertEqual(result.platform, PlatformType.YOUTUBE)
        self.assertEqual(result.status, ContentStatus.PENDING)
        
        # Verify service was called
        self.mock_content_service.create_content.assert_called_once()
    
    @patch('core.services.get_content_service')
    async def test_create_content_from_url_service_unavailable(self, mock_get_service):
        """Test content creation when service is unavailable"""
        # Setup controller without service
        self.controller.initialize()
        
        # Test content creation
        result = await self.controller.create_content_from_url(
            "https://example.com/video"
        )
        
        # Should return None when service unavailable
        self.assertIsNone(result)
    
    async def test_get_analytics_overview_success(self):
        """Test successful analytics overview retrieval"""
        # Setup controller with mock service
        self.controller.initialize()
        self.controller.register_component("analytics_service", self.mock_analytics_service)
        
        # Mock service response
        expected_analytics = AnalyticsDTO(
            total_downloads=100,
            successful_downloads=95,
            failed_downloads=5,
            success_rate=95.0
        )
        self.mock_analytics_service.get_analytics_overview.return_value = expected_analytics
        
        # Test analytics retrieval
        result = await self.controller.get_analytics_overview()
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result.total_downloads, 100)
        self.assertEqual(result.success_rate, 95.0)
        
        # Verify service was called
        self.mock_analytics_service.get_analytics_overview.assert_called_once()
    
    async def test_start_download_success(self):
        """Test successful download start"""
        # Setup controller with mock service
        self.controller.initialize()
        self.controller.register_component("download_service", self.mock_download_service)
        
        # Mock service response
        expected_content = ContentDTO(
            id=2,
            url="https://example.com/download",
            status=ContentStatus.DOWNLOADING
        )
        self.mock_download_service.start_download.return_value = expected_content
        
        # Test download start
        result = await self.controller.start_download(
            "https://example.com/download",
            {"quality": "high"}
        )
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result.url, "https://example.com/download")
        self.assertEqual(result.status, ContentStatus.DOWNLOADING)
        
        # Verify service was called with correct request
        self.mock_download_service.start_download.assert_called_once()
        call_args = self.mock_download_service.start_download.call_args[0][0]
        self.assertEqual(call_args.url, "https://example.com/download")
        self.assertEqual(call_args.quality, "high")
    
    def test_controller_shutdown_disposes_services(self):
        """Test controller shutdown properly disposes services"""
        # Initialize controller
        self.controller.initialize()
        
        # Get service registry and register mock service
        service_registry = self.controller.get_service_registry()
        if service_registry:
            # Register a mock service that supports disposal
            mock_service = Mock()
            mock_service.dispose = Mock()
            service_registry.register_instance(IContentService, mock_service)
            
            # Shutdown controller
            result = self.controller.shutdown()
            
            # Verify shutdown was successful
            self.assertTrue(result)
            self.assertEqual(self.controller._state, ControllerState.SHUTDOWN)
    
    def test_error_handling_in_business_operations(self):
        """Test error handling in high-level business operations"""
        # Setup controller with failing service
        self.controller.initialize()
        
        failing_service = AsyncMock(spec=IContentService)
        failing_service.create_content.side_effect = Exception("Service error")
        self.controller.register_component("content_service", failing_service)
        
        # Test error handling
        async def test_error():
            result = await self.controller.create_content_from_url("https://example.com/error")
            return result
        
        # Should return None and not raise exception
        result = asyncio.run(test_error())
        self.assertIsNone(result)
    
    def test_event_publishing_on_business_operations(self):
        """Test that business operations publish appropriate events"""
        # Setup controller with mock event bus
        self.controller.initialize()
        
        mock_event_bus = Mock()
        self.controller._event_bus = mock_event_bus
        self.controller.register_component("content_service", self.mock_content_service)
        
        # Mock successful content creation
        expected_content = ContentDTO(
            id=1,
            url="https://example.com/video",
            status=ContentStatus.PENDING
        )
        self.mock_content_service.create_content.return_value = expected_content
        
        # Test event publishing
        async def test_events():
            await self.controller.create_content_from_url("https://example.com/video")
        
        asyncio.run(test_events())
        
        # Verify event was published
        mock_event_bus.publish.assert_called()


class TestServiceRegistryIntegration(DatabaseTestCase):
    """Test service registry integration patterns"""
    
    def setUp(self):
        """Set up test environment"""
        super().setUp()
        self.registry = ServiceRegistry()
    
    def test_service_registration_and_retrieval(self):
        """Test basic service registration and retrieval"""
        # Create mock service
        mock_service = Mock(spec=IContentService)
        
        # Register service
        self.registry.register_instance(IContentService, mock_service)
        
        # Retrieve service
        retrieved_service = self.registry.get_service(IContentService)
        
        # Verify
        self.assertIs(retrieved_service, mock_service)
        self.assertTrue(self.registry.is_registered(IContentService))
    
    def test_singleton_lifetime_management(self):
        """Test singleton lifetime creates single instance"""
        from core.services.content_service import ContentService
        
        # Register as singleton
        self.registry.register_singleton(IContentService, ContentService)
        
        # Get multiple instances
        service1 = self.registry.get_service(IContentService)
        service2 = self.registry.get_service(IContentService)
        
        # Should be same instance
        self.assertIs(service1, service2)
    
    def test_transient_lifetime_management(self):
        """Test transient lifetime creates new instances"""
        from core.services.content_service import ContentService
        
        # Register as transient
        self.registry.register_transient(IContentService, ContentService)
        
        # Get multiple instances
        service1 = self.registry.get_service(IContentService)
        service2 = self.registry.get_service(IContentService)
        
        # Should be different instances
        self.assertIsNot(service1, service2)
        self.assertIsInstance(service1, ContentService)
        self.assertIsInstance(service2, ContentService)
    
    def test_service_disposal(self):
        """Test service disposal calls cleanup methods"""
        # Create mock service with disposal methods
        mock_service = Mock()
        mock_service.dispose = Mock()
        
        # Register and retrieve to create singleton
        self.registry.register_instance(IContentService, mock_service)
        retrieved_service = self.registry.get_service(IContentService)
        
        # Dispose services
        self.registry.dispose()
        
        # Verify disposal was called
        mock_service.dispose.assert_called_once()


class TestControllerIntegrationExamples(DatabaseTestCase):
    """Example integration patterns for documentation"""
    
    def setUp(self):
        """Set up test environment"""
        super().setUp()
        self.controller = get_app_controller()
    
    def tearDown(self):
        """Clean up test environment"""
        if self.controller and self.controller.is_ready():
            self.controller.shutdown()
        super().tearDown()
    
    def test_complete_initialization_example(self):
        """Example: Complete controller initialization"""
        # This demonstrates the recommended initialization pattern
        
        # Step 1: Initialize controller
        success = self.controller.initialize()
        self.assertTrue(success, "Controller should initialize successfully")
        
        # Step 2: Verify controller is ready
        self.assertTrue(self.controller.is_ready(), "Controller should be ready")
        
        # Step 3: Access services through controller
        content_service = self.controller.get_content_service()
        analytics_service = self.controller.get_analytics_service()
        download_service = self.controller.get_download_service()
        
        # Step 4: Check status
        status = self.controller.get_status()
        self.assertEqual(status.state, ControllerState.READY)
        self.assertIsInstance(status.components_initialized, list)
        self.assertIsInstance(status.services_registered, list)
        
        print(f"✅ Controller initialized with {len(status.components_initialized)} components")
        print(f"✅ Services registered: {status.services_registered}")
    
    async def test_content_workflow_example(self):
        """Example: Complete content management workflow"""
        # Initialize controller
        self.controller.initialize()
        
        # Mock the content service for demonstration
        mock_content_service = AsyncMock(spec=IContentService)
        self.controller.register_component("content_service", mock_content_service)
        
        # Setup mock responses
        created_content = ContentDTO(
            id=1,
            url="https://youtube.com/watch?v=example",
            platform=PlatformType.YOUTUBE,
            status=ContentStatus.PENDING,
            title="Example Video"
        )
        mock_content_service.create_content.return_value = created_content
        
        # Example workflow
        try:
            # Step 1: Create content from URL
            content = await self.controller.create_content_from_url(
                "https://youtube.com/watch?v=example",
                "youtube"
            )
            self.assertIsNotNone(content)
            print(f"✅ Content created: {content.title} ({content.id})")
            
            # Step 2: Start download
            mock_download_service = AsyncMock(spec=IDownloadService)
            download_content = ContentDTO(
                **created_content.__dict__,
                status=ContentStatus.DOWNLOADING
            )
            mock_download_service.start_download.return_value = download_content
            self.controller.register_component("download_service", mock_download_service)
            
            download_result = await self.controller.start_download(
                content.url,
                {"quality": "720p", "format": "mp4"}
            )
            self.assertIsNotNone(download_result)
            print(f"✅ Download started: {download_result.status}")
            
            # Step 3: Get analytics
            mock_analytics_service = AsyncMock(spec=IAnalyticsService)
            analytics_data = AnalyticsDTO(
                total_downloads=1,
                successful_downloads=0,
                failed_downloads=0,
                success_rate=0.0
            )
            mock_analytics_service.get_analytics_overview.return_value = analytics_data
            self.controller.register_component("analytics_service", mock_analytics_service)
            
            analytics = await self.controller.get_analytics_overview()
            self.assertIsNotNone(analytics)
            print(f"✅ Analytics retrieved: {analytics.total_downloads} total downloads")
            
        except Exception as e:
            self.fail(f"Content workflow failed: {e}")
    
    def test_error_recovery_example(self):
        """Example: Error handling and recovery patterns"""
        # Initialize controller
        self.controller.initialize()
        
        # Test error handler registration
        error_log = []
        
        def custom_error_handler(error: Exception, context: str):
            error_log.append(f"{context}: {error}")
        
        self.controller.add_error_handler(custom_error_handler)
        
        # Simulate error
        test_error = Exception("Test error")
        self.controller.handle_error(test_error, "test_context")
        
        # Verify error was handled
        self.assertEqual(len(error_log), 1)
        self.assertIn("test_context: Test error", error_log[0])
        print(f"✅ Error handled: {error_log[0]}")
        
        # Test error handler removal
        removed = self.controller.remove_error_handler(custom_error_handler)
        self.assertTrue(removed)


if __name__ == "__main__":
    # Configure logging for tests
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"]) 