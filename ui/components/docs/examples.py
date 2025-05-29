"""
UI Components Usage Examples

Practical examples demonstrating how to use and integrate components
in real-world scenarios.
"""

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt

# Example imports (would be actual imports in real usage)
from ui.components.tables import VideoTable, FilterableVideoTable
from ui.components.widgets import PlatformSelector, FilterPopup, ProgressTracker
from ui.components.common import ComponentStateManager, ComponentThemeManager
from ui.components.mixins import LanguageSupport, ThemeSupport, StatefulComponentMixin


# =============================================================================
# Example 1: Basic Video Table Setup
# =============================================================================

def example_basic_video_table():
    """Basic video table with sample data"""
    
    # Create table
    table = VideoTable()
    
    # Configure columns
    columns = [
        {"key": "title", "label": "Title", "width": 300, "sortable": True},
        {"key": "platform", "label": "Platform", "width": 100, "filterable": True},
        {"key": "duration", "label": "Duration", "width": 80, "format": "time"},
        {"key": "upload_date", "label": "Upload Date", "width": 120, "format": "date"}
    ]
    table.set_columns(columns)
    
    # Sample data
    video_data = [
        {
            "title": "How to Build UI Components",
            "platform": "youtube", 
            "duration": 1800,
            "upload_date": "2024-01-15",
            "view_count": 50000
        },
        {
            "title": "Python Tutorial Series",
            "platform": "youtube",
            "duration": 2400, 
            "upload_date": "2024-01-10",
            "view_count": 75000
        },
        {
            "title": "Quick Coding Tips",
            "platform": "tiktok",
            "duration": 60,
            "upload_date": "2024-01-20", 
            "view_count": 25000
        }
    ]
    
    # Set data and show
    table.set_data(video_data)
    table.show()
    
    return table


# =============================================================================
# Example 2: Filterable Table with Advanced Features
# =============================================================================

def example_filterable_table():
    """Filterable table with presets and custom filters"""
    
    # Create filterable table
    table = FilterableVideoTable()
    
    # Add filter presets
    table.add_filter_preset("Recent Videos", {
        "date_range": "last_week",
        "platforms": ["youtube", "tiktok"]
    })
    
    table.add_filter_preset("Long Form Content", {
        "min_duration": 600,  # 10 minutes
        "platforms": ["youtube"]
    })
    
    table.add_filter_preset("Viral Content", {
        "min_views": 100000,
        "date_range": "last_month"
    })
    
    # Configure search behavior
    table.configure_search({
        "debounce_ms": 300,
        "search_columns": ["title", "description"],
        "case_sensitive": False
    })
    
    # Set up event handlers
    def on_selection_changed(selected_videos):
        print(f"Selected {len(selected_videos)} videos")
    
    def on_filter_applied(filter_criteria):
        print(f"Applied filters: {filter_criteria}")
    
    table.selection_changed.connect(on_selection_changed)
    table.filter_applied.connect(on_filter_applied)
    
    return table


# =============================================================================
# Example 3: Platform Selector Integration
# =============================================================================

def example_platform_selector():
    """Platform selector with different modes and URL detection"""
    
    # Create selector in button mode
    selector = PlatformSelector()
    selector.set_mode("buttons")
    
    # Configure platforms
    platforms = [
        {"id": "youtube", "name": "YouTube", "icon": "youtube.png"},
        {"id": "tiktok", "name": "TikTok", "icon": "tiktok.png"}, 
        {"id": "instagram", "name": "Instagram", "icon": "instagram.png"},
        {"id": "twitter", "name": "Twitter", "icon": "twitter.png"}
    ]
    selector.set_platforms(platforms)
    
    # Set up URL detection
    url_patterns = {
        "youtube": r"(youtube\.com|youtu\.be)",
        "tiktok": r"tiktok\.com",
        "instagram": r"instagram\.com",
        "twitter": r"(twitter\.com|x\.com)"
    }
    selector.set_url_patterns(url_patterns)
    
    # Event handlers
    def on_platform_changed(platform_id):
        print(f"Platform changed to: {platform_id}")
        # Update other components based on platform
    
    def on_url_detected(url, detected_platform):
        print(f"Detected {detected_platform} URL: {url}")
        selector.set_selected_platform(detected_platform)
    
    selector.platform_changed.connect(on_platform_changed)
    selector.url_detected.connect(on_url_detected)
    
    return selector


# =============================================================================
# Example 4: Component with State Management
# =============================================================================

