"""
Component Testing Framework

Comprehensive test suite for UI components including unit tests,
integration tests, and mock testing scenarios.
"""

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtTest import QTest

# Add ui components to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ui.components.common.models import ButtonConfig, ButtonType, StatisticsData
from ui.components.common.events import EventType, ComponentEvent, ComponentBus, get_event_bus
from ui.components.mixins.language_support import LanguageSupport
from ui.components.mixins.theme_support import ThemeSupport
from ui.components.mixins.tooltip_support import TooltipSupport
from ui.components.widgets.action_button_group import ActionButtonGroup, create_download_tab_buttons
from ui.components.widgets.statistics_widget import StatisticsWidget
from ui.components.widgets.thumbnail_widget import ThumbnailWidget, create_medium_thumbnail
from ui.components.widgets.progress_tracker import ProgressTracker, create_download_progress_tracker

# Test fixtures
@pytest.fixture
def qapp():
    """Create QApplication instance for testing"""
    if not QApplication.instance():
        app = QApplication([])
    else:
        app = QApplication.instance()
    yield app

@pytest.fixture
def mock_lang_manager():
    """Create mock language manager"""
    lang_manager = Mock()
    lang_manager.tr = Mock(side_effect=lambda key: f"translated_{key}")
    return lang_manager

@pytest.fixture
def sample_theme():
    """Create sample theme dict"""
    return {
        'background_color': '#2b2b2b',
        'text_color': '#ffffff',
        'accent_color': '#0078d4',
        'border_color': '#555555',
        'hover_color': '#404040',
        'button_style': 'QPushButton { background-color: #404040; }',
        'stats_frame_style': 'QFrame { background-color: #2b2b2b; border: 1px solid #555; }',
        'stats_label_style': 'QLabel { color: #ffffff; }',
        'thumbnail_border_color': '#555555',
        'progress_bar_style': 'QProgressBar { border: 1px solid #555; }',
        'progress_label_style': 'QLabel { color: #ffffff; }'
    }

@pytest.fixture
def sample_video_data():
    """Create sample video data for testing"""
    return [
        {
            'title': 'Test Video 1',
            'size': '50.5 MB',
            'download_date': '2025-01-01',
            'url': 'https://example.com/video1'
        },
        {
            'title': 'Test Video 2', 
            'size': '1.2 GB',
            'download_date': '2025-01-02',
            'url': 'https://example.com/video2'
        },
        {
            'title': 'Test Video 3',
            'size': '750 KB',
            'download_date': '2025-01-03',
            'url': 'https://example.com/video3'
        }
    ]

# Event System Tests
class TestEventSystem:
    """Test the component event system"""
    
    def test_event_bus_singleton(self):
        """Test that event bus is singleton"""
        bus1 = get_event_bus()
        bus2 = get_event_bus()
        assert bus1 is bus2
    
    def test_event_emission(self, qapp):
        """Test event emission and subscription"""
        bus = get_event_bus()
        received_events = []
        
        def event_callback(event):
            received_events.append(event)
        
        # Subscribe to state change events
        bus.subscribe(EventType.STATE_CHANGED, event_callback)
        
        # Emit event
        bus.emit_event(
            EventType.STATE_CHANGED,
            "test_component",
            {"test_data": "value"}
        )
        
        # Check event was received
        assert len(received_events) == 1
        assert received_events[0].event_type == EventType.STATE_CHANGED
        assert received_events[0].source_component == "test_component"
        assert received_events[0].data["test_data"] == "value"
    
    def test_component_event_structure(self, qapp):
        """Test ComponentEvent structure"""
        event = ComponentEvent(
            event_type=EventType.DATA_UPDATED,
            source_component="test_component",
            data={"key": "value"},
            target_component="target"
        )
        
        assert event.event_type == EventType.DATA_UPDATED
        assert event.source_component == "test_component"
        assert event.data["key"] == "value"
        assert event.target_component == "target"
        assert event.timestamp is not None

# Mixin Tests
class TestLanguageSupport:
    """Test LanguageSupport mixin"""
    
    def test_language_support_initialization(self, qapp, mock_lang_manager):
        """Test LanguageSupport initialization"""
        class TestComponent(LanguageSupport):
            def update_language(self):
                pass
        
        component = TestComponent("test_component", mock_lang_manager)
        assert component.component_name == "test_component"
        assert component._lang_manager == mock_lang_manager
    
    def test_tr_method(self, qapp, mock_lang_manager):
        """Test tr_() method functionality"""
        class TestComponent(LanguageSupport):
            def update_language(self):
                pass
        
        component = TestComponent("test_component", mock_lang_manager)
        result = component.tr_("TEST_KEY")
        assert result == "translated_TEST_KEY"
        mock_lang_manager.tr.assert_called_with("TEST_KEY")
    
    def test_tr_fallback(self, qapp):
        """Test tr_() fallback when no language manager"""
        class TestComponent(LanguageSupport):
            def update_language(self):
                pass
        
        component = TestComponent("test_component")
        result = component.tr_("TEST_KEY")
        assert result == "TEST_KEY"

