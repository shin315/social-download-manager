"""
Base platform module for abstract platform handlers

This module provides the foundation for platform-specific implementations
following clean architecture principles.
"""

from .platform_handler import (
    AbstractPlatformHandler,
    PlatformError,
    PlatformConnectionError,
    PlatformAuthError,
    PlatformContentError,
    PlatformRateLimitError
)

from .models import (
    PlatformVideoInfo,
    VideoFormat,
    QualityLevel,
    DownloadResult,
    AuthenticationInfo,
    DownloadProgress,
    PlatformCapabilities
)

from .enums import (
    PlatformType,
    ContentType,
    DownloadStatus,
    AuthType,
    ErrorType,
    PlatformConstants
)

from .common import (
    RateLimiter,
    RetryConfig,
    ConnectionPool,
    DataFormatter,
    FormatUtils,
    SimpleCache,
    RateLimitedMixin,
    CachedMixin,
    rate_limited,
    with_retry,
    cached,
    retry_async
)

from .factory import (
    PlatformRegistry,
    PlatformFactory,
    PlatformHandler,
    register_platform,
    unregister_platform,
    create_handler,
    create_handler_for_url,
    detect_platform,
    is_url_supported,
    get_supported_platforms,
    get_platform_capabilities,
    discover_handlers,
    get_factory_info
)

__all__ = [
    # Core handler
    'AbstractPlatformHandler',
    
    # Exceptions
    'PlatformError',
    'PlatformConnectionError', 
    'PlatformAuthError',
    'PlatformContentError',
    'PlatformRateLimitError',
    
    # Models
    'PlatformVideoInfo',
    'VideoFormat',
    'QualityLevel',
    'DownloadResult',
    'AuthenticationInfo',
    'DownloadProgress',
    'PlatformCapabilities',
    
    # Enums
    'PlatformType',
    'ContentType', 
    'DownloadStatus',
    'AuthType',
    'ErrorType',
    'PlatformConstants',
    
    # Common functionality
    'RateLimiter',
    'RetryConfig',
    'ConnectionPool',
    'DataFormatter',
    'FormatUtils',
    'SimpleCache',
    'RateLimitedMixin',
    'CachedMixin',
    
    # Decorators & utilities
    'rate_limited',
    'with_retry',
    'cached',
    'retry_async',
    
    # Factory pattern
    'PlatformRegistry',
    'PlatformFactory',
    'PlatformHandler',
    'register_platform',
    'unregister_platform',
    'create_handler',
    'create_handler_for_url',
    'detect_platform',
    'is_url_supported',
    'get_supported_platforms',
    'get_platform_capabilities',
    'discover_handlers',
    'get_factory_info'
] 