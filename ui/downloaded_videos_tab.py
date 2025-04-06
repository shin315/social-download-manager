from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QAbstractItemView, QProgressBar,
                             QCheckBox, QFrame, QScrollArea, QSizePolicy,
                             QComboBox, QLineEdit, QToolBar, QToolButton,
                             QMenu, QDialogButtonBox, QToolTip,
                             QStyledItemDelegate, QListWidget, QListWidgetItem,
                             QFileDialog, QMessageBox, QApplication)
from PyQt6.QtCore import Qt, QSize, QTimer, QPoint, QEvent, pyqtSignal, QCoreApplication
from PyQt6.QtGui import QPixmap, QCursor, QIcon, QColor, QPainter, QPen, QMouseEvent, QAction, QFontMetrics
import os
import subprocess
import math
import unicodedata
from localization import get_language_manager
from utils.db_manager import DatabaseManager
from datetime import datetime
import json
import sqlite3
import re
import logging
import traceback


class FilterPopup(QMenu):
    """Menu popup for filtering column values"""
    filterChanged = pyqtSignal(int, str)  # Signal emitted when filter changes (column_index, selected_value)
    
    def __init__(self, parent=None, column_index=0, unique_values=None, header_text=""):
        super().__init__(parent)
        
        self.column_index = column_index
        self.unique_values = unique_values or []
        self.header_text = header_text
        self.parent = parent
        
        print(f"DEBUG: FilterPopup initialized for column {column_index}, header='{header_text}', values={self.unique_values}")
        
        # Create actions for each unique value
        self.create_filter_items()
        
    def create_filter_items(self):
        """Create a list of unique values for filtering"""
        # Add "Clear Filter" option at the top of the menu
        clear_filter_text = "Clear Filter"
        if hasattr(self.parent, 'tr_'):
            clear_filter_text = self.parent.tr_("FILTER_CLEAR")
            
        all_action = self.addAction(clear_filter_text)
        all_action.triggered.connect(lambda: self.apply_filter(None))
        
        self.addSeparator()
        
        # Add unique values to the menu
        for value in sorted(self.unique_values):
            display_value = str(value) if value is not None else "Empty"
            action = self.addAction(display_value)
            print(f"DEBUG: Adding filter option: '{display_value}'")
            # Use lambda with default value to avoid closure issues
            action.triggered.connect(lambda checked=False, val=value: self.apply_filter(val))
    
    def apply_filter(self, value):
        """Apply filter for the selected value"""
        print(f"DEBUG: FilterPopup.apply_filter called with value='{value}'")
        # Emit signal with the selected value (None = all)
        self.filterChanged.emit(self.column_index, value)
        self.close()

