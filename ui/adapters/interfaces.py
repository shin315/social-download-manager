"""
Adapter Interfaces for UI v1.2.1 to v2.0 Architecture Bridge

This module defines the interfaces that bridge between legacy UI components
and the new v2.0 architecture systems, ensuring clean separation of concerns
and maintainable code during the transition period.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, Union
from enum import Enum
from dataclasses import dataclass
from PyQt6.QtCore import QObject

# Import v2.0 architecture components
from core.app_controller import AppController
from core.event_system import EventBus, EventType

# Optional import for repository interfaces - handle gracefully if not available
try:
    from data.repositories.base_repository import IRepository
except ImportError:
    # Create a placeholder interface if the repository system is not available
    class IRepository:
        """Placeholder repository interface"""
        pass


class AdapterState(Enum):
    """States for adapter lifecycle management"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    SHUTTING_DOWN = "shutting_down"
    TERMINATED = "terminated"
    ERROR = "error"


class AdapterPriority(Enum):
    """Priority levels for adapter operations"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class AdapterConfig:
    """Configuration for adapter behavior"""
    enable_fallback: bool = True
    log_events: bool = True
    performance_monitoring: bool = True
    event_throttling: bool = False
    throttle_interval_ms: int = 100
    max_retries: int = 3
    timeout_seconds: int = 30
    debug_mode: bool = False


@dataclass
class AdapterMetrics:
    """Metrics for adapter performance monitoring"""
    events_processed: int = 0
    events_failed: int = 0
    data_transformations: int = 0
    average_response_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    last_error: Optional[str] = None
    uptime_seconds: int = 0


class IUIComponentAdapter(ABC):
    """
    Base interface for all UI component adapters.
    
    This interface defines the core lifecycle and behavior for adapters
    that bridge legacy UI components with the v2.0 architecture.
    """
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def attach_component(self, component: QObject) -> bool:
        """
        Attach the legacy UI component to this adapter.
        
        Args:
            component: The legacy UI component (MainWindow, VideoInfoTab, etc.)
            
        Returns:
            True if attachment successful, False otherwise
        """
        pass
    
    @abstractmethod
    def detach_component(self) -> bool:
        """
        Detach the legacy UI component from this adapter.
        
        Returns:
            True if detachment successful, False otherwise
        """
        pass
    
    @abstractmethod
    def update(self, data: Dict[str, Any]) -> bool:
        """
        Update the adapter with new data or state.
        
        Args:
            data: Data to update the adapter with
            
        Returns:
            True if update successful, False otherwise
        """
        pass
    
    @abstractmethod
    def shutdown(self) -> bool:
        """
        Shutdown the adapter gracefully.
        
        Returns:
            True if shutdown successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_state(self) -> AdapterState:
        """Get the current state of the adapter."""
        pass
    
    @abstractmethod
    def get_metrics(self) -> AdapterMetrics:
        """Get performance metrics for the adapter."""
        pass
    
    @abstractmethod
    def handle_error(self, error: Exception, context: str) -> bool:
        """
        Handle errors that occur in the adapter.
        
        Args:
            error: The exception that occurred
            context: Context information about where the error occurred
            
        Returns:
            True if error was handled successfully, False otherwise
        """
        pass


