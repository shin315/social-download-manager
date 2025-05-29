"""
Testing Utilities for Platform Handlers

This module provides testing utilities, base classes, and helpers for testing
platform handler implementations. Includes mocks, fixtures, and assertion helpers.
"""

import asyncio
import pytest
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass
from datetime import datetime, timezone

from platforms.base import (
    AbstractPlatformHandler,
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
    PlatformCapabilities
)


# =====================================================
# Test Data Models
# =====================================================

@dataclass
class MockVideoData:
    """Mock video data for testing"""
    video_id: str = "test_video_123"
    title: str = "Test Video Title"
    description: str = "Test video description #hashtag @mention"
    creator: str = "Test Creator"
    creator_id: str = "creator_123"
    duration: float = 120.0
    view_count: int = 1000000
    like_count: int = 50000
    comment_count: int = 1500
    thumbnail_url: str = "https://example.com/thumbnail.jpg"
    video_url: str = "https://example.com/video.mp4"
    published_at: datetime = datetime.now(timezone.utc)


@dataclass
class MockAPIResponse:
    """Mock API response for testing"""
    status: int = 200
    data: Dict[str, Any] = None
    headers: Dict[str, str] = None
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}
        if self.headers is None:
            self.headers = {"Content-Type": "application/json"}


# =====================================================
# Base Test Classes
# =====================================================

class BasePlatformHandlerTest:
    """Base test class for platform handlers"""
    
    @pytest.fixture
    async def handler(self):
        """Override this fixture in your test class"""
        raise NotImplementedError("Must implement handler fixture")
    
    @pytest.fixture
    def mock_video_data(self):
        """Default mock video data"""
        return MockVideoData()
    
    @pytest.fixture
    def temp_dir(self):
        """Temporary directory for test files"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)
    
    @pytest.mark.asyncio
    async def test_handler_initialization(self, handler):
        """Test handler can be initialized"""
        assert handler is not None
        assert isinstance(handler, AbstractPlatformHandler)
        assert handler.platform_type in PlatformType
        assert handler.name
    
    @pytest.mark.asyncio
    async def test_get_video_info_interface(self, handler):
        """Test get_video_info method exists and has correct signature"""
        assert hasattr(handler, 'get_video_info')
        assert callable(handler.get_video_info)
    
    @pytest.mark.asyncio
    async def test_download_video_interface(self, handler):
        """Test download_video method exists and has correct signature"""
        assert hasattr(handler, 'download_video')
        assert callable(handler.download_video)
    
    @pytest.mark.asyncio
    async def test_get_capabilities(self, handler):
        """Test handler returns valid capabilities"""
        capabilities = handler.get_capabilities()
        assert isinstance(capabilities, PlatformCapabilities)
        assert capabilities.platform_type == handler.platform_type


class AsyncHandlerTest(BasePlatformHandlerTest):
    """Extended base test class for async handlers with lifecycle"""
    
    @pytest.fixture
    async def initialized_handler(self, handler):
        """Handler that's initialized and cleaned up automatically"""
        await handler.initialize()
        try:
            yield handler
        finally:
            await handler.cleanup()
    
    @pytest.mark.asyncio
    async def test_lifecycle_management(self, handler):
        """Test handler lifecycle management"""
        # Test initialization
        await handler.initialize()
        
        # Handler should be usable after initialization
        assert handler.session is not None if hasattr(handler, 'session') else True
        
        # Test cleanup
        await handler.cleanup()
        
        # Handler should be cleaned up
        assert handler.session is None if hasattr(handler, 'session') else True


# =====================================================
# Mock Helpers
# =====================================================

