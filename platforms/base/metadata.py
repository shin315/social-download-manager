"""
Metadata extraction and normalization for platform handlers

This module provides a standardized system for extracting, normalizing,
and enriching metadata from different social media platforms. It includes
data models, transformation utilities, and standardization tools to handle
platform-specific metadata while maintaining a consistent interface.
"""

import asyncio
import logging
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlparse
from pathlib import Path

from .enums import PlatformType, ContentType, QualityLevel
from .models import PlatformVideoInfo, VideoFormat

logger = logging.getLogger(__name__)


# =====================================================
# Metadata Exceptions
# =====================================================

class MetadataError(Exception):
    """Base metadata extraction error"""
    
    def __init__(self, message: str, platform: Optional[PlatformType] = None, url: Optional[str] = None):
        super().__init__(message)
        self.platform = platform
        self.url = url


class MetadataExtractionError(MetadataError):
    """Error during metadata extraction"""
    pass


class MetadataValidationError(MetadataError):
    """Error during metadata validation"""
    pass


class MetadataTransformationError(MetadataError):
    """Error during metadata transformation"""
    pass


# =====================================================
# Raw Metadata Models
# =====================================================

@dataclass
class RawMetadata:
    """Raw metadata from platform API/scraping"""
    platform: PlatformType
    url: str
    raw_data: Dict[str, Any] = field(default_factory=dict)
    extracted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "api"  # api, scrape, file, etc.
    confidence: float = 1.0  # 0.0 to 1.0
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from raw data with dot notation support"""
        keys = key.split('.')
        value = self.raw_data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def has_key(self, key: str) -> bool:
        """Check if key exists in raw data"""
        return self.get(key) is not None


@dataclass
class MetadataField:
    """Metadata field definition for transformation"""
    source_key: str
    target_key: str
    required: bool = False
    default_value: Any = None
    transformer: Optional[Callable[[Any], Any]] = None
    validator: Optional[Callable[[Any], bool]] = None
    description: str = ""
    
    def extract_value(self, raw_metadata: RawMetadata) -> Any:
        """Extract and transform value from raw metadata"""
        value = raw_metadata.get(self.source_key, self.default_value)
        
        # Apply transformer if provided
        if self.transformer and value is not None:
            try:
                value = self.transformer(value)
            except Exception as e:
                logger.warning(f"Transformation failed for {self.source_key}: {e}")
                value = self.default_value
        
        # Apply validator if provided
        if self.validator and value is not None:
            if not self.validator(value):
                logger.warning(f"Validation failed for {self.source_key}")
                if self.required:
                    raise MetadataValidationError(f"Required field {self.source_key} failed validation")
                value = self.default_value
        
        return value


# =====================================================
# Metadata Extractors
# =====================================================

class MetadataExtractor(ABC):
    """Abstract metadata extractor"""
    
    def __init__(self, platform_type: PlatformType):
        self.platform_type = platform_type
        self._logger = logging.getLogger(f"metadata.{platform_type.value}")
    
    @abstractmethod
    async def extract_raw_metadata(self, url: str, **kwargs) -> RawMetadata:
        """Extract raw metadata from platform"""
        pass
    
    @abstractmethod
    def get_field_mappings(self) -> List[MetadataField]:
        """Get field mappings for this platform"""
        pass
    
    async def extract_normalized_metadata(self, url: str, **kwargs) -> PlatformVideoInfo:
        """Extract and normalize metadata"""
        raw_metadata = await self.extract_raw_metadata(url, **kwargs)
        return self.normalize_metadata(raw_metadata)
    
    def normalize_metadata(self, raw_metadata: RawMetadata) -> PlatformVideoInfo:
        """Transform raw metadata to normalized format"""
        normalized_data = {}
        field_mappings = self.get_field_mappings()
        
        for field in field_mappings:
            try:
                value = field.extract_value(raw_metadata)
                if value is not None:
                    normalized_data[field.target_key] = value
            except Exception as e:
                self._logger.error(f"Failed to extract field {field.source_key}: {e}")
                if field.required:
                    raise MetadataExtractionError(
                        f"Required field extraction failed: {field.source_key}",
                        platform=self.platform_type,
                        url=raw_metadata.url
                    )
        
        # Create PlatformVideoInfo with extracted data
        return self._create_video_info(raw_metadata, normalized_data)
    
    def _create_video_info(self, raw_metadata: RawMetadata, normalized_data: Dict[str, Any]) -> PlatformVideoInfo:
        """Create PlatformVideoInfo from normalized data"""
        return PlatformVideoInfo(
            url=raw_metadata.url,
            platform=self.platform_type,
            platform_id=normalized_data.get('platform_id'),
            title=normalized_data.get('title', 'Unknown Title'),
            description=normalized_data.get('description', ''),
            thumbnail_url=normalized_data.get('thumbnail_url', ''),
            duration=normalized_data.get('duration'),
            creator=normalized_data.get('creator', 'Unknown'),
            creator_id=normalized_data.get('creator_id'),
            creator_avatar=normalized_data.get('creator_avatar'),
            content_type=normalized_data.get('content_type', ContentType.VIDEO),
            hashtags=normalized_data.get('hashtags', []),
            mentions=normalized_data.get('mentions', []),
            view_count=normalized_data.get('view_count'),
            like_count=normalized_data.get('like_count'),
            comment_count=normalized_data.get('comment_count'),
            share_count=normalized_data.get('share_count'),
            published_at=normalized_data.get('published_at'),
            formats=normalized_data.get('formats', []),
            extra_data=normalized_data.get('extra_data', {})
        )


# =====================================================
# Data Transformers
# =====================================================

class DataTransformers:
    """Common data transformation utilities"""
    
    @staticmethod
    def to_int(value: Any, default: int = 0) -> int:
        """Convert value to integer"""
        try:
            if isinstance(value, str):
                # Handle formatted numbers like "1.2M", "1.5K"
                value = value.strip().lower()
                if value.endswith('k'):
                    return int(float(value[:-1]) * 1000)
                elif value.endswith('m'):
                    return int(float(value[:-1]) * 1000000)
                elif value.endswith('b'):
                    return int(float(value[:-1]) * 1000000000)
                else:
                    # Remove commas and other formatting
                    value = re.sub(r'[^\d.-]', '', value)
            return int(float(value))
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def to_float(value: Any, default: float = 0.0) -> float:
        """Convert value to float"""
        try:
            if isinstance(value, str):
                value = re.sub(r'[^\d.-]', '', value.strip())
            return float(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def to_datetime(value: Any, formats: Optional[List[str]] = None) -> Optional[datetime]:
        """Convert value to datetime"""
        if not value:
            return None
        
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, (int, float)):
            # Assume Unix timestamp
            try:
                return datetime.fromtimestamp(value, timezone.utc)
            except (ValueError, OSError):
                return None
        
        if isinstance(value, str):
            # Try common formats
            common_formats = [
                '%Y-%m-%dT%H:%M:%S.%fZ',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%d/%m/%Y %H:%M:%S',
                '%d/%m/%Y'
            ]
            
            formats = formats or common_formats
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(value, fmt)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except ValueError:
                    continue
        
        return None
    
    @staticmethod
    def extract_hashtags(text: str) -> List[str]:
        """Extract hashtags from text"""
        if not text:
            return []
        
        hashtag_pattern = r'#(\w+)'
        hashtags = re.findall(hashtag_pattern, text, re.IGNORECASE)
        return [tag.lower() for tag in hashtags]
    
    @staticmethod
    def extract_mentions(text: str) -> List[str]:
        """Extract mentions from text"""
        if not text:
            return []
        
        mention_pattern = r'@(\w+)'
        mentions = re.findall(mention_pattern, text, re.IGNORECASE)
        return [mention.lower() for mention in mentions]
    
    @staticmethod
    def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
        """Sanitize and clean text"""
        if not text:
            return ""
        
        # Remove control characters
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        if max_length and len(text) > max_length:
            text = text[:max_length].strip()
        
        return text
    
    @staticmethod
    def parse_duration(duration_str: str) -> Optional[float]:
        """Parse duration string to seconds"""
        if not duration_str:
            return None
        
        # Handle ISO 8601 duration (PT1H2M3S)
        iso_pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?'
        match = re.match(iso_pattern, duration_str, re.IGNORECASE)
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
        
        # Handle MM:SS or HH:MM:SS format
        time_parts = duration_str.split(':')
        if len(time_parts) == 2:  # MM:SS
            try:
                minutes, seconds = map(float, time_parts)
                return minutes * 60 + seconds
            except ValueError:
                pass
        elif len(time_parts) == 3:  # HH:MM:SS
            try:
                hours, minutes, seconds = map(float, time_parts)
                return hours * 3600 + minutes * 60 + seconds
            except ValueError:
                pass
        
        # Handle numeric seconds
        try:
            return float(duration_str)
        except ValueError:
            return None
    
    @staticmethod
    def normalize_url(url: str, platform: PlatformType) -> str:
        """Normalize URL for platform"""
        if not url:
            return url
        
        # Platform-specific URL normalization
        parsed = urlparse(url)
        
        if platform == PlatformType.TIKTOK:
            # Convert vm.tiktok.com to tiktok.com
            if 'vm.tiktok.com' in parsed.netloc:
                # This would typically require following redirects
                pass
        
        # Remove tracking parameters
        return url  # Simplified for now


# =====================================================
# Data Validators
# =====================================================

class DataValidators:
    """Common data validation utilities"""
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Validate URL format"""
        try:
            parsed = urlparse(url)
            return all([parsed.scheme, parsed.netloc])
        except Exception:
            return False
    
    @staticmethod
    def is_positive_number(value: Any) -> bool:
        """Validate positive number"""
        try:
            return float(value) >= 0
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def is_valid_duration(value: Any) -> bool:
        """Validate duration value"""
        try:
            duration = float(value)
            return 0 <= duration <= 86400  # Max 24 hours
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def is_non_empty_string(value: Any) -> bool:
        """Validate non-empty string"""
        return isinstance(value, str) and len(value.strip()) > 0


