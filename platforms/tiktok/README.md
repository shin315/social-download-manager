# TikTok Platform Handler

The TikTok Platform Handler provides comprehensive support for downloading and extracting metadata from TikTok videos. It's built on the platform handler architecture and offers advanced features including caching, authentication, error handling, and performance optimization.

## Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Basic Usage](#basic-usage)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Error Handling](#error-handling)
- [Performance Features](#performance-features)
- [Examples](#examples)
- [Migration Guide](#migration-guide)

## Quick Start

```python
import asyncio
from platforms.tiktok import TikTokHandler

async def main():
    # Initialize handler
    handler = TikTokHandler()
    
    # Get video information
    url = "https://www.tiktok.com/@user/video/1234567890"
    video_info = await handler.get_video_info(url)
    
    print(f"Title: {video_info.title}")
    print(f"Creator: {video_info.creator}")
    print(f"Views: {video_info.view_count}")
    
    # Download video
    from pathlib import Path
    output_path = Path("downloads/tiktok_video.mp4")
    result = await handler.download_video(url, output_path)
    
    if result.success:
        print(f"Downloaded: {result.file_path}")
    else:
        print(f"Download failed: {result.error}")

asyncio.run(main())
```

## Installation

The TikTok handler is part of the social download manager platform system. Ensure you have the required dependencies:

```bash
pip install yt-dlp
pip install asyncio
pip install pathlib
```

Optional dependencies for enhanced features:
```bash
pip install psutil  # For performance monitoring
pip install aiohttp  # For enhanced HTTP connections
```

## Basic Usage

### Initializing the Handler

```python
from platforms.tiktok import TikTokHandler

# Basic initialization
handler = TikTokHandler()

# With configuration
config = {
    'enable_caching': True,
    'cache_ttl': 1800,  # 30 minutes
    'max_concurrent_operations': 5,
    'enable_concurrent_processing': True
}
handler = TikTokHandler(config=config)

# With authentication info (for future API access)
auth_info = {
    'api_key': 'your_api_key',
    'session_token': 'your_session_token'
}
handler = TikTokHandler(auth_info=auth_info, config=config)
```

### URL Validation

```python
# Check if URL is supported
url = "https://www.tiktok.com/@user/video/1234567890"
if handler.is_valid_url(url):
    print("URL is supported")
else:
    print("URL is not supported")
```

### Getting Video Information

```python
async def get_video_details():
    url = "https://www.tiktok.com/@user/video/1234567890"
    
    try:
        video_info = await handler.get_video_info(url)
        
        # Basic information
        print(f"Title: {video_info.title}")
        print(f"Description: {video_info.description}")
        print(f"Creator: {video_info.creator}")
        print(f"Duration: {video_info.duration} seconds")
        print(f"Upload Date: {video_info.upload_date}")
        
        # Engagement metrics
        print(f"Views: {video_info.view_count:,}")
        print(f"Likes: {video_info.like_count:,}")
        
        # Hashtags and mentions
        metadata = video_info.metadata
        print(f"Hashtags: {metadata.get('hashtags', [])}")
        print(f"Mentions: {metadata.get('mentions', [])}")
        
        # Available formats
        for fmt in video_info.formats:
            print(f"Format: {fmt.quality.value} - {fmt.file_extension}")
            
    except Exception as e:
        print(f"Error getting video info: {e}")
```

### Downloading Videos

```python
from pathlib import Path
from platforms.base import QualityLevel

async def download_video():
    url = "https://www.tiktok.com/@user/video/1234567890"
    output_path = Path("downloads/my_video.mp4")
    
    # Progress callback
    def progress_callback(progress):
        print(f"Progress: {progress.percentage:.1f}% - {progress.downloaded_bytes}/{progress.total_bytes} bytes")
    
    try:
        result = await handler.download_video(
            url=url,
            output_path=output_path,
            quality=QualityLevel.HD,  # Preferred quality
            progress_callback=progress_callback
        )
        
        if result.success:
            print(f"Download completed: {result.file_path}")
            print(f"File size: {result.file_size} bytes")
            print(f"Duration: {result.duration:.2f} seconds")
        else:
            print(f"Download failed: {result.error}")
            
    except Exception as e:
        print(f"Download error: {e}")
```

## API Reference

### TikTokHandler Class

The main class for interacting with TikTok content.

#### Constructor

```python
TikTokHandler(auth_info: Optional[Any] = None, config: Optional[Dict[str, Any]] = None)
```

**Parameters:**
- `auth_info` (Optional[Any]): Authentication information for future API access
- `config` (Optional[Dict[str, Any]]): Configuration dictionary for handler behavior

**Configuration Options:**
- `enable_caching` (bool): Enable caching system (default: True)
- `cache_ttl` (int): Cache time-to-live in seconds (default: 1800)
- `enable_concurrent_processing` (bool): Enable parallel processing (default: True)
- `max_concurrent_operations` (int): Maximum concurrent operations (default: 5)
- `enable_authentication` (bool): Enable authentication features (default: False)
- `session_config` (dict): Session management configuration
- `proxy_config` (dict): Proxy configuration settings

#### Methods

##### get_capabilities()

```python
def get_capabilities() -> PlatformCapabilities
```

Returns the platform's capabilities and supported features.

**Returns:**
- `PlatformCapabilities`: Object describing supported features

**Example:**
```python
caps = handler.get_capabilities()
print(f"Supports download: {caps.supports_download}")
print(f"Supports metadata: {caps.supports_metadata}")
print(f"Supported formats: {caps.supported_formats}")
```

##### is_valid_url()

```python
def is_valid_url(url: str) -> bool
```

Validates if a URL is supported by the TikTok handler.

**Parameters:**
- `url` (str): URL to validate

**Returns:**
- `bool`: True if URL is supported, False otherwise

**Supported URL Patterns:**
- `https://www.tiktok.com/@username/video/123456789`
- `https://vm.tiktok.com/ABC123`
- `https://vt.tiktok.com/ABC123`
- `https://www.tiktok.com/t/ABC123`

##### get_video_info()

```python
async def get_video_info(url: str) -> PlatformVideoInfo
```

Extracts comprehensive metadata from a TikTok video.

**Parameters:**
- `url` (str): TikTok video URL

**Returns:**
- `PlatformVideoInfo`: Comprehensive video information object

**Raises:**
- `PlatformContentError`: Video is private, removed, or unavailable
- `PlatformConnectionError`: Network or API connectivity issues
- `PlatformError`: General processing errors

**Example:**
```python
video_info = await handler.get_video_info(url)
print(f"Video ID: {video_info.platform_id}")
print(f"Title: {video_info.title}")
print(f"Creator: {video_info.creator}")
```

##### download_video()

```python
async def download_video(
    url: str,
    output_path: Path,
    quality: Optional[QualityLevel] = None,
    audio_only: bool = False,
    progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
    **kwargs
) -> DownloadResult
```

Downloads a TikTok video with specified options.

**Parameters:**
- `url` (str): TikTok video URL
- `output_path` (Path): Local file path for downloaded video
- `quality` (Optional[QualityLevel]): Preferred video quality
- `audio_only` (bool): Download audio only (default: False)
- `progress_callback` (Optional[Callable]): Progress update callback
- `**kwargs`: Additional download options

**Returns:**
- `DownloadResult`: Result object with success status and details

**Quality Options:**
- `QualityLevel.HD`: High definition (1080p)
- `QualityLevel.SD`: Standard definition (720p)
- `QualityLevel.LD`: Low definition (480p)
- `QualityLevel.MOBILE`: Mobile quality (360p)
- `QualityLevel.AUDIO_ONLY`: Audio only

**Example:**
```python
result = await handler.download_video(
    url=url,
    output_path=Path("video.mp4"),
    quality=QualityLevel.HD
)
```

### Enhanced Handler (Performance Optimized)

For high-performance applications, use the enhanced handler:

```python
from platforms.tiktok.enhanced_handler import EnhancedTikTokHandler

# Enhanced handler with performance optimizations
enhanced_handler = EnhancedTikTokHandler(config={
    'enable_caching': True,
    'cache_ttl': 3600,  # 1 hour
    'enable_concurrent_processing': True,
    'max_concurrent_operations': 10
})

# Get performance statistics
stats = enhanced_handler.get_performance_stats()
print(f"Cache hit rate: {stats['optimization_stats']['cache_stats']['hit_rate_percent']:.1f}%")
print(f"Operations per second: {stats['performance_monitor']['operations_per_second']:.1f}")
```

## Configuration

### Authentication Configuration

```python
auth_config = {
    'enable_authentication': False,  # Currently not required for public videos
    'session_config': {
        'cookies_file': 'tiktok_cookies.txt',
        'session_timeout': 3600,
        'auto_refresh': True
    },
    'headers_config': {
        'user_agent_rotation': True,
        'rotation_interval': 100,  # requests
        'custom_headers': {
            'Accept-Language': 'en-US,en;q=0.9'
        }
    },
    'proxy_config': {
        'enabled': False,
        'proxy_url': 'http://proxy:8080',
        'rotation_enabled': False
    }
}
```

### Performance Configuration

```python
performance_config = {
    'enable_caching': True,
    'cache_ttl': 1800,  # 30 minutes
    'cache_max_size': 1000,  # entries
    'enable_concurrent_processing': True,
    'max_concurrent_operations': 5,
    'connection_pool_size': 10,
    'request_timeout': 30,  # seconds
    'retry_attempts': 3,
    'retry_backoff': 1.0  # seconds
}
```

### Rate Limiting Configuration

```python
rate_limit_config = {
    'enabled': True,
    'requests_per_minute': 60,
    'burst_limit': 10,
    'cooldown_period': 300,  # 5 minutes
    'adaptive_limiting': True
}
```

## Error Handling

The TikTok handler uses a comprehensive error handling system:

### Exception Types

- **PlatformContentError**: Video is private, removed, or unavailable
- **PlatformConnectionError**: Network connectivity or API issues
- **PlatformError**: General processing errors

### Error Context

Errors include rich context for debugging:

```python
try:
    video_info = await handler.get_video_info(url)
except PlatformContentError as e:
    print(f"Content error: {e}")
    if hasattr(e, 'context'):
        print(f"Operation: {e.context.operation}")
        print(f"Suggestions: {e.context.recovery_options}")
except PlatformConnectionError as e:
    print(f"Connection error: {e}")
    # Implement retry logic
except PlatformError as e:
    print(f"General error: {e}")
```

### Error Recovery

The handler includes automatic error recovery:

```python
# URL normalization recovery
original_url = "https://vm.tiktok.com/ABC123"
# Handler automatically tries alternative URL formats

# Quality degradation recovery
# If HD download fails, automatically tries SD, then LD, etc.
```

## Performance Features

### Caching System

- **Video Info Caching**: 30-minute TTL for video metadata
- **Format Selection Caching**: Cached format choices for quality requests
- **Regex Pattern Caching**: Pre-compiled patterns for text processing
- **Upload Date Caching**: 24-hour cache for date parsing

### Memory Optimization

- **Lazy Loading**: Only loads required metadata fields
- **Batch Processing**: Processes large datasets in manageable chunks
- **String Deduplication**: Removes duplicates while preserving order
- **Memory Monitoring**: Tracks memory usage per operation

### Concurrent Processing

- **Parallel Metadata Extraction**: Simultaneous processing of multiple data fields
- **Concurrent Format Processing**: Parallel analysis of video formats
- **Async Task Pool**: Manages concurrent operations with semaphore limits
- **Connection Pooling**: HTTP connection reuse for efficiency

## Examples

See the [examples directory](examples/) for complete code examples:

- [Basic Usage](examples/basic_usage.py)
- [Advanced Configuration](examples/advanced_config.py)
- [Error Handling](examples/error_handling.py)
- [Performance Optimization](examples/performance_example.py)
- [Batch Processing](examples/batch_processing.py)

## Migration Guide

### From utils/downloader.py

If you're migrating from the old `TikTokDownloader` class:

```python
# Old approach
from utils.downloader import TikTokDownloader
downloader = TikTokDownloader()
video_info = downloader.get_video_info(url)

# New approach
from platforms.tiktok import TikTokHandler
handler = TikTokHandler()
video_info = await handler.get_video_info(url)
```

### Key Changes

1. **Async/Await**: All operations are now asynchronous
2. **Return Types**: `VideoInfo` → `PlatformVideoInfo`
3. **Error Handling**: Qt signals → Platform exceptions
4. **Progress Tracking**: Qt signals → Callback functions
5. **Configuration**: Class parameters → Configuration dictionary

## Testing

Run the test suite to verify functionality:

```bash
# Run all tests
python test_tiktok_comprehensive.py

# Run specific test categories
python test_tiktok_metadata.py
python test_tiktok_download.py
python test_tiktok_error_handling.py

# Run performance tests
python test_tiktok_performance_optimizations.py
```

## Troubleshooting

### Common Issues

1. **"URL not supported"**: Ensure URL is a valid TikTok video URL
2. **"Video is private"**: Video is not publicly accessible
3. **"Network timeout"**: Check internet connection and retry
4. **"Rate limit exceeded"**: Implement delays between requests

### Debug Mode

Enable debug logging for detailed information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Handler operations will now log detailed information
```

### Performance Issues

- Enable caching for repeated operations
- Use enhanced handler for high-performance scenarios
- Monitor memory usage with performance statistics
- Consider reducing concurrent operations if experiencing issues

## Contributing

When contributing to the TikTok handler:

1. Add comprehensive tests for new features
2. Update documentation for API changes
3. Follow the existing code style and patterns
4. Ensure backward compatibility when possible

## License

This TikTok handler is part of the social download manager project. See the main project license for details. 