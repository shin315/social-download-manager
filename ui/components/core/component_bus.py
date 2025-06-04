"""
Advanced Component Bus for v2.0 UI Architecture

This module provides comprehensive cross-component communication including:
- Event-driven messaging between components and tabs
- Subscription-based communication with filtering
- Message routing and priority handling
- Integration with TabLifecycleManager for tab-aware communication
- Request-response patterns for synchronous communication
- Broadcast and unicast messaging
- Message persistence and replay for hibernated tabs
"""

import logging
import threading
import uuid
import json
import time
import weakref
from typing import Dict, Any, Optional, Callable, List, Set, Union, TypeVar, Generic
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from collections import defaultdict, deque
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QMutex, QMutexLocker

from .tab_lifecycle_manager import TabLifecycleManager, TabState, get_global_tab_lifecycle_manager

logger = logging.getLogger(__name__)

T = TypeVar('T')


class MessageType(Enum):
    """Message types for component bus"""
    EVENT = "event"
    REQUEST = "request"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    NOTIFICATION = "notification"
    COMMAND = "command"
    QUERY = "query"
    STATUS_UPDATE = "status_update"


class MessagePriority(Enum):
    """Message priority levels"""
    CRITICAL = 0     # System-critical messages (errors, shutdown)
    HIGH = 1         # Important user actions
    NORMAL = 2       # Standard operations
    LOW = 3          # Background updates, statistics
    DEFERRED = 4     # Can be delayed or dropped


class DeliveryMode(Enum):
    """Message delivery modes"""
    IMMEDIATE = "immediate"        # Deliver now, fail if recipient unavailable
    PERSISTENT = "persistent"      # Queue and deliver when recipient available
    BEST_EFFORT = "best_effort"    # Try to deliver, don't queue if failed
    BROADCAST = "broadcast"        # Deliver to all matching recipients


@dataclass
class BusMessage:
    """Message structure for component bus"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.EVENT
    priority: MessagePriority = MessagePriority.NORMAL
    delivery_mode: DeliveryMode = DeliveryMode.IMMEDIATE
    
    # Routing information
    sender_id: str = ""
    sender_type: str = ""
    recipient_id: Optional[str] = None
    recipient_type: Optional[str] = None
    channel: str = "default"
    
    # Message content
    payload: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    
    # State tracking
    retry_count: int = 0
    max_retries: int = 3
    delivered: bool = False
    acknowledged: bool = False


@dataclass
class Subscription:
    """Subscription information for message filtering"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    subscriber_id: str = ""
    subscriber_type: str = ""
    
    # Filtering criteria
    channel: str = "*"
    message_type: Optional[MessageType] = None
    sender_filter: Optional[str] = None
    payload_filter: Dict[str, Any] = field(default_factory=dict)
    
    # Callback and delivery options
    callback: Optional[Callable[[BusMessage], None]] = None
    delivery_mode: DeliveryMode = DeliveryMode.IMMEDIATE
    priority: MessagePriority = MessagePriority.NORMAL
    
    # State
    active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    message_count: int = 0
    last_message_time: Optional[datetime] = None


@dataclass
class ComponentInfo:
    """Information about registered components"""
    id: str
    type: str
    name: str
    version: str = "1.0"
    capabilities: List[str] = field(default_factory=list)
    subscriptions: Set[str] = field(default_factory=set)
    tab_id: Optional[str] = None
    status: str = "active"
    registered_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    message_stats: Dict[str, int] = field(default_factory=lambda: {
        'sent': 0, 'received': 0, 'failed': 0
    })


@dataclass
class BusMetrics:
    """Component bus performance and usage metrics"""
    total_messages: int = 0
    messages_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    messages_by_priority: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    average_delivery_time: float = 0.0
    failed_deliveries: int = 0
    queued_messages: int = 0
    active_subscriptions: int = 0
    registered_components: int = 0
    uptime_start: datetime = field(default_factory=datetime.now)