class MockHTTPSession:
    """Mock HTTP session for testing"""
    
    def __init__(self, responses: Dict[str, MockAPIResponse] = None):
        self.responses = responses or {}
        self.requests = []
        self.closed = False
    
    async def get(self, url: str, **kwargs):
        """Mock GET request"""
        self.requests.append(('GET', url, kwargs))
        response = self.responses.get(url, MockAPIResponse())
        return MockHTTPResponse(response.status, response.data, response.headers)
    
    async def post(self, url: str, **kwargs):
        """Mock POST request"""
        self.requests.append(('POST', url, kwargs))
        response = self.responses.get(url, MockAPIResponse())
        return MockHTTPResponse(response.status, response.data, response.headers)
    
    async def close(self):
        """Mock session close"""
        self.closed = True


class MockHTTPResponse:
    """Mock HTTP response for testing"""
    
    def __init__(self, status: int, data: Dict[str, Any], headers: Dict[str, str]):
        self.status = status
        self._data = data
        self.headers = headers
    
    async def json(self):
        """Return JSON data"""
        return self._data
    
    async def text(self):
        """Return text data"""
        return str(self._data)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    @property
    def content(self):
        """Mock content for streaming"""
        return MockStreamContent(b"mock file content")


class MockStreamContent:
    """Mock streaming content"""
    
    def __init__(self, content: bytes):
        self.content = content
        self.chunk_size = 1024
    
    async def iter_chunked(self, chunk_size: int):
        """Iterate over content in chunks"""
        for i in range(0, len(self.content), chunk_size):
            yield self.content[i:i + chunk_size]


def create_mock_session_with_responses(responses: Dict[str, MockAPIResponse]):
    """Create a mock session with predefined responses"""
    return MockHTTPSession(responses)


# =====================================================
# Test Fixtures and Factories
# =====================================================

@pytest.fixture
def mock_video_info():
    """Create mock PlatformVideoInfo"""
    return PlatformVideoInfo(
        url="https://example.com/video/123",
        platform=PlatformType.CUSTOM,
        platform_id="test_video_123",
        title="Test Video Title",
        description="Test video description",
        thumbnail_url="https://example.com/thumbnail.jpg",
        duration=120.0,
        creator="Test Creator",
        creator_id="creator_123",
        content_type=ContentType.VIDEO,
        hashtags=["test", "video"],
        mentions=["testuser"],
        view_count=1000000,
        like_count=50000,
        comment_count=1500,
        formats=[
            VideoFormat(
                format_id="hd",
                quality=QualityLevel.HIGH,
                url="https://example.com/video_hd.mp4",
                width=1280,
                height=720,
                ext="mp4"
            )
        ]
    )


@pytest.fixture
def mock_download_result():
    """Create mock DownloadResult"""
    return DownloadResult(
        success=True,
        file_path="/tmp/test_video.mp4",
        file_size=1024000,
        duration=120.0
    )


def create_test_video_formats():
    """Create test video formats"""
    return [
        VideoFormat(
            format_id="best",
            quality=QualityLevel.BEST,
            url="https://example.com/video_best.mp4",
            width=1920,
            height=1080,
            ext="mp4"
        ),
        VideoFormat(
            format_id="high",
            quality=QualityLevel.HIGH,
            url="https://example.com/video_hd.mp4",
            width=1280,
            height=720,
            ext="mp4"
        ),
        VideoFormat(
            format_id="medium",
            quality=QualityLevel.MEDIUM,
            url="https://example.com/video_sd.mp4",
            width=640,
            height=480,
            ext="mp4"
        )
    ]


# =====================================================
# Testing Decorators and Helpers
# =====================================================

def mock_platform_handler(platform_type: PlatformType):
    """Decorator to create a mock platform handler for testing"""
    def decorator(test_func):
        async def wrapper(*args, **kwargs):
            handler = MockPlatformHandler(platform_type)
            return await test_func(handler, *args, **kwargs)
        return wrapper
    return decorator


