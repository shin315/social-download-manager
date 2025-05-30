"""
Data Binding Strategy for Social Download Manager v2.0

Defines the approach for connecting Qt UI components to repository data sources.
This strategy leverages existing ComponentStateManager, event bus, and repository patterns
to create efficient and maintainable data binding between UI and data layers.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, List, Optional, Callable, TypeVar, Generic, Union
from dataclasses import dataclass, field
from datetime import datetime
import logging
from PyQt6.QtCore import QObject, pyqtSignal

from data.models.repositories import IRepository, IContentRepository, IDownloadRepository
from data.models.base import BaseEntity, EntityId
from core.event_system import EventBus, Event, EventType, get_event_bus
from ui.components.common.component_state_manager import ComponentStateManager

T = TypeVar('T', bound=BaseEntity)


class DataBindingMode(Enum):
    """Defines different data binding modes"""
    ONE_WAY = "one_way"  # Data flows from repository to UI only
    TWO_WAY = "two_way"  # Data flows both ways with automatic sync
    ONE_TIME = "one_time"  # Data loaded once, no automatic updates
    REACTIVE = "reactive"  # Real-time updates via event system


class DataSourceType(Enum):
    """Types of data sources supported"""
    REPOSITORY = "repository"
    SERVICE = "service"
    COMPUTED = "computed"
    CACHED = "cached"


@dataclass
class DataBindingConfig:
    """Configuration for data binding between UI and data source"""
    component_id: str
    data_source_type: DataSourceType
    binding_mode: DataBindingMode
    repository_type: Optional[type] = None
    data_filter: Optional[Dict[str, Any]] = None
    auto_refresh_interval: Optional[int] = None  # seconds
    cache_timeout: Optional[int] = None  # seconds
    error_recovery_strategy: str = "log_and_continue"
    validation_rules: List[Callable] = field(default_factory=list)
    transform_functions: Dict[str, Callable] = field(default_factory=dict)


class IDataBindingAdapter(ABC, Generic[T]):
    """Interface for data binding adapters"""
    
    @abstractmethod
    def bind_data(self, ui_component: QObject, repository: IRepository[T], 
                  config: DataBindingConfig) -> bool:
        """Bind UI component to repository data"""
        pass
    
    @abstractmethod
    def unbind_data(self, ui_component: QObject) -> bool:
        """Unbind UI component from data source"""
        pass
    
    @abstractmethod
    def refresh_data(self, ui_component: QObject) -> bool:
        """Refresh data from repository to UI"""
        pass
    
    @abstractmethod
    def sync_data(self, ui_component: QObject, data: Any) -> bool:
        """Sync data from UI to repository"""
        pass


class DataBindingContext:
    """Context for data binding operations"""
    
    def __init__(self, component_id: str, repository: IRepository, 
                 config: DataBindingConfig):
        self.component_id = component_id
        self.repository = repository
        self.config = config
        self.last_sync: Optional[datetime] = None
        self.error_count = 0
        self.is_active = False
        self.cached_data: Optional[Any] = None
        self.cache_timestamp: Optional[datetime] = None
        
    def is_cache_valid(self) -> bool:
        """Check if cached data is still valid"""
        if not self.cached_data or not self.cache_timestamp:
            return False
        
        if self.config.cache_timeout is None:
            return True
        
        elapsed = (datetime.now() - self.cache_timestamp).total_seconds()
        return elapsed < self.config.cache_timeout
    
    def update_cache(self, data: Any):
        """Update cached data"""
        self.cached_data = data
        self.cache_timestamp = datetime.now()


class DataBindingManager(QObject):
    """
    Central manager for Qt-specific data binding operations
    
    Integrates with existing ComponentStateManager and event bus to provide
    seamless data binding between UI components and repository layer.
    """
    
    # Signals for data binding events
    data_bound = pyqtSignal(str, object)  # component_id, repository
    data_unbound = pyqtSignal(str)  # component_id
    data_refreshed = pyqtSignal(str, object)  # component_id, data
    data_synced = pyqtSignal(str, object)  # component_id, data
    binding_error = pyqtSignal(str, str, str)  # component_id, error_type, message
    
    def __init__(self, state_manager: Optional[ComponentStateManager] = None):
        super().__init__()
        
        # Core dependencies
        self._state_manager = state_manager or self._get_default_state_manager()
        self._event_bus = get_event_bus()
        self._logger = logging.getLogger(__name__)
        
        # Binding management
        self._active_bindings: Dict[str, DataBindingContext] = {}
        self._adapters: Dict[type, IDataBindingAdapter] = {}
        self._component_registry: Dict[str, QObject] = {}
        
        # Event subscriptions
        self._setup_event_subscriptions()
        
        # Auto-refresh timer setup will be handled per binding
        
    def _get_default_state_manager(self) -> ComponentStateManager:
        """Get default state manager instance"""
        # This would be implemented to get the global instance
        # For now, create a new one
        return ComponentStateManager()
    
    def _setup_event_subscriptions(self):
        """Subscribe to relevant events for data binding"""
        self._event_bus.subscribe(EventType.DATA_UPDATED, self._handle_data_updated)
        self._event_bus.subscribe(EventType.ERROR_OCCURRED, self._handle_error_event)
        self._event_bus.subscribe(EventType.COMPONENT_DESTROYED, self._handle_component_destroyed)
    
    def register_adapter(self, component_type: type, adapter: IDataBindingAdapter):
        """Register a data binding adapter for a component type"""
        self._adapters[component_type] = adapter
        self._logger.debug(f"Registered adapter for {component_type.__name__}")
    
    def bind_component(self, ui_component: QObject, repository: IRepository[T], 
                      config: DataBindingConfig) -> bool:
        """
        Bind a UI component to a repository data source
        
        Args:
            ui_component: Qt UI component to bind
            repository: Repository instance for data access
            config: Data binding configuration
            
        Returns:
            True if binding successful, False otherwise
        """
        try:
            component_type = type(ui_component)
            component_id = config.component_id
            
            # Check if adapter exists for component type
            if component_type not in self._adapters:
                self._logger.error(f"No adapter registered for {component_type.__name__}")
                return False
            
            # Create binding context
            context = DataBindingContext(component_id, repository, config)
            
            # Get adapter and perform binding
            adapter = self._adapters[component_type]
            if adapter.bind_data(ui_component, repository, config):
                # Store binding context
                self._active_bindings[component_id] = context
                self._component_registry[component_id] = ui_component
                context.is_active = True
                
                # Integrate with state manager
                self._integrate_with_state_manager(component_id, context)
                
                # Setup auto-refresh if configured
                self._setup_auto_refresh(component_id, context)
                
                # Emit success signal
                self.data_bound.emit(component_id, repository)
                
                self._logger.info(f"Successfully bound component {component_id} to repository")
                return True
            else:
                self._logger.error(f"Adapter failed to bind component {component_id}")
                return False
                
        except Exception as e:
            self._logger.error(f"Error binding component {config.component_id}: {e}")
            self.binding_error.emit(config.component_id, "binding_error", str(e))
            return False
    
    def unbind_component(self, component_id: str) -> bool:
        """
        Unbind a UI component from its data source
        
        Args:
            component_id: Component identifier
            
        Returns:
            True if unbinding successful, False otherwise
        """
        try:
            if component_id not in self._active_bindings:
                self._logger.warning(f"Component {component_id} not bound")
                return False
            
            context = self._active_bindings[component_id]
            ui_component = self._component_registry.get(component_id)
            
            if ui_component:
                component_type = type(ui_component)
                if component_type in self._adapters:
                    adapter = self._adapters[component_type]
                    adapter.unbind_data(ui_component)
            
            # Cleanup binding context
            context.is_active = False
            del self._active_bindings[component_id]
            
            if component_id in self._component_registry:
                del self._component_registry[component_id]
            
            # Cleanup state manager integration
            self._cleanup_state_manager_integration(component_id)
            
            # Emit signal
            self.data_unbound.emit(component_id)
            
            self._logger.info(f"Successfully unbound component {component_id}")
            return True
            
        except Exception as e:
            self._logger.error(f"Error unbinding component {component_id}: {e}")
            self.binding_error.emit(component_id, "unbinding_error", str(e))
            return False
    
    def refresh_component_data(self, component_id: str) -> bool:
        """
        Refresh data for a bound component
        
        Args:
            component_id: Component identifier
            
        Returns:
            True if refresh successful, False otherwise
        """
        try:
            if component_id not in self._active_bindings:
                self._logger.warning(f"Component {component_id} not bound")
                return False
            
            context = self._active_bindings[component_id]
            ui_component = self._component_registry.get(component_id)
            
            if not ui_component:
                self._logger.error(f"UI component {component_id} not found")
                return False
            
            component_type = type(ui_component)
            if component_type in self._adapters:
                adapter = self._adapters[component_type]
                
                if adapter.refresh_data(ui_component):
                    context.last_sync = datetime.now()
                    self.data_refreshed.emit(component_id, context.cached_data)
                    
                    self._logger.debug(f"Refreshed data for component {component_id}")
                    return True
                else:
                    self._logger.error(f"Adapter failed to refresh data for {component_id}")
                    return False
            else:
                self._logger.error(f"No adapter for component type {component_type.__name__}")
                return False
                
        except Exception as e:
            self._logger.error(f"Error refreshing data for component {component_id}: {e}")
            self.binding_error.emit(component_id, "refresh_error", str(e))
            return False
    
    def sync_component_data(self, component_id: str, data: Any) -> bool:
        """
        Sync data from UI component to repository
        
        Args:
            component_id: Component identifier
            data: Data to sync to repository
            
        Returns:
            True if sync successful, False otherwise
        """
        try:
            if component_id not in self._active_bindings:
                self._logger.warning(f"Component {component_id} not bound")
                return False
            
            context = self._active_bindings[component_id]
            
            # Check if two-way binding is enabled
            if context.config.binding_mode not in [DataBindingMode.TWO_WAY]:
                self._logger.warning(f"Component {component_id} not configured for two-way binding")
                return False
            
            ui_component = self._component_registry.get(component_id)
            
            if not ui_component:
                self._logger.error(f"UI component {component_id} not found")
                return False
            
            component_type = type(ui_component)
            if component_type in self._adapters:
                adapter = self._adapters[component_type]
                
                if adapter.sync_data(ui_component, data):
                    context.last_sync = datetime.now()
                    context.update_cache(data)
                    self.data_synced.emit(component_id, data)
                    
                    self._logger.debug(f"Synced data for component {component_id}")
                    return True
                else:
                    self._logger.error(f"Adapter failed to sync data for {component_id}")
                    return False
            else:
                self._logger.error(f"No adapter for component type {component_type.__name__}")
                return False
                
        except Exception as e:
            self._logger.error(f"Error syncing data for component {component_id}: {e}")
            self.binding_error.emit(component_id, "sync_error", str(e))
            return False
    
    def get_binding_status(self, component_id: str) -> Optional[Dict[str, Any]]:
        """Get status information for a bound component"""
        if component_id not in self._active_bindings:
            return None
        
        context = self._active_bindings[component_id]
        return {
            'component_id': component_id,
            'is_active': context.is_active,
            'binding_mode': context.config.binding_mode.value,
            'data_source_type': context.config.data_source_type.value,
            'last_sync': context.last_sync.isoformat() if context.last_sync else None,
            'error_count': context.error_count,
            'has_cached_data': context.cached_data is not None,
            'cache_valid': context.is_cache_valid()
        }
    
    def get_all_bindings(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all active bindings"""
        return {
            component_id: self.get_binding_status(component_id)
            for component_id in self._active_bindings.keys()
        }
    
    def _integrate_with_state_manager(self, component_id: str, context: DataBindingContext):
        """Integrate binding with ComponentStateManager"""
        try:
            # Register component with state manager
            if component_id not in self._state_manager.get_registered_components():
                ui_component = self._component_registry.get(component_id)
                if ui_component:
                    # State manager integration would depend on specific implementation
                    # This is a placeholder for the integration
                    pass
            
        except Exception as e:
            self._logger.error(f"Error integrating with state manager: {e}")
    
    def _cleanup_state_manager_integration(self, component_id: str):
        """Cleanup state manager integration for component"""
        try:
            # Cleanup would depend on specific state manager implementation
            pass
        except Exception as e:
            self._logger.error(f"Error cleaning up state manager integration: {e}")
    
    def _setup_auto_refresh(self, component_id: str, context: DataBindingContext):
        """Setup auto-refresh for component if configured"""
        if context.config.auto_refresh_interval:
            # Auto-refresh implementation would use QTimer
            # This is a placeholder for the implementation
            pass
    
    # Event handlers
    def _handle_data_updated(self, event: Event):
        """Handle data update events from repositories"""
        try:
            data = event.data or {}
            source = event.source
            
            # Find components bound to this data source
            for component_id, context in self._active_bindings.items():
                if context.config.binding_mode in [DataBindingMode.REACTIVE, DataBindingMode.TWO_WAY]:
                    # Check if this component should react to this data update
                    if self._should_react_to_update(context, source, data):
                        self.refresh_component_data(component_id)
                        
        except Exception as e:
            self._logger.error(f"Error handling data update event: {e}")
    
    def _handle_error_event(self, event: Event):
        """Handle error events"""
        # Error handling for data binding operations
        pass
    
    def _handle_component_destroyed(self, event: Event):
        """Handle component destruction events"""
        data = event.data or {}
        component_id = data.get('component_id')
        
        if component_id and component_id in self._active_bindings:
            self.unbind_component(component_id)
    
    def _should_react_to_update(self, context: DataBindingContext, source: str, data: Dict[str, Any]) -> bool:
        """Determine if a component should react to a data update"""
        # Implementation would check if the update is relevant to this component
        # Based on data filters, repository type, etc.
        return True  # Placeholder


