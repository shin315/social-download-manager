"""
Lazy Video Table View with Scroll-Based Loading

High-performance QTableView implementation providing:
- Scroll position monitoring for progressive data loading
- Integrated delegate management for custom widgets
- Selection handling with batch operations
- Smooth scrolling optimizations for large datasets
- Memory-efficient rendering with viewport culling

Part of Task 15.1 - Lazy Loading Implementation
"""

import math
from typing import List, Dict, Any, Optional, Set
from PyQt6.QtCore import (
    Qt, QModelIndex, pyqtSignal, QTimer, QRect, QPoint
)
from PyQt6.QtGui import QWheelEvent, QKeyEvent, QPaintEvent
from PyQt6.QtWidgets import (
    QTableView, QHeaderView, QAbstractItemView, QScrollBar,
    QMenu, QApplication, QWidget
)

from .lazy_video_table_model import LazyVideoTableModel
from .lazy_video_delegate import (
    VideoSelectionDelegate, VideoActionsDelegate, VideoStatusDelegate,
    VideoDateDelegate, VideoThumbnailDelegate, VideoProgressDelegate
)
# from ui.components.common.performance_monitor import PerformanceMonitor
# from ui.components.common.events import get_event_bus, EventType


class LazyVideoTableView(QTableView):
    """
    High-performance table view with lazy loading capabilities.
    
    Features:
    - Progressive data loading based on scroll position
    - Custom delegates for rich UI elements
    - Optimized rendering for large datasets
    - Integrated selection and action handling
    - Smooth scrolling with momentum
    """
    
    # Signals for parent integration
    video_selected = pyqtSignal(dict)           # video_data
    videos_selected = pyqtSignal(list)          # [video_data]
    selection_changed = pyqtSignal(int)         # selected_count
    action_requested = pyqtSignal(str, int, dict)  # action, row, video_data
    loading_state_changed = pyqtSignal(bool)   # is_loading
    
    def __init__(self, page_size: int = 100, parent=None):
        super().__init__(parent)
        
        # Configuration
        self.page_size = page_size
        self.buffer_threshold = 10  # Rows before end to trigger loading
        
        # State management
        self.selected_rows: Set[int] = set()
        self.last_visible_range = (0, 0)
        self.is_loading = False
        
        # Performance monitoring
        # self.performance_monitor = PerformanceMonitor()
        
        # Scroll monitoring
        self.scroll_timer = QTimer()
        self.scroll_timer.setSingleShot(True)
        self.scroll_timer.timeout.connect(self._on_scroll_settled)
        
        # Initialize model and delegates
        self._setup_model()
        self._setup_delegates()
        self._setup_ui()
        self._connect_signals()
        
        # Event bus integration
        # self.event_bus = get_event_bus()
    
    def _setup_model(self):
        """Initialize the lazy loading model"""
        self.lazy_model = LazyVideoTableModel(
            page_size=self.page_size,
            buffer_pages=2,
            parent=self
        )
        self.setModel(self.lazy_model)
        
        # Connect model signals
        self.lazy_model.data_loading.connect(self._on_model_loading)
        self.lazy_model.page_loaded.connect(self._on_page_loaded)
        self.lazy_model.error_occurred.connect(self._on_model_error)
        self.lazy_model.total_rows_changed.connect(self._on_total_rows_changed)
    
    def _setup_delegates(self):
        """Setup custom delegates for each column"""
        # Selection checkbox delegate
        self.selection_delegate = VideoSelectionDelegate(self)
        self.selection_delegate.selection_changed.connect(self._on_selection_changed)
        self.setItemDelegateForColumn(0, self.selection_delegate)
        
        # Status delegate with color coding
        self.status_delegate = VideoStatusDelegate(self)
        self.setItemDelegateForColumn(6, self.status_delegate)  # Status column
        
        # Date delegate with multi-line format
        self.date_delegate = VideoDateDelegate(self)
        self.setItemDelegateForColumn(7, self.date_delegate)  # Date column
        
        # Actions delegate
        self.actions_delegate = VideoActionsDelegate(self)
        self.actions_delegate.open_requested.connect(
            lambda row: self._on_action_requested('open', row)
        )
        self.actions_delegate.delete_requested.connect(
            lambda row: self._on_action_requested('delete', row)
        )
        self.setItemDelegateForColumn(9, self.actions_delegate)  # Actions column
        
        # Progress delegate for loading states
        self.progress_delegate = VideoProgressDelegate(self)
        # Applied to all columns for loading indication
    
    def _setup_ui(self):
        """Configure table view UI properties"""
        # Selection behavior
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        
        # Scrolling optimizations
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        
        # Visual properties
        self.setAlternatingRowColors(True)
        self.setShowGrid(True)
        self.setSortingEnabled(True)
        
        # Header configuration
        header = self.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionsMovable(False)
        header.setSortIndicatorShown(True)
        
        # Set column widths from model
        for i, column in enumerate(self.lazy_model.COLUMNS):
            self.setColumnWidth(i, column['width'])
        
        # Configure resize modes
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)   # Select
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) # Title
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)   # Creator
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)   # Quality
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)   # Format
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)   # Size
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)   # Status
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)   # Date
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)   # Hashtags
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.Fixed)   # Actions
        
        # Row height
        self.verticalHeader().setDefaultSectionSize(35)
        self.verticalHeader().hide()
        
        # Context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
    
    def _connect_signals(self):
        """Connect internal signals"""
        # Scroll monitoring
        self.verticalScrollBar().valueChanged.connect(self._on_scroll_changed)
        
        # Selection handling
        self.selectionModel().selectionChanged.connect(self._on_table_selection_changed)
        
        # Header sorting
        header = self.horizontalHeader()
        header.sortIndicatorChanged.connect(self._on_sort_changed)
    
    def _on_scroll_changed(self, value: int):
        """Handle scroll position changes"""
        # Throttle scroll events
        self.scroll_timer.start(100)  # 100ms delay
        
        # Calculate visible range
        visible_range = self._get_visible_row_range()
        
        # Check if we need to load more data
        if visible_range != self.last_visible_range:
            self.last_visible_range = visible_range
            self._request_visible_data()
    
    def _on_scroll_settled(self):
        """Handle scroll settling after throttle period"""
        visible_range = self._get_visible_row_range()
        self.lazy_model.request_visible_pages(visible_range[0], visible_range[1])
    
    def _get_visible_row_range(self) -> tuple:
        """Calculate currently visible row range"""
        viewport_rect = self.viewport().rect()
        
        # Get first visible row
        first_visible = self.rowAt(viewport_rect.top())
        if first_visible < 0:
            first_visible = 0
        
        # Get last visible row
        last_visible = self.rowAt(viewport_rect.bottom())
        if last_visible < 0:
            last_visible = self.lazy_model.rowCount() - 1
        
        return (first_visible, last_visible)
    
    def _request_visible_data(self):
        """Request data for visible area plus buffer"""
        first_visible, last_visible = self.last_visible_range
        
        # Add buffer around visible area
        buffer_size = self.buffer_threshold
        start_row = max(0, first_visible - buffer_size)
        end_row = min(
            self.lazy_model.rowCount() - 1,
            last_visible + buffer_size
        )
        
        # Request pages for this range
        self.lazy_model.request_visible_pages(start_row, end_row)
    
    def _on_model_loading(self, is_loading: bool):
        """Handle model loading state changes"""
        self.is_loading = is_loading
        self.loading_state_changed.emit(is_loading)
        
        # Update cursor to indicate loading
        if is_loading:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        else:
            QApplication.restoreOverrideCursor()
    
    def _on_page_loaded(self, page_num: int):
        """Handle page loaded from model"""
        # Update viewport to show newly loaded data
        self.viewport().update()
        
        # Emit performance metrics
        # self.performance_monitor.track_event('page_loaded', {'page': page_num})
    
    def _on_model_error(self, error_message: str):
        """Handle model errors"""
        print(f"Model error: {error_message}")  # TODO: Proper error handling
    
    def _on_total_rows_changed(self, new_total: int):
        """Handle total row count changes"""
        # Update scrollbar range
        self.verticalScrollBar().setMaximum(
            max(0, new_total - self.viewport().height() // self.rowHeight(0))
        )
    
    def _on_selection_changed(self, row: int, checked: bool):
        """Handle individual row selection changes"""
        if checked:
            self.selected_rows.add(row)
        else:
            self.selected_rows.discard(row)
        
        self.selection_changed.emit(len(self.selected_rows))
        
        # Emit selected videos data
        selected_videos = []
        for row in self.selected_rows:
            video_data = self.lazy_model.get_video_data(row)
            if video_data:
                selected_videos.append(video_data)
        
        self.videos_selected.emit(selected_videos)
    
    def _on_table_selection_changed(self, selected, deselected):
        """Handle table selection model changes"""
        current_index = self.currentIndex()
        if current_index.isValid():
            video_data = self.lazy_model.get_video_data(current_index.row())
            if video_data:
                self.video_selected.emit(video_data)
    
    def _on_action_requested(self, action: str, row: int):
        """Handle action button clicks"""
        video_data = self.lazy_model.get_video_data(row)
        if video_data:
            self.action_requested.emit(action, row, video_data)
    
    def _on_sort_changed(self, logical_index: int, order: Qt.SortOrder):
        """Handle column header sorting"""
        # Model will handle the sorting
        self.lazy_model.sort(logical_index, order)
    
    def _show_context_menu(self, position: QPoint):
        """Show context menu for right-click"""
        index = self.indexAt(position)
        if not index.isValid():
            return
        
        video_data = self.lazy_model.get_video_data(index.row())
        if not video_data:
            return
        
        menu = QMenu(self)
        
        # Add context menu actions
        open_action = menu.addAction("Open File")
        open_action.triggered.connect(
            lambda: self.action_requested.emit('open', index.row(), video_data)
        )
        
        copy_title_action = menu.addAction("Copy Title")
        copy_title_action.triggered.connect(
            lambda: self._copy_to_clipboard(video_data.get('title', ''))
        )
        
        menu.addSeparator()
        
        delete_action = menu.addAction("Delete Video")
        delete_action.triggered.connect(
            lambda: self.action_requested.emit('delete', index.row(), video_data)
        )
        
        # Show menu
        menu.exec(self.mapToGlobal(position))
    
    def _copy_to_clipboard(self, text: str):
        """Copy text to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
    
    def wheelEvent(self, event: QWheelEvent):
        """Handle wheel events for smooth scrolling"""
        # Apply momentum scrolling
        delta = event.angleDelta().y()
        
        # Scroll with pixel precision
        scroll_amount = int(delta / 8)  # Reduce scroll speed
        current_value = self.verticalScrollBar().value()
        new_value = current_value - scroll_amount
        
        self.verticalScrollBar().setValue(new_value)
        
        event.accept()
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard navigation"""
        if event.key() == Qt.Key.Key_Space:
            # Toggle selection of current row
            current_index = self.currentIndex()
            if current_index.isValid():
                row = current_index.row()
                # Toggle selection checkbox
                checkbox_index = self.lazy_model.index(row, 0)
                current_state = checkbox_index.data(Qt.ItemDataRole.UserRole + 1) or False
                self.lazy_model.setData(checkbox_index, not current_state, Qt.ItemDataRole.UserRole + 1)
        else:
            super().keyPressEvent(event)
    
    def apply_filters(self, filters: Dict[str, Any]):
        """Apply filters to the model"""
        self.lazy_model.set_filters(filters)
    
    def refresh_data(self):
        """Refresh all data"""
        self.selected_rows.clear()
        self.lazy_model.refresh_data()
    
    def get_selected_videos(self) -> List[Dict[str, Any]]:
        """Get list of selected video data"""
        selected_videos = []
        for row in self.selected_rows:
            video_data = self.lazy_model.get_video_data(row)
            if video_data:
                selected_videos.append(video_data)
        return selected_videos
    
    def select_all_visible(self):
        """Select all videos in visible area"""
        first_visible, last_visible = self._get_visible_row_range()
        
        for row in range(first_visible, last_visible + 1):
            checkbox_index = self.lazy_model.index(row, 0)
            self.lazy_model.setData(checkbox_index, True, Qt.ItemDataRole.UserRole + 1)
            self.selected_rows.add(row)
        
        self.selection_changed.emit(len(self.selected_rows))
    
    def clear_selection(self):
        """Clear all selections"""
        for row in list(self.selected_rows):
            checkbox_index = self.lazy_model.index(row, 0)
            self.lazy_model.setData(checkbox_index, False, Qt.ItemDataRole.UserRole + 1)
        
        self.selected_rows.clear()
        self.selection_changed.emit(0)
    
    def cleanup(self):
        """Cleanup resources"""
        if hasattr(self, 'lazy_model'):
            self.lazy_model.cleanup()
        
        if hasattr(self, 'scroll_timer'):
            self.scroll_timer.stop() 