class TestThemeSupport:
    """Test ThemeSupport mixin"""
    
    def test_theme_application(self, qapp, sample_theme):
        """Test theme application"""
        class TestWidget(QWidget, ThemeSupport):
            def __init__(self):
                QWidget.__init__(self)
                ThemeSupport.__init__(self, "test_widget")
                self.theme_applied = False
            
            def _apply_component_theme(self, theme):
                self.theme_applied = True
                self.applied_theme = theme
        
        widget = TestWidget()
        widget.apply_theme(sample_theme)
        
        assert widget.theme_applied
        assert widget.applied_theme == sample_theme
        assert widget.get_current_theme() == sample_theme
    
    def test_predefined_themes(self, qapp):
        """Test predefined dark/light themes"""
        class TestWidget(QWidget, ThemeSupport):
            def __init__(self):
                QWidget.__init__(self)
                ThemeSupport.__init__(self, "test_widget")
        
        widget = TestWidget()
        
        # Test dark theme
        widget.apply_dark_theme()
        theme = widget.get_current_theme()
        assert theme['background_color'] == '#2b2b2b'
        assert theme['text_color'] == '#ffffff'
        
        # Test light theme
        widget.apply_light_theme()
        theme = widget.get_current_theme()
        assert theme['background_color'] == '#ffffff'
        assert theme['text_color'] == '#000000'

class TestTooltipSupport:
    """Test TooltipSupport mixin"""
    
    def test_tooltip_formatting(self, qapp):
        """Test tooltip text formatting"""
        class TestComponent(TooltipSupport):
            pass
        
        component = TestComponent("test_component")
        
        # Test basic formatting
        text = "This is a test. With multiple sentences! And questions?"
        formatted = component.format_tooltip_text(text)
        assert '\n' in formatted
        
        # Test hashtag formatting
        text_with_hashtags = "Check this out #awesome #cool #nice"
        formatted = component.format_tooltip_text(text_with_hashtags)
        assert '#awesome\n#cool\n#nice' in formatted
    
    def test_tooltip_length_limit(self, qapp):
        """Test tooltip length limiting"""
        class TestComponent(TooltipSupport):
            pass
        
        component = TestComponent("test_component")
        component.set_max_tooltip_length(50)
        
        long_text = "a" * 100
        formatted = component.format_tooltip_text(long_text)
        assert len(formatted) <= 53  # 50 + "..."

# Widget Tests
class TestActionButtonGroup:
    """Test ActionButtonGroup widget"""
    
    def test_button_group_creation(self, qapp, mock_lang_manager):
        """Test button group creation with configuration"""
        buttons_config = [
            ButtonConfig(ButtonType.SELECT_ALL, "BUTTON_SELECT_ALL", 150),
            ButtonConfig(ButtonType.DELETE_SELECTED, "BUTTON_DELETE_SELECTED", 150)
        ]
        
        group = ActionButtonGroup(buttons_config, lang_manager=mock_lang_manager)
        
        assert len(group.buttons) == 2
        assert ButtonType.SELECT_ALL in group.buttons
        assert ButtonType.DELETE_SELECTED in group.buttons
    
    def test_button_signals(self, qapp, mock_lang_manager):
        """Test button signal emission"""
        buttons_config = [
            ButtonConfig(ButtonType.SELECT_ALL, "BUTTON_SELECT_ALL", 150)
        ]
        
        group = ActionButtonGroup(buttons_config, lang_manager=mock_lang_manager)
        
        # Test signal connection
        signal_received = []
        group.select_all_clicked.connect(lambda: signal_received.append(True))
        
        # Simulate button click
        button = group.get_button(ButtonType.SELECT_ALL)
        button.click()
        
        assert len(signal_received) == 1
    
    def test_factory_functions(self, qapp, mock_lang_manager):
        """Test factory functions for common configurations"""
        download_group = create_download_tab_buttons(mock_lang_manager)
        assert len(download_group.buttons) == 3
        assert ButtonType.SELECT_ALL in download_group.buttons
        assert ButtonType.DELETE_SELECTED in download_group.buttons
        assert ButtonType.REFRESH in download_group.buttons

