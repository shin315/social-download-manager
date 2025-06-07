"""
Data Models for UI Components

Configuration and state models used across different component types.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Set, Optional
from enum import Enum

class SortOrder(Enum):
    """Sort order enumeration"""
    ASCENDING = "ascending"
    DESCENDING = "descending"

class ButtonType(Enum):
    """Button type enumeration"""
    SELECT_ALL = "select_all"
    DELETE_SELECTED = "delete_selected"
    DELETE_ALL = "delete_all"
    REFRESH = "refresh"
    DOWNLOAD = "download"

@dataclass
class ColumnConfig:
    """Configuration for table columns"""
    index: int
    name: str
    key: str  # Translation key
    width: int
    resizable: bool = True
    sortable: bool = True
    filterable: bool = True
    visible: bool = True

@dataclass
class TableConfig:
    """Configuration for video tables"""
    columns: List[ColumnConfig]
    sortable: bool = True
    filterable: bool = False
    multi_select: bool = True
    default_sort_column: int = 0
    default_sort_order: SortOrder = SortOrder.DESCENDING
    row_height: int = 50

@dataclass
class ButtonConfig:
    """Configuration for action buttons"""
    button_type: ButtonType
    text_key: str  # Translation key
    width: int = 150
    enabled: bool = True
    visible: bool = True

@dataclass
class SortConfig:
    """Sorting configuration"""
    column: int = 0
    order: SortOrder = SortOrder.ASCENDING

@dataclass
class FilterConfig:
    """Advanced filter configuration (Enhanced for Task 13.2)"""
    filter_type: str  # "in", "not_in", "equals", "contains", "range"
    values: List[Any]
    operator: str = "AND"  # "AND", "OR" for combining filters
    column: Optional[int] = None  # For backward compatibility

class TabState:
    """State management for tab components"""
    
    def __init__(self):
        self.videos: List[Any] = []
        self.filtered_videos: List[Any] = []
        self.selected_items: Set[int] = set()
        self.active_filters: Dict[int, FilterConfig] = {}
        self.sort_config: SortConfig = SortConfig()
        self.loading: bool = False
        self.processing_count: int = 0
        
    def clear(self):
        """Clear all state"""
        self.videos.clear()
        self.filtered_videos.clear()
        self.selected_items.clear()
        self.active_filters.clear()
        self.sort_config = SortConfig()
        self.loading = False
        self.processing_count = 0

@dataclass
class StatisticsData:
    """Statistics data for display"""
    total_videos: int = 0
    total_size: str = "0 MB"
    last_download: str = "N/A"
    selected_count: int = 0
    filtered_count: int = 0

@dataclass
class TabConfig:
    """Configuration for tab components"""
    tab_id: str
    title_key: str  # Translation key for tab title
    icon_path: Optional[str] = None
    closable: bool = False
    movable: bool = True
    auto_save: bool = True
    validation_required: bool = False
    lifecycle_hooks: bool = True
    component_integration: bool = True
    state_persistence: bool = True 