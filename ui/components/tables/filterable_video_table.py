"""
FilterableVideoTable Component

Video table with advanced filtering capabilities.
Extends VideoTable and implements FilterableTableInterface.
"""

from typing import List, Dict, Any, Optional, Set
from PyQt6.QtWidgets import QHeaderView, QWidget, QHBoxLayout, QLineEdit, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from .video_table import VideoTable
from ..common.component_interfaces import FilterableTableInterface
from ..common.models import TableConfig, FilterConfig
from ..widgets.filter_popup import FilterPopup

class FilterableVideoTable(VideoTable, FilterableTableInterface):
    """Video table with advanced filtering capabilities"""
    
    # Additional signals from FilterableTableInterface
    filter_changed = pyqtSignal(dict)  # Active filters
    filter_applied = pyqtSignal(FilterConfig)  # Applied filter
    filter_cleared = pyqtSignal(int)  # Cleared column filter
    
    # Search-specific signals
    search_applied = pyqtSignal(str, list)  # Query, columns
    search_cleared = pyqtSignal()
    
    def __init__(self, config: TableConfig, parent=None, lang_manager=None):
        super().__init__(config, parent, lang_manager)
        
        # Filter state
        self._active_filters: Dict[int, FilterConfig] = {}
        self._filtered_data: List[Dict[str, Any]] = []
        
        # Search state
        self._search_query: str = ""
        self._search_columns: List[int] = []
        
        # Filter widgets
        self._filter_headers: Dict[int, QWidget] = {}
        self._filter_popups: Dict[int, FilterPopup] = {}
        
        # Search debounce timer
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._execute_search)
        
        # Enable filtering features
        self._setup_filtering()
    
    def _setup_filtering(self):
        """Setup filtering capabilities"""
        if not self.config.filterable:
            return
        
        # Setup filter headers
        self._setup_filter_headers()
        
        # Initialize empty filters
        self._filtered_data = self._original_data.copy()
    
    def _setup_filter_headers(self):
        """Setup filterable column headers"""
        horizontal_header = self.horizontalHeader()
        
        for i, column_config in enumerate(self.config.columns):
            if column_config.filterable:
                # Make header clickable for filters
                horizontal_header.sectionClicked.connect(
                    lambda logical_index=i: self._show_filter_popup(logical_index)
                )
    
    # =========================================================================
    # FilterableTableInterface Implementation
    # =========================================================================
    
    def get_active_filters(self) -> Dict[int, FilterConfig]:
        """Get currently active filters"""
        return self._active_filters.copy()
    
    def apply_filter(self, column: int, filter_config: FilterConfig) -> None:
        """Apply filter to specific column"""
        if column >= len(self.config.columns):
            return
        
        column_config = self.config.columns[column]
        if not column_config.filterable:
            return
        
        # Store filter
        self._active_filters[column] = filter_config
        
        # Apply all filters
        self._apply_all_filters()
        
        # Update header indicator
        self._update_filter_indicator(column, True)
        
        # Emit signals
        self.filter_applied.emit(filter_config)
        self.filter_changed.emit(self._active_filters.copy())
    
    def clear_filter(self, column: int) -> None:
        """Clear filter from specific column"""
        if column in self._active_filters:
            del self._active_filters[column]
            
            # Reapply remaining filters
            self._apply_all_filters()
            
            # Update header indicator
            self._update_filter_indicator(column, False)
            
            # Emit signals
            self.filter_cleared.emit(column)
            self.filter_changed.emit(self._active_filters.copy())
    
    def clear_all_filters(self) -> None:
        """Clear all filters"""
        cleared_columns = list(self._active_filters.keys())
        self._active_filters.clear()
        
        # Reset to original data
        self._filtered_data = self._original_data.copy()
        
        # Apply search if active
        if self._search_query:
            self._apply_search_to_data()
        
        # Update display
        self._update_display_with_filtered_data()
        
        # Update all header indicators
        for column in cleared_columns:
            self._update_filter_indicator(column, False)
        
        # Emit signals
        for column in cleared_columns:
            self.filter_cleared.emit(column)
        self.filter_changed.emit({})
    
    def search(self, query: str, columns: Optional[List[int]] = None) -> None:
        """Search across specified columns"""
        self._search_query = query.strip()
        self._search_columns = columns or list(range(len(self.config.columns)))
        
        # Debounce search
        self._search_timer.start(300)  # 300ms delay
    
    def _execute_search(self):
        """Execute the search with current query"""
        # Apply all filters (including search)
        self._apply_all_filters()
        
        # Emit search signal
        if self._search_query:
            self.search_applied.emit(self._search_query, self._search_columns)
        else:
            self.search_cleared.emit()
    
    def get_filtered_count(self) -> int:
        """Get number of items after filtering"""
        return len(self._filtered_data)
    
    # =========================================================================
    # Filter Processing
    # =========================================================================
    
    def _apply_all_filters(self):
        """Apply all active filters and search to data"""
        # Start with original data
        filtered_data = self._original_data.copy()
        
        # Apply column filters
        for column, filter_config in self._active_filters.items():
            filtered_data = self._apply_single_filter(filtered_data, column, filter_config)
        
        # Apply search
        if self._search_query:
            filtered_data = self._apply_search_filter(filtered_data, self._search_query)
        
        # Store filtered data
        self._filtered_data = filtered_data
        
        # Update display
        self._update_display_with_filtered_data()
    
    def _apply_single_filter(self, data: List[Dict[str, Any]], 
                           column: int, filter_config: FilterConfig) -> List[Dict[str, Any]]:
        """Apply a single filter to data"""
        if column >= len(self.config.columns):
            return data
        
        column_config = self.config.columns[column]
        column_name = column_config.name
        filter_values = filter_config.values
        filter_operator = filter_config.operator
        
        if not filter_values:
            return data
        
        filtered_data = []
        
        for item in data:
            item_value = item.get(column_name, "")
            
            if self._item_matches_filter(item_value, filter_values, filter_operator):
                filtered_data.append(item)
        
        return filtered_data
    
    def _item_matches_filter(self, item_value: Any, filter_values: List[Any], 
                           operator: str) -> bool:
        """Check if item value matches filter criteria"""
        if operator == "in":
            return item_value in filter_values
        elif operator == "equals":
            return item_value == filter_values[0] if filter_values else False
        elif operator == "contains":
            search_text = str(filter_values[0]).lower() if filter_values else ""
            item_text = str(item_value).lower()
            return search_text in item_text
        elif operator == "not_in":
            return item_value not in filter_values
        elif operator == "greater_than":
            try:
                return float(item_value) > float(filter_values[0])
            except (ValueError, TypeError, IndexError):
                return False
        elif operator == "less_than":
            try:
                return float(item_value) < float(filter_values[0])
            except (ValueError, TypeError, IndexError):
                return False
        
        return True
    
    def _apply_search_filter(self, data: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Apply search filter to data"""
        if not query:
            return data
        
        query_lower = query.lower()
        filtered_data = []
        
        for item in data:
            # Search in specified columns
            item_matches = False
            
            for column_index in self._search_columns:
                if column_index >= len(self.config.columns):
                    continue
                
                column_config = self.config.columns[column_index]
                column_name = column_config.name
                item_value = str(item.get(column_name, "")).lower()
                
                if query_lower in item_value:
                    item_matches = True
                    break
            
            if item_matches:
                filtered_data.append(item)
        
        return filtered_data
    
    def _apply_search_to_data(self):
        """Apply current search to filtered data"""
        if self._search_query:
            self._filtered_data = self._apply_search_filter(
                self._filtered_data, self._search_query
            )
    
    def _update_display_with_filtered_data(self):
        """Update table display with filtered data"""
        # Temporarily store filtered data as display data
        original_display_data = self._display_data
        self._display_data = self._filtered_data.copy()
        
        # Apply current sort
        self._apply_sort()
        
        # Update table
        self._update_table_display()
        
        # Restore original display data reference
        # (since _display_data is now the sorted filtered data)
    
    # =========================================================================
    # Filter UI Management
    # =========================================================================
    
    def _show_filter_popup(self, column: int):
        """Show filter popup for column"""
        if column >= len(self.config.columns):
            return
        
        column_config = self.config.columns[column]
        if not column_config.filterable:
            return
        
        # Get unique values for column
        unique_values = self._get_unique_column_values(column)
        
        # Create or get filter popup
        if column not in self._filter_popups:
            self._filter_popups[column] = FilterPopup(
                column_name=column_config.name,
                display_name=self.tr_(column_config.key),
                unique_values=unique_values,
                parent=self
            )
            
            # Connect signals
            popup = self._filter_popups[column]
            popup.filter_applied.connect(
                lambda filter_config, col=column: self.apply_filter(col, filter_config)
            )
            popup.filter_cleared.connect(
                lambda col=column: self.clear_filter(col)
            )
        else:
            # Update values
            self._filter_popups[column].update_values(unique_values)
        
        # Set current filter if any
        if column in self._active_filters:
            self._filter_popups[column].set_filter(self._active_filters[column])
        
        # Show popup
        header = self.horizontalHeader()
        header_rect = header.sectionPosition(column)
        header_width = header.sectionSize(column)
        
        popup_pos = self.mapToGlobal(header.pos())
        popup_pos.setX(popup_pos.x() + header_rect)
        popup_pos.setY(popup_pos.y() + header.height())
        
        self._filter_popups[column].show_at_position(popup_pos)
    
    def _get_unique_column_values(self, column: int) -> List[Any]:
        """Get unique values for a column"""
        if column >= len(self.config.columns):
            return []
        
        column_config = self.config.columns[column]
        column_name = column_config.name
        
        unique_values = set()
        
        # Use original data to get all possible values
        for item in self._original_data:
            value = item.get(column_name)
            if value is not None:
                unique_values.add(value)
        
        # Sort values
        try:
            return sorted(list(unique_values))
        except TypeError:
            # Handle mixed types
            return sorted(list(unique_values), key=str)
    
    def _update_filter_indicator(self, column: int, has_filter: bool):
        """Update visual indicator for filtered column"""
        header = self.horizontalHeader()
        
        if has_filter:
            # Add filter indicator (could be icon or styling)
            current_text = header.model().headerData(column, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
            if not str(current_text).endswith(" 🔍"):
                header.model().setHeaderData(column, Qt.Orientation.Horizontal, f"{current_text} 🔍", Qt.ItemDataRole.DisplayRole)
        else:
            # Remove filter indicator
            current_text = header.model().headerData(column, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
            clean_text = str(current_text).replace(" 🔍", "")
            header.model().setHeaderData(column, Qt.Orientation.Horizontal, clean_text, Qt.ItemDataRole.DisplayRole)
    
    # =========================================================================
    # Overridden Methods
    # =========================================================================
    
    def set_data(self, items: List[Dict[str, Any]]) -> None:
        """Populate table with data (override to handle filtering)"""
        # Store original data
        self._original_data = items.copy()
        
        # Clear existing filters when new data is set
        self._active_filters.clear()
        self._filtered_data = items.copy()
        
        # Apply current sort
        self._display_data = self._filtered_data.copy()
        self._apply_sort()
        
        # Update table display
        self._update_table_display()
        
        # Clear filter indicators
        for column in range(len(self.config.columns)):
            self._update_filter_indicator(column, False)
    
    def get_all_data(self) -> List[Dict[str, Any]]:
        """Get all original data (unfiltered)"""
        return self._original_data.copy()
    
    def get_filtered_data(self) -> List[Dict[str, Any]]:
        """Get currently filtered data"""
        return self._filtered_data.copy()
    
    # =========================================================================
    # Public API Extensions
    # =========================================================================
    
    def set_search_columns(self, columns: List[int]):
        """Set which columns to search in"""
        self._search_columns = [col for col in columns if col < len(self.config.columns)]
    
    def get_search_query(self) -> str:
        """Get current search query"""
        return self._search_query
    
    def clear_search(self):
        """Clear current search"""
        self._search_query = ""
        self._apply_all_filters()
        self.search_cleared.emit()
    
    def has_active_filters(self) -> bool:
        """Check if any filters are active"""
        return bool(self._active_filters or self._search_query)
    
    def get_filter_summary(self) -> Dict[str, Any]:
        """Get summary of active filters"""
        return {
            'column_filters': len(self._active_filters),
            'search_active': bool(self._search_query),
            'search_query': self._search_query,
            'total_items': len(self._original_data),
            'filtered_items': len(self._filtered_data),
            'filter_ratio': len(self._filtered_data) / len(self._original_data) if self._original_data else 1.0
        }
    
    # =========================================================================
    # Language Support
    # =========================================================================
    
    def update_language(self):
        """Update UI for language changes"""
        super().update_language()
        
        # Update filter popups
        for column, popup in self._filter_popups.items():
            if column < len(self.config.columns):
                column_config = self.config.columns[column]
                popup.update_display_name(self.tr_(column_config.key))


# =============================================================================
# Factory Functions
# =============================================================================

def create_filterable_video_info_table_config() -> TableConfig:
    """Create filterable configuration for video info table"""
    config = create_video_info_table_config()
    config.filterable = True
    
    # Make specific columns filterable
    for column in config.columns:
        if column.name in ['status', 'platform', 'quality']:
            column.filterable = True
    
    return config

def create_filterable_downloaded_videos_table_config() -> TableConfig:
    """Create filterable configuration for downloaded videos table"""
    config = create_downloaded_videos_table_config()
    config.filterable = True
    
    # Make all columns filterable except file_path
    for column in config.columns:
        if column.name != 'file_path':
            column.filterable = True
    
    return config 