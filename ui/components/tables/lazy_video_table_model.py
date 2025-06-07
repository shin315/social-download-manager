"""
Lazy Video Table Model for Performance Optimization

Advanced QAbstractTableModel implementation providing:
- Database-backed lazy loading with LIMIT/OFFSET queries
- Progressive data fetching based on scroll position  
- Server-side sorting and filtering to reduce memory usage
- Efficient caching with LRU strategy for loaded pages
- Integration with video processing and selection pipelines

Part of Task 15.1 - Lazy Loading Implementation
"""

import math
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Callable
from PyQt6.QtCore import (
    QAbstractTableModel, QModelIndex, Qt, pyqtSignal, QTimer, QThread, QObject
)
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtWidgets import QApplication

# Import database and component dependencies
from utils.db_manager import DatabaseManager
# from ui.components.common.performance_monitor import PerformanceMonitor
# from ui.components.common.events import get_event_bus, EventType


class LazyPageCache:
    """LRU cache for loaded table pages with memory management"""
    
    def __init__(self, max_pages: int = 10):
        self.max_pages = max_pages
        self.pages: Dict[int, List[Dict[str, Any]]] = {}
        self.access_order: List[int] = []
        self.total_rows: int = 0
        
    def get_page(self, page_num: int) -> Optional[List[Dict[str, Any]]]:
        """Get page data if cached"""
        if page_num in self.pages:
            # Update LRU order
            self.access_order.remove(page_num)
            self.access_order.append(page_num)
            return self.pages[page_num]
        return None
    
    def set_page(self, page_num: int, data: List[Dict[str, Any]]):
        """Cache page data with LRU eviction"""
        # Remove if already exists
        if page_num in self.pages:
            self.access_order.remove(page_num)
        
        # Evict oldest if at capacity
        elif len(self.pages) >= self.max_pages:
            oldest_page = self.access_order.pop(0)
            del self.pages[oldest_page]
        
        # Add new page
        self.pages[page_num] = data
        self.access_order.append(page_num)
    
    def clear(self):
        """Clear all cached pages"""
        self.pages.clear()
        self.access_order.clear()
        self.total_rows = 0
    
    def has_page(self, page_num: int) -> bool:
        """Check if page is cached"""
        return page_num in self.pages
    
    def get_cached_pages(self) -> List[int]:
        """Get list of cached page numbers"""
        return list(self.pages.keys())


class DatabaseQueryWorker(QObject):
    """Background worker for database queries"""
    
    data_loaded = pyqtSignal(int, list, int)  # page_num, data, total_count
    error_occurred = pyqtSignal(str)  # error_message
    
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
    
    def load_page(self, page_num: int, page_size: int, filters: Optional[Dict] = None,
                  sort_column: Optional[str] = None, sort_order: Optional[str] = None):
        """Load page data from database"""
        try:
            offset = page_num * page_size
            
            # Build query with filters and sorting
            query_params = {
                'limit': page_size,
                'offset': offset,
                'filters': filters or {},
                'sort_column': sort_column,
                'sort_order': sort_order
            }
            
            # Get videos from database
            videos_data = self.db_manager.get_downloaded_videos_paginated(**query_params)
            
            # Get total count for pagination
            total_count = self.db_manager.get_downloaded_videos_count(filters=filters)
            
            self.data_loaded.emit(page_num, videos_data, total_count)
            
        except Exception as e:
            self.error_occurred.emit(f"Database query error: {e}")


