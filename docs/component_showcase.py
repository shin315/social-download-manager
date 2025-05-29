"""
Component Showcase

Interactive demonstration of all UI components.
Run this script to see components in action and test their functionality.
"""

import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QPushButton, QTabWidget, QLabel, QTextEdit,
                            QScrollArea, QFrame, QGroupBox, QSpacerItem, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ui.components.common.models import ButtonConfig, ButtonType, StatisticsData
from ui.components.common.events import get_event_bus, EventType
from ui.components.widgets.action_button_group import (ActionButtonGroup, 
                                                       create_download_tab_buttons, 
                                                       create_video_info_tab_buttons)
from ui.components.widgets.statistics_widget import StatisticsWidget
from ui.components.widgets.thumbnail_widget import (ThumbnailWidget, 
                                                   create_small_thumbnail,
                                                   create_medium_thumbnail, 
                                                   create_large_thumbnail)
from ui.components.widgets.progress_tracker import (ProgressTracker,
                                                   create_download_progress_tracker,
                                                   create_simple_progress_tracker,
                                                   create_compact_progress_tracker)

class MockLanguageManager:
    """Mock language manager for demo purposes"""
    
    def __init__(self):
        self.translations = {
            "BUTTON_SELECT_ALL": "Select All",
            "BUTTON_DELETE_SELECTED": "Delete Selected", 
            "BUTTON_DELETE_ALL": "Delete All",
            "BUTTON_REFRESH": "Refresh",
            "BUTTON_DOWNLOAD": "Download",
            "LABEL_TOTAL_VIDEOS": "Total Videos: {}",
            "LABEL_TOTAL_SIZE": "Total Size: {}",
            "LABEL_LAST_DOWNLOAD": "Last Download: {}",
            "LABEL_FILTERED_COUNT": "Filtered: {}",
            "LABEL_SELECTED_COUNT": "Selected: {}",
            "THUMBNAIL_PLACEHOLDER": "No Image",
            "THUMBNAIL_LOADING": "Loading...",
            "THUMBNAIL_ERROR": "Error",
            "PROGRESS_COMPLETED": "Completed",
            "PROGRESS_READY": "Ready"
        }
    
    def tr(self, key):
        return self.translations.get(key, key)

