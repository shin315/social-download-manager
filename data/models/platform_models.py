"""
Platform-Specific Data Models for Social Download Manager v2.0

Specialized models that extend core models with platform-specific
metadata and functionality for TikTok, YouTube, Instagram, and other platforms.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union, ClassVar
from uuid import UUID

from pydantic import Field, field_validator, computed_field, model_validator

from .core_models import Content, ContentMetadata, Download, QualityOption
from .pydantic_models import (
    DatabaseEntity,
    ContentType,
    ContentStatus,
    DataType,
    validate_url,
    validate_json_string
)


# =============================================================================
# PLATFORM-SPECIFIC ENUMS
# =============================================================================

class TikTokVideoType(str, Enum):
    """TikTok-specific video types"""
    REGULAR = "regular"
    SLIDESHOW = "slideshow"
    LIVE = "live"
    DUET = "duet"
    STITCH = "stitch"


class YouTubeVideoType(str, Enum):
    """YouTube-specific video types"""
    REGULAR = "regular"
    SHORT = "short"
    LIVE = "live"
    PREMIERE = "premiere"
    LIVE_STREAM = "livestream"


class InstagramMediaType(str, Enum):
    """Instagram-specific media types"""
    POST = "post"
    STORY = "story"
    REEL = "reel"
    IGTV = "igtv"
    CAROUSEL = "carousel"


class TikTokVisibility(str, Enum):
    """TikTok visibility settings"""
    PUBLIC = "public"
    PRIVATE = "private"
    FRIENDS_ONLY = "friends_only"
    UNLISTED = "unlisted"


class YouTubePrivacy(str, Enum):
    """YouTube privacy settings"""
    PUBLIC = "public"
    UNLISTED = "unlisted"
    PRIVATE = "private"
    SCHEDULED = "scheduled"


# =============================================================================
# TIKTOK MODELS
# =============================================================================

class TikTokContent(Content):
    """TikTok-specific content model extending the base Content model"""
    
    _table_name: ClassVar[str] = "content"
    
    # TikTok-specific fields (stored as metadata)
    tiktok_video_type: Optional[TikTokVideoType] = Field(
        default=None,
        description="Type of TikTok video"
    )
    tiktok_visibility: Optional[TikTokVisibility] = Field(
        default=None,
        description="TikTok visibility setting"
    )
    tiktok_music_title: Optional[str] = Field(
        default=None,
        description="Title of the music used"
    )
    tiktok_music_author: Optional[str] = Field(
        default=None,
        description="Author of the music used"
    )
    tiktok_music_url: Optional[str] = Field(
        default=None,
        description="URL to the music"
    )
    tiktok_effects: Optional[List[str]] = Field(
        default_factory=list,
        description="List of effects used in the video"
    )
    tiktok_hashtags: Optional[List[str]] = Field(
        default_factory=list,
        description="List of hashtags used"
    )
    tiktok_mentions: Optional[List[str]] = Field(
        default_factory=list,
        description="List of user mentions"
    )
    tiktok_duet_original_url: Optional[str] = Field(
        default=None,
        description="URL of original video for duets"
    )
    tiktok_stitch_original_url: Optional[str] = Field(
        default=None,
        description="URL of original video for stitches"
    )
    tiktok_region_blocked: Optional[List[str]] = Field(
        default_factory=list,
        description="List of regions where content is blocked"
    )
    
    # Engagement metrics specific to TikTok
    tiktok_digg_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="TikTok 'digg' (like) count"
    )
    tiktok_play_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="TikTok play count"
    )
    tiktok_collect_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="TikTok collect/save count"
    )
    
    @field_validator('tiktok_music_url', 'tiktok_duet_original_url', 'tiktok_stitch_original_url')
    @classmethod
    def validate_tiktok_urls(cls, v: Optional[str]) -> Optional[str]:
        """Validate TikTok URL fields"""
        if v is not None:
            return validate_url(v)
        return v
    
    @computed_field
    @property
    def is_duet_or_stitch(self) -> bool:
        """Check if content is a duet or stitch"""
        return self.tiktok_video_type in [TikTokVideoType.DUET, TikTokVideoType.STITCH]
    
    @computed_field
    @property
    def total_tiktok_engagement(self) -> int:
        """Calculate total TikTok-specific engagement"""
        total = 0
        if self.tiktok_digg_count:
            total += self.tiktok_digg_count
        if self.tiktok_collect_count:
            total += self.tiktok_collect_count
        if self.comment_count:
            total += self.comment_count
        if self.share_count:
            total += self.share_count
        return total


class TikTokMetadata(ContentMetadata):
    """TikTok-specific metadata model"""
    
    _table_name: ClassVar[str] = "content_metadata"
    
    # Override metadata_type to default to 'tiktok'
    metadata_type: str = Field(
        default="tiktok",
        description="Always 'tiktok' for TikTok metadata"
    )
    
    @model_validator(mode='after')
    def validate_tiktok_metadata(self):
        """Ensure this is TikTok metadata"""
        if self.metadata_type != "tiktok":
            raise ValueError("TikTokMetadata must have metadata_type='tiktok'")
        return self


# =============================================================================
# YOUTUBE MODELS
# =============================================================================

class YouTubeContent(Content):
    """YouTube-specific content model extending the base Content model"""
    
    _table_name: ClassVar[str] = "content"
    
    # YouTube-specific fields
    youtube_video_type: Optional[YouTubeVideoType] = Field(
        default=None,
        description="Type of YouTube video"
    )
    youtube_privacy: Optional[YouTubePrivacy] = Field(
        default=None,
        description="YouTube privacy setting"
    )
    youtube_category_id: Optional[str] = Field(
        default=None,
        description="YouTube category ID"
    )
    youtube_category_name: Optional[str] = Field(
        default=None,
        description="YouTube category name"
    )
    youtube_tags: Optional[List[str]] = Field(
        default_factory=list,
        description="List of YouTube tags"
    )
    youtube_language: Optional[str] = Field(
        default=None,
        description="Video language code"
    )
    youtube_captions_available: Optional[bool] = Field(
        default=None,
        description="Whether captions are available"
    )
    youtube_caption_languages: Optional[List[str]] = Field(
        default_factory=list,
        description="Available caption languages"
    )
    youtube_live_start_time: Optional[datetime] = Field(
        default=None,
        description="Start time for live streams"
    )
    youtube_live_end_time: Optional[datetime] = Field(
        default=None,
        description="End time for live streams"
    )
    youtube_premiere_time: Optional[datetime] = Field(
        default=None,
        description="Premiere scheduled time"
    )
    
    # Channel information
    youtube_channel_id: Optional[str] = Field(
        default=None,
        description="YouTube channel ID"
    )
    youtube_channel_title: Optional[str] = Field(
        default=None,
        description="YouTube channel title"
    )
    youtube_channel_subscriber_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="Channel subscriber count"
    )
    youtube_channel_verified: Optional[bool] = Field(
        default=None,
        description="Whether channel is verified"
    )
    
    # Engagement metrics
    youtube_favorite_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="YouTube favorite count"
    )
    
    @computed_field
    @property
    def is_live_content(self) -> bool:
        """Check if content is live or was live"""
        return self.youtube_video_type in [YouTubeVideoType.LIVE, YouTubeVideoType.LIVE_STREAM]
    
    @computed_field
    @property
    def is_short_form(self) -> bool:
        """Check if content is short-form (YouTube Shorts)"""
        return self.youtube_video_type == YouTubeVideoType.SHORT or \
               (self.duration_seconds is not None and self.duration_seconds <= 60)


class YouTubeMetadata(ContentMetadata):
    """YouTube-specific metadata model"""
    
    _table_name: ClassVar[str] = "content_metadata"
    
    # Override metadata_type to default to 'youtube'
    metadata_type: str = Field(
        default="youtube",
        description="Always 'youtube' for YouTube metadata"
    )
    
    @model_validator(mode='after')
    def validate_youtube_metadata(self):
        """Ensure this is YouTube metadata"""
        if self.metadata_type != "youtube":
            raise ValueError("YouTubeMetadata must have metadata_type='youtube'")
        return self


class YouTubeQualityOption(QualityOption):
    """YouTube-specific quality options with additional metadata"""
    
    _table_name: ClassVar[str] = "quality_options"
    
    # YouTube-specific quality fields
    youtube_itag: Optional[int] = Field(
        default=None,
        description="YouTube itag identifier"
    )
    youtube_quality_label: Optional[str] = Field(
        default=None,
        description="YouTube quality label (144p, 240p, etc.)"
    )
    youtube_has_audio: Optional[bool] = Field(
        default=None,
        description="Whether stream includes audio"
    )
    youtube_has_video: Optional[bool] = Field(
        default=None,
        description="Whether stream includes video"
    )
    youtube_is_adaptive: Optional[bool] = Field(
        default=None,
        description="Whether stream is adaptive (DASH)"
    )
    youtube_container: Optional[str] = Field(
        default=None,
        description="Container format (mp4, webm, etc.)"
    )
    
    @computed_field
    @property
    def is_audio_only(self) -> bool:
        """Check if this is an audio-only stream"""
        return self.youtube_has_audio is True and self.youtube_has_video is False
    
    @computed_field
    @property
    def is_video_only(self) -> bool:
        """Check if this is a video-only stream"""
        return self.youtube_has_video is True and self.youtube_has_audio is False


# =============================================================================
# INSTAGRAM MODELS
# =============================================================================

class InstagramContent(Content):
    """Instagram-specific content model extending the base Content model"""
    
    _table_name: ClassVar[str] = "content"
    
    # Instagram-specific fields
    instagram_media_type: Optional[InstagramMediaType] = Field(
        default=None,
        description="Type of Instagram media"
    )
    instagram_shortcode: Optional[str] = Field(
        default=None,
        description="Instagram shortcode"
    )
    instagram_caption: Optional[str] = Field(
        default=None,
        description="Instagram caption text"
    )
    instagram_location_name: Optional[str] = Field(
        default=None,
        description="Location name if tagged"
    )
    instagram_location_id: Optional[str] = Field(
        default=None,
        description="Location ID if tagged"
    )
    instagram_hashtags: Optional[List[str]] = Field(
        default_factory=list,
        description="List of hashtags used"
    )
    instagram_mentions: Optional[List[str]] = Field(
        default_factory=list,
        description="List of user mentions"
    )
    instagram_is_verified: Optional[bool] = Field(
        default=None,
        description="Whether the account is verified"
    )
    instagram_carousel_count: Optional[int] = Field(
        default=None,
        ge=1,
        description="Number of items in carousel post"
    )
    
    # Story-specific fields
    instagram_story_expires_at: Optional[datetime] = Field(
        default=None,
        description="When story expires (24h from creation)"
    )
    instagram_story_is_highlight: Optional[bool] = Field(
        default=None,
        description="Whether story is saved to highlights"
    )
    
    # Engagement metrics
    instagram_save_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="Number of saves/bookmarks"
    )
    
    @computed_field
    @property
    def is_carousel(self) -> bool:
        """Check if content is a carousel post"""
        return self.instagram_media_type == InstagramMediaType.CAROUSEL or \
               (self.instagram_carousel_count is not None and self.instagram_carousel_count > 1)
    
    @computed_field
    @property
    def is_temporary_content(self) -> bool:
        """Check if content is temporary (stories, not in highlights)"""
        return self.instagram_media_type == InstagramMediaType.STORY and \
               self.instagram_story_is_highlight is not True


class InstagramMetadata(ContentMetadata):
    """Instagram-specific metadata model"""
    
    _table_name: ClassVar[str] = "content_metadata"
    
    # Override metadata_type to default to 'instagram'
    metadata_type: str = Field(
        default="instagram",
        description="Always 'instagram' for Instagram metadata"
    )
    
    @model_validator(mode='after')
    def validate_instagram_metadata(self):
        """Ensure this is Instagram metadata"""
        if self.metadata_type != "instagram":
            raise ValueError("InstagramMetadata must have metadata_type='instagram'")
        return self


# =============================================================================
# GENERIC PLATFORM EXTENSION MODEL
# =============================================================================

class PlatformContentExtension(DatabaseEntity):
    """
    Generic platform-specific content extension.
    
    Can be used for platforms that don't have dedicated models yet
    or for storing additional platform-specific data.
    """
    
    _table_name: ClassVar[str] = "content_metadata"
    
    content_id: int = Field(
        ...,
        description="Reference to content"
    )
    platform_name: str = Field(
        ...,
        description="Name of the platform"
    )
    extension_data: str = Field(
        default="{}",
        description="JSON data with platform-specific fields"
    )
    
    @field_validator('extension_data')
    @classmethod
    def validate_extension_data(cls, v: str) -> str:
        """Validate extension data JSON"""
        return validate_json_string(v)
    
    def get_extension_value(self, key: str, default: Any = None) -> Any:
        """Get value from extension data JSON"""
        try:
            import json
            data = json.loads(self.extension_data)
            return data.get(key, default)
        except (json.JSONDecodeError, TypeError):
            return default
    
    def set_extension_value(self, key: str, value: Any) -> None:
        """Set value in extension data JSON"""
        try:
            import json
            data = json.loads(self.extension_data)
            data[key] = value
            self.extension_data = json.dumps(data)
            self.mark_updated()
        except (json.JSONDecodeError, TypeError):
            self.extension_data = json.dumps({key: value})
            self.mark_updated()


# =============================================================================
# PLATFORM DOWNLOAD EXTENSIONS
# =============================================================================

class TikTokDownload(Download):
    """TikTok-specific download model with additional features"""
    
    _table_name: ClassVar[str] = "downloads"
    
    # TikTok-specific download options
    download_watermark: bool = Field(
        default=False,
        description="Whether to download with TikTok watermark"
    )
    download_music_separately: bool = Field(
        default=False,
        description="Whether to download music track separately"
    )
    
    @computed_field
    @property
    def is_watermark_removal(self) -> bool:
        """Check if this is a watermark removal download"""
        return not self.download_watermark


class YouTubeDownload(Download):
    """YouTube-specific download model with additional features"""
    
    _table_name: ClassVar[str] = "downloads"
    
    # YouTube-specific download options
    download_captions: bool = Field(
        default=False,
        description="Whether to download captions/subtitles"
    )
    caption_language: Optional[str] = Field(
        default=None,
        description="Preferred caption language"
    )
    download_audio_only: bool = Field(
        default=False,
        description="Whether to download audio only"
    )
    merge_audio_video: bool = Field(
        default=True,
        description="Whether to merge separate audio/video streams"
    )


# =============================================================================
# PLATFORM MODEL FACTORY
# =============================================================================

class PlatformModelFactory:
    """Factory for creating platform-specific models"""
    
    # Model mappings for different platforms
    CONTENT_MODELS = {
        'tiktok': TikTokContent,
        'youtube': YouTubeContent,
        'instagram': InstagramContent,
    }
    
    METADATA_MODELS = {
        'tiktok': TikTokMetadata,
        'youtube': YouTubeMetadata,
        'instagram': InstagramMetadata,
    }
    
    DOWNLOAD_MODELS = {
        'tiktok': TikTokDownload,
        'youtube': YouTubeDownload,
        'instagram': Download,  # Use base Download for Instagram
    }
    
    @classmethod
    def get_content_model(cls, platform_name: str) -> type:
        """Get the appropriate content model for a platform"""
        return cls.CONTENT_MODELS.get(platform_name.lower(), Content)
    
    @classmethod
    def get_metadata_model(cls, platform_name: str) -> type:
        """Get the appropriate metadata model for a platform"""
        return cls.METADATA_MODELS.get(platform_name.lower(), ContentMetadata)
    
    @classmethod
    def get_download_model(cls, platform_name: str) -> type:
        """Get the appropriate download model for a platform"""
        return cls.DOWNLOAD_MODELS.get(platform_name.lower(), Download)
    
    @classmethod
    def create_content(cls, platform_name: str, **kwargs) -> Content:
        """Create a content instance for the specified platform"""
        model_class = cls.get_content_model(platform_name)
        return model_class(**kwargs)
    
    @classmethod
    def create_metadata(cls, platform_name: str, **kwargs) -> ContentMetadata:
        """Create a metadata instance for the specified platform"""
        model_class = cls.get_metadata_model(platform_name)
        if 'metadata_type' not in kwargs:
            kwargs['metadata_type'] = platform_name.lower()
        return model_class(**kwargs)
    
    @classmethod
    def create_download(cls, platform_name: str, **kwargs) -> Download:
        """Create a download instance for the specified platform"""
        model_class = cls.get_download_model(platform_name)
        return model_class(**kwargs)


# =============================================================================
# PLATFORM MODEL REGISTRY
# =============================================================================

# Registry of platform-specific models
PLATFORM_MODELS = {
    'tiktok': {
        'content': TikTokContent,
        'metadata': TikTokMetadata,
        'download': TikTokDownload,
    },
    'youtube': {
        'content': YouTubeContent,
        'metadata': YouTubeMetadata,
        'download': YouTubeDownload,
        'quality_option': YouTubeQualityOption,
    },
    'instagram': {
        'content': InstagramContent,
        'metadata': InstagramMetadata,
        'download': Download,  # Use base Download model
    },
}

# All platform model classes for easy import
ALL_PLATFORM_MODELS = [
    TikTokContent, TikTokMetadata, TikTokDownload,
    YouTubeContent, YouTubeMetadata, YouTubeDownload, YouTubeQualityOption,
    InstagramContent, InstagramMetadata,
    PlatformContentExtension,
] 