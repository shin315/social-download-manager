"""
Tab Utilities

This module provides utility functions, decorators, and helpers
to simplify tab development and integration with the component system.
"""

import functools
from typing import Dict, Any, List, Optional, Callable, Type, TypeVar, Union
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QTimer, pyqtSignal

from .models import TabConfig, TabState
from .base_tab import BaseTab
from .tab_state_manager import TabStateManager
from .events import get_event_bus, EventType

T = TypeVar('T', bound=BaseTab)


def tab_lifecycle_handler(lifecycle_event: str):
    """
    Decorator to register lifecycle event handlers for tabs.
    
    Usage:
        @tab_lifecycle_handler('activated')
        def on_my_tab_activated(self):
            # Handle activation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Add timing and error handling
            try:
                result = func(self, *args, **kwargs)
                if hasattr(self, '_lifecycle_timings'):
                    self._lifecycle_timings[lifecycle_event] = True
                return result
            except Exception as e:
                print(f"Error in {lifecycle_event} lifecycle handler: {e}")
                if hasattr(self, 'emit_tab_event'):
                    self.emit_tab_event(f'lifecycle_error', {
                        'event': lifecycle_event,
                        'error': str(e)
                    })
                raise
        
        # Mark function as lifecycle handler
        wrapper._is_lifecycle_handler = True
        wrapper._lifecycle_event = lifecycle_event
        return wrapper
    return decorator


def auto_save_on_change(fields: List[str] = None, delay_ms: int = 1000):
    """
    Decorator to automatically save tab state when specified fields change.
    
    Args:
        fields: List of field names to monitor. If None, monitors all changes.
        delay_ms: Delay in milliseconds before saving (debouncing)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            result = func(self, *args, **kwargs)
            
            # Set up auto-save if tab supports it
            if hasattr(self, '_setup_auto_save'):
                self._setup_auto_save(fields, delay_ms)
            elif hasattr(self, 'save_data'):
                # Simple immediate save fallback
                QTimer.singleShot(delay_ms, self.save_data)
            
            return result
        return wrapper
    return decorator


def validate_before_action(validation_func: Optional[Callable] = None):
    """
    Decorator to validate tab state before executing an action.
    
    Args:
        validation_func: Custom validation function. If None, uses tab's validate_input method.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Determine validation function
            validator = validation_func
            if validator is None and hasattr(self, 'validate_input'):
                validator = self.validate_input
            elif validator is None and hasattr(self, 'is_valid'):
                validator = lambda: [] if self.is_valid() else ['Invalid state']
            
            # Perform validation
            if validator:
                errors = validator()
                if errors:
                    if hasattr(self, 'show_validation_errors'):
                        self.show_validation_errors(errors)
                    return False  # or raise ValidationError
            
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


def with_state_backup(create_snapshot: bool = True):
    """
    Decorator to create state backup before executing a risky operation.
    
    Args:
        create_snapshot: Whether to create a state snapshot
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Create backup
            backup_created = False
            if create_snapshot and hasattr(self, 'create_state_snapshot'):
                backup_created = self.create_state_snapshot(
                    metadata={'operation': func.__name__, 'auto_backup': True}
                )
            
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                # Restore from backup if operation failed
                if backup_created and hasattr(self, 'restore_from_snapshot'):
                    try:
                        self.restore_from_snapshot(-1)  # Restore latest snapshot
                        print(f"Restored tab state after failed operation: {func.__name__}")
                    except:
                        pass  # Backup restoration failed, but don't mask original error
                raise
        return wrapper
    return decorator


class TabFactory:
    """Factory class for creating and configuring tabs"""
    
    _tab_classes: Dict[str, Type[BaseTab]] = {}
    _default_configs: Dict[str, TabConfig] = {}
    
    @classmethod
    def register_tab_class(cls, tab_type: str, tab_class: Type[BaseTab], 
                          default_config: Optional[TabConfig] = None):
        """Register a tab class with the factory"""
        cls._tab_classes[tab_type] = tab_class
        if default_config:
            cls._default_configs[tab_type] = default_config
    
    @classmethod
    def create_tab(cls, tab_type: str, config: Optional[TabConfig] = None, 
                   parent: Optional[QWidget] = None, **kwargs) -> Optional[BaseTab]:
        """Create a tab instance of the specified type"""
        if tab_type not in cls._tab_classes:
            print(f"Unknown tab type: {tab_type}")
            return None
        
        tab_class = cls._tab_classes[tab_type]
        
        # Use provided config or default
        if config is None:
            config = cls._default_configs.get(tab_type)
        
        if config is None:
            # Create basic config
            config = TabConfig(
                tab_id=f"{tab_type}_{id(parent)}",
                title_key=f"tab.{tab_type}.title"
            )
        
        try:
            return tab_class(config=config, parent=parent, **kwargs)
        except Exception as e:
            print(f"Error creating tab {tab_type}: {e}")
            return None
    
    @classmethod
    def get_registered_types(cls) -> List[str]:
        """Get list of registered tab types"""
        return list(cls._tab_classes.keys())


