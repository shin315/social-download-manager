"""
Tab Components Module

This module contains all tab implementations that have been migrated
to use the BaseTab architecture from Task 16.

All tabs in this module:
- Inherit from BaseTab
- Support lifecycle management
- Integrate with component bus
- Provide state persistence
- Support theme and language changes
- Include performance monitoring
- Have comprehensive validation
"""

from .downloaded_videos_tab import DownloadedVideosTab
from .video_info_tab import VideoInfoTab

__all__ = [
    'DownloadedVideosTab',
    'VideoInfoTab'
] 