"""
Common functionality for platform handlers

This module provides shared behaviors and utilities that can be used across
all platform implementations, including rate limiting, retry logic, 
connection pooling, and data formatting.
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, Callable, TypeVar, List, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
import hashlib
import re

from .enums import PlatformConstants, QualityLevel
from .models import VideoFormat, PlatformVideoInfo


T = TypeVar('T')
logger = logging.getLogger(__name__)


# =====================================================
# Rate Limiting
# =====================================================

@dataclass
class RateLimitBucket:
    """Rate limit bucket for tracking requests"""
    requests: int = 0
    window_start: float = field(default_factory=time.time)
    max_requests: int = PlatformConstants.DEFAULT_RATE_LIMIT_REQUESTS
    window_duration: int = PlatformConstants.DEFAULT_RATE_LIMIT_PERIOD  # seconds
    
    def reset_if_needed(self) -> None:
        """Reset bucket if window has expired"""
        current_time = time.time()
        if current_time - self.window_start >= self.window_duration:
            self.requests = 0
            self.window_start = current_time
    
    def can_make_request(self) -> bool:
        """Check if we can make another request"""
        self.reset_if_needed()
        return self.requests < self.max_requests
    
    def add_request(self) -> None:
        """Add a request to the bucket"""
        self.reset_if_needed()
        self.requests += 1
    
    def time_until_reset(self) -> float:
        """Get seconds until bucket resets"""
        current_time = time.time()
        return max(0, (self.window_start + self.window_duration) - current_time)


class RateLimiter:
    """Rate limiter for managing API requests"""
    
    def __init__(self):
        self._buckets: Dict[str, RateLimitBucket] = {}
    
    def get_bucket(
        self, 
        key: str, 
        max_requests: int = PlatformConstants.DEFAULT_RATE_LIMIT_REQUESTS,
        window_duration: int = PlatformConstants.DEFAULT_RATE_LIMIT_PERIOD
    ) -> RateLimitBucket:
        """Get or create rate limit bucket for key"""
        if key not in self._buckets:
            self._buckets[key] = RateLimitBucket(
                max_requests=max_requests,
                window_duration=window_duration
            )
        return self._buckets[key]
    
    async def wait_if_needed(self, key: str, **bucket_kwargs) -> None:
        """Wait if rate limit would be exceeded"""
        bucket = self.get_bucket(key, **bucket_kwargs)
        
        if not bucket.can_make_request():
            wait_time = bucket.time_until_reset()
            if wait_time > 0:
                logger.info(f"Rate limit reached for {key}, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
        
        bucket.add_request()


# Global rate limiter instance
_rate_limiter = RateLimiter()


def rate_limited(
    key_func: Optional[Callable[..., str]] = None,
    max_requests: int = PlatformConstants.DEFAULT_RATE_LIMIT_REQUESTS,
    window_duration: int = PlatformConstants.DEFAULT_RATE_LIMIT_PERIOD
):
    """
    Decorator to add rate limiting to async functions
    
    Args:
        key_func: Function to generate rate limit key from args
        max_requests: Maximum requests per window
        window_duration: Window duration in seconds
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate rate limit key
            if key_func:
                rate_key = key_func(*args, **kwargs)
            else:
                rate_key = f"{func.__module__}.{func.__name__}"
            
            # Apply rate limiting
            await _rate_limiter.wait_if_needed(
                rate_key,
                max_requests=max_requests,
                window_duration=window_duration
            )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# =====================================================
# Retry Logic
# =====================================================