class ExampleComponent(QWidget, StatefulComponentMixin):
    """Example component with state management"""
    
    def __init__(self):
        super().__init__(enable_state_management=True)
        self.setup_ui()
        self.setup_state_management()
    
    def setup_ui(self):
        """Setup the UI elements"""
        layout = QVBoxLayout()
        
        # Add components
        self.video_table = FilterableVideoTable()
        self.platform_selector = PlatformSelector()
        self.progress_tracker = ProgressTracker()
        
        layout.addWidget(self.platform_selector)
        layout.addWidget(self.video_table)
        layout.addWidget(self.progress_tracker)
        
        self.setLayout(layout)
    
    def setup_state_management(self):
        """Configure state management"""
        
        # Initial state
        initial_state = {
            "selected_platform": "youtube",
            "table_filters": {},
            "selected_videos": [],
            "download_progress": {}
        }
        self.set_component_state(initial_state)
        
        # Connect component events to state updates
        self.platform_selector.platform_changed.connect(self.on_platform_changed)
        self.video_table.selection_changed.connect(self.on_selection_changed)
        self.video_table.filter_applied.connect(self.on_filters_changed)
    
    def on_platform_changed(self, platform):
        """Handle platform selection change"""
        state = self.get_component_state()
        state["selected_platform"] = platform
        self.update_component_state(state)
        
        # Update table data based on platform
        self.load_platform_videos(platform)
    
    def on_selection_changed(self, selected_videos):
        """Handle video selection change"""
        state = self.get_component_state()
        state["selected_videos"] = [v["id"] for v in selected_videos]
        self.update_component_state(state)
    
    def on_filters_changed(self, filters):
        """Handle filter changes"""
        state = self.get_component_state()
        state["table_filters"] = filters
        self.update_component_state(state)
    
    def load_platform_videos(self, platform):
        """Load videos for selected platform"""
        # In real implementation, this would fetch data
        sample_data = [
            {"id": "1", "title": f"{platform.title()} Video 1", "platform": platform},
            {"id": "2", "title": f"{platform.title()} Video 2", "platform": platform}
        ]
        self.video_table.set_data(sample_data)


# =============================================================================
# Example 5: Theme-Aware Component
# =============================================================================

class ThemedComponent(QWidget, ThemeSupport):
    """Component that responds to theme changes"""
    
    def __init__(self):
        super().__init__(theme_enabled=True)
        self.setup_ui()
        self.apply_current_theme()
    
    def setup_ui(self):
        """Setup UI elements"""
        layout = QVBoxLayout()
        
        self.video_table = VideoTable()
        self.platform_selector = PlatformSelector()
        
        layout.addWidget(self.platform_selector)
        layout.addWidget(self.video_table)
        
        self.setLayout(layout)
    
    def on_theme_changed(self, theme_name):
        """Handle theme changes"""
        print(f"Applying theme: {theme_name}")
        
        # Get theme manager
        theme_manager = ComponentThemeManager()
        
        # Apply theme to child components
        theme_manager.apply_theme_to_component(
            self.video_table, "TABLE", "NORMAL"
        )
        theme_manager.apply_theme_to_component(
            self.platform_selector, "SELECTOR", "NORMAL"
        )
        
        # Update component stylesheet
        css = theme_manager.generate_component_css("WIDGET", "NORMAL")
        self.setStyleSheet(css)
        
        # Force repaint
        self.update()


# =============================================================================
# Example 6: Component Testing
# =============================================================================

def example_component_testing():
    """Demonstrate component testing"""
    
    from ui.components.testing import ComponentTester, WidgetTester
    from ui.components.testing import create_simple_test_case, test_widget_quickly
    
    # Create components to test
    table = VideoTable()
    selector = PlatformSelector()
    
    # Quick widget testing
    table_result = test_widget_quickly(table, "Video Table Basic Test")
    selector_result = test_widget_quickly(selector, "Platform Selector Test")
    
    print(f"Table test: {'PASSED' if table_result.passed else 'FAILED'}")
    print(f"Selector test: {'PASSED' if selector_result.passed else 'FAILED'}")
    
    # Detailed testing
    tester = ComponentTester()
    
    def test_platform_selection():
        selector.set_selected_platform("youtube")
        assert selector.get_selected_platform() == "youtube"
        
        selector.set_selected_platform("tiktok")  
        assert selector.get_selected_platform() == "tiktok"
    
    test_case = create_simple_test_case(
        "test_platform_selection", 
        test_platform_selection
    )
    
    result = tester.run_test_case(test_case)
    print(f"Platform selection test: {'PASSED' if result.passed else 'FAILED'}")


