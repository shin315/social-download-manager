"""
Enums for platform handlers

This module defines common enumerations used across platform implementations.
"""

from enum import Enum, auto
from typing import Final


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

    @classmethod
    def from_url(cls, url: str) -> 'PlatformType':
        """Detect platform type from URL"""
        url_lower = url.lower()
        
        if any(domain in url_lower for domain in ["tiktok.com", "vm.tiktok.com", "vt.tiktok.com"]):
            return cls.TIKTOK
        elif any(domain in url_lower for domain in ["youtube.com", "youtu.be", "m.youtube.com"]):
            return cls.YOUTUBE
        elif any(domain in url_lower for domain in ["instagram.com", "instagr.am"]):
            return cls.INSTAGRAM
        elif any(domain in url_lower for domain in ["facebook.com", "fb.com", "m.facebook.com"]):
            return cls.FACEBOOK
        elif any(domain in url_lower for domain in ["twitter.com", "x.com", "mobile.twitter.com"]):
            return cls.TWITTER
        elif "linkedin.com" in url_lower:
            return cls.LINKEDIN
        elif "twitch.tv" in url_lower:
            return cls.TWITCH
        else:
            return cls.UNKNOWN

    @property
    def display_name(self) -> str:
        """Get display name for the platform"""
        display_names = {
            self.TIKTOK: "TikTok",
            self.YOUTUBE: "YouTube", 
            self.INSTAGRAM: "Instagram",
            self.FACEBOOK: "Facebook",
            self.TWITTER: "Twitter/X",
            self.LINKEDIN: "LinkedIn",
            self.TWITCH: "Twitch",
            self.UNKNOWN: "Unknown"
        }
        return display_names.get(self, "Unknown")


class ContentType(Enum):
    """Types of content that can be downloaded"""
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    STORY = "story"
    LIVE = "live"
    PLAYLIST = "playlist"
    UNKNOWN = "unknown"


class DownloadStatus(Enum):
    """Download status states"""
    PENDING = auto()
    INITIALIZING = auto()
    DOWNLOADING = auto()
    PROCESSING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()
    PAUSED = auto()


class AuthType(Enum):
    """Authentication types supported by platforms"""
    NONE = "none"           # No authentication required
    API_KEY = "api_key"     # API key authentication
    OAUTH = "oauth"         # OAuth 2.0 authentication
    BEARER = "bearer"       # Bearer token authentication
    BASIC = "basic"         # Basic authentication
    SESSION = "session"     # Session-based authentication


class QualityLevel(Enum):
    """Video quality levels"""
    BEST = "best"
    WORST = "worst"
    UHD_4K = "2160p"      # 4K Ultra HD
    QHD_2K = "1440p"      # 2K Quad HD  
    FHD = "1080p"         # Full HD
    HD = "720p"           # HD
    SD = "480p"           # Standard Definition
    LD = "360p"           # Low Definition
    MOBILE = "240p"       # Mobile quality
    AUDIO_ONLY = "audio"  # Audio only

    @classmethod
    def from_height(cls, height: int) -> 'QualityLevel':
        """Get quality level from video height"""
        if height >= 2160:
            return cls.UHD_4K
        elif height >= 1440:
            return cls.QHD_2K
        elif height >= 1080:
            return cls.FHD
        elif height >= 720:
            return cls.HD
        elif height >= 480:
            return cls.SD
        elif height >= 360:
            return cls.LD
        elif height >= 240:
            return cls.MOBILE
        else:
            return cls.WORST

    @property
    def height(self) -> int:
        """Get the height in pixels for this quality level"""
        heights = {
            self.UHD_4K: 2160,
            self.QHD_2K: 1440,
            self.FHD: 1080,
            self.HD: 720,
            self.SD: 480,
            self.LD: 360,
            self.MOBILE: 240,
            self.AUDIO_ONLY: 0
        }
        return heights.get(self, 0)

    def __lt__(self, other):
        """Enable sorting by quality (higher is better)"""
        if not isinstance(other, QualityLevel):
            return NotImplemented
        return self.height < other.height


class ErrorType(Enum):
    """Types of platform errors"""
    CONNECTION_ERROR = auto()
    AUTHENTICATION_ERROR = auto()
    AUTHORIZATION_ERROR = auto()
    RATE_LIMIT_ERROR = auto()
    CONTENT_NOT_FOUND = auto()
    CONTENT_PRIVATE = auto()
    CONTENT_UNAVAILABLE = auto()
    CONTENT_REGION_RESTRICTED = auto()
    CONTENT_COPYRIGHT = auto()
    INVALID_URL = auto()
    UNSUPPORTED_CONTENT = auto()
    API_CHANGED = auto()
    NETWORK_ERROR = auto()
    PARSING_ERROR = auto()
    UNKNOWN_ERROR = auto()


# Constants
class PlatformConstants:
    """Platform-related constants"""
    
    # Default timeouts (in seconds)
    DEFAULT_CONNECT_TIMEOUT: Final[int] = 30
    DEFAULT_READ_TIMEOUT: Final[int] = 60
    DEFAULT_DOWNLOAD_TIMEOUT: Final[int] = 300
    
    # Rate limiting
    DEFAULT_RATE_LIMIT_REQUESTS: Final[int] = 10
    DEFAULT_RATE_LIMIT_PERIOD: Final[int] = 60  # seconds
    
    # Retry settings
    DEFAULT_MAX_RETRIES: Final[int] = 3
    DEFAULT_RETRY_DELAY: Final[float] = 1.0
    
    # File size limits (in bytes)
    MAX_FILE_SIZE: Final[int] = 1024 * 1024 * 1024 * 2  # 2GB
    MAX_THUMBNAIL_SIZE: Final[int] = 1024 * 1024 * 10    # 10MB
    
    # Supported file extensions
    VIDEO_EXTENSIONS: Final[tuple] = ('.mp4', '.mkv', '.webm', '.avi', '.mov')
    AUDIO_EXTENSIONS: Final[tuple] = ('.mp3', '.m4a', '.wav', '.flac', '.ogg')
    IMAGE_EXTENSIONS: Final[tuple] = ('.jpg', '.jpeg', '.png', '.webp', '.gif') 