"""
Data Mappers for UI v1.2.1 to v2.0 Architecture Bridge

This module contains data mapper implementations that transform data structures
between legacy v1.2.1 formats and the new v2.0 repository/architecture formats.
"""

import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import re

# Import v2.0 data models
from data.models.content import VideoContent, ContentStatus, ContentType, PlatformType
from data.models.downloads import DownloadModel, DownloadStatus
from data.models.base import BaseEntity, EntityId

# Import legacy data structures (v1.2.1 format simulation)
from .interfaces import IDataMapperAdapter


class DataMappingError(Exception):
    """Exception raised when data mapping fails"""
    pass


class DataValidationError(Exception):
    """Exception raised when data validation fails"""
    pass


@dataclass
class LegacyVideoInfo:
    """Legacy video information structure (v1.2.1 format)"""
    url: str
    title: str = ""
    creator: str = ""
    duration: str = ""
    quality: str = ""
    format: str = ""
    size: str = ""
    hashtags: List[str] = None
    thumbnail_url: str = ""
    platform: str = ""
    
    def __post_init__(self):
        if self.hashtags is None:
            self.hashtags = []


@dataclass
class LegacyDownloadInfo:
    """Legacy download information structure (v1.2.1 format)"""
    video_url: str
    title: str
    creator: str
    quality: str
    format: str
    size: str
    status: str
    date: str
    file_path: str = ""
    hashtags: List[str] = None
    platform: str = ""
    
    def __post_init__(self):
        if self.hashtags is None:
            self.hashtags = []


