"""
Event Proxy System for UI v1.2.1 to v2.0 Architecture Bridge

This module contains event proxy implementations that translate between
legacy PyQt signals and the new v2.0 Event System, ensuring seamless
communication between old and new components.
"""

import logging
import weakref
from typing import Any, Dict, List, Optional, Callable, Set, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from threading import Lock, RLock
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

# Import v2.0 architecture components
from core.event_system import EventBus, EventType, Event
from .interfaces import IEventProxyAdapter


class EventTranslationDirection(Enum):
    """Direction of event translation"""
    LEGACY_TO_V2 = "legacy_to_v2"
    V2_TO_LEGACY = "v2_to_legacy"
    BIDIRECTIONAL = "bidirectional"


class EventPriority(Enum):
    """Priority levels for event processing"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class EventMapping:
    """Mapping configuration between legacy and v2.0 events"""
    legacy_event_name: str
    v2_event_type: EventType
    direction: EventTranslationDirection
    priority: EventPriority = EventPriority.NORMAL
    data_transformer: Optional[Callable[[Any], Any]] = None
    condition: Optional[Callable[[Any], bool]] = None
    description: str = ""


@dataclass
class EventRegistration:
    """Registration information for event handlers"""
    handler_id: str
    event_name: str
    handler: Callable[[Any], None]
    is_legacy: bool
    priority: EventPriority
    created_at: datetime = field(default_factory=datetime.now)
    call_count: int = 0
    last_called: Optional[datetime] = None
    is_active: bool = True


class EventBridgeCoordinator(QObject):
    """
    Central coordinator that manages all event bridging between
    legacy and v2.0 systems.
    """
    
    # Legacy-style signals for backward compatibility
    event_translated = pyqtSignal(str, object)  # event_name, data
    translation_error = pyqtSignal(str, str)    # event_name, error_message
    bridge_status_changed = pyqtSignal(bool)    # is_active
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self._lock = RLock()
        
        # Core components
        self._event_bus: Optional[EventBus] = None
        self._event_mappings: Dict[str, EventMapping] = {}
        self._legacy_handlers: Dict[str, List[EventRegistration]] = {}
        self._v2_handlers: Dict[EventType, List[EventRegistration]] = {}
        
        # Event translation cache and metrics
        self._translation_cache: Dict[str, Any] = {}
        self._event_metrics: Dict[str, int] = {
            "legacy_events_processed": 0,
            "v2_events_processed": 0,
            "translation_errors": 0,
            "cache_hits": 0
        }
        
        # Configuration
        self._is_active = False
        self._enable_caching = True
        self._max_cache_size = 1000
        self._debug_mode = False
        
        # Set up default event mappings
        self._setup_default_mappings()
    
    def initialize(self, event_bus: EventBus) -> bool:
        """
        Initialize the coordinator with the v2.0 event bus.
        
        Args:
            event_bus: The v2.0 Event Bus instance
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            with self._lock:
                self._event_bus = event_bus
                self._setup_v2_event_handlers()
                self._is_active = True
                
                self.logger.info("Event Bridge Coordinator initialized successfully")
                self.bridge_status_changed.emit(True)
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to initialize Event Bridge Coordinator: {e}")
            return False
    
    def shutdown(self) -> bool:
        """
        Shutdown the coordinator gracefully.
        
        Returns:
            True if shutdown successful, False otherwise
        """
        try:
            with self._lock:
                self._is_active = False
                self._clear_all_handlers()
                self._event_bus = None
                
                self.logger.info("Event Bridge Coordinator shutdown successfully")
                self.bridge_status_changed.emit(False)
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to shutdown Event Bridge Coordinator: {e}")
            return False
    
    def register_event_mapping(self, mapping: EventMapping) -> bool:
        """
        Register a mapping between legacy and v2.0 events.
        
        Args:
            mapping: Event mapping configuration
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            with self._lock:
                self._event_mappings[mapping.legacy_event_name] = mapping
                self.logger.debug(f"Registered event mapping: {mapping.legacy_event_name} <-> {mapping.v2_event_type}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to register event mapping: {e}")
            return False
    
    def emit_legacy_event(self, event_name: str, data: Any = None) -> bool:
        """
        Emit an event in legacy format and translate it to v2.0 if needed.
        
        Args:
            event_name: Name of the legacy event
            data: Event data
            
        Returns:
            True if event emitted successfully, False otherwise
        """
        try:
            if not self._is_active:
                self.logger.warning("Bridge coordinator is not active")
                return False
            
            with self._lock:
                # Process legacy event handlers
                self._process_legacy_event(event_name, data)
                
                # Translate to v2.0 if mapping exists
                if event_name in self._event_mappings:
                    mapping = self._event_mappings[event_name]
                    if mapping.direction in [EventTranslationDirection.LEGACY_TO_V2, EventTranslationDirection.BIDIRECTIONAL]:
                        self._translate_legacy_to_v2(event_name, data, mapping)
                
                self._event_metrics["legacy_events_processed"] += 1
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to emit legacy event '{event_name}': {e}")
            self._event_metrics["translation_errors"] += 1
            self.translation_error.emit(event_name, str(e))
            return False
    
    def emit_v2_event(self, event_type: EventType, data: Any = None) -> bool:
        """
        Emit an event in v2.0 format and translate it to legacy if needed.
        
        Args:
            event_type: v2.0 event type
            data: Event data
            
        Returns:
            True if event emitted successfully, False otherwise
        """
        try:
            if not self._is_active or not self._event_bus:
                self.logger.warning("Bridge coordinator is not active or event bus not available")
                return False
            
            with self._lock:
                # Emit v2.0 event
                event = Event(event_type=event_type, data=data)
                self._event_bus.emit(event)
                
                # Translate to legacy if mapping exists
                for mapping in self._event_mappings.values():
                    if (mapping.v2_event_type == event_type and 
                        mapping.direction in [EventTranslationDirection.V2_TO_LEGACY, EventTranslationDirection.BIDIRECTIONAL]):
                        self._translate_v2_to_legacy(event_type, data, mapping)
                
                self._event_metrics["v2_events_processed"] += 1
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to emit v2.0 event '{event_type}': {e}")
            self._event_metrics["translation_errors"] += 1
            return False
    
    def register_legacy_handler(self, event_name: str, handler: Callable[[Any], None], 
                               priority: EventPriority = EventPriority.NORMAL) -> str:
        """
        Register a legacy event handler.
        
        Args:
            event_name: Name of the legacy event
            handler: Event handler function
            priority: Handler priority
            
        Returns:
            Handler ID if registration successful, empty string otherwise
        """
        try:
            with self._lock:
                handler_id = f"legacy_{event_name}_{id(handler)}_{datetime.now().timestamp()}"
                registration = EventRegistration(
                    handler_id=handler_id,
                    event_name=event_name,
                    handler=handler,
                    is_legacy=True,
                    priority=priority
                )
                
                if event_name not in self._legacy_handlers:
                    self._legacy_handlers[event_name] = []
                
                self._legacy_handlers[event_name].append(registration)
                # Sort by priority (highest first)
                self._legacy_handlers[event_name].sort(key=lambda x: x.priority.value, reverse=True)
                
                self.logger.debug(f"Registered legacy handler for '{event_name}': {handler_id}")
                return handler_id
                
        except Exception as e:
            self.logger.error(f"Failed to register legacy handler: {e}")
            return ""
    
    def register_v2_handler(self, event_type: EventType, handler: Callable[[Any], None],
                           priority: EventPriority = EventPriority.NORMAL) -> str:
        """
        Register a v2.0 event handler.
        
        Args:
            event_type: v2.0 event type
            handler: Event handler function
            priority: Handler priority
            
        Returns:
            Handler ID if registration successful, empty string otherwise
        """
        try:
            with self._lock:
                handler_id = f"v2_{event_type.value}_{id(handler)}_{datetime.now().timestamp()}"
                registration = EventRegistration(
                    handler_id=handler_id,
                    event_name=event_type.value,
                    handler=handler,
                    is_legacy=False,
                    priority=priority
                )
                
                if event_type not in self._v2_handlers:
                    self._v2_handlers[event_type] = []
                
                self._v2_handlers[event_type].append(registration)
                # Sort by priority (highest first)
                self._v2_handlers[event_type].sort(key=lambda x: x.priority.value, reverse=True)
                
                self.logger.debug(f"Registered v2.0 handler for '{event_type}': {handler_id}")
                return handler_id
                
        except Exception as e:
            self.logger.error(f"Failed to register v2.0 handler: {e}")
            return ""
    
    def unregister_handler(self, handler_id: str) -> bool:
        """
        Unregister an event handler.
        
        Args:
            handler_id: ID of the handler to unregister
            
        Returns:
            True if unregistration successful, False otherwise
        """
        try:
            with self._lock:
                # Search in legacy handlers
                for event_name, handlers in self._legacy_handlers.items():
                    for i, handler in enumerate(handlers):
                        if handler.handler_id == handler_id:
                            del handlers[i]
                            self.logger.debug(f"Unregistered legacy handler: {handler_id}")
                            return True
                
                # Search in v2.0 handlers
                for event_type, handlers in self._v2_handlers.items():
                    for i, handler in enumerate(handlers):
                        if handler.handler_id == handler_id:
                            del handlers[i]
                            self.logger.debug(f"Unregistered v2.0 handler: {handler_id}")
                            return True
                
                self.logger.warning(f"Handler not found: {handler_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to unregister handler: {e}")
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get event processing metrics"""
        with self._lock:
            return {
                **self._event_metrics,
                "active_legacy_handlers": sum(len(handlers) for handlers in self._legacy_handlers.values()),
                "active_v2_handlers": sum(len(handlers) for handlers in self._v2_handlers.values()),
                "event_mappings": len(self._event_mappings),
                "cache_size": len(self._translation_cache),
                "is_active": self._is_active
            }
    
    def clear_cache(self) -> None:
        """Clear the event translation cache"""
        with self._lock:
            self._translation_cache.clear()
            self.logger.debug("Event translation cache cleared")
    
    def set_debug_mode(self, enabled: bool) -> None:
        """Enable or disable debug mode"""
        with self._lock:
            self._debug_mode = enabled
            if enabled:
                self.logger.setLevel(logging.DEBUG)
            self.logger.info(f"Debug mode {'enabled' if enabled else 'disabled'}")
    
    def _setup_default_mappings(self) -> None:
        """Set up default event mappings for common UI events"""
        default_mappings = [
            # Video-related events
            EventMapping(
                legacy_event_name="video_url_changed",
                v2_event_type=EventType.CONTENT_URL_ENTERED,
                direction=EventTranslationDirection.BIDIRECTIONAL,
                description="Video URL input events"
            ),
            EventMapping(
                legacy_event_name="video_info_updated",
                v2_event_type=EventType.CONTENT_METADATA_UPDATED,
                direction=EventTranslationDirection.BIDIRECTIONAL,
                description="Video information updates"
            ),
            EventMapping(
                legacy_event_name="download_requested",
                v2_event_type=EventType.DOWNLOAD_REQUESTED,
                direction=EventTranslationDirection.BIDIRECTIONAL,
                description="Download request events"
            ),
            
            # Download progress events
            EventMapping(
                legacy_event_name="download_progress_updated",
                v2_event_type=EventType.DOWNLOAD_PROGRESS_UPDATED,
                direction=EventTranslationDirection.BIDIRECTIONAL,
                description="Download progress updates"
            ),
            EventMapping(
                legacy_event_name="download_completed",
                v2_event_type=EventType.DOWNLOAD_COMPLETED,
                direction=EventTranslationDirection.BIDIRECTIONAL,
                description="Download completion events"
            ),
            EventMapping(
                legacy_event_name="download_failed",
                v2_event_type=EventType.DOWNLOAD_FAILED,
                direction=EventTranslationDirection.BIDIRECTIONAL,
                description="Download failure events"
            ),
            
            # UI events
            EventMapping(
                legacy_event_name="theme_changed",
                v2_event_type=EventType.CONFIGURATION_UPDATED,
                direction=EventTranslationDirection.BIDIRECTIONAL,
                description="Theme change events",
                data_transformer=lambda data: {"section": "ui", "key": "theme", "value": data}
            ),
            EventMapping(
                legacy_event_name="language_changed",
                v2_event_type=EventType.CONFIGURATION_UPDATED,
                direction=EventTranslationDirection.BIDIRECTIONAL,
                description="Language change events",
                data_transformer=lambda data: {"section": "ui", "key": "language", "value": data}
            ),
            
            # Error events
            EventMapping(
                legacy_event_name="error_occurred",
                v2_event_type=EventType.ERROR_OCCURRED,
                direction=EventTranslationDirection.BIDIRECTIONAL,
                description="Error events"
            )
        ]
        
        for mapping in default_mappings:
            self._event_mappings[mapping.legacy_event_name] = mapping
        
        self.logger.info(f"Set up {len(default_mappings)} default event mappings")
    
    def _setup_v2_event_handlers(self) -> None:
        """Set up handlers for v2.0 events that need translation to legacy"""
        if not self._event_bus:
            return
        
        # Subscribe to all relevant v2.0 events
        v2_event_types = {mapping.v2_event_type for mapping in self._event_mappings.values()}
        
        for event_type in v2_event_types:
            self._event_bus.subscribe(event_type, self._handle_v2_event)
        
        self.logger.debug(f"Set up v2.0 event handlers for {len(v2_event_types)} event types")
    
    def _handle_v2_event(self, event: Event) -> None:
        """Handle v2.0 events and translate to legacy if needed"""
        try:
            # Find mappings for this event type
            for mapping in self._event_mappings.values():
                if (mapping.v2_event_type == event.event_type and 
                    mapping.direction in [EventTranslationDirection.V2_TO_LEGACY, EventTranslationDirection.BIDIRECTIONAL]):
                    self._translate_v2_to_legacy(event.event_type, event.data, mapping)
                    
        except Exception as e:
            self.logger.error(f"Failed to handle v2.0 event {event.event_type}: {e}")
    
    def _process_legacy_event(self, event_name: str, data: Any) -> None:
        """Process legacy event with registered handlers"""
        if event_name not in self._legacy_handlers:
            return
        
        handlers = self._legacy_handlers[event_name]
        for registration in handlers:
            if not registration.is_active:
                continue
            
            try:
                registration.handler(data)
                registration.call_count += 1
                registration.last_called = datetime.now()
                
                if self._debug_mode:
                    self.logger.debug(f"Called legacy handler for '{event_name}': {registration.handler_id}")
                    
            except Exception as e:
                self.logger.error(f"Legacy handler failed for '{event_name}': {e}")
    
    def _translate_legacy_to_v2(self, event_name: str, data: Any, mapping: EventMapping) -> None:
        """Translate legacy event to v2.0 format and emit"""
        try:
            # Apply condition check if specified
            if mapping.condition and not mapping.condition(data):
                return
            
            # Transform data if transformer specified
            transformed_data = data
            if mapping.data_transformer:
                transformed_data = mapping.data_transformer(data)
            
            # Cache the translation if enabled
            if self._enable_caching:
                cache_key = f"{event_name}_{hash(str(data))}"
                if cache_key in self._translation_cache:
                    transformed_data = self._translation_cache[cache_key]
                    self._event_metrics["cache_hits"] += 1
                else:
                    self._translation_cache[cache_key] = transformed_data
                    # Limit cache size
                    if len(self._translation_cache) > self._max_cache_size:
                        # Remove oldest entries
                        oldest_keys = list(self._translation_cache.keys())[:100]
                        for key in oldest_keys:
                            del self._translation_cache[key]
            
            # Emit v2.0 event
            if self._event_bus:
                event = Event(event_type=mapping.v2_event_type, data=transformed_data)
                self._event_bus.emit(event)
                
                if self._debug_mode:
                    self.logger.debug(f"Translated legacy event '{event_name}' to v2.0 '{mapping.v2_event_type}'")
            
            self.event_translated.emit(event_name, transformed_data)
            
        except Exception as e:
            self.logger.error(f"Failed to translate legacy event '{event_name}' to v2.0: {e}")
            self.translation_error.emit(event_name, str(e))
    
    def _translate_v2_to_legacy(self, event_type: EventType, data: Any, mapping: EventMapping) -> None:
        """Translate v2.0 event to legacy format and emit"""
        try:
            # Apply condition check if specified
            if mapping.condition and not mapping.condition(data):
                return
            
            # Transform data if transformer specified
            transformed_data = data
            if mapping.data_transformer:
                # For v2 to legacy, we might need inverse transformation
                # This is a simplified approach - in practice, you might want
                # separate transformers for each direction
                transformed_data = mapping.data_transformer(data)
            
            # Process legacy event
            self._process_legacy_event(mapping.legacy_event_name, transformed_data)
            
            if self._debug_mode:
                self.logger.debug(f"Translated v2.0 event '{event_type}' to legacy '{mapping.legacy_event_name}'")
            
            self.event_translated.emit(mapping.legacy_event_name, transformed_data)
            
        except Exception as e:
            self.logger.error(f"Failed to translate v2.0 event '{event_type}' to legacy: {e}")
            self.translation_error.emit(mapping.legacy_event_name, str(e))
    
    def _clear_all_handlers(self) -> None:
        """Clear all registered handlers"""
        self._legacy_handlers.clear()
        self._v2_handlers.clear()
        self.logger.debug("Cleared all event handlers")