class ComponentBus(QObject):
    """
    Advanced component bus providing comprehensive cross-component communication,
    message routing, subscription management, and integration with tab lifecycle
    for v2.0 UI architecture.
    """
    
    # Signals for bus events
    message_sent = pyqtSignal(str, str)  # message_id, channel
    message_delivered = pyqtSignal(str, str, str)  # message_id, recipient_id, delivery_time
    message_failed = pyqtSignal(str, str, str)  # message_id, recipient_id, error
    subscription_added = pyqtSignal(str, str)  # subscription_id, channel
    component_registered = pyqtSignal(str, str)  # component_id, component_type
    component_unregistered = pyqtSignal(str)  # component_id
    bus_error = pyqtSignal(str, str)  # error_type, error_message
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.config = self._create_default_config()
        if config:
            self.config.update(config)
        
        # Core state
        self._components: Dict[str, ComponentInfo] = {}
        self._subscriptions: Dict[str, Subscription] = {}
        self._message_queue: deque = deque()
        self._request_response_map: Dict[str, BusMessage] = {}
        
        # Channel and routing
        self._channel_subscriptions: Dict[str, Set[str]] = defaultdict(set)
        self._priority_queues: Dict[MessagePriority, deque] = {
            priority: deque() for priority in MessagePriority
        }
        
        # Integration with tab lifecycle
        self._tab_lifecycle_manager = get_global_tab_lifecycle_manager()
        self._hibernated_messages: Dict[str, List[BusMessage]] = defaultdict(list)
        
        # Performance and monitoring
        self._metrics = BusMetrics()
        self._delivery_stats: deque = deque(maxlen=1000)  # Last 1000 deliveries
        
        # Threading and timing
        self._lock = threading.RLock()
        self._processing_timer: Optional[QTimer] = None
        self._cleanup_timer: Optional[QTimer] = None
        self._running = False
        
        # Message persistence
        self._persistence_enabled = self.config['enable_message_persistence']
        self._persistence_path = Path(self.config['persistence_path'])
        if self._persistence_enabled:
            self._persistence_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize bus
        self._setup_tab_lifecycle_integration()
        self._start_processing()
        
        self.logger.info(f"ComponentBus initialized with config: {self.config}")
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration for component bus"""
        return {
            'processing_interval': 10,  # milliseconds
            'cleanup_interval': 60000,  # 1 minute
            'max_queue_size': 10000,
            'message_ttl_seconds': 300,  # 5 minutes
            'enable_message_persistence': True,
            'enable_request_response': True,
            'enable_hibernation_replay': True,
            'max_retry_attempts': 3,
            'delivery_timeout_seconds': 30,
            'persistence_path': 'data/bus_messages',
            'enable_message_compression': True,
            'enable_delivery_confirmation': True,
            'batch_processing_size': 50
        }
    
    def _setup_tab_lifecycle_integration(self) -> None:
        """Set up integration with tab lifecycle manager"""
        try:
            # Connect to tab lifecycle events
            self._tab_lifecycle_manager.tab_hibernated.connect(self._on_tab_hibernated)
            self._tab_lifecycle_manager.tab_restored.connect(self._on_tab_restored)
            self._tab_lifecycle_manager.tab_terminated.connect(self._on_tab_terminated)
            
            self.logger.info("Tab lifecycle integration established")
            
        except Exception as e:
            self.logger.error(f"Failed to setup tab lifecycle integration: {e}")
    
    def _start_processing(self) -> None:
        """Start message processing and cleanup timers"""
        try:
            self._running = True
            
            # Message processing timer
            self._processing_timer = QTimer()
            self._processing_timer.timeout.connect(self._process_message_queue)
            self._processing_timer.start(self.config['processing_interval'])
            
            # Cleanup timer
            self._cleanup_timer = QTimer()
            self._cleanup_timer.timeout.connect(self._cleanup_expired_messages)
            self._cleanup_timer.start(self.config['cleanup_interval'])
            
            self.logger.info("Message processing started")
            
        except Exception as e:
            self.logger.error(f"Failed to start processing: {e}")
    
    def register_component(self, component_id: str, component_type: str, 
                          component_name: str, capabilities: List[str] = None,
                          tab_id: Optional[str] = None) -> bool:
        """
        Register a component with the bus
        
        Args:
            component_id: Unique identifier for the component
            component_type: Type/class of the component
            component_name: Human-readable name
            capabilities: List of capabilities the component provides
            tab_id: Associated tab ID if component is tab-specific
            
        Returns:
            True if registration successful, False otherwise
        """
        with self._lock:
            try:
                if component_id in self._components:
                    self.logger.warning(f"Component {component_id} already registered")
                    return False
                
                component_info = ComponentInfo(
                    id=component_id,
                    type=component_type,
                    name=component_name,
                    capabilities=capabilities or [],
                    tab_id=tab_id
                )
                
                self._components[component_id] = component_info
                self._metrics.registered_components += 1
                
                self.logger.info(f"Component {component_id} ({component_type}) registered")
                self.component_registered.emit(component_id, component_type)
                
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to register component {component_id}: {e}")
                self.bus_error.emit("registration_failed", str(e))
                return False
    
    def unregister_component(self, component_id: str) -> bool:
        """
        Unregister a component from the bus
        
        Args:
            component_id: ID of component to unregister
            
        Returns:
            True if unregistration successful, False otherwise
        """
        with self._lock:
            try:
                if component_id not in self._components:
                    self.logger.warning(f"Component {component_id} not registered")
                    return False
                
                component_info = self._components[component_id]
                
                # Remove all subscriptions for this component
                subscription_ids_to_remove = []
                for sub_id, subscription in self._subscriptions.items():
                    if subscription.subscriber_id == component_id:
                        subscription_ids_to_remove.append(sub_id)
                
                for sub_id in subscription_ids_to_remove:
                    self._remove_subscription(sub_id)
                
                # Remove component
                del self._components[component_id]
                self._metrics.registered_components -= 1
                
                self.logger.info(f"Component {component_id} unregistered")
                self.component_unregistered.emit(component_id)
                
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to unregister component {component_id}: {e}")
                self.bus_error.emit("unregistration_failed", str(e))
                return False
    
    def subscribe(self, subscriber_id: str, channel: str = "*", 
                 message_type: Optional[MessageType] = None,
                 callback: Optional[Callable[[BusMessage], None]] = None,
                 sender_filter: Optional[str] = None,
                 payload_filter: Dict[str, Any] = None) -> Optional[str]:
        """
        Subscribe to messages on the bus
        
        Args:
            subscriber_id: ID of subscribing component
            channel: Channel to subscribe to (* for all)
            message_type: Filter by message type
            callback: Callback function for received messages
            sender_filter: Filter by sender ID pattern
            payload_filter: Filter by payload content
            
        Returns:
            Subscription ID if successful, None otherwise
        """
        with self._lock:
            try:
                if subscriber_id not in self._components:
                    self.logger.error(f"Component {subscriber_id} not registered")
                    return None
                
                subscription = Subscription(
                    subscriber_id=subscriber_id,
                    subscriber_type=self._components[subscriber_id].type,
                    channel=channel,
                    message_type=message_type,
                    callback=callback,
                    sender_filter=sender_filter,
                    payload_filter=payload_filter or {}
                )
                
                self._subscriptions[subscription.id] = subscription
                self._channel_subscriptions[channel].add(subscription.id)
                self._components[subscriber_id].subscriptions.add(subscription.id)
                self._metrics.active_subscriptions += 1
                
                self.logger.info(f"Subscription {subscription.id} created for {subscriber_id} on channel {channel}")
                self.subscription_added.emit(subscription.id, channel)
                
                return subscription.id
                
            except Exception as e:
                self.logger.error(f"Failed to create subscription: {e}")
                self.bus_error.emit("subscription_failed", str(e))
                return None
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Remove a subscription
        
        Args:
            subscription_id: ID of subscription to remove
            
        Returns:
            True if removal successful, False otherwise
        """
        with self._lock:
            return self._remove_subscription(subscription_id)
    
    def _remove_subscription(self, subscription_id: str) -> bool:
        """Internal method to remove a subscription"""
        try:
            if subscription_id not in self._subscriptions:
                return False
            
            subscription = self._subscriptions[subscription_id]
            
            # Remove from channel subscriptions
            self._channel_subscriptions[subscription.channel].discard(subscription_id)
            
            # Remove from component subscriptions
            if subscription.subscriber_id in self._components:
                self._components[subscription.subscriber_id].subscriptions.discard(subscription_id)
            
            # Remove subscription
            del self._subscriptions[subscription_id]
            self._metrics.active_subscriptions -= 1
            
            self.logger.debug(f"Subscription {subscription_id} removed")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to remove subscription {subscription_id}: {e}")
            return False
    
    def send_message(self, message: BusMessage) -> bool:
        """
        Send a message on the bus
        
        Args:
            message: Message to send
            
        Returns:
            True if message queued successfully, False otherwise
        """
        with self._lock:
            try:
                # Validate sender is registered
                if message.sender_id and message.sender_id not in self._components:
                    self.logger.error(f"Sender {message.sender_id} not registered")
                    return False
                
                # Set timestamp if not set
                if not message.timestamp:
                    message.timestamp = datetime.now()
                
                # Set expiration if not set
                if not message.expires_at:
                    ttl = timedelta(seconds=self.config['message_ttl_seconds'])
                    message.expires_at = message.timestamp + ttl
                
                # Add to appropriate queue based on priority
                if message.delivery_mode == DeliveryMode.IMMEDIATE:
                    self._process_message_immediate(message)
                else:
                    self._priority_queues[message.priority].append(message)
                    self._metrics.queued_messages += 1
                
                # Update metrics
                self._metrics.total_messages += 1
                self._metrics.messages_by_type[message.type.value] += 1
                self._metrics.messages_by_priority[message.priority.value] += 1
                
                # Update sender stats
                if message.sender_id in self._components:
                    self._components[message.sender_id].message_stats['sent'] += 1
                    self._components[message.sender_id].last_activity = datetime.now()
                
                self.logger.debug(f"Message {message.id} queued for delivery")
                self.message_sent.emit(message.id, message.channel)
                
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to send message: {e}")
                self.bus_error.emit("send_failed", str(e))
                return False
    
    def send_event(self, sender_id: str, channel: str, event_type: str, 
                  data: Dict[str, Any] = None, priority: MessagePriority = MessagePriority.NORMAL) -> Optional[str]:
        """
        Send an event message
        
        Args:
            sender_id: ID of sending component
            channel: Channel to send on
            event_type: Type of event
            data: Event data
            priority: Message priority
            
        Returns:
            Message ID if successful, None otherwise
        """
        message = BusMessage(
            type=MessageType.EVENT,
            priority=priority,
            delivery_mode=DeliveryMode.BROADCAST,
            sender_id=sender_id,
            sender_type=self._components.get(sender_id, ComponentInfo("", "", "")).type,
            channel=channel,
            payload={'event_type': event_type, 'data': data or {}},
            headers={'event_type': event_type}
        )
        
        return message.id if self.send_message(message) else None
    
    def send_request(self, sender_id: str, recipient_id: str, request_type: str,
                    data: Dict[str, Any] = None, timeout: int = 30) -> Optional[str]:
        """
        Send a request message (request-response pattern)
        
        Args:
            sender_id: ID of requesting component
            recipient_id: ID of target component
            request_type: Type of request
            data: Request data
            timeout: Response timeout in seconds
            
        Returns:
            Correlation ID for tracking response, None if failed
        """
        if not self.config['enable_request_response']:
            self.logger.error("Request-response pattern disabled")
            return None
        
        correlation_id = str(uuid.uuid4())
        
        message = BusMessage(
            type=MessageType.REQUEST,
            priority=MessagePriority.HIGH,
            delivery_mode=DeliveryMode.IMMEDIATE,
            sender_id=sender_id,
            sender_type=self._components.get(sender_id, ComponentInfo("", "", "")).type,
            recipient_id=recipient_id,
            channel="request",
            payload={'request_type': request_type, 'data': data or {}},
            headers={'request_type': request_type},
            correlation_id=correlation_id,
            reply_to=sender_id,
            expires_at=datetime.now() + timedelta(seconds=timeout)
        )
        
        return correlation_id if self.send_message(message) else None
    
    def send_response(self, sender_id: str, correlation_id: str, 
                     response_data: Dict[str, Any], success: bool = True) -> bool:
        """
        Send a response message
        
        Args:
            sender_id: ID of responding component
            correlation_id: Correlation ID from original request
            response_data: Response data
            success: Whether the response indicates success
            
        Returns:
            True if response sent successfully, False otherwise
        """
        # Find original request
        original_request = self._request_response_map.get(correlation_id)
        if not original_request:
            self.logger.error(f"No pending request found for correlation ID {correlation_id}")
            return False
        
        message = BusMessage(
            type=MessageType.RESPONSE,
            priority=MessagePriority.HIGH,
            delivery_mode=DeliveryMode.IMMEDIATE,
            sender_id=sender_id,
            sender_type=self._components.get(sender_id, ComponentInfo("", "", "")).type,
            recipient_id=original_request.reply_to,
            channel="response",
            payload={'success': success, 'data': response_data},
            headers={'success': str(success)},
            correlation_id=correlation_id
        )
        
        # Remove from pending requests
        del self._request_response_map[correlation_id]
        
        return self.send_message(message)
    
    def broadcast(self, sender_id: str, channel: str, message_type: str,
                 data: Dict[str, Any] = None, priority: MessagePriority = MessagePriority.NORMAL) -> Optional[str]:
        """
        Broadcast a message to all subscribers on a channel
        
        Args:
            sender_id: ID of broadcasting component
            channel: Channel to broadcast on
            message_type: Type of broadcast message
            data: Broadcast data
            priority: Message priority
            
        Returns:
            Message ID if successful, None otherwise
        """
        message = BusMessage(
            type=MessageType.BROADCAST,
            priority=priority,
            delivery_mode=DeliveryMode.BROADCAST,
            sender_id=sender_id,
            sender_type=self._components.get(sender_id, ComponentInfo("", "", "")).type,
            channel=channel,
            payload={'broadcast_type': message_type, 'data': data or {}},
            headers={'broadcast_type': message_type}
        )
        
        return message.id if self.send_message(message) else None
    
    def _process_message_queue(self) -> None:
        """Process queued messages in priority order"""
        if not self._running:
            return
        
        try:
            batch_size = self.config['batch_processing_size']
            processed_count = 0
            
            # Process messages by priority (critical first)
            for priority in MessagePriority:
                queue = self._priority_queues[priority]
                
                while queue and processed_count < batch_size:
                    message = queue.popleft()
                    self._metrics.queued_messages -= 1
                    
                    # Check if message has expired
                    if message.expires_at and datetime.now() > message.expires_at:
                        self.logger.debug(f"Message {message.id} expired, dropping")
                        continue
                    
                    self._process_message_immediate(message)
                    processed_count += 1
            
        except Exception as e:
            self.logger.error(f"Error processing message queue: {e}")
    
    def _process_message_immediate(self, message: BusMessage) -> None:
        """Process a message immediately"""
        try:
            delivery_start = time.time()
            delivered_count = 0
            
            # Find matching subscriptions
            matching_subscriptions = self._find_matching_subscriptions(message)
            
            # Handle request-response pattern
            if message.type == MessageType.REQUEST and message.correlation_id:
                self._request_response_map[message.correlation_id] = message
            
            # Deliver to matching subscribers
            for subscription in matching_subscriptions:
                if self._deliver_message_to_subscription(message, subscription):
                    delivered_count += 1
            
            # Update delivery metrics
            delivery_time = (time.time() - delivery_start) * 1000  # milliseconds
            self._update_delivery_metrics(message.id, delivery_time, delivered_count > 0)
            
            # Mark message as delivered
            message.delivered = delivered_count > 0
            
            if delivered_count > 0:
                self.message_delivered.emit(message.id, f"{delivered_count}_recipients", f"{delivery_time:.1f}ms")
            else:
                self.logger.debug(f"No recipients found for message {message.id}")
                
        except Exception as e:
            self.logger.error(f"Error processing message {message.id}: {e}")
            self.message_failed.emit(message.id, "processing_error", str(e))
    
    def _find_matching_subscriptions(self, message: BusMessage) -> List[Subscription]:
        """Find subscriptions that match a message"""
        matching = []
        
        # Get subscriptions for message channel and wildcard
        channel_subs = self._channel_subscriptions.get(message.channel, set())
        wildcard_subs = self._channel_subscriptions.get("*", set())
        candidate_subs = channel_subs | wildcard_subs
        
        for sub_id in candidate_subs:
            subscription = self._subscriptions.get(sub_id)
            if not subscription or not subscription.active:
                continue
            
            # Check message type filter
            if subscription.message_type and subscription.message_type != message.type:
                continue
            
            # Check sender filter
            if subscription.sender_filter and not self._matches_pattern(message.sender_id, subscription.sender_filter):
                continue
            
            # Check payload filter
            if subscription.payload_filter and not self._matches_payload_filter(message.payload, subscription.payload_filter):
                continue
            
            # Check if recipient is hibernated
            component = self._components.get(subscription.subscriber_id)
            if component and component.tab_id:
                tab_state = self._tab_lifecycle_manager.get_tab_state(component.tab_id)
                if tab_state == TabState.HIBERNATED:
                    # Queue message for hibernated tab
                    self._hibernated_messages[component.tab_id].append(message)
                    continue
            
            matching.append(subscription)
        
        return matching
    
    def _matches_pattern(self, value: str, pattern: str) -> bool:
        """Check if value matches pattern (supports * wildcard)"""
        if pattern == "*":
            return True
        
        if "*" not in pattern:
            return value == pattern
        
        # Simple wildcard matching
        import re
        regex_pattern = pattern.replace("*", ".*")
        return bool(re.match(regex_pattern, value))
    
    def _matches_payload_filter(self, payload: Dict[str, Any], filter_dict: Dict[str, Any]) -> bool:
        """Check if payload matches filter criteria"""
        for key, expected_value in filter_dict.items():
            if key not in payload:
                return False
            
            actual_value = payload[key]
            
            # Support various matching types
            if isinstance(expected_value, str) and expected_value.startswith("*"):
                # Wildcard string matching
                if not self._matches_pattern(str(actual_value), expected_value):
                    return False
            elif actual_value != expected_value:
                return False
        
        return True
    
    def _deliver_message_to_subscription(self, message: BusMessage, subscription: Subscription) -> bool:
        """Deliver a message to a specific subscription"""
        try:
            # Update subscription metrics
            subscription.message_count += 1
            subscription.last_message_time = datetime.now()
            
            # Update component metrics
            component = self._components.get(subscription.subscriber_id)
            if component:
                component.message_stats['received'] += 1
                component.last_activity = datetime.now()
            
            # Call subscription callback if available
            if subscription.callback:
                try:
                    subscription.callback(message)
                    return True
                except Exception as e:
                    self.logger.error(f"Subscription callback error for {subscription.id}: {e}")
                    if component:
                        component.message_stats['failed'] += 1
                    return False
            
            # If no callback, just mark as delivered (passive subscription)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to deliver message to subscription {subscription.id}: {e}")
            return False
    
    def _update_delivery_metrics(self, message_id: str, delivery_time: float, success: bool) -> None:
        """Update delivery performance metrics"""
        self._delivery_stats.append({
            'message_id': message_id,
            'delivery_time': delivery_time,
            'success': success,
            'timestamp': datetime.now()
        })
        
        if success:
            # Update rolling average delivery time
            if self._metrics.average_delivery_time == 0:
                self._metrics.average_delivery_time = delivery_time
            else:
                self._metrics.average_delivery_time = (
                    self._metrics.average_delivery_time * 0.9 + delivery_time * 0.1
                )
        else:
            self._metrics.failed_deliveries += 1
    
    def _cleanup_expired_messages(self) -> None:
        """Clean up expired messages and requests"""
        try:
            current_time = datetime.now()
            
            # Clean up expired requests
            expired_requests = []
            for correlation_id, request in self._request_response_map.items():
                if request.expires_at and current_time > request.expires_at:
                    expired_requests.append(correlation_id)
            
            for correlation_id in expired_requests:
                del self._request_response_map[correlation_id]
                self.logger.debug(f"Expired request {correlation_id} cleaned up")
            
            # Clean up expired messages in queues
            for priority_queue in self._priority_queues.values():
                # Convert to list to avoid modification during iteration
                messages = list(priority_queue)
                priority_queue.clear()
                
                for message in messages:
                    if not message.expires_at or current_time <= message.expires_at:
                        priority_queue.append(message)
                    else:
                        self._metrics.queued_messages -= 1
            
            # Clean up old hibernated messages
            for tab_id, messages in list(self._hibernated_messages.items()):
                valid_messages = []
                for message in messages:
                    if not message.expires_at or current_time <= message.expires_at:
                        valid_messages.append(message)
                
                if valid_messages:
                    self._hibernated_messages[tab_id] = valid_messages
                else:
                    del self._hibernated_messages[tab_id]
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def _on_tab_hibernated(self, tab_id: str, saved_state: dict) -> None:
        """Handle tab hibernation event"""
        try:
            self.logger.debug(f"Tab {tab_id} hibernated, preparing message queue")
            
            # Mark components in this tab as hibernated
            for component in self._components.values():
                if component.tab_id == tab_id:
                    component.status = "hibernated"
            
        except Exception as e:
            self.logger.error(f"Error handling tab hibernation for {tab_id}: {e}")
    
    def _on_tab_restored(self, tab_id: str, restored_state: dict) -> None:
        """Handle tab restoration event"""
        try:
            self.logger.debug(f"Tab {tab_id} restored, replaying queued messages")
            
            # Mark components in this tab as active
            for component in self._components.values():
                if component.tab_id == tab_id:
                    component.status = "active"
            
            # Replay hibernated messages if enabled
            if self.config['enable_hibernation_replay'] and tab_id in self._hibernated_messages:
                messages = self._hibernated_messages[tab_id]
                
                for message in messages:
                    # Re-process the message
                    self._process_message_immediate(message)
                
                # Clear hibernated messages for this tab
                del self._hibernated_messages[tab_id]
                
                self.logger.info(f"Replayed {len(messages)} messages for restored tab {tab_id}")
            
        except Exception as e:
            self.logger.error(f"Error handling tab restoration for {tab_id}: {e}")
    
    def _on_tab_terminated(self, tab_id: str) -> None:
        """Handle tab termination event"""
        try:
            self.logger.debug(f"Tab {tab_id} terminated, cleaning up components")
            
            # Unregister all components associated with this tab
            components_to_remove = []
            for component_id, component in self._components.items():
                if component.tab_id == tab_id:
                    components_to_remove.append(component_id)
            
            for component_id in components_to_remove:
                self.unregister_component(component_id)
            
            # Clear hibernated messages for this tab
            if tab_id in self._hibernated_messages:
                del self._hibernated_messages[tab_id]
            
            self.logger.info(f"Cleaned up {len(components_to_remove)} components for terminated tab {tab_id}")
            
        except Exception as e:
            self.logger.error(f"Error handling tab termination for {tab_id}: {e}")
    
    def get_component_info(self, component_id: str) -> Optional[ComponentInfo]:
        """Get information about a registered component"""
        return self._components.get(component_id)
    
    def get_subscription_info(self, subscription_id: str) -> Optional[Subscription]:
        """Get information about a subscription"""
        return self._subscriptions.get(subscription_id)
    
    def get_bus_metrics(self) -> BusMetrics:
        """Get component bus metrics and statistics"""
        return self._metrics
    
    def get_registered_components(self) -> Dict[str, ComponentInfo]:
        """Get all registered components"""
        return self._components.copy()
    
    def get_active_subscriptions(self) -> Dict[str, Subscription]:
        """Get all active subscriptions"""
        return {k: v for k, v in self._subscriptions.items() if v.active}
    
    def get_channel_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for each channel"""
        stats = {}
        
        for channel, sub_ids in self._channel_subscriptions.items():
            active_subs = len([s for s in sub_ids if self._subscriptions.get(s, Subscription()).active])
            
            stats[channel] = {
                'total_subscriptions': len(sub_ids),
                'active_subscriptions': active_subs,
                'components': list(set(
                    self._subscriptions[s].subscriber_id 
                    for s in sub_ids 
                    if s in self._subscriptions
                ))
            }
        
        return stats
    
    def export_bus_state(self, export_path: str) -> bool:
        """Export current bus state for analysis or backup"""
        try:
            export_data = {
                'components': {k: asdict(v) for k, v in self._components.items()},
                'subscriptions': {k: asdict(v) for k, v in self._subscriptions.items()},
                'metrics': asdict(self._metrics),
                'channel_stats': self.get_channel_statistics(),
                'exported_at': datetime.now().isoformat(),
                'version': '1.0'
            }
            
            # Remove callback functions (not serializable)
            for sub_data in export_data['subscriptions'].values():
                sub_data.pop('callback', None)
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            self.logger.info(f"Bus state exported to {export_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export bus state: {e}")
            return False
    
    def shutdown(self) -> None:
        """Shutdown the component bus"""
        with self._lock:
            try:
                self.logger.info("Shutting down ComponentBus")
                
                self._running = False
                
                # Stop timers
                if self._processing_timer:
                    self._processing_timer.stop()
                if self._cleanup_timer:
                    self._cleanup_timer.stop()
                
                # Process remaining messages
                for priority_queue in self._priority_queues.values():
                    while priority_queue:
                        message = priority_queue.popleft()
                        self._process_message_immediate(message)
                
                # Save state if persistence enabled
                if self._persistence_enabled:
                    state_file = self._persistence_path / 'bus_state_shutdown.json'
                    self.export_bus_state(str(state_file))
                
                self.logger.info("ComponentBus shutdown completed")
                
            except Exception as e:
                self.logger.error(f"Error during ComponentBus shutdown: {e}")


# Factory function for creating component bus instances
def create_component_bus(config: Optional[Dict[str, Any]] = None) -> ComponentBus:
    """Create a new component bus instance with optional configuration"""
    return ComponentBus(config)


# Global instance management
_global_component_bus: Optional[ComponentBus] = None


def get_global_component_bus() -> ComponentBus:
    """Get or create the global component bus instance"""
    global _global_component_bus
    
    if _global_component_bus is None:
        _global_component_bus = ComponentBus()
    
    return _global_component_bus


def set_global_component_bus(bus: ComponentBus) -> None:
    """Set the global component bus instance"""
    global _global_component_bus
    _global_component_bus = bus 