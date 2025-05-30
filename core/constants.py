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
    """Enhanced error constants for comprehensive error handling"""
    
    # Error message templates
    MESSAGES = {
        'GENERIC_ERROR': "An unexpected error occurred. Please try again.",
        'VALIDATION_ERROR': "Invalid input provided. Please check your input and try again.",
        'NETWORK_ERROR': "Network error occurred. Please check your connection and try again.",
        'DATABASE_ERROR': "Database error occurred. Please try again later.",
        'PERMISSION_ERROR': "Permission denied. Please check your access rights.",
        'FILE_ERROR': "File operation failed. Please check file permissions and disk space.",
        'AUTHENTICATION_ERROR': "Authentication failed. Please check your credentials.",
        'CONFIGURATION_ERROR': "Configuration error. Please check application settings.",
        
        # UI specific errors
        'UI_COMPONENT_ERROR': "Component error occurred. Please restart the application.",
        'UI_RENDERING_ERROR': "Display issue occurred. Please refresh the interface.",
        'UI_INPUT_ERROR': "Invalid input provided. Please check your input and try again.",
        
        # Platform specific errors
        'PLATFORM_API_ERROR': "Platform service error. Please try again later.",
        'PLATFORM_RATE_LIMIT': "Rate limit exceeded. Please wait before trying again.",
        'PLATFORM_NOT_FOUND': "Content not found or may have been removed.",
        'PLATFORM_PRIVATE': "Content is private and cannot be accessed.",
        
        # Download specific errors
        'DOWNLOAD_FAILED': "Download failed. Please try again.",
        'DOWNLOAD_SPACE_ERROR': "Not enough disk space. Please free up space and try again.",
        'DOWNLOAD_PERMISSION_ERROR': "Download permission denied. Please check file permissions.",
        'DOWNLOAD_NETWORK_ERROR': "Download timed out. Please check your internet connection.",
        'DOWNLOAD_CORRUPTED': "Downloaded file is corrupted. Please try downloading again.",
        
        # Repository specific errors
        'REPOSITORY_CONNECTION_ERROR': "Database connection failed. Please try again later.",
        'REPOSITORY_TRANSACTION_ERROR': "Data operation failed. Please try again.",
        'REPOSITORY_CORRUPTION_ERROR': "Data integrity issue detected. Please contact support.",
    }
    
    # Error codes
    CODES = {
        # Generic codes
        'UNKNOWN': 'ERR_UNKNOWN',
        'VALIDATION': 'ERR_VALIDATION',
        'NETWORK': 'ERR_NETWORK',
        'DATABASE': 'ERR_DATABASE',
        'PERMISSION': 'ERR_PERMISSION',
        'FILE_SYSTEM': 'ERR_FILE_SYSTEM',
        'AUTHENTICATION': 'ERR_AUTH',
        'CONFIGURATION': 'ERR_CONFIG',
        
        # UI codes
        'UI_COMPONENT': 'ERR_UI_COMPONENT',
        'UI_RENDERING': 'ERR_UI_RENDER',
        'UI_INPUT': 'ERR_UI_INPUT',
        'UI_STATE': 'ERR_UI_STATE',
        'UI_EVENT': 'ERR_UI_EVENT',
        
        # Platform codes
        'PLATFORM_API': 'ERR_PLT_API',
        'PLATFORM_RATE_LIMIT': 'ERR_PLT_RATE_LIMIT',
        'PLATFORM_NOT_FOUND': 'ERR_PLT_NOT_FOUND',
        'PLATFORM_PRIVATE': 'ERR_PLT_PRIVATE',
        'PLATFORM_AUTH': 'ERR_PLT_AUTH',
        
        # Download codes
        'DOWNLOAD_FAILED': 'ERR_DWN_FAILED',
        'DOWNLOAD_SPACE': 'ERR_DWN_SPACE',
        'DOWNLOAD_PERMISSION': 'ERR_DWN_PERMISSION',
        'DOWNLOAD_NETWORK': 'ERR_DWN_NETWORK',
        'DOWNLOAD_CORRUPTED': 'ERR_DWN_CORRUPTED',
        
        # Repository codes
        'REPOSITORY_CONNECTION': 'ERR_REP_CONNECTION',
        'REPOSITORY_TRANSACTION': 'ERR_REP_TRANSACTION',
        'REPOSITORY_CORRUPTION': 'ERR_REP_CORRUPTION',
        'REPOSITORY_DEADLOCK': 'ERR_REP_DEADLOCK',
        
        # Service codes
        'SERVICE_UNAVAILABLE': 'ERR_SVC_UNAVAILABLE',
        'SERVICE_TIMEOUT': 'ERR_SVC_TIMEOUT',
        'SERVICE_INVALID_OP': 'ERR_SVC_INVALID_OP',
    }
    
    # Severity levels mapping
    SEVERITY_LEVELS = {
        'LOW': 1,
        'MEDIUM': 2,
        'HIGH': 3,
        'CRITICAL': 4
    }
    
    # Recovery strategies
    RECOVERY_STRATEGIES = {
        'RETRY': 'retry',
        'FALLBACK': 'fallback',
        'FAIL_FAST': 'fail_fast',
        'IGNORE': 'ignore',
        'MANUAL': 'manual_intervention'
    }
    
    # Error categories
    CATEGORIES = {
        'UI': 'ui',
        'PLATFORM': 'platform',
        'DOWNLOAD': 'download',
        'REPOSITORY': 'repository',
        'SERVICE': 'service',
        'DATABASE': 'database',
        'NETWORK': 'network',
        'VALIDATION': 'validation',
        'AUTHENTICATION': 'authentication',
        'PERMISSION': 'permission',
        'FILE_SYSTEM': 'file_system',
        'CONFIGURATION': 'configuration',
        'UNKNOWN': 'unknown',
        'FATAL': 'fatal'
    }
    
    @classmethod
    def get_message(cls, error_type: str) -> str:
        """Get error message by type"""
        return cls.MESSAGES.get(error_type, cls.MESSAGES['GENERIC_ERROR'])
    
    @classmethod
    def get_code(cls, error_type: str) -> str:
        """Get error code by type"""
        return cls.CODES.get(error_type, cls.CODES['UNKNOWN'])
    
    @classmethod
    def get_severity_level(cls, severity: str) -> int:
        """Get numeric severity level"""
        return cls.SEVERITY_LEVELS.get(severity.upper(), 2)
    
    @classmethod
    def is_retryable(cls, error_category: str) -> bool:
        """Check if error category is typically retryable"""
        retryable_categories = ['NETWORK', 'PLATFORM', 'DATABASE', 'DOWNLOAD']
        return error_category.upper() in retryable_categories


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