# =============================================================================
# Example 7: Full Integration Example
# =============================================================================

class VideoManagerWidget(QWidget, LanguageSupport, ThemeSupport, StatefulComponentMixin):
    """Complete example showing all features together"""
    
    def __init__(self):
        super().__init__(
            supported_languages=["en", "vi", "fr"],
            theme_enabled=True,
            enable_state_management=True
        )
        self.setup_ui()
        self.setup_integrations()
    
    def setup_ui(self):
        """Setup the main UI"""
        layout = QVBoxLayout()
        
        # Create components
        self.platform_selector = PlatformSelector()
        self.video_table = FilterableVideoTable() 
        self.progress_tracker = ProgressTracker()
        
        # Add to layout
        layout.addWidget(self.platform_selector)
        layout.addWidget(self.video_table)
        layout.addWidget(self.progress_tracker)
        
        self.setLayout(layout)
    
    def setup_integrations(self):
        """Setup component integrations"""
        
        # State management
        initial_state = {
            "platform": "youtube",
            "videos": [],
            "selected": [],
            "filters": {},
            "progress": {}
        }
        self.set_component_state(initial_state)
        
        # Connect signals
        self.platform_selector.platform_changed.connect(self.on_platform_changed)
        self.video_table.selection_changed.connect(self.on_video_selection)
        self.video_table.filter_applied.connect(self.on_filter_applied)
        
        # Setup accessibility
        from ui.components.common import get_accessibility_manager
        accessibility = get_accessibility_manager()
        
        accessibility.register_component(
            "platform_selector", 
            self.platform_selector,
            role="combobox",
            label=self.tr("Select Platform")
        )
        
        accessibility.register_component(
            "video_table",
            self.video_table, 
            role="table",
            label=self.tr("Video List")
        )
    
    def on_platform_changed(self, platform):
        """Handle platform change"""
        state = self.get_component_state()
        state["platform"] = platform
        self.update_component_state(state)
        
        # Load platform-specific videos
        self.load_videos_for_platform(platform)
    
    def on_video_selection(self, videos):
        """Handle video selection"""
        state = self.get_component_state()
        state["selected"] = [v["id"] for v in videos]
        self.update_component_state(state)
    
    def on_filter_applied(self, filters):
        """Handle filter application"""
        state = self.get_component_state()
        state["filters"] = filters
        self.update_component_state(state)
    
    def on_language_changed(self, language):
        """Handle language change"""
        # Update all text content
        self.platform_selector.retranslate_ui()
        self.video_table.retranslate_ui()
        self.progress_tracker.retranslate_ui()
    
    def on_theme_changed(self, theme):
        """Handle theme change"""
        # Apply theme to all child components
        theme_manager = ComponentThemeManager()
        
        theme_manager.apply_theme_to_component(
            self.platform_selector, "SELECTOR", "NORMAL"
        )
        theme_manager.apply_theme_to_component(
            self.video_table, "TABLE", "NORMAL"
        )
        theme_manager.apply_theme_to_component(
            self.progress_tracker, "PROGRESS", "NORMAL"
        )
    
    def load_videos_for_platform(self, platform):
        """Load videos for the selected platform"""
        # In real app, this would fetch from API/database
        sample_videos = [
            {
                "id": f"{platform}_1",
                "title": f"Sample {platform.title()} Video 1",
                "platform": platform,
                "duration": 180,
                "upload_date": "2024-01-15"
            },
            {
                "id": f"{platform}_2", 
                "title": f"Sample {platform.title()} Video 2",
                "platform": platform,
                "duration": 240,
                "upload_date": "2024-01-12"
            }
        ]
        
        self.video_table.set_data(sample_videos)


# =============================================================================
# Example Application
# =============================================================================

def create_example_app():
    """Create example application showing all components"""
    
    app = QApplication([])
    
    # Create main window
    window = QMainWindow()
    window.setWindowTitle("UI Components Example")
    window.setGeometry(100, 100, 1200, 800)
    
    # Create and set central widget
    central_widget = VideoManagerWidget()
    window.setCentralWidget(central_widget)
    
    # Show window
    window.show()
    
    return app, window


if __name__ == "__main__":
    # Run example application
    app, window = create_example_app()
    app.exec() 