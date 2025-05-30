"""
Repository Event Integration for Social Download Manager v2.0

Extends the existing event bus system to handle repository-related events.
Establishes conventions for repository event naming, payload structure,
and provides specialized event handlers for repository operations.
"""

from typing import Dict, Any, List, Optional, Callable, Union, TypeVar, Type
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import logging
from PyQt6.QtCore import QObject, pyqtSignal

from data.models.repositories import IRepository, IContentRepository
from data.models.repository_interfaces import IDownloadRepository
from data.models.base import BaseEntity, EntityId
from core.event_system import EventBus, Event, EventType, EventHandler, get_event_bus, publish_event
from core.constants import AppConstants

T = TypeVar('T', bound=BaseEntity)


class RepositoryEventType(Enum):
    """Extended event types for repository operations"""
    
    # Entity CRUD operations
    ENTITY_CREATED = "repository.entity.created"
    ENTITY_UPDATED = "repository.entity.updated"
    ENTITY_DELETED = "repository.entity.deleted"
    ENTITY_RETRIEVED = "repository.entity.retrieved"
    
    # Bulk operations
    ENTITIES_BULK_CREATED = "repository.entities.bulk_created"
    ENTITIES_BULK_UPDATED = "repository.entities.bulk_updated"
    ENTITIES_BULK_DELETED = "repository.entities.bulk_deleted"
    
    # Query operations
    QUERY_EXECUTED = "repository.query.executed"
    SEARCH_PERFORMED = "repository.search.performed"
    FILTER_APPLIED = "repository.filter.applied"
    
    # Transaction operations
    TRANSACTION_STARTED = "repository.transaction.started"
    TRANSACTION_COMMITTED = "repository.transaction.committed"
    TRANSACTION_ROLLED_BACK = "repository.transaction.rolled_back"
    
    # Cache operations
    CACHE_HIT = "repository.cache.hit"
    CACHE_MISS = "repository.cache.miss"
    CACHE_INVALIDATED = "repository.cache.invalidated"
    CACHE_UPDATED = "repository.cache.updated"
    
    # Repository lifecycle
    REPOSITORY_INITIALIZED = "repository.lifecycle.initialized"
    REPOSITORY_CONNECTED = "repository.lifecycle.connected"
    REPOSITORY_DISCONNECTED = "repository.lifecycle.disconnected"
    REPOSITORY_ERROR = "repository.lifecycle.error"
    
    # Data validation
    VALIDATION_PASSED = "repository.validation.passed"
    VALIDATION_FAILED = "repository.validation.failed"
    
    # Performance monitoring
    OPERATION_SLOW = "repository.performance.slow"
    OPERATION_COMPLETED = "repository.performance.completed"
    
    # Data integrity
    INTEGRITY_CHECK_PASSED = "repository.integrity.passed"
    INTEGRITY_CHECK_FAILED = "repository.integrity.failed"
    CONSTRAINT_VIOLATION = "repository.integrity.constraint_violation"


@dataclass
class RepositoryEventPayload:
    """Standard payload structure for repository events"""
    
    # Core identification
    repository_type: str
    repository_id: str
    operation: str
    
    # Entity information
    entity_type: Optional[str] = None
    entity_id: Optional[EntityId] = None
    entity_ids: Optional[List[EntityId]] = None
    
    # Operation details
    operation_id: Optional[str] = None
    transaction_id: Optional[str] = None
    query_info: Optional[Dict[str, Any]] = None
    
    # Data
    entity_data: Optional[Dict[str, Any]] = None
    entities_data: Optional[List[Dict[str, Any]]] = None
    previous_data: Optional[Dict[str, Any]] = None
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Performance metrics
    execution_time_ms: Optional[float] = None
    affected_rows: Optional[int] = None
    cache_hit: Optional[bool] = None
    
    # Error information
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    
    # Additional context
    context: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class IRepositoryEventHandler(ABC):
    """Interface for repository event handlers"""
    
    @abstractmethod
    def handle_repository_event(self, event_type: RepositoryEventType, 
                               payload: RepositoryEventPayload) -> None:
        """Handle a repository event"""
        pass
    
    @abstractmethod
    def get_supported_event_types(self) -> List[RepositoryEventType]:
        """Get list of event types this handler supports"""
        pass


