"""
Data models for platform handlers

This module defines data structures used across platform implementations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pathlib import Path

from .enums import (
    PlatformType, 
    ContentType, 
    QualityLevel, 
    DownloadStatus, 
    AuthType
)


@dataclass
class VideoFormat:
    """Represents a video format/quality option"""
    format_id: str
    quality: QualityLevel
    ext: str  # File extension (mp4, webm, etc.)
    height: Optional[int] = None
    width: Optional[int] = None
    fps: Optional[float] = None
    filesize: Optional[int] = None  # Size in bytes
    vcodec: Optional[str] = None    # Video codec
    acodec: Optional[str] = None    # Audio codec
    vbr: Optional[int] = None       # Video bitrate
    abr: Optional[int] = None       # Audio bitrate
    is_audio_only: bool = False
    has_watermark: bool = False
    url: Optional[str] = None       # Direct download URL (if available)
    
    def __post_init__(self):
        """Post-init processing"""
        # Auto-detect quality from height if not set
        if self.quality == QualityLevel.BEST and self.height:
            self.quality = QualityLevel.from_height(self.height)
    
    @property
    def quality_string(self) -> str:
        """Get quality as string"""
        return self.quality.value
    
    @property
    def resolution_string(self) -> Optional[str]:
        """Get resolution as string (e.g., '1920x1080')"""
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return None
    
    @property
    def size_mb(self) -> Optional[float]:
        """Get file size in MB"""
        if self.filesize:
            return round(self.filesize / (1024 * 1024), 2)
        return None


@dataclass
class PlatformVideoInfo:
    """
    Standardized video information from any platform
    
    This replaces the old VideoInfo class with a more structured approach.
    """
    # Core identifiers
    url: str
    platform: PlatformType
    platform_id: Optional[str] = None  # Platform-specific ID
    
    # Basic info
    title: str = "Unknown Title"
    description: str = ""
    thumbnail_url: str = ""
    duration: Optional[float] = None  # Duration in seconds
    
    # Creator info
    creator: str = "Unknown"
    creator_id: Optional[str] = None
    creator_avatar: Optional[str] = None
    
    # Content metadata
    content_type: ContentType = ContentType.VIDEO
    hashtags: List[str] = field(default_factory=list)
    mentions: List[str] = field(default_factory=list)
    
    # Statistics
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    share_count: Optional[int] = None
    
    # Publication info
    published_at: Optional[datetime] = None
    
    # Available formats
    formats: List[VideoFormat] = field(default_factory=list)
    
    # Additional metadata
    extra_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-init processing"""
        # Ensure URL and platform are set
        if not self.url:
            raise ValueError("URL is required")
        
        # Auto-detect platform if not set
        if self.platform == PlatformType.UNKNOWN:
            self.platform = PlatformType.from_url(self.url)
    
    def get_best_format(self, prefer_no_watermark: bool = True) -> Optional[VideoFormat]:
        """Get the best quality format available"""
        if not self.formats:
            return None
        
        # Filter by watermark preference
        candidates = self.formats
        if prefer_no_watermark:
            no_watermark = [f for f in self.formats if not f.has_watermark]
            if no_watermark:
                candidates = no_watermark
        
        # Sort by quality (highest first)
        candidates.sort(key=lambda x: x.quality.height, reverse=True)
        return candidates[0]
    
    def get_format_by_quality(self, quality: QualityLevel) -> Optional[VideoFormat]:
        """Get format by specific quality level"""
        for fmt in self.formats:
            if fmt.quality == quality:
                return fmt
        return None
    
    def get_audio_format(self) -> Optional[VideoFormat]:
        """Get audio-only format if available"""
        for fmt in self.formats:
            if fmt.is_audio_only:
                return fmt
        return None
    
    def get_available_qualities(self) -> List[QualityLevel]:
        """Get list of available quality levels"""
        return sorted(list(set(fmt.quality for fmt in self.formats)), reverse=True)
    
    @property
    def duration_string(self) -> str:
        """Get duration as formatted string"""
        if not self.duration:
            return "Unknown"
        
        minutes, seconds = divmod(int(self.duration), 60)
        hours, minutes = divmod(minutes, 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    def copy(self) -> 'PlatformVideoInfo':
        """Create a deep copy of this video info"""
        import copy
        return copy.deepcopy(self)


@dataclass
class AuthenticationInfo:
    """Authentication information for a platform"""
    auth_type: AuthType
    credentials: Dict[str, Any] = field(default_factory=dict)
    token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    scope: List[str] = field(default_factory=list)
    
    @property
    def is_expired(self) -> bool:
        """Check if authentication is expired"""
        if not self.expires_at:
            return False
        return datetime.now() >= self.expires_at
    
    def is_valid(self) -> bool:
        """Check if authentication is valid"""
        if self.auth_type == AuthType.NONE:
            return True
        return bool(self.token or self.credentials) and not self.is_expired


@dataclass
class DownloadProgress:
    """Download progress information"""
    status: DownloadStatus
    progress_percent: float = 0.0
    downloaded_bytes: int = 0
    total_bytes: Optional[int] = None
    speed_bps: Optional[float] = None  # Bytes per second
    eta_seconds: Optional[float] = None
    message: str = ""
    
    @property
    def speed_mbps(self) -> Optional[float]:
        """Get speed in MB/s"""
        if self.speed_bps:
            return round(self.speed_bps / (1024 * 1024), 2)
        return None
    
    @property
    def eta_string(self) -> str:
        """Get ETA as formatted string"""
        if not self.eta_seconds:
            return "Unknown"
        
        if self.eta_seconds < 60:
            return f"{int(self.eta_seconds)}s"
        elif self.eta_seconds < 3600:
            minutes = int(self.eta_seconds // 60)
            seconds = int(self.eta_seconds % 60)
            return f"{minutes}m {seconds}s"
        else:
            hours = int(self.eta_seconds // 3600)
            minutes = int((self.eta_seconds % 3600) // 60)
            return f"{hours}h {minutes}m"


@dataclass 
class DownloadResult:
    """Result of a download operation"""
    success: bool
    video_info: PlatformVideoInfo
    file_path: Optional[Path] = None
    file_size: Optional[int] = None
    format_used: Optional[VideoFormat] = None
    download_time: Optional[float] = None  # Time taken in seconds
    error_message: Optional[str] = None
    extra_files: List[Path] = field(default_factory=list)  # Thumbnail, subtitle files, etc.
    
    @property
    def file_size_mb(self) -> Optional[float]:
        """Get file size in MB"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return None
    
    @property
    def download_speed_mbps(self) -> Optional[float]:
        """Calculate average download speed in MB/s"""
        if self.file_size and self.download_time and self.download_time > 0:
            return round((self.file_size / (1024 * 1024)) / self.download_time, 2)
        return None


@dataclass
class PlatformCapabilities:
    """Capabilities supported by a platform handler"""
    supports_video: bool = True
    supports_audio: bool = True
    supports_playlists: bool = False
    supports_live: bool = False
    supports_stories: bool = False
    requires_auth: bool = False
    supports_watermark_removal: bool = False
    supports_quality_selection: bool = True
    supports_thumbnails: bool = True
    supports_metadata: bool = True
    max_concurrent_downloads: int = 3
    rate_limit_requests: int = 10
    rate_limit_period: int = 60  # seconds
    
    def __str__(self) -> str:
        """String representation of capabilities"""
        features = []
        if self.supports_video:
            features.append("Video")
        if self.supports_audio:
            features.append("Audio")
        if self.supports_playlists:
            features.append("Playlists")
        if self.supports_live:
            features.append("Live")
        if self.supports_stories:
            features.append("Stories")
        
        return f"Supports: {', '.join(features)}" 