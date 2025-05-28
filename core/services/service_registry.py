"""
Service Registry for Dependency Injection

Provides centralized registration and retrieval of service instances,
enabling dependency injection for controllers and other components.
"""

import logging
from typing import Dict, Any, TypeVar, Type, Optional, List, Callable
from abc import ABC, abstractmethod
from enum import Enum
import threading

T = TypeVar('T')


class ServiceLifetime(Enum):
    """Service lifetime management"""
    SINGLETON = "singleton"  # Single instance for the entire application
    SCOPED = "scoped"       # Single instance per scope (e.g., per request)
    TRANSIENT = "transient"  # New instance every time


class ServiceDescriptor:
    """Describes how a service should be instantiated"""
    
    def __init__(
        self,
        service_type: Type[T],
        implementation_type: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None,
        instance: Optional[T] = None,
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON
    ):
        self.service_type = service_type
        self.implementation_type = implementation_type
        self.factory = factory
        self.instance = instance
        self.lifetime = lifetime
        
        # Validation
        provided_methods = sum([
            implementation_type is not None,
            factory is not None,
            instance is not None
        ])
        
        if provided_methods != 1:
            raise ValueError("Exactly one of implementation_type, factory, or instance must be provided")
    
    def create_instance(self, registry: 'ServiceRegistry') -> T:
        """Create a new instance of the service"""
        if self.instance is not None:
            return self.instance
        elif self.factory is not None:
            return self.factory()
        elif self.implementation_type is not None:
            # Try to resolve constructor dependencies
            return registry._create_with_dependencies(self.implementation_type)
        else:
            raise RuntimeError("No valid instantiation method available")


