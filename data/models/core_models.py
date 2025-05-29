"""
Core Data Models for Social Download Manager v2.0

Core Pydantic models that map directly to the database schema,
providing type-safe representations of all main entities.
"""

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, ClassVar
from uuid import UUID

from pydantic import Field, field_validator, computed_field

from .pydantic_models import (
    DatabaseEntity,
    ContentType,
    ContentStatus,
    DownloadStatus,
    SessionType,
    SessionStatus,
    TagType,
    DataType,
    validate_url,
    validate_json_string,
    validate_positive_numeric,
    validate_percentage,
    validate_slug
)


# =============================================================================
# PLATFORM MODEL
# =============================================================================

class Platform(DatabaseEntity):
    """Platform entity representing supported social media platforms"""
    
    _table_name: ClassVar[str] = "platforms"
    
    # Core fields
    name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Platform internal name (lowercase, no spaces)"
    )
    display_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Platform display name"
    )
    base_url: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Platform base URL"
    )
    api_endpoint: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Platform API endpoint"
    )
    is_active: bool = Field(
        default=True,
        description="Whether platform is currently active"
    )
    supported_content_types: str = Field(
        default="[]",
        description="JSON array of supported content types"
    )
    metadata: str = Field(
        default="{}",
        description="JSON object with platform-specific metadata"
    )
    
    @field_validator('name')
    @classmethod
    def validate_name_format(cls, v: str) -> str:
        """Validate platform name format"""
        v = v.strip().lower()
        if ' ' in v:
            raise ValueError("Platform name cannot contain spaces")
        return v
    
    @field_validator('base_url', 'api_endpoint')
    @classmethod
    def validate_urls(cls, v: Optional[str]) -> Optional[str]:
        """Validate URL fields"""
        if v is not None:
            return validate_url(v)
        return v
    
    @field_validator('supported_content_types', 'metadata')
    @classmethod
    def validate_json_fields(cls, v: str) -> str:
        """Validate JSON string fields"""
        return validate_json_string(v)


# =============================================================================
# CONTENT MODEL
# =============================================================================

class Content(DatabaseEntity):
    """Core content entity representing downloadable content"""
    
    _table_name: ClassVar[str] = "content"
    
    # Required fields
    platform_id: int = Field(
        ...,
        description="Reference to platform"
    )
    original_url: str = Field(
        ...,
        description="Original content URL"
    )
    content_type: ContentType = Field(
        default=ContentType.VIDEO,
        description="Type of content"
    )
    status: ContentStatus = Field(
        default=ContentStatus.PENDING,
        description="Current content status"
    )
    
    # Optional identifiers
    platform_content_id: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Platform-specific content ID"
    )
    canonical_url: Optional[str] = Field(
        default=None,
        description="Canonical URL for the content"
    )
    
    # Content information
    title: Optional[str] = Field(
        default=None,
        description="Content title"
    )
    description: Optional[str] = Field(
        default=None,
        description="Content description"
    )
    
    # Creator information
    author_name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Content creator name"
    )
    author_id: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Platform-specific creator ID"
    )
    author_url: Optional[str] = Field(
        default=None,
        description="Creator profile URL"
    )
    
    # Media properties
    duration_seconds: Optional[int] = Field(
        default=None,
        ge=0,
        description="Content duration in seconds"
    )
    file_size_bytes: Optional[int] = Field(
        default=None,
        ge=0,
        description="File size in bytes"
    )
    file_format: Optional[str] = Field(
        default=None,
        max_length=20,
        description="File format (mp4, mp3, etc.)"
    )
    
    # Engagement metrics
    view_count: int = Field(
        default=0,
        ge=0,
        description="Number of views"
    )
    like_count: int = Field(
        default=0,
        ge=0,
        description="Number of likes"
    )
    comment_count: int = Field(
        default=0,
        ge=0,
        description="Number of comments"
    )
    share_count: int = Field(
        default=0,
        ge=0,
        description="Number of shares"
    )
    
    # Publication info
    published_at: Optional[datetime] = Field(
        default=None,
        description="When content was published"
    )
    
    # Download info
    local_file_path: Optional[str] = Field(
        default=None,
        description="Local file path after download"
    )
    thumbnail_path: Optional[str] = Field(
        default=None,
        description="Local thumbnail path"
    )
    download_quality: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Downloaded quality"
    )
    
    @field_validator('original_url', 'canonical_url', 'author_url')
    @classmethod
    def validate_urls(cls, v: Optional[str]) -> Optional[str]:
        """Validate URL fields"""
        if v is not None:
            return validate_url(v)
        return v
    
    @computed_field
    @property
    def engagement_total(self) -> int:
        """Total engagement count"""
        return self.view_count + self.like_count + self.comment_count + self.share_count


