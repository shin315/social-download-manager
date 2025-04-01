from utils.language_manager import LanguageManager
from utils.file_utils import human_readable_size


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
        self.header_sort_initialized = False  # Flag to track if header sort has been initialized
        
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
            self.tr_("HEADER_TITLE"), 
            self.tr_("HEADER_CREATOR"), 
            self.tr_("HEADER_QUALITY"), 
            self.tr_("HEADER_FORMAT"), 
            self.tr_("HEADER_SIZE"), 
            self.tr_("HEADER_STATUS"), 
            self.tr_("HEADER_DATE"), 
            self.tr_("HEADER_HASHTAGS"), 
            self.tr_("HEADER_ACTIONS")
        ]
        self.downloads_table.setHorizontalHeaderLabels(headers)
        
    def update_table_buttons(self):
        """Update buttons in the table"""
        for row in range(self.downloads_table.rowCount()):
            # Get widget in the Action column
            action_widget = self.downloads_table.cellWidget(row, 9)
            if action_widget:
                # Find buttons in the widget
                for child in action_widget.findChildren(QPushButton):
                    # Update based on current button text
                    if "Open" in child.text() or "Mở" in child.text():
                        child.setText(self.tr_("BUTTON_OPEN"))
                    elif "Delete" in child.text() or "Xóa" in child.text():
                        child.setText(self.tr_("BUTTON_DELETE"))

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

    def create_downloads_table(self):
        """Create the downloads table widget"""
        self.downloads_table = QTableWidget()
        self.downloads_table.setObjectName("downloads_table")
        
        # Set up table properties
        self.downloads_table.setColumnCount(10)
        self.downloads_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.downloads_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.downloads_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.downloads_table.verticalHeader().setVisible(False)
        
        # Enable sorting but we'll handle it ourselves
        self.downloads_table.setSortingEnabled(False)
        
        # Set column headers
        self.download_table_headers = [
            # (name, width%, tooltip, is_filter_enabled)
            ("", 3, "", False),  # Select column (checkbox)
            ("Title", 22, "Title of the video", True),
            ("Creator", 14, "Creator/Author of the video", True),
            ("Quality", 7, "Video quality", True),
            ("Format", 6, "File format", True),
            ("Size", 8, "File size", True),
            ("Status", 8, "Download status", True),
            ("Date", 13, "Download date", True),
            ("Hashtags", 12, "Video hashtags", True),
            ("Actions", 7, "Available actions", False)
        ]
        self.update_table_headers()
        
        # Set font for header
        header_font = self.downloads_table.horizontalHeader().font()
        header_font.setBold(True)
        self.downloads_table.horizontalHeader().setFont(header_font)
        
        # Set width for columns (optimized to give title column more space)
        self.downloads_table.setColumnWidth(0, 30)     # Select
        self.downloads_table.setColumnWidth(1, 260)    # Title - reduced slightly to make room for other columns
        self.downloads_table.setColumnWidth(2, 85)     # Creator - slight reduction
        self.downloads_table.setColumnWidth(3, 90)     # Quality - increased to fully display "Quality"
        self.downloads_table.setColumnWidth(4, 80)     # Format - reduced
        self.downloads_table.setColumnWidth(5, 85)     # Size - increased to fully display "Size"
        self.downloads_table.setColumnWidth(6, 80)     # Status - reduced since it only displays "Successful"
        self.downloads_table.setColumnWidth(7, 100)    # Date - slight reduction
        self.downloads_table.setColumnWidth(8, 90)     # Hashtags - slight reduction
        self.downloads_table.setColumnWidth(9, 130)    # Actions - slight reduction, enough for 2 buttons
        
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
        
        # Set the initial sort indicator FIRST, before connecting events
        header = self.downloads_table.horizontalHeader()
        header.setSortIndicatorShown(True)
        print(f"DEBUG: Setting initial sort indicator to column {self.sort_column} with order {self.sort_order}")
        header.setSortIndicator(self.sort_column, self.sort_order)
        
        # Connect header click event for sorting - AFTER setting the indicator
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self.sort_table)
        
        # Add tooltip for filterable headers
        filterable_columns = [3, 4, 6, 7]  # Quality, Format, Status, Date
        
        # Set tooltips for filterable columns
        for i in filterable_columns:
            header_item = self.downloads_table.horizontalHeaderItem(i)
            if header_item:
                tooltip_text = self.tr_("TOOLTIP_FILTER_BY").format(header_item.text())
                header_item.setToolTip(tooltip_text)
        
        # Enable context menu
        self.downloads_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.downloads_table.customContextMenuRequested.connect(self.show_context_menu)
        
        # Enable header context menu for filtering
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        header.customContextMenuRequested.connect(self.show_header_context_menu)
        
        # Connect cell clicked event
        self.downloads_table.cellClicked.connect(self.handle_cell_clicked)
        
        # Connect selection changed event
        selection_model = self.downloads_table.selectionModel()
        selection_model.selectionChanged.connect(self.handle_selection_changed)
        
        # Connect double click on cells to copy dialog
        self.downloads_table.itemDoubleClicked.connect(self.show_copy_dialog)
        
        # Connect cell hover event for tooltips
        self.downloads_table.setMouseTracking(True)
        self.downloads_table.cellEntered.connect(self.show_full_text_tooltip)
        
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
        
        # Set header sort initialized to true
        self.header_sort_initialized = True
        
        return self.downloads_table

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
        """Handle click event outside of video in the table"""
        if obj == self.downloads_table.viewport() and event.type() == event.Type.MouseButtonPress:
            item = self.downloads_table.itemAt(event.pos())
            if not item:  # Click on empty space
                # Hide details area and show donate area
                self.video_details_frame.setVisible(False)
                # Không set selected_video = None để còn giữ thông tin video đã chọn
                # self.selected_video = None
        return super().eventFilter(obj, event)

    def handle_selection_changed(self, selected, deselected):
        """Handle event when selection in table changes"""
        # Get selected rows
        indexes = selected.indexes()
        if not indexes:
            return
            
        # Get row of first selected item
        row = indexes[0].row()
        
        # Display detailed information of video if row is valid
        if row >= 0 and row < len(self.filtered_videos):
            video = self.filtered_videos[row]
            
            # Kiểm tra nếu video này đã được chọn trước đó và đang hiển thị chi tiết
            if self.selected_video == video:
                # Nếu hiện tại không hiển thị, thì hiển thị lại
                if not self.video_details_frame.isVisible():
                    self.video_details_frame.setVisible(True)
                # Trường hợp đã hiển thị rồi thì không cần làm gì
            else:
                # Video mới được chọn, cập nhật selected_video và hiển thị chi tiết
                self.selected_video = video
                self.video_details_frame.setVisible(True)
                self.update_selected_video_details(video)
            
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
        
    def filter_videos(self):
        """Filter videos based on filters and search keywords"""
        if not hasattr(self, 'all_videos'):
            return
            
        # Start with all videos
        filtered_videos = self.all_videos.copy()
        
        # Apply filtering by search keywords if any
        search_text = self.search_input.text().strip().lower()
        if search_text:
            # Create non-accented version of search keyword
            search_text_no_accent = self.remove_vietnamese_accents(search_text).lower()
            
            # Filter videos by keyword (supporting both accented and non-accented)
            filtered_videos = []
            for video in self.all_videos:
                # Check each field in the video
                match_found = False
                for value in video:
                    if isinstance(value, (str, int, float)):
                        str_value = str(value).lower()
                        str_value_no_accent = self.remove_vietnamese_accents(str_value).lower()
                        
                        # Check accented version
                        if search_text in str_value:
                            match_found = True
                            break
                            
                        # Check non-accented version
                        if search_text_no_accent in str_value_no_accent:
                            match_found = True
                            break
                
                if match_found:
                    filtered_videos.append(video)
        
        # Mapping from UI column index to data index in video list
        column_mapping = {
            1: 0,   # Title
            2: 1,   # Creator
            3: 2,   # Quality
            4: 3,   # Format
            5: 4,   # Size
            6: 5,   # Status
            7: 6,   # Date
            8: 7    # Hashtags
        }
        
        # Debug to see all active filters
        print(f"DEBUG: Active filters: {self.active_filters}")
        
        # Apply active filters
        for ui_column_index, filter_value in self.active_filters.items():
            # Only process columns in mapping
            if ui_column_index in column_mapping:
                data_index = column_mapping[ui_column_index]
                
                # Special case for Date column
                date_column_ui_index = self.get_column_index_by_name(self.tr_("HEADER_DATE"))
                if ui_column_index == date_column_ui_index and isinstance(filter_value, tuple) and len(filter_value) == 3:
                    start_date, end_date, filter_name = filter_value
                    
                    # Debug output
                    print(f"DEBUG: Filtering by date range: {filter_name} - {start_date} to {end_date}")
                    print(f"DEBUG: Date column UI index: {ui_column_index}, data index: {data_index}")
                    
                    # Filter videos by date range
                    before_count = len(filtered_videos)
                    filtered_videos = [
                        video for video in filtered_videos
                        if self.is_date_in_range(video[data_index], start_date, end_date)
                    ]
                    after_count = len(filtered_videos)
                    
                    # Show number of videos filtered out
                    print(f"DEBUG: Date filter resulted in {before_count - after_count} videos filtered out")
                    print(f"DEBUG: First few dates to check: {[video[data_index] for video in self.all_videos[:5]]}")
                else:
                    # Regular filtering - only keep videos with values matching the filter
                    print(f"DEBUG: Normal filter on column {ui_column_index} (data index {data_index}): '{filter_value}'")
                    
                    # Create non-accented version of filter_value
                    filter_value_lower = str(filter_value).lower()
                    filter_value_no_accent = self.remove_vietnamese_accents(filter_value_lower)
                    
                    # Filter videos by value (supporting both accented and non-accented)
                    before_count = len(filtered_videos)
                    filtered_videos = [
                        video for video in filtered_videos
                        if (str(video[data_index]).lower() == filter_value_lower) or 
                           (self.remove_vietnamese_accents(str(video[data_index])).lower() == filter_value_no_accent)
                    ]
                    after_count = len(filtered_videos)
                    
                    # Show number of videos filtered out
                    print(f"DEBUG: Normal filter resulted in {before_count - after_count} videos filtered out")
            else:
                print(f"DEBUG: Column index {ui_column_index} not in mapping, skipping")
        
        # Save filtered list
        self.filtered_videos = filtered_videos
        print(f"DEBUG: Final filtered videos count: {len(filtered_videos)}")
        
        # Display filtered list
        self.display_videos(filtered_videos)
        
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
            # Clear old data
            self.all_videos = []
            self.filtered_videos = []
            
            # Clear current filters
            self.active_filters = {}
            self.update_all_filter_icons()
            
            # Get data from database
            db_manager = DatabaseManager()
            downloads = db_manager.get_downloads()
            
            if not downloads:
                print("No downloads found in database")
                return
                
            print(f"Loaded {len(downloads)} videos from database")
            
            # Process each downloaded record
            for download in downloads:
                # Process hashtags - ensure they are displayed with #
                hashtags = download.get('hashtags', [])
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
                    download.get('thumbnail', '')                # 11 - Thumbnail
                ]
                self.all_videos.append(video_info)
            
            # Update filtered_videos list
            self.filtered_videos = self.all_videos.copy()
            
            # Make sure header_sort_initialized is reset
            self.header_sort_initialized = False
            
            # Map UI column to data column for initial sort
            column_mapping = {
                0: 0,  # Select (no sorting)
                1: 0,  # Title (index 0 in filtered_videos)
                2: 1,  # Creator (index 1 in filtered_videos)
                3: 2,  # Quality (index 2 in filtered_videos)
                4: 3,  # Format (index 3 in filtered_videos)
                5: 4,  # Size (index 4 in filtered_videos)
                6: 5,  # Status (index 5 in filtered_videos)
                7: 6,  # Date (index 6 in filtered_videos)
                8: 7,  # Hashtags (index 7 in filtered_videos)
                9: 8   # Action (no sorting)
            }
            
            # Sort videos based on default sort_column and sort_order
            data_column = column_mapping.get(self.sort_column, 6)  # Default to Date (6) if mapping fails
            print(f"DEBUG: Initial sort using UI column {self.sort_column} mapped to data column {data_column}")
            self.sort_videos(data_column)
            
            # Force update the sort indicator in case it wasn't set
            if hasattr(self, 'downloads_table') and self.downloads_table:
                print(f"DEBUG: Forcing sort indicator update to column {self.sort_column}")
                self.downloads_table.horizontalHeader().setSortIndicator(self.sort_column, self.sort_order)
            
            # Display list of videos
            self.display_videos()
            
            # Update statistics
            self.update_statistics()
            
            print(f"Loaded {len(self.all_videos)} videos")
            
        except Exception as e:
            print(f"Error loading downloaded videos: {e}")
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_ERROR").format(str(e)))

    def display_videos(self, videos=None):
        """Display list of downloaded videos in the table"""
        # Debug: Check videos and original_title
        for idx, video in enumerate(videos[:3] if videos else []):  # Debug only first 3 videos to avoid excessive logging
            has_original = len(video) > 9 and video[9]
            original_value = video[9] if len(video) > 9 else "N/A"
            print(f"DEBUG - Video {idx}: has_original={has_original}, title='{video[0]}', original_title='{original_value}'")
        
        if videos is None:
            videos = self.filtered_videos
            
        # Clear current content and set new row count
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
            
            # Title column
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
            self.downloads_table.setItem(idx, 1, title_item)
            
            # Creator column
            creator_item = QTableWidgetItem(video[1])
            creator_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # Disable editing
            creator_item.setFlags(creator_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.downloads_table.setItem(idx, 2, creator_item)
            
            # Quality column
            quality_item = QTableWidgetItem(video[2])
            quality_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # Disable editing
            quality_item.setFlags(quality_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.downloads_table.setItem(idx, 3, quality_item)
            
            # Format column
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
            self.downloads_table.setItem(idx, 4, format_item)
            
            # Size column
            size_item = QTableWidgetItem(video[4])
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # Disable editing
            size_item.setFlags(size_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.downloads_table.setItem(idx, 5, size_item)
            
            # Status column
            status_value = video[5]  
            # Ensure status is always "Successful" if file exists
            filepath = os.path.join(video[8], video[0]) if video[8] and video[0] else ""
            if filepath and os.path.exists(filepath):
                status_value = "Successful"
            elif status_value == "Download successful":
                status_value = "Successful"
            status_item = QTableWidgetItem(status_value)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # Disable editing
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.downloads_table.setItem(idx, 6, status_item)
            
            # Date column
            date_item = QTableWidgetItem(video[6])
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # Disable editing
            date_item.setFlags(date_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.downloads_table.setItem(idx, 7, date_item)
            
            # Hashtags column - ensure there's a #
            hashtags = video[7]
            # If hashtags don't have a #, add one
            if hashtags and not hashtags.startswith('#'):
                if ' ' in hashtags and not '#' in hashtags:
                    hashtags = ' '.join(['#' + tag.strip() for tag in hashtags.split()])
            
            hashtags_item = QTableWidgetItem(hashtags)
            hashtags_item.setToolTip(hashtags)  # Tooltip when hovered
            # Set text elision (ellipsis) to false to display full text
            hashtags_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            # Set word wrap to true to allow text to wrap if necessary
            hashtags_item.setFlags(hashtags_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.downloads_table.setItem(idx, 8, hashtags_item)
            
            # Action (Open and Delete) column
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0, 0, 0, 0)
            
            # Open button
            open_btn = QPushButton(self.tr_("BUTTON_OPEN"))
            open_btn.clicked.connect(lambda checked, r=idx: self.open_folder_and_select(videos[r][10] if len(videos[r]) > 10 else videos[r][8], r))
            action_layout.addWidget(open_btn)
            
            # Delete button
            delete_btn = QPushButton(self.tr_("BUTTON_DELETE"))
            delete_btn.clicked.connect(lambda checked, r=idx: self.delete_video_and_select(r))
            action_layout.addWidget(delete_btn)
            
            self.downloads_table.setCellWidget(idx, 9, action_widget)
        
        # Update total number of videos displayed (only total number of videos)
        if hasattr(self, 'total_videos_label'):
            self.total_videos_label.setText(self.tr_("LABEL_TOTAL_VIDEOS").format(len(self.all_videos)))
        
        # Hide details area of video if no video is selected
        if len(self.filtered_videos) == 0 and hasattr(self, 'video_details_frame'):
            self.video_details_frame.setVisible(False)
            self.selected_video = None
        
        # Update button states after displaying videos
        self.update_button_states()
        
        # Update Select All/Unselect All button state
        self.update_select_toggle_button()
        
        # Update the video count label
        self.update_video_count_label()

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
                    # Open Explorer and select file
                    path = path.replace('/', '\\')  # Ensure path is in Windows format
                    print(f"DEBUG - Using explorer /select,{path}")
                    os.system(f'explorer /select,"{path}"')
                else:
                    # Just open the folder
                    os.startfile(folder_path)
            elif os.name == 'darwin':  # macOS
                if is_file and os.path.exists(path):
                    # Open Finder and select file
                    subprocess.run(['open', '-R', path], check=True)
                else:
                    # Just open the folder
                    subprocess.run(['open', folder_path], check=True)
            else:  # Linux and other operating systems
                # Try using common file managers on Linux
                if is_file and os.path.exists(path):
                    # Try with nautilus (GNOME)
                    try:
                        subprocess.run(['nautilus', '--select', path], check=True)
                    except:
                        try:
                            # Try with dolphin (KDE)
                            subprocess.run(['dolphin', '--select', path], check=True)
                        except:
                            try:
                                # Try with thunar (XFCE)
                                subprocess.run(['thunar', path], check=True)
                            except:
                                # If no file manager works, open the folder
                                subprocess.run(['xdg-open', folder_path], check=True)
                else:
                    # Just open the folder
                    subprocess.run(['xdg-open', folder_path], check=True)
                    
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
        delete_file_checkbox.setChecked(file_exists)
        
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
            
            # Display the newly loaded video list
            self.display_videos()
            
            # Hide video details if currently displayed
            self.video_details_frame.setVisible(False)
            self.selected_video = None
            
            # Update Select All/Unselect All button state
            self.update_select_toggle_button()
            
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
        filterable_columns = [3, 4, 6, 7]  # Quality, Format, Status, Date (excluding Size)
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
                download_info.get('thumbnail', '')               # 11 - Thumbnail
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
        print(f"DEBUG: sort_table called with column {column}")
        print(f"DEBUG: Current sort_column={self.sort_column}, sort_order={self.sort_order}")
        
        # Determine correct column mapping to match the index in self.filtered_videos
        # The display column order and the index in filtered_videos may differ
        column_mapping = {
            0: 0,  # Select (no sorting)
            1: 0,  # Title (index 0 in filtered_videos)
            2: 1,  # Creator (index 1 in filtered_videos)
            3: 2,  # Quality (index 2 in filtered_videos)
            4: 3,  # Format (index 3 in filtered_videos)
            5: 4,  # Size (index 4 in filtered_videos)
            6: 5,  # Status (index 5 in filtered_videos)
            7: 6,  # Date (index 6 in filtered_videos)
            8: 7,  # Hashtags (index 7 in filtered_videos)
            9: 8   # Action (no sorting)
        }
        
        # Only allow sorting on columns: Title(1), Creator(2), Quality(3), Format(4), Size(5), Date(7)
        # Skip other columns: Select(0), Status(6), Hashtags(8), Actions(9)
        sortable_columns = [1, 2, 3, 4, 5, 7]
        if column not in sortable_columns:
            print(f"DEBUG: Column {column} is not sortable")
            return
            
        # Map UI column to data column
        data_column = column_mapping[column]
        print(f"DEBUG: Mapped UI column {column} to data column {data_column}")
            
        # Reverse the sort order if clicking on the same column
        if self.sort_column == column:
            self.sort_order = Qt.SortOrder.DescendingOrder if self.sort_order == Qt.SortOrder.AscendingOrder else Qt.SortOrder.AscendingOrder
            print(f"DEBUG: Same column clicked, changing sort order to {self.sort_order}")
        else:
            self.sort_column = column
            self.sort_order = Qt.SortOrder.AscendingOrder
            print(f"DEBUG: New column clicked, setting sort_column={self.sort_column}, sort_order={self.sort_order}")
        
        # Force sort indicator on, in case it was toggled off
        self.downloads_table.horizontalHeader().setSortIndicatorShown(True)
        
        # Update the sort indicator manually to match our sorting
        print(f"DEBUG: Setting sort indicator to column {self.sort_column} with order {self.sort_order}")
        self.downloads_table.horizontalHeader().setSortIndicator(self.sort_column, self.sort_order)
        
        # Set our sort initialized flag
        self.header_sort_initialized = True
        
        # Sort the video list with the mapped column
        self.sort_videos(data_column)
        
        # Display the list again
        self.display_videos()

    def sort_videos(self, column):
        """Sort the video list by column"""
        print(f"DEBUG: sort_videos called with data column {column}")
        
        def get_sort_key(video):
            value = video[column]
            
            if column == 2:  # Quality
                # Convert quality to number for sorting
                quality_order = {
                    "1080p": 10,
                    "720p": 9,
                    "480p": 8,
                    "360p": 7,
                    "320kbps": 3,  # Audio quality
                    "192kbps": 2,
                    "128kbps": 1,
                    "Unknown": 0
                }
                return quality_order.get(value, 0)
            
            elif column == 3:  # Format
                # Sort format (MP4 first, MP3 second)
                format_order = {
                    "MP4": 1,
                    "MP3": 2,
                    "Video (mp4)": 1,  # For backward compatibility
                    "Audio (mp3)": 2,  # For backward compatibility
                    "Unknown": 3
                }
                return format_order.get(value, 3)
                
            elif column == 4:  # Size
                try:
                    # Convert MB, KB to numbers
                    if 'MB' in value:
                        return float(value.replace('MB', '').strip())
                    elif 'KB' in value:
                        return float(value.replace('KB', '').strip()) / 1024
                    return 0
                except Exception as e:
                    print(f"Error converting size: {e}")
                    return 0
                    
            elif column == 0 or column == 1:  # Title or Creator
                # Normalize text before sorting
                try:
                    return unicodedata.normalize('NFKD', value.lower())
                except Exception as e:
                    print(f"Error normalizing text: {e}")
                    return value.lower()
                    
            # Default sort text case-insensitively
            if isinstance(value, str):
                return value.lower()
            return value
        
        # Sort the list
        try:
            is_descending = (self.sort_order == Qt.SortOrder.DescendingOrder)
            print(f"DEBUG: Sorting videos, is_descending={is_descending}")
            self.filtered_videos.sort(key=get_sort_key, reverse=is_descending)
            
            # Make sure the sort indicator is properly set
            self.header_sort_initialized = True
            print(f"DEBUG: After sorting, header_sort_initialized={self.header_sort_initialized}")
        except Exception as e:
            print(f"Error sorting videos: {e}")

    def show_full_text_tooltip(self, row, column):
        """Show tooltip with full text when hovering over a cell"""
        # Only show tooltip for text columns
        if column in [1, 2, 8]:  # Title, Creator, Hashtags columns
            item = self.downloads_table.item(row, column)
            if item and 0 <= row < len(self.filtered_videos):
                video = self.filtered_videos[row]
                tooltip_text = ""
                
                # Process tooltip based on column type
                if column == 1:  # Title
                    # If full title is available show it, otherwise show short title
                    if len(video) > 9 and video[9]:
                        tooltip_text = video[9]
                    else:
                        tooltip_text = video[0]
                elif column == 2:  # Creator
                    # Display full creator name
                    tooltip_text = f"Creator: {video[1]}"
                elif column == 8:  # Hashtags
                    # Display full hashtags with proper formatting
                    if video[7]:
                        # Clean hashtag data for better display
                        hashtags = video[7]
                        # Convert to a list of hashtags for better readability
                        if ' ' in hashtags and not all(tag.startswith('#') for tag in hashtags.split()):
                            tooltip_text = ' '.join(['#' + tag.strip() if not tag.strip().startswith('#') else tag.strip() 
                                           for tag in hashtags.split()])
                        else:
                            tooltip_text = hashtags
                    else:
                        tooltip_text = "No hashtags"
                
                # Format tooltip text for better readability
                if tooltip_text:
                    formatted_text = self.format_tooltip_text(tooltip_text)
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
                        # If "Apply to all" is not checked, show error message
                        if not apply_all_checkbox.isChecked():
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
            self.display_videos()
            
            # Show notification
            if self.parent:
                if deleted_files_count > 0:
                    self.parent.status_bar.showMessage(self.tr_("STATUS_VIDEOS_AND_FILES_DELETED").format(deleted_count, deleted_files_count))
                    print(f"Deleted {deleted_count} videos, {deleted_files_count} video files, and {deleted_thumbnails_count} thumbnails")
                else:
                    self.parent.status_bar.showMessage(self.tr_("STATUS_VIDEOS_DELETED").format(deleted_count))

        # Display filtered video list again
        self.load_downloaded_videos()
        self.display_videos()
        
        # Update button states
        self.update_button_states()

    def toggle_select_all(self):
        """Select or deselect all videos"""
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
        # Get current row and column position
        index = self.downloads_table.indexAt(position)
        
        if not index.isValid():
            return
            
        row = index.row()
        column = index.column()
            
        if row < 0 or row >= self.downloads_table.rowCount():
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
            context_menu.exec(QCursor.pos())

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
        
        # No style applied as it's handled in main_window.py
        print("DEBUG: update_button_states in downloaded_videos_tab - button states updated without applying style")

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
            3: 2,  # Quality (index 2 in filtered_videos)
            4: 3,  # Format (index 3 in filtered_videos)
            5: 4,  # Size (index 4 in filtered_videos)
            6: 5,  # Status (index 5 in filtered_videos)
            7: 6,  # Date (index 6 in filtered_videos)
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
        """Show context menu for header to filter"""
        # Get column index from click position
        index = self.downloads_table.horizontalHeader().logicalIndexAt(pos)
        
        # Show menu only for columns that can be filtered
        filterable_columns = [3, 4, 6, 7]  # Quality, Format, Status, Date (excluding Size)
        
        if index in filterable_columns:
            # Handle special case for Date column
            if index == 7:  # Date column
                self.show_date_filter_menu(pos)
                return
                
            # Get list of unique values for this column
            unique_values = self.get_unique_column_values(index)
            
            # Show filter menu
            filter_menu = FilterPopup(self, index, unique_values, self.downloads_table.horizontalHeaderItem(index).text())
            filter_menu.filterChanged.connect(self.apply_column_filter)
            
            # Show menu at cursor position
            header_pos = self.downloads_table.horizontalHeader().mapToGlobal(pos)
            filter_menu.exec(header_pos)
            
    def show_date_filter_menu(self, pos):
        """Show filter menu for date with different options"""
        # Find index of Date column
        date_column_index = self.get_column_index_by_name(self.tr_("HEADER_DATE"))
        if date_column_index == -1:
            date_column_index = 7  # Fallback to default
        
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
        
        date_column_index = self.get_column_index_by_name(self.tr_("HEADER_DATE"))
        print(f"DEBUG: Date column index: {date_column_index}, Date header: {self.tr_('HEADER_DATE')}")
        
        if date_column_index == -1:
            date_column_index = 7  # Default date column index if not found
            print(f"DEBUG: Using default date column index: {date_column_index}")
        
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
            start_date = now.replace(day=now.day-1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now.replace(day=now.day-1, hour=23, minute=59, second=59, microsecond=999999)
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
            column_name = self.downloads_table.horizontalHeaderItem(column_index).text().replace(" 🔍", "")
            
            # If it's a Date column, there might be special handling
            if column_name == self.tr_("HEADER_DATE"):
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
        # Kiểm tra row có hợp lệ không
        if row >= 0 and row < len(self.filtered_videos):
            video = self.filtered_videos[row]
            
            # Nếu đã có thông tin video đã chọn và trùng khớp với video hiện tại
            if self.selected_video == video:
                # Hiển thị lại hộp thông tin chi tiết nếu nó đang bị ẩn
                if not self.video_details_frame.isVisible():
                    self.video_details_frame.setVisible(True)
                    # Không cần cập nhật lại thông tin vì thông tin đã được cập nhật khi chọn trước đó
            else:
                # Video mới được chọn, cập nhật trong handle_selection_changed
                pass
