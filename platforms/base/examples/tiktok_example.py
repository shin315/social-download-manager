"""
TikTok Platform Handler Example

This example demonstrates how to implement a complete TikTok handler using
the Abstract Platform Handler framework. It includes all the best practices,
error handling, authentication, and metadata extraction.
"""

import asyncio
import aiohttp
import logging
import re
from typing import Optional, List, Callable
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


@PlatformHandler(
    platform_type=PlatformType.TIKTOK,
    url_patterns=[
        r'https?://(?:www\.)?tiktok\.com/@([^/]+)/video/(\d+)',
        r'https?://(?:vm|vt)\.tiktok\.com/[A-Za-z0-9]+',
        r'https?://(?:www\.)?tiktok\.com/t/[A-Za-z0-9]+',
    ],
    capabilities=['download', 'metadata', 'user_videos']
)
class TikTokHandler(AbstractPlatformHandler, LifecycleMixin, RateLimitedMixin, CachedMixin):
    """
    TikTok platform handler implementation
    
    Features:
    - Video metadata extraction
    - High-quality video downloads
    - User profile video listing
    - Rate limiting and caching
    - Automatic lifecycle management
    - Comprehensive error handling
    """
    
    def __init__(self):
        super().__init__(
            platform_type=PlatformType.TIKTOK,
            name="TikTok Handler"
        )
        
        # TikTok-specific configuration
        self.api_base_url = "https://api.tiktok.com/aweme/v1/"
        self.web_base_url = "https://www.tiktok.com/"
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        
        # Session will be initialized in lifecycle
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Configure rate limiting: 30 requests per minute
        self.configure_rate_limiting(requests_per_minute=30)
        
        # Configure caching: 5 minute TTL for metadata
        self.configure_caching(default_ttl=300)
    
    async def initialize(self):
        """Initialize TikTok handler resources"""
        await super().initialize()
        
        # Create HTTP session with TikTok-specific configuration
        connector = aiohttp.TCPConnector(
            limit=10,
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
        
        logger.info("TikTok handler initialized")
    
    async def cleanup(self):
        """Clean up TikTok handler resources"""
        if self.session:
            await self.session.close()
            self.session = None
        
        await super().cleanup()
        logger.info("TikTok handler cleaned up")
    
    @rate_limited(requests_per_minute=30)
    @with_retry(max_attempts=3, backoff_factor=1.5)
    @cached(ttl=300)
    async def get_video_info(self, url: str) -> PlatformVideoInfo:
        """
        Extract video information from TikTok URL
        
        Args:
            url: TikTok video URL
            
        Returns:
            PlatformVideoInfo with extracted metadata
            
        Raises:
            PlatformContentError: If video is not found or unavailable
            PlatformConnectionError: If network request fails
            PlatformRateLimitError: If rate limited by TikTok
        """
        async with self.managed_lifecycle():
            try:
                # Normalize URL (handle shortened URLs)
                normalized_url = await self._normalize_url(url)
                
                # Extract video ID from URL
                video_id = self._extract_video_id(normalized_url)
                if not video_id:
                    raise PlatformContentError(
                        "Could not extract video ID from URL",
                        platform=self.platform_type,
                        url=url
                    )
                
                # Fetch video metadata
                metadata = await self._fetch_video_metadata(video_id)
                
                # Parse and normalize metadata
                video_info = self._parse_video_metadata(metadata, normalized_url)
                
                # Extract video formats
                video_info.formats = await self._extract_video_formats(video_id, metadata)
                
                logger.info(f"Successfully extracted TikTok video info: {video_info.title}")
                return video_info
                
            except Exception as e:
                logger.error(f"Failed to get TikTok video info for {url}: {e}")
                raise self._handle_error(e, url=url)
    
    @rate_limited(requests_per_minute=10)
    @with_retry(max_attempts=3, backoff_factor=2.0)
    async def download_video(self, 
                           url: str, 
                           output_path: str,
                           quality: Optional[QualityLevel] = None,
                           progress_callback: Optional[Callable[[DownloadProgress], None]] = None) -> DownloadResult:
        """
        Download video from TikTok
        
        Args:
            url: TikTok video URL
            output_path: Output file path
            quality: Desired video quality (defaults to best available)
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
                
                logger.info(f"Successfully downloaded TikTok video: {output_path}")
                return download_result
                
            except Exception as e:
                logger.error(f"Failed to download TikTok video {url}: {e}")
                raise self._handle_error(e, url=url)
    
    @rate_limited(requests_per_minute=20)
    @cached(ttl=600)
    async def get_user_videos(self, user_id: str, limit: int = 10) -> List[PlatformVideoInfo]:
        """
        Get videos from TikTok user profile
        
        Args:
            user_id: TikTok username (without @)
            limit: Maximum number of videos to return
            
        Returns:
            List of PlatformVideoInfo objects
        """
        async with self.managed_lifecycle():
            try:
                # Fetch user profile and videos
                user_data = await self._fetch_user_profile(user_id)
                videos_data = await self._fetch_user_videos(user_id, limit)
                
                videos = []
                for video_data in videos_data[:limit]:
                    try:
                        video_info = self._parse_video_metadata(
                            video_data, 
                            f"https://www.tiktok.com/@{user_id}/video/{video_data.get('id')}"
                        )
                        videos.append(video_info)
                    except Exception as e:
                        logger.warning(f"Failed to parse video metadata: {e}")
                        continue
                
                logger.info(f"Retrieved {len(videos)} videos for user {user_id}")
                return videos
                
            except Exception as e:
                logger.error(f"Failed to get user videos for {user_id}: {e}")
                raise self._handle_error(e, user_id=user_id)
    
    async def _normalize_url(self, url: str) -> str:
        """Normalize TikTok URL (resolve redirects for shortened URLs)"""
        parsed = urlparse(url)
        
        # Handle shortened URLs (vm.tiktok.com, vt.tiktok.com)
        if parsed.netloc in ['vm.tiktok.com', 'vt.tiktok.com']:
            try:
                async with self.session.get(url, allow_redirects=True) as response:
                    return str(response.url)
            except Exception as e:
                logger.warning(f"Failed to resolve shortened URL {url}: {e}")
                return url
        
        return url
    
    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from TikTok URL"""
        patterns = [
            r'/video/(\d+)',
            r'/v/(\d+)',
            r'video_id=(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    async def _fetch_video_metadata(self, video_id: str) -> dict:
        """Fetch video metadata from TikTok API"""
        # This is a simplified example - real implementation would use
        # TikTok's official API or a reliable scraping method
        
        try:
            # Try official API first (requires authentication)
            if hasattr(self, 'api_token'):
                url = f"{self.api_base_url}video/detail/"
                params = {'aweme_id': video_id}
                headers = {'Authorization': f'Bearer {self.api_token}'}
                
                async with self.session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('aweme_detail', {})
            
            # Fallback to web scraping
            return await self._scrape_video_metadata(video_id)
            
        except aiohttp.ClientError as e:
            raise PlatformConnectionError(
                f"Failed to fetch TikTok metadata: {e}",
                platform=self.platform_type
            )
    
    async def _scrape_video_metadata(self, video_id: str) -> dict:
        """Scrape video metadata from TikTok web page"""
        # Simplified web scraping example
        # Real implementation would need to handle JavaScript rendering
        
        url = f"https://www.tiktok.com/api/recommend/item_list/"
        params = {'count': 1, 'id': video_id}
        
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('itemList', [{}])[0]
            elif response.status == 429:
                raise PlatformRateLimitError(
                    "Rate limited by TikTok",
                    platform=self.platform_type,
                    retry_after=60
                )
            else:
                raise PlatformContentError(
                    f"Video not found or unavailable (status: {response.status})",
                    platform=self.platform_type
                )
    
    def _parse_video_metadata(self, metadata: dict, url: str) -> PlatformVideoInfo:
        """Parse TikTok metadata into normalized format"""
        return PlatformVideoInfo(
            url=url,
            platform=self.platform_type,
            platform_id=metadata.get('id'),
            title=metadata.get('desc', 'TikTok Video'),
            description=metadata.get('desc', ''),
            thumbnail_url=metadata.get('video', {}).get('cover', ''),
            duration=metadata.get('video', {}).get('duration', 0),
            creator=metadata.get('author', {}).get('nickname', 'Unknown'),
            creator_id=metadata.get('author', {}).get('unique_id'),
            creator_avatar=metadata.get('author', {}).get('avatar_larger', ''),
            content_type=ContentType.VIDEO,
            hashtags=self._extract_hashtags(metadata.get('desc', '')),
            mentions=self._extract_mentions(metadata.get('desc', '')),
            view_count=metadata.get('statistics', {}).get('play_count'),
            like_count=metadata.get('statistics', {}).get('digg_count'),
            comment_count=metadata.get('statistics', {}).get('comment_count'),
            share_count=metadata.get('statistics', {}).get('share_count'),
            published_at=self._parse_timestamp(metadata.get('create_time')),
            extra_data={
                'music': metadata.get('music', {}),
                'effects': metadata.get('effect_stickers', []),
                'challenges': metadata.get('cha_list', [])
            }
        )
    
    async def _extract_video_formats(self, video_id: str, metadata: dict) -> List[VideoFormat]:
        """Extract available video formats"""
        formats = []
        video_data = metadata.get('video', {})
        
        # Extract different quality formats
        if 'play_addr' in video_data:
            # High quality format
            formats.append(VideoFormat(
                format_id='high',
                quality=QualityLevel.HIGH,
                url=video_data['play_addr'],
                width=video_data.get('width'),
                height=video_data.get('height'),
                ext='mp4',
                has_watermark=True  # TikTok videos typically have watermarks
            ))
        
        if 'download_addr' in video_data:
            # Download quality (usually best available)
            formats.append(VideoFormat(
                format_id='download',
                quality=QualityLevel.BEST,
                url=video_data['download_addr'],
                width=video_data.get('width'),
                height=video_data.get('height'),
                ext='mp4',
                has_watermark=False  # Download version may not have watermark
            ))
        
        return formats
    
    def _select_best_format(self, formats: List[VideoFormat], quality: Optional[QualityLevel]) -> VideoFormat:
        """Select the best format based on quality preference"""
        if not formats:
            raise PlatformContentError("No formats available")
        
        if quality is None:
            quality = QualityLevel.BEST
        
        # Sort formats by quality preference
        quality_order = {
            QualityLevel.BEST: 1000,
            QualityLevel.HIGH: 800,
            QualityLevel.MEDIUM: 600,
            QualityLevel.LOW: 400
        }
        
        # Filter formats without watermark if available
        no_watermark = [f for f in formats if not f.has_watermark]
        if no_watermark:
            formats = no_watermark
        
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
        """Download file with progress tracking"""
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
                        
                        if progress_callback and total_size > 0:
                            progress = DownloadProgress(
                                downloaded_bytes=downloaded,
                                total_bytes=total_size,
                                percentage=min(100.0, (downloaded / total_size) * 100),
                                speed_bytes_per_second=0,  # Could calculate actual speed
                                status="downloading"
                            )
                            progress_callback(progress)
                
                return DownloadResult(
                    success=True,
                    file_path=output_path,
                    file_size=downloaded,
                    duration=0  # Would be set from video_info
                )
                
        except Exception as e:
            return DownloadResult(
                success=False,
                error_message=str(e)
            )
    
    async def _fetch_user_profile(self, user_id: str) -> dict:
        """Fetch user profile information"""
        # Simplified implementation
        url = f"https://www.tiktok.com/@{user_id}"
        
        async with self.session.get(url) as response:
            if response.status == 200:
                # Would parse user data from response
                return {'username': user_id}
            else:
                raise PlatformContentError(
                    f"User not found: {user_id}",
                    platform=self.platform_type
                )
    
    async def _fetch_user_videos(self, user_id: str, limit: int) -> List[dict]:
        """Fetch user's recent videos"""
        # Simplified implementation
        # Real implementation would paginate through user's videos
        return []  # Would return list of video metadata
    
    def _extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags from video description"""
        if not text:
            return []
        
        hashtag_pattern = r'#(\w+)'
        hashtags = re.findall(hashtag_pattern, text, re.IGNORECASE)
        return [tag.lower() for tag in hashtags]
    
    def _extract_mentions(self, text: str) -> List[str]:
        """Extract user mentions from video description"""
        if not text:
            return []
        
        mention_pattern = r'@(\w+)'
        mentions = re.findall(mention_pattern, text, re.IGNORECASE)
        return [mention.lower() for mention in mentions]
    
    def _parse_timestamp(self, timestamp) -> Optional:
        """Parse TikTok timestamp to datetime"""
        if not timestamp:
            return None
        
        try:
            from datetime import datetime, timezone
            if isinstance(timestamp, (int, float)):
                return datetime.fromtimestamp(timestamp, timezone.utc)
            return None
        except Exception:
            return None
    
    def _handle_error(self, error: Exception, **context) -> PlatformError:
        """Convert generic errors to TikTok-specific platform errors"""
        error_str = str(error).lower()
        
        if isinstance(error, aiohttp.ClientError):
            return PlatformConnectionError(
                f"TikTok connection failed: {error}",
                platform=self.platform_type,
                **context
            )
        elif "not found" in error_str or "404" in error_str:
            return PlatformContentError(
                "TikTok video not found or unavailable",
                platform=self.platform_type,
                **context
            )
        elif "rate limit" in error_str or "429" in error_str:
            return PlatformRateLimitError(
                "Rate limited by TikTok",
                platform=self.platform_type,
                retry_after=60,
                **context
            )
        else:
            return PlatformError(
                f"TikTok handler error: {error}",
                platform=self.platform_type,
                **context
            )


# Example usage
async def example_usage():
    """Example demonstrating TikTok handler usage"""
    
    # Create handler (or use factory)
    handler = TikTokHandler()
    
    try:
        # Initialize handler
        await handler.initialize()
        
        # Get video information
        url = "https://www.tiktok.com/@username/video/1234567890"
        video_info = await handler.get_video_info(url)
        
        print(f"Title: {video_info.title}")
        print(f"Creator: {video_info.creator}")
        print(f"Views: {video_info.view_count:,}")
        print(f"Likes: {video_info.like_count:,}")
        print(f"Duration: {video_info.duration}s")
        print(f"Hashtags: {', '.join(video_info.hashtags)}")
        
        # Download video with progress tracking
        def progress_callback(progress: DownloadProgress):
            print(f"Download progress: {progress.percentage:.1f}%")
        
        result = await handler.download_video(
            url,
            "tiktok_video.mp4",
            quality=QualityLevel.HIGH,
            progress_callback=progress_callback
        )
        
        if result.success:
            print(f"Downloaded to: {result.file_path}")
            print(f"File size: {result.file_size:,} bytes")
        else:
            print(f"Download failed: {result.error_message}")
        
        # Get user videos
        user_videos = await handler.get_user_videos("username", limit=5)
        print(f"\nFound {len(user_videos)} recent videos from user")
        
        for video in user_videos:
            print(f"- {video.title} ({video.view_count:,} views)")
    
    except PlatformError as e:
        print(f"Platform error: {e}")
        print(f"Error type: {type(e).__name__}")
        if hasattr(e, 'url'):
            print(f"URL: {e.url}")
    
    finally:
        # Clean up handler
        await handler.cleanup()


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage()) 