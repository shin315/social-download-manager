"""
Cross-Component Event Coordination System for Task 29.5

This module implements advanced event coordination features that ensure proper
communication between adapted UI components through the v2.0 Event System.
It extends the existing EventBridgeCoordinator with additional capabilities
for event sequencing, throttling, debugging, and cross-component orchestration.
"""

import logging
import threading
from typing import Dict, List, Any, Optional, Callable, Set, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, deque
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread
import weakref
import json
import uuid

# Import existing event system components
from .event_proxy import EventBridgeCoordinator, EventMapping, EventPriority, EventTranslationDirection
from core.event_system import EventBus, Event, EventType, get_event_bus
from ui.components.common.events import ComponentBus, get_event_bus as get_component_bus, ComponentEvent
from core.constants import UIConstants


class EventSequenceState(Enum):
    """States for event sequence processing"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ThrottleStrategy(Enum):
    """Throttling strategies for event processing"""
    NONE = "none"
    DEBOUNCE = "debounce"  # Wait for pause before processing
    THROTTLE = "throttle"  # Limit frequency
    BATCH = "batch"       # Group events together
    PRIORITY = "priority"  # Process high priority events first


@dataclass
class EventSequenceStep:
    """Single step in an event sequence"""
    step_id: str
    event_name: str
    event_type: Union[str, EventType]
    expected_source: Optional[str] = None
    timeout_ms: int = 5000
    is_optional: bool = False
    condition: Optional[Callable[[Any], bool]] = None
    data_validator: Optional[Callable[[Any], bool]] = None
    
    # Runtime state
    state: EventSequenceState = EventSequenceState.PENDING
    received_at: Optional[datetime] = None
    data: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class EventSequence:
    """Sequence of events that must occur in order"""
    sequence_id: str
    name: str
    steps: List[EventSequenceStep]
    timeout_ms: int = 30000
    allow_parallel: bool = False
    rollback_on_failure: bool = False
    
    # Runtime state
    state: EventSequenceState = EventSequenceState.PENDING
    current_step_index: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    
    # Callbacks
    on_complete: Optional[Callable[['EventSequence'], None]] = None
    on_failure: Optional[Callable[['EventSequence', str], None]] = None
    on_step_complete: Optional[Callable[['EventSequence', EventSequenceStep], None]] = None


@dataclass
class ThrottleConfig:
    """Configuration for event throttling"""
    strategy: ThrottleStrategy
    interval_ms: int
    max_events_per_interval: int = 1
    batch_size: int = 10
    priority_levels: Dict[EventPriority, int] = field(default_factory=dict)


@dataclass
class EventDebugInfo:
    """Debug information for event tracing"""
    event_id: str
    event_name: str
    source_component: str
    target_component: Optional[str]
    timestamp: datetime
    processing_time_ms: float
    translation_path: List[str]
    data_size: int
    error: Optional[str] = None


class CrossComponentCoordinator(QObject):
    """
    Advanced event coordination system that manages cross-component
    communication with sequencing, throttling, and debugging capabilities.
    """
    
    # Signals for coordination events
    sequence_started = pyqtSignal(str, str)  # sequence_id, name
    sequence_completed = pyqtSignal(str, str)  # sequence_id, name
    sequence_failed = pyqtSignal(str, str, str)  # sequence_id, name, error
    event_throttled = pyqtSignal(str, int)  # event_name, throttle_count
    debug_event_traced = pyqtSignal(object)  # EventDebugInfo
    
    def __init__(self, bridge_coordinator: Optional[EventBridgeCoordinator] = None):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self._lock = threading.RLock()
        
        # Core components
        self._bridge_coordinator = bridge_coordinator
        self._core_event_bus: Optional[EventBus] = None
        self._component_event_bus: Optional[ComponentBus] = None
        
        # Event sequencing
        self._sequences: Dict[str, EventSequence] = {}
        self._active_sequences: Set[str] = set()
        self._sequence_timers: Dict[str, QTimer] = {}
        
        # Event throttling
        self._throttle_configs: Dict[str, ThrottleConfig] = {}
        self._throttle_queues: Dict[str, deque] = defaultdict(deque)
        self._throttle_timers: Dict[str, QTimer] = {}
        self._throttle_counts: Dict[str, int] = defaultdict(int)
        
        # Event debugging and tracing
        self._debug_enabled = False
        self._event_trace: deque = deque(maxlen=1000)
        self._component_registry: Dict[str, weakref.ref] = {}
        self._event_flow_map: Dict[str, List[str]] = defaultdict(list)
        
        # Cross-component orchestration
        self._component_states: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._component_dependencies: Dict[str, Set[str]] = defaultdict(set)
        self._event_routing_rules: Dict[str, List[Callable]] = defaultdict(list)
        
        # Performance metrics
        self._metrics = {
            "events_coordinated": 0,
            "sequences_completed": 0,
            "sequences_failed": 0,
            "events_throttled": 0,
            "average_processing_time_ms": 0.0,
            "component_count": 0
        }
        
        # Setup default configurations
        self._setup_default_throttle_configs()
        self._setup_default_sequences()
        
        # Initialize timers
        self._cleanup_timer = QTimer()
        self._cleanup_timer.timeout.connect(self._cleanup_expired_sequences)
        self._cleanup_timer.start(30000)  # 30 seconds
        
        self._metrics_timer = QTimer()
        self._metrics_timer.timeout.connect(self._update_metrics)
        self._metrics_timer.start(5000)  # 5 seconds
    
    def initialize(self, 
                   bridge_coordinator: Optional[EventBridgeCoordinator] = None,
                   core_event_bus: Optional[EventBus] = None,
                   component_event_bus: Optional[ComponentBus] = None) -> bool:
        """
        Initialize the cross-component coordinator.
        
        Args:
            bridge_coordinator: Event bridge coordinator instance
            core_event_bus: v2.0 core event bus
            component_event_bus: UI component event bus
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            with self._lock:
                # Set up event buses
                self._bridge_coordinator = bridge_coordinator or self._bridge_coordinator
                self._core_event_bus = core_event_bus or get_event_bus()
                self._component_event_bus = component_event_bus or get_component_bus()
                
                # Subscribe to core events
                if self._core_event_bus:
                    self._setup_core_event_subscriptions()
                
                # Subscribe to component events
                if self._component_event_bus:
                    self._setup_component_event_subscriptions()
                
                # Connect to bridge coordinator if available
                if self._bridge_coordinator:
                    self._bridge_coordinator.event_translated.connect(self._handle_bridge_event)
                    self._bridge_coordinator.translation_error.connect(self._handle_bridge_error)
                
                self.logger.info("Cross-Component Coordinator initialized successfully")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to initialize Cross-Component Coordinator: {e}")
            return False
    
    def register_component(self, component_id: str, component: QObject, 
                         dependencies: Optional[List[str]] = None) -> bool:
        """
        Register a UI component for cross-component coordination.
        
        Args:
            component_id: Unique identifier for the component
            component: The component object
            dependencies: List of component IDs this component depends on
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            with self._lock:
                self._component_registry[component_id] = weakref.ref(component)
                
                if dependencies:
                    self._component_dependencies[component_id].update(dependencies)
                
                self._component_states[component_id] = {
                    "registered_at": datetime.now().isoformat(),
                    "state": "registered",
                    "dependencies": dependencies or []
                }
                
                self.logger.debug(f"Registered component: {component_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to register component '{component_id}': {e}")
            return False
    
    def register_event_sequence(self, sequence: EventSequence) -> bool:
        """
        Register an event sequence for coordination.
        
        Args:
            sequence: Event sequence configuration
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            with self._lock:
                self._sequences[sequence.sequence_id] = sequence
                self.logger.debug(f"Registered event sequence: {sequence.sequence_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to register event sequence '{sequence.sequence_id}': {e}")
            return False
    
    def start_event_sequence(self, sequence_id: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Start an event sequence.
        
        Args:
            sequence_id: ID of the sequence to start
            context: Optional context data for the sequence
            
        Returns:
            True if sequence started successfully, False otherwise
        """
        try:
            with self._lock:
                if sequence_id not in self._sequences:
                    self.logger.error(f"Unknown sequence ID: {sequence_id}")
                    return False
                
                sequence = self._sequences[sequence_id]
                
                if sequence.state != EventSequenceState.PENDING:
                    self.logger.warning(f"Sequence '{sequence_id}' is not in pending state")
                    return False
                
                # Reset sequence state
                sequence.state = EventSequenceState.PROCESSING
                sequence.current_step_index = 0
                sequence.started_at = datetime.now()
                sequence.completed_at = None
                sequence.error = None
                
                # Reset all steps
                for step in sequence.steps:
                    step.state = EventSequenceState.PENDING
                    step.received_at = None
                    step.data = None
                    step.error = None
                
                self._active_sequences.add(sequence_id)
                
                # Set up timeout timer
                if sequence.timeout_ms > 0:
                    timer = QTimer()
                    timer.timeout.connect(lambda: self._handle_sequence_timeout(sequence_id))
                    timer.setSingleShot(True)
                    timer.start(sequence.timeout_ms)
                    self._sequence_timers[sequence_id] = timer
                
                self.sequence_started.emit(sequence_id, sequence.name)
                self.logger.info(f"Started event sequence: {sequence.name} ({sequence_id})")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to start event sequence '{sequence_id}': {e}")
            return False
    
    def set_throttle_config(self, event_name: str, config: ThrottleConfig) -> bool:
        """
        Set throttling configuration for an event.
        
        Args:
            event_name: Name of the event to throttle
            config: Throttling configuration
            
        Returns:
            True if configuration set successfully, False otherwise
        """
        try:
            with self._lock:
                self._throttle_configs[event_name] = config
                self.logger.debug(f"Set throttle config for event: {event_name}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to set throttle config for '{event_name}': {e}")
            return False
    
    def enable_debug_mode(self, enabled: bool = True) -> None:
        """
        Enable or disable debug mode for event tracing.
        
        Args:
            enabled: Whether to enable debug mode
        """
        self._debug_enabled = enabled
        self.logger.info(f"Debug mode {'enabled' if enabled else 'disabled'}")
    
    def get_event_trace(self) -> List[EventDebugInfo]:
        """
        Get the current event trace for debugging.
        
        Returns:
            List of debug information for recent events
        """
        return list(self._event_trace)
    
    def get_component_states(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the current states of all registered components.
        
        Returns:
            Dictionary mapping component IDs to their states
        """
        return dict(self._component_states)
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get coordination metrics.
        
        Returns:
            Dictionary containing various metrics
        """
        with self._lock:
            return dict(self._metrics)
    
    def coordinate_event(self, event_name: str, source_component: str, 
                        data: Any = None, target_component: Optional[str] = None) -> bool:
        """
        Coordinate an event through the cross-component system.
        
        Args:
            event_name: Name of the event
            source_component: Source component ID
            data: Event data
            target_component: Optional target component ID
            
        Returns:
            True if event coordinated successfully, False otherwise
        """
        try:
            start_time = datetime.now()
            
            # Create debug info
            debug_info = EventDebugInfo(
                event_id=str(uuid.uuid4()),
                event_name=event_name,
                source_component=source_component,
                target_component=target_component,
                timestamp=start_time,
                processing_time_ms=0.0,
                translation_path=[],
                data_size=len(str(data)) if data else 0
            )
            
            try:
                # Check throttling
                if not self._check_throttle(event_name, debug_info):
                    return True  # Event was throttled, but this is not an error
                
                # Process event through sequence checking
                self._process_event_sequences(event_name, source_component, data)
                
                # Route event to appropriate handlers
                self._route_event(event_name, source_component, data, target_component, debug_info)
                
                # Update metrics
                self._metrics["events_coordinated"] += 1
                
                # Finalize debug info
                processing_time = (datetime.now() - start_time).total_seconds() * 1000
                debug_info.processing_time_ms = processing_time
                
                if self._debug_enabled:
                    self._event_trace.append(debug_info)
                    self.debug_event_traced.emit(debug_info)
                
                return True
                
            except Exception as e:
                debug_info.error = str(e)
                if self._debug_enabled:
                    self._event_trace.append(debug_info)
                raise
                
        except Exception as e:
            self.logger.error(f"Failed to coordinate event '{event_name}': {e}")
            return False
    
    def _setup_default_throttle_configs(self) -> None:
        """Set up default throttling configurations for common events"""
        default_configs = {
            "download_progress_updated": ThrottleConfig(
                strategy=ThrottleStrategy.THROTTLE,
                interval_ms=100,  # Update progress max once per 100ms
                max_events_per_interval=1
            ),
            "video_url_changed": ThrottleConfig(
                strategy=ThrottleStrategy.DEBOUNCE,
                interval_ms=500,  # Wait 500ms after last change
                max_events_per_interval=1
            ),
            "search_query_changed": ThrottleConfig(
                strategy=ThrottleStrategy.DEBOUNCE,
                interval_ms=300,  # Wait 300ms after last keystroke
                max_events_per_interval=1
            ),
            "window_resized": ThrottleConfig(
                strategy=ThrottleStrategy.THROTTLE,
                interval_ms=50,  # Max 20 times per second
                max_events_per_interval=1
            )
        }
        
        for event_name, config in default_configs.items():
            self._throttle_configs[event_name] = config
    
    def _setup_default_sequences(self) -> None:
        """Set up default event sequences for common workflows"""
        # Video download sequence
        download_sequence = EventSequence(
            sequence_id="video_download_workflow",
            name="Video Download Workflow",
            steps=[
                EventSequenceStep(
                    step_id="url_entered",
                    event_name="video_url_changed",
                    event_type="legacy"
                ),
                EventSequenceStep(
                    step_id="info_fetched",
                    event_name="video_info_updated",
                    event_type="legacy",
                    timeout_ms=10000
                ),
                EventSequenceStep(
                    step_id="download_started",
                    event_name="download_requested",
                    event_type="legacy"
                ),
                EventSequenceStep(
                    step_id="download_completed",
                    event_name="download_completed",
                    event_type="legacy",
                    timeout_ms=300000  # 5 minutes
                )
            ],
            timeout_ms=600000  # 10 minutes total
        )
        
        self._sequences[download_sequence.sequence_id] = download_sequence
    
    def _setup_core_event_subscriptions(self) -> None:
        """Set up subscriptions to core v2.0 events"""
        if not self._core_event_bus:
            return
        
        # Subscribe to relevant core events
        core_events = [
            EventType.DOWNLOAD_REQUESTED,
            EventType.DOWNLOAD_PROGRESS_UPDATED,
            EventType.DOWNLOAD_COMPLETED,
            EventType.DOWNLOAD_FAILED,
            EventType.CONTENT_METADATA_UPDATED,
            EventType.ERROR_OCCURRED
        ]
        
        for event_type in core_events:
            self._core_event_bus.subscribe(event_type, self._handle_core_event)
    
    def _setup_component_event_subscriptions(self) -> None:
        """Set up subscriptions to component events"""
        if not self._component_event_bus:
            return
        
        # Subscribe to all component events for coordination
        self._component_event_bus.event_emitted.connect(self._handle_component_event)
    
    def _handle_core_event(self, event: Event) -> None:
        """Handle core v2.0 events"""
        try:
            event_name = f"core_{event.event_type.value}"
            self.coordinate_event(
                event_name=event_name,
                source_component="core_system",
                data=event.data
            )
        except Exception as e:
            self.logger.error(f"Failed to handle core event {event.event_type}: {e}")
    
    def _handle_component_event(self, event: ComponentEvent) -> None:
        """Handle component events"""
        try:
            self.coordinate_event(
                event_name=f"component_{event.event_type.value}",
                source_component=event.source_component,
                data=event.data,
                target_component=event.target_component
            )
        except Exception as e:
            self.logger.error(f"Failed to handle component event {event.event_type}: {e}")
    
    def _handle_bridge_event(self, event_name: str, data: Any) -> None:
        """Handle events from the bridge coordinator"""
        try:
            self.coordinate_event(
                event_name=f"bridge_{event_name}",
                source_component="event_bridge",
                data=data
            )
        except Exception as e:
            self.logger.error(f"Failed to handle bridge event {event_name}: {e}")
    
    def _handle_bridge_error(self, event_name: str, error_message: str) -> None:
        """Handle errors from the bridge coordinator"""
        self.logger.error(f"Bridge error for event '{event_name}': {error_message}")
        
        self.coordinate_event(
            event_name="bridge_error",
            source_component="event_bridge",
            data={"event_name": event_name, "error": error_message}
        )
    
    def _check_throttle(self, event_name: str, debug_info: EventDebugInfo) -> bool:
        """
        Check if event should be throttled.
        
        Args:
            event_name: Name of the event
            debug_info: Debug information for tracing
            
        Returns:
            True if event should be processed, False if throttled
        """
        if event_name not in self._throttle_configs:
            return True
        
        config = self._throttle_configs[event_name]
        
        if config.strategy == ThrottleStrategy.NONE:
            return True
        
        now = datetime.now()
        queue = self._throttle_queues[event_name]
        
        # Clean old events from queue
        cutoff = now - timedelta(milliseconds=config.interval_ms)
        while queue and queue[0] < cutoff:
            queue.popleft()
        
        if config.strategy == ThrottleStrategy.THROTTLE:
            if len(queue) >= config.max_events_per_interval:
                self._throttle_counts[event_name] += 1
                self.event_throttled.emit(event_name, self._throttle_counts[event_name])
                debug_info.translation_path.append("throttled")
                return False
            
            queue.append(now)
            return True
        
        elif config.strategy == ThrottleStrategy.DEBOUNCE:
            # For debounce, we clear the queue and set a timer
            queue.clear()
            queue.append(now)
            
            # Set up or reset debounce timer
            if event_name in self._throttle_timers:
                self._throttle_timers[event_name].stop()
            
            timer = QTimer()
            timer.timeout.connect(lambda: self._process_debounced_event(event_name, debug_info))
            timer.setSingleShot(True)
            timer.start(config.interval_ms)
            self._throttle_timers[event_name] = timer
            
            return False  # Don't process immediately, wait for debounce
        
        return True
    
    def _process_debounced_event(self, event_name: str, debug_info: EventDebugInfo) -> None:
        """Process a debounced event after the debounce period"""
        try:
            debug_info.translation_path.append("debounced")
            # Re-emit the event for processing
            # This is a simplified approach - in practice, you'd store the event data
            self.logger.debug(f"Processing debounced event: {event_name}")
        except Exception as e:
            self.logger.error(f"Failed to process debounced event '{event_name}': {e}")
    
    def _process_event_sequences(self, event_name: str, source_component: str, data: Any) -> None:
        """Process event against active sequences"""
        with self._lock:
            for sequence_id in list(self._active_sequences):
                sequence = self._sequences[sequence_id]
                
                if sequence.state != EventSequenceState.PROCESSING:
                    continue
                
                current_step = sequence.steps[sequence.current_step_index]
                
                # Check if this event matches the current step
                if self._matches_sequence_step(event_name, source_component, data, current_step):
                    self._advance_sequence(sequence, current_step, data)
    
    def _matches_sequence_step(self, event_name: str, source_component: str, 
                              data: Any, step: EventSequenceStep) -> bool:
        """Check if an event matches a sequence step"""
        # Check event name
        if step.event_name != event_name:
            return False
        
        # Check source component if specified
        if step.expected_source and step.expected_source != source_component:
            return False
        
        # Check condition if specified
        if step.condition and not step.condition(data):
            return False
        
        # Check data validator if specified
        if step.data_validator and not step.data_validator(data):
            return False
        
        return True
    
    def _advance_sequence(self, sequence: EventSequence, step: EventSequenceStep, data: Any) -> None:
        """Advance a sequence to the next step"""
        try:
            # Mark current step as completed
            step.state = EventSequenceState.COMPLETED
            step.received_at = datetime.now()
            step.data = data
            
            # Call step completion callback
            if sequence.on_step_complete:
                sequence.on_step_complete(sequence, step)
            
            # Move to next step
            sequence.current_step_index += 1
            
            # Check if sequence is complete
            if sequence.current_step_index >= len(sequence.steps):
                self._complete_sequence(sequence)
            else:
                # Set up timeout for next step if needed
                next_step = sequence.steps[sequence.current_step_index]
                if next_step.timeout_ms > 0:
                    timer = QTimer()
                    timer.timeout.connect(lambda: self._handle_step_timeout(sequence.sequence_id, next_step.step_id))
                    timer.setSingleShot(True)
                    timer.start(next_step.timeout_ms)
            
        except Exception as e:
            self._fail_sequence(sequence, f"Failed to advance sequence: {e}")
    
    def _complete_sequence(self, sequence: EventSequence) -> None:
        """Complete a sequence successfully"""
        try:
            sequence.state = EventSequenceState.COMPLETED
            sequence.completed_at = datetime.now()
            
            self._active_sequences.discard(sequence.sequence_id)
            
            # Clean up timer
            if sequence.sequence_id in self._sequence_timers:
                self._sequence_timers[sequence.sequence_id].stop()
                del self._sequence_timers[sequence.sequence_id]
            
            # Call completion callback
            if sequence.on_complete:
                sequence.on_complete(sequence)
            
            self._metrics["sequences_completed"] += 1
            self.sequence_completed.emit(sequence.sequence_id, sequence.name)
            self.logger.info(f"Completed event sequence: {sequence.name} ({sequence.sequence_id})")
            
        except Exception as e:
            self.logger.error(f"Failed to complete sequence '{sequence.sequence_id}': {e}")
    
    def _fail_sequence(self, sequence: EventSequence, error: str) -> None:
        """Fail a sequence with an error"""
        try:
            sequence.state = EventSequenceState.FAILED
            sequence.error = error
            
            self._active_sequences.discard(sequence.sequence_id)
            
            # Clean up timer
            if sequence.sequence_id in self._sequence_timers:
                self._sequence_timers[sequence.sequence_id].stop()
                del self._sequence_timers[sequence.sequence_id]
            
            # Call failure callback
            if sequence.on_failure:
                sequence.on_failure(sequence, error)
            
            self._metrics["sequences_failed"] += 1
            self.sequence_failed.emit(sequence.sequence_id, sequence.name, error)
            self.logger.error(f"Failed event sequence: {sequence.name} ({sequence.sequence_id}): {error}")
            
        except Exception as e:
            self.logger.error(f"Failed to handle sequence failure for '{sequence.sequence_id}': {e}")
    
    def _handle_sequence_timeout(self, sequence_id: str) -> None:
        """Handle sequence timeout"""
        if sequence_id in self._sequences:
            sequence = self._sequences[sequence_id]
            self._fail_sequence(sequence, "Sequence timeout")
    
    def _handle_step_timeout(self, sequence_id: str, step_id: str) -> None:
        """Handle step timeout"""
        if sequence_id in self._sequences:
            sequence = self._sequences[sequence_id]
            self._fail_sequence(sequence, f"Step timeout: {step_id}")
    
    def _route_event(self, event_name: str, source_component: str, data: Any, 
                    target_component: Optional[str], debug_info: EventDebugInfo) -> None:
        """Route event to appropriate handlers"""
        try:
            # Add routing info to debug trace
            debug_info.translation_path.append(f"routed_from_{source_component}")
            
            # Route through bridge coordinator if available
            if self._bridge_coordinator:
                self._bridge_coordinator.emit_legacy_event(event_name, data)
                debug_info.translation_path.append("bridge_coordinator")
            
            # Route through component event bus
            if self._component_event_bus and target_component:
                from ui.components.common.events import EventType as ComponentEventType
                # Map to appropriate component event type
                try:
                    comp_event_type = getattr(ComponentEventType, event_name.upper(), None)
                    if comp_event_type:
                        self._component_event_bus.emit_event(
                            comp_event_type, source_component, data or {}, target_component
                        )
                        debug_info.translation_path.append("component_bus")
                except Exception:
                    pass
            
            # Apply custom routing rules
            if event_name in self._event_routing_rules:
                for rule in self._event_routing_rules[event_name]:
                    try:
                        rule(event_name, source_component, data, target_component)
                        debug_info.translation_path.append("custom_rule")
                    except Exception as e:
                        self.logger.error(f"Routing rule failed for '{event_name}': {e}")
            
        except Exception as e:
            debug_info.error = str(e)
            self.logger.error(f"Failed to route event '{event_name}': {e}")
    
    def _cleanup_expired_sequences(self) -> None:
        """Clean up expired sequences"""
        try:
            now = datetime.now()
            expired_sequences = []
            
            with self._lock:
                for sequence_id, sequence in self._sequences.items():
                    if (sequence.state == EventSequenceState.PROCESSING and 
                        sequence.started_at and 
                        (now - sequence.started_at).total_seconds() * 1000 > sequence.timeout_ms):
                        expired_sequences.append(sequence_id)
            
            for sequence_id in expired_sequences:
                sequence = self._sequences[sequence_id]
                self._fail_sequence(sequence, "Sequence expired")
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup expired sequences: {e}")
    
    def _update_metrics(self) -> None:
        """Update performance metrics"""
        try:
            with self._lock:
                # Update component count
                active_components = sum(1 for ref in self._component_registry.values() if ref() is not None)
                self._metrics["component_count"] = active_components
                
                # Calculate average processing time
                if self._event_trace:
                    total_time = sum(event.processing_time_ms for event in self._event_trace 
                                   if event.error is None)
                    successful_events = sum(1 for event in self._event_trace if event.error is None)
                    
                    if successful_events > 0:
                        self._metrics["average_processing_time_ms"] = total_time / successful_events
                
        except Exception as e:
            self.logger.error(f"Failed to update metrics: {e}")


# Global coordinator instance
_global_coordinator: Optional[CrossComponentCoordinator] = None


def get_cross_component_coordinator() -> CrossComponentCoordinator:
    """Get the global cross-component coordinator instance"""
    global _global_coordinator
    if _global_coordinator is None:
        _global_coordinator = CrossComponentCoordinator()
    return _global_coordinator


def initialize_cross_component_coordination(
    bridge_coordinator: Optional[EventBridgeCoordinator] = None
) -> bool:
    """
    Initialize the global cross-component coordination system.
    
    Args:
        bridge_coordinator: Optional bridge coordinator instance
        
    Returns:
        True if initialization successful, False otherwise
    """
    try:
        coordinator = get_cross_component_coordinator()
        return coordinator.initialize(bridge_coordinator=bridge_coordinator)
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to initialize cross-component coordination: {e}")
        return False 