class TabEventHelper:
    """Helper class for tab event handling and communication"""
    
    def __init__(self, tab: BaseTab):
        self.tab = tab
        self.event_bus = get_event_bus()
        self._subscriptions: List[tuple] = []
    
    def subscribe_to_tab_events(self, target_tab_id: str, 
                               event_filter: Optional[Callable] = None):
        """Subscribe to events from another tab"""
        def handler(event):
            if event.source_component == target_tab_id:
                if event_filter is None or event_filter(event):
                    self._handle_external_tab_event(event)
        
        self.event_bus.subscribe(EventType.TAB_DATA_CHANGED, handler)
        self._subscriptions.append((EventType.TAB_DATA_CHANGED, handler))
    
    def broadcast_tab_update(self, update_type: str, data: Dict[str, Any]):
        """Broadcast an update to other tabs"""
        self.event_bus.emit_event(
            event_type=EventType.TAB_DATA_CHANGED,
            source_component=self.tab.get_tab_id(),
            data={
                'update_type': update_type,
                'tab_data': data,
                'timestamp': self._get_current_timestamp()
            }
        )
    
    def request_data_sync(self, source_tab_id: str, fields: List[str]):
        """Request data synchronization from another tab"""
        self.event_bus.emit_event(
            event_type=EventType.STATE_CHANGED,
            source_component=self.tab.get_tab_id(),
            data={
                'request_type': 'data_sync',
                'source_tab_id': source_tab_id,
                'fields': fields
            }
        )
    
    def _handle_external_tab_event(self, event):
        """Handle events from other tabs"""
        # Override in subclasses or provide callback
        if hasattr(self.tab, 'on_external_tab_event'):
            self.tab.on_external_tab_event(event)
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp for event tracking"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def cleanup(self):
        """Cleanup event subscriptions"""
        for event_type, handler in self._subscriptions:
            self.event_bus.unsubscribe(event_type, handler)
        self._subscriptions.clear()


class TabDataSynchronizer:
    """Utility for synchronizing data between tabs"""
    
    def __init__(self, state_manager: TabStateManager):
        self.state_manager = state_manager
        self.sync_rules: Dict[str, Dict[str, Any]] = {}
    
    def add_sync_rule(self, source_tab: str, target_tab: str, 
                     fields: List[str], bidirectional: bool = False):
        """Add a synchronization rule between tabs"""
        rule_id = f"{source_tab}→{target_tab}"
        self.sync_rules[rule_id] = {
            'source': source_tab,
            'target': target_tab,
            'fields': fields,
            'bidirectional': bidirectional
        }
        
        if bidirectional:
            reverse_rule_id = f"{target_tab}→{source_tab}"
            self.sync_rules[reverse_rule_id] = {
                'source': target_tab,
                'target': source_tab,
                'fields': fields,
                'bidirectional': False  # Prevent infinite recursion
            }
    
    def sync_tabs(self, source_tab_id: str, target_tab_id: str, 
                  fields: Optional[List[str]] = None) -> bool:
        """Synchronize data between specific tabs"""
        rule_id = f"{source_tab_id}→{target_tab_id}"
        
        if rule_id in self.sync_rules:
            rule = self.sync_rules[rule_id]
            sync_fields = fields or rule['fields']
            return self.state_manager.synchronize_tab_states(
                source_tab_id, target_tab_id, sync_fields
            )
        
        return False
    
    def apply_all_sync_rules(self, changed_tab_id: str):
        """Apply all relevant sync rules when a tab changes"""
        for rule_id, rule in self.sync_rules.items():
            if rule['source'] == changed_tab_id:
                self.sync_tabs(rule['source'], rule['target'], rule['fields'])


