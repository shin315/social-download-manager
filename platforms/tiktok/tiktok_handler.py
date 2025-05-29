"""
TikTok Platform Handler Implementation

This module contains the TikTok-specific implementation of the AbstractPlatformHandler,
adapting the existing TikTokDownloader functionality to the new platform architecture.
"""

import asyncio
import logging
import re
import unicodedata
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from urllib.parse import urlparse

import yt_dlp

from platforms.base import (
    AbstractPlatformHandler,
    PlatformHandler,
    PlatformType,
    PlatformVideoInfo,
    VideoFormat,
    QualityLevel,
    DownloadResult,
    DownloadProgress,
    DownloadStatus,
    ContentType,
    PlatformCapabilities,
    PlatformError,
    PlatformConnectionError,
    PlatformContentError,
    PlatformRateLimitError,
    AuthType
)

logger = logging.getLogger(__name__)


class TikTokErrorContext:
    """Enhanced error context for detailed error reporting"""
    
    def __init__(
        self,
        operation: str,
        url: Optional[str] = None,
        error_code: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        user_message: Optional[str] = None,
        technical_details: Optional[Dict[str, Any]] = None,
        suggested_actions: Optional[List[str]] = None,
        recovery_options: Optional[List[str]] = None
    ):
        self.operation = operation
        self.url = url
        self.error_code = error_code
        self.timestamp = timestamp or datetime.now()
        self.user_message = user_message
        self.technical_details = technical_details or {}
        self.suggested_actions = suggested_actions or []
        self.recovery_options = recovery_options or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error context to dictionary for logging"""
        return {
            'operation': self.operation,
            'url': self.url,
            'error_code': self.error_code,
            'timestamp': self.timestamp.isoformat(),
            'user_message': self.user_message,
            'technical_details': self.technical_details,
            'suggested_actions': self.suggested_actions,
            'recovery_options': self.recovery_options
        }


class TikTokErrorMonitor:
    """Error rate monitoring and health tracking"""
    
    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.error_history: List[Dict[str, Any]] = []
        self.circuit_breaker_state = False
        self.circuit_breaker_reset_time: Optional[datetime] = None
        self.health_check_interval = 300  # 5 minutes
        self.error_threshold_per_hour = 50
        self.circuit_breaker_duration = 900  # 15 minutes
    
    def record_error(self, error_type: str, context: TikTokErrorContext):
        """Record an error occurrence"""
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        error_record = {
            'type': error_type,
            'timestamp': context.timestamp,
            'operation': context.operation,
            'url': context.url,
            'error_code': context.error_code
        }
        self.error_history.append(error_record)
        
        # Maintain only last hour of history
        cutoff_time = datetime.now() - timedelta(hours=1)
        self.error_history = [
            record for record in self.error_history 
            if record['timestamp'] > cutoff_time
        ]
        
        # Check if circuit breaker should be triggered
        self._check_circuit_breaker()
    
    def _check_circuit_breaker(self):
        """Check if circuit breaker should be triggered"""
        recent_errors = len(self.error_history)
        
        if recent_errors >= self.error_threshold_per_hour and not self.circuit_breaker_state:
            self.circuit_breaker_state = True
            self.circuit_breaker_reset_time = datetime.now() + timedelta(seconds=self.circuit_breaker_duration)
            logger.error(f"Circuit breaker activated due to {recent_errors} errors in the last hour")
    
    def is_circuit_open(self) -> bool:
        """Check if circuit breaker is currently open"""
        if not self.circuit_breaker_state:
            return False
        
        if self.circuit_breaker_reset_time and datetime.now() > self.circuit_breaker_reset_time:
            self.circuit_breaker_state = False
            self.circuit_breaker_reset_time = None
            logger.info("Circuit breaker reset - service restored")
            return False
        
        return True
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status"""
        recent_errors = len(self.error_history)
        error_rate = recent_errors / 60.0  # errors per minute
        
        return {
            'healthy': not self.circuit_breaker_state and error_rate < 1.0,
            'circuit_breaker_active': self.circuit_breaker_state,
            'recent_error_count': recent_errors,
            'error_rate_per_minute': error_rate,
            'error_counts_by_type': self.error_counts.copy(),
            'circuit_breaker_reset_time': self.circuit_breaker_reset_time.isoformat() if self.circuit_breaker_reset_time else None
        }


class TikTokErrorRecovery:
    """Error recovery strategies and graceful degradation"""
    
    @staticmethod
    async def attempt_url_normalization(url: str) -> List[str]:
        """Generate alternative URL formats for retry"""
        alternatives = [url]
        
        # Try different URL formats
        if 'vm.tiktok.com' in url or 'vt.tiktok.com' in url:
            # For short URLs, add different parameters
            alternatives.extend([
                f"{url}?is_from_webapp=1",
                f"{url}?source=h5_m"
            ])
        elif 'tiktok.com/@' in url:
            # For full URLs, try variations
            if '?' in url:
                base_url = url.split('?')[0]
                alternatives.append(base_url)
            else:
                alternatives.extend([
                    f"{url}?is_from_webapp=1",
                    f"{url}?source=h5_m"
                ])
        
        return alternatives
    
    @staticmethod
    async def attempt_quality_degradation(
        formats: List[VideoFormat], 
        failed_quality: QualityLevel
    ) -> Optional[VideoFormat]:
        """Try lower quality formats when high quality fails"""
        quality_order = [
            QualityLevel.FHD,
            QualityLevel.HD,
            QualityLevel.SD,
            QualityLevel.LD,
            QualityLevel.MOBILE,
            QualityLevel.WORST
        ]
        
        try:
            current_index = quality_order.index(failed_quality)
            # Try lower qualities
            for quality in quality_order[current_index + 1:]:
                matching_formats = [f for f in formats if f.quality == quality]
                if matching_formats:
                    return matching_formats[0]
        except ValueError:
            pass
        
        return None
    
    @staticmethod
    def get_recovery_suggestions(error_type: str, context: TikTokErrorContext) -> List[str]:
        """Get recovery suggestions based on error type"""
        suggestions = []
        
        if 'connection' in error_type.lower():
            suggestions.extend([
                "Check your internet connection",
                "Try again in a few minutes",
                "Consider using a VPN if region-blocked"
            ])
        elif 'rate' in error_type.lower() or '429' in str(context.error_code):
            suggestions.extend([
                "Wait a few minutes before trying again",
                "Reduce the number of concurrent downloads",
                "Try downloading during off-peak hours"
            ])
        elif 'private' in error_type.lower() or 'forbidden' in error_type.lower():
            suggestions.extend([
                "This video is private or restricted",
                "Check if the video is still available on TikTok",
                "Try copying the URL again from TikTok"
            ])
        elif 'not found' in error_type.lower() or '404' in str(context.error_code):
            suggestions.extend([
                "The video may have been deleted",
                "Check if the URL is correct",
                "Try searching for the video on TikTok directly"
            ])
        else:
            suggestions.extend([
                "Try refreshing the page and copying the URL again",
                "Check if TikTok is accessible in your region",
                "Report this issue if it persists"
            ])
        
        return suggestions


