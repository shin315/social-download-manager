"""
Platform handler lifecycle management

This module provides comprehensive lifecycle management for platform handlers,
including connection management, resource cleanup, session management, 
and lifecycle hooks for platform-specific operations.
"""

import asyncio
import logging
import weakref
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable, Set, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from enum import Enum

from .enums import PlatformType
from .models import AuthenticationInfo, PlatformCapabilities

logger = logging.getLogger(__name__)


# =====================================================
# Lifecycle States and Events
# =====================================================

class LifecycleState(Enum):
    """Handler lifecycle states"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DISCONNECTING = "disconnecting"
    SHUTTING_DOWN = "shutting_down"
    SHUTDOWN = "shutdown"
    ERROR = "error"


class LifecycleEvent(Enum):
    """Lifecycle events"""
    BEFORE_INIT = "before_init"
    AFTER_INIT = "after_init"
    BEFORE_CONNECT = "before_connect"
    AFTER_CONNECT = "after_connect"
    BEFORE_AUTH = "before_auth"
    AFTER_AUTH = "after_auth"
    BEFORE_SUSPEND = "before_suspend"
    AFTER_SUSPEND = "after_suspend"
    BEFORE_RESUME = "before_resume"
    AFTER_RESUME = "after_resume"
    BEFORE_DISCONNECT = "before_disconnect"
    AFTER_DISCONNECT = "after_disconnect"
    BEFORE_SHUTDOWN = "before_shutdown"
    AFTER_SHUTDOWN = "after_shutdown"
    ON_ERROR = "on_error"
    ON_RECONNECT = "on_reconnect"
    ON_HEALTH_CHECK = "on_health_check"


@dataclass
class LifecycleContext:
    """Context information for lifecycle events"""
    handler_id: str
    platform_type: PlatformType
    state: LifecycleState
    event: LifecycleEvent
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Exception] = None


# =====================================================
# Resource Management
# =====================================================

class ManagedResource(ABC):
    """Base class for managed resources"""
    
    def __init__(self, resource_id: str):
        self.resource_id = resource_id
        self.created_at = datetime.now()
        self._is_disposed = False
    
    @property
    def is_disposed(self) -> bool:
        """Check if resource is disposed"""
        return self._is_disposed
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup the resource"""
        pass
    
    async def dispose(self) -> None:
        """Dispose of the resource"""
        if not self._is_disposed:
            try:
                await self.cleanup()
            except Exception as e:
                logger.warning(f"Error cleaning up resource {self.resource_id}: {e}")
            finally:
                self._is_disposed = True


class SessionResource(ManagedResource):
    """Managed HTTP session resource"""
    
    def __init__(self, resource_id: str, session: Any):
        super().__init__(resource_id)
        self.session = session
        self.last_used = datetime.now()
        self.request_count = 0
    
    def mark_used(self) -> None:
        """Mark session as recently used"""
        self.last_used = datetime.now()
        self.request_count += 1
    
    @property
    def idle_time(self) -> timedelta:
        """Get idle time since last use"""
        return datetime.now() - self.last_used
    
    async def cleanup(self) -> None:
        """Close the HTTP session"""
        if hasattr(self.session, 'close'):
            await self.session.close()


class ConnectionResource(ManagedResource):
    """Managed connection resource"""
    
    def __init__(self, resource_id: str, connection: Any, config: Dict[str, Any]):
        super().__init__(resource_id)
        self.connection = connection
        self.config = config
        self.is_healthy = True
        self.last_health_check = datetime.now()
    
    async def health_check(self) -> bool:
        """Perform health check on connection"""
        try:
            # Basic health check - subclasses can override
            self.last_health_check = datetime.now()
            return self.connection is not None
        except Exception as e:
            logger.warning(f"Health check failed for {self.resource_id}: {e}")
            self.is_healthy = False
            return False
    
    async def cleanup(self) -> None:
        """Close the connection"""
        if hasattr(self.connection, 'close'):
            await self.connection.close()


# =====================================================
# Resource Manager
# =====================================================

