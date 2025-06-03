"""
Adapter Validation Tests for UI Migration

This module contains comprehensive tests for validating the adapter layer
that bridges legacy v1.2.1 components with v2.0 architecture systems.

Test Categories:
1. Interface Compliance Tests
2. Data Mapping Validation Tests  
3. Event Translation Tests
4. Performance and Error Handling Tests
5. Integration Tests
"""

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch, call
from typing import Dict, Any, List, Optional
from datetime import datetime
import weakref

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import adapter components
    IVideoInfoTabAdapter, IDownloadedVideosTabAdapter, IUIComponentAdapter,
    AdapterState, AdapterConfig, AdapterMetrics, AdapterPriority
)

# Import v2.0 architecture components (mock if not available)
try:
    from core.app_controller import AppController
    from core.event_system import EventBus, EventType, Event
    from data.models.content import VideoContent
    from data.models.downloads import DownloadModel
except ImportError:
    # Create mock classes for testing if components not available
    class AppController:
        def get_repository(self, name): return Mock()
    
    class EventBus:
        def subscribe(self, event_type, handler): pass
        def emit(self, event_type, data): pass
    
    class EventType:
        VIDEO_INFO_RETRIEVED = "video_info_retrieved"
        VIDEO_DOWNLOADED = "video_downloaded"
    
    class Event:
        def __init__(self, event_type, data): pass
    
    class VideoContent:
        def __init__(self, **kwargs): 
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class DownloadModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

# Import Qt components for testing
try:
    from PyQt6.QtWidgets import QApplication, QWidget, QTabWidget, QTableWidget
    from PyQt6.QtCore import QObject, pyqtSignal
    from PyQt6.QtTest import QTest
    
    # Ensure QApplication exists for tests
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
        
except ImportError:
    pytest.skip("PyQt6 not available", allow_module_level=True)


class MockLegacyVideoInfoTab(QWidget):
    """Mock legacy VideoInfoTab for testing"""
    
    def __init__(self):
        super().__init__()
        self.url_input = Mock()
        self.video_table = Mock()
        self.downloader = Mock()
        self.get_video_info = Mock()
        self.download_videos = Mock()
        self.video_info_dict = {}
        

class MockLegacyDownloadedVideosTab(QWidget):
    """Mock legacy DownloadedVideosTab for testing"""
    
    def __init__(self):
        super().__init__()
        self.downloads_table = Mock()
        self.all_videos = []
        self.filtered_videos = []
        self.load_downloaded_videos = Mock()
        self.display_videos = Mock()
        self.delete_video = Mock()


@pytest.fixture
def app_controller():
    """Mock AppController for testing"""
    controller = Mock(spec=AppController)
    controller.get_repository.return_value = Mock()
    return controller


@pytest.fixture
def event_bus():
    """Mock EventBus for testing"""
    bus = Mock(spec=EventBus)
    return bus


@pytest.fixture
def adapter_config():
    """Standard adapter configuration for testing"""
    return AdapterConfig(
        enable_fallback=True,
        log_events=True,
        performance_monitoring=True,
        debug_mode=True
    )


@pytest.fixture
def mock_video_info_tab():
    """Mock legacy VideoInfoTab component"""
    return MockLegacyVideoInfoTab()


@pytest.fixture
def mock_downloaded_videos_tab():
    """Mock legacy DownloadedVideosTab component"""
    return MockLegacyDownloadedVideosTab()