# Global data binding manager instance
_data_binding_manager: Optional[DataBindingManager] = None


def get_data_binding_manager() -> DataBindingManager:
    """Get the global data binding manager instance"""
    global _data_binding_manager
    if _data_binding_manager is None:
        _data_binding_manager = DataBindingManager()
    return _data_binding_manager


def create_binding_config(component_id: str, 
                         repository_type: type,
                         binding_mode: DataBindingMode = DataBindingMode.ONE_WAY,
                         **kwargs) -> DataBindingConfig:
    """
    Convenience function to create data binding configuration
    
    Args:
        component_id: Unique identifier for the component
        repository_type: Type of repository to bind to
        binding_mode: Mode of data binding
        **kwargs: Additional configuration options
        
    Returns:
        DataBindingConfig instance
    """
    return DataBindingConfig(
        component_id=component_id,
        data_source_type=DataSourceType.REPOSITORY,
        binding_mode=binding_mode,
        repository_type=repository_type,
        **kwargs
    )


# =============================================================================
# Qt-Specific Binding Patterns
# =============================================================================

class QtDataBindingPattern:
    """Base class for Qt-specific data binding patterns"""
    
    @staticmethod
    def one_way_binding(ui_component: QObject, repository: IRepository, 
                       data_mapper: Callable[[Any], None]):
        """
        Implement one-way data binding pattern
        
        Args:
            ui_component: Qt UI component
            repository: Data repository
            data_mapper: Function to map repository data to UI
        """
        # Implementation placeholder
        pass
    
    @staticmethod
    def two_way_binding(ui_component: QObject, repository: IRepository,
                       ui_to_data_mapper: Callable[[Any], Any],
                       data_to_ui_mapper: Callable[[Any], None]):
        """
        Implement two-way data binding pattern
        
        Args:
            ui_component: Qt UI component
            repository: Data repository
            ui_to_data_mapper: Function to map UI changes to repository data
            data_to_ui_mapper: Function to map repository data to UI
        """
        # Implementation placeholder
        pass
    
    @staticmethod
    def reactive_binding(ui_component: QObject, repository: IRepository,
                        event_bus: EventBus, component_id: str):
        """
        Implement reactive data binding using event bus
        
        Args:
            ui_component: Qt UI component
            repository: Data repository
            event_bus: Event bus for reactive updates
            component_id: Component identifier
        """
        # Implementation placeholder
        pass


