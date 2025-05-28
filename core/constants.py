"""
Constants Management for Social Download Manager v2.0

Centralized storage for all application constants to improve maintainability
and consistency across the codebase.
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple, Final

# =============================================================================
# APPLICATION CONSTANTS
# =============================================================================

class AppConstants:
    """Core application constants"""
    
    # Application metadata
    APP_NAME: Final[str] = "Social Download Manager"
    APP_SHORT_NAME: Final[str] = "SDM"
    APP_VERSION: Final[str] = "2.0.0-dev"
    APP_AUTHOR: Final[str] = "Social Download Manager Team"
    APP_WEBSITE: Final[str] = "https://github.com/social-download-manager"
    APP_DESCRIPTION: Final[str] = "Multi-platform social media content downloader"
    
    # File and directory constants
    CONFIG_FILE: Final[str] = "config.json"
    DEFAULT_DOWNLOAD_DIR: Final[str] = "downloads"
    ASSETS_DIR: Final[str] = "assets"
    BACKUP_DIR: Final[str] = "backup"
    LOG_DIR: Final[str] = "logs"
    TEMP_DIR: Final[str] = "temp"
    
    # Network and timeout constants
    DEFAULT_TIMEOUT: Final[int] = 30
    MAX_RETRIES: Final[int] = 3
    USER_AGENT: Final[str] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    # Performance constants
    MAX_CONCURRENT_DOWNLOADS: Final[int] = 3
    CHUNK_SIZE: Final[int] = 8192
    PROGRESS_UPDATE_INTERVAL: Final[float] = 0.1  # seconds


class PlatformConstants:
    """Platform-specific constants"""
    
    # Supported platforms
    TIKTOK: Final[str] = "tiktok"
    YOUTUBE: Final[str] = "youtube"
    INSTAGRAM: Final[str] = "instagram"
    FACEBOOK: Final[str] = "facebook"
    TWITTER: Final[str] = "twitter"
    
    # Platform display names
    PLATFORM_NAMES: Final[Dict[str, str]] = {
        TIKTOK: "TikTok",
        YOUTUBE: "YouTube",
        INSTAGRAM: "Instagram", 
        FACEBOOK: "Facebook",
        TWITTER: "Twitter/X"
    }
    
    # Platform URLs and patterns
    PLATFORM_DOMAINS: Final[Dict[str, List[str]]] = {
        TIKTOK: ["tiktok.com", "vm.tiktok.com", "vt.tiktok.com"],
        YOUTUBE: ["youtube.com", "youtu.be", "m.youtube.com"],
        INSTAGRAM: ["instagram.com", "instagr.am"],
        FACEBOOK: ["facebook.com", "fb.com", "m.facebook.com"],
        TWITTER: ["twitter.com", "x.com", "mobile.twitter.com"]
    }
    
    # Platform status
    STATUS_STABLE: Final[str] = "stable"
    STATUS_BETA: Final[str] = "beta"
    STATUS_ALPHA: Final[str] = "alpha"
    STATUS_PLANNED: Final[str] = "planned"
    STATUS_DISABLED: Final[str] = "disabled"
    
    PLATFORM_STATUS: Final[Dict[str, str]] = {
        TIKTOK: STATUS_STABLE,
        YOUTUBE: STATUS_PLANNED,
        INSTAGRAM: STATUS_PLANNED,
        FACEBOOK: STATUS_PLANNED,
        TWITTER: STATUS_PLANNED
    }
    
    # Video quality options
    QUALITY_BEST: Final[str] = "best"
    QUALITY_WORST: Final[str] = "worst"
    QUALITY_720P: Final[str] = "720p"
    QUALITY_480P: Final[str] = "480p"
    QUALITY_360P: Final[str] = "360p"
    
    QUALITY_OPTIONS: Final[List[str]] = [
        QUALITY_BEST, QUALITY_720P, QUALITY_480P, QUALITY_360P, QUALITY_WORST
    ]


class UIConstants:
    """User interface constants"""
    
    # Window dimensions
    DEFAULT_WINDOW_WIDTH: Final[int] = 1200
    DEFAULT_WINDOW_HEIGHT: Final[int] = 800
    MIN_WINDOW_WIDTH: Final[int] = 800
    MIN_WINDOW_HEIGHT: Final[int] = 600
    
    # Theme constants
    THEME_LIGHT: Final[str] = "light"
    THEME_DARK: Final[str] = "dark"
    THEME_AUTO: Final[str] = "auto"
    
    AVAILABLE_THEMES: Final[List[str]] = [THEME_LIGHT, THEME_DARK, THEME_AUTO]
    
    # Language constants
    LANG_ENGLISH: Final[str] = "en"
    LANG_VIETNAMESE: Final[str] = "vi"
    LANG_CHINESE: Final[str] = "zh"
    LANG_JAPANESE: Final[str] = "ja"
    LANG_KOREAN: Final[str] = "ko"
    
    AVAILABLE_LANGUAGES: Final[Dict[str, str]] = {
        LANG_ENGLISH: "English",
        LANG_VIETNAMESE: "Tiếng Việt",
        LANG_CHINESE: "中文",
        LANG_JAPANESE: "日本語",
        LANG_KOREAN: "한국어"
    }
    
    # Icon sizes
    ICON_SMALL: Final[Tuple[int, int]] = (16, 16)
    ICON_MEDIUM: Final[Tuple[int, int]] = (24, 24)
    ICON_LARGE: Final[Tuple[int, int]] = (32, 32)
    ICON_XLARGE: Final[Tuple[int, int]] = (48, 48)
    
    # Table settings
    TABLE_ROW_HEIGHT: Final[int] = 40
    TABLE_HEADER_HEIGHT: Final[int] = 35
    TABLE_MIN_COLUMN_WIDTH: Final[int] = 80
    MAX_VISIBLE_ROWS: Final[int] = 1000  # For performance
    
    # Progress bar constants
    PROGRESS_MIN: Final[int] = 0
    PROGRESS_MAX: Final[int] = 100
    PROGRESS_PRECISION: Final[int] = 1  # decimal places


class DatabaseConstants:
    """Database-related constants"""
    
    # Database configuration
    DEFAULT_DB_NAME: Final[str] = "downloads.db"
    DB_VERSION: Final[int] = 2  # v2.0 schema version
    V1_DB_VERSION: Final[int] = 1  # v1.2.1 schema version
    
    # Table names
    TABLE_VIDEOS: Final[str] = "videos"
    TABLE_DOWNLOADS: Final[str] = "downloads"
    TABLE_PLATFORMS: Final[str] = "platforms"
    TABLE_SETTINGS: Final[str] = "settings"
    TABLE_METADATA: Final[str] = "metadata"
    TABLE_SCHEMA_VERSION: Final[str] = "schema_version"
    
    # Common column names
    COL_ID: Final[str] = "id"
    COL_URL: Final[str] = "url"
    COL_TITLE: Final[str] = "title"
    COL_PLATFORM: Final[str] = "platform"
    COL_STATUS: Final[str] = "status"
    COL_CREATED_AT: Final[str] = "created_at"
    COL_UPDATED_AT: Final[str] = "updated_at"
    COL_FILE_PATH: Final[str] = "file_path"
    COL_FILE_SIZE: Final[str] = "file_size"
    COL_DURATION: Final[str] = "duration"
    COL_QUALITY: Final[str] = "quality"
    COL_THUMBNAIL: Final[str] = "thumbnail"
    COL_AUTHOR: Final[str] = "author"
    COL_DESCRIPTION: Final[str] = "description"
    COL_METADATA_JSON: Final[str] = "metadata_json"
    
    # Download status values
    STATUS_PENDING: Final[str] = "pending"
    STATUS_DOWNLOADING: Final[str] = "downloading"
    STATUS_COMPLETED: Final[str] = "completed"
    STATUS_FAILED: Final[str] = "failed"
    STATUS_CANCELLED: Final[str] = "cancelled"
    STATUS_PAUSED: Final[str] = "paused"
    
    DOWNLOAD_STATUSES: Final[List[str]] = [
        STATUS_PENDING, STATUS_DOWNLOADING, STATUS_COMPLETED, 
        STATUS_FAILED, STATUS_CANCELLED, STATUS_PAUSED
    ]
    
    # SQL constants
    SQL_LIMIT_DEFAULT: Final[int] = 100
    SQL_LIMIT_MAX: Final[int] = 1000
    
    # Backup constants
    MAX_BACKUPS: Final[int] = 5
    BACKUP_INTERVAL_DAYS: Final[int] = 7


class ErrorConstants:
    """Error codes and messages"""
    
    # Error categories
    ERROR_NETWORK: Final[str] = "NETWORK_ERROR"
    ERROR_PLATFORM: Final[str] = "PLATFORM_ERROR"
    ERROR_DATABASE: Final[str] = "DATABASE_ERROR"
    ERROR_FILE: Final[str] = "FILE_ERROR"
    ERROR_CONFIG: Final[str] = "CONFIG_ERROR"
    ERROR_UI: Final[str] = "UI_ERROR"
    ERROR_UNKNOWN: Final[str] = "UNKNOWN_ERROR"
    
    # Specific error codes
    ERROR_CODES: Final[Dict[str, int]] = {
        # Network errors (1000-1999)
        "NETWORK_TIMEOUT": 1001,
        "NETWORK_CONNECTION_FAILED": 1002,
        "NETWORK_INVALID_URL": 1003,
        "NETWORK_FORBIDDEN": 1004,
        "NETWORK_NOT_FOUND": 1005,
        
        # Platform errors (2000-2999)
        "PLATFORM_UNSUPPORTED": 2001,
        "PLATFORM_DETECTION_FAILED": 2002,
        "PLATFORM_API_ERROR": 2003,
        "PLATFORM_CONTENT_UNAVAILABLE": 2004,
        "PLATFORM_RATE_LIMITED": 2005,
        
        # Database errors (3000-3999)
        "DATABASE_CONNECTION_FAILED": 3001,
        "DATABASE_QUERY_FAILED": 3002,
        "DATABASE_MIGRATION_FAILED": 3003,
        "DATABASE_CORRUPTION": 3004,
        "DATABASE_PERMISSION_DENIED": 3005,
        
        # File errors (4000-4999)
        "FILE_NOT_FOUND": 4001,
        "FILE_PERMISSION_DENIED": 4002,
        "FILE_DISK_FULL": 4003,
        "FILE_INVALID_PATH": 4004,
        "FILE_ALREADY_EXISTS": 4005,
        
        # Configuration errors (5000-5999)
        "CONFIG_INVALID_FORMAT": 5001,
        "CONFIG_MISSING_REQUIRED": 5002,
        "CONFIG_SAVE_FAILED": 5003,
        "CONFIG_LOAD_FAILED": 5004,
        
        # UI errors (6000-6999)
        "UI_COMPONENT_FAILED": 6001,
        "UI_THEME_LOAD_FAILED": 6002,
        "UI_TRANSLATION_MISSING": 6003,
    }
    
    # Default error messages
    DEFAULT_MESSAGES: Final[Dict[str, str]] = {
        ERROR_NETWORK: "Network connection error occurred",
        ERROR_PLATFORM: "Platform-specific error occurred", 
        ERROR_DATABASE: "Database operation failed",
        ERROR_FILE: "File operation failed",
        ERROR_CONFIG: "Configuration error occurred",
        ERROR_UI: "User interface error occurred",
        ERROR_UNKNOWN: "An unknown error occurred"
    }


class LogConstants:
    """Logging constants"""
    
    # Log levels
    LEVEL_DEBUG: Final[str] = "DEBUG"
    LEVEL_INFO: Final[str] = "INFO"
    LEVEL_WARNING: Final[str] = "WARNING"
    LEVEL_ERROR: Final[str] = "ERROR"
    LEVEL_CRITICAL: Final[str] = "CRITICAL"
    
    # Log file names
    APP_LOG_FILE: Final[str] = "app.log"
    ERROR_LOG_FILE: Final[str] = "error.log"
    DOWNLOAD_LOG_FILE: Final[str] = "downloads.log"
    
    # Log format
    LOG_FORMAT: Final[str] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"
    
    # Log rotation
    MAX_LOG_SIZE: Final[int] = 10 * 1024 * 1024  # 10MB
    MAX_LOG_FILES: Final[int] = 5


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_platform_name(platform_id: str) -> str:
    """Get display name for platform ID"""
    return PlatformConstants.PLATFORM_NAMES.get(platform_id, platform_id.title())


def get_platform_domains(platform_id: str) -> List[str]:
    """Get list of domains for a platform"""
    return PlatformConstants.PLATFORM_DOMAINS.get(platform_id, [])


def is_supported_platform(platform_id: str) -> bool:
    """Check if platform is supported"""
    return platform_id in PlatformConstants.PLATFORM_NAMES


def get_error_message(error_code: str, default: str = None) -> str:
    """Get error message for error code"""
    if default is None:
        default = ErrorConstants.DEFAULT_MESSAGES.get(ErrorConstants.ERROR_UNKNOWN)
    return ErrorConstants.DEFAULT_MESSAGES.get(error_code, default)


def validate_download_status(status: str) -> bool:
    """Validate if download status is valid"""
    return status in DatabaseConstants.DOWNLOAD_STATUSES


def get_asset_path(filename: str) -> Path:
    """Get full path to asset file"""
    return Path(AppConstants.ASSETS_DIR) / filename


def get_platform_icon_path(platform_id: str) -> Path:
    """Get path to platform icon"""
    return get_asset_path("platforms") / f"{platform_id}.png"


# =============================================================================
# CONSTANTS VALIDATION
# =============================================================================

def validate_constants() -> bool:
    """
    Validate that all constants are properly defined and consistent
    
    Returns:
        True if all constants are valid, False otherwise
    """
    try:
        # Check platform consistency
        for platform_id in PlatformConstants.PLATFORM_NAMES.keys():
            if platform_id not in PlatformConstants.PLATFORM_DOMAINS:
                print(f"Warning: Platform {platform_id} missing domain configuration")
                return False
            
            if platform_id not in PlatformConstants.PLATFORM_STATUS:
                print(f"Warning: Platform {platform_id} missing status configuration")
                return False
        
        # Check error code uniqueness
        error_codes = set(ErrorConstants.ERROR_CODES.values())
        if len(error_codes) != len(ErrorConstants.ERROR_CODES):
            print("Warning: Duplicate error codes found")
            return False
        
        # Check required directories exist or can be created
        required_dirs = [
            AppConstants.ASSETS_DIR,
            AppConstants.DEFAULT_DOWNLOAD_DIR,
            AppConstants.LOG_DIR
        ]
        
        for dir_path in required_dirs:
            path = Path(dir_path)
            if not path.exists():
                try:
                    path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    print(f"Warning: Cannot create directory {dir_path}: {e}")
        
        return True
        
    except Exception as e:
        print(f"Constants validation failed: {e}")
        return False


# Export all constant classes for easy importing
__all__ = [
    "AppConstants",
    "PlatformConstants", 
    "UIConstants",
    "DatabaseConstants",
    "ErrorConstants",
    "LogConstants",
    "get_platform_name",
    "get_platform_domains",
    "is_supported_platform",
    "get_error_message", 
    "validate_download_status",
    "get_asset_path",
    "get_platform_icon_path",
    "validate_constants"
] 