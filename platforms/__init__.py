"""
Platform handlers for Social Download Manager v2.0

This module contains platform-specific implementations and the base
interfaces that all platforms must implement.
"""

# Import platform handlers to trigger automatic registration
from .tiktok.tiktok_handler import TikTokHandler
from .youtube.youtube_handler import YouTubeHandler

# Import base classes for external use
from .base import (
    AbstractPlatformHandler,
    PlatformFactory,
    PlatformType,
    PlatformVideoInfo,
    VideoFormat,
    QualityLevel,
    DownloadResult,
    DownloadProgress,
    DownloadStatus,
    ContentType,
    PlatformCapabilities,
    AuthenticationInfo,
    AuthType,
    create_handler,
    create_handler_for_url,
    detect_platform,
    is_url_supported,
    get_supported_platforms,
    register_platform
)

__all__ = [
    # Handlers
    'TikTokHandler',
    'YouTubeHandler',
    
    # Base classes
    'AbstractPlatformHandler',
    'PlatformFactory',
    
    # Data models
    'PlatformVideoInfo',
    'VideoFormat',
    'DownloadResult',
    'DownloadProgress',
    'AuthenticationInfo',
    'PlatformCapabilities',
    
    # Enums
    'PlatformType',
    'QualityLevel',
    'DownloadStatus',
    'ContentType',
    'AuthType',
    
    # Factory functions
    'create_handler',
    'create_handler_for_url',
    'detect_platform',
    'is_url_supported',
    'get_supported_platforms',
    'register_platform'
] 