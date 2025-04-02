import os
import logging
from typing import Dict, Type, Optional

from .platform_handler import PlatformHandler
from .platforms.tiktok_handler import TikTokHandler
from .platforms.youtube_handler import YouTubeHandler

logger = logging.getLogger(__name__)

class PlatformFactory:
    """
    Factory for creating platform handlers.
    Determines the appropriate handler based on URL.
    """
    
    _handlers: Dict[str, Type[PlatformHandler]] = {
        "TikTok": TikTokHandler,
        "YouTube": YouTubeHandler,
    }
    
    _instances: Dict[str, PlatformHandler] = {}
    
    @classmethod
    def get_handler_for_url(cls, url: str) -> Optional[PlatformHandler]:
        """
        Get the appropriate handler for the given URL.
        
        Args:
            url: URL to get handler for
            
        Returns:
            PlatformHandler if a matching handler is found, None otherwise
        """
        # First check if we've already created an instance for each platform
        if not cls._instances:
            for platform_name, handler_class in cls._handlers.items():
                cls._instances[platform_name] = handler_class()
        
        # Try to find a handler that accepts the URL
        for platform_name, handler in cls._instances.items():
            if handler.is_valid_url(url):
                logger.info(f"Using {platform_name} handler for URL: {url}")
                return handler
        
        # No matching handler found
        logger.warning(f"No handler found for URL: {url}")
        return None
    
    @classmethod
    def get_handler_by_name(cls, platform_name: str) -> Optional[PlatformHandler]:
        """
        Get a handler by platform name.
        
        Args:
            platform_name: Name of the platform (e.g. "TikTok", "YouTube")
            
        Returns:
            PlatformHandler if the platform is supported, None otherwise
        """
        # First check if we've already created an instance
        if platform_name in cls._instances:
            return cls._instances[platform_name]
        
        # If not, check if we know how to create this handler
        if platform_name in cls._handlers:
            # Create a new instance and store it
            handler = cls._handlers[platform_name]()
            cls._instances[platform_name] = handler
            return handler
        
        # Platform not supported
        logger.warning(f"Unsupported platform: {platform_name}")
        return None
    
    @classmethod
    def get_all_platforms(cls) -> Dict[str, PlatformHandler]:
        """
        Get all available platform handlers.
        
        Returns:
            Dict mapping platform names to handler instances
        """
        # Create instances for all platforms if they don't exist yet
        for platform_name, handler_class in cls._handlers.items():
            if platform_name not in cls._instances:
                cls._instances[platform_name] = handler_class()
        
        return cls._instances
    
    @classmethod
    def get_supported_platforms(cls) -> list:
        """
        Get a list of all supported platform names.
        
        Returns:
            List of platform names
        """
        return list(cls._handlers.keys())
    
    @classmethod
    def add_platform_handler(cls, platform_name: str, handler_class: Type[PlatformHandler]) -> None:
        """
        Add a new platform handler to the factory.
        
        Args:
            platform_name: Name of the platform
            handler_class: Class of the handler
        """
        cls._handlers[platform_name] = handler_class
        # Remove any existing instance to ensure a fresh one is created next time
        if platform_name in cls._instances:
            del cls._instances[platform_name]
    
    @classmethod
    def set_output_dir_for_all(cls, output_dir: str) -> None:
        """
        Set the output directory for all platform handlers.
        
        Args:
            output_dir: Output directory path
        """
        # Make sure directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Set for all existing instances
        for handler in cls._instances.values():
            handler.set_output_dir(output_dir) 