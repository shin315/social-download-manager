"""
FilterableVideoTable Component

Video table with advanced filtering capabilities.
Extends VideoTable and implements FilterableTableInterface.
Now includes comprehensive state management via mixins.
"""

from typing import List, Dict, Any, Optional, Set
from PyQt6.QtWidgets import QHeaderView, QWidget, QHBoxLayout, QLineEdit, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from .video_table import VideoTable
from ..common.component_interfaces import FilterableTableInterface
from ..common.models import TableConfig, FilterConfig
from ..widgets.filter_popup import FilterPopup
from ..mixins.state_management import FilterableStateMixin, SelectableStateMixin

class FilterableVideoTable(VideoTable, FilterableTableInterface, 
                          FilterableStateMixin, SelectableStateMixin):
    """
    Video table with advanced filtering capabilities and comprehensive state management
    
    Features:
    - Advanced filtering and search
    - State persistence and synchronization
    - Selection state management
    - Filter state tracking and history
    """
    
    # Additional signals from FilterableTableInterface
    filter_changed = pyqtSignal(dict)  # Active filters
    filter_applied = pyqtSignal(FilterConfig)  # Applied filter
    filter_cleared = pyqtSignal(int)  # Cleared column filter
    
    # Search-specific signals
    search_applied = pyqtSignal(str, list)  # Query, columns
    search_cleared = pyqtSignal()
    
    def __init__(self, config: TableConfig, parent=None, lang_manager=None):
        super().__init__(config, parent, lang_manager)
        
        # Initialize state management first
        self._initialize_comprehensive_state()
        
        # Filter state (now managed by FilterableStateMixin)
        self._active_filters: Dict[int, FilterConfig] = {}
        self._filtered_data: List[Dict[str, Any]] = []
        
        # Search state (now managed by FilterableStateMixin)
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
        
        # Connect state management signals
        self._connect_state_management_signals()
    
    def _initialize_comprehensive_state(self):
        """Initialize comprehensive state management for this component"""
        try:
            # Generate unique component ID
            component_id = f"filterable_table_{id(self)}"
            
            # Initialize state management with all mixins
            self.initialize_state_management(
                component_id=component_id,
                component_type="FilterableVideoTable",
                auto_register=True
            )
            
            # Set initial state
            self._synchronize_state_with_internal_data()
            
        except Exception as e:
            print(f"Error initializing comprehensive state: {e}")
    
    def _connect_state_management_signals(self):
        """Connect state management signals to internal operations"""
        # Connect filter state changes
        self.filter_applied.connect(self._on_filter_applied_for_state)
        self.filter_cleared.connect(self._on_filter_cleared_for_state)
        self.search_applied.connect(self._on_search_applied_for_state)
        
        # Connect selection changes from parent VideoTable
        if hasattr(self, 'selection_changed'):
            self.selection_changed.connect(self._on_selection_changed_for_state)
        
        # Connect state restoration signals
        self.state_restored.connect(self._on_state_restored)
    
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

    # =========================================================================
    # Enhanced State Management Integration
    # =========================================================================
    
    def get_component_state(self) -> Dict[str, Any]:
        """Get complete component state including filter and selection state"""
        # Get base state from mixins
        base_state = super().get_component_state()
        
        # Add component-specific state
        component_state = {
            'original_data_count': len(self._original_data),
            'filtered_data_count': len(self._filtered_data),
            'display_data_count': len(self._display_data),
            'filter_popups_count': len(self._filter_popups),
            'current_sort': {
                'column': self._current_sort.column,
                'order': self._current_sort.order.value
            }
        }
        
        # Merge all states
        complete_state = {**base_state, **component_state}
        return complete_state
    
    def set_component_state(self, state: Dict[str, Any]) -> None:
        """Set component state including restoration of filters and selection"""
        # Let mixins handle their state first
        super().set_component_state(state)
        
        # Restore component-specific state
        if 'current_sort' in state:
            sort_info = state['current_sort']
            if 'column' in sort_info and 'order' in sort_info:
                # Restore sorting state
                from ..common.models import SortOrder
                order = SortOrder.ASCENDING if sort_info['order'] == 'ascending' else SortOrder.DESCENDING
                # Don't trigger actual sort, just restore the state
                self._current_sort.column = sort_info['column']
                self._current_sort.order = order
        
        # Synchronize with internal data structures
        self._synchronize_internal_data_with_state()
    
    def _synchronize_state_with_internal_data(self):
        """Synchronize state management with internal data structures"""
        try:
            # Update filter state
            filter_state = {
                'active_filters': self._active_filters,
                'search_query': self._search_query,
                'search_columns': self._search_columns,
                'filter_history': []  # Can be enhanced to track filter history
            }
            
            # Update selection state
            selected_items = []
            if hasattr(self, '_last_selected_items'):
                selected_items = self._last_selected_items
            
            selection_state = {
                'selected_items': selected_items,
                'selection_mode': 'multi',  # Default for table
                'last_selected': selected_items[-1] if selected_items else None,
                'selection_history': []
            }
            
            # Update state via mixins
            self.update_state({**filter_state, **selection_state}, 'internal_sync')
            
        except Exception as e:
            print(f"Error synchronizing state: {e}")
    
    def _synchronize_internal_data_with_state(self):
        """Synchronize internal data structures with state management"""
        try:
            # Restore filters
            active_filters = self.get_active_filters()
            if active_filters != self._active_filters:
                self._active_filters = active_filters
                self._apply_all_filters()
            
            # Restore search
            search_query = self.get_search_query()
            if search_query != self._search_query:
                self._search_query = search_query
                search_columns = self.get_state_field('search_columns') or []
                self._search_columns = search_columns
                if search_query:
                    self._apply_all_filters()
            
            # Restore selection
            selected_items = self.get_selected_items()
            if hasattr(self, '_last_selected_items'):
                if selected_items != self._last_selected_items:
                    # Restore selection in the table
                    self._restore_table_selection(selected_items)
            
        except Exception as e:
            print(f"Error synchronizing internal data with state: {e}")
    
    def _restore_table_selection(self, selected_items: List[Any]):
        """Restore table selection from state"""
        try:
            # Clear current selection
            self.clearSelection()
            
            # Restore selection
            for item in selected_items:
                # Find rows that match the selected items
                for row in range(self.rowCount()):
                    row_data = self._item_data_map.get(row)
                    if row_data and row_data == item:
                        self.selectRow(row)
                        break
            
            # Update internal tracking
            self._last_selected_items = selected_items
            
        except Exception as e:
            print(f"Error restoring table selection: {e}")
    
    # =========================================================================
    # State Management Event Handlers
    # =========================================================================
    
    def _on_filter_applied_for_state(self, filter_config: FilterConfig):
        """Handle filter application for state management"""
        try:
            # Update state with new filter
            current_filters = self.get_active_filters()
            self.set_active_filters(current_filters)
            
            # Create snapshot for undo capability
            self.create_snapshot({'event': 'filter_applied', 'filter': filter_config.__dict__})
            
        except Exception as e:
            print(f"Error handling filter applied for state: {e}")
    
    def _on_filter_cleared_for_state(self, column: int):
        """Handle filter clearing for state management"""
        try:
            # Update state
            current_filters = self.get_active_filters()
            self.set_active_filters(current_filters)
            
            # Create snapshot
            self.create_snapshot({'event': 'filter_cleared', 'column': column})
            
        except Exception as e:
            print(f"Error handling filter cleared for state: {e}")
    
    def _on_search_applied_for_state(self, query: str, columns: List[int]):
        """Handle search application for state management"""
        try:
            # Update state
            self.set_search_query(query, columns)
            
            # Create snapshot
            self.create_snapshot({'event': 'search_applied', 'query': query, 'columns': columns})
            
        except Exception as e:
            print(f"Error handling search applied for state: {e}")
    
    def _on_selection_changed_for_state(self, newly_selected: List[Any], newly_deselected: List[Any]):
        """Handle selection changes for state management"""
        try:
            # Update selection state
            current_selection = self.get_selected_items()
            all_selected = list(set(current_selection + newly_selected))
            final_selection = [item for item in all_selected if item not in newly_deselected]
            
            self.set_selected_items(final_selection)
            
            # Create snapshot for large selection changes
            if len(newly_selected) > 5 or len(newly_deselected) > 5:
                self.create_snapshot({
                    'event': 'selection_changed', 
                    'selected_count': len(final_selection)
                })
            
        except Exception as e:
            print(f"Error handling selection changed for state: {e}")
    
    def _on_state_restored(self, success: bool):
        """Handle state restoration completion"""
        if success:
            try:
                # Refresh display after state restoration
                self._synchronize_internal_data_with_state()
                self._apply_all_filters()
                
                # Update UI indicators
                for column in self._active_filters.keys():
                    self._update_filter_indicator(column, True)
                
                print(f"FilterableVideoTable state restored successfully")
                
            except Exception as e:
                print(f"Error during state restoration: {e}")
    
    # =========================================================================
    # Enhanced State Operations
    # =========================================================================
    
    def save_filter_preset(self, preset_name: str) -> bool:
        """Save current filter configuration as a preset"""
        try:
            preset_data = {
                'active_filters': self.get_active_filters(),
                'search_query': self.get_search_query(),
                'search_columns': self.get_state_field('search_columns'),
                'preset_name': preset_name
            }
            
            return self.create_snapshot({'event': 'filter_preset_saved', 'preset': preset_data})
            
        except Exception as e:
            print(f"Error saving filter preset: {e}")
            return False
    
    def restore_filter_preset(self, snapshot_index: int) -> bool:
        """Restore filter configuration from a preset"""
        try:
            snapshots = self.get_snapshots()
            if 0 <= snapshot_index < len(snapshots):
                snapshot = snapshots[snapshot_index]
                if 'preset' in snapshot.metadata:
                    preset_data = snapshot.metadata['preset']
                    
                    # Clear current filters
                    self.clear_all_filters()
                    
                    # Restore filters
                    for column, filter_config in preset_data.get('active_filters', {}).items():
                        self.apply_filter(int(column), FilterConfig(**filter_config))
                    
                    # Restore search
                    search_query = preset_data.get('search_query', '')
                    search_columns = preset_data.get('search_columns', [])
                    if search_query:
                        self.search(search_query, search_columns)
                    
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error restoring filter preset: {e}")
            return False
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get comprehensive state summary for debugging"""
        try:
            return {
                'component_id': self._component_id,
                'component_type': self._component_type,
                'is_dirty': self.is_state_dirty(),
                'active_filters_count': len(self.get_active_filters()),
                'search_active': bool(self.get_search_query()),
                'selected_items_count': len(self.get_selected_items()),
                'data_counts': {
                    'original': len(self._original_data),
                    'filtered': len(self._filtered_data),
                    'display': len(self._display_data)
                },
                'snapshots_count': len(self.get_snapshots()),
                'history_count': len(self.get_state_history())
            }
            
        except Exception as e:
            print(f"Error getting state summary: {e}")
            return {'error': str(e)}
    
    # =========================================================================
    # Cleanup and Lifecycle
    # =========================================================================
    
    def cleanup_component(self):
        """Enhanced cleanup with state management"""
        try:
            # Create final snapshot before cleanup
            self.create_snapshot({'event': 'component_cleanup'})
            
            # Persist state
            self.persist_state()
            
            # Cleanup state management
            self.cleanup_state_management(persist_state=True)
            
            # Original cleanup
            if hasattr(super(), 'cleanup_component'):
                super().cleanup_component()
            
        except Exception as e:
            print(f"Error during component cleanup: {e}")
    
    def __del__(self):
        """Destructor with state cleanup"""
        try:
            self.cleanup_component()
        except:
            pass  # Ignore errors during destruction


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