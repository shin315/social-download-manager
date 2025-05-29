"""
Download Repository Implementations for Social Download Manager v2.0

Concrete implementations of download-related repositories providing
specialized data access operations for download management.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from .base import EntityId
from .downloads import DownloadModel, DownloadSession, DownloadError, DownloadStatus
from .repositories import BaseRepository, RepositoryError, RepositoryRegistry
from .repository_interfaces import (
    IDownloadRepository, 
    IDownloadSessionRepository, 
    IDownloadErrorRepository
)
from .advanced_queries import QueryMethodsMixin, DateRange, SortDirection
from .transaction_repository import TransactionAwareRepositoryMixin
from .performance_optimizations import (
    PerformanceOptimizedRepository, performance_optimized, CacheStrategy,
    get_global_cache_provider, get_global_performance_monitor
)


class DownloadRepository(BaseRepository[DownloadModel], IDownloadRepository, 
                        QueryMethodsMixin, TransactionAwareRepositoryMixin):
    """
    Download repository implementation
    
    Provides download-specific data access operations with
    optimized queries for download management.
    """
    
    def find_by_content_id(self, content_id: EntityId) -> List[DownloadModel]:
        """Find downloads by content ID"""
        try:
            return self.find_by_criteria({'content_id': content_id})
        except Exception as e:
            self._logger.error(f"Failed to find downloads by content ID: {e}")
            raise RepositoryError(f"Find by content ID failed: {e}")
    
    def find_by_status(self, status: DownloadStatus) -> List[DownloadModel]:
        """Find downloads by status"""
        try:
            return self.find_by_criteria({'status': status.value})
        except Exception as e:
            self._logger.error(f"Failed to find downloads by status: {e}")
            raise RepositoryError(f"Find by status failed: {e}")
    
    def find_active_downloads(self) -> List[DownloadModel]:
        """Find all active downloads (queued, downloading, processing)"""
        try:
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
            
        except Exception as e:
            self._logger.error(f"Failed to find active downloads: {e}")
            raise RepositoryError(f"Find active downloads failed: {e}")
    
    def find_completed_downloads(self) -> List[DownloadModel]:
        """Find all completed downloads"""
        return self.find_by_status(DownloadStatus.COMPLETED)
    
    def find_failed_downloads(self) -> List[DownloadModel]:
        """Find all failed downloads"""
        return self.find_by_status(DownloadStatus.FAILED)
    
    def find_by_file_path(self, file_path: str) -> Optional[DownloadModel]:
        """Find download by output file path"""
        try:
            results = self.find_by_criteria({'file_path': file_path})
            return results[0] if results else None
        except Exception as e:
            self._logger.error(f"Failed to find download by file path: {e}")
            raise RepositoryError(f"Find by file path failed: {e}")
    
    def find_recent_downloads(self, days: int = 7) -> List[DownloadModel]:
        """Find downloads from recent days"""
        try:
            date_range = DateRange.last_days(days)
            return self.find_by_date_range("created_at", date_range)
            
        except Exception as e:
            self._logger.error(f"Failed to find recent downloads: {e}")
            raise RepositoryError(f"Find recent downloads failed: {e}")
    
    def get_download_statistics(self) -> Dict[str, Any]:
        """Get comprehensive download statistics"""
        try:
            stats = {}
            
            # Count by status using advanced query
            status_counts = self.count_by_field('status')
            stats.update(status_counts)
            
            # Total downloads
            stats['total_downloads'] = self.count()
            
            # Success rate
            completed_count = len(self.find_completed_downloads())
            failed_count = len(self.find_failed_downloads())
            total_finished = completed_count + failed_count
            
            if total_finished > 0:
                stats['success_rate'] = (completed_count / total_finished) * 100
            else:
                stats['success_rate'] = 0.0
            
            # Recent activity
            stats['recent_downloads_7_days'] = len(self.find_recent_downloads(7))
            stats['recent_downloads_30_days'] = len(self.find_recent_downloads(30))
            
            # File size statistics
            file_size_stats = self.get_field_statistics('file_size')
            stats['file_size_stats'] = file_size_stats
            
            return stats
            
        except Exception as e:
            self._logger.error(f"Failed to get download statistics: {e}")
            raise RepositoryError(f"Get download statistics failed: {e}")
    
    def find_downloads_by_size_range(self, min_size: int, max_size: int) -> List[DownloadModel]:
        """Find downloads within file size range"""
        try:
            query, params = (self.advanced_query()
                           .where_not_deleted()
                           .where("file_size >= ?", min_size)
                           .where("file_size <= ?", max_size)
                           .where("file_size IS NOT NULL")
                           .order_by("file_size", "DESC")
                           .build())
            
            return self.execute_query(query, params)
            
        except Exception as e:
            self._logger.error(f"Failed to find downloads by size range: {e}")
            raise RepositoryError(f"Find downloads by size range failed: {e}")
    
    def find_retryable_downloads(self) -> List[DownloadModel]:
        """Find downloads that can be retried"""
        try:
            # Find failed downloads with retry count less than max
            query, params = (self.advanced_query()
                           .where_not_deleted()
                           .where("status = ?", DownloadStatus.FAILED.value)
                           .where("retry_count < 3")  # Assuming max retries is 3
                           .order_by("created_at", "DESC")
                           .build())
            
            return self.execute_query(query, params)
            
        except Exception as e:
            self._logger.error(f"Failed to find retryable downloads: {e}")
            raise RepositoryError(f"Find retryable downloads failed: {e}")
    
    def get_download_trends(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get download trends over time"""
        return self.find_trends("created_at", days)
    
    def find_downloads_with_pagination(self, page: int = 1, page_size: int = 20, 
                                     status: Optional[DownloadStatus] = None) -> Dict[str, Any]:
        """Find downloads with pagination and optional status filter"""
        try:
            # Build query with optional status filter
            query_builder = (self.advanced_query()
                           .where_not_deleted())
            
            if status:
                query_builder.where("status = ?", status.value)
            
            # Get total count for pagination
            count_query, count_params = query_builder.select_count().build()
            connection = self._model._get_connection()
            try:
                cursor = connection.cursor()
                cursor.execute(count_query, count_params)
                total_count = cursor.fetchone()[0]
                cursor.close()
            finally:
                self._model._return_connection(connection)
            
            # Get paginated results
            offset = (page - 1) * page_size
            query, params = (query_builder
                           .select(["*"])  # Reset to select all fields
                           .order_by("created_at", SortDirection.DESC.value)
                           .limit(page_size, offset)
                           .build())
            
            items = self.execute_query(query, params)
            
            # Calculate pagination info
            total_pages = (total_count + page_size - 1) // page_size
            has_next = page < total_pages
            has_prev = page > 1
            
            return {
                'items': items,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_next': has_next,
                    'has_prev': has_prev
                }
            }
            
        except Exception as e:
            self._logger.error(f"Failed to find downloads with pagination: {e}")
            raise RepositoryError(f"Pagination query failed: {e}")


