"""
Enhanced Data Models with Advanced Validation

Enhanced versions of core and platform models that integrate
comprehensive validation logic for maximum data integrity.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, ClassVar
from pathlib import Path

from pydantic import Field, field_validator, model_validator

from .core_models import (
    Platform as BasePlatform,
    Content as BaseContent,
    ContentMetadata as BaseContentMetadata,
    Download as BaseDownload,
    DownloadSession as BaseDownloadSession,
    DownloadError as BaseDownloadError,
    QualityOption as BaseQualityOption,
    ApplicationSetting as BaseApplicationSetting
)
from .platform_models import (
    TikTokContent as BaseTikTokContent,
    YouTubeContent as BaseYouTubeContent,
    InstagramContent as BaseInstagramContent,
    PlatformModelFactory
)
from .validators import (
    URLValidator,
    JSONValidator,
    NumericValidator,
    StringValidator,
    DateTimeValidator,
    BusinessRuleValidator,
    validate_status_transition,
    get_platform_validation_rules
)


# =============================================================================
# ENHANCED CORE MODELS
# =============================================================================

class Platform(BasePlatform):
    """Enhanced Platform model with advanced validation"""
    
    @field_validator('name')
    @classmethod
    def validate_name_enhanced(cls, v: str) -> str:
        """Enhanced platform name validation"""
        return StringValidator.validate_slug(v)
    
    @field_validator('base_url', 'api_endpoint')
    @classmethod
    def validate_urls_enhanced(cls, v: Optional[str]) -> Optional[str]:
        """Enhanced URL validation"""
        if v is not None:
            return URLValidator.validate_url_format(v)
        return v
    
    @field_validator('supported_content_types')
    @classmethod
    def validate_supported_content_types(cls, v: str) -> str:
        """Validate supported content types JSON array"""
        return JSONValidator.validate_json_array(v, str)
    
    @field_validator('metadata')
    @classmethod
    def validate_metadata_enhanced(cls, v: str) -> str:
        """Enhanced metadata validation"""
        return JSONValidator.validate_json_object(v)
    
    @model_validator(mode='after')
    def validate_platform_consistency(self):
        """Validate platform configuration consistency"""
        # Parse supported content types
        import json
        try:
            supported_types = json.loads(self.supported_content_types)
            
            # Validate against known content types
            valid_types = ['video', 'audio', 'image', 'post', 'story', 'reel', 'livestream', 'playlist']
            invalid_types = [t for t in supported_types if t not in valid_types]
            if invalid_types:
                raise ValueError(f"Invalid content types: {invalid_types}")
                
        except json.JSONDecodeError:
            raise ValueError("Invalid supported_content_types JSON")
        
        return self


class Content(BaseContent):
    """Enhanced Content model with advanced validation"""
    
    @field_validator('original_url')
    @classmethod
    def validate_original_url(cls, v: str) -> str:
        """Enhanced URL validation with format checking"""
        return URLValidator.validate_url_format(v)
    
    @field_validator('canonical_url', 'author_url')
    @classmethod
    def validate_optional_urls(cls, v: Optional[str]) -> Optional[str]:
        """Enhanced optional URL validation"""
        if v is not None:
            return URLValidator.validate_url_format(v)
        return v
    
    @field_validator('duration_seconds')
    @classmethod
    def validate_duration(cls, v: Optional[int]) -> Optional[int]:
        """Enhanced duration validation"""
        if v is not None:
            return DateTimeValidator.validate_duration_seconds(v)
        return v
    
    @field_validator('file_size_bytes')
    @classmethod
    def validate_file_size(cls, v: Optional[int]) -> Optional[int]:
        """Enhanced file size validation"""
        if v is not None:
            return NumericValidator.validate_file_size(v)
        return v
    
    @field_validator('view_count', 'like_count', 'comment_count', 'share_count')
    @classmethod
    def validate_engagement_counts(cls, v: int) -> int:
        """Enhanced engagement count validation"""
        return NumericValidator.validate_positive_integer(v, "engagement count")
    
    @field_validator('published_at')
    @classmethod
    def validate_published_at(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Enhanced publication date validation"""
        if v is not None:
            return DateTimeValidator.validate_reasonable_date_range(v)
        return v
    
    @field_validator('local_file_path', 'thumbnail_path')
    @classmethod
    def validate_file_paths(cls, v: Optional[str]) -> Optional[str]:
        """Enhanced file path validation"""
        if v is not None:
            return StringValidator.validate_filename(v, allow_path=True)
        return v
    
    @model_validator(mode='after')
    def validate_content_consistency(self):
        """Validate content data consistency"""
        # Validate content type specific requirements
        if self.content_type == 'video':
            if self.duration_seconds is None:
                raise ValueError("Video content must have duration")
        elif self.content_type == 'audio':
            if self.duration_seconds is None:
                raise ValueError("Audio content must have duration")
        elif self.content_type == 'image':
            if self.duration_seconds is not None:
                raise ValueError("Image content cannot have duration")
        
        # Validate file information consistency
        if self.local_file_path and not self.file_size_bytes:
            raise ValueError("Content with local file path should have file size")
        
        return self


