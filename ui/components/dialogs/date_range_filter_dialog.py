"""
Date Range Filter Dialog

Advanced date range picker with validation and preset options.
Part of Task 13.3: Implement Date Range and Quality Filters
"""

from typing import Tuple, Optional
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QCalendarWidget, QGroupBox, QButtonGroup, QRadioButton,
    QDateEdit, QFormLayout, QDialogButtonBox, QMessageBox,
    QSpacerItem, QSizePolicy, QWidget, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from PyQt6.QtGui import QFont, QPalette

from ..mixins.language_support import LanguageSupport


class DateRangeFilterDialog(QDialog, LanguageSupport):
    """
    Advanced date range filter dialog with calendar widgets and presets
    
    Features:
    - Dual calendar widgets for start/end date selection
    - Preset date ranges (Today, Last Week, Last Month, etc.)
    - Date range validation
    - Relative date options 
    - Clear styling and responsive layout
    """
    
    # Signals
    date_range_applied = pyqtSignal(QDate, QDate)  # start_date, end_date
    filter_cleared = pyqtSignal()
    
    def __init__(self, parent=None, initial_start=None, initial_end=None):
        QDialog.__init__(self, parent)
        LanguageSupport.__init__(self, component_name="DateRangeFilter")
        
        # Store initial values
        self.initial_start = initial_start or QDate.currentDate().addDays(-30)
        self.initial_end = initial_end or QDate.currentDate()
        
        # Current selection
        self.selected_start = self.initial_start
        self.selected_end = self.initial_end
        
        # Setup dialog
        self._setup_dialog()
        self._setup_ui()
        self._connect_signals()
        self._apply_initial_values()
    
    def _setup_dialog(self):
        """Configure dialog window properties"""
        self.setWindowTitle(self.tr_("DATE_RANGE_FILTER"))
        self.setModal(True)
        self.setFixedSize(800, 600)
        
        # Center on parent
        if self.parent():
            parent_geometry = self.parent().geometry()
            dialog_geometry = self.geometry()
            x = parent_geometry.x() + (parent_geometry.width() - dialog_geometry.width()) // 2
            y = parent_geometry.y() + (parent_geometry.height() - dialog_geometry.height()) // 2
            self.move(x, y)
        
        # Styling
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
                border: 1px solid #cccccc;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
            }
            QCalendarWidget {
                border: 1px solid #dddddd;
                border-radius: 4px;
                background-color: white;
            }
            QRadioButton {
                padding: 2px;
                margin: 1px;
            }
            QRadioButton:hover {
                background-color: #e6f3ff;
                border-radius: 3px;
            }
        """)
    
    def _setup_ui(self):
        """Setup the dialog UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Header
        self._setup_header(main_layout)
        
        # Content area
        content_layout = QHBoxLayout()
        
        # Left side - Presets
        self._setup_presets_section(content_layout)
        
        # Right side - Calendar selection
        self._setup_calendar_section(content_layout)
        
        main_layout.addLayout(content_layout)
        
        # Custom date inputs
        self._setup_custom_inputs(main_layout)
        
        # Action buttons
        self._setup_action_buttons(main_layout)
    
    def _setup_header(self, parent_layout):
        """Setup dialog header"""
        header_layout = QHBoxLayout()
        
        # Title
        title_label = QLabel(self.tr_("SELECT_DATE_RANGE"))
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        # Spacer
        header_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        # Current selection display
        self.selection_label = QLabel()
        self.selection_label.setStyleSheet("color: #666666; font-style: italic;")
        header_layout.addWidget(self.selection_label)
        
        parent_layout.addLayout(header_layout)
    
    def _setup_presets_section(self, parent_layout):
        """Setup preset date ranges section"""
        presets_group = QGroupBox(self.tr_("QUICK_SELECT"))
        presets_group.setFixedWidth(200)
        presets_layout = QVBoxLayout(presets_group)
        
        # Create button group for presets
        self.presets_group = QButtonGroup(self)
        
        # Define preset options
        presets = [
            ("TODAY", 0, 0),
            ("YESTERDAY", -1, -1),
            ("LAST_7_DAYS", -7, 0),
            ("LAST_30_DAYS", -30, 0),
            ("LAST_90_DAYS", -90, 0),
            ("THIS_MONTH", "this_month", "this_month"),
            ("LAST_MONTH", "last_month", "last_month"),
            ("THIS_YEAR", "this_year", "this_year"),
            ("ALL_TIME", "all_time", "all_time")
        ]
        
        for i, (text_key, start_offset, end_offset) in enumerate(presets):
            radio = QRadioButton(self.tr_(text_key))
            radio.setProperty("start_offset", start_offset)
            radio.setProperty("end_offset", end_offset)
            self.presets_group.addButton(radio, i)
            presets_layout.addWidget(radio)
        
        # Custom option
        presets_layout.addWidget(QLabel(""))  # Spacer
        self.custom_radio = QRadioButton(self.tr_("CUSTOM_RANGE"))
        self.presets_group.addButton(self.custom_radio, len(presets))
        presets_layout.addWidget(self.custom_radio)
        
        # Stretch to fill
        presets_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        parent_layout.addWidget(presets_group)
    
    def _setup_calendar_section(self, parent_layout):
        """Setup calendar widgets section"""
        calendar_group = QGroupBox(self.tr_("CALENDAR_SELECTION"))
        calendar_layout = QVBoxLayout(calendar_group)
        
        # Date range labels
        range_layout = QHBoxLayout()
        
        # Start date
        start_layout = QVBoxLayout()
        start_layout.addWidget(QLabel(self.tr_("START_DATE")))
        self.start_calendar = QCalendarWidget()
        self.start_calendar.setGridVisible(True)
        self.start_calendar.setMaximumDate(QDate.currentDate())
        start_layout.addWidget(self.start_calendar)
        range_layout.addLayout(start_layout)
        
        # End date
        end_layout = QVBoxLayout()
        end_layout.addWidget(QLabel(self.tr_("END_DATE")))
        self.end_calendar = QCalendarWidget()
        self.end_calendar.setGridVisible(True)
        self.end_calendar.setMaximumDate(QDate.currentDate())
        end_layout.addWidget(self.end_calendar)
        range_layout.addLayout(end_layout)
        
        calendar_layout.addLayout(range_layout)
        parent_layout.addWidget(calendar_group)
    
    def _setup_custom_inputs(self, parent_layout):
        """Setup custom date input fields"""
        custom_group = QGroupBox(self.tr_("CUSTOM_DATE_INPUT"))
        custom_layout = QFormLayout(custom_group)
        
        # Date edit widgets
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setMaximumDate(QDate.currentDate())
        self.start_date_edit.setDisplayFormat("yyyy-MM-dd")
        
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setMaximumDate(QDate.currentDate())
        self.end_date_edit.setDisplayFormat("yyyy-MM-dd")
        
        custom_layout.addRow(self.tr_("FROM_DATE"), self.start_date_edit)
        custom_layout.addRow(self.tr_("TO_DATE"), self.end_date_edit)
        
        # Options
        options_layout = QHBoxLayout()
        
        self.include_today_cb = QCheckBox(self.tr_("INCLUDE_TODAY"))
        self.include_today_cb.setChecked(True)
        options_layout.addWidget(self.include_today_cb)
        
        options_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        custom_layout.addRow("", options_layout)
        
        parent_layout.addWidget(custom_group)
    
    def _setup_action_buttons(self, parent_layout):
        """Setup dialog action buttons"""
        button_layout = QHBoxLayout()
        
        # Clear filter button
        self.clear_btn = QPushButton(self.tr_("CLEAR_FILTER"))
        self.clear_btn.setStyleSheet("QPushButton { background-color: #ffeeee; }")
        button_layout.addWidget(self.clear_btn)
        
        # Spacer
        button_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        # Standard buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_layout.addWidget(self.button_box)
        
        parent_layout.addLayout(button_layout)
    
    def _connect_signals(self):
        """Connect dialog signals"""
        # Calendar changes
        self.start_calendar.selectionChanged.connect(self._on_start_date_changed)
        self.end_calendar.selectionChanged.connect(self._on_end_date_changed)
        
        # Date edit changes
        self.start_date_edit.dateChanged.connect(self._on_start_edit_changed)
        self.end_date_edit.dateChanged.connect(self._on_end_edit_changed)
        
        # Preset changes
        self.presets_group.buttonClicked.connect(self._on_preset_selected)
        
        # Action buttons
        self.button_box.accepted.connect(self._apply_filter)
        self.button_box.rejected.connect(self.reject)
        self.clear_btn.clicked.connect(self._clear_filter)
        
        # Include today checkbox
        self.include_today_cb.toggled.connect(self._on_include_today_changed)
    
    def _apply_initial_values(self):
        """Apply initial date values"""
        self.start_calendar.setSelectedDate(self.initial_start)
        self.end_calendar.setSelectedDate(self.initial_end)
        self.start_date_edit.setDate(self.initial_start)
        self.end_date_edit.setDate(self.initial_end)
        self._update_selection_display()
    
    def _on_start_date_changed(self):
        """Handle start date change from calendar"""
        selected_date = self.start_calendar.selectedDate()
        self.selected_start = selected_date
        self.start_date_edit.setDate(selected_date)
        
        # Update end calendar minimum
        self.end_calendar.setMinimumDate(selected_date)
        
        # Ensure end date is not before start date
        if self.selected_end < selected_date:
            self.selected_end = selected_date
            self.end_calendar.setSelectedDate(selected_date)
            self.end_date_edit.setDate(selected_date)
        
        self._update_selection_display()
        self._select_custom_preset()
    
    def _on_end_date_changed(self):
        """Handle end date change from calendar"""
        selected_date = self.end_calendar.selectedDate()
        self.selected_end = selected_date
        self.end_date_edit.setDate(selected_date)
        
        # Update start calendar maximum
        self.start_calendar.setMaximumDate(selected_date)
        
        self._update_selection_display()
        self._select_custom_preset()
    
    def _on_start_edit_changed(self, date):
        """Handle start date change from edit widget"""
        self.selected_start = date
        self.start_calendar.setSelectedDate(date)
        self.end_calendar.setMinimumDate(date)
        
        if self.selected_end < date:
            self.selected_end = date
            self.end_calendar.setSelectedDate(date)
            self.end_date_edit.setDate(date)
        
        self._update_selection_display()
        self._select_custom_preset()
    
    def _on_end_edit_changed(self, date):
        """Handle end date change from edit widget"""
        self.selected_end = date
        self.end_calendar.setSelectedDate(date)
        self.start_calendar.setMaximumDate(date)
        
        self._update_selection_display()
        self._select_custom_preset()
    
    def _on_preset_selected(self, button):
        """Handle preset selection"""
        start_offset = button.property("start_offset")
        end_offset = button.property("end_offset")
        
        if button == self.custom_radio:
            return  # Custom selection, no action needed
        
        # Calculate dates based on preset
        today = QDate.currentDate()
        
        if isinstance(start_offset, int) and isinstance(end_offset, int):
            # Simple day offset
            start_date = today.addDays(start_offset)
            end_date = today.addDays(end_offset)
        else:
            # Special presets
            if start_offset == "this_month":
                start_date = QDate(today.year(), today.month(), 1)
                end_date = today
            elif start_offset == "last_month":
                last_month = today.addMonths(-1)
                start_date = QDate(last_month.year(), last_month.month(), 1)
                end_date = QDate(today.year(), today.month(), 1).addDays(-1)
            elif start_offset == "this_year":
                start_date = QDate(today.year(), 1, 1)
                end_date = today
            elif start_offset == "all_time":
                start_date = QDate(2020, 1, 1)  # Reasonable start date
                end_date = today
            else:
                return
        
        # Apply the dates
        self.selected_start = start_date
        self.selected_end = end_date
        
        self.start_calendar.setSelectedDate(start_date)
        self.end_calendar.setSelectedDate(end_date)
        self.start_date_edit.setDate(start_date)
        self.end_date_edit.setDate(end_date)
        
        self._update_selection_display()
    
    def _on_include_today_changed(self, checked):
        """Handle include today checkbox change"""
        if checked and self.selected_end < QDate.currentDate():
            self.selected_end = QDate.currentDate()
            self.end_calendar.setSelectedDate(self.selected_end)
            self.end_date_edit.setDate(self.selected_end)
            self._update_selection_display()
    
    def _select_custom_preset(self):
        """Select custom preset option"""
        self.custom_radio.setChecked(True)
    
    def _update_selection_display(self):
        """Update the selection display label"""
        start_str = self.selected_start.toString("yyyy-MM-dd")
        end_str = self.selected_end.toString("yyyy-MM-dd")
        
        if self.selected_start == self.selected_end:
            display_text = f"Selected: {start_str}"
        else:
            days_diff = self.selected_start.daysTo(self.selected_end) + 1
            display_text = f"Selected: {start_str} to {end_str} ({days_diff} days)"
        
        self.selection_label.setText(display_text)
    
    def _validate_date_range(self):
        """Validate the selected date range"""
        if self.selected_start > self.selected_end:
            QMessageBox.warning(
                self,
                self.tr_("INVALID_DATE_RANGE"),
                self.tr_("START_DATE_AFTER_END_DATE")
            )
            return False
        
        if self.selected_end > QDate.currentDate():
            QMessageBox.warning(
                self,
                self.tr_("INVALID_DATE_RANGE"), 
                self.tr_("END_DATE_IN_FUTURE")
            )
            return False
        
        # Check for reasonable range (not more than 2 years)
        max_days = 365 * 2
        if self.selected_start.daysTo(self.selected_end) > max_days:
            result = QMessageBox.question(
                self,
                self.tr_("LARGE_DATE_RANGE"),
                self.tr_("DATE_RANGE_VERY_LARGE"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if result != QMessageBox.StandardButton.Yes:
                return False
        
        return True
    
    def _apply_filter(self):
        """Apply the date range filter"""
        if not self._validate_date_range():
            return
        
        self.date_range_applied.emit(self.selected_start, self.selected_end)
        self.accept()
    
    def _clear_filter(self):
        """Clear the date range filter"""
        self.filter_cleared.emit()
        self.reject()
    
    def get_selected_range(self) -> Tuple[QDate, QDate]:
        """Get the currently selected date range"""
        return (self.selected_start, self.selected_end)
    
    def set_date_range(self, start_date: QDate, end_date: QDate):
        """Set the date range programmatically"""
        self.selected_start = start_date
        self.selected_end = end_date
        self.start_calendar.setSelectedDate(start_date)
        self.end_calendar.setSelectedDate(end_date)
        self.start_date_edit.setDate(start_date)
        self.end_date_edit.setDate(end_date)
        self._update_selection_display()
        self._select_custom_preset() 