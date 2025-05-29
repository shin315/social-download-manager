"""
Enhanced TikTok Platform Handler with Performance Optimizations

This module contains an optimized version of the TikTok handler that integrates
caching, connection pooling, memory optimization, and other performance enhancements.
"""

import asyncio
import hashlib
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable

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
    AuthType
)

# Import performance optimizations
from .performance_optimizations import (
    get_optimized_operations,
    TikTokOptimizedOperations,
    TikTokPerformanceCache,
    PerformanceMonitor
)

# Import base handler for core functionality
from .tiktok_handler import (
    TikTokHandler as BaseTikTokHandler,
    TikTokErrorContext,
    TikTokErrorMonitor,
    TikTokErrorRecovery
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
class EnhancedTikTokHandler(BaseTikTokHandler):
    """
    Enhanced TikTok Handler with Performance Optimizations
    
    This class extends the base TikTok handler with comprehensive performance
    optimizations including caching, connection pooling, and memory efficiency.
    """
    
    def __init__(self, auth_info: Optional[Any] = None, config: Optional[Dict[str, Any]] = None):
        """Initialize enhanced TikTok handler with performance optimizations"""
        super().__init__(auth_info, config)
        
        # Initialize performance components
        self._optimized_ops = get_optimized_operations()
        self._performance_monitor = PerformanceMonitor()
        
        # Performance configuration
        self._enable_caching = config.get('enable_caching', True) if config else True
        self._cache_ttl = config.get('cache_ttl', 1800) if config else 1800  # 30 minutes
        self._enable_concurrent_processing = config.get('enable_concurrent_processing', True) if config else True
        self._max_concurrent_operations = config.get('max_concurrent_operations', 5) if config else 5
        
        # Performance metrics
        self._start_time = time.time()
        self._operation_count = 0
        
        logger.info("Enhanced TikTok handler initialized with performance optimizations")
    
    def get_capabilities(self) -> PlatformCapabilities:
        """Get enhanced platform capabilities with performance info"""
        start_time = time.time()
        
        capabilities = super().get_capabilities()
        
        # Add performance-related capabilities
        capabilities.max_concurrent_downloads = self._max_concurrent_operations
        capabilities.supports_caching = self._enable_caching
        capabilities.supports_batch_processing = self._enable_concurrent_processing
        
        duration = time.time() - start_time
        self._performance_monitor.record_operation('get_capabilities', duration)
        
        return capabilities
    
    async def get_video_info(self, url: str) -> PlatformVideoInfo:
        """Get video info with performance optimizations"""
        start_time = time.time()
        self._operation_count += 1
        
        try:
            # Generate cache key
            cache_key = None
            if self._enable_caching:
                url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
                cache_key = f"video_info_{url_hash}"
                
                # Check cache first
                cached_info = self._optimized_ops.cache.get(cache_key)
                if cached_info:
                    logger.info(f"Cache hit for video info: {url}")
                    self._performance_monitor.record_operation('get_video_info_cached', time.time() - start_time)
                    return cached_info
            
            # Extract video info using yt-dlp
            logger.info(f"Extracting info from TikTok URL (optimized): {url}")
            
            try:
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': False,
                    'skip_download': True,
                    'force_json': True,
                }
                
                # Apply authentication if configured
                self._apply_authentication(ydl_opts)
                
                # Execute extraction with optimized operations
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    result = ydl.extract_info(url, download=False)
                
                if not result:
                    raise PlatformContentError("No video information could be extracted")
                
                # Use optimized metadata extraction
                optimized_metadata = await self._optimized_ops.extract_metadata_optimized(
                    result, url, cache_key
                )
                
                # Convert to PlatformVideoInfo using optimized processing
                video_info = await self._convert_ytdlp_to_platform_info_optimized(
                    result, url, optimized_metadata
                )
                
                # Cache the result
                if self._enable_caching and cache_key:
                    self._optimized_ops.cache.set(cache_key, video_info, ttl=self._cache_ttl)
                    logger.debug(f"Cached video info for: {url}")
                
                duration = time.time() - start_time
                self._performance_monitor.record_operation('get_video_info', duration)
                
                return video_info
                
            except Exception as e:
                # Handle errors with enhanced context
                context = self._create_error_context('get_video_info', url, original_error=e)
                
                if "Private video" in str(e) or "not available" in str(e):
                    raise PlatformContentError(f"Video is private or not available: {url}", context=context)
                elif "Sign in" in str(e) or "login" in str(e):
                    raise PlatformConnectionError(f"Authentication required for: {url}", context=context)
                else:
                    logger.error(f"Unexpected error getting TikTok video info for {url}: {e}")
                    raise PlatformError(f"Failed to get video info: {str(e)}", context=context)
                    
        except Exception as e:
            duration = time.time() - start_time
            self._performance_monitor.record_operation('get_video_info_error', duration)
            raise
    
    async def _convert_ytdlp_to_platform_info_optimized(
        self, 
        result: Dict[str, Any], 
        url: str,
        optimized_metadata: Optional[Dict[str, Any]] = None
    ) -> PlatformVideoInfo:
        """Convert yt-dlp result to PlatformVideoInfo with optimizations"""
        start_time = time.time()
        
        try:
            # Use pre-extracted optimized metadata if available
            if optimized_metadata:
                video_id = optimized_metadata.get('id', '')
                title = optimized_metadata.get('title', '')
                description = optimized_metadata.get('description', '')
                creator = optimized_metadata.get('creator', '')
                duration = optimized_metadata.get('duration')
                view_count = optimized_metadata.get('view_count', 0)
                like_count = optimized_metadata.get('like_count', 0)
                hashtags = optimized_metadata.get('hashtags', [])
                mentions = optimized_metadata.get('mentions', [])
            else:
                # Fallback to standard extraction
                video_id = result.get('id', '')
                title = result.get('title', '') or result.get('alt_title', '') or 'TikTok Video'
                description = result.get('description', '') or ''
                creator = result.get('uploader', '') or result.get('creator', '') or 'Unknown'
                duration = result.get('duration')
                view_count = result.get('view_count', 0) or 0
                like_count = result.get('like_count', 0) or 0
                hashtags = self._extract_hashtags(f"{title} {description}")
                mentions = self._extract_mentions(f"{title} {description}")
            
            # Process formats with optimization
            formats = result.get('formats', [])
            if formats and self._enable_concurrent_processing:
                processed_formats = await self._optimized_ops.process_formats_batch(formats)
                video_formats = await self._convert_formats_optimized(processed_formats)
            else:
                video_formats = [
                    await self._convert_single_format_optimized(fmt)
                    for fmt in formats[:10]  # Limit to first 10 for performance
                    if fmt.get('url')
                ]
                video_formats = [fmt for fmt in video_formats if fmt]  # Filter None results
            
            # Extract additional metadata efficiently
            upload_date = self._parse_upload_date_optimized(result.get('upload_date'))
            thumbnail_url = result.get('thumbnail') or result.get('thumbnails', [{}])[-1].get('url', '')
            
            # Create PlatformVideoInfo with optimized data
            video_info = PlatformVideoInfo(
                url=url,
                platform=PlatformType.TIKTOK,
                platform_id=video_id,
                title=title,
                description=description,
                creator=creator,
                creator_url=f"https://www.tiktok.com/@{creator}",
                thumbnail_url=thumbnail_url,
                duration=duration,
                upload_date=upload_date,
                view_count=view_count,
                like_count=like_count,
                content_type=ContentType.VIDEO,
                formats=video_formats,
                metadata={
                    'hashtags': hashtags,
                    'mentions': mentions,
                    'comment_count': result.get('comment_count', 0),
                    'share_count': result.get('repost_count', 0),
                    'music_info': self._extract_music_info(result),
                    'effects': self._extract_video_effects(result),
                    'location': self._extract_location_info(result),
                    'platform_specific': {
                        'tiktok_video_id': video_id,
                        'is_verified_creator': result.get('uploader_verified', False),
                        'creator_follower_count': result.get('uploader_follower_count', 0),
                        'video_category': result.get('category', ''),
                        'age_limit': result.get('age_limit', 0),
                        'availability': result.get('availability', 'public'),
                        'original_url': result.get('original_url', url),
                        'extracted_at': datetime.now().isoformat()
                    }
                }
            )
            
            duration = time.time() - start_time
            self._performance_monitor.record_operation('convert_ytdlp_to_platform_info', duration)
            
            return video_info
            
        except Exception as e:
            logger.error(f"Error converting yt-dlp result to PlatformVideoInfo: {e}")
            raise PlatformError(f"Failed to process video information: {str(e)}")
    
    async def _convert_formats_optimized(self, processed_formats: List[Dict[str, Any]]) -> List[VideoFormat]:
        """Convert processed formats to VideoFormat objects efficiently"""
        start_time = time.time()
        
        video_formats = []
        for fmt_data in processed_formats:
            try:
                # Map quality efficiently
                quality_str = fmt_data.get('quality', 'MOBILE')
                quality_map = {
                    'HD': QualityLevel.HD,
                    'SD': QualityLevel.SD,
                    'LD': QualityLevel.LD,
                    'MOBILE': QualityLevel.MOBILE
                }
                quality = quality_map.get(quality_str, QualityLevel.MOBILE)
                
                video_format = VideoFormat(
                    format_id=fmt_data.get('format_id', ''),
                    url=fmt_data.get('url', ''),
                    quality=quality,
                    file_extension=fmt_data.get('ext', 'mp4'),
                    filesize=fmt_data.get('filesize'),
                    audio_codec=fmt_data.get('acodec', 'aac'),
                    video_codec=fmt_data.get('vcodec', 'h264')
                )
                video_formats.append(video_format)
                
            except Exception as e:
                logger.warning(f"Error processing format: {e}")
                continue
        
        duration = time.time() - start_time
        self._performance_monitor.record_operation('convert_formats', duration)
        
        return video_formats
    
    async def _convert_single_format_optimized(self, fmt: Dict[str, Any]) -> Optional[VideoFormat]:
        """Convert single format with optimization"""
        try:
            quality = self._map_ytdlp_quality_to_platform(fmt)
            
            return VideoFormat(
                format_id=fmt.get('format_id', ''),
                url=fmt.get('url', ''),
                quality=quality,
                file_extension=fmt.get('ext', 'mp4'),
                filesize=fmt.get('filesize'),
                audio_codec=fmt.get('acodec', 'aac'),
                video_codec=fmt.get('vcodec', 'h264'),
                resolution=f"{fmt.get('width', 0)}x{fmt.get('height', 0)}",
                fps=fmt.get('fps', 30),
                bitrate=fmt.get('tbr')
            )
        except Exception as e:
            logger.warning(f"Error converting format: {e}")
            return None
    
    def _parse_upload_date_optimized(self, upload_date_str: Optional[str]) -> Optional[datetime]:
        """Optimized upload date parsing with caching"""
        if not upload_date_str:
            return None
        
        # Check cache first
        if self._enable_caching:
            cache_key = f"upload_date_{upload_date_str}"
            cached_date = self._optimized_ops.cache.get(cache_key)
            if cached_date:
                return cached_date
        
        try:
            # Parse date efficiently
            if len(upload_date_str) == 8:  # YYYYMMDD
                parsed_date = datetime.strptime(upload_date_str, '%Y%m%d')
            elif len(upload_date_str) == 14:  # YYYYMMDDHHMMSS
                parsed_date = datetime.strptime(upload_date_str, '%Y%m%d%H%M%S')
            else:
                # Try other common formats
                for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S']:
                    try:
                        parsed_date = datetime.strptime(upload_date_str, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    return None
            
            # Cache result
            if self._enable_caching:
                self._optimized_ops.cache.set(cache_key, parsed_date, ttl=86400)  # 24 hours
            
            return parsed_date
            
        except Exception as e:
            logger.warning(f"Error parsing upload date '{upload_date_str}': {e}")
            return None
    
    async def download_video(
        self,
        url: str,
        output_path: Path,
        quality: Optional[QualityLevel] = None,
        audio_only: bool = False,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
        **kwargs
    ) -> DownloadResult:
        """Download video with performance optimizations"""
        start_time = time.time()
        self._operation_count += 1
        
        try:
            # Check if already downloading
            if url in self._active_downloads:
                raise PlatformError(f"Download already in progress for: {url}")
            
            # Get video info with caching
            video_info = await self.get_video_info(url)
            
            # Select best format efficiently
            selected_format = await self._select_best_format_optimized(
                video_info, quality, audio_only, **kwargs
            )
            
            if not selected_format:
                raise PlatformError("No suitable format found for download")
            
            # Execute download with optimizations
            result = await self._execute_optimized_download(
                url, output_path, selected_format, progress_callback, **kwargs
            )
            
            duration = time.time() - start_time
            self._performance_monitor.record_operation('download_video', duration)
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            self._performance_monitor.record_operation('download_video_error', duration)
            raise
    
    async def _select_best_format_optimized(
        self,
        video_info: PlatformVideoInfo,
        quality: Optional[QualityLevel] = None,
        audio_only: bool = False,
        **kwargs
    ) -> Optional[VideoFormat]:
        """Optimized format selection with caching"""
        start_time = time.time()
        
        # Generate cache key for format selection
        cache_key = None
        if self._enable_caching:
            quality_str = quality.value if quality else 'auto'
            cache_key = f"format_{video_info.platform_id}_{quality_str}_{audio_only}"
            
            cached_format = self._optimized_ops.cache.get(cache_key)
            if cached_format:
                self._performance_monitor.record_operation('format_selection_cached', time.time() - start_time)
                return cached_format
        
        # Use base class format selection
        selected_format = await super()._select_best_format(video_info, quality, audio_only, **kwargs)
        
        # Cache result
        if self._enable_caching and cache_key and selected_format:
            self._optimized_ops.cache.set(cache_key, selected_format, ttl=self._cache_ttl)
        
        duration = time.time() - start_time
        self._performance_monitor.record_operation('format_selection', duration)
        
        return selected_format
    
    async def _execute_optimized_download(
        self,
        url: str,
        output_path: Path,
        selected_format: VideoFormat,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
        **kwargs
    ) -> DownloadResult:
        """Execute download with performance optimizations"""
        start_time = time.time()
        
        # Add to active downloads
        self._active_downloads[url] = {
            'start_time': start_time,
            'format': selected_format,
            'output_path': output_path
        }
        
        try:
            # Use enhanced download options
            ydl_opts = await self._build_enhanced_download_options(
                output_path,
                format_id=selected_format.format_id,
                audio_only=kwargs.get('audio_only', False),
                **kwargs
            )
            
            # Execute download with error handling
            success = await self._execute_download_with_ydlp(url, ydl_opts, None)
            
            if success:
                result = DownloadResult(
                    success=True,
                    file_path=str(output_path),
                    format_used=selected_format,
                    file_size=output_path.stat().st_size if output_path.exists() else 0,
                    duration=time.time() - start_time,
                    metadata={
                        'download_method': 'enhanced_optimized',
                        'cache_enabled': self._enable_caching,
                        'concurrent_processing': self._enable_concurrent_processing
                    }
                )
                
                self._add_to_downloads(url, True, str(output_path))
                return result
            else:
                raise PlatformError("Download failed")
                
        except Exception as e:
            logger.error(f"Optimized download failed for {url}: {e}")
            self._add_to_downloads(url, False, str(output_path))
            raise
        finally:
            # Remove from active downloads
            self._active_downloads.pop(url, None)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        base_stats = self._optimized_ops.get_performance_report()
        
        # Add handler-specific stats
        handler_stats = {
            'handler_uptime': time.time() - self._start_time,
            'total_operations': self._operation_count,
            'active_downloads': len(self._active_downloads),
            'performance_config': {
                'caching_enabled': self._enable_caching,
                'cache_ttl': self._cache_ttl,
                'concurrent_processing': self._enable_concurrent_processing,
                'max_concurrent_operations': self._max_concurrent_operations
            },
            'error_monitor_stats': self.get_error_health_status()
        }
        
        return {
            'handler_stats': handler_stats,
            'optimization_stats': base_stats,
            'performance_monitor': self._performance_monitor.get_stats()
        }
    
    def cleanup_resources(self) -> None:
        """Cleanup performance optimization resources"""
        logger.info("Cleaning up enhanced TikTok handler resources")
        
        # Cleanup optimized operations
        self._optimized_ops.cleanup()
        
        # Clear performance monitor
        self._performance_monitor = PerformanceMonitor()
        
        # Reset counters
        self._operation_count = 0
        self._start_time = time.time()
        
        logger.info("Enhanced TikTok handler cleanup completed") 