# =============================================================================
# CONTENT METADATA MODEL
# =============================================================================

class ContentMetadata(DatabaseEntity):
    """Platform-specific metadata for content"""
    
    _table_name: ClassVar[str] = "content_metadata"
    
    content_id: int = Field(
        ...,
        description="Reference to content"
    )
    metadata_type: str = Field(
        ...,
        max_length=100,
        description="Type/category of metadata"
    )
    metadata_key: str = Field(
        ...,
        max_length=255,
        description="Metadata key"
    )
    metadata_value: Optional[str] = Field(
        default=None,
        description="Metadata value"
    )
    data_type: DataType = Field(
        default=DataType.STRING,
        description="Data type of the value"
    )
    parent_key: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Parent key for hierarchical metadata"
    )
    
    @field_validator('metadata_key')
    @classmethod
    def validate_metadata_key(cls, v: str) -> str:
        """Validate metadata key is not empty"""
        if not v.strip():
            raise ValueError("Metadata key cannot be empty")
        return v.strip()


# =============================================================================
# DOWNLOAD MODELS
# =============================================================================

class Download(DatabaseEntity):
    """Download entity representing a download request"""
    
    _table_name: ClassVar[str] = "downloads"
    
    # Required fields
    content_id: int = Field(
        ...,
        description="Reference to content being downloaded"
    )
    output_directory: str = Field(
        ...,
        description="Directory for downloaded files"
    )
    
    # Download configuration
    requested_quality: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Requested quality"
    )
    requested_format: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Requested file format"
    )
    custom_filename: Optional[str] = Field(
        default=None,
        description="Custom filename override"
    )
    
    # Status and progress
    status: DownloadStatus = Field(
        default=DownloadStatus.QUEUED,
        description="Current download status"
    )
    progress_percentage: Decimal = Field(
        default=Decimal('0.00'),
        ge=Decimal('0.00'),
        le=Decimal('100.00'),
        description="Download progress percentage"
    )
    current_speed_bps: Optional[int] = Field(
        default=None,
        ge=0,
        description="Current download speed in bytes per second"
    )
    average_speed_bps: Optional[int] = Field(
        default=None,
        ge=0,
        description="Average download speed in bytes per second"
    )
    
    # File information
    final_filename: Optional[str] = Field(
        default=None,
        description="Final filename after download"
    )
    final_file_path: Optional[str] = Field(
        default=None,
        description="Final file path after download"
    )
    actual_file_size: Optional[int] = Field(
        default=None,
        ge=0,
        description="Actual downloaded file size"
    )
    actual_format: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Actual file format"
    )
    actual_quality: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Actual quality downloaded"
    )
    
    # Timing
    queued_at: Optional[datetime] = Field(
        default=None,
        description="When download was queued"
    )
    started_at: Optional[datetime] = Field(
        default=None,
        description="When download started"
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="When download completed"
    )
    
    # Error handling
    error_count: int = Field(
        default=0,
        ge=0,
        description="Number of errors encountered"
    )
    last_error_message: Optional[str] = Field(
        default=None,
        description="Last error message"
    )
    retry_count: int = Field(
        default=0,
        ge=0,
        description="Number of retries attempted"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum number of retries allowed"
    )
    
    # Configuration
    downloader_engine: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Downloader engine used"
    )
    download_options: str = Field(
        default="{}",
        description="JSON configuration options"
    )
    
    @field_validator('download_options')
    @classmethod
    def validate_download_options(cls, v: str) -> str:
        """Validate download options JSON"""
        return validate_json_string(v)
    
    @computed_field
    @property
    def can_retry(self) -> bool:
        """Check if download can be retried"""
        return self.retry_count < self.max_retries and self.status == DownloadStatus.FAILED


