"""
Virtual Table Model System

Comprehensive Qt-based virtual table implementation for handling massive video collections:
- QAbstractItemModel with virtual data loading
- Dynamic data fetching with beginFetchRows/endFetchRows
- Integration with database pagination and background processing
- Memory-efficient data virtualization
- Custom filtering and sorting for large datasets

Part of Task 15.6 - Virtual Table Mode
"""

import os
import sys
import time
import threading
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Set, Union, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from abc import ABC, abstractmethod

# Qt imports
try:
    from PyQt6.QtCore import (
        QAbstractTableModel, QAbstractItemModel, QModelIndex, Qt, QVariant,
        QSortFilterProxyModel, QIdentityProxyModel, pyqtSignal, QObject,
        QTimer, QThread, QMutex, QMutexLocker, QSize, QRect
    )
    from PyQt6.QtGui import QPixmap, QIcon, QFont, QColor, QPalette
    from PyQt6.QtWidgets import QTableView, QHeaderView, QAbstractItemView
    HAS_QT = True
except ImportError:
    print("PyQt6 not available - virtual table disabled")
    HAS_QT = False
    
    # Fallback implementations
    class MockQAbstractTableModel:
        def __init__(self):
            pass
        
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
    
    class MockQModelIndex:
        def __init__(self):
            self.valid = True
        
        def isValid(self):
            return self.valid
        
        def row(self):
            return 0
        
        def column(self):
            return 0
    
    # Mock Qt classes
    QAbstractTableModel = MockQAbstractTableModel
    QModelIndex = MockQModelIndex
    QSortFilterProxyModel = object
    QIdentityProxyModel = object
    QObject = object
    pyqtSignal = lambda *args: lambda func: func

# Integration imports
try:
    from core.database.advanced_pagination import AdvancedDatabasePaginator
    HAS_PAGINATION = True
except ImportError:
    HAS_PAGINATION = False

try:
    from core.background.task_manager import get_task_manager, TaskPriority
    HAS_BACKGROUND = True
except ImportError:
    HAS_BACKGROUND = False

try:
    from core.memory.advanced_memory_manager import get_memory_manager
    HAS_MEMORY = True
except ImportError:
    HAS_MEMORY = False


class VirtualDataState(Enum):
    """States for virtual data items"""
    NOT_LOADED = "not_loaded"
    LOADING = "loading"
    LOADED = "loaded"
    ERROR = "error"


class ColumnType(IntEnum):
    """Column types for video table"""
    THUMBNAIL = 0
    TITLE = 1
    DURATION = 2
    SIZE = 3
    DATE_ADDED = 4
    STATUS = 5
    PROGRESS = 6
    URL = 7


@dataclass
class VirtualDataItem:
    """Virtual data item with lazy loading"""
    row_id: int
    video_id: Optional[str] = None
    title: Optional[str] = None
    duration: Optional[int] = None
    file_size: Optional[int] = None
    date_added: Optional[datetime] = None
    status: Optional[str] = None
    progress: Optional[float] = None
    url: Optional[str] = None
    thumbnail_path: Optional[str] = None
    state: VirtualDataState = VirtualDataState.NOT_LOADED
    last_accessed: datetime = field(default_factory=datetime.now)


