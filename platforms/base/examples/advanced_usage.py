"""
Advanced Usage Examples for Platform Handler Framework

This module demonstrates advanced patterns and use cases for the
Abstract Platform Handler framework including batch processing,
middleware, custom extractors, and integration patterns.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Callable, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from platforms.base import (
    AbstractPlatformHandler,
    PlatformFactory,
    PlatformVideoInfo,
    DownloadResult,
    DownloadProgress,
    QualityLevel,
    PlatformType,
    metadata_manager,
    MetadataExtractor,
    MetadataField,
    DataTransformers,
    RawMetadata,
    create_handler_for_url,
    detect_platform,
    rate_limited,
    cached
)

logger = logging.getLogger(__name__)


# =====================================================
# Batch Processing Patterns
# =====================================================

class BatchProcessor:
    """Advanced batch processing for multiple videos"""
    
    def __init__(self, max_concurrent: int = 5, rate_limit_per_platform: int = 30):
        self.max_concurrent = max_concurrent
        self.rate_limit_per_platform = rate_limit_per_platform
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.platform_semaphores: Dict[PlatformType, asyncio.Semaphore] = {}
    
    def _get_platform_semaphore(self, platform: PlatformType) -> asyncio.Semaphore:
        """Get rate limiting semaphore for platform"""
        if platform not in self.platform_semaphores:
            self.platform_semaphores[platform] = asyncio.Semaphore(self.rate_limit_per_platform)
        return self.platform_semaphores[platform]
    
    async def process_urls(
        self, 
        urls: List[str],
        operation: str = "info",  # "info", "download", or "both"
        download_dir: Optional[Path] = None,
        quality: Optional[QualityLevel] = None,
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """Process multiple URLs concurrently with rate limiting"""
        
        tasks = []
        for i, url in enumerate(urls):
            task = self._process_single_url(
                url, operation, download_dir, quality, 
                lambda p, idx=i: progress_callback(idx, p) if progress_callback else None
            )
            tasks.append(task)
        
        # Execute with concurrency control
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    'url': urls[i],
                    'success': False,
                    'error': str(result),
                    'error_type': type(result).__name__
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _process_single_url(
        self,
        url: str,
        operation: str,
        download_dir: Optional[Path],
        quality: Optional[QualityLevel],
        progress_callback: Optional[Callable]
    ) -> Dict[str, Any]:
        """Process a single URL with concurrency and rate limiting"""
        
        async with self.semaphore:  # Global concurrency limit
            try:
                # Detect platform and get appropriate semaphore
                platform = detect_platform(url)
                platform_semaphore = self._get_platform_semaphore(platform)
                
                async with platform_semaphore:  # Platform-specific rate limit
                    handler = create_handler_for_url(url)
                    
                    async with handler.managed_lifecycle():
                        result = {
                            'url': url,
                            'platform': platform.value,
                            'success': True
                        }
                        
                        # Get video info
                        if operation in ["info", "both"]:
                            video_info = await handler.get_video_info(url)
                            result['video_info'] = {
                                'title': video_info.title,
                                'creator': video_info.creator,
                                'duration': video_info.duration,
                                'view_count': video_info.view_count,
                                'like_count': video_info.like_count
                            }
                        
                        # Download video
                        if operation in ["download", "both"] and download_dir:
                            filename = f"{platform.value}_{video_info.platform_id or 'unknown'}.mp4"
                            output_path = download_dir / filename
                            
                            download_result = await handler.download_video(
                                url, str(output_path), quality, progress_callback
                            )
                            
                            result['download'] = {
                                'success': download_result.success,
                                'file_path': download_result.file_path,
                                'file_size': download_result.file_size,
                                'error_message': download_result.error_message
                            }
                        
                        return result
                        
            except Exception as e:
                logger.error(f"Failed to process {url}: {e}")
                return {
                    'url': url,
                    'success': False,
                    'error': str(e),
                    'error_type': type(e).__name__
                }


# =====================================================
# Middleware Pattern
# =====================================================

class HandlerMiddleware:
    """Base middleware class for handlers"""
    
    async def before_get_video_info(self, handler, url: str) -> str:
        """Called before get_video_info"""
        return url
    
    async def after_get_video_info(self, handler, url: str, result: PlatformVideoInfo) -> PlatformVideoInfo:
        """Called after get_video_info"""
        return result
    
    async def before_download(self, handler, url: str, output_path: str) -> tuple:
        """Called before download"""
        return url, output_path
    
    async def after_download(self, handler, url: str, result: DownloadResult) -> DownloadResult:
        """Called after download"""
        return result


class LoggingMiddleware(HandlerMiddleware):
    """Middleware that logs all operations"""
    
    def __init__(self, logger_name: str = "platform_handler"):
        self.logger = logging.getLogger(logger_name)
    
    async def before_get_video_info(self, handler, url: str) -> str:
        self.logger.info(f"[{handler.platform_type.value}] Getting video info for: {url}")
        return url
    
    async def after_get_video_info(self, handler, url: str, result: PlatformVideoInfo) -> PlatformVideoInfo:
        self.logger.info(f"[{handler.platform_type.value}] Retrieved info for: {result.title}")
        return result
    
    async def before_download(self, handler, url: str, output_path: str) -> tuple:
        self.logger.info(f"[{handler.platform_type.value}] Starting download to: {output_path}")
        return url, output_path
    
    async def after_download(self, handler, url: str, result: DownloadResult) -> DownloadResult:
        if result.success:
            self.logger.info(f"[{handler.platform_type.value}] Download completed: {result.file_path}")
        else:
            self.logger.error(f"[{handler.platform_type.value}] Download failed: {result.error_message}")
        return result


class MetricsMiddleware(HandlerMiddleware):
    """Middleware that collects metrics"""
    
    def __init__(self):
        self.metrics = {
            'video_info_requests': 0,
            'download_requests': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'total_bytes_downloaded': 0,
            'platform_usage': {}
        }
    
    async def before_get_video_info(self, handler, url: str) -> str:
        self.metrics['video_info_requests'] += 1
        platform = handler.platform_type.value
        if platform not in self.metrics['platform_usage']:
            self.metrics['platform_usage'][platform] = 0
        self.metrics['platform_usage'][platform] += 1
        return url
    
    async def before_download(self, handler, url: str, output_path: str) -> tuple:
        self.metrics['download_requests'] += 1
        return url, output_path
    
    async def after_download(self, handler, url: str, result: DownloadResult) -> DownloadResult:
        if result.success:
            self.metrics['successful_downloads'] += 1
            if result.file_size:
                self.metrics['total_bytes_downloaded'] += result.file_size
        else:
            self.metrics['failed_downloads'] += 1
        return result
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics"""
        return self.metrics.copy()


