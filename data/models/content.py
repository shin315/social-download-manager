"""
Content Models for Social Download Manager v2.0

Defines content entities for different types of social media content
including videos, images, audio, and posts from various platforms.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import json
from dataclasses import asdict

from .base import BaseEntity, BaseModel, ValidationError, EntityId, JsonData


class ContentType(Enum):
    """Types of downloadable content"""
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    POST = "post"
    STORY = "story"
    REEL = "reel"
    LIVESTREAM = "livestream"
    PLAYLIST = "playlist"


class ContentStatus(Enum):
    """Status of content processing"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class PlatformType(Enum):
    """Supported social media platforms"""
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    TWITCH = "twitch"
    UNKNOWN = "unknown"


@dataclass
class QualityOption:
    """Represents a quality option for content"""
    quality_id: str
    resolution: Optional[str] = None
    bitrate: Optional[int] = None
    format: Optional[str] = None
    file_size: Optional[int] = None
    duration: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'quality_id': self.quality_id,
            'resolution': self.resolution,
            'bitrate': self.bitrate,
            'format': self.format,
            'file_size': self.file_size,
            'duration': self.duration
        }


@dataclass
class ContentModel(BaseEntity):
    """
    Base content entity for all types of downloadable content
    
    Contains common fields for any content from social media platforms.
    """
    # Core content information
    url: str = ""
    platform: PlatformType = PlatformType.UNKNOWN
    content_type: ContentType = ContentType.VIDEO
    status: ContentStatus = ContentStatus.PENDING
    
    # Content metadata
    title: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    author_id: Optional[str] = None
    thumbnail_url: Optional[str] = None
    
    # Platform-specific identifiers
    platform_id: Optional[str] = None  # Original ID from platform
    platform_url: Optional[str] = None  # Clean platform URL
    
    # Content properties
    duration: Optional[float] = None  # Duration in seconds
    file_size: Optional[int] = None   # File size in bytes
    format: Optional[str] = None      # File format (mp4, mp3, jpg, etc.)
    quality: Optional[str] = None     # Quality setting used
    
    # Download information
    local_path: Optional[str] = None  # Path to downloaded file
    download_progress: float = 0.0    # Progress percentage (0-100)
    download_speed: Optional[float] = None  # Download speed in bytes/sec
    
    # Content stats (from platform)
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    share_count: Optional[int] = None
    
    # Publication info
    published_at: Optional[datetime] = None
    
    # Quality options available
    available_qualities: List[QualityOption] = field(default_factory=list)
    
    # Additional metadata
    hashtags: List[str] = field(default_factory=list)
    mentions: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize after creation"""
        super().__post_init__()
        
        # Ensure URL is provided
        if not self.url:
            raise ValueError("Content URL is required")
        
        # Set platform_url if not provided
        if not self.platform_url:
            self.platform_url = self.url
    
    def get_display_name(self) -> str:
        """Get a display-friendly name for the content"""
        if self.title:
            return self.title
        elif self.platform_id:
            return f"{self.platform.value}_{self.platform_id}"
        else:
            return f"content_{self.id}"
    
    def is_downloaded(self) -> bool:
        """Check if content has been successfully downloaded"""
        return self.status == ContentStatus.COMPLETED and self.local_path is not None
    
    def get_file_extension(self) -> Optional[str]:
        """Get the file extension based on format"""
        if not self.format:
            return None
        
        format_map = {
            'mp4': 'mp4',
            'webm': 'webm',
            'mkv': 'mkv',
            'mp3': 'mp3',
            'wav': 'wav',
            'jpg': 'jpg',
            'png': 'png',
            'gif': 'gif'
        }
        
        return format_map.get(self.format.lower())

    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary with proper type conversion"""
        data = super().to_dict()  # Get base conversion
        
        # Serialize complex fields as JSON
        if self.available_qualities:
            data['available_qualities'] = json.dumps([q.to_dict() if hasattr(q, 'to_dict') else asdict(q) for q in self.available_qualities])
        else:
            data['available_qualities'] = "[]"
        
        if self.hashtags:
            data['hashtags'] = json.dumps(self.hashtags)
        else:
            data['hashtags'] = "[]"
        
        if self.mentions:
            data['mentions'] = json.dumps(self.mentions)
        else:
            data['mentions'] = "[]"
        
        # Convert enum values to strings
        data['platform'] = self.platform.value
        data['content_type'] = self.content_type.value
        data['status'] = self.status.value
        
        # Convert datetime to ISO string
        if self.published_at:
            data['published_at'] = self.published_at.isoformat()
        
        # Ensure metadata is JSON string (not dict)
        if isinstance(data.get('metadata'), dict):
            data['metadata'] = json.dumps(data['metadata'])
        elif not data.get('metadata'):
            data['metadata'] = "{}"
        
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContentModel':
        """Create entity from dictionary with proper type conversion"""
        # Create a copy to avoid modifying original
        data_copy = data.copy()
        
        # Deserialize JSON fields
        if 'available_qualities' in data_copy and data_copy['available_qualities']:
            try:
                qualities_data = json.loads(data_copy['available_qualities'])
                data_copy['available_qualities'] = [QualityOption(**q) for q in qualities_data]
            except (json.JSONDecodeError, TypeError):
                data_copy['available_qualities'] = []
        
        if 'hashtags' in data_copy and data_copy['hashtags']:
            try:
                data_copy['hashtags'] = json.loads(data_copy['hashtags'])
            except (json.JSONDecodeError, TypeError):
                data_copy['hashtags'] = []
        
        if 'mentions' in data_copy and data_copy['mentions']:
            try:
                data_copy['mentions'] = json.loads(data_copy['mentions'])
            except (json.JSONDecodeError, TypeError):
                data_copy['mentions'] = []
        
        # Convert enum strings to enums
        if 'platform' in data_copy:
            data_copy['platform'] = PlatformType(data_copy['platform'])
        
        if 'content_type' in data_copy:
            data_copy['content_type'] = ContentType(data_copy['content_type'])
        
        if 'status' in data_copy:
            data_copy['status'] = ContentStatus(data_copy['status'])
        
        # Convert datetime strings
        if 'published_at' in data_copy and data_copy['published_at']:
            try:
                data_copy['published_at'] = datetime.fromisoformat(data_copy['published_at'])
            except (ValueError, TypeError):
                data_copy['published_at'] = None
        
        return cls(**data_copy)

    @classmethod
    def from_row(cls, row) -> 'ContentModel':
        """Create entity from database row"""
        # Convert sqlite3.Row to dict properly
        data = {key: row[key] for key in row.keys()}
        return cls.from_dict(data)


