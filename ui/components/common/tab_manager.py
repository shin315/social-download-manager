"""
Tab Manager System

This module provides centralized management for all tabs in the application,
coordinating lifecycle, state management, communication, and styling.

Features:
- Centralized tab registration and lifecycle management
- Coordinated state persistence across all tabs
- Inter-tab communication orchestration
- Global theme and styling coordination
- Performance monitoring and debugging
- Tab validation and error handling
"""

from typing import Dict, Any, List, Optional, Set, Type, Callable
from PyQt6.QtWidgets import QTabWidget, QWidget
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from dataclasses import dataclass
from datetime import datetime
import logging

from .base_tab import BaseTab
from .tab_state_manager import TabStateManager, TabStateSnapshot
from .tab_styling import TabStyleManager, TabStyleVariant, set_global_tab_theme
from .tab_utilities import TabFactory, TabPerformanceMonitor
from .models import TabConfig, TabState
from .events import get_event_bus, EventType, ComponentEvent


@dataclass
class TabRegistration:
    """Registration information for a tab"""
    tab_id: str
    tab_instance: BaseTab
    config: TabConfig
    registration_time: datetime
    last_activated: Optional[datetime] = None
    performance_monitor: Optional[TabPerformanceMonitor] = None
    is_dirty: bool = False
    validation_errors: List[str] = None