class DownloadProgressTracker:
    """Enhanced progress tracker for download operations"""
    
    def __init__(self, url: str, callback: Optional[Callable[[DownloadProgress], None]] = None):
        self.url = url
        self.callback = callback
        self.last_progress = None
    
    def progress_hook(self, d: Dict[str, Any]) -> None:
        """Enhanced progress hook with detailed information"""
        try:
            if d['status'] == 'downloading':
                # Extract progress information
                total_bytes = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
                downloaded_bytes = d.get('downloaded_bytes', 0)
                
                # Calculate progress percentage
                if total_bytes > 0:
                    progress_percent = (downloaded_bytes / total_bytes) * 100
                else:
                    progress_percent = 0
                
                # Extract speed and ETA information
                speed = d.get('speed', 0) or 0
                eta = d.get('eta', 0) or 0
                
                # Create enhanced progress object
                progress = DownloadProgress(
                    status=DownloadStatus.DOWNLOADING,
                    progress_percent=progress_percent,
                    downloaded_bytes=downloaded_bytes,
                    total_bytes=total_bytes,
                    speed_bps=speed,
                    eta_seconds=eta,
                    message=f"Downloading... {progress_percent:.1f}%"
                )
                
                # Only notify if progress changed significantly (reduce noise)
                if self._should_notify_progress(progress):
                    self.last_progress = progress
                    if self.callback:
                        self.callback(progress)
                
            elif d['status'] == 'finished':
                # Download completed
                progress = DownloadProgress(
                    status=DownloadStatus.COMPLETED,
                    progress_percent=100.0,
                    downloaded_bytes=d.get('total_bytes', 0),
                    total_bytes=d.get('total_bytes', 0),
                    speed_bps=0,
                    message="Download completed"
                )
                
                if self.callback:
                    self.callback(progress)
                    
            elif d['status'] == 'error':
                # Download error
                progress = DownloadProgress(
                    status=DownloadStatus.FAILED,
                    progress_percent=0.0,
                    message=f"Download error: {d.get('error', 'Unknown error')}"
                )
                
                if self.callback:
                    self.callback(progress)
                    
        except Exception as e:
            logger.error(f"Error in progress hook: {e}")
    
    def _should_notify_progress(self, progress: DownloadProgress) -> bool:
        """Determine if we should notify about this progress update"""
        if not self.last_progress:
            return True
        
        # Notify if progress changed by at least 1% or every 5 seconds
        percent_change = abs(progress.progress_percent - self.last_progress.progress_percent)
        return percent_change >= 1.0