@dataclass 
class VideoContent(ContentModel):
    """Specialized content model for video content"""
    content_type: ContentType = ContentType.VIDEO
    
    # Video-specific properties
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    
    # Video quality metrics
    video_bitrate: Optional[int] = None
    audio_bitrate: Optional[int] = None
    
    def get_resolution_string(self) -> Optional[str]:
        """Get resolution as string (e.g., '1920x1080')"""
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return None
    
    def is_hd(self) -> bool:
        """Check if video is HD quality"""
        return self.height is not None and self.height >= 720
    
    def is_4k(self) -> bool:
        """Check if video is 4K quality"""
        return self.height is not None and self.height >= 2160


@dataclass
class AudioContent(ContentModel):
    """Specialized content model for audio content"""
    content_type: ContentType = ContentType.AUDIO
    
    # Audio-specific properties
    audio_codec: Optional[str] = None
    audio_bitrate: Optional[int] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    
    # Music metadata
    artist: Optional[str] = None
    album: Optional[str] = None
    genre: Optional[str] = None
    
    def is_high_quality(self) -> bool:
        """Check if audio is high quality"""
        return self.audio_bitrate is not None and self.audio_bitrate >= 256


@dataclass
class ImageContent(ContentModel):
    """Specialized content model for image content"""
    content_type: ContentType = ContentType.IMAGE
    
    # Image-specific properties
    width: Optional[int] = None
    height: Optional[int] = None
    image_format: Optional[str] = None
    color_depth: Optional[int] = None
    
    def get_resolution_string(self) -> Optional[str]:
        """Get resolution as string"""
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return None
    
    def get_aspect_ratio(self) -> Optional[float]:
        """Get aspect ratio"""
        if self.width and self.height:
            return self.width / self.height
        return None


@dataclass
class PostContent(ContentModel):
    """Specialized content model for text posts and mixed content"""
    content_type: ContentType = ContentType.POST
    
    # Post-specific properties
    text_content: Optional[str] = None
    attached_media: List[str] = field(default_factory=list)  # URLs to attached media
    
    # Social engagement
    replies_count: Optional[int] = None
    repost_count: Optional[int] = None
    
    def has_media(self) -> bool:
        """Check if post has attached media"""
        return len(self.attached_media) > 0
    
    def get_text_preview(self, max_length: int = 100) -> str:
        """Get a preview of the text content"""
        if not self.text_content:
            return ""
        
        if len(self.text_content) <= max_length:
            return self.text_content
        
        return self.text_content[:max_length-3] + "..."


