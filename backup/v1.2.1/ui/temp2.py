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
