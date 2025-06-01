"""
Component Styles

Generates PyQt stylesheets for specific component types using design tokens.
Each component type has its own method for creating token-based styles.
"""

from typing import Dict, Any, Optional


class ComponentStyler:
    """
    Component-specific stylesheet generator
    
    Uses design tokens to create consistent, maintainable stylesheets
    for different PyQt component types.
    """
    
    def __init__(self, style_manager):
        self.style_manager = style_manager
    
    def _get_token(self, token_name: str, fallback: str = "") -> str:
        """Helper to get token value as string"""
        value = self.style_manager.get_token_value(token_name, fallback)
        return str(value) if value is not None else fallback
    
    def get_main_window_styles(self, **overrides) -> str:
        """Generate main window and widget base styles"""
        return f"""
            QMainWindow, QWidget {{
                background-color: {self._get_token('color-background-primary', '#f0f0f0')};
                color: {self._get_token('color-text-primary', '#333333')};
                font-family: {self._get_token('font-family-sans', 'Inter, sans-serif')};
            }}
        """
    
    def get_button_styles(self, **overrides) -> str:
        """Generate button styles using design tokens"""
        return f"""
            QPushButton {{
                background-color: {self._get_token('color-button-primary-background', '#0078d7')};
                color: {self._get_token('color-button-primary-text', '#ffffff')};
                border: none;
                padding: {self._get_token('spacing-component-padding-sm', '8px')} {self._get_token('spacing-component-padding-md', '15px')};
                border-radius: 4px;
                font-size: {self._get_token('typography-button-default', '12pt')};
                font-weight: {self._get_token('font-weight-medium', '500')};
            }}
            QPushButton:hover {{
                background-color: {self._get_token('color-button-primary-background-hover', '#0086f0')};
            }}
            QPushButton:pressed {{
                background-color: {self._get_token('color-button-primary-background', '#0078d7')};
                transform: translateY(1px);
            }}
            QPushButton:disabled {{
                background-color: {self._get_token('color-button-secondary-background', '#e5e5e5')} !important;
                color: {self._get_token('color-text-tertiary', '#a0a0a0')} !important;
                border: none !important;
            }}
        """
    
    def get_input_styles(self, **overrides) -> str:
        """Generate input field and combobox styles"""
        return f"""
            QLineEdit, QComboBox {{
                background-color: {self._get_token('color-background-primary', '#ffffff')};
                color: {self._get_token('color-text-primary', '#333333')};
                border: 1px solid {self._get_token('color-border-default', '#cccccc')};
                padding: {self._get_token('spacing-component-padding-sm', '5px')};
                border-radius: 3px;
                font-size: {self._get_token('typography-body-default', '12pt')};
                min-height: {self._get_token('size-input-height-md', '40px')};
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 2px solid {self._get_token('color-border-focus', '#0078d7')};
                outline: none;
            }}
            QComboBox:hover {{
                background-color: {self._get_token('color-background-secondary', '#f5f5f5')};
                border: 1px solid {self._get_token('color-border-strong', '#bbbbbb')};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::drop-down:hover {{
                background-color: {self._get_token('color-background-tertiary', '#e5e5e5')};
            }}
            QComboBox::down-arrow {{
                width: 10px;
                height: 10px;
            }}
        """
    
    def get_table_styles(self, **overrides) -> str:
        """Generate table widget styles"""
        return f"""
            QTableWidget {{
                background-color: {self._get_token('color-background-primary', '#ffffff')};
                color: {self._get_token('color-text-primary', '#333333')};
                gridline-color: {self._get_token('color-border-default', '#dddddd')};
                border: 1px solid {self._get_token('color-border-default', '#cccccc')};
                border-radius: 3px;
                font-size: {self._get_token('typography-body-default', '12pt')};
            }}
            QTableWidget::item {{
                border-bottom: 1px solid {self._get_token('color-border-default', '#eeeeee')};
                color: {self._get_token('color-text-primary', '#333333')};
                padding: {self._get_token('spacing-component-padding-sm', '8px')};
            }}
            QTableWidget::item:selected {{
                background-color: {self._get_token('color-button-primary-background', '#0078d7')};
                color: {self._get_token('color-button-primary-text', '#ffffff')};
            }}
            QTableWidget::item:hover {{
                background-color: {self._get_token('color-background-tertiary', '#e8e8e8')};
            }}
            QHeaderView::section {{
                background-color: {self._get_token('color-background-secondary', '#e0e0e0')};
                color: {self._get_token('color-text-primary', '#333333')};
                padding: {self._get_token('spacing-component-padding-sm', '5px')};
                border: 1px solid {self._get_token('color-border-default', '#cccccc')};
                font-weight: {self._get_token('font-weight-semibold', '600')};
            }}
            QHeaderView::section:hover {{
                background-color: {self._get_token('color-background-tertiary', '#d0d0d0')};
            }}
        """
    
    def get_tab_styles(self, **overrides) -> str:
        """Generate tab widget styles"""
        return f"""
            QTabWidget::pane {{
                border: 1px solid {self._get_token('color-border-default', '#cccccc')};
                background-color: {self._get_token('color-background-primary', '#f0f0f0')};
                border-radius: 3px;
            }}
            QTabBar::tab {{
                background-color: {self._get_token('color-background-secondary', '#e0e0e0')};
                color: {self._get_token('color-text-primary', '#333333')};
                padding: {self._get_token('spacing-component-padding-sm', '8px')} {self._get_token('spacing-component-padding-md', '15px')};
                border: 1px solid {self._get_token('color-border-default', '#cccccc')};
                border-bottom: none;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-size: {self._get_token('typography-body-default', '12pt')};
            }}
            QTabBar::tab:selected {{
                background-color: {self._get_token('color-button-primary-background', '#0078d7')};
                color: {self._get_token('color-button-primary-text', '#ffffff')};
                font-weight: {self._get_token('font-weight-medium', '500')};
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {self._get_token('color-background-tertiary', '#d0d0d0')};
            }}
        """
    
    def get_checkbox_styles(self, **overrides) -> str:
        """Generate checkbox styles"""
        return f"""
            QCheckBox {{
                color: {self._get_token('color-text-primary', '#333333')};
                font-size: {self._get_token('typography-body-default', '12pt')};
                spacing: {self._get_token('spacing-component-padding-sm', '5px')};
            }}
            QCheckBox::indicator {{
                width: {self._get_token('size-icon-sm', '16px')};
                height: {self._get_token('size-icon-sm', '16px')};
                background-color: {self._get_token('color-background-secondary', '#e0e0e0')};
                border: 1px solid {self._get_token('color-border-default', '#aaaaaa')};
                border-radius: 2px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {self._get_token('color-button-primary-background', '#0078d7')};
                border: 1px solid {self._get_token('color-button-primary-background', '#0078d7')};
                border-radius: 2px;
            }}
            QCheckBox::indicator:hover {{
                border: 1px solid {self._get_token('color-border-focus', '#0078d7')};
            }}
        """
    
    def get_menu_styles(self, **overrides) -> str:
        """Generate menu and menubar styles"""
        return f"""
            QMenuBar {{
                background-color: {self._get_token('color-background-secondary', '#e0e0e0')};
                color: {self._get_token('color-text-primary', '#333333')};
                border-bottom: 1px solid {self._get_token('color-border-default', '#cccccc')};
                font-size: {self._get_token('typography-body-default', '12pt')};
            }}
            QMenuBar::item {{
                padding: {self._get_token('spacing-component-padding-sm', '4px')} {self._get_token('spacing-component-padding-sm', '8px')};
                background-color: transparent;
            }}
            QMenuBar::item:selected,
            QMenuBar::item:hover {{
                background-color: {self._get_token('color-background-tertiary', '#d0d0d0')};
            }}
            QMenu {{
                background-color: {self._get_token('color-background-primary', '#f5f5f5')};
                color: {self._get_token('color-text-primary', '#333333')};
                border: 1px solid {self._get_token('color-border-default', '#cccccc')};
                padding: {self._get_token('spacing-component-padding-xs', '2px')};
            }}
            QMenu::item {{
                padding: {self._get_token('spacing-component-padding-sm', '4px')} {self._get_token('spacing-component-padding-md', '12px')};
                border: none;
            }}
            QMenu::item:selected {{
                background-color: {self._get_token('color-button-primary-background', '#0078d7')};
                color: {self._get_token('color-button-primary-text', '#ffffff')};
            }}
            QMenu::item:hover:!selected {{
                background-color: {self._get_token('color-background-tertiary', '#e0e0e0')};
            }}
        """
    
    def get_statusbar_styles(self, **overrides) -> str:
        """Generate status bar styles"""
        return f"""
            QStatusBar {{
                background-color: {self._get_token('color-background-secondary', '#e0e0e0')};
                color: {self._get_token('color-text-primary', '#333333')};
                border-top: 1px solid {self._get_token('color-border-default', '#cccccc')};
                font-size: {self._get_token('typography-body-small', '11pt')};
                padding: {self._get_token('spacing-component-padding-xs', '2px')};
            }}
        """
    
    def get_dialog_styles(self, **overrides) -> str:
        """Generate dialog styles"""
        return f"""
            QDialog {{
                background-color: {self._get_token('color-background-primary', '#f5f5f5')};
                color: {self._get_token('color-text-primary', '#333333')};
                border-radius: {self._get_token('spacing-component-padding-sm', '8px')};
                border: 1px solid {self._get_token('color-border-default', '#cccccc')};
            }}
        """
    
    def get_tooltip_styles(self, **overrides) -> str:
        """Generate tooltip styles"""
        return f"""
            QToolTip {{
                background-color: {self._get_token('color-background-inverse', '#333333')};
                color: {self._get_token('color-text-inverse', '#ffffff')};
                border: 1px solid {self._get_token('color-border-default', '#555555')};
                padding: {self._get_token('spacing-component-padding-sm', '5px')};
                border-radius: 3px;
                font-size: {self._get_token('typography-body-small', '11pt')};
            }}
        """
    
    def get_complete_stylesheet(self, components: list = None, **overrides) -> str:
        """
        Generate a complete stylesheet combining multiple components
        
        Args:
            components: List of component types to include. If None, includes all.
            **overrides: Style overrides
            
        Returns:
            Complete stylesheet string
        """
        if components is None:
            components = [
                'main_window', 'button', 'input', 'table', 'tab', 
                'checkbox', 'menu', 'statusbar', 'dialog', 'tooltip'
            ]
        
        stylesheets = []
        for component in components:
            method_name = f"get_{component}_styles"
            if hasattr(self, method_name):
                method = getattr(self, method_name)
                stylesheets.append(method(**overrides))
        
        return "\n".join(stylesheets) 