"""
FilterPopup Widget

Popup widget for filtering table columns.
Provides different filter types and operators for column filtering.
"""

from typing import List, Any, Dict, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QLineEdit, 
    QPushButton, QComboBox, QListWidget, QListWidgetItem, QLabel,
    QFrame, QScrollArea, QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QFont

from ..common.models import FilterConfig
from ..mixins.language_support import LanguageSupport

class FilterPopup(QWidget, LanguageSupport):
    """Popup widget for column filtering"""
    
    # Signals
    filter_applied = pyqtSignal(FilterConfig)
    filter_cleared = pyqtSignal()
    popup_closed = pyqtSignal()
    
    def __init__(self, column_name: str, display_name: str, 
                 unique_values: List[Any], parent=None):
        QWidget.__init__(self, parent)
        LanguageSupport.__init__(self, "FilterPopup")
        
        # Configuration
        self.column_name = column_name
        self.display_name = display_name
        self.unique_values = unique_values
        
        # State
        self._current_filter: Optional[FilterConfig] = None
        self._filter_type = "in"  # "in", "contains", "equals", "range"
        
        # UI components
        self._value_checkboxes: Dict[Any, QCheckBox] = {}
        
        # Setup
        self._setup_window()
        self._setup_ui()
        self._populate_values()
    
    def _setup_window(self):
        """Setup popup window properties"""
        self.setWindowFlags(
            Qt.WindowType.Popup | 
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        
        # Styling
        self.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            QCheckBox {
                padding: 2px;
                margin: 1px;
            }
            QCheckBox:hover {
                background-color: #f0f0f0;
            }
            QPushButton {
                padding: 4px 8px;
                border: 1px solid #ccc;
                border-radius: 2px;
                background-color: #f9f9f9;
            }
            QPushButton:hover {
                background-color: #e9e9e9;
            }
            QPushButton:pressed {
                background-color: #d9d9d9;
            }
        """)
        
        # Size constraints
        self.setMinimumWidth(200)
        self.setMaximumWidth(300)
        self.setMaximumHeight(400)
    
    def _setup_ui(self):
        """Setup the popup UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        # Header
        self._setup_header(layout)
        
        # Filter type selector
        self._setup_filter_type_selector(layout)
        
        # Values area
        self._setup_values_area(layout)
        
        # Action buttons
        self._setup_action_buttons(layout)
    
    def _setup_header(self, parent_layout):
        """Setup header with column name"""
        header_layout = QHBoxLayout()
        
        # Column name label
        self.header_label = QLabel(f"Filter: {self.display_name}")
        font = QFont()
        font.setBold(True)
        self.header_label.setFont(font)
        header_layout.addWidget(self.header_label)
        
        # Close button
        self.close_button = QPushButton("×")
        self.close_button.setFixedSize(20, 20)
        self.close_button.clicked.connect(self.close)
        header_layout.addWidget(self.close_button)
        
        parent_layout.addLayout(header_layout)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        parent_layout.addWidget(separator)
    
    def _setup_filter_type_selector(self, parent_layout):
        """Setup filter type selection"""
        type_layout = QHBoxLayout()
        
        type_layout.addWidget(QLabel(self.tr_("FILTER_TYPE")))
        
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            self.tr_("FILTER_TYPE_IN"),           # "in"
            self.tr_("FILTER_TYPE_CONTAINS"),     # "contains"
            self.tr_("FILTER_TYPE_EQUALS"),       # "equals"
            self.tr_("FILTER_TYPE_NOT_IN"),       # "not_in"
        ])
        self.type_combo.currentTextChanged.connect(self._on_filter_type_changed)
        type_layout.addWidget(self.type_combo)
        
        parent_layout.addLayout(type_layout)
    
    def _setup_values_area(self, parent_layout):
        """Setup values selection area"""
        # Quick actions
        quick_layout = QHBoxLayout()
        
        self.select_all_btn = QPushButton(self.tr_("SELECT_ALL"))
        self.select_all_btn.clicked.connect(self._select_all_values)
        quick_layout.addWidget(self.select_all_btn)
        
        self.select_none_btn = QPushButton(self.tr_("SELECT_NONE"))
        self.select_none_btn.clicked.connect(self._select_no_values)
        quick_layout.addWidget(self.select_none_btn)
        
        parent_layout.addLayout(quick_layout)
        
        # Search input for filtering values
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.tr_("SEARCH_VALUES"))
        self.search_input.textChanged.connect(self._filter_values)
        parent_layout.addWidget(self.search_input)
        
        # Values list
        self.values_scroll = QScrollArea()
        self.values_widget = QWidget()
        self.values_layout = QVBoxLayout(self.values_widget)
        self.values_layout.setContentsMargins(0, 0, 0, 0)
        
        self.values_scroll.setWidget(self.values_widget)
        self.values_scroll.setWidgetResizable(True)
        self.values_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.values_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarNever)
        
        parent_layout.addWidget(self.values_scroll)
    
    def _setup_action_buttons(self, parent_layout):
        """Setup action buttons"""
        button_layout = QHBoxLayout()
        
        self.apply_button = QPushButton(self.tr_("APPLY_FILTER"))
        self.apply_button.clicked.connect(self._apply_filter)
        button_layout.addWidget(self.apply_button)
        
        self.clear_button = QPushButton(self.tr_("CLEAR_FILTER"))
        self.clear_button.clicked.connect(self._clear_filter)
        button_layout.addWidget(self.clear_button)
        
        parent_layout.addLayout(button_layout)
    
    def _populate_values(self):
        """Populate values list"""
        # Clear existing checkboxes
        self._clear_values_layout()
        self._value_checkboxes.clear()
        
        # Create checkboxes for unique values
        for value in self.unique_values:
            checkbox = QCheckBox(str(value))
            checkbox.setChecked(True)  # Default: all selected
            checkbox.userData = value
            
            self._value_checkboxes[value] = checkbox
            self.values_layout.addWidget(checkbox)
        
        # Add stretch at the end
        self.values_layout.addStretch()
    
    def _clear_values_layout(self):
        """Clear all widgets from values layout"""
        while self.values_layout.count():
            child = self.values_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def _on_filter_type_changed(self, text: str):
        """Handle filter type change"""
        # Map display text to internal type
        type_map = {
            self.tr_("FILTER_TYPE_IN"): "in",
            self.tr_("FILTER_TYPE_CONTAINS"): "contains", 
            self.tr_("FILTER_TYPE_EQUALS"): "equals",
            self.tr_("FILTER_TYPE_NOT_IN"): "not_in",
        }
        
        self._filter_type = type_map.get(text, "in")
        
        # Update UI based on filter type
        if self._filter_type == "contains":
            # Hide checkboxes, show text input
            self._show_text_input_mode()
        elif self._filter_type == "equals":
            # Show single selection mode
            self._show_single_selection_mode()
        else:
            # Show multi-selection mode  
            self._show_multi_selection_mode()
    
    def _show_text_input_mode(self):
        """Show text input for contains filter"""
        # Hide values area
        self.values_scroll.hide()
        self.select_all_btn.hide()
        self.select_none_btn.hide()
        
        # Show search input as main input
        self.search_input.setPlaceholderText(self.tr_("ENTER_SEARCH_TEXT"))
        self.search_input.clear()
    
    def _show_single_selection_mode(self):
        """Show single selection for equals filter"""
        self.values_scroll.show()
        self.select_all_btn.hide()
        self.select_none_btn.show()
        
        # Convert checkboxes to radio button behavior
        self._setup_single_selection()
    
    def _show_multi_selection_mode(self):
        """Show multi-selection for in/not_in filters"""
        self.values_scroll.show()
        self.select_all_btn.show()
        self.select_none_btn.show()
        
        self.search_input.setPlaceholderText(self.tr_("SEARCH_VALUES"))
    
    def _setup_single_selection(self):
        """Setup single selection behavior"""
        # Clear all selections first
        for checkbox in self._value_checkboxes.values():
            checkbox.setChecked(False)
            checkbox.clicked.connect(self._on_single_selection_clicked)
    
    def _on_single_selection_clicked(self):
        """Handle single selection click"""
        sender = self.sender()
        if sender.isChecked():
            # Uncheck all others
            for checkbox in self._value_checkboxes.values():
                if checkbox != sender:
                    checkbox.setChecked(False)
    
    def _select_all_values(self):
        """Select all visible values"""
        for checkbox in self._value_checkboxes.values():
            if checkbox.isVisible():
                checkbox.setChecked(True)
    
    def _select_no_values(self):
        """Deselect all values"""
        for checkbox in self._value_checkboxes.values():
            checkbox.setChecked(False)
    
    def _filter_values(self, search_text: str):
        """Filter visible values based on search"""
        search_lower = search_text.lower()
        
        for value, checkbox in self._value_checkboxes.items():
            value_text = str(value).lower()
            matches = search_lower in value_text
            checkbox.setVisible(matches)
    
    def _apply_filter(self):
        """Apply current filter settings"""
        if self._filter_type == "contains":
            # Use search input text
            search_text = self.search_input.text().strip()
            if not search_text:
                return
            
            filter_config = FilterConfig(
                column=self.column_name,
                operator="contains",
                values=[search_text]
            )
        else:
            # Use selected values
            selected_values = []
            for value, checkbox in self._value_checkboxes.items():
                if checkbox.isChecked():
                    selected_values.append(value)
            
            if not selected_values:
                return
            
            filter_config = FilterConfig(
                column=self.column_name,
                operator=self._filter_type,
                values=selected_values
            )
        
        self._current_filter = filter_config
        self.filter_applied.emit(filter_config)
        self.close()
    
    def _clear_filter(self):
        """Clear current filter"""
        self._current_filter = None
        self.filter_cleared.emit()
        self.close()
    
    # =========================================================================
    # Public API
    # =========================================================================
    
    def update_values(self, unique_values: List[Any]):
        """Update available values"""
        self.unique_values = unique_values
        self._populate_values()
    
    def update_display_name(self, display_name: str):
        """Update display name"""
        self.display_name = display_name
        self.header_label.setText(f"Filter: {display_name}")
    
    def set_filter(self, filter_config: FilterConfig):
        """Set current filter configuration"""
        self._current_filter = filter_config
        
        # Update UI to match filter
        if filter_config.operator == "contains":
            self.type_combo.setCurrentText(self.tr_("FILTER_TYPE_CONTAINS"))
            self.search_input.setText(filter_config.values[0] if filter_config.values else "")
        elif filter_config.operator == "equals":
            self.type_combo.setCurrentText(self.tr_("FILTER_TYPE_EQUALS"))
            # Select single value
            self._select_no_values()
            if filter_config.values:
                target_value = filter_config.values[0]
                if target_value in self._value_checkboxes:
                    self._value_checkboxes[target_value].setChecked(True)
        elif filter_config.operator == "not_in":
            self.type_combo.setCurrentText(self.tr_("FILTER_TYPE_NOT_IN"))
            # Select values
            self._select_all_values()
            for value in filter_config.values:
                if value in self._value_checkboxes:
                    self._value_checkboxes[value].setChecked(False)
        else:  # "in"
            self.type_combo.setCurrentText(self.tr_("FILTER_TYPE_IN"))
            # Select only specified values
            self._select_no_values()
            for value in filter_config.values:
                if value in self._value_checkboxes:
                    self._value_checkboxes[value].setChecked(True)
    
    def show_at_position(self, position: QPoint):
        """Show popup at specific position"""
        self.move(position)
        self.show()
        self.raise_()
        self.activateWindow()
    
    def closeEvent(self, event):
        """Handle close event"""
        self.popup_closed.emit()
        super().closeEvent(event)
    
    # =========================================================================
    # Language Support
    # =========================================================================
    
    def update_language(self):
        """Update UI for language changes"""
        super().update_language()
        
        # Update header
        self.header_label.setText(f"Filter: {self.display_name}")
        
        # Update buttons
        self.select_all_btn.setText(self.tr_("SELECT_ALL"))
        self.select_none_btn.setText(self.tr_("SELECT_NONE"))
        self.apply_button.setText(self.tr_("APPLY_FILTER"))
        self.clear_button.setText(self.tr_("CLEAR_FILTER"))
        
        # Update placeholders
        if self._filter_type == "contains":
            self.search_input.setPlaceholderText(self.tr_("ENTER_SEARCH_TEXT"))
        else:
            self.search_input.setPlaceholderText(self.tr_("SEARCH_VALUES"))
        
        # Update combo box items
        current_index = self.type_combo.currentIndex()
        self.type_combo.clear()
        self.type_combo.addItems([
            self.tr_("FILTER_TYPE_IN"),
            self.tr_("FILTER_TYPE_CONTAINS"),
            self.tr_("FILTER_TYPE_EQUALS"),
            self.tr_("FILTER_TYPE_NOT_IN"),
        ])
        self.type_combo.setCurrentIndex(current_index) 