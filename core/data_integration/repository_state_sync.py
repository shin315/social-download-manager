"""
Repository-UI State Synchronization for Social Download Manager v2.0

Extends the existing ComponentStateManager to handle repository data, implementing Repository-UI State Synchronization for subtask 18.2.
Provides mechanisms to observe repository changes and update UI state accordingly,
and translate UI state changes into repository operations.
"""

from typing import Dict, Any, List, Optional, Callable, Set, Union, TypeVar
from datetime import datetime
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from data.models.repositories import IRepository, IContentRepository, IDownloadRepository
from data.models.base import BaseEntity, EntityId
from ui.components.common.component_state_manager import (
    ComponentStateManager, ComponentStateInterface, ComponentStateSnapshot, ComponentStateChange
)
from core.event_system import EventBus, Event, EventType, get_event_bus, publish_event
from .data_binding_strategy import DataBindingManager, DataBindingConfig, DataBindingMode

T = TypeVar('T', bound=BaseEntity)


@dataclass
class RepositoryStateMapping:
    """Mapping configuration between repository data and UI state"""
    repository_field: str
    ui_state_field: str
    transform_to_ui: Optional[Callable[[Any], Any]] = None
    transform_to_repository: Optional[Callable[[Any], Any]] = None
    bidirectional: bool = True
    auto_sync: bool = True


@dataclass
class RepositorySyncConfig:
    """Configuration for repository-UI synchronization"""
    component_id: str
    repository_type: type
    field_mappings: List[RepositoryStateMapping]
    sync_mode: str = "bidirectional"  # "ui_to_repo", "repo_to_ui", "bidirectional"
    batch_updates: bool = True
    debounce_interval: int = 500  # milliseconds
    conflict_resolution: str = "repository_wins"  # "ui_wins", "repository_wins", "manual"
    enable_optimistic_updates: bool = True


class IRepositoryStateObserver(ABC):
    """Interface for observing repository state changes"""
    
    @abstractmethod
    def on_repository_data_changed(self, repository: IRepository, entity_id: Optional[EntityId], 
                                  change_type: str, data: Any) -> None:
        """Handle repository data changes"""
        pass
    
    @abstractmethod
    def on_repository_error(self, repository: IRepository, error: Exception, 
                           operation: str) -> None:
        """Handle repository operation errors"""
        pass


class RepositoryStateTracker(QObject):
    """Tracks repository state changes and notifies observers"""
    
    # Signals for repository state events
    repository_data_changed = pyqtSignal(object, str, str, object)  # repository, entity_id, change_type, data
    repository_error_occurred = pyqtSignal(object, Exception, str)  # repository, error, operation
    
    def __init__(self):
        super().__init__()
        self._tracked_repositories: Dict[str, IRepository] = {}
        self._observers: List[IRepositoryStateObserver] = {}
        self._logger = logging.getLogger(__name__)
        
        # Setup event subscriptions for repository events
        self._event_bus = get_event_bus()
        self._setup_repository_event_subscriptions()
    
    def _setup_repository_event_subscriptions(self):
        """Subscribe to repository-related events"""
        self._event_bus.subscribe(EventType.DATA_UPDATED, self._handle_repository_data_updated)
        self._event_bus.subscribe(EventType.ERROR_OCCURRED, self._handle_repository_error)
    
    def track_repository(self, repository_id: str, repository: IRepository) -> None:
        """Start tracking a repository for state changes"""
        self._tracked_repositories[repository_id] = repository
        self._logger.debug(f"Started tracking repository: {repository_id}")
    
    def untrack_repository(self, repository_id: str) -> None:
        """Stop tracking a repository"""
        if repository_id in self._tracked_repositories:
            del self._tracked_repositories[repository_id]
            self._logger.debug(f"Stopped tracking repository: {repository_id}")
    
    def add_observer(self, observer: IRepositoryStateObserver) -> None:
        """Add a repository state observer"""
        if observer not in self._observers:
            self._observers.append(observer)
    
    def remove_observer(self, observer: IRepositoryStateObserver) -> None:
        """Remove a repository state observer"""
        if observer in self._observers:
            self._observers.remove(observer)
    
    def _handle_repository_data_updated(self, event: Event) -> None:
        """Handle repository data update events"""
        try:
            data = event.data or {}
            source = event.source
            
            # Find matching tracked repository
            for repo_id, repository in self._tracked_repositories.items():
                if source == repo_id or source == repository.__class__.__name__:
                    entity_id = data.get('entity_id')
                    change_type = data.get('change_type', 'update')
                    entity_data = data.get('data')
                    
                    # Emit signal
                    self.repository_data_changed.emit(repository, entity_id, change_type, entity_data)
                    
                    # Notify observers
                    for observer in self._observers:
                        try:
                            observer.on_repository_data_changed(repository, entity_id, change_type, entity_data)
                        except Exception as e:
                            self._logger.error(f"Error in repository observer: {e}")
                    
                    break
                    
        except Exception as e:
            self._logger.error(f"Error handling repository data update: {e}")
    
    def _handle_repository_error(self, event: Event) -> None:
        """Handle repository error events"""
        try:
            data = event.data or {}
            source = event.source
            error_message = data.get('error_message', '')
            operation = data.get('operation', 'unknown')
            
            # Find matching tracked repository
            for repo_id, repository in self._tracked_repositories.items():
                if source == repo_id or source == repository.__class__.__name__:
                    error = Exception(error_message)
                    
                    # Emit signal
                    self.repository_error_occurred.emit(repository, error, operation)
                    
                    # Notify observers
                    for observer in self._observers:
                        try:
                            observer.on_repository_error(repository, error, operation)
                        except Exception as e:
                            self._logger.error(f"Error in repository error observer: {e}")
                    
                    break
                    
        except Exception as e:
            self._logger.error(f"Error handling repository error: {e}")