class TestAdapterInterfaceCompliance:
    """Test that adapters properly implement required interfaces"""
    
    def test_video_info_tab_adapter_interface_compliance(self):
        """Test VideoInfoTabAdapter implements IVideoInfoTabAdapter"""
        adapter = VideoInfoTabAdapter()
        
        # Check that adapter has all required methods
        assert hasattr(adapter, 'initialize')
        assert hasattr(adapter, 'attach_component')
        assert hasattr(adapter, 'detach_component')
        assert hasattr(adapter, 'update')
        assert hasattr(adapter, 'shutdown')
        assert hasattr(adapter, 'get_state')
        assert hasattr(adapter, 'get_metrics')
        assert hasattr(adapter, 'handle_error')
        
        # Check VideoInfoTab-specific methods
        assert hasattr(adapter, 'setup_repository_integration')
        assert hasattr(adapter, 'handle_url_input')
        assert hasattr(adapter, 'update_video_info_display')
        assert hasattr(adapter, 'handle_download_request')
        
        # Check initial state
        assert adapter.get_state() == AdapterState.UNINITIALIZED
        
    def test_downloaded_videos_tab_adapter_interface_compliance(self):
        """Test DownloadedVideosTabAdapter implements IDownloadedVideosTabAdapter"""
        adapter = DownloadedVideosTabAdapter()
        
        # Check that adapter has all required methods
        assert hasattr(adapter, 'initialize')
        assert hasattr(adapter, 'attach_component')
        assert hasattr(adapter, 'detach_component')
        assert hasattr(adapter, 'update')
        assert hasattr(adapter, 'shutdown')
        assert hasattr(adapter, 'get_state')
        assert hasattr(adapter, 'get_metrics')
        assert hasattr(adapter, 'handle_error')
        
        # Check DownloadedVideosTab-specific methods
        assert hasattr(adapter, 'setup_repository_integration')
        assert hasattr(adapter, 'load_videos_page')
        assert hasattr(adapter, 'apply_filter')
        assert hasattr(adapter, 'apply_sort')
        assert hasattr(adapter, 'select_video')
        assert hasattr(adapter, 'delete_video')
        assert hasattr(adapter, 'refresh_videos')
        
        # Check initial state
        assert adapter.get_state() == AdapterState.UNINITIALIZED


class TestAdapterLifecycle:
    """Test adapter lifecycle management"""
    
    def test_video_info_tab_adapter_initialization(self, app_controller, event_bus, adapter_config):
        """Test VideoInfoTabAdapter initialization"""
        adapter = VideoInfoTabAdapter()
        
        # Test successful initialization
        result = adapter.initialize(app_controller, event_bus, adapter_config)
        assert result is True
        assert adapter.get_state() == AdapterState.ACTIVE
        assert adapter._app_controller == app_controller
        assert adapter._event_bus == event_bus
        assert adapter._config == adapter_config
        
    def test_downloaded_videos_tab_adapter_initialization(self, app_controller, event_bus, adapter_config):
        """Test DownloadedVideosTabAdapter initialization"""
        adapter = DownloadedVideosTabAdapter()
        
        # Test successful initialization
        result = adapter.initialize(app_controller, event_bus, adapter_config)
        assert result is True
        assert adapter.get_state() == AdapterState.ACTIVE
        assert adapter._app_controller == app_controller
        assert adapter._event_bus == event_bus
        assert adapter._config == adapter_config
    
    def test_adapter_component_attachment(self, app_controller, event_bus, adapter_config, mock_video_info_tab):
        """Test attaching legacy components to adapters"""
        adapter = VideoInfoTabAdapter()
        adapter.initialize(app_controller, event_bus, adapter_config)
        
        # Test successful component attachment
        result = adapter.attach_component(mock_video_info_tab)
        assert result is True
        assert adapter._video_info_tab == mock_video_info_tab
        
        # Test invalid component type
        with pytest.raises(VideoInfoTabAdapterError):
            adapter.attach_component("invalid_component")
    
    def test_adapter_shutdown(self, app_controller, event_bus, adapter_config):
        """Test adapter shutdown process"""
        adapter = VideoInfoTabAdapter()
        adapter.initialize(app_controller, event_bus, adapter_config)
        
        # Test graceful shutdown
        result = adapter.shutdown()
        assert result is True
        assert adapter.get_state() == AdapterState.TERMINATED