class MockPlatformHandler(AbstractPlatformHandler):
    """Complete mock platform handler for testing"""
    
    def __init__(self, platform_type: PlatformType = PlatformType.CUSTOM):
        super().__init__(platform_type, f"Mock {platform_type.display_name} Handler")
        self.mock_responses = {}
        self.mock_video_data = MockVideoData()
    
    def set_mock_response(self, url: str, response: MockAPIResponse):
        """Set mock response for URL"""
        self.mock_responses[url] = response
    
    def set_mock_video_data(self, video_data: MockVideoData):
        """Set mock video data"""
        self.mock_video_data = video_data
    
    async def get_video_info(self, url: str) -> PlatformVideoInfo:
        """Mock video info extraction"""
        return PlatformVideoInfo(
            url=url,
            platform=self.platform_type,
            platform_id=self.mock_video_data.video_id,
            title=self.mock_video_data.title,
            description=self.mock_video_data.description,
            creator=self.mock_video_data.creator,
            creator_id=self.mock_video_data.creator_id,
            duration=self.mock_video_data.duration,
            view_count=self.mock_video_data.view_count,
            like_count=self.mock_video_data.like_count,
            comment_count=self.mock_video_data.comment_count,
            thumbnail_url=self.mock_video_data.thumbnail_url,
            published_at=self.mock_video_data.published_at,
            formats=create_test_video_formats()
        )
    
    async def download_video(self, url: str, output_path: str, 
                           quality: Optional[QualityLevel] = None,
                           progress_callback: Optional[Callable] = None) -> DownloadResult:
        """Mock video download"""
        # Simulate progress updates
        if progress_callback:
            for i in range(0, 101, 20):
                progress = DownloadProgress(
                    downloaded_bytes=i * 1024,
                    total_bytes=100 * 1024,
                    percentage=float(i),
                    speed_bytes_per_second=1024 * 10,
                    status="downloading" if i < 100 else "completed"
                )
                progress_callback(progress)
                await asyncio.sleep(0.01)  # Small delay for realism
        
        # Create empty file to simulate download
        Path(output_path).touch()
        
        return DownloadResult(
            success=True,
            file_path=output_path,
            file_size=100 * 1024,
            duration=self.mock_video_data.duration
        )


# =====================================================
# Assertion Helpers
# =====================================================

def assert_valid_video_info(video_info: PlatformVideoInfo):
    """Assert that video info is valid"""
    assert isinstance(video_info, PlatformVideoInfo)
    assert video_info.url
    assert video_info.platform in PlatformType
    assert video_info.title
    assert video_info.creator
    assert isinstance(video_info.hashtags, list)
    assert isinstance(video_info.mentions, list)
    assert isinstance(video_info.formats, list)


def assert_valid_download_result(result: DownloadResult):
    """Assert that download result is valid"""
    assert isinstance(result, DownloadResult)
    assert isinstance(result.success, bool)
    
    if result.success:
        assert result.file_path
        assert Path(result.file_path).exists()
        assert result.file_size >= 0
    else:
        assert result.error_message


def assert_valid_video_format(format_obj: VideoFormat):
    """Assert that video format is valid"""
    assert isinstance(format_obj, VideoFormat)
    assert format_obj.format_id
    assert format_obj.quality in QualityLevel
    assert format_obj.ext


async def assert_raises_platform_error(coro, error_type: type = PlatformError):
    """Assert that coroutine raises a platform error"""
    with pytest.raises(error_type):
        await coro


# =====================================================
# Performance Testing Helpers
# =====================================================

