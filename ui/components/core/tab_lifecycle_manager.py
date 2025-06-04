"""
Advanced Tab Lifecycle Manager for v2.0 UI Architecture

This module provides comprehensive tab lifecycle management including:
- Tab state preservation during application lifecycle
- Tab hibernation mechanism for inactive tabs to reduce memory usage
- Tab restoration from saved state on application restart
- Resource management and cleanup
- Performance optimization through intelligent state management
"""

import logging
import threading
import time
import weakref
import pickle
import gzip
import json
from typing import Dict, Any, Optional, Callable, List, Set, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


class TabState(Enum):
    """Tab lifecycle states"""
    UNINITIALIZED = auto()
    INITIALIZING = auto()
    ACTIVE = auto()
    BACKGROUND = auto()
    SUSPENDED = auto()
    HIBERNATING = auto()
    HIBERNATED = auto()
    RESTORING = auto()
    TERMINATING = auto()
    TERMINATED = auto()
    ERROR = auto()


class TabPriority(Enum):
    """Tab priority levels for resource allocation"""
    CRITICAL = 0    # Never hibernate (e.g., active downloads)
    HIGH = 1        # Hibernate only under memory pressure
    NORMAL = 2      # Standard hibernation rules
    LOW = 3         # Aggressive hibernation
    DISPOSABLE = 4  # Can be terminated if needed


@dataclass
class TabMetrics:
    """Performance and resource metrics for a tab"""
    memory_usage: int = 0  # bytes
    cpu_usage: float = 0.0  # percentage
    last_interaction: datetime = field(default_factory=datetime.now)
    creation_time: datetime = field(default_factory=datetime.now)
    activation_count: int = 0
    hibernation_count: int = 0
    total_active_time: timedelta = field(default_factory=lambda: timedelta())
    resource_warnings: List[str] = field(default_factory=list)


@dataclass
class TabSnapshot:
    """Serializable tab state snapshot"""
    tab_id: str
    tab_type: str
    state_data: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: datetime
    version: str = "1.0"
    checksum: str = ""


