"""
Custom Platform Handler Template

This template provides a complete starting point for implementing new platform handlers.
Copy this file and modify it for your specific platform requirements.

Replace 'Custom' with your platform name throughout the file.
"""

import asyncio
import aiohttp
import logging
import re
from typing import Optional, List, Callable, Dict, Any
from urllib.parse import urlparse

from platforms.base import (
    AbstractPlatformHandler,
    PlatformHandler,
    PlatformType,
    PlatformVideoInfo,
    VideoFormat,
    QualityLevel,
    DownloadResult,
    DownloadProgress,
    ContentType,
    PlatformError,
    PlatformConnectionError,
    PlatformContentError,
    PlatformRateLimitError,
    LifecycleMixin,
    RateLimitedMixin,
    CachedMixin,
    rate_limited,
    with_retry,
    cached
)

logger = logging.getLogger(__name__)


# TODO: Update these patterns for your platform
@PlatformHandler(
    platform_type=PlatformType.CUSTOM,  # Change to your platform type
    url_patterns=[
        r'https?://(?:www\.)?yourplatform\.com/video/(\d+)',
        r'https?://yourplatform\.com/v/([a-zA-Z0-9_-]+)',
        # Add more URL patterns as needed
    ],
    capabilities=['download', 'metadata']  # Add capabilities your platform supports
)
class CustomPlatformHandler(AbstractPlatformHandler, LifecycleMixin, RateLimitedMixin, CachedMixin):
    """
    Custom platform handler implementation
    
    TODO: Update this docstring with your platform's specific features
    
    Features:
    - Video metadata extraction
    - Video downloads
    - Rate limiting and caching
    - Lifecycle management
    - Error handling
    """
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(
            platform_type=PlatformType.CUSTOM,  # Change to your platform
            name="Custom Platform Handler"  # Change to your platform name
        )
        
        # TODO: Configure your platform's API settings
        self.api_key = api_key
        self.api_base_url = "https://api.yourplatform.com/v1/"
        self.web_base_url = "https://www.yourplatform.com/"
        
        # TODO: Set appropriate User-Agent for your platform
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        
        # Session will be initialized in lifecycle
        self.session: Optional[aiohttp.ClientSession] = None
        
        # TODO: Configure rate limiting based on platform limits
        # Example: 60 requests per minute
        self.configure_rate_limiting(requests_per_minute=60)
        
        # TODO: Configure caching TTL based on data freshness needs
        # Example: 5 minutes for metadata
        self.configure_caching(default_ttl=300)
    
    async def initialize(self):
        """Initialize platform handler resources"""
        await super().initialize()
        
        # TODO: Add any platform-specific validation
        if not self.api_key:
            logger.warning("No API key provided. Some features may be limited.")
        
        # Create HTTP session with platform-specific configuration
        connector = aiohttp.TCPConnector(
            limit=10,  # TODO: Adjust based on platform limits
            limit_per_host=5,
            ttl_dns_cache=300,
            use_dns_cache=True
        )
        
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': self.user_agent}
        )
        
        logger.info("Custom platform handler initialized")
    
    async def cleanup(self):
        """Clean up platform handler resources"""
        if self.session:
            await self.session.close()
            self.session = None
        
        await super().cleanup()
        logger.info("Custom platform handler cleaned up")
    
    @rate_limited(requests_per_minute=60)  # TODO: Adjust rate limit
    @with_retry(max_attempts=3, backoff_factor=1.5)
    @cached(ttl=300)  # TODO: Adjust cache TTL
    async def get_video_info(self, url: str) -> PlatformVideoInfo:
        """
        Extract video information from platform URL
        
        TODO: Implement your platform's metadata extraction logic
        
        Args:
            url: Platform video URL
            
        Returns:
            PlatformVideoInfo with extracted metadata
            
        Raises:
            PlatformContentError: If video is not found or unavailable
            PlatformConnectionError: If network request fails
            PlatformRateLimitError: If rate limited by platform
        """
        async with self.managed_lifecycle():
            try:
                # TODO: Extract video ID from URL
                video_id = self._extract_video_id(url)
                if not video_id:
                    raise PlatformContentError(
                        "Could not extract video ID from URL",
                        platform=self.platform_type,
                        url=url
                    )
                
                # TODO: Fetch video metadata from your platform's API
                metadata = await self._fetch_video_metadata(video_id)
                
                # TODO: Parse and normalize metadata
                video_info = self._parse_video_metadata(metadata, url)
                
                # TODO: Extract video formats if needed
                video_info.formats = await self._extract_video_formats(video_id, metadata)
                
                logger.info(f"Successfully extracted video info: {video_info.title}")
                return video_info
                
            except Exception as e:
                logger.error(f"Failed to get video info for {url}: {e}")
                raise self._handle_error(e, url=url)
    
    @rate_limited(requests_per_minute=30)  # TODO: Adjust for downloads
    @with_retry(max_attempts=3, backoff_factor=2.0)
    async def download_video(self, 
                           url: str, 
                           output_path: str,
                           quality: Optional[QualityLevel] = None,
                           progress_callback: Optional[Callable[[DownloadProgress], None]] = None) -> DownloadResult:
        """
        Download video from platform
        
        TODO: Implement your platform's download logic
        
        Args:
            url: Platform video URL
            output_path: Output file path
            quality: Desired video quality
            progress_callback: Progress update callback
            
        Returns:
            DownloadResult with download information
        """
        async with self.managed_lifecycle():
            try:
                # Get video information and formats
                video_info = await self.get_video_info(url)
                
                if not video_info.formats:
                    raise PlatformContentError(
                        "No downloadable formats found",
                        platform=self.platform_type,
                        url=url
                    )
                
                # Select best format based on quality preference
                selected_format = self._select_best_format(video_info.formats, quality)
                
                if not selected_format.url:
                    raise PlatformContentError(
                        "Selected format has no download URL",
                        platform=self.platform_type,
                        url=url
                    )
                
                # Download the video
                download_result = await self._download_file(
                    selected_format.url,
                    output_path,
                    progress_callback
                )
                
                # Update result with video information
                download_result.video_info = video_info
                download_result.format_info = selected_format
                
                logger.info(f"Successfully downloaded video: {output_path}")
                return download_result
                
            except Exception as e:
                logger.error(f"Failed to download video {url}: {e}")
                raise self._handle_error(e, url=url)
    
    # Optional: Implement if your platform supports search
    async def search_content(self, query: str, limit: int = 10) -> List[PlatformVideoInfo]:
        """
        Search for content on platform
        
        TODO: Implement if your platform supports search
        """
        raise NotImplementedError("Search not implemented for this platform")
    
    # Optional: Implement if your platform supports user video listings
    async def get_user_videos(self, user_id: str, limit: int = 10) -> List[PlatformVideoInfo]:
        """
        Get videos from user profile
        
        TODO: Implement if your platform supports user video listings
        """
        raise NotImplementedError("User videos not implemented for this platform")
    
    def _extract_video_id(self, url: str) -> Optional[str]:
        """
        Extract video ID from platform URL
        
        TODO: Implement URL parsing for your platform
        """
        # Example patterns - replace with your platform's URL structure
        patterns = [
            r'/video/(\d+)',
            r'/v/([a-zA-Z0-9_-]+)',
            r'video_id=([a-zA-Z0-9_-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    async def _fetch_video_metadata(self, video_id: str) -> dict:
        """
        Fetch video metadata from platform API
        
        TODO: Implement API call to your platform
        """
        try:
            # Example API call - replace with your platform's API
            url = f"{self.api_base_url}videos/{video_id}"
            headers = {}
            
            # Add authentication if required
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
                # OR headers['X-API-Key'] = self.api_key
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    raise PlatformContentError(
                        "Video not found",
                        platform=self.platform_type
                    )
                elif response.status == 429:
                    raise PlatformRateLimitError(
                        "Rate limited by platform",
                        platform=self.platform_type,
                        retry_after=60
                    )
                else:
                    raise PlatformConnectionError(
                        f"API request failed (status: {response.status})",
                        platform=self.platform_type
                    )
                    
        except aiohttp.ClientError as e:
            raise PlatformConnectionError(
                f"Failed to fetch metadata: {e}",
                platform=self.platform_type
            )
    
    def _parse_video_metadata(self, metadata: dict, url: str) -> PlatformVideoInfo:
        """
        Parse platform metadata into normalized format
        
        TODO: Map your platform's metadata fields to PlatformVideoInfo
        """
        # Example mapping - replace with your platform's data structure
        return PlatformVideoInfo(
            url=url,
            platform=self.platform_type,
            platform_id=metadata.get('id'),
            title=metadata.get('title', 'Untitled Video'),
            description=metadata.get('description', ''),
            thumbnail_url=metadata.get('thumbnail_url', ''),
            duration=metadata.get('duration'),
            creator=metadata.get('author', {}).get('name', 'Unknown'),
            creator_id=metadata.get('author', {}).get('id'),
            creator_avatar=metadata.get('author', {}).get('avatar_url'),
            content_type=ContentType.VIDEO,
            hashtags=self._extract_hashtags(metadata.get('description', '')),
            mentions=self._extract_mentions(metadata.get('description', '')),
            view_count=metadata.get('stats', {}).get('views'),
            like_count=metadata.get('stats', {}).get('likes'),
            comment_count=metadata.get('stats', {}).get('comments'),
            share_count=metadata.get('stats', {}).get('shares'),
            published_at=self._parse_timestamp(metadata.get('created_at')),
            extra_data={
                # Add any platform-specific data here
                'platform_specific_field': metadata.get('custom_field')
            }
        )
    
    async def _extract_video_formats(self, video_id: str, metadata: dict) -> List[VideoFormat]:
        """
        Extract available video formats
        
        TODO: Parse format information from your platform's API response
        """
        formats = []
        
        # Example format extraction - replace with your platform's structure
        video_urls = metadata.get('video_urls', {})
        
        if 'hd' in video_urls:
            formats.append(VideoFormat(
                format_id='hd',
                quality=QualityLevel.HIGH,
                url=video_urls['hd'],
                width=1280,
                height=720,
                ext='mp4'
            ))
        
        if 'sd' in video_urls:
            formats.append(VideoFormat(
                format_id='sd',
                quality=QualityLevel.MEDIUM,
                url=video_urls['sd'],
                width=640,
                height=480,
                ext='mp4'
            ))
        
        return formats
    
    def _select_best_format(self, formats: List[VideoFormat], quality: Optional[QualityLevel]) -> VideoFormat:
        """Select the best format based on quality preference"""
        if not formats:
            raise PlatformContentError("No formats available")
        
        if quality is None:
            quality = QualityLevel.BEST
        
        # Quality preference mapping
        quality_order = {
            QualityLevel.BEST: 1000,
            QualityLevel.HIGH: 800,
            QualityLevel.MEDIUM: 600,
            QualityLevel.LOW: 400
        }
        
        # Sort by quality
        sorted_formats = sorted(
            formats,
            key=lambda f: quality_order.get(f.quality, 0),
            reverse=True
        )
        
        return sorted_formats[0]
    
    async def _download_file(self, 
                           url: str, 
                           output_path: str,
                           progress_callback: Optional[Callable] = None) -> DownloadResult:
        """
        Download file with progress tracking
        
        TODO: Implement actual file download logic
        """
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    raise PlatformConnectionError(
                        f"Failed to download file (status: {response.status})",
                        platform=self.platform_type
                    )
                
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                
                with open(output_path, 'wb') as file:
                    async for chunk in response.content.iter_chunked(8192):
                        file.write(chunk)
                        downloaded += len(chunk)
                        
                        # Report progress if callback provided
                        if progress_callback and total_size > 0:
                            progress = DownloadProgress(
                                downloaded_bytes=downloaded,
                                total_bytes=total_size,
                                percentage=min(100.0, (downloaded / total_size) * 100),
                                speed_bytes_per_second=0,  # TODO: Calculate actual speed
                                status="downloading"
                            )
                            progress_callback(progress)
                
                return DownloadResult(
                    success=True,
                    file_path=output_path,
                    file_size=downloaded
                )
                
        except Exception as e:
            return DownloadResult(
                success=False,
                error_message=str(e)
            )
    
    def _extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags from text"""
        if not text:
            return []
        
        hashtag_pattern = r'#(\w+)'
        hashtags = re.findall(hashtag_pattern, text, re.IGNORECASE)
        return [tag.lower() for tag in hashtags]
    
    def _extract_mentions(self, text: str) -> List[str]:
        """Extract user mentions from text"""
        if not text:
            return []
        
        mention_pattern = r'@(\w+)'
        mentions = re.findall(mention_pattern, text, re.IGNORECASE)
        return [mention.lower() for mention in mentions]
    
    def _parse_timestamp(self, timestamp) -> Optional:
        """Parse timestamp to datetime"""
        if not timestamp:
            return None
        
        try:
            from datetime import datetime, timezone
            if isinstance(timestamp, (int, float)):
                return datetime.fromtimestamp(timestamp, timezone.utc)
            elif isinstance(timestamp, str):
                # Try ISO format
                return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except Exception:
            pass
        
        return None
    
    def _handle_error(self, error: Exception, **context) -> PlatformError:
        """
        Convert generic errors to platform-specific platform errors
        
        TODO: Add platform-specific error handling patterns
        """
        error_str = str(error).lower()
        
        if isinstance(error, aiohttp.ClientError):
            return PlatformConnectionError(
                f"Platform connection failed: {error}",
                platform=self.platform_type,
                **context
            )
        elif "not found" in error_str or "404" in error_str:
            return PlatformContentError(
                "Content not found or unavailable",
                platform=self.platform_type,
                **context
            )
        elif "rate limit" in error_str or "429" in error_str:
            return PlatformRateLimitError(
                "Rate limited by platform",
                platform=self.platform_type,
                retry_after=60,
                **context
            )
        elif "forbidden" in error_str or "403" in error_str:
            return PlatformContentError(
                "Access forbidden",
                platform=self.platform_type,
                **context
            )
        else:
            return PlatformError(
                f"Platform handler error: {error}",
                platform=self.platform_type,
                **context
            )


# Example usage and testing
async def example_usage():
    """Example demonstrating custom platform handler usage"""
    
    # Create handler
    handler = CustomPlatformHandler(api_key="your_api_key_here")
    
    try:
        # Initialize handler
        await handler.initialize()
        
        # Test video info extraction
        url = "https://www.yourplatform.com/video/123456"
        
        try:
            video_info = await handler.get_video_info(url)
            
            print(f"Title: {video_info.title}")
            print(f"Creator: {video_info.creator}")
            print(f"Duration: {video_info.duration}s")
            print(f"Views: {video_info.view_count:,}")
            
            # Test download
            def progress_callback(progress: DownloadProgress):
                print(f"Download progress: {progress.percentage:.1f}%")
            
            result = await handler.download_video(
                url,
                "custom_video.mp4",
                quality=QualityLevel.HIGH,
                progress_callback=progress_callback
            )
            
            if result.success:
                print(f"Downloaded to: {result.file_path}")
            else:
                print(f"Download failed: {result.error_message}")
                
        except PlatformError as e:
            print(f"Platform error: {e}")
            print(f"Error type: {type(e).__name__}")
    
    finally:
        # Always clean up
        await handler.cleanup()


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage()) 