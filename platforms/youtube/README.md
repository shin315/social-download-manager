# YouTube Platform Handler

A stub implementation of the AbstractPlatformHandler for YouTube video processing in the Social Download Manager v2.0.

## Overview

The `YouTubeHandler` provides a placeholder implementation that follows the platform abstraction pattern, allowing for future integration with YouTube's API while maintaining compatibility with the existing platform factory system.

## Features

### ✅ Currently Implemented (Stub)
- **URL Validation**: Comprehensive regex-based validation for all YouTube URL formats
- **Video ID Extraction**: Extracts video IDs from various YouTube URL structures
- **URL Normalization**: Converts URLs to standard YouTube format
- **Platform Factory Integration**: Automatic registration and discovery
- **Interface Compliance**: Full implementation of AbstractPlatformHandler
- **Stub Video Information**: Returns placeholder video metadata
- **Stub Download Handling**: Returns appropriate "not implemented" responses

### 🚧 Not Yet Implemented
- **Actual Video Download**: Real video file downloading
- **YouTube API Integration**: Authentication and API calls
- **Playlist Support**: Multiple video processing
- **Live Stream Support**: Real-time content handling
- **Quality Selection**: Actual format selection and download
- **Thumbnail Download**: Cover image retrieval

## Installation & Setup

The YouTube handler is automatically registered when the `platforms` module is imported:

```python
import platforms  # This registers YouTubeHandler automatically

# Or import directly
from platforms.youtube import YouTubeHandler
```

## Usage

### Basic Handler Creation

```python
from platforms import create_handler_for_url, PlatformType
from platforms.youtube import YouTubeHandler

# Create handler from URL (recommended)
handler = create_handler_for_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

# Or create directly
handler = YouTubeHandler()

# Or via factory
from platforms import PlatformFactory
factory = PlatformFactory()
handler = factory.create_handler(PlatformType.YOUTUBE)
```

### URL Validation

```python
handler = YouTubeHandler()

# Check if URL is valid
is_valid = handler.is_valid_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
print(f"Valid: {is_valid}")  # Valid: True

# Extract video ID
video_id = handler.extract_video_id("https://youtu.be/dQw4w9WgXcQ")
print(f"Video ID: {video_id}")  # Video ID: dQw4w9WgXcQ

# Normalize URL
normalized = handler.normalize_url("https://youtu.be/dQw4w9WgXcQ")
print(f"Normalized: {normalized}")  
# Normalized: https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

### Getting Video Information (Stub)

```python
import asyncio

async def get_video_info_example():
    handler = YouTubeHandler()
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    # Get video information (returns stub data)
    video_info = await handler.get_video_info(url)
    
    print(f"Title: {video_info.title}")
    print(f"Platform: {video_info.platform.display_name}")
    print(f"Video ID: {video_info.platform_id}")
    print(f"Duration: {video_info.duration}s")
    print(f"Available formats: {len(video_info.formats)}")

# Run the async function
asyncio.run(get_video_info_example())
```

### Platform Capabilities

```python
handler = YouTubeHandler()
capabilities = handler.get_capabilities()

print(f"Supports video: {capabilities.supports_video}")
print(f"Supports audio: {capabilities.supports_audio}")
print(f"Requires auth: {capabilities.requires_auth}")
print(f"Supports playlists: {capabilities.supports_playlists}")
```

### Download Attempt (Stub Behavior)

```python
import asyncio
from pathlib import Path

async def download_example():
    handler = YouTubeHandler()
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    output_path = Path("./downloads")
    
    # Attempt download (will return failure with stub message)
    result = await handler.download_video(url, output_path)
    
    print(f"Success: {result.success}")  # Success: False
    print(f"Error: {result.error_message}")
    # Error: YouTube download not implemented - this is a stub handler

asyncio.run(download_example())
```

## Supported URL Formats

The YouTube handler recognizes and validates the following URL patterns:

### Standard URLs
- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtube.com/watch?v=VIDEO_ID`
- `http://youtube.com/watch?v=VIDEO_ID`

### Short URLs
- `https://youtu.be/VIDEO_ID`
- `https://youtu.be/VIDEO_ID?t=TIMESTAMP`

### Embed URLs
- `https://www.youtube.com/embed/VIDEO_ID`
- `https://youtube.com/embed/VIDEO_ID`

### Mobile URLs
- `https://m.youtube.com/watch?v=VIDEO_ID`

### YouTube Music
- `https://music.youtube.com/watch?v=VIDEO_ID`

### Legacy Format
- `https://www.youtube.com/v/VIDEO_ID`

### With Parameters
- `https://www.youtube.com/watch?v=VIDEO_ID&t=42s`
- `https://www.youtube.com/watch?v=VIDEO_ID&list=PLAYLIST_ID`

## API Reference

### Class: `YouTubeHandler`

Inherits from: `AbstractPlatformHandler`

#### Constructor

```python
def __init__(
    self, 
    platform_type: Optional[PlatformType] = None,
    auth_info: Optional[Any] = None, 
    config: Optional[Dict[str, Any]] = None
)
```