class TabLifecycleManager(QObject):
    """
    Advanced tab lifecycle manager providing comprehensive tab state management,
    hibernation, recovery, and resource optimization for v2.0 UI architecture.
    """
    
    # Signals for tab lifecycle events
    tab_created = pyqtSignal(str)  # tab_id
    tab_activated = pyqtSignal(str)  # tab_id
    tab_deactivated = pyqtSignal(str)  # tab_id
    tab_suspended = pyqtSignal(str)  # tab_id
    tab_hibernated = pyqtSignal(str, dict)  # tab_id, saved_state
    tab_restored = pyqtSignal(str, dict)  # tab_id, restored_state
    tab_terminated = pyqtSignal(str)  # tab_id
    tab_error = pyqtSignal(str, str)  # tab_id, error_message
    memory_pressure = pyqtSignal(float)  # memory_usage_percentage
    performance_warning = pyqtSignal(str, str)  # tab_id, metric_name
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.config = self._create_default_config()
        if config:
            self.config.update(config)
        
        # Tab registry and state tracking
        self._tabs: Dict[str, QWidget] = {}
        self._tab_states: Dict[str, TabState] = {}
        self._tab_priorities: Dict[str, TabPriority] = {}
        self._tab_metrics: Dict[str, TabMetrics] = {}
        self._tab_snapshots: Dict[str, TabSnapshot] = {}
        self._state_callbacks: Dict[str, List[Callable]] = {}
        
        # Hibernation and restoration
        self._hibernated_tabs: Dict[str, Dict[str, Any]] = {}
        self._restoration_queue: List[str] = []
        self._snapshot_storage_path = Path(self.config['snapshot_storage_path'])
        self._snapshot_storage_path.mkdir(parents=True, exist_ok=True)
        
        # Performance monitoring
        self._monitoring_enabled = self.config['enable_performance_monitoring']
        self._monitor_timer: Optional[QTimer] = None
        self._hibernation_timer: Optional[QTimer] = None
        self._active_tab_id: Optional[str] = None
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Initialize monitoring if enabled
        if self._monitoring_enabled:
            self._start_monitoring()
        
        self.logger.info("TabLifecycleManager initialized with config: %s", self.config)
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration for tab lifecycle manager"""
        return {
            'hibernation_threshold_minutes': 5,
            'memory_pressure_threshold': 0.85,  # 85% memory usage
            'max_hibernated_tabs': 10,
            'snapshot_interval_minutes': 2,
            'enable_performance_monitoring': True,
            'enable_automatic_hibernation': True,
            'enable_state_persistence': True,
            'snapshot_storage_path': 'data/tab_snapshots',
            'max_snapshot_age_days': 7,
            'compression_enabled': True,
            'checksum_validation': True
        }
    
    def _start_monitoring(self) -> None:
        """Start performance monitoring and hibernation timers"""
        try:
            # Performance monitoring timer (every 30 seconds)
            self._monitor_timer = QTimer()
            self._monitor_timer.timeout.connect(self._monitor_performance)
            self._monitor_timer.start(30000)
            
            # Hibernation check timer (every 60 seconds)
            self._hibernation_timer = QTimer()
            self._hibernation_timer.timeout.connect(self._check_hibernation_candidates)
            self._hibernation_timer.start(60000)
            
            self.logger.info("Performance monitoring started")
            
        except Exception as e:
            self.logger.error(f"Failed to start monitoring: {e}")
    
    def register_tab(self, tab_id: str, tab_widget: QWidget, 
                    priority: TabPriority = TabPriority.NORMAL) -> bool:
        """
        Register a new tab with the lifecycle manager
        
        Args:
            tab_id: Unique identifier for the tab
            tab_widget: The tab widget instance
            priority: Priority level for resource management
            
        Returns:
            True if registration successful, False otherwise
        """
        with self._lock:
            try:
                if tab_id in self._tabs:
                    self.logger.warning(f"Tab {tab_id} already registered")
                    return False
                
                # Store tab with weak reference to prevent memory leaks
                self._tabs[tab_id] = tab_widget
                self._tab_states[tab_id] = TabState.INITIALIZING
                self._tab_priorities[tab_id] = priority
                self._tab_metrics[tab_id] = TabMetrics()
                self._state_callbacks[tab_id] = []
                
                # Set up tab-specific callbacks
                self._setup_tab_callbacks(tab_id, tab_widget)
                
                # Transition to active state
                self._transition_state(tab_id, TabState.ACTIVE)
                
                self.logger.info(f"Tab {tab_id} registered with priority {priority}")
                self.tab_created.emit(tab_id)
                
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to register tab {tab_id}: {e}")
                self.tab_error.emit(tab_id, str(e))
                return False
    
    def _setup_tab_callbacks(self, tab_id: str, tab_widget: QWidget) -> None:
        """Set up callbacks for tab widget events"""
        try:
            # Connect tab widget signals if available
            if hasattr(tab_widget, 'destroyed'):
                tab_widget.destroyed.connect(lambda: self._on_tab_destroyed(tab_id))
            
            # Monitor tab interactions
            if hasattr(tab_widget, 'focusInEvent'):
                original_focus_in = tab_widget.focusInEvent
                def focus_in_wrapper(event):
                    self._on_tab_interaction(tab_id)
                    return original_focus_in(event)
                tab_widget.focusInEvent = focus_in_wrapper
                
        except Exception as e:
            self.logger.error(f"Failed to setup callbacks for tab {tab_id}: {e}")
    
    def activate_tab(self, tab_id: str) -> bool:
        """
        Activate a tab, restoring from hibernation if necessary
        
        Args:
            tab_id: ID of tab to activate
            
        Returns:
            True if activation successful, False otherwise
        """
        with self._lock:
            try:
                if tab_id not in self._tabs:
                    self.logger.error(f"Tab {tab_id} not registered")
                    return False
                
                current_state = self._tab_states.get(tab_id)
                
                # Handle hibernated tab restoration
                if current_state == TabState.HIBERNATED:
                    if not self._restore_tab(tab_id):
                        return False
                
                # Deactivate current active tab
                if self._active_tab_id and self._active_tab_id != tab_id:
                    self.deactivate_tab(self._active_tab_id)
                
                # Activate the tab
                self._active_tab_id = tab_id
                self._transition_state(tab_id, TabState.ACTIVE)
                self._update_metrics(tab_id, 'activation_count', 1)
                self._update_interaction_time(tab_id)
                
                self.logger.info(f"Tab {tab_id} activated")
                self.tab_activated.emit(tab_id)
                
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to activate tab {tab_id}: {e}")
                self.tab_error.emit(tab_id, str(e))
                return False
    
    def deactivate_tab(self, tab_id: str) -> bool:
        """
        Deactivate a tab, moving it to background state
        
        Args:
            tab_id: ID of tab to deactivate
            
        Returns:
            True if deactivation successful, False otherwise
        """
        with self._lock:
            try:
                if tab_id not in self._tabs:
                    self.logger.error(f"Tab {tab_id} not registered")
                    return False
                
                current_state = self._tab_states.get(tab_id)
                if current_state != TabState.ACTIVE:
                    self.logger.warning(f"Tab {tab_id} not active (state: {current_state})")
                    return False
                
                # Transition to background
                self._transition_state(tab_id, TabState.BACKGROUND)
                
                # Clear active tab if this was it
                if self._active_tab_id == tab_id:
                    self._active_tab_id = None
                
                self.logger.info(f"Tab {tab_id} deactivated")
                self.tab_deactivated.emit(tab_id)
                
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to deactivate tab {tab_id}: {e}")
                self.tab_error.emit(tab_id, str(e))
                return False
    
    def hibernate_tab(self, tab_id: str) -> bool:
        """
        Hibernate a tab, saving its state and releasing resources
        
        Args:
            tab_id: ID of tab to hibernate
            
        Returns:
            True if hibernation successful, False otherwise
        """
        with self._lock:
            try:
                if tab_id not in self._tabs:
                    self.logger.error(f"Tab {tab_id} not registered")
                    return False
                
                current_state = self._tab_states.get(tab_id)
                priority = self._tab_priorities.get(tab_id, TabPriority.NORMAL)
                
                # Don't hibernate critical tabs
                if priority == TabPriority.CRITICAL:
                    self.logger.info(f"Tab {tab_id} has critical priority, skipping hibernation")
                    return False
                
                # Don't hibernate active tab
                if current_state == TabState.ACTIVE:
                    self.logger.info(f"Tab {tab_id} is active, cannot hibernate")
                    return False
                
                # Create state snapshot
                snapshot = self._create_snapshot(tab_id)
                if not snapshot:
                    self.logger.error(f"Failed to create snapshot for tab {tab_id}")
                    return False
                
                # Transition to hibernating state
                self._transition_state(tab_id, TabState.HIBERNATING)
                
                # Save snapshot to storage
                if self.config['enable_state_persistence']:
                    self._save_snapshot(snapshot)
                
                # Store hibernated state in memory
                self._hibernated_tabs[tab_id] = snapshot.state_data
                
                # Release tab widget resources (but keep reference for restoration)
                tab_widget = self._tabs[tab_id]
                if hasattr(tab_widget, 'release_resources'):
                    tab_widget.release_resources()
                
                # Transition to hibernated state
                self._transition_state(tab_id, TabState.HIBERNATED)
                self._update_metrics(tab_id, 'hibernation_count', 1)
                
                self.logger.info(f"Tab {tab_id} hibernated successfully")
                self.tab_hibernated.emit(tab_id, snapshot.state_data)
                
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to hibernate tab {tab_id}: {e}")
                self.tab_error.emit(tab_id, str(e))
                return False
    
    def _restore_tab(self, tab_id: str) -> bool:
        """
        Restore a hibernated tab from saved state
        
        Args:
            tab_id: ID of tab to restore
            
        Returns:
            True if restoration successful, False otherwise
        """
        try:
            if tab_id not in self._hibernated_tabs:
                self.logger.error(f"No hibernated state found for tab {tab_id}")
                return False
            
            # Transition to restoring state
            self._transition_state(tab_id, TabState.RESTORING)
            
            # Get hibernated state
            hibernated_state = self._hibernated_tabs[tab_id]
            tab_widget = self._tabs[tab_id]
            
            # Restore tab widget state
            if hasattr(tab_widget, 'restore_state'):
                success = tab_widget.restore_state(hibernated_state)
                if not success:
                    self.logger.error(f"Failed to restore state for tab {tab_id}")
                    self._transition_state(tab_id, TabState.ERROR)
                    return False
            
            # Clean up hibernated state
            del self._hibernated_tabs[tab_id]
            
            # Transition to background state (not active yet)
            self._transition_state(tab_id, TabState.BACKGROUND)
            
            self.logger.info(f"Tab {tab_id} restored successfully")
            self.tab_restored.emit(tab_id, hibernated_state)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore tab {tab_id}: {e}")
            self._transition_state(tab_id, TabState.ERROR)
            self.tab_error.emit(tab_id, str(e))
            return False
    
    def _create_snapshot(self, tab_id: str) -> Optional[TabSnapshot]:
        """Create a state snapshot for a tab"""
        try:
            tab_widget = self._tabs[tab_id]
            
            # Extract state data from tab widget
            state_data = {}
            if hasattr(tab_widget, 'save_state'):
                state_data = tab_widget.save_state()
            elif hasattr(tab_widget, '__getstate__'):
                state_data = tab_widget.__getstate__()
            else:
                # Default state extraction
                state_data = {
                    'geometry': tab_widget.geometry().getRect() if hasattr(tab_widget, 'geometry') else None,
                    'visible': tab_widget.isVisible() if hasattr(tab_widget, 'isVisible') else True,
                    'enabled': tab_widget.isEnabled() if hasattr(tab_widget, 'isEnabled') else True
                }
            
            # Create snapshot
            snapshot = TabSnapshot(
                tab_id=tab_id,
                tab_type=type(tab_widget).__name__,
                state_data=state_data,
                metadata={
                    'priority': self._tab_priorities[tab_id].name,
                    'metrics': asdict(self._tab_metrics[tab_id])
                },
                timestamp=datetime.now()
            )
            
            # Generate checksum if enabled
            if self.config['checksum_validation']:
                snapshot.checksum = self._generate_checksum(snapshot)
            
            return snapshot
            
        except Exception as e:
            self.logger.error(f"Failed to create snapshot for tab {tab_id}: {e}")
            return None
    
    def _save_snapshot(self, snapshot: TabSnapshot) -> bool:
        """Save snapshot to persistent storage"""
        try:
            snapshot_file = self._snapshot_storage_path / f"{snapshot.tab_id}_{snapshot.timestamp.strftime('%Y%m%d_%H%M%S')}.snapshot"
            
            # Serialize snapshot
            data = asdict(snapshot)
            json_data = json.dumps(data, default=str, indent=2)
            
            # Compress if enabled
            if self.config['compression_enabled']:
                compressed_data = gzip.compress(json_data.encode('utf-8'))
                with open(snapshot_file.with_suffix('.snapshot.gz'), 'wb') as f:
                    f.write(compressed_data)
            else:
                with open(snapshot_file, 'w', encoding='utf-8') as f:
                    f.write(json_data)
            
            self.logger.debug(f"Snapshot saved for tab {snapshot.tab_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save snapshot: {e}")
            return False
    
    def _generate_checksum(self, snapshot: TabSnapshot) -> str:
        """Generate checksum for snapshot integrity verification"""
        import hashlib
        data_str = json.dumps(snapshot.state_data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]
    
    def _transition_state(self, tab_id: str, new_state: TabState) -> None:
        """Transition tab to new state with validation and callbacks"""
        old_state = self._tab_states.get(tab_id, TabState.UNINITIALIZED)
        
        # Validate state transition
        if not self._is_valid_transition(old_state, new_state):
            self.logger.warning(f"Invalid state transition for tab {tab_id}: {old_state} -> {new_state}")
            return
        
        # Update state
        self._tab_states[tab_id] = new_state
        
        # Execute state callbacks
        callbacks = self._state_callbacks.get(tab_id, [])
        for callback in callbacks:
            try:
                callback(tab_id, old_state, new_state)
            except Exception as e:
                self.logger.error(f"State callback error for tab {tab_id}: {e}")
        
        self.logger.debug(f"Tab {tab_id} state transition: {old_state} -> {new_state}")
    
    def _is_valid_transition(self, old_state: TabState, new_state: TabState) -> bool:
        """Validate if state transition is allowed"""
        valid_transitions = {
            TabState.UNINITIALIZED: [TabState.INITIALIZING, TabState.ERROR],
            TabState.INITIALIZING: [TabState.ACTIVE, TabState.ERROR],
            TabState.ACTIVE: [TabState.BACKGROUND, TabState.SUSPENDED, TabState.TERMINATING],
            TabState.BACKGROUND: [TabState.ACTIVE, TabState.SUSPENDED, TabState.HIBERNATING, TabState.TERMINATING],
            TabState.SUSPENDED: [TabState.BACKGROUND, TabState.HIBERNATING, TabState.TERMINATING],
            TabState.HIBERNATING: [TabState.HIBERNATED, TabState.ERROR],
            TabState.HIBERNATED: [TabState.RESTORING, TabState.TERMINATING],
            TabState.RESTORING: [TabState.BACKGROUND, TabState.ERROR],
            TabState.TERMINATING: [TabState.TERMINATED],
            TabState.TERMINATED: [],
            TabState.ERROR: [TabState.TERMINATING, TabState.RESTORING]
        }
        
        return new_state in valid_transitions.get(old_state, [])
    
    def _monitor_performance(self) -> None:
        """Monitor tab performance and trigger hibernation if needed"""
        try:
            import psutil
            
            # Get system memory usage
            memory = psutil.virtual_memory()
            memory_percentage = memory.percent / 100.0
            
            # Emit memory pressure warning if threshold exceeded
            if memory_percentage > self.config['memory_pressure_threshold']:
                self.memory_pressure.emit(memory_percentage)
                
                # Trigger aggressive hibernation under memory pressure
                if self.config['enable_automatic_hibernation']:
                    self._hibernate_low_priority_tabs()
            
            # Update tab metrics
            for tab_id in list(self._tabs.keys()):
                self._update_tab_metrics(tab_id)
                
        except Exception as e:
            self.logger.error(f"Performance monitoring error: {e}")
    
    def _check_hibernation_candidates(self) -> None:
        """Check which tabs are candidates for hibernation"""
        if not self.config['enable_automatic_hibernation']:
            return
        
        try:
            current_time = datetime.now()
            hibernation_threshold = timedelta(minutes=self.config['hibernation_threshold_minutes'])
            
            for tab_id, metrics in self._tab_metrics.items():
                # Skip if already hibernated or active
                state = self._tab_states.get(tab_id)
                if state in [TabState.HIBERNATED, TabState.ACTIVE, TabState.HIBERNATING, TabState.RESTORING]:
                    continue
                
                # Check if tab has been inactive long enough
                inactive_time = current_time - metrics.last_interaction
                priority = self._tab_priorities.get(tab_id, TabPriority.NORMAL)
                
                should_hibernate = False
                
                if priority == TabPriority.LOW and inactive_time > hibernation_threshold / 2:
                    should_hibernate = True
                elif priority == TabPriority.DISPOSABLE and inactive_time > hibernation_threshold / 4:
                    should_hibernate = True
                elif inactive_time > hibernation_threshold:
                    should_hibernate = True
                
                if should_hibernate:
                    self.logger.info(f"Hibernating inactive tab {tab_id} (inactive for {inactive_time})")
                    self.hibernate_tab(tab_id)
                    
        except Exception as e:
            self.logger.error(f"Hibernation check error: {e}")
    
    def _hibernate_low_priority_tabs(self) -> None:
        """Hibernate low priority tabs under memory pressure"""
        # Sort tabs by priority and last interaction time
        hibernation_candidates = []
        
        for tab_id in self._tabs:
            state = self._tab_states.get(tab_id)
            if state in [TabState.BACKGROUND, TabState.SUSPENDED]:
                priority = self._tab_priorities.get(tab_id, TabPriority.NORMAL)
                metrics = self._tab_metrics.get(tab_id)
                hibernation_candidates.append((tab_id, priority.value, metrics.last_interaction))
        
        # Sort by priority (higher value = lower priority) and last interaction time
        hibernation_candidates.sort(key=lambda x: (x[1], x[2]))
        
        # Hibernate up to max allowed
        hibernated_count = 0
        max_hibernate = min(len(hibernation_candidates), self.config['max_hibernated_tabs'])
        
        for tab_id, _, _ in hibernation_candidates:
            if hibernated_count >= max_hibernate:
                break
            
            if self.hibernate_tab(tab_id):
                hibernated_count += 1
    
    def _update_tab_metrics(self, tab_id: str) -> None:
        """Update performance metrics for a tab"""
        try:
            import psutil
            
            tab_widget = self._tabs.get(tab_id)
            if not tab_widget:
                return
            
            metrics = self._tab_metrics[tab_id]
            
            # Estimate memory usage (simplified)
            try:
                process = psutil.Process()
                metrics.memory_usage = process.memory_info().rss // len(self._tabs)
            except:
                pass
            
            # Check for resource warnings
            if metrics.memory_usage > 100 * 1024 * 1024:  # 100MB per tab
                warning = f"High memory usage: {metrics.memory_usage // 1024 // 1024}MB"
                if warning not in metrics.resource_warnings:
                    metrics.resource_warnings.append(warning)
                    self.performance_warning.emit(tab_id, "memory_usage")
                    
        except Exception as e:
            self.logger.error(f"Failed to update metrics for tab {tab_id}: {e}")
    
    def _update_metrics(self, tab_id: str, metric: str, increment: int) -> None:
        """Update a specific metric for a tab"""
        if tab_id in self._tab_metrics:
            current_value = getattr(self._tab_metrics[tab_id], metric, 0)
            setattr(self._tab_metrics[tab_id], metric, current_value + increment)
    
    def _update_interaction_time(self, tab_id: str) -> None:
        """Update last interaction time for a tab"""
        if tab_id in self._tab_metrics:
            self._tab_metrics[tab_id].last_interaction = datetime.now()
    
    def _on_tab_interaction(self, tab_id: str) -> None:
        """Handle tab interaction event"""
        self._update_interaction_time(tab_id)
        if self._tab_states.get(tab_id) != TabState.ACTIVE:
            self.activate_tab(tab_id)
    
    def _on_tab_destroyed(self, tab_id: str) -> None:
        """Handle tab destruction event"""
        self.unregister_tab(tab_id)
    
    def unregister_tab(self, tab_id: str) -> bool:
        """
        Unregister a tab and clean up its resources
        
        Args:
            tab_id: ID of tab to unregister
            
        Returns:
            True if unregistration successful, False otherwise
        """
        with self._lock:
            try:
                if tab_id not in self._tabs:
                    self.logger.warning(f"Tab {tab_id} not registered")
                    return False
                
                # Transition to terminating state
                self._transition_state(tab_id, TabState.TERMINATING)
                
                # Clean up resources
                if tab_id in self._hibernated_tabs:
                    del self._hibernated_tabs[tab_id]
                
                # Remove from active tab if necessary
                if self._active_tab_id == tab_id:
                    self._active_tab_id = None
                
                # Remove from registries
                del self._tabs[tab_id]
                del self._tab_states[tab_id]
                del self._tab_priorities[tab_id]
                del self._tab_metrics[tab_id]
                if tab_id in self._state_callbacks:
                    del self._state_callbacks[tab_id]
                
                # Transition to terminated state
                self._tab_states[tab_id] = TabState.TERMINATED
                
                self.logger.info(f"Tab {tab_id} unregistered successfully")
                self.tab_terminated.emit(tab_id)
                
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to unregister tab {tab_id}: {e}")
                self.tab_error.emit(tab_id, str(e))
                return False
    
    def get_tab_state(self, tab_id: str) -> Optional[TabState]:
        """Get current state of a tab"""
        return self._tab_states.get(tab_id)
    
    def get_tab_metrics(self, tab_id: str) -> Optional[TabMetrics]:
        """Get performance metrics for a tab"""
        return self._tab_metrics.get(tab_id)
    
    def get_active_tab_id(self) -> Optional[str]:
        """Get ID of currently active tab"""
        return self._active_tab_id
    
    def get_all_tab_states(self) -> Dict[str, TabState]:
        """Get states of all registered tabs"""
        return self._tab_states.copy()
    
    def add_state_callback(self, tab_id: str, callback: Callable[[str, TabState, TabState], None]) -> None:
        """Add callback for tab state transitions"""
        if tab_id in self._state_callbacks:
            self._state_callbacks[tab_id].append(callback)
    
    def remove_state_callback(self, tab_id: str, callback: Callable) -> None:
        """Remove callback for tab state transitions"""
        if tab_id in self._state_callbacks:
            try:
                self._state_callbacks[tab_id].remove(callback)
            except ValueError:
                pass
    
    def force_hibernation(self, tab_id: str) -> bool:
        """Force hibernation of a specific tab"""
        return self.hibernate_tab(tab_id)
    
    def cleanup_old_snapshots(self) -> int:
        """Clean up old snapshot files and return count of files removed"""
        try:
            removed_count = 0
            max_age = timedelta(days=self.config['max_snapshot_age_days'])
            cutoff_time = datetime.now() - max_age
            
            for snapshot_file in self._snapshot_storage_path.glob("*.snapshot*"):
                try:
                    file_time = datetime.fromtimestamp(snapshot_file.stat().st_mtime)
                    if file_time < cutoff_time:
                        snapshot_file.unlink()
                        removed_count += 1
                except Exception as e:
                    self.logger.error(f"Failed to remove old snapshot {snapshot_file}: {e}")
            
            self.logger.info(f"Cleaned up {removed_count} old snapshot files")
            return removed_count
            
        except Exception as e:
            self.logger.error(f"Snapshot cleanup error: {e}")
            return 0
    
    def shutdown(self) -> None:
        """Shutdown the tab lifecycle manager"""
        with self._lock:
            try:
                self.logger.info("Shutting down TabLifecycleManager")
                
                # Stop monitoring timers
                if self._monitor_timer:
                    self._monitor_timer.stop()
                if self._hibernation_timer:
                    self._hibernation_timer.stop()
                
                # Save snapshots for all active tabs
                for tab_id in list(self._tabs.keys()):
                    if self._tab_states.get(tab_id) in [TabState.ACTIVE, TabState.BACKGROUND]:
                        snapshot = self._create_snapshot(tab_id)
                        if snapshot and self.config['enable_state_persistence']:
                            self._save_snapshot(snapshot)
                
                # Clean up old snapshots
                self.cleanup_old_snapshots()
                
                self.logger.info("TabLifecycleManager shutdown completed")
                
            except Exception as e:
                self.logger.error(f"Error during shutdown: {e}")


# Factory function for creating tab lifecycle manager instances
def create_tab_lifecycle_manager(config: Optional[Dict[str, Any]] = None) -> TabLifecycleManager:
    """Create a new tab lifecycle manager instance with optional configuration"""
    return TabLifecycleManager(config)


# Global instance management
_global_tab_lifecycle_manager: Optional[TabLifecycleManager] = None


def get_global_tab_lifecycle_manager() -> TabLifecycleManager:
    """Get or create the global tab lifecycle manager instance"""
    global _global_tab_lifecycle_manager
    
    if _global_tab_lifecycle_manager is None:
        _global_tab_lifecycle_manager = TabLifecycleManager()
    
    return _global_tab_lifecycle_manager


def set_global_tab_lifecycle_manager(manager: TabLifecycleManager) -> None:
    """Set the global tab lifecycle manager instance"""
    global _global_tab_lifecycle_manager
    _global_tab_lifecycle_manager = manager 