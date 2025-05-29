"""
Component State Management System

Advanced state management system specifically designed for UI components,
providing fine-grained state control, inter-component synchronization,
and integration with the existing TabStateManager system.
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Set, Callable, Union
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
import logging

from .tab_state_manager import TabStateManager, TabStateSnapshot
from .events import get_event_bus, EventType, ComponentEvent
from .interfaces import StateManagerInterface


@dataclass
class ComponentStateSnapshot:
    """Snapshot of component state at a specific point in time"""
    component_id: str
    component_type: str
    timestamp: datetime
    state_data: Dict[str, Any]
    metadata: Dict[str, Any]
    parent_component: Optional[str] = None
    version: str = "1.0"


@dataclass
class ComponentStateChange:
    """Record of a component state change"""
    component_id: str
    timestamp: datetime
    field_name: str
    old_value: Any
    new_value: Any
    change_type: str  # 'set', 'update', 'clear', 'sync'
    triggered_by: Optional[str] = None


class ComponentStateInterface(ABC):
    """Interface for components that support state management"""
    
    @abstractmethod
    def get_component_state(self) -> Dict[str, Any]:
        """Get complete component state"""
        pass
    
    @abstractmethod
    def set_component_state(self, state: Dict[str, Any]) -> None:
        """Set component state"""
        pass
    
    @abstractmethod
    def get_state_fields(self) -> List[str]:
        """Get list of state field names"""
        pass
    
    @abstractmethod
    def is_state_dirty(self) -> bool:
        """Check if component state has unsaved changes"""
        pass


class ComponentStateManager(QObject):
    """
    Advanced state management system for UI components providing:
    - Individual component state tracking
    - Inter-component state synchronization
    - State change history and rollback
    - Automatic state persistence
    - Component lifecycle integration
    """
    
    # Signals for component state events
    component_state_changed = pyqtSignal(str, str, object, object)  # component_id, field, old_value, new_value
    state_synchronized = pyqtSignal(str, str, list)  # source_component, target_component, fields
    state_persisted = pyqtSignal(str, bool)  # component_id, success
    state_restored = pyqtSignal(str, bool)  # component_id, success
    conflict_detected = pyqtSignal(str, dict)  # component_id, conflict_info
    
    def __init__(self, tab_state_manager: Optional[TabStateManager] = None):
        super().__init__()
        
        # Core state storage
        self._component_states: Dict[str, Dict[str, Any]] = {}
        self._component_types: Dict[str, str] = {}
        self._state_history: Dict[str, List[ComponentStateChange]] = {}
        self._state_snapshots: Dict[str, List[ComponentStateSnapshot]] = {}
        
        # Component registration
        self._registered_components: Dict[str, ComponentStateInterface] = {}
        self._component_dependencies: Dict[str, Set[str]] = {}
        self._state_synchronization_rules: Dict[str, Dict[str, List[str]]] = {}
        
        # State tracking
        self._dirty_components: Set[str] = set()
        self._locked_components: Set[str] = set()
        self._state_watchers: Dict[str, List[Callable]] = {}
        
        # Configuration
        self._max_history_per_component = 50
        self._max_snapshots_per_component = 10
        self._auto_persist_interval = 10  # seconds
        self._enable_conflict_detection = True
        
        # Integration with tab state manager
        self._tab_state_manager = tab_state_manager
        
        # Event bus integration
        self._event_bus = get_event_bus()
        self._setup_event_subscriptions()
        
        # Auto-persistence timer
        self._auto_persist_timer = QTimer()
        self._auto_persist_timer.timeout.connect(self._auto_persist_dirty_components)
        self._auto_persist_timer.start(self._auto_persist_interval * 1000)
        
        # Logging
        self._logger = logging.getLogger(__name__)
    
    def _setup_event_subscriptions(self):
        """Subscribe to relevant component events"""
        self._event_bus.subscribe(EventType.COMPONENT_CREATED, self._handle_component_created)
        self._event_bus.subscribe(EventType.COMPONENT_DESTROYED, self._handle_component_destroyed)
        self._event_bus.subscribe(EventType.TAB_ACTIVATED, self._handle_tab_activated)
        self._event_bus.subscribe(EventType.TAB_DEACTIVATED, self._handle_tab_deactivated)
    
    # =============================================================================
    # Component Registration and Lifecycle
    # =============================================================================
    
    def register_component(self, component_id: str, component: ComponentStateInterface, 
                          component_type: str, parent_component: Optional[str] = None) -> bool:
        """Register a component for state management"""
        try:
            if component_id in self._registered_components:
                self._logger.warning(f"Component {component_id} already registered")
                return False
            
            # Register component
            self._registered_components[component_id] = component
            self._component_types[component_id] = component_type
            self._component_states[component_id] = component.get_component_state()
            self._state_history[component_id] = []
            self._state_snapshots[component_id] = []
            self._state_watchers[component_id] = []
            
            # Setup dependencies
            if parent_component:
                if parent_component not in self._component_dependencies:
                    self._component_dependencies[parent_component] = set()
                self._component_dependencies[parent_component].add(component_id)
            
            # Create initial snapshot
            self._create_component_snapshot(component_id, {'event': 'registration'})
            
            self._logger.info(f"Registered component: {component_id} ({component_type})")
            return True
            
        except Exception as e:
            self._logger.error(f"Error registering component {component_id}: {e}")
            return False
    
    def unregister_component(self, component_id: str, persist_state: bool = True) -> bool:
        """Unregister a component from state management"""
        try:
            if component_id not in self._registered_components:
                return False
            
            # Persist state if requested
            if persist_state and component_id in self._dirty_components:
                self.persist_component_state(component_id)
            
            # Cleanup state tracking
            self._component_states.pop(component_id, None)
            self._component_types.pop(component_id, None)
            self._registered_components.pop(component_id, None)
            self._state_history.pop(component_id, None)
            self._state_snapshots.pop(component_id, None)
            self._state_watchers.pop(component_id, None)
            self._dirty_components.discard(component_id)
            self._locked_components.discard(component_id)
            
            # Clean up dependencies
            for parent, children in self._component_dependencies.items():
                children.discard(component_id)
            self._component_dependencies.pop(component_id, None)
            
            self._logger.info(f"Unregistered component: {component_id}")
            return True
            
        except Exception as e:
            self._logger.error(f"Error unregistering component {component_id}: {e}")
            return False
    
    # =============================================================================
    # State Management Operations
    # =============================================================================
    
    def get_component_state(self, component_id: str) -> Optional[Dict[str, Any]]:
        """Get current state for a component"""
        return self._component_states.get(component_id)
    
    def set_component_state(self, component_id: str, state: Dict[str, Any], 
                           triggered_by: Optional[str] = None) -> bool:
        """Set state for a component"""
        try:
            if component_id not in self._registered_components:
                return False
            
            if component_id in self._locked_components:
                self._logger.warning(f"Component {component_id} is locked")
                return False
            
            # Get current state for change tracking
            current_state = self._component_states[component_id]
            
            # Record individual field changes
            for field, new_value in state.items():
                old_value = current_state.get(field)
                if old_value != new_value:
                    change = ComponentStateChange(
                        component_id=component_id,
                        timestamp=datetime.now(),
                        field_name=field,
                        old_value=old_value,
                        new_value=new_value,
                        change_type='set',
                        triggered_by=triggered_by
                    )
                    self._add_state_change(component_id, change)
                    
                    # Emit signal for this field change
                    self.component_state_changed.emit(component_id, field, old_value, new_value)
            
            # Update state
            self._component_states[component_id].update(state)
            self._mark_component_dirty(component_id)
            
            # Update component
            component = self._registered_components[component_id]
            component.set_component_state(self._component_states[component_id])
            
            # Check for synchronization rules
            self._apply_synchronization_rules(component_id, list(state.keys()))
            
            return True
            
        except Exception as e:
            self._logger.error(f"Error setting state for {component_id}: {e}")
            return False
    
    def update_component_field(self, component_id: str, field_name: str, value: Any,
                             triggered_by: Optional[str] = None) -> bool:
        """Update a single field in component state"""
        return self.set_component_state(component_id, {field_name: value}, triggered_by)
    
    def clear_component_state(self, component_id: str) -> bool:
        """Clear all state for a component"""
        try:
            if component_id not in self._registered_components:
                return False
            
            if component_id in self._locked_components:
                self._logger.warning(f"Component {component_id} is locked")
                return False
            
            # Get component to determine initial state
            component = self._registered_components[component_id]
            initial_state = {}
            
            # Create change record
            change = ComponentStateChange(
                component_id=component_id,
                timestamp=datetime.now(),
                field_name='*all*',
                old_value=self._component_states[component_id].copy(),
                new_value=initial_state,
                change_type='clear'
            )
            self._add_state_change(component_id, change)
            
            # Clear state
            self._component_states[component_id] = initial_state
            component.set_component_state(initial_state)
            self._mark_component_dirty(component_id)
            
            return True
            
        except Exception as e:
            self._logger.error(f"Error clearing state for {component_id}: {e}")
            return False
    
    # =============================================================================
    # State Synchronization
    # =============================================================================
    
    def synchronize_components(self, source_component_id: str, target_component_id: str,
                             fields: Optional[List[str]] = None) -> bool:
        """Synchronize state between two components"""
        try:
            if (source_component_id not in self._registered_components or 
                target_component_id not in self._registered_components):
                return False
            
            if target_component_id in self._locked_components:
                self._logger.warning(f"Target component {target_component_id} is locked")
                return False
            
            source_state = self._component_states[source_component_id]
            
            # Determine fields to synchronize
            if fields is None:
                target_component = self._registered_components[target_component_id]
                available_fields = target_component.get_state_fields()
                fields = [f for f in source_state.keys() if f in available_fields]
            
            # Synchronize specified fields
            sync_data = {field: source_state[field] for field in fields if field in source_state}
            
            if sync_data:
                success = self.set_component_state(
                    target_component_id, 
                    sync_data, 
                    triggered_by=f"sync_from_{source_component_id}"
                )
                
                if success:
                    self.state_synchronized.emit(source_component_id, target_component_id, fields)
                
                return success
            
            return True
            
        except Exception as e:
            self._logger.error(f"Error synchronizing {source_component_id} -> {target_component_id}: {e}")
            return False
    
    def add_synchronization_rule(self, source_component_id: str, target_component_id: str,
                               fields: List[str]) -> None:
        """Add automatic synchronization rule between components"""
        if source_component_id not in self._state_synchronization_rules:
            self._state_synchronization_rules[source_component_id] = {}
        
        self._state_synchronization_rules[source_component_id][target_component_id] = fields
    
    def remove_synchronization_rule(self, source_component_id: str, target_component_id: str) -> None:
        """Remove synchronization rule between components"""
        if (source_component_id in self._state_synchronization_rules and
            target_component_id in self._state_synchronization_rules[source_component_id]):
            del self._state_synchronization_rules[source_component_id][target_component_id]
    
    def _apply_synchronization_rules(self, source_component_id: str, changed_fields: List[str]) -> None:
        """Apply automatic synchronization rules for changed fields"""
        if source_component_id not in self._state_synchronization_rules:
            return
        
        for target_component_id, sync_fields in self._state_synchronization_rules[source_component_id].items():
            # Check if any of the changed fields should be synchronized
            fields_to_sync = [f for f in changed_fields if f in sync_fields]
            
            if fields_to_sync:
                self.synchronize_components(source_component_id, target_component_id, fields_to_sync)
    
    # =============================================================================
    # State Persistence and Snapshots
    # =============================================================================
    
    def create_component_snapshot(self, component_id: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Create a snapshot of component state"""
        return self._create_component_snapshot(component_id, metadata)
    
    def _create_component_snapshot(self, component_id: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Internal method to create component snapshot"""
        try:
            if component_id not in self._registered_components:
                return False
            
            snapshot = ComponentStateSnapshot(
                component_id=component_id,
                component_type=self._component_types[component_id],
                timestamp=datetime.now(),
                state_data=self._component_states[component_id].copy(),
                metadata=metadata or {}
            )
            
            # Add to snapshots list
            self._state_snapshots[component_id].append(snapshot)
            
            # Maintain snapshot limit
            if len(self._state_snapshots[component_id]) > self._max_snapshots_per_component:
                self._state_snapshots[component_id].pop(0)
            
            return True
            
        except Exception as e:
            self._logger.error(f"Error creating snapshot for {component_id}: {e}")
            return False
    
    def restore_from_snapshot(self, component_id: str, snapshot_index: int = -1) -> bool:
        """Restore component state from a snapshot"""
        try:
            if (component_id not in self._state_snapshots or 
                not self._state_snapshots[component_id]):
                return False
            
            snapshots = self._state_snapshots[component_id]
            if abs(snapshot_index) > len(snapshots):
                return False
            
            snapshot = snapshots[snapshot_index]
            return self.set_component_state(
                component_id, 
                snapshot.state_data, 
                triggered_by=f"restore_snapshot_{snapshot.timestamp}"
            )
            
        except Exception as e:
            self._logger.error(f"Error restoring from snapshot for {component_id}: {e}")
            return False
    
    def persist_component_state(self, component_id: str) -> bool:
        """Persist component state (integrate with tab state manager if available)"""
        try:
            if component_id not in self._registered_components:
                return False
            
            # If tab state manager is available, use it for persistence
            if self._tab_state_manager:
                # For components, we'll store state as part of tab state
                # This is a simplified approach - in a real implementation,
                # you might want a separate component persistence mechanism
                tab_state = self._tab_state_manager.get_state("current_tab")
                if not tab_state:
                    tab_state = {}
                
                if 'component_states' not in tab_state:
                    tab_state['component_states'] = {}
                
                tab_state['component_states'][component_id] = self._component_states[component_id]
                self._tab_state_manager.set_state("current_tab", tab_state)
            
            self._dirty_components.discard(component_id)
            self.state_persisted.emit(component_id, True)
            return True
            
        except Exception as e:
            self._logger.error(f"Error persisting state for {component_id}: {e}")
            self.state_persisted.emit(component_id, False)
            return False
    
    def restore_component_state(self, component_id: str) -> bool:
        """Restore component state from persistence"""
        try:
            if component_id not in self._registered_components:
                return False
            
            # Try to restore from tab state manager
            if self._tab_state_manager:
                tab_state = self._tab_state_manager.get_state("current_tab")
                if (tab_state and 'component_states' in tab_state and 
                    component_id in tab_state['component_states']):
                    
                    restored_state = tab_state['component_states'][component_id]
                    success = self.set_component_state(
                        component_id, 
                        restored_state, 
                        triggered_by="restore_from_persistence"
                    )
                    
                    self.state_restored.emit(component_id, success)
                    return success
            
            self.state_restored.emit(component_id, False)
            return False
            
        except Exception as e:
            self._logger.error(f"Error restoring state for {component_id}: {e}")
            self.state_restored.emit(component_id, False)
            return False
    
    def _auto_persist_dirty_components(self) -> None:
        """Auto-persist all dirty components"""
        for component_id in list(self._dirty_components):
            self.persist_component_state(component_id)
    
    # =============================================================================
    # State Watching and Callbacks
    # =============================================================================
    
    def add_state_watcher(self, component_id: str, callback: Callable[[str, str, Any, Any], None]) -> bool:
        """Add a callback to watch state changes for a component"""
        if component_id not in self._registered_components:
            return False
        
        self._state_watchers[component_id].append(callback)
        return True
    
    def remove_state_watcher(self, component_id: str, callback: Callable) -> bool:
        """Remove a state watcher callback"""
        if component_id in self._state_watchers:
            try:
                self._state_watchers[component_id].remove(callback)
                return True
            except ValueError:
                pass
        return False
    
    def _notify_state_watchers(self, component_id: str, field_name: str, old_value: Any, new_value: Any) -> None:
        """Notify all watchers of a state change"""
        if component_id in self._state_watchers:
            for callback in self._state_watchers[component_id]:
                try:
                    callback(component_id, field_name, old_value, new_value)
                except Exception as e:
                    self._logger.error(f"Error in state watcher callback: {e}")
    
    # =============================================================================
    # State History and Change Tracking
    # =============================================================================
    
    def get_state_history(self, component_id: str) -> List[ComponentStateChange]:
        """Get state change history for a component"""
        return self._state_history.get(component_id, [])
    
    def get_component_snapshots(self, component_id: str) -> List[ComponentStateSnapshot]:
        """Get all snapshots for a component"""
        return self._state_snapshots.get(component_id, [])
    
    def _add_state_change(self, component_id: str, change: ComponentStateChange) -> None:
        """Add a state change to history"""
        if component_id not in self._state_history:
            self._state_history[component_id] = []
        
        self._state_history[component_id].append(change)
        
        # Maintain history limit
        if len(self._state_history[component_id]) > self._max_history_per_component:
            self._state_history[component_id].pop(0)
        
        # Notify watchers
        self._notify_state_watchers(component_id, change.field_name, change.old_value, change.new_value)
    
    # =============================================================================
    # Component Locking and Utilities
    # =============================================================================
    
    def lock_component(self, component_id: str) -> None:
        """Lock component state to prevent modifications"""
        self._locked_components.add(component_id)
    
    def unlock_component(self, component_id: str) -> None:
        """Unlock component state to allow modifications"""
        self._locked_components.discard(component_id)
    
    def is_component_locked(self, component_id: str) -> bool:
        """Check if component is locked"""
        return component_id in self._locked_components
    
    def is_component_dirty(self, component_id: str) -> bool:
        """Check if component has unsaved changes"""
        return component_id in self._dirty_components
    
    def get_dirty_components(self) -> List[str]:
        """Get list of components with unsaved changes"""
        return list(self._dirty_components)
    
    def _mark_component_dirty(self, component_id: str) -> None:
        """Mark component as having unsaved changes"""
        self._dirty_components.add(component_id)
    
    # =============================================================================
    # Event Handlers
    # =============================================================================
    
    def _handle_component_created(self, event: ComponentEvent) -> None:
        """Handle component creation events"""
        pass  # Components register themselves
    
    def _handle_component_destroyed(self, event: ComponentEvent) -> None:
        """Handle component destruction events"""
        component_id = event.data.get('component_id')
        if component_id:
            self.unregister_component(component_id)
    
    def _handle_tab_activated(self, event: ComponentEvent) -> None:
        """Handle tab activation - restore component states"""
        tab_id = event.data.get('tab_id')
        if tab_id:
            # Restore states for components in this tab
            for component_id in self._registered_components:
                if component_id.startswith(f"{tab_id}_"):
                    self.restore_component_state(component_id)
    
    def _handle_tab_deactivated(self, event: ComponentEvent) -> None:
        """Handle tab deactivation - persist component states"""
        tab_id = event.data.get('tab_id')
        if tab_id:
            # Persist states for components in this tab
            for component_id in self._registered_components:
                if component_id.startswith(f"{tab_id}_") and component_id in self._dirty_components:
                    self.persist_component_state(component_id)
    
    # =============================================================================
    # Debug and Monitoring
    # =============================================================================
    
    def get_manager_status(self) -> Dict[str, Any]:
        """Get comprehensive status information"""
        return {
            'registered_components': list(self._registered_components.keys()),
            'component_types': self._component_types,
            'dirty_components': list(self._dirty_components),
            'locked_components': list(self._locked_components),
            'total_history_entries': sum(len(history) for history in self._state_history.values()),
            'total_snapshots': sum(len(snapshots) for snapshots in self._state_snapshots.values()),
            'synchronization_rules': self._state_synchronization_rules,
            'auto_persist_interval': self._auto_persist_interval,
            'conflict_detection_enabled': self._enable_conflict_detection
        }
    
    def cleanup(self) -> None:
        """Cleanup manager resources"""
        try:
            # Stop auto-persist timer
            self._auto_persist_timer.stop()
            
            # Persist all dirty components
            for component_id in list(self._dirty_components):
                self.persist_component_state(component_id)
            
            # Clear all data structures
            self._component_states.clear()
            self._component_types.clear()
            self._registered_components.clear()
            self._state_history.clear()
            self._state_snapshots.clear()
            self._component_dependencies.clear()
            self._state_synchronization_rules.clear()
            self._dirty_components.clear()
            self._locked_components.clear()
            self._state_watchers.clear()
            
            self._logger.info("Component state manager cleanup completed")
            
        except Exception as e:
            self._logger.error(f"Error during component state manager cleanup: {e}")


# Global component state manager instance
_component_state_manager: Optional[ComponentStateManager] = None

def get_component_state_manager() -> ComponentStateManager:
    """Get global component state manager instance"""
    global _component_state_manager
    if _component_state_manager is None:
        _component_state_manager = ComponentStateManager()
    return _component_state_manager

def initialize_component_state_manager(tab_state_manager: Optional[TabStateManager] = None) -> ComponentStateManager:
    """Initialize global component state manager"""
    global _component_state_manager
    _component_state_manager = ComponentStateManager(tab_state_manager)
    return _component_state_manager 