# Abstract Platform Handler Framework

A comprehensive, production-ready framework for implementing social media platform handlers with support for video downloading, metadata extraction, and content processing.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Quick Start](#quick-start)
4. [Core Components](#core-components)
5. [Implementation Guide](#implementation-guide)
6. [Error Handling](#error-handling)
7. [Lifecycle Management](#lifecycle-management)
8. [Authentication](#authentication)
9. [Metadata Extraction](#metadata-extraction)
10. [Factory Pattern](#factory-pattern)
11. [Common Utilities](#common-utilities)
12. [Examples](#examples)
13. [Testing](#testing)
14. [Advanced Usage](#advanced-usage)
15. [Performance](#performance)
16. [Configuration](#configuration)
17. [Troubleshooting](#troubleshooting)
18. [Migration Guide](#migration-guide)
19. [Contributing](#contributing)

## Overview

The Abstract Platform Handler Framework provides a unified interface for implementing social media platform integrations. It offers:

- **Async-first design** with full type safety
- **Comprehensive error handling** with platform-specific exceptions
- **Lifecycle management** with resource cleanup
- **Rate limiting and caching** out of the box
- **Metadata extraction** with customizable field mapping
- **Authentication framework** supporting multiple auth types
- **Factory pattern** for handler discovery and instantiation
- **Testing utilities** with mocks and fixtures

## Architecture

```
platforms/base/
├── __init__.py           # Module exports
├── enums.py             # Platform types and enums
├── models.py            # Data models and DTOs
├── platform_handler.py  # Abstract base handler
├── common.py            # Utilities (rate limiting, caching, etc.)
├── factory.py           # Factory pattern implementation
├── lifecycle.py         # Lifecycle and resource management
├── authentication.py   # Authentication framework
├── metadata.py          # Metadata extraction framework
└── examples/            # Implementation examples and templates
    ├── tiktok_example.py     # Complete TikTok implementation
    ├── youtube_example.py    # Complete YouTube implementation
    ├── custom_platform.py   # Template for new platforms
    ├── testing_utils.py     # Testing utilities and helpers
    └── advanced_usage.py    # Advanced patterns and examples
```

## 🏗️ Architecture Overview

The Abstract Platform Handler framework follows Clean Architecture principles and provides:

- **Abstract Interfaces**: Standardized contracts for all platform implementations
- **Common functionality**: Shared utilities like rate limiting, caching, and retry logic
- **Error Handling**: Comprehensive exception hierarchy with context and recovery
- **Lifecycle Management**: Resource management, connection pooling, and cleanup
- **Authentication**: Multi-provider auth system with token management
- **Metadata Extraction**: Normalized data handling across platforms
- **Factory Pattern**: Automatic platform detection and handler creation

## 📁 Module Structure

```
platforms/base/
├── README.md                 # This documentation
├── __init__.py              # Module exports
├── enums.py                 # Platform enums and constants
├── models.py                # Data models and structures
├── platform_handler.py     # Abstract handler interface
├── common.py                # Shared utilities and mixins
├── factory.py               # Platform factory and registry
├── lifecycle.py             # Resource and lifecycle management
├── authentication.py       # Authentication framework
├── metadata.py              # Metadata extraction system
└── examples/                # Example implementations
    ├── tiktok_example.py    # TikTok handler example
    ├── youtube_example.py   # YouTube handler example
    └── custom_platform.py   # Custom platform template
```

## 🚀 Quick Start

### 1. Basic Platform Handler Implementation

```python
from platforms.base import (
    AbstractPlatformHandler,
    PlatformType,
    PlatformVideoInfo,
    DownloadResult,
    PlatformHandler
)

@PlatformHandler(
    platform_type=PlatformType.CUSTOM,
    url_patterns=[r'https?://custom\.com/.*']
)
class CustomPlatformHandler(AbstractPlatformHandler):
    """Custom platform handler implementation"""
    
    def __init__(self):
        super().__init__(
            platform_type=PlatformType.CUSTOM,
            name="Custom Platform"
        )
    
    async def get_video_info(self, url: str) -> PlatformVideoInfo:
        """Extract video information from URL"""
        # Your implementation here
        return PlatformVideoInfo(
            url=url,
            platform=self.platform_type,
            title="Custom Video",
            # ... other fields
        )
    
    async def download_video(self, url: str, output_path: str) -> DownloadResult:
        """Download video from platform"""
        # Your implementation here
        return DownloadResult(
            success=True,
            file_path=output_path,
            # ... other fields
        )
```

### 2. Using the Factory Pattern

```python
from platforms.base import create_handler_for_url, detect_platform

# Automatic platform detection
url = "https://www.tiktok.com/@user/video/123"
platform = detect_platform(url)
print(f"Detected platform: {platform.display_name}")

# Create handler for URL
handler = create_handler_for_url(url)
video_info = await handler.get_video_info(url)
```

### 3. Metadata Extraction

```python
from platforms.base import metadata_manager

# Extract normalized metadata
platform = PlatformType.TIKTOK
url = "https://www.tiktok.com/@user/video/123"

video_info = await metadata_manager.extract_metadata(platform, url)
print(f"Title: {video_info.title}")
print(f"Creator: {video_info.creator}")
print(f"Views: {video_info.view_count}")
```

## 🔧 Core Components

### PlatformType Enum

Supported platforms with auto-detection:

```python
class PlatformType(Enum):
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    TWITCH = "twitch"
```

### Data Models

#### PlatformVideoInfo
Normalized video information across all platforms:

```python
@dataclass
class PlatformVideoInfo:
    url: str
    platform: PlatformType
    platform_id: Optional[str] = None
    title: str = ""
    description: str = ""
    thumbnail_url: str = ""
    duration: Optional[float] = None
    creator: str = ""
    creator_id: Optional[str] = None
    creator_avatar: Optional[str] = None
    content_type: ContentType = ContentType.VIDEO
    hashtags: List[str] = field(default_factory=list)
    mentions: List[str] = field(default_factory=list)
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    share_count: Optional[int] = None
    published_at: Optional[datetime] = None
    formats: List[VideoFormat] = field(default_factory=list)
    extra_data: Dict[str, Any] = field(default_factory=dict)
```

#### VideoFormat
Video format specifications:

```python
@dataclass
class VideoFormat:
    format_id: str
    quality: QualityLevel
    ext: str = "mp4"
    url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    filesize: Optional[int] = None
    fps: Optional[float] = None
    vcodec: Optional[str] = None
    acodec: Optional[str] = None
    has_watermark: bool = False
    is_live: bool = False
```

### Abstract Handler Interface

```python
class AbstractPlatformHandler(ABC):
    """Abstract base class for platform handlers"""
    
    @abstractmethod
    async def get_video_info(self, url: str) -> PlatformVideoInfo:
        """Extract video information from URL"""
        pass
    
    @abstractmethod
    async def download_video(self, url: str, output_path: str, 
                           quality: Optional[QualityLevel] = None,
                           progress_callback: Optional[Callable] = None) -> DownloadResult:
        """Download video from platform"""
        pass
    
    async def search_content(self, query: str, limit: int = 10) -> List[PlatformVideoInfo]:
        """Search for content on platform (optional)"""
        raise NotImplementedError("Search not supported")
    
    async def get_user_videos(self, user_id: str, limit: int = 10) -> List[PlatformVideoInfo]:
        """Get videos from user profile (optional)"""
        raise NotImplementedError("User videos not supported")
```

## 🛡️ Error Handling

### Exception Hierarchy

```python
PlatformError                    # Base exception
├── PlatformConnectionError      # Network/connection issues
├── PlatformAuthError           # Authentication failures
├── PlatformContentError        # Content not found/unavailable
├── PlatformRateLimitError      # Rate limiting (with retry_after)
├── MetadataError               # Metadata extraction issues
│   ├── MetadataExtractionError
│   ├── MetadataValidationError
│   └── MetadataTransformationError
└── AuthenticationError         # Auth framework issues
    ├── TokenExpiredError
    ├── InvalidCredentialsError
    ├── RefreshTokenError
    └── AuthFlowError
```

### Error Handling Best Practices

```python
from platforms.base import PlatformError, with_retry

class MyPlatformHandler(AbstractPlatformHandler):
    
    @with_retry(max_attempts=3, backoff_factor=2.0)
    async def get_video_info(self, url: str) -> PlatformVideoInfo:
        try:
            # Your implementation
            return video_info
        except Exception as e:
            # Convert to appropriate platform error
            raise self._handle_error(e, url=url)
    
    def _handle_error(self, error: Exception, **context) -> PlatformError:
        """Convert generic errors to platform-specific errors"""
        if "network" in str(error).lower():
            return PlatformConnectionError(
                "Network connection failed",
                platform=self.platform_type,
                **context
            )
        elif "not found" in str(error).lower():
            return PlatformContentError(
                "Content not found",
                platform=self.platform_type,
                **context
            )
        else:
            return PlatformError(
                f"Unexpected error: {error}",
                platform=self.platform_type,
                **context
            )
```

## 🔄 Lifecycle Management

### Resource Management

```python
from platforms.base import LifecycleMixin

class MyPlatformHandler(AbstractPlatformHandler, LifecycleMixin):
    
    async def initialize(self):
        """Initialize handler resources"""
        await super().initialize()
        # Your initialization code
        self.session = aiohttp.ClientSession()
    
    async def cleanup(self):
        """Clean up handler resources"""
        if hasattr(self, 'session'):
            await self.session.close()
        await super().cleanup()
    
    async def get_video_info(self, url: str) -> PlatformVideoInfo:
        async with self.managed_lifecycle():
            # Handler automatically initialized and cleaned up
            async with self.session.get(url) as response:
                # Your implementation
                pass
```

### Connection Pooling

```python
from platforms.base import ConnectionPool

# Global connection pool (automatically configured)
pool = ConnectionPool(max_connections=100, max_connections_per_host=30)

# Use in your handler
class MyPlatformHandler(AbstractPlatformHandler):
    
    async def get_video_info(self, url: str) -> PlatformVideoInfo:
        session = await pool.get_session()
        try:
            async with session.get(url) as response:
                # Your implementation
                pass
        finally:
            await pool.return_session(session)
```

## 🔐 Authentication

### OAuth Integration

```python
from platforms.base import AuthenticationManager, OAuthProvider

# Register OAuth provider
auth_manager = AuthenticationManager()
oauth_provider = OAuthProvider(
    client_id="your_client_id",
    client_secret="your_client_secret",
    authorization_url="https://platform.com/oauth/authorize",
    token_url="https://platform.com/oauth/token",
    scopes=["read", "download"]
)

auth_manager.register_provider(PlatformType.CUSTOM, AuthType.OAUTH, oauth_provider)

# Use in handler
class MyPlatformHandler(AbstractPlatformHandler):
    
    async def get_video_info(self, url: str) -> PlatformVideoInfo:
        # Get authenticated session
        auth_info = await auth_manager.authenticate(
            platform=self.platform_type,
            auth_type=AuthType.OAUTH
        )
        
        # Use auth_info.token for API calls
        headers = {"Authorization": f"Bearer {auth_info.token}"}
        # Your implementation
```

### API Key Authentication

```python
from platforms.base import APIKeyAuthProvider

# Simple API key auth
api_key_provider = APIKeyAuthProvider(api_key="your_api_key")
auth_manager.register_provider(PlatformType.CUSTOM, AuthType.API_KEY, api_key_provider)
```

## 📊 Metadata Extraction

### Custom Metadata Extractor

```python
from platforms.base import MetadataExtractor, MetadataField, DataTransformers

class CustomMetadataExtractor(MetadataExtractor):
    
    def __init__(self):
        super().__init__(PlatformType.CUSTOM)
    
    async def extract_raw_metadata(self, url: str, **kwargs) -> RawMetadata:
        # Extract raw data from platform API
        raw_data = await self._fetch_api_data(url)
        
        return RawMetadata(
            platform=self.platform_type,
            url=url,
            raw_data=raw_data,
            source="api"
        )
    
    def get_field_mappings(self) -> List[MetadataField]:
        return [
            MetadataField(
                source_key='video.title',
                target_key='title',
                required=True,
                transformer=lambda x: DataTransformers.sanitize_text(x, 500),
                description='Video title'
            ),
            MetadataField(
                source_key='video.stats.views',
                target_key='view_count',
                transformer=DataTransformers.to_int,
                description='View count'
            ),
            # ... more field mappings
        ]

# Register the extractor
from platforms.base import metadata_manager
metadata_manager.register_extractor(CustomMetadataExtractor())
```

### Data Transformers

Built-in transformers for common data types:

```python
from platforms.base import DataTransformers

# Number parsing with K/M/B suffixes
views = DataTransformers.to_int("1.5M")  # Returns 1500000

# Duration parsing
duration = DataTransformers.parse_duration("PT3M33S")  # Returns 213.0 seconds
duration2 = DataTransformers.parse_duration("3:33")    # Returns 213.0 seconds

# Text extraction
hashtags = DataTransformers.extract_hashtags("#funny #viral #trending")
# Returns ['funny', 'viral', 'trending']

mentions = DataTransformers.extract_mentions("Thanks @user1 and @user2!")
# Returns ['user1', 'user2']

# Text sanitization
clean_text = DataTransformers.sanitize_text("Title\x00\x01with\x02control\x03chars", 50)
# Returns "Title with control chars"
```

## 🏭 Factory Pattern

### Platform Registration

```python
from platforms.base import register_platform

# Register with decorator
@PlatformHandler(
    platform_type=PlatformType.CUSTOM,
    url_patterns=[r'https?://custom\.com/.*'],
    capabilities=['download', 'metadata', 'search']
)
class CustomHandler(AbstractPlatformHandler):
    # Implementation
    pass

# Manual registration
register_platform(
    platform_type=PlatformType.CUSTOM,
    handler_class=CustomHandler,
    url_patterns=[r'https?://custom\.com/.*']
)
```

### Auto-Discovery

```python
from platforms.base import discover_handlers

# Discover handlers in modules
discover_handlers('platforms.handlers')  # Scans all handlers in module
```

## 🔧 Common Utilities

### Rate Limiting

```python
from platforms.base import rate_limited, RateLimiter

# Decorator approach
@rate_limited(requests_per_minute=60, requests_per_hour=1000)
async def api_call():
    # Your API call here
    pass

# Manual rate limiter
rate_limiter = RateLimiter()
rate_limiter.add_bucket("api_calls", 60, 60)  # 60 requests per 60 seconds

async def my_function():
    await rate_limiter.acquire("api_calls")
    # Your code here
```

### Caching

```python
from platforms.base import cached, SimpleCache

# Decorator approach
@cached(ttl=300)  # Cache for 5 minutes
async def expensive_operation(url: str):
    # Your expensive operation
    return result

# Manual cache
cache = SimpleCache(default_ttl=300)
await cache.set("key", value)
value = await cache.get("key")
```

### Retry Logic

```python
from platforms.base import with_retry, retry_async

# Decorator approach
@with_retry(max_attempts=3, backoff_factor=2.0, exceptions=[ConnectionError])
async def unreliable_api_call():
    # Your API call here
    pass

# Manual retry
async def my_function():
    return await retry_async(
        unreliable_api_call,
        max_attempts=3,
        backoff_factor=2.0
    )
```

## 📈 Performance Optimization

### Connection Pooling Best Practices

```python
# Use global connection pool
from platforms.base import ConnectionPool

# Configure pool size based on your needs
pool = ConnectionPool(
    max_connections=100,          # Total connections
    max_connections_per_host=30,  # Per host limit
    timeout=30.0,                 # Connection timeout
    keepalive_timeout=30.0        # Keep-alive timeout
)
```

### Memory Management

```python
class OptimizedHandler(AbstractPlatformHandler):
    
    def __init__(self):
        super().__init__(PlatformType.CUSTOM, "Optimized Handler")
        # Use weak references for caches
        self._cache = weakref.WeakValueDictionary()
    
    async def cleanup(self):
        """Clean up resources"""
        self._cache.clear()
        await super().cleanup()
```

## 🧪 Testing

### Handler Testing Template

```python
import pytest
from platforms.base import PlatformVideoInfo, DownloadResult
from .my_handler import MyPlatformHandler

class TestMyPlatformHandler:
    
    @pytest.fixture
    async def handler(self):
        handler = MyPlatformHandler()
        await handler.initialize()
        yield handler
        await handler.cleanup()
    
    @pytest.mark.asyncio
    async def test_get_video_info(self, handler):
        url = "https://platform.com/video/123"
        video_info = await handler.get_video_info(url)
        
        assert isinstance(video_info, PlatformVideoInfo)
        assert video_info.url == url
        assert video_info.platform == handler.platform_type
        assert video_info.title
        assert video_info.creator
    
    @pytest.mark.asyncio
    async def test_download_video(self, handler, tmp_path):
        url = "https://platform.com/video/123"
        output_path = tmp_path / "video.mp4"
        
        result = await handler.download_video(url, str(output_path))
        
        assert isinstance(result, DownloadResult)
        assert result.success
        assert result.file_path == str(output_path)
        assert output_path.exists()
    
    @pytest.mark.asyncio
    async def test_error_handling(self, handler):
        with pytest.raises(PlatformContentError):
            await handler.get_video_info("https://platform.com/invalid")
```

### Metadata Testing

```python
import pytest
from platforms.base import metadata_manager, PlatformType

@pytest.mark.asyncio
async def test_metadata_extraction():
    url = "https://platform.com/video/123"
    platform = PlatformType.CUSTOM
    
    video_info = await metadata_manager.extract_metadata(platform, url)
    
    assert video_info.platform == platform
    assert video_info.url == url
    assert video_info.title
    assert isinstance(video_info.view_count, int)
```

## 🔍 Debugging

### Logging Configuration

```python
import logging

# Configure platform-specific logging
logging.getLogger("platforms.base").setLevel(logging.INFO)
logging.getLogger("platforms.base.tiktok").setLevel(logging.DEBUG)
logging.getLogger("platforms.base.metadata").setLevel(logging.DEBUG)

# In your handler
class MyHandler(AbstractPlatformHandler):
    
    def __init__(self):
        super().__init__(PlatformType.CUSTOM, "My Handler")
        self.logger = logging.getLogger(f"platforms.{self.platform_type.value}")
    
    async def get_video_info(self, url: str) -> PlatformVideoInfo:
        self.logger.info(f"Extracting video info from: {url}")
        try:
            # Your implementation
            self.logger.debug(f"Extracted metadata: {metadata}")
            return video_info
        except Exception as e:
            self.logger.error(f"Failed to extract video info: {e}")
            raise
```

### Error Context

```python
try:
    video_info = await handler.get_video_info(url)
except PlatformError as e:
    print(f"Platform: {e.platform}")
    print(f"URL: {e.url}")
    print(f"Error: {e}")
    print(f"Original error: {e.__cause__}")
```

## 🚀 Deployment

### Production Configuration

```python
from platforms.base import PlatformFactory, ConnectionPool

# Configure for production
connection_pool = ConnectionPool(
    max_connections=500,
    max_connections_per_host=100,
    timeout=60.0,
    keepalive_timeout=60.0
)

# Set up factory with production handlers
factory = PlatformFactory()
factory.discover_handlers('myapp.platforms')

# Configure authentication
from platforms.base import AuthenticationManager
auth_manager = AuthenticationManager()
# Register your auth providers
```

### Environment Variables

```bash
# Rate limiting
PLATFORM_RATE_LIMIT_PER_MINUTE=60
PLATFORM_RATE_LIMIT_PER_HOUR=1000

# Connection pooling
PLATFORM_MAX_CONNECTIONS=500
PLATFORM_MAX_CONNECTIONS_PER_HOST=100

# Authentication
TIKTOK_API_KEY=your_api_key
YOUTUBE_CLIENT_ID=your_client_id
YOUTUBE_CLIENT_SECRET=your_client_secret

# Logging
PLATFORM_LOG_LEVEL=INFO
```

## 📚 Migration Guide

### From Legacy Platform Handlers

1. **Inherit from AbstractPlatformHandler**:
```python
# Old
class TikTokHandler:
    def get_video_info(self, url):
        # Implementation

# New
class TikTokHandler(AbstractPlatformHandler):
    def __init__(self):
        super().__init__(PlatformType.TIKTOK, "TikTok Handler")
    
    async def get_video_info(self, url: str) -> PlatformVideoInfo:
        # Updated implementation with async/await
```

2. **Update Method Signatures**:
```python
# Old
def download_video(self, url, path):
    return {"success": True, "path": path}

# New
async def download_video(self, url: str, output_path: str, 
                        quality: Optional[QualityLevel] = None,
                        progress_callback: Optional[Callable] = None) -> DownloadResult:
    return DownloadResult(success=True, file_path=output_path)
```

3. **Use New Error Handling**:
```python
# Old
raise Exception("Video not found")

# New
raise PlatformContentError(
    "Video not found",
    platform=self.platform_type,
    url=url
)
```

4. **Register with Factory**:
```python
@PlatformHandler(
    platform_type=PlatformType.TIKTOK,
    url_patterns=[r'https?://(?:www\.)?tiktok\.com/.*']
)
class TikTokHandler(AbstractPlatformHandler):
    # Implementation
```

## 🔗 Integration Examples

### Flask Web App

```python
from flask import Flask, request, jsonify
from platforms.base import create_handler_for_url, detect_platform

app = Flask(__name__)

@app.route('/video-info', methods=['POST'])
async def get_video_info():
    url = request.json['url']
    
    try:
        handler = create_handler_for_url(url)
        video_info = await handler.get_video_info(url)
        
        return jsonify({
            'success': True,
            'platform': video_info.platform.value,
            'title': video_info.title,
            'creator': video_info.creator,
            'duration': video_info.duration,
            'view_count': video_info.view_count
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400
```

### Django Integration

```python
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import asyncio
from platforms.base import create_handler_for_url

@csrf_exempt
async def video_info_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        url = data['url']
        
        try:
            handler = create_handler_for_url(url)
            video_info = await handler.get_video_info(url)
            
            return JsonResponse({
                'success': True,
                'data': {
                    'platform': video_info.platform.value,
                    'title': video_info.title,
                    'creator': video_info.creator,
                    # ... other fields
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
```

## 📋 Best Practices

### 1. Error Handling
- Always use platform-specific exceptions
- Provide meaningful error context
- Implement retry logic for transient errors
- Log errors with appropriate levels

### 2. Performance
- Use connection pooling
- Implement caching for expensive operations
- Use rate limiting to respect platform limits
- Clean up resources properly

### 3. Security
- Never log sensitive information (tokens, passwords)
- Use secure credential storage
- Validate all input data
- Implement proper authentication

### 4. Maintainability
- Document your handlers thoroughly
- Use type hints consistently
- Write comprehensive tests
- Follow the established patterns

### 5. Extensibility
- Design for future platform additions
- Use the metadata extraction system
- Register handlers with the factory
- Implement optional methods when appropriate

## 🆘 Troubleshooting

### Common Issues

#### Handler Not Found
```python
# Issue: Platform not detected
try:
    handler = create_handler_for_url(url)
except ValueError as e:
    print(f"Platform not supported: {e}")

# Solution: Check URL patterns and registration
from platforms.base import get_supported_platforms
print(f"Supported platforms: {get_supported_platforms()}")
```

#### Authentication Errors
```python
# Issue: Token expired
try:
    video_info = await handler.get_video_info(url)
except TokenExpiredError:
    # Refresh token automatically handled by AuthenticationManager
    await auth_manager.refresh_token(platform, auth_type)
    video_info = await handler.get_video_info(url)
```

#### Rate Limiting
```python
# Issue: Rate limit exceeded
try:
    await handler.get_video_info(url)
except PlatformRateLimitError as e:
    print(f"Rate limited. Retry after: {e.retry_after} seconds")
    await asyncio.sleep(e.retry_after)
    # Retry the operation
```

#### Memory Issues
```python
# Issue: Memory leaks
# Solution: Proper cleanup
async with handler.managed_lifecycle():
    # Handler automatically cleaned up
    video_info = await handler.get_video_info(url)
```

## 📞 Support

For additional support:

1. Check the example implementations in `platforms/base/examples/`
2. Review the test cases for usage patterns
3. Enable debug logging for detailed operation traces
4. Consult the source code documentation

## 🔄 Changelog

### v2.0.0 (Current)
- Complete rewrite with async/await support
- Added comprehensive error handling
- Implemented lifecycle management
- Added authentication framework
- Created metadata extraction system
- Factory pattern for automatic platform detection
- Production-ready performance optimizations

---

*This documentation is part of the Social Download Manager v2.0 Abstract Platform Handler framework.*

## Examples

The framework includes comprehensive examples and templates:

### Complete Platform Implementations

#### TikTok Handler Example
```python
# platforms/base/examples/tiktok_example.py
from platforms.base.examples.tiktok_example import TikTokHandler

handler = TikTokHandler()
await handler.initialize()

video_info = await handler.get_video_info("https://www.tiktok.com/@user/video/123")
print(f"Title: {video_info.title}")
```

#### YouTube Handler Example
```python
# platforms/base/examples/youtube_example.py
from platforms.base.examples.youtube_example import YouTubeHandler

handler = YouTubeHandler(api_key="your_api_key")
await handler.initialize()

videos = await handler.search_content("python programming", limit=5)
for video in videos:
    print(f"Found: {video.title}")
```

### Custom Platform Template

Use the custom platform template to implement new platform handlers:

```python
# Copy platforms/base/examples/custom_platform.py
# Replace 'Custom' with your platform name
# Update URL patterns, API endpoints, and metadata mapping
# Implement platform-specific logic

from platforms.base.examples.custom_platform import CustomPlatformHandler

# Your implementation here
```

### Advanced Usage Patterns

```python
# platforms/base/examples/advanced_usage.py

# Batch processing
from platforms.base.examples.advanced_usage import BatchProcessor

processor = BatchProcessor(max_concurrent=5)
results = await processor.process_urls(urls, operation="info")

# Middleware pattern
from platforms.base.examples.advanced_usage import LoggingMiddleware, MiddlewareHandler

middleware_handler = MiddlewareHandler(handler, [LoggingMiddleware()])
video_info = await middleware_handler.get_video_info(url)

# Streaming processing
from platforms.base.examples.advanced_usage import StreamingProcessor

processor = StreamingProcessor(batch_size=10)
async for batch_result in processor.process_url_stream(url_stream, process_func):
    print(f"Processed batch: {batch_result}")
```

## Testing

### Using Testing Utilities

```python
# platforms/base/examples/testing_utils.py
from platforms.base.examples.testing_utils import (
    BasePlatformHandlerTest,
    AsyncHandlerTest,
    MockPlatformHandler,
    assert_valid_video_info
)

class MyPlatformHandlerTest(AsyncHandlerTest):
    @pytest.fixture
    async def handler(self):
        return MyPlatformHandler()
    
    @pytest.mark.asyncio
    async def test_video_info_extraction(self, initialized_handler):
        video_info = await initialized_handler.get_video_info("https://example.com/video/123")
        assert_valid_video_info(video_info)
```

### Mock Handlers for Testing

```python
from platforms.base.examples.testing_utils import MockPlatformHandler, MockVideoData

# Create mock handler
handler = MockPlatformHandler(PlatformType.CUSTOM)
handler.set_mock_video_data(MockVideoData(
    title="Test Video",
    creator="Test Creator",
    duration=120.0
))

# Use in tests
video_info = await handler.get_video_info("https://example.com/video/123")
assert video_info.title == "Test Video"
```

### Performance Testing

```python
from platforms.base.examples.testing_utils import measure_performance, PerformanceTimer

# Measure operation performance
result, elapsed = await measure_performance(
    handler.get_video_info(url),
    expected_max_time=2.0
)

# Manual timing
with PerformanceTimer() as timer:
    await some_operation()
print(f"Operation took {timer.elapsed:.3f} seconds")
```

## Advanced Usage

### Batch Processing

Process multiple URLs concurrently with rate limiting:

```python
from platforms.base.examples.advanced_usage import BatchProcessor

processor = BatchProcessor(
    max_concurrent=5,
    rate_limit_per_platform=30
)

# Process multiple URLs
results = await processor.process_urls(
    urls=["https://platform1.com/video/1", "https://platform2.com/video/2"],
    operation="both",  # "info", "download", or "both"
    download_dir=Path("./downloads"),
    quality=QualityLevel.HIGH,
    progress_callback=lambda idx, progress: print(f"Video {idx}: {progress.percentage}%")
)

for result in results:
    if result['success']:
        print(f"✓ {result['video_info']['title']}")
    else:
        print(f"✗ {result['url']}: {result['error']}")
```

### Middleware Pattern

Add cross-cutting concerns like logging and metrics:

```python
from platforms.base.examples.advanced_usage import (
    LoggingMiddleware,
    MetricsMiddleware,
    MiddlewareHandler
)

# Create handler with middleware
handler = create_handler_for_url(url)
middlewares = [
    LoggingMiddleware("my_app"),
    MetricsMiddleware()
]

middleware_handler = MiddlewareHandler(handler, middlewares)

# Use handler normally - middleware is applied automatically
video_info = await middleware_handler.get_video_info(url)

# Get metrics
metrics = middlewares[1].get_metrics()
print(f"Total requests: {metrics['video_info_requests']}")
```

### Custom Metadata Extractors

Extend metadata extraction with custom fields:

```python
from platforms.base.examples.advanced_usage import EnhancedMetadataExtractor
from platforms.base import metadata_manager

# Register enhanced extractor
enhanced_extractor = EnhancedMetadataExtractor(PlatformType.TIKTOK)
metadata_manager.register_extractor(enhanced_extractor)

# Extract enhanced metadata
video_info = await metadata_manager.extract_metadata(PlatformType.TIKTOK, url)
print(f"Sentiment: {video_info.extra_data.get('sentiment_scores')}")
print(f"Language: {video_info.extra_data.get('detected_language')}")
```

### Streaming Processing

Process URLs in real-time streams:

```python
from platforms.base.examples.advanced_usage import StreamingProcessor, url_generator

async def process_batch(urls: List[str]) -> Dict[str, Any]:
    # Your batch processing logic
    return {"processed": len(urls), "timestamp": datetime.now()}

# Create processor
processor = StreamingProcessor(batch_size=10, processing_delay=1.0)

# Process streaming URLs
url_stream = url_generator(urls, delay=0.5)
async for result in processor.process_url_stream(url_stream, process_batch):
    print(f"Batch processed: {result}")
```

### Service Layer Integration

Integrate with service architectures:

```python
from platforms.base.examples.advanced_usage import PlatformHandlerService

service = PlatformHandlerService()

# Get metadata with caching and error handling
metadata = await service.get_video_metadata(url)
if metadata['success']:
    print(f"Title: {metadata['title']}")

# Bulk download with progress tracking
download_requests = [
    {'url': 'https://platform1.com/video/1', 'download_dir': './downloads'},
    {'url': 'https://platform2.com/video/2', 'download_dir': './downloads'}
]

def progress_callback(progress):
    print(f"Overall progress: {progress['overall_percentage']:.1f}%")

results = await service.bulk_download(download_requests, progress_callback)
```

## File Overview

### Core Framework Files

- **`enums.py`**: Platform types, content types, quality levels, and error types
- **`models.py`**: Data models for video info, formats, download results, and capabilities
- **`platform_handler.py`**: Abstract base handler with lifecycle and error handling
- **`common.py`**: Rate limiting, caching, retry logic, and utility functions
- **`factory.py`**: Factory pattern for handler registration and instantiation
- **`lifecycle.py`**: Advanced lifecycle management and resource pooling
- **`authentication.py`**: Comprehensive authentication framework
- **`metadata.py`**: Metadata extraction with field mapping and transformation

### Example and Template Files

- **`examples/tiktok_example.py`**: Complete TikTok handler implementation (600+ lines)
- **`examples/youtube_example.py`**: Complete YouTube handler implementation (500+ lines)
- **`examples/custom_platform.py`**: Template for implementing new platforms (500+ lines)
- **`examples/testing_utils.py`**: Comprehensive testing utilities and helpers (400+ lines)
- **`examples/advanced_usage.py`**: Advanced patterns and integration examples (600+ lines)

### Documentation

- **`README.md`**: This comprehensive documentation (1000+ lines)

## Quick Implementation Checklist

To implement a new platform handler:

1. **Copy the template**: Start with `examples/custom_platform.py`
2. **Update platform info**: Change `PlatformType`, URL patterns, and API endpoints
3. **Implement core methods**: `get_video_info()` and `download_video()`
4. **Add metadata mapping**: Update `_parse_video_metadata()` for your platform's API response
5. **Configure rate limits**: Adjust `@rate_limited` decorators for platform limits
6. **Add authentication**: Implement platform-specific auth if required
7. **Write tests**: Use `testing_utils.py` base classes and fixtures
8. **Register handler**: Use `@PlatformHandler` decorator for auto-registration

## Performance Considerations

- **Connection Pooling**: Reuse HTTP sessions across requests
- **Rate Limiting**: Respect platform rate limits to avoid blocking
- **Caching**: Cache video metadata to reduce API calls
- **Batch Processing**: Process multiple URLs concurrently
- **Streaming**: Use streaming downloads for large files
- **Resource Management**: Properly cleanup resources with lifecycle management

## Best Practices

1. **Always use lifecycle management** with `async with handler.managed_lifecycle()`
2. **Handle errors gracefully** with platform-specific exception types
3. **Respect rate limits** and implement proper backoff strategies
4. **Cache metadata** to improve performance and reduce API usage
5. **Use type hints** for better code quality and IDE support
6. **Test thoroughly** using the provided testing utilities
7. **Document platform-specific quirks** in handler docstrings
8. **Follow async patterns** throughout your implementation

## Troubleshooting

### Common Issues

1. **Rate Limiting**: Reduce concurrent requests or increase delays
2. **Authentication Failures**: Check API keys and authentication setup
3. **Network Timeouts**: Increase timeout values or implement retry logic
4. **Memory Usage**: Use streaming for large downloads
5. **Platform Changes**: Monitor platform API changes and update handlers

### Debug Tools

```python
import logging

# Enable debug logging
logging.getLogger('platforms.base').setLevel(logging.DEBUG)

# Use performance timer
from platforms.base.examples.testing_utils import PerformanceTimer

with PerformanceTimer() as timer:
    result = await handler.get_video_info(url)
print(f"Operation took {timer.elapsed:.3f} seconds")
```

## Contributing

1. Follow the existing code style and patterns
2. Add comprehensive tests for new features
3. Update documentation for API changes
4. Use type hints throughout
5. Follow async patterns consistently
6. Add examples for new functionality

## License

This framework is designed for educational and development purposes. Ensure compliance with platform terms of service when using in production. 