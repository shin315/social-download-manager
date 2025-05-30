"""
Platform Selector Integration for Data Integration Layer
Social Download Manager v2.0

This module integrates the PlatformSelector component with repository data,
providing platform-specific data querying and state management.

Leverages Task 19 error handling system for robust error management.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, Set, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

# Core imports
try:
    from data.models.repositories import IContentRepository
    from data.models.content import PlatformType, ContentModel
    from core.event_system import get_event_bus, EventType, Event
    
    # Try to import IDownloadRepository but make it optional
    try:
        from data.models.repositories import IDownloadRepository
    except ImportError:
        IDownloadRepository = None
    
    # Task 19 Error Handling Integration
    from data.models.error_management import ErrorInfo, ErrorCategory, ErrorSeverity, ErrorContext
    from core.component_error_handlers import ComponentErrorHandler, ComponentErrorConfig
    from core.logging_strategy import get_enhanced_logger, log_error_with_context
    from core.recovery_strategies import RecoveryAction, execute_recovery_action
    
    ERROR_HANDLING_AVAILABLE = True
except ImportError as e:
    ERROR_HANDLING_AVAILABLE = False
    logging.warning(f"Task 19 error handling not available: {e}")
    # Fallback imports
    from typing import Any as ErrorCategory, Any as ErrorSeverity, Any as ErrorContext
    from data.models.content import PlatformType, ContentModel
    from data.models.repositories import IContentRepository
    IDownloadRepository = None


class PlatformState(Enum):
    """Platform selection states"""
    UNSELECTED = "unselected"
    SELECTED = "selected"  
    LOADING = "loading"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class PlatformData:
    """Platform information and statistics"""
    platform_type: PlatformType
    total_content: int = 0
    downloaded_content: int = 0
    failed_downloads: int = 0
    last_updated: Optional[datetime] = None
    is_available: bool = True
    error_message: Optional[str] = None
    state: PlatformState = PlatformState.UNSELECTED


@dataclass
class PlatformSelectionEvent:
    """Event data for platform selection changes"""
    platform: PlatformType
    selected: bool
    previous_selection: Optional[PlatformType]
    data: Optional[PlatformData]
    timestamp: datetime


class PlatformDataAdapter:
    """Adapter for retrieving platform-specific data from repositories"""
    
    def __init__(self, content_repo: IContentRepository, download_repo: Optional[Any] = None):
        self.content_repo = content_repo
        self.download_repo = download_repo
        self.logger = logging.getLogger(__name__)
        
        # Error handling setup
        if ERROR_HANDLING_AVAILABLE:
            self.error_handler = ComponentErrorHandler(
                ComponentErrorConfig(
                    component_name="PlatformDataAdapter",
                    error_category=ErrorCategory.REPOSITORY,
                    default_severity=ErrorSeverity.MEDIUM,
                    max_retries=3
                )
            )
            self.enhanced_logger = get_enhanced_logger("PlatformDataAdapter")
        else:
            self.error_handler = None
            self.enhanced_logger = None
    
    async def get_platform_data(self, platform: PlatformType) -> PlatformData:
        """
        Get comprehensive data for a specific platform
        
        Args:
            platform: Platform type to get data for
            
        Returns:
            PlatformData with current statistics and status
        """
        try:
            # Get basic content counts
            total_content = await self._get_total_content_count(platform)
            downloaded_content = await self._get_downloaded_content_count(platform)
            failed_downloads = await self._get_failed_downloads_count(platform)
            
            platform_data = PlatformData(
                platform_type=platform,
                total_content=total_content,
                downloaded_content=downloaded_content,
                failed_downloads=failed_downloads,
                last_updated=datetime.now(),
                is_available=True,
                state=PlatformState.SELECTED
            )
            
            return platform_data
            
        except Exception as e:
            if self.error_handler:
                handled = self.error_handler.handle_error(
                    e, 
                    operation="get_platform_data",
                    context={"platform": platform.value}
                )
                if not handled:
                    raise
            
            # Return error state
            return PlatformData(
                platform_type=platform,
                is_available=False,
                error_message=str(e),
                state=PlatformState.ERROR
            )
    
    async def _get_total_content_count(self, platform: PlatformType) -> int:
        """Get total content count for platform"""
        try:
            content_list = self.content_repo.find_by_platform(platform)
            return len(content_list) if content_list else 0
        except Exception as e:
            if self.enhanced_logger:
                log_error_with_context(
                    "PlatformDataAdapter",
                    ErrorInfo(
                        error_id=f"platform_count_{platform.value}",
                        error_code="PLATFORM_COUNT_ERROR",
                        message=f"Failed to get content count for {platform.value}",
                        category=ErrorCategory.REPOSITORY,
                        severity=ErrorSeverity.LOW,
                        context=ErrorContext(operation="get_total_content_count")
                    ),
                    {"platform": platform.value}
                )
            raise
    
    async def _get_downloaded_content_count(self, platform: PlatformType) -> int:
        """Get downloaded content count for platform"""
        try:
            from data.models.content import ContentStatus
            downloaded = self.content_repo.find_by_status(ContentStatus.COMPLETED)
            platform_downloaded = [c for c in downloaded if c.platform == platform]
            return len(platform_downloaded)
        except Exception as e:
            self.logger.warning(f"Failed to get downloaded count for {platform.value}: {e}")
            return 0
    
    async def _get_failed_downloads_count(self, platform: PlatformType) -> int:
        """Get failed downloads count for platform"""
        try:
            from data.models.content import ContentStatus
            failed = self.content_repo.find_by_status(ContentStatus.FAILED)
            platform_failed = [c for c in failed if c.platform == platform]
            return len(platform_failed)
        except Exception as e:
            self.logger.warning(f"Failed to get failed count for {platform.value}: {e}")
            return 0


class PlatformSelectorManager:
    """
    Manages PlatformSelector component integration with repository data
    Provides state management, event handling, and data synchronization
    """
    
    def __init__(self, content_repo: IContentRepository, download_repo: Optional[Any] = None):
        self.content_repo = content_repo
        self.download_repo = download_repo
        self.logger = logging.getLogger(__name__)
        
        # Data adapter
        self.data_adapter = PlatformDataAdapter(content_repo, download_repo)
        
        # State management
        self.platform_data: Dict[PlatformType, PlatformData] = {}
        self.selected_platforms: Set[PlatformType] = set()
        self.current_platform: Optional[PlatformType] = None
        
        # Event system
        self.event_bus = get_event_bus()
        self.selection_callbacks: List[Callable[[PlatformSelectionEvent], None]] = []
        
        # Error handling setup
        if ERROR_HANDLING_AVAILABLE:
            self.error_handler = ComponentErrorHandler(
                ComponentErrorConfig(
                    component_name="PlatformSelectorManager",
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
        """Setup event subscriptions for data changes"""
        self.event_bus.subscribe(EventType.DATA_UPDATED, self._handle_data_updated)
        self.event_bus.subscribe(EventType.DOWNLOAD_COMPLETED, self._handle_download_completed)
        self.event_bus.subscribe(EventType.DOWNLOAD_FAILED, self._handle_download_failed)
    
    async def initialize_platforms(self) -> Dict[PlatformType, PlatformData]:
        """
        Initialize platform data for all supported platforms
        
        Returns:
            Dictionary mapping platforms to their data
        """
        try:
            supported_platforms = [PlatformType.YOUTUBE, PlatformType.TIKTOK]
            tasks = []
            
            for platform in supported_platforms:
                task = self.data_adapter.get_platform_data(platform)
                tasks.append(task)
            
            # Execute all platform data requests concurrently
            platform_data_list = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(platform_data_list):
                platform = supported_platforms[i]
                
                if isinstance(result, Exception):
                    if self.error_handler:
                        self.error_handler.handle_error(
                            result,
                            operation="initialize_platforms",
                            context={"platform": platform.value}
                        )
                    
                    # Create error state
                    self.platform_data[platform] = PlatformData(
                        platform_type=platform,
                        is_available=False,
                        error_message=str(result),
                        state=PlatformState.ERROR
                    )
                else:
                    self.platform_data[platform] = result
            
            return self.platform_data
            
        except Exception as e:
            if self.error_handler:
                self.error_handler.handle_error(e, operation="initialize_platforms")
            raise
    
    def select_platform(self, platform: PlatformType) -> bool:
        """
        Select a platform and trigger appropriate repository queries
        
        Args:
            platform: Platform to select
            
        Returns:
            bool: True if selection was successful
        """
        try:
            # Validate platform availability
            platform_data = self.platform_data.get(platform)
            if not platform_data or not platform_data.is_available:
                if self.enhanced_logger:
                    log_error_with_context(
                        "PlatformSelectorManager",
                        ErrorInfo(
                            error_id=f"platform_unavailable_{platform.value}",
                            error_code="PLATFORM_UNAVAILABLE",
                            message=f"Platform {platform.value} is not available",
                            category=ErrorCategory.UI,
                            severity=ErrorSeverity.LOW,
                            context=ErrorContext(operation="select_platform")
                        ),
                        {"platform": platform.value}
                    )
                return False
            
            # Store previous selection
            previous_platform = self.current_platform
            
            # Update state
            self.current_platform = platform
            self.selected_platforms.add(platform)
            
            # Update platform state
            platform_data.state = PlatformState.SELECTED
            
            # Create selection event
            selection_event = PlatformSelectionEvent(
                platform=platform,
                selected=True,
                previous_selection=previous_platform,
                data=platform_data,
                timestamp=datetime.now()
            )
            
            # Notify callbacks
            self._notify_selection_callbacks(selection_event)
            
            # Emit event
            self.event_bus.publish(Event(
                event_type=EventType.UI_UPDATE_REQUIRED,
                source="PlatformSelectorManager",
                data={
                    "action": "platform_selected",
                    "platform": platform.value,
                    "selection_event": asdict(selection_event)
                }
            ))
            
            return True
            
        except Exception as e:
            if self.error_handler:
                self.error_handler.handle_error(
                    e,
                    operation="select_platform",
                    context={"platform": platform.value}
                )
            return False
    
    def deselect_platform(self, platform: PlatformType) -> bool:
        """
        Deselect a platform
        
        Args:
            platform: Platform to deselect
            
        Returns:
            bool: True if deselection was successful
        """
        try:
            if platform not in self.selected_platforms:
                return False
            
            # Update state
            self.selected_platforms.discard(platform)
            if self.current_platform == platform:
                # Select another platform if available
                self.current_platform = next(iter(self.selected_platforms), None)
            
            # Update platform state
            if platform in self.platform_data:
                self.platform_data[platform].state = PlatformState.UNSELECTED
            
            # Create selection event
            selection_event = PlatformSelectionEvent(
                platform=platform,
                selected=False,
                previous_selection=platform,
                data=self.platform_data.get(platform),
                timestamp=datetime.now()
            )
            
            # Notify callbacks
            self._notify_selection_callbacks(selection_event)
            
            # Emit event
            self.event_bus.publish(Event(
                event_type=EventType.UI_UPDATE_REQUIRED,
                source="PlatformSelectorManager",
                data={
                    "action": "platform_deselected",
                    "platform": platform.value,
                    "selection_event": asdict(selection_event)
                }
            ))
            
            return True
            
        except Exception as e:
            if self.error_handler:
                self.error_handler.handle_error(
                    e,
                    operation="deselect_platform",
                    context={"platform": platform.value}
                )
            return False
    
    def add_selection_callback(self, callback: Callable[[PlatformSelectionEvent], None]):
        """Add callback for platform selection events"""
        self.selection_callbacks.append(callback)
    
    def remove_selection_callback(self, callback: Callable[[PlatformSelectionEvent], None]):
        """Remove callback for platform selection events"""
        try:
            self.selection_callbacks.remove(callback)
        except ValueError:
            pass
    
    def _notify_selection_callbacks(self, event: PlatformSelectionEvent):
        """Notify all selection callbacks"""
        for callback in self.selection_callbacks:
            try:
                callback(event)
            except Exception as e:
                self.logger.error(f"Error in selection callback: {e}")
    
    async def refresh_platform_data(self, platform: Optional[PlatformType] = None) -> bool:
        """
        Refresh platform data from repositories
        
        Args:
            platform: Specific platform to refresh, or None for all
            
        Returns:
            bool: True if refresh was successful
        """
        try:
            if platform:
                platforms_to_refresh = [platform]
            else:
                platforms_to_refresh = list(self.platform_data.keys())
            
            for p in platforms_to_refresh:
                try:
                    # Set loading state
                    if p in self.platform_data:
                        self.platform_data[p].state = PlatformState.LOADING
                    
                    # Get fresh data
                    fresh_data = await self.data_adapter.get_platform_data(p)
                    self.platform_data[p] = fresh_data
                    
                except Exception as e:
                    if self.error_handler:
                        self.error_handler.handle_error(
                            e,
                            operation="refresh_platform_data",
                            context={"platform": p.value}
                        )
                    
                    # Set error state
                    if p in self.platform_data:
                        self.platform_data[p].state = PlatformState.ERROR
                        self.platform_data[p].error_message = str(e)
            
            return True
            
        except Exception as e:
            if self.error_handler:
                self.error_handler.handle_error(e, operation="refresh_platform_data")
            return False
    
    def get_platform_data(self, platform: PlatformType) -> Optional[PlatformData]:
        """Get data for a specific platform"""
        return self.platform_data.get(platform)
    
    def get_all_platform_data(self) -> Dict[PlatformType, PlatformData]:
        """Get data for all platforms"""
        return self.platform_data.copy()
    
    def get_selected_platforms(self) -> Set[PlatformType]:
        """Get currently selected platforms"""
        return self.selected_platforms.copy()
    
    def get_current_platform(self) -> Optional[PlatformType]:
        """Get currently active platform"""
        return self.current_platform
    
    # Event handlers
    def _handle_data_updated(self, event: Event):
        """Handle data update events"""
        try:
            # Check if this affects any platforms
            if 'platform' in event.data:
                platform_str = event.data['platform']
                try:
                    platform = PlatformType(platform_str)
                    # Refresh platform data asynchronously
                    asyncio.create_task(self.refresh_platform_data(platform))
                except ValueError:
                    pass
        except Exception as e:
            self.logger.error(f"Error handling data update event: {e}")
    
    def _handle_download_completed(self, event: Event):
        """Handle download completion events"""
        try:
            if 'platform' in event.data:
                platform_str = event.data['platform']
                try:
                    platform = PlatformType(platform_str)
                    # Update downloaded count
                    if platform in self.platform_data:
                        self.platform_data[platform].downloaded_content += 1
                        self.platform_data[platform].last_updated = datetime.now()
                except ValueError:
                    pass
        except Exception as e:
            self.logger.error(f"Error handling download completed event: {e}")
    
    def _handle_download_failed(self, event: Event):
        """Handle download failure events"""
        try:
            if 'platform' in event.data:
                platform_str = event.data['platform']
                try:
                    platform = PlatformType(platform_str)
                    # Update failed count
                    if platform in self.platform_data:
                        self.platform_data[platform].failed_downloads += 1
                        self.platform_data[platform].last_updated = datetime.now()
                except ValueError:
                    pass
        except Exception as e:
            self.logger.error(f"Error handling download failed event: {e}")


# Global instance management
_platform_selector_manager: Optional[PlatformSelectorManager] = None


def get_platform_selector_manager(
    content_repo: Optional[IContentRepository] = None,
    download_repo: Optional[Any] = None
) -> PlatformSelectorManager:
    """
    Get or create the global PlatformSelectorManager instance
    
    Args:
        content_repo: Content repository instance
        download_repo: Download repository instance
        
    Returns:
        PlatformSelectorManager instance
    """
    global _platform_selector_manager
    
    if _platform_selector_manager is None:
        if content_repo is None:
            raise ValueError("Content repository must be provided for initialization")
        
        _platform_selector_manager = PlatformSelectorManager(content_repo, download_repo)
    
    return _platform_selector_manager


def reset_platform_selector_manager():
    """Reset the global platform selector manager (for testing)"""
    global _platform_selector_manager
    _platform_selector_manager = None 