"""
VideoInfoTab Adapter for UI v1.2.1 to v2.0 Architecture Bridge

This module contains the adapter implementation that bridges the legacy VideoInfoTab
component with the new v2.0 architecture systems (Repository Layer, Event System,
Platform Handlers), maintaining the familiar UI while leveraging modern architecture.
"""

import logging
import weakref
from typing import Any, Dict, List, Optional, Callable, Set
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer
from PyQt6.QtWidgets import QWidget, QTabWidget
from PyQt6.QtGui import QPixmap

# Import v2.0 architecture components
from core.app_controller import AppController
from core.event_system import EventBus, EventType, Event
# data.repositories doesn't exist - using core components directly

# Import v2.0 data models
from data.models.content import VideoContent
from data.models.downloads import DownloadModel

# Import adapter interfaces and components
from .interfaces import (
    IVideoInfoTabAdapter, AdapterState, AdapterConfig, AdapterMetrics,
    AdapterPriority, IRepository
)
from .event_proxy import (
    EventBridgeCoordinator, EventTranslator, LegacyEventHandler,
    get_global_coordinator
)
from .data_mappers import get_video_mapper, VideoDataMapper


class VideoInfoTabAdapterError(Exception):
    """Exception raised by VideoInfoTab adapter operations"""
    pass


