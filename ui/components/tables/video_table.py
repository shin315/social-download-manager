"""
VideoTable Base Component

Base video table with common functionality for displaying video information.
Implements TableInterface and integrates with BaseTab architecture.
"""

from typing import List, Dict, Any, Optional, Callable
from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMenu, QApplication, QStyle
)
from PyQt6.QtCore import Qt, pyqtSignal, QModelIndex
from PyQt6.QtGui import QFont, QPixmap, QIcon

from ..common.interfaces import TableInterface
from ..common import QWidgetABCMeta
from ..common.models import TableConfig, ColumnConfig, SortConfig, SortOrder
from ..mixins.language_support import LanguageSupport
from ..mixins.theme_support import ThemeSupport

class VideoTable(QTableWidget, TableInterface,
                LanguageSupport, ThemeSupport, metaclass=QWidgetABCMeta):
    """Base video table with common functionality"""
    
    # Signals from TableInterface
    selection_changed = pyqtSignal(list)  # Selected items
    item_action_requested = pyqtSignal(str, object)  # Action, item
    sort_changed = pyqtSignal(SortConfig)  # Sort configuration
    
    # Additional convenience signals
    context_menu_requested = pyqtSignal(int, int, object)  # Row, column, item
    double_clicked = pyqtSignal(object)  # Item data
    
    def __init__(self, config: TableConfig, parent=None, lang_manager=None):
        # Initialize parent classes in the correct order
        super().__init__(parent)  # This calls QTableWidget.__init__
        LanguageSupport.__init__(self, "VideoTable", lang_manager)
        ThemeSupport.__init__(self, "VideoTable")
        
        # Store configuration
        self.config = config
        
        # Data storage
        self._original_data: List[Dict[str, Any]] = []
        self._display_data: List[Dict[str, Any]] = []
        self._item_data_map: Dict[int, Dict[str, Any]] = {}  # Row -> data mapping
        
        # Selection tracking
        self._selected_rows: set = set()
        self._last_selected_items: List[Any] = []
        
        # Context menu
        self._context_menu: Optional[QMenu] = None
        self._context_actions: Dict[str, Callable] = {}
        
        # Initialize state
        self._init_state()
        
        # Setup UI
        self.setup_ui()
        
        # Connect signals
        self._connect_signals()
    
    def _init_state(self):
        """Initialize component state"""
        # Set default sort
        self._current_sort = SortConfig(
            column=self.config.default_sort_column,
            order=self.config.default_sort_order
        )
    
    def setup_ui(self):
        """Setup table UI based on configuration"""
        # Initialize table with configuration
        self.setup_table(self.config)
        
        # Set visual properties
        self._setup_visual_properties()
        
        # Enable context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    
    def _setup_visual_properties(self):
        """Setup visual properties of the table"""
        # Row height
        self.verticalHeader().setDefaultSectionSize(self.config.row_height)
        self.verticalHeader().hide()  # Hide row numbers
        
        # Grid and styling
        self.setShowGrid(True)
        self.setGridStyle(Qt.PenStyle.SolidLine)
        self.setAlternatingRowColors(True)
        
        # Selection behavior
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
        # Headers
        horizontal_header = self.horizontalHeader()
        horizontal_header.setStretchLastSection(False)
        horizontal_header.setSectionsMovable(False)
        
        # Performance optimizations
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    
    def _connect_signals(self):
        """Connect internal signals"""
        # Selection changes
        self.itemSelectionChanged.connect(self._on_selection_changed)
        
        # Context menu
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        # Double click
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
        
        # Header click (for sorting)
        if self.config.sortable:
            self.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
    
    # =========================================================================
    # TableInterface Implementation
    # =========================================================================
    
    def setup_table(self, config: TableConfig) -> None:
        """Initialize table with configuration"""
        # Set column count
        self.setColumnCount(len(config.columns))
        self.setRowCount(0)
        
        # Configure headers
        self._setup_headers(config.columns)
        
        # Configure table behavior
        selection_mode = (
            QAbstractItemView.SelectionMode.MultiSelection if config.multi_select 
            else QAbstractItemView.SelectionMode.SingleSelection
        )
        self.setSelectionMode(selection_mode)
        
        # Configure sorting
        if config.sortable:
            self.setSortingEnabled(False)  # We handle sorting manually
    
    def _setup_headers(self, columns: List[ColumnConfig]):
        """Setup table headers"""
        header_labels = []
        for col in columns:
            header_labels.append(self.tr_(col.key))
        
        self.setHorizontalHeaderLabels(header_labels)
        
        # Configure column properties
        horizontal_header = self.horizontalHeader()
        for i, col in enumerate(columns):
            # Set width
            if col.width > 0:
                self.setColumnWidth(i, col.width)
            
            # Set resize mode
            if not col.resizable:
                horizontal_header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
            else:
                horizontal_header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
            
            # Set visibility
            if not col.visible:
                self.hideColumn(i)
    
    def set_data(self, items: List[Dict[str, Any]]) -> None:
        """Populate table with data"""
        self._original_data = items.copy()
        self._display_data = items.copy()
        
        # Apply current sort if any
        self._apply_sort()
        
        # Update table display
        self._update_table_display()
    
    def _update_table_display(self):
        """Update table display with current data"""
        # Clear existing data
        self.setRowCount(0)
        self._item_data_map.clear()
        
        # Add rows
        for row_index, item_data in enumerate(self._display_data):
            self._add_table_row(row_index, item_data)
    
    def _add_table_row(self, row_index: int, item_data: Dict[str, Any]):
        """Add a single row to the table"""
        self.insertRow(row_index)
        self._item_data_map[row_index] = item_data
        
        # Populate columns
        for col_index, column_config in enumerate(self.config.columns):
            value = item_data.get(column_config.name, "")
            item = self._create_table_item(value, column_config)
            self.setItem(row_index, col_index, item)
    
    def _create_table_item(self, value: Any, column_config: ColumnConfig) -> QTableWidgetItem:
        """Create a table item with proper formatting"""
        # Convert value to string
        display_text = self._format_cell_value(value, column_config)
        
        # Create item
        item = QTableWidgetItem(display_text)
        
        # Set data for sorting
        item.setData(Qt.ItemDataRole.UserRole, value)
        
        # Make non-editable
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        
        # Set tooltip for long text
        if len(display_text) > 50:
            item.setToolTip(display_text)
        
        return item
    
    def _format_cell_value(self, value: Any, column_config: ColumnConfig) -> str:
        """Format cell value for display"""
        if value is None:
            return ""
        
        # Handle different data types
        if isinstance(value, (int, float)):
            if column_config.name in ['duration', 'file_size']:
                return self._format_duration_or_size(value, column_config.name)
            return str(value)
        elif isinstance(value, bool):
            return "✓" if value else "✗"
        else:
            return str(value)
    
    def _format_duration_or_size(self, value: int, field_type: str) -> str:
        """Format duration or file size"""
        if field_type == 'duration':
            # Format seconds to HH:MM:SS
            hours = value // 3600
            minutes = (value % 3600) // 60
            seconds = value % 60
            if hours > 0:
                return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                return f"{minutes:02d}:{seconds:02d}"
        elif field_type == 'file_size':
            # Format bytes to human readable
            for unit in ['B', 'KB', 'MB', 'GB']:
                if value < 1024.0:
                    return f"{value:.1f} {unit}"
                value /= 1024.0
            return f"{value:.1f} TB"
        
        return str(value)
    
    def get_selected_items(self) -> List[Dict[str, Any]]:
        """Get currently selected items"""
        selected_items = []
        selected_rows = set()
        
        # Get selected row indices
        for item in self.selectedItems():
            selected_rows.add(item.row())
        
        # Get data for selected rows
        for row in selected_rows:
            if row in self._item_data_map:
                selected_items.append(self._item_data_map[row])
        
        return selected_items
    
    def clear_selection(self) -> None:
        """Clear all selections"""
        self.clearSelection()
        self._selected_rows.clear()
    
    def select_all(self) -> None:
        """Select all items"""
        self.selectAll()
    
    def get_sort_config(self) -> SortConfig:
        """Get current sort configuration"""
        return self._current_sort
    
    def apply_sort(self, sort_config: SortConfig) -> None:
        """Apply sort configuration"""
        self._current_sort = sort_config
        self._apply_sort()
        self._update_table_display()
        self.sort_changed.emit(sort_config)
    
    def _apply_sort(self):
        """Apply current sort to display data"""
        if not self._display_data or self._current_sort.column >= len(self.config.columns):
            return
        
        column_config = self.config.columns[self._current_sort.column]
        column_name = column_config.name
        
        # Sort data
        reverse_order = (self._current_sort.order == SortOrder.DESCENDING)
        
        try:
            self._display_data.sort(
                key=lambda item: item.get(column_name, ""),
                reverse=reverse_order
            )
        except TypeError:
            # Handle mixed types by converting to string
            self._display_data.sort(
                key=lambda item: str(item.get(column_name, "")),
                reverse=reverse_order
            )
    
    # =========================================================================
    # Event Handlers
    # =========================================================================
    
    def _on_selection_changed(self):
        """Handle selection changes"""
        selected_items = self.get_selected_items()
        
        # Only emit if selection actually changed
        if selected_items != self._last_selected_items:
            self._last_selected_items = selected_items
            self.selection_changed.emit(selected_items)
    
    def _on_header_clicked(self, logical_index: int):
        """Handle header click for sorting"""
        if not self.config.sortable or logical_index >= len(self.config.columns):
            return
        
        column_config = self.config.columns[logical_index]
        if not column_config.sortable:
            return
        
        # Toggle sort order if same column, otherwise use ascending
        if self._current_sort.column == logical_index:
            new_order = (
                SortOrder.DESCENDING if self._current_sort.order == SortOrder.ASCENDING
                else SortOrder.ASCENDING
            )
        else:
            new_order = SortOrder.ASCENDING
        
        # Apply new sort
        new_sort_config = SortConfig(column=logical_index, order=new_order)
        self.apply_sort(new_sort_config)
    
    def _on_item_double_clicked(self, item: QTableWidgetItem):
        """Handle item double click"""
        if item and item.row() in self._item_data_map:
            item_data = self._item_data_map[item.row()]
            self.double_clicked.emit(item_data)
    
    def _show_context_menu(self, position):
        """Show context menu at position"""
        item = self.itemAt(position)
        if not item:
            return
        
        row = item.row()
        column = item.column()
        item_data = self._item_data_map.get(row)
        
        if not item_data:
            return
        
        # Create context menu if not exists
        if not self._context_menu:
            self._create_context_menu()
        
        # Emit signal for external handling
        self.context_menu_requested.emit(row, column, item_data)
        
        # Show menu if it has actions
        if self._context_menu and self._context_menu.actions():
            self._context_menu.exec(self.mapToGlobal(position))
    
    def _create_context_menu(self):
        """Create default context menu"""
        self._context_menu = QMenu(self)
        
        # Add default actions
        self.add_context_action("copy", self.tr_("ACTION_COPY"), self._copy_selected)
        self.add_context_action("select_all", self.tr_("ACTION_SELECT_ALL"), self.select_all)
    
    # =========================================================================
    # Public API Methods
    # =========================================================================
    
    def add_context_action(self, action_id: str, text: str, callback: Callable):
        """Add action to context menu"""
        if not self._context_menu:
            self._create_context_menu()
        
        action = self._context_menu.addAction(text)
        action.triggered.connect(callback)
        self._context_actions[action_id] = callback
    
    def remove_context_action(self, action_id: str):
        """Remove action from context menu"""
        if action_id in self._context_actions:
            del self._context_actions[action_id]
            # Rebuild menu
            if self._context_menu:
                self._context_menu.clear()
                for aid, callback in self._context_actions.items():
                    action = self._context_menu.addAction(aid)
                    action.triggered.connect(callback)
    
    def get_all_data(self) -> List[Dict[str, Any]]:
        """Get all table data"""
        return self._original_data.copy()
    
    def get_display_data(self) -> List[Dict[str, Any]]:
        """Get currently displayed data (after sorting)"""
        return self._display_data.copy()
    
    def refresh(self):
        """Refresh table display"""
        self._update_table_display()
    
    def _copy_selected(self):
        """Copy selected items to clipboard"""
        selected_items = self.get_selected_items()
        if not selected_items:
            return
        
        # Create text representation
        lines = []
        for item in selected_items:
            line_parts = []
            for column_config in self.config.columns:
                value = item.get(column_config.name, "")
                line_parts.append(str(value))
            lines.append("\t".join(line_parts))
        
        # Copy to clipboard
        clipboard_text = "\n".join(lines)
        QApplication.clipboard().setText(clipboard_text)
    
    # =========================================================================
    # Language and Theme Support
    # =========================================================================
    
    def update_language(self):
        """Update UI for language changes"""
        super().update_language()
        
        # Update headers
        header_labels = []
        for col in self.config.columns:
            header_labels.append(self.tr_(col.key))
        self.setHorizontalHeaderLabels(header_labels)
        
        # Update context menu
        if self._context_menu:
            self._create_context_menu()
    
    def apply_theme(self, theme: Dict):
        """Apply theme to table"""
        super().apply_theme(theme)
        
        # Get table-specific theme settings
        table_theme = theme.get('videotable', {})
        
        # Apply table styling
        if 'table_style' in table_theme:
            self.setStyleSheet(table_theme['table_style'])
        
        # Apply header styling
        if 'header_style' in table_theme:
            self.horizontalHeader().setStyleSheet(table_theme['header_style'])


