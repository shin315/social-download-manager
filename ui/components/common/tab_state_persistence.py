"""
Enhanced Tab State Persistence System

This module provides a practical state persistence implementation that extends 
the existing TabStateManager to provide seamless tab switching with state preservation.
Designed for subtask 16.1 implementation.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QLineEdit, QComboBox, QTableWidget, QCheckBox

from .tab_state_manager import TabStateManager, FileBasedStatePersistence
from .models import TabState


class EnhancedStatePersistence(FileBasedStatePersistence):
    """Enhanced file-based state persistence with better serialization support"""
    
    def __init__(self, storage_path: str = "data/tab_states"):
        super().__init__(storage_path)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def save_tab_ui_state(self, tab_id: str, ui_state: Dict[str, Any]) -> bool:
        """Save UI-specific state data"""
        try:
            file_path = self._get_ui_state_file_path(tab_id)
            ui_data = {
                'ui_state': ui_state,
                'session_id': self.session_id,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(ui_data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Error saving UI state for {tab_id}: {e}")
            return False
    
    def load_tab_ui_state(self, tab_id: str) -> Optional[Dict[str, Any]]:
        """Load UI-specific state data"""
        try:
            file_path = self._get_ui_state_file_path(tab_id)
            if not os.path.exists(file_path):
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                ui_data = json.load(f)
            
            return ui_data.get('ui_state', {})
        except Exception as e:
            print(f"Error loading UI state for {tab_id}: {e}")
            return None
    
    def _get_ui_state_file_path(self, tab_id: str) -> str:
        """Get file path for UI state"""
        safe_tab_id = "".join(c for c in tab_id if c.isalnum() or c in "_-")
        return os.path.join(self.storage_path, f"{safe_tab_id}_ui_state.json")


class TabStateCapture:
    """Utility class for capturing and restoring UI element states"""
    
    @staticmethod
    def capture_line_edit(widget: QLineEdit) -> Dict[str, Any]:
        """Capture QLineEdit state"""
        return {
            'text': widget.text(),
            'cursor_position': widget.cursorPosition(),
            'selection_start': widget.selectionStart(),
            'selection_length': widget.selectionLength(),
            'placeholder_text': widget.placeholderText()
        }
    
    @staticmethod
    def restore_line_edit(widget: QLineEdit, state: Dict[str, Any]) -> None:
        """Restore QLineEdit state"""
        if 'text' in state:
            widget.setText(state['text'])
        if 'cursor_position' in state:
            widget.setCursorPosition(state['cursor_position'])
        if 'selection_start' in state and 'selection_length' in state:
            start = state['selection_start']
            length = state['selection_length']
            if start >= 0 and length > 0:
                widget.setSelection(start, length)
    
    @staticmethod
    def capture_combo_box(widget: QComboBox) -> Dict[str, Any]:
        """Capture QComboBox state"""
        return {
            'current_index': widget.currentIndex(),
            'current_text': widget.currentText(),
            'items': [widget.itemText(i) for i in range(widget.count())]
        }
    
    @staticmethod
    def restore_combo_box(widget: QComboBox, state: Dict[str, Any]) -> None:
        """Restore QComboBox state"""
        if 'current_index' in state:
            index = state['current_index']
            if 0 <= index < widget.count():
                widget.setCurrentIndex(index)
        elif 'current_text' in state:
            # Try to find and set by text if index is not available
            text = state['current_text']
            index = widget.findText(text)
            if index >= 0:
                widget.setCurrentIndex(index)
    
    @staticmethod
    def capture_table_widget(widget: QTableWidget) -> Dict[str, Any]:
        """Capture QTableWidget state"""
        selected_rows = []
        for item in widget.selectedItems():
            if item.row() not in selected_rows:
                selected_rows.append(item.row())
        
        return {
            'selected_rows': selected_rows,
            'current_row': widget.currentRow(),
            'current_column': widget.currentColumn(),
            'sort_column': widget.horizontalHeader().sortIndicatorSection(),
            'sort_order': widget.horizontalHeader().sortIndicatorOrder().value,
            'column_widths': [widget.columnWidth(i) for i in range(widget.columnCount())]
        }
    
    @staticmethod
    def restore_table_widget(widget: QTableWidget, state: Dict[str, Any]) -> None:
        """Restore QTableWidget state"""
        try:
            # Restore selection
            if 'selected_rows' in state:
                widget.clearSelection()
                for row in state['selected_rows']:
                    if 0 <= row < widget.rowCount():
                        widget.selectRow(row)
            
            # Restore current cell
            if 'current_row' in state and 'current_column' in state:
                row, col = state['current_row'], state['current_column']
                if 0 <= row < widget.rowCount() and 0 <= col < widget.columnCount():
                    widget.setCurrentCell(row, col)
            
            # Restore sorting
            if 'sort_column' in state and 'sort_order' in state:
                sort_col = state['sort_column']
                sort_order = state['sort_order']
                if 0 <= sort_col < widget.columnCount():
                    widget.sortByColumn(sort_col, sort_order)
            
            # Restore column widths
            if 'column_widths' in state:
                widths = state['column_widths']
                for i, width in enumerate(widths):
                    if i < widget.columnCount() and width > 0:
                        widget.setColumnWidth(i, width)
                        
        except Exception as e:
            print(f"Error restoring table widget state: {e}")


class PracticalStateManager(QObject):
    """
    Practical state manager for real-world tab state persistence.
    Focuses on common UI elements and user data.
    """
    
    # Signals
    state_saved = pyqtSignal(str, bool)  # tab_id, success
    state_restored = pyqtSignal(str, bool)  # tab_id, success
    
    def __init__(self, storage_path: str = "data/tab_states"):
        super().__init__()
        self.persistence = EnhancedStatePersistence(storage_path)
        self.capture = TabStateCapture()
        
        # Auto-save timer
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save_all)
        self.auto_save_timer.start(10000)  # Auto-save every 10 seconds
        
        # Registry of tabs and their state capture functions
        self.tab_registry: Dict[str, Dict[str, Any]] = {}
    
    def register_tab(self, tab_id: str, tab_instance, capture_func=None, restore_func=None):
        """Register a tab for state management"""
        self.tab_registry[tab_id] = {
            'instance': tab_instance,
            'capture_func': capture_func or self._default_capture_state,
            'restore_func': restore_func or self._default_restore_state,
            'last_save': None
        }
    
    def save_tab_state(self, tab_id: str) -> bool:
        """Save tab state to persistent storage"""
        if tab_id not in self.tab_registry:
            return False
        
        try:
            tab_info = self.tab_registry[tab_id]
            tab_instance = tab_info['instance']
            capture_func = tab_info['capture_func']
            
            # Capture current state
            ui_state = capture_func(tab_instance)
            
            # Save to file
            success = self.persistence.save_tab_ui_state(tab_id, ui_state)
            
            if success:
                tab_info['last_save'] = datetime.now()
                self.state_saved.emit(tab_id, True)
            else:
                self.state_saved.emit(tab_id, False)
            
            return success
            
        except Exception as e:
            print(f"Error saving state for tab {tab_id}: {e}")
            self.state_saved.emit(tab_id, False)
            return False
    
    def restore_tab_state(self, tab_id: str) -> bool:
        """Restore tab state from persistent storage"""
        if tab_id not in self.tab_registry:
            return False
        
        try:
            tab_info = self.tab_registry[tab_id]
            tab_instance = tab_info['instance']
            restore_func = tab_info['restore_func']
            
            # Load state from file
            ui_state = self.persistence.load_tab_ui_state(tab_id)
            
            if ui_state is None:
                self.state_restored.emit(tab_id, False)
                return False
            
            # Restore state
            success = restore_func(tab_instance, ui_state)
            self.state_restored.emit(tab_id, success)
            
            return success
            
        except Exception as e:
            print(f"Error restoring state for tab {tab_id}: {e}")
            self.state_restored.emit(tab_id, False)
            return False
    
    def auto_save_all(self):
        """Auto-save all registered tabs"""
        for tab_id in self.tab_registry:
            self.save_tab_state(tab_id)
    
    def _default_capture_state(self, tab_instance) -> Dict[str, Any]:
        """Default state capture implementation"""
        state = {}
        
        # Capture common UI elements
        for child in tab_instance.findChildren(QLineEdit):
            if hasattr(child, 'objectName') and child.objectName():
                state[f"line_edit_{child.objectName()}"] = self.capture.capture_line_edit(child)
        
        for child in tab_instance.findChildren(QComboBox):
            if hasattr(child, 'objectName') and child.objectName():
                state[f"combo_box_{child.objectName()}"] = self.capture.capture_combo_box(child)
        
        for child in tab_instance.findChildren(QTableWidget):
            if hasattr(child, 'objectName') and child.objectName():
                state[f"table_{child.objectName()}"] = self.capture.capture_table_widget(child)
        
        return state
    
    def _default_restore_state(self, tab_instance, state: Dict[str, Any]) -> bool:
        """Default state restore implementation"""
        try:
            # Restore line edits
            for key, value in state.items():
                if key.startswith("line_edit_"):
                    widget_name = key[10:]  # Remove "line_edit_" prefix
                    widget = tab_instance.findChild(QLineEdit, widget_name)
                    if widget:
                        self.capture.restore_line_edit(widget, value)
            
            # Restore combo boxes
            for key, value in state.items():
                if key.startswith("combo_box_"):
                    widget_name = key[10:]  # Remove "combo_box_" prefix
                    widget = tab_instance.findChild(QComboBox, widget_name)
                    if widget:
                        self.capture.restore_combo_box(widget, value)
            
            # Restore tables
            for key, value in state.items():
                if key.startswith("table_"):
                    widget_name = key[6:]  # Remove "table_" prefix
                    widget = tab_instance.findChild(QTableWidget, widget_name)
                    if widget:
                        self.capture.restore_table_widget(widget, value)
            
            return True
            
        except Exception as e:
            print(f"Error during state restoration: {e}")
            return False


# Global instance for easy access
practical_state_manager = PracticalStateManager() 