@PlatformHandler(
    platform_type=PlatformType.TIKTOK,
    url_patterns=[
        r'https?://(www\.)?tiktok\.com/@[\w\.-]+/video/\d+',
        r'https?://(www\.)?tiktok\.com/@[\w\.-]+/video/\d+\?[\w=&]+',
        r'https?://(vm\.|vt\.)?tiktok\.com/\w+',
        r'https?://(www\.)?tiktok\.com/t/\w+',
        r'https?://(www\.)?tiktok\.com/@[\w\.-]+/video/\d+\?is_from_webapp=1',
        r'https?://(www\.)?tiktok\.com/@[\w\.-]+/photo/\d+',
        r'https?://(www\.)?tiktok\.com/@[\w\.-]+/photo/\d+\?[\w=&]+'
    ]
)
class TikTokHandler(AbstractPlatformHandler):
    """
    TikTok platform handler implementation
    
    This handler adapts the existing TikTokDownloader functionality to work with
    the new AbstractPlatformHandler interface, providing async/await support,
    proper error handling, and consistent API with other platform handlers.
    """
    
    def __init__(self, auth_info: Optional[Any] = None, config: Optional[Dict[str, Any]] = None):
        """Initialize TikTok handler"""
        super().__init__(
            platform_type=PlatformType.TIKTOK,
            auth_info=auth_info,
            config=config
        )
        
        # TikTok-specific configuration
        self._output_dir = self._config.get('output_dir', '')
        self._downloads = {}  # Track downloaded videos
        self._converting_mp3_urls = set()  # Track MP3 conversions
        self._downloading_urls = set()  # Track active downloads
        
        # Authentication & Session Management
        self._session_config = self._config.get('session', {})
        self._headers_config = self._config.get('headers', {})
        self._proxy_config = self._config.get('proxy', {})
        
        # User agents for rotation (helps avoid detection)
        self._user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        ]
        
        # Current session info
        self._current_user_agent = self._get_user_agent()
        self._session_cookies = {}
        self._request_count = 0
        self._last_request_time = 0
        
        # Enhanced Error Handling Components
        self._error_monitor = TikTokErrorMonitor()
        self._error_recovery = TikTokErrorRecovery()
        self._enable_error_monitoring = self._config.get('error_monitoring', {}).get('enabled', True)
        self._enable_circuit_breaker = self._config.get('circuit_breaker', {}).get('enabled', True)
        self._enable_recovery_suggestions = self._config.get('recovery', {}).get('enabled', True)
        
        # URL patterns for validation
        self._url_patterns = [
            r'https?://(www\.)?tiktok\.com/@[\w\.-]+/video/\d+',
            r'https?://(www\.)?tiktok\.com/@[\w\.-]+/video/\d+\?[\w=&]+',
            r'https?://(vm\.|vt\.)?tiktok\.com/\w+',
            r'https?://(www\.)?tiktok\.com/t/\w+',
            r'https?://(www\.)?tiktok\.com/@[\w\.-]+/video/\d+\?is_from_webapp=1'
        ]
        
        # Patterns for unsupported content
        self._unsupported_patterns = [
            r'https?://(www\.)?tiktok\.com/@[\w\.-]+/photo/\d+',
            r'https?://(www\.)?tiktok\.com/@[\w\.-]+/photo/\d+\?[\w=&]+'
        ]
    
    def get_capabilities(self) -> PlatformCapabilities:
        """Get TikTok platform capabilities"""
        return PlatformCapabilities(
            supports_video=True,
            supports_audio=True,
            supports_playlists=False,
            supports_live=False,
            supports_stories=False,
            requires_auth=False,
            supports_watermark_removal=True,
            supports_quality_selection=True,
            supports_thumbnails=True,
            supports_metadata=True,
            max_concurrent_downloads=3,
            rate_limit_requests=30,
            rate_limit_period=60  # 30 requests per minute
        )
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid for TikTok platform"""
        if not url:
            return False
            
        logger.debug(f"Checking TikTok URL: {url}")
        
        # First check if it's an unsupported content type
        for pattern in self._unsupported_patterns:
            if re.match(pattern, url):
                logger.debug(f"Unsupported TikTok content (photo/album): {pattern}")
                return False
        
        # Check against valid URL patterns
        for pattern in self._url_patterns:
            if re.match(pattern, url):
                logger.debug(f"Valid TikTok URL format: {pattern}")
                return True
        
        logger.debug(f"Invalid TikTok URL: {url}")
        return False
    
    async def get_video_info(self, url: str) -> PlatformVideoInfo:
        """
        Get video information from TikTok URL
        
        Args:
            url: TikTok video URL
            
        Returns:
            PlatformVideoInfo with video details
            
        Raises:
            PlatformContentError: If video is not found, private, or unsupported content
            PlatformConnectionError: If network request fails
            PlatformError: For other platform-specific errors
        """
        if not self.is_valid_url(url):
            raise PlatformContentError(
                f"Invalid TikTok video URL: {url}",
                platform=self.platform_type,
                url=url
            )
        
        # Check for unsupported content early (photos/albums)
        if re.search(r'/photo/', url) or re.search(r'/album/', url):
            raise PlatformContentError(
                "TikTok photos and albums are not supported for download",
                platform=self.platform_type,
                url=url
            )
        
        try:
            # Configure yt-dlp options
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
            }
            
            logger.info(f"Extracting info from TikTok URL: {url}")
            
            # Use yt-dlp to extract video information
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    result = ydl.extract_info(url, download=False)
                except yt_dlp.utils.DownloadError as e:
                    # Handle specific yt-dlp errors
                    error_msg = str(e).lower()
                    logger.error(f"yt-dlp download error: {error_msg}")
                    
                    if "private" in error_msg:
                        raise PlatformContentError(
                            "Video is private and cannot be accessed",
                            platform=self.platform_type,
                            url=url,
                            original_error=e
                        )
                    elif "not available" in error_msg:
                        raise PlatformContentError(
                            "Video is not available or has been removed",
                            platform=self.platform_type,
                            url=url,
                            original_error=e
                        )
                    elif "copyright" in error_msg:
                        raise PlatformContentError(
                            "Video is not available due to copyright restrictions",
                            platform=self.platform_type,
                            url=url,
                            original_error=e
                        )
                    elif "region" in error_msg:
                        raise PlatformContentError(
                            "Video is not available in your region",
                            platform=self.platform_type,
                            url=url,
                            original_error=e
                        )
                    elif "api" in error_msg or "tiktok" in error_msg or "extractor" in error_msg:
                        raise PlatformConnectionError(
                            "TikTok API may have changed. Please update the application",
                            platform=self.platform_type,
                            url=url,
                            original_error=e
                        )
                    else:
                        raise PlatformError(
                            f"Failed to extract video information: {str(e)}",
                            platform=self.platform_type,
                            url=url,
                            original_error=e
                        )
                
                if not result:
                    raise PlatformContentError(
                        "No video information could be extracted",
                        platform=self.platform_type,
                        url=url
                    )
                
                # Check if content is actually a video (not photo/image)
                is_photo = result.get('webpage_url_basename', '').startswith('photo/')
                is_album = 'album' in result.get('webpage_url', '').lower()
                is_image = result.get('is_image', False)
                
                if is_photo or is_album or is_image:
                    raise PlatformContentError(
                        "TikTok photos and albums are not supported for download",
                        platform=self.platform_type,
                        url=url
                    )
                
                # Convert yt-dlp result to PlatformVideoInfo
                video_info = await self._convert_ytdlp_to_platform_info(result, url)
                
                logger.info(f"Successfully extracted TikTok video info: {video_info.title}")
                return video_info
                
        except PlatformError:
            # Re-raise platform errors as-is
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting TikTok video info for {url}: {e}")
            raise PlatformError(
                f"Unexpected error extracting video information: {str(e)}",
                platform=self.platform_type,
                url=url,
                original_error=e
            )
    
    async def download_video(
        self,
        url: str,
        output_path: Path,
        quality: Optional[QualityLevel] = None,
        audio_only: bool = False,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
        **kwargs
    ) -> DownloadResult:
        """
        Download video from TikTok with enhanced features
        
        Args:
            url: TikTok video URL
            output_path: Output file path
            quality: Desired video quality
            audio_only: Whether to download audio only
            progress_callback: Optional callback for progress updates
            **kwargs: Additional options
            
        Returns:
            DownloadResult with download information
        """
        if not self.is_valid_url(url):
            raise PlatformContentError(
                f"Invalid TikTok video URL: {url}",
                platform=self.platform_type,
                url=url
            )
        
        # Check if already downloading
        if url in self._downloading_urls:
            raise PlatformError(
                f"URL is already being downloaded: {url}",
                platform=self.platform_type,
                url=url
            )
        
        self._downloading_urls.add(url)
        
        # Enhanced configuration
        max_retries = kwargs.get('max_retries', 3)
        allow_resumption = kwargs.get('allow_resumption', True)
        retry_delay = kwargs.get('initial_retry_delay', 1.0)
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Get video info first
            video_info = await self.get_video_info(url)
            
            # Enhanced format selection
            selected_format = await self._select_best_format(
                video_info, quality, audio_only, **kwargs
            )
            
            # Extract kwargs options
            format_id = selected_format.format_id if selected_format else kwargs.get('format_id')
            remove_watermark = kwargs.get('remove_watermark', True)
            output_template = kwargs.get('output_template')
            force_overwrite = kwargs.get('force_overwrite', False)
            
            # Setup progress tracking
            progress_tracker = DownloadProgressTracker(url, progress_callback)
            
            # Retry logic implementation
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    logger.info(f"Download attempt {attempt + 1}/{max_retries + 1} for: {url}")
                    
                    # Apply authentication and session management
                    await self._update_session_state()
                    
                    # Build enhanced yt-dlp options
                    ydl_opts = await self._build_enhanced_download_options(
                        output_path=output_path,
                        format_id=format_id,
                        audio_only=audio_only,
                        remove_watermark=remove_watermark,
                        output_template=output_template,
                        force_overwrite=force_overwrite,
                        progress_tracker=progress_tracker,
                        allow_resumption=allow_resumption,
                        attempt=attempt
                    )
                    
                    logger.info(f"Starting TikTok video download: {url}")
                    
                    # Download using yt-dlp
                    download_result = await self._execute_download_with_ydlp(
                        url, ydl_opts, progress_tracker
                    )
                    
                    # Calculate download time
                    download_time = asyncio.get_event_loop().time() - start_time
                    
                    # Create successful download result
                    result = DownloadResult(
                        success=True,
                        video_info=video_info,
                        file_path=output_path,
                        file_size=output_path.stat().st_size if output_path.exists() else 0,
                        format_used=selected_format,
                        download_time=download_time
                    )
                    
                    # Track download
                    self._add_to_downloads(url, True, str(output_path))
                    
                    logger.info(f"Successfully downloaded TikTok video: {output_path}")
                    return result
                    
                except (yt_dlp.utils.DownloadError, PlatformConnectionError) as e:
                    last_exception = e
                    error_msg = str(e).lower()
                    
                    # Check if this is a retryable error
                    is_retryable = self._is_retryable_error(error_msg)
                    
                    if attempt < max_retries and is_retryable:
                        # Calculate exponential backoff with jitter
                        delay = retry_delay * (2 ** attempt) + (0.1 * attempt)
                        logger.warning(f"Download attempt {attempt + 1} failed, retrying in {delay:.1f}s: {error_msg}")
                        
                        # Notify progress callback of retry
                        if progress_callback:
                            retry_progress = DownloadProgress(
                                status=DownloadStatus.PENDING,
                                progress_percent=0.0,
                                message=f"Retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries + 1})"
                            )
                            progress_callback(retry_progress)
                        
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # Not retryable or max retries reached
                        logger.error(f"Download failed after {attempt + 1} attempts: {error_msg}")
                        break
            
            # If we reach here, all retries failed
            error_msg = str(last_exception) if last_exception else "Unknown error"
            
            # Create failed download result
            result = DownloadResult(
                success=False,
                video_info=video_info,
                error_message=error_msg
            )
            
            self._add_to_downloads(url, False, error_msg)
            
            raise PlatformError(
                f"Download failed after {max_retries + 1} attempts: {error_msg}",
                platform=self.platform_type,
                url=url,
                original_error=last_exception
            )
                    
        except PlatformError:
            # Re-raise platform errors as-is
            raise
        except Exception as e:
            logger.error(f"Unexpected error downloading TikTok video {url}: {e}")
            raise PlatformError(
                f"Unexpected download error: {str(e)}",
                platform=self.platform_type,
                url=url,
                original_error=e
            )
        finally:
            # Always remove from downloading set
            self._downloading_urls.discard(url)
    
    def set_output_dir(self, directory: str) -> None:
        """Set the output directory for downloads"""
        self._output_dir = directory
        self._config['output_dir'] = directory
    
    def get_downloads(self) -> Dict[str, Any]:
        """Get information about downloaded videos"""
        return self._downloads.copy()
    
    def is_downloading(self, url: str) -> bool:
        """Check if URL is currently being downloaded"""
        return url in self._downloading_urls
    
    def is_converting_mp3(self, url: str) -> bool:
        """Check if URL is currently being converted to MP3"""
        return url in self._converting_mp3_urls
    
    # =====================================================
    # Private Helper Methods
    # =====================================================
    
    async def _convert_ytdlp_to_platform_info(self, result: Dict[str, Any], url: str) -> PlatformVideoInfo:
        """Convert yt-dlp result to PlatformVideoInfo with enhanced TikTok-specific metadata"""
        
        # Extract basic information
        title = result.get('title', 'Unknown Title')
        thumbnail_url = result.get('thumbnail', '')
        duration = result.get('duration', 0)
        description = result.get('description', '')
        
        # Extract creator information with enhanced details
        creator = result.get('uploader', '') or result.get('channel', '') or result.get('creator', '')
        creator_id = result.get('uploader_id', '') or result.get('channel_id', '')
        creator_url = result.get('uploader_url', '') or result.get('channel_url', '')
        creator_avatar = result.get('uploader_avatar', '') or result.get('channel_avatar', '')
        
        # Extract engagement statistics
        view_count = result.get('view_count', 0)
        like_count = result.get('like_count', 0)
        comment_count = result.get('comment_count', 0)  # TikTok specific
        share_count = result.get('repost_count', 0) or result.get('share_count', 0)  # TikTok shares
        
        # Enhanced timestamp processing
        upload_date = result.get('upload_date')
        timestamp = None
        if upload_date:
            try:
                from datetime import datetime
                if len(upload_date) == 8:  # YYYYMMDD format
                    timestamp = datetime.strptime(upload_date, '%Y%m%d')
                elif len(upload_date) == 14:  # YYYYMMDDHHMMSS format
                    timestamp = datetime.strptime(upload_date, '%Y%m%d%H%M%S')
                else:
                    # Try to parse as epoch timestamp
                    timestamp = datetime.fromtimestamp(int(upload_date))
            except (ValueError, TypeError, OSError):
                logger.warning(f"Could not parse upload_date: {upload_date}")
        
        # Enhanced hashtag and mention extraction
        hashtags = self._extract_hashtags(f"{title} {description}")
        mentions = self._extract_mentions(f"{title} {description}")
        
        # Extract TikTok-specific music/sound information
        music_info = self._extract_music_info(result)
        
        # Extract video characteristics and effects
        video_effects = self._extract_video_effects(result)
        
        # Enhanced location and geo data
        location_info = self._extract_location_info(result)
        
        # Convert formats with enhanced metadata
        formats = []
        if result.get('formats'):
            for fmt in result['formats']:
                video_format = VideoFormat(
                    format_id=fmt.get('format_id', ''),
                    quality=self._map_ytdlp_quality_to_platform(fmt),
                    ext=fmt.get('ext', 'mp4'),
                    url=fmt.get('url', ''),
                    filesize=fmt.get('filesize', 0),
                    width=fmt.get('width'),
                    height=fmt.get('height'),
                    fps=fmt.get('fps'),
                    vcodec=fmt.get('vcodec'),
                    acodec=fmt.get('acodec'),
                    abr=fmt.get('abr'),
                    vbr=fmt.get('vbr'),
                    # Enhanced TikTok format metadata
                    has_watermark=fmt.get('has_watermark', True),  # TikTok usually has watermarks
                    is_audio_only=fmt.get('vcodec') == 'none'
                )
                formats.append(video_format)
        
        # Extract video platform ID (TikTok video ID)
        platform_id = self.extract_video_id(url) or result.get('id', '')
        
        # Build comprehensive extra_data with TikTok-specific information
        extra_data = {
            # Original yt-dlp data (for debugging/advanced use)
            'original_url': result.get('webpage_url', url),
            'extractor': result.get('extractor', 'tiktok'),
            'extractor_key': result.get('extractor_key', 'TikTok'),
            
            # TikTok-specific metadata
            'video_id': platform_id,
            'is_watermarked': True,  # TikTok videos typically have watermarks
            'music': music_info,
            'effects': video_effects,
            'location': location_info,
            
            # Creator verification and additional info
            'creator_url': creator_url,  # Store creator URL in extra_data
            'creator_verified': result.get('uploader_verified', False) or creator.endswith('✓'),
            'creator_follower_count': result.get('uploader_follower_count', 0),
            
            # Video characteristics
            'video_codec': result.get('vcodec'),
            'audio_codec': result.get('acodec'),
            'container': result.get('container'),
            'protocol': result.get('protocol'),
            
            # Additional engagement metrics
            'favorite_count': result.get('favorite_count', 0),
            'dislike_count': result.get('dislike_count', 0),
            
            # Content categorization
            'categories': result.get('categories', []),
            'tags': result.get('tags', []),
            'age_limit': result.get('age_limit', 0),
            
            # Technical details
            'resolution': f"{result.get('width', 0)}x{result.get('height', 0)}" if result.get('width') and result.get('height') else None,
            'aspect_ratio': result.get('width', 0) / result.get('height', 1) if result.get('height') else None,
            
            # Availability and restrictions
            'availability': result.get('availability', 'public'),
            'live_status': result.get('live_status', 'not_live'),
            
            # Timestamps in different formats
            'epoch_timestamp': result.get('timestamp'),
            'upload_date_string': upload_date,
            
            # Language and region
            'language': result.get('language'),
            'subtitles_available': bool(result.get('subtitles')),
            'automatic_captions_available': bool(result.get('automatic_captions')),
        }
        
        # Create enhanced PlatformVideoInfo
        return PlatformVideoInfo(
            url=url,
            platform=self.platform_type,
            platform_id=platform_id,
            title=title,
            description=description,
            thumbnail_url=thumbnail_url,
            duration=duration,
            creator=creator,
            creator_id=creator_id,
            creator_avatar=creator_avatar,
            content_type=ContentType.VIDEO,
            hashtags=hashtags,
            mentions=mentions,
            view_count=view_count,
            like_count=like_count,
            comment_count=comment_count,
            share_count=share_count,
            published_at=timestamp,
            formats=formats,
            extra_data=extra_data
        )
    
    def _map_ytdlp_quality_to_platform(self, fmt: Dict[str, Any]) -> QualityLevel:
        """Map yt-dlp format to platform quality level"""
        height = fmt.get('height', 0) or 0  # Handle None values
        
        if height >= 1080:
            return QualityLevel.FHD  # Full HD (1080p)
        elif height >= 720:
            return QualityLevel.HD   # HD (720p)
        elif height >= 480:
            return QualityLevel.SD   # Standard Definition (480p)
        elif height >= 360:
            return QualityLevel.LD   # Low Definition (360p)
        elif height >= 240:
            return QualityLevel.MOBILE  # Mobile quality (240p)
        else:
            return QualityLevel.AUDIO_ONLY if fmt.get('vcodec') == 'none' else QualityLevel.WORST
    
    def _build_download_options(
        self,
        output_path: Path,
        format_id: Optional[str] = None,
        audio_only: bool = False,
        remove_watermark: bool = True,
        output_template: Optional[str] = None,
        force_overwrite: bool = False
    ) -> Dict[str, Any]:
        """Build yt-dlp download options"""
        
        options = {
            'outtmpl': str(output_path) if not output_template else output_template,
            'quiet': True,
            'no_warnings': True,
        }
        
        # Format selection
        if audio_only:
            options['format'] = 'bestaudio/best'
            options['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        elif format_id:
            options['format'] = format_id
        else:
            options['format'] = 'best'
        
        # Overwrite handling
        if force_overwrite:
            options['overwrites'] = True
        
        return options
    
    def _progress_hook(self, d: Dict[str, Any], progress_info: Dict[str, Any]) -> None:
        """Handle download progress updates"""
        if d['status'] == 'downloading':
            # Update progress information
            progress_info['total_bytes'] = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
            progress_info['downloaded_bytes'] = d.get('downloaded_bytes', 0)
            
            # Calculate progress percentage
            if progress_info['total_bytes'] > 0:
                progress_percent = (progress_info['downloaded_bytes'] / progress_info['total_bytes']) * 100
            else:
                progress_percent = 0
            
            # Extract speed information
            speed = d.get('speed', 0) or 0
            speed_str = f"{speed / 1024 / 1024:.1f} MB/s" if speed > 0 else "Unknown"
            
            # Create progress object
            progress = DownloadProgress(
                status=DownloadStatus.DOWNLOADING,
                progress_percent=progress_percent,
                downloaded_bytes=progress_info['downloaded_bytes'],
                total_bytes=progress_info['total_bytes'],
                speed_bps=speed
            )
            
            # Notify progress callbacks
            self._notify_progress(progress_info['url'], progress)
            
        elif d['status'] == 'finished':
            # Download completed
            progress = DownloadProgress(
                status=DownloadStatus.COMPLETED,
                progress_percent=100.0,
                downloaded_bytes=progress_info['total_bytes'],
                total_bytes=progress_info['total_bytes'],
                speed_bps=0
            )
            
            self._notify_progress(progress_info['url'], progress)
    
    def _add_to_downloads(self, url: str, success: bool, file_path: str) -> None:
        """Track download information"""
        self._downloads[url] = {
            'success': success,
            'file_path': file_path,
            'timestamp': __import__('datetime').datetime.now()
        }
    
    def _extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags from text"""
        if not text:
            return []
        
        hashtag_pattern = r'#(\w+)'
        hashtags = re.findall(hashtag_pattern, text)
        return list(set(hashtags))  # Remove duplicates
    
    def _extract_mentions(self, text: str) -> List[str]:
        """Extract mentions from text"""
        if not text:
            return []
        
        mention_pattern = r'@(\w+)'
        mentions = re.findall(mention_pattern, text)
        return list(set(mentions))  # Remove duplicates
    
    def _extract_music_info(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract music information from yt-dlp result"""
        music_info = {}
        
        if result.get('track'):
            music_info['track'] = result['track']
        
        if result.get('artist'):
            music_info['artist'] = result['artist']
        
        if result.get('album'):
            music_info['album'] = result['album']
        
        if result.get('genre'):
            music_info['genre'] = result['genre']
        
        if result.get('date'):
            music_info['date'] = result['date']
        
        return music_info
    
    def _extract_video_effects(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract video effects from yt-dlp result"""
        video_effects = {}
        
        if result.get('effects'):
            video_effects['effects'] = result['effects']
        
        if result.get('contrast'):
            video_effects['contrast'] = result['contrast']
        
        if result.get('brightness'):
            video_effects['brightness'] = result['brightness']
        
        if result.get('saturation'):
            video_effects['saturation'] = result['saturation']
        
        if result.get('hue'):
            video_effects['hue'] = result['hue']
        
        return video_effects
    
    def _extract_location_info(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract location information from yt-dlp result"""
        location_info = {}
        
        if result.get('location'):
            location_info['location'] = result['location']
        
        if result.get('latitude'):
            location_info['latitude'] = result['latitude']
        
        if result.get('longitude'):
            location_info['longitude'] = result['longitude']
        
        return location_info
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from TikTok URL"""
        # Standard TikTok video URL pattern
        match = re.search(r'/video/(\d+)', url)
        if match:
            return match.group(1)
        
        # For shortened URLs, we can't extract ID without resolving
        return None
    
    def normalize_url(self, url: str) -> str:
        """Normalize TikTok URL"""
        # Basic normalization - remove unnecessary parameters
        parsed = urlparse(url)
        
        # For shortened URLs, we'd need to resolve them
        if parsed.netloc in ['vm.tiktok.com', 'vt.tiktok.com']:
            # In a real implementation, you'd resolve the redirect
            return url
        
        # Clean up standard URLs
        if 'tiktok.com' in parsed.netloc:
            # Remove tracking parameters but keep essential ones
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        
        return url
    
    def slugify(self, text: str) -> str:
        """Convert text to a safe filename slug"""
        # Normalize Unicode text
        text = unicodedata.normalize('NFKD', text)
        text = ''.join([c for c in text if not unicodedata.combining(c)])
        
        # Replace spaces with hyphens and convert to lowercase
        text = text.lower().replace(' ', '-')
        
        # Remove characters that aren't letters, numbers, or hyphens
        text = re.sub(r'[^\w\s-]', '', text)
        
        # Remove consecutive hyphens
        text = re.sub(r'[-\s]+', '-', text)
        
        # Ensure no hyphens at beginning or end
        return text.strip('-')
    
    # =====================================================
    # Authentication & Session Management Methods
    # =====================================================
    
    def _get_user_agent(self) -> str:
        """Get user agent for requests (with rotation support)"""
        if self._headers_config.get('user_agent'):
            return self._headers_config['user_agent']
        
        # Rotate user agents based on request count
        import random
        if self._headers_config.get('rotate_user_agent', True):
            return random.choice(self._user_agents)
        
        return self._user_agents[0]  # Default to first one
    
    def _get_headers(self) -> Dict[str, str]:
        """Build headers for TikTok requests"""
        headers = {
            'User-Agent': self._current_user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Add custom headers from config
        custom_headers = self._headers_config.get('custom', {})
        headers.update(custom_headers)
        
        return headers
    
    def _get_proxy_config(self) -> Optional[Dict[str, str]]:
        """Get proxy configuration if available"""
        if not self._proxy_config.get('enabled', False):
            return None
        
        proxy_url = self._proxy_config.get('url')
        if not proxy_url:
            return None
        
        return {
            'http': proxy_url,
            'https': proxy_url
        }
    
    def _should_authenticate(self) -> bool:
        """Check if authentication is required for the current request"""
        # For TikTok with yt-dlp, authentication is generally not required
        # for public content, but this method can be extended for future needs
        return self._auth_info is not None
    
    def _apply_authentication(self, ydl_opts: Dict[str, Any]) -> None:
        """Apply authentication settings to yt-dlp options"""
        # Add custom headers
        headers = self._get_headers()
        if headers:
            ydl_opts.setdefault('http_headers', {}).update(headers)
        
        # Add proxy configuration
        proxy_config = self._get_proxy_config()
        if proxy_config:
            ydl_opts['proxy'] = proxy_config.get('https', proxy_config.get('http'))
        
        # Add cookies if available
        if self._session_cookies:
            ydl_opts['cookiefile'] = None  # Use in-memory cookies
            # yt-dlp will handle cookies automatically
        
        # Add rate limiting
        rate_limit = self._config.get('rate_limit', {})
        if rate_limit.get('enabled', True):
            ydl_opts['sleep_interval'] = rate_limit.get('sleep_interval', 1)
            ydl_opts['max_sleep_interval'] = rate_limit.get('max_sleep_interval', 5)
        
        # Add authentication info if available
        if self._should_authenticate() and self._auth_info:
            if hasattr(self._auth_info, 'credentials'):
                # Future API key support
                api_key = self._auth_info.credentials.get('api_key')
                if api_key:
                    ydl_opts['http_headers']['Authorization'] = f'Bearer {api_key}'
    
    async def _update_session_state(self) -> None:
        """Update session state for downloads (async version)"""
        import time
        self._request_count += 1
        self._last_request_time = time.time()
        
        # Rotate user agent if configured
        if (self._headers_config.get('rotate_user_agent', True) and 
            self._request_count % self._headers_config.get('rotate_interval', 10) == 0):
            self._current_user_agent = self._get_user_agent()
        
        # Apply rate limiting if needed
        rate_limit = self._config.get('rate_limit', {})
        if rate_limit.get('enabled', True):
            min_interval = rate_limit.get('min_request_interval', 0.5)
            elapsed = time.time() - self._last_request_time
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)
    
    def _validate_authentication(self) -> bool:
        """Validate current authentication state"""
        if not self._should_authenticate():
            return True  # No auth required
        
        if not self._auth_info:
            return False
        
        # Check if auth info is valid and not expired
        return self._auth_info.is_valid()
    
    def set_authentication(self, auth_info: Optional[Any]) -> None:
        """Set new authentication information"""
        self._auth_info = auth_info
        logger.info(f"Authentication {'enabled' if auth_info else 'disabled'} for TikTok handler")
    
    def clear_session(self) -> None:
        """Clear current session data"""
        self._session_cookies.clear()
        self._request_count = 0
        self._last_request_time = 0
        logger.info("TikTok session cleared")
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information"""
        return {
            'authenticated': self._should_authenticate(),
            'user_agent': self._current_user_agent,
            'request_count': self._request_count,
            'last_request_time': self._last_request_time,
            'cookies_count': len(self._session_cookies),
            'proxy_enabled': self._proxy_config.get('enabled', False)
        }
    
    # =====================================================
    # Enhanced Download Helper Methods
    # =====================================================
    
    async def _select_best_format(
        self,
        video_info: PlatformVideoInfo,
        quality: Optional[QualityLevel] = None,
        audio_only: bool = False,
        **kwargs
    ) -> Optional[VideoFormat]:
        """Select the best format based on quality preferences"""
        if not video_info.formats:
            return None
        
        available_formats = video_info.formats
        
        # Filter for audio-only if requested
        if audio_only:
            audio_formats = [f for f in available_formats if f.is_audio_only]
            if audio_formats:
                # Return best audio quality
                return max(audio_formats, key=lambda f: f.abr or 0)
            return None
        
        # Filter video formats
        video_formats = [f for f in available_formats if not f.is_audio_only]
        if not video_formats:
            return None
        
        # If specific quality requested, try to match it
        if quality:
            quality_matches = [f for f in video_formats if f.quality == quality]
            if quality_matches:
                # Among matching quality, prefer no watermark
                no_watermark = [f for f in quality_matches if not f.has_watermark]
                if no_watermark:
                    return max(no_watermark, key=lambda f: f.vbr or 0)
                return max(quality_matches, key=lambda f: f.vbr or 0)
        
        # Default selection: best quality available
        prefer_no_watermark = kwargs.get('prefer_no_watermark', True)
        
        if prefer_no_watermark:
            no_watermark_formats = [f for f in video_formats if not f.has_watermark]
            if no_watermark_formats:
                return max(no_watermark_formats, key=lambda f: (f.quality.height, f.vbr or 0))
        
        # Fallback to best quality overall
        return max(video_formats, key=lambda f: (f.quality.height, f.vbr or 0))
    
    async def _build_enhanced_download_options(
        self,
        output_path: Path,
        format_id: Optional[str] = None,
        audio_only: bool = False,
        remove_watermark: bool = True,
        output_template: Optional[str] = None,
        force_overwrite: bool = False,
        progress_tracker: 'DownloadProgressTracker' = None,
        allow_resumption: bool = True,
        attempt: int = 0
    ) -> Dict[str, Any]:
        """Build enhanced yt-dlp download options with retry and resumption support"""
        
        options = {
            'outtmpl': str(output_path) if not output_template else output_template,
            'quiet': True,
            'no_warnings': True,
        }
        
        # Format selection
        if audio_only:
            options['format'] = 'bestaudio/best'
            options['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        elif format_id:
            options['format'] = format_id
        else:
            options['format'] = 'best'
        
        # Overwrite handling
        if force_overwrite:
            options['overwrites'] = True
        
        # Resumption support
        if allow_resumption and output_path.exists():
            options['continue'] = True
            options['nooverwrites'] = False
        
        # Enhanced progress tracking
        if progress_tracker:
            options['progress_hooks'] = [progress_tracker.progress_hook]
        
        # Apply authentication and session settings
        self._apply_authentication(options)
        
        # Add retry-specific options
        if attempt > 0:
            # Add more conservative settings for retries
            options['socket_timeout'] = 30
            options['retries'] = 1  # yt-dlp internal retries
        
        return options
    
    async def _execute_download_with_ydlp(
        self,
        url: str,
        ydl_opts: Dict[str, Any],
        progress_tracker: 'DownloadProgressTracker'
    ) -> bool:
        """Execute download using yt-dlp with async support"""
        loop = asyncio.get_event_loop()
        
        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                return True
        
        # Run in thread pool to avoid blocking the event loop
        return await loop.run_in_executor(None, _download)
    
    def _is_retryable_error(self, error_msg: str) -> bool:
        """Determine if an error is retryable"""
        retryable_patterns = [
            'connection',
            'timeout',
            'network',
            'temporary',
            '429',  # Rate limit
            '502',  # Bad gateway
            '503',  # Service unavailable
            '504',  # Gateway timeout
            'ssl',
            'certificate'
        ]
        
        non_retryable_patterns = [
            'private',
            'removed',
            'deleted',
            'not available',
            'copyright',
            '404',  # Not found
            '403',  # Forbidden
            '401',  # Unauthorized
        ]
        
        error_lower = error_msg.lower()
        
        # Check non-retryable first (more specific)
        if any(pattern in error_lower for pattern in non_retryable_patterns):
            return False
        
        # Check retryable patterns
        return any(pattern in error_lower for pattern in retryable_patterns)
    
    # =====================================================
    # Comprehensive Error Handling Methods
    # =====================================================
    
    def _create_error_context(
        self,
        operation: str,
        url: Optional[str] = None,
        error_code: Optional[str] = None,
        original_error: Optional[Exception] = None,
        **kwargs
    ) -> TikTokErrorContext:
        """Create detailed error context for enhanced error reporting"""
        
        # Extract error details
        error_msg = str(original_error) if original_error else None
        technical_details = {
            'original_error_type': type(original_error).__name__ if original_error else None,
            'original_error_message': error_msg,
            'session_info': self.get_session_info(),
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        
        # Generate user-friendly message
        user_message = self._generate_user_friendly_message(operation, error_msg, error_code)
        
        # Get recovery suggestions
        suggested_actions = []
        recovery_options = []
        
        if self._enable_recovery_suggestions:
            error_type = type(original_error).__name__ if original_error else 'Unknown'
            context = TikTokErrorContext(operation, url, error_code)
            suggested_actions = self._error_recovery.get_recovery_suggestions(error_type, context)
            recovery_options = self._get_recovery_options(operation, error_msg)
        
        return TikTokErrorContext(
            operation=operation,
            url=url,
            error_code=error_code,
            user_message=user_message,
            technical_details=technical_details,
            suggested_actions=suggested_actions,
            recovery_options=recovery_options
        )
    
    def _generate_user_friendly_message(
        self,
        operation: str,
        error_msg: Optional[str],
        error_code: Optional[str]
    ) -> str:
        """Generate user-friendly error messages"""
        
        if not error_msg:
            return f"An error occurred during {operation}. Please try again."
        
        error_lower = error_msg.lower()
        
        # Network and connection errors
        if any(word in error_lower for word in ['connection', 'network', 'timeout', 'ssl']):
            return "Connection failed. Please check your internet connection and try again."
        
        # Rate limiting
        if '429' in str(error_code) or 'rate' in error_lower:
            return "Too many requests. Please wait a few minutes before trying again."
        
        # Content not available
        if any(word in error_lower for word in ['private', 'not available', 'removed', 'deleted']):
            return "This video is not available. It may be private, deleted, or restricted in your region."
        
        # Authentication issues
        if any(word in error_lower for word in ['forbidden', 'unauthorized', '403', '401']):
            return "Access denied. This content may require authentication or may be restricted."
        
        # Not found
        if '404' in str(error_code) or 'not found' in error_lower:
            return "Video not found. Please check the URL and try again."
        
        # API changes
        if any(word in error_lower for word in ['api', 'extractor', 'youtube-dl', 'yt-dlp']):
            return "TikTok's service may have changed. Please update the application or try again later."
        
        # Generic error with operation context
        operation_msg = {
            'video_info_extraction': 'extracting video information',
            'download': 'downloading the video',
            'authentication': 'authenticating with TikTok',
            'url_validation': 'validating the URL'
        }.get(operation, operation)
        
        return f"Error {operation_msg}. Please try again or contact support if the issue persists."
    
    def _get_recovery_options(self, operation: str, error_msg: Optional[str]) -> List[str]:
        """Get specific recovery options based on operation and error"""
        options = []
        
        if operation == 'download' and error_msg:
            error_lower = error_msg.lower()
            
            if 'quality' in error_lower or 'format' in error_lower:
                options.append("Try downloading in lower quality")
                options.append("Try audio-only download")
            
            if 'watermark' in error_lower:
                options.append("Try downloading with watermark included")
            
            if 'connection' in error_lower:
                options.append("Try using a different network")
                options.append("Try using a VPN")
        
        elif operation == 'video_info_extraction':
            options.extend([
                "Try refreshing the TikTok page and copying the URL again",
                "Try using a different URL format (mobile vs desktop)",
                "Check if the video is still available on TikTok"
            ])
        
        return options
    
    def _handle_error_with_context(
        self,
        operation: str,
        original_error: Exception,
        url: Optional[str] = None,
        **kwargs
    ) -> PlatformError:
        """Handle errors with comprehensive context and monitoring"""
        
        # Create detailed error context
        error_context = self._create_error_context(
            operation=operation,
            url=url,
            original_error=original_error,
            **kwargs
        )
        
        # Record error for monitoring
        if self._enable_error_monitoring:
            error_type = type(original_error).__name__
            self._error_monitor.record_error(error_type, error_context)
            
            # Log detailed error context
            logger.error(f"TikTok handler error in {operation}: {error_context.to_dict()}")
        
        # Check circuit breaker
        if self._enable_circuit_breaker and self._error_monitor.is_circuit_open():
            raise PlatformError(
                "TikTok service is temporarily unavailable due to repeated errors. Please try again later.",
                platform=self.platform_type,
                url=url,
                original_error=original_error
            )
        
        # Determine appropriate platform exception type
        error_msg = str(original_error).lower()
        
        if any(word in error_msg for word in ['private', 'not available', 'removed', 'deleted', 'forbidden']):
            exception_class = PlatformContentError
        elif any(word in error_msg for word in ['connection', 'network', 'timeout', 'ssl']):
            exception_class = PlatformConnectionError
        elif '429' in error_msg or 'rate' in error_msg:
            exception_class = PlatformRateLimitError
        else:
            exception_class = PlatformError
        
        # Create enhanced exception with context
        enhanced_error = exception_class(
            error_context.user_message,
            platform=self.platform_type,
            url=url,
            original_error=original_error
        )
        
        # Add error context as attribute for advanced error handling
        enhanced_error.error_context = error_context
        
        return enhanced_error
    
    async def _attempt_error_recovery(
        self,
        operation: str,
        original_error: Exception,
        url: Optional[str] = None,
        **recovery_kwargs
    ) -> Optional[Any]:
        """Attempt automatic error recovery based on error type and operation"""
        
        if not self._enable_recovery_suggestions:
            return None
        
        error_msg = str(original_error).lower()
        
        # URL normalization recovery for connection errors
        if url and 'connection' in error_msg and operation in ['video_info_extraction', 'download']:
            logger.info(f"Attempting URL normalization recovery for {url}")
            alternative_urls = await self._error_recovery.attempt_url_normalization(url)
            
            for alt_url in alternative_urls[1:]:  # Skip original URL
                try:
                    if operation == 'video_info_extraction':
                        return await self.get_video_info(alt_url)
                    # Add other recovery operations as needed
                except Exception as retry_error:
                    logger.debug(f"Recovery attempt with {alt_url} failed: {retry_error}")
                    continue
        
        # Quality degradation recovery for download errors
        if (operation == 'download' and 
            'format' in error_msg and 
            'video_info' in recovery_kwargs and 
            'failed_quality' in recovery_kwargs):
            
            logger.info("Attempting quality degradation recovery")
            video_info = recovery_kwargs['video_info']
            failed_quality = recovery_kwargs['failed_quality']
            
            fallback_format = await self._error_recovery.attempt_quality_degradation(
                video_info.formats, failed_quality
            )
            
            if fallback_format:
                logger.info(f"Found fallback format: {fallback_format.quality.value}")
                return fallback_format
        
        return None
    
    def get_error_health_status(self) -> Dict[str, Any]:
        """Get current error monitoring and health status"""
        if not self._enable_error_monitoring:
            return {'error_monitoring': 'disabled'}
        
        health_status = self._error_monitor.get_health_status()
        health_status.update({
            'error_monitoring_enabled': self._enable_error_monitoring,
            'circuit_breaker_enabled': self._enable_circuit_breaker,
            'recovery_suggestions_enabled': self._enable_recovery_suggestions
        })
        
        return health_status
    
    def reset_error_state(self) -> None:
        """Reset error monitoring state (admin function)"""
        if self._enable_error_monitoring:
            self._error_monitor = TikTokErrorMonitor()
            logger.info("TikTok error monitoring state reset") 