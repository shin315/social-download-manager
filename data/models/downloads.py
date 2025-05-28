"""
Download Tracking Models for Social Download Manager v2.0

Defines models for tracking download sessions, progress monitoring,
and download error handling.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Dict, Any, List
from datetime import datetime

from .base import BaseEntity, BaseModel, ValidationError, EntityId, JsonData


class DownloadStatus(Enum):
    """Download session status"""
    QUEUED = "queued"
    STARTING = "starting"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    RETRYING = "retrying"


@dataclass
class DownloadProgress:
    """Download progress information"""
    bytes_downloaded: int = 0
    total_bytes: Optional[int] = None
    percentage: float = 0.0
    speed_bytes_per_sec: Optional[float] = None
    eta_seconds: Optional[float] = None
    
    def update(self, bytes_downloaded: int, total_bytes: Optional[int] = None, 
               speed: Optional[float] = None):
        """Update progress information"""
        self.bytes_downloaded = bytes_downloaded
        if total_bytes is not None:
            self.total_bytes = total_bytes
        if speed is not None:
            self.speed_bytes_per_sec = speed
        
        # Calculate percentage
        if self.total_bytes and self.total_bytes > 0:
            self.percentage = (self.bytes_downloaded / self.total_bytes) * 100
        
        # Calculate ETA
        if (self.speed_bytes_per_sec and self.speed_bytes_per_sec > 0 and 
            self.total_bytes and self.bytes_downloaded < self.total_bytes):
            remaining_bytes = self.total_bytes - self.bytes_downloaded
            self.eta_seconds = remaining_bytes / self.speed_bytes_per_sec
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'bytes_downloaded': self.bytes_downloaded,
            'total_bytes': self.total_bytes,
            'percentage': self.percentage,
            'speed_bytes_per_sec': self.speed_bytes_per_sec,
            'eta_seconds': self.eta_seconds
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DownloadProgress':
        """Create from dictionary"""
        return cls(
            bytes_downloaded=data.get('bytes_downloaded', 0),
            total_bytes=data.get('total_bytes'),
            percentage=data.get('percentage', 0.0),
            speed_bytes_per_sec=data.get('speed_bytes_per_sec'),
            eta_seconds=data.get('eta_seconds')
        )


@dataclass(kw_only=True)
class DownloadError(BaseEntity):
    """Download error tracking"""
    download_id: EntityId  # Required field
    error_type: str = ""
    error_message: str = ""
    error_code: Optional[str] = None
    stack_trace: Optional[str] = None
    retry_count: int = 0
    can_retry: bool = True
    
    def __post_init__(self):
        """Initialize after creation"""
        super().__post_init__()
        
        if not self.download_id:
            raise ValueError("Download ID is required")


@dataclass(kw_only=True)
class DownloadSession(BaseEntity):
    """Download session tracking"""
    content_id: EntityId  # Required field
    url: str = ""
    status: DownloadStatus = DownloadStatus.QUEUED
    
    # Download configuration
    quality: Optional[str] = None
    format: Optional[str] = None
    output_path: Optional[str] = None
    
    # Progress tracking
    progress: DownloadProgress = field(default_factory=DownloadProgress)
    
    # Timing information
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Error handling
    error_count: int = 0
    last_error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # Session metadata
    downloader_type: Optional[str] = None  # e.g., 'yt-dlp', 'custom'
    session_config: JsonData = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize after creation"""
        super().__post_init__()
        
        if not self.content_id:
            raise ValueError("Content ID is required")
        if not self.url:
            raise ValueError("URL is required")
    
    def start_download(self) -> None:
        """Mark download as started"""
        self.status = DownloadStatus.DOWNLOADING
        self.started_at = datetime.now()
        self.mark_updated()
    
    def complete_download(self, final_path: str) -> None:
        """Mark download as completed"""
        self.status = DownloadStatus.COMPLETED
        self.completed_at = datetime.now()
        self.output_path = final_path
        self.progress.percentage = 100.0
        self.mark_updated()
    
    def fail_download(self, error_message: str) -> None:
        """Mark download as failed"""
        self.status = DownloadStatus.FAILED
        self.last_error = error_message
        self.error_count += 1
        self.mark_updated()
    
    def pause_download(self) -> None:
        """Pause download"""
        self.status = DownloadStatus.PAUSED
        self.mark_updated()
    
    def resume_download(self) -> None:
        """Resume download"""
        self.status = DownloadStatus.DOWNLOADING
        self.mark_updated()
    
    def cancel_download(self) -> None:
        """Cancel download"""
        self.status = DownloadStatus.CANCELLED
        self.mark_updated()
    
    def can_retry(self) -> bool:
        """Check if download can be retried"""
        return (self.status == DownloadStatus.FAILED and 
                self.retry_count < self.max_retries)
    
    def retry_download(self) -> None:
        """Retry failed download"""
        if not self.can_retry():
            raise ValueError("Download cannot be retried")
        
        self.status = DownloadStatus.RETRYING
        self.retry_count += 1
        self.mark_updated()
    
    def update_progress(self, bytes_downloaded: int, total_bytes: Optional[int] = None,
                       speed: Optional[float] = None) -> None:
        """Update download progress"""
        self.progress.update(bytes_downloaded, total_bytes, speed)
        self.mark_updated()
    
    def get_duration(self) -> Optional[float]:
        """Get download duration in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def get_average_speed(self) -> Optional[float]:
        """Get average download speed in bytes per second"""
        duration = self.get_duration()
        if duration and duration > 0 and self.progress.bytes_downloaded > 0:
            return self.progress.bytes_downloaded / duration
        return None


@dataclass(kw_only=True)
class DownloadModel(BaseEntity):
    """Main download model combining content and session information"""
    content_id: EntityId  # Required field
    url: str  # Required field
    session_id: Optional[EntityId] = None
    
    # Download configuration
    quality: Optional[str] = None
    format: Optional[str] = None
    output_directory: str = "downloads"
    
    # Status and progress
    status: DownloadStatus = DownloadStatus.QUEUED
    progress_percentage: float = 0.0
    download_speed: Optional[float] = None
    
    # File information
    filename: Optional[str] = None
    file_size: Optional[int] = None
    file_path: Optional[str] = None
    
    # Timing
    queued_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Error tracking
    error_message: Optional[str] = None
    retry_count: int = 0
    
    def __post_init__(self):
        """Initialize after creation"""
        super().__post_init__()
        
        if not self.content_id:
            raise ValueError("Content ID is required")
        if not self.url:
            raise ValueError("URL is required")
        
        if self.queued_at is None:
            self.queued_at = self.created_at


class DownloadModelManager(BaseModel[DownloadModel]):
    """Model manager for download entities"""
    
    def get_table_name(self) -> str:
        return "downloads"
    
    def get_entity_class(self) -> type:
        return DownloadModel
    
    def get_schema(self) -> str:
        """Get the CREATE TABLE SQL schema for downloads"""
        return """
        CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id INTEGER NOT NULL,
            session_id INTEGER,
            
            -- Download configuration
            url TEXT NOT NULL,
            quality TEXT,
            format TEXT,
            output_directory TEXT DEFAULT 'downloads',
            
            -- Status and progress
            status TEXT NOT NULL DEFAULT 'queued',
            progress_percentage REAL DEFAULT 0.0,
            download_speed REAL,
            
            -- File information
            filename TEXT,
            file_size INTEGER,
            file_path TEXT,
            
            -- Timing
            queued_at TEXT,
            started_at TEXT,
            completed_at TEXT,
            
            -- Error tracking
            error_message TEXT,
            retry_count INTEGER DEFAULT 0,
            
            -- Base entity fields
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            version INTEGER DEFAULT 1,
            is_deleted INTEGER DEFAULT 0,
            metadata TEXT,
            
            -- Foreign key constraints
            FOREIGN KEY (content_id) REFERENCES content(id) ON DELETE CASCADE
        );
        
        CREATE INDEX IF NOT EXISTS idx_downloads_content_id ON downloads(content_id);
        CREATE INDEX IF NOT EXISTS idx_downloads_status ON downloads(status);
        CREATE INDEX IF NOT EXISTS idx_downloads_queued_at ON downloads(queued_at);
        CREATE INDEX IF NOT EXISTS idx_downloads_completed_at ON downloads(completed_at);
        """
    
    def validate_entity(self, entity: DownloadModel) -> List[ValidationError]:
        """Validate download entity"""
        errors = super().validate_entity(entity)
        
        # Validate required fields
        if not entity.content_id:
            errors.append(ValidationError('content_id', entity.content_id, 'Content ID is required'))
        
        if not entity.url:
            errors.append(ValidationError('url', entity.url, 'URL is required'))
        
        # Validate status
        if not isinstance(entity.status, DownloadStatus):
            errors.append(ValidationError('status', entity.status, 'Invalid download status'))
        
        # Validate progress
        if entity.progress_percentage < 0 or entity.progress_percentage > 100:
            errors.append(ValidationError('progress_percentage', entity.progress_percentage, 
                                        'Progress must be between 0 and 100'))
        
        return errors
    
    def find_by_content_id(self, content_id: EntityId) -> List[DownloadModel]:
        """Find downloads by content ID"""
        return self.find_by_criteria({'content_id': content_id})
    
    def find_by_status(self, status: DownloadStatus) -> List[DownloadModel]:
        """Find downloads by status"""
        return self.find_by_criteria({'status': status.value})
    
    def find_active_downloads(self) -> List[DownloadModel]:
        """Find all active downloads"""
        active_statuses = [
            DownloadStatus.QUEUED,
            DownloadStatus.STARTING,
            DownloadStatus.DOWNLOADING,
            DownloadStatus.PROCESSING,
            DownloadStatus.RETRYING
        ]
        
        results = []
        for status in active_statuses:
            results.extend(self.find_by_status(status))
        return results
    
    def find_completed_downloads(self) -> List[DownloadModel]:
        """Find all completed downloads"""
        return self.find_by_status(DownloadStatus.COMPLETED)
    
    def find_failed_downloads(self) -> List[DownloadModel]:
        """Find all failed downloads"""
        return self.find_by_status(DownloadStatus.FAILED)


class DownloadSessionManager(BaseModel[DownloadSession]):
    """Model manager for download session entities"""
    
    def get_table_name(self) -> str:
        return "download_sessions"
    
    def get_entity_class(self) -> type:
        return DownloadSession
    
    def get_schema(self) -> str:
        """Get the CREATE TABLE SQL schema for download sessions"""
        return """
        CREATE TABLE IF NOT EXISTS download_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id INTEGER NOT NULL,
            url TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            
            -- Download configuration
            quality TEXT,
            format TEXT,
            output_path TEXT,
            
            -- Progress tracking (stored as JSON)
            progress TEXT,
            
            -- Timing information
            started_at TEXT,
            completed_at TEXT,
            
            -- Error handling
            error_count INTEGER DEFAULT 0,
            last_error TEXT,
            retry_count INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3,
            
            -- Session metadata
            downloader_type TEXT,
            session_config TEXT,
            
            -- Base entity fields
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            version INTEGER DEFAULT 1,
            is_deleted INTEGER DEFAULT 0,
            metadata TEXT,
            
            -- Foreign key constraints
            FOREIGN KEY (content_id) REFERENCES content(id) ON DELETE CASCADE
        );
        
        CREATE INDEX IF NOT EXISTS idx_sessions_content_id ON download_sessions(content_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_status ON download_sessions(status);
        CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON download_sessions(started_at);
        """


class DownloadErrorManager(BaseModel[DownloadError]):
    """Model manager for download error entities"""
    
    def get_table_name(self) -> str:
        return "download_errors"
    
    def get_entity_class(self) -> type:
        return DownloadError
    
    def get_schema(self) -> str:
        """Get the CREATE TABLE SQL schema for download errors"""
        return """
        CREATE TABLE IF NOT EXISTS download_errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            download_id INTEGER NOT NULL,
            error_type TEXT NOT NULL,
            error_message TEXT NOT NULL,
            error_code TEXT,
            stack_trace TEXT,
            retry_count INTEGER DEFAULT 0,
            can_retry INTEGER DEFAULT 1,
            
            -- Base entity fields
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            version INTEGER DEFAULT 1,
            is_deleted INTEGER DEFAULT 0,
            metadata TEXT,
            
            -- Foreign key constraints
            FOREIGN KEY (download_id) REFERENCES downloads(id) ON DELETE CASCADE
        );
        
        CREATE INDEX IF NOT EXISTS idx_errors_download_id ON download_errors(download_id);
        CREATE INDEX IF NOT EXISTS idx_errors_error_type ON download_errors(error_type);
        CREATE INDEX IF NOT EXISTS idx_errors_created_at ON download_errors(created_at);
        """ 