class TabValidationHelper:
    """Helper for tab validation operations"""
    
    @staticmethod
    def create_validation_chain(*validators: Callable) -> Callable:
        """Create a validation chain from multiple validators"""
        def combined_validator(tab: BaseTab) -> List[str]:
            all_errors = []
            for validator in validators:
                try:
                    errors = validator(tab)
                    if errors:
                        all_errors.extend(errors)
                except Exception as e:
                    all_errors.append(f"Validation error: {e}")
            return all_errors
        return combined_validator
    
    @staticmethod
    def required_fields_validator(fields: List[str]) -> Callable:
        """Create validator for required fields"""
        def validator(tab: BaseTab) -> List[str]:
            errors = []
            state = tab.get_tab_state()
            
            for field in fields:
                if not hasattr(state, field):
                    errors.append(f"Missing required field: {field}")
                else:
                    value = getattr(state, field)
                    if value is None or (isinstance(value, (list, str)) and len(value) == 0):
                        errors.append(f"Required field '{field}' is empty")
            
            return errors
        return validator
    
    @staticmethod
    def data_consistency_validator() -> Callable:
        """Create validator for data consistency"""
        def validator(tab: BaseTab) -> List[str]:
            errors = []
            state = tab.get_tab_state()
            
            # Check if filtered videos are subset of all videos
            if hasattr(state, 'videos') and hasattr(state, 'filtered_videos'):
                video_ids = {v.get('id') for v in state.videos if isinstance(v, dict) and 'id' in v}
                filtered_ids = {v.get('id') for v in state.filtered_videos if isinstance(v, dict) and 'id' in v}
                
                if not filtered_ids.issubset(video_ids):
                    errors.append("Filtered videos contain items not in main video list")
            
            # Check if selected items are valid indices
            if hasattr(state, 'selected_items') and hasattr(state, 'filtered_videos'):
                max_index = len(state.filtered_videos) - 1
                invalid_selections = [idx for idx in state.selected_items if idx > max_index]
                if invalid_selections:
                    errors.append(f"Invalid selection indices: {invalid_selections}")
            
            return errors
        return validator


class TabPerformanceMonitor:
    """Monitor tab performance metrics"""
    
    def __init__(self, tab: BaseTab):
        self.tab = tab
        self.metrics: Dict[str, Any] = {
            'initialization_time': None,
            'data_load_time': None,
            'state_save_time': None,
            'validation_time': None,
            'memory_usage': None
        }
        self.start_times: Dict[str, float] = {}
    
    def start_timing(self, operation: str):
        """Start timing an operation"""
        import time
        self.start_times[operation] = time.time()
    
    def end_timing(self, operation: str):
        """End timing an operation"""
        import time
        if operation in self.start_times:
            duration = time.time() - self.start_times[operation]
            self.metrics[f"{operation}_time"] = duration
            del self.start_times[operation]
            return duration
        return None
    
    def measure_memory_usage(self):
        """Measure current memory usage"""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            self.metrics['memory_usage'] = process.memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            pass  # psutil not available
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get performance metrics report"""
        self.measure_memory_usage()
        return self.metrics.copy()


# Utility functions

def create_standard_tab_config(tab_id: str, title_key: str, **kwargs) -> TabConfig:
    """Create a standard tab configuration with common defaults"""
    return TabConfig(
        tab_id=tab_id,
        title_key=title_key,
        auto_save=kwargs.get('auto_save', True),
        lifecycle_hooks=kwargs.get('lifecycle_hooks', True),
        component_integration=kwargs.get('component_integration', True),
        state_persistence=kwargs.get('state_persistence', True),
        validation_required=kwargs.get('validation_required', False),
        **{k: v for k, v in kwargs.items() if k not in [
            'auto_save', 'lifecycle_hooks', 'component_integration', 
            'state_persistence', 'validation_required'
        ]}
    )


def setup_tab_logging(tab: BaseTab, log_level: str = 'INFO'):
    """Setup logging for a tab"""
    import logging
    logger = logging.getLogger(f"tab.{tab.get_tab_id()}")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Add tab-specific logging methods
    tab._logger = logger
    tab.log_info = logger.info
    tab.log_warning = logger.warning
    tab.log_error = logger.error
    tab.log_debug = logger.debug


def apply_theme_to_tab(tab: BaseTab, theme_config: Dict[str, Any]):
    """Apply theme configuration to a tab"""
    if hasattr(tab, 'apply_theme'):
        tab.apply_theme(theme_config)
    elif hasattr(tab, 'apply_theme_colors'):
        tab.apply_theme_colors(theme_config)


def connect_tab_to_state_manager(tab: BaseTab, state_manager: TabStateManager):
    """Connect a tab to the state manager system"""
    tab_id = tab.get_tab_id()
    
    # Register tab with state manager
    state_manager.register_tab(tab_id)
    
    # Connect tab signals to state manager
    if hasattr(tab, 'tab_data_changed'):
        tab.tab_data_changed.connect(
            lambda: state_manager._mark_tab_dirty(tab_id)
        )
    
    # Add state manager reference to tab
    tab._state_manager = state_manager
    
    # Add convenience methods
    def save_to_manager():
        return state_manager.save_tab_state(tab_id)
    
    def load_from_manager():
        return state_manager.load_tab_state(tab_id)
    
    tab.save_to_state_manager = save_to_manager
    tab.load_from_state_manager = load_from_manager 