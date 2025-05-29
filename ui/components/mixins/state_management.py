"""
State Management Mixins

Provides reusable state management functionality that components can inherit
to automatically integrate with the ComponentStateManager system.
"""

from typing import Dict, Any, List, Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal
from abc import ABC, abstractmethod

from ..common.component_state_manager import (
    ComponentStateInterface, 
    get_component_state_manager,
    ComponentStateSnapshot,
    ComponentStateChange
)


class StatefulComponentMixin(ComponentStateInterface):
    """
    Mixin that provides state management capabilities to components.
    
    Components inheriting this mixin automatically get:
    - State tracking and persistence
    - State change history
    - State synchronization capabilities
    - Automatic state restoration
    """
    
    # State management signals
    state_changed = pyqtSignal(str, object, object)  # field_name, old_value, new_value
    state_synchronized = pyqtSignal(str, list)  # target_component_id, fields
    state_persisted = pyqtSignal(bool)  # success
    state_restored = pyqtSignal(bool)  # success
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # State management setup
        self._state_manager = get_component_state_manager()
        self._component_id: Optional[str] = None
        self._component_type: str = self.__class__.__name__
        self._state_fields: List[str] = []
        self._state_data: Dict[str, Any] = {}
        self._is_state_dirty: bool = False
        self._auto_register: bool = True
        
        # State change callbacks
        self._state_change_callbacks: List[Callable[[str, Any, Any], None]] = []
        
    def initialize_state_management(self, component_id: str, 
                                  component_type: Optional[str] = None,
                                  auto_register: bool = True) -> bool:
        """Initialize state management for this component"""
        try:
            self._component_id = component_id
            if component_type:
                self._component_type = component_type
            self._auto_register = auto_register
            
            # Initialize state data
            self._state_data = self.get_component_state()
            self._state_fields = list(self._state_data.keys())
            
            # Register with state manager if auto-register is enabled
            if self._auto_register:
                success = self._state_manager.register_component(
                    component_id, self, self._component_type
                )
                
                if success:
                    # Connect state manager signals
                    self._connect_state_manager_signals()
                    
                    # Add state change watcher
                    self._state_manager.add_state_watcher(
                        component_id, self._handle_state_change_notification
                    )
                
                return success
            
            return True
            
        except Exception as e:
            print(f"Error initializing state management for {component_id}: {e}")
            return False
    
    def cleanup_state_management(self, persist_state: bool = True) -> bool:
        """Cleanup state management for this component"""
        try:
            if self._component_id and self._auto_register:
                return self._state_manager.unregister_component(
                    self._component_id, persist_state
                )
            return True
            
        except Exception as e:
            print(f"Error cleaning up state management: {e}")
            return False
    
    # =============================================================================
    # ComponentStateInterface Implementation
    # =============================================================================
    
    def get_component_state(self) -> Dict[str, Any]:
        """Get complete component state - must be implemented by subclasses"""
        return self._state_data.copy()
    
    def set_component_state(self, state: Dict[str, Any]) -> None:
        """Set component state - must be implemented by subclasses"""
        # Update internal state data
        old_state = self._state_data.copy()
        self._state_data.update(state)
        
        # Mark as dirty
        self._is_state_dirty = True
        
        # Notify of changes
        for field, new_value in state.items():
            old_value = old_state.get(field)
            if old_value != new_value:
                self._notify_state_change(field, old_value, new_value)
    
    def get_state_fields(self) -> List[str]:
        """Get list of state field names"""
        return self._state_fields.copy()
    
    def is_state_dirty(self) -> bool:
        """Check if component state has unsaved changes"""
        return self._is_state_dirty
    
    # =============================================================================
    # State Management Operations
    # =============================================================================
    
    def get_state_field(self, field_name: str) -> Any:
        """Get value of a specific state field"""
        return self._state_data.get(field_name)
    
    def set_state_field(self, field_name: str, value: Any, 
                       triggered_by: Optional[str] = None) -> bool:
        """Set value of a specific state field"""
        if not self._component_id:
            # If not registered with state manager, update locally
            old_value = self._state_data.get(field_name)
            self._state_data[field_name] = value
            self._is_state_dirty = True
            self._notify_state_change(field_name, old_value, value)
            return True
        
        return self._state_manager.update_component_field(
            self._component_id, field_name, value, triggered_by
        )
    
    def update_state(self, state: Dict[str, Any], 
                    triggered_by: Optional[str] = None) -> bool:
        """Update multiple state fields"""
        if not self._component_id:
            # If not registered with state manager, update locally
            old_state = self._state_data.copy()
            self._state_data.update(state)
            self._is_state_dirty = True
            
            # Notify of changes
            for field, new_value in state.items():
                old_value = old_state.get(field)
                if old_value != new_value:
                    self._notify_state_change(field, old_value, new_value)
            return True
        
        return self._state_manager.set_component_state(
            self._component_id, state, triggered_by
        )
    
    def clear_state(self) -> bool:
        """Clear all component state"""
        if not self._component_id:
            # If not registered with state manager, clear locally
            old_state = self._state_data.copy()
            self._state_data.clear()
            self._is_state_dirty = True
            self._notify_state_change('*all*', old_state, {})
            return True
        
        return self._state_manager.clear_component_state(self._component_id)
    
    def persist_state(self) -> bool:
        """Persist component state"""
        if not self._component_id:
            return False
        
        return self._state_manager.persist_component_state(self._component_id)
    
    def restore_state(self) -> bool:
        """Restore component state from persistence"""
        if not self._component_id:
            return False
        
        return self._state_manager.restore_component_state(self._component_id)
    
    # =============================================================================
    # State Synchronization
    # =============================================================================
    
    def synchronize_with(self, target_component_id: str, 
                        fields: Optional[List[str]] = None) -> bool:
        """Synchronize this component's state with another component"""
        if not self._component_id:
            return False
        
        return self._state_manager.synchronize_components(
            self._component_id, target_component_id, fields
        )
    
    def add_sync_rule(self, target_component_id: str, fields: List[str]) -> None:
        """Add automatic synchronization rule with another component"""
        if self._component_id:
            self._state_manager.add_synchronization_rule(
                self._component_id, target_component_id, fields
            )
    
    def remove_sync_rule(self, target_component_id: str) -> None:
        """Remove synchronization rule with another component"""
        if self._component_id:
            self._state_manager.remove_synchronization_rule(
                self._component_id, target_component_id
            )
    
    # =============================================================================
    # State History and Snapshots
    # =============================================================================
    
    def create_snapshot(self, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Create a snapshot of current state"""
        if not self._component_id:
            return False
        
        return self._state_manager.create_component_snapshot(
            self._component_id, metadata
        )
    
    def restore_from_snapshot(self, snapshot_index: int = -1) -> bool:
        """Restore state from a snapshot"""
        if not self._component_id:
            return False
        
        return self._state_manager.restore_from_snapshot(
            self._component_id, snapshot_index
        )
    
    def get_state_history(self) -> List[ComponentStateChange]:
        """Get state change history"""
        if not self._component_id:
            return []
        
        return self._state_manager.get_state_history(self._component_id)
    
    def get_snapshots(self) -> List[ComponentStateSnapshot]:
        """Get all state snapshots"""
        if not self._component_id:
            return []
        
        return self._state_manager.get_component_snapshots(self._component_id)
    
    # =============================================================================
    # State Change Management
    # =============================================================================
    
    def add_state_change_callback(self, callback: Callable[[str, Any, Any], None]) -> None:
        """Add callback to be notified of state changes"""
        self._state_change_callbacks.append(callback)
    
    def remove_state_change_callback(self, callback: Callable) -> None:
        """Remove state change callback"""
        try:
            self._state_change_callbacks.remove(callback)
        except ValueError:
            pass
    
    def _notify_state_change(self, field_name: str, old_value: Any, new_value: Any) -> None:
        """Notify all callbacks of state change"""
        # Emit signal
        self.state_changed.emit(field_name, old_value, new_value)
        
        # Call callbacks
        for callback in self._state_change_callbacks:
            try:
                callback(field_name, old_value, new_value)
            except Exception as e:
                print(f"Error in state change callback: {e}")
    
    def _handle_state_change_notification(self, component_id: str, field_name: str, 
                                        old_value: Any, new_value: Any) -> None:
        """Handle state change notifications from state manager"""
        self._notify_state_change(field_name, old_value, new_value)
    
    def _connect_state_manager_signals(self) -> None:
        """Connect to state manager signals"""
        if self._component_id:
            # Connect state persistence signals
            self._state_manager.state_persisted.connect(
                lambda comp_id, success: self._handle_state_persisted(comp_id, success)
            )
            self._state_manager.state_restored.connect(
                lambda comp_id, success: self._handle_state_restored(comp_id, success)
            )
            self._state_manager.state_synchronized.connect(
                lambda source_id, target_id, fields: self._handle_state_synchronized(source_id, target_id, fields)
            )
    
    def _handle_state_persisted(self, component_id: str, success: bool) -> None:
        """Handle state persistence completion"""
        if component_id == self._component_id:
            if success:
                self._is_state_dirty = False
            self.state_persisted.emit(success)
    
    def _handle_state_restored(self, component_id: str, success: bool) -> None:
        """Handle state restoration completion"""
        if component_id == self._component_id:
            if success:
                self._is_state_dirty = False
            self.state_restored.emit(success)
    
    def _handle_state_synchronized(self, source_id: str, target_id: str, fields: List[str]) -> None:
        """Handle state synchronization completion"""
        if source_id == self._component_id:
            self.state_synchronized.emit(target_id, fields)


class FilterableStateMixin(StatefulComponentMixin):
    """
    Enhanced state mixin for components that support filtering.
    
    Provides additional state management for:
    - Active filters
    - Filter history
    - Search queries
    - Filter state synchronization
    """
    
    # Filter-specific signals
    filter_applied = pyqtSignal(dict)  # filter_config
    filter_cleared = pyqtSignal(str)  # filter_field
    search_applied = pyqtSignal(str, list)  # query, columns
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter state data
        self._filter_state: Dict[str, Any] = {
            'active_filters': {},
            'search_query': '',
            'search_columns': [],
            'filter_history': []
        }
    
    def get_component_state(self) -> Dict[str, Any]:
        """Get component state including filter state"""
        base_state = super().get_component_state()
        base_state.update(self._filter_state)
        return base_state
    
    def set_component_state(self, state: Dict[str, Any]) -> None:
        """Set component state including filter state"""
        # Update filter state
        for field in self._filter_state.keys():
            if field in state:
                self._filter_state[field] = state[field]
        
        # Call parent implementation
        super().set_component_state(state)
    
    def get_state_fields(self) -> List[str]:
        """Get state fields including filter fields"""
        base_fields = super().get_state_fields()
        filter_fields = list(self._filter_state.keys())
        return base_fields + filter_fields
    
    # Filter-specific state management
    def get_active_filters(self) -> Dict[str, Any]:
        """Get currently active filters"""
        return self._filter_state['active_filters'].copy()
    
    def set_active_filters(self, filters: Dict[str, Any]) -> bool:
        """Set active filters"""
        return self.set_state_field('active_filters', filters, 'filter_update')
    
    def add_filter(self, field: str, filter_config: Dict[str, Any]) -> bool:
        """Add a single filter"""
        active_filters = self.get_active_filters()
        active_filters[field] = filter_config
        success = self.set_active_filters(active_filters)
        
        if success:
            self.filter_applied.emit(filter_config)
        
        return success
    
    def remove_filter(self, field: str) -> bool:
        """Remove a specific filter"""
        active_filters = self.get_active_filters()
        if field in active_filters:
            del active_filters[field]
            success = self.set_active_filters(active_filters)
            
            if success:
                self.filter_cleared.emit(field)
            
            return success
        
        return True
    
    def clear_all_filters(self) -> bool:
        """Clear all active filters"""
        success = self.set_active_filters({})
        
        if success:
            self.filter_cleared.emit('*all*')
        
        return success
    
    def get_search_query(self) -> str:
        """Get current search query"""
        return self._filter_state['search_query']
    
    def set_search_query(self, query: str, columns: Optional[List[int]] = None) -> bool:
        """Set search query and columns"""
        state_update = {'search_query': query}
        if columns is not None:
            state_update['search_columns'] = columns
        
        success = self.update_state(state_update, 'search_update')
        
        if success:
            self.search_applied.emit(query, columns or self._filter_state['search_columns'])
        
        return success


class SelectableStateMixin(StatefulComponentMixin):
    """
    Enhanced state mixin for components that support item selection.
    
    Provides additional state management for:
    - Selected items
    - Selection history
    - Multi-selection modes
    - Selection synchronization
    """
    
    # Selection-specific signals
    selection_changed = pyqtSignal(list, list)  # selected_items, deselected_items
    selection_cleared = pyqtSignal()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Selection state data
        self._selection_state: Dict[str, Any] = {
            'selected_items': [],
            'selection_mode': 'multi',  # 'single', 'multi', 'extended'
            'last_selected': None,
            'selection_history': []
        }
    
    def get_component_state(self) -> Dict[str, Any]:
        """Get component state including selection state"""
        base_state = super().get_component_state()
        base_state.update(self._selection_state)
        return base_state
    
    def set_component_state(self, state: Dict[str, Any]) -> None:
        """Set component state including selection state"""
        # Update selection state
        for field in self._selection_state.keys():
            if field in state:
                self._selection_state[field] = state[field]
        
        # Call parent implementation
        super().set_component_state(state)
    
    def get_state_fields(self) -> List[str]:
        """Get state fields including selection fields"""
        base_fields = super().get_state_fields()
        selection_fields = list(self._selection_state.keys())
        return base_fields + selection_fields
    
    # Selection-specific state management
    def get_selected_items(self) -> List[Any]:
        """Get currently selected items"""
        return self._selection_state['selected_items'].copy()
    
    def set_selected_items(self, items: List[Any]) -> bool:
        """Set selected items"""
        old_selection = self.get_selected_items()
        success = self.set_state_field('selected_items', items, 'selection_update')
        
        if success:
            # Calculate differences
            old_set = set(old_selection)
            new_set = set(items)
            newly_selected = list(new_set - old_set)
            newly_deselected = list(old_set - new_set)
            
            if newly_selected or newly_deselected:
                self.selection_changed.emit(newly_selected, newly_deselected)
        
        return success
    
    def add_to_selection(self, items: List[Any]) -> bool:
        """Add items to selection"""
        current_selection = self.get_selected_items()
        new_selection = list(set(current_selection + items))
        return self.set_selected_items(new_selection)
    
    def remove_from_selection(self, items: List[Any]) -> bool:
        """Remove items from selection"""
        current_selection = self.get_selected_items()
        new_selection = [item for item in current_selection if item not in items]
        return self.set_selected_items(new_selection)
    
    def clear_selection(self) -> bool:
        """Clear all selected items"""
        success = self.set_selected_items([])
        
        if success:
            self.selection_cleared.emit()
        
        return success
    
    def get_selection_mode(self) -> str:
        """Get current selection mode"""
        return self._selection_state['selection_mode']
    
    def set_selection_mode(self, mode: str) -> bool:
        """Set selection mode"""
        if mode in ['single', 'multi', 'extended']:
            return self.set_state_field('selection_mode', mode, 'mode_change')
        return False 