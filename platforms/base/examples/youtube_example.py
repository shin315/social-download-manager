"""
YouTube Platform Handler Example

This example demonstrates how to implement a YouTube handler using
the Abstract Platform Handler framework with YouTube API integration.
"""

import asyncio
import aiohttp
import logging
import re
from typing import Optional, List, Callable, Dict, Any
from urllib.parse import urlparse, parse_qs

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
    PlatformAuthError,
    LifecycleMixin,
    RateLimitedMixin,
    CachedMixin,
    rate_limited,
    with_retry,
    cached
)

logger = logging.getLogger(__name__)


@PlatformHandler(
    platform_type=PlatformType.YOUTUBE,
    url_patterns=[
        r'https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
        r'https?://(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)',
        r'https?://youtu\.be/([a-zA-Z0-9_-]+)',
        r'https?://(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]+)',
    ],
    capabilities=['download', 'metadata', 'search', 'user_videos', 'playlists']
)
class YouTubeHandler(AbstractPlatformHandler, LifecycleMixin, RateLimitedMixin, CachedMixin):
    """
    YouTube platform handler implementation
    
    Features:
    - Video metadata extraction via YouTube API
    - Multiple quality downloads
    - Channel video listing
    - Video search functionality
    - Playlist support
    - Rate limiting and authentication
    """
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(
            platform_type=PlatformType.YOUTUBE,
            name="YouTube Handler"
        )
        
        # YouTube API configuration
        self.api_key = api_key
        self.api_base_url = "https://www.googleapis.com/youtube/v3"
        self.api_quota_limit = 10000  # Daily quota limit
        self.api_quota_used = 0
        
        # Session will be initialized in lifecycle
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Configure rate limiting: 100 requests per minute (API limit)
        self.configure_rate_limiting(requests_per_minute=100)
        
        # Configure caching: 10 minute TTL for metadata
        self.configure_caching(default_ttl=600)
    
    async def initialize(self):
        """Initialize YouTube handler resources"""
        await super().initialize()
        
        if not self.api_key:
            logger.warning("No YouTube API key provided. Some features may be limited.")
        
        # Create HTTP session
        connector = aiohttp.TCPConnector(
            limit=20,
            limit_per_host=10,
            ttl_dns_cache=300,
            use_dns_cache=True
        )
        
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        )
        
        logger.info("YouTube handler initialized")
    
    async def cleanup(self):
        """Clean up YouTube handler resources"""
        if self.session:
            await self.session.close()
            self.session = None
        
        await super().cleanup()
        logger.info("YouTube handler cleaned up")
    
    @rate_limited(requests_per_minute=100)
    @with_retry(max_attempts=3, backoff_factor=1.5)
    @cached(ttl=600)
    async def get_video_info(self, url: str) -> PlatformVideoInfo:
        """
        Extract video information from YouTube URL
        
        Args:
            url: YouTube video URL
            
        Returns:
            PlatformVideoInfo with extracted metadata
        """
        async with self.managed_lifecycle():
            try:
                # Extract video ID from URL
                video_id = self._extract_video_id(url)
                if not video_id:
                    raise PlatformContentError(
                        "Could not extract video ID from URL",
                        platform=self.platform_type,
                        url=url
                    )
                
                # Check API quota
                self._check_api_quota(1)
                
                # Fetch video metadata from YouTube API
                metadata = await self._fetch_video_metadata(video_id)
                
                # Parse and normalize metadata
                video_info = self._parse_video_metadata(metadata, url)
                
                # Extract video formats (requires additional processing)
                video_info.formats = await self._extract_video_formats(video_id)
                
                logger.info(f"Successfully extracted YouTube video info: {video_info.title}")
                return video_info
                
            except Exception as e:
                logger.error(f"Failed to get YouTube video info for {url}: {e}")
                raise self._handle_error(e, url=url)
    
    @rate_limited(requests_per_minute=50)
    @with_retry(max_attempts=3, backoff_factor=2.0)
    async def download_video(self, 
                           url: str, 
                           output_path: str,
                           quality: Optional[QualityLevel] = None,
                           progress_callback: Optional[Callable[[DownloadProgress], None]] = None) -> DownloadResult:
        """Download video from YouTube"""
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
                
                # Select best format
                selected_format = self._select_best_format(video_info.formats, quality)
                
                # Download the video
                download_result = await self._download_file(
                    selected_format.url,
                    output_path,
                    progress_callback
                )
                
                # Update result with video information
                download_result.video_info = video_info
                download_result.format_info = selected_format
                
                logger.info(f"Successfully downloaded YouTube video: {output_path}")
                return download_result
                
            except Exception as e:
                logger.error(f"Failed to download YouTube video {url}: {e}")
                raise self._handle_error(e, url=url)
    
    @rate_limited(requests_per_minute=60)
    @cached(ttl=900)
    async def search_content(self, query: str, limit: int = 10) -> List[PlatformVideoInfo]:
        """
        Search for YouTube videos
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of PlatformVideoInfo objects
        """
        async with self.managed_lifecycle():
            try:
                if not self.api_key:
                    raise PlatformAuthError(
                        "YouTube API key required for search",
                        platform=self.platform_type
                    )
                
                # Check API quota
                self._check_api_quota(100)  # Search costs 100 quota units
                
                # Perform search
                search_results = await self._search_videos(query, limit)
                
                videos = []
                for result in search_results:
                    try:
                        video_info = await self.get_video_info(
                            f"https://www.youtube.com/watch?v={result['id']['videoId']}"
                        )
                        videos.append(video_info)
                    except Exception as e:
                        logger.warning(f"Failed to get video info for search result: {e}")
                        continue
                
                logger.info(f"Found {len(videos)} videos for query: {query}")
                return videos
                
            except Exception as e:
                logger.error(f"Failed to search YouTube for '{query}': {e}")
                raise self._handle_error(e, query=query)
    
    @rate_limited(requests_per_minute=60)
    @cached(ttl=1800)
    async def get_user_videos(self, user_id: str, limit: int = 10) -> List[PlatformVideoInfo]:
        """Get videos from YouTube channel"""
        async with self.managed_lifecycle():
            try:
                if not self.api_key:
                    raise PlatformAuthError(
                        "YouTube API key required for channel videos",
                        platform=self.platform_type
                    )
                
                # Check API quota
                self._check_api_quota(50)
                
                # Get channel uploads playlist
                channel_data = await self._get_channel_data(user_id)
                uploads_playlist_id = channel_data['contentDetails']['relatedPlaylists']['uploads']
                
                # Get videos from uploads playlist
                playlist_videos = await self._get_playlist_videos(uploads_playlist_id, limit)
                
                videos = []
                for video_data in playlist_videos:
                    try:
                        video_info = await self.get_video_info(
                            f"https://www.youtube.com/watch?v={video_data['snippet']['resourceId']['videoId']}"
                        )
                        videos.append(video_info)
                    except Exception as e:
                        logger.warning(f"Failed to get video info: {e}")
                        continue
                
                logger.info(f"Retrieved {len(videos)} videos for channel {user_id}")
                return videos
                
            except Exception as e:
                logger.error(f"Failed to get channel videos for {user_id}: {e}")
                raise self._handle_error(e, user_id=user_id)
    
    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL"""
        patterns = [
            r'(?:v=|v\/|embed\/|youtu\.be\/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/watch\?.*v=([a-zA-Z0-9_-]{11})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def _check_api_quota(self, cost: int) -> None:
        """Check if API quota allows the operation"""
        if self.api_quota_used + cost > self.api_quota_limit:
            raise PlatformError(
                "YouTube API quota exceeded for today",
                platform=self.platform_type
            )
        
        self.api_quota_used += cost
    
    async def _fetch_video_metadata(self, video_id: str) -> dict:
        """Fetch video metadata from YouTube API"""
        if not self.api_key:
            # Fallback to basic scraping (limited data)
            return await self._scrape_video_metadata(video_id)
        
        url = f"{self.api_base_url}/videos"
        params = {
            'part': 'snippet,statistics,contentDetails,status',
            'id': video_id,
            'key': self.api_key
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    items = data.get('items', [])
                    if items:
                        return items[0]
                    else:
                        raise PlatformContentError(
                            "Video not found",
                            platform=self.platform_type
                        )
                elif response.status == 403:
                    error_data = await response.json()
                    error_message = error_data.get('error', {}).get('message', 'API access forbidden')
                    raise PlatformAuthError(
                        f"YouTube API error: {error_message}",
                        platform=self.platform_type
                    )
                else:
                    raise PlatformConnectionError(
                        f"YouTube API request failed (status: {response.status})",
                        platform=self.platform_type
                    )
        
        except aiohttp.ClientError as e:
            raise PlatformConnectionError(
                f"Failed to fetch YouTube metadata: {e}",
                platform=self.platform_type
            )
    
    async def _scrape_video_metadata(self, video_id: str) -> dict:
        """Fallback: scrape basic metadata from YouTube page"""
        # Simplified scraping - real implementation would parse page content
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        async with self.session.get(url) as response:
            if response.status == 200:
                # Would parse HTML content for basic metadata
                return {
                    'id': video_id,
                    'snippet': {
                        'title': 'YouTube Video',
                        'description': '',
                        'channelTitle': 'Unknown Channel',
                        'publishedAt': '',
                        'thumbnails': {
                            'high': {'url': f'https://i.ytimg.com/vi/{video_id}/hqdefault.jpg'}
                        }
                    },
                    'statistics': {},
                    'contentDetails': {'duration': 'PT0S'}
                }
            else:
                raise PlatformContentError(
                    "Video not found or unavailable",
                    platform=self.platform_type
                )
    
    def _parse_video_metadata(self, metadata: dict, url: str) -> PlatformVideoInfo:
        """Parse YouTube metadata into normalized format"""
        snippet = metadata.get('snippet', {})
        statistics = metadata.get('statistics', {})
        content_details = metadata.get('contentDetails', {})
        
        return PlatformVideoInfo(
            url=url,
            platform=self.platform_type,
            platform_id=metadata.get('id'),
            title=snippet.get('title', 'YouTube Video'),
            description=snippet.get('description', ''),
            thumbnail_url=snippet.get('thumbnails', {}).get('high', {}).get('url', ''),
            duration=self._parse_duration(content_details.get('duration', 'PT0S')),
            creator=snippet.get('channelTitle', 'Unknown'),
            creator_id=snippet.get('channelId'),
            content_type=ContentType.VIDEO,
            hashtags=self._extract_hashtags(snippet.get('description', '')),
            mentions=self._extract_mentions(snippet.get('description', '')),
            view_count=int(statistics.get('viewCount', 0)) if statistics.get('viewCount') else None,
            like_count=int(statistics.get('likeCount', 0)) if statistics.get('likeCount') else None,
            comment_count=int(statistics.get('commentCount', 0)) if statistics.get('commentCount') else None,
            published_at=self._parse_timestamp(snippet.get('publishedAt')),
            extra_data={
                'category_id': snippet.get('categoryId'),
                'default_language': snippet.get('defaultLanguage'),
                'tags': snippet.get('tags', []),
                'definition': content_details.get('definition'),
                'caption': content_details.get('caption'),
                'licensed_content': content_details.get('licensedContent')
            }
        )
    
    async def _extract_video_formats(self, video_id: str) -> List[VideoFormat]:
        """Extract available video formats"""
        # This would typically use youtube-dl or similar tool
        # For this example, we'll return some standard formats
        formats = [
            VideoFormat(
                format_id='720p',
                quality=QualityLevel.HIGH,
                ext='mp4',
                width=1280,
                height=720
            ),
            VideoFormat(
                format_id='480p',
                quality=QualityLevel.MEDIUM,
                ext='mp4',
                width=854,
                height=480
            ),
            VideoFormat(
                format_id='360p',
                quality=QualityLevel.LOW,
                ext='mp4',
                width=640,
                height=360
            )
        ]
        
        return formats
    
    async def _search_videos(self, query: str, limit: int) -> List[dict]:
        """Search for videos using YouTube API"""
        url = f"{self.api_base_url}/search"
        params = {
            'part': 'snippet',
            'q': query,
            'type': 'video',
            'maxResults': min(limit, 50),
            'order': 'relevance',
            'key': self.api_key
        }
        
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('items', [])
            else:
                raise PlatformConnectionError(
                    f"YouTube search failed (status: {response.status})",
                    platform=self.platform_type
                )
    
    async def _get_channel_data(self, channel_id: str) -> dict:
        """Get channel information"""
        url = f"{self.api_base_url}/channels"
        params = {
            'part': 'contentDetails',
            'id': channel_id,
            'key': self.api_key
        }
        
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                items = data.get('items', [])
                if items:
                    return items[0]
                else:
                    raise PlatformContentError(
                        "Channel not found",
                        platform=self.platform_type
                    )
            else:
                raise PlatformConnectionError(
                    f"Channel data request failed (status: {response.status})",
                    platform=self.platform_type
                )
    
    async def _get_playlist_videos(self, playlist_id: str, limit: int) -> List[dict]:
        """Get videos from playlist"""
        url = f"{self.api_base_url}/playlistItems"
        params = {
            'part': 'snippet',
            'playlistId': playlist_id,
            'maxResults': min(limit, 50),
            'key': self.api_key
        }
        
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('items', [])
            else:
                raise PlatformConnectionError(
                    f"Playlist request failed (status: {response.status})",
                    platform=self.platform_type
                )
    
    def _select_best_format(self, formats: List[VideoFormat], quality: Optional[QualityLevel]) -> VideoFormat:
        """Select the best format based on quality preference"""
        if not formats:
            raise PlatformContentError("No formats available")
        
        if quality is None:
            quality = QualityLevel.HIGH
        
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
        """Download file with progress tracking"""
        # This is a placeholder - real implementation would use
        # youtube-dl or similar tool for actual YouTube downloads
        
        return DownloadResult(
            success=False,
            error_message="YouTube download requires youtube-dl integration"
        )
    
    def _parse_duration(self, duration_str: str) -> Optional[float]:
        """Parse ISO 8601 duration to seconds"""
        if not duration_str:
            return None
        
        # Parse ISO 8601 format (PT1H2M3S)
        pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?'
        match = re.match(pattern, duration_str)
        
        if match:
            hours, minutes, seconds = match.groups()
            total_seconds = 0
            
            if hours:
                total_seconds += int(hours) * 3600
            if minutes:
                total_seconds += int(minutes) * 60
            if seconds:
                total_seconds += float(seconds)
            
            return total_seconds
        
        return None
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional:
        """Parse YouTube timestamp to datetime"""
        if not timestamp_str:
            return None
        
        try:
            from datetime import datetime
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except Exception:
            return None
    
    def _extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags from description"""
        if not text:
            return []
        
        hashtag_pattern = r'#(\w+)'
        hashtags = re.findall(hashtag_pattern, text, re.IGNORECASE)
        return [tag.lower() for tag in hashtags]
    
    def _extract_mentions(self, text: str) -> List[str]:
        """Extract mentions from description"""
        if not text:
            return []
        
        # YouTube doesn't have @mentions like Twitter, but we can look for channel references
        mention_pattern = r'@(\w+)'
        mentions = re.findall(mention_pattern, text, re.IGNORECASE)
        return [mention.lower() for mention in mentions]
    
    def _handle_error(self, error: Exception, **context) -> PlatformError:
        """Convert generic errors to YouTube-specific platform errors"""
        error_str = str(error).lower()
        
        if isinstance(error, aiohttp.ClientError):
            return PlatformConnectionError(
                f"YouTube connection failed: {error}",
                platform=self.platform_type,
                **context
            )
        elif "not found" in error_str or "404" in error_str:
            return PlatformContentError(
                "YouTube video not found or unavailable",
                platform=self.platform_type,
                **context
            )
        elif "forbidden" in error_str or "403" in error_str:
            return PlatformAuthError(
                "YouTube API access forbidden",
                platform=self.platform_type,
                **context
            )
        elif "quota" in error_str:
            return PlatformError(
                "YouTube API quota exceeded",
                platform=self.platform_type,
                **context
            )
        else:
            return PlatformError(
                f"YouTube handler error: {error}",
                platform=self.platform_type,
                **context
            )