class DownloadSessionRepository(BaseRepository[DownloadSession], IDownloadSessionRepository, 
                               QueryMethodsMixin, TransactionAwareRepositoryMixin):
    """
    Download session repository implementation
    
    Manages download session lifecycle and progress tracking.
    """
    
    def find_by_content_id(self, content_id: EntityId) -> List[DownloadSession]:
        """Find sessions by content ID"""
        try:
            return self.find_by_criteria({'content_id': content_id})
        except Exception as e:
            self._logger.error(f"Failed to find sessions by content ID: {e}")
            raise RepositoryError(f"Find sessions by content ID failed: {e}")
    
    def find_by_status(self, status: DownloadStatus) -> List[DownloadSession]:
        """Find sessions by status"""
        try:
            return self.find_by_criteria({'status': status.value})
        except Exception as e:
            self._logger.error(f"Failed to find sessions by status: {e}")
            raise RepositoryError(f"Find sessions by status failed: {e}")
    
    def find_active_sessions(self) -> List[DownloadSession]:
        """Find all active download sessions"""
        try:
            active_statuses = [
                DownloadStatus.STARTING,
                DownloadStatus.DOWNLOADING,
                DownloadStatus.PROCESSING,
                DownloadStatus.RETRYING
            ]
            
            results = []
            for status in active_statuses:
                results.extend(self.find_by_status(status))
            return results
            
        except Exception as e:
            self._logger.error(f"Failed to find active sessions: {e}")
            raise RepositoryError(f"Find active sessions failed: {e}")
    
    def find_sessions_by_downloader_type(self, downloader_type: str) -> List[DownloadSession]:
        """Find sessions by downloader type"""
        try:
            return self.find_by_criteria({'downloader_type': downloader_type})
        except Exception as e:
            self._logger.error(f"Failed to find sessions by downloader type: {e}")
            raise RepositoryError(f"Find sessions by downloader type failed: {e}")
    
    def find_longest_running_sessions(self, limit: int = 10) -> List[DownloadSession]:
        """Find the longest running active sessions"""
        try:
            # Find active sessions and calculate duration
            active_sessions = self.find_active_sessions()
            now = datetime.now()
            
            # Calculate duration for each session
            sessions_with_duration = []
            for session in active_sessions:
                if session.started_at:
                    duration = (now - session.started_at).total_seconds()
                    sessions_with_duration.append((session, duration))
            
            # Sort by duration (longest first) and return top N
            sessions_with_duration.sort(key=lambda x: x[1], reverse=True)
            return [session for session, _ in sessions_with_duration[:limit]]
            
        except Exception as e:
            self._logger.error(f"Failed to find longest running sessions: {e}")
            raise RepositoryError(f"Find longest running sessions failed: {e}")
    
    def find_stalled_sessions(self, timeout_minutes: int = 30) -> List[DownloadSession]:
        """Find sessions that appear to be stalled"""
        try:
            timeout_datetime = datetime.now() - timedelta(minutes=timeout_minutes)
            timeout_iso = timeout_datetime.isoformat()
            
            # Find active sessions that haven't been updated recently
            query, params = (self.advanced_query()
                           .where_not_deleted()
                           .where_or([
                               "status = ?",
                               "status = ?",
                               "status = ?"
                           ], [
                               DownloadStatus.DOWNLOADING.value,
                               DownloadStatus.PROCESSING.value,
                               DownloadStatus.STARTING.value
                           ])
                           .where("updated_at < ?", timeout_iso)
                           .order_by("updated_at", "ASC")
                           .build())
            
            return self.execute_query(query, params)
            
        except Exception as e:
            self._logger.error(f"Failed to find stalled sessions: {e}")
            raise RepositoryError(f"Find stalled sessions failed: {e}")
    
    def cleanup_completed_sessions(self, older_than_days: int = 30) -> int:
        """Clean up old completed sessions and return count removed"""
        try:
            cutoff_date = datetime.now() - timedelta(days=older_than_days)
            cutoff_iso = cutoff_date.isoformat()
            
            # Find old completed sessions
            query, params = (self.advanced_query()
                           .where("status = ?", DownloadStatus.COMPLETED.value)
                           .where("completed_at < ?", cutoff_iso)
                           .build())
            
            old_sessions = self.execute_query(query, params)
            count = len(old_sessions)
            
            # Delete them
            for session in old_sessions:
                self.delete(session.id, soft_delete=False)  # Hard delete for cleanup
            
            return count
            
        except Exception as e:
            self._logger.error(f"Failed to cleanup completed sessions: {e}")
            raise RepositoryError(f"Cleanup completed sessions failed: {e}")
    
    def get_session_performance_stats(self) -> Dict[str, Any]:
        """Get session performance statistics"""
        try:
            stats = {}
            
            # Count by status using advanced queries
            status_counts = self.count_by_field('status')
            stats.update(status_counts)
            
            # Active sessions
            active_count = len(self.find_active_sessions())
            stats['active_sessions'] = active_count
            
            # Stalled sessions
            stalled_count = len(self.find_stalled_sessions())
            stats['stalled_sessions'] = stalled_count
            
            # Average session duration (for completed sessions)
            completed_sessions = self.find_by_status(DownloadStatus.COMPLETED)
            if completed_sessions:
                total_duration = 0
                valid_sessions = 0
                
                for session in completed_sessions:
                    duration = session.get_duration()
                    if duration is not None:
                        total_duration += duration
                        valid_sessions += 1
                
                if valid_sessions > 0:
                    stats['average_session_duration_seconds'] = total_duration / valid_sessions
            
            # Session trends
            stats['session_trends'] = self.find_trends("created_at", 7)
            
            return stats
            
        except Exception as e:
            self._logger.error(f"Failed to get session performance stats: {e}")
            raise RepositoryError(f"Get session performance stats failed: {e}")