class DownloadedVideosTab(QWidget):
    """Tab for managing downloaded videos"""

    def __init__(self, parent=None):
        """Initialize the downloaded videos management tab"""
        super().__init__(parent)
        
        self.parent = parent  # Reference to MainWindow
        self.lang_manager = parent.lang_manager if parent and hasattr(parent, 'lang_manager') else None
        self.all_videos = []  # List of all downloaded videos
        self.filtered_videos = []  # List of filtered videos
        self.selected_video = None  # Currently selected video
        self.sort_column = 7  # Default sort by download date (descending)
        self.sort_order = Qt.SortOrder.DescendingOrder  # Default sort order is descending
        self.subtitle_info_label = None  # Label to display subtitle information
        self.current_platform = "All"  # Track current platform for UI adjustments
        self._context_menu_active = False  # Flag to track when a context menu is active
        
        # For managing custom column widths
        self.column_resize_timer = None
        self.save_width_timeout = 500  # ms to wait after resizing before saving (prevents saving during drag)
        
        print(f"DEBUG: Initial sort_column={self.sort_column}, sort_order={self.sort_order}")
        
        # Column indices - these will be updated based on platform
        self.select_col = 0
        self.platform_col = 1  # Will be hidden for specific platforms
        self.title_col = 2
        self.creator_col = 3
        self.quality_col = 4
        self.format_col = 5
        self.duration_col = 6
        self.size_col = 7
        self.hashtags_col = -1  # Only used in TikTok view
        self.date_col = 8
        
        # Filter storage variables
        self.active_filters = {}  # {column_index: [allowed_values]}
        
        # Initialize UI
        self.init_ui()
        
        # Load downloaded videos list
        self.load_downloaded_videos()
        
    def tr_(self, key):
        """Translate based on current language"""
        if hasattr(self, 'lang_manager') and self.lang_manager:
            return self.lang_manager.tr(key)
        return key  # Fallback if no language manager
    
    def format_tooltip_text(self, text):
        """Format tooltip text with line breaks for better readability"""
        if not text:
            return ""
        
        # Add line breaks after periods, exclamation marks, question marks followed by a space
        formatted_text = re.sub(r'([.!?]) ', r'\1\n', text)
        # Add line breaks after commas followed by a space
        formatted_text = re.sub(r'([,]) ', r'\1\n', formatted_text)
        
        # Handle hashtags - one hashtag per line
        formatted_text = re.sub(r' (#[^\s#]+)', r'\n\1', formatted_text)
        
        return formatted_text
        
    def update_language(self):
        """Update display language when language changes"""
        # Update title and search label
        self.search_label.setText(self.tr_("LABEL_SEARCH"))
        self.search_input.setPlaceholderText(self.tr_("PLACEHOLDER_SEARCH"))
        
        # Update statistics labels
        self.update_statistics()  # This function will directly update the labels
        
        # Update Select/Unselect All button
        current_text = self.select_toggle_btn.text()
        if current_text == "Select All" or current_text == "Chọn Tất Cả":
            self.select_toggle_btn.setText(self.tr_("BUTTON_SELECT_ALL"))
        else:
            self.select_toggle_btn.setText(self.tr_("BUTTON_UNSELECT_ALL"))
        
        # Update Refresh and Delete Selected buttons
        self.refresh_btn.setText(self.tr_("BUTTON_REFRESH"))
        self.delete_selected_btn.setText(self.tr_("BUTTON_DELETE_SELECTED"))
        
        # Update table headers
        self.update_table_headers()
        
        # Update table contents (need to update buttons in the Action column)
        for row in range(self.downloads_table.rowCount()):
            # Get widget in the Action column
            action_widget = self.downloads_table.cellWidget(row, 9)
            if action_widget:
                # Find buttons in the widget
                for child in action_widget.findChildren(QPushButton):
                    # Update button text
                    if child.text() == "Open" or child.text() == "Mở":
                        child.setText(self.tr_("BUTTON_OPEN"))
                    elif child.text() == "Delete" or child.text() == "Xóa":
                        child.setText(self.tr_("BUTTON_DELETE"))
        
        # Refresh the table to ensure everything is displayed correctly
        self.display_videos()
        
    def update_table_headers(self):
        """Update table headers based on current language"""
        headers = [
            "",  # Select column has no title
            self.tr_("LABEL_PLATFORM"),
            self.tr_("HEADER_TITLE"), 
            self.tr_("HEADER_CREATOR"), 
            self.tr_("HEADER_QUALITY"), 
            self.tr_("HEADER_FORMAT"), 
            self.tr_("HEADER_DURATION"),
            self.tr_("HEADER_SIZE"), 
            self.tr_("HEADER_COMPLETED_ON")
        ]
        self.downloads_table.setHorizontalHeaderLabels(headers)
        
    def update_table_buttons(self):
        """Update buttons in the table"""
        # Removed since there are no buttons in the Actions column anymore
        pass

    def init_ui(self):
        # Main layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Search section
        search_layout = QHBoxLayout()
        
        # Search label
        self.search_label = QLabel(self.tr_("LABEL_SEARCH"))
        search_layout.addWidget(self.search_label)
        
        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.tr_("PLACEHOLDER_SEARCH"))
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
        self.total_videos_label = QLabel(self.tr_("LABEL_TOTAL_VIDEOS").format(0))
        stats_box.addWidget(self.total_videos_label)
        
        # Total size
        self.total_size_label = QLabel(self.tr_("LABEL_TOTAL_SIZE").format("0 MB"))
        stats_box.addWidget(self.total_size_label)
        
        # Last download
        self.last_download_label = QLabel(self.tr_("LABEL_LAST_DOWNLOAD").format("N/A"))
        stats_box.addWidget(self.last_download_label)
        
        # Add to layout of frame
        stats_frame_layout.addLayout(stats_box)
        stats_frame_layout.addStretch(1)
        
        # Select/Unselect All button
        self.select_toggle_btn = QPushButton(self.tr_("BUTTON_SELECT_ALL"))
        self.select_toggle_btn.clicked.connect(self.toggle_select_all)
        stats_frame_layout.addWidget(self.select_toggle_btn)
        
        # Delete Selected button
        self.delete_selected_btn = QPushButton(self.tr_("BUTTON_DELETE_SELECTED"))
        self.delete_selected_btn.clicked.connect(self.delete_selected_videos)
        stats_frame_layout.addWidget(self.delete_selected_btn)
        
        # Refresh button
        self.refresh_btn = QPushButton(self.tr_("BUTTON_REFRESH"))
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

        # Thêm đoạn code này vào cuối phương thức init_ui
        # Đảm bảo không hiển thị mũi tên chỉ báo sắp xếp
        if hasattr(self, 'downloads_table') and self.downloads_table:
            self.downloads_table.horizontalHeader().setSortIndicatorShown(False)
            self.downloads_table.setSortingEnabled(False)

    def create_downloads_table(self):
        """Create table for displaying downloaded videos"""
        self.downloads_table = QTableWidget()
        
        # Set selection style
        self.downloads_table.setAlternatingRowColors(True)
        
        # Set table to fill the available space
        self.downloads_table.horizontalHeader().setStretchLastSection(False)
        
        # Default TikTok view will have hashtags column visible
        # Default view with platform column (use QFlags to set default sort order)
        self.current_platform = ""  # Default is All platforms
        
        # Set up default column indices
        self.select_col = 0
        self.platform_col = 1
        self.title_col = 2
        self.creator_col = 3
        self.quality_col = 4
        self.format_col = 5
        self.duration_col = 6
        self.size_col = 7
        self.hashtags_col = -1  # Not shown by default
        self.date_col = 8
        
        # Initialize sort column/order
        self.sort_column = self.date_col
        self.sort_order = Qt.SortOrder.DescendingOrder
        
        # Configure table for default view
        self.downloads_table.setColumnCount(9)  # 9 columns with platform column by default
        
        # Set header labels
        header_labels = [
            "",  # Selection checkbox
            self.tr_("LABEL_PLATFORM"),
            self.tr_("HEADER_TITLE"),
            self.tr_("HEADER_CREATOR"),
            self.tr_("HEADER_QUALITY"),
            self.tr_("HEADER_FORMAT"),
            self.tr_("HEADER_DURATION"),
            self.tr_("HEADER_SIZE"), 
            self.tr_("HEADER_COMPLETED_ON")
        ]
        self.downloads_table.setHorizontalHeaderLabels(header_labels)
        
        # Set initial column widths
        self.downloads_table.setColumnWidth(self.select_col, 30)      # Checkbox column - keep small
        self.downloads_table.setColumnWidth(self.platform_col, 100)   # Platform column
        self.downloads_table.setColumnWidth(self.title_col, 250)      # Title column - can stretch
        self.downloads_table.setColumnWidth(self.creator_col, 100)    # Creator
        self.downloads_table.setColumnWidth(self.quality_col, 85)     # Quality
        self.downloads_table.setColumnWidth(self.format_col, 75)      # Format
        self.downloads_table.setColumnWidth(self.duration_col, 80)    # Duration
        self.downloads_table.setColumnWidth(self.size_col, 75)        # Size
        self.downloads_table.setColumnWidth(self.date_col, 120)       # Keep at 120
        
        # Set row selection mode
        self.downloads_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.downloads_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        
        # Calculate minimum column widths based on header text
        self.calculate_min_column_widths()
        
        # Set resize mode for columns
        self.downloads_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Select
        self.downloads_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)  # Platform - Interactive
        self.downloads_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Title - Stretch
        self.downloads_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)  # Creator
        self.downloads_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)  # Quality
        self.downloads_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)  # Format
        self.downloads_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive)  # Duration
        self.downloads_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Interactive)  # Size
        self.downloads_table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.Interactive)  # Date
        
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
        
        # Load saved column widths if available
        self.load_column_widths()
        
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
        filterable_columns = [self.platform_col, self.quality_col, self.format_col, self.date_col]  # Platform, Quality, Format, Date
        
        # Set tooltips for filterable columns
        for i in filterable_columns:
            header_item = self.downloads_table.horizontalHeaderItem(i)
            if header_item:
                tooltip_text = self.tr_("TOOLTIP_FILTER_BY").format(header_item.text())
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
        
    def calculate_min_column_widths(self):
        """Calculate minimum column widths based on header text"""
        print("DEBUG: Calculating minimum column widths")
        
        # Get the font metrics to calculate text width
        font_metrics = QFontMetrics(self.downloads_table.font())
        
        # Set padding for different column types
        padding = 30  # Default padding in pixels
        icon_padding = 1  # Additional padding for columns with filter icons
        
        # Get horizontal header
        header = self.downloads_table.horizontalHeader()
        
        # Make sure the minimum width enforcement is in place
        if not header.signalsBlocked():
            try:
                # Disconnect any existing connection to avoid multiple connections
                header.sectionResized.disconnect(self.enforce_min_column_width)
            except:
                pass  # If no connection existed, that's fine
            
            try:
                # Also disconnect save_column_widths_delayed if connected
                header.sectionResized.disconnect(self.save_column_widths_delayed)
            except:
                pass  # If no connection existed, that's fine
            
            # Connect resize signal to our minimum width enforcer
            header.sectionResized.connect(self.enforce_min_column_width)
            
            # Connect resize signal to save column widths after a short delay
            header.sectionResized.connect(self.save_column_widths_delayed)
        
        # Calculate and store minimum width for each column
        for col in range(self.downloads_table.columnCount()):
            header_item = self.downloads_table.horizontalHeaderItem(col)
            if header_item:
                # Get header text
                header_text = header_item.text()
                
                # Calculate text width
                text_width = font_metrics.horizontalAdvance(header_text)
                
                # Add appropriate padding based on column type
                if col == 0:  # Checkbox column
                    min_width = 30  # Fixed width for checkbox column
                elif col in [1, 4, 5, 8]:  # Columns with filter icons (Platform, Quality, Format, Date)
                    min_width = text_width + padding + icon_padding  # Extra padding for filter icon
                else:
                    min_width = text_width + padding
                
                # Store minimum width in header item's user data
                header_item.setData(Qt.ItemDataRole.UserRole, min_width)
                
                # Apply minimum width if current width is smaller
                current_width = self.downloads_table.columnWidth(col)
                if min_width > current_width:
                    print(f"DEBUG: Setting min width for column {col} ({header_text}) from {current_width} to {min_width}")
                    self.downloads_table.setColumnWidth(col, min_width)
                else:
                    print(f"DEBUG: Keeping current width for column {col} ({header_text}): {current_width}")
        
        # Always ensure select column is narrow but visible
        self.downloads_table.setColumnWidth(0, 30)
    
    def enforce_min_column_width(self, column_index, old_size, new_size):
        """Enforce minimum column width when user tries to resize below minimum"""
        header_item = self.downloads_table.horizontalHeaderItem(column_index)
        if header_item:
            # Get the stored minimum width from user data
            min_width = header_item.data(Qt.ItemDataRole.UserRole)
            if min_width and new_size < min_width:
                print(f"DEBUG: Enforcing min width for column {column_index}: {min_width}")
                # Temporarily block signals to avoid recursion
                header = self.downloads_table.horizontalHeader()
                header.blockSignals(True)
                header.resizeSection(column_index, min_width)
                header.blockSignals(False)

    def save_column_widths_delayed(self, column_index, old_size, new_size):
        """Save column widths after a short delay to prevent excessive saving during resize"""
        # If we have an existing timer, stop it
        if self.column_resize_timer and self.column_resize_timer.isActive():
            self.column_resize_timer.stop()
        
        # Create a new timer to save after delay
        if not self.column_resize_timer:
            self.column_resize_timer = QTimer()
            self.column_resize_timer.setSingleShot(True)
            self.column_resize_timer.timeout.connect(self.save_column_widths)
        
        # Start timer - will save column widths after timeout
        self.column_resize_timer.start(self.save_width_timeout)

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
        
        # Detailed information area
        self.info_frame = QFrame()
        self.info_frame.setFrameShape(QFrame.Shape.NoFrame)
        self.info_frame.setStyleSheet("background-color: transparent;")
        
        # Scroll area for detailed information
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("""
            background-color: transparent; 
            border: none;
        """)
        
        # Set style for scrollbar
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                border: none;
                background: rgba(0, 0, 0, 0.1);
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(80, 80, 80, 0.5);
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(80, 80, 80, 0.7);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        # Widget and layout to contain detailed information
        info_content = QWidget()
        info_content.setStyleSheet("background-color: transparent;")
        info_layout = QVBoxLayout(info_content)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(10)  # Increase spacing
        
        # Video title
        self.title_label = QLabel()
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #e6e6e6;")  # Increase font-size
        info_layout.addWidget(self.title_label)
        
        # Grid layout for technical information
        tech_info_layout = QHBoxLayout()
        tech_info_layout.setSpacing(25)  # Increase spacing
        
        # Column 1: Quality, Format, Duration
        tech_col1 = QVBoxLayout()
        tech_col1.setSpacing(8)  # Increase spacing
        self.quality_label = QLabel()
        self.format_label = QLabel()
        self.duration_label = QLabel()
        
        for label in [self.quality_label, self.format_label, self.duration_label]:
            label.setStyleSheet("color: #b3b3b3; font-size: 13px;")  # Add font-size
            tech_col1.addWidget(label)
        
        # Column 2: Size, Date
        tech_col2 = QVBoxLayout()
        tech_col2.setSpacing(8)  # Increase spacing
        self.size_label = QLabel()
        self.date_label = QLabel()
        self.status_label = QLabel()
        
        for label in [self.size_label, self.date_label, self.status_label]:
            label.setStyleSheet("color: #b3b3b3; font-size: 13px;")  # Add font-size
            tech_col2.addWidget(label)
        
        # Add columns to technical layout
        tech_info_layout.addLayout(tech_col1)
        tech_info_layout.addLayout(tech_col2)
        tech_info_layout.addStretch(1)
        
        info_layout.addLayout(tech_info_layout)
        
        # Hashtags
        self.hashtags_label = QLabel()
        self.hashtags_label.setWordWrap(True)
        self.hashtags_label.setStyleSheet("color: #3897f0; font-size: 13px;")
        info_layout.addWidget(self.hashtags_label)
        
        # Folder path
        self.folder_layout = QHBoxLayout()
        folder_icon_label = QLabel("📁")  # Unicode folder icon
        folder_icon_label.setStyleSheet("color: #b3b3b3;")
        self.folder_layout.addWidget(folder_icon_label)
        
        self.folder_label = QLabel()
        self.folder_label.setStyleSheet("color: #b3b3b3; font-size: 12px;")
        self.folder_layout.addWidget(self.folder_label)
        
        # Add Play video button
        self.play_btn = QPushButton("▶️ Play")
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d7;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #1084d9;
            }
            QPushButton:pressed {
                background-color: #0063b1;
            }
        """)
        self.play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.play_btn.clicked.connect(self.play_selected_video)
        self.folder_layout.addWidget(self.play_btn)
        
        self.folder_layout.addStretch(1)
        
        info_layout.addLayout(self.folder_layout)
        
        # Description
        self.desc_label = QLabel()
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("color: #cccccc; font-size: 13px;")
        info_layout.addWidget(self.desc_label)
        
        info_layout.addStretch(1)
        
        # Set widget for scroll area
        scroll_area.setWidget(info_content)
        
        # Add scroll area to frame
        info_frame_layout = QVBoxLayout(self.info_frame)
        info_frame_layout.setContentsMargins(0, 0, 0, 0)
        info_frame_layout.addWidget(scroll_area)
        
        details_layout.addWidget(self.info_frame, 1)  # Stretch factor 1 to expand

    def thumbnail_click_event(self, event):
        """Handle click event on thumbnail"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Play video when left mouse button is clicked
            self.play_selected_video()

    def eventFilter(self, obj, event):
        """Filter events for objects being watched"""
        # Handle events for selected objects
        if obj == self.search_input and event.type() == QEvent.Type.KeyPress:
            # Check if Enter key was pressed 
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                # Prevent default implementation and apply search
                self.filter_videos()
                return True
        
        # Handle mouse press events
        if event.type() == QEvent.Type.MouseButtonPress:
            # Store the mouse button that was pressed
            if hasattr(event, 'button'):
                button_type = "Left" if event.button() == Qt.MouseButton.LeftButton else "Right" if event.button() == Qt.MouseButton.RightButton else "Other"
                print(f"DEBUG: Mouse button pressed: {button_type}")
                
                # If right mouse button pressed, set context menu flag to prevent detail display
                if event.button() == Qt.MouseButton.RightButton:
                    self._context_menu_active = True
                    print("DEBUG: Set context menu active flag from right click")
            
            # Handle clicks outside the downloads table area to clear selection
            if obj == self and self.downloads_table:
                # Get click position
                pos = event.pos()
                # Check if the click is outside the downloads table area
                table_rect = self.downloads_table.geometry()
                if not table_rect.contains(pos):
                    # Clear selection
                    print("DEBUG: Click outside table - clearing selection")
                    self.downloads_table.clearSelection()
                    # Also hide details if visible
                    if hasattr(self, 'video_details_frame') and self.video_details_frame.isVisible():
                        self.video_details_frame.setVisible(False)
                        self.selected_video = None
        
        # Call the base class implementation for standard event handling
        return super().eventFilter(obj, event)

    def handle_selection_changed(self, selected, deselected):
        """Handle event when selection in table changes"""
        # Get selected rows
        indexes = selected.indexes()
        if not indexes:
            return
            
        # Check if this was triggered by a right-click
        # We need to check if a context menu event is in progress
        is_right_click = hasattr(self, '_context_menu_active') and self._context_menu_active
        
        # Show trace message for better debugging
        print(f"DEBUG: Selection changed - Right click: {is_right_click}, Context menu active: {self._context_menu_active}")
        
        # Get row of first selected item
        row = indexes[0].row()
        
        # Display detailed information of video if row is valid and not from right-click
        if row >= 0 and row < len(self.filtered_videos) and not is_right_click:
            video = self.filtered_videos[row]
            
            # Kiểm tra nếu video này đã được chọn trước đó và đang hiển thị chi tiết
            if self.selected_video == video:
                # Nếu hiện tại không hiển thị, thì hiển thị lại
                if not self.video_details_frame.isVisible():
                    self.video_details_frame.setVisible(True)
                    print("DEBUG: Showing details for already selected video")
                # Trường hợp đã hiển thị rồi thì không cần làm gì
            else:
                # Video mới được chọn, cập nhật selected_video và hiển thị chi tiết
                self.selected_video = video
                self.video_details_frame.setVisible(True)
                self.update_selected_video_details(video)
                print("DEBUG: Showing details for newly selected video")
            
    def remove_vietnamese_accents(self, text):
        """Remove Vietnamese accents from a string"""
        if not text:
            return ""
            
        text = str(text)
        
        # Mapping accented characters to non-accented ones
        patterns = {
            '[àáảãạăắằẵặẳâầấậẫẩ]': 'a',
            '[đ]': 'd',
            '[èéẻẽẹêềếểễệ]': 'e',
            '[ìíỉĩị]': 'i',
            '[òóỏõọôồốổỗộơờớởỡợ]': 'o',
            '[ùúủũụưừứửữự]': 'u',
            '[ỳýỷỹỵ]': 'y',
            '[ÀÁẢÃẠĂẮẰẴẶẲÂẦẤẬẪẨ]': 'A',
            '[Đ]': 'D',
            '[ÈÉẺẼẸÊỀẾỂỄỆ]': 'E',
            '[ÌÍỈĨỊ]': 'I',
            '[ÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢ]': 'O',
            '[ÙÚỦŨỤƯỪỨỬỮỰ]': 'U',
            '[ỲÝỶỸỴ]': 'Y'
        }
        
        import re
        for regex, replacement in patterns.items():
            text = re.sub(regex, replacement, text)
            
        return text
        
    def filter_videos(self, skip_platform=False):
        """Filter videos based on search text and active filters"""
        filtered_videos = []
        search_text = self.search_input.text().lower()
        
        # Map from column UI index to data index in filtered_videos
        column_mapping = {
            self.platform_col: 12,  # Platform (index 12 in video_info)
            self.title_col: 0,      # Title (index 0 in video_info)
            self.creator_col: 1,    # Creator (index 1 in video_info)
            self.quality_col: 2,    # Quality (index 2 in video_info)
            self.format_col: 3,     # Format (index 3 in video_info)
            self.duration_col: 10,  # Duration (index 10 in video_info)
            self.size_col: 4,       # Size (index 4 in video_info)
            self.date_col: 6,       # Date (index 6 in video_info)
        }
        
        # Define platform column index outside of conditions
        platform_column_index = 12  # Platform is stored at index 12 in video_info
        
        # Start with all videos if we're not skipping platform filter
        if skip_platform:
            source_videos = self.filtered_videos
        else:
            source_videos = self.all_videos
            
            # If we have a platform filter active and not skipping it
            if platform_column_index in self.active_filters:
                platform = self.active_filters[platform_column_index]
                # Pre-filter by platform
                source_videos = [v for v in source_videos if len(v) > platform_column_index and v[platform_column_index] == platform]
        
        # Apply search filter and column filters
        for video in source_videos:
            # Skip if video doesn't match search filter
            if search_text and not self.video_matches_search(video, search_text):
                continue
                
            # Check column filters
            skip_video = False
            for column_index, filter_value in self.active_filters.items():
                # Skip platform filter if we're already handling it separately
                if skip_platform and column_index == platform_column_index:
                    continue
                
                # Handle date range filter differently
                if column_index == self.date_col and isinstance(filter_value, tuple) and len(filter_value) == 3:
                    # Date range filter has (start_date, end_date, filter_name)
                    start_date, end_date, _ = filter_value
                    
                    # Get the date string for the current video
                    date_str = ""
                    if len(video) > 6:
                        date_str = video[6]  # Date is at index 6
                    
                    # Parse date string to datetime
                    try:
                        print(f"DEBUG Date Filter: Trying to parse date string '{date_str}'")
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                        
                        # Check if date is in range
                        in_range = (start_date <= date_obj <= end_date)
                        print(f"DEBUG Date Filter: Date {date_obj} in range {start_date} to {end_date}: {in_range}")
                        if not in_range:
                            skip_video = True
                            break
                    except Exception as e:
                        print(f"Error parsing date: {e}")
                        skip_video = True
                        break
                else:
                    # Regular column filter - check if value matches
                    # Map UI column index to data index
                    data_index = column_mapping.get(column_index, column_index)
                    
                    if data_index < len(video):
                        cell_value = video[data_index]
                        print(f"DEBUG Filter: Comparing column {column_index}=>{data_index}, value='{cell_value}' with filter='{filter_value}'")
                        if cell_value != filter_value:
                            skip_video = True
                            break
            
            if not skip_video:
                filtered_videos.append(video)
        
        # Update the filtered list
        self.filtered_videos = filtered_videos
        
        # Update the display
        self.display_videos(filtered_videos)
        
        # Update statistics
        self.update_statistics()
        
        # Update video count label
        self.update_video_count_label()

    def is_date_in_range(self, date_string, start_date, end_date):
        """Check if date is within the given time range"""
        from datetime import datetime
        
        if not date_string or date_string == "Unknown":
            return False
            
        try:
            # Convert date string to datetime
            # Try multiple date formats
            video_date = None
            
            # List of possible date formats
            date_formats = [
                "%Y/%m/%d %H:%M",  # YYYY/MM/DD HH:MM
                "%Y/%m/%d",         # YYYY/MM/DD
                "%d/%m/%Y %H:%M",   # DD/MM/YYYY HH:MM
                "%d/%m/%Y",         # DD/MM/YYYY
                "%Y-%m-%d %H:%M",   # YYYY-MM-DD HH:MM
                "%Y-%m-%d",         # YYYY-MM-DD
                "%d-%m-%Y %H:%M",   # DD-MM-YYYY HH:MM
                "%d-%m-%Y"          # DD-MM-YYYY
            ]
            
            # Try each format until successful
            for date_format in date_formats:
                try:
                    video_date = datetime.strptime(date_string, date_format)
                    break  # Exit loop if format matches
                except ValueError:
                    continue
            
            # If date string cannot be parsed
            if video_date is None:
                print(f"Could not parse date string: {date_string}")
                return False
                
            # Check if date is within the time range
            return start_date <= video_date <= end_date
            
        except Exception as e:
            print(f"Error parsing date: {e}")
            return False

    def load_downloaded_videos(self):
        """Load list of downloaded videos from database"""
        try:
            # Create database manager
            db_manager = DatabaseManager()
            
            # Get list of downloaded videos
            downloads = db_manager.get_downloads()
            
            # Clear current list
            self.all_videos = []
            
            # Process each download
            for download in downloads:
                # Extract hashtags from description or separate hashtags column
                hashtags = download.get('hashtags', '')
                if not hashtags and 'description' in download:
                    # Extract hashtags from description
                    description = download.get('description', '')
                    hashtags = ' '.join(re.findall(r'#\w+', description))
                
                # Convert hashtags to proper format if it's a list
                if isinstance(hashtags, list):
                    hashtags_str = ' '.join(['#' + tag for tag in hashtags])
                else:
                    # If already a string, check if it has #
                    hashtags_str = str(hashtags)
                    if hashtags_str and ' ' in hashtags_str and not '#' in hashtags_str:
                        hashtags_str = ' '.join(['#' + tag.strip() for tag in hashtags_str.split()])
                
                # Ensure correct creator information is kept
                creator = download.get('creator', 'Unknown')
                if creator == 'Unknown' and download.get('url', ''):
                    # Extract username from URL if no creator is provided
                    url = download.get('url', '')
                    if '@' in url:
                        creator = url.split('@')[1].split('/')[0]
                
                # Display status in a friendly way
                status = download.get('status', 'Success')
                print(f"DEBUG loading video status initial: {status}")
                if status == 'Success' or status == 'Download successful':
                    status = 'Successful'
                print(f"DEBUG loading video status after conversion: {status}")
                
                # Check and update actual file size
                file_path = download.get('filepath', '')
                file_size = download.get('filesize', 'Unknown')
                db_size_updated = False
                
                if file_path and os.path.exists(file_path):
                    try:
                        size_bytes = os.path.getsize(file_path)
                        size_mb = size_bytes / (1024 * 1024)
                        actual_file_size = f"{size_mb:.2f} MB"
                        
                        # If actual file size differs from value in DB
                        if actual_file_size != file_size:
                            print(f"File size mismatch for {file_path}. DB: {file_size}, Actual: {actual_file_size}")
                            file_size = actual_file_size
                            # Update file size in database
                            if 'id' in download:
                                print(f"Updating filesize by ID: {download['id']}")
                                update_success = db_manager.update_download_filesize(download['id'], actual_file_size)
                                db_size_updated = update_success
                            elif 'url' in download and download['url']:
                                print(f"Updating filesize by URL: {download['url']}")
                                update_success = db_manager.update_download_filesize(download['url'], actual_file_size)
                                db_size_updated = update_success
                            else:
                                print(f"Cannot update filesize - no ID or URL found in download info")
                        # Remove debug message when filesize matches
                    except Exception as e:
                        print(f"Error getting file size: {e}")
                
                # Determine platform from URL or platform field
                platform = download.get('platform', 'Unknown')
                if platform == 'Unknown' and 'url' in download:
                    url = download.get('url', '')
                    if 'tiktok.com' in url:
                        platform = 'TikTok'
                    elif 'youtube.com' in url or 'youtu.be' in url:
                        platform = 'YouTube'
                    elif 'instagram.com' in url:
                        platform = 'Instagram'
                    elif 'facebook.com' in url:
                        platform = 'Facebook'
                
                # Create video info with complete information
                video_info = [
                    download.get('title', 'Unknown'),            # 0 - Title
                    creator,                                     # 1 - Creator
                    download.get('quality', 'Unknown'),          # 2 - Quality
                    download.get('format', 'Unknown'),           # 3 - Format
                    file_size,                                   # 4 - Size (updated)
                    status,                                      # 5 - Status
                    download.get('download_date', 'Unknown'),    # 6 - Date
                    hashtags_str,                                # 7 - Hashtags
                    os.path.dirname(download.get('filepath', '')), # 8 - Folder
                    download.get('description', 'Unknown'),      # 9 - Description
                    download.get('duration', 'Unknown'),         # 10 - Duration
                    download.get('thumbnail', ''),               # 11 - Thumbnail
                    platform                                     # 12 - Platform
                ]
                self.all_videos.append(video_info)
            
            # Update filtered_videos list
            self.filtered_videos = self.all_videos.copy()
            
            # Sort videos based on default sort_column and sort_order
            data_column = 6  # Mapping from UI column 7 (Date) to data index 6
            print(f"DEBUG: load_downloaded_videos - Sorting videos with data_column={data_column}, sort_order={self.sort_order}")
            self.sort_videos(data_column, self.sort_order)
            
            # Display list of videos
            self.display_videos()
            
            # Update statistics
            self.update_statistics()
            
            # Update button states based on whether there are videos
            self.update_button_states()
            
            print(f"Loaded {len(self.all_videos)} videos")
            
        except Exception as e:
            print(f"Error loading downloaded videos: {e}")
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_ERROR").format(str(e)))

    def filter_by_platform(self, platform):
        """Filter videos by platform"""
        print(f"DEBUG: filter_by_platform called with platform = {platform}")
        
        try:
            # Save current platform
            self.current_platform = platform
            
            # Reset table columns based on platform
            if platform == "TikTok":
                print(f"DEBUG: Calling setup_tiktok_table_columns() from filter_by_platform")
                self.setup_tiktok_table_columns()
            elif platform == "YouTube":
                print(f"DEBUG: Calling setup_youtube_table_columns() from filter_by_platform")
                self.setup_youtube_table_columns()
            else:
                print(f"DEBUG: Calling setup_default_table_columns() from filter_by_platform")
                self.setup_default_table_columns()
                
            # Define column index for platform filtering
            platform_column_index = 12  # Platform is stored at index 12 in video_info
            
            # If platform is "All", show all videos
            if platform == "All":
                # Reset any existing platform filter
                if platform_column_index in self.active_filters:
                    del self.active_filters[platform_column_index]
                
                # Apply all other active filters
                self.filter_videos()
                
                print(f"DEBUG: Showing all platforms, total videos: {len(self.filtered_videos)}")
                return
                
            # Apply platform filter
            # Filter videos by platform (all_videos is the source of truth)
            filtered_platform_videos = []
            
            print(f"DEBUG: All videos count: {len(self.all_videos)}")
            # Print platform value for each video for debugging
            for idx, video in enumerate(self.all_videos[:5]):  # Print first 5 for brevity
                platform_value = video[platform_column_index] if len(video) > platform_column_index else "Unknown"
                print(f"DEBUG: Video {idx} platform: {platform_value}")
            
            for video in self.all_videos:
                # Check if video has platform info
                if len(video) > platform_column_index:
                    video_platform = video[platform_column_index]
                    if video_platform == platform:
                        filtered_platform_videos.append(video)
                        
            # Update the active_filters to include platform filter
            self.active_filters[platform_column_index] = platform
            
            # Update filtered_videos list
            self.filtered_videos = filtered_platform_videos
            
            # Apply other active filters
            self.filter_videos(skip_platform=True)
            
            print(f"DEBUG: Filtered to {platform} platform, total videos: {len(self.filtered_videos)}")
            
        except Exception as e:
            print(f"Error filtering videos by platform: {e}")
            print(traceback.format_exc())
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_ERROR").format(str(e)))

    def display_videos(self, videos=None):
        """Display list of downloaded videos in the table"""
        # Check if videos are provided, if not use filtered_videos
        if videos is None:
            videos = self.filtered_videos
            
        # If no videos to display, just clear the table and return
        if not videos:
            self.downloads_table.clearContents()
            self.downloads_table.setRowCount(0)
            self.video_details_frame.hide()
            
            # Cập nhật trạng thái nút khi không có video
            self.update_button_states()
            return
            
        # Disable sorting temporarily to avoid triggering while updating
        was_sorting_enabled = self.downloads_table.isSortingEnabled()
        self.downloads_table.setSortingEnabled(False)
        
        # Print current platform and column count before clearing
        print(f"DEBUG: display_videos - current_platform={self.current_platform}, columnCount={self.downloads_table.columnCount()}")
        
        # Clear table
        self.downloads_table.clearContents()
        self.downloads_table.setRowCount(0)
        
        # Add new rows for each video
        for idx, video in enumerate(videos):
            self.downloads_table.insertRow(idx)
            
            # Select (checkbox) column
            select_widget = QWidget()
            layout = QHBoxLayout(select_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            checkbox = QCheckBox()
            checkbox.setChecked(False)  # Default is not selected
            checkbox.stateChanged.connect(self.checkbox_state_changed)
            layout.addWidget(checkbox)
            
            self.downloads_table.setCellWidget(idx, 0, select_widget)
            
            # Check which platform-specific view to use
            if self.current_platform == "TikTok":
                # TikTok-specific view without platform column
                
                # Title column (index 1 in TikTok view)
                title_item = QTableWidgetItem(video[0])
                # Save full title in UserRole for later use
                if len(video) > 9 and video[9]:
                    title_item.setData(Qt.ItemDataRole.UserRole, video[9])  # Save original_title
                else:
                    title_item.setData(Qt.ItemDataRole.UserRole, video[0])  # Fallback save short title
                # Prefer using full title for tooltip if available
                if len(video) > 9 and video[9]:
                    # Format tooltip more readable with line breaks
                    tooltip_text = self.format_tooltip_text(video[9])
                    title_item.setToolTip(tooltip_text)  # Tooltip with full title formatted
                else:
                    # Format tooltip more readable with line breaks
                    tooltip_text = self.format_tooltip_text(video[0]) 
                    title_item.setToolTip(tooltip_text)  # Fallback with short title formatted
                # Disable editing
                title_item.setFlags(title_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.downloads_table.setItem(idx, self.title_col, title_item)
                
                # Creator column (index 2 in TikTok view)
                creator_item = QTableWidgetItem(video[1])
                creator_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                creator_item.setToolTip(video[1])  # Add tooltip for full text
                # Disable editing
                creator_item.setFlags(creator_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.downloads_table.setItem(idx, self.creator_col, creator_item)
                
                # Quality column (index 3 in TikTok view)
                quality_item = QTableWidgetItem(video[2])
                quality_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                quality_item.setToolTip(video[2])  # Add tooltip for full text
                # Disable editing
                quality_item.setFlags(quality_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.downloads_table.setItem(idx, self.quality_col, quality_item)
                
                # Format column (index 4 in TikTok view)
                format_value = video[3]
                # Ensure correct format is displayed as text (MP4 or MP3)
                if format_value == "1080p" or format_value == "720p" or format_value == "480p" or format_value == "360p" or format_value == "Video (mp4)":
                    format_value = self.tr_("FORMAT_VIDEO_MP4")
                elif format_value == "320kbps" or format_value == "192kbps" or format_value == "128kbps" or format_value == "Audio (mp3)":
                    format_value = self.tr_("FORMAT_AUDIO_MP3")
                # If it's an MP3 file but format is incorrect, fix it
                filepath = os.path.join(video[8], video[0]) if video[8] and video[0] else ""
                if filepath and filepath.lower().endswith('.mp3'):
                    format_value = self.tr_("FORMAT_AUDIO_MP3")
                format_item = QTableWidgetItem(format_value)
                format_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Disable editing
                format_item.setFlags(format_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.downloads_table.setItem(idx, self.format_col, format_item)
                
                # Duration column (index 5 in TikTok view)
                duration_value = video[10] if len(video) > 10 else "Unknown"
                # Format duration in a user-friendly way if it's in seconds
                try:
                    if duration_value and duration_value != "Unknown" and str(duration_value).isdigit():
                        # Convert seconds to MM:SS format
                        duration_secs = int(duration_value)
                        minutes = duration_secs // 60
                        seconds = duration_secs % 60
                        duration_value = f"{minutes}:{seconds:02d}"
                except:
                    pass  # Keep original value if conversion fails
                
                duration_item = QTableWidgetItem(str(duration_value))
                duration_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Disable editing
                duration_item.setFlags(duration_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.downloads_table.setItem(idx, self.duration_col, duration_item)
                
                # Size column (index 6 in TikTok view)
                size_item = QTableWidgetItem(video[4])
                size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Disable editing
                size_item.setFlags(size_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.downloads_table.setItem(idx, self.size_col, size_item)
                
                # Hashtags column (index 7 in TikTok view)
                hashtags_value = video[7] if len(video) > 7 else ""
                # Format hashtags for display (first 3 hashtags, if too many)
                if hashtags_value:
                    # If it's a string that might contain multiple hashtags
                    hashtags_list = []
                    if isinstance(hashtags_value, str):
                        if ' ' in hashtags_value:
                            # Split by space and ensure each has a # prefix
                            hashtags_list = [tag if tag.startswith('#') else f"#{tag}" for tag in hashtags_value.split()]
                        else:
                            # Single hashtag
                            hashtags_list = [hashtags_value if hashtags_value.startswith('#') else f"#{hashtags_value}"]
                    
                    # Show first 3 hashtags and indicate more if truncated
                    if len(hashtags_list) > 3:
                        display_hashtags = " ".join(hashtags_list[:3]) + "..."
                    else:
                        display_hashtags = " ".join(hashtags_list)
                else:
                    display_hashtags = ""
                
                hashtags_item = QTableWidgetItem(display_hashtags)
                # Store full hashtags in user role for filtering/sorting
                hashtags_item.setData(Qt.ItemDataRole.UserRole, hashtags_value)
                hashtags_item.setToolTip(hashtags_value)  # Show full hashtags on hover
                # Disable editing
                hashtags_item.setFlags(hashtags_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.downloads_table.setItem(idx, self.hashtags_col, hashtags_item)
                
                # Date column (index 8 in TikTok view)
                date_string = video[6]
                date_item = QTableWidgetItem(date_string)
                date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Disable editing
                date_item.setFlags(date_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.downloads_table.setItem(idx, self.date_col, date_item)
                
            elif self.current_platform == "YouTube":
                # YouTube-specific view with playlist and release date columns
                print(f"DEBUG: Processing YouTube view for video {idx}")
                
                # Title column (index 1 in YouTube view)
                title_item = QTableWidgetItem(video[0])
                # Save full title in UserRole for later use
                if len(video) > 9 and video[9]:
                    title_item.setData(Qt.ItemDataRole.UserRole, video[9])  # Save original_title
                else:
                    title_item.setData(Qt.ItemDataRole.UserRole, video[0])  # Fallback save short title
                # Prefer using full title for tooltip if available
                if len(video) > 9 and video[9]:
                    # Format tooltip more readable with line breaks
                    tooltip_text = self.format_tooltip_text(video[9])
                    title_item.setToolTip(tooltip_text)  # Tooltip with full title formatted
                else:
                    # Format tooltip more readable with line breaks
                    tooltip_text = self.format_tooltip_text(video[0]) 
                    title_item.setToolTip(tooltip_text)  # Fallback with short title formatted
                # Disable editing
                title_item.setFlags(title_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.downloads_table.setItem(idx, self.title_col, title_item)
                
                # Channel column (index 2 in YouTube view)
                creator_item = QTableWidgetItem(video[1])
                creator_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                creator_item.setToolTip(video[1])  # Add tooltip for full text
                # Disable editing
                creator_item.setFlags(creator_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.downloads_table.setItem(idx, self.creator_col, creator_item)
                
                # Playlist column (index 3 in YouTube view)
                # Extract playlist info from platform_data if available (placeholder for now)
                playlist_value = "N/A"  # Default value
                # In the future, this will extract from platform_data in the database
                
                playlist_item = QTableWidgetItem(playlist_value)
                playlist_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Disable editing
                playlist_item.setFlags(playlist_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.downloads_table.setItem(idx, self.playlist_col, playlist_item)
                
                # Quality column (index 4 in YouTube view)
                quality_item = QTableWidgetItem(video[2])
                quality_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                quality_item.setToolTip(video[2])  # Add tooltip for full text
                # Disable editing
                quality_item.setFlags(quality_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.downloads_table.setItem(idx, self.quality_col, quality_item)
                
                # Format column (index 5 in YouTube view)
                format_value = video[3]
                # Ensure correct format is displayed as text (MP4 or MP3)
                if format_value == "1080p" or format_value == "720p" or format_value == "480p" or format_value == "360p" or format_value == "Video (mp4)":
                    format_value = self.tr_("FORMAT_VIDEO_MP4")
                elif format_value == "320kbps" or format_value == "192kbps" or format_value == "128kbps" or format_value == "Audio (mp3)":
                    format_value = self.tr_("FORMAT_AUDIO_MP3")
                # If it's an MP3 file but format is incorrect, fix it
                filepath = os.path.join(video[8], video[0]) if video[8] and video[0] else ""
                if filepath and filepath.lower().endswith('.mp3'):
                    format_value = self.tr_("FORMAT_AUDIO_MP3")
                format_item = QTableWidgetItem(format_value)
                format_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Disable editing
                format_item.setFlags(format_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.downloads_table.setItem(idx, self.format_col, format_item)
                
                # Duration column (index 6 in YouTube view)
                duration_value = video[10] if len(video) > 10 else "Unknown"
                # Format duration in a user-friendly way if it's in seconds
                try:
                    if duration_value and duration_value != "Unknown" and str(duration_value).isdigit():
                        # Convert seconds to MM:SS format
                        duration_secs = int(duration_value)
                        minutes = duration_secs // 60
                        seconds = duration_secs % 60
                        duration_value = f"{minutes}:{seconds:02d}"
                except:
                    pass  # Keep original value if conversion fails
                
                duration_item = QTableWidgetItem(str(duration_value))
                duration_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Disable editing
                duration_item.setFlags(duration_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.downloads_table.setItem(idx, self.duration_col, duration_item)
                
                # Size column (index 7 in YouTube view)
                size_item = QTableWidgetItem(video[4])
                size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Disable editing
                size_item.setFlags(size_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.downloads_table.setItem(idx, self.size_col, size_item)
                
                # Release Date column (index 8 in YouTube view)
                # Extract release date info from platform_data if available (placeholder for now)
                release_date_value = "N/A"  # Default value
                # In the future, this will extract from upload_date in platform_data in the database
                
                release_date_item = QTableWidgetItem(release_date_value)
                release_date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Disable editing
                release_date_item.setFlags(release_date_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.downloads_table.setItem(idx, self.release_date_col, release_date_item)
                
                # Download Date column (index 9 in YouTube view)
                date_item = QTableWidgetItem(video[6])
                date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Disable editing
                date_item.setFlags(date_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.downloads_table.setItem(idx, self.date_col, date_item)
                
            else:
                # Default view with platform column
                
                # Platform column (index 1 in default view)
                platform_value = video[12] if len(video) > 12 else "Unknown"
                platform_item = QTableWidgetItem(platform_value)
                platform_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Disable editing
                platform_item.setFlags(platform_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.downloads_table.setItem(idx, self.platform_col, platform_item)
                
                # Title column (index 2 in default view)
                title_item = QTableWidgetItem(video[0])
                # Save full title in UserRole for later use
                if len(video) > 9 and video[9]:
                    title_item.setData(Qt.ItemDataRole.UserRole, video[9])  # Save original_title
                else:
                    title_item.setData(Qt.ItemDataRole.UserRole, video[0])  # Fallback save short title
                # Prefer using full title for tooltip if available
                if len(video) > 9 and video[9]:
                    # Format tooltip more readable with line breaks
                    tooltip_text = self.format_tooltip_text(video[9])
                    title_item.setToolTip(tooltip_text)  # Tooltip with full title formatted
                else:
                    # Format tooltip more readable with line breaks
                    tooltip_text = self.format_tooltip_text(video[0]) 
                    title_item.setToolTip(tooltip_text)  # Fallback with short title formatted
                # Disable editing
                title_item.setFlags(title_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.downloads_table.setItem(idx, self.title_col, title_item)
                
                # Creator column (index 3 in default view)
                creator_item = QTableWidgetItem(video[1])
                creator_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Disable editing
                creator_item.setFlags(creator_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.downloads_table.setItem(idx, self.creator_col, creator_item)
                
                # Quality column (index 4 in default view)
                quality_item = QTableWidgetItem(video[2])
                quality_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Disable editing
                quality_item.setFlags(quality_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.downloads_table.setItem(idx, self.quality_col, quality_item)
                
                # Format column (index 5 in default view)
                format_value = video[3]
                # Ensure correct format is displayed as text (MP4 or MP3)
                if format_value == "1080p" or format_value == "720p" or format_value == "480p" or format_value == "360p" or format_value == "Video (mp4)":
                    format_value = self.tr_("FORMAT_VIDEO_MP4")
                elif format_value == "320kbps" or format_value == "192kbps" or format_value == "128kbps" or format_value == "Audio (mp3)":
                    format_value = self.tr_("FORMAT_AUDIO_MP3")
                # If it's an MP3 file but format is incorrect, fix it
                filepath = os.path.join(video[8], video[0]) if video[8] and video[0] else ""
                if filepath and filepath.lower().endswith('.mp3'):
                    format_value = self.tr_("FORMAT_AUDIO_MP3")
                format_item = QTableWidgetItem(format_value)
                format_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Disable editing
                format_item.setFlags(format_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.downloads_table.setItem(idx, self.format_col, format_item)
                
                # Duration column (index 6 in default view)
                duration_value = video[10] if len(video) > 10 else "Unknown"
                # Format duration in a user-friendly way if it's in seconds
                try:
                    if duration_value and duration_value != "Unknown" and str(duration_value).isdigit():
                        # Convert seconds to MM:SS format
                        duration_secs = int(duration_value)
                        minutes = duration_secs // 60
                        seconds = duration_secs % 60
                        duration_value = f"{minutes}:{seconds:02d}"
                except:
                    pass  # Keep original value if conversion fails
                
                duration_item = QTableWidgetItem(str(duration_value))
                duration_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Disable editing
                duration_item.setFlags(duration_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.downloads_table.setItem(idx, self.duration_col, duration_item)
                
                # Size column (index 7 in default view)
                size_item = QTableWidgetItem(video[4])
                size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Disable editing
                size_item.setFlags(size_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.downloads_table.setItem(idx, self.size_col, size_item)
                
                # Date column (index 8 in default view)
                date_string = video[6]
                date_item = QTableWidgetItem(date_string)
                date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Disable editing
                date_item.setFlags(date_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.downloads_table.setItem(idx, self.date_col, date_item)
        
        # Finished adding data to table
        
        # Re-enable sorting if it was enabled previously
        if was_sorting_enabled:
            self.downloads_table.setSortingEnabled(True)
            
        # Update row count and total size
        self.update_statistics()
        
        # Cập nhật trạng thái nút sau khi hiển thị video
        self.update_button_states()
        
        # Restore current selected item (if any)
        if self.selected_video and self.selected_video in videos:
            # Find index of selected video
            try:
                selected_idx = videos.index(self.selected_video)
                # Select row in table
                self.downloads_table.selectRow(selected_idx)
            except ValueError:
                # Video not found in current list, clear selection
                self.selected_video = None
                self.video_details_frame.hide()

    def open_folder_and_select(self, path, row=None):
        """Open folder and select corresponding row"""
        # Select corresponding row
        if row is not None and 0 <= row < self.downloads_table.rowCount():
            self.downloads_table.selectRow(row)
        
        # Open folder
        self.open_folder(path)
    
    def delete_video_and_select(self, row):
        """Delete video and select corresponding row"""
        # Select corresponding row
        if row is not None and 0 <= row < self.downloads_table.rowCount():
            self.downloads_table.selectRow(row)
        
        # Delete video
        self.delete_video(row)

    def open_folder(self, path):
        """
        Open folder containing downloaded video
        If path is a folder: open that folder
        If path is a file: open the folder containing the file and select that file
        """
        print(f"DEBUG - Opening path: '{path}'")
        
        # Determine if path is a file or folder
        is_file = os.path.isfile(path)
        folder_path = os.path.dirname(path) if is_file else path
        
        # Check if directory exists
        if not os.path.exists(folder_path):
            QMessageBox.warning(self, self.tr_("DIALOG_ERROR"), 
                               self.tr_("DIALOG_FOLDER_NOT_FOUND").format(folder_path))
            return
            
        # Open folder and select file (if it's a file)
        try:
            if os.name == 'nt':  # Windows
                if is_file and os.path.exists(path):
                    # Open Explorer and select file using subprocess.Popen (no flashing cmd)
                    path = path.replace('/', '\\')  # Ensure path is in Windows format
                    print(f"DEBUG - Using explorer /select,{path}")
                    
                    # Sử dụng subprocess.Popen thay vì os.system để tránh hiện cửa sổ CMD
                    subprocess.Popen(['explorer', '/select,', path], shell=False, 
                                     creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    # Just open the folder without cmd flashing
                    subprocess.Popen(['explorer', folder_path], shell=False,
                                    creationflags=subprocess.CREATE_NO_WINDOW)
            elif os.name == 'darwin':  # macOS
                if is_file and os.path.exists(path):
                    # Open Finder and select file
                    subprocess.Popen(['open', '-R', path])
                else:
                    # Just open the folder
                    subprocess.Popen(['open', folder_path])
            else:  # Linux and other operating systems
                # Try using common file managers on Linux
                if is_file and os.path.exists(path):
                    # Try with nautilus (GNOME)
                    try:
                        subprocess.Popen(['nautilus', '--select', path])
                    except:
                        try:
                            # Try with dolphin (KDE)
                            subprocess.Popen(['dolphin', '--select', path])
                        except:
                            try:
                                # Try with thunar (XFCE)
                                subprocess.Popen(['thunar', path])
                            except:
                                # If no file manager works, open the folder
                                subprocess.Popen(['xdg-open', folder_path])
                else:
                    # Just open the folder
                    subprocess.Popen(['xdg-open', folder_path])
                    
        except Exception as e:
            print(f"DEBUG - Error opening folder: {str(e)}")
            QMessageBox.warning(self, self.tr_("DIALOG_ERROR"), 
                               self.tr_("DIALOG_CANNOT_OPEN_FOLDER").format(str(e)))

    def delete_video(self, video_idx):
        """Delete downloaded video from list"""
        if video_idx < 0 or video_idx >= len(self.filtered_videos):
            return
            
        print(f"Delete video called with index: {video_idx}")
        print(f"Current filtered_videos length: {len(self.filtered_videos)}")
        
        # Get information of video to delete
        video = self.filtered_videos[video_idx]
        title = video[0]
        file_path = os.path.join(video[8], title + '.' + ('mp3' if video[3] == 'MP3' or 'mp3' in video[3].lower() else 'mp4'))
        file_exists = os.path.exists(file_path)
        
        # Get thumbnail information
        thumbnail_path = video[11] if len(video) > 11 and video[11] else ""
        thumbnail_exists = thumbnail_path and os.path.exists(thumbnail_path)
        
        print(f"Attempting to delete video: {title}")
        
        # Create custom message box with delete file checkbox
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(self.tr_("DIALOG_CONFIRM_DELETION"))
        
        # Remove emoji and details, keep the message simple
        confirmation_text = self.tr_("DIALOG_CONFIRM_DELETE_VIDEO").format(title)
        
        msg_box.setText(confirmation_text)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        msg_box.setIcon(QMessageBox.Icon.Question)
        
        # Set minimum size
        msg_box.setMinimumWidth(500)
        msg_box.setMinimumHeight(200)
        
        # Determine current theme
        current_theme = "dark"
        if hasattr(self, 'parent') and hasattr(self.parent, 'current_theme'):
            current_theme = self.parent.current_theme
        
        # Add style based on theme
        if current_theme == "light":
            light_style = """
                QMessageBox {
                    background-color: #f0f0f0;
                    color: #333333;
                }
                QLabel {
                    color: #333333;
                }
                QPushButton {
                    background-color: #0078d7;
                    color: white;
                    border: none;
                    padding: 6px 12px;
                    margin: 4px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #005fa3;
                }
                QCheckBox {
                    color: #333333;
                }
            """
            msg_box.setStyleSheet(light_style)
        else:
            # Style for message box in dark mode
            dark_style = """
                QMessageBox {
                    background-color: #2d2d2d;
                    color: #e0e0e0;
                }
                QLabel {
                    color: #e0e0e0;
                }
                QPushButton {
                    background-color: #0078d7;
                    color: white;
                    border: none;
                    padding: 6px 12px;
                    margin: 4px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #005fa3;
                }
                QCheckBox {
                    color: #e0e0e0;
                }
            """
            msg_box.setStyleSheet(dark_style)
            
        # Add "Delete file from disk" checkbox
        delete_file_checkbox = QCheckBox(self.tr_("DIALOG_DELETE_FILE_FROM_DISK"))
        delete_file_checkbox.setEnabled(file_exists)
        delete_file_checkbox.setChecked(False)  # Mặc định không chọn để tránh xóa nhầm file
        
        # Find button box to add checkbox in the same row
        button_box = msg_box.findChild(QDialogButtonBox)
        if button_box:
            # Put checkbox to the left of button box
            button_layout = button_box.layout()
            button_layout.insertWidget(0, delete_file_checkbox, 0, Qt.AlignmentFlag.AlignLeft)
            # Add more space between checkbox and buttons
            button_layout.insertSpacing(1, 50)
            # Customize checkbox for better visibility
            delete_file_checkbox.setStyleSheet("QCheckBox { margin-right: 15px; }")
        else:
            # If button box not found, use old method
            checkbox_container = QWidget()
            layout = QHBoxLayout(checkbox_container)
            layout.setContentsMargins(25, 0, 0, 0)
            layout.addWidget(delete_file_checkbox)
            layout.addStretch()
            msg_box.layout().addWidget(checkbox_container, 1, 2)
        
        # Display message box and handle response
        reply = msg_box.exec()
        
        if reply == QMessageBox.StandardButton.Yes:
            print("User confirmed deletion")
            
            # Delete file from disk if checkbox is checked and file exists
            deleted_files_count = 0
            deleted_thumbnails_count = 0
            
            if delete_file_checkbox.isChecked() and file_exists:
                try:
                    os.remove(file_path)
                    print(f"File deleted from disk: {file_path}")
                    deleted_files_count += 1
                    
                    # Delete thumbnail if it exists
                    if thumbnail_exists:
                        try:
                            os.remove(thumbnail_path)
                            print(f"Thumbnail deleted from disk: {thumbnail_path}")
                            deleted_thumbnails_count += 1
                        except Exception as e:
                            print(f"Error deleting thumbnail from disk: {e}")
                    
                except Exception as e:
                    print(f"Error deleting file from disk: {e}")
                    QMessageBox.warning(self, self.tr_("DIALOG_ERROR"), 
                                      self.tr_("DIALOG_CANNOT_DELETE_FILE").format(str(e)))
            
            # Delete from database
            try:
                db_manager = DatabaseManager()
                db_manager.delete_download_by_title(title)
            except Exception as e:
                print(f"Error deleting video from database: {e}")
            
            # Delete from UI list
            deleted_count = 0
            video_to_remove = self.filtered_videos[video_idx]
            if video_to_remove in self.all_videos:
                self.all_videos.remove(video_to_remove)
                deleted_count += 1
            
            if video_to_remove in self.filtered_videos:
                self.filtered_videos.remove(video_to_remove)
            
            # Hide details area if selected video is deleted
            if self.selected_video and self.selected_video[0] == title:
                self.video_details_frame.setVisible(False)
                self.selected_video = None
            
            # Update UI
            self.update_statistics()
            self.display_videos()
            
            # Display notification
            if self.parent:
                if deleted_files_count > 0:
                    self.parent.status_bar.showMessage(self.tr_("STATUS_VIDEOS_AND_FILES_DELETED").format(deleted_count, deleted_files_count))
                    print(f"Deleted {deleted_count} videos, {deleted_files_count} video files, and {deleted_thumbnails_count} thumbnails")
                else:
                    self.parent.status_bar.showMessage(self.tr_("STATUS_VIDEOS_DELETED").format(deleted_count))

    def refresh_downloads(self):
        """Refresh the list of downloaded videos"""
        try:
            # Display refreshing message
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_REFRESHING"))
            
            # Save current platform
            current_platform = self.current_platform
            print(f"DEBUG: Saving current platform before refresh: {current_platform}")
            
            # Clear current filters
            self.active_filters = {}
            self.update_all_filter_icons()
            
            # Clear the filtered_videos list and reload from database
            self.filtered_videos = []
            self.load_downloaded_videos()
            
            # Reset the search input
            self.search_input.clear()
            
            # Check thumbnails for all downloaded videos
            self.check_and_update_thumbnails()
            
            # Re-apply platform filter if needed
            if current_platform and current_platform != "All":
                print(f"DEBUG: Re-applying platform filter: {current_platform}")
                self.filter_by_platform(current_platform)
            else:
                # If current platform is empty string or "All", show all videos
                print(f"DEBUG: Showing all videos (current_platform={current_platform})")
                # Set current_platform properly to "All"
                self.current_platform = "All"
                # Setup default table columns
                self.setup_default_table_columns()
                # Display the newly loaded video list
                self.filtered_videos = self.all_videos.copy()
                self.display_videos()
            
            # Hide video details if currently displayed
            self.video_details_frame.setVisible(False)
            self.selected_video = None
            
            # Update Select All/Unselect All button state
            self.update_select_toggle_button()
            
            # Đảm bảo không hiển thị mũi tên chỉ báo sắp xếp sau khi tải lại dữ liệu
            if hasattr(self, 'downloads_table') and self.downloads_table:
                self.downloads_table.horizontalHeader().setSortIndicatorShown(False)
                self.downloads_table.setSortingEnabled(False)
            
            # Update message in status bar
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_VIDEOS_REFRESHED"))
        except Exception as e:
            print(f"Error refreshing videos: {e}")
            # Show error message in the status bar
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_REFRESH_ERROR"))

    def update_all_filter_icons(self):
        """Update all filter icons on headers"""
        # Clear all filter icons
        filterable_columns = [1, 4, 5, 6, 8]  # Platform, Quality, Format, Duration, Date
        for column_index in filterable_columns:
            self.update_filter_icon(column_index, False)
        
        # Update headers to ensure correct titles
        self.update_table_headers()
        
        # Update tooltips for filterable columns
        for column_index in filterable_columns:
            header_item = self.downloads_table.horizontalHeaderItem(column_index)
            if header_item:
                tooltip_text = self.tr_("TOOLTIP_FILTER_BY").format(header_item.text())
                header_item.setToolTip(tooltip_text)

    def check_and_update_thumbnails(self):
        """Check and update thumbnails for all videos"""
        if not self.all_videos:
            return
            
        db_manager = DatabaseManager()
        for video in self.all_videos:
            # Check if video has thumbnail path and thumbnail exists
            thumbnail_path = video[11] if len(video) > 11 and video[11] else ""
            if not thumbnail_path or not os.path.exists(thumbnail_path):
                # Find video_id from video URL
                video_info = db_manager.get_download_by_title(video[0])
                if not video_info or 'url' not in video_info:
                    continue
                    
                try:
                    video_id = video_info['url'].split('/')[-1].split('?')[0]
                    
                    # Create thumbnails directory if it doesn't exist
                    thumbnails_dir = os.path.join(video[8], "thumbnails")
                    if not os.path.exists(thumbnails_dir):
                        os.makedirs(thumbnails_dir)
                        
                    # Set new thumbnail path
                    new_thumbnail_path = os.path.join(thumbnails_dir, f"{video_id}.jpg")
                    
                    # Update thumbnail path in database
                    metadata_str = video_info.get('metadata', '{}')
                    metadata = json.loads(metadata_str) if metadata_str else {}
                    metadata['thumbnail'] = new_thumbnail_path
                    
                    # Update database
                    conn = sqlite3.connect(db_manager.db_path)
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE downloads SET metadata = ? WHERE title = ?", 
                        (json.dumps(metadata), video[0])
                    )
                    conn.commit()
                    conn.close()
                    
                    print(f"Updated thumbnail path for {video[0]}")
                    
                    # Try creating thumbnail from video or TikTok API if needed
                    # Here we're just updating the path, the thumbnail will be reloaded when needed
                except Exception as e:
                    print(f"Error updating thumbnail for {video[0]}: {e}")

    def add_downloaded_video(self, download_info):
        """Add downloaded video to list"""
        try:
            print(f"DEBUG adding video: Title={download_info.get('title', 'Unknown')}")
            print(f"DEBUG quality={download_info.get('quality', 'Unknown')}, format={download_info.get('format', 'Unknown')}")
            
            # Ensure hashtags are in the correct format
            hashtags = download_info.get('hashtags', [])
            if hashtags:
                if isinstance(hashtags, list):
                    hashtags_str = ' '.join(['#' + tag for tag in hashtags])
                else:
                    hashtags_str = str(hashtags)
                    if ' ' in hashtags_str and not '#' in hashtags_str:
                        hashtags_str = ' '.join(['#' + tag.strip() for tag in hashtags_str.split()])
            else:
                hashtags_str = ""
                
            print(f"DEBUG hashtags={hashtags_str}")
            
            # Get creator information
            creator = download_info.get('creator', 'Unknown')
            # If creator is not provided, try getting it from URL
            if creator == 'Unknown' and download_info.get('url', ''):
                url = download_info.get('url', '')
                if '@' in url:
                    creator = url.split('@')[1].split('/')[0]
            
            # Display status in a friendly way
            status = download_info.get('status', 'Success')
            print(f"DEBUG loading video status initial: {status}")
            if status == 'Success' or status == 'Download successful':
                status = 'Successful'
            print(f"DEBUG loading video status after conversion: {status}")
            
            # Filter out hashtags from title if not filtered
            title = download_info.get('title', 'Unknown')
            original_title = title  # Save original title before processing

            # Process hashtags
            hashtags = download_info.get('hashtags', [])
            if hashtags:
                if isinstance(hashtags, list):
                    hashtags_str = ' '.join(['#' + tag if not tag.startswith('#') else tag for tag in hashtags])
                else:
                    hashtags_str = str(hashtags)
                    if ' ' in hashtags_str and not '#' in hashtags_str:
                        hashtags_str = ' '.join(['#' + tag.strip() for tag in hashtags_str.split()])
            else:
                hashtags_str = ""

            # If there are hashtags but title still contains #, filter out the hashtags from title
            if '#' in title:
                # Extract hashtags from title to ensure no information is lost
                import re
                found_hashtags = re.findall(r'#([^\s#]+)', title)
                if found_hashtags:
                    # Add found hashtags to the list if not already present
                    if isinstance(hashtags, list):
                        for tag in found_hashtags:
                            if tag not in hashtags:
                                hashtags.append(tag)
                    
                    # Update hashtags string
                    if isinstance(hashtags, list):
                        hashtags_str = ' '.join(['#' + tag if not tag.startswith('#') else tag for tag in hashtags])
                    
                    # Remove hashtags and extra spaces from title
                    cleaned_title = re.sub(r'#\S+', '', title).strip()
                    # Remove multiple spaces into one space
                    cleaned_title = re.sub(r'\s+', ' ', cleaned_title).strip()
                    title = cleaned_title
                    
                print(f"DEBUG cleaned title: {title}")

            # Update title in download_info if it's been cleaned
            if title != original_title:
                download_info['title'] = title
                
            # Update hashtags in download_info
            if hashtags_str and isinstance(hashtags, list):
                download_info['hashtags'] = hashtags

            # Save original title to description if not already present
            if not download_info.get('description'):
                download_info['description'] = original_title
            
            # Check and update actual file size
            file_path = download_info.get('filepath', '')
            file_size = download_info.get('filesize', 'Unknown')
            if file_path and os.path.exists(file_path):
                try:
                    size_bytes = os.path.getsize(file_path)
                    size_mb = size_bytes / (1024 * 1024)
                    file_size = f"{size_mb:.2f} MB"
                    # Update file size in download_info to save in DB
                    download_info['filesize'] = file_size
                    print(f"Updated file size for {file_path}: {file_size}")
                except Exception as e:
                    print(f"Error getting file size: {e}")
            
            # Create video info with complete information
            video_info = [
                title,                                           # 0 - Title (hashtags removed)
                creator,                                         # 1 - Creator
                download_info.get('quality', 'Unknown'),         # 2 - Quality
                download_info.get('format', 'Unknown'),          # 3 - Format
                file_size,                                       # 4 - Size (updated)
                status,                                          # 5 - Status
                download_info.get('download_date', 'Unknown'),   # 6 - Date
                hashtags_str,                                    # 7 - Hashtags
                os.path.dirname(download_info.get('filepath', '')), # 8 - Folder
                download_info.get('description', 'Unknown'),     # 9 - Description
                download_info.get('duration', 'Unknown'),        # 10 - Duration
                download_info.get('thumbnail', ''),               # 11 - Thumbnail
                download_info.get('platform', 'Unknown')          # 12 - Platform
            ]
            
            # Add new video to the beginning of the list instead of the end
            self.all_videos.insert(0, video_info)
            
            # Add new video to database
            try:
                db_manager = DatabaseManager()
                db_manager.add_download(download_info)
            except Exception as db_error:
                print(f"Error adding video to database: {db_error}")
            
            # Update filtered_videos list
            if self.search_input.text():
                # Filter new video by current keyword
                search_text = self.search_input.text().lower()
                title = download_info.get('title', '').lower()
                if search_text in title or search_text in hashtags_str.lower():
                    # Add to the beginning of the list
                    self.filtered_videos.insert(0, video_info)
            else:
                # If no search keyword, add directly to the beginning of the list
                self.filtered_videos.insert(0, video_info)
            
            # Display the list again
            self.display_videos()
            
            # Update statistics information
            self.update_statistics()
            
            # Notification
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_VIDEO_ADDED"))
                
            return True
        except Exception as e:
            print(f"Error adding downloaded video: {e}")
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_ADD_VIDEO_ERROR"))
            return False

    def update_statistics(self):
        """Update statistics information"""
        # Update total number of videos
        count = len(self.all_videos) if hasattr(self, 'all_videos') else 0
        self.total_videos_label.setText(self.tr_("LABEL_TOTAL_VIDEOS").format(count))
        
        # Update other statistics
        if hasattr(self, 'all_videos') and self.all_videos:
            # Calculate total size
            try:
                total_size = sum(float(video[4].replace('MB', '').strip()) for video in self.all_videos if isinstance(video[4], str) and 'MB' in video[4])
                self.total_size_label.setText(self.tr_("LABEL_TOTAL_SIZE").format(f"{total_size:.2f} MB"))
            except (ValueError, IndexError):
                self.total_size_label.setText(self.tr_("LABEL_TOTAL_SIZE").format("0 MB"))
            
            # Last download
            try:
                self.last_download_label.setText(self.tr_("LABEL_LAST_DOWNLOAD").format(self.all_videos[-1][6]))
            except (IndexError, TypeError):
                self.last_download_label.setText(self.tr_("LABEL_LAST_DOWNLOAD").format("N/A"))
        else:
            # Update information when there are no videos
            self.total_size_label.setText(self.tr_("LABEL_TOTAL_SIZE").format("0 MB"))
            self.last_download_label.setText(self.tr_("LABEL_LAST_DOWNLOAD").format("N/A"))

    def apply_theme_colors(self, theme):
        """Apply colors according to theme"""
        if theme == "dark":
            # Dark theme
            # Colors for dark mode
            title_color = "#e6e6e6"
            label_color = "#b3b3b3"
            desc_color = "#cccccc"
            hashtag_color = "#3897f0"
            background_color = "#292929"
            audio_background = "#7952b3"
            details_frame_style = "background-color: #2d2d2d;"
            icon_color = "#b3b3b3"
            
            # Style for stats frame - dark mode
            stats_frame_style = """
                #statsFrame {
                    background-color: #2d2d2d;
                    border-radius: 8px;
                    padding: 8px;
                    margin-top: 8px;
                    border: 1px solid #444444;
                }
                #statsFrame QLabel {
                    color: #dddddd;
                    font-weight: 500;
                }
                #statsFrame QPushButton {
                    background-color: #0078d7;
                    color: #ffffff;
                    border: none;
                    padding: 8px 15px;
                    border-radius: 4px;
                }
                #statsFrame QPushButton:hover {
                    background-color: #0086f0;
                }
                #statsFrame QPushButton:pressed {
                    background-color: #0067b8;
                }
            """
            
            # Style for table in dark mode
            table_style = """
                QTableWidget::item:hover {
                    background-color: rgba(80, 140, 255, 0.15);
                }
            """
            
            # Style for scrollbar in dark mode
            scrollbar_style = """
                QScrollBar:vertical {
                    border: none;
                    background: rgba(80, 80, 80, 0.2);
                    width: 8px;
                    margin: 0px;
                    border-radius: 4px;
                }
                QScrollBar::handle:vertical {
                    background: rgba(180, 180, 180, 0.5);
                    min-height: 20px;
                    border-radius: 4px;
                }
                QScrollBar::handle:vertical:hover {
                    background: rgba(180, 180, 180, 0.7);
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: none;
                }
            """
        else:
            # Light theme
            # Colors for light mode
            title_color = "#000000"
            label_color = "#555555"
            desc_color = "#333333"
            hashtag_color = "#0078d7"
            background_color = "#d8d8d8"
            audio_background = "#9966cc"
            details_frame_style = "background-color: #f5f5f5;"
            icon_color = "#555555"
            
            # Style for stats frame - light mode
            stats_frame_style = """
                #statsFrame {
                    background-color: #f5f5f5;
                    border-radius: 8px;
                    padding: 5px;
                    border: 1px solid #dddddd;
                }
                #statsFrame QLabel {
                    font-weight: 500;
                }
            """
            
            # Style for table in light mode
            table_style = """
                QTableWidget::item:hover {
                    background-color: rgba(0, 120, 215, 0.1);
                }
            """
            
            # Style for scrollbar in light mode
            scrollbar_style = """
                QScrollBar:vertical {
                    border: none;
                    background: rgba(0, 0, 0, 0.05);
                    width: 8px;
                    margin: 0px;
                    border-radius: 4px;
                }
                QScrollBar::handle:vertical {
                    background: rgba(0, 0, 0, 0.2);
                    min-height: 20px;
                    border-radius: 4px;
                }
                QScrollBar::handle:vertical:hover {
                    background: rgba(0, 0, 0, 0.3);
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: none;
                }
            """
        
        # Apply style to table
        self.downloads_table.setStyleSheet(table_style)
        
        # Apply style to scrollbar
        self.setStyleSheet(scrollbar_style)
        
        # Apply colors to stats frame
        if hasattr(self, 'stats_frame'):
            self.stats_frame.setStyleSheet(stats_frame_style)
        
        # Apply colors to other components...
        if hasattr(self, 'video_details_frame'):
            self.video_details_frame.setStyleSheet(details_frame_style)
        
        if hasattr(self, 'title_label'):
            self.title_label.setStyleSheet(f"font-weight: bold; font-size: 16px; color: {title_color};")
            
        if hasattr(self, 'quality_label') and hasattr(self, 'format_label') and hasattr(self, 'duration_label'):
            for label in [self.quality_label, self.format_label, self.duration_label,
                          self.size_label, self.date_label, self.status_label]:
                label.setStyleSheet(f"color: {label_color}; font-size: 13px;")
            
        if hasattr(self, 'hashtags_label'):
            self.hashtags_label.setStyleSheet(f"color: {hashtag_color}; font-size: 13px;")
            
        if hasattr(self, 'folder_label'):
            self.folder_label.setStyleSheet(f"color: {label_color}; font-size: 12px;")
            
        # Update color for folder icon
        if hasattr(self, 'folder_layout'):
            for i in range(self.folder_layout.count()):
                item = self.folder_layout.itemAt(i)
                if item and item.widget() and isinstance(item.widget(), QLabel) and "📁" in item.widget().text():
                    item.widget().setStyleSheet(f"color: {icon_color};")
            
        if hasattr(self, 'desc_label'):
            self.desc_label.setStyleSheet(f"color: {desc_color}; font-size: 13px;")
            
        if hasattr(self, 'thumbnail_label'):
            self.thumbnail_label.setStyleSheet(f"background-color: {background_color}; border-radius: 8px;")
        
        # Store colors for use when displaying video details
        self.theme_colors = {
            "background": background_color,
            "audio_background": audio_background
        }

    def update_selected_video_details(self, video):
        """Update selected video details"""
        if not video:
            self.video_details_frame.setVisible(False)
            return
        
        self.selected_video = video
        self.video_details_frame.setVisible(True)
        
        # Update title - Prioritize original_title if available, but truncate it
        title = ""
        if len(video) > 9 and video[9]:
            title = video[9]  # Use original_title
        else:
            title = video[0]  # Fallback: short title
            
        # Truncate title if too long
        if len(title) > 45:
            title = title[:45] + "..."
            
        self.title_label.setText(title)
        
        # Check file path to determine correct quality and format
        filepath = os.path.join(video[8], video[0]) if video[8] and video[0] else ""
        is_mp3 = filepath and filepath.lower().endswith('.mp3')
        
        # Update technical information
        if is_mp3:
            self.quality_label.setText(f"🔷 {self.tr_('DETAIL_QUALITY')}: 320kbps")
        else:
            self.quality_label.setText(f"🔷 {self.tr_('DETAIL_QUALITY')}: {video[2]}")
        
        # Ensure correct format display
        format_value = ""
        if is_mp3:
            format_value = self.tr_("FORMAT_AUDIO_MP3")
        else:
            format_value = video[3]
            if format_value == "1080p" or format_value == "720p" or format_value == "480p" or format_value == "360p" or format_value == "Video (mp4)":
                format_value = self.tr_("FORMAT_VIDEO_MP4")
            elif format_value == "320kbps" or format_value == "192kbps" or format_value == "128kbps" or format_value == "Audio (mp3)":
                format_value = self.tr_("FORMAT_AUDIO_MP3")
        self.format_label.setText(f"🎬 {self.tr_('DETAIL_FORMAT')}: {format_value}")
        
        # Update size and date
        self.size_label.setText(f"💾 {self.tr_('DETAIL_SIZE')}: {video[4]}")
        self.date_label.setText(f"📅 {self.tr_('DETAIL_DOWNLOADED')}: {video[6]}")
        
        # Check if file exists and display corresponding status
        status_value = video[5]
        if filepath and os.path.exists(filepath):
            status_value = "Successful"
        elif status_value == "Download successful":
            status_value = "Successful"
        self.status_label.setText(f"✅ {self.tr_('DETAIL_STATUS')}: {status_value}")
        
        # Display duration
        if hasattr(self, 'duration_label'):
            # Check if duration information exists in the video (index 10 if available)
            if len(video) > 10 and video[10]:
                duration = video[10]
            else:
                # If not available, use default value
                duration = "Unknown" 
            self.duration_label.setText(f"⏱️ {self.tr_('DETAIL_DURATION')}: {duration}")
        
        # Update hashtags - Ensure correct display
        hashtags = video[7]
        if hashtags and not hashtags.startswith('#'):
            # If it's a string of hashtags separated by spaces without # symbol
            if ' ' in hashtags and not '#' in hashtags:
                hashtags = ' '.join(['#' + tag.strip() for tag in hashtags.split()])
        self.hashtags_label.setText(hashtags)  # Hashtags
        
        # Update folder path
        self.folder_label.setText(video[8])  # Folder

        # Update creator
        creator = video[1] if len(video) > 1 else "Unknown"
        self.desc_label.setText(f"Creator: {creator}")
        
        # Add subtitle information if available
        if len(video) > 12 and video[12] is not None:
            has_subtitle = bool(video[12])  # has_subtitle is at index 12
            subtitle_language = video[13] if len(video) > 13 else ""  # subtitle_language at index 13
            subtitle_type = video[14] if len(video) > 14 else ""  # subtitle_type at index 14
            
            if has_subtitle and self.subtitle_info_label is None:
                # Create subtitle info label if it doesn't exist yet
                self.subtitle_info_label = QLabel()
                self.subtitle_info_label.setWordWrap(True)
                self.subtitle_info_label.setStyleSheet("padding: 5px; border-radius: 4px; background-color: rgba(80, 80, 80, 0.1);")
                self.video_details_frame.layout().addWidget(self.subtitle_info_label)
            
            if has_subtitle and self.subtitle_info_label is not None:
                # Update subtitle info label
                type_text = self.tr_("SUBTITLE_TYPE_OFFICIAL") if subtitle_type == "official" else self.tr_("SUBTITLE_TYPE_AUTO")
                self.subtitle_info_label.setText(
                    f"🗣️ {self.tr_('LABEL_HAS_SUBTITLES').format('✓')}\n"
                    f"🌐 {self.tr_('LABEL_SUBTITLE_LANGUAGE').format(subtitle_language.upper())}\n"
                    f"📝 {self.tr_('LABEL_SUBTITLE_TYPE').format(type_text)}"
                )
                self.subtitle_info_label.setVisible(True)
            elif self.subtitle_info_label is not None:
                self.subtitle_info_label.setVisible(False)
        elif self.subtitle_info_label is not None:
            self.subtitle_info_label.setVisible(False)
        
        # Update thumbnail
        # Reset pixmap first to ensure clean state
        # Update thumbnail
        # Reset pixmap first to ensure clean state
        default_pixmap = QPixmap(150, 150)
        default_pixmap.fill(Qt.GlobalColor.transparent)
        self.thumbnail_label.setPixmap(default_pixmap)
        
        # Set default style based on file type
        is_audio = is_mp3 or "MP3" in format_value or "Audio" in video[3] or "mp3" in format_value.lower()
        if is_audio:
            # If it's an audio file, use music icon as default
            self.thumbnail_label.setStyleSheet(f"background-color: {self.theme_colors['audio_background']}; border-radius: 8px;")
            self.play_icon.setText("🎵")  # Unicode music icon
            self.play_icon.setStyleSheet("font-size: 52px; color: white; background-color: transparent;")
            self.play_icon.setVisible(True)  # Always show music icon for MP3 files
        else:
            # If it's a video, use play icon as default
            self.thumbnail_label.setStyleSheet(f"background-color: {self.theme_colors['background']}; border-radius: 8px;")
            self.play_icon.setText("▶️")  # Unicode play icon
            self.play_icon.setStyleSheet("font-size: 52px; color: white; background-color: transparent;")
        
        # Try to load thumbnail for both mp3 and mp4 files
        thumbnail_path = video[11] if len(video) > 11 and video[11] else ""
        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                print(f"Loading thumbnail from: {thumbnail_path}")
                pixmap = QPixmap(thumbnail_path)
                if not pixmap.isNull():
                    print(f"Successfully loaded thumbnail: {thumbnail_path}, size: {pixmap.width()}x{pixmap.height()}")
                    pixmap = pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio)
                    self.thumbnail_label.setPixmap(pixmap)
                    # When thumbnail loads successfully, remove background color
                    self.thumbnail_label.setStyleSheet("background-color: transparent; border-radius: 8px;")
                    # Hide play icon when thumbnail is available
                    self.play_icon.setVisible(False)
                else:
                    print(f"Failed to load thumbnail: pixmap is null for {thumbnail_path}")
                    self.play_icon.setVisible(True)
            except Exception as e:
                print(f"Error loading thumbnail: {e} for {thumbnail_path}")
                self.play_icon.setVisible(True)
        else:
            print(f"No thumbnail or file doesn't exist: {thumbnail_path}")
            self.play_icon.setVisible(True)

    def sort_table(self, column):
        """Sort the table by the clicked column"""
        print(f"DEBUG: sort_table called with column={column}")
        print(f"DEBUG: Before sort - current sort_column={self.sort_column}, sort_order={self.sort_order}")
        
        # Disable table sorting to avoid issues during update
        was_sorting_enabled = self.downloads_table.isSortingEnabled()
        self.downloads_table.setSortingEnabled(False)
        
        # Determine correct column mapping to match the index in self.filtered_videos based on current platform
        if self.current_platform == "TikTok":
            # TikTok view column mapping (without Platform column)
            column_mapping = {
                0: 0,  # Select (no sorting)
                1: 0,  # Title (index 0 in filtered_videos)
                2: 1,  # Creator (index 1 in filtered_videos)
                3: 2,  # Quality (index 2 in filtered_videos)
                4: 3,  # Format (index 3 in filtered_videos)
                5: 10, # Duration (index 10 in filtered_videos)
                6: 4,  # Size (index 4 in filtered_videos)
                7: 7,  # Hashtags (index 7 in filtered_videos)
                8: 6   # Date (index 6 in filtered_videos)
            }
            # Define sortable columns for TikTok view
            sortable_columns = [1, 2, 3, 4, 5, 6, 7, 8]  # All columns except checkbox
        elif self.current_platform == "YouTube":
            # YouTube view column mapping
            column_mapping = {
                0: 0,  # Select (no sorting)
                1: 0,  # Title (index 0 in filtered_videos)
                2: 1,  # Channel (index 1 in filtered_videos)
                3: -1, # Playlist (placeholder in filtered_videos for now)
                4: 2,  # Quality (index 2 in filtered_videos)
                5: 3,  # Format (index 3 in filtered_videos)
                6: 10, # Duration (index 10 in filtered_videos)
                7: 4,  # Size (index 4 in filtered_videos)
                8: -1, # Release Date (placeholder in filtered_videos for now)
                9: 6   # Download Date (index 6 in filtered_videos)
            }
            # Define sortable columns for YouTube view
            sortable_columns = [1, 2, 3, 4, 5, 6, 7, 8, 9]  # All columns except checkbox
        else:
            # Default view with Platform column
            column_mapping = {
                0: 0,  # Select (no sorting)
                1: 12, # Platform (index 12 in filtered_videos)
                2: 0,  # Title (index 0 in filtered_videos)
                3: 1,  # Creator (index 1 in filtered_videos)
                4: 2,  # Quality (index 2 in filtered_videos)
                5: 3,  # Format (index 3 in filtered_videos)
                6: 10, # Duration (index 10 in filtered_videos)
                7: 4,  # Size (index 4 in filtered_videos)
                8: 6   # Date (index 6 in filtered_videos)
            }
            # Define sortable columns for default view
            sortable_columns = [1, 2, 3, 4, 5, 6, 7, 8]  # All columns except checkbox

        # Skip if column is not sortable (e.g., checkbox column)
        if column not in sortable_columns:
            print(f"DEBUG: Column {column} is not sortable, skipping")
            return
            
        # Get corresponding data column in filtered_videos
        data_column = column_mapping.get(column, -1)
        if data_column < 0:
            print(f"DEBUG: Column {column} mapping not found or invalid")
            return
            
        # Log sorted column information
        print(f"DEBUG: Table column {column} maps to data column {data_column}")
        
        # Toggle sort order if the same column is clicked again
        if self.sort_column == column:
            self.sort_order = Qt.SortOrder.AscendingOrder if self.sort_order == Qt.SortOrder.DescendingOrder else Qt.SortOrder.DescendingOrder
        else:
            self.sort_column = column
            self.sort_order = Qt.SortOrder.AscendingOrder
            
        print(f"DEBUG: After sort - sort_column={self.sort_column}, sort_order={self.sort_order}")
            
        # Sort videos by the selected column
        self.sort_videos(data_column, self.sort_order)
        
        # Update the table header to show sort indicator
        header = self.downloads_table.horizontalHeader()
        header.setSortIndicator(column, self.sort_order)
        
        # Put sort indicator only on the sorted column
        if was_sorting_enabled:
            self.downloads_table.setSortingEnabled(True)
        
        print(f"DEBUG: Sorted videos by column {column} / data column {data_column}")

    def sort_videos(self, column, sort_order):
        """Sort the videos list by the specified column and order"""
        # Disable table sorting to avoid triggering sort signals during update
        was_sorting_enabled = self.downloads_table.isSortingEnabled()
        self.downloads_table.setSortingEnabled(False)
        
        try:
            # Handle special case for column index 7 (hashtags) in TikTok view
            if self.current_platform == "TikTok" and column == 7:
                self.sort_by_hashtags(sort_order)
                return
            
            # Define a sort key function based on the column
            def sort_key(video):
                # Ensure column index is valid for the video
                if len(video) <= column or video[column] is None:
                    return ""  # Return empty string for invalid or empty values
                
                # Get the value at the specified column
                value = video[column]
                
                # Special case for date (column 6)
                if column == 6:  # Download date
                    # Try to convert date string to a sortable format
                    try:
                        # Check if it's a timestamp or a date string
                        if isinstance(value, (int, float)):
                            return value
                        
                        # Try different date formats
                        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y"]:
                            try:
                                return datetime.strptime(value, fmt)
                            except ValueError:
                                continue
                            
                        # If all formats fail, return the original string
                        return value
                    except Exception:
                        return value
                
                # Special case for size (column 4) - convert to bytes for sorting
                if column == 4:  # Size column
                    try:
                        # Extract numeric value from size string (e.g., "10.5 MB" -> 10.5)
                        size_parts = value.split()
                        if len(size_parts) == 2:
                            size_value = float(size_parts[0])
                            size_unit = size_parts[1].upper()
                            
                            # Convert to bytes based on unit
                            if size_unit == "KB":
                                return size_value * 1024
                            elif size_unit == "MB":
                                return size_value * 1024 * 1024
                            elif size_unit == "GB":
                                return size_value * 1024 * 1024 * 1024
                            else:
                                return size_value
                        else:
                            return 0  # Default if format is not recognized
                    except Exception:
                        return 0  # Default value on error
                
                # Special case for duration (column 10)
                if column == 10:  # Duration
                    # Try to convert duration in formats like "5:30" to seconds
                    try:
                        if isinstance(value, (int, float)):
                            return value  # Already in seconds
                        
                        # Check if in MM:SS format
                        if ":" in value:
                            parts = value.split(":")
                            if len(parts) == 2:
                                return int(parts[0]) * 60 + int(parts[1])
                        
                        # Try to convert directly to int if possible
                        return int(value)
                    except:
                        return 0  # Default value on error
                
                # Default case - return the value as is
                return value

            # Sort the filtered videos list
            self.filtered_videos.sort(
                key=sort_key,
                reverse=(sort_order == Qt.SortOrder.DescendingOrder)
            )
            
            # Update the table to show sorted data
            self.display_videos()
            
        except Exception as e:
            print(f"Error sorting videos: {e}")
            traceback.print_exc()
        
        # Restore sorting if it was enabled
        if was_sorting_enabled:
            self.downloads_table.setSortingEnabled(True)

    def sort_by_hashtags(self, sort_order):
        """Special sorting method for hashtags"""
        try:
            # Clone the filtered videos
            sorted_videos = self.filtered_videos.copy()
            
            # Define key function for hashtag sorting
            def hashtag_sort_key(video):
                # Get hashtags at index 7
                hashtags = video[7] if len(video) > 7 else ""
                
                # Prepare hashtags for sorting
                if not hashtags:
                    return ("", 0)  # Empty hashtags sort first (or last when reversed)
                
                # Normalize hashtags to ensure consistent sorting
                if isinstance(hashtags, str):
                    # Clean and normalize hashtags
                    normalized = hashtags.lower().strip()
                    
                    # Count hashtags
                    if ' ' in normalized:
                        tags = [tag.strip() for tag in normalized.split() if tag.strip()]
                        count = len(tags)
                        # First sort by count, then by the actual hashtag content
                        return (normalized, count)
                    else:
                        # Single hashtag
                        return (normalized, 1)
                else:
                    return ("", 0)
            
            # Sort by normalized hashtags and count
            # Primary sort by hashtag text, secondary by count
            sorted_videos.sort(key=hashtag_sort_key, reverse=(sort_order == Qt.SortOrder.DescendingOrder))
            
            # Update and display
            if len(sorted_videos) > 0:
                self.filtered_videos = sorted_videos
                print(f"DEBUG: After sorting by hashtags with order {sort_order}")
                hashtags = sorted_videos[0][7] if len(sorted_videos[0]) > 7 else "None"
                print(f"DEBUG: First item hashtags: {hashtags}")
            
            # Display the sorted videos
            self.display_videos()
            
        except Exception as e:
            print(f"Error sorting videos by hashtags: {e}")
            import traceback
            traceback.print_exc()

    def show_full_text_tooltip(self, row, column):
        """Show tooltip with full text when hovering over a cell"""
        # Don't process for checkbox column
        if column == self.select_col:
            QToolTip.hideText()
            return
            
        # Get table item
        item = self.downloads_table.item(row, column)
        if item and 0 <= row < len(self.filtered_videos):
            # Get text content
            text = item.text()
            tooltip_text = text
            
            # Special processing for certain columns
            video = self.filtered_videos[row]
            
            # Title column - use full title if available
            if (column == self.title_col) and len(video) > 9 and video[9]:
                tooltip_text = video[9]
            
            # Creator column - add "Creator: " prefix
            elif column == self.creator_col:
                tooltip_text = f"Creator: {text}"
            
            # Hashtags column - convert to better format
            elif (column == self.hashtags_col) and video[7]:
                hashtags = video[7]
                # Ensure hashtags are properly formatted
                if ' ' in hashtags and not all(tag.startswith('#') for tag in hashtags.split()):
                    tooltip_text = ' '.join(['#' + tag.strip() if not tag.strip().startswith('#') else tag.strip() 
                               for tag in hashtags.split()])
                else:
                    tooltip_text = hashtags
            
            # Format tooltip for better readability
            if tooltip_text:
                formatted_text = self.format_tooltip_text(tooltip_text)
                
                # Only show tooltip if text is actually truncated or contains multiple lines
                rect = self.downloads_table.visualItemRect(item)
                font_metrics = QFontMetrics(item.font())
                if (font_metrics.horizontalAdvance(text) > rect.width() or '\n' in formatted_text or 
                    (column == self.title_col and len(video) > 9 and video[9] != text)):
                    
                    # Force tooltip to use current theme by hiding any existing tooltip first
                    QToolTip.hideText()
                    
                    # Show new tooltip with formatted text
                    QToolTip.showText(QCursor.pos(), formatted_text)
                else:
                    QToolTip.hideText()
            else:
                QToolTip.hideText()
        else:
            QToolTip.hideText()

    def show_copy_dialog(self, item):
        """Show dialog to copy text when double-clicking on a cell in the table"""
        column = item.column()
        row = item.row()
        
        # Only show copy dialog for Title (1), Creator (2) and Hashtags (8) columns
        if column not in [1, 2, 8]:
            return
        
        # Get full video information from filtered_videos
        full_text = ""
        if 0 <= row < len(self.filtered_videos):
            video = self.filtered_videos[row]
            
            if column == 1:  # Title
                title = video[0] if len(video) > 0 else ""
                full_title = video[9] if len(video) > 9 and video[9] else title
                
                # Remove hashtags from title
                # Delete all text starting with # and ending with whitespace
                cleaned_full_title = re.sub(r'#\S+\s*', '', full_title).strip()
                # Replace multiple spaces with a single space
                cleaned_full_title = re.sub(r'\s+', ' ', cleaned_full_title).strip()
                
                # Only display cleaned full title, no longer display short title above
                full_text = cleaned_full_title
                
            elif column == 2:  # Creator
                full_text = video[1] if len(video) > 1 else ""
            elif column == 8:  # Hashtags
                # Format hashtags for easy reading and copying
                if len(video) > 7 and video[7]:
                    hashtags = video[7]
                    # Ensure each hashtag has # symbol
                    if ' ' in hashtags and not all(tag.startswith('#') for tag in hashtags.split()):
                        full_text = ' '.join(['#' + tag.strip() if not tag.strip().startswith('#') else tag.strip() 
                                              for tag in hashtags.split()])
                    else:
                        full_text = hashtags
        else:
            full_text = item.text()  # Fallback to cell text
            
        if not full_text:
            return
            
        # Determine dialog title based on column
        if column == 1:
            title = self.tr_("HEADER_TITLE")
        elif column == 2:
            title = self.tr_("HEADER_CREATOR")
        else:  # column == 8
            title = self.tr_("HEADER_HASHTAGS")
            
        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setMinimumWidth(600)  # Increase minimum width
        dialog.setMinimumHeight(400)  # Add minimum height
        dialog.resize(600, 400)  # Set default size
        
        # Determine current theme from parent window
        current_theme = "dark"
        if hasattr(self, 'parent') and hasattr(self.parent, 'current_theme'):
            current_theme = self.parent.current_theme
        
        # Apply style based on current theme
        if current_theme == "light":
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #f0f0f0;
                    color: #333333;
                }
                QTextEdit {
                    background-color: #ffffff;
                    color: #333333;
                    border: 1px solid #cccccc;
                    padding: 5px;
                    font-size: 14px;
                }
                QPushButton {
                    background-color: #0078d7;
                    color: #ffffff;
                    border: none;
                    padding: 8px 15px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #0086f0;
                }
            """)
        else:
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #2d2d2d;
                    color: #ffffff;
                }
                QTextEdit {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    border: 1px solid #555555;
                    padding: 5px;
                    font-size: 14px;
                }
                QPushButton {
                    background-color: #0078d7;
                    color: #ffffff;
                    border: none;
                    padding: 8px 15px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #0086f0;
                }
            """)
        
        # Dialog layout
        layout = QVBoxLayout(dialog)
        
        # Text edit for display and copy
        text_edit = QTextEdit(dialog)
        text_edit.setPlainText(full_text)
        text_edit.setReadOnly(True)  # Only allow reading and copying
        text_edit.setMinimumHeight(300)  # Set minimum height for text edit
        text_edit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)  # Auto wrap text
        
        # Set up scroll bar
        text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        layout.addWidget(text_edit)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # Copy button
        copy_btn = QPushButton(self.tr_("BUTTON_COPY"))
        # Add column_name corresponding to data type
        if column == 1:  # Title
            copy_btn.clicked.connect(lambda: self.copy_to_clipboard(full_text, "title"))
        elif column == 2:  # Creator
            copy_btn.clicked.connect(lambda: self.copy_to_clipboard(full_text, "creator"))
        elif column == 8:  # Hashtags
            copy_btn.clicked.connect(lambda: self.copy_to_clipboard(full_text, "hashtags"))
        else:
            copy_btn.clicked.connect(lambda: self.copy_to_clipboard(full_text))
        button_layout.addWidget(copy_btn)
        
        # Close button
        close_btn = QPushButton(self.tr_("BUTTON_CANCEL"))
        close_btn.clicked.connect(dialog.close)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        # Show dialog and handle response after dialog is closed
        dialog.exec()
        
        # Clear selection and set focus to search input to avoid selection effect
        self.downloads_table.clearSelection()
        self.downloads_table.clearFocus()
        # Set focus back to search input
        self.search_input.setFocus()
        
    def copy_to_clipboard(self, text, column_name=None):
        """Copy text to clipboard with special handling for some columns"""
        if not text:
            return
        
        # Special handling for title - remove hashtags
        if column_name == "title":
            # Remove hashtags from title
            text = re.sub(r'#\w+', '', text).strip()
            # Replace double spaces with a single space
            text = re.sub(r'\s+', ' ', text)
        
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        if self.parent:
            # Show preview of copied text in status bar (up to 50 characters)
            copied_text = text[:50] + "..." if len(text) > 50 else text
            self.parent.status_bar.showMessage(self.tr_("STATUS_TEXT_COPIED").format(copied_text), 3000)

    def delete_selected_videos(self):
        """Delete selected videos from database and table"""
        # Get list of selected videos
        selected_videos = []
        for row in range(self.downloads_table.rowCount()):
            select_widget = self.downloads_table.cellWidget(row, 0)
            if select_widget:
                checkbox = select_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    if row < len(self.filtered_videos):
                        selected_videos.append(self.filtered_videos[row])
        
        # Check if any video is selected
        if not selected_videos:
            QMessageBox.information(self, self.tr_("DIALOG_INFO"), 
                                   self.tr_("DIALOG_NO_VIDEOS_SELECTED"))
            return
        
        # Create custom message box with delete file checkbox
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(self.tr_("DIALOG_CONFIRM_DELETION"))
        
        # Set detailed text
        if self.lang_manager:
            # Use current language directly to get translated text
            confirmation_text = self.lang_manager.tr("DIALOG_CONFIRM_DELETE_SELECTED").format(len(selected_videos))
        else:
            # Fallback if no language manager
            confirmation_text = f"Are you sure you want to delete {len(selected_videos)} selected videos?"
        
        # If there are multiple videos, add list of videos to be deleted (up to 3 videos)
        if len(selected_videos) > 1:
            videos_list = "\n".join([f"• {video[0]}" for video in selected_videos[:3]])
            if len(selected_videos) > 3:
                videos_list += f"\n• ... and {len(selected_videos) - 3} other videos"
            
            confirmation_text += f"\n\n{videos_list}"
        
        msg_box.setText(confirmation_text)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        msg_box.setIcon(QMessageBox.Icon.Question)
        
        # Set minimum size
        msg_box.setMinimumWidth(500)
        msg_box.setMinimumHeight(200)
        
        # Determine current theme
        current_theme = "dark"
        if hasattr(self, 'parent') and hasattr(self.parent, 'current_theme'):
            current_theme = self.parent.current_theme
        
        # Add style based on theme
        if current_theme == "light":
            light_style = """
                QMessageBox {
                    background-color: #f0f0f0;
                    color: #333333;
                }
                QLabel {
                    color: #333333;
                }
                QPushButton {
                    background-color: #0078d7;
                    color: white;
                    border: none;
                    padding: 6px 12px;
                    margin: 4px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #005fa3;
                }
                QCheckBox {
                    color: #333333;
                }
            """
            msg_box.setStyleSheet(light_style)
            
        # Add checkbox "Delete file from disk"
        delete_file_checkbox = QCheckBox(self.tr_("DIALOG_DELETE_FILES_FROM_DISK"))
        
        # Create container for checkboxes
        checkbox_container = QWidget()
        checkbox_layout = QVBoxLayout(checkbox_container)
        checkbox_layout.setContentsMargins(0, 0, 0, 0)
        checkbox_layout.setSpacing(5)
        checkbox_layout.addWidget(delete_file_checkbox)
        
        # Find button box to add checkboxes to layout
        button_box = msg_box.findChild(QDialogButtonBox)
        if button_box:
            # Add container to the left of button box
            button_layout = button_box.layout()
            button_layout.insertWidget(0, checkbox_container, 0, Qt.AlignmentFlag.AlignLeft)
            # Add more space between checkboxes and buttons
            button_layout.insertSpacing(1, 50)
            
            # Customize checkboxes for better visibility
            delete_file_checkbox.setStyleSheet("QCheckBox { margin-right: 15px; }")
        else:
            # If no button box found, use old method
            msg_box.layout().addWidget(checkbox_container, 1, 2)
        
        # Show message box and handle response
        reply = msg_box.exec()
        
        if reply == QMessageBox.StandardButton.Yes:
            # Count number of deleted items
            deleted_count = 0
            deleted_files_count = 0
            deleted_thumbnails_count = 0
            
            # Delete selected videos
            for video in selected_videos:
                title = video[0]
                file_path = os.path.join(video[8], title + '.' + ('mp3' if video[3] == 'MP3' or 'mp3' in video[3].lower() else 'mp4'))
                file_exists = os.path.exists(file_path)
                
                # Get thumbnail information
                thumbnail_path = video[11] if len(video) > 11 and video[11] else ""
                thumbnail_exists = thumbnail_path and os.path.exists(thumbnail_path)
                
                print(f"Deleting selected video: {title}")
                
                # Delete file from disk if checkbox is checked and file exists
                if delete_file_checkbox.isChecked() and file_exists:
                    try:
                        os.remove(file_path)
                        print(f"File deleted from disk: {file_path}")
                        deleted_files_count += 1
                        
                        # Delete thumbnail if it exists
                        if thumbnail_exists:
                            try:
                                os.remove(thumbnail_path)
                                print(f"Thumbnail deleted from disk: {thumbnail_path}")
                                deleted_thumbnails_count += 1
                            except Exception as e:
                                print(f"Error deleting thumbnail from disk: {e}")
                        
                    except Exception as e:
                        print(f"Error deleting file from disk: {e}")
                        # Show error message
                        QMessageBox.warning(self, self.tr_("DIALOG_ERROR"), 
                                         self.tr_("DIALOG_CANNOT_DELETE_FILE").format(str(e)))
                
                # Delete from database
                try:
                    db_manager = DatabaseManager()
                    db_manager.delete_download_by_title(title)
                    
                    # Delete from UI list
                    if video in self.all_videos:
                        self.all_videos.remove(video)
                    deleted_count += 1
                    
                    # Delete from filtered list
                    if video in self.filtered_videos:
                        self.filtered_videos.remove(video)
                    
                    # Hide details area if selected video is deleted
                    if self.selected_video and self.selected_video[0] == video[0]:
                        self.video_details_frame.setVisible(False)
                        self.selected_video = None
                except Exception as e:
                    print(f"Error deleting video from database: {e}")
            
            # Update UI
            self.update_statistics()
            
            # Reload all videos from database (to ensure we have clean data)
            self.load_downloaded_videos()
            
            # Re-apply the current platform filter
            if self.current_platform:
                print(f"DEBUG: Re-applying platform filter after deletion: {self.current_platform}")
                self.filter_by_platform(self.current_platform)
            else:
                # If no platform filter is active, just display all videos
                self.display_videos()
            
            # Show notification
            if self.parent:
                if deleted_files_count > 0:
                    self.parent.status_bar.showMessage(self.tr_("STATUS_VIDEOS_AND_FILES_DELETED").format(deleted_count, deleted_files_count))
                    print(f"Deleted {deleted_count} videos, {deleted_files_count} video files, and {deleted_thumbnails_count} thumbnails")
                else:
                    self.parent.status_bar.showMessage(self.tr_("STATUS_VIDEOS_DELETED").format(deleted_count))
        
        # Update button states
        self.update_button_states()

    def toggle_select_all(self):
        """Select or deselect all videos"""
        # If there are no videos, don't do anything
        if self.downloads_table.rowCount() == 0:
            return
            
        # Get current button state
        is_select_all = self.select_toggle_btn.text() == self.tr_("BUTTON_SELECT_ALL")
        
        # Get list of all checkboxes
        checkboxes = []
        for row in range(self.downloads_table.rowCount()):
            select_widget = self.downloads_table.cellWidget(row, 0)
            if select_widget:
                checkbox = select_widget.findChild(QCheckBox)
                if checkbox:
                    checkboxes.append(checkbox)
        
        # Temporarily disconnect signals to avoid multiple calls
        for checkbox in checkboxes:
            checkbox.blockSignals(True)
        
        # Set new state for all checkboxes
        for checkbox in checkboxes:
            checkbox.setChecked(is_select_all)
        
        # Reconnect signals after update
        for checkbox in checkboxes:
            checkbox.blockSignals(False)
        
        # Update button based on action taken
        if is_select_all:
            self.select_toggle_btn.setText(self.tr_("BUTTON_UNSELECT_ALL"))
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_ALL_VIDEOS_SELECTED"))
        else:
            self.select_toggle_btn.setText(self.tr_("BUTTON_SELECT_ALL"))
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_ALL_VIDEOS_UNSELECTED"))
                
    def update_select_toggle_button(self):
        """Update select all button state based on checkbox states"""
        # Check if there are any videos in the table
        if self.downloads_table.rowCount() == 0:
            self.select_toggle_btn.setText(self.tr_("BUTTON_SELECT_ALL"))
            return
            
        # Check status of all checkboxes
        all_checked = True
        any_checked = False
        
        for row in range(self.downloads_table.rowCount()):
            select_widget = self.downloads_table.cellWidget(row, 0)
            if select_widget:
                checkbox = select_widget.findChild(QCheckBox)
                if checkbox:
                    if checkbox.isChecked():
                        any_checked = True
                    else:
                        all_checked = False
        
        # Update button state
        if all_checked and any_checked:
            self.select_toggle_btn.setText(self.tr_("BUTTON_UNSELECT_ALL"))
        else:
            self.select_toggle_btn.setText(self.tr_("BUTTON_SELECT_ALL"))
            
    def checkbox_state_changed(self):
        """Handle checkbox state change"""
        self.update_select_toggle_button()

    def show_context_menu(self, position):
        """Show right-click menu for downloaded videos table"""
        # Set flag to indicate context menu is active
        print("DEBUG: Context menu triggered")
        self._context_menu_active = True
        
        # Get current row and column position
        index = self.downloads_table.indexAt(position)
        
        if not index.isValid():
            self._context_menu_active = False
            return
            
        row = index.row()
        column = index.column()
            
        if row < 0 or row >= self.downloads_table.rowCount():
            self._context_menu_active = False
            return
        
        # Create context menu
        context_menu = QMenu(self)
        
        # Get video details from filtered_videos
        if row < len(self.filtered_videos):
            video = self.filtered_videos[row]
            
            # Determine how to access data based on video type
            if isinstance(video, list):
                # If it's a list, access by index based on schema [title, creator, quality, format, size, status, date, hashtags, directory, orig_title, duration, thumbnail]
                title = video[0] if len(video) > 0 else ""
                creator = video[1] if len(video) > 1 else ""
                format_str = video[3] if len(video) > 3 else "MP4"  # Default to MP4
                hashtags_raw = video[7] if len(video) > 7 else ""
                directory_path = video[8] if len(video) > 8 else ""
                original_title = video[9] if len(video) > 9 else title  # Use original_title if available
                
                print(f"DEBUG - Video data: title='{title}', original_title='{original_title}'")
                
                # Determine filepath based on title and format
                if title and directory_path:
                    ext = "mp3" if format_str == "MP3" else "mp4"
                    filepath = os.path.join(directory_path, f"{title}.{ext}")
                else:
                    filepath = ""
            elif isinstance(video, dict):
                title = video.get('title', '')
                creator = video.get('creator', '')
                hashtags_raw = video.get('hashtags', [])
                filepath = video.get('filepath', '')
                original_title = video.get('original_title', title)  # Use original_title if available
                
                print(f"DEBUG - Dict data: title='{title}', original_title='{original_title}'")
            else:
                title = getattr(video, 'title', '')
                creator = getattr(video, 'creator', '')
                hashtags_raw = getattr(video, 'hashtags', [])
                filepath = getattr(video, 'filepath', '')
                original_title = getattr(video, 'original_title', title)  # Use original_title if available
                
                print(f"DEBUG - Object data: title='{title}', original_title='{original_title}'")
            
            # Determine data type based on column
            if column == 1:  # Title
                # Add Copy Title action
                copy_action = QAction(self.tr_("CONTEXT_COPY_TITLE"), self)
                # Get full title from UserRole data instead of displayed text
                item = self.downloads_table.item(row, column)
                
                # Debug: check UserRole data
                user_role_data = item.data(Qt.ItemDataRole.UserRole) if item else None
                displayed_text = item.text() if item else ""
                
                print(f"DEBUG - Title column - Displayed: '{displayed_text}'")
                print(f"DEBUG - Title column - UserRole: '{user_role_data}'")
                print(f"DEBUG - Video original_title (index 9): '{original_title}'")
                
                # Prioritize UserRole data (original_title) if available
                full_title = user_role_data if user_role_data else (original_title if original_title else title)
                print(f"DEBUG - Final title to copy: '{full_title}'")
                
                # Fix lambda creation to avoid closure issues
                copy_action.triggered.connect(lambda checked=False, title_to_copy=full_title: self.copy_to_clipboard(title_to_copy, column_name="title"))
                context_menu.addAction(copy_action)
            
            elif column == 2:  # Creator
                # Add Copy Creator action
                copy_action = QAction(self.tr_("CONTEXT_COPY_CREATOR"), self)
                print(f"DEBUG - Creator to copy: '{creator}'")
                copy_action.triggered.connect(lambda checked=False, creator_to_copy=creator: self.copy_to_clipboard(creator_to_copy, column_name="creator"))
                context_menu.addAction(copy_action)
            
            elif column == 8:  # Hashtags
                # Handle hashtags
                hashtags_str = ""
                if isinstance(hashtags_raw, list):
                    hashtags_str = ' '.join([f"#{tag}" for tag in hashtags_raw])
                else:
                    # If it's a string, assume hashtags is a pre-formatted string
                    hashtags_str = hashtags_raw
                
                print(f"DEBUG - Hashtags to copy: '{hashtags_str}'")
                # Add Copy Hashtags action
                copy_action = QAction(self.tr_("CONTEXT_COPY_HASHTAGS"), self)
                copy_action.triggered.connect(lambda checked=False, hashtags_to_copy=hashtags_str: self.copy_to_clipboard(hashtags_to_copy, column_name="hashtags"))
                context_menu.addAction(copy_action)
            
            # Common functionality for all columns
            # Add separator if there's an action before
            if not context_menu.isEmpty():
                context_menu.addSeparator()
            
            # Action: Play Video
            play_action = QAction(self.tr_("CONTEXT_PLAY_VIDEO"), self)
            play_action.triggered.connect(lambda: self.play_video(row))
            context_menu.addAction(play_action)
            
            # Action: Open File Location
            if directory_path or filepath:
                # Determine full file path
                full_filepath = ""
                
                if filepath and os.path.exists(filepath):
                    # If full file path already exists and file exists
                    full_filepath = filepath
                elif title and directory_path:
                    # If only title and directory, create file path
                    if isinstance(video, list):
                        # Determine file extension from format_str
                        ext = "mp3" if format_str == "MP3" or "mp3" in format_str.lower() else "mp4"
                        
                        # Create file path
                        possible_filepath = os.path.join(directory_path, f"{title}.{ext}")
                        
                        # Check if file exists
                        if os.path.exists(possible_filepath):
                            full_filepath = possible_filepath
                        else:
                            # If file doesn't exist, try to find a similar file
                            print(f"DEBUG - File not found: '{possible_filepath}', searching for similar files...")
                            try:
                                # Search for similar files in the directory
                                files = os.listdir(directory_path)
                                best_match = None
                                
                                # Remove special characters and punctuation from title for comparison
                                clean_title = title.replace('?', '').replace('!', '').replace(':', '').strip()
                                
                                for file in files:
                                    # Only check MP3 or MP4 files
                                    if file.endswith('.mp3') or file.endswith('.mp4'):
                                        # Compare file name (without extension) with title
                                        file_name = os.path.splitext(file)[0]
                                        
                                        # If file name contains title or vice versa
                                        if clean_title in file_name or file_name in clean_title:
                                            best_match = file
                                            break
                                
                                if best_match:
                                    full_filepath = os.path.join(directory_path, best_match)
                                    print(f"DEBUG - Found matching file: '{full_filepath}'")
                                else:
                                    # If no file found, use directory
                                    full_filepath = directory_path
                            except Exception as e:
                                print(f"DEBUG - Error searching for file: {str(e)}")
                                full_filepath = directory_path
                    else:
                        # Default to using directory if no file path is specified
                        full_filepath = directory_path
                else:
                    # If no information is provided, use directory
                    full_filepath = directory_path or os.path.dirname(filepath) if filepath else ""
                
                # If still no file found, use directory
                if not full_filepath or not os.path.exists(full_filepath):
                    full_filepath = directory_path
                
                # Create action and connect to event
                open_folder_action = QAction(self.tr_("CONTEXT_OPEN_LOCATION"), self)
                open_folder_action.triggered.connect(lambda: self.open_folder(full_filepath))
                context_menu.addAction(open_folder_action)
            
            # Add separator
            context_menu.addSeparator()
            
            # Action: Delete Video
            delete_action = QAction(self.tr_("CONTEXT_DELETE"), self)
            delete_action.triggered.connect(lambda: self.delete_video(row))
            context_menu.addAction(delete_action)
        
        # Show menu if there are actions
        if not context_menu.isEmpty():
            # Connect the aboutToHide signal to reset the context menu flag
            context_menu.aboutToHide.connect(self.reset_context_menu_flag)
            context_menu.exec(QCursor.pos())
        else:
            self._context_menu_active = False
    
    def reset_context_menu_flag(self):
        """Reset the context menu active flag when menu hides"""
        print("DEBUG: Context menu closed, resetting flag")
        self._context_menu_active = False

    def play_video(self, row):
        """Play video using default system player"""
        if row < 0 or row >= len(self.filtered_videos):
            return
            
        video = self.filtered_videos[row]
        
        # Log for debugging
        print(f"DEBUG - Attempting to play video at row {row}")
        
        # Determine how to access file path based on video type
        filepath = ""
        title = ""
        directory_path = ""
        
        if isinstance(video, list):
            # If it's a list, get title, format, and directory to create full path
            title = video[0] if len(video) > 0 else ""
            format_str = video[3] if len(video) > 3 else "MP4"  # Default to MP4
            directory_path = video[8] if len(video) > 8 else ""
            
            print(f"DEBUG - Video data: title='{title}', format='{format_str}', directory='{directory_path}'")
        elif isinstance(video, dict):
            filepath = video.get('filepath', '')
            title = video.get('title', '')
            directory_path = video.get('directory', '')
            print(f"DEBUG - Dict filepath: '{filepath}'")
        else:
            filepath = getattr(video, 'filepath', '')
            title = getattr(video, 'title', '')
            directory_path = getattr(video, 'directory', '')
            print(f"DEBUG - Object filepath: '{filepath}'")
        
        # If full file path is available
        if filepath and os.path.exists(filepath):
            output_file = filepath
        else:
            # If no filepath, create from directory and title
            if title and directory_path:
                # Normalize directory path
                directory_path = os.path.normpath(directory_path)
                
                # Handle special characters in filename
                safe_title = title.replace('/', '_').replace('\\', '_').replace('?', '')
                
                # Handle different file extensions
                ext = ""
                if isinstance(video, list):
                    format_str = video[3] if len(video) > 3 else "MP4"
                    ext = "mp3" if format_str == "MP3" or "mp3" in format_str.lower() else "mp4"
                else:
                    # Based on file extension if available
                    if filepath and filepath.lower().endswith('.mp3'):
                        ext = "mp3"
                    else:
                        ext = "mp4"  # Default is mp4
                
                # Create full file path
                output_file = os.path.join(directory_path, f"{safe_title}.{ext}")
                output_file = os.path.normpath(output_file)
                
                print(f"DEBUG - Generated filepath: '{output_file}'")
            else:
                print(f"DEBUG - Not enough data to generate filepath")
                QMessageBox.warning(
                    self, 
                    self.tr_("DIALOG_ERROR"), 
                    self.tr_("CONTEXT_FILE_NOT_FOUND")
                )
                return
        
        # Check if file exists
        if not os.path.exists(output_file):
            print(f"DEBUG - File not found at '{output_file}', checking for similar files...")
            found_file = False
            
            # Search for file in directory based on title
            if directory_path and os.path.exists(directory_path):
                try:
                    # Remove unwanted characters for search
                    search_title = title.replace('?', '').replace('!', '').replace(':', '').strip()
                    
                    # Create different variations of title for search
                    title_variants = [
                        search_title,
                        search_title.split('#')[0].strip(),  # Remove hashtag if present
                        ' '.join(search_title.split()[:5]) if len(search_title.split()) > 5 else search_title,  # First 5 words
                        search_title.replace(' ', '_')  # Replace spaces with underscores
                    ]
                    
                    print(f"DEBUG - Searching for title variants: {title_variants}")
                    
                    # List files in directory
                    files = os.listdir(directory_path)
                    
                    # Find best match
                    best_match = None
                    highest_score = 0
                    
                    for file in files:
                        # Only consider mp4 or mp3 files
                        if file.endswith('.mp4') or file.endswith('.mp3'):
                            file_without_ext = os.path.splitext(file)[0]
                            
                            # Calculate similarity score
                            score = 0
                            for variant in title_variants:
                                if variant in file_without_ext or file_without_ext in variant:
                                    # If this string is in the file name or vice versa
                                    score = max(score, len(variant) / max(len(variant), len(file_without_ext)))
                                    if score > 0.8:  # If similarity > 80%
                                        break
                            
                            if score > highest_score:
                                highest_score = score
                                best_match = file
                    
                    # If a matching file is found
                    if best_match and highest_score > 0.5:  # Set threshold to 50% similarity
                        output_file = os.path.join(directory_path, best_match)
                        found_file = True
                        print(f"DEBUG - Found matching file with score {highest_score}: '{output_file}'")
                    else:
                        print(f"DEBUG - No good match found. Best match: {best_match} with score {highest_score}")
                        
                    # If no matching file is found, try to find a file starting with the first few words of the title
                    if not found_file:
                        # Get first 3 words of title
                        first_few_words = ' '.join(search_title.split()[:3]) if len(search_title.split()) > 3 else search_title
                        
                        for file in files:
                            if (file.endswith('.mp4') or file.endswith('.mp3')) and file.startswith(first_few_words):
                                output_file = os.path.join(directory_path, file)
                                found_file = True
                                print(f"DEBUG - Found file starting with first few words: '{output_file}'")
                                break
                                
                except Exception as e:
                    print(f"DEBUG - Error while searching for files: {str(e)}")
            
            # If no file is found
            if not found_file:
                error_msg = f"{self.tr_('CONTEXT_FILE_NOT_FOUND')}: {title}"
                print(f"DEBUG - {error_msg}")
                QMessageBox.warning(self, self.tr_("DIALOG_ERROR"), error_msg)
                return
        
        # Play file using default system player
        try:
            print(f"DEBUG - Playing file: '{output_file}'")
            if os.name == 'nt':  # Windows
                os.startfile(output_file)
            elif os.name == 'posix':  # macOS, Linux
                subprocess.Popen(['xdg-open', output_file])
                
            # Show message in status bar
            if self.parent and self.parent.status_bar:
                self.parent.status_bar.showMessage(f"{self.tr_('CONTEXT_PLAYING')}: {os.path.basename(output_file)}")
                
                # Add timer to reset status bar after 5 seconds
                QTimer.singleShot(5000, lambda: self.parent.status_bar.showMessage(self.tr_("STATUS_READY")))
        except Exception as e:
            error_msg = f"{self.tr_('CONTEXT_CANNOT_PLAY')}: {str(e)}"
            print(f"DEBUG - Error playing file: {error_msg}")
            QMessageBox.warning(self, self.tr_("DIALOG_ERROR"), error_msg)

    def update_button_states(self):
        """Update button states based on number of videos in table"""
        has_videos = self.downloads_table.rowCount() > 0
        
        # Disable buttons when there are no videos
        self.select_toggle_btn.setEnabled(has_videos)
        self.delete_selected_btn.setEnabled(has_videos)
        
        # Apply proper styling based on enabled state
        if not has_videos:
            # Update button text when no videos exist
            self.select_toggle_btn.setText(self.tr_("BUTTON_SELECT_ALL"))
            
            # Apply disabled style explicitly
            disabled_style = """
                QPushButton:disabled {
                    background-color: #444444;
                    color: #888888;
                    border-color: #555555;
                }
            """
            self.select_toggle_btn.setStyleSheet(disabled_style)
            self.delete_selected_btn.setStyleSheet(disabled_style)
        else:
            # Reset style when enabled
            self.select_toggle_btn.setStyleSheet("")
            self.delete_selected_btn.setStyleSheet("")
        
        # Debug logs for troubleshooting
        print(f"DEBUG: update_button_states - has_videos={has_videos}, rowCount={self.downloads_table.rowCount()}")
        print(f"DEBUG: select_toggle_btn enabled: {self.select_toggle_btn.isEnabled()}")
        print(f"DEBUG: delete_selected_btn enabled: {self.delete_selected_btn.isEnabled()}")
        
        print("DEBUG: update_button_states in downloaded_videos_tab - button states updated")

    def play_selected_video(self):
        """Play currently selected video in video details area"""
        if not self.selected_video:
            QMessageBox.information(self, self.tr_("DIALOG_INFO"), self.tr_("DIALOG_NO_VIDEO_SELECTED"))
            return
            
        # Find row of selected video in filtered_videos
        try:
            selected_index = self.filtered_videos.index(self.selected_video)
            self.play_video(selected_index)
        except ValueError:
            # Video no longer in filtered_videos list
            QMessageBox.warning(self, self.tr_("DIALOG_ERROR"), self.tr_("CONTEXT_FILE_NOT_FOUND"))

    def keyPressEvent(self, event):
        """Handle key press events"""
        # If not special keys, let widget handle them
        if event.key() not in [Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_PageUp, Qt.Key.Key_PageDown, Qt.Key.Key_Home, Qt.Key.Key_End]:
            super().keyPressEvent(event)
            return
            
        # Ensure table has focus when key is pressed
        if not self.downloads_table.hasFocus():
            self.downloads_table.setFocus()
            
        # Get table model
        model = self.downloads_table.model()
        if not model:
            super().keyPressEvent(event)
            return
            
        # Get current row selected in table
        current_row = -1
        selected_rows = self.downloads_table.selectionModel().selectedRows()
        if selected_rows:
            current_row = selected_rows[0].row()
        elif self.selected_video:
            # If no row is selected but video is displayed
            try:
                current_row = self.filtered_videos.index(self.selected_video)
                # If row found, select it
                self.downloads_table.selectRow(current_row)
            except (ValueError, IndexError):
                current_row = -1
                
        # If no row is selected and there's a video in the list
        if current_row == -1 and len(self.filtered_videos) > 0:
            # Select first row
            self.downloads_table.selectRow(0)
            current_row = 0
            
        # Handle navigation keys
        new_row = current_row
        
        if event.key() == Qt.Key.Key_Up:
            new_row = max(0, current_row - 1)
        elif event.key() == Qt.Key.Key_Down:
            new_row = min(len(self.filtered_videos) - 1, current_row + 1)
        elif event.key() == Qt.Key.Key_PageUp:
            # Move up 10 rows
            new_row = max(0, current_row - 10)
        elif event.key() == Qt.Key.Key_PageDown:
            # Move down 10 rows
            new_row = min(len(self.filtered_videos) - 1, current_row + 10)
        elif event.key() == Qt.Key.Key_Home:
            # Move to first row
            new_row = 0
        elif event.key() == Qt.Key.Key_End:
            # Move to last row
            new_row = len(self.filtered_videos) - 1 if len(self.filtered_videos) > 0 else current_row
            
        # If row changed, update selection
        if new_row != current_row and 0 <= new_row < len(self.filtered_videos):
            self.downloads_table.selectRow(new_row)
            # Ensure selected row is visible
            self.downloads_table.scrollTo(self.downloads_table.model().index(new_row, 0), QAbstractItemView.ScrollHint.EnsureVisible)
            
        event.accept()

    def get_unique_column_values(self, column_index):
        """Get list of unique values for a column"""
        # Map from column UI index to data index in filtered_videos
        column_mapping = {
            self.platform_col: 12,  # Platform (index 12 in video_info)
            self.title_col: 0,      # Title (index 0 in video_info)
            self.creator_col: 1,    # Creator (index 1 in video_info)
            self.quality_col: 2,    # Quality (index 2 in video_info)
            self.format_col: 3,     # Format (index 3 in video_info)
            self.duration_col: 10,  # Duration (index 10 in video_info)
            self.size_col: 4,       # Size (index 4 in video_info)
            self.date_col: 6,       # Date (index 6 in video_info)
        }
        
        # If column_index is not in mapping, return empty list
        if column_index not in column_mapping:
            return []
        
        # Get index in filtered_videos corresponding to column UI
        data_index = column_mapping[column_index]
        
        # Collect unique values
        unique_values = set()
        for video in self.all_videos:
            if data_index < len(video):
                unique_values.add(video[data_index])
        
        return list(unique_values)

    def show_header_context_menu(self, pos):
        """Show context menu for header when right-clicked"""
        column_index = self.downloads_table.horizontalHeader().logicalIndexAt(pos)
        print(f"DEBUG: show_header_context_menu called for column index {column_index}")

        # Get the filterable columns
        if self.current_platform == "TikTok":
            filterable_columns = [3, 4, 8]  # Quality, Format, Date for TikTok
        elif self.current_platform == "YouTube":
            filterable_columns = [4, 5, 9]  # Quality, Format, Date for YouTube
        else:
            filterable_columns = [1, 4, 5, 8]  # Platform, Quality, Format, Date for all modes
        
        print(f"DEBUG: Filterable columns: {filterable_columns}")
        
        menu = QMenu(self)
        
        # Only show filter options for filterable columns
        if column_index in filterable_columns:
            # Nhận date_column_index phụ thuộc vào platform hiện tại
            date_column_index = self.date_col
            
            # Xử lý cột Date giống các cột khác - tạo FilterPopup trực tiếp
            unique_values = self.get_unique_column_values(column_index)
            print(f"DEBUG: Unique values for column {column_index}: {unique_values}")
            
            if unique_values:
                # Tạo và hiển thị popup menu filter
                header_text = self.downloads_table.horizontalHeaderItem(column_index).text()
                
                # Đối với cột date, vẫn dùng date filter menu
                if column_index == date_column_index:
                    # Hiển thị menu lọc theo ngày
                    date_menu = QMenu(self)
                    
                    # Add Clear filter option at the top
                    action_clear = QAction(self.tr_("FILTER_CLEAR"), self)
                    
                    # Add options to filter by date
                    action_today = QAction(self.tr_("FILTER_TODAY"), self)
                    action_yesterday = QAction(self.tr_("FILTER_YESTERDAY"), self)
                    action_last_7_days = QAction(self.tr_("FILTER_LAST_7_DAYS"), self)
                    action_last_30_days = QAction(self.tr_("FILTER_LAST_30_DAYS"), self)
                    action_this_month = QAction(self.tr_("FILTER_THIS_MONTH"), self)
                    action_last_month = QAction(self.tr_("FILTER_LAST_MONTH"), self)
                    
                    # Connect actions to filter by date function
                    action_clear.triggered.connect(lambda: self.filter_by_date_range("Clear filter"))
                    action_today.triggered.connect(lambda: self.filter_by_date_range("Today"))
                    action_yesterday.triggered.connect(lambda: self.filter_by_date_range("Yesterday"))
                    action_last_7_days.triggered.connect(lambda: self.filter_by_date_range("Last 7 days"))
                    action_last_30_days.triggered.connect(lambda: self.filter_by_date_range("Last 30 days"))
                    action_this_month.triggered.connect(lambda: self.filter_by_date_range("This month"))
                    action_last_month.triggered.connect(lambda: self.filter_by_date_range("Last month"))
                    
                    # Add clear action first with separator
                    date_menu.addAction(action_clear)
                    date_menu.addSeparator()
                    
                    # Add other actions to menu
                    date_menu.addAction(action_today)
                    date_menu.addAction(action_yesterday)
                    date_menu.addAction(action_last_7_days)
                    date_menu.addAction(action_last_30_days)
                    date_menu.addAction(action_this_month)
                    date_menu.addAction(action_last_month)
                    
                    # Hiển thị menu trực tiếp tại vị trí header
                    date_menu.exec(self.downloads_table.horizontalHeader().mapToGlobal(pos))
                else:
                    # Các cột khác sử dụng FilterPopup
                    filter_popup = FilterPopup(self, column_index, unique_values, header_text)
                    print(f"DEBUG: Creating FilterPopup for column {column_index} with header text '{header_text}'")
                    filter_popup.filterChanged.connect(self.apply_column_filter)
                    filter_popup.exec(self.downloads_table.horizontalHeader().mapToGlobal(pos))
                
                return  # Return early as we're using a popup menu
        
        # Skip adding "Reset Column Widths" option - removed as per client request
        
        # Show the menu if it has actions
        if not menu.isEmpty():
            menu.exec(self.downloads_table.horizontalHeader().mapToGlobal(pos))

    def show_date_filter_menu(self, pos):
        """Show filter menu for date with different options"""
        # Find index of Date column
        date_column_index = self.date_col  # Use the date_col property directly
        
        # Get position of header to show menu
        header_pos = self.downloads_table.horizontalHeader().mapToGlobal(pos)
        
        # Create context menu with options to filter by date
        date_menu = QMenu(self)
        
        # Add Clear filter option at the top
        action_clear = QAction(self.tr_("FILTER_CLEAR"), self)
        
        # Add options to filter by date
        action_today = QAction(self.tr_("FILTER_TODAY"), self)
        action_yesterday = QAction(self.tr_("FILTER_YESTERDAY"), self)
        action_last_7_days = QAction(self.tr_("FILTER_LAST_7_DAYS"), self)
        action_last_30_days = QAction(self.tr_("FILTER_LAST_30_DAYS"), self)
        action_this_month = QAction(self.tr_("FILTER_THIS_MONTH"), self)
        action_last_month = QAction(self.tr_("FILTER_LAST_MONTH"), self)
        
        # Connect actions to filter by date function
        action_clear.triggered.connect(lambda: self.filter_by_date_range("Clear filter"))
        action_today.triggered.connect(lambda: self.filter_by_date_range("Today"))
        action_yesterday.triggered.connect(lambda: self.filter_by_date_range("Yesterday"))
        action_last_7_days.triggered.connect(lambda: self.filter_by_date_range("Last 7 days"))
        action_last_30_days.triggered.connect(lambda: self.filter_by_date_range("Last 30 days"))
        action_this_month.triggered.connect(lambda: self.filter_by_date_range("This month"))
        action_last_month.triggered.connect(lambda: self.filter_by_date_range("Last month"))
        
        # Add clear action first with separator
        date_menu.addAction(action_clear)
        date_menu.addSeparator()
        
        # Add other actions to menu
        date_menu.addAction(action_today)
        date_menu.addAction(action_yesterday)
        date_menu.addAction(action_last_7_days)
        date_menu.addAction(action_last_30_days)
        date_menu.addAction(action_this_month)
        date_menu.addAction(action_last_month)
        
        # Show menu at header position
        date_menu.exec(header_pos)

    def filter_by_date_range(self, date_range):
        """Filter videos by date range"""
        print(f"DEBUG: filter_by_date_range called with date_range={date_range}")
        
        # Depending on date_range, set start and end dates
        filter_name = date_range
        now = datetime.now()
        
        # Use the class property directly
        date_column_index = self.date_col
        
        # Check for clear filter first
        if date_range.lower() == "clear filter" or date_range.lower() == self.tr_("FILTER_CLEAR").lower():
            # Clear filter
            if date_column_index in self.active_filters:
                del self.active_filters[date_column_index]
            self.update_filter_icon(date_column_index, False)
            
            # If no filters left, show ready message
            if not self.active_filters and self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_READY"))
            else:
                # Update status message with remaining filters
                self.update_filter_status_message()
            
            self.filter_videos()
            print(f"DEBUG: Filter cleared for date column")
            return
        
        # Determine time range based on selection
        date_range_lower = date_range.lower()
        if date_range_lower == "today" or date_range_lower == "hôm nay":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
            filter_name = "Hôm nay"
        elif date_range_lower == "yesterday" or date_range_lower == "hôm qua":
            from datetime import timedelta
            start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = (now - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)
            filter_name = "Hôm qua"
        elif date_range_lower == "last 7 days" or date_range_lower == "last_7_days" or date_range_lower == "7 ngày qua":
            from datetime import timedelta
            start_date = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
            filter_name = "7 ngày qua"
        elif date_range_lower == "last 30 days" or date_range_lower == "last_30_days" or date_range_lower == "30 ngày qua":
            from datetime import timedelta
            start_date = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
            filter_name = "30 ngày qua"
        elif date_range_lower == "this month" or date_range_lower == "this_month" or date_range_lower == "tháng này":
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
            filter_name = "Tháng này"
        elif date_range_lower == "last month" or date_range_lower == "last_month" or date_range_lower == "tháng trước":
            if now.month == 1:  # If January, last month is December of previous year
                start_date = now.replace(year=now.year-1, month=12, day=1, hour=0, minute=0, second=0, microsecond=0)
                import calendar
                last_day = calendar.monthrange(now.year-1, 12)[1]
                end_date = now.replace(year=now.year-1, month=12, day=last_day, hour=23, minute=59, second=59, microsecond=999999)
            else:
                start_date = now.replace(month=now.month-1, day=1, hour=0, minute=0, second=0, microsecond=0)
                import calendar
                last_day = calendar.monthrange(now.year, now.month-1)[1]
                end_date = now.replace(month=now.month-1, day=last_day, hour=23, minute=59, second=59, microsecond=999999)
            filter_name = "Tháng trước"
        else:
            # No filter applied
            print(f"DEBUG: Unknown date filter: {date_range}")
            return
            
        print(f"DEBUG: Date filter applied - Start: {start_date}, End: {end_date}, Name: {filter_name}")
        
        # Save time filter
        self.active_filters[date_column_index] = (start_date, end_date, filter_name)
        
        # Update filter icon
        self.update_filter_icon(date_column_index, True, filter_name)
        
        # Update status message summarizing all filters
        self.update_filter_status_message()
        
        # Refresh video list
        self.filter_videos()

    def apply_column_filter(self, column_index, selected_value):
        """Apply filter to a specific column"""
        print(f"DEBUG: apply_column_filter called with column_index={column_index}, selected_value='{selected_value}'")
        
        # If no value is selected, remove filter for this column
        if not selected_value:
            if column_index in self.active_filters:
                del self.active_filters[column_index]
            self.update_filter_icon(column_index, False)
            
            # If no filters left, show ready message
            if not self.active_filters and self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_READY"))
            else:
                # Update status message with remaining filters
                self.update_filter_status_message()
        else:
            # Update filter
            self.active_filters[column_index] = selected_value
            self.update_filter_icon(column_index, True, selected_value)
            
            # Update status message summarizing all filters
            self.update_filter_status_message()
        
        # Print filter information for debugging
        print(f"Applied filter for column {column_index}: {selected_value}")
        print(f"Active filters: {self.active_filters}")
        
        # Apply filter and refresh displayed list
        self.filter_videos()
    
    def update_filter_icon(self, column_index, has_filter, filter_value=None):
        """Update filter icon on header"""
        # Header title remains unchanged - keep column name
        pass

    def update_filter_status_message(self):
        """Update status bar message to show all active filters"""
        if not self.parent or not self.active_filters:
            return
        
        filter_messages = []
        
        for column_index, filter_value in self.active_filters.items():
            # Get column name from header
            header_item = self.downloads_table.horizontalHeaderItem(column_index)
            if header_item is None:
                # Use a fallback name based on column index
                if column_index == self.date_col:
                    column_name = self.tr_("HEADER_COMPLETED_ON")
                elif column_index == self.platform_col:
                    column_name = self.tr_("LABEL_PLATFORM")
                elif column_index == self.quality_col:
                    column_name = self.tr_("HEADER_QUALITY")
                elif column_index == self.format_col:
                    column_name = self.tr_("HEADER_FORMAT")
                elif column_index == self.duration_col:
                    column_name = self.tr_("HEADER_DURATION")
                else:
                    column_name = f"Column {column_index}"
            else:
                column_name = header_item.text().replace(" 🔍", "")
            
            # If it's a Date column, there might be special handling
            if column_index == self.date_col:
                if isinstance(filter_value, tuple) and len(filter_value) == 3:
                    # Get filter name from end of tuple (timestamp, timestamp, filter_name)
                    filter_name = filter_value[2]
                    filter_messages.append(f"{column_name}: {filter_name}")
                else:
                    # If filter_value is a string (filter name)
                    filter_messages.append(f"{column_name}: {filter_value}")
            else:
                filter_messages.append(f"{column_name}: {filter_value}")
        
        # Create summary message
        if filter_messages:
            message = "Đang lọc: " + " | ".join(filter_messages)
            self.parent.status_bar.showMessage(message)

    def get_column_index_by_name(self, column_name):
        """Get column index based on display name (header text)"""
        for i in range(self.downloads_table.columnCount()):
            header_item = self.downloads_table.horizontalHeaderItem(i)
            if header_item and header_item.text().replace(" 🔍", "") == column_name:
                return i
        return -1

    def update_video_count_label(self):
        """Update label displaying filtered video count"""
        # Check if tab has a video count label
        if hasattr(self, 'video_count_label'):
            total_count = len(self.all_videos) if hasattr(self, 'all_videos') else 0
            filtered_count = len(self.filtered_videos) if hasattr(self, 'filtered_videos') else 0
            
            # Display filtered video count / total video count
            if filtered_count < total_count:
                self.video_count_label.setText(f"{filtered_count}/{total_count} {self.tr_('LABEL_VIDEOS')}")
            else:
                self.video_count_label.setText(f"{total_count} {self.tr_('LABEL_VIDEOS')}")

    def handle_cell_clicked(self, row, column):
        """Handle when a cell is clicked in the table"""
        print(f"DEBUG: Cell clicked - row: {row}, column: {column}")
        
        # Check if row is valid
        if row >= 0 and row < len(self.filtered_videos):
            video = self.filtered_videos[row]
            
            # Show the detail information box if it's hidden
            if not self.video_details_frame.isVisible():
                self.video_details_frame.setVisible(True)
            
            # If we already have selected video information and it matches the current video
            if self.selected_video == video:
                # No need to update information as it was already updated when previously selected
                pass
            else:
                # New video selected, updated in handle_selection_changed
                pass

    def video_matches_search(self, video, search_text):
        """Check if video matches search text"""
        if not search_text:
            return True
            
        # Create non-accented version of search keyword
        search_text_no_accent = self.remove_vietnamese_accents(search_text).lower()
        
        # Check each field in the video
        for value in video:
            if isinstance(value, (str, int, float)):
                str_value = str(value).lower()
                str_value_no_accent = self.remove_vietnamese_accents(str_value).lower()
                
                # Check accented version
                if search_text in str_value:
                    return True
                    
                # Check non-accented version
                if search_text_no_accent in str_value_no_accent:
                    return True
                    
        return False

    def setup_tiktok_table_columns(self):
        """Set up table columns specifically for TikTok"""
        # Save current column widths before switching view
        if self.current_platform != "TikTok":  # Only if changing to a different view
            self.save_column_widths()
        
        # Disable sorting temporarily
        was_sorting_enabled = self.downloads_table.isSortingEnabled()
        self.downloads_table.setSortingEnabled(False)
        
        # Save current selection before clearing
        selected_rows = set()
        for index in self.downloads_table.selectedIndexes():
            selected_rows.add(index.row())
        
        # Clear current content
        self.downloads_table.clearContents()
        self.downloads_table.setRowCount(0)
        
        # Configure table for TikTok
        self.downloads_table.setColumnCount(9)  # 9 columns for TikTok view (including hashtags)
        
        # Update column indices for TikTok view
        self.select_col = 0
        self.title_col = 1
        self.creator_col = 2
        self.quality_col = 3
        self.format_col = 4
        self.duration_col = 5
        self.size_col = 6
        self.hashtags_col = 7  # Show hashtags column for TikTok
        self.date_col = 8
        
        # Set header labels
        header_labels = [
            "",  # Selection checkbox
            self.tr_("HEADER_TITLE"),
            self.tr_("HEADER_CREATOR"),
            self.tr_("HEADER_QUALITY"),
            self.tr_("HEADER_FORMAT"),
            self.tr_("HEADER_DURATION"),
            self.tr_("HEADER_SIZE"),
            self.tr_("HEADER_HASHTAGS"),
            self.tr_("HEADER_COMPLETED_ON")
        ]
        self.downloads_table.setHorizontalHeaderLabels(header_labels)
        
        # Set column widths for TikTok view
        self.downloads_table.setColumnWidth(self.select_col, 30)      # Checkbox column
        self.downloads_table.setColumnWidth(self.title_col, 250)      # Title column
        self.downloads_table.setColumnWidth(self.creator_col, 120)    # Creator
        self.downloads_table.setColumnWidth(self.quality_col, 85)     # Quality
        self.downloads_table.setColumnWidth(self.format_col, 75)      # Format
        self.downloads_table.setColumnWidth(self.duration_col, 80)    # Duration
        self.downloads_table.setColumnWidth(self.size_col, 75)        # Size
        self.downloads_table.setColumnWidth(self.hashtags_col, 150)   # Hashtags
        self.downloads_table.setColumnWidth(self.date_col, 120)       # Date
        
        # Update current platform
        self.current_platform = "TikTok"
        
        # Calculate minimum column widths based on header text
        self.calculate_min_column_widths()
        
        # Set resize mode for columns
        self.downloads_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Select
        self.downloads_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Title - Stretch
        self.downloads_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)  # Creator
        self.downloads_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)  # Quality
        self.downloads_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)  # Format
        self.downloads_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)  # Duration
        self.downloads_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive)  # Size
        self.downloads_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Interactive)  # Hashtags
        self.downloads_table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.Interactive)  # Date
        
        # Load saved column widths if available
        self.load_column_widths()
        
        # Restore sorting if it was enabled
        if was_sorting_enabled:
            self.downloads_table.setSortingEnabled(True)
        
        # Update statistics
        self.update_statistics()
        
        print(f"DEBUG: Set up TikTok table columns with hashtags")

    def setup_default_table_columns(self):
        """Reset table to default columns with platform visible"""
        # Save current column widths before switching view
        if self.current_platform == "TikTok":  # Only if changing to a different view
            self.save_column_widths()
        
        # Disable sorting temporarily
        was_sorting_enabled = self.downloads_table.isSortingEnabled()
        self.downloads_table.setSortingEnabled(False)
        
        # Save current selection before clearing
        selected_rows = set()
        for index in self.downloads_table.selectedIndexes():
            selected_rows.add(index.row())
        
        # Clear current content
        self.downloads_table.clearContents()
        self.downloads_table.setRowCount(0)
        
        # Configure table for default view
        self.downloads_table.setColumnCount(9)  # 9 columns for default view with platform
        
        # Reset column indices to default
        self.select_col = 0
        self.platform_col = 1
        self.title_col = 2
        self.creator_col = 3
        self.quality_col = 4
        self.format_col = 5
        self.duration_col = 6
        self.size_col = 7
        self.hashtags_col = -1  # Not shown directly
        self.date_col = 8
        
        # Set header labels
        header_labels = [
            "",  # Selection checkbox
            self.tr_("LABEL_PLATFORM"),
            self.tr_("HEADER_TITLE"),
            self.tr_("HEADER_CREATOR"),
            self.tr_("HEADER_QUALITY"),
            self.tr_("HEADER_FORMAT"),
            self.tr_("HEADER_DURATION"),
            self.tr_("HEADER_SIZE"), 
            self.tr_("HEADER_COMPLETED_ON")
        ]
        self.downloads_table.setHorizontalHeaderLabels(header_labels)
        
        # Set column widths
        self.downloads_table.setColumnWidth(self.select_col, 30)      # Checkbox column
        self.downloads_table.setColumnWidth(self.platform_col, 100)   # Platform column
        self.downloads_table.setColumnWidth(self.title_col, 250)      # Title column
        self.downloads_table.setColumnWidth(self.creator_col, 100)
        self.downloads_table.setColumnWidth(self.quality_col, 85)     # Quality
        self.downloads_table.setColumnWidth(self.format_col, 75)      # Format
        self.downloads_table.setColumnWidth(self.duration_col, 80)    # Duration
        self.downloads_table.setColumnWidth(self.size_col, 75)        # Size
        self.downloads_table.setColumnWidth(self.date_col, 120)       # Date
        
        # Update current platform
        self.current_platform = ""  # Empty string means "All" platforms
        
        # Calculate minimum column widths based on header text
        self.calculate_min_column_widths()
        
        # Set resize mode for columns
        self.downloads_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Select
        self.downloads_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)  # Platform
        self.downloads_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Title - Stretch
        self.downloads_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)  # Creator
        self.downloads_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)  # Quality
        self.downloads_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)  # Format
        self.downloads_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive)  # Duration
        self.downloads_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Interactive)  # Size
        self.downloads_table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.Interactive)  # Date
        
        # Load saved column widths if available
        self.load_column_widths()
        
        # Restore sorting if it was enabled
        if was_sorting_enabled:
            self.downloads_table.setSortingEnabled(True)
        
        # Update statistics
        self.update_statistics()
        
        print(f"DEBUG: Reset to default table columns")

    def save_column_widths(self):
        """Save current column widths to app settings"""
        try:
            # Read existing config
            config_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')
            config = {}
            
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
            
            # Create or update column_widths section in config
            if 'column_widths' not in config:
                config['column_widths'] = {}
            
            # Store width for each column based on current view
            column_widths = {}
            header = self.downloads_table.horizontalHeader()
            
            # Save ALL column widths, including the checkbox column
            for i in range(self.downloads_table.columnCount()):
                column_widths[str(i)] = header.sectionSize(i)
            
            print(f"DEBUG: Saving column widths for {self.current_platform}: {column_widths}")
            
            # Store different widths for different views
            if self.current_platform == "TikTok":
                config['column_widths']['tiktok'] = column_widths
            elif self.current_platform == "YouTube":
                config['column_widths']['youtube'] = column_widths
            elif self.current_platform == "All":
                config['column_widths']['all'] = column_widths
            else:
                # Default fallback
                config['column_widths']['all'] = column_widths
            
            # Save updated config
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=4)
                
            return True
        except Exception as e:
            print(f"Error saving column widths: {e}")
            return False
    
    def load_column_widths(self):
        """Load column widths from app settings"""
        try:
            # Read existing config
            config_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')
            
            if not os.path.exists(config_file):
                print("DEBUG: Config file does not exist, using default column widths")
                return
            
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Check if column_widths section exists
            if 'column_widths' not in config:
                print("DEBUG: No column_widths in config, using default column widths")
                return
                
            # Determine which set of widths to use
            widths_key = None
            if self.current_platform == "TikTok" and 'tiktok' in config['column_widths']:
                widths_key = 'tiktok'
            elif self.current_platform == "YouTube" and 'youtube' in config['column_widths']:
                widths_key = 'youtube'
            elif (self.current_platform == "" or self.current_platform == "All") and 'all' in config['column_widths']:
                widths_key = 'all'
            
            if not widths_key:
                print(f"DEBUG: No column_widths for {self.current_platform} view, using default column widths")
                return
            
            # Load width for each column
            column_widths = config['column_widths'][widths_key]
            print(f"DEBUG: Loading column widths for {widths_key} view: {column_widths}")
            
            header = self.downloads_table.horizontalHeader()
            
            # Block signals temporarily to avoid triggering resizing events
            header.blockSignals(True)
            
            for col_str, width in column_widths.items():
                col = int(col_str)
                if col < self.downloads_table.columnCount():
                    # Always respect minimum width constraints
                    header_item = self.downloads_table.horizontalHeaderItem(col)
                    min_width = 0
                    if header_item:
                        min_width = header_item.data(Qt.ItemDataRole.UserRole) or 0
                    
                    # Only apply if the saved width is greater than the minimum width
                    if width >= min_width:
                        header.resizeSection(col, width)
                        print(f"DEBUG: Set column {col} width to {width}")
                    else:
                        print(f"DEBUG: Saved width {width} is less than minimum {min_width}, using minimum")
                        header.resizeSection(col, min_width)
            
            # Unblock signals
            header.blockSignals(False)
            
            return True
        except Exception as e:
            print(f"Error loading column widths: {e}")
            return False
    
    def set_platform(self, platform):
        """Set current platform and filter videos accordingly"""
        # Save current column widths before changing platform
        self.save_column_widths()
        
        if platform == "All":
            self.current_platform = "All"  # Thiết lập là "All" thay vì None
            print("DEBUG: Showing all platforms")
            self.filter_videos()  # This will reset to show all videos
            self.update_table_headers()  # Update headers for default view
            self.status_bar.showMessage(self.tr_("STATUS_SHOWING_ALL_PLATFORMS"))
        else:
            self.current_platform = platform
            print(f"DEBUG: Filtering videos by platform: {platform}")
            self.filter_by_platform(platform)
            
            # Special case for TikTok to show hashtags column
            if platform == "TikTok":
                self.setup_tiktok_table_columns()
            elif platform == "YouTube":
                self.setup_youtube_table_columns()
            else:
                self.setup_default_table_columns()
                
        # Load column widths for the new platform
        self.load_column_widths()

    def closeEvent(self, event):
        """Called when tab is closed"""
        # Save column widths before closing
        self.save_column_widths()
        
        # Close any open popup dialogs
        if hasattr(self, 'copy_dialog') and self.copy_dialog and self.copy_dialog.isVisible():
            self.copy_dialog.close()
            
        # Continue with normal close event
        super().closeEvent(event)

    def setup_youtube_table_columns(self):
        """Set up table columns specifically for YouTube"""
        print(f"DEBUG: >>> setup_youtube_table_columns called, current_platform={self.current_platform}")
        # Save current column widths before switching view
        if self.current_platform != "YouTube":  # Only if changing to a different view
            self.save_column_widths()
        
        # Disable sorting temporarily
        was_sorting_enabled = self.downloads_table.isSortingEnabled()
        self.downloads_table.setSortingEnabled(False)
        
        # Save current selection before clearing
        selected_rows = set()
        for index in self.downloads_table.selectedIndexes():
            selected_rows.add(index.row())
        
        # Clear current content
        self.downloads_table.clearContents()
        self.downloads_table.setRowCount(0)
        
        # Configure table for YouTube
        self.downloads_table.setColumnCount(10)  # 10 columns for YouTube view (including playlist and release date)
        
        # Update column indices for YouTube view
        self.select_col = 0
        self.title_col = 1
        self.creator_col = 2       # Channel in YouTube context
        self.playlist_col = 3      # New column for YouTube
        self.quality_col = 4
        self.format_col = 5
        self.duration_col = 6
        self.size_col = 7
        self.release_date_col = 8  # New column for YouTube
        self.date_col = 9
        
        # Set header labels
        header_labels = [
            "",  # Selection checkbox
            self.tr_("HEADER_TITLE"),
            self.tr_("HEADER_CHANNEL"),      # Channel instead of Creator
            self.tr_("HEADER_PLAYLIST"),     # New column
            self.tr_("HEADER_QUALITY"),
            self.tr_("HEADER_FORMAT"),
            self.tr_("HEADER_DURATION"),
            self.tr_("HEADER_SIZE"),
            self.tr_("HEADER_RELEASE_DATE"), # New column
            self.tr_("HEADER_COMPLETED_ON")
        ]
        self.downloads_table.setHorizontalHeaderLabels(header_labels)
        
        # Set column widths for YouTube view
        self.downloads_table.setColumnWidth(self.select_col, 30)          # Checkbox column
        self.downloads_table.setColumnWidth(self.title_col, 250)          # Title column
        self.downloads_table.setColumnWidth(self.creator_col, 120)        # Channel name
        self.downloads_table.setColumnWidth(self.playlist_col, 120)       # Playlist
        self.downloads_table.setColumnWidth(self.quality_col, 85)         # Quality
        self.downloads_table.setColumnWidth(self.format_col, 75)          # Format
        self.downloads_table.setColumnWidth(self.duration_col, 80)        # Duration
        self.downloads_table.setColumnWidth(self.size_col, 75)            # Size
        self.downloads_table.setColumnWidth(self.release_date_col, 120)   # Release Date
        self.downloads_table.setColumnWidth(self.date_col, 120)           # Download Date
        
        # Update current platform
        self.current_platform = "YouTube"
        
        # Calculate minimum column widths based on header text
        self.calculate_min_column_widths()
        
        # Set resize mode for columns
        self.downloads_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Select
        self.downloads_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Title - Stretch
        self.downloads_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)  # Channel
        self.downloads_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)  # Playlist
        self.downloads_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)  # Quality
        self.downloads_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)  # Format
        self.downloads_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive)  # Duration
        self.downloads_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Interactive)  # Size
        self.downloads_table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.Interactive)  # Release Date
        self.downloads_table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeMode.Interactive)  # Download Date
        
        # Load saved column widths if available
        self.load_column_widths()
        
        # Restore sorting if it was enabled
        if was_sorting_enabled:
            self.downloads_table.setSortingEnabled(True)
        
        # Update statistics
        self.update_statistics()
        
        print(f"DEBUG: <<< YouTube table columns set up with playlist and release date")