class EventTranslator(IEventProxyAdapter):
    """
    Event translator that provides a simplified interface to the
    Event Bridge Coordinator for specific component adapters.
    """
    
    def __init__(self, coordinator: EventBridgeCoordinator):
        self.coordinator = coordinator
        self.logger = logging.getLogger(__name__)
        self._registered_handlers: Set[str] = set()
    
    def register_legacy_handler(self, event_name: str, handler: Callable[[Any], None]) -> bool:
        """Register a legacy event handler"""
        try:
            handler_id = self.coordinator.register_legacy_handler(event_name, handler)
            if handler_id:
                self._registered_handlers.add(handler_id)
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to register legacy handler: {e}")
            return False
    
    def register_v2_handler(self, event_type: EventType, handler: Callable[[Any], None]) -> bool:
        """Register a v2.0 event handler"""
        try:
            handler_id = self.coordinator.register_v2_handler(event_type, handler)
            if handler_id:
                self._registered_handlers.add(handler_id)
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to register v2.0 handler: {e}")
            return False
    
    def translate_event(self, source_event: Any, target_format: str) -> Optional[Any]:
        """Translate an event between legacy and v2.0 formats"""
        # This is a simplified implementation
        # In practice, you might want more sophisticated translation logic
        try:
            if target_format == "v2":
                # Legacy to v2.0 translation
                return source_event
            elif target_format == "legacy":
                # v2.0 to legacy translation
                return source_event
            else:
                self.logger.error(f"Unknown target format: {target_format}")
                return None
        except Exception as e:
            self.logger.error(f"Event translation failed: {e}")
            return None
    
    def emit_legacy_event(self, event_name: str, data: Any) -> bool:
        """Emit an event in legacy format"""
        return self.coordinator.emit_legacy_event(event_name, data)
    
    def emit_v2_event(self, event_type: EventType, data: Any) -> bool:
        """Emit an event in v2.0 format"""
        return self.coordinator.emit_v2_event(event_type, data)
    
    def cleanup(self) -> None:
        """Clean up registered handlers"""
        for handler_id in self._registered_handlers:
            self.coordinator.unregister_handler(handler_id)
        self._registered_handlers.clear()
        self.logger.debug("Event translator cleaned up")


