"""
FilterManager - Centralized Filter Management

Manages multiple column filters with SQL generation and real-time updates.
Part of Task 13.2: Enhanced Column Filter Components
"""

from typing import Dict, List, Any, Optional, Tuple
from PyQt6.QtCore import QObject, pyqtSignal
from ..common.models import FilterConfig


class FilterManager(QObject):
    """
    Centralized manager for column filters with SQL generation
    
    Features:
    - Multiple column filter support
    - Real-time filter combination
    - SQL WHERE clause generation
    - Filter state persistence
    - Performance optimization for large datasets
    """
    
    # Signals
    filters_changed = pyqtSignal(dict)  # Emitted when any filter changes
    filter_applied = pyqtSignal(str, FilterConfig)  # column, filter_config
    filter_removed = pyqtSignal(str)  # column
    sql_generated = pyqtSignal(str, list)  # where_clause, parameters
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Filter storage: {column_name: FilterConfig}
        self._active_filters: Dict[str, FilterConfig] = {}
        
        # Column metadata for SQL generation
        self._column_mappings: Dict[str, str] = {}  # {display_name: field_name}
        self._column_types: Dict[str, str] = {}     # {field_name: data_type}
        
        # Performance optimization
        self._sql_cache: Dict[str, Tuple[str, List[Any]]] = {}
        self._cache_enabled = True
        
    def set_column_mapping(self, display_name: str, field_name: str, data_type: str = "TEXT"):
        """
        Set mapping between display column name and database field name
        
        Args:
            display_name: Column header text shown to user
            field_name: Database field name
            data_type: SQL data type (TEXT, INTEGER, REAL, DATE)
        """
        self._column_mappings[display_name] = field_name
        self._column_types[field_name] = data_type
        
        # Clear cache when mappings change
        self._clear_sql_cache()
    
    def apply_filter(self, column_display_name: str, filter_config: FilterConfig):
        """
        Apply a filter to a specific column
        
        Args:
            column_display_name: Display name of the column
            filter_config: Filter configuration object
        """
        field_name = self._column_mappings.get(column_display_name)
        if not field_name:
            raise ValueError(f"Unknown column: {column_display_name}")
        
        # Store the filter
        self._active_filters[field_name] = filter_config
        
        # Clear SQL cache
        self._clear_sql_cache()
        
        # Emit signals
        self.filter_applied.emit(field_name, filter_config)
        self.filters_changed.emit(self._active_filters.copy())
        
        # Generate and emit SQL
        where_clause, params = self.generate_sql_where_clause()
        if where_clause:
            self.sql_generated.emit(where_clause, params)
    
    def remove_filter(self, column_display_name: str):
        """Remove filter from a specific column"""
        field_name = self._column_mappings.get(column_display_name)
        if not field_name:
            return
        
        if field_name in self._active_filters:
            del self._active_filters[field_name]
            
            # Clear SQL cache
            self._clear_sql_cache()
            
            # Emit signals
            self.filter_removed.emit(field_name)
            self.filters_changed.emit(self._active_filters.copy())
            
            # Generate and emit SQL
            where_clause, params = self.generate_sql_where_clause()
            self.sql_generated.emit(where_clause, params)
    
    def clear_all_filters(self):
        """Clear all active filters"""
        if not self._active_filters:
            return
        
        self._active_filters.clear()
        self._clear_sql_cache()
        
        self.filters_changed.emit({})
        self.sql_generated.emit("", [])
    
    def get_active_filters(self) -> Dict[str, FilterConfig]:
        """Get copy of all active filters"""
        return self._active_filters.copy()
    
    def has_filters(self) -> bool:
        """Check if any filters are active"""
        return bool(self._active_filters)
    
    def generate_sql_where_clause(self) -> Tuple[str, List[Any]]:
        """
        Generate SQL WHERE clause for all active filters
        
        Returns:
            Tuple of (where_clause, parameters)
        """
        if not self._active_filters:
            return "", []
        
        # Check cache first
        cache_key = self._generate_cache_key()
        if self._cache_enabled and cache_key in self._sql_cache:
            return self._sql_cache[cache_key]
        
        where_conditions = []
        parameters = []
        
        for field_name, filter_config in self._active_filters.items():
            condition, params = self._generate_field_condition(field_name, filter_config)
            if condition:
                where_conditions.append(condition)
                parameters.extend(params)
        
        where_clause = " AND ".join(where_conditions) if where_conditions else ""
        
        # Cache the result
        if self._cache_enabled:
            self._sql_cache[cache_key] = (where_clause, parameters)
        
        return where_clause, parameters
    
    def _generate_field_condition(self, field_name: str, filter_config: FilterConfig) -> Tuple[str, List[Any]]:
        """Generate SQL condition for a single field"""
        field_type = self._column_types.get(field_name, "TEXT")
        filter_type = filter_config.filter_type
        values = filter_config.values
        
        if not values:
            return "", []
        
        # Handle different filter types
        if filter_type == "in":
            return self._generate_in_condition(field_name, values, field_type)
        elif filter_type == "not_in":
            return self._generate_not_in_condition(field_name, values, field_type)
        elif filter_type == "contains":
            return self._generate_contains_condition(field_name, values[0] if values else "")
        elif filter_type == "equals":
            return self._generate_equals_condition(field_name, values[0] if values else "", field_type)
        elif filter_type == "range":
            return self._generate_range_condition(field_name, values, field_type)
        else:
            return "", []
    
    def _generate_in_condition(self, field_name: str, values: List[Any], field_type: str) -> Tuple[str, List[Any]]:
        """Generate IN condition"""
        if not values:
            return "", []
        
        placeholders = ",".join(["?" for _ in values])
        condition = f"{field_name} IN ({placeholders})"
        
        # Convert values based on field type
        converted_values = [self._convert_value(v, field_type) for v in values]
        
        return condition, converted_values
    
    def _generate_not_in_condition(self, field_name: str, values: List[Any], field_type: str) -> Tuple[str, List[Any]]:
        """Generate NOT IN condition"""
        if not values:
            return "", []
        
        placeholders = ",".join(["?" for _ in values])
        condition = f"{field_name} NOT IN ({placeholders})"
        
        converted_values = [self._convert_value(v, field_type) for v in values]
        
        return condition, converted_values
    
    def _generate_contains_condition(self, field_name: str, value: Any) -> Tuple[str, List[Any]]:
        """Generate LIKE condition for text search"""
        if not value:
            return "", []
        
        condition = f"LOWER({field_name}) LIKE LOWER(?)"
        return condition, [f"%{value}%"]
    
    def _generate_equals_condition(self, field_name: str, value: Any, field_type: str) -> Tuple[str, List[Any]]:
        """Generate equals condition"""
        if value is None:
            return f"{field_name} IS NULL", []
        
        condition = f"{field_name} = ?"
        converted_value = self._convert_value(value, field_type)
        
        return condition, [converted_value]
    
    def _generate_range_condition(self, field_name: str, values: List[Any], field_type: str) -> Tuple[str, List[Any]]:
        """Generate range condition (BETWEEN)"""
        if len(values) < 2:
            return "", []
        
        min_val, max_val = values[0], values[1]
        condition = f"{field_name} BETWEEN ? AND ?"
        
        converted_values = [
            self._convert_value(min_val, field_type),
            self._convert_value(max_val, field_type)
        ]
        
        return condition, converted_values
    
    def _convert_value(self, value: Any, field_type: str) -> Any:
        """Convert value to appropriate type for SQL"""
        if value is None:
            return None
        
        try:
            if field_type == "INTEGER":
                return int(value)
            elif field_type == "REAL":
                return float(value)
            elif field_type == "DATE":
                # Handle date conversion if needed
                return str(value)
            else:  # TEXT
                return str(value)
        except (ValueError, TypeError):
            return str(value)  # Fallback to string
    
    def _generate_cache_key(self) -> str:
        """Generate cache key for current filter state"""
        filter_items = []
        for field_name, filter_config in sorted(self._active_filters.items()):
            filter_items.append(f"{field_name}:{filter_config.filter_type}:{','.join(map(str, filter_config.values))}")
        
        return "|".join(filter_items)
    
    def _clear_sql_cache(self):
        """Clear SQL generation cache"""
        self._sql_cache.clear()
    
    def get_filter_summary(self) -> Dict[str, str]:
        """Get human-readable summary of active filters"""
        summary = {}
        
        for field_name, filter_config in self._active_filters.items():
            # Find display name
            display_name = None
            for disp_name, mapped_field in self._column_mappings.items():
                if mapped_field == field_name:
                    display_name = disp_name
                    break
            
            if not display_name:
                display_name = field_name
            
            # Generate summary text
            filter_type = filter_config.filter_type
            values = filter_config.values
            
            if filter_type == "in":
                summary[display_name] = f"In: {', '.join(map(str, values[:3]))}" + ("..." if len(values) > 3 else "")
            elif filter_type == "not_in":
                summary[display_name] = f"Not in: {', '.join(map(str, values[:3]))}" + ("..." if len(values) > 3 else "")
            elif filter_type == "contains":
                summary[display_name] = f"Contains: {values[0] if values else ''}"
            elif filter_type == "equals":
                summary[display_name] = f"Equals: {values[0] if values else ''}"
            elif filter_type == "range":
                summary[display_name] = f"Range: {values[0]} - {values[1]}" if len(values) >= 2 else ""
        
        return summary
    
    def export_filters(self) -> Dict[str, Any]:
        """Export filters for persistence"""
        return {
            'filters': {
                field_name: {
                    'filter_type': config.filter_type,
                    'values': config.values,
                    'operator': getattr(config, 'operator', 'AND')
                }
                for field_name, config in self._active_filters.items()
            },
            'column_mappings': self._column_mappings.copy(),
            'column_types': self._column_types.copy()
        }
    
    def import_filters(self, filter_data: Dict[str, Any]):
        """Import filters from persistence"""
        try:
            # Restore mappings
            if 'column_mappings' in filter_data:
                self._column_mappings = filter_data['column_mappings'].copy()
            if 'column_types' in filter_data:
                self._column_types = filter_data['column_types'].copy()
            
            # Restore filters
            if 'filters' in filter_data:
                self._active_filters.clear()
                for field_name, filter_info in filter_data['filters'].items():
                    filter_config = FilterConfig(
                        filter_type=filter_info.get('filter_type', 'in'),
                        values=filter_info.get('values', []),
                        operator=filter_info.get('operator', 'AND')
                    )
                    self._active_filters[field_name] = filter_config
                
                # Clear cache and emit signals
                self._clear_sql_cache()
                self.filters_changed.emit(self._active_filters.copy())
        
        except Exception as e:
            print(f"Error importing filters: {e}")
            self.clear_all_filters() 