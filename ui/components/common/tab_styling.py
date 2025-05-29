"""
Tab Styling Framework

This module provides a comprehensive styling system for tabs that integrates
with the ThemeSupport mixin and ensures consistent appearance across all tab types.

Features:
- Unified theme application system
- Responsive design elements
- Tab-specific styling patterns
- CSS generation utilities
- Animation and transition support
- Accessibility considerations
"""

from typing import Dict, Any, Optional, List, Union
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QColor, QPalette
from dataclasses import dataclass
from enum import Enum

class TabStyleVariant(Enum):
    """Tab style variants for different use cases"""
    DEFAULT = "default"
    DOWNLOAD = "download"         # For download-focused tabs
    DATA_MANAGEMENT = "data"      # For data management tabs  
    SETTINGS = "settings"         # For configuration tabs
    ANALYTICS = "analytics"       # For statistics/analytics tabs


@dataclass
class TabColorScheme:
    """Color scheme for tab styling"""
    primary: str = "#0078d4"           # Primary accent color
    primary_hover: str = "#106ebe"     # Primary hover state
    primary_pressed: str = "#005a9e"   # Primary pressed state
    
    secondary: str = "#6c757d"         # Secondary color
    secondary_hover: str = "#5a6268"   # Secondary hover state
    
    background: str = "#ffffff"        # Main background
    surface: str = "#f8f9fa"           # Surface/card background
    surface_hover: str = "#e9ecef"     # Surface hover state
    
    text_primary: str = "#212529"      # Primary text
    text_secondary: str = "#6c757d"    # Secondary text
    text_muted: str = "#adb5bd"        # Muted text
    text_on_primary: str = "#ffffff"   # Text on primary color
    
    border: str = "#dee2e6"            # Border color
    border_focus: str = "#0078d4"      # Focus border color
    
    success: str = "#28a745"           # Success color
    warning: str = "#ffc107"           # Warning color
    error: str = "#dc3545"             # Error color
    info: str = "#17a2b8"              # Info color
    
    input_background: str = "#ffffff"  # Input field background
    input_border: str = "#ced4da"      # Input field border
    input_focus: str = "#80bdff"       # Input field focus color
    
    table_header: str = "#f8f9fa"      # Table header background
    table_row_alt: str = "#f8f9fa"     # Alternate table row color
    table_selection: str = "#007bff"   # Table selection color
    
    progress_background: str = "#e9ecef"  # Progress bar background
    progress_fill: str = "#007bff"        # Progress bar fill