class TestStatisticsWidget:
    """Test StatisticsWidget"""
    
    def test_statistics_calculation(self, qapp, sample_video_data, mock_lang_manager):
        """Test statistics calculation"""
        widget = StatisticsWidget(lang_manager=mock_lang_manager)
        widget.update_statistics(sample_video_data)
        
        stats = widget.get_statistics()
        assert stats.total_videos == 3
        assert 'GB' in stats.total_size or 'MB' in stats.total_size
        assert stats.last_download == '2025-01-03'
    
    def test_size_parsing(self, qapp, mock_lang_manager):
        """Test size string parsing"""
        widget = StatisticsWidget(lang_manager=mock_lang_manager)
        
        # Test various size formats
        assert widget._parse_size_string("50.5 MB") == 50.5 * 1024 * 1024
        assert widget._parse_size_string("1.2 GB") == int(1.2 * 1024 * 1024 * 1024)
        assert widget._parse_size_string("750 KB") == 750 * 1024
        assert widget._parse_size_string("N/A") == 0
    
    def test_size_formatting(self, qapp, mock_lang_manager):
        """Test size formatting"""
        widget = StatisticsWidget(lang_manager=mock_lang_manager)
        
        # Test formatting
        assert "GB" in widget._format_size(2 * 1024 * 1024 * 1024)
        assert "MB" in widget._format_size(50 * 1024 * 1024)
        assert "KB" in widget._format_size(500 * 1024)
        assert "B" in widget._format_size(100)

class TestThumbnailWidget:
    """Test ThumbnailWidget"""
    
    def test_thumbnail_widget_creation(self, qapp, mock_lang_manager):
        """Test thumbnail widget creation"""
        widget = ThumbnailWidget(lang_manager=mock_lang_manager, size=(100, 80))
        assert widget.thumbnail_size == (100, 80)
        assert widget.size().width() == 100
        assert widget.size().height() == 80
    
    def test_thumbnail_states(self, qapp, mock_lang_manager):
        """Test different thumbnail states"""
        widget = ThumbnailWidget(lang_manager=mock_lang_manager)
        
        # Test placeholder state
        widget.set_placeholder()
        assert not widget.loading_state
        assert widget.current_url == ""
        
        # Test loading state
        widget.set_loading_state()
        assert widget.loading_state
        
        # Test error state
        widget.set_error_state()
        assert not widget.loading_state
    
    def test_factory_functions(self, qapp, mock_lang_manager):
        """Test thumbnail factory functions"""
        small = create_medium_thumbnail(lang_manager=mock_lang_manager)
        assert small.thumbnail_size == (120, 90)

class TestProgressTracker:
    """Test ProgressTracker widget"""
    
    def test_progress_updates(self, qapp, mock_lang_manager):
        """Test progress updates"""
        tracker = ProgressTracker(lang_manager=mock_lang_manager)
        
        # Test progress update
        tracker.update_progress(50, "Downloading...")
        assert tracker.get_progress() == 50
        assert tracker.get_status() == "Downloading..."
        
        # Test completion
        tracker.update_progress(100, "Complete")
        assert tracker.is_completed()
    
    def test_indeterminate_mode(self, qapp, mock_lang_manager):
        """Test indeterminate progress mode"""
        tracker = ProgressTracker(lang_manager=mock_lang_manager)
        
        tracker.set_indeterminate(True)
        assert tracker.progress_bar.minimum() == 0
        assert tracker.progress_bar.maximum() == 0
        
        tracker.set_indeterminate(False)
        assert tracker.progress_bar.maximum() == 100
    
    def test_error_handling(self, qapp, mock_lang_manager):
        """Test error state handling"""
        tracker = ProgressTracker(lang_manager=mock_lang_manager)
        
        tracker.set_error("Test error")
        assert tracker.is_failed()
        assert "Test error" in tracker.get_status()
    
    def test_factory_functions(self, qapp, mock_lang_manager):
        """Test progress tracker factory functions"""
        download_tracker = create_download_progress_tracker(lang_manager=mock_lang_manager)
        assert download_tracker.show_speed
        assert download_tracker.show_status