**Parameters:**
- `platform_type`: Platform type (defaults to `PlatformType.YOUTUBE`)
- `auth_info`: Authentication information (not currently used)
- `config`: Configuration dictionary for handler settings

#### Methods

##### `get_capabilities() -> PlatformCapabilities`
Returns the platform capabilities for YouTube.

**Returns:** `PlatformCapabilities` object with YouTube-specific settings

##### `is_valid_url(url: str) -> bool`
Validates if a URL is a supported YouTube URL format.

**Parameters:**
- `url`: URL string to validate

**Returns:** `True` if URL is valid YouTube URL, `False` otherwise

##### `async get_video_info(url: str) -> PlatformVideoInfo`
Retrieves video information for a YouTube URL (stub implementation).

**Parameters:**
- `url`: Valid YouTube video URL

**Returns:** `PlatformVideoInfo` with stub video data

**Raises:**
- `PlatformContentError`: If URL is invalid or unsupported

##### `async download_video(...) -> DownloadResult`
Attempts to download a YouTube video (stub implementation).

**Parameters:**
- `url`: Video URL to download
- `output_path`: Directory to save the file
- `quality`: Desired video quality (optional)
- `audio_only`: Download audio only (optional)
- `**kwargs`: Additional download options

**Returns:** `DownloadResult` indicating stub implementation failure

##### `extract_video_id(url: str) -> Optional[str]`
Extracts the video ID from a YouTube URL.

**Parameters:**
- `url`: YouTube URL

**Returns:** Video ID string or `None` if not found

##### `normalize_url(url: str) -> str`
Converts YouTube URL to standard format.

**Parameters:**
- `url`: YouTube URL in any supported format

**Returns:** Normalized URL in standard YouTube format

##### `get_platform_specific_info() -> Dict[str, Any]`
Returns YouTube-specific platform information.

**Returns:** Dictionary containing platform details and implementation status

## Factory Integration

The YouTube handler is automatically registered with the platform factory:

```python
from platforms import detect_platform, is_url_supported, get_supported_platforms

# Platform detection
platform = detect_platform("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
print(platform)  # PlatformType.YOUTUBE

# URL support checking
supported = is_url_supported("https://youtu.be/dQw4w9WgXcQ")
print(supported)  # True

# List supported platforms
platforms = get_supported_platforms()
print("YouTube" in [p.display_name for p in platforms])  # True
```

## Testing

Comprehensive test coverage is provided:

### Run All Tests
```bash
# URL validation tests
python test_youtube_validation.py

# Stub methods tests
python test_youtube_stub_methods.py

# Factory registration tests
python test_youtube_factory_registration.py

# Comprehensive unit tests
python tests/test_youtube_handler.py
```

### Test Coverage
- **35 total tests** across 4 test suites
- **100% pass rate** for all test scenarios
- **URL validation**: 28 test cases covering valid/invalid URLs
- **Method testing**: 9 test cases for all handler methods
- **Factory integration**: 7 test cases for platform factory
- **Unit tests**: 19 comprehensive test cases

## Configuration

The YouTube handler accepts configuration options:

```python
config = {
    'youtube_api_key': 'your-api-key',  # For future implementation
    'max_retries': 3,
    'request_timeout': 30,
    'output_dir': './downloads'
}

handler = YouTubeHandler(config=config)
```

### Available Configuration Options
- `youtube_api_key`: API key for YouTube Data API (future use)
- `max_retries`: Maximum number of retry attempts
- `request_timeout`: Request timeout in seconds
- `output_dir`: Default output directory for downloads

## Future Implementation

When implementing actual YouTube functionality, consider:

### YouTube Data API v3
- Video metadata retrieval
- Playlist information
- Channel details
- Search functionality

### Download Implementation
- Integration with `yt-dlp` or similar
- Quality selection and format handling
- Progress tracking and callbacks
- Error handling and recovery

### Authentication
- OAuth 2.0 flow for API access
- API key management
- Rate limiting compliance

### Enhanced Features
- Playlist processing
- Live stream handling
- Subtitle/caption download
- Thumbnail extraction

## Error Handling

The handler provides appropriate error types:

```python
from platforms.base import PlatformContentError, PlatformConnectionError

try:
    await handler.get_video_info("invalid-url")
except PlatformContentError as e:
    print(f"Content error: {e}")
except PlatformConnectionError as e:
    print(f"Connection error: {e}")
```

## Dependencies

- **Python 3.8+**
- **platforms.base**: Abstract platform handler interface
- **typing**: Type annotations
- **pathlib**: Path handling
- **asyncio**: Async operation support
- **re**: Regular expression support

## Contributing

When enhancing the YouTube handler:

1. **Maintain Interface Compliance**: Ensure all AbstractPlatformHandler methods remain implemented
2. **Update Tests**: Add test cases for new functionality
3. **Document Changes**: Update this README with new features
4. **Follow Patterns**: Maintain consistency with other platform handlers
5. **Error Handling**: Provide appropriate error types and messages

## License

Part of the Social Download Manager v2.0 project.

---

*This is a stub implementation. Actual YouTube download functionality will be added in future releases.* 