class DataVirtualizationManager(QObject):
    """
    Manages virtual data loading and caching
    
    Handles dynamic data fetching, caching, and memory management
    for virtual table operations with background processing integration
    """
    
    # Signals
    if HAS_QT:
        dataLoaded = pyqtSignal(int, int)  # start_row, end_row
        dataError = pyqtSignal(int, str)   # row, error_message
        cacheUpdated = pyqtSignal(int)     # cache_size
    
    def __init__(self, page_size: int = 100, cache_size: int = 1000):
        if HAS_QT:
            super().__init__()
        
        self.page_size = page_size
        self.cache_size = cache_size
        
        # Data storage
        self._data_cache = {}  # row_id -> VirtualDataItem
        self._loading_rows = set()  # Currently loading rows
        self._total_rows = 0
        
        # Thread safety
        self._cache_lock = QMutex() if HAS_QT else threading.Lock()
        
        # Integration components
        self.paginator = None
        self.task_manager = None
        self.memory_manager = None
        
        # Performance tracking
        self._stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'data_loads': 0,
            'memory_usage': 0
        }
        
        # Initialize integrations
        self._initialize_integrations()
        
        # Cache cleanup timer
        if HAS_QT:
            self.cleanup_timer = QTimer()
            self.cleanup_timer.timeout.connect(self._cleanup_cache)
            self.cleanup_timer.start(30000)  # 30 seconds
    
    def _initialize_integrations(self):
        """Initialize integration with other systems"""
        
        # Database pagination
        if HAS_PAGINATION:
            try:
                self.paginator = AdvancedDatabasePaginator()
                print("✅ Database pagination integration initialized")
            except Exception as e:
                print(f"⚠️ Database pagination integration failed: {e}")
        
        # Background processing
        if HAS_BACKGROUND:
            try:
                self.task_manager = get_task_manager()
                print("✅ Background processing integration initialized")
            except Exception as e:
                print(f"⚠️ Background processing integration failed: {e}")
        
        # Memory management
        if HAS_MEMORY:
            try:
                self.memory_manager = get_memory_manager()
                print("✅ Memory management integration initialized")
            except Exception as e:
                print(f"⚠️ Memory management integration failed: {e}")
    
    def set_total_rows(self, total: int):
        """Set total number of rows available"""
        self._total_rows = total
    
    def get_total_rows(self) -> int:
        """Get total number of rows"""
        return self._total_rows
    
    def get_data_item(self, row: int) -> Optional[VirtualDataItem]:
        """Get data item for specific row"""
        
        if HAS_QT:
            locker = QMutexLocker(self._cache_lock)
        else:
            self._cache_lock.acquire()
        
        try:
            # Check cache first
            if row in self._data_cache:
                item = self._data_cache[row]
                item.last_accessed = datetime.now()
                self._stats['cache_hits'] += 1
                return item
            
            # Cache miss
            self._stats['cache_misses'] += 1
            
            # Create placeholder item
            placeholder = VirtualDataItem(
                row_id=row,
                title=f"Loading row {row}...",
                state=VirtualDataState.NOT_LOADED
            )
            self._data_cache[row] = placeholder
            
            # Trigger background loading
            self._load_data_range(row, row + 1)
            
            return placeholder
        finally:
            if not HAS_QT:
                self._cache_lock.release()
    
    def _load_data_range(self, start_row: int, end_row: int):
        """Load data range in background"""
        
        # Check if already loading
        loading_range = set(range(start_row, end_row))
        if loading_range.intersection(self._loading_rows):
            return  # Already loading some of these rows
        
        # Mark as loading
        self._loading_rows.update(loading_range)
        
        # Submit background task
        if self.task_manager:
            try:
                task_id = self.task_manager.submit_task(
                    task_type="virtual_data_load",
                    parameters={
                        'start_row': start_row,
                        'end_row': end_row,
                        'page_size': self.page_size
                    },
                    priority=TaskPriority.HIGH,
                    callback=self._on_data_loaded
                )
                print(f"📊 Submitted virtual data load task: {task_id}")
            except Exception as e:
                print(f"❌ Failed to submit data load task: {e}")
                self._loading_rows.difference_update(loading_range)
        else:
            # Fallback: load synchronously
            self._load_data_sync(start_row, end_row)
    
    def _load_data_sync(self, start_row: int, end_row: int):
        """Load data synchronously (fallback)"""
        
        try:
            # Simulate data loading
            for row in range(start_row, end_row):
                item = VirtualDataItem(
                    row_id=row,
                    video_id=f"video_{row:06d}",
                    title=f"Video {row + 1}",
                    duration=120 + (row % 300),  # 2-7 minutes
                    file_size=50 * 1024 * 1024 + (row % 100) * 1024 * 1024,  # 50-150 MB
                    date_added=datetime.now() - timedelta(days=row % 365),
                    status="downloaded" if row % 3 == 0 else "pending",
                    progress=100.0 if row % 3 == 0 else (row % 100),
                    url=f"https://example.com/video_{row}",
                    state=VirtualDataState.LOADED
                )
                
                if HAS_QT:
                    locker = QMutexLocker(self._cache_lock)
                else:
                    self._cache_lock.acquire()
                
                try:
                    self._data_cache[row] = item
                    self._loading_rows.discard(row)
                finally:
                    if not HAS_QT:
                        self._cache_lock.release()
            
            # Emit signal
            if HAS_QT and hasattr(self, 'dataLoaded'):
                self.dataLoaded.emit(start_row, end_row)
            
            self._stats['data_loads'] += 1
            
        except Exception as e:
            print(f"❌ Data loading error: {e}")
            
            # Mark as error
            for row in range(start_row, end_row):
                if HAS_QT:
                    locker = QMutexLocker(self._cache_lock)
                else:
                    self._cache_lock.acquire()
                
                try:
                    if row in self._data_cache:
                        self._data_cache[row].state = VirtualDataState.ERROR
                    self._loading_rows.discard(row)
                finally:
                    if not HAS_QT:
                        self._cache_lock.release()
            
            if HAS_QT and hasattr(self, 'dataError'):
                self.dataError.emit(start_row, str(e))
    
    def _on_data_loaded(self, result):
        """Handle background data loading completion"""
        
        if result.state.value == "completed":
            start_row = result.result_data.get('start_row', 0)
            end_row = result.result_data.get('end_row', 0)
            
            print(f"✅ Virtual data loaded: rows {start_row}-{end_row}")
            
            # Update loading state
            for row in range(start_row, end_row):
                self._loading_rows.discard(row)
            
            # Emit signal
            if HAS_QT and hasattr(self, 'dataLoaded'):
                self.dataLoaded.emit(start_row, end_row)
        
        else:
            print(f"❌ Virtual data loading failed: {result.error_message}")
    
    def prefetch_range(self, start_row: int, end_row: int):
        """Prefetch data range for smooth scrolling"""
        
        # Calculate missing rows
        missing_rows = []
        if HAS_QT:
            locker = QMutexLocker(self._cache_lock)
        else:
            self._cache_lock.acquire()
        
        try:
            for row in range(start_row, end_row):
                if row not in self._data_cache or self._data_cache[row].state == VirtualDataState.NOT_LOADED:
                    missing_rows.append(row)
        finally:
            if not HAS_QT:
                self._cache_lock.release()
        
        if missing_rows:
            # Group consecutive rows for efficient loading
            ranges = self._group_consecutive_rows(missing_rows)
            for range_start, range_end in ranges:
                self._load_data_range(range_start, range_end + 1)
    
    def _group_consecutive_rows(self, rows: List[int]) -> List[Tuple[int, int]]:
        """Group consecutive row numbers into ranges"""
        
        if not rows:
            return []
        
        rows.sort()
        ranges = []
        start = rows[0]
        end = rows[0]
        
        for row in rows[1:]:
            if row == end + 1:
                end = row
            else:
                ranges.append((start, end))
                start = end = row
        
        ranges.append((start, end))
        return ranges
    
    def _cleanup_cache(self):
        """Clean up old cache entries"""
        
        if len(self._data_cache) <= self.cache_size:
            return
        
        if HAS_QT:
            locker = QMutexLocker(self._cache_lock)
        else:
            self._cache_lock.acquire()
        
        try:
            # Sort by last accessed time
            items = list(self._data_cache.items())
            items.sort(key=lambda x: x[1].last_accessed)
            
            # Remove oldest items
            to_remove = len(items) - self.cache_size
            for i in range(to_remove):
                row_id, _ = items[i]
                del self._data_cache[row_id]
            
            print(f"🧹 Cleaned up {to_remove} cache entries")
            
            # Update memory stats
            if self.memory_manager:
                self._stats['memory_usage'] = len(self._data_cache) * 1024  # Rough estimate
            
            # Emit signal
            if HAS_QT and hasattr(self, 'cacheUpdated'):
                self.cacheUpdated.emit(len(self._data_cache))
        finally:
            if not HAS_QT:
                self._cache_lock.release()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get virtualization statistics"""
        
        if HAS_QT:
            locker = QMutexLocker(self._cache_lock)
        else:
            self._cache_lock.acquire()
        
        try:
            return {
                'cache_size': len(self._data_cache),
                'loading_rows': len(self._loading_rows),
                'total_rows': self._total_rows,
                **self._stats
            }
        finally:
            if not HAS_QT:
                self._cache_lock.release()
    
    def clear_cache(self):
        """Clear all cached data"""
        
        if HAS_QT:
            locker = QMutexLocker(self._cache_lock)
        else:
            self._cache_lock.acquire()
        
        try:
            self._data_cache.clear()
            self._loading_rows.clear()
        finally:
            if not HAS_QT:
                self._cache_lock.release()
            
        print("🗑️ Virtual data cache cleared")


class VirtualVideoTableModel(QAbstractTableModel):
    """
    Virtual table model for large video collections
    
    Implements QAbstractItemModel with virtual data loading,
    dynamic fetching, and integration with background processing
    """
    
    # Column definitions
    COLUMNS = [
        ("Thumbnail", ColumnType.THUMBNAIL),
        ("Title", ColumnType.TITLE),
        ("Duration", ColumnType.DURATION),
        ("Size", ColumnType.SIZE),
        ("Date Added", ColumnType.DATE_ADDED),
        ("Status", ColumnType.STATUS),
        ("Progress", ColumnType.PROGRESS),
        ("URL", ColumnType.URL)
    ]
    
    def __init__(self, parent=None):
        if HAS_QT:
            super().__init__(parent)
        
        # Data virtualization
        self.data_manager = DataVirtualizationManager()
        
        # Connect signals
        if HAS_QT:
            self.data_manager.dataLoaded.connect(self._on_data_loaded)
            self.data_manager.dataError.connect(self._on_data_error)
        
        # Fetch parameters
        self.fetch_size = 100
        self.prefetch_buffer = 50
        
        # Performance tracking
        self._last_fetch_time = time.time()
        self._fetch_stats = {
            'total_fetches': 0,
            'average_fetch_time': 0
        }
    
    def rowCount(self, parent=QModelIndex()) -> int:
        """Return total number of rows"""
        if parent.isValid():
            return 0
        return self.data_manager.get_total_rows()
    
    def columnCount(self, parent=QModelIndex()) -> int:
        """Return number of columns"""
        if parent.isValid():
            return 0
        return len(self.COLUMNS)
    
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Return data for given index and role"""
        
        if not index.isValid():
            return QVariant()
        
        row = index.row()
        column = index.column()
        
        # Get data item
        item = self.data_manager.get_data_item(row)
        if not item:
            return QVariant()
        
        # Handle different roles
        if role == Qt.ItemDataRole.DisplayRole:
            return self._get_display_data(item, column)
        elif role == Qt.ItemDataRole.DecorationRole:
            return self._get_decoration_data(item, column)
        elif role == Qt.ItemDataRole.ToolTipRole:
            return self._get_tooltip_data(item, column)
        elif role == Qt.ItemDataRole.BackgroundRole:
            return self._get_background_data(item, column)
        elif role == Qt.ItemDataRole.ForegroundRole:
            return self._get_foreground_data(item, column)
        
        return QVariant()
    
    def _get_display_data(self, item: VirtualDataItem, column: int) -> str:
        """Get display data for column"""
        
        column_type = self.COLUMNS[column][1]
        
        if item.state == VirtualDataState.LOADING:
            return "Loading..."
        elif item.state == VirtualDataState.ERROR:
            return "Error"
        elif item.state == VirtualDataState.NOT_LOADED:
            return "..."
        
        # Return actual data
        if column_type == ColumnType.THUMBNAIL:
            return ""  # Thumbnail handled by decoration role
        elif column_type == ColumnType.TITLE:
            return item.title or "Unknown"
        elif column_type == ColumnType.DURATION:
            if item.duration:
                minutes = item.duration // 60
                seconds = item.duration % 60
                return f"{minutes}:{seconds:02d}"
            return "0:00"
        elif column_type == ColumnType.SIZE:
            if item.file_size:
                return self._format_file_size(item.file_size)
            return "0 B"
        elif column_type == ColumnType.DATE_ADDED:
            if item.date_added:
                return item.date_added.strftime("%Y-%m-%d %H:%M")
            return ""
        elif column_type == ColumnType.STATUS:
            return item.status or "unknown"
        elif column_type == ColumnType.PROGRESS:
            if item.progress is not None:
                return f"{item.progress:.1f}%"
            return "0%"
        elif column_type == ColumnType.URL:
            return item.url or ""
        
        return ""
    
    def _get_decoration_data(self, item: VirtualDataItem, column: int):
        """Get decoration (icon/pixmap) data for column"""
        
        column_type = self.COLUMNS[column][1]
        
        if column_type == ColumnType.THUMBNAIL:
            if item.thumbnail_path and os.path.exists(item.thumbnail_path):
                return QPixmap(item.thumbnail_path).scaled(64, 48, Qt.AspectRatioMode.KeepAspectRatio)
            else:
                # Return placeholder thumbnail
                placeholder = QPixmap(64, 48)
                placeholder.fill(QColor(200, 200, 200))
                return placeholder
        
        return QVariant()
    
    def _get_tooltip_data(self, item: VirtualDataItem, column: int) -> str:
        """Get tooltip data for column"""
        
        if item.state == VirtualDataState.LOADING:
            return "Loading data..."
        elif item.state == VirtualDataState.ERROR:
            return "Failed to load data"
        
        column_type = self.COLUMNS[column][1]
        
        if column_type == ColumnType.TITLE:
            return f"Video ID: {item.video_id}\nTitle: {item.title}"
        elif column_type == ColumnType.SIZE:
            return f"File size: {self._format_file_size(item.file_size or 0)}"
        elif column_type == ColumnType.URL:
            return f"Source URL: {item.url}"
        
        return ""
    
    def _get_background_data(self, item: VirtualDataItem, column: int):
        """Get background color for cell"""
        
        if item.state == VirtualDataState.LOADING:
            return QColor(255, 255, 200)  # Light yellow
        elif item.state == VirtualDataState.ERROR:
            return QColor(255, 200, 200)  # Light red
        
        return QVariant()
    
    def _get_foreground_data(self, item: VirtualDataItem, column: int):
        """Get foreground color for cell"""
        
        if item.state == VirtualDataState.LOADING:
            return QColor(100, 100, 100)  # Gray
        elif item.state == VirtualDataState.ERROR:
            return QColor(150, 0, 0)  # Dark red
        
        return QVariant()
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Return header data"""
        
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self.COLUMNS):
                return self.COLUMNS[section][0]
        elif orientation == Qt.Orientation.Vertical and role == Qt.ItemDataRole.DisplayRole:
            return str(section + 1)
        
        return QVariant()
    
    def canFetchMore(self, parent: QModelIndex) -> bool:
        """Check if more data can be fetched"""
        
        if parent.isValid():
            return False
        
        # Always allow fetching for virtual model
        return True
    
    def fetchMore(self, parent: QModelIndex):
        """Fetch more data"""
        
        if parent.isValid():
            return
        
        # Track fetch timing
        start_time = time.time()
        
        # Determine fetch range based on current view
        # This would typically be called by the view when scrolling
        current_rows = self.rowCount()
        fetch_start = max(0, current_rows - self.prefetch_buffer)
        fetch_end = min(self.data_manager.get_total_rows(), current_rows + self.fetch_size)
        
        # Prefetch data
        self.data_manager.prefetch_range(fetch_start, fetch_end)
        
        # Update stats
        fetch_time = time.time() - start_time
        self._fetch_stats['total_fetches'] += 1
        self._fetch_stats['average_fetch_time'] = (
            (self._fetch_stats['average_fetch_time'] * (self._fetch_stats['total_fetches'] - 1) + fetch_time) /
            self._fetch_stats['total_fetches']
        )
        
        print(f"📊 Fetched data range {fetch_start}-{fetch_end} in {fetch_time:.3f}s")
    
    def _on_data_loaded(self, start_row: int, end_row: int):
        """Handle data loaded signal"""
        
        # Notify views that data has changed
        if HAS_QT:
            top_left = self.index(start_row, 0)
            bottom_right = self.index(end_row - 1, self.columnCount() - 1)
            self.dataChanged.emit(top_left, bottom_right)
    
    def _on_data_error(self, row: int, error_message: str):
        """Handle data error signal"""
        
        print(f"❌ Data error at row {row}: {error_message}")
        
        # Notify view of change
        if HAS_QT:
            index = self.index(row, 0)
            self.dataChanged.emit(index, index)
    
    def set_total_rows(self, total: int):
        """Set total number of rows and update model"""
        
        if HAS_QT:
            self.beginResetModel()
        
        self.data_manager.set_total_rows(total)
        
        if HAS_QT:
            self.endResetModel()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        
        return {
            'model_stats': self._fetch_stats,
            'data_manager_stats': self.data_manager.get_stats()
        }


class VirtualTableProxyStack(QObject):
    """
    Proxy model stack for virtual table
    
    Combines QIdentityProxyModel and QSortFilterProxyModel
    for dynamic data transformation and filtering
    """
    
    def __init__(self, source_model: VirtualVideoTableModel):
        if HAS_QT:
            super().__init__()
        
        self.source_model = source_model
        
        # Create proxy stack
        if HAS_QT:
            # Identity proxy for data transformation
            self.identity_proxy = QIdentityProxyModel()
            self.identity_proxy.setSourceModel(source_model)
            
            # Sort/filter proxy for filtering and sorting
            self.filter_proxy = VirtualSortFilterProxyModel()
            self.filter_proxy.setSourceModel(self.identity_proxy)
            
            # Final model for views
            self.final_model = self.filter_proxy
        else:
            # Fallback
            self.final_model = source_model
    
    def get_final_model(self):
        """Get the final model for views"""
        return self.final_model
    
    def set_filter_text(self, text: str):
        """Set filter text"""
        if HAS_QT and hasattr(self, 'filter_proxy'):
            self.filter_proxy.setFilterText(text)
    
    def set_status_filter(self, status: str):
        """Set status filter"""
        if HAS_QT and hasattr(self, 'filter_proxy'):
            self.filter_proxy.setStatusFilter(status)


class VirtualSortFilterProxyModel(QSortFilterProxyModel):
    """
    Custom sort/filter proxy model for virtual table
    
    Implements efficient filtering for large datasets
    with virtual data support
    """
    
    def __init__(self):
        if HAS_QT:
            super().__init__()
        
        self.filter_text = ""
        self.status_filter = ""
        
        # Enable dynamic sorting
        if HAS_QT:
            self.setDynamicSortFilter(True)
    
    def setFilterText(self, text: str):
        """Set filter text and update filter"""
        self.filter_text = text.lower()
        if HAS_QT:
            self.invalidateFilter()
    
    def setStatusFilter(self, status: str):
        """Set status filter and update filter"""
        self.status_filter = status.lower()
        if HAS_QT:
            self.invalidateFilter()
    
    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        """Check if row should be included in filtered results"""
        
        if not HAS_QT:
            return True
        
        # Get source model
        source_model = self.sourceModel()
        if not source_model:
            return True
        
        # Check text filter
        if self.filter_text:
            title_index = source_model.index(source_row, ColumnType.TITLE)
            title = source_model.data(title_index, Qt.ItemDataRole.DisplayRole)
            if title and self.filter_text not in title.lower():
                return False
        
        # Check status filter
        if self.status_filter:
            status_index = source_model.index(source_row, ColumnType.STATUS)
            status = source_model.data(status_index, Qt.ItemDataRole.DisplayRole)
            if status and self.status_filter not in status.lower():
                return False
        
        return True
    
    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        """Custom sorting logic"""
        
        if not HAS_QT:
            return False
        
        left_data = self.sourceModel().data(left, Qt.ItemDataRole.DisplayRole)
        right_data = self.sourceModel().data(right, Qt.ItemDataRole.DisplayRole)
        
        # Handle different column types
        column = left.column()
        column_type = VirtualVideoTableModel.COLUMNS[column][1]
        
        if column_type in [ColumnType.DURATION, ColumnType.SIZE, ColumnType.PROGRESS]:
            # Numeric comparison
            try:
                left_num = float(str(left_data).split()[0]) if left_data else 0
                right_num = float(str(right_data).split()[0]) if right_data else 0
                return left_num < right_num
            except (ValueError, IndexError):
                pass
        
        # Default string comparison
        return str(left_data) < str(right_data)


# Global virtual table manager
_global_virtual_manager: Optional[DataVirtualizationManager] = None

def get_virtual_manager() -> DataVirtualizationManager:
    """Get global virtual table manager"""
    global _global_virtual_manager
    
    if _global_virtual_manager is None:
        _global_virtual_manager = DataVirtualizationManager()
    
    return _global_virtual_manager

def cleanup_virtual_manager():
    """Cleanup global virtual table manager"""
    global _global_virtual_manager
    
    if _global_virtual_manager:
        _global_virtual_manager.clear_cache()
        _global_virtual_manager = None 