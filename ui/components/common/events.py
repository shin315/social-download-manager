"""
Component Event System

Event-driven communication system for components to reduce coupling
and enable loose communication between UI components.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Callable, List, Optional
from PyQt6.QtCore import QObject, pyqtSignal
from enum import Enum

class EventType(Enum):
    """Standard event types for component communication"""
    
    # State events
    STATE_CHANGED = "state_changed"
    STATE_RESET = "state_reset"
    
    # Data events
    DATA_LOADED = "data_loaded"
    DATA_UPDATED = "data_updated"
    DATA_CLEARED = "data_cleared"
    
    # Selection events
    SELECTION_CHANGED = "selection_changed"
    SELECT_ALL = "select_all"
    SELECT_NONE = "select_none"
    
    # Filter events
    FILTER_APPLIED = "filter_applied"
    FILTER_CLEARED = "filter_cleared"
    FILTER_CHANGED = "filter_changed"
    
    # Sort events
    SORT_CHANGED = "sort_changed"
    
    # UI events
    LANGUAGE_CHANGED = "language_changed"
    THEME_CHANGED = "theme_changed"
    
    # Progress events
    PROGRESS_UPDATED = "progress_updated"
    PROGRESS_COMPLETED = "progress_completed"
    PROGRESS_FAILED = "progress_failed"
    
    # Component lifecycle events
    COMPONENT_INITIALIZED = "component_initialized"
    COMPONENT_DESTROYED = "component_destroyed"
    
    # Tab lifecycle events
    TAB_ACTIVATED = "tab_activated"
    TAB_DEACTIVATED = "tab_deactivated"
    TAB_INITIALIZED = "tab_initialized"
    TAB_CLEANUP = "tab_cleanup"
    TAB_DATA_CHANGED = "tab_data_changed"
    TAB_VALIDATION_CHANGED = "tab_validation_changed"
    
    # Video-specific events
    VIDEO_INFO_RECEIVED = "video_info_received"
    VIDEO_DOWNLOAD_STARTED = "video_download_started"
    VIDEO_DOWNLOAD_PROGRESS = "video_download_progress"
    VIDEO_DOWNLOAD_COMPLETED = "video_download_completed"
    VIDEO_DOWNLOAD_FAILED = "video_download_failed"

@dataclass
class ComponentEvent:
    """Event data structure for component communication"""
    
    event_type: EventType
    source_component: str
    data: Dict[str, Any]
    timestamp: datetime = None
    target_component: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class ComponentBus(QObject):
    """Event bus for component communication"""
    
    # Global event signal
    event_emitted = pyqtSignal(ComponentEvent)
    
    def __init__(self):
        super().__init__()
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._component_subscribers: Dict[str, List[Callable]] = {}
        
    def emit_event(self, event_type: EventType, source_component: str, 
                   data: Dict[str, Any], target_component: Optional[str] = None):
        """Emit an event through the bus"""
        event = ComponentEvent(
            event_type=event_type,
            source_component=source_component,
            data=data,
            target_component=target_component
        )
        
        # Emit PyQt signal
        self.event_emitted.emit(event)
        
        # Call direct subscribers
        self._notify_subscribers(event)
        
    def subscribe(self, event_type: EventType, callback: Callable[[ComponentEvent], None]):
        """Subscribe to events of a specific type"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        
    def unsubscribe(self, event_type: EventType, callback: Callable[[ComponentEvent], None]):
        """Unsubscribe from events of a specific type"""
        if event_type in self._subscribers:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)
                
    def subscribe_component(self, component_name: str, callback: Callable[[ComponentEvent], None]):
        """Subscribe to all events from a specific component"""
        if component_name not in self._component_subscribers:
            self._component_subscribers[component_name] = []
        self._component_subscribers[component_name].append(callback)
        
    def unsubscribe_component(self, component_name: str, callback: Callable[[ComponentEvent], None]):
        """Unsubscribe from events from a specific component"""
        if component_name in self._component_subscribers:
            if callback in self._component_subscribers[component_name]:
                self._component_subscribers[component_name].remove(callback)
    
    def _notify_subscribers(self, event: ComponentEvent):
        """Notify all relevant subscribers"""
        # Notify event type subscribers
        if event.event_type in self._subscribers:
            for callback in self._subscribers[event.event_type]:
                try:
                    callback(event)
                except Exception as e:
                    print(f"Error in event callback: {e}")
        
        # Notify component subscribers
        if event.source_component in self._component_subscribers:
            for callback in self._component_subscribers[event.source_component]:
                try:
                    callback(event)
                except Exception as e:
                    print(f"Error in component event callback: {e}")

