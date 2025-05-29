"""
TikTok Platform Handler Implementation

This module contains the TikTok-specific implementation of the AbstractPlatformHandler,
adapting the existing TikTokDownloader functionality to the new platform architecture.
"""

import asyncio
import logging
import re
import unicodedata
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
        **kwargs
    ) -> DownloadResult:
        """
        Download video from TikTok
        
        Args:
            url: TikTok video URL
            output_path: Output file path
            quality: Desired video quality
            audio_only: Whether to download audio only
            **kwargs: Additional options (format_id, remove_watermark, force_overwrite, etc.)
            
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
        
        try:
            # Get video info first
            video_info = await self.get_video_info(url)
            
            # Extract kwargs options
            format_id = kwargs.get('format_id')
            remove_watermark = kwargs.get('remove_watermark', True)
            output_template = kwargs.get('output_template')
            force_overwrite = kwargs.get('force_overwrite', False)
            
            # Build yt-dlp options
            ydl_opts = self._build_download_options(
                output_path=output_path,
                format_id=format_id,
                audio_only=audio_only,
                remove_watermark=remove_watermark,
                output_template=output_template,
                force_overwrite=force_overwrite
            )
            
            # Add progress hook
            progress_info = {'url': url, 'total_bytes': 0, 'downloaded_bytes': 0}
            ydl_opts['progress_hooks'] = [lambda d: self._progress_hook(d, progress_info)]
            
            logger.info(f"Starting TikTok video download: {url}")
            
            # Download using yt-dlp
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    ydl.download([url])
                    
                    # Create successful download result
                    result = DownloadResult(
                        success=True,
                        video_info=video_info,
                        file_path=output_path,
                        file_size=output_path.stat().st_size if output_path.exists() else 0,
                        format_used=None  # Could be determined from selected format
                    )
                    
                    # Track download
                    self._add_to_downloads(url, True, str(output_path))
                    
                    logger.info(f"Successfully downloaded TikTok video: {output_path}")
                    return result
                    
                except yt_dlp.utils.DownloadError as e:
                    error_msg = str(e)
                    logger.error(f"yt-dlp download error: {error_msg}")
                    
                    # Create failed download result
                    result = DownloadResult(
                        success=False,
                        video_info=video_info,
                        error_message=error_msg
                    )
                    
                    self._add_to_downloads(url, False, error_msg)
                    
                    raise PlatformError(
                        f"Download failed: {error_msg}",
                        platform=self.platform_type,
                        url=url,
                        original_error=e
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
    
    def _update_session_state(self) -> None:
        """Update session state after a request"""
        import time
        self._request_count += 1
        self._last_request_time = time.time()
        
        # Rotate user agent if configured
        if (self._headers_config.get('rotate_user_agent', True) and 
            self._request_count % self._headers_config.get('rotate_interval', 10) == 0):
            self._current_user_agent = self._get_user_agent()
    
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