"""
Theme Styles

Theme-specific styling utilities and helper methods.
Provides easy access to themed styles and theme switching functionality.
"""

from typing import Dict, Any, Optional
from ..themes import ThemeType


class ThemeStyler:
    """
    Theme-specific styling utilities
    
    Provides helper methods and utilities for working with themed styles
    and managing theme-specific appearance changes.
    """
    
    def __init__(self, style_manager):
        self.style_manager = style_manager
    
    def get_theme_type(self) -> Optional[ThemeType]:
        """Get the current theme type"""
        active_theme = self.style_manager.theme_manager.get_active_theme()
        if active_theme:
            return active_theme.metadata.theme_type
        return None
    
    def is_dark_theme(self) -> bool:
        """Check if current theme is dark"""
        theme_type = self.get_theme_type()
        return theme_type == ThemeType.DARK if theme_type else False
    
    def is_light_theme(self) -> bool:
        """Check if current theme is light"""
        theme_type = self.get_theme_type()
        return theme_type == ThemeType.LIGHT if theme_type else True
    
    def is_high_contrast_theme(self) -> bool:
        """Check if current theme is high contrast"""
        theme_type = self.get_theme_type()
        return theme_type == ThemeType.HIGH_CONTRAST if theme_type else False
    
    def get_icon_suffix_for_theme(self) -> str:
        """Get the appropriate icon suffix for the current theme"""
        if self.is_dark_theme():
            return "-outlined"  # Light icons for dark theme
        elif self.is_high_contrast_theme():
            return "-outlined"  # High contrast icons
        else:
            return "-bw"  # Dark icons for light theme
    
    def get_platform_icon_path(self, platform: str, base_path: str = "assets/platforms/") -> str:
        """
        Get the themed platform icon path
        
        Args:
            platform: Platform name (e.g., 'tiktok', 'youtube')
            base_path: Base path to platform icons
            
        Returns:
            Full path to themed icon
        """
        suffix = self.get_icon_suffix_for_theme()
        return f"{base_path}{platform}{suffix}.png"
    
    def get_themed_color(self, base_token: str, dark_token: str = None, 
                        light_token: str = None, high_contrast_token: str = None) -> str:
        """
        Get a color token based on current theme type
        
        Args:
            base_token: Base token name to use as fallback
            dark_token: Token to use for dark theme
            light_token: Token to use for light theme
            high_contrast_token: Token to use for high contrast theme
            
        Returns:
            Color value for current theme
        """
        theme_type = self.get_theme_type()
        
        if theme_type == ThemeType.DARK and dark_token:
            return self.style_manager.get_token_value(dark_token)
        elif theme_type == ThemeType.LIGHT and light_token:
            return self.style_manager.get_token_value(light_token)
        elif theme_type == ThemeType.HIGH_CONTRAST and high_contrast_token:
            return self.style_manager.get_token_value(high_contrast_token)
        
        return self.style_manager.get_token_value(base_token)
    
    def apply_theme_to_widget(self, widget, component_type: str, **overrides):
        """
        Apply themed styles to a specific widget
        
        Args:
            widget: PyQt widget to style
            component_type: Type of component styling to apply
            **overrides: Style overrides
        """
        stylesheet = self.style_manager.generate_stylesheet(component_type, **overrides)
        widget.setStyleSheet(stylesheet)
    
    def get_theme_specific_stylesheet(self, component_type: str, **overrides) -> str:
        """
        Get a stylesheet with theme-specific adjustments
        
        Args:
            component_type: Component type to style
            **overrides: Style overrides
            
        Returns:
            Themed stylesheet string
        """
        base_stylesheet = self.style_manager.generate_stylesheet(component_type, **overrides)
        
        # Add theme-specific adjustments
        theme_adjustments = self._get_theme_adjustments()
        
        if theme_adjustments:
            return base_stylesheet + "\n" + theme_adjustments
        
        return base_stylesheet
    
    def _get_theme_adjustments(self) -> str:
        """Get theme-specific style adjustments"""
        theme_type = self.get_theme_type()
        
        if theme_type == ThemeType.HIGH_CONTRAST:
            return self._get_high_contrast_adjustments()
        elif theme_type == ThemeType.DARK:
            return self._get_dark_theme_adjustments()
        
        return ""
    
    def _get_high_contrast_adjustments(self) -> str:
        """Get high contrast theme adjustments"""
        return """
            /* High contrast theme adjustments */
            * {
                outline: 2px solid transparent;
            }
            *:focus {
                outline: 2px solid #FFFF00 !important;
                outline-offset: 2px;
            }
            QPushButton:hover {
                transform: scale(1.05);
            }
        """
    
    def _get_dark_theme_adjustments(self) -> str:
        """Get dark theme adjustments"""
        return """
            /* Dark theme adjustments */
            QScrollBar:vertical {
                background-color: #3d3d3d;
                border: 1px solid #555555;
                width: 12px;
            }
            QScrollBar::handle:vertical {
                background-color: #606060;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #707070;
            }
        """
    
    def get_tooltip_style_for_theme(self) -> str:
        """Get application-wide tooltip style for current theme"""
        from .component_styles import ComponentStyler
        styler = ComponentStyler(self.style_manager)
        return styler.get_tooltip_styles()
    
    def create_theme_context_styles(self, context: str) -> Dict[str, str]:
        """
        Create styles for a specific context (e.g., 'settings', 'main', 'dialog')
        
        Args:
            context: Context identifier
            
        Returns:
            Dict mapping component types to their themed styles for the context
        """
        context_components = self._get_components_for_context(context)
        styles = {}
        
        for component in context_components:
            styles[component] = self.get_theme_specific_stylesheet(component)
        
        return styles
    
    def _get_components_for_context(self, context: str) -> list:
        """Get component types needed for a specific context"""
        context_map = {
            'main': ['main_window', 'button', 'input', 'table', 'tab', 'menu', 'statusbar'],
            'dialog': ['dialog', 'button', 'input', 'checkbox'],
            'settings': ['dialog', 'button', 'input', 'checkbox', 'tab'],
            'table': ['table', 'button', 'input', 'checkbox'],
            'form': ['input', 'button', 'checkbox']
        }
        
        return context_map.get(context, ['main_window', 'button', 'input'])
    
    def export_current_theme_css(self, file_path: str = None) -> str:
        """
        Export current theme as CSS file
        
        Args:
            file_path: Optional file path to save CSS
            
        Returns:
            Complete CSS stylesheet for current theme
        """
        from .component_styles import ComponentStyler
        styler = ComponentStyler(self.style_manager)
        
        css_content = f"""
/* Social Download Manager - {self.style_manager.get_current_theme_name().title()} Theme */
/* Generated automatically from design tokens */

{styler.get_complete_stylesheet()}
        """.strip()
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(css_content)
            except Exception as e:
                print(f"Failed to save CSS file: {e}")
        
        return css_content 