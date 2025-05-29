"""
Language Support Mixin

Provides standardized language management for UI components.
Extracted from downloaded_videos_tab.py and video_info_tab.py.
"""

from typing import Optional
from ..common.events import EventEmitter, EventSubscriber, EventType

class LanguageSupport(EventEmitter, EventSubscriber):
    """Mixin providing standardized language management"""
    
    def __init__(self, component_name: str, lang_manager=None):
        EventEmitter.__init__(self, component_name)
        EventSubscriber.__init__(self, component_name)
        self._lang_manager = lang_manager
        
        # Subscribe to language change events
        self.subscribe_to_event(EventType.LANGUAGE_CHANGED, self._on_language_changed)
    
    def init_language_support(self, lang_manager=None):
        """Initialize language support with language manager"""
        if lang_manager:
            self._lang_manager = lang_manager
    
    def tr_(self, key: str) -> str:
        """Translate text using language manager"""
        if hasattr(self, '_lang_manager') and self._lang_manager:
            return self._lang_manager.tr(key)
        return key  # Fallback if no language manager
    
    def update_language(self):
        """Update component language - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement update_language()")
    
    def set_language_manager(self, lang_manager):
        """Set the language manager"""
        self._lang_manager = lang_manager
        self.update_language()
    
    def get_language_manager(self):
        """Get the current language manager"""
        return self._lang_manager
    
    def _on_language_changed(self, event):
        """Handle language change events"""
        # Update language manager if provided in event
        if 'lang_manager' in event.data:
            self._lang_manager = event.data['lang_manager']
        
        # Update component language
        try:
            self.update_language()
        except NotImplementedError:
            # If subclass hasn't implemented update_language, that's ok
            pass
    
    def emit_language_changed(self, new_language: str):
        """Emit language change event"""
        self.emit_event(EventType.LANGUAGE_CHANGED, {
            'language': new_language,
            'lang_manager': self._lang_manager
        })
    
    def __del__(self):
        """Cleanup subscriptions on destruction"""
        if hasattr(self, 'cleanup_subscriptions'):
            self.cleanup_subscriptions() 