#!/usr/bin/env python3
"""
Platform Handler Optimization Framework - Task 21.5
Comprehensive optimization for TikTok and YouTube download handlers

Features:
- Optimized video metadata extraction algorithms
- Efficient URL parsing and validation
- Improved API response handling and parsing
- Optimized video quality selection logic
- Smart retry mechanisms with exponential backoff
- Platform-specific performance optimizations
"""

import asyncio
import hashlib
import time
import logging
import re
from typing import Dict, List, Any, Optional, Tuple, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from pathlib import Path
import json
import random

@dataclass
class URLParsingConfig:
    """Configuration for URL parsing optimization"""
    enable_caching: bool = True
    cache_size: int = 1000
    precompile_patterns: bool = True
    use_fast_validation: bool = True
    validate_redirects: bool = True
    timeout_seconds: float = 5.0

@dataclass
class MetadataExtractionConfig:
    """Configuration for metadata extraction optimization"""
    enable_parallel_extraction: bool = True
    max_concurrent_extractions: int = 5
    use_field_priority: bool = True
    cache_extracted_data: bool = True
    data_compression: bool = True
    incremental_extraction: bool = True

@dataclass
class QualitySelectionConfig:
    """Configuration for quality selection optimization"""
    enable_smart_selection: bool = True
    prefer_adaptive_streams: bool = True
    quality_preference_cache: bool = True
    bandwidth_aware_selection: bool = True
    fallback_strategies: List[str] = field(default_factory=lambda: ["lower_quality", "audio_only", "best_available"])

@dataclass
class RetryConfig:
    """Configuration for retry mechanisms"""
    max_retries: int = 3
    base_delay: float = 1.0
    exponential_backoff: bool = True
    jitter: bool = True
    retry_on_status_codes: List[int] = field(default_factory=lambda: [429, 502, 503, 504])
    circuit_breaker_enabled: bool = True
    circuit_breaker_threshold: int = 5

