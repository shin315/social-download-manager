"""
DownloadedVideosTab Adapter for UI v1.2.1 to v2.0 Architecture Bridge

This module contains the adapter implementation that bridges the legacy DownloadedVideosTab
component with the new v2.0 architecture systems (Repository Layer, Event System),
maintaining the familiar UI while leveraging modern data management and event handling.
"""

import logging
import weakref
from typing import Any, Dict, List, Optional, Callable, Set, Tuple
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer
from PyQt6.QtWidgets import QWidget, QTabWidget, QTableWidget, QAbstractItemView
from PyQt6.QtGui import QPixmap

# Import v2.0 architecture components
from core.app_controller import AppController
from core.event_system import EventBus, EventType, Event
from data.repositories.base_repository import IRepository
from data.models.video_content import VideoContent
from data.models.download_record import DownloadRecord

# Import adapter interfaces and components
from .interfaces import (
    IDownloadedVideosTabAdapter, AdapterState, AdapterConfig, AdapterMetrics,
    AdapterPriority
)
from .event_proxy import (
    EventBridgeCoordinator, EventTranslator, LegacyEventHandler,
    get_global_coordinator
)
from .data_mappers import get_video_mapper, get_download_mapper, VideoDataMapper, DownloadDataMapper


class DownloadedVideosTabAdapterError(Exception):
    """Exception raised by DownloadedVideosTab adapter operations"""
    pass