class IMainWindowAdapter(IUIComponentAdapter):
    """
    Interface for MainWindow adapter that bridges the main window
    with the v2.0 App Controller and architecture systems.
    """
    
    @abstractmethod
    def setup_menu_integration(self) -> bool:
        """
        Set up integration between MainWindow menus and v2.0 systems.
        
        Returns:
            True if setup successful, False otherwise
        """
        pass
    
    @abstractmethod
    def setup_status_bar_integration(self) -> bool:
        """
        Set up integration between status bar and v2.0 event system.
        
        Returns:
            True if setup successful, False otherwise
        """
        pass
    
    @abstractmethod
    def handle_theme_change(self, theme: str) -> bool:
        """
        Handle theme changes through the v2.0 configuration system.
        
        Args:
            theme: Theme name (e.g., "dark", "light")
            
        Returns:
            True if theme change handled successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def handle_language_change(self, language: str) -> bool:
        """
        Handle language changes through the v2.0 configuration system.
        
        Args:
            language: Language code (e.g., "en", "vi")
            
        Returns:
            True if language change handled successfully, False otherwise
        """
        pass


class IVideoInfoTabAdapter(IUIComponentAdapter):
    """
    Interface for VideoInfoTab adapter that bridges video information
    display with the v2.0 Repository Layer and Event System.
    """
    
    @abstractmethod
    def setup_repository_integration(self, repository: IRepository) -> bool:
        """
        Set up integration with the video content repository.
        
        Args:
            repository: The content repository instance
            
        Returns:
            True if setup successful, False otherwise
        """
        pass
    
    @abstractmethod
    def handle_url_input(self, url: str) -> bool:
        """
        Handle URL input through the v2.0 platform handler system.
        
        Args:
            url: Video URL to process
            
        Returns:
            True if URL processed successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def update_video_info_display(self, video_data: Dict[str, Any]) -> bool:
        """
        Update the video information display with repository data.
        
        Args:
            video_data: Video information from the repository
            
        Returns:
            True if display updated successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def handle_download_request(self, download_options: Dict[str, Any]) -> bool:
        """
        Handle download requests through the v2.0 download system.
        
        Args:
            download_options: Download configuration options
            
        Returns:
            True if download initiated successfully, False otherwise
        """
        pass


class IDownloadedVideosTabAdapter(IUIComponentAdapter):
    """
    Interface for DownloadedVideosTab adapter that bridges downloaded
    videos management with the v2.0 Repository Layer and Event System.
    """
    
    @abstractmethod
    def setup_download_repository_integration(self, repository: IRepository) -> bool:
        """
        Set up integration with the download repository.
        
        Args:
            repository: The download repository instance
            
        Returns:
            True if setup successful, False otherwise
        """
        pass
    
    @abstractmethod
    def refresh_video_list(self) -> bool:
        """
        Refresh the video list from the repository.
        
        Returns:
            True if refresh successful, False otherwise
        """
        pass
    
    @abstractmethod
    def handle_video_selection(self, video_ids: List[str]) -> bool:
        """
        Handle video selection events.
        
        Args:
            video_ids: List of selected video IDs
            
        Returns:
            True if selection handled successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def handle_video_actions(self, action: str, video_ids: List[str]) -> bool:
        """
        Handle actions on selected videos (delete, re-download, etc.).
        
        Args:
            action: Action to perform
            video_ids: List of video IDs to act on
            
        Returns:
            True if actions performed successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def update_download_progress(self, video_id: str, progress: Dict[str, Any]) -> bool:
        """
        Update download progress for a specific video.
        
        Args:
            video_id: ID of the video being downloaded
            progress: Progress information
            
        Returns:
            True if progress updated successfully, False otherwise
        """
        pass


class IEventProxyAdapter(ABC):
    """
    Interface for event proxy adapters that translate between
    legacy event mechanisms and the v2.0 Event System.
    """
    
    @abstractmethod
    def register_legacy_handler(self, 
                               event_name: str, 
                               handler: Callable[[Any], None]) -> bool:
        """
        Register a legacy event handler.
        
        Args:
            event_name: Name of the legacy event
            handler: Legacy event handler function
            
        Returns:
            True if registration successful, False otherwise
        """
        pass
    
    @abstractmethod
    def register_v2_handler(self, 
                           event_type: EventType, 
                           handler: Callable[[Any], None]) -> bool:
        """
        Register a v2.0 event handler.
        
        Args:
            event_type: v2.0 event type
            handler: v2.0 event handler function
            
        Returns:
            True if registration successful, False otherwise
        """
        pass
    
    @abstractmethod
    def translate_event(self, 
                       source_event: Any, 
                       target_format: str) -> Optional[Any]:
        """
        Translate an event between legacy and v2.0 formats.
        
        Args:
            source_event: Source event to translate
            target_format: Target format ("legacy" or "v2")
            
        Returns:
            Translated event or None if translation failed
        """
        pass
    
    @abstractmethod
    def emit_legacy_event(self, event_name: str, data: Any) -> bool:
        """
        Emit an event in legacy format.
        
        Args:
            event_name: Name of the event
            data: Event data
            
        Returns:
            True if event emitted successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def emit_v2_event(self, event_type: EventType, data: Any) -> bool:
        """
        Emit an event in v2.0 format.
        
        Args:
            event_type: v2.0 event type
            data: Event data
            
        Returns:
            True if event emitted successfully, False otherwise
        """
        pass