@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_attempts: int = PlatformConstants.DEFAULT_MAX_RETRIES
    base_delay: float = PlatformConstants.DEFAULT_RETRY_DELAY
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on_exceptions: tuple = (Exception,)
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number"""
        if attempt <= 0:
            return 0
        
        # Exponential backoff
        delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        delay = min(delay, self.max_delay)
        
        # Add jitter to prevent thundering herd
        if self.jitter:
            import random
            delay = delay * (0.5 + random.random() * 0.5)
        
        return delay


async def retry_async(
    func: Callable[..., T],
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs
) -> T:
    """
    Retry an async function with exponential backoff
    
    Args:
        func: Async function to retry
        *args: Arguments for the function
        config: Retry configuration
        **kwargs: Keyword arguments for the function
        
    Returns:
        Result of the function
        
    Raises:
        Exception: Last exception if all retries failed
    """
    if config is None:
        config = RetryConfig()
    
    last_exception = None
    
    for attempt in range(1, config.max_attempts + 1):
        try:
            return await func(*args, **kwargs)
        except config.retry_on_exceptions as e:
            last_exception = e
            
            if attempt == config.max_attempts:
                logger.error(f"All {config.max_attempts} retry attempts failed for {func.__name__}")
                break
            
            delay = config.get_delay(attempt)
            logger.warning(
                f"Attempt {attempt}/{config.max_attempts} failed for {func.__name__}: {e}. "
                f"Retrying in {delay:.1f}s"
            )
            
            if delay > 0:
                await asyncio.sleep(delay)
    
    raise last_exception


def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator to add retry logic to async functions
    
    Args:
        config: Retry configuration
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_async(func, *args, config=config, **kwargs)
        return wrapper
    return decorator


# =====================================================
# Connection Pooling & Session Management
# =====================================================

class ConnectionPool:
    """Simple connection pool for HTTP sessions"""
    
    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        self._sessions: Dict[str, Any] = {}  # Store aiohttp sessions
        self._session_locks: Dict[str, asyncio.Lock] = {}
    
    async def get_session(self, key: str = "default") -> Any:
        """Get or create an aiohttp session"""
        if key not in self._session_locks:
            self._session_locks[key] = asyncio.Lock()
        
        async with self._session_locks[key]:
            if key not in self._sessions:
                import aiohttp
                connector = aiohttp.TCPConnector(
                    limit=self.max_connections,
                    ttl_dns_cache=300,
                    use_dns_cache=True
                )
                self._sessions[key] = aiohttp.ClientSession(
                    connector=connector,
                    timeout=aiohttp.ClientTimeout(
                        total=PlatformConstants.DEFAULT_READ_TIMEOUT
                    )
                )
        
        return self._sessions[key]
    
    async def close_session(self, key: str = "default") -> None:
        """Close a specific session"""
        if key in self._sessions:
            await self._sessions[key].close()
            del self._sessions[key]
            
        if key in self._session_locks:
            del self._session_locks[key]
    
    async def close_all(self) -> None:
        """Close all sessions"""
        for session in self._sessions.values():
            await session.close()
        self._sessions.clear()
        self._session_locks.clear()


# Global connection pool
_connection_pool = ConnectionPool()


async def get_http_session(key: str = "default"):
    """Get HTTP session from global pool"""
    return await _connection_pool.get_session(key)


# =====================================================
# Data Formatting & Validation
# =====================================================

class DataFormatter:
    """Utilities for formatting and validating data"""
    
    @staticmethod
    def sanitize_filename(filename: str, max_length: int = 255) -> str:
        """
        Sanitize filename for filesystem compatibility
        
        Args:
            filename: Original filename
            max_length: Maximum filename length
            
        Returns:
            Sanitized filename
        """
        # Remove invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Remove control characters
        filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)
        
        # Trim whitespace and dots
        filename = filename.strip(' .')
        
        # Ensure not empty
        if not filename:
            filename = "untitled"
        
        # Truncate if too long
        if len(filename) > max_length:
            name, ext = Path(filename).stem, Path(filename).suffix
            max_name_length = max_length - len(ext)
            filename = name[:max_name_length] + ext
        
        return filename
    
    @staticmethod
    def normalize_url(url: str) -> str:
        """
        Normalize URL by removing tracking parameters and fragments
        
        Args:
            url: Original URL
            
        Returns:
            Normalized URL
        """
        # Remove common tracking parameters
        tracking_params = [
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            'fbclid', 'gclid', 'ref', 'source', '_source'
        ]
        
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        # Remove tracking parameters
        filtered_params = {
            k: v for k, v in query_params.items() 
            if k not in tracking_params
        }
        
        # Rebuild query string
        new_query = urlencode(filtered_params, doseq=True)
        
        # Rebuild URL without fragment
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            ''  # Remove fragment
        ))
    
    @staticmethod
    def format_duration(seconds: Optional[float]) -> str:
        """
        Format duration in seconds to human-readable string
        
        Args:
            seconds: Duration in seconds
            
        Returns:
            Formatted duration string
        """
        if not seconds or seconds <= 0:
            return "Unknown"
        
        hours, remainder = divmod(int(seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    @staticmethod
    def format_file_size(bytes_size: Optional[int]) -> str:
        """
        Format file size in bytes to human-readable string
        
        Args:
            bytes_size: Size in bytes
            
        Returns:
            Formatted size string
        """
        if not bytes_size or bytes_size <= 0:
            return "Unknown"
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024
        
        return f"{bytes_size:.1f} PB"
    
    @staticmethod
    def extract_hashtags(text: str) -> List[str]:
        """
        Extract hashtags from text
        
        Args:
            text: Text to extract hashtags from
            
        Returns:
            List of hashtags (without # symbol)
        """
        if not text:
            return []
        
        hashtag_pattern = r'#(\w+)'
        hashtags = re.findall(hashtag_pattern, text)
        return [tag.lower() for tag in hashtags]
    
    @staticmethod
    def extract_mentions(text: str) -> List[str]:
        """
        Extract mentions from text
        
        Args:
            text: Text to extract mentions from
            
        Returns:
            List of mentions (without @ symbol)
        """
        if not text:
            return []
        
        mention_pattern = r'@(\w+)'
        mentions = re.findall(mention_pattern, text)
        return [mention.lower() for mention in mentions]


# =====================================================
# Quality & Format Utilities
# =====================================================

class FormatUtils:
    """Utilities for working with video formats and quality"""
    
    @staticmethod
    def sort_formats_by_quality(formats: List[VideoFormat]) -> List[VideoFormat]:
        """
        Sort formats by quality (best first)
        
        Args:
            formats: List of video formats
            
        Returns:
            Sorted list of formats
        """
        return sorted(formats, key=lambda f: f.quality.height, reverse=True)
    
    @staticmethod
    def filter_formats_by_extension(
        formats: List[VideoFormat], 
        extensions: List[str]
    ) -> List[VideoFormat]:
        """
        Filter formats by file extension
        
        Args:
            formats: List of video formats
            extensions: List of allowed extensions (e.g., ['mp4', 'webm'])
            
        Returns:
            Filtered list of formats
        """
        return [f for f in formats if f.ext.lower() in [ext.lower() for ext in extensions]]
    
    @staticmethod
    def get_best_format_for_quality(
        formats: List[VideoFormat],
        target_quality: QualityLevel,
        prefer_no_watermark: bool = True
    ) -> Optional[VideoFormat]:
        """
        Get the best format for a target quality
        
        Args:
            formats: Available formats
            target_quality: Desired quality level
            prefer_no_watermark: Prefer formats without watermark
            
        Returns:
            Best matching format or None
        """
        if not formats:
            return None
        
        # Filter by watermark preference
        candidates = formats
        if prefer_no_watermark:
            no_watermark = [f for f in formats if not f.has_watermark]
            if no_watermark:
                candidates = no_watermark
        
        # Find exact match first
        exact_matches = [f for f in candidates if f.quality == target_quality]
        if exact_matches:
            return FormatUtils.sort_formats_by_quality(exact_matches)[0]
        
        # Find closest quality
        target_height = target_quality.height
        candidates_with_distance = [
            (f, abs(f.quality.height - target_height))
            for f in candidates
        ]
        
        # Sort by distance and then by quality
        candidates_with_distance.sort(key=lambda x: (x[1], -x[0].quality.height))
        return candidates_with_distance[0][0] if candidates_with_distance else None


# =====================================================
# Caching
# =====================================================

@dataclass
class CacheEntry:
    """Cache entry with expiration"""
    data: Any
    created_at: datetime
    expires_at: Optional[datetime] = None
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if self.expires_at is None:
            return False
        return datetime.now() >= self.expires_at


class SimpleCache:
    """Simple in-memory cache with TTL support"""
    
    def __init__(self, default_ttl: int = 300):  # 5 minutes default
        self._cache: Dict[str, CacheEntry] = {}
        self._default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        if entry.is_expired():
            del self._cache[key]
            return None
        
        return entry.data
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        if ttl is None:
            ttl = self._default_ttl
        
        expires_at = None
        if ttl > 0:
            expires_at = datetime.now() + timedelta(seconds=ttl)
        
        self._cache[key] = CacheEntry(
            data=value,
            created_at=datetime.now(),
            expires_at=expires_at
        )
    
    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cache entries"""
        self._cache.clear()
    
    def cleanup_expired(self) -> int:
        """Remove expired entries and return count removed"""
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        return len(expired_keys)


# Global cache instance
_cache = SimpleCache()


def cached(ttl: int = 300, key_func: Optional[Callable[..., str]] = None):
    """
    Decorator to add caching to functions
    
    Args:
        ttl: Time to live in seconds
        key_func: Function to generate cache key from args
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Create key from function name and args hash
                args_str = str(args) + str(sorted(kwargs.items()))
                args_hash = hashlib.md5(args_str.encode()).hexdigest()[:8]
                cache_key = f"{func.__module__}.{func.__name__}:{args_hash}"
            
            # Try to get from cache
            cached_result = _cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            _cache.set(cache_key, result, ttl)
            logger.debug(f"Cache set for {cache_key}")
            
            return result
        return wrapper
    return decorator


# =====================================================
# Common Mixins
# =====================================================

class RateLimitedMixin:
    """Mixin to add rate limiting functionality to handlers"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rate_limiter = RateLimiter()
    
    async def _rate_limited_request(self, key: str, func: Callable, *args, **kwargs):
        """Make a rate-limited request"""
        capabilities = self.get_capabilities()
        await self._rate_limiter.wait_if_needed(
            key,
            max_requests=capabilities.rate_limit_requests,
            window_duration=capabilities.rate_limit_period
        )
        return await func(*args, **kwargs)


class CachedMixin:
    """Mixin to add caching functionality to handlers"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache = SimpleCache()
    
    def _get_cache_key(self, prefix: str, *args) -> str:
        """Generate cache key"""
        args_str = ":".join(str(arg) for arg in args)
        return f"{self._platform_type.value}:{prefix}:{args_str}"
    
    async def _cached_request(
        self, 
        key: str, 
        func: Callable, 
        ttl: int = 300,
        *args, 
        **kwargs
    ):
        """Make a cached request"""
        cached_result = self._cache.get(key)
        if cached_result is not None:
            return cached_result
        
        result = await func(*args, **kwargs)
        self._cache.set(key, result, ttl)
        return result 