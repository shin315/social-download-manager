"""
Downloaded Videos Tab - Migrated to Component Architecture

This is the migrated version of downloaded_videos_tab.py that now inherits from BaseTab
and integrates with the component system established in Task 15 and enhanced in Task 16.

Migration preserves all existing functionality while adding:
- Tab lifecycle management
- State persistence and recovery
- Component bus integration
- Enhanced theme and language support
- Better error handling and validation
"""

from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QTableWidget, QHeaderView,
                             QTableWidgetItem, QMessageBox, QFrame, QScrollArea, QApplication, QDialog, QTextEdit, QCheckBox,
                             QMenu, QDialogButtonBox, QToolTip, QAbstractItemView,
                             QStyledItemDelegate, QSizePolicy, QListWidget, QListWidgetItem,
                             QFileDialog)
from PyQt6.QtCore import Qt, QSize, QTimer, QPoint, QEvent, pyqtSignal, QCoreApplication
from PyQt6.QtGui import QPixmap, QCursor, QIcon, QColor, QPainter, QPen, QMouseEvent, QAction
import os
import subprocess
import math
import unicodedata
from datetime import datetime
import json
import sqlite3
import re
import logging
from typing import List, Dict, Any, Optional

# Import the new component architecture
from ..common import (
    BaseTab, TabConfig, TabState, 
    TabEventHelper, TabPerformanceMonitor,
    tab_lifecycle_handler, auto_save_on_change, validate_before_action,
    create_standard_tab_config, setup_tab_logging, connect_tab_to_state_manager
)
from ..tables.video_table import VideoTable
# from ..widgets.video_details import VideoDetailsWidget  # TODO: Create this widget
from utils.db_manager import DatabaseManager


class FilterPopup(QMenu):
    """Menu popup for filtering column values"""
    filterChanged = pyqtSignal(int, str)  # Signal emitted when filter changes (column_index, selected_value)
    
    def __init__(self, parent=None, column_index=0, unique_values=None, header_text=""):
        super().__init__(parent)
        
        self.column_index = column_index
        self.unique_values = unique_values or []
        self.header_text = header_text
        
        # Create actions for each unique value
        self.create_filter_items()
        
    def create_filter_items(self):
        """Create a list of unique values for filtering"""
        # Add "Clear Filter" option at the top of the menu
        all_action = self.addAction("Clear Filter")
        all_action.triggered.connect(lambda: self.apply_filter(None))
        
        self.addSeparator()
        
        # Add unique values to the menu
        for value in sorted(self.unique_values):
            display_value = str(value) if value is not None else "Empty"
            action = self.addAction(display_value)
            # Use lambda with default value to avoid closure issues
            action.triggered.connect(lambda checked=False, val=value: self.apply_filter(val))
    
    def apply_filter(self, value):
        """Apply filter for the selected value"""
        # Emit signal with the selected value (None = all)
        self.filterChanged.emit(self.column_index, value)
        self.close()