class DownloadSession(DatabaseEntity):
    """Download session for detailed tracking"""
    
    _table_name: ClassVar[str] = "download_sessions"
    
    # Required fields
    download_id: int = Field(
        ...,
        description="Reference to download"
    )
    session_uuid: str = Field(
        ...,
        min_length=36,
        max_length=36,
        description="Unique session identifier"
    )
    
    # Session configuration
    session_type: SessionType = Field(
        default=SessionType.STANDARD,
        description="Type of download session"
    )
    session_status: SessionStatus = Field(
        default=SessionStatus.ACTIVE,
        description="Current session status"
    )
    
    # Progress tracking
    bytes_downloaded: int = Field(
        default=0,
        ge=0,
        description="Bytes downloaded in this session"
    )
    total_bytes: Optional[int] = Field(
        default=None,
        ge=0,
        description="Total bytes to download"
    )
    chunks_completed: int = Field(
        default=0,
        ge=0,
        description="Number of chunks completed"
    )
    total_chunks: Optional[int] = Field(
        default=None,
        ge=0,
        description="Total number of chunks"
    )
    
    # Performance metrics
    peak_speed_bps: Optional[int] = Field(
        default=None,
        ge=0,
        description="Peak download speed"
    )
    average_speed_bps: Optional[int] = Field(
        default=None,
        ge=0,
        description="Average download speed"
    )
    connection_count: int = Field(
        default=1,
        ge=1,
        description="Number of connections used"
    )
    
    # Session timing
    session_started_at: Optional[datetime] = Field(
        default=None,
        description="When session started"
    )
    session_ended_at: Optional[datetime] = Field(
        default=None,
        description="When session ended"
    )
    session_duration_seconds: Optional[int] = Field(
        default=None,
        ge=0,
        description="Session duration in seconds"
    )
    
    # Session configuration
    user_agent: Optional[str] = Field(
        default=None,
        description="User agent used for session"
    )
    headers: str = Field(
        default="{}",
        description="HTTP headers used (JSON)"
    )
    proxy_used: Optional[str] = Field(
        default=None,
        description="Proxy server used"
    )
    
    # Status
    termination_reason: Optional[str] = Field(
        default=None,
        description="Reason for session termination"
    )
    
    @field_validator('session_uuid')
    @classmethod
    def validate_session_uuid(cls, v: str) -> str:
        """Validate UUID format"""
        if len(v) != 36:
            raise ValueError("Session UUID must be 36 characters long")
        return v
    
    @field_validator('headers')
    @classmethod
    def validate_headers(cls, v: str) -> str:
        """Validate headers JSON"""
        return validate_json_string(v)
    
    @computed_field
    @property
    def progress_percentage(self) -> float:
        """Calculate download progress percentage"""
        if self.total_bytes and self.total_bytes > 0:
            return min(100.0, (self.bytes_downloaded / self.total_bytes) * 100.0)
        return 0.0