class TabStyleManager:
    """Manages styling for tab components"""
    
    def __init__(self):
        self.color_schemes = {
            'light': self._create_light_scheme(),
            'dark': self._create_dark_scheme(),
            'high_contrast': self._create_high_contrast_scheme()
        }
        self.current_theme = 'light'
        self.style_variants = {}
        self._setup_variant_styles()
    
    def _create_light_scheme(self) -> TabColorScheme:
        """Create light theme color scheme"""
        return TabColorScheme()
    
    def _create_dark_scheme(self) -> TabColorScheme:
        """Create dark theme color scheme"""
        return TabColorScheme(
            primary="#0d7377",
            primary_hover="#14a085",
            primary_pressed="#0a525a",
            
            background="#1e1e1e",
            surface="#2d2d30",
            surface_hover="#3e3e42",
            
            text_primary="#ffffff",
            text_secondary="#cccccc",
            text_muted="#969696",
            
            border="#404040",
            border_focus="#0d7377",
            
            input_background="#2d2d30",
            input_border="#404040",
            
            table_header="#2d2d30",
            table_row_alt="#323235",
            
            progress_background="#404040"
        )
    
    def _create_high_contrast_scheme(self) -> TabColorScheme:
        """Create high contrast theme color scheme"""
        return TabColorScheme(
            primary="#0000ff",
            primary_hover="#0000cc",
            primary_pressed="#000099",
            
            background="#ffffff",
            surface="#ffffff",
            surface_hover="#f0f0f0",
            
            text_primary="#000000",
            text_secondary="#000000",
            text_muted="#000000",
            
            border="#000000",
            border_focus="#0000ff",
            
            input_background="#ffffff",
            input_border="#000000"
        )
    
    def _setup_variant_styles(self):
        """Setup styling patterns for different tab variants"""
        self.style_variants = {
            TabStyleVariant.DEFAULT: self._get_default_variant_style,
            TabStyleVariant.DOWNLOAD: self._get_download_variant_style,
            TabStyleVariant.DATA_MANAGEMENT: self._get_data_variant_style,
            TabStyleVariant.SETTINGS: self._get_settings_variant_style,
            TabStyleVariant.ANALYTICS: self._get_analytics_variant_style
        }
    
    def get_color_scheme(self, theme_name: str = None) -> TabColorScheme:
        """Get color scheme for specified theme"""
        theme = theme_name or self.current_theme
        return self.color_schemes.get(theme, self.color_schemes['light'])
    
    def set_theme(self, theme_name: str):
        """Set current theme"""
        if theme_name in self.color_schemes:
            self.current_theme = theme_name
    
    def generate_base_tab_style(self, 
                               variant: TabStyleVariant = TabStyleVariant.DEFAULT,
                               theme_name: str = None) -> str:
        """Generate base CSS style for tabs"""
        scheme = self.get_color_scheme(theme_name)
        variant_style = self.style_variants.get(variant, self._get_default_variant_style)
        
        base_style = f"""
        /* Base Tab Styling */
        QWidget {{
            background-color: {scheme.background};
            color: {scheme.text_primary};
            font-family: "Segoe UI", Arial, sans-serif;
            font-size: 9pt;
        }}
        
        /* Label Styling */
        QLabel {{
            color: {scheme.text_primary};
            font-weight: 500;
            padding: 2px 4px;
        }}
        
        QLabel[class="section-header"] {{
            font-size: 10pt;
            font-weight: 600;
            color: {scheme.primary};
            border-bottom: 1px solid {scheme.border};
            padding-bottom: 4px;
            margin-bottom: 8px;
        }}
        
        /* Input Field Styling */
        QLineEdit {{
            background-color: {scheme.input_background};
            color: {scheme.text_primary};
            border: 2px solid {scheme.input_border};
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 9pt;
            selection-background-color: {scheme.primary};
            selection-color: {scheme.text_on_primary};
        }}
        
        QLineEdit:focus {{
            border-color: {scheme.border_focus};
            outline: none;
        }}
        
        QLineEdit:hover {{
            border-color: {scheme.primary_hover};
        }}
        
        QLineEdit:disabled {{
            background-color: {scheme.surface};
            color: {scheme.text_muted};
            border-color: {scheme.border};
        }}
        
        QLineEdit[readOnly="true"] {{
            background-color: {scheme.surface};
            color: {scheme.text_secondary};
        }}
        
        /* Button Styling */
        QPushButton {{
            background-color: {scheme.primary};
            color: {scheme.text_on_primary};
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-size: 9pt;
            font-weight: 500;
            min-height: 14px;
        }}
        
        QPushButton:hover {{
            background-color: {scheme.primary_hover};
        }}
        
        QPushButton:pressed {{
            background-color: {scheme.primary_pressed};
        }}
        
        QPushButton:disabled {{
            background-color: {scheme.text_muted};
            color: {scheme.surface};
        }}
        
        QPushButton[class="secondary"] {{
            background-color: {scheme.secondary};
            color: {scheme.text_on_primary};
        }}
        
        QPushButton[class="secondary"]:hover {{
            background-color: {scheme.secondary_hover};
        }}
        
        QPushButton[class="outline"] {{
            background-color: transparent;
            color: {scheme.primary};
            border: 2px solid {scheme.primary};
        }}
        
        QPushButton[class="outline"]:hover {{
            background-color: {scheme.primary};
            color: {scheme.text_on_primary};
        }}
        
        /* Checkbox Styling */
        QCheckBox {{
            color: {scheme.text_primary};
            spacing: 8px;
        }}
        
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 2px solid {scheme.input_border};
            border-radius: 3px;
            background-color: {scheme.input_background};
        }}
        
        QCheckBox::indicator:hover {{
            border-color: {scheme.primary};
        }}
        
        QCheckBox::indicator:checked {{
            background-color: {scheme.primary};
            border-color: {scheme.primary};
        }}
        
        QCheckBox::indicator:checked:hover {{
            background-color: {scheme.primary_hover};
        }}
        """
        
        # Add variant-specific styles
        variant_styles = variant_style(scheme)
        
        return base_style + variant_styles
    
    def generate_table_style(self, theme_name: str = None) -> str:
        """Generate CSS style for table widgets"""
        scheme = self.get_color_scheme(theme_name)
        
        return f"""
        /* Table Widget Styling */
        QTableWidget {{
            background-color: {scheme.background};
            alternate-background-color: {scheme.table_row_alt};
            color: {scheme.text_primary};
            gridline-color: {scheme.border};
            border: 1px solid {scheme.border};
            border-radius: 8px;
            selection-background-color: {scheme.table_selection};
            selection-color: {scheme.text_on_primary};
        }}
        
        QTableWidget::item {{
            padding: 8px;
            border: none;
        }}
        
        QTableWidget::item:selected {{
            background-color: {scheme.table_selection};
            color: {scheme.text_on_primary};
        }}
        
        QTableWidget::item:hover {{
            background-color: {scheme.surface_hover};
        }}
        
        QHeaderView::section {{
            background-color: {scheme.table_header};
            color: {scheme.text_primary};
            border: 1px solid {scheme.border};
            border-radius: 0;
            padding: 8px 12px;
            font-weight: 600;
            font-size: 9pt;
        }}
        
        QHeaderView::section:hover {{
            background-color: {scheme.surface_hover};
        }}
        
        QHeaderView::section:pressed {{
            background-color: {scheme.primary};
            color: {scheme.text_on_primary};
        }}
        
        /* Scrollbar Styling */
        QScrollBar:vertical {{
            background-color: {scheme.surface};
            width: 12px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {scheme.border};
            border-radius: 6px;
            min-height: 20px;
            margin: 2px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {scheme.text_muted};
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            border: none;
            background: none;
        }}
        
        QScrollBar:horizontal {{
            background-color: {scheme.surface};
            height: 12px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:horizontal {{
            background-color: {scheme.border};
            border-radius: 6px;
            min-width: 20px;
            margin: 2px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background-color: {scheme.text_muted};
        }}
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            border: none;
            background: none;
        }}
        """
    
    def generate_progress_bar_style(self, theme_name: str = None) -> str:
        """Generate CSS style for progress bars"""
        scheme = self.get_color_scheme(theme_name)
        
        return f"""
        /* Progress Bar Styling */
        QProgressBar {{
            background-color: {scheme.progress_background};
            border: 1px solid {scheme.border};
            border-radius: 8px;
            text-align: center;
            font-size: 9pt;
            font-weight: 500;
            color: {scheme.text_primary};
        }}
        
        QProgressBar::chunk {{
            background-color: {scheme.progress_fill};
            border-radius: 6px;
            margin: 1px;
        }}
        
        QProgressBar[status="success"]::chunk {{
            background-color: {scheme.success};
        }}
        
        QProgressBar[status="warning"]::chunk {{
            background-color: {scheme.warning};
        }}
        
        QProgressBar[status="error"]::chunk {{
            background-color: {scheme.error};
        }}
        """
    
    def generate_combo_box_style(self, theme_name: str = None) -> str:
        """Generate CSS style for combo boxes"""
        scheme = self.get_color_scheme(theme_name)
        
        return f"""
        /* ComboBox Styling */
        QComboBox {{
            background-color: {scheme.input_background};
            color: {scheme.text_primary};
            border: 2px solid {scheme.input_border};
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 9pt;
            min-width: 100px;
        }}
        
        QComboBox:hover {{
            border-color: {scheme.primary_hover};
        }}
        
        QComboBox:focus {{
            border-color: {scheme.border_focus};
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        
        QComboBox::down-arrow {{
            width: 0;
            height: 0;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid {scheme.text_secondary};
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {scheme.background};
            color: {scheme.text_primary};
            border: 1px solid {scheme.border};
            border-radius: 6px;
            padding: 4px;
            selection-background-color: {scheme.primary};
            selection-color: {scheme.text_on_primary};
        }}
        """
    
    def _get_default_variant_style(self, scheme: TabColorScheme) -> str:
        """Get default variant-specific styles"""
        return f"""
        /* Default Tab Variant */
        QWidget[variant="default"] {{
            /* Standard spacing and layout */
        }}
        """
    
    def _get_download_variant_style(self, scheme: TabColorScheme) -> str:
        """Get download variant-specific styles"""
        return f"""
        /* Download Tab Variant */
        QWidget[variant="download"] {{
            /* Enhanced progress indicators */
        }}
        
        QPushButton[role="download"] {{
            background-color: {scheme.success};
            font-weight: 600;
        }}
        
        QPushButton[role="download"]:hover {{
            background-color: #218838;
        }}
        
        QLabel[role="status"] {{
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: 500;
        }}
        
        QLabel[status="downloading"] {{
            background-color: {scheme.info};
            color: {scheme.text_on_primary};
        }}
        
        QLabel[status="completed"] {{
            background-color: {scheme.success};
            color: {scheme.text_on_primary};
        }}
        
        QLabel[status="error"] {{
            background-color: {scheme.error};
            color: {scheme.text_on_primary};
        }}
        """
    
    def _get_data_variant_style(self, scheme: TabColorScheme) -> str:
        """Get data management variant-specific styles"""
        return f"""
        /* Data Management Tab Variant */
        QWidget[variant="data"] {{
            /* Enhanced table and data display */
        }}
        
        QPushButton[role="data-action"] {{
            background-color: {scheme.info};
        }}
        
        QPushButton[role="data-action"]:hover {{
            background-color: #138496;
        }}
        
        QPushButton[role="delete"] {{
            background-color: {scheme.error};
        }}
        
        QPushButton[role="delete"]:hover {{
            background-color: #c82333;
        }}
        """
    
    def _get_settings_variant_style(self, scheme: TabColorScheme) -> str:
        """Get settings variant-specific styles"""
        return f"""
        /* Settings Tab Variant */
        QWidget[variant="settings"] {{
            /* Clean, organized layout */
        }}
        
        QLabel[role="setting-group"] {{
            font-size: 10pt;
            font-weight: 600;
            color: {scheme.primary};
            margin-top: 16px;
            margin-bottom: 8px;
        }}
        """
    
    def _get_analytics_variant_style(self, scheme: TabColorScheme) -> str:
        """Get analytics variant-specific styles"""
        return f"""
        /* Analytics Tab Variant */
        QWidget[variant="analytics"] {{
            /* Data visualization focus */
        }}
        
        QLabel[role="metric"] {{
            font-size: 11pt;
            font-weight: 600;
            text-align: center;
            padding: 12px;
            border: 1px solid {scheme.border};
            border-radius: 8px;
            background-color: {scheme.surface};
        }}
        
        QLabel[metric="primary"] {{
            color: {scheme.primary};
        }}
        
        QLabel[metric="success"] {{
            color: {scheme.success};
        }}
        
        QLabel[metric="warning"] {{
            color: {scheme.warning};
        }}
        
        QLabel[metric="error"] {{
            color: {scheme.error};
        }}
        """