class TabManager(QObject):
    """
    Central tab management system providing:
    - Tab lifecycle coordination
    - State management orchestration
    - Inter-tab communication
    - Global styling and theming
    - Performance monitoring
    - Debugging and diagnostics
    """
    
    # Tab manager signals
    tab_registered = pyqtSignal(str, BaseTab)        # tab_id, tab_instance
    tab_unregistered = pyqtSignal(str)               # tab_id
    tab_activated = pyqtSignal(str, BaseTab)         # tab_id, tab_instance
    tab_deactivated = pyqtSignal(str, BaseTab)       # tab_id, tab_instance
    tab_state_changed = pyqtSignal(str, bool)        # tab_id, is_dirty
    tab_validation_changed = pyqtSignal(str, bool)   # tab_id, is_valid
    global_theme_changed = pyqtSignal(dict)          # theme_data
    performance_alert = pyqtSignal(str, str, float)  # tab_id, metric, value
    
    def __init__(self, tab_widget: Optional[QTabWidget] = None):
        """
        Initialize the tab manager
        
        Args:
            tab_widget: Optional QTabWidget to manage
        """
        super().__init__()
        
        # Core components
        self._tab_widget = tab_widget
        self._registered_tabs: Dict[str, TabRegistration] = {}
        self._state_manager = TabStateManager()
        self._style_manager = TabStyleManager()
        self._event_bus = get_event_bus()
        
        # Configuration
        self._auto_save_interval = 30  # seconds
        self._performance_monitoring = True
        self._validation_enabled = True
        self._debug_mode = False
        
        # State tracking
        self._active_tab_id: Optional[str] = None
        self._dirty_tabs: Set[str] = set()
        self._invalid_tabs: Set[str] = set()
        
        # Timers and automation
        self._auto_save_timer = QTimer()
        self._auto_save_timer.timeout.connect(self._auto_save_all_tabs)
        self._auto_save_timer.start(self._auto_save_interval * 1000)
        
        self._validation_timer = QTimer()
        self._validation_timer.timeout.connect(self._validate_all_tabs)
        self._validation_timer.start(60000)  # Validate every minute
        
        # Setup logging
        self._logger = logging.getLogger(__name__)
        
        # Setup event subscriptions
        self._setup_event_subscriptions()
        
        # Connect to tab widget if provided
        if self._tab_widget:
            self._connect_tab_widget()
    
    def _setup_event_subscriptions(self):
        """Set up event bus subscriptions"""
        try:
            self._event_bus.subscribe(EventType.TAB_ACTIVATED, self._handle_tab_activated)
            self._event_bus.subscribe(EventType.TAB_DEACTIVATED, self._handle_tab_deactivated)
            self._event_bus.subscribe(EventType.TAB_DATA_CHANGED, self._handle_tab_data_changed)
            self._event_bus.subscribe(EventType.THEME_CHANGED, self._handle_theme_changed)
            self._event_bus.subscribe(EventType.STATE_CHANGED, self._handle_state_changed)
        except Exception as e:
            self._logger.error(f"Error setting up event subscriptions: {e}")
    
    def _connect_tab_widget(self):
        """Connect to the QTabWidget for automatic management"""
        if self._tab_widget:
            self._tab_widget.currentChanged.connect(self._on_tab_widget_changed)
    
    # =============================================================================
    # Tab Registration and Management
    # =============================================================================
    
    def register_tab(self, tab: BaseTab, config: Optional[TabConfig] = None) -> bool:
        """
        Register a tab with the manager
        
        Args:
            tab: BaseTab instance to register
            config: Optional tab configuration
            
        Returns:
            bool: True if registration successful
        """
        try:
            tab_id = tab.get_tab_id()
            
            # Check if already registered
            if tab_id in self._registered_tabs:
                self._logger.warning(f"Tab {tab_id} already registered")
                return False
            
            # Use tab's config if not provided
            if config is None:
                config = tab._config
            
            # Create performance monitor
            performance_monitor = TabPerformanceMonitor(tab) if self._performance_monitoring else None
            
            # Create registration
            registration = TabRegistration(
                tab_id=tab_id,
                tab_instance=tab,
                config=config,
                registration_time=datetime.now(),
                performance_monitor=performance_monitor
            )
            
            # Register with state manager
            self._state_manager.register_tab(tab_id, tab.get_tab_state())
            
            # Connect tab signals
            self._connect_tab_signals(tab)
            
            # Store registration
            self._registered_tabs[tab_id] = registration
            
            # Apply current theme if available
            if hasattr(self, '_current_theme'):
                tab.apply_theme(self._current_theme)
            
            # Emit registration signal
            self.tab_registered.emit(tab_id, tab)
            
            self._logger.info(f"Successfully registered tab: {tab_id}")
            return True
            
        except Exception as e:
            self._logger.error(f"Error registering tab {tab_id}: {e}")
            return False
    
    def unregister_tab(self, tab_id: str, save_state: bool = True) -> bool:
        """
        Unregister a tab from the manager
        
        Args:
            tab_id: ID of tab to unregister
            save_state: Whether to save state before unregistering
            
        Returns:
            bool: True if unregistration successful
        """
        try:
            if tab_id not in self._registered_tabs:
                self._logger.warning(f"Tab {tab_id} not registered")
                return False
            
            registration = self._registered_tabs[tab_id]
            tab = registration.tab_instance
            
            # Save state if requested
            if save_state and tab_id in self._dirty_tabs:
                tab.save_data()
            
            # Disconnect signals
            self._disconnect_tab_signals(tab)
            
            # Unregister from state manager
            self._state_manager.unregister_tab(tab_id, save_state)
            
            # Cleanup tracking
            self._dirty_tabs.discard(tab_id)
            self._invalid_tabs.discard(tab_id)
            
            # Remove registration
            del self._registered_tabs[tab_id]
            
            # Update active tab if this was active
            if self._active_tab_id == tab_id:
                self._active_tab_id = None
            
            # Emit unregistration signal
            self.tab_unregistered.emit(tab_id)
            
            self._logger.info(f"Successfully unregistered tab: {tab_id}")
            return True
            
        except Exception as e:
            self._logger.error(f"Error unregistering tab {tab_id}: {e}")
            return False
    
    def get_tab(self, tab_id: str) -> Optional[BaseTab]:
        """Get tab instance by ID"""
        registration = self._registered_tabs.get(tab_id)
        return registration.tab_instance if registration else None
    
    def get_registered_tabs(self) -> List[str]:
        """Get list of registered tab IDs"""
        return list(self._registered_tabs.keys())
    
    def get_active_tab(self) -> Optional[BaseTab]:
        """Get currently active tab"""
        return self.get_tab(self._active_tab_id) if self._active_tab_id else None
    
    # =============================================================================
    # Tab Lifecycle Management
    # =============================================================================
    
    def activate_tab(self, tab_id: str) -> bool:
        """
        Activate a specific tab
        
        Args:
            tab_id: ID of tab to activate
            
        Returns:
            bool: True if activation successful
        """
        try:
            if tab_id not in self._registered_tabs:
                self._logger.warning(f"Cannot activate unregistered tab: {tab_id}")
                return False
            
            registration = self._registered_tabs[tab_id]
            tab = registration.tab_instance
            
            # Deactivate current tab
            if self._active_tab_id and self._active_tab_id != tab_id:
                self.deactivate_tab(self._active_tab_id)
            
            # Activate new tab
            tab.on_tab_activated()
            self._active_tab_id = tab_id
            registration.last_activated = datetime.now()
            
            # Emit activation signal
            self.tab_activated.emit(tab_id, tab)
            
            # Emit activation event
            self._event_bus.emit_event(
                event_type=EventType.TAB_ACTIVATED,
                source_component="TabManager",
                data={'tab_id': tab_id, 'timestamp': datetime.now().isoformat()}
            )
            
            self._logger.info(f"Activated tab: {tab_id}")
            return True
            
        except Exception as e:
            self._logger.error(f"Error activating tab {tab_id}: {e}")
            return False
    
    def deactivate_tab(self, tab_id: str) -> bool:
        """
        Deactivate a specific tab
        
        Args:
            tab_id: ID of tab to deactivate
            
        Returns:
            bool: True if deactivation successful
        """
        try:
            if tab_id not in self._registered_tabs:
                return False
            
            registration = self._registered_tabs[tab_id]
            tab = registration.tab_instance
            
            # Deactivate tab
            tab.on_tab_deactivated()
            
            # Update active tab if this was active
            if self._active_tab_id == tab_id:
                self._active_tab_id = None
            
            # Emit deactivation signal
            self.tab_deactivated.emit(tab_id, tab)
            
            # Emit deactivation event
            self._event_bus.emit_event(
                event_type=EventType.TAB_DEACTIVATED,
                source_component="TabManager",
                data={'tab_id': tab_id, 'timestamp': datetime.now().isoformat()}
            )
            
            self._logger.info(f"Deactivated tab: {tab_id}")
            return True
            
        except Exception as e:
            self._logger.error(f"Error deactivating tab {tab_id}: {e}")
            return False
    
    # =============================================================================
    # State Management Coordination
    # =============================================================================
    
    def save_tab_state(self, tab_id: str) -> bool:
        """Save state for a specific tab"""
        try:
            if tab_id not in self._registered_tabs:
                return False
            
            tab = self._registered_tabs[tab_id].tab_instance
            success = tab.save_data()
            
            if success:
                self._dirty_tabs.discard(tab_id)
                self._state_manager.save_tab_state(tab_id)
            
            return success
            
        except Exception as e:
            self._logger.error(f"Error saving tab state {tab_id}: {e}")
            return False
    
    def load_tab_state(self, tab_id: str) -> bool:
        """Load state for a specific tab"""
        try:
            if tab_id not in self._registered_tabs:
                return False
            
            tab = self._registered_tabs[tab_id].tab_instance
            return self._state_manager.load_tab_state(tab_id)
            
        except Exception as e:
            self._logger.error(f"Error loading tab state {tab_id}: {e}")
            return False
    
    def save_all_tab_states(self) -> Dict[str, bool]:
        """Save states for all dirty tabs"""
        results = {}
        for tab_id in list(self._dirty_tabs):
            results[tab_id] = self.save_tab_state(tab_id)
        return results
    
    def _auto_save_all_tabs(self):
        """Auto-save all dirty tabs"""
        if self._dirty_tabs:
            self._logger.info(f"Auto-saving {len(self._dirty_tabs)} dirty tabs")
            self.save_all_tab_states()
    
    # =============================================================================
    # Theme and Styling Management
    # =============================================================================
    
    def apply_global_theme(self, theme_data: Dict[str, Any]) -> None:
        """Apply theme to all registered tabs"""
        try:
            # Store current theme
            self._current_theme = theme_data
            
            # Determine theme name
            theme_name = self._determine_theme_name(theme_data)
            
            # Update global style manager
            set_global_tab_theme(theme_name)
            
            # Apply to all registered tabs
            for registration in self._registered_tabs.values():
                registration.tab_instance.apply_theme(theme_data)
            
            # Emit global theme change
            self.global_theme_changed.emit(theme_data)
            
            # Emit theme change event
            self._event_bus.emit_event(
                event_type=EventType.THEME_CHANGED,
                source_component="TabManager",
                data={'theme': theme_data, 'theme_name': theme_name}
            )
            
            self._logger.info(f"Applied global theme: {theme_name}")
            
        except Exception as e:
            self._logger.error(f"Error applying global theme: {e}")
    
    def _determine_theme_name(self, theme_data: Dict[str, Any]) -> str:
        """Determine theme name from theme data"""
        bg_color = theme_data.get('background', '#ffffff').lower()
        if bg_color in ['#1e1e1e', '#2d2d30', '#000000'] or 'dark' in str(theme_data.get('name', '')).lower():
            return 'dark'
        elif theme_data.get('high_contrast', False) or 'contrast' in str(theme_data.get('name', '')).lower():
            return 'high_contrast'
        return 'light'
    
    # =============================================================================
    # Validation and Error Handling
    # =============================================================================
    
    def validate_tab(self, tab_id: str) -> List[str]:
        """Validate a specific tab"""
        if tab_id not in self._registered_tabs:
            return [f"Tab {tab_id} not registered"]
        
        try:
            tab = self._registered_tabs[tab_id].tab_instance
            errors = tab.validate_input()
            
            # Update validation state
            if errors:
                self._invalid_tabs.add(tab_id)
            else:
                self._invalid_tabs.discard(tab_id)
            
            # Store errors in registration
            self._registered_tabs[tab_id].validation_errors = errors
            
            # Emit validation change
            self.tab_validation_changed.emit(tab_id, len(errors) == 0)
            
            return errors
            
        except Exception as e:
            error_msg = f"Validation error for tab {tab_id}: {e}"
            self._logger.error(error_msg)
            return [error_msg]
    
    def validate_all_tabs(self) -> Dict[str, List[str]]:
        """Validate all registered tabs"""
        results = {}
        for tab_id in self._registered_tabs:
            results[tab_id] = self.validate_tab(tab_id)
        return results
    
    def _validate_all_tabs(self):
        """Internal method for periodic validation"""
        if self._validation_enabled:
            invalid_count = len(self._invalid_tabs)
            results = self.validate_all_tabs()
            new_invalid_count = len(self._invalid_tabs)
            
            if new_invalid_count != invalid_count:
                self._logger.info(f"Validation complete: {new_invalid_count} invalid tabs")
    
    # =============================================================================
    # Performance Monitoring
    # =============================================================================
    
    def get_tab_performance_metrics(self, tab_id: str) -> Optional[Dict[str, Any]]:
        """Get performance metrics for a specific tab"""
        registration = self._registered_tabs.get(tab_id)
        if registration and registration.performance_monitor:
            return registration.performance_monitor.get_performance_report()
        return None
    
    def get_all_performance_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get performance metrics for all tabs"""
        metrics = {}
        for tab_id, registration in self._registered_tabs.items():
            if registration.performance_monitor:
                metrics[tab_id] = registration.performance_monitor.get_performance_report()
        return metrics
    
    def check_performance_alerts(self):
        """Check for performance issues and emit alerts"""
        for tab_id, registration in self._registered_tabs.items():
            if registration.performance_monitor:
                metrics = registration.performance_monitor.get_performance_report()
                
                # Check for slow operations (> 5 seconds)
                for metric_name, value in metrics.items():
                    if metric_name.endswith('_time') and isinstance(value, (int, float)) and value > 5.0:
                        self.performance_alert.emit(tab_id, metric_name, value)
    
    # =============================================================================
    # Event Handlers
    # =============================================================================
    
    def _connect_tab_signals(self, tab: BaseTab):
        """Connect tab signals to manager handlers"""
        tab.tab_activated.connect(lambda: self._on_tab_signal_activated(tab.get_tab_id()))
        tab.tab_deactivated.connect(lambda: self._on_tab_signal_deactivated(tab.get_tab_id()))
        tab.tab_data_changed.connect(lambda: self._on_tab_signal_data_changed(tab.get_tab_id()))
    
    def _disconnect_tab_signals(self, tab: BaseTab):
        """Disconnect tab signals from manager handlers"""
        # Note: In a real implementation, you'd need to store signal connections to properly disconnect
        # For now, we'll rely on tab cleanup
        pass
    
    def _on_tab_signal_activated(self, tab_id: str):
        """Handle tab activation signal"""
        if self._active_tab_id != tab_id:
            self._active_tab_id = tab_id
            if tab_id in self._registered_tabs:
                self._registered_tabs[tab_id].last_activated = datetime.now()
    
    def _on_tab_signal_deactivated(self, tab_id: str):
        """Handle tab deactivation signal"""
        if self._active_tab_id == tab_id:
            self._active_tab_id = None
    
    def _on_tab_signal_data_changed(self, tab_id: str):
        """Handle tab data change signal"""
        self._dirty_tabs.add(tab_id)
        if tab_id in self._registered_tabs:
            self._registered_tabs[tab_id].is_dirty = True
        self.tab_state_changed.emit(tab_id, True)
    
    def _on_tab_widget_changed(self, index: int):
        """Handle QTabWidget tab change"""
        if self._tab_widget and index >= 0:
            widget = self._tab_widget.widget(index)
            if isinstance(widget, BaseTab):
                self.activate_tab(widget.get_tab_id())
    
    def _handle_tab_activated(self, event: ComponentEvent):
        """Handle tab activation events from component bus"""
        tab_id = event.data.get('tab_id')
        if tab_id and tab_id in self._registered_tabs:
            self._on_tab_signal_activated(tab_id)
    
    def _handle_tab_deactivated(self, event: ComponentEvent):
        """Handle tab deactivation events from component bus"""
        tab_id = event.data.get('tab_id')
        if tab_id and tab_id in self._registered_tabs:
            self._on_tab_signal_deactivated(tab_id)
    
    def _handle_tab_data_changed(self, event: ComponentEvent):
        """Handle tab data change events from component bus"""
        tab_id = event.data.get('tab_id')
        if tab_id and tab_id in self._registered_tabs:
            self._on_tab_signal_data_changed(tab_id)
    
    def _handle_theme_changed(self, event: ComponentEvent):
        """Handle theme change events from component bus"""
        if 'theme' in event.data:
            self.apply_global_theme(event.data['theme'])
    
    def _handle_state_changed(self, event: ComponentEvent):
        """Handle general state change events from component bus"""
        tab_id = event.data.get('tab_id')
        if tab_id and tab_id in self._registered_tabs:
            self._dirty_tabs.add(tab_id)
    
    # =============================================================================
    # Debug and Diagnostics
    # =============================================================================
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Get comprehensive debug information"""
        return {
            'registered_tabs': list(self._registered_tabs.keys()),
            'active_tab': self._active_tab_id,
            'dirty_tabs': list(self._dirty_tabs),
            'invalid_tabs': list(self._invalid_tabs),
            'auto_save_interval': self._auto_save_interval,
            'performance_monitoring': self._performance_monitoring,
            'validation_enabled': self._validation_enabled,
            'debug_mode': self._debug_mode,
            'state_manager_info': {
                'total_snapshots': len(self._state_manager._state_snapshots),
                'total_transactions': len(self._state_manager._transactions)
            },
            'tab_details': {
                tab_id: {
                    'registration_time': reg.registration_time.isoformat(),
                    'last_activated': reg.last_activated.isoformat() if reg.last_activated else None,
                    'is_dirty': reg.is_dirty,
                    'validation_errors': reg.validation_errors or [],
                    'config': asdict(reg.config)
                }
                for tab_id, reg in self._registered_tabs.items()
            }
        }
    
    def cleanup(self) -> None:
        """Cleanup tab manager resources"""
        try:
            # Stop timers
            self._auto_save_timer.stop()
            self._validation_timer.stop()
            
            # Save all dirty tabs
            self.save_all_tab_states()
            
            # Cleanup state manager
            self._state_manager.cleanup()
            
            # Clear registrations
            self._registered_tabs.clear()
            self._dirty_tabs.clear()
            self._invalid_tabs.clear()
            
            self._logger.info("Tab manager cleanup completed")
            
        except Exception as e:
            self._logger.error(f"Error during tab manager cleanup: {e}")


# Global tab manager instance
_tab_manager: Optional[TabManager] = None

def get_tab_manager() -> TabManager:
    """Get the global tab manager instance"""
    global _tab_manager
    if _tab_manager is None:
        _tab_manager = TabManager()
    return _tab_manager

def initialize_tab_manager(tab_widget: Optional[QTabWidget] = None) -> TabManager:
    """Initialize the global tab manager with optional tab widget"""
    global _tab_manager
    _tab_manager = TabManager(tab_widget)
    return _tab_manager 