# =====================================================
# Platform-Specific Extractors
# =====================================================

class TikTokMetadataExtractor(MetadataExtractor):
    """TikTok-specific metadata extractor"""
    
    def __init__(self):
        super().__init__(PlatformType.TIKTOK)
    
    async def extract_raw_metadata(self, url: str, **kwargs) -> RawMetadata:
        """Extract raw metadata from TikTok"""
        # Placeholder implementation - would integrate with actual TikTok API/scraper
        raw_data = {
            'id': '7123456789',
            'desc': 'Sample TikTok video',
            'author': {
                'uniqueId': 'username',
                'nickname': 'Display Name',
                'avatarLarger': 'https://example.com/avatar.jpg'
            },
            'stats': {
                'playCount': 1500000,
                'likeCount': 75000,
                'commentCount': 1200,
                'shareCount': 5000
            },
            'createTime': 1640995200,
            'video': {
                'duration': 15,
                'playAddr': 'https://example.com/video.mp4',
                'cover': 'https://example.com/cover.jpg'
            },
            'music': {
                'title': 'Original Sound',
                'author': 'username'
            }
        }
        
        return RawMetadata(
            platform=PlatformType.TIKTOK,
            url=url,
            raw_data=raw_data,
            source="api"
        )
    
    def get_field_mappings(self) -> List[MetadataField]:
        """Get TikTok field mappings"""
        return [
            MetadataField(
                source_key='id',
                target_key='platform_id',
                required=True,
                description='TikTok video ID'
            ),
            MetadataField(
                source_key='desc',
                target_key='title',
                required=True,
                transformer=lambda x: DataTransformers.sanitize_text(x, 500),
                validator=DataValidators.is_non_empty_string,
                description='Video description/title'
            ),
            MetadataField(
                source_key='desc',
                target_key='description',
                transformer=lambda x: DataTransformers.sanitize_text(x),
                description='Video description'
            ),
            MetadataField(
                source_key='video.cover',
                target_key='thumbnail_url',
                validator=DataValidators.is_valid_url,
                description='Video thumbnail URL'
            ),
            MetadataField(
                source_key='video.duration',
                target_key='duration',
                transformer=DataTransformers.to_float,
                validator=DataValidators.is_valid_duration,
                description='Video duration in seconds'
            ),
            MetadataField(
                source_key='author.nickname',
                target_key='creator',
                required=True,
                transformer=lambda x: DataTransformers.sanitize_text(x, 100),
                description='Creator display name'
            ),
            MetadataField(
                source_key='author.uniqueId',
                target_key='creator_id',
                transformer=lambda x: DataTransformers.sanitize_text(x, 50),
                description='Creator username'
            ),
            MetadataField(
                source_key='author.avatarLarger',
                target_key='creator_avatar',
                validator=DataValidators.is_valid_url,
                description='Creator avatar URL'
            ),
            MetadataField(
                source_key='stats.playCount',
                target_key='view_count',
                transformer=DataTransformers.to_int,
                validator=DataValidators.is_positive_number,
                description='View count'
            ),
            MetadataField(
                source_key='stats.likeCount',
                target_key='like_count',
                transformer=DataTransformers.to_int,
                validator=DataValidators.is_positive_number,
                description='Like count'
            ),
            MetadataField(
                source_key='stats.commentCount',
                target_key='comment_count',
                transformer=DataTransformers.to_int,
                validator=DataValidators.is_positive_number,
                description='Comment count'
            ),
            MetadataField(
                source_key='stats.shareCount',
                target_key='share_count',
                transformer=DataTransformers.to_int,
                validator=DataValidators.is_positive_number,
                description='Share count'
            ),
            MetadataField(
                source_key='createTime',
                target_key='published_at',
                transformer=DataTransformers.to_datetime,
                description='Publication timestamp'
            ),
            MetadataField(
                source_key='desc',
                target_key='hashtags',
                transformer=DataTransformers.extract_hashtags,
                default_value=[],
                description='Extracted hashtags'
            ),
            MetadataField(
                source_key='desc',
                target_key='mentions',
                transformer=DataTransformers.extract_mentions,
                default_value=[],
                description='Extracted mentions'
            )
        ]