class DownloadedVideosTabAdapter(QObject, IDownloadedVideosTabAdapter):
    """
    Adapter that bridges the legacy DownloadedVideosTab with v2.0 architecture systems.
    
    This adapter maintains the existing DownloadedVideosTab UI and behavior while
    connecting it to the Repository Layer and Event System for improved data management,
    pagination, sorting, and filtering.
    """
    
    # Signals for adapter events
    adapter_initialized = pyqtSignal()
    adapter_error = pyqtSignal(str, str)  # error_type, error_message
    video_selected = pyqtSignal(str)  # content_id
    video_deleted = pyqtSignal(str)  # content_id
    videos_filtered = pyqtSignal(dict)  # filter_criteria
    videos_sorted = pyqtSignal(str, bool)  # sort_column, ascending
    repository_data_changed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Core adapter state
        self._state = AdapterState.UNINITIALIZED
        self._config = AdapterConfig()
        self._metrics = AdapterMetrics()
        
        # v2.0 architecture components
        self._app_controller: Optional[AppController] = None
        self._event_bus: Optional[EventBus] = None
        self._repository: Optional[IRepository] = None
        self._event_translator: Optional[EventTranslator] = None
        self._legacy_handler: Optional[LegacyEventHandler] = None
        
        # Legacy component reference
        self._downloaded_videos_tab: Optional[QWidget] = None
        self._table_widget: Optional[QTableWidget] = None
        self._tab_widget_ref: Optional[weakref.ReferenceType] = None
        
        # Data mapping and caching
        self._video_mapper: VideoDataMapper = get_video_mapper()
        self._download_mapper: DownloadDataMapper = get_download_mapper()
        self._videos_cache: Dict[str, DownloadRecord] = {}
        self._filtered_videos: List[DownloadRecord] = []
        self._original_methods: Dict[str, Callable] = {}
        self._proxy_connections: List[Any] = []
        
        # Feature flags and performance
        self._feature_flags = {
            "use_v2_repository": True,
            "enable_pagination": True,
            "enable_advanced_filtering": True,
            "enable_caching": True,
            "enable_event_bridging": True,
            "enable_performance_monitoring": True,
            "enable_lazy_loading": True
        }
        
        # Performance monitoring
        self._start_time: Optional[datetime] = None
        self._method_call_counts: Dict[str, int] = {}
        self._last_error: Optional[str] = None
        self._cache_hits = 0
        self._cache_misses = 0
        
        # Pagination and filtering state
        self._current_page = 0
        self._page_size = 50
        self._total_pages = 0
        self._total_videos = 0
        self._current_filter: Optional[Dict[str, Any]] = None
        self._current_sort: Optional[Tuple[str, bool]] = None  # (column, ascending)
        
        # Video collection management
        self._loaded_videos: List[DownloadRecord] = []
        self._selected_video_ids: Set[str] = set()
        self._max_cache_size = 1000
        
        # Status tracking
        self._initialization_attempts = 0
        self._max_initialization_attempts = 3
        
        self.logger.debug("DownloadedVideosTab adapter created")
    
    def initialize(self, 
                  app_controller: AppController,
                  event_bus: EventBus,
                  config: AdapterConfig) -> bool:
        """
        Initialize the adapter with v2.0 architecture components.
        
        Args:
            app_controller: The v2.0 App Controller instance
            event_bus: The v2.0 Event Bus instance
            config: Adapter configuration
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            self._initialization_attempts += 1
            self._state = AdapterState.INITIALIZING
            self._start_time = datetime.now()
            
            # Store v2.0 components
            self._app_controller = app_controller
            self._event_bus = event_bus
            self._config = config
            
            # Initialize event system integration
            if not self._initialize_event_system():
                raise DownloadedVideosTabAdapterError("Failed to initialize event system integration")
            
            # Set up performance monitoring if enabled
            if self._config.performance_monitoring:
                self._setup_performance_monitoring()
            
            self._state = AdapterState.ACTIVE
            self.logger.info("DownloadedVideosTab adapter initialized successfully")
            self.adapter_initialized.emit()
            return True
            
        except Exception as e:
            self._state = AdapterState.ERROR
            self._last_error = str(e)
            self.logger.error(f"Failed to initialize DownloadedVideosTab adapter: {e}")
            self.adapter_error.emit("initialization", str(e))
            
            # Retry logic
            if self._initialization_attempts < self._max_initialization_attempts:
                self.logger.info(f"Retrying initialization (attempt {self._initialization_attempts + 1})")
                QTimer.singleShot(1000, lambda: self.initialize(app_controller, event_bus, config))
            
            return False 

    def attach_component(self, component: QObject) -> bool:
        """
        Attach the legacy DownloadedVideosTab component to this adapter.
        
        Args:
            component: The legacy DownloadedVideosTab instance
            
        Returns:
            True if attachment successful, False otherwise
        """
        try:
            if not isinstance(component, QWidget):
                raise DownloadedVideosTabAdapterError(f"Expected QWidget, got {type(component)}")
            
            self._downloaded_videos_tab = component
            self._tab_widget_ref = weakref.ref(component)
            
            # Find the table widget within the tab
            self._find_table_widget()
            
            # Set up method proxying for key DownloadedVideosTab methods
            if not self._setup_method_proxying():
                raise DownloadedVideosTabAdapterError("Failed to set up method proxying")
            
            # Set up signal connections for events
            if not self._setup_signal_connections():
                raise DownloadedVideosTabAdapterError("Failed to set up signal connections")
            
            # Set up repository integration
            if self._feature_flags["use_v2_repository"]:
                repository = self._app_controller.get_repository("download_records") if self._app_controller else None
                if repository and not self.setup_repository_integration(repository):
                    self.logger.warning("Failed to set up repository integration, continuing without it")
            
            # Initialize video cache and load initial data
            if self._feature_flags["enable_caching"]:
                self._setup_video_cache()
            
            # Load initial video data
            self._load_initial_data()
            
            self.logger.info("DownloadedVideosTab component attached successfully")
            return True
            
        except Exception as e:
            self._last_error = str(e)
            self.logger.error(f"Failed to attach DownloadedVideosTab component: {e}")
            self.adapter_error.emit("attachment", str(e))
            return False
    
    def detach_component(self) -> bool:
        """
        Detach the legacy DownloadedVideosTab component from this adapter.
        
        Returns:
            True if detachment successful, False otherwise
        """
        try:
            if self._downloaded_videos_tab:
                # Restore original methods
                self._restore_original_methods()
                
                # Disconnect signals
                self._disconnect_signals()
                
                # Clear cache and data
                self._videos_cache.clear()
                self._filtered_videos.clear()
                self._loaded_videos.clear()
                self._selected_video_ids.clear()
                
                # Clear references
                self._downloaded_videos_tab = None
                self._table_widget = None
                self._tab_widget_ref = None
            
            self.logger.info("DownloadedVideosTab component detached successfully")
            return True
            
        except Exception as e:
            self._last_error = str(e)
            self.logger.error(f"Failed to detach DownloadedVideosTab component: {e}")
            self.adapter_error.emit("detachment", str(e))
            return False
    
    def update(self, data: Dict[str, Any]) -> bool:
        """
        Update the adapter with new data or state.
        
        Args:
            data: Data to update the adapter with
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            # Update download records if provided
            if "download_records" in data:
                records = data["download_records"]
                if isinstance(records, list):
                    self._update_video_list(records)
                elif isinstance(records, DownloadRecord):
                    self._add_or_update_video(records)
            
            # Update pagination settings if provided
            if "pagination" in data:
                pagination = data["pagination"]
                if "page_size" in pagination:
                    self._page_size = pagination["page_size"]
                if "page" in pagination:
                    self._current_page = pagination["page"]
                    self._refresh_display()
            
            # Update filter settings if provided
            if "filter" in data:
                filter_criteria = data["filter"]
                self._apply_filter(filter_criteria)
            
            # Update sort settings if provided
            if "sort" in data:
                sort_data = data["sort"]
                column = sort_data.get("column", "date_downloaded")
                ascending = sort_data.get("ascending", False)
                self._apply_sort(column, ascending)
            
            # Update feature flags if provided
            if "feature_flags" in data:
                self._feature_flags.update(data["feature_flags"])
                self.logger.debug(f"Updated feature flags: {data['feature_flags']}")
            
            return True
            
        except Exception as e:
            self._last_error = str(e)
            self.logger.error(f"Failed to update adapter: {e}")
            self.adapter_error.emit("update", str(e))
            return False
    
    def shutdown(self) -> bool:
        """
        Shutdown the adapter gracefully.
        
        Returns:
            True if shutdown successful, False otherwise
        """
        try:
            self._state = AdapterState.SHUTTING_DOWN
            
            # Detach component
            self.detach_component()
            
            # Clean up event system
            if self._event_translator:
                self._event_translator.cleanup()
            
            if self._legacy_handler:
                self._legacy_handler.disconnect_all()
            
            # Clean up references
            self._app_controller = None
            self._event_bus = None
            self._repository = None
            self._event_translator = None
            self._legacy_handler = None
            
            self._state = AdapterState.TERMINATED
            self.logger.info("DownloadedVideosTab adapter shutdown successfully")
            return True
            
        except Exception as e:
            self._state = AdapterState.ERROR
            self._last_error = str(e)
            self.logger.error(f"Failed to shutdown adapter: {e}")
            self.adapter_error.emit("shutdown", str(e))
            return False
    
    def get_state(self) -> AdapterState:
        """Get the current state of the adapter."""
        return self._state
    
    def get_metrics(self) -> AdapterMetrics:
        """Get performance metrics for the adapter."""
        if self._start_time:
            self._metrics.uptime_seconds = int((datetime.now() - self._start_time).total_seconds())
        
        self._metrics.last_error = self._last_error
        self._metrics.memory_usage_mb = self._get_memory_usage()
        
        # Add custom metrics for downloaded videos adapter
        custom_metrics = {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "total_videos": self._total_videos,
            "loaded_videos": len(self._loaded_videos),
            "current_page": self._current_page,
            "total_pages": self._total_pages,
            "selected_videos": len(self._selected_video_ids)
        }
        
        return self._metrics
    
    def handle_error(self, error: Exception, context: str) -> bool:
        """
        Handle errors that occur in the adapter.
        
        Args:
            error: The exception that occurred
            context: Context information about where the error occurred
            
        Returns:
            True if error was handled successfully, False otherwise
        """
        try:
            self._last_error = f"{context}: {str(error)}"
            self._metrics.events_failed += 1
            
            self.logger.error(f"DownloadedVideosTab adapter error in {context}: {error}")
            self.adapter_error.emit(context, str(error))
            
            # Implement error recovery strategies
            if "repository" in context and self._feature_flags["use_v2_repository"]:
                self.logger.info("Repository error, disabling v2.0 repository features temporarily")
                self._feature_flags["use_v2_repository"] = False
                return True
            
            if "pagination" in context and self._feature_flags["enable_pagination"]:
                self.logger.info("Pagination error, disabling pagination temporarily")
                self._feature_flags["enable_pagination"] = False
                return True
            
            # For other errors, try to maintain functionality
            if self._config.enable_fallback:
                self.logger.info("Enabling fallback mode due to error")
                self._enable_fallback_mode()
                return True
            
            return False
            
        except Exception as e:
            self.logger.critical(f"Failed to handle error: {e}")
            return False 

    def setup_repository_integration(self, repository: IRepository) -> bool:
        """
        Set up integration with the download records repository.
        
        Args:
            repository: The download records repository instance
            
        Returns:
            True if setup successful, False otherwise
        """
        try:
            self._repository = repository
            
            # Register for repository events if event translator is available
            if self._event_translator:
                self._event_translator.register_v2_handler(
                    EventType.DOWNLOAD_COMPLETED,
                    self._handle_download_completed
                )
                
                self._event_translator.register_v2_handler(
                    EventType.DOWNLOAD_DELETED,
                    self._handle_download_deleted
                )
                
                self._event_translator.register_v2_handler(
                    EventType.DOWNLOAD_UPDATED,
                    self._handle_download_updated
                )
            
            self.logger.info("Repository integration set up successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set up repository integration: {e}")
            return False
    
    def load_videos_page(self, page: int = None, page_size: int = None) -> bool:
        """
        Load a specific page of videos from the repository.
        
        Args:
            page: Page number to load (0-based)
            page_size: Number of videos per page
            
        Returns:
            True if loading successful, False otherwise
        """
        try:
            if page is not None:
                self._current_page = page
            if page_size is not None:
                self._page_size = page_size
            
            if not self._repository or not self._feature_flags["enable_pagination"]:
                return self._load_all_videos()
            
            # Calculate offset
            offset = self._current_page * self._page_size
            
            # Load videos from repository with pagination
            if hasattr(self._repository, 'get_paginated'):
                result = self._repository.get_paginated(
                    offset=offset,
                    limit=self._page_size,
                    filters=self._current_filter,
                    sort_by=self._current_sort[0] if self._current_sort else None,
                    sort_ascending=self._current_sort[1] if self._current_sort else True
                )
                
                if result:
                    videos = result.get('items', [])
                    self._total_videos = result.get('total', 0)
                    self._total_pages = (self._total_videos + self._page_size - 1) // self._page_size
                    
                    # Update loaded videos
                    self._loaded_videos = videos
                    
                    # Update cache
                    if self._feature_flags["enable_caching"]:
                        for video in videos:
                            self._videos_cache[video.content_id] = video
                    
                    # Update display
                    self._update_display()
                    
                    self.logger.debug(f"Loaded page {self._current_page} with {len(videos)} videos")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to load videos page: {e}")
            self.handle_error(e, "load_videos_page")
            return False
    
    def apply_filter(self, filter_criteria: Dict[str, Any]) -> bool:
        """
        Apply filter to the video list.
        
        Args:
            filter_criteria: Filter criteria (platform, date_range, status, etc.)
            
        Returns:
            True if filter applied successfully, False otherwise
        """
        try:
            self._current_filter = filter_criteria
            self._current_page = 0  # Reset to first page
            
            # Emit filter event
            self.videos_filtered.emit(filter_criteria)
            
            # Reload data with filter
            return self.load_videos_page()
            
        except Exception as e:
            self.logger.error(f"Failed to apply filter: {e}")
            self.handle_error(e, "apply_filter")
            return False
    
    def apply_sort(self, column: str, ascending: bool = True) -> bool:
        """
        Apply sorting to the video list.
        
        Args:
            column: Column to sort by
            ascending: Sort direction
            
        Returns:
            True if sort applied successfully, False otherwise
        """
        try:
            self._current_sort = (column, ascending)
            
            # Emit sort event
            self.videos_sorted.emit(column, ascending)
            
            # Reload data with new sort
            return self.load_videos_page()
            
        except Exception as e:
            self.logger.error(f"Failed to apply sort: {e}")
            self.handle_error(e, "apply_sort")
            return False
    
    def select_video(self, content_id: str) -> bool:
        """
        Select a video in the list.
        
        Args:
            content_id: ID of the video to select
            
        Returns:
            True if selection successful, False otherwise
        """
        try:
            self._selected_video_ids.add(content_id)
            
            # Update visual selection if table widget is available
            if self._table_widget:
                self._update_table_selection()
            
            # Emit selection event
            self.video_selected.emit(content_id)
            
            self.logger.debug(f"Video selected: {content_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to select video: {e}")
            self.handle_error(e, "select_video")
            return False
    
    def delete_video(self, content_id: str) -> bool:
        """
        Delete a video from the repository and list.
        
        Args:
            content_id: ID of the video to delete
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            # Remove from repository if using v2.0
            if self._repository and self._feature_flags["use_v2_repository"]:
                if hasattr(self._repository, 'delete'):
                    self._repository.delete(content_id)
            
            # Remove from cache and local lists
            if content_id in self._videos_cache:
                del self._videos_cache[content_id]
            
            self._loaded_videos = [v for v in self._loaded_videos if v.content_id != content_id]
            self._filtered_videos = [v for v in self._filtered_videos if v.content_id != content_id]
            self._selected_video_ids.discard(content_id)
            
            # Update display
            self._update_display()
            
            # Emit deletion event
            self.video_deleted.emit(content_id)
            
            self.logger.info(f"Video deleted: {content_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete video: {e}")
            self.handle_error(e, "delete_video")
            return False
    
    def refresh_videos(self) -> bool:
        """
        Refresh the video list from the repository.
        
        Returns:
            True if refresh successful, False otherwise
        """
        try:
            # Clear cache if enabled
            if self._feature_flags["enable_caching"]:
                self._videos_cache.clear()
                self._cache_hits = 0
                self._cache_misses = 0
            
            # Reload current page
            success = self.load_videos_page()
            
            if success:
                self.repository_data_changed.emit()
                self.logger.info("Video list refreshed successfully")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to refresh videos: {e}")
            self.handle_error(e, "refresh_videos")
            return False
    
    def get_video_by_id(self, content_id: str) -> Optional[DownloadRecord]:
        """
        Get a video by its content ID.
        
        Args:
            content_id: ID of the video to retrieve
            
        Returns:
            DownloadRecord if found, None otherwise
        """
        try:
            # Check cache first
            if self._feature_flags["enable_caching"] and content_id in self._videos_cache:
                self._cache_hits += 1
                return self._videos_cache[content_id]
            
            # Check loaded videos
            for video in self._loaded_videos:
                if video.content_id == content_id:
                    return video
            
            # Query repository if available
            if self._repository and self._feature_flags["use_v2_repository"]:
                video = self._repository.get_by_id(content_id)
                if video and self._feature_flags["enable_caching"]:
                    self._videos_cache[content_id] = video
                    self._cache_misses += 1
                return video
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get video by ID: {e}")
            return None
    
    def _initialize_event_system(self) -> bool:
        """Initialize event system integration"""
        try:
            if not self._feature_flags["enable_event_bridging"]:
                return True
            
            # Get global event bridge coordinator
            coordinator = get_global_coordinator()
            
            # Initialize coordinator with v2.0 event bus if not already done
            if not coordinator._is_active:
                if not coordinator.initialize(self._event_bus):
                    raise DownloadedVideosTabAdapterError("Failed to initialize event bridge coordinator")
            
            # Create event translator
            self._event_translator = EventTranslator(coordinator)
            
            # Create legacy event handler
            self._legacy_handler = LegacyEventHandler(coordinator)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize event system: {e}")
            return False
    
    def _find_table_widget(self) -> None:
        """Find the QTableWidget within the downloaded videos tab"""
        try:
            if not self._downloaded_videos_tab:
                return
            
            # Try to find QTableWidget in the widget hierarchy
            table_widgets = self._downloaded_videos_tab.findChildren(QTableWidget)
            if table_widgets:
                self._table_widget = table_widgets[0]
                self.logger.debug("Found table widget for downloaded videos")
            else:
                self.logger.warning("No QTableWidget found in downloaded videos tab")
                
        except Exception as e:
            self.logger.error(f"Failed to find table widget: {e}")
    
    def _setup_method_proxying(self) -> bool:
        """Set up method proxying for key DownloadedVideosTab methods"""
        try:
            if not self._downloaded_videos_tab:
                return False
            
            # Methods to proxy for v2.0 integration
            methods_to_proxy = [
                'load_videos',
                'refresh_video_list',
                'filter_videos',
                'sort_videos',
                'delete_selected_videos',
                'select_video',
                'update_video_info'
            ]
            
            for method_name in methods_to_proxy:
                if hasattr(self._downloaded_videos_tab, method_name):
                    original_method = getattr(self._downloaded_videos_tab, method_name)
                    self._original_methods[method_name] = original_method
                    
                    # Create proxy method
                    proxy_method = self._create_proxy_method(method_name, original_method)
                    setattr(self._downloaded_videos_tab, method_name, proxy_method)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set up method proxying: {e}")
            return False
    
    def _create_proxy_method(self, method_name: str, original_method: Callable) -> Callable:
        """Create a proxy method that adds v2.0 integration"""
        def proxy_method(*args, **kwargs):
            try:
                # Track method calls
                self._method_call_counts[method_name] = self._method_call_counts.get(method_name, 0) + 1
                
                # Pre-processing for specific methods
                if method_name == 'filter_videos' and args:
                    filter_criteria = args[0] if isinstance(args[0], dict) else {}
                    self.apply_filter(filter_criteria)
                elif method_name == 'sort_videos' and args:
                    column = args[0] if len(args) > 0 else "date_downloaded"
                    ascending = args[1] if len(args) > 1 else True
                    self.apply_sort(column, ascending)
                elif method_name == 'delete_selected_videos':
                    for video_id in list(self._selected_video_ids):
                        self.delete_video(video_id)
                elif method_name == 'refresh_video_list':
                    self.refresh_videos()
                elif method_name == 'load_videos':
                    self.load_videos_page()
                
                # Call original method
                result = original_method(*args, **kwargs)
                
                # Post-processing
                if self._config.log_events:
                    self.logger.debug(f"Proxied method call: {method_name} with args: {args}")
                
                return result
                
            except Exception as e:
                self.logger.error(f"Error in proxy method {method_name}: {e}")
                self.handle_error(e, f"proxy_method_{method_name}")
                return None
        
        return proxy_method 

    def _setup_signal_connections(self) -> bool:
        """Set up signal connections for legacy events"""
        try:
            if not self._downloaded_videos_tab or not self._legacy_handler:
                return False
            
            # Connect video selection signal if available
            if hasattr(self._downloaded_videos_tab, 'video_selected'):
                self._legacy_handler.connect_signal(
                    self._downloaded_videos_tab.video_selected,
                    "video_selected",
                    lambda content_id: content_id
                )
            
            # Connect video deletion signal if available
            if hasattr(self._downloaded_videos_tab, 'video_deleted'):
                self._legacy_handler.connect_signal(
                    self._downloaded_videos_tab.video_deleted,
                    "video_deleted"
                )
            
            # Connect filter changed signal if available
            if hasattr(self._downloaded_videos_tab, 'filter_changed'):
                self._legacy_handler.connect_signal(
                    self._downloaded_videos_tab.filter_changed,
                    "filter_changed"
                )
            
            # Connect sort changed signal if available
            if hasattr(self._downloaded_videos_tab, 'sort_changed'):
                self._legacy_handler.connect_signal(
                    self._downloaded_videos_tab.sort_changed,
                    "sort_changed"
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set up signal connections: {e}")
            return False
    
    def _setup_video_cache(self) -> None:
        """Set up video content caching system"""
        try:
            self._videos_cache.clear()
            self._cache_hits = 0
            self._cache_misses = 0
            
            self.logger.debug("Video cache set up successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to set up video cache: {e}")
    
    def _load_initial_data(self) -> None:
        """Load initial video data"""
        try:
            self.load_videos_page(page=0)
        except Exception as e:
            self.logger.error(f"Failed to load initial data: {e}")
    
    def _load_all_videos(self) -> bool:
        """Load all videos without pagination (fallback)"""
        try:
            if not self._repository:
                return False
            
            if hasattr(self._repository, 'get_all'):
                videos = self._repository.get_all()
                self._loaded_videos = videos
                self._total_videos = len(videos)
                self._total_pages = 1
                
                # Update cache
                if self._feature_flags["enable_caching"]:
                    for video in videos:
                        self._videos_cache[video.content_id] = video
                
                # Update display
                self._update_display()
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to load all videos: {e}")
            return False
    
    def _update_display(self) -> None:
        """Update the UI display with current video data"""
        try:
            if not self._downloaded_videos_tab:
                return
            
            # Convert to legacy format for display
            legacy_videos = []
            for video in self._loaded_videos:
                legacy_video = self._download_mapper.map_to_legacy(video)
                if legacy_video:
                    legacy_videos.append(legacy_video.__dict__)
            
            # Update display using legacy interface
            if hasattr(self._downloaded_videos_tab, 'update_video_list'):
                self._downloaded_videos_tab.update_video_list(legacy_videos)
            
            # Update table widget directly if available
            if self._table_widget:
                self._update_table_widget(legacy_videos)
            
            # Update pagination info if available
            if hasattr(self._downloaded_videos_tab, 'update_pagination_info'):
                pagination_info = {
                    'current_page': self._current_page,
                    'total_pages': self._total_pages,
                    'total_videos': self._total_videos,
                    'page_size': self._page_size
                }
                self._downloaded_videos_tab.update_pagination_info(pagination_info)
            
        except Exception as e:
            self.logger.error(f"Failed to update display: {e}")
    
    def _update_table_widget(self, videos: List[Dict[str, Any]]) -> None:
        """Update the table widget with video data"""
        try:
            if not self._table_widget:
                return
            
            # Clear existing rows
            self._table_widget.setRowCount(0)
            
            # Add videos to table
            for i, video in enumerate(videos):
                self._table_widget.insertRow(i)
                
                # Add video data to columns (adjust based on actual table structure)
                columns = ['title', 'creator', 'date_downloaded', 'platform', 'quality', 'size']
                for j, column in enumerate(columns):
                    if j < self._table_widget.columnCount():
                        value = str(video.get(column, ''))
                        self._table_widget.setItem(i, j, value)
            
        except Exception as e:
            self.logger.error(f"Failed to update table widget: {e}")
    
    def _update_table_selection(self) -> None:
        """Update table selection based on selected video IDs"""
        try:
            if not self._table_widget:
                return
            
            # Clear current selection
            self._table_widget.clearSelection()
            
            # Select rows for selected video IDs
            for row in range(self._table_widget.rowCount()):
                # Get video ID from row (implementation depends on table structure)
                # This is a simplified approach
                video_id = self._get_video_id_from_row(row)
                if video_id in self._selected_video_ids:
                    self._table_widget.selectRow(row)
            
        except Exception as e:
            self.logger.error(f"Failed to update table selection: {e}")
    
    def _get_video_id_from_row(self, row: int) -> Optional[str]:
        """Get video ID from table row"""
        try:
            if not self._table_widget or row >= len(self._loaded_videos):
                return None
            
            return self._loaded_videos[row].content_id
            
        except Exception as e:
            self.logger.error(f"Failed to get video ID from row: {e}")
            return None
    
    def _add_or_update_video(self, video: DownloadRecord) -> None:
        """Add or update a video in the list"""
        try:
            # Update cache
            if self._feature_flags["enable_caching"]:
                self._videos_cache[video.content_id] = video
            
            # Update loaded videos
            for i, loaded_video in enumerate(self._loaded_videos):
                if loaded_video.content_id == video.content_id:
                    self._loaded_videos[i] = video
                    break
            else:
                # Add new video
                self._loaded_videos.append(video)
            
            # Update display
            self._update_display()
            
        except Exception as e:
            self.logger.error(f"Failed to add or update video: {e}")
    
    def _update_video_list(self, videos: List[DownloadRecord]) -> None:
        """Update the entire video list"""
        try:
            self._loaded_videos = videos
            
            # Update cache
            if self._feature_flags["enable_caching"]:
                for video in videos:
                    self._videos_cache[video.content_id] = video
            
            # Update display
            self._update_display()
            
        except Exception as e:
            self.logger.error(f"Failed to update video list: {e}")
    
    def _apply_filter(self, filter_criteria: Dict[str, Any]) -> bool:
        """Apply filter to loaded videos (internal method)"""
        try:
            if not filter_criteria:
                self._filtered_videos = self._loaded_videos.copy()
                return True
            
            filtered = []
            for video in self._loaded_videos:
                if self._video_matches_filter(video, filter_criteria):
                    filtered.append(video)
            
            self._filtered_videos = filtered
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to apply filter: {e}")
            return False
    
    def _video_matches_filter(self, video: DownloadRecord, filter_criteria: Dict[str, Any]) -> bool:
        """Check if video matches filter criteria"""
        try:
            # Platform filter
            if 'platform' in filter_criteria:
                platform = filter_criteria['platform']
                if platform and video.video_content.platform.value != platform:
                    return False
            
            # Date range filter
            if 'date_range' in filter_criteria:
                date_range = filter_criteria['date_range']
                if 'start' in date_range and video.download_date < date_range['start']:
                    return False
                if 'end' in date_range and video.download_date > date_range['end']:
                    return False
            
            # Status filter
            if 'status' in filter_criteria:
                status = filter_criteria['status']
                if status and video.status.value != status:
                    return False
            
            # Title search
            if 'title_search' in filter_criteria:
                search_term = filter_criteria['title_search'].lower()
                if search_term and search_term not in video.video_content.metadata.title.lower():
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to check filter match: {e}")
            return True  # Include by default on error
    
    def _apply_sort(self, column: str, ascending: bool) -> bool:
        """Apply sort to loaded videos (internal method)"""
        try:
            def get_sort_key(video: DownloadRecord):
                if column == 'title':
                    return video.video_content.metadata.title
                elif column == 'creator':
                    return video.video_content.metadata.creator
                elif column == 'date_downloaded':
                    return video.download_date
                elif column == 'platform':
                    return video.video_content.platform.value
                elif column == 'quality':
                    return video.quality
                elif column == 'size':
                    return video.file_size
                else:
                    return video.download_date
            
            self._loaded_videos.sort(key=get_sort_key, reverse=not ascending)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to apply sort: {e}")
            return False
    
    def _refresh_display(self) -> None:
        """Refresh the display with current data"""
        try:
            self._update_display()
        except Exception as e:
            self.logger.error(f"Failed to refresh display: {e}")
    
    def _handle_download_completed(self, event_data: Any) -> None:
        """Handle download completed events from v2.0 system"""
        try:
            if isinstance(event_data, dict) and "download_record" in event_data:
                download_record = event_data["download_record"]
                if isinstance(download_record, DownloadRecord):
                    self._add_or_update_video(download_record)
                    
        except Exception as e:
            self.logger.error(f"Failed to handle download completed: {e}")
    
    def _handle_download_deleted(self, event_data: Any) -> None:
        """Handle download deleted events from v2.0 system"""
        try:
            if isinstance(event_data, dict) and "content_id" in event_data:
                content_id = event_data["content_id"]
                self.delete_video(content_id)
                
        except Exception as e:
            self.logger.error(f"Failed to handle download deleted: {e}")
    
    def _handle_download_updated(self, event_data: Any) -> None:
        """Handle download updated events from v2.0 system"""
        try:
            if isinstance(event_data, dict) and "download_record" in event_data:
                download_record = event_data["download_record"]
                if isinstance(download_record, DownloadRecord):
                    self._add_or_update_video(download_record)
                    
        except Exception as e:
            self.logger.error(f"Failed to handle download updated: {e}")
    
    def _setup_performance_monitoring(self) -> None:
        """Set up performance monitoring"""
        try:
            if not self._config.performance_monitoring:
                return
            
            # Create timer for periodic metrics collection
            self._metrics_timer = QTimer()
            self._metrics_timer.timeout.connect(self._collect_metrics)
            self._metrics_timer.start(15000)  # Collect every 15 seconds
            
        except Exception as e:
            self.logger.error(f"Failed to set up performance monitoring: {e}")
    
    def _collect_metrics(self) -> None:
        """Collect performance metrics"""
        try:
            # Update uptime
            if self._start_time:
                uptime = (datetime.now() - self._start_time).total_seconds()
                self._metrics.uptime_seconds = int(uptime)
            
            # Update memory usage
            self._metrics.memory_usage_mb = self._get_memory_usage()
            
            # Calculate average response time (simplified)
            total_calls = sum(self._method_call_counts.values())
            if total_calls > 0:
                self._metrics.average_response_time_ms = self._metrics.uptime_seconds * 1000 / total_calls
            
            # Update data transformation count
            self._metrics.data_transformations = len(self._videos_cache)
                
        except Exception as e:
            self.logger.error(f"Failed to collect metrics: {e}")
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0
        except Exception:
            return 0.0
    
    def _enable_fallback_mode(self) -> None:
        """Enable fallback mode for error recovery"""
        try:
            # Disable v2.0 features and fall back to legacy behavior
            self._feature_flags["use_v2_repository"] = False
            self._feature_flags["enable_pagination"] = False
            self._feature_flags["enable_advanced_filtering"] = False
            self._feature_flags["enable_event_bridging"] = False
            self._feature_flags["enable_caching"] = False
            
            self.logger.warning("DownloadedVideosTab fallback mode enabled due to errors")
            
        except Exception as e:
            self.logger.error(f"Failed to enable fallback mode: {e}")
    
    def _restore_original_methods(self) -> None:
        """Restore original methods that were proxied"""
        try:
            for method_name, original_method in self._original_methods.items():
                if self._downloaded_videos_tab and hasattr(self._downloaded_videos_tab, method_name):
                    setattr(self._downloaded_videos_tab, method_name, original_method)
            
            self._original_methods.clear()
            
        except Exception as e:
            self.logger.error(f"Failed to restore original methods: {e}")
    
    def _disconnect_signals(self) -> None:
        """Disconnect all signal connections"""
        try:
            for connection in self._proxy_connections:
                try:
                    connection.disconnect()
                except Exception:
                    pass  # Connection might already be disconnected
            
            self._proxy_connections.clear()
            
        except Exception as e:
            self.logger.error(f"Failed to disconnect signals: {e}")


# Factory function for easy adapter creation
def create_downloaded_videos_tab_adapter() -> DownloadedVideosTabAdapter:
    """Create a DownloadedVideosTab adapter instance"""
    return DownloadedVideosTabAdapter()


# Global adapter instance
_global_downloaded_videos_tab_adapter: Optional[DownloadedVideosTabAdapter] = None


def get_global_downloaded_videos_tab_adapter() -> DownloadedVideosTabAdapter:
    """Get the global DownloadedVideosTab adapter instance"""
    global _global_downloaded_videos_tab_adapter
    if _global_downloaded_videos_tab_adapter is None:
        _global_downloaded_videos_tab_adapter = DownloadedVideosTabAdapter()
    return _global_downloaded_videos_tab_adapter 