# Example usage
async def example_usage():
    """Example demonstrating YouTube handler usage"""
    
    # Create handler with API key
    api_key = "YOUR_YOUTUBE_API_KEY"  # Replace with actual API key
    handler = YouTubeHandler(api_key=api_key)
    
    try:
        # Initialize handler
        await handler.initialize()
        
        # Get video information
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        video_info = await handler.get_video_info(url)
        
        print(f"Title: {video_info.title}")
        print(f"Channel: {video_info.creator}")
        print(f"Views: {video_info.view_count:,}")
        print(f"Likes: {video_info.like_count:,}")
        print(f"Duration: {video_info.duration}s")
        print(f"Published: {video_info.published_at}")
        
        # Search for videos
        search_results = await handler.search_content("python tutorial", limit=5)
        print(f"\nFound {len(search_results)} search results:")
        
        for video in search_results[:3]:
            print(f"- {video.title} by {video.creator}")
        
        # Get channel videos
        channel_videos = await handler.get_user_videos("UC_channel_id", limit=5)
        print(f"\nFound {len(channel_videos)} channel videos")
        
        for video in channel_videos:
            print(f"- {video.title} ({video.view_count:,} views)")
    
    except PlatformError as e:
        print(f"Platform error: {e}")
        print(f"Error type: {type(e).__name__}")
    
    finally:
        # Clean up handler
        await handler.cleanup()


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage()) 