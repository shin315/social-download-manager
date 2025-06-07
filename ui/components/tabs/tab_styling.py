"""
Tab Styling Module for Social Download Manager v2.0

Provides styling utilities for tab components in the v1.2.1 dark theme
"""

from typing import Dict, Any, Optional
from PyQt6.QtWidgets import QWidget, QHeaderView, QTableWidget
from PyQt6.QtCore import Qt


class TabStyleHelper:
    """Helper class for applying v1.2.1 dark theme styles to tab components"""
    
    @staticmethod
    def get_v121_dark_colors():
        """Get v1.2.1 dark theme colors"""
        return {
            'background': '#2d2d2d',
            'surface': '#3d3d3d', 
            'text': '#ffffff',
            'text_secondary': '#cccccc',
            'primary': '#0078d7',
            'primary_hover': '#0086f0',
            'primary_pressed': '#0067b8',
            'border': '#444444',
            'border_focus': '#555555',
            'hover': '#505050',
            'selected': '#0078d7',
            'input_bg': '#3d3d3d',
            'disabled': '#777777'
        }
    
    @staticmethod
    def apply_table_dark_styling(table: QTableWidget):
        """Apply v1.2.1 dark styling to a table widget"""
        colors = TabStyleHelper.get_v121_dark_colors()
        
        dark_table_style = f"""
        QTableWidget {{
            background-color: {colors['background']};
            color: {colors['text']};
            gridline-color: {colors['border']};
            border: 1px solid {colors['border']};
            selection-background-color: {colors['selected']};
            selection-color: {colors['text']};
        }}
        QTableWidget::item {{
            border-bottom: 1px solid {colors['border']};
            color: {colors['text']};
            padding: 4px;
        }}
        QTableWidget::item:selected {{
            background-color: {colors['selected']};
            color: {colors['text']};
        }}
        QTableWidget::item:hover {{
            background-color: {colors['hover']};
        }}
        QHeaderView::section {{
            background-color: {colors['surface']};
            color: {colors['text']};
            padding: 5px;
            border: 1px solid {colors['border']};
            font-weight: normal;
        }}
        QHeaderView::section:hover {{
            background-color: {colors['hover']};
            border: 1px solid {colors['primary']};
        }}
        QHeaderView::section:pressed {{
            background-color: {colors['primary']};
            color: {colors['text']};
        }}
        """
        
        table.setStyleSheet(dark_table_style)
    
    @staticmethod
    def apply_input_dark_styling(widget: QWidget):
        """Apply v1.2.1 dark styling to input widgets"""
        colors = TabStyleHelper.get_v121_dark_colors()
        
        input_style = f"""
        QLineEdit, QComboBox {{
            background-color: {colors['input_bg']};
            color: {colors['text']};
            border: 1px solid {colors['border_focus']};
            padding: 5px;
            border-radius: 3px;
        }}
        QLineEdit:focus, QComboBox:focus {{
            border: 2px solid {colors['primary']};
        }}
        QLineEdit:hover, QComboBox:hover {{
            background-color: {colors['hover']};
            border: 1px solid {colors['primary']};
        }}
        """
        
        widget.setStyleSheet(input_style)
    
    @staticmethod 
    def apply_button_dark_styling(widget: QWidget):
        """Apply v1.2.1 dark styling to button widgets"""
        colors = TabStyleHelper.get_v121_dark_colors()
        
        button_style = f"""
        QPushButton {{
            background-color: {colors['primary']};
            color: {colors['text']};
            border: none;
            padding: 8px 15px;
            border-radius: 4px;
        }}
        QPushButton:hover {{
            background-color: {colors['primary_hover']};
        }}
        QPushButton:pressed {{
            background-color: {colors['primary_pressed']};
        }}
        QPushButton:disabled {{
            background-color: {colors['border']};
            color: {colors['disabled']};
        }}
        """
        
        widget.setStyleSheet(button_style)


def apply_theme_colors(widget: QWidget, theme_data: Dict[str, Any]):
    """Apply theme colors to a widget based on v1.2.1 styling"""
    if not theme_data or theme_data.get('name') != 'dark':
        return
    
    # Apply based on widget type
    if isinstance(widget, QTableWidget):
        TabStyleHelper.apply_table_dark_styling(widget)
    else:
        # Apply general dark styling
        colors = TabStyleHelper.get_v121_dark_colors()
        general_style = f"""
        QWidget {{
            background-color: {colors['background']};
            color: {colors['text']};
        }}
        """
        widget.setStyleSheet(general_style)


def get_header_hover_style():
    """Get CSS style for table header hover effects"""
    colors = TabStyleHelper.get_v121_dark_colors()
    
    return f"""
    QHeaderView::section:hover {{
        background-color: {colors['hover']};
        border: 1px solid {colors['primary']};
        color: {colors['text']};
    }}
    QHeaderView::section:pressed {{
        background-color: {colors['primary']};
        color: {colors['text']};
    }}
    """ 