class ComponentShowcase(QMainWindow):
    """Main showcase window"""
    
    def __init__(self):
        super().__init__()
        self.lang_manager = MockLanguageManager()
        self.current_theme = self.get_light_theme()
        
        self.setWindowTitle("Component Showcase - Social Download Manager")
        self.setGeometry(100, 100, 1200, 800)
        
        self.setup_ui()
        self.setup_demo_data()
        self.setup_timers()
        
    def setup_ui(self):
        """Setup the main UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Title
        title_label = QLabel("Component Architecture Showcase")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; margin: 10px;")
        main_layout.addWidget(title_label)
        
        # Theme toggle buttons
        theme_layout = QHBoxLayout()
        self.light_theme_btn = QPushButton("Light Theme")
        self.dark_theme_btn = QPushButton("Dark Theme")
        self.light_theme_btn.clicked.connect(self.apply_light_theme)
        self.dark_theme_btn.clicked.connect(self.apply_dark_theme)
        
        theme_layout.addWidget(self.light_theme_btn)
        theme_layout.addWidget(self.dark_theme_btn)
        theme_layout.addStretch()
        main_layout.addLayout(theme_layout)
        
        # Component tabs
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create component tabs
        self.create_button_group_tab()
        self.create_statistics_widget_tab()
        self.create_thumbnail_widget_tab()
        self.create_progress_tracker_tab()
        self.create_integration_demo_tab()
        
        # Event log
        self.create_event_log()
        main_layout.addWidget(self.event_log_frame)
        
        # Setup event logging
        self.setup_event_logging()
    
    def create_button_group_tab(self):
        """Create ActionButtonGroup demonstration tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Description
        desc = QLabel("ActionButtonGroup Components")
        desc.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(desc)
        
        # Factory function examples
        factory_group = QGroupBox("Factory Function Examples")
        factory_layout = QVBoxLayout(factory_group)
        
        # Download tab buttons
        download_label = QLabel("Download Tab Buttons:")
        factory_layout.addWidget(download_label)
        
        self.download_buttons = create_download_tab_buttons(self.lang_manager)
        self.download_buttons.select_all_clicked.connect(
            lambda: self.log_event("Download buttons: Select All clicked")
        )
        self.download_buttons.delete_selected_clicked.connect(
            lambda: self.log_event("Download buttons: Delete Selected clicked")
        )
        self.download_buttons.refresh_clicked.connect(
            lambda: self.log_event("Download buttons: Refresh clicked")
        )
        factory_layout.addWidget(self.download_buttons)
        
        # Video info tab buttons
        info_label = QLabel("Video Info Tab Buttons:")
        factory_layout.addWidget(info_label)
        
        self.info_buttons = create_video_info_tab_buttons(self.lang_manager)
        self.info_buttons.select_all_clicked.connect(
            lambda: self.log_event("Info buttons: Select All clicked")
        )
        self.info_buttons.delete_selected_clicked.connect(
            lambda: self.log_event("Info buttons: Delete Selected clicked")
        )
        self.info_buttons.delete_all_clicked.connect(
            lambda: self.log_event("Info buttons: Delete All clicked")
        )
        factory_layout.addWidget(self.info_buttons)
        
        layout.addWidget(factory_group)
        
        # Custom configuration example
        custom_group = QGroupBox("Custom Configuration Example")
        custom_layout = QVBoxLayout(custom_group)
        
        custom_buttons_config = [
            ButtonConfig(ButtonType.DOWNLOAD, "BUTTON_DOWNLOAD", 120),
            ButtonConfig(ButtonType.REFRESH, "BUTTON_REFRESH", 120),
        ]
        self.custom_buttons = ActionButtonGroup(custom_buttons_config, 
                                               lang_manager=self.lang_manager,
                                               add_stretch=False)
        self.custom_buttons.download_clicked.connect(
            lambda: self.log_event("Custom buttons: Download clicked")
        )
        self.custom_buttons.refresh_clicked.connect(
            lambda: self.log_event("Custom buttons: Refresh clicked")
        )
        custom_layout.addWidget(self.custom_buttons)
        
        # State control buttons
        state_layout = QHBoxLayout()
        enable_btn = QPushButton("Enable All")
        disable_btn = QPushButton("Disable All")
        enable_btn.clicked.connect(self.enable_all_buttons)
        disable_btn.clicked.connect(self.disable_all_buttons)
        state_layout.addWidget(enable_btn)
        state_layout.addWidget(disable_btn)
        custom_layout.addLayout(state_layout)
        
        layout.addWidget(custom_group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "Button Groups")
    
    def create_statistics_widget_tab(self):
        """Create StatisticsWidget demonstration tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Description
        desc = QLabel("StatisticsWidget Component")
        desc.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(desc)
        
        # Statistics widget
        self.stats_widget = StatisticsWidget(lang_manager=self.lang_manager)
        layout.addWidget(self.stats_widget)
        
        # Control buttons
        control_group = QGroupBox("Controls")
        control_layout = QVBoxLayout(control_group)
        
        btn_layout = QHBoxLayout()
        update_btn = QPushButton("Update with Sample Data")
        clear_btn = QPushButton("Clear Statistics")
        large_data_btn = QPushButton("Load Large Dataset")
        
        update_btn.clicked.connect(self.update_sample_statistics)
        clear_btn.clicked.connect(self.clear_statistics)
        large_data_btn.clicked.connect(self.load_large_dataset)
        
        btn_layout.addWidget(update_btn)
        btn_layout.addWidget(clear_btn)
        btn_layout.addWidget(large_data_btn)
        control_layout.addLayout(btn_layout)
        
        # Filter/selection controls
        filter_layout = QHBoxLayout()
        set_filtered_btn = QPushButton("Set Filtered Count (5)")
        set_selected_btn = QPushButton("Set Selected Count (3)")
        
        set_filtered_btn.clicked.connect(lambda: self.stats_widget.set_filtered_count(5))
        set_selected_btn.clicked.connect(lambda: self.stats_widget.set_selected_count(3))
        
        filter_layout.addWidget(set_filtered_btn)
        filter_layout.addWidget(set_selected_btn)
        control_layout.addLayout(filter_layout)
        
        layout.addWidget(control_group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "Statistics")
    
    def create_thumbnail_widget_tab(self):
        """Create ThumbnailWidget demonstration tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Description
        desc = QLabel("ThumbnailWidget Components")
        desc.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(desc)
        
        # Size examples
        size_group = QGroupBox("Different Sizes")
        size_layout = QHBoxLayout(size_group)
        
        # Small thumbnail
        small_label = QLabel("Small (80x60)")
        small_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.small_thumbnail = create_small_thumbnail(lang_manager=self.lang_manager)
        small_container = QVBoxLayout()
        small_container.addWidget(small_label)
        small_container.addWidget(self.small_thumbnail)
        small_widget = QWidget()
        small_widget.setLayout(small_container)
        size_layout.addWidget(small_widget)
        
        # Medium thumbnail
        medium_label = QLabel("Medium (120x90)")
        medium_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.medium_thumbnail = create_medium_thumbnail(lang_manager=self.lang_manager)
        medium_container = QVBoxLayout()
        medium_container.addWidget(medium_label)
        medium_container.addWidget(self.medium_thumbnail)
        medium_widget = QWidget()
        medium_widget.setLayout(medium_container)
        size_layout.addWidget(medium_widget)
        
        # Large thumbnail
        large_label = QLabel("Large (160x120)")
        large_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.large_thumbnail = create_large_thumbnail(lang_manager=self.lang_manager)
        large_container = QVBoxLayout()
        large_container.addWidget(large_label)
        large_container.addWidget(self.large_thumbnail)
        large_widget = QWidget()
        large_widget.setLayout(large_container)
        size_layout.addWidget(large_widget)
        
        layout.addWidget(size_group)
        
        # State demonstration
        state_group = QGroupBox("State Demonstration")
        state_layout = QHBoxLayout(state_group)
        
        # State thumbnails
        self.placeholder_thumb = ThumbnailWidget(lang_manager=self.lang_manager)
        self.loading_thumb = ThumbnailWidget(lang_manager=self.lang_manager)
        self.error_thumb = ThumbnailWidget(lang_manager=self.lang_manager)
        
        self.placeholder_thumb.set_placeholder()
        self.loading_thumb.set_loading_state()
        self.error_thumb.set_error_state()
        
        state_layout.addWidget(QLabel("Placeholder:"))
        state_layout.addWidget(self.placeholder_thumb)
        state_layout.addWidget(QLabel("Loading:"))
        state_layout.addWidget(self.loading_thumb)
        state_layout.addWidget(QLabel("Error:"))
        state_layout.addWidget(self.error_thumb)
        
        layout.addWidget(state_group)
        
        # Controls
        control_group = QGroupBox("Controls")
        control_layout = QVBoxLayout(control_group)
        
        btn_layout = QHBoxLayout()
        load_btn = QPushButton("Simulate Load")
        clear_btn = QPushButton("Clear All")
        error_btn = QPushButton("Simulate Error")
        
        load_btn.clicked.connect(self.simulate_thumbnail_load)
        clear_btn.clicked.connect(self.clear_thumbnails)
        error_btn.clicked.connect(self.simulate_thumbnail_error)
        
        btn_layout.addWidget(load_btn)
        btn_layout.addWidget(clear_btn)
        btn_layout.addWidget(error_btn)
        control_layout.addLayout(btn_layout)
        
        layout.addWidget(control_group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "Thumbnails")
    
    def create_progress_tracker_tab(self):
        """Create ProgressTracker demonstration tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Description
        desc = QLabel("ProgressTracker Components")
        desc.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(desc)
        
        # Factory examples
        factory_group = QGroupBox("Factory Function Examples")
        factory_layout = QVBoxLayout(factory_group)
        
        # Download progress tracker
        download_label = QLabel("Download Progress Tracker:")
        factory_layout.addWidget(download_label)
        self.download_progress = create_download_progress_tracker(lang_manager=self.lang_manager)
        factory_layout.addWidget(self.download_progress)
        
        # Simple progress tracker
        simple_label = QLabel("Simple Progress Tracker:")
        factory_layout.addWidget(simple_label)
        self.simple_progress = create_simple_progress_tracker(lang_manager=self.lang_manager)
        factory_layout.addWidget(self.simple_progress)
        
        # Compact progress tracker
        compact_label = QLabel("Compact Progress Tracker:")
        factory_layout.addWidget(compact_label)
        self.compact_progress = create_compact_progress_tracker(lang_manager=self.lang_manager)
        factory_layout.addWidget(self.compact_progress)
        
        layout.addWidget(factory_group)
        
        # Controls
        control_group = QGroupBox("Controls")
        control_layout = QVBoxLayout(control_group)
        
        # Progress controls
        progress_layout = QHBoxLayout()
        start_btn = QPushButton("Start Progress")
        pause_btn = QPushButton("Set to 50%")
        complete_btn = QPushButton("Complete")
        error_btn = QPushButton("Set Error")
        reset_btn = QPushButton("Reset")
        
        start_btn.clicked.connect(self.start_progress)
        pause_btn.clicked.connect(self.set_progress_50)
        complete_btn.clicked.connect(self.complete_progress)
        error_btn.clicked.connect(self.set_progress_error)
        reset_btn.clicked.connect(self.reset_progress)
        
        progress_layout.addWidget(start_btn)
        progress_layout.addWidget(pause_btn)
        progress_layout.addWidget(complete_btn)
        progress_layout.addWidget(error_btn)
        progress_layout.addWidget(reset_btn)
        control_layout.addLayout(progress_layout)
        
        # Indeterminate mode
        indeterminate_layout = QHBoxLayout()
        indeterminate_btn = QPushButton("Toggle Indeterminate Mode")
        indeterminate_btn.clicked.connect(self.toggle_indeterminate)
        indeterminate_layout.addWidget(indeterminate_btn)
        control_layout.addLayout(indeterminate_layout)
        
        layout.addWidget(control_group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "Progress")
    
    def create_integration_demo_tab(self):
        """Create integration demonstration tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Description
        desc = QLabel("Component Integration Demo")
        desc.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(desc)
        
        # Mock video list
        video_group = QGroupBox("Mock Video Download Interface")
        video_layout = QVBoxLayout(video_group)
        
        # Action buttons
        self.integration_buttons = create_download_tab_buttons(self.lang_manager)
        self.integration_buttons.select_all_clicked.connect(self.integration_select_all)
        self.integration_buttons.delete_selected_clicked.connect(self.integration_delete_selected)
        self.integration_buttons.refresh_clicked.connect(self.integration_refresh)
        video_layout.addWidget(self.integration_buttons)
        
        # Statistics
        self.integration_stats = StatisticsWidget(lang_manager=self.lang_manager)
        video_layout.addWidget(self.integration_stats)
        
        # Progress tracker
        self.integration_progress = create_download_progress_tracker(lang_manager=self.lang_manager)
        video_layout.addWidget(self.integration_progress)
        
        # Thumbnail
        thumb_layout = QHBoxLayout()
        thumb_layout.addWidget(QLabel("Sample Thumbnail:"))
        self.integration_thumbnail = create_medium_thumbnail(lang_manager=self.lang_manager)
        thumb_layout.addWidget(self.integration_thumbnail)
        thumb_layout.addStretch()
        video_layout.addLayout(thumb_layout)
        
        layout.addWidget(video_group)
        
        # Integration controls
        control_group = QGroupBox("Integration Controls")
        control_layout = QVBoxLayout(control_group)
        
        btn_layout = QHBoxLayout()
        simulate_download_btn = QPushButton("Simulate Download")
        update_stats_btn = QPushButton("Update Statistics")
        load_thumb_btn = QPushButton("Load Thumbnail")
        
        simulate_download_btn.clicked.connect(self.simulate_download)
        update_stats_btn.clicked.connect(self.update_integration_stats)
        load_thumb_btn.clicked.connect(self.load_integration_thumbnail)
        
        btn_layout.addWidget(simulate_download_btn)
        btn_layout.addWidget(update_stats_btn)
        btn_layout.addWidget(load_thumb_btn)
        control_layout.addLayout(btn_layout)
        
        layout.addWidget(control_group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "Integration")
    
    def create_event_log(self):
        """Create event log widget"""
        self.event_log_frame = QGroupBox("Event Log")
        layout = QVBoxLayout(self.event_log_frame)
        
        self.event_log = QTextEdit()
        self.event_log.setMaximumHeight(150)
        self.event_log.setReadOnly(True)
        layout.addWidget(self.event_log)
        
        # Clear button
        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self.event_log.clear)
        layout.addWidget(clear_btn)
    
    def setup_event_logging(self):
        """Setup event bus logging"""
        bus = get_event_bus()
        
        # Subscribe to all major event types
        events_to_log = [
            EventType.STATE_CHANGED,
            EventType.DATA_UPDATED,
            EventType.LANGUAGE_CHANGED,
            EventType.THEME_CHANGED,
            EventType.PROGRESS_UPDATED,
            EventType.PROGRESS_COMPLETED
        ]
        
        for event_type in events_to_log:
            bus.subscribe(event_type, self.handle_event_log)
    
    def handle_event_log(self, event):
        """Handle event logging"""
        timestamp = event.timestamp.strftime("%H:%M:%S")
        message = f"[{timestamp}] {event.event_type.value} from {event.source_component}"
        if event.data:
            message += f" - {list(event.data.keys())}"
        self.log_event(message)
    
    def log_event(self, message):
        """Add message to event log"""
        self.event_log.append(message)
        self.event_log.verticalScrollBar().setValue(
            self.event_log.verticalScrollBar().maximum()
        )
    
    def setup_demo_data(self):
        """Setup demo data"""
        self.sample_videos = [
            {'title': 'Amazing Video 1', 'size': '45.2 MB', 'download_date': '2025-01-15'},
            {'title': 'Cool Video 2', 'size': '1.8 GB', 'download_date': '2025-01-14'},
            {'title': 'Awesome Video 3', 'size': '892 KB', 'download_date': '2025-01-13'},
            {'title': 'Epic Video 4', 'size': '156 MB', 'download_date': '2025-01-12'},
        ]
        
        self.large_dataset = []
        for i in range(500):
            self.large_dataset.append({
                'title': f'Video {i+1}',
                'size': f'{(i % 100) + 1} MB',
                'download_date': f'2025-01-{(i % 30) + 1:02d}'
            })
    
    def setup_timers(self):
        """Setup timers for animated demos"""
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.update_progress_demo)
        self.progress_value = 0
    
    def get_light_theme(self):
        """Get light theme"""
        return {
            'background_color': '#ffffff',
            'text_color': '#000000',
            'accent_color': '#0078d4',
            'border_color': '#cccccc',
            'hover_color': '#f0f0f0',
            'button_style': 'QPushButton { background-color: #f0f0f0; border: 1px solid #ccc; padding: 5px; }',
            'stats_frame_style': 'QFrame { background-color: #f8f8f8; border: 1px solid #ddd; padding: 10px; }',
            'stats_label_style': 'QLabel { color: #333; }',
            'thumbnail_border_color': '#cccccc',
            'progress_bar_style': 'QProgressBar { border: 1px solid #ccc; }',
            'progress_label_style': 'QLabel { color: #333; }'
        }
    
    def get_dark_theme(self):
        """Get dark theme"""
        return {
            'background_color': '#2b2b2b',
            'text_color': '#ffffff',
            'accent_color': '#0078d4',
            'border_color': '#555555',
            'hover_color': '#404040',
            'button_style': 'QPushButton { background-color: #404040; border: 1px solid #555; color: white; padding: 5px; }',
            'stats_frame_style': 'QFrame { background-color: #333; border: 1px solid #555; padding: 10px; }',
            'stats_label_style': 'QLabel { color: #fff; }',
            'thumbnail_border_color': '#555555',
            'progress_bar_style': 'QProgressBar { border: 1px solid #555; }',
            'progress_label_style': 'QLabel { color: #fff; }'
        }
    
    def apply_light_theme(self):
        """Apply light theme to all components"""
        self.current_theme = self.get_light_theme()
        self.apply_theme_to_components()
        self.log_event("Applied light theme")
    
    def apply_dark_theme(self):
        """Apply dark theme to all components"""
        self.current_theme = self.get_dark_theme()
        self.apply_theme_to_components()
        self.log_event("Applied dark theme")
    
    def apply_theme_to_components(self):
        """Apply current theme to all components"""
        components = [
            self.download_buttons, self.info_buttons, self.custom_buttons,
            self.stats_widget, self.small_thumbnail, self.medium_thumbnail, 
            self.large_thumbnail, self.download_progress, self.simple_progress,
            self.compact_progress, self.integration_buttons, self.integration_stats,
            self.integration_progress, self.integration_thumbnail
        ]
        
        for component in components:
            if hasattr(component, 'apply_theme'):
                component.apply_theme(self.current_theme)
    
    # Button group demo methods
    def enable_all_buttons(self):
        """Enable all buttons in custom group"""
        for button_type in self.custom_buttons.buttons.keys():
            self.custom_buttons.set_button_enabled(button_type, True)
        self.log_event("Enabled all custom buttons")
    
    def disable_all_buttons(self):
        """Disable all buttons in custom group"""
        for button_type in self.custom_buttons.buttons.keys():
            self.custom_buttons.set_button_enabled(button_type, False)
        self.log_event("Disabled all custom buttons")
    
    # Statistics demo methods
    def update_sample_statistics(self):
        """Update statistics with sample data"""
        self.stats_widget.update_statistics(self.sample_videos)
        self.log_event("Updated statistics with sample data")
    
    def clear_statistics(self):
        """Clear statistics"""
        self.stats_widget.clear_statistics()
        self.log_event("Cleared statistics")
    
    def load_large_dataset(self):
        """Load large dataset for performance testing"""
        self.stats_widget.update_statistics(self.large_dataset)
        self.log_event(f"Loaded large dataset ({len(self.large_dataset)} items)")
    
    # Thumbnail demo methods
    def simulate_thumbnail_load(self):
        """Simulate thumbnail loading"""
        thumbnails = [self.small_thumbnail, self.medium_thumbnail, self.large_thumbnail]
        for thumb in thumbnails:
            thumb.set_loading_state()
        
        # Simulate load completion after 2 seconds
        QTimer.singleShot(2000, self.complete_thumbnail_load)
        self.log_event("Simulating thumbnail load...")
    
    def complete_thumbnail_load(self):
        """Complete thumbnail loading simulation"""
        thumbnails = [self.small_thumbnail, self.medium_thumbnail, self.large_thumbnail]
        for thumb in thumbnails:
            thumb.set_placeholder()
        self.log_event("Thumbnail load completed")
    
    def clear_thumbnails(self):
        """Clear all thumbnails"""
        thumbnails = [self.small_thumbnail, self.medium_thumbnail, self.large_thumbnail]
        for thumb in thumbnails:
            thumb.clear_thumbnail()
        self.log_event("Cleared all thumbnails")
    
    def simulate_thumbnail_error(self):
        """Simulate thumbnail error"""
        thumbnails = [self.small_thumbnail, self.medium_thumbnail, self.large_thumbnail]
        for thumb in thumbnails:
            thumb.set_error_state()
        self.log_event("Simulated thumbnail error")
    
    # Progress demo methods
    def start_progress(self):
        """Start progress simulation"""
        self.progress_value = 0
        self.progress_timer.start(100)  # Update every 100ms
        self.log_event("Started progress simulation")
    
    def update_progress_demo(self):
        """Update progress demo"""
        self.progress_value += 2
        
        trackers = [self.download_progress, self.simple_progress, self.compact_progress]
        for tracker in trackers:
            tracker.update_progress(self.progress_value, f"Processing... {self.progress_value}%")
            if hasattr(tracker, 'set_speed'):
                tracker.set_speed(f"{2.5 + (self.progress_value % 10) / 10:.1f} MB/s")
        
        if self.progress_value >= 100:
            self.progress_timer.stop()
            self.log_event("Progress simulation completed")
    
    def set_progress_50(self):
        """Set progress to 50%"""
        trackers = [self.download_progress, self.simple_progress, self.compact_progress]
        for tracker in trackers:
            tracker.update_progress(50, "Halfway there...")
        self.log_event("Set progress to 50%")
    
    def complete_progress(self):
        """Complete progress"""
        trackers = [self.download_progress, self.simple_progress, self.compact_progress]
        for tracker in trackers:
            tracker.set_completed()
        self.log_event("Completed progress")
    
    def set_progress_error(self):
        """Set progress error"""
        trackers = [self.download_progress, self.simple_progress, self.compact_progress]
        for tracker in trackers:
            tracker.set_error("Download failed!")
        self.log_event("Set progress error")
    
    def reset_progress(self):
        """Reset progress"""
        self.progress_timer.stop()
        trackers = [self.download_progress, self.simple_progress, self.compact_progress]
        for tracker in trackers:
            tracker.reset_progress()
        self.log_event("Reset progress")
    
    def toggle_indeterminate(self):
        """Toggle indeterminate mode"""
        trackers = [self.download_progress, self.simple_progress, self.compact_progress]
        is_indeterminate = not trackers[0]._is_indeterminate
        
        for tracker in trackers:
            tracker.set_indeterminate(is_indeterminate)
        
        self.log_event(f"Set indeterminate mode: {is_indeterminate}")
    
    # Integration demo methods
    def integration_select_all(self):
        """Integration demo: select all"""
        self.log_event("Integration: Select All - updating statistics")
        self.integration_stats.set_selected_count(len(self.sample_videos))
    
    def integration_delete_selected(self):
        """Integration demo: delete selected"""
        self.log_event("Integration: Delete Selected - updating statistics")
        self.integration_stats.set_selected_count(0)
    
    def integration_refresh(self):
        """Integration demo: refresh"""
        self.log_event("Integration: Refresh - reloading data")
        self.integration_stats.update_statistics(self.sample_videos)
    
    def simulate_download(self):
        """Simulate a complete download process"""
        self.log_event("Integration: Starting download simulation")
        
        # Reset progress
        self.integration_progress.reset_progress()
        
        # Start progress
        self.integration_download_progress = 0
        self.integration_timer = QTimer()
        self.integration_timer.timeout.connect(self.update_integration_download)
        self.integration_timer.start(200)
    
    def update_integration_download(self):
        """Update integration download progress"""
        self.integration_download_progress += 5
        
        self.integration_progress.update_progress(
            self.integration_download_progress, 
            f"Downloading video... {self.integration_download_progress}%"
        )
        self.integration_progress.set_speed(f"{3.2 + (self.integration_download_progress % 15) / 10:.1f} MB/s")
        
        if self.integration_download_progress >= 100:
            self.integration_timer.stop()
            self.integration_progress.set_completed()
            self.log_event("Integration: Download completed")
            
            # Update statistics
            new_video = {
                'title': f'Downloaded Video {len(self.sample_videos) + 1}',
                'size': '67.8 MB',
                'download_date': '2025-01-16'
            }
            self.sample_videos.append(new_video)
            self.integration_stats.update_statistics(self.sample_videos)
    
    def update_integration_stats(self):
        """Update integration statistics"""
        self.integration_stats.update_statistics(self.sample_videos)
        self.log_event("Integration: Updated statistics")
    
    def load_integration_thumbnail(self):
        """Load integration thumbnail"""
        self.integration_thumbnail.set_loading_state()
        QTimer.singleShot(1500, lambda: self.integration_thumbnail.set_placeholder())
        self.log_event("Integration: Loading thumbnail")

def main():
    """Main function to run the showcase"""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show showcase
    showcase = ComponentShowcase()
    showcase.show()
    
    # Apply initial theme
    showcase.apply_light_theme()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 