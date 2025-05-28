"""
Data Transfer Objects (DTOs) for Core Services

DTOs provide clean interfaces between controllers and services,
ensuring data structure consistency and type safety.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from data.models import ContentType, ContentStatus, PlatformType


@dataclass(frozen=True)
class ContentDTO:
    """Data Transfer Object for content information"""
    
    id: Optional[int] = None
    url: str = ""
    platform: Optional[PlatformType] = None
    content_type: Optional[ContentType] = None
    title: Optional[str] = None
    author: Optional[str] = None
    platform_id: Optional[str] = None
    status: ContentStatus = ContentStatus.PENDING
    
    # Media information
    duration: Optional[int] = None
    file_size: Optional[int] = None
    file_path: Optional[str] = None
    thumbnail_url: Optional[str] = None
    
    # Download information
    download_progress: int = 0
    download_started_at: Optional[datetime] = None
    downloaded_at: Optional[datetime] = None
    
    # Error handling
    retry_count: int = 0
    error_message: Optional[str] = None
    
    # Metadata
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_model(cls, model) -> 'ContentDTO':
        """Create DTO from ContentModel"""
        return cls(
            id=model.id,
            url=model.url,
            platform=model.platform,
            content_type=model.content_type,
            title=model.title,
            author=model.author,
            platform_id=model.platform_id,
            status=model.status,
            duration=model.duration,
            file_size=model.file_size,
            file_path=model.file_path,
            thumbnail_url=model.thumbnail_url,
            download_progress=model.download_progress,
            download_started_at=model.download_started_at,
            downloaded_at=model.downloaded_at,
            retry_count=model.retry_count,
            error_message=model.error_message,
            description=model.description,
            tags=model.tags or [],
            metadata=model.metadata or {},
            created_at=model.created_at,
            updated_at=model.updated_at
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert DTO to dictionary for JSON serialization"""
        result = {}
        for field_name, field_value in self.__dict__.items():
            if isinstance(field_value, (datetime,)):
                result[field_name] = field_value.isoformat() if field_value else None
            elif isinstance(field_value, (PlatformType, ContentType, ContentStatus)):
                result[field_name] = field_value.value if field_value else None
            else:
                result[field_name] = field_value
        return result


@dataclass(frozen=True)
class DownloadRequestDTO:
    """Data Transfer Object for download requests"""
    
    url: str
    platform: Optional[PlatformType] = None
    quality: str = "best"
    format_preference: str = "mp4"
    output_path: Optional[str] = None
    
    # Additional options
    extract_audio: bool = False
    extract_thumbnail: bool = True
    subtitle_languages: List[str] = field(default_factory=list)
    
    # Metadata
    custom_filename: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DownloadProgressDTO:
    """Data Transfer Object for download progress updates"""
    
    content_id: int
    progress_percentage: float
    download_speed: Optional[float] = None  # bytes per second
    eta_seconds: Optional[int] = None  # estimated time to completion
    downloaded_bytes: int = 0
    total_bytes: Optional[int] = None
    status: ContentStatus = ContentStatus.DOWNLOADING
    
    # Error information
    error_message: Optional[str] = None
    
    # Timestamps
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class PlatformStatsDTO:
    """Data Transfer Object for platform statistics"""
    
    platform: PlatformType
    total_content: int = 0
    completed_downloads: int = 0
    failed_downloads: int = 0
    pending_downloads: int = 0
    in_progress_downloads: int = 0
    
    # Storage statistics
    total_storage_bytes: int = 0
    average_file_size: float = 0.0
    
    # Performance statistics
    success_rate: float = 0.0
    average_download_time: float = 0.0
    
    # Time-based statistics
    downloads_today: int = 0
    downloads_this_week: int = 0
    downloads_this_month: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'platform': self.platform.value,
            'total_content': self.total_content,
            'completed_downloads': self.completed_downloads,
            'failed_downloads': self.failed_downloads,
            'pending_downloads': self.pending_downloads,
            'in_progress_downloads': self.in_progress_downloads,
            'total_storage_bytes': self.total_storage_bytes,
            'average_file_size': self.average_file_size,
            'success_rate': self.success_rate,
            'average_download_time': self.average_download_time,
            'downloads_today': self.downloads_today,
            'downloads_this_week': self.downloads_this_week,
            'downloads_this_month': self.downloads_this_month,
        }