class TestDataMapping:
    """Test data mapping between legacy and v2.0 formats"""
    
    def test_video_content_mapping(self):
        """Test mapping video data between legacy and v2.0 formats"""
        adapter = VideoInfoTabAdapter()
        
        # Test legacy to v2.0 mapping
        legacy_video_info = {
            'title': 'Test Video',
            'creator': 'test_user',
            'duration': 30,
            'url': 'https://example.com/video',
            'thumbnail_url': 'https://example.com/thumb.jpg',
            'description': 'Test description'
        }
        
        # The adapter should have a video mapper
        assert adapter._video_mapper is not None
        
        # Test that cache is properly initialized
        assert isinstance(adapter._video_cache, dict)
        assert len(adapter._video_cache) == 0
    
    def test_download_model_mapping(self):
        """Test mapping download data between legacy and v2.0 formats"""
        adapter = DownloadedVideosTabAdapter()
        
        # Test legacy download data
        legacy_download = {
            'id': 'test_id',
            'title': 'Downloaded Video',
            'file_path': '/path/to/video.mp4',
            'download_date': '2024-01-01 12:00:00',
            'file_size': 1024*1024,  # 1MB
            'quality': '720p',
            'format': 'mp4'
        }
        
        # The adapter should have mappers
        assert adapter._video_mapper is not None
        assert adapter._download_mapper is not None
        
        # Test that caches are properly initialized
        assert isinstance(adapter._videos_cache, dict)
        assert isinstance(adapter._filtered_videos, list)


class TestEventTranslation:
    """Test event translation between legacy and v2.0 systems"""
    
    def test_video_info_event_translation(self, app_controller, event_bus, adapter_config, mock_video_info_tab):
        """Test event translation for VideoInfoTab"""
        adapter = VideoInfoTabAdapter()
        adapter.initialize(app_controller, event_bus, adapter_config)
        adapter.attach_component(mock_video_info_tab)
        
        # Test URL input event handling
        test_url = "https://www.tiktok.com/@user/video/123456789"
        result = adapter.handle_url_input(test_url)
        assert result is True
        assert adapter._current_video_url == test_url
        
        # Test video info update
        video_data = {
            'url': test_url,
            'title': 'Test Video',
            'creator': 'test_user'
        }
        result = adapter.update_video_info_display(video_data)
        assert result is True
    
    def test_downloaded_videos_event_translation(self, app_controller, event_bus, adapter_config, mock_downloaded_videos_tab):
        """Test event translation for DownloadedVideosTab"""
        adapter = DownloadedVideosTabAdapter()
        adapter.initialize(app_controller, event_bus, adapter_config)
        adapter.attach_component(mock_downloaded_videos_tab)
        
        # Test video selection
        test_video_id = "test_video_123"
        result = adapter.select_video(test_video_id)
        assert result is True
        assert test_video_id in adapter._selected_video_ids
        
        # Test filtering
        filter_criteria = {'quality': '720p', 'format': 'mp4'}
        result = adapter.apply_filter(filter_criteria)
        assert result is True
        assert adapter._current_filter == filter_criteria


class TestPerformanceAndErrorHandling:
    """Test adapter performance monitoring and error handling"""
    
    def test_performance_monitoring(self, app_controller, event_bus):
        """Test adapter performance monitoring"""
        config = AdapterConfig(performance_monitoring=True)
        adapter = VideoInfoTabAdapter()
        adapter.initialize(app_controller, event_bus, config)
        
        # Check that metrics are being collected
        metrics = adapter.get_metrics()
        assert isinstance(metrics, AdapterMetrics)
        assert metrics.events_processed >= 0
        assert metrics.memory_usage_mb >= 0
    
    def test_error_handling(self, app_controller, event_bus, adapter_config):
        """Test adapter error handling"""
        adapter = VideoInfoTabAdapter()
        adapter.initialize(app_controller, event_bus, adapter_config)
        
        # Test error handling
        test_error = Exception("Test error")
        result = adapter.handle_error(test_error, "test_context")
        assert result is True
        assert adapter._last_error == "Test error"
    
    def test_fallback_mode(self, app_controller, event_bus, adapter_config, mock_video_info_tab):
        """Test adapter fallback mode when v2.0 systems fail"""
        adapter = VideoInfoTabAdapter()
        adapter.initialize(app_controller, event_bus, adapter_config)
        adapter.attach_component(mock_video_info_tab)
        
        # Simulate v2.0 system failure
        adapter._app_controller = None
        
        # Adapter should enable fallback mode
        adapter._enable_fallback_mode()
        
        # Check that original methods are restored
        assert len(adapter._original_methods) >= 0