class DownloadError(DatabaseEntity):
    """Download error tracking"""
    
    _table_name: ClassVar[str] = "download_errors"
    
    # Required fields
    download_id: int = Field(
        ...,
        description="Reference to download"
    )
    error_type: str = Field(
        ...,
        max_length=100,
        description="Type/category of error"
    )
    error_message: str = Field(
        ...,
        description="Error message"
    )
    
    # Optional fields
    session_id: Optional[int] = Field(
        default=None,
        description="Reference to download session"
    )
    error_code: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Error code"
    )
    
    # Technical details
    stack_trace: Optional[str] = Field(
        default=None,
        description="Error stack trace"
    )
    request_url: Optional[str] = Field(
        default=None,
        description="URL that caused the error"
    )
    response_headers: Optional[str] = Field(
        default=None,
        description="Response headers (JSON)"
    )
    user_agent: Optional[str] = Field(
        default=None,
        description="User agent used"
    )
    
    # Context information
    retry_attempt: int = Field(
        default=0,
        ge=0,
        description="Retry attempt number"
    )
    occurred_at: Optional[datetime] = Field(
        default=None,
        description="When error occurred"
    )
    
    # Resolution tracking
    is_resolved: bool = Field(
        default=False,
        description="Whether error has been resolved"
    )
    resolution_method: Optional[str] = Field(
        default=None,
        description="How error was resolved"
    )
    resolved_at: Optional[datetime] = Field(
        default=None,
        description="When error was resolved"
    )
    
    @field_validator('error_type', 'error_message')
    @classmethod
    def validate_required_text(cls, v: str) -> str:
        """Validate required text fields are not empty"""
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()
    
    @field_validator('request_url')
    @classmethod
    def validate_request_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate request URL"""
        if v is not None:
            return validate_url(v)
        return v
    
    @field_validator('response_headers')
    @classmethod
    def validate_response_headers(cls, v: Optional[str]) -> Optional[str]:
        """Validate response headers JSON"""
        if v is not None:
            return validate_json_string(v)
        return v


# =============================================================================
# QUALITY OPTIONS MODEL
# =============================================================================

class QualityOption(DatabaseEntity):
    """Available quality options for content"""
    
    _table_name: ClassVar[str] = "quality_options"
    
    # Required fields
    content_id: int = Field(
        ...,
        description="Reference to content"
    )
    quality_label: str = Field(
        ...,
        max_length=50,
        description="Quality label (e.g., '1080p', 'HD')"
    )
    format: str = Field(
        ...,
        max_length=20,
        description="File format (e.g., 'mp4', 'mp3')"
    )
    
    # Technical specifications
    resolution_width: Optional[int] = Field(
        default=None,
        gt=0,
        description="Video width in pixels"
    )
    resolution_height: Optional[int] = Field(
        default=None,
        gt=0,
        description="Video height in pixels"
    )
    bitrate_kbps: Optional[int] = Field(
        default=None,
        gt=0,
        description="Bitrate in kilobits per second"
    )
    fps: Optional[Decimal] = Field(
        default=None,
        gt=Decimal('0'),
        description="Frames per second"
    )
    audio_bitrate_kbps: Optional[int] = Field(
        default=None,
        gt=0,
        description="Audio bitrate in kbps"
    )
    
    # File information
    estimated_file_size: Optional[int] = Field(
        default=None,
        ge=0,
        description="Estimated file size in bytes"
    )
    codec: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Video codec"
    )
    audio_codec: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Audio codec"
    )
    
    # Availability
    is_available: bool = Field(
        default=True,
        description="Whether quality is currently available"
    )
    download_url: Optional[str] = Field(
        default=None,
        description="Direct download URL"
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="When download URL expires"
    )
    
    @field_validator('quality_label', 'format')
    @classmethod
    def validate_required_fields(cls, v: str) -> str:
        """Validate required text fields"""
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()
    
    @field_validator('download_url')
    @classmethod
    def validate_download_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate download URL"""
        if v is not None:
            return validate_url(v)
        return v
    
    @computed_field
    @property
    def resolution_string(self) -> Optional[str]:
        """Get resolution as string (e.g., '1920x1080')"""
        if self.resolution_width and self.resolution_height:
            return f"{self.resolution_width}x{self.resolution_height}"
        return None


# =============================================================================
# TAG MODELS
# =============================================================================