class ContentMetadata(BaseContentMetadata):
    """Enhanced ContentMetadata model with advanced validation"""
    
    @field_validator('metadata_value')
    @classmethod
    def validate_metadata_value_by_type(cls, v: Optional[str], info) -> Optional[str]:
        """Validate metadata value based on data type"""
        if v is not None and info.data and 'data_type' in info.data:
            data_type = info.data['data_type']
            return JSONValidator.validate_metadata_value(v, data_type)
        return v
    
    @model_validator(mode='after')
    def validate_metadata_consistency(self):
        """Validate metadata consistency"""
        # Validate hierarchical metadata
        if self.parent_key and not self.metadata_key.startswith(f"{self.parent_key}."):
            raise ValueError("Child metadata key must start with parent key")
        
        return self


class Download(BaseDownload):
    """Enhanced Download model with advanced validation"""
    
    @field_validator('output_directory')
    @classmethod
    def validate_output_directory(cls, v: str) -> str:
        """Enhanced output directory validation"""
        validated_path = StringValidator.validate_filename(v, allow_path=True)
        
        # Ensure it's an absolute path
        try:
            path = Path(validated_path)
            if not path.is_absolute():
                raise ValueError("Output directory must be absolute path")
        except Exception as e:
            raise ValueError(f"Invalid output directory: {str(e)}")
        
        return validated_path
    
    @field_validator('progress_percentage')
    @classmethod
    def validate_progress(cls, v: Decimal) -> Decimal:
        """Enhanced progress validation"""
        return NumericValidator.validate_decimal_precision(v, 5, 2)
    
    @field_validator('current_speed_bps', 'average_speed_bps')
    @classmethod
    def validate_speeds(cls, v: Optional[int]) -> Optional[int]:
        """Enhanced speed validation"""
        if v is not None:
            return NumericValidator.validate_speed_bps(v)
        return v
    
    @field_validator('actual_file_size')
    @classmethod
    def validate_actual_file_size(cls, v: Optional[int]) -> Optional[int]:
        """Enhanced file size validation"""
        if v is not None:
            return NumericValidator.validate_file_size(v)
        return v
    
    @field_validator('final_filename', 'custom_filename')
    @classmethod
    def validate_filenames(cls, v: Optional[str]) -> Optional[str]:
        """Enhanced filename validation"""
        if v is not None:
            return StringValidator.validate_filename(v, allow_path=False)
        return v
    
    @field_validator('final_file_path')
    @classmethod
    def validate_final_file_path(cls, v: Optional[str]) -> Optional[str]:
        """Enhanced file path validation"""
        if v is not None:
            return StringValidator.validate_filename(v, allow_path=True)
        return v
    
    @field_validator('download_options')
    @classmethod
    def validate_download_options_enhanced(cls, v: str) -> str:
        """Enhanced download options validation"""
        return JSONValidator.validate_json_object(v)
    
    @model_validator(mode='after')
    def validate_download_consistency(self):
        """Validate download data consistency"""
        # Validate retry logic
        if self.retry_count > self.max_retries:
            raise ValueError("Retry count cannot exceed max retries")
        
        # Validate timing sequence
        if self.started_at and self.queued_at and self.started_at < self.queued_at:
            raise ValueError("Start time cannot be before queue time")
        
        if self.completed_at and self.started_at and self.completed_at < self.started_at:
            raise ValueError("Completion time cannot be before start time")
        
        # Validate progress vs status
        if self.status == 'completed' and self.progress_percentage < Decimal('100.00'):
            raise ValueError("Completed download must have 100% progress")
        
        return self