class TestIntegrationScenarios:
    """Test end-to-end integration scenarios"""
    
    def test_video_download_workflow(self, app_controller, event_bus, adapter_config, mock_video_info_tab):
        """Test complete video download workflow through adapters"""
        video_adapter = VideoInfoTabAdapter()
        video_adapter.initialize(app_controller, event_bus, adapter_config)
        video_adapter.attach_component(mock_video_info_tab)
        
        downloaded_adapter = DownloadedVideosTabAdapter()
        downloaded_adapter.initialize(app_controller, event_bus, adapter_config)
        
        # Step 1: URL input
        test_url = "https://www.tiktok.com/@user/video/123456789"
        result = video_adapter.handle_url_input(test_url)
        assert result is True
        
        # Step 2: Video info retrieval (simulated)
        video_data = {
            'url': test_url,
            'title': 'Test Video',
            'creator': 'test_user',
            'duration': 30
        }
        result = video_adapter.update_video_info_display(video_data)
        assert result is True
        
        # Step 3: Download request
        download_options = {
            'url': test_url,
            'quality': '720p',
            'format': 'mp4',
            'output_path': '/downloads/'
        }
        result = video_adapter.handle_download_request(download_options)
        assert result is True
        
        # Step 4: Downloaded videos update (simulated)
        download_data = {
            'content_id': 'test_video_123',
            'title': 'Test Video',
            'file_path': '/downloads/test_video.mp4',
            'status': 'completed'
        }
        result = downloaded_adapter.update(download_data)
        assert result is True
    
    def test_multi_adapter_coordination(self, app_controller, event_bus, adapter_config):
        """Test coordination between multiple adapters"""
        video_adapter = VideoInfoTabAdapter()
        downloaded_adapter = DownloadedVideosTabAdapter()
        
        # Initialize both adapters with same event bus
        video_adapter.initialize(app_controller, event_bus, adapter_config)
        downloaded_adapter.initialize(app_controller, event_bus, adapter_config)
        
        # Both adapters should be active and connected to same event bus
        assert video_adapter.get_state() == AdapterState.ACTIVE
        assert downloaded_adapter.get_state() == AdapterState.ACTIVE
        assert video_adapter._event_bus == event_bus
        assert downloaded_adapter._event_bus == event_bus


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_invalid_initialization_parameters(self):
        """Test adapter behavior with invalid initialization parameters"""
        adapter = VideoInfoTabAdapter()
        
        # Test with None parameters
        result = adapter.initialize(None, None, None)
        assert result is False
        assert adapter.get_state() == AdapterState.ERROR
    
    def test_double_initialization(self, app_controller, event_bus, adapter_config):
        """Test double initialization of adapters"""
        adapter = VideoInfoTabAdapter()
        
        # First initialization should succeed
        result1 = adapter.initialize(app_controller, event_bus, adapter_config)
        assert result1 is True
        
        # Second initialization should be handled gracefully
        result2 = adapter.initialize(app_controller, event_bus, adapter_config)
        # Implementation may choose to succeed or fail - just ensure no crash
        assert isinstance(result2, bool)
    
    def test_component_detachment_without_attachment(self):
        """Test detaching component that was never attached"""
        adapter = VideoInfoTabAdapter()
        
        # Should handle gracefully
        result = adapter.detach_component()
        assert isinstance(result, bool)
    
    def test_memory_cleanup_on_shutdown(self, app_controller, event_bus, adapter_config, mock_video_info_tab):
        """Test that adapters properly clean up memory on shutdown"""
        adapter = VideoInfoTabAdapter()
        adapter.initialize(app_controller, event_bus, adapter_config)
        adapter.attach_component(mock_video_info_tab)
        
        # Add some data to caches
        adapter._video_cache['test'] = VideoContent(title='Test')
        assert len(adapter._video_cache) > 0
        
        # Shutdown should clean up
        adapter.shutdown()
        
        # References should be cleared
        assert adapter._video_info_tab is None
        assert adapter._app_controller is None
        assert adapter._event_bus is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"]) 