class YouTubeMetadataExtractor(MetadataExtractor):
    """YouTube-specific metadata extractor"""
    
    def __init__(self):
        super().__init__(PlatformType.YOUTUBE)
    
    async def extract_raw_metadata(self, url: str, **kwargs) -> RawMetadata:
        """Extract raw metadata from YouTube"""
        # Placeholder implementation
        raw_data = {
            'id': 'dQw4w9WgXcQ',
            'title': 'Sample YouTube Video',
            'description': 'This is a sample YouTube video description',
            'channelTitle': 'Channel Name',
            'channelId': 'UCChannelId',
            'thumbnails': {
                'high': {'url': 'https://example.com/thumbnail.jpg'}
            },
            'duration': 'PT3M33S',
            'viewCount': '1000000',
            'likeCount': '50000',
            'commentCount': '2500',
            'publishedAt': '2021-01-01T00:00:00Z',
            'tags': ['tag1', 'tag2', 'tag3']
        }
        
        return RawMetadata(
            platform=PlatformType.YOUTUBE,
            url=url,
            raw_data=raw_data,
            source="api"
        )
    
    def get_field_mappings(self) -> List[MetadataField]:
        """Get YouTube field mappings"""
        return [
            MetadataField(
                source_key='id',
                target_key='platform_id',
                required=True,
                description='YouTube video ID'
            ),
            MetadataField(
                source_key='title',
                target_key='title',
                required=True,
                transformer=lambda x: DataTransformers.sanitize_text(x, 500),
                validator=DataValidators.is_non_empty_string,
                description='Video title'
            ),
            MetadataField(
                source_key='description',
                target_key='description',
                transformer=lambda x: DataTransformers.sanitize_text(x),
                description='Video description'
            ),
            MetadataField(
                source_key='thumbnails.high.url',
                target_key='thumbnail_url',
                validator=DataValidators.is_valid_url,
                description='Video thumbnail URL'
            ),
            MetadataField(
                source_key='duration',
                target_key='duration',
                transformer=DataTransformers.parse_duration,
                validator=DataValidators.is_valid_duration,
                description='Video duration'
            ),
            MetadataField(
                source_key='channelTitle',
                target_key='creator',
                required=True,
                transformer=lambda x: DataTransformers.sanitize_text(x, 100),
                description='Channel name'
            ),
            MetadataField(
                source_key='channelId',
                target_key='creator_id',
                transformer=lambda x: DataTransformers.sanitize_text(x, 50),
                description='Channel ID'
            ),
            MetadataField(
                source_key='viewCount',
                target_key='view_count',
                transformer=DataTransformers.to_int,
                validator=DataValidators.is_positive_number,
                description='View count'
            ),
            MetadataField(
                source_key='likeCount',
                target_key='like_count',
                transformer=DataTransformers.to_int,
                validator=DataValidators.is_positive_number,
                description='Like count'
            ),
            MetadataField(
                source_key='commentCount',
                target_key='comment_count',
                transformer=DataTransformers.to_int,
                validator=DataValidators.is_positive_number,
                description='Comment count'
            ),
            MetadataField(
                source_key='publishedAt',
                target_key='published_at',
                transformer=DataTransformers.to_datetime,
                description='Publication date'
            ),
            MetadataField(
                source_key='tags',
                target_key='hashtags',
                default_value=[],
                description='Video tags as hashtags'
            )
        ]