# Integration Tests
class TestComponentIntegration:
    """Test component integration scenarios"""
    
    def test_event_communication(self, qapp, mock_lang_manager, sample_theme):
        """Test event communication between components"""
        # Create components
        button_group = ActionButtonGroup(
            [ButtonConfig(ButtonType.SELECT_ALL, "BUTTON_SELECT_ALL", 150)],
            lang_manager=mock_lang_manager
        )
        stats_widget = StatisticsWidget(lang_manager=mock_lang_manager)
        
        # Test theme propagation
        button_group.apply_theme(sample_theme)
        stats_widget.apply_theme(sample_theme)
        
        assert button_group.get_current_theme() == sample_theme
        assert stats_widget.get_current_theme() == sample_theme
    
    def test_language_synchronization(self, qapp, mock_lang_manager):
        """Test language synchronization across components"""
        components = [
            ActionButtonGroup([ButtonConfig(ButtonType.SELECT_ALL, "BUTTON_SELECT_ALL", 150)], 
                            lang_manager=mock_lang_manager),
            StatisticsWidget(lang_manager=mock_lang_manager),
            ThumbnailWidget(lang_manager=mock_lang_manager),
            ProgressTracker(lang_manager=mock_lang_manager)
        ]
        
        # All components should have same language manager
        for component in components:
            assert component.get_language_manager() == mock_lang_manager
    
    @patch('ui.components.widgets.thumbnail_widget.QNetworkAccessManager')
    def test_thumbnail_loading_integration(self, mock_network, qapp, mock_lang_manager):
        """Test thumbnail loading with network mock"""
        widget = ThumbnailWidget(lang_manager=mock_lang_manager)
        
        # Test URL loading
        test_url = "https://example.com/thumbnail.jpg"
        widget.load_thumbnail(test_url)
        
        assert widget.current_url == test_url
        assert widget.is_loading()
    
    def test_component_cleanup(self, qapp, mock_lang_manager):
        """Test component cleanup and resource management"""
        components = [
            ActionButtonGroup([ButtonConfig(ButtonType.SELECT_ALL, "BUTTON_SELECT_ALL", 150)], 
                            lang_manager=mock_lang_manager),
            StatisticsWidget(lang_manager=mock_lang_manager),
            ThumbnailWidget(lang_manager=mock_lang_manager),
            ProgressTracker(lang_manager=mock_lang_manager)
        ]
        
        # Test cleanup methods exist
        for component in components:
            if hasattr(component, 'cleanup_subscriptions'):
                component.cleanup_subscriptions()
            if hasattr(component, 'cleanup'):
                component.cleanup()

# Performance Tests
class TestComponentPerformance:
    """Test component performance characteristics"""
    
    def test_large_dataset_statistics(self, qapp, mock_lang_manager):
        """Test statistics widget with large dataset"""
        # Create large dataset
        large_dataset = []
        for i in range(1000):
            large_dataset.append({
                'title': f'Video {i}',
                'size': f'{i % 100} MB',
                'download_date': f'2025-01-{(i % 30) + 1:02d}',
                'url': f'https://example.com/video{i}'
            })
        
        widget = StatisticsWidget(lang_manager=mock_lang_manager)
        
        # Time the update
        import time
        start_time = time.time()
        widget.update_statistics(large_dataset)
        end_time = time.time()
        
        # Should complete in reasonable time (< 1 second)
        assert end_time - start_time < 1.0
        assert widget.get_statistics().total_videos == 1000
    
    def test_event_bus_performance(self, qapp):
        """Test event bus performance with many subscribers"""
        bus = get_event_bus()
        callbacks = []
        
        # Create many subscribers
        for i in range(100):
            def callback(event, i=i):
                pass
            callbacks.append(callback)
            bus.subscribe(EventType.DATA_UPDATED, callback)
        
        # Time event emission
        import time
        start_time = time.time()
        for i in range(100):
            bus.emit_event(EventType.DATA_UPDATED, "test", {"data": i})
        end_time = time.time()
        
        # Should complete in reasonable time
        assert end_time - start_time < 1.0

# Mock Integration Tests
class TestMockIntegration:
    """Test components with mocked dependencies"""
    
    @patch('ui.components.widgets.thumbnail_widget.QNetworkAccessManager')
    def test_thumbnail_network_failure(self, mock_network, qapp, mock_lang_manager):
        """Test thumbnail widget network failure handling"""
        widget = ThumbnailWidget(lang_manager=mock_lang_manager)
        
        # Mock network failure
        widget._on_thumbnail_failed("test_url", "Network error")
        
        assert not widget.is_loading()
        assert widget.current_url == "test_url"
    
    def test_statistics_with_invalid_data(self, qapp, mock_lang_manager):
        """Test statistics widget with invalid data"""
        widget = StatisticsWidget(lang_manager=mock_lang_manager)
        
        # Test with invalid data
        invalid_data = [
            {'title': 'Test', 'size': 'invalid', 'download_date': None},
            {'title': 'Test2'},  # Missing fields
            None,  # Null entry
        ]
        
        # Should handle gracefully
        widget.update_statistics(invalid_data)
        stats = widget.get_statistics()
        assert stats.total_videos == 3  # Still counts entries
        assert stats.total_size == "0 MB"  # Invalid sizes default to 0

if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"]) 