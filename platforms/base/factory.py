"""
Platform factory for automatic platform detection and handler instantiation

This module implements the factory pattern to automatically detect platform types
from URLs and create appropriate platform handlers.
"""

import logging
from typing import Dict, Type, Optional, Any, List, Callable
from urllib.parse import urlparse

from .platform_handler import AbstractPlatformHandler
from .models import AuthenticationInfo, PlatformCapabilities
from .enums import PlatformType

logger = logging.getLogger(__name__)


class PlatformRegistry:
    """Registry for platform handlers"""
    
    def __init__(self):
        self._handlers: Dict[PlatformType, Type[AbstractPlatformHandler]] = {}
        self._url_patterns: Dict[PlatformType, List[str]] = {}
        self._detection_callbacks: Dict[PlatformType, Callable[[str], bool]] = {}
    
    def register(
        self,
        platform_type: PlatformType,
        handler_class: Type[AbstractPlatformHandler],
        url_patterns: Optional[List[str]] = None,
        detection_callback: Optional[Callable[[str], bool]] = None
    ) -> None:
        """
        Register a platform handler
        
        Args:
            platform_type: The platform type this handler supports
            handler_class: The handler class to instantiate
            url_patterns: List of URL patterns (domain names) for this platform
            detection_callback: Custom callback for URL detection
        """
        if not issubclass(handler_class, AbstractPlatformHandler):
            raise TypeError(f"Handler class must inherit from AbstractPlatformHandler")
        
        self._handlers[platform_type] = handler_class
        
        if url_patterns:
            self._url_patterns[platform_type] = url_patterns
        
        if detection_callback:
            self._detection_callbacks[platform_type] = detection_callback
        
        logger.info(f"Registered handler for {platform_type.display_name}: {handler_class.__name__}")
    
    def unregister(self, platform_type: PlatformType) -> bool:
        """
        Unregister a platform handler
        
        Args:
            platform_type: Platform type to unregister
            
        Returns:
            True if handler was found and removed
        """
        removed = False
        
        if platform_type in self._handlers:
            del self._handlers[platform_type]
            removed = True
        
        if platform_type in self._url_patterns:
            del self._url_patterns[platform_type]
        
        if platform_type in self._detection_callbacks:
            del self._detection_callbacks[platform_type]
        
        if removed:
            logger.info(f"Unregistered handler for {platform_type.display_name}")
        
        return removed
    
    def get_handler_class(self, platform_type: PlatformType) -> Optional[Type[AbstractPlatformHandler]]:
        """Get handler class for platform type"""
        return self._handlers.get(platform_type)
    
    def get_registered_platforms(self) -> List[PlatformType]:
        """Get list of registered platform types"""
        return list(self._handlers.keys())
    
    def detect_platform(self, url: str) -> PlatformType:
        """
        Detect platform type from URL
        
        Args:
            url: URL to analyze
            
        Returns:
            Detected platform type or PlatformType.UNKNOWN
        """
        # Normalize URL
        url_lower = url.lower().strip()
        
        # Try custom detection callbacks first
        for platform_type, callback in self._detection_callbacks.items():
            try:
                if callback(url):
                    logger.debug(f"Platform detected via callback: {platform_type.display_name}")
                    return platform_type
            except Exception as e:
                logger.warning(f"Detection callback error for {platform_type.display_name}: {e}")
        
        # Try URL pattern matching
        parsed_url = urlparse(url_lower)
        domain = parsed_url.netloc.lower()
        
        # Remove www. prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
        
        for platform_type, patterns in self._url_patterns.items():
            for pattern in patterns:
                if pattern.lower() in domain:
                    logger.debug(f"Platform detected via pattern: {platform_type.display_name}")
                    return platform_type
        
        # Fallback to enum-based detection
        detected = PlatformType.from_url(url)
        if detected != PlatformType.UNKNOWN:
            logger.debug(f"Platform detected via enum: {detected.display_name}")
        
        return detected
    
    def is_supported(self, platform_type: PlatformType) -> bool:
        """Check if platform type is supported"""
        return platform_type in self._handlers
    
    def is_url_supported(self, url: str) -> bool:
        """Check if URL is supported"""
        detected_platform = self.detect_platform(url)
        return self.is_supported(detected_platform)


# Global registry instance
_registry = PlatformRegistry()


