"""
UI Components Package

This package contains modular, reusable UI components extracted from the large UI files.
Components are organized by type: mixins, widgets, tables, tabs, and common utilities.

The v2.0 component architecture provides:
- Modular, reusable components
- Clean separation of concerns  
- Enhanced testability
- Better maintainability
- Consistent APIs across components
"""

# Import individual component modules
from . import mixins
from . import widgets  
from . import tables
from . import tabs
from . import common

# Import specific components for direct access
from .mixins import (
    LanguageSupport, ThemeSupport, TooltipSupport,
    StatefulComponentMixin, FilterableStateMixin, SelectableStateMixin,
    EnhancedThemeSupport, AccessibilitySupport
)

from .widgets import (
    ActionButtonGroup, ProgressTracker, StatisticsWidget, ThumbnailWidget,
    PlatformSelector, FilterPopup, ButtonConfig, ButtonType
)

from .tables import (
    VideoTable, FilterableVideoTable,
    create_video_info_table_config, create_downloaded_videos_table_config,
    create_filterable_video_info_table_config, create_filterable_downloaded_videos_table_config
)

from .tabs import (
    VideoInfoTab, DownloadedVideosTab
)

from .common import (
    QWidgetABCMeta, BaseTab, TabConfig, TabState,
    TabEventHelper, TabPerformanceMonitor, EventType, ComponentEvent
)

# Define what gets exported when using "from ui.components import *"
__all__ = [
    # Sub-modules
    'mixins', 'widgets', 'tables', 'tabs', 'common',
    
    # Mixins
    'LanguageSupport', 'ThemeSupport', 'TooltipSupport',
    'StatefulComponentMixin', 'FilterableStateMixin', 'SelectableStateMixin',
    'EnhancedThemeSupport', 'AccessibilitySupport',
    
    # Widgets  
    'ActionButtonGroup', 'ProgressTracker', 'StatisticsWidget', 'ThumbnailWidget',
    'PlatformSelector', 'FilterPopup', 'ButtonConfig', 'ButtonType',
    
    # Tables
    'VideoTable', 'FilterableVideoTable',
    'create_video_info_table_config', 'create_downloaded_videos_table_config',
    'create_filterable_video_info_table_config', 'create_filterable_downloaded_videos_table_config',
    
    # Tabs
    'VideoInfoTab', 'DownloadedVideosTab',
    
    # Common
    'QWidgetABCMeta', 'BaseTab', 'TabConfig', 'TabState',
    'TabEventHelper', 'TabPerformanceMonitor', 'EventType', 'ComponentEvent'
] 