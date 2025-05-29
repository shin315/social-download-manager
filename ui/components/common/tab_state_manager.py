"""
Tab State Management System

This module provides advanced state management capabilities for tabs,
including persistence, inter-tab communication, state synchronization,
and recovery mechanisms.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from dataclasses import asdict, dataclass
from abc import ABC, abstractmethod

from .models import TabState, TabConfig
from .events import get_event_bus, EventType, ComponentEvent
from .interfaces import StateManagerInterface


@dataclass
class TabStateSnapshot:
    """Snapshot of tab state at a specific point in time"""
    tab_id: str
    timestamp: datetime
    state_data: Dict[str, Any]
    metadata: Dict[str, Any]
    version: str = "1.0"


@dataclass
class TabStateTransaction:
    """Transaction record for state changes"""
    transaction_id: str
    tab_id: str
    timestamp: datetime
    action: str  # 'save', 'restore', 'sync', 'clear'
    state_before: Optional[Dict[str, Any]]
    state_after: Optional[Dict[str, Any]]
    success: bool
    error_message: Optional[str] = None


class TabStatePersistence(ABC):
    """Abstract interface for tab state persistence"""
    
    @abstractmethod
    def save_state(self, tab_id: str, state: TabState) -> bool:
        """Save tab state to persistent storage"""
        pass
    
    @abstractmethod
    def load_state(self, tab_id: str) -> Optional[TabState]:
        """Load tab state from persistent storage"""
        pass
    
    @abstractmethod
    def delete_state(self, tab_id: str) -> bool:
        """Delete tab state from persistent storage"""
        pass
    
    @abstractmethod
    def list_saved_states(self) -> List[str]:
        """List all saved tab state IDs"""
        pass


class FileBasedStatePersistence(TabStatePersistence):
    """File-based implementation of tab state persistence"""
    
    def __init__(self, storage_path: str = "data/tab_states"):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
    
    def _get_state_file_path(self, tab_id: str) -> str:
        """Get file path for tab state"""
        safe_tab_id = "".join(c for c in tab_id if c.isalnum() or c in "_-")
        return os.path.join(self.storage_path, f"{safe_tab_id}_state.json")
    
    def save_state(self, tab_id: str, state: TabState) -> bool:
        """Save tab state to JSON file"""
        try:
            state_data = {
                'videos': state.videos,
                'filtered_videos': state.filtered_videos,
                'selected_items': list(state.selected_items),
                'active_filters': {str(k): asdict(v) for k, v in state.active_filters.items()},
                'sort_config': asdict(state.sort_config),
                'loading': state.loading,
                'processing_count': state.processing_count,
                'timestamp': datetime.now().isoformat()
            }
            
            file_path = self._get_state_file_path(tab_id)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Error saving tab state for {tab_id}: {e}")
            return False
    
    def load_state(self, tab_id: str) -> Optional[TabState]:
        """Load tab state from JSON file"""
        try:
            file_path = self._get_state_file_path(tab_id)
            if not os.path.exists(file_path):
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
            
            # Reconstruct TabState object
            state = TabState()
            state.videos = state_data.get('videos', [])
            state.filtered_videos = state_data.get('filtered_videos', [])
            state.selected_items = set(state_data.get('selected_items', []))
            # Note: active_filters and sort_config reconstruction would need proper object creation
            state.loading = state_data.get('loading', False)
            state.processing_count = state_data.get('processing_count', 0)
            
            return state
        except Exception as e:
            print(f"Error loading tab state for {tab_id}: {e}")
            return None
    
    def delete_state(self, tab_id: str) -> bool:
        """Delete tab state file"""
        try:
            file_path = self._get_state_file_path(tab_id)
            if os.path.exists(file_path):
                os.remove(file_path)
            return True
        except Exception as e:
            print(f"Error deleting tab state for {tab_id}: {e}")
            return False
    
    def list_saved_states(self) -> List[str]:
        """List all saved tab state IDs"""
        try:
            files = os.listdir(self.storage_path)
            tab_ids = []
            for file in files:
                if file.endswith('_state.json'):
                    tab_id = file.replace('_state.json', '')
                    tab_ids.append(tab_id)
            return tab_ids
        except Exception as e:
            print(f"Error listing saved states: {e}")
            return []


class TabStateManager(QObject, StateManagerInterface):
    """
    Advanced tab state management system providing:
    - State persistence and recovery
    - Inter-tab state synchronization
    - State change tracking and transactions
    - Automatic state snapshots
    - State validation and recovery
    """
    
    # Signals for state management events
    state_saved = pyqtSignal(str, bool)  # tab_id, success
    state_loaded = pyqtSignal(str, bool)  # tab_id, success
    state_synchronized = pyqtSignal(str, str)  # source_tab_id, target_tab_id
    state_conflict_detected = pyqtSignal(str, dict)  # tab_id, conflict_info
    recovery_completed = pyqtSignal(str, bool)  # tab_id, success
    
    def __init__(self, persistence_backend: Optional[TabStatePersistence] = None):
        super().__init__()
        
        # State storage
        self._tab_states: Dict[str, TabState] = {}
        self._state_snapshots: Dict[str, List[TabStateSnapshot]] = {}
        self._transactions: List[TabStateTransaction] = []
        self._state_locks: Set[str] = set()
        
        # Configuration
        self._max_snapshots_per_tab = 10
        self._auto_save_interval = 30  # seconds
        self._transaction_history_limit = 100
        
        # Persistence backend
        self._persistence = persistence_backend or FileBasedStatePersistence()
        
        # Component bus integration
        self._event_bus = get_event_bus()
        self._setup_event_subscriptions()
        
        # Auto-save timer
        self._auto_save_timer = QTimer()
        self._auto_save_timer.timeout.connect(self._auto_save_all_states)
        self._auto_save_timer.start(self._auto_save_interval * 1000)
        
        # State change tracking
        self._dirty_tabs: Set[str] = set()
        self._state_change_callbacks: Dict[str, List[Callable]] = {}
    
    def _setup_event_subscriptions(self):
        """Subscribe to relevant component bus events"""
        self._event_bus.subscribe(EventType.TAB_ACTIVATED, self._handle_tab_activated)
        self._event_bus.subscribe(EventType.TAB_DEACTIVATED, self._handle_tab_deactivated)
        self._event_bus.subscribe(EventType.TAB_DATA_CHANGED, self._handle_tab_data_changed)
        self._event_bus.subscribe(EventType.STATE_CHANGED, self._handle_state_changed)
    
    # =============================================================================
    # StateManagerInterface implementation
    # =============================================================================
    
    def get_state(self, tab_id: str) -> Dict[str, Any]:
        """Get current state for a tab"""
        if tab_id in self._tab_states:
            state = self._tab_states[tab_id]
            return {
                'videos': state.videos,
                'filtered_videos': state.filtered_videos,
                'selected_items': list(state.selected_items),
                'active_filters': state.active_filters,
                'sort_config': state.sort_config,
                'loading': state.loading,
                'processing_count': state.processing_count
            }
        return {}
    
    def set_state(self, tab_id: str, state: Dict[str, Any]) -> None:
        """Set state for a tab"""
        if tab_id in self._state_locks:
            print(f"Tab {tab_id} is locked, cannot set state")
            return
        
        # Convert dict to TabState object
        tab_state = TabState()
        if 'videos' in state:
            tab_state.videos = state['videos']
        if 'filtered_videos' in state:
            tab_state.filtered_videos = state['filtered_videos']
        if 'selected_items' in state:
            tab_state.selected_items = set(state['selected_items'])
        if 'active_filters' in state:
            tab_state.active_filters = state['active_filters']
        if 'sort_config' in state:
            tab_state.sort_config = state['sort_config']
        if 'loading' in state:
            tab_state.loading = state['loading']
        if 'processing_count' in state:
            tab_state.processing_count = state['processing_count']
        
        self._tab_states[tab_id] = tab_state
        self._mark_tab_dirty(tab_id)
        
        # Emit state change event
        self._event_bus.emit_event(
            event_type=EventType.STATE_CHANGED,
            source_component=f"TabStateManager",
            data={'tab_id': tab_id, 'state': state}
        )
    
    def clear_state(self, tab_id: str) -> None:
        """Clear state for a tab"""
        if tab_id in self._state_locks:
            print(f"Tab {tab_id} is locked, cannot clear state")
            return
        
        if tab_id in self._tab_states:
            self._tab_states[tab_id].clear()
            self._mark_tab_dirty(tab_id)
    
    # =============================================================================
    # Advanced State Management
    # =============================================================================
    
    def register_tab(self, tab_id: str, initial_state: Optional[TabState] = None) -> None:
        """Register a new tab with the state manager"""
        if tab_id not in self._tab_states:
            self._tab_states[tab_id] = initial_state or TabState()
            self._state_snapshots[tab_id] = []
            self._state_change_callbacks[tab_id] = []
            
            # Try to load persisted state
            self.load_tab_state(tab_id)
    
    def unregister_tab(self, tab_id: str, save_state: bool = True) -> None:
        """Unregister a tab from the state manager"""
        if save_state and tab_id in self._dirty_tabs:
            self.save_tab_state(tab_id)
        
        # Cleanup
        self._tab_states.pop(tab_id, None)
        self._state_snapshots.pop(tab_id, None)
        self._state_change_callbacks.pop(tab_id, None)
        self._dirty_tabs.discard(tab_id)
        self._state_locks.discard(tab_id)
    
    def save_tab_state(self, tab_id: str) -> bool:
        """Save tab state to persistent storage"""
        if tab_id not in self._tab_states:
            return False
        
        try:
            # Create transaction record
            transaction = TabStateTransaction(
                transaction_id=f"{tab_id}_{datetime.now().timestamp()}",
                tab_id=tab_id,
                timestamp=datetime.now(),
                action='save',
                state_before=None,
                state_after=self.get_state(tab_id),
                success=False
            )
            
            # Save to persistence backend
            success = self._persistence.save_state(tab_id, self._tab_states[tab_id])
            transaction.success = success
            
            if success:
                self._dirty_tabs.discard(tab_id)
                self._create_state_snapshot(tab_id)
            else:
                transaction.error_message = "Persistence backend save failed"
            
            self._add_transaction(transaction)
            self.state_saved.emit(tab_id, success)
            
            return success
            
        except Exception as e:
            transaction.success = False
            transaction.error_message = str(e)
            self._add_transaction(transaction)
            self.state_saved.emit(tab_id, False)
            return False
    
    def load_tab_state(self, tab_id: str) -> bool:
        """Load tab state from persistent storage"""
        try:
            # Create transaction record
            transaction = TabStateTransaction(
                transaction_id=f"{tab_id}_{datetime.now().timestamp()}",
                tab_id=tab_id,
                timestamp=datetime.now(),
                action='load',
                state_before=self.get_state(tab_id) if tab_id in self._tab_states else None,
                state_after=None,
                success=False
            )
            
            # Load from persistence backend
            loaded_state = self._persistence.load_state(tab_id)
            
            if loaded_state:
                self._tab_states[tab_id] = loaded_state
                transaction.state_after = self.get_state(tab_id)
                transaction.success = True
                self._dirty_tabs.discard(tab_id)
            else:
                transaction.error_message = "No saved state found or load failed"
            
            self._add_transaction(transaction)
            self.state_loaded.emit(tab_id, transaction.success)
            
            return transaction.success
            
        except Exception as e:
            transaction.success = False
            transaction.error_message = str(e)
            self._add_transaction(transaction)
            self.state_loaded.emit(tab_id, False)
            return False
    
    def synchronize_tab_states(self, source_tab_id: str, target_tab_id: str, 
                             fields: Optional[List[str]] = None) -> bool:
        """Synchronize state between two tabs"""
        if source_tab_id not in self._tab_states or target_tab_id not in self._tab_states:
            return False
        
        if target_tab_id in self._state_locks:
            print(f"Target tab {target_tab_id} is locked, cannot synchronize")
            return False
        
        try:
            source_state = self._tab_states[source_tab_id]
            target_state = self._tab_states[target_tab_id]
            
            # Synchronize specified fields or all fields
            if fields is None:
                fields = ['videos', 'filtered_videos', 'selected_items', 'active_filters', 'sort_config']
            
            for field in fields:
                if hasattr(source_state, field) and hasattr(target_state, field):
                    setattr(target_state, field, getattr(source_state, field))
            
            self._mark_tab_dirty(target_tab_id)
            self.state_synchronized.emit(source_tab_id, target_tab_id)
            
            return True
            
        except Exception as e:
            print(f"Error synchronizing states: {e}")
            return False
    
    def create_state_snapshot(self, tab_id: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Create a snapshot of current tab state"""
        return self._create_state_snapshot(tab_id, metadata)
    
    def _create_state_snapshot(self, tab_id: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Internal method to create state snapshot"""
        if tab_id not in self._tab_states:
            return False
        
        try:
            snapshot = TabStateSnapshot(
                tab_id=tab_id,
                timestamp=datetime.now(),
                state_data=self.get_state(tab_id),
                metadata=metadata or {}
            )
            
            # Add to snapshots list
            if tab_id not in self._state_snapshots:
                self._state_snapshots[tab_id] = []
            
            self._state_snapshots[tab_id].append(snapshot)
            
            # Maintain snapshot limit
            if len(self._state_snapshots[tab_id]) > self._max_snapshots_per_tab:
                self._state_snapshots[tab_id].pop(0)
            
            return True
            
        except Exception as e:
            print(f"Error creating snapshot for {tab_id}: {e}")
            return False
    
    def restore_from_snapshot(self, tab_id: str, snapshot_index: int = -1) -> bool:
        """Restore tab state from a snapshot"""
        if tab_id not in self._state_snapshots or not self._state_snapshots[tab_id]:
            return False
        
        if tab_id in self._state_locks:
            print(f"Tab {tab_id} is locked, cannot restore")
            return False
        
        try:
            snapshots = self._state_snapshots[tab_id]
            if abs(snapshot_index) > len(snapshots):
                return False
            
            snapshot = snapshots[snapshot_index]
            self.set_state(tab_id, snapshot.state_data)
            
            # Create transaction record
            transaction = TabStateTransaction(
                transaction_id=f"{tab_id}_restore_{datetime.now().timestamp()}",
                tab_id=tab_id,
                timestamp=datetime.now(),
                action='restore',
                state_before=None,
                state_after=snapshot.state_data,
                success=True
            )
            self._add_transaction(transaction)
            
            return True
            
        except Exception as e:
            print(f"Error restoring from snapshot: {e}")
            return False
    
    def get_state_snapshots(self, tab_id: str) -> List[TabStateSnapshot]:
        """Get all snapshots for a tab"""
        return self._state_snapshots.get(tab_id, [])
    
    def lock_tab_state(self, tab_id: str) -> None:
        """Lock tab state to prevent modifications"""
        self._state_locks.add(tab_id)
    
    def unlock_tab_state(self, tab_id: str) -> None:
        """Unlock tab state to allow modifications"""
        self._state_locks.discard(tab_id)
    
    def is_tab_locked(self, tab_id: str) -> bool:
        """Check if tab state is locked"""
        return tab_id in self._state_locks
    
    def is_tab_dirty(self, tab_id: str) -> bool:
        """Check if tab has unsaved changes"""
        return tab_id in self._dirty_tabs
    
    def get_dirty_tabs(self) -> List[str]:
        """Get list of tabs with unsaved changes"""
        return list(self._dirty_tabs)
    
    def _mark_tab_dirty(self, tab_id: str) -> None:
        """Mark tab as having unsaved changes"""
        self._dirty_tabs.add(tab_id)
    
    def _auto_save_all_states(self) -> None:
        """Auto-save all dirty tab states"""
        for tab_id in list(self._dirty_tabs):
            self.save_tab_state(tab_id)
    
    def _add_transaction(self, transaction: TabStateTransaction) -> None:
        """Add transaction to history"""
        self._transactions.append(transaction)
        
        # Maintain transaction history limit
        if len(self._transactions) > self._transaction_history_limit:
            self._transactions.pop(0)
    
    def get_transaction_history(self, tab_id: Optional[str] = None) -> List[TabStateTransaction]:
        """Get transaction history for a tab or all tabs"""
        if tab_id:
            return [t for t in self._transactions if t.tab_id == tab_id]
        return self._transactions
    
    # =============================================================================
    # Event Handlers
    # =============================================================================
    
    def _handle_tab_activated(self, event: ComponentEvent) -> None:
        """Handle tab activation events"""
        tab_id = event.data.get('tab_id')
        if tab_id and tab_id in self._tab_states:
            # Create snapshot on activation
            self._create_state_snapshot(tab_id, {'event': 'activation'})
    
    def _handle_tab_deactivated(self, event: ComponentEvent) -> None:
        """Handle tab deactivation events"""
        tab_id = event.data.get('tab_id')
        if tab_id and tab_id in self._dirty_tabs:
            # Auto-save on deactivation
            self.save_tab_state(tab_id)
    
    def _handle_tab_data_changed(self, event: ComponentEvent) -> None:
        """Handle tab data change events"""
        tab_id = event.data.get('tab_id')
        if tab_id:
            self._mark_tab_dirty(tab_id)
    
    def _handle_state_changed(self, event: ComponentEvent) -> None:
        """Handle general state change events"""
        tab_id = event.data.get('tab_id')
        if tab_id:
            self._mark_tab_dirty(tab_id)
    
    # =============================================================================
    # Recovery and Validation
    # =============================================================================
    
    def validate_tab_state(self, tab_id: str) -> List[str]:
        """Validate tab state and return list of issues"""
        issues = []
        
        if tab_id not in self._tab_states:
            issues.append(f"Tab {tab_id} not registered")
            return issues
        
        state = self._tab_states[tab_id]
        
        # Basic validation
        if not isinstance(state.videos, list):
            issues.append("Videos must be a list")
        
        if not isinstance(state.filtered_videos, list):
            issues.append("Filtered videos must be a list")
        
        if not isinstance(state.selected_items, set):
            issues.append("Selected items must be a set")
        
        if not isinstance(state.processing_count, int) or state.processing_count < 0:
            issues.append("Processing count must be non-negative integer")
        
        return issues
    
    def recover_tab_state(self, tab_id: str) -> bool:
        """Attempt to recover corrupted tab state"""
        try:
            # Try loading from persistence
            if self.load_tab_state(tab_id):
                self.recovery_completed.emit(tab_id, True)
                return True
            
            # Try restoring from snapshot
            if self._state_snapshots.get(tab_id):
                if self.restore_from_snapshot(tab_id):
                    self.recovery_completed.emit(tab_id, True)
                    return True
            
            # Last resort: reset to empty state
            self._tab_states[tab_id] = TabState()
            self._mark_tab_dirty(tab_id)
            self.recovery_completed.emit(tab_id, True)
            return True
            
        except Exception as e:
            print(f"Recovery failed for {tab_id}: {e}")
            self.recovery_completed.emit(tab_id, False)
            return False
    
    def cleanup(self) -> None:
        """Cleanup resources and save all dirty states"""
        # Stop auto-save timer
        self._auto_save_timer.stop()
        
        # Save all dirty states
        for tab_id in list(self._dirty_tabs):
            self.save_tab_state(tab_id)
        
        # Clear subscriptions
        self._event_bus.unsubscribe(EventType.TAB_ACTIVATED, self._handle_tab_activated)
        self._event_bus.unsubscribe(EventType.TAB_DEACTIVATED, self._handle_tab_deactivated)
        self._event_bus.unsubscribe(EventType.TAB_DATA_CHANGED, self._handle_tab_data_changed)
        self._event_bus.unsubscribe(EventType.STATE_CHANGED, self._handle_state_changed) 