class DownloadSession(BaseDownloadSession):
    """Enhanced DownloadSession model with advanced validation"""
    
    @field_validator('session_uuid')
    @classmethod
    def validate_session_uuid_enhanced(cls, v: str) -> str:
        """Enhanced UUID validation"""
        return StringValidator.validate_uuid_string(v)
    
    @field_validator('bytes_downloaded', 'total_bytes')
    @classmethod
    def validate_byte_counts(cls, v: Optional[int]) -> Optional[int]:
        """Enhanced byte count validation"""
        if v is not None:
            return NumericValidator.validate_file_size(v)
        return v
    
    @field_validator('peak_speed_bps', 'average_speed_bps')
    @classmethod
    def validate_session_speeds(cls, v: Optional[int]) -> Optional[int]:
        """Enhanced speed validation"""
        if v is not None:
            return NumericValidator.validate_speed_bps(v)
        return v
    
    @field_validator('headers')
    @classmethod
    def validate_headers_enhanced(cls, v: str) -> str:
        """Enhanced headers validation"""
        return JSONValidator.validate_json_object(v)
    
    @model_validator(mode='after')
    def validate_session_consistency(self):
        """Validate session data consistency"""
        # Validate byte progress
        if self.total_bytes and self.bytes_downloaded > self.total_bytes:
            raise ValueError("Downloaded bytes cannot exceed total bytes")
        
        # Validate chunk progress
        if self.total_chunks and self.chunks_completed > self.total_chunks:
            raise ValueError("Completed chunks cannot exceed total chunks")
        
        # Validate timing
        if (self.session_ended_at and self.session_started_at and 
            self.session_ended_at < self.session_started_at):
            raise ValueError("Session end time cannot be before start time")
        
        # Validate speed consistency
        if (self.peak_speed_bps and self.average_speed_bps and 
            self.average_speed_bps > self.peak_speed_bps):
            raise ValueError("Average speed cannot exceed peak speed")
        
        return self


