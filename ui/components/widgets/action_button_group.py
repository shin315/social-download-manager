"""
Action Button Group Widget

Reusable button group for common actions like Select All, Delete Selected, etc.
Extracted from downloaded_videos_tab.py and video_info_tab.py button sections.
"""

from typing import List, Dict, Callable, Optional
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QSpacerItem, QSizePolicy
from PyQt6.QtCore import pyqtSignal

from ..common.models import ButtonConfig, ButtonType
from ..common.interfaces import ComponentInterface
from ..common import QWidgetABCMeta
from ..mixins.language_support import LanguageSupport
from ..mixins.theme_support import ThemeSupport

class ActionButtonGroup(QWidget, ComponentInterface, LanguageSupport, ThemeSupport, metaclass=QWidgetABCMeta):
    """Reusable button group for common actions"""
    
    # Signals for button actions
    select_all_clicked = pyqtSignal()
    select_none_clicked = pyqtSignal()
    delete_selected_clicked = pyqtSignal()
    delete_all_clicked = pyqtSignal()
    refresh_clicked = pyqtSignal()
    download_clicked = pyqtSignal()
    
    # Generic button clicked signal with button type
    button_clicked = pyqtSignal(ButtonType)
    
    def __init__(self, buttons_config: List[ButtonConfig], parent=None, 
                 lang_manager=None, add_stretch: bool = True):
        QWidget.__init__(self, parent)
        ComponentInterface.__init__(self)
        LanguageSupport.__init__(self, "ActionButtonGroup", lang_manager)
        ThemeSupport.__init__(self, "ActionButtonGroup")
        
        self.buttons_config = buttons_config
        self.add_stretch = add_stretch
        self.buttons: Dict[ButtonType, QPushButton] = {}
        self._button_states: Dict[ButtonType, bool] = {}
        
        self.setup_ui()
        
    def setup_ui(self):
        """Initialize the button group UI"""
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(10)
        
        # Create buttons based on configuration
        for button_config in self.buttons_config:
            button = self._create_button(button_config)
            self.buttons[button_config.button_type] = button
            self._button_states[button_config.button_type] = button_config.enabled
            
            if button_config.visible:
                self.layout.addWidget(button)
        
        # Add stretch to push buttons to one side if requested
        if self.add_stretch:
            self.layout.addStretch(1)
    
    def _create_button(self, config: ButtonConfig) -> QPushButton:
        """Create a button based on configuration"""
        button = QPushButton()
        button.setText(self.tr_(config.text_key))
        button.setFixedWidth(config.width)
        button.setEnabled(config.enabled)
        
        # Connect to appropriate signal
        self._connect_button_signal(button, config.button_type)
        
        return button
    
    def _connect_button_signal(self, button: QPushButton, button_type: ButtonType):
        """Connect button to appropriate signal based on type"""
        def button_clicked():
            self.button_clicked.emit(button_type)
            
            # Emit specific signals
            if button_type == ButtonType.SELECT_ALL:
                self.select_all_clicked.emit()
            elif button_type == ButtonType.DELETE_SELECTED:
                self.delete_selected_clicked.emit()
            elif button_type == ButtonType.DELETE_ALL:
                self.delete_all_clicked.emit()
            elif button_type == ButtonType.REFRESH:
                self.refresh_clicked.emit()
            elif button_type == ButtonType.DOWNLOAD:
                self.download_clicked.emit()
        
        button.clicked.connect(button_clicked)
    
    def update_language(self):
        """Update button text for language changes"""
        for button_config in self.buttons_config:
            if button_config.button_type in self.buttons:
                button = self.buttons[button_config.button_type]
                button.setText(self.tr_(button_config.text_key))
    
    def apply_theme(self, theme: Dict):
        """Apply theme to buttons"""
        super().apply_theme(theme)
        # Apply theme to all buttons
        for button in self.buttons.values():
            if 'button_style' in theme:
                button.setStyleSheet(theme['button_style'])
    
    def update_button_states(self, state_dict: Dict[ButtonType, bool]):
        """Update button enabled/disabled states"""
        for button_type, enabled in state_dict.items():
            if button_type in self.buttons:
                self.buttons[button_type].setEnabled(enabled)
                self._button_states[button_type] = enabled
    
    def set_button_enabled(self, button_type: ButtonType, enabled: bool):
        """Enable or disable a specific button"""
        if button_type in self.buttons:
            self.buttons[button_type].setEnabled(enabled)
            self._button_states[button_type] = enabled
    
    def is_button_enabled(self, button_type: ButtonType) -> bool:
        """Check if a button is enabled"""
        return self._button_states.get(button_type, False)
    
    def get_button(self, button_type: ButtonType) -> Optional[QPushButton]:
        """Get a specific button widget"""
        return self.buttons.get(button_type)
    
    def set_button_text(self, button_type: ButtonType, text: str):
        """Set custom text for a button"""
        if button_type in self.buttons:
            self.buttons[button_type].setText(text)
    
    def hide_button(self, button_type: ButtonType):
        """Hide a specific button"""
        if button_type in self.buttons:
            self.buttons[button_type].hide()
    
    def show_button(self, button_type: ButtonType):
        """Show a specific button"""
        if button_type in self.buttons:
            self.buttons[button_type].show()
    
    def toggle_select_button_text(self, all_selected: bool):
        """Toggle select all/none button text based on selection state"""
        if ButtonType.SELECT_ALL in self.buttons:
            button = self.buttons[ButtonType.SELECT_ALL]
            if all_selected:
                button.setText(self.tr_("BUTTON_UNSELECT_ALL"))
            else:
                button.setText(self.tr_("BUTTON_SELECT_ALL"))
    
    def add_custom_button(self, text: str, callback: Callable, width: int = 150) -> QPushButton:
        """Add a custom button to the group"""
        button = QPushButton(text)
        button.setFixedWidth(width)
        button.clicked.connect(callback)
        
        # Insert before stretch if it exists
        if self.add_stretch:
            self.layout.insertWidget(self.layout.count() - 1, button)
        else:
            self.layout.addWidget(button)
        
        return button
    
    def get_all_buttons(self) -> List[QPushButton]:
        """Get all buttons in the group"""
        return list(self.buttons.values())
    
    def clear_buttons(self):
        """Remove all buttons from the group"""
        for button in self.buttons.values():
            button.deleteLater()
        self.buttons.clear()
        self._button_states.clear()

