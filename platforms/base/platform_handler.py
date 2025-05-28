"""
Abstract platform handler and exceptions

This module defines the abstract base class that all platform handlers must implement,
following clean architecture principles and providing a consistent interface.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Callable, Union
from pathlib import Path
from contextlib import asynccontextmanager

from .models import (
    PlatformVideoInfo,
    VideoFormat,
    DownloadResult,
    DownloadProgress,
    AuthenticationInfo,
    PlatformCapabilities
)
from .enums import (
    PlatformType,
    QualityLevel,
    DownloadStatus
)

# Platform constants
DEFAULT_CONNECT_TIMEOUT = 30
DEFAULT_READ_TIMEOUT = 60
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0

# =====================================================
# Exception Classes
# =====================================================

class PlatformError(Exception):
    """Base exception for all platform-related errors"""
    
    def __init__(
        self, 
        message: str, 
        platform: Optional[PlatformType] = None,
        url: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.platform = platform
        self.url = url
        self.original_error = original_error
    
    def __str__(self) -> str:
        parts = [self.message]
        if self.platform:
            parts.append(f"Platform: {self.platform.display_name}")
        if self.url:
            parts.append(f"URL: {self.url}")
        return " | ".join(parts)


class PlatformConnectionError(PlatformError):
    """Error connecting to platform"""
    pass


class PlatformAuthError(PlatformError):
    """Authentication error"""
    pass


class PlatformContentError(PlatformError):
    """Content-related error (not found, private, etc.)"""
    pass


class PlatformRateLimitError(PlatformError):
    """Rate limit exceeded error"""
    
    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


# =====================================================
# Abstract Platform Handler
# =====================================================

class AbstractPlatformHandler(ABC):
    """
    Abstract base class for all platform handlers
    
    This class defines the contract that all platform implementations must follow.
    It provides common functionality and enforces implementation of required methods.
    """
    
    def __init__(
        self,
        platform_type: PlatformType,
        auth_info: Optional[AuthenticationInfo] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize platform handler
        
        Args:
            platform_type: The platform this handler supports
            auth_info: Authentication information (if required)
            config: Configuration dictionary
        """
        self._platform_type = platform_type
        self._auth_info = auth_info
        self._config = config or {}
        self._logger = logging.getLogger(f"platform.{platform_type.value}")
        self._is_initialized = False
        self._download_progress_callbacks: List[Callable[[str, DownloadProgress], None]] = []
        
        # Configuration with defaults
        self._connect_timeout = self._config.get(
            'connect_timeout', 
            DEFAULT_CONNECT_TIMEOUT
        )
        self._read_timeout = self._config.get(
            'read_timeout',
            DEFAULT_READ_TIMEOUT
        )
        self._max_retries = self._config.get(
            'max_retries',
            DEFAULT_MAX_RETRIES
        )
        self._retry_delay = self._config.get(
            'retry_delay',
            DEFAULT_RETRY_DELAY
        )
    
    # =====================================================
    # Properties
    # =====================================================
    
    @property
    def platform_type(self) -> PlatformType:
        """Get the platform type this handler supports"""
        return self._platform_type
    
    @property
    def is_initialized(self) -> bool:
        """Check if handler is initialized"""
        return self._is_initialized
    
    @property
    def is_authenticated(self) -> bool:
        """Check if handler is authenticated (if authentication is required)"""
        if not self.get_capabilities().requires_auth:
            return True
        return self._auth_info is not None and self._auth_info.is_valid()
    
    # =====================================================
    # Abstract Methods (Must be implemented by subclasses)
    # =====================================================
    
    @abstractmethod
    def get_capabilities(self) -> PlatformCapabilities:
        """
        Get capabilities supported by this platform
        
        Returns:
            PlatformCapabilities object describing what this platform supports
        """
        pass
    
    @abstractmethod
    def is_valid_url(self, url: str) -> bool:
        """
        Check if URL is valid for this platform
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is valid for this platform
        """
        pass
    
    @abstractmethod
    async def get_video_info(self, url: str) -> PlatformVideoInfo:
        """
        Get video information from URL
        
        Args:
            url: Video URL
            
        Returns:
            PlatformVideoInfo object with video details
            
        Raises:
            PlatformError: If unable to get video info
        """
        pass
    
    @abstractmethod
    async def download_video(
        self,
        url: str,
        output_path: Path,
        quality: Optional[QualityLevel] = None,
        audio_only: bool = False,
        **kwargs
    ) -> DownloadResult:
        """
        Download video from URL
        
        Args:
            url: Video URL
            output_path: Directory to save file
            quality: Desired quality (None for best)
            audio_only: Download audio only
            **kwargs: Additional options
            
        Returns:
            DownloadResult object with download details
            
        Raises:
            PlatformError: If download fails
        """
        pass
    
    # =====================================================
    # Lifecycle Methods
    # =====================================================
    
    async def initialize(self) -> None:
        """
        Initialize the platform handler
        
        This method should be called before using the handler.
        Can be overridden by subclasses for custom initialization.
        """
        if self._is_initialized:
            return
        
        self._logger.info(f"Initializing {self._platform_type.display_name} handler")
        
        # Validate authentication if required
        capabilities = self.get_capabilities()
        if capabilities.requires_auth and not self.is_authenticated:
            raise PlatformAuthError(
                f"Authentication required for {self._platform_type.display_name}",
                platform=self._platform_type
            )
        
        # Custom initialization
        await self._initialize_platform()
        
        self._is_initialized = True
        self._logger.info(f"{self._platform_type.display_name} handler initialized")
    
    async def shutdown(self) -> None:
        """
        Shutdown the platform handler and cleanup resources
        
        Can be overridden by subclasses for custom cleanup.
        """
        if not self._is_initialized:
            return
        
        self._logger.info(f"Shutting down {self._platform_type.display_name} handler")
        
        # Custom cleanup
        await self._cleanup_platform()
        
        self._is_initialized = False
        self._download_progress_callbacks.clear()
        self._logger.info(f"{self._platform_type.display_name} handler shutdown complete")
    
    @asynccontextmanager
    async def managed_session(self):
        """
        Context manager for automatic initialization and cleanup
        
        Usage:
            async with handler.managed_session():
                video_info = await handler.get_video_info(url)
        """
        await self.initialize()
        try:
            yield self
        finally:
            await self.shutdown()
    
    # =====================================================
    # Optional Override Methods
    # =====================================================
    
    async def _initialize_platform(self) -> None:
        """
        Platform-specific initialization
        
        Override this method in subclasses for custom initialization logic.
        """
        pass
    
    async def _cleanup_platform(self) -> None:
        """
        Platform-specific cleanup
        
        Override this method in subclasses for custom cleanup logic.
        """
        pass
    
    # =====================================================
    # Progress and Event Handling
    # =====================================================
    
    def add_progress_callback(self, callback: Callable[[str, DownloadProgress], None]) -> None:
        """
        Add a progress callback for download operations
        
        Args:
            callback: Function that takes (url, progress) parameters
        """
        if callback not in self._download_progress_callbacks:
            self._download_progress_callbacks.append(callback)
    
    def remove_progress_callback(self, callback: Callable[[str, DownloadProgress], None]) -> None:
        """Remove a progress callback"""
        if callback in self._download_progress_callbacks:
            self._download_progress_callbacks.remove(callback)
    
    def _notify_progress(self, url: str, progress: DownloadProgress) -> None:
        """Notify all progress callbacks"""
        for callback in self._download_progress_callbacks:
            try:
                callback(url, progress)
            except Exception as e:
                self._logger.warning(f"Progress callback error: {e}")
    
    # =====================================================
    # Common Utility Methods
    # =====================================================
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """
        Extract platform-specific video ID from URL
        
        Should be overridden by subclasses for platform-specific logic.
        Default implementation returns None.
        
        Args:
            url: Video URL
            
        Returns:
            Video ID or None if not extractable
        """
        return None
    
    def normalize_url(self, url: str) -> str:
        """
        Normalize URL to canonical form
        
        Should be overridden by subclasses for platform-specific logic.
        Default implementation returns URL as-is.
        
        Args:
            url: Original URL
            
        Returns:
            Normalized URL
        """
        return url
    
    async def get_thumbnail(self, video_info: PlatformVideoInfo) -> Optional[bytes]:
        """
        Download thumbnail for video
        
        Args:
            video_info: Video information containing thumbnail URL
            
        Returns:
            Thumbnail data as bytes or None if not available
        """
        if not video_info.thumbnail_url:
            return None
        
        try:
            # This is a basic implementation - subclasses can override
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    video_info.thumbnail_url,
                    timeout=aiohttp.ClientTimeout(total=self._connect_timeout)
                ) as response:
                    if response.status == 200:
                        return await response.read()
            return None
        except Exception as e:
            self._logger.warning(f"Failed to download thumbnail: {e}")
            return None
    
    def _create_video_format(
        self,
        format_id: str,
        quality: Union[QualityLevel, str],
        ext: str,
        **kwargs
    ) -> VideoFormat:
        """
        Helper method to create VideoFormat objects
        
        Args:
            format_id: Format identifier
            quality: Quality level (enum or string)
            ext: File extension
            **kwargs: Additional format properties
            
        Returns:
            VideoFormat object
        """
        # Convert string quality to enum
        if isinstance(quality, str):
            try:
                quality = QualityLevel(quality)
            except ValueError:
                # Try to parse height from string like "720p"
                if quality.endswith('p') and quality[:-1].isdigit():
                    height = int(quality[:-1])
                    quality = QualityLevel.from_height(height)
                else:
                    quality = QualityLevel.BEST
        
        return VideoFormat(
            format_id=format_id,
            quality=quality,
            ext=ext,
            **kwargs
        )
    
    def _handle_error(self, error: Exception, url: Optional[str] = None) -> PlatformError:
        """
        Convert generic exceptions to appropriate PlatformError subclasses
        
        Args:
            error: Original exception
            url: URL that caused the error (if any)
            
        Returns:
            Appropriate PlatformError subclass
        """
        if isinstance(error, PlatformError):
            return error
        
        error_msg = str(error).lower()
        
        # Connection-related errors
        if any(keyword in error_msg for keyword in ['connection', 'timeout', 'network']):
            return PlatformConnectionError(
                str(error),
                platform=self._platform_type,
                url=url,
                original_error=error
            )
        
        # Authentication errors
        if any(keyword in error_msg for keyword in ['auth', 'login', 'token', 'unauthorized']):
            return PlatformAuthError(
                str(error),
                platform=self._platform_type,
                url=url,
                original_error=error
            )
        
        # Rate limiting
        if any(keyword in error_msg for keyword in ['rate limit', 'too many requests', '429']):
            return PlatformRateLimitError(
                str(error),
                platform=self._platform_type,
                url=url,
                original_error=error
            )
        
        # Content errors
        if any(keyword in error_msg for keyword in ['not found', '404', 'private', 'unavailable']):
            error_type = ErrorType.CONTENT_NOT_FOUND
            if 'private' in error_msg:
                error_type = ErrorType.CONTENT_PRIVATE
            elif 'unavailable' in error_msg:
                error_type = ErrorType.CONTENT_UNAVAILABLE
            
            return PlatformContentError(
                str(error),
                error_type=error_type,
                platform=self._platform_type,
                url=url,
                original_error=error
            )
        
        # Default to generic platform error
        return PlatformError(
            str(error),
            platform=self._platform_type,
            url=url,
            original_error=error
        )
    
    def __str__(self) -> str:
        """String representation"""
        return f"{self.__class__.__name__}({self._platform_type.display_name})"
    
    def __repr__(self) -> str:
        """Detailed representation"""
        return (
            f"{self.__class__.__name__}("
            f"platform={self._platform_type.value}, "
            f"initialized={self._is_initialized}, "
            f"authenticated={self.is_authenticated})"
        ) 