class TabStyleHelper:
    """Helper class for applying styles to tab widgets"""
    
    def __init__(self, style_manager: TabStyleManager = None):
        self.style_manager = style_manager or TabStyleManager()
    
    def apply_tab_style(self, 
                       widget: QWidget,
                       variant: TabStyleVariant = TabStyleVariant.DEFAULT,
                       theme_name: str = None):
        """Apply complete tab styling to a widget"""
        # Generate combined stylesheet
        styles = [
            self.style_manager.generate_base_tab_style(variant, theme_name),
            self.style_manager.generate_table_style(theme_name),
            self.style_manager.generate_progress_bar_style(theme_name),
            self.style_manager.generate_combo_box_style(theme_name)
        ]
        
        combined_style = "\n".join(styles)
        widget.setStyleSheet(combined_style)
        
        # Set variant property for CSS selectors
        widget.setProperty("variant", variant.value)
    
    def apply_theme_colors_to_widget(self, 
                                   widget: QWidget,
                                   widget_type: str,
                                   theme_data: Dict[str, Any],
                                   variant: TabStyleVariant = TabStyleVariant.DEFAULT):
        """Apply theme colors to specific widget types"""
        scheme = self._convert_theme_data_to_scheme(theme_data)
        
        if widget_type == "table":
            widget.setStyleSheet(self.style_manager.generate_table_style())
        elif widget_type == "progress":
            widget.setStyleSheet(self.style_manager.generate_progress_bar_style())
        elif widget_type == "combo":
            widget.setStyleSheet(self.style_manager.generate_combo_box_style())
        else:
            # Apply base styling
            widget.setStyleSheet(self.style_manager.generate_base_tab_style(variant))
    
    def _convert_theme_data_to_scheme(self, theme_data: Dict[str, Any]) -> TabColorScheme:
        """Convert theme dictionary to TabColorScheme"""
        # This would map the existing theme data structure to our color scheme
        # For now, create a basic mapping
        return TabColorScheme(
            primary=theme_data.get('accent', '#0078d4'),
            background=theme_data.get('background', '#ffffff'),
            text_primary=theme_data.get('text', '#000000'),
            border=theme_data.get('border', '#cccccc'),
            # ... add more mappings as needed
        )
    
    def update_widget_property(self, widget: QWidget, property_name: str, value: Any):
        """Update widget property and refresh styling"""
        widget.setProperty(property_name, value)
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()


# Global style manager instance
_style_manager = TabStyleManager()

def get_tab_style_manager() -> TabStyleManager:
    """Get the global tab style manager instance"""
    return _style_manager

def apply_tab_theme(widget: QWidget, 
                   variant: TabStyleVariant = TabStyleVariant.DEFAULT,
                   theme_name: str = None):
    """Convenience function to apply tab theme to a widget"""
    helper = TabStyleHelper(_style_manager)
    helper.apply_tab_style(widget, variant, theme_name)

def set_global_tab_theme(theme_name: str):
    """Set the global tab theme"""
    _style_manager.set_theme(theme_name) 