class ServiceRegistry:
    """Central registry for service dependency injection"""
    
    def __init__(self):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._singletons: Dict[Type, Any] = {}
        self._lock = threading.RLock()
        self._logger = logging.getLogger(__name__)
        self._circular_detection: List[Type] = []
    
    def register_singleton(self, service_type: Type[T], implementation_type: Type[T]) -> 'ServiceRegistry':
        """
        Register a service as singleton (created once and reused)
        
        Args:
            service_type: Interface or base type
            implementation_type: Concrete implementation type
            
        Returns:
            Self for method chaining
        """
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation_type=implementation_type,
            lifetime=ServiceLifetime.SINGLETON
        )
        
        with self._lock:
            self._services[service_type] = descriptor
            self._logger.debug(f"Registered singleton service: {service_type.__name__} -> {implementation_type.__name__}")
        
        return self
    
    def register_transient(self, service_type: Type[T], implementation_type: Type[T]) -> 'ServiceRegistry':
        """
        Register a service as transient (new instance every time)
        
        Args:
            service_type: Interface or base type
            implementation_type: Concrete implementation type
            
        Returns:
            Self for method chaining
        """
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation_type=implementation_type,
            lifetime=ServiceLifetime.TRANSIENT
        )
        
        with self._lock:
            self._services[service_type] = descriptor
            self._logger.debug(f"Registered transient service: {service_type.__name__} -> {implementation_type.__name__}")
        
        return self
    
    def register_instance(self, service_type: Type[T], instance: T) -> 'ServiceRegistry':
        """
        Register a specific instance as singleton
        
        Args:
            service_type: Interface or base type
            instance: Concrete instance
            
        Returns:
            Self for method chaining
        """
        descriptor = ServiceDescriptor(
            service_type=service_type,
            instance=instance,
            lifetime=ServiceLifetime.SINGLETON
        )
        
        with self._lock:
            self._services[service_type] = descriptor
            self._singletons[service_type] = instance
            self._logger.debug(f"Registered instance service: {service_type.__name__}")
        
        return self
    
    def register_factory(self, service_type: Type[T], factory: Callable[[], T], lifetime: ServiceLifetime = ServiceLifetime.SINGLETON) -> 'ServiceRegistry':
        """
        Register a factory function for creating service instances
        
        Args:
            service_type: Interface or base type
            factory: Factory function that creates instances
            lifetime: Service lifetime
            
        Returns:
            Self for method chaining
        """
        descriptor = ServiceDescriptor(
            service_type=service_type,
            factory=factory,
            lifetime=lifetime
        )
        
        with self._lock:
            self._services[service_type] = descriptor
            self._logger.debug(f"Registered factory service: {service_type.__name__} ({lifetime.value})")
        
        return self
    
    def get_service(self, service_type: Type[T]) -> T:
        """
        Get a service instance
        
        Args:
            service_type: Type of service to retrieve
            
        Returns:
            Service instance
            
        Raises:
            KeyError: If service is not registered
            RuntimeError: If circular dependency is detected
        """
        with self._lock:
            if service_type not in self._services:
                raise KeyError(f"Service {service_type.__name__} is not registered")
            
            descriptor = self._services[service_type]
            
            # Check for singleton
            if descriptor.lifetime == ServiceLifetime.SINGLETON:
                if service_type in self._singletons:
                    return self._singletons[service_type]
                
                # Create singleton instance
                instance = self._create_instance(service_type, descriptor)
                self._singletons[service_type] = instance
                return instance
            
            # Create new instance for transient
            return self._create_instance(service_type, descriptor)
    
    def try_get_service(self, service_type: Type[T]) -> Optional[T]:
        """
        Try to get a service instance, returning None if not registered
        
        Args:
            service_type: Type of service to retrieve
            
        Returns:
            Service instance or None if not registered
        """
        try:
            return self.get_service(service_type)
        except KeyError:
            return None
    
    def is_registered(self, service_type: Type) -> bool:
        """
        Check if a service type is registered
        
        Args:
            service_type: Type to check
            
        Returns:
            True if registered
        """
        with self._lock:
            return service_type in self._services
    
    def get_registered_services(self) -> List[Type]:
        """
        Get list of all registered service types
        
        Returns:
            List of registered service types
        """
        with self._lock:
            return list(self._services.keys())
    
    def unregister(self, service_type: Type) -> bool:
        """
        Unregister a service
        
        Args:
            service_type: Type to unregister
            
        Returns:
            True if service was registered and removed
        """
        with self._lock:
            if service_type in self._services:
                del self._services[service_type]
                if service_type in self._singletons:
                    del self._singletons[service_type]
                self._logger.debug(f"Unregistered service: {service_type.__name__}")
                return True
            return False
    
    def clear(self) -> None:
        """Clear all registered services"""
        with self._lock:
            self._services.clear()
            self._singletons.clear()
            self._logger.debug("Cleared all registered services")
    
    def _create_instance(self, service_type: Type[T], descriptor: ServiceDescriptor) -> T:
        """Create instance with circular dependency detection"""
        # Check for circular dependency
        if service_type in self._circular_detection:
            dependency_chain = " -> ".join([t.__name__ for t in self._circular_detection])
            raise RuntimeError(f"Circular dependency detected: {dependency_chain} -> {service_type.__name__}")
        
        try:
            self._circular_detection.append(service_type)
            return descriptor.create_instance(self)
        finally:
            self._circular_detection.remove(service_type)
    
    def _create_with_dependencies(self, implementation_type: Type[T]) -> T:
        """Create instance and inject dependencies"""
        try:
            # Simple constructor injection - for more complex scenarios,
            # we would need to inspect the constructor parameters
            return implementation_type()
        except Exception as e:
            self._logger.error(f"Failed to create instance of {implementation_type.__name__}: {e}")
            raise RuntimeError(f"Failed to create service instance: {e}")
    
    def dispose(self) -> None:
        """Dispose of all singleton services that support disposal"""
        with self._lock:
            for service_type, instance in self._singletons.items():
                try:
                    if hasattr(instance, 'dispose'):
                        instance.dispose()
                    elif hasattr(instance, 'close'):
                        instance.close()
                    elif hasattr(instance, 'cleanup'):
                        instance.cleanup()
                except Exception as e:
                    self._logger.error(f"Error disposing service {service_type.__name__}: {e}")
            
            self._singletons.clear()
            self._logger.debug("Disposed all singleton services")


# Global service registry instance
_service_registry: Optional[ServiceRegistry] = None
_registry_lock = threading.Lock()


def get_service_registry() -> ServiceRegistry:
    """Get the global service registry instance"""
    global _service_registry
    if _service_registry is None:
        with _registry_lock:
            if _service_registry is None:
                _service_registry = ServiceRegistry()
    return _service_registry


def configure_services() -> ServiceRegistry:
    """Configure default services in the registry"""
    registry = get_service_registry()
    
    # Import services to register them
    from .content_service import IContentService, ContentService
    
    # Register core services
    registry.register_singleton(IContentService, ContentService)
    
    # TODO: Register other services as they are implemented
    # registry.register_singleton(IAnalyticsService, AnalyticsService)
    # registry.register_singleton(IDownloadService, DownloadService)
    
    logging.getLogger(__name__).info("Default services configured")
    return registry


def get_service(service_type: Type[T]) -> T:
    """Convenience function to get a service from the global registry"""
    return get_service_registry().get_service(service_type)


def try_get_service(service_type: Type[T]) -> Optional[T]:
    """Convenience function to try getting a service from the global registry"""
    return get_service_registry().try_get_service(service_type) 