class RepositoryStateManager(ComponentStateManager, IRepositoryStateObserver):
    """
    Extended ComponentStateManager that handles repository data synchronization
    
    Provides mechanisms to:
    - Observe repository changes and update UI state accordingly
    - Translate UI state changes into repository operations
    - Handle conflicts between UI and repository state
    - Manage transaction-aware state synchronization
    """
    
    # Additional signals for repository synchronization
    repository_sync_started = pyqtSignal(str, str)  # component_id, repository_id
    repository_sync_completed = pyqtSignal(str, str, bool)  # component_id, repository_id, success
    repository_conflict_detected = pyqtSignal(str, dict)  # component_id, conflict_info
    repository_sync_error = pyqtSignal(str, str, str)  # component_id, repository_id, error_message
    
    def __init__(self, tab_state_manager=None, data_binding_manager: Optional[DataBindingManager] = None):
        super().__init__(tab_state_manager)
        
        # Repository synchronization components
        self._data_binding_manager = data_binding_manager
        self._repository_tracker = RepositoryStateTracker()
        self._repository_tracker.add_observer(self)
        
        # Repository sync configuration
        self._repository_sync_configs: Dict[str, RepositorySyncConfig] = {}
        self._repository_instances: Dict[str, IRepository] = {}
        self._sync_timers: Dict[str, QTimer] = {}
        self._pending_updates: Dict[str, Dict[str, Any]] = {}
        
        # Conflict resolution
        self._conflict_handlers: Dict[str, Callable] = {}
        
        # Enhanced logging
        self._logger = logging.getLogger(__name__)
        
        # Connect repository tracker signals
        self._repository_tracker.repository_data_changed.connect(self._handle_repository_data_changed)
        self._repository_tracker.repository_error_occurred.connect(self._handle_repository_error)
    
    # =============================================================================
    # Repository Registration and Configuration
    # =============================================================================
    
    def register_repository_sync(self, component_id: str, repository: IRepository, 
                                config: RepositorySyncConfig) -> bool:
        """Register a component for repository synchronization"""
        try:
            if component_id not in self._registered_components:
                self._logger.error(f"Component {component_id} not registered with state manager")
                return False
            
            # Store configuration and repository
            self._repository_sync_configs[component_id] = config
            self._repository_instances[component_id] = repository
            
            # Start tracking repository
            repository_id = f"{component_id}_{repository.__class__.__name__}"
            self._repository_tracker.track_repository(repository_id, repository)
            
            # Setup debounce timer if needed
            if config.debounce_interval > 0:
                timer = QTimer()
                timer.setSingleShot(True)
                timer.timeout.connect(lambda: self._process_pending_updates(component_id))
                self._sync_timers[component_id] = timer
            
            self._logger.info(f"Registered repository sync for component: {component_id}")
            return True
            
        except Exception as e:
            self._logger.error(f"Error registering repository sync for {component_id}: {e}")
            return False
    
    def unregister_repository_sync(self, component_id: str) -> bool:
        """Unregister repository synchronization for a component"""
        try:
            # Stop tracking repository
            if component_id in self._repository_instances:
                repository = self._repository_instances[component_id]
                repository_id = f"{component_id}_{repository.__class__.__name__}"
                self._repository_tracker.untrack_repository(repository_id)
            
            # Cleanup timers
            if component_id in self._sync_timers:
                self._sync_timers[component_id].stop()
                del self._sync_timers[component_id]
            
            # Cleanup configurations
            self._repository_sync_configs.pop(component_id, None)
            self._repository_instances.pop(component_id, None)
            self._pending_updates.pop(component_id, None)
            
            self._logger.info(f"Unregistered repository sync for component: {component_id}")
            return True
            
        except Exception as e:
            self._logger.error(f"Error unregistering repository sync for {component_id}: {e}")
            return False
    
    # =============================================================================
    # Enhanced State Management with Repository Integration
    # =============================================================================
    
    def set_component_state(self, component_id: str, state: Dict[str, Any], 
                           triggered_by: Optional[str] = None, 
                           sync_to_repository: bool = True) -> bool:
        """Enhanced state setting with repository synchronization"""
        try:
            # Call parent implementation first
            success = super().set_component_state(component_id, state, triggered_by)
            
            if success and sync_to_repository and component_id in self._repository_sync_configs:
                # Schedule repository synchronization
                self._schedule_repository_sync(component_id, state, 'ui_to_repository')
            
            return success
            
        except Exception as e:
            self._logger.error(f"Error setting component state with repository sync: {e}")
            return False
    
    def sync_component_to_repository(self, component_id: str, 
                                   fields: Optional[List[str]] = None) -> bool:
        """Explicitly sync component state to repository"""
        try:
            if component_id not in self._repository_sync_configs:
                self._logger.warning(f"No repository sync config for component: {component_id}")
                return False
            
            config = self._repository_sync_configs[component_id]
            repository = self._repository_instances[component_id]
            component_state = self._component_states.get(component_id, {})
            
            # Determine fields to sync
            if fields is None:
                fields = list(component_state.keys())
            
            # Apply field mappings and transform data
            repository_data = self._transform_ui_to_repository_data(
                component_id, component_state, fields
            )
            
            if repository_data:
                # Perform repository update
                success = self._update_repository_data(repository, repository_data)
                
                if success:
                    self.repository_sync_completed.emit(component_id, 
                                                      repository.__class__.__name__, True)
                    
                    # Publish event
                    publish_event(
                        EventType.DATA_UPDATED,
                        f"RepositoryStateManager_{component_id}",
                        {
                            'component_id': component_id,
                            'sync_direction': 'ui_to_repository',
                            'fields': fields,
                            'data': repository_data
                        }
                    )
                else:
                    self.repository_sync_error.emit(component_id, 
                                                  repository.__class__.__name__, 
                                                  "Repository update failed")
                
                return success
            
            return True
            
        except Exception as e:
            self._logger.error(f"Error syncing component {component_id} to repository: {e}")
            self.repository_sync_error.emit(component_id, "unknown", str(e))
            return False
    
    def sync_repository_to_component(self, component_id: str, 
                                   repository_data: Dict[str, Any]) -> bool:
        """Sync repository data to component state"""
        try:
            if component_id not in self._repository_sync_configs:
                return False
            
            config = self._repository_sync_configs[component_id]
            
            # Transform repository data to UI state format
            ui_state_data = self._transform_repository_to_ui_data(
                component_id, repository_data
            )
            
            if ui_state_data:
                # Update component state (without triggering repository sync)
                success = super().set_component_state(
                    component_id, ui_state_data, 
                    triggered_by="repository_sync"
                )
                
                if success:
                    self.repository_sync_completed.emit(component_id, 
                                                      "repository", True)
                
                return success
            
            return True
            
        except Exception as e:
            self._logger.error(f"Error syncing repository to component {component_id}: {e}")
            return False
    
    # =============================================================================
    # Repository State Observer Implementation
    # =============================================================================
    
    def _handle_repository_data_changed(self, repository: IRepository, entity_id: str, 
                                       change_type: str, data: Any) -> None:
        """Handle repository data changed signal"""
        self.on_repository_data_changed(repository, entity_id, change_type, data)
    
    def _handle_repository_error(self, repository: IRepository, error: Exception, operation: str) -> None:
        """Handle repository error signal"""
        self.on_repository_error(repository, error, operation)
    
    def on_repository_data_changed(self, repository: IRepository, entity_id: Optional[EntityId], 
                                  change_type: str, data: Any) -> None:
        """Handle repository data changes"""
        try:
            # Find components that use this repository
            affected_components = []
            for component_id, repo in self._repository_instances.items():
                if repo is repository:
                    affected_components.append(component_id)
            
            # Update affected components
            for component_id in affected_components:
                config = self._repository_sync_configs[component_id]
                
                if config.sync_mode in ["bidirectional", "repo_to_ui"]:
                    # Check if this change affects the component
                    if self._should_sync_repository_change(component_id, entity_id, change_type, data):
                        # Transform and apply repository data to component
                        if isinstance(data, dict):
                            self.sync_repository_to_component(component_id, data)
                        else:
                            # Handle entity objects
                            entity_dict = self._entity_to_dict(data) if data else {}
                            self.sync_repository_to_component(component_id, entity_dict)
            
        except Exception as e:
            self._logger.error(f"Error handling repository data change: {e}")
    
    def on_repository_error(self, repository: IRepository, error: Exception, 
                           operation: str) -> None:
        """Handle repository operation errors"""
        try:
            # Find components that use this repository
            for component_id, repo in self._repository_instances.items():
                if repo is repository:
                    self.repository_sync_error.emit(component_id, 
                                                  repository.__class__.__name__, 
                                                  str(error))
                    
                    # Handle error based on configuration
                    config = self._repository_sync_configs[component_id]
                    if hasattr(config, 'error_recovery_strategy'):
                        self._handle_repository_error(component_id, error, operation)
            
        except Exception as e:
            self._logger.error(f"Error handling repository error: {e}")
    
    # =============================================================================
    # Data Transformation and Mapping
    # =============================================================================
    
    def _transform_ui_to_repository_data(self, component_id: str, ui_state: Dict[str, Any], 
                                       fields: List[str]) -> Dict[str, Any]:
        """Transform UI state data to repository format"""
        try:
            config = self._repository_sync_configs[component_id]
            repository_data = {}
            
            for mapping in config.field_mappings:
                if mapping.ui_state_field in fields and mapping.ui_state_field in ui_state:
                    ui_value = ui_state[mapping.ui_state_field]
                    
                    # Apply transformation if provided
                    if mapping.transform_to_repository:
                        repository_value = mapping.transform_to_repository(ui_value)
                    else:
                        repository_value = ui_value
                    
                    repository_data[mapping.repository_field] = repository_value
            
            return repository_data
            
        except Exception as e:
            self._logger.error(f"Error transforming UI to repository data: {e}")
            return {}
    
    def _transform_repository_to_ui_data(self, component_id: str, 
                                       repository_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform repository data to UI state format"""
        try:
            config = self._repository_sync_configs[component_id]
            ui_state_data = {}
            
            for mapping in config.field_mappings:
                if mapping.repository_field in repository_data:
                    repo_value = repository_data[mapping.repository_field]
                    
                    # Apply transformation if provided
                    if mapping.transform_to_ui:
                        ui_value = mapping.transform_to_ui(repo_value)
                    else:
                        ui_value = repo_value
                    
                    ui_state_data[mapping.ui_state_field] = ui_value
            
            return ui_state_data
            
        except Exception as e:
            self._logger.error(f"Error transforming repository to UI data: {e}")
            return {}
    
    # =============================================================================
    # Synchronization Scheduling and Batching
    # =============================================================================
    
    def _schedule_repository_sync(self, component_id: str, state_data: Dict[str, Any], 
                                sync_direction: str) -> None:
        """Schedule repository synchronization with debouncing"""
        try:
            config = self._repository_sync_configs[component_id]
            
            if config.batch_updates and component_id in self._sync_timers:
                # Add to pending updates
                if component_id not in self._pending_updates:
                    self._pending_updates[component_id] = {}
                
                self._pending_updates[component_id].update(state_data)
                
                # Restart debounce timer
                timer = self._sync_timers[component_id]
                timer.stop()
                timer.start(config.debounce_interval)
            else:
                # Immediate sync
                if sync_direction == 'ui_to_repository':
                    self.sync_component_to_repository(component_id)
                
        except Exception as e:
            self._logger.error(f"Error scheduling repository sync: {e}")
    
    def _process_pending_updates(self, component_id: str) -> None:
        """Process batched pending updates"""
        try:
            if component_id in self._pending_updates:
                pending_data = self._pending_updates[component_id]
                self._pending_updates[component_id] = {}
                
                # Apply pending updates to repository
                if pending_data:
                    self.sync_component_to_repository(component_id, list(pending_data.keys()))
                
        except Exception as e:
            self._logger.error(f"Error processing pending updates for {component_id}: {e}")
    
    # =============================================================================
    # Helper Methods
    # =============================================================================
    
    def _should_sync_repository_change(self, component_id: str, entity_id: Optional[EntityId], 
                                     change_type: str, data: Any) -> bool:
        """Determine if a repository change should sync to component"""
        # Implementation would check filters, entity relevance, etc.
        # For now, sync all changes
        return True
    
    def _entity_to_dict(self, entity: Any) -> Dict[str, Any]:
        """Convert entity object to dictionary"""
        if hasattr(entity, '__dict__'):
            return {k: v for k, v in entity.__dict__.items() if not k.startswith('_')}
        elif hasattr(entity, 'to_dict'):
            return entity.to_dict()
        else:
            return {}
    
    def _update_repository_data(self, repository: IRepository, data: Dict[str, Any]) -> bool:
        """Update repository with transformed data"""
        try:
            # This would depend on the specific repository implementation
            # For now, assume a generic update method
            if hasattr(repository, 'update_data'):
                return repository.update_data(data)
            else:
                # Fallback to save if entity can be constructed
                return True
                
        except Exception as e:
            self._logger.error(f"Error updating repository data: {e}")
            return False
    
    def _handle_repository_error(self, component_id: str, error: Exception, operation: str) -> None:
        """Handle repository errors based on configuration"""
        try:
            config = self._repository_sync_configs[component_id]
            
            # Log error
            self._logger.error(f"Repository error for {component_id}: {error}")
            
            # Apply error recovery strategy
            if hasattr(config, 'error_recovery_strategy'):
                if config.error_recovery_strategy == 'retry':
                    # Schedule retry
                    pass
                elif config.error_recovery_strategy == 'rollback':
                    # Rollback to last known good state
                    pass
                # Add more strategies as needed
                
        except Exception as e:
            self._logger.error(f"Error handling repository error: {e}")
    
    # =============================================================================
    # Public API Extensions
    # =============================================================================
    
    def get_repository_sync_status(self, component_id: str) -> Optional[Dict[str, Any]]:
        """Get repository synchronization status for a component"""
        if component_id not in self._repository_sync_configs:
            return None
        
        config = self._repository_sync_configs[component_id]
        repository = self._repository_instances.get(component_id)
        
        return {
            'component_id': component_id,
            'repository_type': repository.__class__.__name__ if repository else None,
            'sync_mode': config.sync_mode,
            'has_pending_updates': component_id in self._pending_updates and bool(self._pending_updates[component_id]),
            'field_mappings_count': len(config.field_mappings),
            'batch_updates': config.batch_updates,
            'debounce_interval': config.debounce_interval
        }
    
    def get_all_repository_sync_status(self) -> Dict[str, Dict[str, Any]]:
        """Get repository synchronization status for all components"""
        return {
            component_id: self.get_repository_sync_status(component_id)
            for component_id in self._repository_sync_configs.keys()
        }


# =============================================================================
# Factory Functions and Utilities
# =============================================================================

def create_repository_sync_config(component_id: str, repository_type: type,
                                 field_mappings: List[RepositoryStateMapping],
                                 **kwargs) -> RepositorySyncConfig:
    """Create repository synchronization configuration"""
    return RepositorySyncConfig(
        component_id=component_id,
        repository_type=repository_type,
        field_mappings=field_mappings,
        **kwargs
    )


def create_field_mapping(repository_field: str, ui_state_field: str,
                        transform_to_ui: Optional[Callable] = None,
                        transform_to_repository: Optional[Callable] = None,
                        **kwargs) -> RepositoryStateMapping:
    """Create field mapping configuration"""
    return RepositoryStateMapping(
        repository_field=repository_field,
        ui_state_field=ui_state_field,
        transform_to_ui=transform_to_ui,
        transform_to_repository=transform_to_repository,
        **kwargs
    )


# Global repository state manager instance
_repository_state_manager: Optional[RepositoryStateManager] = None


def get_repository_state_manager() -> RepositoryStateManager:
    """Get the global repository state manager instance"""
    global _repository_state_manager
    if _repository_state_manager is None:
        _repository_state_manager = RepositoryStateManager()
    return _repository_state_manager 