class IDataMapperAdapter(ABC):
    """
    Interface for data mapper adapters that transform data structures
    between v1.2.1 and v2.0 formats.
    """
    
    @abstractmethod
    def map_to_v2(self, legacy_data: Any) -> Optional[Any]:
        """
        Map legacy data structure to v2.0 format.
        
        Args:
            legacy_data: Data in legacy format
            
        Returns:
            Data in v2.0 format or None if mapping failed
        """
        pass
    
    @abstractmethod
    def map_to_legacy(self, v2_data: Any) -> Optional[Any]:
        """
        Map v2.0 data structure to legacy format.
        
        Args:
            v2_data: Data in v2.0 format
            
        Returns:
            Data in legacy format or None if mapping failed
        """
        pass
    
    @abstractmethod
    def validate_legacy_data(self, data: Any) -> bool:
        """
        Validate data in legacy format.
        
        Args:
            data: Data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        pass
    
    @abstractmethod
    def validate_v2_data(self, data: Any) -> bool:
        """
        Validate data in v2.0 format.
        
        Args:
            data: Data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        pass
    
    @abstractmethod
    def get_supported_types(self) -> List[str]:
        """
        Get list of supported data types for mapping.
        
        Returns:
            List of supported data type names
        """
        pass


@dataclass
class AdapterRegistration:
    """Registration information for an adapter"""
    adapter_id: str
    adapter_type: str
    adapter_instance: IUIComponentAdapter
    component_type: str
    priority: AdapterPriority
    config: AdapterConfig
    created_at: float
    is_active: bool = False


class IAdapterRegistry(ABC):
    """
    Interface for adapter registry that manages all adapter instances.
    """
    
    @abstractmethod
    def register_adapter(self, 
                        adapter_id: str,
                        adapter: IUIComponentAdapter,
                        component_type: str,
                        priority: AdapterPriority = AdapterPriority.NORMAL,
                        config: Optional[AdapterConfig] = None) -> bool:
        """
        Register an adapter with the registry.
        
        Args:
            adapter_id: Unique identifier for the adapter
            adapter: Adapter instance
            component_type: Type of component being adapted
            priority: Adapter priority
            config: Adapter configuration
            
        Returns:
            True if registration successful, False otherwise
        """
        pass
    
    @abstractmethod
    def unregister_adapter(self, adapter_id: str) -> bool:
        """
        Unregister an adapter from the registry.
        
        Args:
            adapter_id: ID of adapter to unregister
            
        Returns:
            True if unregistration successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_adapter(self, adapter_id: str) -> Optional[IUIComponentAdapter]:
        """
        Get an adapter by ID.
        
        Args:
            adapter_id: ID of adapter to retrieve
            
        Returns:
            Adapter instance or None if not found
        """
        pass
    
    @abstractmethod
    def get_adapters_by_type(self, component_type: str) -> List[IUIComponentAdapter]:
        """
        Get all adapters for a specific component type.
        
        Args:
            component_type: Component type to filter by
            
        Returns:
            List of adapters for the component type
        """
        pass
    
    @abstractmethod
    def get_all_registrations(self) -> List[AdapterRegistration]:
        """
        Get all adapter registrations.
        
        Returns:
            List of all adapter registrations
        """
        pass
    
    @abstractmethod
    def shutdown_all_adapters(self) -> bool:
        """
        Shutdown all registered adapters.
        
        Returns:
            True if all adapters shutdown successfully, False otherwise
        """
        pass 