class VideoDataMapper(IDataMapperAdapter):
    """
    Data mapper for video information between legacy and v2.0 formats.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._supported_types = ["video_info", "video_metadata", "video_content"]
    
    def map_to_v2(self, legacy_data: Any) -> Optional[VideoContent]:
        """
        Map legacy video information to v2.0 VideoContent format.
        
        Args:
            legacy_data: Legacy video data (dict or LegacyVideoInfo)
            
        Returns:
            VideoContent instance or None if mapping failed
        """
        try:
            # Handle different input types
            if isinstance(legacy_data, dict):
                legacy_video = LegacyVideoInfo(**legacy_data)
            elif isinstance(legacy_data, LegacyVideoInfo):
                legacy_video = legacy_data
            else:
                raise DataMappingError(f"Unsupported legacy data type: {type(legacy_data)}")
            
            # Validate legacy data
            if not self.validate_legacy_data(legacy_video):
                self.logger.error("Legacy video data validation failed")
                return None
            
            # Map platform type
            platform_type = self._map_platform_type(legacy_video.platform)
            
            # Create VideoContent using ContentModel fields
            video_content = VideoContent(
                url=legacy_video.url,
                platform=platform_type,
                content_type=ContentType.VIDEO,
                status=ContentStatus.PENDING,
                title=legacy_video.title or "Unknown Title",
                author=legacy_video.creator or "Unknown Creator",
                duration=self._parse_duration(legacy_video.duration),
                quality=legacy_video.quality or "unknown",
                format=legacy_video.format or "unknown",
                file_size=self._parse_size(legacy_video.size),
                thumbnail_url=legacy_video.thumbnail_url,
                hashtags=legacy_video.hashtags or [],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            self.logger.debug(f"Successfully mapped legacy video to v2.0: {video_content.url}")
            return video_content
            
        except Exception as e:
            self.logger.error(f"Failed to map legacy video data to v2.0: {e}")
            return None
    
    def map_to_legacy(self, v2_data: Any) -> Optional[LegacyVideoInfo]:
        """
        Map v2.0 VideoContent to legacy video information format.
        
        Args:
            v2_data: VideoContent instance
            
        Returns:
            LegacyVideoInfo instance or None if mapping failed
        """
        try:
            if not isinstance(v2_data, VideoContent):
                raise DataMappingError(f"Expected VideoContent, got {type(v2_data)}")
            
            # Validate v2.0 data
            if not self.validate_v2_data(v2_data):
                self.logger.error("v2.0 video data validation failed")
                return None
            
            # Map to legacy format using ContentModel fields
            legacy_video = LegacyVideoInfo(
                url=v2_data.url,
                title=v2_data.title or "",
                creator=v2_data.author or "",
                duration=self._format_duration(v2_data.duration),
                quality=v2_data.quality or "",
                format=v2_data.format or "",
                size=self._format_size(v2_data.file_size),
                hashtags=(v2_data.hashtags or []).copy(),
                thumbnail_url=v2_data.thumbnail_url or "",
                platform=v2_data.platform.value if v2_data.platform else "unknown"
            )
            
            self.logger.debug(f"Successfully mapped v2.0 video to legacy: {v2_data.url}")
            return legacy_video
            
        except Exception as e:
            self.logger.error(f"Failed to map v2.0 video data to legacy: {e}")
            return None
    
    def validate_legacy_data(self, data: Any) -> bool:
        """Validate legacy video data"""
        try:
            if isinstance(data, dict):
                # Check required fields
                required_fields = ["url"]
                return all(field in data for field in required_fields)
            elif isinstance(data, LegacyVideoInfo):
                return bool(data.url)
            return False
        except Exception as e:
            self.logger.error(f"Legacy data validation error: {e}")
            return False
    
    def validate_v2_data(self, data: Any) -> bool:
        """Validate v2.0 video data"""
        try:
            if not isinstance(data, VideoContent):
                return False
            return bool(data.url and data.content_id and data.metadata)
        except Exception as e:
            self.logger.error(f"v2.0 data validation error: {e}")
            return False
    
    def get_supported_types(self) -> List[str]:
        """Get supported data types"""
        return self._supported_types.copy()
    
    def _map_platform_type(self, platform_str: str) -> PlatformType:
        """Map platform string to PlatformType enum"""
        platform_mapping = {
            "tiktok": PlatformType.TIKTOK,
            "youtube": PlatformType.YOUTUBE,
            "instagram": PlatformType.INSTAGRAM,
            "facebook": PlatformType.FACEBOOK
        }
        return platform_mapping.get(platform_str.lower(), PlatformType.UNKNOWN)
    
    def _parse_duration(self, duration_str: str) -> int:
        """Parse duration string to seconds"""
        try:
            if not duration_str:
                return 0
            # Handle formats like "1:30", "90s", "1m30s"
            if ":" in duration_str:
                parts = duration_str.split(":")
                return int(parts[0]) * 60 + int(parts[1])
            elif duration_str.endswith("s"):
                return int(duration_str[:-1])
            elif duration_str.endswith("m"):
                return int(duration_str[:-1]) * 60
            return int(duration_str)
        except (ValueError, IndexError):
            return 0
    
    def _format_duration(self, duration_seconds: int) -> str:
        """Format duration seconds to string"""
        if duration_seconds <= 0:
            return ""
        minutes = duration_seconds // 60
        seconds = duration_seconds % 60
        return f"{minutes}:{seconds:02d}"
    
    def _parse_size(self, size_str: str) -> int:
        """Parse size string to bytes"""
        try:
            if not size_str:
                return 0
            size_str = size_str.upper()
            if "MB" in size_str:
                return int(float(size_str.replace("MB", "").strip()) * 1024 * 1024)
            elif "KB" in size_str:
                return int(float(size_str.replace("KB", "").strip()) * 1024)
            elif "GB" in size_str:
                return int(float(size_str.replace("GB", "").strip()) * 1024 * 1024 * 1024)
            return int(size_str)
        except (ValueError, AttributeError):
            return 0
    
    def _format_size(self, size_bytes: int) -> str:
        """Format size bytes to string"""
        if size_bytes <= 0:
            return ""
        if size_bytes >= 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
        elif size_bytes >= 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        elif size_bytes >= 1024:
            return f"{size_bytes / 1024:.1f} KB"
        return f"{size_bytes} B"
    
    def _generate_content_id(self, url: str) -> str:
        """Generate content ID from URL"""
        return hashlib.md5(url.encode()).hexdigest()


class DownloadDataMapper(IDataMapperAdapter):
    """
    Data mapper for download information between legacy and v2.0 formats.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._supported_types = ["download_info", "download_record", "download_history"]
    
    def map_to_v2(self, legacy_data: Any) -> Optional[DownloadModel]:
        """
        Map legacy download information to v2.0 DownloadModel format.
        
        Args:
            legacy_data: Legacy download data (dict or LegacyDownloadInfo)
            
        Returns:
            DownloadModel instance or None if mapping failed
        """
        try:
            # Handle different input types
            if isinstance(legacy_data, dict):
                legacy_download = LegacyDownloadInfo(**legacy_data)
            elif isinstance(legacy_data, LegacyDownloadInfo):
                legacy_download = legacy_data
            else:
                raise DataMappingError(f"Unsupported legacy data type: {type(legacy_data)}")
            
            # Validate legacy data
            if not self.validate_legacy_data(legacy_download):
                self.logger.error("Legacy download data validation failed")
                return None
            
            # Map download status
            download_status = self._map_download_status(legacy_download.status)
            
            # Parse date and size
            parsed_date = self._parse_date(legacy_download.date)
            file_size = self._parse_size(legacy_download.size)
            
            # Create DownloadModel using correct field names
            download_record = DownloadModel(
                content_id=self._generate_content_id(legacy_download.video_url),
                url=legacy_download.video_url,
                status=download_status,
                quality=legacy_download.quality or "unknown",
                format=legacy_download.format or "unknown",
                filename=legacy_download.title or "unknown",
                file_size=file_size,
                file_path=legacy_download.file_path,
                progress_percentage=100.0 if download_status == DownloadStatus.COMPLETED else 0.0,
                queued_at=parsed_date,
                completed_at=parsed_date if download_status == DownloadStatus.COMPLETED else None,
                created_at=parsed_date or datetime.now(),
                updated_at=datetime.now()
            )
            
            self.logger.debug(f"Successfully mapped legacy download to v2.0: {download_record.url}")
            return download_record
            
        except Exception as e:
            self.logger.error(f"Failed to map legacy download data to v2.0: {e}")
            return None
    
    def map_to_legacy(self, v2_data: Any) -> Optional[LegacyDownloadInfo]:
        """
        Map v2.0 DownloadModel to legacy download information format.
        
        Args:
            v2_data: DownloadModel instance
            
        Returns:
            LegacyDownloadInfo instance or None if mapping failed
        """
        try:
            if not isinstance(v2_data, DownloadModel):
                raise DataMappingError(f"Expected DownloadModel, got {type(v2_data)}")
            
            # Validate v2.0 data
            if not self.validate_v2_data(v2_data):
                self.logger.error("v2.0 download data validation failed")
                return None
            
            # Map to legacy format using DownloadModel fields
            legacy_download = LegacyDownloadInfo(
                video_url=v2_data.url,
                title=v2_data.filename or "Unknown",
                creator="Unknown",  # Not available in DownloadModel
                quality=v2_data.quality or "unknown",
                format=v2_data.format or "unknown",
                size=self._format_size(v2_data.file_size),
                status=self._format_download_status(v2_data.status),
                date=v2_data.completed_at.strftime("%Y-%m-%d") if v2_data.completed_at else v2_data.created_at.strftime("%Y-%m-%d"),
                file_path=v2_data.file_path or "",
                hashtags=[],  # Not available in DownloadModel
                platform=""  # Not directly available in DownloadModel
            )
            
            self.logger.debug(f"Successfully mapped v2.0 download to legacy: {v2_data.url}")
            return legacy_download
            
        except Exception as e:
            self.logger.error(f"Failed to map v2.0 download data to legacy: {e}")
            return None
    
    def validate_legacy_data(self, data: Any) -> bool:
        """Validate legacy download data"""
        try:
            if isinstance(data, dict):
                required_fields = ["video_url", "title", "status"]
                return all(field in data for field in required_fields)
            elif isinstance(data, LegacyDownloadInfo):
                return bool(data.video_url and data.title)
            return False
        except Exception as e:
            self.logger.error(f"Legacy data validation error: {e}")
            return False
    
    def validate_v2_data(self, data: Any) -> bool:
        """Validate v2.0 download data"""
        try:
            if not isinstance(data, DownloadModel):
                return False
            return bool(data.content_id and data.url)
        except Exception as e:
            self.logger.error(f"v2.0 data validation error: {e}")
            return False
    
    def get_supported_types(self) -> List[str]:
        """Get supported data types"""
        return self._supported_types.copy()
    
    def _map_download_status(self, status_str: str) -> DownloadStatus:
        """Map status string to DownloadStatus enum"""
        status_mapping = {
            "completed": DownloadStatus.COMPLETED,
            "downloading": DownloadStatus.IN_PROGRESS,
            "pending": DownloadStatus.PENDING,
            "failed": DownloadStatus.FAILED,
            "cancelled": DownloadStatus.CANCELLED,
            "paused": DownloadStatus.PAUSED
        }
        return status_mapping.get(status_str.lower(), DownloadStatus.PENDING)
    
    def _format_download_status(self, status: DownloadStatus) -> str:
        """Format DownloadStatus enum to string"""
        status_mapping = {
            DownloadStatus.COMPLETED: "completed",
            DownloadStatus.IN_PROGRESS: "downloading",
            DownloadStatus.PENDING: "pending",
            DownloadStatus.FAILED: "failed",
            DownloadStatus.CANCELLED: "cancelled",
            DownloadStatus.PAUSED: "paused"
        }
        return status_mapping.get(status, "pending")
    
    def _map_platform_type(self, platform_str: str) -> PlatformType:
        """Map platform string to PlatformType enum"""
        platform_mapping = {
            "tiktok": PlatformType.TIKTOK,
            "youtube": PlatformType.YOUTUBE,
            "instagram": PlatformType.INSTAGRAM,
            "facebook": PlatformType.FACEBOOK
        }
        return platform_mapping.get(platform_str.lower(), PlatformType.UNKNOWN)
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime"""
        try:
            if not date_str:
                return datetime.now()
            # Try different date formats
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
                "%d/%m/%Y %H:%M:%S",
                "%d/%m/%Y"
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            return datetime.now()
        except Exception:
            return datetime.now()
    
    def _parse_size(self, size_str: str) -> int:
        """Parse size string to bytes (reuse from VideoDataMapper)"""
        try:
            if not size_str:
                return 0
            size_str = size_str.upper()
            if "MB" in size_str:
                return int(float(size_str.replace("MB", "").strip()) * 1024 * 1024)
            elif "KB" in size_str:
                return int(float(size_str.replace("KB", "").strip()) * 1024)
            elif "GB" in size_str:
                return int(float(size_str.replace("GB", "").strip()) * 1024 * 1024 * 1024)
            return int(size_str)
        except (ValueError, AttributeError):
            return 0
    
    def _format_size(self, size_bytes: int) -> str:
        """Format size bytes to string (reuse from VideoDataMapper)"""
        if size_bytes <= 0:
            return ""
        if size_bytes >= 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
        elif size_bytes >= 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        elif size_bytes >= 1024:
            return f"{size_bytes / 1024:.1f} KB"
        return f"{size_bytes} B"
    
    def _generate_download_id(self, url: str, date: str) -> str:
        """Generate download ID from URL and date"""
        return hashlib.md5(f"{url}_{date}".encode()).hexdigest()
    
    def _generate_content_id(self, url: str) -> str:
        """Generate content ID from URL"""
        return hashlib.md5(url.encode()).hexdigest()


class ConfigurationDataMapper(IDataMapperAdapter):
    """
    Data mapper for configuration data between legacy and v2.0 formats.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._supported_types = ["config", "settings", "preferences"]
    
    def map_to_v2(self, legacy_data: Any) -> Optional[Dict[str, Any]]:
        """
        Map legacy configuration to v2.0 format.
        
        Args:
            legacy_data: Legacy configuration data
            
        Returns:
            v2.0 configuration dict or None if mapping failed
        """
        try:
            if not isinstance(legacy_data, dict):
                raise DataMappingError(f"Expected dict, got {type(legacy_data)}")
            
            # Map legacy config keys to v2.0 format
            v2_config = {
                "app": {
                    "name": legacy_data.get("app_name", "Social Download Manager"),
                    "version": legacy_data.get("version", "2.0.0"),
                    "theme": legacy_data.get("current_theme", "dark"),
                    "language": legacy_data.get("language", "en")
                },
                "download": {
                    "output_folder": legacy_data.get("output_folder", ""),
                    "quality": legacy_data.get("default_quality", "best"),
                    "format": legacy_data.get("default_format", "mp4"),
                    "concurrent_downloads": legacy_data.get("max_concurrent", 3)
                },
                "ui": {
                    "window_geometry": legacy_data.get("window_geometry", {}),
                    "table_headers": legacy_data.get("table_headers", {}),
                    "tab_preferences": legacy_data.get("tab_preferences", {})
                },
                "platforms": {
                    "tiktok": {
                        "enabled": legacy_data.get("tiktok_enabled", True),
                        "cookies": legacy_data.get("tiktok_cookies", "")
                    },
                    "youtube": {
                        "enabled": legacy_data.get("youtube_enabled", False),
                        "api_key": legacy_data.get("youtube_api_key", "")
                    }
                }
            }
            
            self.logger.debug("Successfully mapped legacy config to v2.0")
            return v2_config
            
        except Exception as e:
            self.logger.error(f"Failed to map legacy config to v2.0: {e}")
            return None
    
    def map_to_legacy(self, v2_data: Any) -> Optional[Dict[str, Any]]:
        """
        Map v2.0 configuration to legacy format.
        
        Args:
            v2_data: v2.0 configuration data
            
        Returns:
            Legacy configuration dict or None if mapping failed
        """
        try:
            if not isinstance(v2_data, dict):
                raise DataMappingError(f"Expected dict, got {type(v2_data)}")
            
            # Map v2.0 config to legacy format
            legacy_config = {
                "app_name": v2_data.get("app", {}).get("name", "Social Download Manager"),
                "version": v2_data.get("app", {}).get("version", "1.2.1"),
                "current_theme": v2_data.get("app", {}).get("theme", "dark"),
                "language": v2_data.get("app", {}).get("language", "en"),
                "output_folder": v2_data.get("download", {}).get("output_folder", ""),
                "default_quality": v2_data.get("download", {}).get("quality", "best"),
                "default_format": v2_data.get("download", {}).get("format", "mp4"),
                "max_concurrent": v2_data.get("download", {}).get("concurrent_downloads", 3),
                "window_geometry": v2_data.get("ui", {}).get("window_geometry", {}),
                "table_headers": v2_data.get("ui", {}).get("table_headers", {}),
                "tab_preferences": v2_data.get("ui", {}).get("tab_preferences", {}),
                "tiktok_enabled": v2_data.get("platforms", {}).get("tiktok", {}).get("enabled", True),
                "tiktok_cookies": v2_data.get("platforms", {}).get("tiktok", {}).get("cookies", ""),
                "youtube_enabled": v2_data.get("platforms", {}).get("youtube", {}).get("enabled", False),
                "youtube_api_key": v2_data.get("platforms", {}).get("youtube", {}).get("api_key", "")
            }
            
            self.logger.debug("Successfully mapped v2.0 config to legacy")
            return legacy_config
            
        except Exception as e:
            self.logger.error(f"Failed to map v2.0 config to legacy: {e}")
            return None
    
    def validate_legacy_data(self, data: Any) -> bool:
        """Validate legacy configuration data"""
        try:
            return isinstance(data, dict)
        except Exception as e:
            self.logger.error(f"Legacy config validation error: {e}")
            return False
    
    def validate_v2_data(self, data: Any) -> bool:
        """Validate v2.0 configuration data"""
        try:
            if not isinstance(data, dict):
                return False
            # Check for required sections
            required_sections = ["app", "download", "ui", "platforms"]
            return all(section in data for section in required_sections)
        except Exception as e:
            self.logger.error(f"v2.0 config validation error: {e}")
            return False
    
    def get_supported_types(self) -> List[str]:
        """Get supported data types"""
        return self._supported_types.copy()


# Factory functions for easy mapper creation
def create_video_mapper() -> VideoDataMapper:
    """Create a VideoDataMapper instance"""
    return VideoDataMapper()


def create_download_mapper() -> DownloadDataMapper:
    """Create a DownloadDataMapper instance"""
    return DownloadDataMapper()


def create_config_mapper() -> ConfigurationDataMapper:
    """Create a ConfigurationDataMapper instance"""
    return ConfigurationDataMapper()


# Global mapper instances
_video_mapper = None
_download_mapper = None
_config_mapper = None


def get_video_mapper() -> VideoDataMapper:
    """Get global VideoDataMapper instance"""
    global _video_mapper
    if _video_mapper is None:
        _video_mapper = VideoDataMapper()
    return _video_mapper


def get_download_mapper() -> DownloadDataMapper:
    """Get global DownloadDataMapper instance"""
    global _download_mapper
    if _download_mapper is None:
        _download_mapper = DownloadDataMapper()
    return _download_mapper


def get_config_mapper() -> ConfigurationDataMapper:
    """Get global ConfigurationDataMapper instance"""
    global _config_mapper
    if _config_mapper is None:
        _config_mapper = ConfigurationDataMapper()
    return _config_mapper 