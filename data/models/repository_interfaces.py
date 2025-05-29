"""
Extended Repository Interfaces for Social Download Manager v2.0

Additional repository interfaces for download tracking, sessions, and other domain models.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from .base import EntityId
from .downloads import DownloadModel, DownloadSession, DownloadError, DownloadStatus
from .repositories import IRepository


class IDownloadRepository(IRepository[DownloadModel]):
    """
    Repository interface for download tracking
    
    Provides operations for managing download records with
    specialized queries for download management.
    """
    
    @abstractmethod
    def find_by_content_id(self, content_id: EntityId) -> List[DownloadModel]:
        """Find downloads by content ID"""
        pass
    
    @abstractmethod
    def find_by_status(self, status: DownloadStatus) -> List[DownloadModel]:
        """Find downloads by status"""
        pass
    
    @abstractmethod
    def find_active_downloads(self) -> List[DownloadModel]:
        """Find all active downloads (queued, downloading, processing)"""
        pass
    
    @abstractmethod
    def find_completed_downloads(self) -> List[DownloadModel]:
        """Find all completed downloads"""
        pass
    
    @abstractmethod
    def find_failed_downloads(self) -> List[DownloadModel]:
        """Find all failed downloads"""
        pass
    
    @abstractmethod
    def find_by_file_path(self, file_path: str) -> Optional[DownloadModel]:
        """Find download by output file path"""
        pass
    
    @abstractmethod
    def find_recent_downloads(self, days: int = 7) -> List[DownloadModel]:
        """Find downloads from recent days"""
        pass
    
    @abstractmethod
    def get_download_statistics(self) -> Dict[str, Any]:
        """Get comprehensive download statistics"""
        pass
    
    @abstractmethod
    def find_downloads_by_size_range(self, min_size: int, max_size: int) -> List[DownloadModel]:
        """Find downloads within file size range"""
        pass
    
    @abstractmethod
    def find_retryable_downloads(self) -> List[DownloadModel]:
        """Find downloads that can be retried"""
        pass


class IDownloadSessionRepository(IRepository[DownloadSession]):
    """
    Repository interface for download sessions
    
    Manages download session lifecycle and progress tracking.
    """
    
    @abstractmethod
    def find_by_content_id(self, content_id: EntityId) -> List[DownloadSession]:
        """Find sessions by content ID"""
        pass
    
    @abstractmethod
    def find_by_status(self, status: DownloadStatus) -> List[DownloadSession]:
        """Find sessions by status"""
        pass
    
    @abstractmethod
    def find_active_sessions(self) -> List[DownloadSession]:
        """Find all active download sessions"""
        pass
    
    @abstractmethod
    def find_sessions_by_downloader_type(self, downloader_type: str) -> List[DownloadSession]:
        """Find sessions by downloader type"""
        pass
    
    @abstractmethod
    def find_longest_running_sessions(self, limit: int = 10) -> List[DownloadSession]:
        """Find the longest running active sessions"""
        pass
    
    @abstractmethod
    def find_stalled_sessions(self, timeout_minutes: int = 30) -> List[DownloadSession]:
        """Find sessions that appear to be stalled"""
        pass
    
    @abstractmethod
    def cleanup_completed_sessions(self, older_than_days: int = 30) -> int:
        """Clean up old completed sessions and return count removed"""
        pass
    
    @abstractmethod
    def get_session_performance_stats(self) -> Dict[str, Any]:
        """Get session performance statistics"""
        pass


class IDownloadErrorRepository(IRepository[DownloadError]):
    """
    Repository interface for download error tracking
    
    Manages error records and analysis for download failures.
    """
    
    @abstractmethod
    def find_by_download_id(self, download_id: EntityId) -> List[DownloadError]:
        """Find errors by download ID"""
        pass
    
    @abstractmethod
    def find_by_error_type(self, error_type: str) -> List[DownloadError]:
        """Find errors by type"""
        pass
    
    @abstractmethod
    def find_recent_errors(self, hours: int = 24) -> List[DownloadError]:
        """Find errors from recent hours"""
        pass
    
    @abstractmethod
    def find_retryable_errors(self) -> List[DownloadError]:
        """Find errors that can be retried"""
        pass
    
    @abstractmethod
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error occurrence statistics"""
        pass
    
    @abstractmethod
    def get_most_common_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most frequently occurring errors"""
        pass
    
    @abstractmethod
    def find_errors_by_pattern(self, pattern: str) -> List[DownloadError]:
        """Find errors matching a message pattern"""
        pass
    
    @abstractmethod
    def cleanup_old_errors(self, older_than_days: int = 90) -> int:
        """Clean up old error records and return count removed"""
        pass


class IUserRepository(IRepository):
    """
    Repository interface for user management
    
    Note: This is a placeholder for future user management features.
    Currently not implemented but included for completeness.
    """
    
    @abstractmethod
    def find_by_username(self, username: str) -> Optional:
        """Find user by username"""
        pass
    
    @abstractmethod
    def find_by_email(self, email: str) -> Optional:
        """Find user by email"""
        pass
    
    @abstractmethod
    def verify_credentials(self, username: str, password_hash: str) -> bool:
        """Verify user credentials"""
        pass


class IConfigurationRepository(IRepository):
    """
    Repository interface for application configuration
    
    Manages application settings and user preferences.
    """
    
    @abstractmethod
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get configuration setting value"""
        pass
    
    @abstractmethod
    def set_setting(self, key: str, value: Any) -> bool:
        """Set configuration setting value"""
        pass
    
    @abstractmethod
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all configuration settings"""
        pass
    
    @abstractmethod
    def delete_setting(self, key: str) -> bool:
        """Delete configuration setting"""
        pass
    
    @abstractmethod
    def reset_to_defaults(self) -> bool:
        """Reset all settings to default values"""
        pass


class IAnalyticsRepository(IRepository):
    """
    Repository interface for analytics and metrics
    
    Manages usage statistics and performance metrics.
    """
    
    @abstractmethod
    def record_download_event(self, event_data: Dict[str, Any]) -> bool:
        """Record a download event for analytics"""
        pass
    
    @abstractmethod
    def get_usage_statistics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get usage statistics for date range"""
        pass
    
    @abstractmethod
    def get_platform_usage_trends(self, days: int = 30) -> Dict[str, List]:
        """Get platform usage trends"""
        pass
    
    @abstractmethod
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get application performance metrics"""
        pass 