class PlatformFactory:
    """Factory for creating platform handlers"""
    
    def __init__(self, registry: Optional[PlatformRegistry] = None):
        """
        Initialize factory
        
        Args:
            registry: Custom registry (uses global if None)
        """
        self._registry = registry or _registry
    
    def create_handler(
        self,
        platform_type: PlatformType,
        auth_info: Optional[AuthenticationInfo] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> AbstractPlatformHandler:
        """
        Create handler for specific platform type
        
        Args:
            platform_type: Platform type to create handler for
            auth_info: Authentication information
            config: Configuration dictionary
            
        Returns:
            Platform handler instance
            
        Raises:
            ValueError: If platform type is not supported
        """
        handler_class = self._registry.get_handler_class(platform_type)
        
        if handler_class is None:
            supported_platforms = self._registry.get_registered_platforms()
            raise ValueError(
                f"Unsupported platform: {platform_type.display_name}. "
                f"Supported platforms: {[p.display_name for p in supported_platforms]}"
            )
        
        try:
            handler = handler_class(
                platform_type=platform_type,
                auth_info=auth_info,
                config=config
            )
            logger.info(f"Created handler for {platform_type.display_name}: {handler_class.__name__}")
            return handler
        except Exception as e:
            logger.error(f"Failed to create handler for {platform_type.display_name}: {e}")
            raise
    
    def create_handler_for_url(
        self,
        url: str,
        auth_info: Optional[AuthenticationInfo] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> AbstractPlatformHandler:
        """
        Create handler for URL (auto-detect platform)
        
        Args:
            url: URL to create handler for
            auth_info: Authentication information
            config: Configuration dictionary
            
        Returns:
            Platform handler instance
            
        Raises:
            ValueError: If platform cannot be detected or is not supported
        """
        platform_type = self._registry.detect_platform(url)
        
        if platform_type == PlatformType.UNKNOWN:
            raise ValueError(f"Cannot detect platform from URL: {url}")
        
        return self.create_handler(platform_type, auth_info, config)
    
    def get_supported_platforms(self) -> List[PlatformType]:
        """Get list of supported platform types"""
        return self._registry.get_registered_platforms()
    
    def is_url_supported(self, url: str) -> bool:
        """Check if URL is supported"""
        return self._registry.is_url_supported(url)
    
    def detect_platform(self, url: str) -> PlatformType:
        """Detect platform type from URL"""
        return self._registry.detect_platform(url)
    
    def get_platform_capabilities(self, platform_type: PlatformType) -> Optional[PlatformCapabilities]:
        """
        Get capabilities for a platform type
        
        Args:
            platform_type: Platform type to get capabilities for
            
        Returns:
            Platform capabilities or None if not supported
        """
        try:
            # Create a temporary handler to get capabilities
            handler = self.create_handler(platform_type)
            return handler.get_capabilities()
        except Exception as e:
            logger.warning(f"Failed to get capabilities for {platform_type.display_name}: {e}")
            return None


# Global factory instance
_factory = PlatformFactory()


# =====================================================
# Convenience Functions
# =====================================================

def register_platform(
    platform_type: PlatformType,
    handler_class: Type[AbstractPlatformHandler],
    url_patterns: Optional[List[str]] = None,
    detection_callback: Optional[Callable[[str], bool]] = None
) -> None:
    """
    Register a platform handler globally
    
    Args:
        platform_type: The platform type this handler supports
        handler_class: The handler class to instantiate
        url_patterns: List of URL patterns (domain names) for this platform
        detection_callback: Custom callback for URL detection
    """
    _registry.register(platform_type, handler_class, url_patterns, detection_callback)


def unregister_platform(platform_type: PlatformType) -> bool:
    """
    Unregister a platform handler globally
    
    Args:
        platform_type: Platform type to unregister
        
    Returns:
        True if handler was found and removed
    """
    return _registry.unregister(platform_type)


def create_handler(
    platform_type: PlatformType,
    auth_info: Optional[AuthenticationInfo] = None,
    config: Optional[Dict[str, Any]] = None
) -> AbstractPlatformHandler:
    """
    Create handler for specific platform type using global factory
    
    Args:
        platform_type: Platform type to create handler for
        auth_info: Authentication information
        config: Configuration dictionary
        
    Returns:
        Platform handler instance
    """
    return _factory.create_handler(platform_type, auth_info, config)


def create_handler_for_url(
    url: str,
    auth_info: Optional[AuthenticationInfo] = None,
    config: Optional[Dict[str, Any]] = None
) -> AbstractPlatformHandler:
    """
    Create handler for URL using global factory (auto-detect platform)
    
    Args:
        url: URL to create handler for
        auth_info: Authentication information
        config: Configuration dictionary
        
    Returns:
        Platform handler instance
    """
    return _factory.create_handler_for_url(url, auth_info, config)


def detect_platform(url: str) -> PlatformType:
    """Detect platform type from URL using global factory"""
    return _factory.detect_platform(url)


def is_url_supported(url: str) -> bool:
    """Check if URL is supported using global factory"""
    return _factory.is_url_supported(url)


def get_supported_platforms() -> List[PlatformType]:
    """Get list of supported platform types using global factory"""
    return _factory.get_supported_platforms()


def get_platform_capabilities(platform_type: PlatformType) -> Optional[PlatformCapabilities]:
    """Get capabilities for a platform type using global factory"""
    return _factory.get_platform_capabilities(platform_type)


# =====================================================
# Auto-registration Support
# =====================================================

class PlatformHandler:
    """
    Decorator for automatic platform handler registration
    
    Usage:
        @PlatformHandler(
            platform_type=PlatformType.TIKTOK,
            url_patterns=['tiktok.com', 'vm.tiktok.com']
        )
        class TikTokHandler(AbstractPlatformHandler):
            pass
    """
    
    def __init__(
        self,
        platform_type: PlatformType,
        url_patterns: Optional[List[str]] = None,
        detection_callback: Optional[Callable[[str], bool]] = None,
        auto_register: bool = True
    ):
        """
        Initialize decorator
        
        Args:
            platform_type: Platform type this handler supports
            url_patterns: URL patterns for detection
            detection_callback: Custom detection callback
            auto_register: Whether to auto-register the handler
        """
        self.platform_type = platform_type
        self.url_patterns = url_patterns
        self.detection_callback = detection_callback
        self.auto_register = auto_register
    
    def __call__(self, handler_class: Type[AbstractPlatformHandler]) -> Type[AbstractPlatformHandler]:
        """Apply decorator to handler class"""
        if not issubclass(handler_class, AbstractPlatformHandler):
            raise TypeError(f"Handler class must inherit from AbstractPlatformHandler")
        
        # Store metadata on the class
        handler_class._platform_type = self.platform_type
        handler_class._url_patterns = self.url_patterns
        handler_class._detection_callback = self.detection_callback
        
        # Auto-register if enabled
        if self.auto_register:
            register_platform(
                self.platform_type,
                handler_class,
                self.url_patterns,
                self.detection_callback
            )
        
        return handler_class


# =====================================================
# Utility Functions
# =====================================================

def discover_handlers(module_name: str) -> int:
    """
    Discover and register handlers from a module
    
    Args:
        module_name: Module name to scan for handlers
        
    Returns:
        Number of handlers discovered and registered
    """
    import importlib
    import inspect
    
    try:
        module = importlib.import_module(module_name)
        discovered = 0
        
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if (issubclass(obj, AbstractPlatformHandler) and 
                obj != AbstractPlatformHandler and
                hasattr(obj, '_platform_type')):
                
                register_platform(
                    obj._platform_type,
                    obj,
                    getattr(obj, '_url_patterns', None),
                    getattr(obj, '_detection_callback', None)
                )
                discovered += 1
                logger.info(f"Auto-discovered handler: {name}")
        
        return discovered
    except Exception as e:
        logger.error(f"Failed to discover handlers from {module_name}: {e}")
        return 0


def get_factory_info() -> Dict[str, Any]:
    """
    Get information about the current factory state
    
    Returns:
        Dictionary with factory information
    """
    supported_platforms = _factory.get_supported_platforms()
    
    info = {
        'supported_platforms': [p.value for p in supported_platforms],
        'total_handlers': len(supported_platforms),
        'platform_details': {}
    }
    
    for platform in supported_platforms:
        handler_class = _registry.get_handler_class(platform)
        capabilities = _factory.get_platform_capabilities(platform)
        
        info['platform_details'][platform.value] = {
            'display_name': platform.display_name,
            'handler_class': handler_class.__name__ if handler_class else None,
            'url_patterns': _registry._url_patterns.get(platform, []),
            'has_custom_detection': platform in _registry._detection_callbacks,
            'capabilities': capabilities.__dict__ if capabilities else None
        }
    
    return info 