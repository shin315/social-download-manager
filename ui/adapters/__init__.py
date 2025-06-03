"""
UI Adapters Package for v1.2.1 to v2.0 Architecture Bridge

This package contains adapter implementations that bridge legacy UI components
with the new v2.0 architecture systems (Repository Layer, Event System, Platform Handlers).
"""

# Core interfaces and structures
from .interfaces import (
    IUIComponentAdapter, IMainWindowAdapter, IVideoInfoTabAdapter, 
    IDownloadedVideosTabAdapter, IEventProxyAdapter, IDataMapperAdapter,
    IAdapterRegistry, AdapterState, AdapterConfig, AdapterMetrics, 
    AdapterPriority
)

# Data mapping components
from .data_mappers import (
    VideoDataMapper, DownloadDataMapper, ConfigurationDataMapper,
    get_video_mapper, get_download_mapper, get_config_mapper
)

# Event bridging components
from .event_proxy import (
    EventBridgeCoordinator, EventTranslator, LegacyEventHandler,
    get_global_coordinator
)

# Adapter implementations
from .main_window_adapter import (
    MainWindowAdapter, MainWindowAdapterError,
    create_main_window_adapter, get_global_main_window_adapter
)

from .video_info_tab_adapter import (
    VideoInfoTabAdapter, VideoInfoTabAdapterError,
    create_video_info_tab_adapter, get_global_video_info_tab_adapter
)

from .downloaded_videos_tab_adapter import (
    DownloadedVideosTabAdapter, DownloadedVideosTabAdapterError,
    create_downloaded_videos_tab_adapter, get_global_downloaded_videos_tab_adapter
)

# Factory functions for easy adapter creation
__adapters__ = {
    'main_window': create_main_window_adapter,
    'video_info_tab': create_video_info_tab_adapter,
    'downloaded_videos_tab': create_downloaded_videos_tab_adapter,
}

def create_adapter(adapter_type: str):
    """
    Factory function to create adapters by type.
    
    Args:
        adapter_type: Type of adapter to create ('main_window', 'video_info_tab', 'downloaded_videos_tab')
        
    Returns:
        Adapter instance
        
    Raises:
        ValueError: If adapter_type is not supported
    """
    if adapter_type not in __adapters__:
        raise ValueError(f"Unsupported adapter type: {adapter_type}. "
                        f"Supported types: {list(__adapters__.keys())}")
    
    return __adapters__[adapter_type]()

# Global adapter instances
__global_adapters__ = {
    'main_window': get_global_main_window_adapter,
    'video_info_tab': get_global_video_info_tab_adapter,
    'downloaded_videos_tab': get_global_downloaded_videos_tab_adapter,
}

def get_global_adapter(adapter_type: str):
    """
    Get global adapter instance by type.
    
    Args:
        adapter_type: Type of adapter to get
        
    Returns:
        Global adapter instance
        
    Raises:
        ValueError: If adapter_type is not supported
    """
    if adapter_type not in __global_adapters__:
        raise ValueError(f"Unsupported adapter type: {adapter_type}. "
                        f"Supported types: {list(__global_adapters__.keys())}")
    
    return __global_adapters__[adapter_type]()

# Version information
__version__ = "2.0.0"
__author__ = "Social Download Manager Team"
__description__ = "UI Adapters for bridging v1.2.1 UI with v2.0 Architecture"

# Public API
__all__ = [
    # Core interfaces
    'IUIComponentAdapter', 'IMainWindowAdapter', 'IVideoInfoTabAdapter', 
    'IDownloadedVideosTabAdapter', 'IEventProxyAdapter', 'IDataMapperAdapter',
    'IAdapterRegistry', 'AdapterState', 'AdapterConfig', 'AdapterMetrics', 
    'AdapterPriority',
    
    # Data mappers
    'VideoDataMapper', 'DownloadDataMapper', 'ConfigurationDataMapper',
    'get_video_mapper', 'get_download_mapper', 'get_config_mapper',
    
    # Event system
    'EventBridgeCoordinator', 'EventTranslator', 'LegacyEventHandler',
    'get_global_coordinator',
    
    # Adapter implementations
    'MainWindowAdapter', 'MainWindowAdapterError',
    'VideoInfoTabAdapter', 'VideoInfoTabAdapterError', 
    'DownloadedVideosTabAdapter', 'DownloadedVideosTabAdapterError',
    
    # Factory functions
    'create_adapter', 'get_global_adapter',
    'create_main_window_adapter', 'get_global_main_window_adapter',
    'create_video_info_tab_adapter', 'get_global_video_info_tab_adapter',
    'create_downloaded_videos_tab_adapter', 'get_global_downloaded_videos_tab_adapter',
] 