# Factory functions for common button group configurations

def create_download_tab_buttons(lang_manager=None) -> ActionButtonGroup:
    """Create button group for downloaded videos tab"""
    buttons_config = [
        ButtonConfig(ButtonType.SELECT_ALL, "BUTTON_SELECT_ALL", 150),
        ButtonConfig(ButtonType.DELETE_SELECTED, "BUTTON_DELETE_SELECTED", 150),
        ButtonConfig(ButtonType.REFRESH, "BUTTON_REFRESH", 150)
    ]
    return ActionButtonGroup(buttons_config, lang_manager=lang_manager)

def create_video_info_tab_buttons(lang_manager=None) -> ActionButtonGroup:
    """Create button group for video info tab"""
    buttons_config = [
        ButtonConfig(ButtonType.SELECT_ALL, "BUTTON_SELECT_ALL", 150),
        ButtonConfig(ButtonType.DELETE_SELECTED, "BUTTON_DELETE_SELECTED", 150),
        ButtonConfig(ButtonType.DELETE_ALL, "BUTTON_DELETE_ALL", 150)
    ]
    return ActionButtonGroup(buttons_config, lang_manager=lang_manager, add_stretch=True)

def create_download_action_buttons(lang_manager=None) -> ActionButtonGroup:
    """Create button group with download action"""
    buttons_config = [
        ButtonConfig(ButtonType.DOWNLOAD, "BUTTON_DOWNLOAD", 150)
    ]
    return ActionButtonGroup(buttons_config, lang_manager=lang_manager, add_stretch=False) 