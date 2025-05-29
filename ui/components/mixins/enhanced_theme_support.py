"""
Enhanced Theme Support Mixin

Advanced theming support that integrates with ComponentThemeManager,
providing automatic theme application, state management, and responsive design.

This mixin extends the basic ThemeSupport with:
- Component-specific theming
- State-based styling
- Responsive design support
- Dynamic theme switching
- Theme animation support
"""

from typing import Dict, Any, Optional, List, Callable
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QResizeEvent
from abc import ABC, abstractmethod

from .theme_support import ThemeSupport
from ..common.component_theming import (
    ComponentThemeManager, ComponentThemeType, ComponentState,
    ResponsiveBreakpoint, get_component_theme_manager, apply_component_theme
)
from ..common.events import EventType, ComponentEvent


class EnhancedThemeSupport(ThemeSupport):
    """
    Enhanced theme support mixin with component-specific theming,
    state management, and responsive design capabilities.
    """
    
    # Enhanced theme signals
    theme_state_changed = pyqtSignal(str)  # state
    responsive_breakpoint_changed = pyqtSignal(str)  # breakpoint
    theme_animation_finished = pyqtSignal()
    
    def __init__(self, 
                 component_name: str,
                 component_type: ComponentThemeType = ComponentThemeType.WIDGET,
                 auto_theme: bool = True):
        super().__init__(component_name)
        
        # Component theming properties
        self._component_type = component_type
        self._component_id = f"{component_name}_{id(self)}"
        self._current_state = ComponentState.NORMAL
        self._current_breakpoint = ResponsiveBreakpoint.DESKTOP
        self._auto_theme = auto_theme
        
        # Theme manager integration
        self._theme_manager = get_component_theme_manager()
        self._active_theme_name = "light"
        
        # State management
        self._state_change_timer = QTimer()
        self._state_change_timer.setSingleShot(True)
        self._state_change_timer.timeout.connect(self._apply_deferred_state_change)
        
        # Responsive design
        self._last_widget_size = None
        self._responsive_enabled = True
        
        # Theme callbacks
        self._state_change_callbacks: List[Callable[[ComponentState], None]] = []
        self._breakpoint_change_callbacks: List[Callable[[ResponsiveBreakpoint], None]] = []
        
        # Initialize theme if auto-theming is enabled
        if self._auto_theme and hasattr(self, 'setStyleSheet'):
            self._initialize_component_theming()
    
    def _initialize_component_theming(self):
        """Initialize component theming with default settings"""
        try:
            # Apply default theme
            self.apply_component_theme(self._active_theme_name)
            
            # Subscribe to global theme changes
            self.subscribe_to_event(EventType.THEME_CHANGED, self._on_global_theme_changed)
            
        except Exception as e:
            print(f"Error initializing component theming: {e}")
    
    # =========================================================================
    # Enhanced Theme Management
    # =========================================================================
    
    def apply_component_theme(self, 
                             theme_name: str,
                             force_refresh: bool = False) -> bool:
        """Apply component-specific theme"""
        try:
            if not force_refresh and theme_name == self._active_theme_name:
                return True
            
            # Generate and apply CSS
            css = self._theme_manager.apply_theme_to_component(
                component_id=self._component_id,
                theme_name=theme_name,
                component_type=self._component_type,
                widget=self if isinstance(self, QWidget) else None,
                state=self._current_state
            )
            
            # Apply to widget if applicable
            if hasattr(self, 'setStyleSheet') and css:
                self.setStyleSheet(css)
            
            # Update state
            self._active_theme_name = theme_name
            
            # Emit theme change signal
            self.emit_event(EventType.THEME_CHANGED, {
                'theme_name': theme_name,
                'component_id': self._component_id,
                'component_type': self._component_type.value
            })
            
            return True
            
        except Exception as e:
            print(f"Error applying component theme: {e}")
            return False
    
    def set_component_state(self, 
                           state: ComponentState,
                           apply_immediately: bool = True) -> bool:
        """Set component state and update styling"""
        try:
            if state == self._current_state:
                return True
            
            old_state = self._current_state
            self._current_state = state
            
            # Apply state change immediately or defer
            if apply_immediately:
                self._apply_state_change(old_state, state)
            else:
                # Defer state change to avoid rapid state changes
                self._state_change_timer.start(50)  # 50ms delay
            
            # Emit state change signal
            self.theme_state_changed.emit(state.value)
            
            # Call state change callbacks
            for callback in self._state_change_callbacks:
                try:
                    callback(state)
                except Exception as e:
                    print(f"Error in state change callback: {e}")
            
            return True
            
        except Exception as e:
            print(f"Error setting component state: {e}")
            return False
    
    def _apply_state_change(self, old_state: ComponentState, new_state: ComponentState):
        """Apply the actual state change"""
        try:
            # Update theme with new state
            css = self._theme_manager.apply_theme_to_component(
                component_id=self._component_id,
                theme_name=self._active_theme_name,
                component_type=self._component_type,
                widget=self if isinstance(self, QWidget) else None,
                state=new_state
            )
            
            # Apply CSS if widget supports it
            if hasattr(self, 'setStyleSheet') and css:
                self.setStyleSheet(css)
            
            # Handle specific state transitions
            self._handle_state_transition(old_state, new_state)
            
        except Exception as e:
            print(f"Error applying state change: {e}")
    
    def _apply_deferred_state_change(self):
        """Apply deferred state change"""
        self._apply_state_change(ComponentState.NORMAL, self._current_state)
    
    def _handle_state_transition(self, old_state: ComponentState, new_state: ComponentState):
        """Handle specific state transitions (can be overridden by subclasses)"""
        # Default implementation - can be extended by components
        if new_state == ComponentState.LOADING:
            self._handle_loading_state()
        elif new_state == ComponentState.ERROR:
            self._handle_error_state()
        elif new_state == ComponentState.SUCCESS:
            self._handle_success_state()
    
    def _handle_loading_state(self):
        """Handle loading state (override in subclasses)"""
        pass
    
    def _handle_error_state(self):
        """Handle error state (override in subclasses)"""
        pass
    
    def _handle_success_state(self):
        """Handle success state (override in subclasses)"""
        pass
    
    # =========================================================================
    # Responsive Design Support
    # =========================================================================
    
    def enable_responsive_design(self, enabled: bool = True):
        """Enable or disable responsive design"""
        self._responsive_enabled = enabled
        
        if enabled and isinstance(self, QWidget):
            # Force initial responsive check
            self._check_responsive_breakpoint()
    
    def _check_responsive_breakpoint(self):
        """Check and update responsive breakpoint"""
        if not self._responsive_enabled or not isinstance(self, QWidget):
            return
        
        try:
            current_size = (self.width(), self.height())
            
            # Only process if size actually changed
            if current_size == self._last_widget_size:
                return
            
            self._last_widget_size = current_size
            
            # Determine new breakpoint
            new_breakpoint = self._theme_manager._get_responsive_breakpoint(self)
            
            if new_breakpoint != self._current_breakpoint:
                old_breakpoint = self._current_breakpoint
                self._current_breakpoint = new_breakpoint
                
                # Apply responsive styling
                self._apply_responsive_styling(old_breakpoint, new_breakpoint)
                
                # Emit breakpoint change signal
                self.responsive_breakpoint_changed.emit(new_breakpoint.name)
                
                # Call breakpoint change callbacks
                for callback in self._breakpoint_change_callbacks:
                    try:
                        callback(new_breakpoint)
                    except Exception as e:
                        print(f"Error in breakpoint change callback: {e}")
        
        except Exception as e:
            print(f"Error checking responsive breakpoint: {e}")
    
    def _apply_responsive_styling(self, 
                                 old_breakpoint: ResponsiveBreakpoint,
                                 new_breakpoint: ResponsiveBreakpoint):
        """Apply responsive styling for new breakpoint"""
        try:
            # Reapply theme with new breakpoint
            css = self._theme_manager.apply_theme_to_component(
                component_id=self._component_id,
                theme_name=self._active_theme_name,
                component_type=self._component_type,
                widget=self if isinstance(self, QWidget) else None,
                state=self._current_state
            )
            
            if hasattr(self, 'setStyleSheet') and css:
                self.setStyleSheet(css)
            
            # Handle responsive-specific changes
            self._handle_responsive_change(old_breakpoint, new_breakpoint)
            
        except Exception as e:
            print(f"Error applying responsive styling: {e}")
    
    def _handle_responsive_change(self, 
                                 old_breakpoint: ResponsiveBreakpoint,
                                 new_breakpoint: ResponsiveBreakpoint):
        """Handle responsive breakpoint changes (override in subclasses)"""
        pass
    
    # =========================================================================
    # Event Handling
    # =========================================================================
    
    def resizeEvent(self, event: QResizeEvent):
        """Handle resize events for responsive design"""
        if hasattr(super(), 'resizeEvent'):
            super().resizeEvent(event)
        
        # Check responsive breakpoint on resize
        if self._responsive_enabled:
            # Use timer to avoid excessive breakpoint checks
            if not hasattr(self, '_resize_timer'):
                self._resize_timer = QTimer()
                self._resize_timer.setSingleShot(True)
                self._resize_timer.timeout.connect(self._check_responsive_breakpoint)
            
            self._resize_timer.start(100)  # 100ms delay
    
    def _on_global_theme_changed(self, event):
        """Handle global theme change events"""
        if 'theme_name' in event.data and event.source_component != self._component_id:
            # Apply global theme change
            theme_name = event.data['theme_name']
            self.apply_component_theme(theme_name, force_refresh=True)
    
    # =========================================================================
    # Callback Management
    # =========================================================================
    
    def add_state_change_callback(self, callback: Callable[[ComponentState], None]):
        """Add callback for state changes"""
        if callback not in self._state_change_callbacks:
            self._state_change_callbacks.append(callback)
    
    def remove_state_change_callback(self, callback: Callable[[ComponentState], None]):
        """Remove state change callback"""
        if callback in self._state_change_callbacks:
            self._state_change_callbacks.remove(callback)
    
    def add_breakpoint_change_callback(self, callback: Callable[[ResponsiveBreakpoint], None]):
        """Add callback for breakpoint changes"""
        if callback not in self._breakpoint_change_callbacks:
            self._breakpoint_change_callbacks.append(callback)
    
    def remove_breakpoint_change_callback(self, callback: Callable[[ResponsiveBreakpoint], None]):
        """Remove breakpoint change callback"""
        if callback in self._breakpoint_change_callbacks:
            self._breakpoint_change_callbacks.remove(callback)
    
    # =========================================================================
    # Theme Information and Control
    # =========================================================================
    
    def get_current_theme_name(self) -> str:
        """Get current theme name"""
        return self._active_theme_name
    
    def get_current_state(self) -> ComponentState:
        """Get current component state"""
        return self._current_state
    
    def get_current_breakpoint(self) -> ResponsiveBreakpoint:
        """Get current responsive breakpoint"""
        return self._current_breakpoint
    
    def get_available_themes(self) -> List[str]:
        """Get available theme names"""
        return self._theme_manager.get_available_themes()
    
    def get_component_theme_info(self) -> Dict[str, Any]:
        """Get comprehensive theme information"""
        return {
            'component_id': self._component_id,
            'component_type': self._component_type.value,
            'active_theme': self._active_theme_name,
            'current_state': self._current_state.value,
            'current_breakpoint': self._current_breakpoint.name,
            'responsive_enabled': self._responsive_enabled,
            'auto_theme': self._auto_theme,
            'available_themes': self.get_available_themes()
        }
    
    def export_component_theme_settings(self) -> Dict[str, Any]:
        """Export component theme settings"""
        return {
            'component_name': self.component_name,
            'component_type': self._component_type.value,
            'active_theme': self._active_theme_name,
            'responsive_enabled': self._responsive_enabled,
            'auto_theme': self._auto_theme
        }
    
    def import_component_theme_settings(self, settings: Dict[str, Any]) -> bool:
        """Import component theme settings"""
        try:
            if 'active_theme' in settings:
                self.apply_component_theme(settings['active_theme'])
            
            if 'responsive_enabled' in settings:
                self.enable_responsive_design(settings['responsive_enabled'])
            
            if 'auto_theme' in settings:
                self._auto_theme = settings['auto_theme']
            
            return True
            
        except Exception as e:
            print(f"Error importing component theme settings: {e}")
            return False
    
    # =========================================================================
    # Lifecycle Management
    # =========================================================================
    
    def cleanup_enhanced_theme_support(self):
        """Cleanup enhanced theme support resources"""
        try:
            # Stop timers
            if hasattr(self, '_state_change_timer'):
                self._state_change_timer.stop()
            
            if hasattr(self, '_resize_timer'):
                self._resize_timer.stop()
            
            # Clear callbacks
            self._state_change_callbacks.clear()
            self._breakpoint_change_callbacks.clear()
            
            # Cleanup base theme support
            if hasattr(super(), 'cleanup_subscriptions'):
                super().cleanup_subscriptions()
            
        except Exception as e:
            print(f"Error during enhanced theme support cleanup: {e}")
    
    def __del__(self):
        """Destructor with enhanced cleanup"""
        try:
            self.cleanup_enhanced_theme_support()
        except:
            pass  # Ignore errors during destruction


