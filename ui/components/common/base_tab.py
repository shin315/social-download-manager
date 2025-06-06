"""
Base Tab Implementation

This module provides the abstract BaseTab class that all tab implementations
should inherit from. It integrates with the component architecture from Task 15
and provides standardized lifecycle management, state handling, and theme support.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import asdict
from PyQt6.QtWidgets import QWidget, QTableWidget, QProgressBar, QComboBox
from PyQt6.QtCore import pyqtSignal, QObject, QEvent
import json
import os

from .tab_interfaces import (
    TabInterface, TabLifecycleInterface, TabNavigationInterface,
    TabDataInterface, TabValidationInterface, TabStateInterface,
    FullTabProtocol
)
from .models import TabConfig, TabState
from .events import get_event_bus, EventType, ComponentEvent
# Use lazy imports to avoid circular dependency
# from ..mixins import LanguageSupport, ThemeSupport, TooltipSupport
from .tab_styling import TabStyleManager, TabStyleHelper, TabStyleVariant, apply_tab_theme
from . import QWidgetABCMeta


class BaseTab(QWidget, TabInterface, metaclass=QWidgetABCMeta):
    """
    Abstract base class for all tab implementations.
    Note: Temporarily removed mixins inheritance to avoid circular dependency.
    TODO: Refactor to use composition pattern instead of multiple inheritance.
    """
    
    # Tab-specific signals
    tab_activated = pyqtSignal()
    tab_deactivated = pyqtSignal()
    tab_data_changed = pyqtSignal()
    tab_validation_changed = pyqtSignal(bool)  # True if valid, False if invalid
    tab_initialized = pyqtSignal()
    tab_cleanup_requested = pyqtSignal()
    
    def __init__(self, config: TabConfig, parent: Optional[QWidget] = None):
        """
        Initialize the base tab.
        
        Args:
            config: Tab configuration object
            parent: Parent widget (typically MainWindow)
        """
        super().__init__(parent)
        
        # Store configuration and parent reference
        self._config = config
        self._parent_window = parent
        
        # Initialize state
        self._tab_state = TabState()
        self._is_initialized = False
        self._is_active = False
        self._data_dirty = False
        self._validation_errors: List[str] = []
        
        # Get language manager from parent
        self._lang_manager = None
        if parent and hasattr(parent, 'lang_manager'):
            self._lang_manager = parent.lang_manager
        elif parent and hasattr(parent, 'language_manager'):
            self._lang_manager = parent.language_manager
        
        # Log language manager status (debug mode only)
        if hasattr(self, '_config') and getattr(self._config, 'debug_mode', False):
            if self._lang_manager:
                print(f"DEBUG: BaseTab got language manager: {type(self._lang_manager)}")
            else:
                print(f"DEBUG: BaseTab NO language manager from parent: {parent}")
        
        # Connect to global component bus if available
        self._component_bus = get_event_bus()
        
        # Styling integration
        self._style_manager = TabStyleManager()
        self._style_helper = TabStyleHelper(self._style_manager)
        self._current_style_variant = TabStyleVariant.DEFAULT
        
        # Initialize mixins
        if config.component_integration:
            # NOTE: Mixins are currently disabled due to circular dependency issues
            # TODO: Refactor to use composition pattern instead of multiple inheritance
            try:
                # Initialize mixins based on config - check if parent has required attributes
                # if parent and hasattr(parent, 'lang_manager'):
                #     LanguageSupport.__init__(self, parent.lang_manager)
                # else:
                #     LanguageSupport.__init__(self, None)
                # 
                # ThemeSupport.__init__(self, {})  # Will be set via apply_theme
                # TooltipSupport.__init__(self)
                pass  # Placeholder until mixins are properly implemented
            except Exception as e:
                # Ignore mixin initialization errors for now
                print(f"Warning: Mixin initialization failed: {e}")
                pass
        
        # Set up component bus subscriptions
        self._setup_component_subscriptions()
        
        # Perform initialization if lifecycle hooks are enabled
        if self._config.lifecycle_hooks:
            self._initialize_lifecycle()
    
    def _initialize_lifecycle(self) -> None:
        """Initialize lifecycle hooks and connect signals"""
        # Connect tab signals
        self.tab_activated.connect(self._on_activated_wrapper)
        self.tab_deactivated.connect(self._on_deactivated_wrapper)
        
        # Connect to component bus events if component integration is enabled
        if self._config.component_integration and self._component_bus:
            self._component_bus.subscribe(EventType.LANGUAGE_CHANGED, self._handle_language_change)
            self._component_bus.subscribe(EventType.THEME_CHANGED, self._handle_theme_change)
        
        # Perform tab initialization
        self.on_tab_initialization()
        self._is_initialized = True
    
    # =============================================================================
    # Abstract methods that concrete tabs must implement
    # =============================================================================
    
    @abstractmethod
    def setup_ui(self) -> None:
        """Initialize the tab's UI components"""
        pass
    
    @abstractmethod
    def get_tab_id(self) -> str:
        """Return unique identifier for this tab"""
        pass
    
    @abstractmethod
    def load_data(self) -> None:
        """Load tab-specific data"""
        pass
    
    @abstractmethod
    def save_data(self) -> bool:
        """Save tab data, return success status"""
        pass
    
    @abstractmethod
    def refresh_data(self) -> None:
        """Refresh/reload tab data"""
        pass
    
    @abstractmethod
    def validate_input(self) -> List[str]:
        """Validate tab input, return list of error messages"""
        pass
    
    # =============================================================================
    # TabLifecycleInterface implementation
    # =============================================================================
    
    def on_tab_activated(self) -> None:
        """Called when tab becomes active - can be overridden by subclasses"""
        if self._config.state_persistence:
            self.restore_tab_state()
    
    def on_tab_deactivated(self) -> None:
        """Called when tab becomes inactive - can be overridden by subclasses"""
        if self._config.auto_save and self.is_data_dirty():
            self.save_data()
        if self._config.state_persistence:
            self.save_tab_state()
    
    def on_tab_initialization(self) -> None:
        """Called during tab initialization - can be overridden by subclasses"""
        self.setup_ui()
        self.load_data()
    
    def on_tab_cleanup(self) -> None:
        """Called when tab is being destroyed - can be overridden by subclasses"""
        if self._config.auto_save and self.is_data_dirty():
            self.save_data()
        
        # Disconnect from component bus
        if self._component_bus:
            # Clean up subscriptions - we need to track them for cleanup
            pass  # Implement proper cleanup when we add subscription tracking
    
    def _on_activated_wrapper(self) -> None:
        """Internal wrapper for tab activation"""
        self._is_active = True
        self.on_tab_activated()
        
        # Emit component bus event
        if self._component_bus:
            self._component_bus.emit_event(
                event_type=EventType.TAB_ACTIVATED,
                source_component=self.get_tab_id(),
                data={
                    'tab_id': self.get_tab_id(),
                    'tab_instance': self
                }
            )
    
    def _on_deactivated_wrapper(self) -> None:
        """Internal wrapper for tab deactivation"""
        self._is_active = False
        self.on_tab_deactivated()
        
        # Emit component bus event
        if self._component_bus:
            self._component_bus.emit_event(
                event_type=EventType.TAB_DEACTIVATED,
                source_component=self.get_tab_id(),
                data={
                    'tab_id': self.get_tab_id(),
                    'tab_instance': self
                }
            )
    
    # =============================================================================
    # TabNavigationInterface implementation
    # =============================================================================
    
    def can_navigate_away(self) -> bool:
        """Check if user can navigate away from this tab"""
        if self._config.validation_required and not self.is_valid():
            return False
        
        if self._config.auto_save:
            return True
        
        # If auto-save is disabled and data is dirty, ask user
        return not self.is_data_dirty()
    
    def get_tab_title(self) -> str:
        """Get localized tab title"""
        return self.tr_(self._config.title_key)
    
    def get_tab_icon(self) -> Optional[str]:
        """Get tab icon path/name"""
        return self._config.icon_path
    
    # =============================================================================
    # TabDataInterface implementation
    # =============================================================================
    
    def is_data_dirty(self) -> bool:
        """Check if tab has unsaved changes"""
        return self._data_dirty
    
    def _set_data_dirty(self, dirty: bool = True) -> None:
        """Mark tab data as dirty or clean"""
        if self._data_dirty != dirty:
            self._data_dirty = dirty
            self.tab_data_changed.emit()
    
    # =============================================================================
    # TabValidationInterface implementation
    # =============================================================================
    
    def is_valid(self) -> bool:
        """Check if tab is in valid state"""
        errors = self.validate_input()
        return len(errors) == 0
    
    def show_validation_errors(self, errors: List[str]) -> None:
        """Display validation errors to user - default implementation"""
        self._validation_errors = errors
        self.tab_validation_changed.emit(len(errors) == 0)
        
        # Can be overridden by subclasses for custom error display
        if errors:
            print(f"Validation errors in tab {self.get_tab_id()}: {errors}")
    
    # =============================================================================
    # TabStateInterface implementation
    # =============================================================================
    
    def get_state(self) -> Dict[str, Any]:
        """Get current component state"""
        return {
            'tab_state': self.get_tab_state().__dict__,
            'data_dirty': self._data_dirty,
            'validation_errors': self._validation_errors
        }
    
    def set_state(self, state: Dict[str, Any]) -> None:
        """Set component state"""
        if 'tab_state' in state:
            tab_state = TabState()
            tab_state.__dict__.update(state['tab_state'])
            self.set_tab_state(tab_state)
        
        if 'data_dirty' in state:
            self._data_dirty = state['data_dirty']
        
        if 'validation_errors' in state:
            self._validation_errors = state['validation_errors']
    
    def clear_state(self) -> None:
        """Clear all component state"""
        self._tab_state.clear()
        self._data_dirty = False
        self._validation_errors.clear()
    
    def get_tab_state(self) -> TabState:
        """Get complete tab state"""
        return self._tab_state
    
    def set_tab_state(self, state: TabState) -> None:
        """Set tab state from TabState object"""
        self._tab_state = state
    
    def save_tab_state(self) -> None:
        """Persist tab state to storage - can be overridden"""
        # Default implementation does nothing
        # Subclasses can override to implement actual persistence
        pass
    
    def restore_tab_state(self) -> None:
        """Restore tab state from storage - can be overridden"""
        # Default implementation does nothing
        # Subclasses can override to implement actual restoration
        pass
    
    # =============================================================================
    # Theme and Language Support (integrating with Task 15 mixins)
    # =============================================================================
    
    def get_language_manager(self):
        """Get language manager instance"""
        return self._lang_manager
    
    def update_language(self) -> None:
        """Update UI language - placeholder method"""
        # NOTE: This is a placeholder for mixin functionality
        # TODO: Implement proper language update when mixins are restored
        pass
    
    def tr_(self, key: str) -> str:
        """Translate text key - now properly connected to language manager"""
        if self._lang_manager:
            # Try tr_ first (for compatibility), then tr
            if hasattr(self._lang_manager, 'tr_'):
                return self._lang_manager.tr_(key)
            elif hasattr(self._lang_manager, 'tr'):
                return self._lang_manager.tr(key)
        return key  # Return key as fallback
    
    def _handle_language_change(self, event) -> None:
        """Handle language change events from component bus"""
        self.update_language()
    
    def _handle_theme_change(self, event) -> None:
        """Handle theme change events from component bus"""
        if hasattr(event, 'data') and 'theme' in event.data:
            self.apply_theme(event.data['theme'])
    
    def apply_theme(self, theme_data: Dict[str, Any]) -> None:
        """Apply theme to the tab (ThemeSupport integration)"""
        try:
            # NOTE: Mixins are currently disabled, so we skip super().apply_theme()
            # TODO: Re-enable when mixins are properly implemented
            # super().apply_theme(theme_data)  # Disabled due to missing mixins
            
            # Apply styling framework theme
            self._apply_styling_theme(theme_data)
            
        except Exception as e:
            print(f"Error applying theme to tab {self.get_tab_id()}: {e}")
    
    def apply_theme_colors(self, theme: Dict[str, Any]) -> None:
        """Apply theme colors using the styling framework"""
        try:
            # Determine theme name from theme data
            theme_name = self._determine_theme_name(theme)
            
            # Update style manager theme
            self._style_manager.set_theme(theme_name)
            
            # Reapply styling with new theme
            self._style_helper.apply_tab_style(self, self._current_style_variant, theme_name)
            
            # Apply theme to child widgets
            self._apply_theme_to_children(theme)
            
        except Exception as e:
            print(f"Error applying theme colors: {e}")
    
    def _apply_styling_theme(self, theme_data: Dict[str, Any]) -> None:
        """Apply styling framework theme"""
        try:
            # Convert theme data to styling framework format
            theme_name = self._determine_theme_name(theme_data)
            
            # Apply theme through styling framework
            self._style_helper.apply_tab_style(self, self._current_style_variant, theme_name)
            
        except Exception as e:
            print(f"Error applying styling theme: {e}")
    
    def _determine_theme_name(self, theme_data: Dict[str, Any]) -> str:
        """Determine theme name from theme data"""
        # Check for dark theme indicators
        bg_color = theme_data.get('background', '#ffffff').lower()
        if bg_color in ['#1e1e1e', '#2d2d30', '#000000'] or 'dark' in str(theme_data.get('name', '')).lower():
            return 'dark'
        
        # Check for high contrast indicators
        if theme_data.get('high_contrast', False) or 'contrast' in str(theme_data.get('name', '')).lower():
            return 'high_contrast'
        
        # Default to light theme
        return 'light'
    
    def _apply_theme_to_children(self, theme: Dict[str, Any]) -> None:
        """Apply theme to specific child widgets"""
        try:
            # Apply to tables
            for table in self.findChildren(QTableWidget):
                self._style_helper.apply_theme_colors_to_widget(table, 'table', theme, self._current_style_variant)
            
            # Apply to progress bars
            for progress in self.findChildren(QProgressBar):
                self._style_helper.apply_theme_colors_to_widget(progress, 'progress', theme, self._current_style_variant)
            
            # Apply to combo boxes
            for combo in self.findChildren(QComboBox):
                self._style_helper.apply_theme_colors_to_widget(combo, 'combo', theme, self._current_style_variant)
            
        except Exception as e:
            print(f"Error applying theme to children: {e}")
    
    # =============================================================================
    # Parent Window Integration
    # =============================================================================
    
    def get_parent_window(self):
        """Get parent window reference"""
        return self._parent_window
    
    def set_parent_window(self, parent) -> None:
        """Set parent window reference"""
        self._parent_window = parent
    
    def emit_to_parent(self, signal_name: str, *args) -> None:
        """Emit signal to parent window"""
        if self._parent_window and hasattr(self._parent_window, signal_name):
            signal = getattr(self._parent_window, signal_name)
            if hasattr(signal, 'emit'):
                signal.emit(*args)
    
    # =============================================================================
    # Signal Management
    # =============================================================================
    
    def connect_tab_signals(self) -> None:
        """Connect all tab-specific signals - can be overridden"""
        # Default implementation connects to component bus
        if self._component_bus and self._config.component_integration:
            self.tab_activated.connect(
                lambda: self._component_bus.emit_event(
                    event_type=EventType.TAB_ACTIVATED,
                    source_component=self.get_tab_id(),
                    data={'tab_id': self.get_tab_id()}
                )
            )
    
    def disconnect_tab_signals(self) -> None:
        """Disconnect all tab-specific signals"""
        # For now, just emit cleanup event
        if self._component_bus:
            self._component_bus.emit_event(
                event_type=EventType.TAB_CLEANUP,
                source_component=self.get_tab_id(),
                data={'tab_id': self.get_tab_id()}
            )
    
    def emit_tab_event(self, event_type: str, data: Any = None) -> None:
        """Emit tab event through component bus"""
        if self._component_bus:
            # Convert string event_type to EventType enum if needed
            if isinstance(event_type, str):
                try:
                    event_type_enum = EventType(event_type)
                except ValueError:
                    print(f"Unknown event type: {event_type}")
                    return
            else:
                event_type_enum = event_type
            
            self._component_bus.emit_event(
                event_type=event_type_enum,
                source_component=self.get_tab_id(),
                data=data or {}
            )
    
    # =============================================================================
    # Utility methods
    # =============================================================================
    
    def is_initialized(self) -> bool:
        """Check if tab has been initialized"""
        return self._is_initialized
    
    def is_active(self) -> bool:
        """Check if tab is currently active"""
        return self._is_active
    
    def get_config(self) -> TabConfig:
        """Get tab configuration"""
        return self._config
    
    def closeEvent(self, event) -> None:
        """Handle tab close event"""
        self.on_tab_cleanup()
        super().closeEvent(event)

    def _initialize_tab(self) -> None:
        """Initialize the tab with all required setup"""
        try:
            # Setup UI first
            self.setup_ui()
            
            # Apply initial styling
            self._apply_initial_styling()
            
            # Load data if required
            if self._config.state_persistence:
                self.load_data()
            
            # Set up lifecycle hooks
            if self._config.lifecycle_hooks:
                self._setup_lifecycle_hooks()
            
            # Mark as initialized
            self._is_initialized = True
            self.tab_initialized.emit()
            
            # Emit initialization event
            self._emit_tab_event('tab_initialized', {
                'tab_id': self.get_tab_id(),
                'config': asdict(self._config)
            })
            
        except Exception as e:
            print(f"Error initializing tab {self.get_tab_id()}: {e}")
            raise

    def _apply_initial_styling(self) -> None:
        """Apply initial styling to the tab"""
        try:
            # Determine style variant based on tab type
            tab_id = self.get_tab_id()
            if 'download' in tab_id or 'video_info' in tab_id:
                self._current_style_variant = TabStyleVariant.DOWNLOAD
            elif 'data' in tab_id or 'downloaded' in tab_id:
                self._current_style_variant = TabStyleVariant.DATA_MANAGEMENT
            elif 'settings' in tab_id or 'config' in tab_id:
                self._current_style_variant = TabStyleVariant.SETTINGS
            elif 'analytics' in tab_id or 'stats' in tab_id:
                self._current_style_variant = TabStyleVariant.ANALYTICS
            else:
                self._current_style_variant = TabStyleVariant.DEFAULT
            
            # Apply styling
            apply_tab_theme(self, self._current_style_variant)
            
        except Exception as e:
            print(f"Error applying initial styling: {e}")

    def set_style_variant(self, variant: TabStyleVariant) -> None:
        """Set the styling variant for this tab"""
        try:
            self._current_style_variant = variant
            # Reapply styling with new variant
            self._style_helper.apply_tab_style(self, variant)
        except Exception as e:
            print(f"Error setting style variant: {e}")
    
    def get_style_variant(self) -> TabStyleVariant:
        """Get the current styling variant"""
        return self._current_style_variant
    
    def update_widget_style_property(self, widget: QWidget, property_name: str, value: Any) -> None:
        """Update widget style property and refresh styling"""
        try:
            self._style_helper.update_widget_property(widget, property_name, value)
        except Exception as e:
            print(f"Error updating widget style property: {e}")

    def _setup_component_subscriptions(self) -> None:
        """Set up component bus event subscriptions"""
        try:
            # Subscribe to relevant events
            self._component_bus.subscribe(EventType.THEME_CHANGED, self._handle_theme_changed)
            self._component_bus.subscribe(EventType.LANGUAGE_CHANGED, self._handle_language_changed)
            
            # Store subscriptions for cleanup
            self._component_subscriptions = [
                (EventType.THEME_CHANGED, self._handle_theme_changed),
                (EventType.LANGUAGE_CHANGED, self._handle_language_changed)
            ]
            
        except Exception as e:
            print(f"Error setting up component subscriptions: {e}")
    
    def _setup_lifecycle_hooks(self) -> None:
        """Set up lifecycle hooks if enabled"""
        try:
            # Connect lifecycle signals to internal handlers
            self.tab_activated.connect(self._on_tab_activated_internal)
            self.tab_deactivated.connect(self._on_tab_deactivated_internal)
            self.tab_data_changed.connect(self._on_tab_data_changed_internal)
            
        except Exception as e:
            print(f"Error setting up lifecycle hooks: {e}")
    
    def _on_tab_activated_internal(self) -> None:
        """Internal tab activation handler"""
        try:
            self._is_active = True
            self.on_tab_activated()
        except Exception as e:
            print(f"Error in internal tab activation: {e}")
    
    def _on_tab_deactivated_internal(self) -> None:
        """Internal tab deactivation handler"""
        try:
            self._is_active = False
            self.on_tab_deactivated()
        except Exception as e:
            print(f"Error in internal tab deactivation: {e}")
    
    def _on_tab_data_changed_internal(self) -> None:
        """Internal tab data change handler"""
        try:
            self._data_dirty = True
        except Exception as e:
            print(f"Error in internal data change handler: {e}")
    
    def _handle_theme_changed(self, event: ComponentEvent) -> None:
        """Handle theme changed events from component bus"""
        try:
            if 'theme' in event.data:
                self.apply_theme(event.data['theme'])
        except Exception as e:
            print(f"Error handling theme change: {e}")
    
    def _handle_language_changed(self, event: ComponentEvent) -> None:
        """Handle language changed events from component bus"""
        try:
            self.update_language()
        except Exception as e:
            print(f"Error handling language change: {e}") 