class Tag(DatabaseEntity):
    """Tag entity for content organization"""
    
    _table_name: ClassVar[str] = "tags"
    
    # Required fields
    name: str = Field(
        ...,
        max_length=100,
        description="Tag name"
    )
    slug: str = Field(
        ...,
        max_length=100,
        description="URL-friendly tag slug"
    )
    
    # Optional fields
    description: Optional[str] = Field(
        default=None,
        description="Tag description"
    )
    tag_type: TagType = Field(
        default=TagType.USER,
        description="Type of tag"
    )
    usage_count: int = Field(
        default=0,
        ge=0,
        description="Number of times tag is used"
    )
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate tag name"""
        if not v.strip():
            raise ValueError("Tag name cannot be empty")
        return v.strip()
    
    @field_validator('slug')
    @classmethod
    def validate_slug_format(cls, v: str) -> str:
        """Validate slug format"""
        return validate_slug(v)


class ContentTag(DatabaseEntity):
    """Junction table for content-tag relationships"""
    
    _table_name: ClassVar[str] = "content_tags"
    
    # Required fields (composite primary key)
    content_id: int = Field(
        ...,
        description="Reference to content"
    )
    tag_id: int = Field(
        ...,
        description="Reference to tag"
    )
    
    # Relationship metadata
    assigned_by: str = Field(
        default="user",
        description="Who/what assigned this tag"
    )
    confidence_score: Optional[Decimal] = Field(
        default=None,
        ge=Decimal('0.00'),
        le=Decimal('1.00'),
        description="Confidence score for auto-assigned tags"
    )
    
    @field_validator('assigned_by')
    @classmethod
    def validate_assigned_by(cls, v: str) -> str:
        """Validate assigned_by field"""
        valid_values = ['user', 'auto', 'import', 'system']
        if v not in valid_values:
            raise ValueError(f"assigned_by must be one of: {valid_values}")
        return v


# =============================================================================
# SUPPORTING MODELS
# =============================================================================

class SchemaMigration(DatabaseEntity):
    """Schema migration tracking"""
    
    _table_name: ClassVar[str] = "schema_migrations"
    
    # Required fields
    version: str = Field(
        ...,
        max_length=50,
        description="Migration version"
    )
    
    # Optional fields
    description: Optional[str] = Field(
        default=None,
        description="Migration description"
    )
    migration_file: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Migration file name"
    )
    
    # Execution tracking
    executed_at: Optional[datetime] = Field(
        default=None,
        description="When migration was executed"
    )
    execution_time_ms: Optional[int] = Field(
        default=None,
        ge=0,
        description="Execution time in milliseconds"
    )
    success: bool = Field(
        default=True,
        description="Whether migration succeeded"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if migration failed"
    )
    
    # Rollback information
    rollback_file: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Rollback file name"
    )
    can_rollback: bool = Field(
        default=False,
        description="Whether migration can be rolled back"
    )
    
    @field_validator('version')
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate version is not empty"""
        if not v.strip():
            raise ValueError("Version cannot be empty")
        return v.strip()


class ApplicationSetting(DatabaseEntity):
    """Application settings storage"""
    
    _table_name: ClassVar[str] = "application_settings"
    
    # Required fields
    setting_key: str = Field(
        ...,
        max_length=255,
        description="Setting key"
    )
    
    # Optional fields
    setting_value: Optional[str] = Field(
        default=None,
        description="Setting value"
    )
    data_type: DataType = Field(
        default=DataType.STRING,
        description="Data type of the setting value"
    )
    description: Optional[str] = Field(
        default=None,
        description="Setting description"
    )
    
    # Validation
    is_required: bool = Field(
        default=False,
        description="Whether setting is required"
    )
    default_value: Optional[str] = Field(
        default=None,
        description="Default value for the setting"
    )
    validation_regex: Optional[str] = Field(
        default=None,
        description="Regex pattern for validation"
    )
    
    @field_validator('setting_key')
    @classmethod
    def validate_setting_key(cls, v: str) -> str:
        """Validate setting key"""
        if not v.strip():
            raise ValueError("Setting key cannot be empty")
        return v.strip()


# =============================================================================
# MODEL REGISTRY
# =============================================================================

# Registry of all core models for easy access
CORE_MODELS = {
    'platform': Platform,
    'content': Content,
    'content_metadata': ContentMetadata,
    'download': Download,
    'download_session': DownloadSession,
    'download_error': DownloadError,
    'quality_option': QualityOption,
    'tag': Tag,
    'content_tag': ContentTag,
    'schema_migration': SchemaMigration,
    'application_setting': ApplicationSetting,
}

# Model lookup by table name
MODELS_BY_TABLE = {
    model._table_name: model 
    for model in CORE_MODELS.values()
} 