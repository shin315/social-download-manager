"""
Download Management Integration for Data Integration Layer
Social Download Manager v2.0

This module integrates UI components with the DownloadRepository, providing
download progress tracking, status updates, queue management, and comprehensive
error handling using Task 19's error management system.

Leverages existing data integration patterns from Task 18 subtasks.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, Set, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
from threading import Lock
import uuid

# Core imports
try:
    from data.models.repositories import IDownloadRepository
    from data.models.content import ContentStatus as DownloadStatus, PlatformType, ContentModel
    from core.event_system import get_event_bus, EventType, Event
    
    # Task 19 Error Handling Integration
    from data.models.error_management import ErrorInfo, ErrorCategory, ErrorSeverity, ErrorContext
    from core.component_error_handlers import ComponentErrorHandler, ComponentErrorConfig
    from core.logging_strategy import get_enhanced_logger, log_error_with_context
    from core.recovery_strategies import RecoveryAction, execute_recovery_action
    
    # Task 18 Data Integration Components
    from core.data_integration.repository_event_integration import get_repository_event_manager
    from core.data_integration.async_loading_patterns import get_async_repository_manager
    from core.data_integration.repository_state_sync import get_repository_state_manager
    
    ERROR_HANDLING_AVAILABLE = True
except ImportError as e:
    ERROR_HANDLING_AVAILABLE = False
    logging.warning(f"Task 19 error handling not available: {e}")
    # Fallback imports
    from typing import Any as ErrorCategory, Any as ErrorSeverity, Any as ErrorContext
    from data.models.content import ContentStatus as DownloadStatus, PlatformType, ContentModel
    from core.event_system import get_event_bus, EventType, Event
    IDownloadRepository = None


class DownloadOperationType(Enum):
    """Download operation types"""
    SINGLE_DOWNLOAD = auto()
    BATCH_DOWNLOAD = auto()
    QUEUE_DOWNLOAD = auto()
    RESUME_DOWNLOAD = auto()
    CANCEL_DOWNLOAD = auto()
    RETRY_DOWNLOAD = auto()


class DownloadQueueState(Enum):
    """Download queue states"""
    IDLE = "idle"
    PROCESSING = "processing"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass
class DownloadProgress:
    """Download progress information"""
    download_id: str
    url: str
    title: Optional[str] = None
    platform: Optional[PlatformType] = None
    status: DownloadStatus = DownloadStatus.PENDING
    progress_percent: float = 0.0
    downloaded_bytes: int = 0
    total_bytes: Optional[int] = None
    download_speed: Optional[float] = None  # bytes/second
    eta: Optional[timedelta] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_updated: datetime = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now()


@dataclass
class DownloadQueueInfo:
    """Download queue information"""
    total_downloads: int = 0
    pending_downloads: int = 0
    active_downloads: int = 0
    completed_downloads: int = 0
    failed_downloads: int = 0
    queue_state: DownloadQueueState = DownloadQueueState.IDLE
    estimated_completion: Optional[datetime] = None
    total_progress_percent: float = 0.0


@dataclass
class DownloadOperationEvent:
    """Event data for download operations"""
    operation_type: DownloadOperationType
    download_id: Optional[str] = None
    download_ids: Optional[List[str]] = None
    progress: Optional[DownloadProgress] = None
    queue_info: Optional[DownloadQueueInfo] = None
    success: bool = True
    error_message: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class DownloadProgressTracker:
    """Tracks download progress and provides statistics"""
    
    def __init__(self):
        self.downloads: Dict[str, DownloadProgress] = {}
        self._lock = Lock()
        self.logger = logging.getLogger(__name__)
        
        # Error handling setup
        if ERROR_HANDLING_AVAILABLE:
            self.error_handler = ComponentErrorHandler(
                ComponentErrorConfig(
                    component_name="DownloadProgressTracker",
                    error_category=ErrorCategory.DOWNLOAD,
                    default_severity=ErrorSeverity.MEDIUM,
                    max_retries=3
                )
            )
            self.enhanced_logger = get_enhanced_logger("DownloadProgressTracker")
        else:
            self.error_handler = None
            self.enhanced_logger = None
    
    def add_download(self, progress: DownloadProgress) -> bool:
        """Add a download to tracking"""
        try:
            with self._lock:
                self.downloads[progress.download_id] = progress
                return True
        except Exception as e:
            if self.error_handler:
                self.error_handler.handle_error(
                    e,
                    operation="add_download",
                    context={"download_id": progress.download_id}
                )
            return False
    
    def update_progress(self, download_id: str, **updates) -> bool:
        """Update download progress"""
        try:
            with self._lock:
                if download_id not in self.downloads:
                    return False
                
                download = self.downloads[download_id]
                for key, value in updates.items():
                    if hasattr(download, key):
                        setattr(download, key, value)
                
                download.last_updated = datetime.now()
                
                # Calculate ETA if we have speed and remaining bytes
                if (download.download_speed and download.download_speed > 0 and 
                    download.total_bytes and download.downloaded_bytes < download.total_bytes):
                    remaining_bytes = download.total_bytes - download.downloaded_bytes
                    eta_seconds = remaining_bytes / download.download_speed
                    download.eta = timedelta(seconds=eta_seconds)
                
                return True
        except Exception as e:
            if self.error_handler:
                self.error_handler.handle_error(
                    e,
                    operation="update_progress",
                    context={"download_id": download_id}
                )
            return False
    
    def get_progress(self, download_id: str) -> Optional[DownloadProgress]:
        """Get progress for a specific download"""
        with self._lock:
            return self.downloads.get(download_id)
    
    def get_all_progress(self) -> Dict[str, DownloadProgress]:
        """Get all download progress"""
        with self._lock:
            return self.downloads.copy()
    
    def remove_download(self, download_id: str) -> bool:
        """Remove download from tracking"""
        try:
            with self._lock:
                return self.downloads.pop(download_id, None) is not None
        except Exception as e:
            self.logger.error(f"Error removing download {download_id}: {e}")
            return False
    
    def get_queue_info(self) -> DownloadQueueInfo:
        """Get overall queue information"""
        try:
            with self._lock:
                total = len(self.downloads)
                if total == 0:
                    return DownloadQueueInfo()
                
                pending = sum(1 for d in self.downloads.values() if d.status == DownloadStatus.PENDING)
                active = sum(1 for d in self.downloads.values() if d.status == DownloadStatus.DOWNLOADING)
                completed = sum(1 for d in self.downloads.values() if d.status == DownloadStatus.COMPLETED)
                failed = sum(1 for d in self.downloads.values() if d.status == DownloadStatus.FAILED)
                
                # Calculate total progress
                total_progress = 0.0
                if total > 0:
                    total_progress = sum(d.progress_percent for d in self.downloads.values()) / total
                
                # Determine queue state
                if active > 0:
                    queue_state = DownloadQueueState.PROCESSING
                elif pending > 0:
                    queue_state = DownloadQueueState.IDLE
                elif failed > 0 and completed == 0:
                    queue_state = DownloadQueueState.ERROR
                else:
                    queue_state = DownloadQueueState.COMPLETED
                
                return DownloadQueueInfo(
                    total_downloads=total,
                    pending_downloads=pending,
                    active_downloads=active,
                    completed_downloads=completed,
                    failed_downloads=failed,
                    queue_state=queue_state,
                    total_progress_percent=total_progress
                )
        except Exception as e:
            if self.error_handler:
                self.error_handler.handle_error(e, operation="get_queue_info")
            return DownloadQueueInfo()


class DownloadUIStateManager:
    """Manages UI state for download operations"""
    
    def __init__(self, download_repo: Optional[Any] = None):
        self.download_repo = download_repo
        self.logger = logging.getLogger(__name__)
        
        # Progress tracking
        self.progress_tracker = DownloadProgressTracker()
        
        # State management
        self.ui_callbacks: Dict[str, List[Callable]] = {
            'progress_update': [],
            'status_change': [],
            'queue_update': [],
            'error': []
        }
        
        # Event system integration
        self.event_bus = get_event_bus()
        
        # Error handling setup
        if ERROR_HANDLING_AVAILABLE:
            self.error_handler = ComponentErrorHandler(
                ComponentErrorConfig(
                    component_name="DownloadUIStateManager",
                    error_category=ErrorCategory.UI,
                    default_severity=ErrorSeverity.MEDIUM,
                    max_retries=2
                )
            )
        else:
            self.error_handler = None
        
        # Setup event subscriptions
        self._setup_event_subscriptions()
    
    def _setup_event_subscriptions(self):
        """Setup event subscriptions for download events"""
        self.event_bus.subscribe(EventType.DOWNLOAD_STARTED, self._handle_download_started)
        self.event_bus.subscribe(EventType.DOWNLOAD_PROGRESS, self._handle_download_progress)
        self.event_bus.subscribe(EventType.DOWNLOAD_COMPLETED, self._handle_download_completed)
        self.event_bus.subscribe(EventType.DOWNLOAD_FAILED, self._handle_download_failed)
        self.event_bus.subscribe(EventType.DOWNLOAD_CANCELLED, self._handle_download_cancelled)
    
    def register_callback(self, event_type: str, callback: Callable):
        """Register UI callback for download events"""
        if event_type in self.ui_callbacks:
            self.ui_callbacks[event_type].append(callback)
    
    def unregister_callback(self, event_type: str, callback: Callable):
        """Unregister UI callback"""
        if event_type in self.ui_callbacks:
            try:
                self.ui_callbacks[event_type].remove(callback)
            except ValueError:
                pass
    
    def _notify_callbacks(self, event_type: str, *args, **kwargs):
        """Notify registered callbacks"""
        for callback in self.ui_callbacks.get(event_type, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                self.logger.error(f"Error in {event_type} callback: {e}")
    
    async def start_download(self, content: ContentModel) -> str:
        """Start a download and return download ID"""
        try:
            download_id = str(uuid.uuid4())
            
            # Create progress entry
            progress = DownloadProgress(
                download_id=download_id,
                url=content.url,
                title=content.title,
                platform=content.platform,
                status=DownloadStatus.PENDING,
                started_at=datetime.now()
            )
            
            self.progress_tracker.add_download(progress)
            
            # Emit event
            self.event_bus.publish(Event(
                event_type=EventType.DOWNLOAD_STARTED,
                source="DownloadUIStateManager",
                data={
                    "download_id": download_id,
                    "content": asdict(content),
                    "progress": asdict(progress)
                }
            ))
            
            return download_id
            
        except Exception as e:
            if self.error_handler:
                self.error_handler.handle_error(
                    e,
                    operation="start_download",
                    context={"content_url": content.url}
                )
            raise
    
    async def batch_start_downloads(self, contents: List[ContentModel]) -> List[str]:
        """Start multiple downloads"""
        download_ids = []
        
        try:
            for content in contents:
                download_id = await self.start_download(content)
                download_ids.append(download_id)
            
            # Emit batch event
            operation_event = DownloadOperationEvent(
                operation_type=DownloadOperationType.BATCH_DOWNLOAD,
                download_ids=download_ids,
                queue_info=self.progress_tracker.get_queue_info()
            )
            
            self._notify_callbacks('queue_update', operation_event)
            
            return download_ids
            
        except Exception as e:
            if self.error_handler:
                self.error_handler.handle_error(e, operation="batch_start_downloads")
            raise
    
    def cancel_download(self, download_id: str) -> bool:
        """Cancel a download"""
        try:
            progress = self.progress_tracker.get_progress(download_id)
            if not progress:
                return False
            
            # Update status
            self.progress_tracker.update_progress(
                download_id,
                status=DownloadStatus.CANCELLED
            )
            
            # Emit event
            self.event_bus.publish(Event(
                event_type=EventType.DOWNLOAD_CANCELLED,
                source="DownloadUIStateManager",
                data={
                    "download_id": download_id,
                    "progress": asdict(progress)
                }
            ))
            
            return True
            
        except Exception as e:
            if self.error_handler:
                self.error_handler.handle_error(
                    e,
                    operation="cancel_download",
                    context={"download_id": download_id}
                )
            return False
    
    def retry_download(self, download_id: str) -> bool:
        """Retry a failed download"""
        try:
            progress = self.progress_tracker.get_progress(download_id)
            if not progress or progress.status != DownloadStatus.FAILED:
                return False
            
            # Reset progress
            self.progress_tracker.update_progress(
                download_id,
                status=DownloadStatus.PENDING,
                progress_percent=0.0,
                downloaded_bytes=0,
                error_message=None,
                started_at=datetime.now()
            )
            
            # Create operation event
            operation_event = DownloadOperationEvent(
                operation_type=DownloadOperationType.RETRY_DOWNLOAD,
                download_id=download_id,
                progress=progress
            )
            
            self._notify_callbacks('status_change', operation_event)
            
            return True
            
        except Exception as e:
            if self.error_handler:
                self.error_handler.handle_error(
                    e,
                    operation="retry_download",
                    context={"download_id": download_id}
                )
            return False
    
    def get_download_progress(self, download_id: str) -> Optional[DownloadProgress]:
        """Get progress for specific download"""
        return self.progress_tracker.get_progress(download_id)
    
    def get_all_downloads(self) -> Dict[str, DownloadProgress]:
        """Get all download progress"""
        return self.progress_tracker.get_all_progress()
    
    def get_queue_info(self) -> DownloadQueueInfo:
        """Get queue information"""
        return self.progress_tracker.get_queue_info()
    
    # Event handlers
    def _handle_download_started(self, event: Event):
        """Handle download started event"""
        try:
            download_id = event.data.get('download_id')
            if download_id:
                self.progress_tracker.update_progress(
                    download_id,
                    status=DownloadStatus.DOWNLOADING
                )
                
                progress = self.progress_tracker.get_progress(download_id)
                if progress:
                    operation_event = DownloadOperationEvent(
                        operation_type=DownloadOperationType.SINGLE_DOWNLOAD,
                        download_id=download_id,
                        progress=progress
                    )
                    self._notify_callbacks('status_change', operation_event)
        except Exception as e:
            self.logger.error(f"Error handling download started: {e}")
    
    def _handle_download_progress(self, event: Event):
        """Handle download progress event"""
        try:
            download_id = event.data.get('download_id')
            progress_percent = event.data.get('progress_percent', 0.0)
            downloaded_bytes = event.data.get('downloaded_bytes', 0)
            total_bytes = event.data.get('total_bytes')
            download_speed = event.data.get('download_speed')
            
            if download_id:
                self.progress_tracker.update_progress(
                    download_id,
                    progress_percent=progress_percent,
                    downloaded_bytes=downloaded_bytes,
                    total_bytes=total_bytes,
                    download_speed=download_speed
                )
                
                progress = self.progress_tracker.get_progress(download_id)
                if progress:
                    self._notify_callbacks('progress_update', progress)
        except Exception as e:
            self.logger.error(f"Error handling download progress: {e}")
    
    def _handle_download_completed(self, event: Event):
        """Handle download completed event"""
        try:
            download_id = event.data.get('download_id')
            if download_id:
                self.progress_tracker.update_progress(
                    download_id,
                    status=DownloadStatus.COMPLETED,
                    progress_percent=100.0,
                    completed_at=datetime.now()
                )
                
                progress = self.progress_tracker.get_progress(download_id)
                if progress:
                    operation_event = DownloadOperationEvent(
                        operation_type=DownloadOperationType.SINGLE_DOWNLOAD,
                        download_id=download_id,
                        progress=progress,
                        queue_info=self.progress_tracker.get_queue_info()
                    )
                    self._notify_callbacks('status_change', operation_event)
                    self._notify_callbacks('queue_update', operation_event)
        except Exception as e:
            self.logger.error(f"Error handling download completed: {e}")
    
    def _handle_download_failed(self, event: Event):
        """Handle download failed event"""
        try:
            download_id = event.data.get('download_id')
            error_message = event.data.get('error_message', 'Unknown error')
            
            if download_id:
                self.progress_tracker.update_progress(
                    download_id,
                    status=DownloadStatus.FAILED,
                    error_message=error_message
                )
                
                progress = self.progress_tracker.get_progress(download_id)
                if progress:
                    operation_event = DownloadOperationEvent(
                        operation_type=DownloadOperationType.SINGLE_DOWNLOAD,
                        download_id=download_id,
                        progress=progress,
                        success=False,
                        error_message=error_message
                    )
                    self._notify_callbacks('error', operation_event)
                    self._notify_callbacks('status_change', operation_event)
        except Exception as e:
            self.logger.error(f"Error handling download failed: {e}")
    
    def _handle_download_cancelled(self, event: Event):
        """Handle download cancelled event"""
        try:
            download_id = event.data.get('download_id')
            if download_id:
                progress = self.progress_tracker.get_progress(download_id)
                if progress:
                    operation_event = DownloadOperationEvent(
                        operation_type=DownloadOperationType.CANCEL_DOWNLOAD,
                        download_id=download_id,
                        progress=progress
                    )
                    self._notify_callbacks('status_change', operation_event)
        except Exception as e:
            self.logger.error(f"Error handling download cancelled: {e}")


class DownloadManagementIntegrator:
    """
    Main integrator for download management with UI components
    Coordinates between DownloadRepository, UI state, and event systems
    """
    
    def __init__(self, download_repo: Optional[Any] = None):
        self.download_repo = download_repo
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.ui_state_manager = DownloadUIStateManager(download_repo)
        
        # Integration with Task 18 components
        try:
            self.event_manager = get_repository_event_manager()
            self.async_manager = get_async_repository_manager()
            self.state_sync = get_repository_state_manager()
        except Exception as e:
            self.logger.warning(f"Task 18 components not available: {e}")
            self.event_manager = None
            self.async_manager = None
            self.state_sync = None
        
        # Error handling setup
        if ERROR_HANDLING_AVAILABLE:
            self.error_handler = ComponentErrorHandler(
                ComponentErrorConfig(
                    component_name="DownloadManagementIntegrator",
                    error_category=ErrorCategory.INTEGRATION,
                    default_severity=ErrorSeverity.HIGH,
                    max_retries=2
                )
            )
        else:
            self.error_handler = None
    
    async def start_single_download(self, content: ContentModel) -> str:
        """Start a single download"""
        try:
            if ERROR_HANDLING_AVAILABLE:
                self.enhanced_logger = get_enhanced_logger("DownloadManagementIntegrator")
                log_error_with_context(
                    "DownloadManagementIntegrator",
                    ErrorInfo(
                        error_id=f"download_start_{content.id}",
                        error_code="DOWNLOAD_START",
                        message=f"Starting download for {content.title}",
                        category=ErrorCategory.DOWNLOAD,
                        severity=ErrorSeverity.LOW,
                        context=ErrorContext(operation="start_single_download")
                    ),
                    {"content_id": content.id, "platform": content.platform.value}
                )
            
            download_id = await self.ui_state_manager.start_download(content)
            
            # Integrate with async manager if available
            if self.async_manager:
                await self.async_manager.execute_async_operation(
                    operation_id=f"download_{download_id}",
                    operation=lambda: self._perform_download(content, download_id),
                    operation_type="download",
                    timeout=timedelta(hours=2)
                )
            
            return download_id
            
        except Exception as e:
            if self.error_handler:
                self.error_handler.handle_error(
                    e,
                    operation="start_single_download",
                    context={"content_id": content.id}
                )
            raise
    
    async def start_batch_downloads(self, contents: List[ContentModel]) -> List[str]:
        """Start multiple downloads"""
        try:
            download_ids = await self.ui_state_manager.batch_start_downloads(contents)
            
            # Schedule downloads with async manager if available
            if self.async_manager:
                for i, (content, download_id) in enumerate(zip(contents, download_ids)):
                    await self.async_manager.execute_async_operation(
                        operation_id=f"batch_download_{i}_{download_id}",
                        operation=lambda c=content, d_id=download_id: self._perform_download(c, d_id),
                        operation_type="batch_download",
                        timeout=timedelta(hours=2),
                        priority=1  # Lower priority for batch
                    )
            
            return download_ids
            
        except Exception as e:
            if self.error_handler:
                self.error_handler.handle_error(e, operation="start_batch_downloads")
            raise
    
    async def _perform_download(self, content: ContentModel, download_id: str):
        """Perform the actual download (mock implementation)"""
        try:
            # This would integrate with the actual download system
            # For now, simulate download progress
            import time
            
            for progress in [10, 25, 50, 75, 90, 100]:
                # Simulate download progress
                self.ui_state_manager.progress_tracker.update_progress(
                    download_id,
                    progress_percent=progress,
                    downloaded_bytes=progress * 1024 * 1024,  # Simulate MB
                    total_bytes=100 * 1024 * 1024,  # 100MB total
                    download_speed=1024 * 1024  # 1MB/s
                )
                
                # Publish progress event
                self.ui_state_manager.event_bus.publish(Event(
                    event_type=EventType.DOWNLOAD_PROGRESS,
                    source="DownloadManagementIntegrator",
                    data={
                        "download_id": download_id,
                        "progress_percent": progress,
                        "downloaded_bytes": progress * 1024 * 1024,
                        "total_bytes": 100 * 1024 * 1024,
                        "download_speed": 1024 * 1024
                    }
                ))
                
                await asyncio.sleep(0.1)  # Simulate time
            
            # Complete download
            self.ui_state_manager.event_bus.publish(Event(
                event_type=EventType.DOWNLOAD_COMPLETED,
                source="DownloadManagementIntegrator",
                data={"download_id": download_id}
            ))
            
        except Exception as e:
            # Handle download failure
            self.ui_state_manager.event_bus.publish(Event(
                event_type=EventType.DOWNLOAD_FAILED,
                source="DownloadManagementIntegrator",
                data={
                    "download_id": download_id,
                    "error_message": str(e)
                }
            ))
            raise
    
    def cancel_download(self, download_id: str) -> bool:
        """Cancel a download"""
        return self.ui_state_manager.cancel_download(download_id)
    
    def retry_download(self, download_id: str) -> bool:
        """Retry a failed download"""
        return self.ui_state_manager.retry_download(download_id)
    
    def get_download_progress(self, download_id: str) -> Optional[DownloadProgress]:
        """Get progress for a specific download"""
        return self.ui_state_manager.get_download_progress(download_id)
    
    def get_all_downloads(self) -> Dict[str, DownloadProgress]:
        """Get all downloads"""
        return self.ui_state_manager.get_all_downloads()
    
    def get_queue_info(self) -> DownloadQueueInfo:
        """Get queue information"""
        return self.ui_state_manager.get_queue_info()
    
    def register_ui_callback(self, event_type: str, callback: Callable):
        """Register UI callback"""
        self.ui_state_manager.register_callback(event_type, callback)
    
    def unregister_ui_callback(self, event_type: str, callback: Callable):
        """Unregister UI callback"""
        self.ui_state_manager.unregister_callback(event_type, callback)


# Global instance management
_download_management_integrator: Optional[DownloadManagementIntegrator] = None


def get_download_management_integrator(
    download_repo: Optional[Any] = None
) -> DownloadManagementIntegrator:
    """
    Get or create the global DownloadManagementIntegrator instance
    
    Args:
        download_repo: Download repository instance
        
    Returns:
        DownloadManagementIntegrator instance
    """
    global _download_management_integrator
    
    if _download_management_integrator is None:
        _download_management_integrator = DownloadManagementIntegrator(download_repo)
    
    return _download_management_integrator


def reset_download_management_integrator():
    """Reset the global download management integrator (for testing)"""
    global _download_management_integrator
    _download_management_integrator = None 