class DownloadErrorRepository(BaseRepository[DownloadError], IDownloadErrorRepository, 
                             QueryMethodsMixin, TransactionAwareRepositoryMixin):
    """
    Download error repository implementation
    
    Manages error records and analysis for download failures.
    """
    
    def find_by_download_id(self, download_id: EntityId) -> List[DownloadError]:
        """Find errors by download ID"""
        try:
            return self.find_by_criteria({'download_id': download_id})
        except Exception as e:
            self._logger.error(f"Failed to find errors by download ID: {e}")
            raise RepositoryError(f"Find errors by download ID failed: {e}")
    
    def find_by_error_type(self, error_type: str) -> List[DownloadError]:
        """Find errors by type"""
        try:
            return self.find_by_criteria({'error_type': error_type})
        except Exception as e:
            self._logger.error(f"Failed to find errors by type: {e}")
            raise RepositoryError(f"Find errors by type failed: {e}")
    
    def find_recent_errors(self, hours: int = 24) -> List[DownloadError]:
        """Find errors from recent hours"""
        try:
            date_range = DateRange.last_hours(hours)
            return self.find_by_date_range("created_at", date_range)
            
        except Exception as e:
            self._logger.error(f"Failed to find recent errors: {e}")
            raise RepositoryError(f"Find recent errors failed: {e}")
    
    def find_retryable_errors(self) -> List[DownloadError]:
        """Find errors that can be retried"""
        try:
            return self.find_by_criteria({'can_retry': True})
        except Exception as e:
            self._logger.error(f"Failed to find retryable errors: {e}")
            raise RepositoryError(f"Find retryable errors failed: {e}")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error occurrence statistics"""
        try:
            stats = {}
            
            # Total errors
            stats['total_errors'] = self.count()
            
            # Recent errors
            stats['errors_last_24h'] = len(self.find_recent_errors(24))
            stats['errors_last_7_days'] = len(self.find_recent_errors(24 * 7))
            
            # Retryable vs non-retryable
            retryable_count = len(self.find_retryable_errors())
            stats['retryable_errors'] = retryable_count
            stats['non_retryable_errors'] = stats['total_errors'] - retryable_count
            
            # Error type distribution
            error_type_counts = self.count_by_field('error_type')
            stats['error_types'] = error_type_counts
            
            # Error trends
            stats['error_trends'] = self.find_trends("created_at", 7)
            
            return stats
            
        except Exception as e:
            self._logger.error(f"Failed to get error statistics: {e}")
            raise RepositoryError(f"Get error statistics failed: {e}")
    
    def get_most_common_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most frequently occurring errors"""
        try:
            # Group by error_type and count occurrences
            query = f"""
                SELECT error_type, COUNT(*) as count, MAX(created_at) as last_occurrence
                FROM {self.advanced_query().table_name}
                WHERE is_deleted = 0
                GROUP BY error_type
                ORDER BY count DESC
                LIMIT {limit}
            """
            
            connection = self._model._get_connection()
            try:
                cursor = connection.cursor()
                cursor.execute(query)
                rows = cursor.fetchall()
                cursor.close()
                
                # Convert to list of dictionaries
                result = []
                for row in rows:
                    result.append({
                        'error_type': row[0],
                        'count': row[1],
                        'last_occurrence': row[2]
                    })
                
                return result
                
            finally:
                self._model._return_connection(connection)
                
        except Exception as e:
            self._logger.error(f"Failed to get most common errors: {e}")
            raise RepositoryError(f"Get most common errors failed: {e}")
    
    def find_errors_by_pattern(self, pattern: str) -> List[DownloadError]:
        """Find errors matching a message pattern"""
        try:
            query, params = (self.advanced_query()
                           .where_not_deleted()
                           .where("error_message LIKE ?", f"%{pattern}%")
                           .order_by("created_at", "DESC")
                           .build())
            
            return self.execute_query(query, params)
            
        except Exception as e:
            self._logger.error(f"Failed to find errors by pattern: {e}")
            raise RepositoryError(f"Find errors by pattern failed: {e}")
    
    def cleanup_old_errors(self, older_than_days: int = 90) -> int:
        """Clean up old error records and return count removed"""
        try:
            cutoff_date = datetime.now() - timedelta(days=older_than_days)
            cutoff_iso = cutoff_date.isoformat()
            
            # Find old errors
            query, params = (self.advanced_query()
                           .where("created_at < ?", cutoff_iso)
                           .build())
            
            old_errors = self.execute_query(query, params)
            count = len(old_errors)
            
            # Delete them
            for error in old_errors:
                self.delete(error.id, soft_delete=False)  # Hard delete for cleanup
            
            return count
            
        except Exception as e:
            self._logger.error(f"Failed to cleanup old errors: {e}")
            raise RepositoryError(f"Cleanup old errors failed: {e}")