# =============================================================================
# Repository Integration Helpers
# =============================================================================

class RepositoryDataMapper:
    """Helper class for mapping repository data to UI formats"""
    
    @staticmethod
    def map_content_to_table_data(content_list: List[Any]) -> List[Dict[str, Any]]:
        """Map content repository data to table format"""
        # Implementation placeholder
        return []
    
    @staticmethod
    def map_download_to_progress_data(download: Any) -> Dict[str, Any]:
        """Map download repository data to progress widget format"""
        # Implementation placeholder
        return {}
    
    @staticmethod
    def map_platform_data(platforms: List[Any]) -> List[Dict[str, Any]]:
        """Map platform data for selector widgets"""
        # Implementation placeholder
        return []


# =============================================================================
# Documentation and Usage Examples
# =============================================================================

"""
Data Binding Strategy Implementation Guide

This module implements a Qt-specific data binding strategy that:

1. **Leverages Existing Architecture**:
   - Uses ComponentStateManager for state persistence
   - Integrates with the event bus for reactive updates
   - Works with the repository pattern from Task 12

2. **Supports Multiple Binding Modes**:
   - ONE_WAY: Repository → UI (read-only display)
   - TWO_WAY: Repository ↔ UI (editable data)
   - REACTIVE: Real-time updates via events
   - ONE_TIME: Load once, no automatic updates

3. **Qt Integration Patterns**:
   - Signal/slot connections for automatic updates
   - Model/View architecture for complex widgets
   - Custom adapters for different component types

4. **Performance Considerations**:
   - Caching for frequently accessed data
   - Lazy loading for large datasets
   - Debounced updates to prevent UI flooding

Usage Example:

```python
from core.data_integration.data_binding_strategy import (
    get_data_binding_manager, create_binding_config, DataBindingMode
)
from data.models.repositories import get_content_repository

# Get managers
binding_manager = get_data_binding_manager()
content_repo = get_content_repository()

# Create binding configuration
config = create_binding_config(
    component_id="video_table_main",
    repository_type=ContentRepository,
    binding_mode=DataBindingMode.TWO_WAY,
    auto_refresh_interval=30,
    cache_timeout=60
)

# Bind UI component to repository
video_table = VideoTable()
success = binding_manager.bind_component(video_table, content_repo, config)

if success:
    print("Data binding established successfully")
```

This strategy provides the foundation for implementing specific adapters
for each UI component type in subsequent subtasks.
""" 