class PerformanceTimer:
    """Simple timer for performance testing"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
    
    def start(self):
        """Start timer"""
        import time
        self.start_time = time.time()
    
    def stop(self):
        """Stop timer"""
        import time
        self.end_time = time.time()
    
    @property
    def elapsed(self) -> float:
        """Get elapsed time in seconds"""
        if self.start_time is None or self.end_time is None:
            return 0.0
        return self.end_time - self.start_time
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


async def measure_performance(coro, expected_max_time: float = 5.0):
    """Measure performance of a coroutine"""
    with PerformanceTimer() as timer:
        result = await coro
    
    assert timer.elapsed <= expected_max_time, f"Operation took {timer.elapsed:.2f}s, expected max {expected_max_time}s"
    return result, timer.elapsed


# =====================================================
# Integration Test Helpers
# =====================================================

class TestPlatformFactory:
    """Factory for creating test platform components"""
    
    @staticmethod
    def create_handler(platform_type: PlatformType, **kwargs) -> MockPlatformHandler:
        """Create a mock handler for testing"""
        return MockPlatformHandler(platform_type)
    
    @staticmethod
    def create_video_info(platform_type: PlatformType, **overrides) -> PlatformVideoInfo:
        """Create test video info"""
        defaults = {
            'url': f'https://{platform_type.value}.com/video/test',
            'platform': platform_type,
            'platform_id': 'test_video',
            'title': f'Test {platform_type.display_name} Video',
            'creator': 'Test Creator',
            'formats': create_test_video_formats()
        }
        defaults.update(overrides)
        return PlatformVideoInfo(**defaults)
    
    @staticmethod
    def create_api_responses(platform_type: PlatformType) -> Dict[str, MockAPIResponse]:
        """Create standard API responses for platform"""
        base_url = f"https://api.{platform_type.value}.com"
        
        return {
            f"{base_url}/video/test": MockAPIResponse(
                status=200,
                data={
                    'id': 'test_video',
                    'title': f'Test {platform_type.display_name} Video',
                    'description': 'Test video description',
                    'author': {
                        'name': 'Test Creator',
                        'id': 'test_creator'
                    },
                    'stats': {
                        'views': 1000000,
                        'likes': 50000,
                        'comments': 1500
                    },
                    'duration': 120,
                    'thumbnail_url': 'https://example.com/thumb.jpg'
                }
            ),
            f"{base_url}/video/notfound": MockAPIResponse(
                status=404,
                data={'error': 'Video not found'}
            ),
            f"{base_url}/video/ratelimited": MockAPIResponse(
                status=429,
                data={'error': 'Rate limited'},
                headers={'Retry-After': '60'}
            )
        }


# =====================================================
# Example Test Class
# =====================================================

class ExamplePlatformHandlerTest(AsyncHandlerTest):
    """Example test class showing how to test a platform handler"""
    
    @pytest.fixture
    async def handler(self):
        """Create handler for testing"""
        return MockPlatformHandler(PlatformType.CUSTOM)
    
    @pytest.mark.asyncio
    async def test_get_video_info_success(self, initialized_handler, mock_video_data):
        """Test successful video info extraction"""
        initialized_handler.set_mock_video_data(mock_video_data)
        
        url = "https://example.com/video/123"
        video_info = await initialized_handler.get_video_info(url)
        
        assert_valid_video_info(video_info)
        assert video_info.title == mock_video_data.title
        assert video_info.creator == mock_video_data.creator
        assert video_info.duration == mock_video_data.duration
    
    @pytest.mark.asyncio
    async def test_download_video_success(self, initialized_handler, temp_dir):
        """Test successful video download"""
        url = "https://example.com/video/123"
        output_path = temp_dir / "test_video.mp4"
        
        progress_updates = []
        def progress_callback(progress: DownloadProgress):
            progress_updates.append(progress)
        
        result = await initialized_handler.download_video(
            url, str(output_path), progress_callback=progress_callback
        )
        
        assert_valid_download_result(result)
        assert result.success
        assert len(progress_updates) > 0
        assert progress_updates[-1].percentage == 100.0
    
    @pytest.mark.asyncio
    async def test_download_performance(self, initialized_handler, temp_dir):
        """Test download performance"""
        url = "https://example.com/video/123"
        output_path = temp_dir / "test_video.mp4"
        
        result, elapsed = await measure_performance(
            initialized_handler.download_video(url, str(output_path)),
            expected_max_time=1.0
        )
        
        assert result.success
        print(f"Download took {elapsed:.3f} seconds")


if __name__ == "__main__":
    # Example of running tests
    pytest.main([__file__, "-v"]) 