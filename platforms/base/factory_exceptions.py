"""
Factory-specific exceptions for enhanced error handling

This module defines specialized exceptions for platform factory operations,
providing more granular error handling and better error context for factory-related failures.
"""

from typing import Optional, List, Any, Dict
from .enums import PlatformType


class FactoryError(Exception):
    """Base exception for all factory-related errors"""
    
    def __init__(
        self, 
        message: str, 
        operation: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.operation = operation
        self.context = context or {}
    
    def __str__(self) -> str:
        parts = [self.message]
        if self.operation:
            parts.append(f"Operation: {self.operation}")
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"Context: {context_str}")
        return " | ".join(parts)


class PlatformRegistrationError(FactoryError):
    """Error during platform handler registration"""
    
    def __init__(
        self,
        message: str,
        platform_type: Optional[PlatformType] = None,
        handler_class: Optional[type] = None,
        **kwargs
    ):
        super().__init__(message, operation="registration", **kwargs)
        self.platform_type = platform_type
        self.handler_class = handler_class
    
    def __str__(self) -> str:
        parts = [self.message]
        if self.platform_type:
            parts.append(f"Platform: {self.platform_type.display_name}")
        if self.handler_class:
            parts.append(f"Handler: {self.handler_class.__name__}")
        if self.operation:
            parts.append(f"Operation: {self.operation}")
        return " | ".join(parts)


class DuplicateRegistrationError(PlatformRegistrationError):
    """Error when attempting to register a platform that's already registered"""
    
    def __init__(
        self,
        platform_type: PlatformType,
        existing_handler: type,
        new_handler: type
    ):
        message = f"Platform {platform_type.display_name} is already registered"
        super().__init__(
            message,
            platform_type=platform_type,
            handler_class=new_handler,
            context={
                "existing_handler": existing_handler.__name__,
                "attempted_handler": new_handler.__name__
            }
        )
        self.existing_handler = existing_handler


class InvalidHandlerError(PlatformRegistrationError):
    """Error when attempting to register an invalid handler class"""
    
    def __init__(
        self,
        handler_class: type,
        reason: str,
        platform_type: Optional[PlatformType] = None
    ):
        message = f"Invalid handler class: {reason}"
        super().__init__(
            message,
            platform_type=platform_type,
            handler_class=handler_class,
            context={"validation_failure": reason}
        )
        self.reason = reason


class PlatformDetectionError(FactoryError):
    """Error during platform detection from URL"""
    
    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        detection_method: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, operation="detection", **kwargs)
        self.url = url
        self.detection_method = detection_method
    
    def __str__(self) -> str:
        parts = [self.message]
        if self.url:
            parts.append(f"URL: {self.url}")
        if self.detection_method:
            parts.append(f"Method: {self.detection_method}")
        if self.operation:
            parts.append(f"Operation: {self.operation}")
        return " | ".join(parts)


class UnsupportedPlatformError(FactoryError):
    """Error when trying to use an unsupported platform"""
    
    def __init__(
        self,
        platform_type: PlatformType,
        supported_platforms: Optional[List[PlatformType]] = None,
        **kwargs
    ):
        message = f"Unsupported platform: {platform_type.display_name}"
        if supported_platforms:
            platform_names = [p.display_name for p in supported_platforms]
            message += f". Supported platforms: {platform_names}"
        
        super().__init__(message, operation="handler_creation", **kwargs)
        self.platform_type = platform_type
        self.supported_platforms = supported_platforms or []


class UnsupportedUrlError(FactoryError):
    """Error when trying to process an unsupported URL"""
    
    def __init__(
        self,
        url: str,
        detected_platform: Optional[PlatformType] = None,
        **kwargs
    ):
        message = f"Cannot detect or create handler for URL: {url}"
        if detected_platform and detected_platform != PlatformType.UNKNOWN:
            message += f" (detected as {detected_platform.display_name} but not supported)"
        
        super().__init__(message, operation="url_processing", **kwargs)
        self.url = url
        self.detected_platform = detected_platform


class HandlerInstantiationError(FactoryError):
    """Error during handler instantiation"""
    
    def __init__(
        self,
        message: str,
        platform_type: Optional[PlatformType] = None,
        handler_class: Optional[type] = None,
        original_error: Optional[Exception] = None,
        **kwargs
    ):
        super().__init__(message, operation="instantiation", **kwargs)
        self.platform_type = platform_type
        self.handler_class = handler_class
        self.original_error = original_error
    
    def __str__(self) -> str:
        parts = [self.message]
        if self.platform_type:
            parts.append(f"Platform: {self.platform_type.display_name}")
        if self.handler_class:
            parts.append(f"Handler: {self.handler_class.__name__}")
        if self.original_error:
            parts.append(f"Cause: {self.original_error}")
        if self.operation:
            parts.append(f"Operation: {self.operation}")
        return " | ".join(parts)


class CapabilityRetrievalError(FactoryError):
    """Error when retrieving platform capabilities"""
    
    def __init__(
        self,
        platform_type: PlatformType,
        original_error: Optional[Exception] = None,
        **kwargs
    ):
        message = f"Failed to retrieve capabilities for {platform_type.display_name}"
        super().__init__(message, operation="capability_retrieval", **kwargs)
        self.platform_type = platform_type
        self.original_error = original_error


class DetectionCallbackError(FactoryError):
    """Error in custom detection callback"""
    
    def __init__(
        self,
        platform_type: PlatformType,
        url: str,
        original_error: Exception,
        **kwargs
    ):
        message = f"Detection callback failed for {platform_type.display_name}"
        super().__init__(message, operation="callback_detection", **kwargs)
        self.platform_type = platform_type
        self.url = url
        self.original_error = original_error
    
    def __str__(self) -> str:
        parts = [self.message]
        parts.append(f"Platform: {self.platform_type.display_name}")
        parts.append(f"URL: {self.url}")
        parts.append(f"Cause: {self.original_error}")
        return " | ".join(parts)


class FactoryConfigurationError(FactoryError):
    """Error in factory configuration"""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_value: Optional[Any] = None,
        **kwargs
    ):
        super().__init__(message, operation="configuration", **kwargs)
        self.config_key = config_key
        self.config_value = config_value


class RegistryStateError(FactoryError):
    """Error related to registry state inconsistency"""
    
    def __init__(
        self,
        message: str,
        registry_state: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(message, operation="registry_management", **kwargs)
        self.registry_state = registry_state or {}


# Convenience function for error chaining
def chain_factory_error(
    original_error: Exception,
    factory_error_class: type,
    additional_context: Optional[Dict[str, Any]] = None,
    **kwargs
) -> FactoryError:
    """
    Chain an original exception with a factory-specific error
    
    Args:
        original_error: The original exception that occurred
        factory_error_class: The factory error class to wrap with
        additional_context: Additional context to include
        **kwargs: Additional arguments for the factory error
    
    Returns:
        Factory error with chained context
    """
    context = additional_context or {}
    context["original_error_type"] = type(original_error).__name__
    context["original_error_message"] = str(original_error)
    
    if hasattr(kwargs, 'context'):
        kwargs['context'].update(context)
    else:
        kwargs['context'] = context
    
    return factory_error_class(**kwargs) 