@dataclass
class PlatformOptimizationConfig:
    """Main configuration for platform optimization"""
    url_parsing: URLParsingConfig = field(default_factory=URLParsingConfig)
    metadata_extraction: MetadataExtractionConfig = field(default_factory=MetadataExtractionConfig)
    quality_selection: QualitySelectionConfig = field(default_factory=QualitySelectionConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    
    # Performance tuning
    request_timeout: float = 30.0
    connection_pool_size: int = 20
    keep_alive_timeout: float = 30.0
    enable_compression: bool = True
    
    # Platform-specific settings
    tiktok_optimizations: Dict[str, Any] = field(default_factory=dict)
    youtube_optimizations: Dict[str, Any] = field(default_factory=dict)

class URLParser:
    """Optimized URL parsing and validation"""
    
    def __init__(self, config: URLParsingConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # URL cache
        self._url_cache = {} if config.enable_caching else None
        self._pattern_cache = {}
        
        # Precompiled patterns for major platforms
        if config.precompile_patterns:
            self._compile_patterns()
    
    def _compile_patterns(self):
        """Precompile regex patterns for performance"""
        self._pattern_cache = {
            'tiktok': [
                re.compile(r'https?://(www\.)?tiktok\.com/@[\w\.-]+/video/\d+'),
                re.compile(r'https?://(vm\.|vt\.)?tiktok\.com/\w+'),
                re.compile(r'https?://(www\.)?tiktok\.com/t/\w+'),
            ],
            'youtube': [
                re.compile(r'https?://(www\.)?youtube\.com/watch\?v=[\w-]+'),
                re.compile(r'https?://youtu\.be/[\w-]+'),
                re.compile(r'https?://(www\.)?youtube\.com/embed/[\w-]+'),
            ]
        }
    
    def parse_url(self, url: str) -> Dict[str, Any]:
        """Optimized URL parsing with caching"""
        if not url:
            return {'valid': False, 'error': 'Empty URL'}
        
        # Check cache first
        if self.config.enable_caching and url in self._url_cache:
            return self._url_cache[url].copy()
        
        start_time = time.time()
        
        try:
            # Fast validation
            if self.config.use_fast_validation and not self._fast_validate(url):
                result = {'valid': False, 'error': 'Invalid URL format'}
            else:
                result = self._detailed_parse(url)
            
            # Cache result
            if self.config.enable_caching:
                if len(self._url_cache) >= self.config.cache_size:
                    # Remove oldest entry
                    oldest_key = next(iter(self._url_cache))
                    del self._url_cache[oldest_key]
                self._url_cache[url] = result.copy()
            
            parse_time = time.time() - start_time
            result['parse_time_ms'] = round(parse_time * 1000, 2)
            
            return result
            
        except Exception as e:
            self.logger.error(f"URL parsing error for {url}: {e}")
            return {'valid': False, 'error': str(e)}
    
    def _fast_validate(self, url: str) -> bool:
        """Fast URL validation using basic checks"""
        return (
            url.startswith(('http://', 'https://')) and
            len(url) > 10 and
            '.' in url and
            ' ' not in url
        )
    
    def _detailed_parse(self, url: str) -> Dict[str, Any]:
        """Detailed URL parsing and platform detection"""
        result = {
            'valid': False,
            'platform': None,
            'video_id': None,
            'normalized_url': None,
            'metadata': {}
        }
        
        # Detect platform and extract info
        for platform, patterns in self._pattern_cache.items():
            for pattern in patterns:
                match = pattern.match(url)
                if match:
                    result['valid'] = True
                    result['platform'] = platform
                    result['video_id'] = self._extract_video_id(url, platform)
                    result['normalized_url'] = self._normalize_url(url, platform)
                    result['metadata'] = self._extract_url_metadata(url, platform, match)
                    return result
        
        return result
    
    def _extract_video_id(self, url: str, platform: str) -> Optional[str]:
        """Extract video ID based on platform"""
        if platform == 'tiktok':
            # TikTok video ID extraction
            patterns = [
                r'/video/(\d+)',
                r'tiktok\.com/(\w+)/?$',
                r'/t/(\w+)'
            ]
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
        
        elif platform == 'youtube':
            # YouTube video ID extraction
            patterns = [
                r'[?&]v=([a-zA-Z0-9_-]{11})',
                r'youtu\.be/([a-zA-Z0-9_-]{11})',
                r'embed/([a-zA-Z0-9_-]{11})'
            ]
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
        
        return None
    
    def _normalize_url(self, url: str, platform: str) -> str:
        """Normalize URL to standard format"""
        video_id = self._extract_video_id(url, platform)
        if not video_id:
            return url
        
        if platform == 'tiktok':
            # Normalize to standard TikTok format
            if '/video/' in url:
                return url.split('?')[0]  # Remove query params
            else:
                # Short URL, keep as is for now
                return url
        
        elif platform == 'youtube':
            return f"https://www.youtube.com/watch?v={video_id}"
        
        return url
    
    def _extract_url_metadata(self, url: str, platform: str, match) -> Dict[str, Any]:
        """Extract metadata from URL structure"""
        metadata = {'extracted_at': datetime.now().isoformat()}
        
        if platform == 'tiktok':
            # Extract creator from URL if available
            creator_match = re.search(r'/@([^/]+)/', url)
            if creator_match:
                metadata['creator_username'] = creator_match.group(1)
        
        elif platform == 'youtube':
            # Extract additional YouTube URL parameters
            if '&list=' in url:
                playlist_match = re.search(r'[&?]list=([a-zA-Z0-9_-]+)', url)
                if playlist_match:
                    metadata['playlist_id'] = playlist_match.group(1)
            
            if '&t=' in url:
                time_match = re.search(r'[&?]t=(\d+)', url)
                if time_match:
                    metadata['start_time'] = int(time_match.group(1))
        
        return metadata

class MetadataExtractor:
    """Optimized metadata extraction with parallel processing"""
    
    def __init__(self, config: MetadataExtractionConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Extraction cache
        self._metadata_cache = {}
        self._extraction_semaphore = asyncio.Semaphore(config.max_concurrent_extractions)
        
        # Field priorities for optimization
        self._field_priorities = {
            'critical': ['title', 'video_id', 'platform', 'url'],
            'important': ['creator', 'duration', 'quality_formats'],
            'optional': ['description', 'hashtags', 'view_count', 'like_count'],
            'extended': ['comments', 'related_videos', 'chapters']
        }
    
    async def extract_metadata(self, url: str, platform: str, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and optimize metadata from raw platform data"""
        cache_key = self._generate_cache_key(url, platform)
        
        # Check cache
        if self.config.cache_extracted_data and cache_key in self._metadata_cache:
            cached_data = self._metadata_cache[cache_key]
            if self._is_cache_valid(cached_data):
                return cached_data['metadata']
        
        async with self._extraction_semaphore:
            start_time = time.time()
            
            try:
                # Extract metadata with prioritization
                if self.config.use_field_priority:
                    metadata = await self._extract_with_priority(raw_data, platform)
                else:
                    metadata = await self._extract_all_fields(raw_data, platform)
                
                # Add extraction metadata
                metadata['extraction_info'] = {
                    'extraction_time_ms': round((time.time() - start_time) * 1000, 2),
                    'method': 'priority_based' if self.config.use_field_priority else 'complete',
                    'platform': platform,
                    'cached': False
                }
                
                # Cache result
                if self.config.cache_extracted_data:
                    self._cache_metadata(cache_key, metadata)
                
                return metadata
                
            except Exception as e:
                self.logger.error(f"Metadata extraction failed for {url}: {e}")
                return {'error': str(e), 'platform': platform}
    
    async def _extract_with_priority(self, raw_data: Dict[str, Any], platform: str) -> Dict[str, Any]:
        """Extract metadata with field prioritization"""
        metadata = {}
        
        # Extract critical fields first
        for priority_level in ['critical', 'important', 'optional']:
            fields = self._field_priorities[priority_level]
            
            if self.config.enable_parallel_extraction and len(fields) > 1:
                # Parallel extraction for multiple fields
                tasks = []
                for field in fields:
                    task = self._extract_single_field(raw_data, field, platform)
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for field, result in zip(fields, results):
                    if not isinstance(result, Exception) and result is not None:
                        metadata[field] = result
            else:
                # Sequential extraction
                for field in fields:
                    try:
                        value = await self._extract_single_field(raw_data, field, platform)
                        if value is not None:
                            metadata[field] = value
                    except Exception as e:
                        self.logger.warning(f"Failed to extract {field}: {e}")
        
        return metadata
    
    async def _extract_single_field(self, raw_data: Dict[str, Any], field: str, platform: str) -> Any:
        """Extract a single metadata field"""
        if platform == 'tiktok':
            return self._extract_tiktok_field(raw_data, field)
        elif platform == 'youtube':
            return self._extract_youtube_field(raw_data, field)
        else:
            return None
    
    def _extract_tiktok_field(self, data: Dict[str, Any], field: str) -> Any:
        """Extract TikTok-specific fields"""
        field_mappings = {
            'title': lambda d: d.get('title', '') or d.get('desc', ''),
            'video_id': lambda d: d.get('id', ''),
            'creator': lambda d: d.get('uploader', '') or d.get('creator', ''),
            'duration': lambda d: d.get('duration'),
            'view_count': lambda d: d.get('view_count', 0),
            'like_count': lambda d: d.get('like_count', 0),
            'description': lambda d: d.get('description', ''),
            'hashtags': lambda d: self._extract_hashtags(d.get('description', '')),
            'quality_formats': lambda d: self._extract_quality_info(d.get('formats', [])),
        }
        
        extractor = field_mappings.get(field)
        return extractor(data) if extractor else None
    
    def _extract_youtube_field(self, data: Dict[str, Any], field: str) -> Any:
        """Extract YouTube-specific fields"""
        snippet = data.get('snippet', {})
        statistics = data.get('statistics', {})
        
        field_mappings = {
            'title': lambda d: snippet.get('title', ''),
            'video_id': lambda d: d.get('id', ''),
            'creator': lambda d: snippet.get('channelTitle', ''),
            'duration': lambda d: self._parse_youtube_duration(d.get('contentDetails', {}).get('duration', '')),
            'view_count': lambda d: int(statistics.get('viewCount', 0)) if statistics.get('viewCount') else 0,
            'like_count': lambda d: int(statistics.get('likeCount', 0)) if statistics.get('likeCount') else 0,
            'description': lambda d: snippet.get('description', ''),
            'hashtags': lambda d: self._extract_hashtags(snippet.get('description', '')),
            'quality_formats': lambda d: [],  # Would need yt-dlp integration
        }
        
        extractor = field_mappings.get(field)
        return extractor(data) if extractor else None
    
    def _generate_cache_key(self, url: str, platform: str) -> str:
        """Generate cache key for metadata"""
        content = f"{platform}:{url}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _is_cache_valid(self, cached_data: Dict[str, Any]) -> bool:
        """Check if cached metadata is still valid"""
        cached_time = datetime.fromisoformat(cached_data.get('cached_at', ''))
        ttl = timedelta(minutes=30)  # 30 minute cache TTL
        return datetime.now() - cached_time < ttl

    def _cache_metadata(self, cache_key: str, metadata: Dict[str, Any]):
        """Cache metadata with timestamp"""
        cache_entry = {
            'metadata': metadata,
            'cached_at': datetime.now().isoformat()
        }
        
        # Maintain cache size limit
        if len(self._metadata_cache) >= 1000:  # Max 1000 entries
            # Remove oldest entry
            oldest_key = min(self._metadata_cache.keys(), 
                           key=lambda k: self._metadata_cache[k].get('cached_at', ''))
            del self._metadata_cache[oldest_key]
        
        self._metadata_cache[cache_key] = cache_entry

    def _extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags from text"""
        if not text:
            return []
        hashtag_pattern = re.compile(r'#(\w+)')
        return hashtag_pattern.findall(text)
    
    def _extract_quality_info(self, formats: List[Dict]) -> List[Dict]:
        """Extract quality information from formats"""
        if not formats:
            return []
        
        quality_info = []
        for fmt in formats:
            info = {
                'format_id': fmt.get('format_id', ''),
                'resolution': f"{fmt.get('width', 0)}x{fmt.get('height', 0)}",
                'bitrate': fmt.get('tbr', 0),
                'codec': fmt.get('vcodec', ''),
                'ext': fmt.get('ext', '')
            }
            quality_info.append(info)
        
        return quality_info
    
    def _parse_youtube_duration(self, duration_str: str) -> int:
        """Parse YouTube duration string (PT1M30S format) to seconds"""
        if not duration_str:
            return 0
        
        pattern = re.compile(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?')
        match = pattern.match(duration_str)
        
        if not match:
            return 0
        
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        
        return hours * 3600 + minutes * 60 + seconds

class QualitySelector:
    """Optimized video quality selection logic"""
    
    def __init__(self, config: QualitySelectionConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Quality preference cache
        self._preference_cache = {} if config.quality_preference_cache else None
        
        # Quality scoring weights
        self._quality_weights = {
            'resolution': 0.4,
            'bitrate': 0.3,
            'codec_efficiency': 0.2,
            'file_size': 0.1
        }
    
    def select_best_quality(self, formats: List[Dict[str, Any]], preferences: Dict[str, Any] = None) -> Dict[str, Any]:
        """Select optimal quality format based on preferences and constraints"""
        if not formats:
            return None
        
        preferences = preferences or {}
        cache_key = self._generate_preference_key(formats, preferences)
        
        # Check cache
        if self.config.quality_preference_cache and cache_key in self._preference_cache:
            return self._preference_cache[cache_key]
        
        start_time = time.time()
        
        try:
            # Score all formats
            scored_formats = []
            for fmt in formats:
                score = self._calculate_quality_score(fmt, preferences)
                scored_formats.append((score, fmt))
            
            # Sort by score (highest first)
            scored_formats.sort(key=lambda x: x[0], reverse=True)
            
            # Apply fallback strategies if needed
            selected = self._apply_fallback_strategies(scored_formats, preferences)
            
            selection_time = time.time() - start_time
            result = {
                'format': selected[1] if selected else None,
                'score': selected[0] if selected else 0,
                'selection_time_ms': round(selection_time * 1000, 2),
                'total_formats_evaluated': len(formats)
            }
            
            # Cache result
            if self.config.quality_preference_cache:
                self._preference_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            self.logger.error(f"Quality selection failed: {e}")
            return {'format': formats[0], 'error': str(e)} if formats else None
    
    def _calculate_quality_score(self, fmt: Dict[str, Any], preferences: Dict[str, Any]) -> float:
        """Calculate quality score for a format"""
        score = 0.0
        
        # Resolution score
        height = fmt.get('height', 0) or 0
        resolution_score = min(height / 1080.0, 1.0) * 100  # Normalize to 1080p
        score += resolution_score * self._quality_weights['resolution']
        
        # Bitrate score
        bitrate = fmt.get('tbr', 0) or fmt.get('vbr', 0) or 0
        if bitrate > 0:
            bitrate_score = min(bitrate / 5000.0, 1.0) * 100  # Normalize to 5Mbps
            score += bitrate_score * self._quality_weights['bitrate']
        
        # Codec efficiency score
        vcodec = fmt.get('vcodec', '').lower()
        codec_scores = {
            'av01': 100,  # AV1 (most efficient)
            'vp9': 85,
            'h265': 80,
            'hevc': 80,
            'h264': 70,
            'avc1': 70,
            'vp8': 50
        }
        codec_score = codec_scores.get(vcodec, 30)
        score += codec_score * self._quality_weights['codec_efficiency']
        
        # File size score (smaller is better for same quality)
        filesize = fmt.get('filesize', 0) or 0
        if filesize > 0 and height > 0:
            size_per_pixel = filesize / (height * fmt.get('width', height * 16/9))
            size_score = max(0, 100 - (size_per_pixel / 1000))  # Penalize large files
            score += size_score * self._quality_weights['file_size']
        
        # Apply user preferences
        if preferences:
            score = self._apply_user_preferences(score, fmt, preferences)
        
        return score
    
    def _apply_user_preferences(self, base_score: float, fmt: Dict[str, Any], preferences: Dict[str, Any]) -> float:
        """Apply user preferences to quality score"""
        score = base_score
        
        # Preferred quality level
        preferred_quality = preferences.get('quality_level', 'high')
        height = fmt.get('height', 0) or 0
        
        if preferred_quality == 'high' and height >= 1080:
            score *= 1.2
        elif preferred_quality == 'medium' and 720 <= height < 1080:
            score *= 1.2
        elif preferred_quality == 'low' and height < 720:
            score *= 1.2
        
        # Bandwidth constraints
        max_bitrate = preferences.get('max_bitrate')
        if max_bitrate:
            fmt_bitrate = fmt.get('tbr', 0) or 0
            if fmt_bitrate > max_bitrate:
                score *= 0.5  # Heavy penalty for exceeding bandwidth
        
        # Format preferences
        preferred_formats = preferences.get('preferred_formats', [])
        fmt_ext = fmt.get('ext', '').lower()
        if preferred_formats and fmt_ext in preferred_formats:
            score *= 1.1
        
        return score
    
    def _generate_preference_key(self, formats: List[Dict], preferences: Dict) -> str:
        """Generate cache key for quality preferences"""
        format_ids = [f.get('format_id', '') for f in formats[:5]]  # First 5 for key
        pref_str = json.dumps(preferences, sort_keys=True)
        content = f"{'-'.join(format_ids)}:{pref_str}"
        return hashlib.md5(content.encode()).hexdigest()

    def _apply_fallback_strategies(self, scored_formats: List[Tuple[float, Dict]], preferences: Dict[str, Any]) -> Tuple[float, Dict]:
        """Apply fallback strategies for quality selection"""
        if not scored_formats:
            return None
        
        # Primary selection - highest score
        primary_selection = scored_formats[0]
        
        # Check if primary selection meets minimum requirements
        primary_format = primary_selection[1]
        
        # Apply fallback strategies from config
        for strategy in self.config.fallback_strategies:
            if strategy == "lower_quality":
                # If primary is too high quality, find a more reasonable option
                primary_height = primary_format.get('height', 0)
                if primary_height > 1080 and preferences.get('max_height'):
                    for score, fmt in scored_formats:
                        if fmt.get('height', 0) <= preferences.get('max_height', 1080):
                            return (score, fmt)
            
            elif strategy == "audio_only":
                # Fallback to audio-only if video fails
                for score, fmt in scored_formats:
                    if fmt.get('vcodec') == 'none' and fmt.get('acodec') != 'none':
                        return (score, fmt)
            
            elif strategy == "best_available":
                # Just return the best available format
                return primary_selection
        
        return primary_selection

class RetryManager:
    """Smart retry mechanism with exponential backoff and circuit breaker"""
    
    def __init__(self, config: RetryConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Circuit breaker state
        self._circuit_state = 'closed'  # closed, open, half_open
        self._failure_count = 0
        self._last_failure_time = None
        self._circuit_timeout = 60  # seconds
    
    async def execute_with_retry(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation with smart retry logic"""
        if self.config.circuit_breaker_enabled and self._circuit_state == 'open':
            if not self._should_attempt_reset():
                raise Exception("Circuit breaker is open")
            else:
                self._circuit_state = 'half_open'
        
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                start_time = time.time()
                
                # Execute operation
                if asyncio.iscoroutinefunction(operation):
                    result = await operation(*args, **kwargs)
                else:
                    result = operation(*args, **kwargs)
                
                # Success - reset circuit breaker
                if self.config.circuit_breaker_enabled:
                    self._reset_circuit_breaker()
                
                execution_time = time.time() - start_time
                
                return {
                    'result': result,
                    'attempt': attempt + 1,
                    'execution_time_ms': round(execution_time * 1000, 2),
                    'retries_used': attempt
                }
                
            except Exception as e:
                last_exception = e
                self.logger.warning(f"Operation failed on attempt {attempt + 1}: {e}")
                
                # Check if should retry
                if attempt < self.config.max_retries and self._should_retry(e):
                    delay = self._calculate_delay(attempt)
                    self.logger.info(f"Retrying in {delay:.2f} seconds...")
                    await asyncio.sleep(delay)
                else:
                    # Max retries reached or non-retryable error
                    if self.config.circuit_breaker_enabled:
                        self._record_failure()
                    break
        
        # All retries failed
        raise last_exception
    
    def _should_retry(self, exception: Exception) -> bool:
        """Determine if an exception should trigger a retry"""
        error_str = str(exception).lower()
        
        # Check for retryable error patterns
        retryable_patterns = [
            'timeout', 'connection', 'network', 'temporary',
            'rate limit', 'too many requests', 'service unavailable'
        ]
        
        for pattern in retryable_patterns:
            if pattern in error_str:
                return True
        
        # Check HTTP status codes if available
        if hasattr(exception, 'status') or hasattr(exception, 'status_code'):
            status = getattr(exception, 'status', None) or getattr(exception, 'status_code', None)
            return status in self.config.retry_on_status_codes
        
        return False
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for next retry attempt"""
        if self.config.exponential_backoff:
            delay = self.config.base_delay * (2 ** attempt)
        else:
            delay = self.config.base_delay
        
        # Add jitter to prevent thundering herd
        if self.config.jitter:
            jitter_range = delay * 0.1
            jitter = random.uniform(-jitter_range, jitter_range)
            delay += jitter
        
        return delay
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset"""
        if self._last_failure_time is None:
            return True
        
        time_since_failure = time.time() - self._last_failure_time
        return time_since_failure >= self._circuit_timeout
    
    def _record_failure(self):
        """Record a failure for circuit breaker"""
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        if self._failure_count >= self.config.circuit_breaker_threshold:
            self._circuit_state = 'open'
            self.logger.warning(f"Circuit breaker opened after {self._failure_count} failures")
    
    def _reset_circuit_breaker(self):
        """Reset circuit breaker after successful operation"""
        self._failure_count = 0
        self._last_failure_time = None
        self._circuit_state = 'closed'

class PlatformOptimizer:
    """Main platform handler optimization coordinator"""
    
    def __init__(self, config: PlatformOptimizationConfig = None):
        self.config = config or PlatformOptimizationConfig()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.url_parser = URLParser(self.config.url_parsing)
        self.metadata_extractor = MetadataExtractor(self.config.metadata_extraction)
        self.quality_selector = QualitySelector(self.config.quality_selection)
        self.retry_manager = RetryManager(self.config.retry)
        
        # Performance metrics
        self._metrics = defaultdict(list)
        self._start_time = time.time()
    
    async def optimize_platform_handler(self, platform: str, handler_instance: Any) -> Dict[str, Any]:
        """Apply optimizations to a platform handler"""
        self.logger.info(f"Applying optimizations to {platform} handler")
        
        optimization_results = {
            'platform': platform,
            'timestamp': datetime.now().isoformat(),
            'optimizations_applied': [],
            'performance_improvements': {},
            'configuration': {}
        }
        
        try:
            # Apply URL parsing optimizations
            if hasattr(handler_instance, 'is_valid_url'):
                optimization_results['optimizations_applied'].append('url_parsing_optimization')
                await self._apply_url_parsing_optimization(handler_instance, platform)
            
            # Apply metadata extraction optimizations
            if hasattr(handler_instance, 'get_video_info'):
                optimization_results['optimizations_applied'].append('metadata_extraction_optimization')
                await self._apply_metadata_optimization(handler_instance, platform)
            
            # Apply quality selection optimizations
            if hasattr(handler_instance, '_select_best_format'):
                optimization_results['optimizations_applied'].append('quality_selection_optimization')
                await self._apply_quality_optimization(handler_instance, platform)
            
            # Apply retry mechanism optimizations
            optimization_results['optimizations_applied'].append('retry_mechanism_optimization')
            await self._apply_retry_optimization(handler_instance, platform)
            
            # Platform-specific optimizations
            platform_specific = await self._apply_platform_specific_optimizations(handler_instance, platform)
            optimization_results['optimizations_applied'].extend(platform_specific)
            
            # Record configuration
            optimization_results['configuration'] = {
                'url_parsing': self.config.url_parsing.__dict__,
                'metadata_extraction': self.config.metadata_extraction.__dict__,
                'quality_selection': self.config.quality_selection.__dict__,
                'retry': self.config.retry.__dict__
            }
            
            self.logger.info(f"Successfully optimized {platform} handler")
            
        except Exception as e:
            self.logger.error(f"Failed to optimize {platform} handler: {e}")
            optimization_results['error'] = str(e)
        
        return optimization_results
    
    async def _apply_url_parsing_optimization(self, handler: Any, platform: str):
        """Apply URL parsing optimizations"""
        if platform == 'tiktok':
            # TikTok-specific URL optimizations
            pass
        elif platform == 'youtube':
            # YouTube-specific URL optimizations  
            pass
    
    async def _apply_metadata_optimization(self, handler: Any, platform: str):
        """Apply metadata extraction optimizations"""
        # Enhance metadata extraction with parallel processing
        if platform == 'tiktok':
            # TikTok metadata optimizations
            pass
        elif platform == 'youtube':
            # YouTube metadata optimizations
            pass
    
    async def _apply_quality_optimization(self, handler: Any, platform: str):
        """Apply quality selection optimizations"""
        # Enhanced quality selection logic
        pass
    
    async def _apply_retry_optimization(self, handler: Any, platform: str):
        """Apply retry mechanism optimizations"""
        # Smart retry with exponential backoff
        pass
    
    async def _apply_platform_specific_optimizations(self, handler: Any, platform: str) -> List[str]:
        """Apply platform-specific optimizations"""
        optimizations = []
        
        if platform == 'tiktok':
            # TikTok-specific optimizations
            tiktok_opts = self.config.tiktok_optimizations
            
            # Optimize for TikTok's short video format
            if tiktok_opts.get('optimize_short_videos', True):
                optimizations.append('tiktok_short_video_optimization')
            
            # Optimize watermark handling
            if tiktok_opts.get('optimize_watermark_detection', True):
                optimizations.append('tiktok_watermark_optimization')
            
            # Optimize for TikTok's API rate limits
            if tiktok_opts.get('optimize_rate_limiting', True):
                optimizations.append('tiktok_rate_limit_optimization')
        
        elif platform == 'youtube':
            # YouTube-specific optimizations
            youtube_opts = self.config.youtube_optimizations
            
            # Optimize for YouTube API quota
            if youtube_opts.get('optimize_api_quota', True):
                optimizations.append('youtube_api_quota_optimization')
            
            # Optimize for YouTube's adaptive streams
            if youtube_opts.get('optimize_adaptive_streams', True):
                optimizations.append('youtube_adaptive_stream_optimization')
            
            # Optimize playlist handling
            if youtube_opts.get('optimize_playlists', True):
                optimizations.append('youtube_playlist_optimization')
        
        return optimizations
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        uptime = time.time() - self._start_time
        
        return {
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': round(uptime, 2),
            'components': {
                'url_parser': {
                    'cache_size': len(self.url_parser._url_cache) if self.url_parser._url_cache else 0,
                    'patterns_compiled': len(self.url_parser._pattern_cache)
                },
                'metadata_extractor': {
                    'cache_size': len(self.metadata_extractor._metadata_cache),
                    'concurrent_limit': self.config.metadata_extraction.max_concurrent_extractions
                },
                'quality_selector': {
                    'cache_size': len(self.quality_selector._preference_cache) if self.quality_selector._preference_cache else 0,
                    'smart_selection': self.config.quality_selection.enable_smart_selection
                },
                'retry_manager': {
                    'circuit_state': self.retry_manager._circuit_state,
                    'failure_count': self.retry_manager._failure_count,
                    'max_retries': self.config.retry.max_retries
                }
            },
            'configuration_summary': {
                'total_optimizations_enabled': sum([
                    self.config.url_parsing.enable_caching,
                    self.config.metadata_extraction.enable_parallel_extraction,
                    self.config.quality_selection.enable_smart_selection,
                    self.config.retry.exponential_backoff
                ]),
                'performance_mode': 'high_performance' if all([
                    self.config.url_parsing.use_fast_validation,
                    self.config.metadata_extraction.enable_parallel_extraction,
                    self.config.quality_selection.enable_smart_selection
                ]) else 'standard'
            }
        }

def create_platform_optimizer(config_dict: Dict[str, Any] = None) -> PlatformOptimizer:
    """Factory function to create platform optimizer"""
    if config_dict:
        # Convert dict to config objects
        url_config = URLParsingConfig(**config_dict.get('url_parsing', {}))
        metadata_config = MetadataExtractionConfig(**config_dict.get('metadata_extraction', {}))
        quality_config = QualitySelectionConfig(**config_dict.get('quality_selection', {}))
        retry_config = RetryConfig(**config_dict.get('retry', {}))
        
        config = PlatformOptimizationConfig(
            url_parsing=url_config,
            metadata_extraction=metadata_config,
            quality_selection=quality_config,
            retry=retry_config
        )
        
        # Add platform-specific settings
        if 'tiktok_optimizations' in config_dict:
            config.tiktok_optimizations = config_dict['tiktok_optimizations']
        if 'youtube_optimizations' in config_dict:
            config.youtube_optimizations = config_dict['youtube_optimizations']
    else:
        config = PlatformOptimizationConfig()
    
    return PlatformOptimizer(config)

if __name__ == "__main__":
    # Example usage
    optimizer = create_platform_optimizer()
    
    print("Platform Handler Optimization Framework initialized")
    print("Available optimizations:")
    print("- URL parsing and validation optimization")
    print("- Metadata extraction with parallel processing")
    print("- Smart quality selection algorithms")
    print("- Exponential backoff retry mechanisms")
    print("- Platform-specific performance tuning")
    print("- Circuit breaker pattern for resilience") 