# ============================================================================= 
# Convenience Functions
# =============================================================================

def apply_enhanced_theme(widget: QWidget,
                        component_name: str,
                        theme_name: str = "light",
                        component_type: ComponentThemeType = ComponentThemeType.WIDGET,
                        state: ComponentState = ComponentState.NORMAL) -> bool:
    """Convenience function to apply enhanced theme to any widget"""
    try:
        # Generate component ID
        component_id = f"{component_name}_{id(widget)}"
        
        # Apply theme
        manager = get_component_theme_manager()
        css = manager.apply_theme_to_component(
            component_id, theme_name, component_type, widget, state
        )
        
        if css:
            widget.setStyleSheet(css)
            return True
            
        return False
        
    except Exception as e:
        print(f"Error applying enhanced theme: {e}")
        return False

def create_themed_widget(widget_class,
                        component_name: str,
                        theme_name: str = "light",
                        component_type: ComponentThemeType = ComponentThemeType.WIDGET,
                        *args, **kwargs):
    """Create a widget with enhanced theming applied"""
    try:
        # Create widget instance
        widget = widget_class(*args, **kwargs)
        
        # Apply enhanced theme
        apply_enhanced_theme(widget, component_name, theme_name, component_type)
        
        return widget
        
    except Exception as e:
        print(f"Error creating themed widget: {e}")
        return None 