# Global event bus instance
_global_event_bus = ComponentBus()

def get_event_bus() -> ComponentBus:
    """Get the global event bus instance"""
    return _global_event_bus

class EventEmitter:
    """Mixin class for components that emit events"""
    
    def __init__(self, component_name: str):
        self.component_name = component_name
        self.event_bus = get_event_bus()
    
    def emit_event(self, event_type: EventType, data: Dict[str, Any], 
                   target_component: Optional[str] = None):
        """Emit an event from this component"""
        self.event_bus.emit_event(
            event_type=event_type,
            source_component=self.component_name,
            data=data,
            target_component=target_component
        )
    
    def emit_state_changed(self, state_data: Dict[str, Any]):
        """Convenience method to emit state change events"""
        self.emit_event(EventType.STATE_CHANGED, state_data)
    
    def emit_data_updated(self, data: Any):
        """Convenience method to emit data update events"""
        self.emit_event(EventType.DATA_UPDATED, {"data": data})
    
    def emit_selection_changed(self, selected_items: List[Any]):
        """Convenience method to emit selection change events"""
        self.emit_event(EventType.SELECTION_CHANGED, {"selected_items": selected_items})

class EventSubscriber:
    """Mixin class for components that subscribe to events"""
    
    def __init__(self, component_name: str):
        self.component_name = component_name
        self.event_bus = get_event_bus()
        self._subscriptions: List[tuple] = []  # Track subscriptions for cleanup
    
    def subscribe_to_event(self, event_type: EventType, callback: Callable[[ComponentEvent], None]):
        """Subscribe to an event type"""
        self.event_bus.subscribe(event_type, callback)
        self._subscriptions.append((event_type, callback))
    
    def subscribe_to_component(self, component_name: str, callback: Callable[[ComponentEvent], None]):
        """Subscribe to events from a specific component"""
        self.event_bus.subscribe_component(component_name, callback)
        self._subscriptions.append((component_name, callback))
    
    def cleanup_subscriptions(self):
        """Clean up all subscriptions (call in destructor)"""
        for subscription in self._subscriptions:
            if isinstance(subscription[0], EventType):
                self.event_bus.unsubscribe(subscription[0], subscription[1])
            else:
                self.event_bus.unsubscribe_component(subscription[0], subscription[1])
        self._subscriptions.clear()

class StateManager(EventEmitter):
    """Base state manager for components"""
    
    def __init__(self, component_name: str, initial_state: Dict[str, Any] = None):
        super().__init__(component_name)
        self._state = initial_state or {}
        self._previous_state = {}
    
    def get_state(self) -> Dict[str, Any]:
        """Get current state"""
        return self._state.copy()
    
    def set_state(self, new_state: Dict[str, Any], emit_event: bool = True):
        """Set state and optionally emit change event"""
        self._previous_state = self._state.copy()
        self._state.update(new_state)
        
        if emit_event:
            self.emit_state_changed({
                "current_state": self._state,
                "previous_state": self._previous_state,
                "changed_keys": list(new_state.keys())
            })
    
    def update_state_field(self, key: str, value: Any, emit_event: bool = True):
        """Update a single state field"""
        old_value = self._state.get(key)
        self._state[key] = value
        
        if emit_event and old_value != value:
            self.emit_state_changed({
                "current_state": self._state,
                "changed_field": key,
                "old_value": old_value,
                "new_value": value
            })
    
    def clear_state(self, emit_event: bool = True):
        """Clear all state"""
        self._previous_state = self._state.copy()
        self._state.clear()
        
        if emit_event:
            self.emit_event(EventType.STATE_RESET, {
                "previous_state": self._previous_state
            })
    
    def get_state_field(self, key: str, default: Any = None) -> Any:
        """Get a single state field"""
        return self._state.get(key, default)
    
    def has_state_field(self, key: str) -> bool:
        """Check if state has a specific field"""
        return key in self._state 