class ContentModelManager(BaseModel[ContentModel]):
    """Model manager for content entities"""
    
    def get_table_name(self) -> str:
        return "content"
    
    def get_entity_class(self) -> type:
        return ContentModel
    
    def get_schema(self) -> str:
        """Get the CREATE TABLE SQL schema for content"""
        return """
        CREATE TABLE IF NOT EXISTS content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            platform TEXT NOT NULL,
            content_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            
            -- Content metadata
            title TEXT,
            description TEXT,
            author TEXT,
            author_id TEXT,
            thumbnail_url TEXT,
            
            -- Platform identifiers
            platform_id TEXT,
            platform_url TEXT,
            
            -- Content properties
            duration REAL,
            file_size INTEGER,
            format TEXT,
            quality TEXT,
            
            -- Download information
            local_path TEXT,
            download_progress REAL DEFAULT 0.0,
            download_speed REAL,
            
            -- Content stats
            view_count INTEGER,
            like_count INTEGER,
            comment_count INTEGER,
            share_count INTEGER,
            
            -- Publication info
            published_at TEXT,
            
            -- Additional data
            available_qualities TEXT,  -- JSON array
            hashtags TEXT,             -- JSON array
            mentions TEXT,             -- JSON array
            
            -- Base entity fields
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            version INTEGER DEFAULT 1,
            is_deleted INTEGER DEFAULT 0,
            metadata TEXT              -- JSON object
        );
        
        -- Create unique constraint separately
        CREATE UNIQUE INDEX IF NOT EXISTS idx_content_platform_id 
        ON content(platform, platform_id) 
        WHERE platform_id IS NOT NULL;
        
        -- Create other indexes
        CREATE INDEX IF NOT EXISTS idx_content_platform ON content(platform);
        CREATE INDEX IF NOT EXISTS idx_content_status ON content(status);
        CREATE INDEX IF NOT EXISTS idx_content_type ON content(content_type);
        CREATE INDEX IF NOT EXISTS idx_content_author ON content(author);
        CREATE INDEX IF NOT EXISTS idx_content_created ON content(created_at);
        """
    
    def validate_entity(self, entity: ContentModel) -> List[ValidationError]:
        """Validate content entity"""
        errors = super().validate_entity(entity)
        
        # Validate required fields
        if not entity.url:
            errors.append(ValidationError('url', entity.url, 'URL is required'))
        
        # Validate enums
        if not isinstance(entity.platform, PlatformType):
            errors.append(ValidationError('platform', entity.platform, 'Invalid platform type'))
        
        if not isinstance(entity.content_type, ContentType):
            errors.append(ValidationError('content_type', entity.content_type, 'Invalid content type'))
        
        if not isinstance(entity.status, ContentStatus):
            errors.append(ValidationError('status', entity.status, 'Invalid content status'))
        
        # Validate progress
        if entity.download_progress < 0 or entity.download_progress > 100:
            errors.append(ValidationError('download_progress', entity.download_progress, 'Progress must be between 0 and 100'))
        
        return errors
    
    def find_by_url(self, url: str) -> Optional[ContentModel]:
        """Find content by URL"""
        results = self.find_by_criteria({'url': url})
        return results[0] if results else None
    
    def find_by_platform_id(self, platform: PlatformType, platform_id: str) -> Optional[ContentModel]:
        """Find content by platform and platform ID"""
        results = self.find_by_criteria({
            'platform': platform.value,
            'platform_id': platform_id
        })
        return results[0] if results else None
    
    def find_by_status(self, status: ContentStatus) -> List[ContentModel]:
        """Find content by status"""
        return self.find_by_criteria({'status': status.value})
    
    def find_by_platform(self, platform: PlatformType) -> List[ContentModel]:
        """Find content by platform"""
        return self.find_by_criteria({'platform': platform.value})
    
    def find_completed_downloads(self) -> List[ContentModel]:
        """Find all completed downloads"""
        return self.find_by_status(ContentStatus.COMPLETED)
    
    def find_failed_downloads(self) -> List[ContentModel]:
        """Find all failed downloads"""
        return self.find_by_status(ContentStatus.FAILED)
    
    def get_download_stats(self) -> Dict[str, int]:
        """Get download statistics"""
        stats = {}
        for status in ContentStatus:
            count = len(self.find_by_status(status))
            stats[status.value] = count
        return stats 