class LegacyEventHandler(QObject):
    """
    Helper class for handling legacy PyQt signals in a consistent way.
    
    This class provides a standardized interface for connecting to
    legacy UI component signals and translating them to the bridge system.
    """
    
    def __init__(self, coordinator: EventBridgeCoordinator):
        super().__init__()
        self.coordinator = coordinator
        self.logger = logging.getLogger(__name__)
        self._connections: List[Any] = []
    
    def connect_signal(self, signal, event_name: str, 
                      data_extractor: Optional[Callable[[Any], Any]] = None) -> bool:
        """
        Connect a PyQt signal to the event bridge system.
        
        Args:
            signal: PyQt signal to connect
            event_name: Name of the event to emit
            data_extractor: Optional function to extract data from signal arguments
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            def signal_handler(*args):
                try:
                    # Extract data using the provided extractor or use args directly
                    data = data_extractor(*args) if data_extractor else args[0] if args else None
                    self.coordinator.emit_legacy_event(event_name, data)
                except Exception as e:
                    self.logger.error(f"Signal handler failed for '{event_name}': {e}")
            
            # Connect the signal
            connection = signal.connect(signal_handler)
            self._connections.append((signal, signal_handler))
            
            self.logger.debug(f"Connected signal to event '{event_name}'")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect signal for '{event_name}': {e}")
            return False
    
    def disconnect_all(self) -> None:
        """Disconnect all signal connections"""
        for signal, handler in self._connections:
            try:
                signal.disconnect(handler)
            except Exception as e:
                self.logger.error(f"Failed to disconnect signal: {e}")
        
        self._connections.clear()
        self.logger.debug("Disconnected all signals")


# Global coordinator instance
_global_coordinator: Optional[EventBridgeCoordinator] = None
_coordinator_lock = Lock()


def get_global_coordinator() -> EventBridgeCoordinator:
    """Get the global Event Bridge Coordinator instance"""
    global _global_coordinator
    with _coordinator_lock:
        if _global_coordinator is None:
            _global_coordinator = EventBridgeCoordinator()
        return _global_coordinator


def create_event_translator() -> EventTranslator:
    """Create an Event Translator instance"""
    coordinator = get_global_coordinator()
    return EventTranslator(coordinator)


def create_legacy_handler() -> LegacyEventHandler:
    """Create a Legacy Event Handler instance"""
    coordinator = get_global_coordinator()
    return LegacyEventHandler(coordinator) 