class ResourceManager:
    """Manages platform handler resources"""
    
    def __init__(self, max_idle_time: int = 300):  # 5 minutes default
        self._resources: Dict[str, ManagedResource] = {}
        self._resource_locks: Dict[str, asyncio.Lock] = {}
        self._max_idle_time = max_idle_time
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
    
    async def add_resource(self, resource: ManagedResource) -> None:
        """Add a managed resource"""
        self._resources[resource.resource_id] = resource
        self._resource_locks[resource.resource_id] = asyncio.Lock()
        logger.debug(f"Added resource: {resource.resource_id}")
    
    async def remove_resource(self, resource_id: str) -> bool:
        """Remove and dispose a resource"""
        if resource_id in self._resources:
            resource = self._resources[resource_id]
            await resource.dispose()
            del self._resources[resource_id]
            
            if resource_id in self._resource_locks:
                del self._resource_locks[resource_id]
            
            logger.debug(f"Removed resource: {resource_id}")
            return True
        return False
    
    async def get_resource(self, resource_id: str) -> Optional[ManagedResource]:
        """Get a resource by ID"""
        resource = self._resources.get(resource_id)
        if resource and not resource.is_disposed:
            return resource
        return None
    
    async def cleanup_idle_resources(self) -> int:
        """Clean up idle resources and return count cleaned"""
        cleaned = 0
        current_time = datetime.now()
        
        idle_resources = []
        for resource_id, resource in self._resources.items():
            if isinstance(resource, SessionResource):
                if resource.idle_time.total_seconds() > self._max_idle_time:
                    idle_resources.append(resource_id)
        
        for resource_id in idle_resources:
            if await self.remove_resource(resource_id):
                cleaned += 1
        
        return cleaned
    
    async def dispose_all(self) -> None:
        """Dispose all resources"""
        logger.info("Disposing all resources...")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Dispose all resources
        for resource_id in list(self._resources.keys()):
            await self.remove_resource(resource_id)
        
        logger.info("All resources disposed")
    
    async def start_cleanup_task(self, interval: int = 60) -> None:
        """Start background cleanup task"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop(interval))
    
    async def _cleanup_loop(self, interval: int) -> None:
        """Background cleanup loop"""
        try:
            while not self._shutdown_event.is_set():
                await asyncio.sleep(interval)
                if not self._shutdown_event.is_set():
                    cleaned = await self.cleanup_idle_resources()
                    if cleaned > 0:
                        logger.debug(f"Cleaned up {cleaned} idle resources")
        except asyncio.CancelledError:
            logger.debug("Cleanup task cancelled")
        except Exception as e:
            logger.error(f"Error in cleanup loop: {e}")


# =====================================================
# Lifecycle Hooks
# =====================================================

LifecycleHook = Callable[[LifecycleContext], Optional[asyncio.Task]]


class LifecycleManager:
    """Manages handler lifecycle and hooks"""
    
    def __init__(self):
        self._hooks: Dict[LifecycleEvent, List[LifecycleHook]] = {}
        self._state_history: Dict[str, List[LifecycleState]] = {}
        self._current_states: Dict[str, LifecycleState] = {}
    
    def add_hook(self, event: LifecycleEvent, hook: LifecycleHook) -> None:
        """Add a lifecycle hook"""
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(hook)
        logger.debug(f"Added hook for {event.value}")
    
    def remove_hook(self, event: LifecycleEvent, hook: LifecycleHook) -> bool:
        """Remove a lifecycle hook"""
        if event in self._hooks and hook in self._hooks[event]:
            self._hooks[event].remove(hook)
            return True
        return False
    
    async def emit_event(self, context: LifecycleContext) -> None:
        """Emit a lifecycle event to all registered hooks"""
        # Update state tracking
        self._current_states[context.handler_id] = context.state
        
        if context.handler_id not in self._state_history:
            self._state_history[context.handler_id] = []
        self._state_history[context.handler_id].append(context.state)
        
        # Execute hooks
        hooks = self._hooks.get(context.event, [])
        if hooks:
            logger.debug(f"Emitting {context.event.value} for {context.handler_id}")
            
            # Run hooks concurrently
            tasks = []
            for hook in hooks:
                try:
                    result = hook(context)
                    if asyncio.iscoroutine(result):
                        tasks.append(asyncio.create_task(result))
                except Exception as e:
                    logger.error(f"Error in lifecycle hook: {e}")
            
            # Wait for all hooks to complete
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_current_state(self, handler_id: str) -> Optional[LifecycleState]:
        """Get current state for handler"""
        return self._current_states.get(handler_id)
    
    def get_state_history(self, handler_id: str) -> List[LifecycleState]:
        """Get state history for handler"""
        return self._state_history.get(handler_id, [])
    
    def cleanup_handler(self, handler_id: str) -> None:
        """Clean up tracking for a handler"""
        self._current_states.pop(handler_id, None)
        self._state_history.pop(handler_id, None)


# =====================================================
# Connection Pool Manager
# =====================================================

@dataclass
class ConnectionConfig:
    """Connection configuration"""
    max_connections: int = 10
    connection_timeout: int = 30
    read_timeout: int = 60
    max_idle_time: int = 300
    health_check_interval: int = 60
    max_retries: int = 3
    retry_delay: float = 1.0


class ConnectionPool:
    """Advanced connection pool with health monitoring"""
    
    def __init__(self, config: ConnectionConfig):
        self.config = config
        self._connections: Dict[str, ConnectionResource] = {}
        self._available_connections: Set[str] = set()
        self._in_use_connections: Set[str] = set()
        self._connection_lock = asyncio.Lock()
        self._health_check_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
    
    async def get_connection(self, connection_id: str) -> Optional[ConnectionResource]:
        """Get an available connection"""
        async with self._connection_lock:
            if connection_id in self._available_connections:
                self._available_connections.remove(connection_id)
                self._in_use_connections.add(connection_id)
                return self._connections.get(connection_id)
        return None
    
    async def return_connection(self, connection_id: str) -> None:
        """Return a connection to the pool"""
        async with self._connection_lock:
            if connection_id in self._in_use_connections:
                self._in_use_connections.remove(connection_id)
                self._available_connections.add(connection_id)
    
    async def add_connection(self, connection: ConnectionResource) -> None:
        """Add a connection to the pool"""
        async with self._connection_lock:
            self._connections[connection.resource_id] = connection
            self._available_connections.add(connection.resource_id)
    
    async def remove_connection(self, connection_id: str) -> None:
        """Remove a connection from the pool"""
        async with self._connection_lock:
            if connection_id in self._connections:
                connection = self._connections[connection_id]
                await connection.dispose()
                del self._connections[connection_id]
                self._available_connections.discard(connection_id)
                self._in_use_connections.discard(connection_id)
    
    async def health_check_loop(self) -> None:
        """Background health check loop"""
        try:
            while not self._shutdown_event.is_set():
                await self._perform_health_checks()
                await asyncio.sleep(self.config.health_check_interval)
        except asyncio.CancelledError:
            logger.debug("Health check loop cancelled")
        except Exception as e:
            logger.error(f"Error in health check loop: {e}")
    
    async def _perform_health_checks(self) -> None:
        """Perform health checks on all connections"""
        unhealthy_connections = []
        
        for connection_id, connection in self._connections.items():
            if connection_id in self._available_connections:
                is_healthy = await connection.health_check()
                if not is_healthy:
                    unhealthy_connections.append(connection_id)
        
        # Remove unhealthy connections
        for connection_id in unhealthy_connections:
            await self.remove_connection(connection_id)
            logger.warning(f"Removed unhealthy connection: {connection_id}")
    
    async def start_health_monitoring(self) -> None:
        """Start background health monitoring"""
        if self._health_check_task is None or self._health_check_task.done():
            self._health_check_task = asyncio.create_task(self.health_check_loop())
    
    async def shutdown(self) -> None:
        """Shutdown the connection pool"""
        logger.info("Shutting down connection pool...")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Cancel health check task
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        for connection_id in list(self._connections.keys()):
            await self.remove_connection(connection_id)
        
        logger.info("Connection pool shutdown complete")


# =====================================================
# Platform Lifecycle Mixin
# =====================================================

class LifecycleMixin:
    """Mixin to add advanced lifecycle management to platform handlers"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._handler_id = f"{self._platform_type.value}_{id(self)}"
        self._lifecycle_manager = LifecycleManager()
        self._resource_manager = ResourceManager()
        self._connection_pool: Optional[ConnectionPool] = None
        self._lifecycle_state = LifecycleState.UNINITIALIZED
        
        # Set up default hooks
        self._setup_default_hooks()
    
    def _setup_default_hooks(self) -> None:
        """Set up default lifecycle hooks"""
        self._lifecycle_manager.add_hook(
            LifecycleEvent.BEFORE_INIT,
            self._on_before_init
        )
        self._lifecycle_manager.add_hook(
            LifecycleEvent.AFTER_INIT,
            self._on_after_init
        )
        self._lifecycle_manager.add_hook(
            LifecycleEvent.ON_ERROR,
            self._on_error
        )
        self._lifecycle_manager.add_hook(
            LifecycleEvent.BEFORE_SHUTDOWN,
            self._on_before_shutdown
        )
    
    @property
    def lifecycle_state(self) -> LifecycleState:
        """Get current lifecycle state"""
        return self._lifecycle_state
    
    @property
    def handler_id(self) -> str:
        """Get unique handler ID"""
        return self._handler_id
    
    async def _transition_state(
        self, 
        new_state: LifecycleState, 
        event: LifecycleEvent,
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Transition to a new lifecycle state"""
        old_state = self._lifecycle_state
        self._lifecycle_state = new_state
        
        context = LifecycleContext(
            handler_id=self._handler_id,
            platform_type=self._platform_type,
            state=new_state,
            event=event,
            data=data or {}
        )
        
        logger.debug(f"State transition: {old_state.value} -> {new_state.value}")
        await self._lifecycle_manager.emit_event(context)
    
    async def initialize_with_lifecycle(self) -> None:
        """Initialize with full lifecycle management"""
        try:
            await self._transition_state(
                LifecycleState.INITIALIZING,
                LifecycleEvent.BEFORE_INIT
            )
            
            # Initialize connection pool if needed
            capabilities = self.get_capabilities()
            if capabilities.max_concurrent_downloads > 1:
                config = ConnectionConfig(
                    max_connections=capabilities.max_concurrent_downloads,
                    max_idle_time=300
                )
                self._connection_pool = ConnectionPool(config)
                await self._connection_pool.start_health_monitoring()
            
            # Start resource manager cleanup
            await self._resource_manager.start_cleanup_task()
            
            # Call original initialization
            await self.initialize()
            
            await self._transition_state(
                LifecycleState.READY,
                LifecycleEvent.AFTER_INIT
            )
            
        except Exception as e:
            await self._transition_state(
                LifecycleState.ERROR,
                LifecycleEvent.ON_ERROR,
                {'error': str(e)}
            )
            raise
    
    async def shutdown_with_lifecycle(self) -> None:
        """Shutdown with full lifecycle management"""
        try:
            await self._transition_state(
                LifecycleState.SHUTTING_DOWN,
                LifecycleEvent.BEFORE_SHUTDOWN
            )
            
            # Shutdown connection pool
            if self._connection_pool:
                await self._connection_pool.shutdown()
            
            # Dispose all resources
            await self._resource_manager.dispose_all()
            
            # Call original shutdown
            await self.shutdown()
            
            await self._transition_state(
                LifecycleState.SHUTDOWN,
                LifecycleEvent.AFTER_SHUTDOWN
            )
            
        except Exception as e:
            await self._transition_state(
                LifecycleState.ERROR,
                LifecycleEvent.ON_ERROR,
                {'error': str(e)}
            )
            raise
        finally:
            # Clean up lifecycle tracking
            self._lifecycle_manager.cleanup_handler(self._handler_id)
    
    @asynccontextmanager
    async def managed_lifecycle(self):
        """Context manager for complete lifecycle management"""
        await self.initialize_with_lifecycle()
        try:
            yield self
        finally:
            await self.shutdown_with_lifecycle()
    
    # Default hook implementations
    async def _on_before_init(self, context: LifecycleContext) -> None:
        """Default before init hook"""
        logger.info(f"Initializing {context.platform_type.display_name} handler")
    
    async def _on_after_init(self, context: LifecycleContext) -> None:
        """Default after init hook"""
        logger.info(f"{context.platform_type.display_name} handler ready")
    
    async def _on_error(self, context: LifecycleContext) -> None:
        """Default error hook"""
        error_msg = context.data.get('error', 'Unknown error')
        logger.error(f"Handler error: {error_msg}")
    
    async def _on_before_shutdown(self, context: LifecycleContext) -> None:
        """Default before shutdown hook"""
        logger.info(f"Shutting down {context.platform_type.display_name} handler")
    
    # Resource management helpers
    async def add_managed_resource(self, resource: ManagedResource) -> None:
        """Add a managed resource"""
        await self._resource_manager.add_resource(resource)
    
    async def get_managed_resource(self, resource_id: str) -> Optional[ManagedResource]:
        """Get a managed resource"""
        return await self._resource_manager.get_resource(resource_id)
    
    def add_lifecycle_hook(self, event: LifecycleEvent, hook: LifecycleHook) -> None:
        """Add a custom lifecycle hook"""
        self._lifecycle_manager.add_hook(event, hook) 