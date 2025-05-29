"""
UI Table Components

Core table components that handle video data display, filtering, and sorting.
These are high-risk extractions due to complex functionality and dependencies.
"""

from .video_table import (
    VideoTable,
    create_video_info_table_config,
    create_downloaded_videos_table_config
)

from .filterable_video_table import (
    FilterableVideoTable,
    create_filterable_video_info_table_config,
    create_filterable_downloaded_videos_table_config
)

__all__ = [
    'VideoTable',
    'FilterableVideoTable',
    'create_video_info_table_config', 
    'create_downloaded_videos_table_config',
    'create_filterable_video_info_table_config',
    'create_filterable_downloaded_videos_table_config'
] 