class LazyVideoTableModel(QAbstractTableModel):
    """
    High-performance lazy loading table model for video data.
    
    Features:
    - Database-backed pagination with configurable page size
    - Progressive loading based on scroll position
    - Server-side sorting and filtering
    - LRU page caching for smooth scrolling
    - Background query execution
    """
    
    # Signals for UI updates
    data_loading = pyqtSignal(bool)  # loading_state
    page_loaded = pyqtSignal(int)    # page_number
    error_occurred = pyqtSignal(str) # error_message
    total_rows_changed = pyqtSignal(int)  # new_total
    
    # Column definitions (matching existing table structure)
    COLUMNS = [
        {'key': 'select', 'name': 'Select', 'width': 50},
        {'key': 'title', 'name': 'Title', 'width': 250},
        {'key': 'creator', 'name': 'Creator', 'width': 120},
        {'key': 'quality', 'name': 'Quality', 'width': 80},
        {'key': 'format', 'name': 'Format', 'width': 80},
        {'key': 'size', 'name': 'Size', 'width': 80},
        {'key': 'status', 'name': 'Status', 'width': 90},
        {'key': 'date', 'name': 'Date', 'width': 120},
        {'key': 'hashtags', 'name': 'Hashtags', 'width': 150},
        {'key': 'actions', 'name': 'Actions', 'width': 130}
    ]
    
    def __init__(self, page_size: int = 100, buffer_pages: int = 2, parent=None):
        super().__init__(parent)
        
        # Configuration
        self.page_size = page_size
        self.buffer_pages = buffer_pages  # Pages to preload around visible area
        
        # Data management
        self.page_cache = LazyPageCache(max_pages=10)
        self.total_rows = 0
        self.loaded_pages: set = set()
        self.loading_pages: set = set()
        
        # Filtering and sorting
        self.active_filters: Dict[str, Any] = {}
        self.sort_column: Optional[str] = None
        self.sort_order: Optional[str] = None
        
        # Background worker
        self.worker_thread = QThread()
        self.query_worker = DatabaseQueryWorker()
        self.query_worker.moveToThread(self.worker_thread)
        
        # Connect worker signals
        self.query_worker.data_loaded.connect(self._on_page_loaded)
        self.query_worker.error_occurred.connect(self._on_query_error)
        
        self.worker_thread.start()
        
        # Performance monitoring
        # self.performance_monitor = PerformanceMonitor()
        
        # Fetch throttling
        self.fetch_timer = QTimer()
        self.fetch_timer.setSingleShot(True)
        self.fetch_timer.timeout.connect(self._process_fetch_queue)
        self.fetch_queue: set = set()
        
        # Event bus integration
        # self.event_bus = get_event_bus()
    
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return total number of rows"""
        return self.total_rows
    
    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return number of columns"""
        return len(self.COLUMNS)
    
    def headerData(self, section: int, orientation: Qt.Orientation, 
                   role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Return header data"""
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            if 0 <= section < len(self.COLUMNS):
                return self.COLUMNS[section]['name']
        return None
    
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Return data for given index"""
        if not index.isValid():
            return None
        
        row = index.row()
        column = index.column()
        
        # Check if we need to load this page
        page_num = row // self.page_size
        if not self.page_cache.has_page(page_num):
            self._request_page_load(page_num)
            return None  # Return None while loading
        
        # Get data from cache
        page_data = self.page_cache.get_page(page_num)
        if not page_data:
            return None
        
        # Calculate row within page
        row_in_page = row % self.page_size
        if row_in_page >= len(page_data):
            return None
        
        video_data = page_data[row_in_page]
        
        if role == Qt.ItemDataRole.DisplayRole:
            return self._get_display_data(video_data, column)
        elif role == Qt.ItemDataRole.UserRole:
            return video_data  # Return full video data
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            return self._get_text_alignment(column)
        
        return None
    
    def _get_display_data(self, video_data: Dict[str, Any], column: int) -> str:
        """Get display text for column"""
        if column >= len(self.COLUMNS):
            return ""
        
        column_key = self.COLUMNS[column]['key']
        
        # Map database fields to display values
        field_mapping = {
            'select': '',  # Handled by delegate
            'title': video_data.get('title', ''),
            'creator': video_data.get('creator', ''),
            'quality': video_data.get('quality', ''),
            'format': video_data.get('format', ''),
            'size': video_data.get('file_size', ''),
            'status': video_data.get('status', ''),
            'date': self._format_date(video_data.get('download_date')),
            'hashtags': ', '.join(video_data.get('hashtags', [])),
            'actions': ''  # Handled by delegate
        }
        
        return field_mapping.get(column_key, '')
    
    def _get_text_alignment(self, column: int) -> Qt.AlignmentFlag:
        """Get text alignment for column"""
        # Center alignment for specific columns
        center_columns = ['select', 'quality', 'format', 'size', 'status', 'actions']
        if column < len(self.COLUMNS):
            column_key = self.COLUMNS[column]['key']
            if column_key in center_columns:
                return Qt.AlignmentFlag.AlignCenter
        return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    
    def _format_date(self, date_value: Any) -> str:
        """Format date for display"""
        if not date_value:
            return ""
        
        try:
            if isinstance(date_value, str):
                date_obj = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            elif isinstance(date_value, datetime):
                date_obj = date_value
            else:
                return str(date_value)
            
            return date_obj.strftime("%m/%d/%Y\n%H:%M:%S")
        except Exception:
            return str(date_value)
    
    def canFetchMore(self, parent: QModelIndex = QModelIndex()) -> bool:
        """Check if more data can be fetched"""
        if self.total_rows == 0:
            return True  # Initial load
        
        total_pages = math.ceil(self.total_rows / self.page_size)
        return len(self.loaded_pages) < total_pages
    
    def fetchMore(self, parent: QModelIndex = QModelIndex()):
        """Fetch more data (triggered by view)"""
        if not self.canFetchMore():
            return
        
        # Calculate which pages to load
        visible_pages = self._get_visible_pages()
        for page_num in visible_pages:
            if page_num not in self.loaded_pages and page_num not in self.loading_pages:
                self._request_page_load(page_num)
    
    def _get_visible_pages(self) -> List[int]:
        """Get list of pages that should be loaded based on visible area"""
        # This will be called by the view to determine visible pages
        # For now, return next unloaded page
        total_pages = math.ceil(self.total_rows / self.page_size) if self.total_rows > 0 else 1
        
        for page_num in range(total_pages):
            if page_num not in self.loaded_pages:
                return [page_num]
        
        return []
    
    def _request_page_load(self, page_num: int):
        """Request loading of a specific page"""
        if page_num in self.loading_pages or page_num in self.loaded_pages:
            return
        
        # Add to fetch queue for throttling
        self.fetch_queue.add(page_num)
        
        # Start throttled fetch timer
        if not self.fetch_timer.isActive():
            self.fetch_timer.start(50)  # 50ms throttle
    
    def _process_fetch_queue(self):
        """Process queued page fetch requests"""
        if not self.fetch_queue:
            return
        
        # Load multiple pages in batch
        pages_to_load = list(self.fetch_queue)[:3]  # Load up to 3 pages at once
        self.fetch_queue.clear()
        
        for page_num in pages_to_load:
            if page_num not in self.loading_pages:
                self.loading_pages.add(page_num)
                self.data_loading.emit(True)
                
                # Execute query in worker thread
                self.query_worker.load_page(
                    page_num=page_num,
                    page_size=self.page_size,
                    filters=self.active_filters,
                    sort_column=self.sort_column,
                    sort_order=self.sort_order
                )
    
    def _on_page_loaded(self, page_num: int, data: List[Dict[str, Any]], total_count: int):
        """Handle page data loaded from worker"""
        self.loading_pages.discard(page_num)
        
        # Update total rows if changed
        if total_count != self.total_rows:
            old_total = self.total_rows
            self.total_rows = total_count
            
            # Emit model change signals
            if old_total == 0:
                self.beginInsertRows(QModelIndex(), 0, total_count - 1)
                self.endInsertRows()
            else:
                self.beginResetModel()
                self.endResetModel()
            
            self.total_rows_changed.emit(total_count)
        
        # Cache the page data
        self.page_cache.set_page(page_num, data)
        self.loaded_pages.add(page_num)
        
        # Calculate row range for this page
        start_row = page_num * self.page_size
        end_row = min(start_row + len(data) - 1, self.total_rows - 1)
        
        # Emit data changed for loaded rows
        if end_row >= start_row:
            top_left = self.index(start_row, 0)
            bottom_right = self.index(end_row, self.columnCount() - 1)
            self.dataChanged.emit(top_left, bottom_right)
        
        self.page_loaded.emit(page_num)
        
        # Check if all loading is complete
        if not self.loading_pages:
            self.data_loading.emit(False)
    
    def _on_query_error(self, error_message: str):
        """Handle query error from worker"""
        self.loading_pages.clear()
        self.data_loading.emit(False)
        self.error_occurred.emit(error_message)
    
    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder):
        """Sort model data"""
        if column >= len(self.COLUMNS):
            return
        
        column_key = self.COLUMNS[column]['key']
        
        # Skip sorting for non-sortable columns
        if column_key in ['select', 'actions']:
            return
        
        # Map column to database field
        db_field_mapping = {
            'title': 'title',
            'creator': 'creator', 
            'quality': 'quality',
            'format': 'format',
            'size': 'file_size',
            'status': 'status',
            'date': 'download_date',
            'hashtags': 'hashtags'
        }
        
        db_field = db_field_mapping.get(column_key)
        if not db_field:
            return
        
        self.sort_column = db_field
        self.sort_order = 'ASC' if order == Qt.SortOrder.AscendingOrder else 'DESC'
        
        # Clear cache and reload data
        self.refresh_data()
    
    def set_filters(self, filters: Dict[str, Any]):
        """Apply filters to the model"""
        if filters != self.active_filters:
            self.active_filters = filters.copy()
            self.refresh_data()
    
    def refresh_data(self):
        """Refresh all data by clearing cache and reloading"""
        self.beginResetModel()
        
        # Clear all cached data
        self.page_cache.clear()
        self.loaded_pages.clear()
        self.loading_pages.clear()
        self.fetch_queue.clear()
        
        # Reset row count
        self.total_rows = 0
        
        self.endResetModel()
        
        # Load first page
        self._request_page_load(0)
    
    def get_video_data(self, row: int) -> Optional[Dict[str, Any]]:
        """Get full video data for a specific row"""
        page_num = row // self.page_size
        page_data = self.page_cache.get_page(page_num)
        
        if page_data:
            row_in_page = row % self.page_size
            if row_in_page < len(page_data):
                return page_data[row_in_page]
        
        return None
    
    def request_visible_pages(self, first_visible_row: int, last_visible_row: int):
        """Request loading of pages for visible rows"""
        first_page = first_visible_row // self.page_size
        last_page = last_visible_row // self.page_size
        
        # Load visible pages plus buffer
        for page_num in range(
            max(0, first_page - self.buffer_pages),
            min(math.ceil(self.total_rows / self.page_size), last_page + self.buffer_pages + 1)
        ):
            if page_num not in self.loaded_pages:
                self._request_page_load(page_num)
    
    def cleanup(self):
        """Cleanup resources"""
        if self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait(3000)  # Wait up to 3 seconds
        
        self.page_cache.clear()
        self.fetch_timer.stop() 