@dataclass(frozen=True)
class ContentSearchResultDTO:
    """Data Transfer Object for content search results"""
    
    content: ContentDTO
    relevance_score: float = 0.0
    matching_fields: List[str] = field(default_factory=list)
    snippet: Optional[str] = None


@dataclass(frozen=True) 
class AnalyticsDTO:
    """Data Transfer Object for analytics data"""
    
    # Overall statistics
    total_downloads: int = 0
    successful_downloads: int = 0
    failed_downloads: int = 0
    success_rate: float = 0.0
    
    # Platform breakdown
    platform_stats: Dict[str, PlatformStatsDTO] = field(default_factory=dict)
    
    # Time-based statistics
    downloads_by_day: Dict[str, int] = field(default_factory=dict)  # ISO date -> count
    downloads_by_hour: Dict[int, int] = field(default_factory=dict)  # hour -> count
    
    # Content type statistics
    video_downloads: int = 0
    audio_downloads: int = 0
    image_downloads: int = 0
    
    # Storage statistics
    total_storage_used: int = 0  # bytes
    average_file_size: float = 0.0
    largest_file_size: int = 0
    
    # Performance statistics
    average_download_speed: float = 0.0  # bytes per second
    fastest_download_speed: float = 0.0
    average_download_time: float = 0.0  # seconds
    
    # Error statistics
    common_errors: Dict[str, int] = field(default_factory=dict)  # error message -> count
    
    # Generated timestamp
    generated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'total_downloads': self.total_downloads,
            'successful_downloads': self.successful_downloads,
            'failed_downloads': self.failed_downloads,
            'success_rate': self.success_rate,
            'platform_stats': {
                platform: stats.to_dict() 
                for platform, stats in self.platform_stats.items()
            },
            'downloads_by_day': self.downloads_by_day,
            'downloads_by_hour': self.downloads_by_hour,
            'video_downloads': self.video_downloads,
            'audio_downloads': self.audio_downloads,
            'image_downloads': self.image_downloads,
            'total_storage_used': self.total_storage_used,
            'average_file_size': self.average_file_size,
            'largest_file_size': self.largest_file_size,
            'average_download_speed': self.average_download_speed,
            'fastest_download_speed': self.fastest_download_speed,
            'average_download_time': self.average_download_time,
            'common_errors': self.common_errors,
            'generated_at': self.generated_at.isoformat()
        }


# Utility functions for DTO conversion

def content_model_to_dto(model) -> ContentDTO:
    """Convert ContentModel to ContentDTO"""
    return ContentDTO.from_model(model)


def content_models_to_dtos(models: List) -> List[ContentDTO]:
    """Convert list of ContentModels to list of ContentDTOs"""
    return [ContentDTO.from_model(model) for model in models]


def dto_to_content_model(dto: ContentDTO):
    """Convert ContentDTO to ContentModel for database operations"""
    from data.models import ContentModel
    
    return ContentModel(
        id=dto.id,
        url=dto.url,
        platform=dto.platform,
        content_type=dto.content_type,
        title=dto.title,
        author=dto.author,
        platform_id=dto.platform_id,
        status=dto.status,
        duration=dto.duration,
        file_size=dto.file_size,
        file_path=dto.file_path,
        thumbnail_url=dto.thumbnail_url,
        download_progress=dto.download_progress,
        download_started_at=dto.download_started_at,
        downloaded_at=dto.downloaded_at,
        retry_count=dto.retry_count,
        error_message=dto.error_message,
        description=dto.description,
        tags=dto.tags,
        metadata=dto.metadata,
        created_at=dto.created_at,
        updated_at=dto.updated_at
    ) 