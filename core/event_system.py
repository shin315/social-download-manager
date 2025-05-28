"""
Event System for Social Download Manager v2.0

Provides event-driven communication between different components
of the application without tight coupling.
"""

import threading
from typing import Dict, List, Callable, Any, Optional
from enum import Enum, auto
from dataclasses import dataclass
from datetime import datetime


class EventType(Enum):
    """Standard event types for the application"""
    # Download events
    DOWNLOAD_STARTED = auto()
    DOWNLOAD_PROGRESS = auto()
    DOWNLOAD_COMPLETED = auto()
    DOWNLOAD_FAILED = auto()
    DOWNLOAD_CANCELLED = auto()
    
    # Platform events
    PLATFORM_DETECTED = auto()
    PLATFORM_ERROR = auto()
    PLATFORM_UNAVAILABLE = auto()
    
    # UI events
    UI_UPDATE_REQUIRED = auto()
    UI_THEME_CHANGED = auto()
    UI_LANGUAGE_CHANGED = auto()
    
    # Database events
    DB_CONNECTED = auto()
    DB_DISCONNECTED = auto()
    DB_MIGRATION_STARTED = auto()
    DB_MIGRATION_COMPLETED = auto()
    DB_ERROR = auto()
    
    # Application events
    APP_STARTUP = auto()
    APP_SHUTDOWN = auto()
    CONFIG_CHANGED = auto()
    ERROR_OCCURRED = auto()


@dataclass
class Event:
    """Event object containing event data"""
    event_type: EventType
    source: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class EventHandler:
    """Base class for event handlers"""
    
    def handle_event(self, event: Event) -> None:
        """Handle an event. Override in subclasses."""
        pass


class EventBus:
    """Central event bus for managing event subscriptions and publishing"""
    
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable[[Event], None]]] = {}
        self._handlers: List[EventHandler] = []
        self._lock = threading.RLock()
        self._event_history: List[Event] = []
        self._max_history = 1000
    
    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """
        Subscribe to events of a specific type
        
        Args:
            event_type: Type of event to subscribe to
            callback: Function to call when event occurs
        """
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)
    
    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> bool:
        """
        Unsubscribe from events of a specific type
        
        Args:
            event_type: Type of event to unsubscribe from
            callback: Function to remove from subscriptions
            
        Returns:
            True if callback was found and removed, False otherwise
        """
        with self._lock:
            if event_type in self._subscribers:
                try:
                    self._subscribers[event_type].remove(callback)
                    return True
                except ValueError:
                    return False
            return False
    
    def add_handler(self, handler: EventHandler) -> None:
        """
        Add an event handler that receives all events
        
        Args:
            handler: EventHandler instance to add
        """
        with self._lock:
            if handler not in self._handlers:
                self._handlers.append(handler)
    
    def remove_handler(self, handler: EventHandler) -> bool:
        """
        Remove an event handler
        
        Args:
            handler: EventHandler instance to remove
            
        Returns:
            True if handler was found and removed, False otherwise
        """
        with self._lock:
            try:
                self._handlers.remove(handler)
                return True
            except ValueError:
                return False
    
    def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribers
        
        Args:
            event: Event to publish
        """
        with self._lock:
            # Add to history
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history.pop(0)
            
            # Notify specific subscribers
            if event.event_type in self._subscribers:
                for callback in self._subscribers[event.event_type][:]:  # Copy to avoid modification during iteration
                    try:
                        callback(event)
                    except Exception as e:
                        print(f"Error in event callback: {e}")
            
            # Notify general handlers
            for handler in self._handlers[:]:  # Copy to avoid modification during iteration
                try:
                    handler.handle_event(event)
                except Exception as e:
                    print(f"Error in event handler: {e}")
    
    def publish_async(self, event: Event) -> None:
        """
        Publish an event asynchronously
        
        Args:
            event: Event to publish
        """
        def async_publish():
            self.publish(event)
        
        thread = threading.Thread(target=async_publish, daemon=True)
        thread.start()
    
    def get_event_history(self, event_type: Optional[EventType] = None, limit: Optional[int] = None) -> List[Event]:
        """
        Get event history
        
        Args:
            event_type: Filter by specific event type (optional)
            limit: Maximum number of events to return (optional)
            
        Returns:
            List of events
        """
        with self._lock:
            events = self._event_history[:]
            
            if event_type:
                events = [e for e in events if e.event_type == event_type]
            
            if limit:
                events = events[-limit:]
            
            return events
    
    def clear_history(self) -> None:
        """Clear event history"""
        with self._lock:
            self._event_history.clear()
    
    def get_subscriber_count(self, event_type: EventType) -> int:
        """Get number of subscribers for an event type"""
        with self._lock:
            return len(self._subscribers.get(event_type, []))
    
    def get_total_subscribers(self) -> int:
        """Get total number of event subscribers"""
        with self._lock:
            return sum(len(subs) for subs in self._subscribers.values())


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def publish_event(event_type: EventType, source: str, data: Optional[Dict[str, Any]] = None) -> None:
    """
    Convenience function to publish an event
    
    Args:
        event_type: Type of event
        source: Source component/module name
        data: Optional event data
    """
    event = Event(event_type=event_type, source=source, data=data)
    get_event_bus().publish(event)


def subscribe_to_event(event_type: EventType, callback: Callable[[Event], None]) -> None:
    """
    Convenience function to subscribe to an event
    
    Args:
        event_type: Type of event to subscribe to
        callback: Function to call when event occurs
    """
    get_event_bus().subscribe(event_type, callback)


# Example event handlers for common scenarios
class DownloadEventHandler(EventHandler):
    """Handler for download-related events"""
    
    def handle_event(self, event: Event) -> None:
        if event.event_type in [EventType.DOWNLOAD_STARTED, EventType.DOWNLOAD_PROGRESS, 
                               EventType.DOWNLOAD_COMPLETED, EventType.DOWNLOAD_FAILED, 
                               EventType.DOWNLOAD_CANCELLED]:
            self._handle_download_event(event)
    
    def _handle_download_event(self, event: Event) -> None:
        """Handle download events - override in subclasses"""
        pass


class UIEventHandler(EventHandler):
    """Handler for UI-related events"""
    
    def handle_event(self, event: Event) -> None:
        if event.event_type in [EventType.UI_UPDATE_REQUIRED, EventType.UI_THEME_CHANGED,
                               EventType.UI_LANGUAGE_CHANGED]:
            self._handle_ui_event(event)
    
    def _handle_ui_event(self, event: Event) -> None:
        """Handle UI events - override in subclasses"""
        pass 