# =============================================================================
# Factory Functions
# =============================================================================

def create_video_info_table_config() -> TableConfig:
    """Create configuration for video info table"""
    columns = [
        ColumnConfig(0, "status", "COLUMN_STATUS", 80, sortable=True),
        ColumnConfig(1, "title", "COLUMN_TITLE", 300, sortable=True),
        ColumnConfig(2, "platform", "COLUMN_PLATFORM", 100, sortable=True),
        ColumnConfig(3, "duration", "COLUMN_DURATION", 100, sortable=True),
        ColumnConfig(4, "quality", "COLUMN_QUALITY", 100, sortable=True),
        ColumnConfig(5, "progress", "COLUMN_PROGRESS", 150, sortable=False),
    ]
    
    return TableConfig(
        columns=columns,
        sortable=True,
        filterable=False,
        multi_select=True,
        default_sort_column=0,
        default_sort_order=SortOrder.DESCENDING,
        row_height=60
    )

def create_downloaded_videos_table_config() -> TableConfig:
    """Create configuration for downloaded videos table"""
    columns = [
        ColumnConfig(0, "title", "COLUMN_TITLE", 250, sortable=True),
        ColumnConfig(1, "platform", "COLUMN_PLATFORM", 100, sortable=True),
        ColumnConfig(2, "download_date", "COLUMN_DOWNLOAD_DATE", 150, sortable=True),
        ColumnConfig(3, "file_size", "COLUMN_FILE_SIZE", 100, sortable=True),
        ColumnConfig(4, "quality", "COLUMN_QUALITY", 100, sortable=True),
        ColumnConfig(5, "file_path", "COLUMN_FILE_PATH", 200, sortable=True),
    ]
    
    return TableConfig(
        columns=columns,
        sortable=True,
        filterable=True,
        multi_select=True,
        default_sort_column=2,  # Sort by download date
        default_sort_order=SortOrder.DESCENDING,
        row_height=50
    ) 