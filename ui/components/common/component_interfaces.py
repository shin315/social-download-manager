"""
Component Interfaces for UI Components

Defines consistent interfaces for all UI components to ensure proper integration
with the BaseTab architecture and component system.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtWidgets import QWidget

from .models import (
    TableConfig, ColumnConfig, SortConfig, FilterConfig, 
    ButtonConfig, StatisticsData, TabState
)

# =============================================================================
# Platform Types and Models
# =============================================================================

class PlatformType(Enum):
    """Supported platform types"""
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    UNKNOWN = "unknown"

@dataclass
class PlatformCapability:
    """Platform capability definition"""
    download: bool = False
    metadata: bool = False
    search: bool = False
    user_videos: bool = False
    playlists: bool = False

@dataclass
class PlatformInfo:
    """Platform information"""
    platform_type: PlatformType
    name: str
    icon_path: str
    capabilities: PlatformCapability
    url_patterns: List[str]
    available: bool = True

# =============================================================================
# Table Component Interfaces
# =============================================================================

class TableInterface(ABC):
    """Interface for table components"""
    
    # Signals
    selection_changed = pyqtSignal(list)  # Selected items
    item_action_requested = pyqtSignal(str, object)  # Action, item
    sort_changed = pyqtSignal(SortConfig)  # Sort configuration
    
    @abstractmethod
    def setup_table(self, config: TableConfig) -> None:
        """Initialize table with configuration"""
        pass
    
    @abstractmethod
    def set_data(self, items: List[Any]) -> None:
        """Populate table with data"""
        pass
    
    @abstractmethod
    def get_selected_items(self) -> List[Any]:
        """Get currently selected items"""
        pass
    
    @abstractmethod
    def clear_selection(self) -> None:
        """Clear all selections"""
        pass
    
    @abstractmethod
    def select_all(self) -> None:
        """Select all items"""
        pass
    
    @abstractmethod
    def get_sort_config(self) -> SortConfig:
        """Get current sort configuration"""
        pass
    
    @abstractmethod
    def apply_sort(self, sort_config: SortConfig) -> None:
        """Apply sort configuration"""
        pass

class FilterableTableInterface(TableInterface):
    """Interface for filterable table components"""
    
    # Additional signals
    filter_changed = pyqtSignal(dict)  # Active filters
    filter_applied = pyqtSignal(FilterConfig)  # Applied filter
    filter_cleared = pyqtSignal(int)  # Cleared column filter
    
    @abstractmethod
    def get_active_filters(self) -> Dict[int, FilterConfig]:
        """Get currently active filters"""
        pass
    
    @abstractmethod
    def apply_filter(self, column: int, filter_config: FilterConfig) -> None:
        """Apply filter to specific column"""
        pass
    
    @abstractmethod
    def clear_filter(self, column: int) -> None:
        """Clear filter from specific column"""
        pass
    
    @abstractmethod
    def clear_all_filters(self) -> None:
        """Clear all filters"""
        pass
    
    @abstractmethod
    def search(self, query: str, columns: Optional[List[int]] = None) -> None:
        """Search across specified columns"""
        pass
    
    @abstractmethod
    def get_filtered_count(self) -> int:
        """Get number of items after filtering"""
        pass

# =============================================================================
# Platform Selector Interface
# =============================================================================

class PlatformSelectorInterface(ABC):
    """Interface for platform selector components"""
    
    # Signals
    platform_selected = pyqtSignal(PlatformType)  # Manual selection
    platform_auto_detected = pyqtSignal(PlatformType, str)  # Auto-detection
    url_validated = pyqtSignal(bool, PlatformType)  # Validation result
    
    @abstractmethod
    def detect_platform(self, url: str) -> Optional[PlatformType]:
        """Auto-detect platform from URL"""
        pass
    
    @abstractmethod
    def set_platform(self, platform: PlatformType) -> None:
        """Manually set platform"""
        pass
    
    @abstractmethod
    def get_selected_platform(self) -> Optional[PlatformType]:
        """Get currently selected platform"""
        pass
    
    @abstractmethod
    def validate_url(self, url: str, platform: PlatformType) -> bool:
        """Validate URL for specific platform"""
        pass
    
    @abstractmethod
    def get_platform_info(self, platform: PlatformType) -> Optional[PlatformInfo]:
        """Get platform information"""
        pass
    
    @abstractmethod
    def get_available_platforms(self) -> List[PlatformInfo]:
        """Get list of available platforms"""
        pass

# =============================================================================
# Progress Tracking Interface
# =============================================================================

class ProgressTrackerInterface(ABC):
    """Interface for progress tracking components"""
    
    # Signals  
    progress_updated = pyqtSignal(int, str)  # Progress %, speed
    progress_completed = pyqtSignal()
    progress_failed = pyqtSignal(str)  # Error message
    progress_cancelled = pyqtSignal()
    
    @abstractmethod
    def update_progress(self, progress: int, message: str = "") -> None:
        """Update progress value and message"""
        pass
    
    @abstractmethod
    def set_indeterminate(self, indeterminate: bool) -> None:
        """Set indeterminate progress mode"""
        pass
    
    @abstractmethod
    def set_speed(self, speed: str) -> None:
        """Set current speed/rate"""
        pass
    
    @abstractmethod
    def set_status(self, status: str) -> None:
        """Set status message"""
        pass
    
    @abstractmethod
    def reset_progress(self) -> None:
        """Reset to initial state"""
        pass
    
    @abstractmethod
    def set_error(self, error_message: str) -> None:
        """Set error state"""
        pass
    
    @abstractmethod
    def set_completed(self) -> None:
        """Mark as completed"""
        pass
    
    @abstractmethod
    def get_progress(self) -> int:
        """Get current progress value"""
        pass
    
    @abstractmethod
    def is_completed(self) -> bool:
        """Check if progress is completed"""
        pass

# =============================================================================
# Search and Filter Interfaces
# =============================================================================

class SearchInterface(ABC):
    """Interface for search components"""
    
    # Signals
    search_query_changed = pyqtSignal(str)  # Search query
    search_executed = pyqtSignal(str, list)  # Query, columns
    search_cleared = pyqtSignal()
    
    @abstractmethod
    def set_search_query(self, query: str) -> None:
        """Set search query"""
        pass
    
    @abstractmethod
    def get_search_query(self) -> str:
        """Get current search query"""
        pass
    
    @abstractmethod
    def clear_search(self) -> None:
        """Clear search query"""
        pass
    
    @abstractmethod
    def set_search_columns(self, columns: List[int]) -> None:
        """Set columns to search in"""
        pass
    
    @abstractmethod
    def get_search_columns(self) -> List[int]:
        """Get columns being searched"""
        pass

class FilterInterface(ABC):
    """Interface for filter components"""
    
    # Signals
    filter_value_changed = pyqtSignal(FilterConfig)
    filter_reset = pyqtSignal()
    
    @abstractmethod
    def set_filter_options(self, options: List[Any]) -> None:
        """Set available filter options"""
        pass
    
    @abstractmethod
    def get_filter_value(self) -> FilterConfig:
        """Get current filter configuration"""
        pass
    
    @abstractmethod
    def set_filter_value(self, config: FilterConfig) -> None:
        """Set filter configuration"""
        pass
    
    @abstractmethod
    def reset_filter(self) -> None:
        """Reset filter to default"""
        pass

# =============================================================================
# Video Details Interface
# =============================================================================

class VideoDetailsInterface(ABC):
    """Interface for video details components"""
    
    # Signals
    detail_expanded = pyqtSignal(str)  # Section name
    detail_collapsed = pyqtSignal(str)  # Section name
    action_requested = pyqtSignal(str, dict)  # Action, video_info
    
    @abstractmethod
    def set_video_info(self, video_info: Dict[str, Any]) -> None:
        """Set video information to display"""
        pass
    
    @abstractmethod
    def get_video_info(self) -> Dict[str, Any]:
        """Get current video information"""
        pass
    
    @abstractmethod
    def expand_section(self, section: str) -> None:
        """Expand specific detail section"""
        pass
    
    @abstractmethod
    def collapse_section(self, section: str) -> None:
        """Collapse specific detail section"""
        pass
    
    @abstractmethod
    def is_section_expanded(self, section: str) -> bool:
        """Check if section is expanded"""
        pass
    
    @abstractmethod
    def set_download_status(self, status: str) -> None:
        """Set download status display"""
        pass

# =============================================================================
# Statistics Interface
# =============================================================================

class StatisticsInterface(ABC):
    """Interface for statistics components"""
    
    # Signals
    statistics_updated = pyqtSignal(StatisticsData)
    
    @abstractmethod
    def update_statistics(self, data: StatisticsData) -> None:
        """Update statistics display"""
        pass
    
    @abstractmethod
    def get_statistics(self) -> StatisticsData:
        """Get current statistics"""
        pass
    
    @abstractmethod
    def reset_statistics(self) -> None:
        """Reset statistics to default values"""
        pass

# =============================================================================
# Action Button Group Interface
# =============================================================================

class ActionButtonGroupInterface(ABC):
    """Interface for action button group components"""
    
    # Signals
    button_clicked = pyqtSignal(str)  # Button action
    
    @abstractmethod
    def set_button_configs(self, configs: List[ButtonConfig]) -> None:
        """Set button configurations"""
        pass
    
    @abstractmethod
    def update_button_states(self, states: Dict[str, bool]) -> None:
        """Update button enabled/disabled states"""
        pass
    
    @abstractmethod
    def set_button_enabled(self, button_id: str, enabled: bool) -> None:
        """Enable/disable specific button"""
        pass
    
    @abstractmethod
    def is_button_enabled(self, button_id: str) -> bool:
        """Check if button is enabled"""
        pass
    
    @abstractmethod
    def add_custom_button(self, button_id: str, text: str, 
                         callback: Callable) -> None:
        """Add custom button"""
        pass

# =============================================================================
# Thumbnail Interface
# =============================================================================

class ThumbnailInterface(ABC):
    """Interface for thumbnail components"""
    
    # Signals
    thumbnail_clicked = pyqtSignal(str)  # URL or path
    thumbnail_loaded = pyqtSignal(str)  # URL
    thumbnail_error = pyqtSignal(str, str)  # URL, error
    
    @abstractmethod
    def load_thumbnail(self, url: str) -> None:
        """Load thumbnail from URL"""
        pass
    
    @abstractmethod
    def set_thumbnail_path(self, path: str) -> None:
        """Set thumbnail from local path"""
        pass
    
    @abstractmethod
    def set_placeholder(self) -> None:
        """Set placeholder image"""
        pass
    
    @abstractmethod
    def clear_thumbnail(self) -> None:
        """Clear thumbnail display"""
        pass
    
    @abstractmethod
    def set_size(self, width: int, height: int) -> None:
        """Set thumbnail size"""
        pass

# =============================================================================
# Configuration Models for Components
# =============================================================================

@dataclass
class PlatformSelectorConfig:
    """Configuration for platform selector"""
    auto_detect: bool = True
    show_capabilities: bool = True
    show_status: bool = True
    default_platform: Optional[PlatformType] = None
    enabled_platforms: List[PlatformType] = None

@dataclass
class SearchConfig:
    """Configuration for search widget"""
    enable_history: bool = True
    debounce_delay: int = 300
    search_columns: Optional[List[int]] = None
    placeholder_text: str = "Search..."
    case_sensitive: bool = False

@dataclass
class FilterWidgetConfig:
    """Configuration for filter widget"""
    filter_type: str = "dropdown"  # dropdown, text, date, range
    allow_multiple: bool = False
    placeholder_text: str = "Filter..."
    case_sensitive: bool = False

@dataclass
class VideoDetailsConfig:
    """Configuration for video details widget"""
    sections: List[str] = None  # Sections to show
    expandable: bool = True
    show_thumbnail: bool = True
    show_actions: bool = True
    compact_mode: bool = False

@dataclass
class ThumbnailConfig:
    """Configuration for thumbnail widget"""
    default_size: tuple = (120, 90)
    enable_click: bool = True
    show_loading: bool = True
    cache_thumbnails: bool = True
    placeholder_path: Optional[str] = None

# =============================================================================
# Interface Registry
# =============================================================================

class ComponentInterfaceRegistry:
    """Registry for component interfaces"""
    
    _interfaces = {
        'table': TableInterface,
        'filterable_table': FilterableTableInterface,
        'platform_selector': PlatformSelectorInterface,
        'progress_tracker': ProgressTrackerInterface,
        'search': SearchInterface,
        'filter': FilterInterface,
        'video_details': VideoDetailsInterface,
        'statistics': StatisticsInterface,
        'action_buttons': ActionButtonGroupInterface,
        'thumbnail': ThumbnailInterface,
    }
    
    @classmethod
    def get_interface(cls, component_type: str):
        """Get interface class for component type"""
        return cls._interfaces.get(component_type)
    
    @classmethod
    def list_interfaces(cls) -> List[str]:
        """List available interface types"""
        return list(cls._interfaces.keys())
    
    @classmethod
    def validate_component(cls, component: QWidget, 
                          interface_type: str) -> bool:
        """Validate component implements required interface"""
        interface_class = cls.get_interface(interface_type)
        if interface_class:
            return isinstance(component, interface_class)
        return False 