class VideoInfoTabAdapter(QObject):
    """
    Adapter that bridges the legacy VideoInfoTab with v2.0 architecture systems.
    
    This adapter handles video URL input, information retrieval, and download
    initiation while integrating with the v2.0 App Controller and Event System.
    
    Implements IVideoInfoTabAdapter interface manually to avoid metaclass conflicts.
    """
    
    # Signals for adapter events
    adapter_initialized = pyqtSignal()
    adapter_error = pyqtSignal(str, str)  # error_type, error_message
    video_url_entered = pyqtSignal(str)  # video_url
    video_info_updated = pyqtSignal(dict)  # video_info
    download_requested = pyqtSignal(dict)  # download_options
    repository_data_changed = pyqtSignal(str)  # content_id
    
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
        self._video_info_tab: Optional[QWidget] = None
        self._tab_widget_ref: Optional[weakref.ReferenceType] = None
        
        # Data mapping and caching
        self._video_mapper: VideoDataMapper = get_video_mapper()
        self._video_cache: Dict[str, VideoContent] = {}
        self._url_processing_cache: Dict[str, bool] = {}
        self._original_methods: Dict[str, Callable] = {}
        self._proxy_connections: List[Any] = []
        
        # Feature flags and performance
        self._feature_flags = {
            "use_v2_repository": True,
            "use_v2_platform_handlers": True,
            "enable_video_caching": True,
            "enable_event_bridging": True,
            "enable_performance_monitoring": True,
            "enable_auto_metadata_fetch": True
        }
        
        # Performance monitoring
        self._start_time: Optional[datetime] = None
        self._method_call_counts: Dict[str, int] = {}
        self._last_error: Optional[str] = None
        self._cache_hits = 0
        self._cache_misses = 0
        
        # Video processing state
        self._current_video_url: Optional[str] = None
        self._current_video_content: Optional[VideoContent] = None
        self._processing_queue: List[str] = []
        self._max_cache_size = 100
        
        # Status tracking
        self._initialization_attempts = 0
        self._max_initialization_attempts = 3
        
        self.logger.debug("VideoInfoTab adapter created")
    
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
                raise VideoInfoTabAdapterError("Failed to initialize event system integration")
            
            # Set up performance monitoring if enabled
            if self._config.performance_monitoring:
                self._setup_performance_monitoring()
            
            self._state = AdapterState.ACTIVE
            self.logger.info("VideoInfoTab adapter initialized successfully")
            self.adapter_initialized.emit()
            return True
            
        except Exception as e:
            self._state = AdapterState.ERROR
            self._last_error = str(e)
            self.logger.error(f"Failed to initialize VideoInfoTab adapter: {e}")
            self.adapter_error.emit("initialization", str(e))
            
            # Retry logic
            if self._initialization_attempts < self._max_initialization_attempts:
                self.logger.info(f"Retrying initialization (attempt {self._initialization_attempts + 1})")
                QTimer.singleShot(1000, lambda: self.initialize(app_controller, event_bus, config))
            
            return False
    
    def attach_component(self, component: QObject) -> bool:
        """
        Attach the legacy VideoInfoTab component to this adapter.
        
        Args:
            component: The legacy VideoInfoTab instance
            
        Returns:
            True if attachment successful, False otherwise
        """
        try:
            if not isinstance(component, QWidget):
                raise VideoInfoTabAdapterError(f"Expected QWidget, got {type(component)}")
            
            self._video_info_tab = component
            self._tab_widget_ref = weakref.ref(component)
            
            # Set up method proxying for key VideoInfoTab methods
            if not self._setup_method_proxying():
                raise VideoInfoTabAdapterError("Failed to set up method proxying")
            
            # Set up signal connections for events
            if not self._setup_signal_connections():
                raise VideoInfoTabAdapterError("Failed to set up signal connections")
            
            # Set up repository integration
            if self._feature_flags["use_v2_repository"]:
                repository = self._app_controller.get_repository("video_content") if self._app_controller else None
                if repository and not self.setup_repository_integration(repository):
                    self.logger.warning("Failed to set up repository integration, continuing without it")
            
            # Initialize video cache
            if self._feature_flags["enable_video_caching"]:
                self._setup_video_cache()
            
            self.logger.info("VideoInfoTab component attached successfully")
            return True
            
        except Exception as e:
            self._last_error = str(e)
            self.logger.error(f"Failed to attach VideoInfoTab component: {e}")
            self.adapter_error.emit("attachment", str(e))
            return False
    
    def detach_component(self) -> bool:
        """
        Detach the legacy VideoInfoTab component from this adapter.
        
        Returns:
            True if detachment successful, False otherwise
        """
        try:
            if self._video_info_tab:
                # Restore original methods
                self._restore_original_methods()
                
                # Disconnect signals
                self._disconnect_signals()
                
                # Clear cache
                self._video_cache.clear()
                self._url_processing_cache.clear()
                
                # Clear references
                self._video_info_tab = None
                self._tab_widget_ref = None
            
            self.logger.info("VideoInfoTab component detached successfully")
            return True
            
        except Exception as e:
            self._last_error = str(e)
            self.logger.error(f"Failed to detach VideoInfoTab component: {e}")
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
            # Update video information if provided
            if "video_content" in data:
                video_content = data["video_content"]
                if isinstance(video_content, VideoContent):
                    self._update_video_content(video_content)
                elif isinstance(video_content, dict):
                    # Convert dict to VideoContent
                    mapped_content = self._video_mapper.map_to_v2(video_content)
                    if mapped_content:
                        self._update_video_content(mapped_content)
            
            # Update feature flags if provided
            if "feature_flags" in data:
                self._feature_flags.update(data["feature_flags"])
                self.logger.debug(f"Updated feature flags: {data['feature_flags']}")
            
            # Update cache settings if provided
            if "cache_settings" in data:
                cache_settings = data["cache_settings"]
                if "max_size" in cache_settings:
                    self._max_cache_size = cache_settings["max_size"]
                    self._trim_cache()
            
            # Update metrics if provided
            if "metrics" in data:
                metrics_data = data["metrics"]
                self._metrics.events_processed += metrics_data.get("events_processed", 0)
                self._metrics.data_transformations += metrics_data.get("data_transformations", 0)
            
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
            self.logger.info("VideoInfoTab adapter shutdown successfully")
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
        
        # Add custom metrics for video adapter
        custom_metrics = {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_size": len(self._video_cache),
            "videos_processed": len(self._video_cache),
            "processing_queue_size": len(self._processing_queue)
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
            
            self.logger.error(f"VideoInfoTab adapter error in {context}: {error}")
            self.adapter_error.emit(context, str(error))
            
            # Implement error recovery strategies
            if "repository" in context and self._feature_flags["use_v2_repository"]:
                self.logger.info("Repository error, disabling v2.0 repository features temporarily")
                self._feature_flags["use_v2_repository"] = False
                return True
            
            if "platform" in context and self._feature_flags["use_v2_platform_handlers"]:
                self.logger.info("Platform handler error, falling back to legacy processing")
                self._feature_flags["use_v2_platform_handlers"] = False
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
        Set up integration with the video content repository.
        
        Args:
            repository: The content repository instance
            
        Returns:
            True if setup successful, False otherwise
        """
        try:
            self._repository = repository
            
            # Register for repository events if event translator is available
            if self._event_translator:
                self._event_translator.register_v2_handler(
                    EventType.CONTENT_METADATA_UPDATED,
                    self._handle_repository_content_update
                )
                
                self._event_translator.register_v2_handler(
                    EventType.CONTENT_PROCESSING_COMPLETED,
                    self._handle_content_processing_completed
                )
            
            self.logger.info("Repository integration set up successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set up repository integration: {e}")
            return False
    
    def handle_url_input(self, url: str) -> bool:
        """
        Handle URL input through the v2.0 platform handler system.
        
        Args:
            url: Video URL to process
            
        Returns:
            True if URL processed successfully, False otherwise
        """
        try:
            if not url or not url.strip():
                return False
            
            url = url.strip()
            self._current_video_url = url
            
            # Check cache first if enabled
            if self._feature_flags["enable_video_caching"]:
                cached_content = self._get_cached_video(url)
                if cached_content:
                    self._cache_hits += 1
                    self._update_video_display(cached_content)
                    return True
                else:
                    self._cache_misses += 1
            
            # Add to processing queue
            if url not in self._processing_queue:
                self._processing_queue.append(url)
            
            # Emit v2.0 event for URL processing
            if self._event_translator:
                self._event_translator.emit_v2_event(
                    EventType.CONTENT_URL_ENTERED,
                    {"url": url, "source": "video_info_tab"}
                )
            
            # Also emit legacy event for backward compatibility
            self.video_url_entered.emit(url)
            
            # Start processing if using v2.0 platform handlers
            if self._feature_flags["use_v2_platform_handlers"]:
                self._process_url_v2(url)
            
            self.logger.debug(f"URL input handled: {url}")
            self._method_call_counts["handle_url_input"] = self._method_call_counts.get("handle_url_input", 0) + 1
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to handle URL input: {e}")
            self.handle_error(e, "handle_url_input")
            return False
    
    def update_video_info_display(self, video_data: Dict[str, Any]) -> bool:
        """
        Update the video information display with repository data.
        
        Args:
            video_data: Video information from the repository
            
        Returns:
            True if display updated successfully, False otherwise
        """
        try:
            if not self._video_info_tab:
                return False
            
            # Convert to VideoContent if needed
            video_content = None
            if isinstance(video_data, dict):
                video_content = self._video_mapper.map_to_v2(video_data)
            elif isinstance(video_data, VideoContent):
                video_content = video_data
            
            if not video_content:
                self.logger.error("Failed to map video data to VideoContent")
                return False
            
            # Update cache
            if self._feature_flags["enable_video_caching"]:
                self._cache_video(video_content)
            
            # Update display using legacy interface
            legacy_data = self._video_mapper.map_to_legacy(video_content)
            if legacy_data and hasattr(self._video_info_tab, 'update_video_info'):
                self._video_info_tab.update_video_info(legacy_data.__dict__)
            
            # Update current video content
            self._current_video_content = video_content
            
            # Emit update events
            self.video_info_updated.emit(legacy_data.__dict__ if legacy_data else {})
            self.repository_data_changed.emit(video_content.content_id)
            
            self.logger.debug(f"Video info display updated for: {video_content.content_id}")
            self._metrics.data_transformations += 1
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update video info display: {e}")
            self.handle_error(e, "update_video_info_display")
            return False
    
    def handle_download_request(self, download_options: Dict[str, Any]) -> bool:
        """
        Handle download requests through the v2.0 download system.
        
        Args:
            download_options: Download configuration options
            
        Returns:
            True if download initiated successfully, False otherwise
        """
        try:
            if not self._current_video_content:
                self.logger.warning("No current video content for download request")
                return False
            
            # Enhance download options with current video data
            enhanced_options = {
                **download_options,
                "content_id": self._current_video_content.content_id,
                "url": self._current_video_content.url,
                "title": self._current_video_content.metadata.title,
                "platform": self._current_video_content.platform.value if self._current_video_content.platform else "unknown"
            }
            
            # Emit v2.0 download request event
            if self._event_translator:
                self._event_translator.emit_v2_event(
                    EventType.DOWNLOAD_REQUESTED,
                    enhanced_options
                )
            
            # Also emit legacy event
            self.download_requested.emit(enhanced_options)
            
            self.logger.info(f"Download request handled for: {self._current_video_content.content_id}")
            self._method_call_counts["handle_download_request"] = self._method_call_counts.get("handle_download_request", 0) + 1
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to handle download request: {e}")
            self.handle_error(e, "handle_download_request")
            return False
    
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
                    raise VideoInfoTabAdapterError("Failed to initialize event bridge coordinator")
            
            # Create event translator
            self._event_translator = EventTranslator(coordinator)
            
            # Create legacy event handler
            self._legacy_handler = LegacyEventHandler(coordinator)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize event system: {e}")
            return False
    
    def _setup_method_proxying(self) -> bool:
        """Set up method proxying for key VideoInfoTab methods"""
        try:
            if not self._video_info_tab:
                return False
            
            # Methods to proxy for v2.0 integration
            methods_to_proxy = [
                'set_video_url',
                'update_video_info',
                'clear_video_info',
                'request_download',
                'refresh_video_data'
            ]
            
            for method_name in methods_to_proxy:
                if hasattr(self._video_info_tab, method_name):
                    original_method = getattr(self._video_info_tab, method_name)
                    self._original_methods[method_name] = original_method
                    
                    # Create proxy method
                    proxy_method = self._create_proxy_method(method_name, original_method)
                    setattr(self._video_info_tab, method_name, proxy_method)
            
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
                if method_name == 'set_video_url' and args:
                    url = args[0]
                    self.handle_url_input(url)
                elif method_name == 'request_download' and args:
                    download_options = args[0] if isinstance(args[0], dict) else {}
                    self.handle_download_request(download_options)
                elif method_name == 'update_video_info' and args:
                    video_data = args[0] if isinstance(args[0], dict) else {}
                    self.update_video_info_display(video_data)
                
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
            if not self._video_info_tab or not self._legacy_handler:
                return False
            
            # Connect URL input signal if available
            if hasattr(self._video_info_tab, 'url_input_changed'):
                self._legacy_handler.connect_signal(
                    self._video_info_tab.url_input_changed,
                    "video_url_changed",
                    lambda url: url
                )
            
            # Connect video info updated signal if available
            if hasattr(self._video_info_tab, 'video_info_updated'):
                self._legacy_handler.connect_signal(
                    self._video_info_tab.video_info_updated,
                    "video_info_updated"
                )
            
            # Connect download request signal if available
            if hasattr(self._video_info_tab, 'download_requested'):
                self._legacy_handler.connect_signal(
                    self._video_info_tab.download_requested,
                    "download_requested"
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set up signal connections: {e}")
            return False
    
    def _setup_video_cache(self) -> None:
        """Set up video content caching system"""
        try:
            self._video_cache.clear()
            self._url_processing_cache.clear()
            self._cache_hits = 0
            self._cache_misses = 0
            
            self.logger.debug("Video cache set up successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to set up video cache: {e}")
    
    def _cache_video(self, video_content: VideoContent) -> None:
        """Cache video content"""
        try:
            if not self._feature_flags["enable_video_caching"]:
                return
            
            # Use URL as cache key
            cache_key = video_content.url
            self._video_cache[cache_key] = video_content
            
            # Trim cache if needed
            if len(self._video_cache) > self._max_cache_size:
                self._trim_cache()
            
        except Exception as e:
            self.logger.error(f"Failed to cache video: {e}")
    
    def _get_cached_video(self, url: str) -> Optional[VideoContent]:
        """Get cached video content"""
        try:
            return self._video_cache.get(url)
        except Exception as e:
            self.logger.error(f"Failed to get cached video: {e}")
            return None
    
    def _trim_cache(self) -> None:
        """Trim cache to maximum size"""
        try:
            if len(self._video_cache) <= self._max_cache_size:
                return
            
            # Remove oldest entries (simple approach)
            items_to_remove = len(self._video_cache) - self._max_cache_size
            keys_to_remove = list(self._video_cache.keys())[:items_to_remove]
            
            for key in keys_to_remove:
                del self._video_cache[key]
            
            self.logger.debug(f"Trimmed cache, removed {items_to_remove} entries")
            
        except Exception as e:
            self.logger.error(f"Failed to trim cache: {e}")
    
    def _process_url_v2(self, url: str) -> None:
        """Process URL using v2.0 platform handlers"""
        try:
            if not self._app_controller:
                return
            
            # Get appropriate platform handler
            platform_handler = self._app_controller.get_platform_handler(url)
            if not platform_handler:
                self.logger.warning(f"No platform handler found for URL: {url}")
                return
            
            # Process URL asynchronously
            # This is a simplified approach - in real implementation you'd want
            # proper async handling
            self.logger.debug(f"Processing URL with v2.0 platform handler: {url}")
            
        except Exception as e:
            self.logger.error(f"Failed to process URL with v2.0: {e}")
    
    def _update_video_content(self, video_content: VideoContent) -> None:
        """Update current video content and display"""
        try:
            self._current_video_content = video_content
            
            # Update cache
            if self._feature_flags["enable_video_caching"]:
                self._cache_video(video_content)
            
            # Update display
            self._update_video_display(video_content)
            
            # Remove from processing queue if present
            if video_content.url in self._processing_queue:
                self._processing_queue.remove(video_content.url)
            
        except Exception as e:
            self.logger.error(f"Failed to update video content: {e}")
    
    def _update_video_display(self, video_content: VideoContent) -> None:
        """Update the video display with content"""
        try:
            if not self._video_info_tab:
                return
            
            # Convert to legacy format
            legacy_data = self._video_mapper.map_to_legacy(video_content)
            if not legacy_data:
                self.logger.error("Failed to map video content to legacy format")
                return
            
            # Update display fields if methods exist
            if hasattr(self._video_info_tab, 'set_title'):
                self._video_info_tab.set_title(legacy_data.title)
            
            if hasattr(self._video_info_tab, 'set_creator'):
                self._video_info_tab.set_creator(legacy_data.creator)
            
            if hasattr(self._video_info_tab, 'set_duration'):
                self._video_info_tab.set_duration(legacy_data.duration)
            
            if hasattr(self._video_info_tab, 'set_quality'):
                self._video_info_tab.set_quality(legacy_data.quality)
            
            if hasattr(self._video_info_tab, 'set_thumbnail'):
                self._video_info_tab.set_thumbnail(legacy_data.thumbnail_url)
            
            # Update all info at once if method exists
            if hasattr(self._video_info_tab, 'update_video_info'):
                self._video_info_tab.update_video_info(legacy_data.__dict__)
            
        except Exception as e:
            self.logger.error(f"Failed to update video display: {e}")
    
    def _handle_repository_content_update(self, event_data: Any) -> None:
        """Handle repository content update events"""
        try:
            if isinstance(event_data, dict) and "content_id" in event_data:
                content_id = event_data["content_id"]
                
                # Fetch updated content from repository
                if self._repository:
                    updated_content = self._repository.get_by_id(content_id)
                    if updated_content and isinstance(updated_content, VideoContent):
                        self._update_video_content(updated_content)
                        
        except Exception as e:
            self.logger.error(f"Failed to handle repository content update: {e}")
    
    def _handle_content_processing_completed(self, event_data: Any) -> None:
        """Handle content processing completion events"""
        try:
            if isinstance(event_data, dict):
                url = event_data.get("url")
                content_id = event_data.get("content_id")
                
                if url and self._repository:
                    # Fetch the processed content
                    content = self._repository.get_by_url(url)
                    if content and isinstance(content, VideoContent):
                        self._update_video_content(content)
                        
        except Exception as e:
            self.logger.error(f"Failed to handle content processing completion: {e}")
    
    def _setup_performance_monitoring(self) -> None:
        """Set up performance monitoring"""
        try:
            if not self._config.performance_monitoring:
                return
            
            # Create timer for periodic metrics collection
            self._metrics_timer = QTimer()
            self._metrics_timer.timeout.connect(self._collect_metrics)
            self._metrics_timer.start(10000)  # Collect every 10 seconds
            
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
            self._metrics.data_transformations = len(self._video_cache)
                
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
            self._feature_flags["use_v2_platform_handlers"] = False
            self._feature_flags["enable_event_bridging"] = False
            self._feature_flags["enable_video_caching"] = False
            
            self.logger.warning("VideoInfoTab fallback mode enabled due to errors")
            
        except Exception as e:
            self.logger.error(f"Failed to enable fallback mode: {e}")
    
    def _restore_original_methods(self) -> None:
        """Restore original methods that were proxied"""
        try:
            for method_name, original_method in self._original_methods.items():
                if self._video_info_tab and hasattr(self._video_info_tab, method_name):
                    setattr(self._video_info_tab, method_name, original_method)
            
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
def create_video_info_tab_adapter() -> VideoInfoTabAdapter:
    """Create a VideoInfoTab adapter instance"""
    return VideoInfoTabAdapter()


# Global adapter instance
_global_video_info_tab_adapter: Optional[VideoInfoTabAdapter] = None


def get_global_video_info_tab_adapter() -> VideoInfoTabAdapter:
    """Get the global VideoInfoTab adapter instance"""
    global _global_video_info_tab_adapter
    if _global_video_info_tab_adapter is None:
        _global_video_info_tab_adapter = VideoInfoTabAdapter()
    return _global_video_info_tab_adapter 