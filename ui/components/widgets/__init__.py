"""
UI Widget Components

Self-contained widget components that can be reused across different tabs.
These are medium-risk extractions with limited external dependencies.
"""

from .action_button_group import ActionButtonGroup, ButtonConfig, ButtonType
from .progress_tracker import ProgressTracker
from .statistics_widget import StatisticsWidget
from .thumbnail_widget import ThumbnailWidget

# Import new widgets
from .platform_selector import (
    PlatformSelector,
    create_combo_platform_selector_config,
    create_button_platform_selector_config,
    create_auto_detect_platform_selector_config
)
from .filter_popup import FilterPopup

__all__ = [
    'ActionButtonGroup',
    'ProgressTracker',
    'StatisticsWidget',
    'ThumbnailWidget',
    'ButtonConfig',
    'ButtonType',
    'PlatformSelector',
    'FilterPopup',
    'create_combo_platform_selector_config',
    'create_button_platform_selector_config',
    'create_auto_detect_platform_selector_config',
] 