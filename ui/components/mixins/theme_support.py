"""
Theme Support Mixin

Provides standardized theme management for UI components.
Extracted from downloaded_videos_tab.py and video_info_tab.py apply_theme_colors methods.
"""

from typing import Dict, Any
from ..common.events import EventEmitter, EventSubscriber, EventType

class ThemeSupport(EventEmitter, EventSubscriber):
    """Mixin providing standardized theme management"""
    
    def __init__(self, component_name: str):
        EventEmitter.__init__(self, component_name)
        EventSubscriber.__init__(self, component_name)
        self._current_theme = {}
        
        # Subscribe to theme change events
        self.subscribe_to_event(EventType.THEME_CHANGED, self._on_theme_changed)
    
    def apply_theme(self, theme: Dict[str, Any]):
        """Apply theme to component"""
        self._current_theme = theme.copy()
        
        # Apply base theme elements
        self._apply_base_theme(theme)
        
        # Apply component-specific theme
        self._apply_component_theme(theme)
        
        # Emit theme applied event
        self.emit_event(EventType.THEME_CHANGED, {
            'theme': theme,
            'component': self.component_name
        })
    
    def _apply_base_theme(self, theme: Dict[str, Any]):
        """Apply common theme elements - override in subclasses if needed"""
        # Common theme application logic
        if hasattr(self, 'setStyleSheet') and 'background_color' in theme:
            self.setStyleSheet(f"background-color: {theme['background_color']};")
    
    def _apply_component_theme(self, theme: Dict[str, Any]):
        """Apply component-specific theme - override in subclasses"""
        # To be implemented by subclasses for specific theming needs
        pass
    
    def get_current_theme(self) -> Dict[str, Any]:
        """Get currently applied theme"""
        return self._current_theme.copy()
    
    def _on_theme_changed(self, event):
        """Handle theme change events from other components"""
        if 'theme' in event.data and event.source_component != self.component_name:
            # Apply theme if it's not from this component (avoid circular updates)
            self.apply_theme(event.data['theme'])
    
    def emit_theme_changed(self, theme: Dict[str, Any]):
        """Emit theme change event"""
        self.emit_event(EventType.THEME_CHANGED, {
            'theme': theme,
            'source': 'manual_change'
        })
    
    def apply_dark_theme(self):
        """Apply predefined dark theme"""
        dark_theme = {
            'background_color': '#2b2b2b',
            'text_color': '#ffffff',
            'accent_color': '#0078d4',
            'border_color': '#555555',
            'hover_color': '#404040'
        }
        self.apply_theme(dark_theme)
    
    def apply_light_theme(self):
        """Apply predefined light theme"""
        light_theme = {
            'background_color': '#ffffff',
            'text_color': '#000000',
            'accent_color': '#0078d4',
            'border_color': '#cccccc',
            'hover_color': '#f0f0f0'
        }
        self.apply_theme(light_theme)
    
    def __del__(self):
        """Cleanup subscriptions on destruction"""
        if hasattr(self, 'cleanup_subscriptions'):
            self.cleanup_subscriptions() 