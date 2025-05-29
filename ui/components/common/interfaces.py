"""
Component Interfaces

Abstract base classes and protocols defining component interfaces
for standardized communication and state management.
"""

from abc import ABC, abstractmethod
from typing import List, Any, Dict, Optional, Protocol
from PyQt6.QtCore import QObject, pyqtSignal
from .models import TableConfig, FilterConfig, SortConfig, StatisticsData

class ComponentInterface(ABC):
    """Base interface for all UI components"""
    
    @abstractmethod
    def setup_ui(self) -> None:
        """Initialize the component's UI"""
        pass
    
    @abstractmethod
    def update_language(self) -> None:
        """Update component text for language changes"""
        pass
    
    @abstractmethod
    def apply_theme(self, theme: dict) -> None:
        """Apply theme colors and styles"""
        pass

class StateManagerInterface(ABC):
    """Interface for components that manage state"""
    
    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        """Get current component state"""
        pass
    
    @abstractmethod
    def set_state(self, state: Dict[str, Any]) -> None:
        """Set component state"""
        pass
    
    @abstractmethod
    def clear_state(self) -> None:
        """Clear all component state"""
        pass

class TableInterface(ComponentInterface):
    """Interface for table components"""
    
    @abstractmethod
    def set_data(self, data: List[Any]) -> None:
        """Set table data"""
        pass
    
    @abstractmethod
    def get_selected_items(self) -> List[Any]:
        """Get currently selected items"""
        pass
    
    @abstractmethod
    def clear_selection(self) -> None:
        """Clear table selection"""
        pass
    
    @abstractmethod
    def refresh_display(self) -> None:
        """Refresh table display"""
        pass

class FilterInterface(ABC):
    """Interface for filterable components"""
    
    @abstractmethod
    def apply_text_filter(self, text: str) -> None:
        """Apply text-based filter"""
        pass
    
    @abstractmethod
    def apply_column_filter(self, column: int, values: List[Any]) -> None:
        """Apply column-specific filter"""
        pass
    
    @abstractmethod
    def clear_filters(self) -> None:
        """Clear all active filters"""
        pass
    
    @abstractmethod
    def get_filtered_data(self) -> List[Any]:
        """Get currently filtered data"""
        pass

class SortInterface(ABC):
    """Interface for sortable components"""
    
    @abstractmethod
    def sort_by_column(self, column: int, ascending: bool = True) -> None:
        """Sort data by specified column"""
        pass
    
    @abstractmethod
    def get_sort_config(self) -> SortConfig:
        """Get current sort configuration"""
        pass

class SelectionInterface(ABC):
    """Interface for components with selection capability"""
    
    @abstractmethod
    def select_all(self) -> None:
        """Select all items"""
        pass
    
    @abstractmethod
    def select_none(self) -> None:
        """Clear all selections"""
        pass
    
    @abstractmethod
    def toggle_selection(self, index: int) -> None:
        """Toggle selection for specific item"""
        pass
    
    @abstractmethod
    def get_selection_count(self) -> int:
        """Get number of selected items"""
        pass

class StatisticsInterface(ABC):
    """Interface for components that display statistics"""
    
    @abstractmethod
    def update_statistics(self, data: List[Any]) -> None:
        """Update statistics based on data"""
        pass
    
    @abstractmethod
    def get_statistics(self) -> StatisticsData:
        """Get current statistics"""
        pass

class ProgressInterface(ABC):
    """Interface for progress tracking components"""
    
    @abstractmethod
    def update_progress(self, progress: int, message: str = "") -> None:
        """Update progress value and message"""
        pass
    
    @abstractmethod
    def set_indeterminate(self, indeterminate: bool) -> None:
        """Set progress bar to indeterminate state"""
        pass
    
    @abstractmethod
    def reset_progress(self) -> None:
        """Reset progress to initial state"""
        pass

class ThumbnailInterface(ABC):
    """Interface for thumbnail display components"""
    
    @abstractmethod
    def load_thumbnail(self, url: str) -> None:
        """Load thumbnail from URL"""
        pass
    
    @abstractmethod
    def set_thumbnail(self, image_data: bytes) -> None:
        """Set thumbnail from image data"""
        pass
    
    @abstractmethod
    def clear_thumbnail(self) -> None:
        """Clear current thumbnail"""
        pass

# Protocol for language support
class LanguageSupport(Protocol):
    """Protocol for components with language support"""
    
    def tr_(self, key: str) -> str:
        """Translate text using language manager"""
        ...
    
    def update_language(self) -> None:
        """Update component language"""
        ...

# Protocol for theme support  
class ThemeSupport(Protocol):
    """Protocol for components with theme support"""
    
    def apply_theme(self, theme: dict) -> None:
        """Apply theme to component"""
        ...

# Protocol for tooltip support
class TooltipSupport(Protocol):
    """Protocol for components with tooltip support"""
    
    def format_tooltip_text(self, text: str) -> str:
        """Format tooltip text"""
        ...
    
    def show_tooltip(self, text: str, position: Optional[tuple] = None) -> None:
        """Show tooltip at position"""
        ... 