"""
UI Adapters for Social Download Manager v2.0

Provides adapter classes for integrating different UI components
with the core application architecture.
"""

from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod


class BaseAdapter(ABC):
    """Base class for all UI adapters"""
    
    def __init__(self, name: str):
        self.name = name
        self.initialized = False
        
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the adapter"""
        pass
        
    @abstractmethod
    def shutdown(self) -> bool:
        """Shutdown the adapter"""
        pass


class VideoInfoAdapter(BaseAdapter):
    """Adapter for video info tab"""
    
    def __init__(self):
        super().__init__("video_info")
        self.tab_instance = None
        
    def initialize(self) -> bool:
        """Initialize video info adapter"""
        try:
            self.initialized = True
            return True
        except Exception:
            return False
            
    def shutdown(self) -> bool:
        """Shutdown video info adapter"""
        self.initialized = False
        return True
        
    def set_tab_instance(self, tab):
        """Set the tab instance"""
        self.tab_instance = tab


class DownloadedVideosAdapter(BaseAdapter):
    """Adapter for downloaded videos tab"""
    
    def __init__(self):
        super().__init__("downloaded_videos")
        self.tab_instance = None
        
    def initialize(self) -> bool:
        """Initialize downloaded videos adapter"""
        try:
            self.initialized = True
            return True
        except Exception:
            return False
            
    def shutdown(self) -> bool:
        """Shutdown downloaded videos adapter"""
        self.initialized = False
        return True
        
    def set_tab_instance(self, tab):
        """Set the tab instance"""
        self.tab_instance = tab


class AdapterFactory:
    """Factory for creating adapters"""
    
    @staticmethod
    def create_adapters() -> Dict[str, BaseAdapter]:
        """Create all available adapters"""
        return {
            "video_info": VideoInfoAdapter(),
            "downloaded_videos": DownloadedVideosAdapter()
        }


# Export main classes
__all__ = [
    'BaseAdapter',
    'VideoInfoAdapter', 
    'DownloadedVideosAdapter',
    'AdapterFactory'
] 