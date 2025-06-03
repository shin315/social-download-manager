"""
Statistics Widget

Widget for displaying video statistics like total count, size, last download.
Extracted from downloaded_videos_tab.py update_statistics method.
"""

from typing import List, Any, Dict
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame
from PyQt6.QtCore import pyqtSignal

from ..common.models import StatisticsData
from ..common.interfaces import ComponentInterface, StatisticsInterface
from ..common import QWidgetABCMeta
from ..mixins.language_support import LanguageSupport
from ..mixins.theme_support import ThemeSupport

class StatisticsWidget(QWidget, ComponentInterface, StatisticsInterface,
                      LanguageSupport, ThemeSupport, metaclass=QWidgetABCMeta):
    """Widget for displaying video statistics"""
    
    statistics_updated = pyqtSignal(StatisticsData)
    
    def __init__(self, parent=None, lang_manager=None):
        QWidget.__init__(self, parent)
        ComponentInterface.__init__(self)
        StatisticsInterface.__init__(self)
        LanguageSupport.__init__(self, "StatisticsWidget", lang_manager)
        ThemeSupport.__init__(self, "StatisticsWidget")
        
        self._current_statistics = StatisticsData()
        self.setup_ui()
    
    def setup_ui(self):
        """Initialize the statistics widget UI"""
        # Create frame to hold statistics with floating effect
        self.stats_frame = QFrame()
        self.stats_frame.setObjectName("statsFrame")
        
        # Main layout for the widget
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 8, 0, 0)
        main_layout.addWidget(self.stats_frame)
        
        # Stats frame layout
        stats_frame_layout = QHBoxLayout(self.stats_frame)
        stats_frame_layout.setContentsMargins(15, 10, 15, 10)
        
        # Create statistics box
        stats_box = QHBoxLayout()
        stats_box.setSpacing(20)  # Space between information items
        
        # Total videos label
        self.total_videos_label = QLabel()
        stats_box.addWidget(self.total_videos_label)
        
        # Total size label
        self.total_size_label = QLabel()
        stats_box.addWidget(self.total_size_label)
        
        # Last download label
        self.last_download_label = QLabel()
        stats_box.addWidget(self.last_download_label)
        
        # Filtered count label (optional, hidden by default)
        self.filtered_count_label = QLabel()
        self.filtered_count_label.hide()
        stats_box.addWidget(self.filtered_count_label)
        
        # Selected count label (optional, hidden by default)
        self.selected_count_label = QLabel()
        self.selected_count_label.hide()
        stats_box.addWidget(self.selected_count_label)
        
        # Add to frame layout
        stats_frame_layout.addLayout(stats_box)
        stats_frame_layout.addStretch(1)
        
        # Initialize display
        self.update_display()
    
    def update_language(self):
        """Update labels for language changes"""
        self.update_display()
    
    def apply_theme(self, theme: Dict):
        """Apply theme to statistics widget"""
        super().apply_theme(theme)
        
        # Apply theme to frame and labels
        if 'stats_frame_style' in theme:
            self.stats_frame.setStyleSheet(theme['stats_frame_style'])
        
        if 'stats_label_style' in theme:
            for label in [self.total_videos_label, self.total_size_label, 
                         self.last_download_label, self.filtered_count_label,
                         self.selected_count_label]:
                label.setStyleSheet(theme['stats_label_style'])
    
    def update_statistics(self, data: List[Any]):
        """Update statistics based on video data"""
        if not data:
            self._current_statistics = StatisticsData()
        else:
            self._current_statistics = self._calculate_statistics(data)
        
        self.update_display()
        self.statistics_updated.emit(self._current_statistics)
    
    def _calculate_statistics(self, videos: List[Any]) -> StatisticsData:
        """Calculate statistics from video data"""
        total_videos = len(videos)
        total_size_bytes = 0
        last_download_date = "N/A"
        
        # Calculate total size and find last download
        for video in videos:
            # Handle different video data structures
            if isinstance(video, dict):
                # Extract size
                size_str = video.get('size', '0')
                size_bytes = self._parse_size_string(size_str)
                total_size_bytes += size_bytes
                
                # Extract download date
                download_date = video.get('download_date') or video.get('date')
                if download_date and (last_download_date == "N/A" or download_date > last_download_date):
                    last_download_date = download_date
            elif hasattr(video, 'size'):
                # Object with size attribute
                size_bytes = self._parse_size_string(getattr(video, 'size', '0'))
                total_size_bytes += size_bytes
                
                # Get download date
                download_date = getattr(video, 'download_date', None) or getattr(video, 'date', None)
                if download_date and (last_download_date == "N/A" or download_date > last_download_date):
                    last_download_date = download_date
        
        # Format total size
        total_size = self._format_size(total_size_bytes)
        
        return StatisticsData(
            total_videos=total_videos,
            total_size=total_size,
            last_download=last_download_date
        )
    
    def _parse_size_string(self, size_str: str) -> int:
        """Parse size string to bytes"""
        if not size_str or size_str == "N/A":
            return 0
        
        try:
            # Remove any non-numeric characters except decimal point
            import re
            size_parts = re.findall(r'[\d.]+', str(size_str))
            if not size_parts:
                return 0
            
            size_value = float(size_parts[0])
            
            # Check for unit
            size_str_upper = str(size_str).upper()
            if 'GB' in size_str_upper:
                return int(size_value * 1024 * 1024 * 1024)
            elif 'MB' in size_str_upper:
                return int(size_value * 1024 * 1024)
            elif 'KB' in size_str_upper:
                return int(size_value * 1024)
            else:
                return int(size_value)  # Assume bytes
        except (ValueError, TypeError):
            return 0
    
    def _format_size(self, size_bytes: int) -> str:
        """Format size in bytes to human readable format"""
        if size_bytes == 0:
            return "0 MB"
        
        # Convert to appropriate unit
        if size_bytes >= 1024 * 1024 * 1024:  # GB
            size_gb = size_bytes / (1024 * 1024 * 1024)
            return f"{size_gb:.1f} GB"
        elif size_bytes >= 1024 * 1024:  # MB
            size_mb = size_bytes / (1024 * 1024)
            return f"{size_mb:.1f} MB"
        elif size_bytes >= 1024:  # KB
            size_kb = size_bytes / 1024
            return f"{size_kb:.1f} KB"
        else:
            return f"{size_bytes} B"
    
    def update_display(self):
        """Update the display labels"""
        stats = self._current_statistics
        
        # Update labels with translated text
        self.total_videos_label.setText(
            self.tr_("LABEL_TOTAL_VIDEOS").format(stats.total_videos)
        )
        self.total_size_label.setText(
            self.tr_("LABEL_TOTAL_SIZE").format(stats.total_size)
        )
        self.last_download_label.setText(
            self.tr_("LABEL_LAST_DOWNLOAD").format(stats.last_download)
        )
        
        # Update optional labels if they have data
        if stats.filtered_count > 0:
            self.filtered_count_label.setText(
                self.tr_("LABEL_FILTERED_COUNT").format(stats.filtered_count)
            )
            self.filtered_count_label.show()
        else:
            self.filtered_count_label.hide()
        
        if stats.selected_count > 0:
            self.selected_count_label.setText(
                self.tr_("LABEL_SELECTED_COUNT").format(stats.selected_count)
            )
            self.selected_count_label.show()
        else:
            self.selected_count_label.hide()
    
    def get_statistics(self) -> StatisticsData:
        """Get current statistics"""
        return self._current_statistics
    
    def set_filtered_count(self, count: int):
        """Set filtered items count"""
        self._current_statistics.filtered_count = count
        self.update_display()
    
    def set_selected_count(self, count: int):
        """Set selected items count"""
        self._current_statistics.selected_count = count
        self.update_display()
    
    def clear_statistics(self):
        """Clear all statistics"""
        self._current_statistics = StatisticsData()
        self.update_display()
    
    def set_custom_statistic(self, label_key: str, value: str):
        """Set a custom statistic (for extensibility)"""
        # Could be extended to support custom statistics
        pass 