class DownloadedVideosTab(BaseTab):
    """
    Downloaded Videos Tab with Component Architecture Integration
    
    This tab manages downloaded videos with advanced features:
    - State persistence and recovery
    - Component bus integration for inter-tab communication
    - Enhanced filtering and sorting
    - Theme and language support through mixins
    - Performance monitoring and validation
    """
    
    # Tab-specific signals (in addition to BaseTab signals)
    video_selected = pyqtSignal(dict)  # Emitted when a video is selected
    video_deleted = pyqtSignal(str)    # Emitted when a video is deleted
    filter_changed = pyqtSignal(dict)  # Emitted when filters change
    
    def __init__(self, config: Optional[TabConfig] = None, parent=None):
        """Initialize the downloaded videos management tab"""
        
        # Create default config if none provided
        if config is None:
            config = create_standard_tab_config(
                tab_id="downloaded_videos",
                title_key="TAB_DOWNLOADED_VIDEOS",
                auto_save=True,
                validation_required=True,
                state_persistence=True
            )
        
        # Initialize tab-specific state variables BEFORE super().__init__()
        self.parent = parent  # Reference to MainWindow
        self.all_videos = []  # List of all downloaded videos
        self.filtered_videos = []  # List of filtered videos
        self.selected_video = None  # Currently selected video
        self.sort_column = 7  # Default sort by download date (descending)
        self.sort_order = Qt.SortOrder.DescendingOrder  # Default sort order is descending
        
        # Column indices
        self.select_col = 0
        self.title_col = 1
        self.creator_col = 2
        self.quality_col = 3
        self.format_col = 4
        self.size_col = 5
        self.status_col = 6
        self.date_col = 7
        self.hashtags_col = 8
        self.actions_col = 9
        
        # Filter storage variables
        self.active_filters = {}  # {column_index: [allowed_values]}
        
        # Initialize base tab
        super().__init__(config, parent)
        
        print(f"DEBUG: Initial sort_column={self.sort_column}, sort_order={self.sort_order}")
    
    def get_tab_id(self) -> str:
        """Return unique tab identifier"""
        return "downloaded_videos"
    
    def setup_ui(self) -> None:
        """Initialize the tab's UI components"""
        # Main layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Search section
        search_layout = QHBoxLayout()
        
        # Search label
        self.search_label = QLabel(self.tr_("Search:"))
        search_layout.addWidget(self.search_label)
        
        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.tr_("Search downloaded videos..."))
        self.search_input.textChanged.connect(self.filter_videos)
        search_layout.addWidget(self.search_input, 1)
        
        main_layout.addLayout(search_layout)
        
        # Downloaded videos table
        self.create_downloads_table()
        main_layout.addWidget(self.downloads_table)
        
        # Video details area
        self.create_video_details_area()
        main_layout.addWidget(self.video_details_frame)
        
        # Hide video details area by default
        self.video_details_frame.setVisible(False)

        # Statistics layout
        stats_layout = QHBoxLayout()
        stats_layout.setContentsMargins(0, 8, 0, 0)  # Create space with top part
        
        # Create frame to hold statistics with floating effect
        self.stats_frame = QFrame()
        self.stats_frame.setObjectName("statsFrame")
        stats_frame_layout = QHBoxLayout(self.stats_frame)
        stats_frame_layout.setContentsMargins(15, 10, 15, 10)
        
        # Create box to hold statistics information
        stats_box = QHBoxLayout()
        stats_box.setSpacing(20)  # Space between information items
        
        # Total videos
        self.total_videos_label = QLabel("Total videos: 0")
        stats_box.addWidget(self.total_videos_label)
        
        # Total size
        self.total_size_label = QLabel("Total size: 0 MB")
        stats_box.addWidget(self.total_size_label)
        
        # Last download
        self.last_download_label = QLabel("Last download: N/A")
        stats_box.addWidget(self.last_download_label)
        
        # Add to layout of frame
        stats_frame_layout.addLayout(stats_box)
        stats_frame_layout.addStretch(1)
        
        # Select/Unselect All button
        self.select_toggle_btn = QPushButton(self.tr_("Select All"))
        self.select_toggle_btn.clicked.connect(self.toggle_select_all)
        stats_frame_layout.addWidget(self.select_toggle_btn)
        
        # Delete Selected button
        self.delete_selected_btn = QPushButton(self.tr_("Delete Selected"))
        self.delete_selected_btn.clicked.connect(self.delete_selected_videos)
        stats_frame_layout.addWidget(self.delete_selected_btn)
        
        # Refresh button
        self.refresh_btn = QPushButton(self.tr_("Refresh"))
        self.refresh_btn.clicked.connect(self.refresh_downloads)
        stats_frame_layout.addWidget(self.refresh_btn)
        
        # Add frame to main layout
        stats_layout.addWidget(self.stats_frame)
        main_layout.addLayout(stats_layout)
        
        # Connect click outside event
        self.downloads_table.viewport().installEventFilter(self)
        
        # Set up context menu for downloaded videos table
        self.downloads_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.downloads_table.customContextMenuRequested.connect(self.show_context_menu)
        
        # Update initial button states
        self.update_button_states()

        # Đảm bảo không hiển thị mũi tên chỉ báo sắp xếp
        if hasattr(self, 'downloads_table') and self.downloads_table:
            self.downloads_table.horizontalHeader().setSortIndicatorShown(False)
            self.downloads_table.setSortingEnabled(False)

    def create_downloads_table(self):
        """Create table for displaying downloaded videos"""
        # Create table widget
        self.downloads_table = QTableWidget()
        self.downloads_table.setObjectName("downloads_table")
        
        # Configure table properties
        self.downloads_table.setColumnCount(10)  # Include selection column
        
        # Set header labels
        header_labels = [
            "",  # Selection checkbox
            "Title",
            "Creator",
            "Quality",
            "Format",
            "Size",
            "Status",
            "Date",
            "Hashtags",
            "Actions"
        ]
        self.downloads_table.setHorizontalHeaderLabels(header_labels)
        
        # Style header - bỏ bold font để tiết kiệm không gian
        header_font = self.downloads_table.horizontalHeader().font()
        header_font.setBold(False)  # Bỏ in đậm để tiết kiệm không gian
        self.downloads_table.horizontalHeader().setFont(header_font)
        
        # Set custom column widths
        self.downloads_table.setColumnWidth(self.select_col, 30)     # Checkbox column
        self.downloads_table.setColumnWidth(self.title_col, 225)     # Increased title from 220 to 225
        self.downloads_table.setColumnWidth(self.creator_col, 100)   # Keep at 100
        self.downloads_table.setColumnWidth(self.quality_col, 85)    # Reduced from 100 to 85 (just enough for "Quality")
        self.downloads_table.setColumnWidth(self.format_col, 75)     # Increased from 70 to 75 for better display
        self.downloads_table.setColumnWidth(self.size_col, 75)       # Increased from 70 to 75 for better display
        self.downloads_table.setColumnWidth(self.status_col, 80)     # Keep at 80
        self.downloads_table.setColumnWidth(self.date_col, 120)      # Keep at 120
        self.downloads_table.setColumnWidth(self.hashtags_col, 100)  # Keep at 100
        self.downloads_table.setColumnWidth(self.actions_col, 130)   # Keep at 130
        
        # Set row selection mode
        self.downloads_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.downloads_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        
        # Set resize mode for columns
        self.downloads_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Select
        self.downloads_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Title - Stretch
        self.downloads_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Creator
        self.downloads_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)  # Quality
        self.downloads_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # Format
        self.downloads_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)  # Size
        self.downloads_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)  # Status
        self.downloads_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)  # Date
        self.downloads_table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)  # Hashtags
        self.downloads_table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeMode.Fixed)  # Actions
        
        # Show sort indicator
        self.downloads_table.horizontalHeader().setSortIndicatorShown(False)  # Changed from True to False
        # Set initial sort indicator to match sort_column and sort_order
        print(f"DEBUG: Setting initial sort indicator - column={self.sort_column}, order={self.sort_order}")
        self.downloads_table.horizontalHeader().setSortIndicator(self.sort_column, self.sort_order)
        print(f"DEBUG: After setting sort indicator - indicator section={self.downloads_table.horizontalHeader().sortIndicatorSection()}, indicator order={self.downloads_table.horizontalHeader().sortIndicatorOrder()}")
        
        # Enable sorting on the table itself
        self.downloads_table.setSortingEnabled(True)
        print(f"DEBUG: Enabled Qt automatic sorting")
        
        # Allow clicking on header to sort
        self.downloads_table.horizontalHeader().setSectionsClickable(True)
        # Connect header click event to sort method
        self.downloads_table.horizontalHeader().sectionClicked.connect(self.sort_table)
        
        # Connect selection changed event instead of itemClicked
        # Use safer way to disconnect signal
        try:
            self.downloads_table.itemClicked.disconnect()
        except (TypeError, RuntimeError):
            # Signal not yet connected or already disconnected
            pass
        
        # Connect table click event to new handler method
        self.downloads_table.cellClicked.connect(self.handle_cell_clicked)
        
        # Connect selection changed event to update details
        self.downloads_table.selectionModel().selectionChanged.connect(self.handle_selection_changed)
        
        # Connect double-click event to display copy dialog
        self.downloads_table.itemDoubleClicked.connect(self.show_copy_dialog)
        
        # Enable mouse tracking to display tooltip on hover
        self.downloads_table.setMouseTracking(True)
        self.downloads_table.cellEntered.connect(self.show_full_text_tooltip)
        
        # Set up header context menu for filters
        self.downloads_table.horizontalHeader().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.downloads_table.horizontalHeader().customContextMenuRequested.connect(self.show_header_context_menu)
        
        # Add tooltip for filterable headers
        filterable_columns = [3, 4, 6, 7]  # Quality, Format, Status, Date
        
        # Set tooltips for filterable columns
        for i in filterable_columns:
            header_item = self.downloads_table.horizontalHeaderItem(i)
            if header_item:
                tooltip_text = f"Right-click to filter by {header_item.text()}"
                header_item.setToolTip(tooltip_text)
        
        # Set style for table
        self.downloads_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #444444;
                border: none;
                background-color: #2a2a2a;
                selection-background-color: #3D5A80;
                selection-color: white;
            }
            QTableWidget::item:selected {
                background-color: #0078d7;
            }
            QHeaderView::section {
                background-color: #2D2D2D;
                color: white;
                border: 1px solid #444444;
                padding: 4px;
            }
            QHeaderView::section:hover {
                background-color: #3D5A80;
                border: 1px solid #6F9CEB;
            }
            QHeaderView::section:checked {
                background-color: #3D5A80;
            }
        """)
        
        # Reset row count
        self.downloads_table.setRowCount(0)
        
        # Set focus policy to receive keyboard events
        self.downloads_table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocusProxy(self.downloads_table)
        
        # Install event filter to handle clicks outside the table
        self.installEventFilter(self)

    def create_video_details_area(self):
        """Create area to display detailed video information"""
        self.video_details_frame = QFrame()
        self.video_details_frame.setStyleSheet("""
            QFrame {
                background-color: #202020;
                border-radius: 8px;
                margin-top: 10px;
            }
        """)
        
        # Main layout for details area
        details_layout = QHBoxLayout(self.video_details_frame)
        details_layout.setContentsMargins(15, 15, 15, 15)
        
        # Thumbnail area (left side)
        thumbnail_frame = QFrame()
        thumbnail_frame.setFixedSize(150, 150)
        thumbnail_frame.setStyleSheet("background-color: transparent; border: none;")
        
        # Stack layout to overlay play icon on thumbnail
        stack_layout = QVBoxLayout(thumbnail_frame)
        stack_layout.setContentsMargins(0, 0, 0, 0)
        
        # Thumbnail
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(150, 150)
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setStyleSheet("background-color: #303030; border-radius: 8px;")
        self.thumbnail_label.setCursor(Qt.CursorShape.PointingHandCursor)  # Change cursor on hover
        
        # Remove tooltip for thumbnail
        self.thumbnail_label.setToolTip("")
        self.thumbnail_label.setToolTipDuration(0)  # Disable tooltip
        
        # Connect click event on thumbnail
        self.thumbnail_label.mousePressEvent = self.thumbnail_click_event
        
        # Play icon (overlaid on thumbnail)
        self.play_icon = QLabel()
        self.play_icon.setText("▶️")  # Unicode play symbol
        self.play_icon.setStyleSheet("font-size: 52px; color: white; background-color: transparent;")
        self.play_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.play_icon.setFixedSize(150, 150)
        
        # Add thumbnail and play icon to stack layout
        stack_layout.addWidget(self.thumbnail_label)
        stack_layout.addWidget(self.play_icon)
        
        # Set stacking order
        self.thumbnail_label.raise_()
        self.play_icon.raise_()
        
        details_layout.addWidget(thumbnail_frame)
        
        # Video info area (right side)
        info_layout = QVBoxLayout()
        
        # Video title
        self.video_title_label = QLabel("Video Title")
        self.video_title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        info_layout.addWidget(self.video_title_label)
        
        # Creator
        self.video_creator_label = QLabel("Creator: Unknown")
        self.video_creator_label.setStyleSheet("color: #CCCCCC;")
        info_layout.addWidget(self.video_creator_label)
        
        # Quality and format
        quality_format_layout = QHBoxLayout()
        self.video_quality_label = QLabel("Quality: Unknown")
        self.video_format_label = QLabel("Format: Unknown")
        self.video_quality_label.setStyleSheet("color: #CCCCCC;")
        self.video_format_label.setStyleSheet("color: #CCCCCC;")
        quality_format_layout.addWidget(self.video_quality_label)
        quality_format_layout.addWidget(self.video_format_label)
        quality_format_layout.addStretch()
        info_layout.addLayout(quality_format_layout)
        
        # Size and date
        size_date_layout = QHBoxLayout()
        self.video_size_label = QLabel("Size: Unknown")
        self.video_date_label = QLabel("Downloaded: Unknown")
        self.video_size_label.setStyleSheet("color: #CCCCCC;")
        self.video_date_label.setStyleSheet("color: #CCCCCC;")
        size_date_layout.addWidget(self.video_size_label)
        size_date_layout.addWidget(self.video_date_label)
        size_date_layout.addStretch()
        info_layout.addLayout(size_date_layout)
        
        # Path
        self.video_path_label = QLabel("Path: Unknown")
        self.video_path_label.setStyleSheet("color: #CCCCCC; font-family: monospace;")
        self.video_path_label.setWordWrap(True)
        info_layout.addWidget(self.video_path_label)
        
        # Add stretch to push content to top
        info_layout.addStretch()
        
        details_layout.addLayout(info_layout)
    
    @tab_lifecycle_handler('load_data')
    def load_data(self) -> None:
        """Load tab-specific data"""
        try:
            self.load_downloaded_videos()
        except Exception as e:
            print(f"Error loading data: {e}")
    
    def save_data(self) -> bool:
        """Save tab data, return success status"""
        try:
            # No specific save needed for downloaded videos tab - data is in database
            return True
        except Exception as e:
            print(f"Error saving data: {e}")
            return False
    
    def refresh_data(self) -> None:
        """Refresh/reload tab data"""
        try:
            self.load_downloaded_videos()
        except Exception as e:
            print(f"Error refreshing data: {e}")
    
    def validate_input(self) -> List[str]:
        """Validate tab input, return list of error messages"""
        errors = []
        
        # Check if database connection is available
        try:
            db_manager = DatabaseManager()
            if not db_manager.connection:
                errors.append("Database connection not available")
        except Exception as e:
            errors.append(f"Database error: {e}")
        
        return errors
    
    def load_downloaded_videos(self):
        """Load downloaded videos from database"""
        try:
            # Clear existing data
            self.all_videos.clear()
            self.filtered_videos.clear()
            
            # Load from database
            db_manager = DatabaseManager()
            videos = db_manager.get_all_videos()
            
            if videos:
                self.all_videos = videos
                self.filtered_videos = videos.copy()
                print(f"Loaded {len(videos)} videos from database")
            else:
                print("No videos found in database")
            
            # Update display
            self.display_videos()
            self.update_statistics()
            
        except Exception as e:
            print(f"Error loading videos: {e}")
            # Show error to user
            if self.parent():
                QMessageBox.warning(
                    self.parent(),
                    "Error Loading Videos",
                    f"Failed to load videos: {e}"
                )

    def display_videos(self, videos=None):
        """Display videos in table"""
        if videos is None:
            videos = self.filtered_videos
        
        # Set row count
        self.downloads_table.setRowCount(len(videos))
        
        for row, video in enumerate(videos):
            # Checkbox column
            checkbox = QCheckBox()
            checkbox.stateChanged.connect(self.checkbox_state_changed)
            self.downloads_table.setCellWidget(row, self.select_col, checkbox)
            
            # Title
            title_item = QTableWidgetItem(video.get('title', 'Unknown'))
            title_item.setFlags(title_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.downloads_table.setItem(row, self.title_col, title_item)
            
            # Creator
            creator_item = QTableWidgetItem(video.get('creator', 'Unknown'))
            creator_item.setFlags(creator_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.downloads_table.setItem(row, self.creator_col, creator_item)
            
            # Quality
            quality_item = QTableWidgetItem(video.get('quality', 'Unknown'))
            quality_item.setFlags(quality_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.downloads_table.setItem(row, self.quality_col, quality_item)
            
            # Format
            format_item = QTableWidgetItem(video.get('format', 'Unknown'))
            format_item.setFlags(format_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.downloads_table.setItem(row, self.format_col, format_item)
            
            # Size
            size = video.get('size', 0)
            size_text = self.format_size(size) if size else 'Unknown'
            size_item = QTableWidgetItem(size_text)
            size_item.setFlags(size_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.downloads_table.setItem(row, self.size_col, size_item)
            
            # Status
            status_item = QTableWidgetItem(video.get('status', 'Downloaded'))
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.downloads_table.setItem(row, self.status_col, status_item)
            
            # Date
            date_item = QTableWidgetItem(video.get('download_date', 'Unknown'))
            date_item.setFlags(date_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.downloads_table.setItem(row, self.date_col, date_item)
            
            # Hashtags
            hashtags = video.get('hashtags', [])
            hashtags_text = ' '.join(hashtags) if hashtags else ''
            hashtags_item = QTableWidgetItem(hashtags_text)
            hashtags_item.setFlags(hashtags_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.downloads_table.setItem(row, self.hashtags_col, hashtags_item)
            
            # Actions
            actions_widget = QFrame()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(5, 0, 5, 0)
            
            open_btn = QPushButton("Open")
            open_btn.clicked.connect(lambda checked, r=row: self.open_folder_and_select(videos[r].get('download_path', ''), r))
            actions_layout.addWidget(open_btn)
            
            delete_btn = QPushButton("Delete")
            delete_btn.clicked.connect(lambda checked, r=row: self.delete_video_and_select(r))
            actions_layout.addWidget(delete_btn)
            
            self.downloads_table.setCellWidget(row, self.actions_col, actions_widget)
        
        # Update button states
        self.update_button_states()

    def format_size(self, size_bytes):
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        size_name = ["B", "KB", "MB", "GB", "TB"]
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"

    def update_statistics(self):
        """Update statistics display"""
        total_videos = len(self.all_videos)
        total_size = sum(video.get('size', 0) for video in self.all_videos)
        total_size_text = self.format_size(total_size)
        
        # Find most recent download
        last_download = "N/A"
        if self.all_videos:
            dates = [video.get('download_date', '') for video in self.all_videos if video.get('download_date')]
            if dates:
                last_download = max(dates)
        
        self.total_videos_label.setText(f"Total videos: {total_videos}")
        self.total_size_label.setText(f"Total size: {total_size_text}")
        self.last_download_label.setText(f"Last download: {last_download}")

    def filter_videos(self):
        """Filter videos based on search text"""
        search_text = self.search_input.text().lower()
        
        if not search_text:
            self.filtered_videos = self.all_videos.copy()
        else:
            self.filtered_videos = []
            for video in self.all_videos:
                # Search in title, creator, and hashtags
                title = video.get('title', '').lower()
                creator = video.get('creator', '').lower()
                hashtags = ' '.join(video.get('hashtags', [])).lower()
                
                if (search_text in title or 
                    search_text in creator or 
                    search_text in hashtags):
                    self.filtered_videos.append(video)
        
        self.display_videos()

    def toggle_select_all(self):
        """Toggle select all checkboxes"""
        # Check current state
        total_checkboxes = self.downloads_table.rowCount()
        if total_checkboxes == 0:
            return
        
        checked_count = 0
        for row in range(total_checkboxes):
            checkbox = self.downloads_table.cellWidget(row, self.select_col)
            if checkbox and checkbox.isChecked():
                checked_count += 1
        
        # If all are checked, uncheck all. Otherwise, check all
        check_state = checked_count < total_checkboxes
        
        for row in range(total_checkboxes):
            checkbox = self.downloads_table.cellWidget(row, self.select_col)
            if checkbox:
                checkbox.setChecked(check_state)
        
        # Update button text
        if check_state:
            self.select_toggle_btn.setText("Unselect All")
        else:
            self.select_toggle_btn.setText("Select All")

    def delete_selected_videos(self):
        """Delete selected videos"""
        selected_rows = []
        for row in range(self.downloads_table.rowCount()):
            checkbox = self.downloads_table.cellWidget(row, self.select_col)
            if checkbox and checkbox.isChecked():
                selected_rows.append(row)
        
        if not selected_rows:
            QMessageBox.information(self, "No Selection", "Please select videos to delete.")
            return
        
        # Confirm deletion
        reply = QMessageBox.question(
            self, 
            "Confirm Deletion", 
            f"Are you sure you want to delete {len(selected_rows)} selected video(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Delete from database and lists
            videos_to_delete = []
            for row in reversed(selected_rows):  # Reverse to maintain indices
                video = self.filtered_videos[row]
                videos_to_delete.append(video)
            
            # Remove from database
            db_manager = DatabaseManager()
            for video in videos_to_delete:
                db_manager.delete_video(video.get('id'))
                # Remove from lists
                if video in self.all_videos:
                    self.all_videos.remove(video)
                if video in self.filtered_videos:
                    self.filtered_videos.remove(video)
            
            # Refresh display
            self.display_videos()
            self.update_statistics()
                
    def refresh_downloads(self):
        """Refresh the downloads list"""
        self.load_downloaded_videos()

    def update_button_states(self):
        """Update button states based on selection"""
        selected_count = 0
        for row in range(self.downloads_table.rowCount()):
            checkbox = self.downloads_table.cellWidget(row, self.select_col)
            if checkbox and checkbox.isChecked():
                selected_count += 1
        
        self.delete_selected_btn.setEnabled(selected_count > 0)
        
        # Update select toggle button text
        total_rows = self.downloads_table.rowCount()
        if selected_count == 0:
            self.select_toggle_btn.setText("Select All")
        elif selected_count == total_rows:
            self.select_toggle_btn.setText("Unselect All")

    def checkbox_state_changed(self):
        """Handle checkbox state change"""
        self.update_button_states()

    # Placeholder methods for advanced functionality
    def thumbnail_click_event(self, event):
        """Handle thumbnail click"""
        pass

    def eventFilter(self, obj, event):
        """Event filter for handling clicks"""
        return super().eventFilter(obj, event)

    def handle_selection_changed(self, selected, deselected):
        """Handle table selection change"""
        pass

    def handle_cell_clicked(self, row, column):
        """Handle table cell click"""
        pass

    def show_copy_dialog(self, item):
        """Show copy dialog"""
        pass

    def show_full_text_tooltip(self, row, column):
        """Show full text tooltip"""
        pass

    def show_header_context_menu(self, pos):
        """Show header context menu"""
        pass

    def show_context_menu(self, position):
        """Show context menu"""
        pass

    def sort_table(self, column):
        """Handle table sorting"""
        pass

    def open_folder_and_select(self, path, row=None):
        """Open folder and select file"""
        if path and os.path.exists(path):
            try:
                if os.name == 'nt':  # Windows
                    subprocess.run(['explorer', '/select,', path])
                elif os.name == 'posix':  # macOS and Linux
                    subprocess.run(['open', '-R', path])
            except Exception as e:
                print(f"Error opening folder: {e}")

    def delete_video_and_select(self, row):
        """Delete video at specific row"""
        if 0 <= row < len(self.filtered_videos):
            video = self.filtered_videos[row]
            
            # Confirm deletion
            reply = QMessageBox.question(
                self,
                "Confirm Deletion",
                f"Are you sure you want to delete '{video.get('title', 'Unknown')}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Remove from database
                db_manager = DatabaseManager()
                db_manager.delete_video(video.get('id'))
                
                # Remove from lists
                if video in self.all_videos:
                    self.all_videos.remove(video)
                if video in self.filtered_videos:
                    self.filtered_videos.remove(video)
                
                # Refresh display
                self.display_videos()
                self.update_statistics() 