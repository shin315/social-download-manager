"""
UI Table Components

Core table components that handle video data display, filtering, and sorting.
These are high-risk extractions due to complex functionality and dependencies.
"""

from .video_table import VideoTable
from .filterable_video_table import FilterableVideoTable

__all__ = [
    'VideoTable',
    'FilterableVideoTable'
] 