# Repository factory functions
_repository_registry = RepositoryRegistry()


def get_download_repository() -> IDownloadRepository:
    """Get download repository instance"""
    from .downloads import DownloadModelManager
    
    # Register model manager if not already registered
    if DownloadModel not in _repository_registry._model_managers:
        _repository_registry.register_model_manager(DownloadModel, DownloadModelManager())
    
    return _repository_registry.get_repository(DownloadRepository, DownloadModel)


def get_download_session_repository() -> IDownloadSessionRepository:
    """Get download session repository instance"""
    from .downloads import DownloadSessionManager
    
    # Register model manager if not already registered
    if DownloadSession not in _repository_registry._model_managers:
        _repository_registry.register_model_manager(DownloadSession, DownloadSessionManager())
    
    return _repository_registry.get_repository(DownloadSessionRepository, DownloadSession)


def get_download_error_repository() -> IDownloadErrorRepository:
    """Get download error repository instance"""
    from .downloads import DownloadErrorManager
    
    # Register model manager if not already registered
    if DownloadError not in _repository_registry._model_managers:
        _repository_registry.register_model_manager(DownloadError, DownloadErrorManager())
    
    return _repository_registry.get_repository(DownloadErrorRepository, DownloadError)


def register_download_repositories() -> None:
    """Register all download-related repositories"""
    from .downloads import DownloadModelManager, DownloadSessionManager, DownloadErrorManager
    
    _repository_registry.register_model_manager(DownloadModel, DownloadModelManager())
    _repository_registry.register_model_manager(DownloadSession, DownloadSessionManager())
    _repository_registry.register_model_manager(DownloadError, DownloadErrorManager()) 