class RepositoryEventPublisher(QObject):
    """
    Publisher for repository events with standardized payload structure
    
    Provides methods to publish repository events with consistent naming
    and payload structure. Integrates with the existing event bus system.
    """
    
    # PyQt signals for repository events
    entity_created = pyqtSignal(str, str, dict)  # repository_type, entity_id, data
    entity_updated = pyqtSignal(str, str, dict, dict)  # repository_type, entity_id, new_data, old_data
    entity_deleted = pyqtSignal(str, str)  # repository_type, entity_id
    query_executed = pyqtSignal(str, dict, int)  # repository_type, query_info, result_count
    transaction_completed = pyqtSignal(str, str, bool)  # repository_type, transaction_id, success
    repository_error = pyqtSignal(str, str, str)  # repository_type, operation, error_message
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        super().__init__()
        self._event_bus = event_bus or get_event_bus()
        self._logger = logging.getLogger(__name__)
        
        # Event publishing configuration
        self._enable_qt_signals = True
        self._enable_event_bus = True
        self._enable_logging = True
        
        # Performance tracking
        self._event_counts: Dict[str, int] = {}
        self._last_event_time: Optional[datetime] = None
    
    def publish_entity_created(self, repository: IRepository, entity: BaseEntity, 
                              context: Optional[Dict[str, Any]] = None) -> None:
        """Publish entity created event"""
        payload = RepositoryEventPayload(
            repository_type=repository.__class__.__name__,
            repository_id=self._get_repository_id(repository),
            operation="create",
            entity_type=entity.__class__.__name__,
            entity_id=getattr(entity, 'id', None),
            entity_data=self._entity_to_dict(entity),
            context=context
        )
        
        self._publish_event(RepositoryEventType.ENTITY_CREATED, payload)
        
        # Emit Qt signal
        if self._enable_qt_signals:
            self.entity_created.emit(
                payload.repository_type,
                str(payload.entity_id),
                payload.entity_data or {}
            )
    
    def publish_entity_updated(self, repository: IRepository, entity: BaseEntity,
                              previous_data: Optional[Dict[str, Any]] = None,
                              context: Optional[Dict[str, Any]] = None) -> None:
        """Publish entity updated event"""
        payload = RepositoryEventPayload(
            repository_type=repository.__class__.__name__,
            repository_id=self._get_repository_id(repository),
            operation="update",
            entity_type=entity.__class__.__name__,
            entity_id=getattr(entity, 'id', None),
            entity_data=self._entity_to_dict(entity),
            previous_data=previous_data,
            context=context
        )
        
        self._publish_event(RepositoryEventType.ENTITY_UPDATED, payload)
        
        # Emit Qt signal
        if self._enable_qt_signals:
            self.entity_updated.emit(
                payload.repository_type,
                str(payload.entity_id),
                payload.entity_data or {},
                payload.previous_data or {}
            )
    
    def publish_entity_deleted(self, repository: IRepository, entity_id: EntityId,
                              entity_type: str, previous_data: Optional[Dict[str, Any]] = None,
                              context: Optional[Dict[str, Any]] = None) -> None:
        """Publish entity deleted event"""
        payload = RepositoryEventPayload(
            repository_type=repository.__class__.__name__,
            repository_id=self._get_repository_id(repository),
            operation="delete",
            entity_type=entity_type,
            entity_id=entity_id,
            previous_data=previous_data,
            context=context
        )
        
        self._publish_event(RepositoryEventType.ENTITY_DELETED, payload)
        
        # Emit Qt signal
        if self._enable_qt_signals:
            self.entity_deleted.emit(payload.repository_type, str(entity_id))
    
    def publish_query_executed(self, repository: IRepository, query_info: Dict[str, Any],
                              result_count: int, execution_time_ms: Optional[float] = None,
                              context: Optional[Dict[str, Any]] = None) -> None:
        """Publish query executed event"""
        payload = RepositoryEventPayload(
            repository_type=repository.__class__.__name__,
            repository_id=self._get_repository_id(repository),
            operation="query",
            query_info=query_info,
            affected_rows=result_count,
            execution_time_ms=execution_time_ms,
            context=context
        )
        
        self._publish_event(RepositoryEventType.QUERY_EXECUTED, payload)
        
        # Emit Qt signal
        if self._enable_qt_signals:
            self.query_executed.emit(payload.repository_type, query_info, result_count)
    
    def publish_transaction_started(self, repository: IRepository, transaction_id: str,
                                   context: Optional[Dict[str, Any]] = None) -> None:
        """Publish transaction started event"""
        payload = RepositoryEventPayload(
            repository_type=repository.__class__.__name__,
            repository_id=self._get_repository_id(repository),
            operation="transaction_start",
            transaction_id=transaction_id,
            context=context
        )
        
        self._publish_event(RepositoryEventType.TRANSACTION_STARTED, payload)
    
    def publish_transaction_completed(self, repository: IRepository, transaction_id: str,
                                     success: bool, execution_time_ms: Optional[float] = None,
                                     context: Optional[Dict[str, Any]] = None) -> None:
        """Publish transaction completed event"""
        event_type = RepositoryEventType.TRANSACTION_COMMITTED if success else RepositoryEventType.TRANSACTION_ROLLED_BACK
        
        payload = RepositoryEventPayload(
            repository_type=repository.__class__.__name__,
            repository_id=self._get_repository_id(repository),
            operation="transaction_complete",
            transaction_id=transaction_id,
            execution_time_ms=execution_time_ms,
            context=context
        )
        
        self._publish_event(event_type, payload)
        
        # Emit Qt signal
        if self._enable_qt_signals:
            self.transaction_completed.emit(payload.repository_type, transaction_id, success)
    
    def publish_repository_error(self, repository: IRepository, operation: str,
                                error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """Publish repository error event"""
        payload = RepositoryEventPayload(
            repository_type=repository.__class__.__name__,
            repository_id=self._get_repository_id(repository),
            operation=operation,
            error_type=error.__class__.__name__,
            error_message=str(error),
            error_details=self._extract_error_details(error),
            context=context
        )
        
        self._publish_event(RepositoryEventType.REPOSITORY_ERROR, payload)
        
        # Emit Qt signal
        if self._enable_qt_signals:
            self.repository_error.emit(payload.repository_type, operation, str(error))
    
    def publish_cache_event(self, repository: IRepository, operation: str,
                           cache_key: str, hit: bool, context: Optional[Dict[str, Any]] = None) -> None:
        """Publish cache-related event"""
        event_type = RepositoryEventType.CACHE_HIT if hit else RepositoryEventType.CACHE_MISS
        
        payload = RepositoryEventPayload(
            repository_type=repository.__class__.__name__,
            repository_id=self._get_repository_id(repository),
            operation=operation,
            cache_hit=hit,
            context={**(context or {}), 'cache_key': cache_key}
        )
        
        self._publish_event(event_type, payload)
    
    def publish_performance_event(self, repository: IRepository, operation: str,
                                 execution_time_ms: float, is_slow: bool = False,
                                 context: Optional[Dict[str, Any]] = None) -> None:
        """Publish performance-related event"""
        event_type = RepositoryEventType.OPERATION_SLOW if is_slow else RepositoryEventType.OPERATION_COMPLETED
        
        payload = RepositoryEventPayload(
            repository_type=repository.__class__.__name__,
            repository_id=self._get_repository_id(repository),
            operation=operation,
            execution_time_ms=execution_time_ms,
            context=context
        )
        
        self._publish_event(event_type, payload)
    
    def publish_bulk_operation(self, repository: IRepository, operation: str,
                              entity_type: str, entity_ids: List[EntityId],
                              affected_rows: int, execution_time_ms: Optional[float] = None,
                              context: Optional[Dict[str, Any]] = None) -> None:
        """Publish bulk operation event"""
        event_type_map = {
            'create': RepositoryEventType.ENTITIES_BULK_CREATED,
            'update': RepositoryEventType.ENTITIES_BULK_UPDATED,
            'delete': RepositoryEventType.ENTITIES_BULK_DELETED
        }
        
        event_type = event_type_map.get(operation, RepositoryEventType.QUERY_EXECUTED)
        
        payload = RepositoryEventPayload(
            repository_type=repository.__class__.__name__,
            repository_id=self._get_repository_id(repository),
            operation=f"bulk_{operation}",
            entity_type=entity_type,
            entity_ids=entity_ids,
            affected_rows=affected_rows,
            execution_time_ms=execution_time_ms,
            context=context
        )
        
        self._publish_event(event_type, payload)
    
    def _publish_event(self, event_type: RepositoryEventType, payload: RepositoryEventPayload) -> None:
        """Internal method to publish event through event bus"""
        try:
            # Update event tracking
            self._event_counts[event_type.value] = self._event_counts.get(event_type.value, 0) + 1
            self._last_event_time = datetime.now()
            
            # Log event if enabled
            if self._enable_logging:
                self._logger.debug(f"Publishing repository event: {event_type.value} from {payload.repository_type}")
            
            # Publish through event bus if enabled
            if self._enable_event_bus:
                # Convert to standard Event format
                event_data = {
                    'repository_event_type': event_type.value,
                    'payload': payload.__dict__
                }
                
                # Map to standard EventType
                standard_event_type = self._map_to_standard_event_type(event_type)
                
                publish_event(
                    event_type=standard_event_type,
                    source=f"Repository_{payload.repository_type}",
                    data=event_data
                )
            
        except Exception as e:
            self._logger.error(f"Error publishing repository event: {e}")
    
    def _map_to_standard_event_type(self, repo_event_type: RepositoryEventType) -> EventType:
        """Map repository event type to standard event type"""
        mapping = {
            RepositoryEventType.ENTITY_CREATED: EventType.DATA_UPDATED,
            RepositoryEventType.ENTITY_UPDATED: EventType.DATA_UPDATED,
            RepositoryEventType.ENTITY_DELETED: EventType.DATA_UPDATED,
            RepositoryEventType.QUERY_EXECUTED: EventType.DATA_UPDATED,
            RepositoryEventType.REPOSITORY_ERROR: EventType.ERROR_OCCURRED,
            RepositoryEventType.TRANSACTION_STARTED: EventType.STATE_CHANGED,
            RepositoryEventType.TRANSACTION_COMMITTED: EventType.STATE_CHANGED,
            RepositoryEventType.TRANSACTION_ROLLED_BACK: EventType.STATE_CHANGED,
        }
        
        return mapping.get(repo_event_type, EventType.DATA_UPDATED)
    
    def _get_repository_id(self, repository: IRepository) -> str:
        """Get unique identifier for repository"""
        return f"{repository.__class__.__name__}_{id(repository)}"
    
    def _entity_to_dict(self, entity: BaseEntity) -> Dict[str, Any]:
        """Convert entity to dictionary"""
        if hasattr(entity, 'to_dict'):
            return entity.to_dict()
        elif hasattr(entity, '__dict__'):
            return {k: v for k, v in entity.__dict__.items() if not k.startswith('_')}
        else:
            return {'id': getattr(entity, 'id', None)}
    
    def _extract_error_details(self, error: Exception) -> Dict[str, Any]:
        """Extract detailed error information"""
        details = {
            'error_class': error.__class__.__name__,
            'error_module': error.__class__.__module__,
        }
        
        # Add specific error attributes if available
        if hasattr(error, 'code'):
            details['error_code'] = error.code
        if hasattr(error, 'details'):
            details['error_details'] = error.details
        
        return details
    
    # Configuration methods
    def enable_qt_signals(self, enabled: bool = True) -> None:
        """Enable or disable Qt signal emission"""
        self._enable_qt_signals = enabled
    
    def enable_event_bus(self, enabled: bool = True) -> None:
        """Enable or disable event bus publishing"""
        self._enable_event_bus = enabled
    
    def enable_logging(self, enabled: bool = True) -> None:
        """Enable or disable event logging"""
        self._enable_logging = enabled
    
    def get_event_statistics(self) -> Dict[str, Any]:
        """Get event publishing statistics"""
        return {
            'event_counts': self._event_counts.copy(),
            'total_events': sum(self._event_counts.values()),
            'last_event_time': self._last_event_time.isoformat() if self._last_event_time else None,
            'qt_signals_enabled': self._enable_qt_signals,
            'event_bus_enabled': self._enable_event_bus,
            'logging_enabled': self._enable_logging
        }


class RepositoryEventSubscriber:
    """
    Subscriber for repository events with filtering and routing capabilities
    
    Provides methods to subscribe to specific repository events with
    filtering by repository type, entity type, operation, etc.
    """
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus or get_event_bus()
        self._logger = logging.getLogger(__name__)
        
        # Subscription tracking
        self._subscriptions: List[Callable] = []
        self._handlers: Dict[str, List[IRepositoryEventHandler]] = {}
        
        # Filtering configuration
        self._repository_filters: Dict[str, List[str]] = {}
        self._entity_filters: Dict[str, List[str]] = {}
        self._operation_filters: Dict[str, List[str]] = {}
    
    def subscribe_to_repository_events(self, handler: IRepositoryEventHandler,
                                     repository_types: Optional[List[str]] = None,
                                     entity_types: Optional[List[str]] = None,
                                     operations: Optional[List[str]] = None) -> None:
        """Subscribe to repository events with optional filtering"""
        
        # Store handler
        handler_id = f"{handler.__class__.__name__}_{id(handler)}"
        if handler_id not in self._handlers:
            self._handlers[handler_id] = []
        self._handlers[handler_id].append(handler)
        
        # Store filters
        if repository_types:
            self._repository_filters[handler_id] = repository_types
        if entity_types:
            self._entity_filters[handler_id] = entity_types
        if operations:
            self._operation_filters[handler_id] = operations
        
        # Subscribe to event bus
        def event_callback(event: Event):
            self._handle_event(event, handler, handler_id)
        
        self._event_bus.subscribe(EventType.DATA_UPDATED, event_callback)
        self._event_bus.subscribe(EventType.ERROR_OCCURRED, event_callback)
        self._event_bus.subscribe(EventType.STATE_CHANGED, event_callback)
        
        self._subscriptions.append(event_callback)
        
        self._logger.debug(f"Subscribed repository event handler: {handler_id}")
    
    def subscribe_to_entity_events(self, entity_type: str, 
                                  callback: Callable[[RepositoryEventType, RepositoryEventPayload], None]) -> None:
        """Subscribe to events for a specific entity type"""
        
        def event_callback(event: Event):
            if self._is_repository_event(event):
                payload = self._extract_repository_payload(event)
                if payload and payload.entity_type == entity_type:
                    repo_event_type = self._extract_repository_event_type(event)
                    if repo_event_type:
                        callback(repo_event_type, payload)
        
        self._event_bus.subscribe(EventType.DATA_UPDATED, event_callback)
        self._subscriptions.append(event_callback)
    
    def subscribe_to_repository_type(self, repository_type: str,
                                   callback: Callable[[RepositoryEventType, RepositoryEventPayload], None]) -> None:
        """Subscribe to events from a specific repository type"""
        
        def event_callback(event: Event):
            if self._is_repository_event(event):
                payload = self._extract_repository_payload(event)
                if payload and payload.repository_type == repository_type:
                    repo_event_type = self._extract_repository_event_type(event)
                    if repo_event_type:
                        callback(repo_event_type, payload)
        
        self._event_bus.subscribe(EventType.DATA_UPDATED, event_callback)
        self._event_bus.subscribe(EventType.ERROR_OCCURRED, event_callback)
        self._event_bus.subscribe(EventType.STATE_CHANGED, event_callback)
        self._subscriptions.append(event_callback)
    
    def _handle_event(self, event: Event, handler: IRepositoryEventHandler, handler_id: str) -> None:
        """Handle incoming event and route to appropriate handler"""
        try:
            if not self._is_repository_event(event):
                return
            
            payload = self._extract_repository_payload(event)
            if not payload:
                return
            
            # Apply filters
            if not self._passes_filters(payload, handler_id):
                return
            
            # Extract repository event type
            repo_event_type = self._extract_repository_event_type(event)
            if not repo_event_type:
                return
            
            # Check if handler supports this event type
            supported_types = handler.get_supported_event_types()
            if repo_event_type not in supported_types:
                return
            
            # Call handler
            handler.handle_repository_event(repo_event_type, payload)
            
        except Exception as e:
            self._logger.error(f"Error handling repository event in {handler_id}: {e}")
    
    def _is_repository_event(self, event: Event) -> bool:
        """Check if event is a repository event"""
        return (event.data and 
                'repository_event_type' in event.data and 
                'payload' in event.data)
    
    def _extract_repository_payload(self, event: Event) -> Optional[RepositoryEventPayload]:
        """Extract repository payload from event"""
        try:
            if not event.data or 'payload' not in event.data:
                return None
            
            payload_data = event.data['payload']
            return RepositoryEventPayload(**payload_data)
            
        except Exception as e:
            self._logger.error(f"Error extracting repository payload: {e}")
            return None
    
    def _extract_repository_event_type(self, event: Event) -> Optional[RepositoryEventType]:
        """Extract repository event type from event"""
        try:
            if not event.data or 'repository_event_type' not in event.data:
                return None
            
            event_type_str = event.data['repository_event_type']
            return RepositoryEventType(event_type_str)
            
        except Exception as e:
            self._logger.error(f"Error extracting repository event type: {e}")
            return None
    
    def _passes_filters(self, payload: RepositoryEventPayload, handler_id: str) -> bool:
        """Check if payload passes all filters for handler"""
        
        # Repository type filter
        if handler_id in self._repository_filters:
            if payload.repository_type not in self._repository_filters[handler_id]:
                return False
        
        # Entity type filter
        if handler_id in self._entity_filters:
            if not payload.entity_type or payload.entity_type not in self._entity_filters[handler_id]:
                return False
        
        # Operation filter
        if handler_id in self._operation_filters:
            if payload.operation not in self._operation_filters[handler_id]:
                return False
        
        return True
    
    def unsubscribe_all(self) -> None:
        """Unsubscribe from all repository events"""
        for callback in self._subscriptions:
            self._event_bus.unsubscribe(EventType.DATA_UPDATED, callback)
            self._event_bus.unsubscribe(EventType.ERROR_OCCURRED, callback)
            self._event_bus.unsubscribe(EventType.STATE_CHANGED, callback)
        
        self._subscriptions.clear()
        self._handlers.clear()
        self._repository_filters.clear()
        self._entity_filters.clear()
        self._operation_filters.clear()
        
        self._logger.debug("Unsubscribed from all repository events")


class RepositoryEventManager:
    """
    Central manager for repository event publishing and subscription
    
    Provides a unified interface for repository event management,
    combining publisher and subscriber functionality.
    """
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus or get_event_bus()
        self._publisher = RepositoryEventPublisher(self._event_bus)
        self._subscriber = RepositoryEventSubscriber(self._event_bus)
        self._logger = logging.getLogger(__name__)
        
        # Repository registration
        self._registered_repositories: Dict[str, IRepository] = {}
        
        # Event middleware
        self._middleware: List[Callable[[RepositoryEventType, RepositoryEventPayload], None]] = []
    
    def register_repository(self, repository: IRepository, repository_id: Optional[str] = None) -> str:
        """Register a repository for event publishing"""
        if repository_id is None:
            repository_id = f"{repository.__class__.__name__}_{id(repository)}"
        
        self._registered_repositories[repository_id] = repository
        self._logger.info(f"Registered repository: {repository_id}")
        
        return repository_id
    
    def unregister_repository(self, repository_id: str) -> bool:
        """Unregister a repository"""
        if repository_id in self._registered_repositories:
            del self._registered_repositories[repository_id]
            self._logger.info(f"Unregistered repository: {repository_id}")
            return True
        return False
    
    def get_publisher(self) -> RepositoryEventPublisher:
        """Get the event publisher"""
        return self._publisher
    
    def get_subscriber(self) -> RepositoryEventSubscriber:
        """Get the event subscriber"""
        return self._subscriber
    
    def add_middleware(self, middleware: Callable[[RepositoryEventType, RepositoryEventPayload], None]) -> None:
        """Add event middleware for processing events"""
        self._middleware.append(middleware)
    
    def remove_middleware(self, middleware: Callable[[RepositoryEventType, RepositoryEventPayload], None]) -> bool:
        """Remove event middleware"""
        if middleware in self._middleware:
            self._middleware.remove(middleware)
            return True
        return False
    
    def get_registered_repositories(self) -> Dict[str, str]:
        """Get list of registered repositories"""
        return {repo_id: repo.__class__.__name__ for repo_id, repo in self._registered_repositories.items()}
    
    def get_event_statistics(self) -> Dict[str, Any]:
        """Get comprehensive event statistics"""
        return {
            'publisher_stats': self._publisher.get_event_statistics(),
            'registered_repositories': self.get_registered_repositories(),
            'middleware_count': len(self._middleware)
        }


# Global repository event manager instance
_repository_event_manager: Optional[RepositoryEventManager] = None


def get_repository_event_manager() -> RepositoryEventManager:
    """Get the global repository event manager instance"""
    global _repository_event_manager
    if _repository_event_manager is None:
        _repository_event_manager = RepositoryEventManager()
    return _repository_event_manager


def publish_repository_event(event_type: RepositoryEventType, repository: IRepository,
                           **kwargs) -> None:
    """Convenience function to publish repository events"""
    manager = get_repository_event_manager()
    publisher = manager.get_publisher()
    
    # Route to appropriate publisher method based on event type
    if event_type == RepositoryEventType.ENTITY_CREATED:
        entity = kwargs.get('entity')
        context = kwargs.get('context')
        if entity:
            publisher.publish_entity_created(repository, entity, context)
    
    elif event_type == RepositoryEventType.ENTITY_UPDATED:
        entity = kwargs.get('entity')
        previous_data = kwargs.get('previous_data')
        context = kwargs.get('context')
        if entity:
            publisher.publish_entity_updated(repository, entity, previous_data, context)
    
    elif event_type == RepositoryEventType.ENTITY_DELETED:
        entity_id = kwargs.get('entity_id')
        entity_type = kwargs.get('entity_type')
        previous_data = kwargs.get('previous_data')
        context = kwargs.get('context')
        if entity_id and entity_type:
            publisher.publish_entity_deleted(repository, entity_id, entity_type, previous_data, context)
    
    elif event_type == RepositoryEventType.REPOSITORY_ERROR:
        operation = kwargs.get('operation', 'unknown')
        error = kwargs.get('error')
        context = kwargs.get('context')
        if error:
            publisher.publish_repository_error(repository, operation, error, context)


def subscribe_to_repository_events(handler: IRepositoryEventHandler, **filters) -> None:
    """Convenience function to subscribe to repository events"""
    manager = get_repository_event_manager()
    subscriber = manager.get_subscriber()
    
    repository_types = filters.get('repository_types')
    entity_types = filters.get('entity_types')
    operations = filters.get('operations')
    
    subscriber.subscribe_to_repository_events(handler, repository_types, entity_types, operations) 