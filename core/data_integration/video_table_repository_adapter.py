"""
VideoTable Repository Integration Adapters for Social Download Manager v2.0

Implements specific adapters for connecting VideoTable and FilterableVideoTable components
to ContentRepository data. Creates data models that translate between repository entities
and table display formats, implements filtering and sorting mechanisms that leverage
repository query capabilities, and ensures efficient updates when repository data changes.

This module bridges the UI table components with the repository layer, providing
seamless data integration with performance optimizations and real-time updates.
"""

from typing import Dict, Any, List, Optional, Callable, Union, Set
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import logging
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QWidget

from data.models.repositories import IContentRepository
from data.models.repository_interfaces import IDownloadRepository
from data.models.base import BaseEntity, EntityId
from data.models.content import VideoContent, ContentStatus, Platform
from data.models.download import DownloadRecord, DownloadStatus
from ui.components.tables.video_table import VideoTable
from ui.components.tables.filterable_video_table import FilterableVideoTable
from ui.components.common.models import TableConfig, ColumnConfig, FilterConfig, SortOrder
from .data_binding_strategy import (
    get_data_binding_manager, DataBindingMode, DataBindingConfig,
    IDataBindingAdapter, DataBindingContext
)
from .repository_state_sync import get_repository_state_manager
from .repository_event_integration import (
    get_repository_event_manager, RepositoryEventType, RepositoryEventPayload
)
from .async_loading_patterns import (
    get_async_repository_manager, LoadingPriority, create_loading_config,
    create_qt_loading_indicator
)
from .repository_ui_error_integration import (
    get_repository_ui_error_integrator, create_error_display_config,
    create_repository_error_context
)


class TableDataMode(Enum):
    """Modes for table data handling"""
    LIVE = "live"  # Real-time updates from repository
    CACHED = "cached"  # Cached data with periodic refresh
    SNAPSHOT = "snapshot"  # Static snapshot of data


@dataclass
class TableRepositoryConfig:
    """Configuration for table-repository integration"""
    data_mode: TableDataMode = TableDataMode.LIVE
    auto_refresh_interval: int = 30  # seconds
    batch_size: int = 100  # for pagination
    enable_lazy_loading: bool = True
    enable_virtual_scrolling: bool = False
    cache_timeout: int = 300  # seconds
    max_cached_items: int = 1000
    enable_optimistic_updates: bool = True
    enable_real_time_sync: bool = True
    filter_debounce_delay: int = 300  # milliseconds
    sort_debounce_delay: int = 200  # milliseconds


@dataclass
class VideoTableData:
    """Standardized data structure for video tables"""
    id: str
    title: str
    platform: str
    status: str
    duration: Optional[str] = None
    quality: Optional[str] = None
    progress: Optional[float] = None
    download_date: Optional[datetime] = None
    file_size: Optional[int] = None
    file_path: Optional[str] = None
    thumbnail_url: Optional[str] = None
    url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for table display"""
        return {
            'id': self.id,
            'title': self.title,
            'platform': self.platform,
            'status': self.status,
            'duration': self.duration or '',
            'quality': self.quality or '',
            'progress': self.progress or 0.0,
            'download_date': self.download_date.strftime('%Y-%m-%d %H:%M') if self.download_date else '',
            'file_size': self._format_file_size(self.file_size) if self.file_size else '',
            'file_path': self.file_path or '',
            'thumbnail_url': self.thumbnail_url or '',
            'url': self.url or '',
            'metadata': self.metadata or {}
        }
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"


class IVideoTableRepositoryAdapter(ABC):
    """Interface for video table repository adapters"""
    
    @abstractmethod
    def load_data(self, filters: Optional[Dict[str, Any]] = None,
                  sort_column: Optional[str] = None,
                  sort_order: Optional[SortOrder] = None,
                  limit: Optional[int] = None,
                  offset: Optional[int] = None) -> List[VideoTableData]:
        """Load data from repository"""
        pass
    
    @abstractmethod
    def refresh_data(self) -> None:
        """Refresh data from repository"""
        pass
    
    @abstractmethod
    def get_total_count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Get total count of items matching filters"""
        pass
    
    @abstractmethod
    def subscribe_to_changes(self, callback: Callable[[List[VideoTableData]], None]) -> None:
        """Subscribe to data changes"""
        pass


