"""
UI Widget Components

Self-contained widget components that can be reused across different tabs.
These are medium-risk extractions with limited external dependencies.
"""

from .action_button_group import ActionButtonGroup
from .statistics_widget import StatisticsWidget
from .thumbnail_widget import ThumbnailWidget
from .progress_tracker import ProgressTracker

__all__ = [
    'ActionButtonGroup',
    'StatisticsWidget',
    'ThumbnailWidget',
    'ProgressTracker'
] 