class MiddlewareHandler:
    """Handler wrapper that applies middleware"""
    
    def __init__(self, handler: AbstractPlatformHandler, middlewares: List[HandlerMiddleware]):
        self.handler = handler
        self.middlewares = middlewares
    
    async def get_video_info(self, url: str) -> PlatformVideoInfo:
        """Get video info with middleware applied"""
        processed_url = url
        
        # Apply before middlewares
        for middleware in self.middlewares:
            processed_url = await middleware.before_get_video_info(self.handler, processed_url)
        
        # Execute original method
        result = await self.handler.get_video_info(processed_url)
        
        # Apply after middlewares
        for middleware in reversed(self.middlewares):
            result = await middleware.after_get_video_info(self.handler, processed_url, result)
        
        return result
    
    async def download_video(self, url: str, output_path: str, **kwargs) -> DownloadResult:
        """Download video with middleware applied"""
        processed_url, processed_path = url, output_path
        
        # Apply before middlewares
        for middleware in self.middlewares:
            processed_url, processed_path = await middleware.before_download(
                self.handler, processed_url, processed_path
            )
        
        # Execute original method
        result = await self.handler.download_video(processed_url, processed_path, **kwargs)
        
        # Apply after middlewares
        for middleware in reversed(self.middlewares):
            result = await middleware.after_download(self.handler, processed_url, result)
        
        return result


# =====================================================
# Custom Metadata Extractors
# =====================================================

class EnhancedMetadataExtractor(MetadataExtractor):
    """Enhanced metadata extractor with additional features"""
    
    def __init__(self, platform_type: PlatformType):
        super().__init__(platform_type)
        self.sentiment_analyzer = None  # Would integrate sentiment analysis
        self.language_detector = None   # Would integrate language detection
    
    async def extract_raw_metadata(self, url: str, **kwargs) -> RawMetadata:
        """Enhanced raw metadata extraction"""
        # This would call the base implementation and add enhancements
        raw_metadata = await super().extract_raw_metadata(url, **kwargs)
        
        # Add sentiment analysis
        description = raw_metadata.get('description', '')
        if description:
            sentiment = await self._analyze_sentiment(description)
            raw_metadata.raw_data['sentiment'] = sentiment
        
        # Add language detection
        title = raw_metadata.get('title', '')
        if title:
            language = await self._detect_language(title)
            raw_metadata.raw_data['language'] = language
        
        return raw_metadata
    
    async def _analyze_sentiment(self, text: str) -> Dict[str, float]:
        """Analyze sentiment of text (mock implementation)"""
        # This would integrate with a real sentiment analysis service
        return {
            'positive': 0.7,
            'negative': 0.2,
            'neutral': 0.1
        }
    
    async def _detect_language(self, text: str) -> str:
        """Detect language of text (mock implementation)"""
        # This would integrate with a real language detection service
        return 'en'
    
    def get_field_mappings(self) -> List[MetadataField]:
        """Enhanced field mappings"""
        base_mappings = super().get_field_mappings()
        
        # Add enhanced fields
        enhanced_mappings = [
            MetadataField(
                source_key='sentiment',
                target_key='sentiment_scores',
                description='Sentiment analysis scores'
            ),
            MetadataField(
                source_key='language',
                target_key='detected_language',
                description='Detected content language'
            )
        ]
        
        return base_mappings + enhanced_mappings