class ContentRepositoryTableAdapter(QObject, IVideoTableRepositoryAdapter):
    """
    Adapter for connecting VideoTable to ContentRepository
    
    Handles content data loading, filtering, sorting, and real-time updates
    from the content repository to video table components.
    """
    
    # Signals for data changes
    data_loaded = pyqtSignal(list)  # List[VideoTableData]
    data_updated = pyqtSignal(list)  # Updated items
    data_error = pyqtSignal(str)  # Error message
    loading_started = pyqtSignal()
    loading_finished = pyqtSignal()
    
    def __init__(self, content_repository: IContentRepository,
                 config: Optional[TableRepositoryConfig] = None):
        super().__init__()
        
        self._content_repository = content_repository
        self._config = config or TableRepositoryConfig()
        self._logger = logging.getLogger(__name__)
        
        # Data management
        self._cached_data: List[VideoTableData] = []
        self._last_refresh: Optional[datetime] = None
        self._data_change_callbacks: List[Callable] = []
        
        # Repository integration
        self._repository_event_manager = get_repository_event_manager()
        self._async_manager = get_async_repository_manager()
        self._error_integrator = get_repository_ui_error_integrator()
        
        # Timers for auto-refresh and debouncing
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._auto_refresh)
        
        self._filter_debounce_timer = QTimer()
        self._filter_debounce_timer.setSingleShot(True)
        self._filter_debounce_timer.timeout.connect(self._execute_debounced_filter)
        
        self._sort_debounce_timer = QTimer()
        self._sort_debounce_timer.setSingleShot(True)
        self._sort_debounce_timer.timeout.connect(self._execute_debounced_sort)
        
        # Pending operations
        self._pending_filters: Optional[Dict[str, Any]] = None
        self._pending_sort_column: Optional[str] = None
        self._pending_sort_order: Optional[SortOrder] = None
        
        # Setup repository event subscriptions
        self._setup_repository_subscriptions()
        
        # Start auto-refresh if enabled
        if self._config.auto_refresh_interval > 0:
            self._refresh_timer.start(self._config.auto_refresh_interval * 1000)
    
    def load_data(self, filters: Optional[Dict[str, Any]] = None,
                  sort_column: Optional[str] = None,
                  sort_order: Optional[SortOrder] = None,
                  limit: Optional[int] = None,
                  offset: Optional[int] = None) -> List[VideoTableData]:
        """Load data from content repository"""
        try:
            # Check if we can use cached data
            if self._can_use_cached_data(filters, sort_column, sort_order):
                return self._get_cached_data(filters, sort_column, sort_order, limit, offset)
            
            # Load data asynchronously
            operation_id = self._async_manager.execute_async_operation(
                component_id="content_table_adapter",
                repository=self._content_repository,
                operation_func=self._load_data_from_repository,
                operation_name="Load Content Data",
                priority=LoadingPriority.HIGH,
                timeout_seconds=30,
                filters=filters,
                sort_column=sort_column,
                sort_order=sort_order,
                limit=limit,
                offset=offset
            )
            
            # Return cached data immediately if available
            if self._cached_data and self._config.data_mode == TableDataMode.CACHED:
                return self._get_cached_data(filters, sort_column, sort_order, limit, offset)
            
            return []
            
        except Exception as e:
            self._logger.error(f"Error loading data: {e}")
            self._handle_repository_error(e, "load_data")
            return []
    
    def _load_data_from_repository(self, filters: Optional[Dict[str, Any]] = None,
                                  sort_column: Optional[str] = None,
                                  sort_order: Optional[SortOrder] = None,
                                  limit: Optional[int] = None,
                                  offset: Optional[int] = None,
                                  progress_callback: Optional[Callable] = None) -> List[VideoTableData]:
        """Load data from repository (executed in background thread)"""
        try:
            # Report initial progress
            if progress_callback:
                progress_callback(0.1, "Querying content repository...")
            
            # Build repository query
            query_filters = self._build_repository_filters(filters)
            query_sort = self._build_repository_sort(sort_column, sort_order)
            
            # Report progress
            if progress_callback:
                progress_callback(0.3, "Executing repository query...")
            
            # Execute repository query
            content_items = self._content_repository.find_all(
                filters=query_filters,
                sort_by=query_sort.get('column') if query_sort else None,
                sort_order=query_sort.get('order') if query_sort else None,
                limit=limit,
                offset=offset
            )
            
            # Report progress
            if progress_callback:
                progress_callback(0.7, f"Processing {len(content_items)} items...")
            
            # Convert to table data
            table_data = []
            for i, content in enumerate(content_items):
                table_item = self._convert_content_to_table_data(content)
                table_data.append(table_item)
                
                # Report progress periodically
                if progress_callback and i % 10 == 0:
                    progress = 0.7 + (0.2 * (i / len(content_items)))
                    progress_callback(progress, f"Processing item {i+1}/{len(content_items)}")
            
            # Cache the data
            if self._config.data_mode in [TableDataMode.CACHED, TableDataMode.LIVE]:
                self._cached_data = table_data
                self._last_refresh = datetime.now()
            
            # Report completion
            if progress_callback:
                progress_callback(1.0, f"Loaded {len(table_data)} items")
            
            return table_data
            
        except Exception as e:
            self._logger.error(f"Error in background data loading: {e}")
            raise
    
    def _convert_content_to_table_data(self, content: VideoContent) -> VideoTableData:
        """Convert VideoContent entity to VideoTableData"""
        return VideoTableData(
            id=str(content.id),
            title=content.title or "Unknown Title",
            platform=content.platform.value if content.platform else "Unknown",
            status=content.status.value if content.status else "Unknown",
            duration=self._format_duration(content.duration),
            quality=content.quality or "Unknown",
            progress=0.0,  # Progress is handled by download repository
            url=content.url,
            thumbnail_url=content.thumbnail_url,
            metadata=content.metadata or {}
        )
    
    def _format_duration(self, duration_seconds: Optional[int]) -> Optional[str]:
        """Format duration in human-readable format"""
        if duration_seconds is None:
            return None
        
        hours = duration_seconds // 3600
        minutes = (duration_seconds % 3600) // 60
        seconds = duration_seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    def _build_repository_filters(self, filters: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Convert table filters to repository filters"""
        if not filters:
            return None
        
        repo_filters = {}
        
        # Map table filter fields to repository fields
        field_mapping = {
            'platform': 'platform',
            'status': 'status',
            'title': 'title',
            'quality': 'quality'
        }
        
        for table_field, repo_field in field_mapping.items():
            if table_field in filters:
                repo_filters[repo_field] = filters[table_field]
        
        return repo_filters if repo_filters else None
    
    def _build_repository_sort(self, sort_column: Optional[str],
                              sort_order: Optional[SortOrder]) -> Optional[Dict[str, Any]]:
        """Convert table sort to repository sort"""
        if not sort_column:
            return None
        
        # Map table columns to repository fields
        column_mapping = {
            'title': 'title',
            'platform': 'platform',
            'status': 'status',
            'duration': 'duration',
            'quality': 'quality'
        }
        
        repo_column = column_mapping.get(sort_column)
        if not repo_column:
            return None
        
        repo_order = 'asc' if sort_order == SortOrder.ASCENDING else 'desc'
        
        return {
            'column': repo_column,
            'order': repo_order
        }
    
    def refresh_data(self) -> None:
        """Refresh data from repository"""
        try:
            self.loading_started.emit()
            
            # Clear cached data
            self._cached_data.clear()
            self._last_refresh = None
            
            # Load fresh data
            self.load_data()
            
        except Exception as e:
            self._logger.error(f"Error refreshing data: {e}")
            self._handle_repository_error(e, "refresh_data")
        finally:
            self.loading_finished.emit()
    
    def get_total_count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Get total count of items matching filters"""
        try:
            repo_filters = self._build_repository_filters(filters)
            return self._content_repository.count(filters=repo_filters)
        except Exception as e:
            self._logger.error(f"Error getting total count: {e}")
            self._handle_repository_error(e, "get_total_count")
            return 0
    
    def subscribe_to_changes(self, callback: Callable[[List[VideoTableData]], None]) -> None:
        """Subscribe to data changes"""
        self._data_change_callbacks.append(callback)
    
    def _can_use_cached_data(self, filters: Optional[Dict[str, Any]],
                           sort_column: Optional[str],
                           sort_order: Optional[SortOrder]) -> bool:
        """Check if cached data can be used"""
        if not self._cached_data or not self._last_refresh:
            return False
        
        # Check cache timeout
        if self._config.cache_timeout > 0:
            cache_age = (datetime.now() - self._last_refresh).total_seconds()
            if cache_age > self._config.cache_timeout:
                return False
        
        # For live mode, always refresh
        if self._config.data_mode == TableDataMode.LIVE:
            return False
        
        return True
    
    def _get_cached_data(self, filters: Optional[Dict[str, Any]],
                        sort_column: Optional[str],
                        sort_order: Optional[SortOrder],
                        limit: Optional[int],
                        offset: Optional[int]) -> List[VideoTableData]:
        """Get data from cache with filtering and sorting"""
        data = self._cached_data.copy()
        
        # Apply filters
        if filters:
            data = self._apply_filters_to_cached_data(data, filters)
        
        # Apply sorting
        if sort_column:
            data = self._apply_sort_to_cached_data(data, sort_column, sort_order)
        
        # Apply pagination
        if offset:
            data = data[offset:]
        if limit:
            data = data[:limit]
        
        return data
    
    def _apply_filters_to_cached_data(self, data: List[VideoTableData],
                                    filters: Dict[str, Any]) -> List[VideoTableData]:
        """Apply filters to cached data"""
        filtered_data = []
        
        for item in data:
            matches = True
            
            for field, value in filters.items():
                item_value = getattr(item, field, None)
                
                if isinstance(value, list):
                    if item_value not in value:
                        matches = False
                        break
                elif isinstance(value, str):
                    if value.lower() not in str(item_value).lower():
                        matches = False
                        break
                else:
                    if item_value != value:
                        matches = False
                        break
            
            if matches:
                filtered_data.append(item)
        
        return filtered_data
    
    def _apply_sort_to_cached_data(self, data: List[VideoTableData],
                                  sort_column: str,
                                  sort_order: Optional[SortOrder]) -> List[VideoTableData]:
        """Apply sorting to cached data"""
        reverse = sort_order == SortOrder.DESCENDING
        
        try:
            return sorted(data, key=lambda x: getattr(x, sort_column, ''), reverse=reverse)
        except Exception as e:
            self._logger.warning(f"Error sorting cached data: {e}")
            return data
    
    def _setup_repository_subscriptions(self) -> None:
        """Setup subscriptions to repository events"""
        subscriber = self._repository_event_manager.get_subscriber()
        
        # Subscribe to content repository events
        def handle_content_event(event_type, payload):
            if event_type in [
                RepositoryEventType.REPOSITORY_ENTITY_CREATED,
                RepositoryEventType.REPOSITORY_ENTITY_UPDATED,
                RepositoryEventType.REPOSITORY_ENTITY_DELETED
            ]:
                # Refresh data on content changes
                if self._config.enable_real_time_sync:
                    self._handle_repository_change(event_type, payload)
        
        subscriber.subscribe_to_repository_type("ContentRepository", handle_content_event)
    
    def _handle_repository_change(self, event_type: RepositoryEventType,
                                payload: RepositoryEventPayload) -> None:
        """Handle repository change events"""
        try:
            if event_type == RepositoryEventType.REPOSITORY_ENTITY_CREATED:
                # Add new item to cache
                if payload.entity_data:
                    new_item = self._convert_entity_data_to_table_data(payload.entity_data)
                    self._cached_data.append(new_item)
                    self._notify_data_change([new_item])
            
            elif event_type == RepositoryEventType.REPOSITORY_ENTITY_UPDATED:
                # Update existing item in cache
                if payload.entity_id and payload.entity_data:
                    self._update_cached_item(payload.entity_id, payload.entity_data)
            
            elif event_type == RepositoryEventType.REPOSITORY_ENTITY_DELETED:
                # Remove item from cache
                if payload.entity_id:
                    self._remove_cached_item(payload.entity_id)
            
        except Exception as e:
            self._logger.error(f"Error handling repository change: {e}")
    
    def _convert_entity_data_to_table_data(self, entity_data: Dict[str, Any]) -> VideoTableData:
        """Convert entity data from event to table data"""
        return VideoTableData(
            id=str(entity_data.get('id', '')),
            title=entity_data.get('title', 'Unknown Title'),
            platform=entity_data.get('platform', 'Unknown'),
            status=entity_data.get('status', 'Unknown'),
            duration=self._format_duration(entity_data.get('duration')),
            quality=entity_data.get('quality', 'Unknown'),
            url=entity_data.get('url'),
            thumbnail_url=entity_data.get('thumbnail_url'),
            metadata=entity_data.get('metadata', {})
        )
    
    def _update_cached_item(self, entity_id: str, entity_data: Dict[str, Any]) -> None:
        """Update item in cache"""
        for i, item in enumerate(self._cached_data):
            if item.id == entity_id:
                updated_item = self._convert_entity_data_to_table_data(entity_data)
                self._cached_data[i] = updated_item
                self._notify_data_change([updated_item])
                break
    
    def _remove_cached_item(self, entity_id: str) -> None:
        """Remove item from cache"""
        self._cached_data = [item for item in self._cached_data if item.id != entity_id]
        self._notify_data_change([])
    
    def _notify_data_change(self, changed_items: List[VideoTableData]) -> None:
        """Notify subscribers of data changes"""
        for callback in self._data_change_callbacks:
            try:
                callback(changed_items)
            except Exception as e:
                self._logger.error(f"Error in data change callback: {e}")
        
        # Emit signal
        self.data_updated.emit([item.to_dict() for item in changed_items])
    
    def _auto_refresh(self) -> None:
        """Auto-refresh data"""
        if self._config.data_mode == TableDataMode.LIVE:
            self.refresh_data()
    
    def _handle_repository_error(self, error: Exception, operation: str) -> None:
        """Handle repository errors"""
        context = create_repository_error_context(
            user_action=operation,
            entity_type="VideoContent",
            component_id="content_table_adapter"
        )
        
        self._error_integrator.handle_repository_error(
            self._content_repository, error, operation, "content_table_adapter", context
        )
        
        # Emit error signal
        self.data_error.emit(str(error))
    
    # Debounced operations
    def load_data_debounced(self, filters: Optional[Dict[str, Any]] = None,
                           sort_column: Optional[str] = None,
                           sort_order: Optional[SortOrder] = None) -> None:
        """Load data with debouncing for filters and sorting"""
        self._pending_filters = filters
        self._pending_sort_column = sort_column
        self._pending_sort_order = sort_order
        
        # Start debounce timers
        if filters:
            self._filter_debounce_timer.start(self._config.filter_debounce_delay)
        
        if sort_column:
            self._sort_debounce_timer.start(self._config.sort_debounce_delay)
    
    def _execute_debounced_filter(self) -> None:
        """Execute debounced filter operation"""
        if self._pending_filters is not None:
            self.load_data(
                filters=self._pending_filters,
                sort_column=self._pending_sort_column,
                sort_order=self._pending_sort_order
            )
    
    def _execute_debounced_sort(self) -> None:
        """Execute debounced sort operation"""
        if self._pending_sort_column is not None:
            self.load_data(
                filters=self._pending_filters,
                sort_column=self._pending_sort_column,
                sort_order=self._pending_sort_order
            )


class DownloadRepositoryTableAdapter(QObject, IVideoTableRepositoryAdapter):
    """
    Adapter for connecting VideoTable to DownloadRepository
    
    Handles download data loading, progress tracking, and real-time updates
    from the download repository to video table components.
    """
    
    # Signals for download-specific events
    download_progress_updated = pyqtSignal(str, float)  # download_id, progress
    download_status_changed = pyqtSignal(str, str)  # download_id, status
    
    def __init__(self, download_repository: IDownloadRepository,
                 content_repository: IContentRepository,
                 config: Optional[TableRepositoryConfig] = None):
        super().__init__()
        
        self._download_repository = download_repository
        self._content_repository = content_repository
        self._config = config or TableRepositoryConfig()
        self._logger = logging.getLogger(__name__)
        
        # Data management
        self._cached_data: List[VideoTableData] = []
        self._last_refresh: Optional[datetime] = None
        self._data_change_callbacks: List[Callable] = []
        
        # Repository integration
        self._repository_event_manager = get_repository_event_manager()
        self._async_manager = get_async_repository_manager()
        self._error_integrator = get_repository_ui_error_integrator()
        
        # Setup repository event subscriptions
        self._setup_repository_subscriptions()
    
    def load_data(self, filters: Optional[Dict[str, Any]] = None,
                  sort_column: Optional[str] = None,
                  sort_order: Optional[SortOrder] = None,
                  limit: Optional[int] = None,
                  offset: Optional[int] = None) -> List[VideoTableData]:
        """Load download data from repository"""
        try:
            # Load data asynchronously
            operation_id = self._async_manager.execute_async_operation(
                component_id="download_table_adapter",
                repository=self._download_repository,
                operation_func=self._load_download_data_from_repository,
                operation_name="Load Download Data",
                priority=LoadingPriority.HIGH,
                timeout_seconds=30,
                filters=filters,
                sort_column=sort_column,
                sort_order=sort_order,
                limit=limit,
                offset=offset
            )
            
            return self._cached_data if self._cached_data else []
            
        except Exception as e:
            self._logger.error(f"Error loading download data: {e}")
            self._handle_repository_error(e, "load_data")
            return []
    
    def _load_download_data_from_repository(self, filters: Optional[Dict[str, Any]] = None,
                                          sort_column: Optional[str] = None,
                                          sort_order: Optional[SortOrder] = None,
                                          limit: Optional[int] = None,
                                          offset: Optional[int] = None,
                                          progress_callback: Optional[Callable] = None) -> List[VideoTableData]:
        """Load download data from repository (executed in background thread)"""
        try:
            # Report initial progress
            if progress_callback:
                progress_callback(0.1, "Querying download repository...")
            
            # Load download records
            download_records = self._download_repository.find_all(
                filters=self._build_download_filters(filters),
                limit=limit,
                offset=offset
            )
            
            if progress_callback:
                progress_callback(0.5, f"Loading content data for {len(download_records)} downloads...")
            
            # Load associated content data
            table_data = []
            for i, download in enumerate(download_records):
                # Get associated content
                content = None
                if download.content_id:
                    try:
                        content = self._content_repository.find_by_id(download.content_id)
                    except Exception as e:
                        self._logger.warning(f"Could not load content for download {download.id}: {e}")
                
                # Convert to table data
                table_item = self._convert_download_to_table_data(download, content)
                table_data.append(table_item)
                
                # Report progress
                if progress_callback and i % 5 == 0:
                    progress = 0.5 + (0.4 * (i / len(download_records)))
                    progress_callback(progress, f"Processing download {i+1}/{len(download_records)}")
            
            # Apply sorting
            if sort_column:
                table_data = self._sort_download_data(table_data, sort_column, sort_order)
            
            # Cache the data
            self._cached_data = table_data
            self._last_refresh = datetime.now()
            
            if progress_callback:
                progress_callback(1.0, f"Loaded {len(table_data)} downloads")
            
            return table_data
            
        except Exception as e:
            self._logger.error(f"Error in background download data loading: {e}")
            raise
    
    def _convert_download_to_table_data(self, download: DownloadRecord,
                                      content: Optional[VideoContent]) -> VideoTableData:
        """Convert DownloadRecord and VideoContent to VideoTableData"""
        return VideoTableData(
            id=str(download.id),
            title=content.title if content else "Unknown Title",
            platform=content.platform.value if content and content.platform else "Unknown",
            status=download.status.value if download.status else "Unknown",
            duration=self._format_duration(content.duration) if content else None,
            quality=download.quality or (content.quality if content else None),
            progress=download.progress or 0.0,
            download_date=download.created_at,
            file_size=download.file_size,
            file_path=download.file_path,
            url=content.url if content else None,
            thumbnail_url=content.thumbnail_url if content else None,
            metadata={
                'download_id': str(download.id),
                'content_id': str(download.content_id) if download.content_id else None,
                'download_metadata': download.metadata or {},
                'content_metadata': content.metadata if content else {}
            }
        )
    
    def _build_download_filters(self, filters: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Convert table filters to download repository filters"""
        if not filters:
            return None
        
        repo_filters = {}
        
        # Map table filter fields to download repository fields
        field_mapping = {
            'status': 'status',
            'quality': 'quality',
            'download_date': 'created_at'
        }
        
        for table_field, repo_field in field_mapping.items():
            if table_field in filters:
                repo_filters[repo_field] = filters[table_field]
        
        return repo_filters if repo_filters else None
    
    def _sort_download_data(self, data: List[VideoTableData],
                           sort_column: str,
                           sort_order: Optional[SortOrder]) -> List[VideoTableData]:
        """Sort download data"""
        reverse = sort_order == SortOrder.DESCENDING
        
        try:
            if sort_column == 'download_date':
                return sorted(data, key=lambda x: x.download_date or datetime.min, reverse=reverse)
            elif sort_column == 'file_size':
                return sorted(data, key=lambda x: x.file_size or 0, reverse=reverse)
            else:
                return sorted(data, key=lambda x: getattr(x, sort_column, ''), reverse=reverse)
        except Exception as e:
            self._logger.warning(f"Error sorting download data: {e}")
            return data
    
    def _format_duration(self, duration_seconds: Optional[int]) -> Optional[str]:
        """Format duration in human-readable format"""
        if duration_seconds is None:
            return None
        
        hours = duration_seconds // 3600
        minutes = (duration_seconds % 3600) // 60
        seconds = duration_seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    def refresh_data(self) -> None:
        """Refresh download data from repository"""
        self._cached_data.clear()
        self._last_refresh = None
        self.load_data()
    
    def get_total_count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Get total count of downloads matching filters"""
        try:
            repo_filters = self._build_download_filters(filters)
            return self._download_repository.count(filters=repo_filters)
        except Exception as e:
            self._logger.error(f"Error getting download count: {e}")
            return 0
    
    def subscribe_to_changes(self, callback: Callable[[List[VideoTableData]], None]) -> None:
        """Subscribe to download data changes"""
        self._data_change_callbacks.append(callback)
    
    def _setup_repository_subscriptions(self) -> None:
        """Setup subscriptions to download repository events"""
        subscriber = self._repository_event_manager.get_subscriber()
        
        def handle_download_event(event_type, payload):
            if event_type == RepositoryEventType.REPOSITORY_ENTITY_UPDATED:
                # Handle download progress updates
                if payload.entity_type == "DownloadRecord" and payload.entity_id:
                    self._handle_download_progress_update(payload)
        
        subscriber.subscribe_to_repository_type("DownloadRepository", handle_download_event)
    
    def _handle_download_progress_update(self, payload: RepositoryEventPayload) -> None:
        """Handle download progress updates"""
        try:
            entity_id = payload.entity_id
            entity_data = payload.entity_data or {}
            
            # Update cached item
            for item in self._cached_data:
                if item.metadata and item.metadata.get('download_id') == entity_id:
                    # Update progress
                    if 'progress' in entity_data:
                        item.progress = entity_data['progress']
                        self.download_progress_updated.emit(entity_id, item.progress)
                    
                    # Update status
                    if 'status' in entity_data:
                        item.status = entity_data['status']
                        self.download_status_changed.emit(entity_id, item.status)
                    
                    break
            
            # Notify data change
            self._notify_data_change([])
            
        except Exception as e:
            self._logger.error(f"Error handling download progress update: {e}")
    
    def _notify_data_change(self, changed_items: List[VideoTableData]) -> None:
        """Notify subscribers of data changes"""
        for callback in self._data_change_callbacks:
            try:
                callback(changed_items)
            except Exception as e:
                self._logger.error(f"Error in download data change callback: {e}")
    
    def _handle_repository_error(self, error: Exception, operation: str) -> None:
        """Handle repository errors"""
        context = create_repository_error_context(
            user_action=operation,
            entity_type="DownloadRecord",
            component_id="download_table_adapter"
        )
        
        self._error_integrator.handle_repository_error(
            self._download_repository, error, operation, "download_table_adapter", context
        )


class VideoTableDataBindingAdapter(IDataBindingAdapter):
    """
    Data binding adapter for VideoTable components
    
    Implements the IDataBindingAdapter interface to provide seamless
    data binding between repository adapters and VideoTable/FilterableVideoTable.
    """
    
    def __init__(self, table: Union[VideoTable, FilterableVideoTable],
                 repository_adapter: IVideoTableRepositoryAdapter):
        self._table = table
        self._repository_adapter = repository_adapter
        self._logger = logging.getLogger(__name__)
        
        # Setup connections
        self._setup_adapter_connections()
        self._setup_table_connections()
    
    def bind_data(self, context: DataBindingContext) -> bool:
        """Bind repository data to table"""
        try:
            # Load data from repository adapter
            data = self._repository_adapter.load_data(
                filters=context.filters,
                sort_column=context.sort_column,
                sort_order=context.sort_order,
                limit=context.limit,
                offset=context.offset
            )
            
            # Convert to table format
            table_data = [item.to_dict() for item in data]
            
            # Set data in table
            self._table.set_data(table_data)
            
            return True
            
        except Exception as e:
            self._logger.error(f"Error binding data to table: {e}")
            return False
    
    def update_data(self, context: DataBindingContext) -> bool:
        """Update table data"""
        return self.bind_data(context)
    
    def get_data(self) -> Any:
        """Get current table data"""
        if hasattr(self._table, 'get_all_data'):
            return self._table.get_all_data()
        return []
    
    def _setup_adapter_connections(self) -> None:
        """Setup connections to repository adapter"""
        self._repository_adapter.data_loaded.connect(self._on_data_loaded)
        self._repository_adapter.data_updated.connect(self._on_data_updated)
        self._repository_adapter.data_error.connect(self._on_data_error)
    
    def _setup_table_connections(self) -> None:
        """Setup connections to table"""
        # Connect table signals if available
        if hasattr(self._table, 'sort_changed'):
            self._table.sort_changed.connect(self._on_table_sort_changed)
        
        if hasattr(self._table, 'filter_changed'):
            self._table.filter_changed.connect(self._on_table_filter_changed)
    
    def _on_data_loaded(self, data: List[Dict[str, Any]]) -> None:
        """Handle data loaded from repository"""
        self._table.set_data(data)
    
    def _on_data_updated(self, data: List[Dict[str, Any]]) -> None:
        """Handle data updates from repository"""
        # For now, refresh all data
        # Could be optimized to update only changed items
        current_data = self._repository_adapter._cached_data
        table_data = [item.to_dict() for item in current_data]
        self._table.set_data(table_data)
    
    def _on_data_error(self, error_message: str) -> None:
        """Handle data errors from repository"""
        self._logger.error(f"Repository data error: {error_message}")
    
    def _on_table_sort_changed(self, column: int, order: SortOrder) -> None:
        """Handle table sort changes"""
        # Get column name
        if hasattr(self._table, 'config') and column < len(self._table.config.columns):
            column_name = self._table.config.columns[column].name
            
            # Load data with new sort
            self._repository_adapter.load_data(
                sort_column=column_name,
                sort_order=order
            )
    
    def _on_table_filter_changed(self, filters: Dict[str, Any]) -> None:
        """Handle table filter changes"""
        # Convert table filters to repository filters
        self._repository_adapter.load_data(filters=filters)


# =============================================================================
# Factory Functions and Utilities
# =============================================================================

def create_content_table_integration(table: Union[VideoTable, FilterableVideoTable],
                                    content_repository: IContentRepository,
                                    config: Optional[TableRepositoryConfig] = None) -> VideoTableDataBindingAdapter:
    """Create complete integration for content table"""
    # Create repository adapter
    repository_adapter = ContentRepositoryTableAdapter(content_repository, config)
    
    # Create data binding adapter
    binding_adapter = VideoTableDataBindingAdapter(table, repository_adapter)
    
    # Setup loading indicator
    loading_indicator = create_qt_loading_indicator(table)
    loading_config = create_loading_config(
        show_progress_bar=True,
        show_loading_text=True,
        minimum_display_time=500
    )
    
    async_manager = get_async_repository_manager()
    async_manager.register_loading_indicator("content_table_adapter", loading_indicator)
    async_manager.register_loading_config("content_table_adapter", loading_config)
    
    # Setup error handling
    error_config = create_error_display_config(
        show_message_box=True,
        show_status_bar=True,
        auto_dismiss_timeout=5
    )
    
    error_integrator = get_repository_ui_error_integrator(table)
    error_integrator.register_component_error_config("content_table_adapter", error_config)
    
    return binding_adapter


def create_download_table_integration(table: Union[VideoTable, FilterableVideoTable],
                                     download_repository: IDownloadRepository,
                                     content_repository: IContentRepository,
                                     config: Optional[TableRepositoryConfig] = None) -> VideoTableDataBindingAdapter:
    """Create complete integration for download table"""
    # Create repository adapter
    repository_adapter = DownloadRepositoryTableAdapter(
        download_repository, content_repository, config
    )
    
    # Create data binding adapter
    binding_adapter = VideoTableDataBindingAdapter(table, repository_adapter)
    
    # Setup loading indicator
    loading_indicator = create_qt_loading_indicator(table)
    loading_config = create_loading_config(
        show_progress_bar=True,
        show_loading_text=True,
        minimum_display_time=500
    )
    
    async_manager = get_async_repository_manager()
    async_manager.register_loading_indicator("download_table_adapter", loading_indicator)
    async_manager.register_loading_config("download_table_adapter", loading_config)
    
    return binding_adapter


def create_table_repository_config(data_mode: TableDataMode = TableDataMode.LIVE,
                                  auto_refresh_interval: int = 30,
                                  enable_real_time_sync: bool = True,
                                  **kwargs) -> TableRepositoryConfig:
    """Create table repository configuration"""
    return TableRepositoryConfig(
        data_mode=data_mode,
        auto_refresh_interval=auto_refresh_interval,
        enable_real_time_sync=enable_real_time_sync,
        **kwargs
    )


# =============================================================================
# Documentation and Usage Examples
# =============================================================================

"""
VideoTable Repository Integration Implementation Guide

This module provides comprehensive integration between VideoTable/FilterableVideoTable
components and repository data sources:

1. **Repository Adapters**:
   - ContentRepositoryTableAdapter for content data
   - DownloadRepositoryTableAdapter for download data
   - Standardized VideoTableData format for consistent display

2. **Data Binding Integration**:
   - VideoTableDataBindingAdapter implementing IDataBindingAdapter
   - Seamless connection between repository and UI components
   - Real-time data synchronization and updates

3. **Performance Optimizations**:
   - Caching with configurable timeout
   - Lazy loading and pagination support
   - Debounced filtering and sorting
   - Asynchronous data loading with progress tracking

4. **Error Handling**:
   - Repository error integration with UI error presentation
   - Graceful error recovery and user feedback
   - Comprehensive error logging and monitoring

Usage Example:

```python
from core.data_integration.video_table_repository_adapter import (
    create_content_table_integration, create_table_repository_config,
    TableDataMode
)

# Create table
table = FilterableVideoTable(create_filterable_video_info_table_config())

# Create repository integration
config = create_table_repository_config(
    data_mode=TableDataMode.LIVE,
    auto_refresh_interval=30,
    enable_real_time_sync=True
)

binding_adapter = create_content_table_integration(
    table, content_repository, config
)

# Load initial data
binding_adapter.bind_data(DataBindingContext())

# The table will now automatically:
# - Load data from repository
# - Update when repository data changes
# - Handle errors gracefully
# - Show loading indicators
# - Support filtering and sorting
```

This integration ensures that VideoTable components are seamlessly connected
to repository data with optimal performance and user experience.
""" 