# =====================================================
# Metadata Manager
# =====================================================

class MetadataManager:
    """Central metadata management system"""
    
    def __init__(self):
        self._extractors: Dict[PlatformType, MetadataExtractor] = {}
        self._enrichers: List[Callable[[PlatformVideoInfo], PlatformVideoInfo]] = []
        self._register_default_extractors()
    
    def _register_default_extractors(self) -> None:
        """Register default extractors"""
        self.register_extractor(TikTokMetadataExtractor())
        self.register_extractor(YouTubeMetadataExtractor())
    
    def register_extractor(self, extractor: MetadataExtractor) -> None:
        """Register a metadata extractor"""
        self._extractors[extractor.platform_type] = extractor
        logger.info(f"Registered metadata extractor for {extractor.platform_type.display_name}")
    
    def register_enricher(self, enricher: Callable[[PlatformVideoInfo], PlatformVideoInfo]) -> None:
        """Register a metadata enricher"""
        self._enrichers.append(enricher)
        logger.info("Registered metadata enricher")
    
    async def extract_metadata(self, platform: PlatformType, url: str, **kwargs) -> PlatformVideoInfo:
        """Extract metadata for a platform and URL"""
        extractor = self._extractors.get(platform)
        if not extractor:
            raise MetadataExtractionError(
                f"No metadata extractor available for {platform.display_name}",
                platform=platform,
                url=url
            )
        
        try:
            # Extract normalized metadata
            video_info = await extractor.extract_normalized_metadata(url, **kwargs)
            
            # Apply enrichers
            for enricher in self._enrichers:
                try:
                    video_info = enricher(video_info)
                except Exception as e:
                    logger.warning(f"Enricher failed: {e}")
            
            return video_info
        except Exception as e:
            if isinstance(e, MetadataError):
                raise
            raise MetadataExtractionError(
                f"Failed to extract metadata: {e}",
                platform=platform,
                url=url
            ) from e
    
    def get_supported_platforms(self) -> List[PlatformType]:
        """Get list of supported platforms"""
        return list(self._extractors.keys())
    
    def get_field_mappings(self, platform: PlatformType) -> Optional[List[MetadataField]]:
        """Get field mappings for a platform"""
        extractor = self._extractors.get(platform)
        return extractor.get_field_mappings() if extractor else None


# =====================================================
# Metadata Enrichers
# =====================================================

def content_type_enricher(video_info: PlatformVideoInfo) -> PlatformVideoInfo:
    """Enrich content type based on metadata"""
    # Determine content type from duration or other metadata
    if video_info.duration:
        if video_info.duration < 60:
            video_info.content_type = ContentType.VIDEO
        elif video_info.duration > 3600:
            video_info.content_type = ContentType.VIDEO  # Long form
    
    return video_info


def quality_enricher(video_info: PlatformVideoInfo) -> PlatformVideoInfo:
    """Enrich video quality information"""
    # Add quality levels if not present
    if not video_info.formats:
        # Create default format based on platform
        default_format = VideoFormat(
            format_id="default",
            quality=QualityLevel.BEST,
            ext="mp4"
        )
        video_info.formats = [default_format]
    
    return video_info


# Global metadata manager instance
metadata_manager = MetadataManager()

# Register default enrichers
metadata_manager.register_enricher(content_type_enricher)
metadata_manager.register_enricher(quality_enricher) 