# =====================================================
# Streaming and Real-time Processing
# =====================================================

class StreamingProcessor:
    """Process videos in streaming fashion"""
    
    def __init__(self, batch_size: int = 10, processing_delay: float = 1.0):
        self.batch_size = batch_size
        self.processing_delay = processing_delay
    
    async def process_url_stream(
        self, 
        url_stream: AsyncGenerator[str, None],
        processor_func: Callable[[List[str]], Any]
    ) -> AsyncGenerator[Any, None]:
        """Process URLs from an async stream in batches"""
        
        batch = []
        async for url in url_stream:
            batch.append(url)
            
            if len(batch) >= self.batch_size:
                # Process batch
                result = await processor_func(batch)
                yield result
                
                # Clear batch and add delay
                batch = []
                await asyncio.sleep(self.processing_delay)
        
        # Process remaining URLs
        if batch:
            result = await processor_func(batch)
            yield result


async def url_generator(urls: List[str], delay: float = 0.5) -> AsyncGenerator[str, None]:
    """Generate URLs with delay (simulates real-time input)"""
    for url in urls:
        yield url
        await asyncio.sleep(delay)


# =====================================================
# Integration Patterns
# =====================================================

class PlatformHandlerService:
    """Service layer for platform handlers with caching and error handling"""
    
    def __init__(self):
        self.factory = PlatformFactory()
        self.cache = {}
        self.error_counts = {}
        self.max_errors_per_platform = 5
    
    @cached(ttl=600)
    async def get_video_metadata(self, url: str) -> Dict[str, Any]:
        """Get video metadata with caching"""
        try:
            platform = detect_platform(url)
            
            # Check error count for platform
            if self.error_counts.get(platform, 0) >= self.max_errors_per_platform:
                raise Exception(f"Platform {platform.value} has too many errors")
            
            handler = create_handler_for_url(url)
            async with handler.managed_lifecycle():
                video_info = await handler.get_video_info(url)
                
                # Reset error count on success
                self.error_counts[platform] = 0
                
                return {
                    'success': True,
                    'platform': platform.value,
                    'title': video_info.title,
                    'creator': video_info.creator,
                    'duration': video_info.duration,
                    'view_count': video_info.view_count,
                    'like_count': video_info.like_count,
                    'hashtags': video_info.hashtags,
                    'published_at': video_info.published_at.isoformat() if video_info.published_at else None
                }
                
        except Exception as e:
            platform = detect_platform(url)
            self.error_counts[platform] = self.error_counts.get(platform, 0) + 1
            
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'platform': platform.value if platform else 'unknown'
            }
    
    async def bulk_download(
        self, 
        download_requests: List[Dict[str, Any]],
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """Bulk download with progress tracking"""
        
        processor = BatchProcessor(max_concurrent=3)
        
        urls = [req['url'] for req in download_requests]
        download_dir = Path(download_requests[0].get('download_dir', './downloads'))
        download_dir.mkdir(exist_ok=True)
        
        def batch_progress_callback(idx: int, progress: DownloadProgress):
            if progress_callback:
                overall_progress = {
                    'current_index': idx,
                    'total_items': len(urls),
                    'current_progress': progress.percentage,
                    'overall_percentage': ((idx * 100) + progress.percentage) / len(urls)
                }
                progress_callback(overall_progress)
        
        results = await processor.process_urls(
            urls=urls,
            operation="both",
            download_dir=download_dir,
            quality=QualityLevel.HIGH,
            progress_callback=batch_progress_callback
        )
        
        return results


# =====================================================
# Advanced Usage Examples
# =====================================================

async def example_batch_processing():
    """Example: Batch processing multiple videos"""
    print("=== Batch Processing Example ===")
    
    urls = [
        "https://www.tiktok.com/@user1/video/123",
        "https://www.youtube.com/watch?v=abc123",
        "https://www.tiktok.com/@user2/video/456",
    ]
    
    processor = BatchProcessor(max_concurrent=2)
    
    # Process for info only
    results = await processor.process_urls(urls, operation="info")
    
    print(f"Processed {len(results)} URLs:")
    for result in results:
        if result['success']:
            info = result['video_info']
            print(f"  ✓ {info['title']} by {info['creator']} ({result['platform']})")
        else:
            print(f"  ✗ {result['url']}: {result['error']}")


async def example_middleware_usage():
    """Example: Using middleware with handlers"""
    print("\n=== Middleware Example ===")
    
    # Create handler with middleware
    from platforms.base.examples.tiktok_example import TikTokHandler
    
    handler = TikTokHandler()
    middlewares = [
        LoggingMiddleware("example_logger"),
        MetricsMiddleware()
    ]
    
    middleware_handler = MiddlewareHandler(handler, middlewares)
    
    # Use handler with middleware
    try:
        url = "https://www.tiktok.com/@user/video/123"
        video_info = await middleware_handler.get_video_info(url)
        print(f"Got video info: {video_info.title}")
        
        # Get metrics
        metrics_middleware = middlewares[1]
        metrics = metrics_middleware.get_metrics()
        print(f"Metrics: {metrics}")
        
    except Exception as e:
        print(f"Error: {e}")


async def example_streaming_processing():
    """Example: Streaming URL processing"""
    print("\n=== Streaming Processing Example ===")
    
    urls = [
        "https://www.tiktok.com/@user1/video/123",
        "https://www.tiktok.com/@user2/video/456",
        "https://www.youtube.com/watch?v=abc123",
        "https://www.tiktok.com/@user3/video/789",
    ]
    
    processor = StreamingProcessor(batch_size=2, processing_delay=0.5)
    
    async def process_batch(batch_urls: List[str]) -> Dict[str, Any]:
        """Process a batch of URLs"""
        print(f"Processing batch: {batch_urls}")
        
        # Simple processing - just detect platforms
        platforms = [detect_platform(url).value for url in batch_urls]
        return {
            'batch_size': len(batch_urls),
            'platforms': platforms,
            'timestamp': datetime.now().isoformat()
        }
    
    # Process URL stream
    url_stream = url_generator(urls, delay=0.3)
    
    async for batch_result in processor.process_url_stream(url_stream, process_batch):
        print(f"Batch result: {batch_result}")


async def example_service_integration():
    """Example: Service layer integration"""
    print("\n=== Service Integration Example ===")
    
    service = PlatformHandlerService()
    
    # Get metadata with caching
    url = "https://www.tiktok.com/@user/video/123"
    metadata = await service.get_video_metadata(url)
    
    print(f"Metadata: {metadata}")
    
    # Bulk download example
    download_requests = [
        {
            'url': 'https://www.tiktok.com/@user1/video/123',
            'download_dir': './downloads'
        },
        {
            'url': 'https://www.youtube.com/watch?v=abc123',
            'download_dir': './downloads'
        }
    ]
    
    def progress_callback(progress: Dict[str, Any]):
        print(f"Overall progress: {progress['overall_percentage']:.1f}%")
    
    try:
        results = await service.bulk_download(download_requests, progress_callback)
        print(f"Bulk download results: {len(results)} items")
        
        for result in results:
            if result['success']:
                print(f"  ✓ Downloaded: {result.get('download', {}).get('file_path')}")
            else:
                print(f"  ✗ Failed: {result['error']}")
                
    except Exception as e:
        print(f"Bulk download error: {e}")


async def example_custom_metadata_extractor():
    """Example: Custom metadata extractor"""
    print("\n=== Custom Metadata Extractor Example ===")
    
    # Register enhanced extractor
    enhanced_extractor = EnhancedMetadataExtractor(PlatformType.TIKTOK)
    metadata_manager.register_extractor(enhanced_extractor)
    
    try:
        url = "https://www.tiktok.com/@user/video/123"
        video_info = await metadata_manager.extract_metadata(PlatformType.TIKTOK, url)
        
        print(f"Enhanced metadata:")
        print(f"  Title: {video_info.title}")
        print(f"  Sentiment: {video_info.extra_data.get('sentiment_scores')}")
        print(f"  Language: {video_info.extra_data.get('detected_language')}")
        
    except Exception as e:
        print(f"Enhanced extraction error: {e}")


# =====================================================
# Main Example Runner
# =====================================================

async def main():
    """Run all advanced usage examples"""
    print("🚀 Advanced Platform Handler Framework Examples\n")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        await example_batch_processing()
        await example_middleware_usage()
        await example_streaming_processing()
        await example_service_integration()
        await example_custom_metadata_extractor()
        
        print("\n✅ All examples completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 