class QualityOption(BaseQualityOption):
    """Enhanced QualityOption model with advanced validation"""
    
    @field_validator('estimated_file_size')
    @classmethod
    def validate_estimated_file_size(cls, v: Optional[int]) -> Optional[int]:
        """Enhanced file size estimation validation"""
        if v is not None:
            return NumericValidator.validate_file_size(v)
        return v
    
    @field_validator('download_url')
    @classmethod
    def validate_download_url_enhanced(cls, v: Optional[str]) -> Optional[str]:
        """Enhanced download URL validation"""
        if v is not None:
            return URLValidator.validate_url_format(v)
        return v
    
    @field_validator('expires_at')
    @classmethod
    def validate_expires_at(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Enhanced expiration validation"""
        if v is not None:
            return DateTimeValidator.validate_future_datetime(v, "expires_at")
        return v
    
    @model_validator(mode='after')
    def validate_quality_consistency(self):
        """Validate quality option consistency"""
        # Validate resolution consistency
        if (self.resolution_width and not self.resolution_height) or \
           (self.resolution_height and not self.resolution_width):
            raise ValueError("Both width and height must be specified for resolution")
        
        # Validate bitrate vs file size consistency
        if (self.bitrate_kbps and self.estimated_file_size and 
            hasattr(self, 'content') and hasattr(self.content, 'duration_seconds')):
            # Basic sanity check for file size estimate
            pass  # Implementation depends on content access
        
        return self


# =============================================================================
# ENHANCED PLATFORM MODELS
# =============================================================================

class TikTokContent(BaseTikTokContent):
    """Enhanced TikTok content model with platform-specific validation"""
    
    @field_validator('tiktok_music_url', 'tiktok_duet_original_url', 'tiktok_stitch_original_url')
    @classmethod
    def validate_tiktok_urls_enhanced(cls, v: Optional[str]) -> Optional[str]:
        """Enhanced TikTok URL validation"""
        if v is not None:
            # For TikTok URLs, validate against TikTok patterns
            return URLValidator.validate_platform_url(v, 'tiktok')
        return v
    
    @field_validator('original_url')
    @classmethod
    def validate_original_url_tiktok(cls, v: str) -> str:
        """Validate original URL is TikTok format"""
        return URLValidator.validate_platform_url(v, 'tiktok')
    
    @model_validator(mode='after')
    def validate_tiktok_consistency(self):
        """Validate TikTok-specific consistency"""
        # Get TikTok validation rules
        rules = get_platform_validation_rules('tiktok')
        
        # Validate duration limits
        if self.duration_seconds and self.duration_seconds > rules.get('max_duration', 600):
            raise ValueError(f"TikTok video duration exceeds platform limit")
        
        # Validate duet/stitch consistency
        if (self.tiktok_video_type == 'duet' and not self.tiktok_duet_original_url):
            raise ValueError("Duet video must have original video URL")
        
        if (self.tiktok_video_type == 'stitch' and not self.tiktok_stitch_original_url):
            raise ValueError("Stitch video must have original video URL")
        
        return self


class YouTubeContent(BaseYouTubeContent):
    """Enhanced YouTube content model with platform-specific validation"""
    
    @field_validator('original_url')
    @classmethod
    def validate_original_url_youtube(cls, v: str) -> str:
        """Validate original URL is YouTube format"""
        return URLValidator.validate_platform_url(v, 'youtube')
    
    @field_validator('youtube_live_start_time', 'youtube_live_end_time', 'youtube_premiere_time')
    @classmethod
    def validate_youtube_datetimes(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Enhanced YouTube datetime validation"""
        if v is not None:
            return DateTimeValidator.validate_reasonable_date_range(v)
        return v
    
    @model_validator(mode='after')
    def validate_youtube_consistency(self):
        """Validate YouTube-specific consistency"""
        # Get YouTube validation rules
        rules = get_platform_validation_rules('youtube')
        
        # Validate duration limits
        if self.duration_seconds and self.duration_seconds > rules.get('max_duration', 43200):
            raise ValueError(f"YouTube video duration exceeds platform limit")
        
        # Validate live stream timing
        if (self.youtube_live_start_time and self.youtube_live_end_time and 
            self.youtube_live_end_time <= self.youtube_live_start_time):
            raise ValueError("Live stream end time must be after start time")
        
        # Validate shorts
        if (self.youtube_video_type == 'short' and self.duration_seconds and 
            self.duration_seconds > 60):
            raise ValueError("YouTube Shorts cannot be longer than 60 seconds")
        
        return self


class InstagramContent(BaseInstagramContent):
    """Enhanced Instagram content model with platform-specific validation"""
    
    @field_validator('original_url')
    @classmethod
    def validate_original_url_instagram(cls, v: str) -> str:
        """Validate original URL is Instagram format"""
        return URLValidator.validate_platform_url(v, 'instagram')
    
    @field_validator('instagram_story_expires_at')
    @classmethod
    def validate_story_expiration(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Enhanced story expiration validation"""
        if v is not None:
            # Stories should expire within 24 hours
            now = datetime.now()
            max_expiry = now.replace(hour=23, minute=59, second=59)
            if v > max_expiry:
                raise ValueError("Story expiration cannot be more than 24 hours")
        return v
    
    @model_validator(mode='after')
    def validate_instagram_consistency(self):
        """Validate Instagram-specific consistency"""
        # Get Instagram validation rules
        rules = get_platform_validation_rules('instagram')
        
        # Validate duration limits
        if self.duration_seconds and self.duration_seconds > rules.get('max_duration', 3600):
            raise ValueError(f"Instagram content duration exceeds platform limit")
        
        # Validate carousel consistency
        if (self.instagram_media_type == 'carousel' and 
            (not self.instagram_carousel_count or self.instagram_carousel_count < 2)):
            raise ValueError("Carousel posts must have at least 2 items")
        
        # Validate story consistency
        if (self.instagram_media_type == 'story' and not self.instagram_story_expires_at):
            raise ValueError("Story posts must have expiration time")
        
        return self


# =============================================================================
# ENHANCED FACTORY
# =============================================================================

class EnhancedPlatformModelFactory(PlatformModelFactory):
    """Enhanced factory with validation-aware model creation"""
    
    # Enhanced model mappings
    CONTENT_MODELS = {
        'tiktok': TikTokContent,
        'youtube': YouTubeContent,
        'instagram': InstagramContent,
    }
    
    @classmethod
    def create_content_with_validation(cls, platform_name: str, data: Dict[str, Any]) -> Content:
        """Create content with full validation"""
        model_class = cls.get_content_model(platform_name)
        
        # Pre-validate URL format for platform
        if 'original_url' in data:
            data['original_url'] = URLValidator.validate_platform_url(
                data['original_url'], platform_name
            )
        
        # Extract and validate platform content ID
        if 'original_url' in data and not data.get('platform_content_id'):
            content_id = URLValidator.extract_content_id(data['original_url'], platform_name)
            if content_id:
                data['platform_content_id'] = content_id
        
        # Normalize URL
        if 'original_url' in data:
            data['canonical_url'] = URLValidator.normalize_url(
                data['original_url'], platform_name
            )
        
        return model_class.model_validate(data)
    
    @classmethod
    def validate_download_request(cls, content_data: Dict[str, Any], 
                                download_data: Dict[str, Any]) -> bool:
        """Validate download request with business rules"""
        is_valid, errors = BusinessRuleValidator.validate_download_request(
            content_data, download_data
        )
        
        if not is_valid:
            raise ValueError(f"Download validation failed: {'; '.join(errors)}")
        
        return True


# =============================================================================
# MODEL REGISTRY WITH ENHANCED MODELS
# =============================================================================

# Registry of enhanced models
ENHANCED_MODELS = {
    'platform': Platform,
    'content': Content,
    'content_metadata': ContentMetadata,
    'download': Download,
    'download_session': DownloadSession,
    'quality_option': QualityOption,
    'tiktok_content': TikTokContent,
    'youtube_content': YouTubeContent,
    'instagram_content': InstagramContent,
}

# Enhanced model lookup by table name
ENHANCED_MODELS_BY_TABLE = {
    model._table_name: model 
    for model in ENHANCED_MODELS.values()
    if hasattr(model, '_table_name')
} 