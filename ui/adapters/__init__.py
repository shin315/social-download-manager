"""
UI Adapters for Social Download Manager v2.0

Provides adapter classes for integrating different UI components
with the core application architecture.

These are placeholder/stub implementations to satisfy imports while
the full adapter system has been phased out in v2.0.
"""

from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from enum import Enum, auto
from dataclasses import dataclass


class AdapterState(Enum):
    """States for UI adapters"""
    UNINITIALIZED = auto()
    INITIALIZING = auto()
    ACTIVE = auto()
    ERROR = auto()
    SHUTDOWN = auto()


@dataclass
class AdapterConfig:
    """Configuration for UI component adapters"""
    adapter_id: str = ""
    enable_performance_monitoring: bool = True
    enable_error_recovery: bool = True
    max_retry_attempts: int = 3
    timeout_seconds: float = 5.0
    debug_mode: bool = False


@dataclass 
class AdapterMetrics:
    """Metrics for adapter performance"""
    initialization_time: float = 0.0
    success_rate: float = 1.0
    error_count: int = 0
    memory_usage: float = 0.0


class IUIComponentAdapter(ABC):
    """Interface for UI component adapters"""
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the adapter"""
        pass
        
    @abstractmethod
    def shutdown(self) -> bool:
        """Shutdown the adapter"""
        pass
    
    @abstractmethod
    def get_state(self) -> AdapterState:
        """Get current adapter state"""
        pass


class BaseAdapter(IUIComponentAdapter):
    """Base class for all UI adapters"""
    
    def __init__(self, name: str):
        self.name = name
        self.state = AdapterState.UNINITIALIZED
        self.tab_instance = None
        
    def initialize(self) -> bool:
        """Initialize the adapter"""
        try:
            self.state = AdapterState.ACTIVE
            return True
        except Exception:
            self.state = AdapterState.ERROR
            return False
            
    def shutdown(self) -> bool:
        """Shutdown the adapter"""
        self.state = AdapterState.SHUTDOWN
        return True
        
    def get_state(self) -> AdapterState:
        """Get current adapter state"""
        return self.state
        
    def set_tab_instance(self, tab):
        """Set the tab instance"""
        self.tab_instance = tab


class MainWindowAdapter(BaseAdapter):
    """Adapter for main window"""
    
    def __init__(self):
        super().__init__("main_window")


class VideoInfoTabAdapter(BaseAdapter):
    """Adapter for video info tab"""
    
    def __init__(self):
        super().__init__("video_info_tab")


class DownloadedVideosTabAdapter(BaseAdapter):
    """Adapter for downloaded videos tab"""
    
    def __init__(self):
        super().__init__("downloaded_videos_tab")


class EventBridgeCoordinator:
    """Placeholder for event bridge coordinator"""
    
    def __init__(self):
        self.initialized = False
        
    def initialize(self) -> bool:
        self.initialized = True
        return True
        
    def shutdown(self) -> bool:
        self.initialized = False
        return True


# Factory functions
def create_main_window_adapter() -> MainWindowAdapter:
    """Create main window adapter"""
    return MainWindowAdapter()


def create_video_info_tab_adapter() -> VideoInfoTabAdapter:
    """Create video info tab adapter"""
    return VideoInfoTabAdapter()


def create_downloaded_videos_tab_adapter() -> DownloadedVideosTabAdapter:
    """Create downloaded videos tab adapter"""
    return DownloadedVideosTabAdapter()


def get_global_coordinator() -> EventBridgeCoordinator:
    """Get global event bridge coordinator"""
    return EventBridgeCoordinator()


# Export main classes
__all__ = [
    'IUIComponentAdapter',
    'AdapterState', 
    'AdapterConfig',
    'AdapterMetrics',
    'BaseAdapter',
    'MainWindowAdapter',
    'VideoInfoTabAdapter', 
    'DownloadedVideosTabAdapter',
    'EventBridgeCoordinator',
    'create_main_window_adapter',
    'create_video_info_tab_adapter',
    'create_downloaded_videos_tab_adapter',
    'get_global_coordinator'
] 