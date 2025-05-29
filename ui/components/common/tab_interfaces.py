"""
Tab Interface Protocols

This module defines the interface protocols specifically for tab implementations,
building upon the component architecture established in Task 15.

These interfaces ensure consistency across all tab implementations while
providing integration with the existing component system.
"""

from abc import ABC, abstractmethod
from typing import List, Any, Dict, Optional, Protocol, Union
from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtWidgets import QWidget
from .interfaces import ComponentInterface, StateManagerInterface
from .models import TabConfig, TabState

class TabLifecycleInterface(ABC):
    """Interface for tab lifecycle management"""
    
    @abstractmethod
    def on_tab_activated(self) -> None:
        """Called when tab becomes active"""
        pass
    
    @abstractmethod
    def on_tab_deactivated(self) -> None:
        """Called when tab becomes inactive"""
        pass
    
    @abstractmethod
    def on_tab_initialization(self) -> None:
        """Called during tab initialization"""
        pass
    
    @abstractmethod
    def on_tab_cleanup(self) -> None:
        """Called when tab is being destroyed"""
        pass

class TabNavigationInterface(ABC):
    """Interface for tab navigation and communication"""
    
    @abstractmethod
    def can_navigate_away(self) -> bool:
        """Check if user can navigate away from this tab"""
        pass
    
    @abstractmethod
    def get_tab_id(self) -> str:
        """Get unique identifier for this tab"""
        pass
    
    @abstractmethod
    def get_tab_title(self) -> str:
        """Get localized tab title"""
        pass
    
    @abstractmethod
    def get_tab_icon(self) -> Optional[str]:
        """Get tab icon path/name"""
        pass

class TabDataInterface(ABC):
    """Interface for tab data management"""
    
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
    def is_data_dirty(self) -> bool:
        """Check if tab has unsaved changes"""
        pass

class TabValidationInterface(ABC):
    """Interface for tab input validation"""
    
    @abstractmethod
    def validate_input(self) -> List[str]:
        """Validate tab input, return list of error messages"""
        pass
    
    @abstractmethod
    def is_valid(self) -> bool:
        """Check if tab is in valid state"""
        pass
    
    @abstractmethod
    def show_validation_errors(self, errors: List[str]) -> None:
        """Display validation errors to user"""
        pass

class TabStateInterface(StateManagerInterface):
    """Interface for tab state management, extending base state interface"""
    
    @abstractmethod
    def get_tab_state(self) -> TabState:
        """Get complete tab state"""
        pass
    
    @abstractmethod
    def set_tab_state(self, state: TabState) -> None:
        """Set tab state from TabState object"""
        pass
    
    @abstractmethod
    def save_tab_state(self) -> None:
        """Persist tab state to storage"""
        pass
    
    @abstractmethod
    def restore_tab_state(self) -> None:
        """Restore tab state from storage"""
        pass

class TabInterface(ComponentInterface, TabLifecycleInterface, 
                  TabNavigationInterface, TabDataInterface, 
                  TabValidationInterface, TabStateInterface):
    """
    Complete tab interface combining all tab-specific protocols.
    
    This is the main interface that all tab implementations should follow.
    It combines component functionality with tab-specific requirements.
    """
    pass

# Protocol definitions for mixin support
class TabLanguageSupport(Protocol):
    """Protocol for tab language support"""
    
    def tr_(self, key: str) -> str:
        """Translate text using language manager"""
        ...
    
    def update_language(self) -> None:
        """Update tab language"""
        ...
    
    def get_language_manager(self):
        """Get language manager instance"""
        ...

class TabThemeSupport(Protocol):
    """Protocol for tab theme support"""
    
    def apply_theme_colors(self, theme: dict) -> None:
        """Apply theme colors to tab"""
        ...
    
    def get_theme_config(self) -> dict:
        """Get current theme configuration"""
        ...

class TabParentSupport(Protocol):
    """Protocol for parent window integration"""
    
    def get_parent_window(self):
        """Get parent window reference"""
        ...
    
    def set_parent_window(self, parent) -> None:
        """Set parent window reference"""
        ...
    
    def emit_to_parent(self, signal_name: str, *args) -> None:
        """Emit signal to parent window"""
        ...

class TabSignalSupport(Protocol):
    """Protocol for tab signal management"""
    
    def connect_tab_signals(self) -> None:
        """Connect all tab-specific signals"""
        ...
    
    def disconnect_tab_signals(self) -> None:
        """Disconnect all tab-specific signals"""
        ...
    
    def emit_tab_event(self, event_type: str, data: Any = None) -> None:
        """Emit tab event through component bus"""
        ...

# Combined protocol for complete tab implementation
class FullTabProtocol(TabLanguageSupport, TabThemeSupport, 
                     TabParentSupport, TabSignalSupport, Protocol):
    """
    Complete protocol defining all expected functionality for a tab.
    
    This protocol can be used for type checking and ensuring
    tab implementations provide all required functionality.
    
    Note: This protocol includes all mixin protocols but not TabInterface
    (which is ABC-based). For implementation, use TabInterface with mixins.
    """
    
    # Include key methods from TabInterface for protocol completeness
    def get_tab_id(self) -> str:
        """Get unique identifier for this tab"""
        ...
    
    def setup_ui(self) -> None:
        """Set up tab UI components"""
        ...
    
    def load_data(self) -> None:
        """Load tab-specific data"""
        ...
    
    def save_data(self) -> bool:
        """Save tab data, return success status"""
        ...
    
    def validate_input(self) -> List[str]:
        """Validate tab input, return list of error messages"""
        ...
    
    def get_tab_state(self) -> TabState:
        """Get complete tab state"""
        ...
    
    def set_tab_state(self, state: TabState) -> None:
        """Set tab state from TabState object"""
        ... 