"""
Component Theming System

Advanced theming system specifically designed for UI components,
extending the existing TabStyleManager with component-specific theming,
responsive design, state-based styling, and dynamic theme management.

This system provides:
- Component-specific theme customization
- Responsive design patterns
- State-based styling (hover, active, disabled, etc.)
- Dynamic theme switching with animations
- Theme persistence and restoration
- Component theme inheritance and composition
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Set, Callable, Union, Tuple
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QColor, QPalette, QFont, QFontMetrics
from dataclasses import dataclass, asdict, field
from enum import Enum
from abc import ABC, abstractmethod
import logging

from .tab_styling import TabStyleManager, TabColorScheme, TabStyleVariant
from .events import get_event_bus, EventType, ComponentEvent

class ComponentThemeType(Enum):
    """Component-specific theme types"""
    TABLE = "table"
    BUTTON = "button"
    INPUT = "input"
    SELECTOR = "selector"
    PROGRESS = "progress"
    FILTER = "filter"
    SEARCH = "search"
    POPUP = "popup"
    DIALOG = "dialog"
    WIDGET = "widget"


class ComponentState(Enum):
    """Component interaction states"""
    NORMAL = "normal"
    HOVER = "hover"
    ACTIVE = "active"
    PRESSED = "pressed"
    DISABLED = "disabled"
    FOCUSED = "focused"
    LOADING = "loading"
    ERROR = "error"
    SUCCESS = "success"
    WARNING = "warning"


class ResponsiveBreakpoint(Enum):
    """Responsive design breakpoints"""
    MOBILE = 480    # < 480px
    TABLET = 768    # 480px - 768px
    DESKTOP = 1024  # 768px - 1024px
    WIDE = 1440     # 1024px - 1440px
    ULTRA_WIDE = 2560  # > 1440px


@dataclass
class ComponentColorPalette:
    """Extended color palette for component theming"""
    # Base colors (inherited from TabColorScheme)
    primary: str = "#0078d4"
    secondary: str = "#6c757d"
    background: str = "#ffffff"
    surface: str = "#f8f9fa"
    text_primary: str = "#212529"
    border: str = "#dee2e6"
    
    # Component-specific colors
    table_header_bg: str = "#f8f9fa"
    table_row_hover: str = "#f5f5f5"
    table_row_selected: str = "#e3f2fd"
    table_border: str = "#e0e0e0"
    
    button_primary: str = "#0078d4"
    button_primary_hover: str = "#106ebe"
    button_primary_active: str = "#005a9e"
    button_secondary: str = "#6c757d"
    button_danger: str = "#dc3545"
    
    input_bg: str = "#ffffff"
    input_border: str = "#ced4da"
    input_border_focus: str = "#80bdff"
    input_placeholder: str = "#6c757d"
    
    progress_bg: str = "#e9ecef"
    progress_fill: str = "#007bff"
    progress_text: str = "#495057"
    
    popup_bg: str = "#ffffff"
    popup_shadow: str = "rgba(0, 0, 0, 0.15)"
    popup_border: str = "#dee2e6"
    
    # State colors
    disabled_bg: str = "#f8f9fa"
    disabled_text: str = "#6c757d"
    disabled_border: str = "#e9ecef"
    
    # Feedback colors
    success_bg: str = "#d4edda"
    success_border: str = "#c3e6cb"
    success_text: str = "#155724"
    
    warning_bg: str = "#fff3cd"
    warning_border: str = "#ffeaa7"
    warning_text: str = "#856404"
    
    error_bg: str = "#f8d7da"
    error_border: str = "#f5c6cb"
    error_text: str = "#721c24"


@dataclass
class ComponentTypography:
    """Typography settings for components"""
    font_family: str = "Segoe UI, Arial, sans-serif"
    font_size_xs: int = 8
    font_size_sm: int = 9
    font_size_base: int = 10
    font_size_lg: int = 11
    font_size_xl: int = 12
    font_size_xxl: int = 14
    
    font_weight_light: int = 300
    font_weight_normal: int = 400
    font_weight_medium: int = 500
    font_weight_semibold: int = 600
    font_weight_bold: int = 700
    
    line_height: float = 1.4
    letter_spacing: float = 0.0


@dataclass
class ComponentSpacing:
    """Spacing and sizing settings"""
    xs: int = 2
    sm: int = 4
    base: int = 8
    md: int = 12
    lg: int = 16
    xl: int = 24
    xxl: int = 32
    
    border_radius_sm: int = 4
    border_radius_base: int = 6
    border_radius_lg: int = 8
    border_radius_xl: int = 12
    
    border_width: int = 1
    focus_border_width: int = 2
    
    component_padding: int = 8
    component_margin: int = 4


@dataclass
class ComponentAnimations:
    """Animation settings for components"""
    duration_fast: int = 150
    duration_normal: int = 250
    duration_slow: int = 400
    
    easing_ease_out: str = "cubic-bezier(0.25, 0.1, 0.25, 1)"
    easing_ease_in: str = "cubic-bezier(0.55, 0.055, 0.675, 0.19)"
    easing_ease_in_out: str = "cubic-bezier(0.645, 0.045, 0.355, 1)"
    
    hover_scale: float = 1.02
    active_scale: float = 0.98
    
    transition_properties: List[str] = field(default_factory=lambda: [
        "background-color", "border-color", "color", "box-shadow", "transform"
    ])


@dataclass
class ComponentTheme:
    """Complete component theme configuration"""
    name: str
    type: ComponentThemeType
    colors: ComponentColorPalette
    typography: ComponentTypography
    spacing: ComponentSpacing
    animations: ComponentAnimations
    custom_properties: Dict[str, Any] = field(default_factory=dict)
    parent_theme: Optional[str] = None
    responsive_overrides: Dict[ResponsiveBreakpoint, Dict[str, Any]] = field(default_factory=dict)


class ComponentThemeManager:
    """Advanced component theme management system"""
    
    def __init__(self, tab_style_manager: TabStyleManager = None):
        self.tab_style_manager = tab_style_manager or TabStyleManager()
        self._themes: Dict[str, ComponentTheme] = {}
        self._active_themes: Dict[str, str] = {}  # component_id -> theme_name
        self._component_states: Dict[str, ComponentState] = {}
        self._responsive_cache: Dict[Tuple[str, ResponsiveBreakpoint], str] = {}
        self._animation_properties: Dict[str, QPropertyAnimation] = {}
        
        # Theme change listeners
        self._theme_change_callbacks: Dict[str, List[Callable]] = {}
        
        # Event bus integration
        self.event_bus = get_event_bus()
        
        # Initialize built-in themes
        self._initialize_builtin_themes()
        
        # Performance optimization
        self._style_cache: Dict[str, str] = {}
        self._cache_ttl = 300000  # 5 minutes in milliseconds
        self._last_cache_clear = datetime.now()
    
    def _initialize_builtin_themes(self):
        """Initialize built-in component themes"""
        # Light theme
        light_colors = ComponentColorPalette()
        light_theme = ComponentTheme(
            name="light",
            type=ComponentThemeType.WIDGET,
            colors=light_colors,
            typography=ComponentTypography(),
            spacing=ComponentSpacing(),
            animations=ComponentAnimations()
        )
        self.register_theme(light_theme)
        
        # Dark theme
        dark_colors = ComponentColorPalette(
            primary="#0d7377",
            background="#1e1e1e",
            surface="#2d2d30",
            text_primary="#ffffff",
            border="#404040",
            
            table_header_bg="#2d2d30",
            table_row_hover="#3e3e42",
            table_row_selected="#1a4754",
            table_border="#404040",
            
            button_primary="#0d7377",
            button_primary_hover="#14a085",
            button_secondary="#5a6268",
            
            input_bg="#2d2d30",
            input_border="#404040",
            input_border_focus="#0d7377",
            
            popup_bg="#2d2d30",
            popup_shadow="rgba(0, 0, 0, 0.3)",
            popup_border="#404040",
            
            disabled_bg="#3e3e42",
            disabled_text="#969696",
            disabled_border="#555555"
        )
        
        dark_theme = ComponentTheme(
            name="dark",
            type=ComponentThemeType.WIDGET,
            colors=dark_colors,
            typography=ComponentTypography(),
            spacing=ComponentSpacing(),
            animations=ComponentAnimations()
        )
        self.register_theme(dark_theme)
        
        # High contrast theme
        hc_colors = ComponentColorPalette(
            primary="#0000ff",
            background="#ffffff",
            surface="#ffffff", 
            text_primary="#000000",
            border="#000000",
            
            table_header_bg="#ffffff",
            table_row_hover="#f0f0f0",
            table_row_selected="#cce7ff",
            table_border="#000000",
            
            button_primary="#0000ff",
            button_primary_hover="#0000cc",
            button_secondary="#000000",
            
            input_bg="#ffffff",
            input_border="#000000",
            input_border_focus="#0000ff"
        )
        
        hc_theme = ComponentTheme(
            name="high_contrast",
            type=ComponentThemeType.WIDGET,
            colors=hc_colors,
            typography=ComponentTypography(font_weight_medium=600, font_weight_semibold=700),
            spacing=ComponentSpacing(border_width=2, focus_border_width=3),
            animations=ComponentAnimations(duration_fast=0, duration_normal=0, duration_slow=0)
        )
        self.register_theme(hc_theme)
    
    def register_theme(self, theme: ComponentTheme):
        """Register a new component theme"""
        self._themes[theme.name] = theme
        self._clear_style_cache()
    
    def get_theme(self, theme_name: str) -> Optional[ComponentTheme]:
        """Get a registered theme"""
        return self._themes.get(theme_name)
    
    def get_available_themes(self) -> List[str]:
        """Get list of available theme names"""
        return list(self._themes.keys())
    
    def apply_theme_to_component(self, 
                                component_id: str,
                                theme_name: str,
                                component_type: ComponentThemeType,
                                widget: QWidget = None,
                                state: ComponentState = ComponentState.NORMAL) -> str:
        """Apply theme to a specific component and return CSS"""
        theme = self.get_theme(theme_name)
        if not theme:
            theme = self.get_theme("light")  # Fallback
        
        # Store active theme for component
        self._active_themes[component_id] = theme_name
        self._component_states[component_id] = state
        
        # Generate component-specific CSS
        css = self._generate_component_css(theme, component_type, state)
        
        # Apply responsive overrides if needed
        if widget:
            breakpoint = self._get_responsive_breakpoint(widget)
            css = self._apply_responsive_overrides(css, theme, breakpoint)
        
        # Cache the result
        cache_key = f"{component_id}_{theme_name}_{component_type.value}_{state.value}"
        self._style_cache[cache_key] = css
        
        # Apply to widget if provided
        if widget:
            self._apply_css_to_widget(widget, css)
            
            # Setup state change animations
            self._setup_state_animations(widget, theme)
        
        # Emit theme change event
        self._emit_theme_changed(component_id, theme_name, component_type)
        
        return css
    
    def _generate_component_css(self, 
                               theme: ComponentTheme,
                               component_type: ComponentThemeType,
                               state: ComponentState) -> str:
        """Generate CSS for specific component type and state"""
        colors = theme.colors
        typography = theme.typography
        spacing = theme.spacing
        animations = theme.animations
        
        # Base styles
        base_css = f"""
        QWidget {{
            font-family: {typography.font_family};
            font-size: {typography.font_size_base}pt;
            color: {colors.text_primary};
            background-color: {colors.background};
            border-radius: {spacing.border_radius_base}px;
        }}
        """
        
        # Component-specific styles
        component_css = ""
        
        if component_type == ComponentThemeType.TABLE:
            component_css = self._generate_table_css(theme, state)
        elif component_type == ComponentThemeType.BUTTON:
            component_css = self._generate_button_css(theme, state)
        elif component_type == ComponentThemeType.INPUT:
            component_css = self._generate_input_css(theme, state)
        elif component_type == ComponentThemeType.SELECTOR:
            component_css = self._generate_selector_css(theme, state)
        elif component_type == ComponentThemeType.PROGRESS:
            component_css = self._generate_progress_css(theme, state)
        elif component_type == ComponentThemeType.POPUP:
            component_css = self._generate_popup_css(theme, state)
        
        # State-specific modifications
        state_css = self._generate_state_css(theme, state)
        
        # Animation styles
        animation_css = self._generate_animation_css(theme)
        
        return f"{base_css}\n{component_css}\n{state_css}\n{animation_css}"
    
    def _generate_table_css(self, theme: ComponentTheme, state: ComponentState) -> str:
        """Generate table-specific CSS"""
        colors = theme.colors
        spacing = theme.spacing
        
        return f"""
        /* Table Styling */
        QTableWidget, QTableView {{
            background-color: {colors.background};
            alternate-background-color: {colors.table_row_hover};
            selection-background-color: {colors.table_row_selected};
            gridline-color: {colors.table_border};
            border: {spacing.border_width}px solid {colors.border};
            border-radius: {spacing.border_radius_base}px;
        }}
        
        QTableWidget::item, QTableView::item {{
            padding: {spacing.component_padding}px;
            border: none;
        }}
        
        QTableWidget::item:hover, QTableView::item:hover {{
            background-color: {colors.table_row_hover};
        }}
        
        QTableWidget::item:selected, QTableView::item:selected {{
            background-color: {colors.table_row_selected};
            color: {colors.text_primary};
        }}
        
        QHeaderView::section {{
            background-color: {colors.table_header_bg};
            color: {colors.text_primary};
            padding: {spacing.component_padding}px;
            border: none;
            border-bottom: {spacing.border_width}px solid {colors.table_border};
            font-weight: {theme.typography.font_weight_medium};
        }}
        
        QHeaderView::section:hover {{
            background-color: {colors.table_row_hover};
        }}
        """
    
    def _generate_button_css(self, theme: ComponentTheme, state: ComponentState) -> str:
        """Generate button-specific CSS"""
        colors = theme.colors
        spacing = theme.spacing
        typography = theme.typography
        
        # State-specific button colors
        if state == ComponentState.HOVER:
            bg_color = colors.button_primary_hover
        elif state == ComponentState.ACTIVE or state == ComponentState.PRESSED:
            bg_color = colors.button_primary_active
        elif state == ComponentState.DISABLED:
            bg_color = colors.disabled_bg
        else:
            bg_color = colors.button_primary
        
        return f"""
        /* Button Styling */
        QPushButton {{
            background-color: {bg_color};
            color: {colors.text_primary if state == ComponentState.DISABLED else "#ffffff"};
            border: {spacing.border_width}px solid {bg_color};
            border-radius: {spacing.border_radius_base}px;
            padding: {spacing.component_padding}px {spacing.md}px;
            font-weight: {typography.font_weight_medium};
            font-size: {typography.font_size_base}pt;
        }}
        
        QPushButton:hover {{
            background-color: {colors.button_primary_hover};
            border-color: {colors.button_primary_hover};
        }}
        
        QPushButton:pressed {{
            background-color: {colors.button_primary_active};
            border-color: {colors.button_primary_active};
        }}
        
        QPushButton:disabled {{
            background-color: {colors.disabled_bg};
            color: {colors.disabled_text};
            border-color: {colors.disabled_border};
        }}
        
        QPushButton[class="secondary"] {{
            background-color: {colors.button_secondary};
            border-color: {colors.button_secondary};
        }}
        
        QPushButton[class="danger"] {{
            background-color: {colors.button_danger};
            border-color: {colors.button_danger};
        }}
        """
    
    def _generate_input_css(self, theme: ComponentTheme, state: ComponentState) -> str:
        """Generate input field-specific CSS"""
        colors = theme.colors
        spacing = theme.spacing
        
        border_color = colors.input_border
        if state == ComponentState.FOCUSED:
            border_color = colors.input_border_focus
        elif state == ComponentState.ERROR:
            border_color = colors.error_border
        elif state == ComponentState.DISABLED:
            border_color = colors.disabled_border
        
        return f"""
        /* Input Field Styling */
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {colors.input_bg if state != ComponentState.DISABLED else colors.disabled_bg};
            color: {colors.text_primary if state != ComponentState.DISABLED else colors.disabled_text};
            border: {spacing.border_width if state != ComponentState.FOCUSED else spacing.focus_border_width}px solid {border_color};
            border-radius: {spacing.border_radius_base}px;
            padding: {spacing.component_padding}px {spacing.md}px;
            font-size: {theme.typography.font_size_base}pt;
        }}
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border: {spacing.focus_border_width}px solid {colors.input_border_focus};
            outline: none;
        }}
        
        QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
            background-color: {colors.disabled_bg};
            color: {colors.disabled_text};
            border-color: {colors.disabled_border};
        }}
        """
    
    def _generate_selector_css(self, theme: ComponentTheme, state: ComponentState) -> str:
        """Generate selector/combobox-specific CSS"""
        colors = theme.colors
        spacing = theme.spacing
        
        return f"""
        /* Selector/ComboBox Styling */
        QComboBox {{
            background-color: {colors.input_bg};
            color: {colors.text_primary};
            border: {spacing.border_width}px solid {colors.input_border};
            border-radius: {spacing.border_radius_base}px;
            padding: {spacing.component_padding}px {spacing.md}px;
            min-width: 100px;
        }}
        
        QComboBox:hover {{
            border-color: {colors.primary};
        }}
        
        QComboBox:focus {{
            border: {spacing.focus_border_width}px solid {colors.input_border_focus};
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        
        QComboBox::down-arrow {{
            width: 12px;
            height: 12px;
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {colors.popup_bg};
            border: {spacing.border_width}px solid {colors.popup_border};
            border-radius: {spacing.border_radius_base}px;
            selection-background-color: {colors.table_row_selected};
        }}
        """
    
    def _generate_progress_css(self, theme: ComponentTheme, state: ComponentState) -> str:
        """Generate progress bar-specific CSS"""
        colors = theme.colors
        spacing = theme.spacing
        
        return f"""
        /* Progress Bar Styling */
        QProgressBar {{
            background-color: {colors.progress_bg};
            color: {colors.progress_text};
            border: {spacing.border_width}px solid {colors.border};
            border-radius: {spacing.border_radius_base}px;
            text-align: center;
            font-weight: {theme.typography.font_weight_medium};
        }}
        
        QProgressBar::chunk {{
            background-color: {colors.progress_fill};
            border-radius: {spacing.border_radius_sm}px;
        }}
        """
    
    def _generate_popup_css(self, theme: ComponentTheme, state: ComponentState) -> str:
        """Generate popup/dialog-specific CSS"""
        colors = theme.colors
        spacing = theme.spacing
        
        return f"""
        /* Popup/Dialog Styling */
        QDialog, QMenu {{
            background-color: {colors.popup_bg};
            color: {colors.text_primary};
            border: {spacing.border_width}px solid {colors.popup_border};
            border-radius: {spacing.border_radius_lg}px;
        }}
        
        QMenu::item {{
            padding: {spacing.component_padding}px {spacing.md}px;
            border: none;
        }}
        
        QMenu::item:selected {{
            background-color: {colors.table_row_hover};
        }}
        
        QMenu::separator {{
            height: 1px;
            background-color: {colors.border};
            margin: {spacing.sm}px 0;
        }}
        """
    
    def _generate_state_css(self, theme: ComponentTheme, state: ComponentState) -> str:
        """Generate state-specific CSS modifications"""
        colors = theme.colors
        
        if state == ComponentState.DISABLED:
            return f"""
            QWidget:disabled {{
                color: {colors.disabled_text};
                background-color: {colors.disabled_bg};
            }}
            """
        elif state == ComponentState.ERROR:
            return f"""
            QWidget[state="error"] {{
                border-color: {colors.error_border};
                background-color: {colors.error_bg};
            }}
            """
        elif state == ComponentState.SUCCESS:
            return f"""
            QWidget[state="success"] {{
                border-color: {colors.success_border};
                background-color: {colors.success_bg};
            }}
            """
        elif state == ComponentState.WARNING:
            return f"""
            QWidget[state="warning"] {{
                border-color: {colors.warning_border};
                background-color: {colors.warning_bg};
            }}
            """
        
        return ""
    
    def _generate_animation_css(self, theme: ComponentTheme) -> str:
        """Generate animation-related CSS"""
        animations = theme.animations
        
        return f"""
        /* Animation Styles */
        QWidget {{
            transition: {', '.join(animations.transition_properties)} {animations.duration_normal}ms {animations.easing_ease_out};
        }}
        
        QPushButton {{
            transition: all {animations.duration_fast}ms {animations.easing_ease_out};
        }}
        
        QPushButton:hover {{
            transform: scale({animations.hover_scale});
        }}
        
        QPushButton:pressed {{
            transform: scale({animations.active_scale});
        }}
        """
    
    def _get_responsive_breakpoint(self, widget: QWidget) -> ResponsiveBreakpoint:
        """Determine responsive breakpoint based on widget size"""
        width = widget.width()
        
        if width < ResponsiveBreakpoint.MOBILE.value:
            return ResponsiveBreakpoint.MOBILE
        elif width < ResponsiveBreakpoint.TABLET.value:
            return ResponsiveBreakpoint.TABLET
        elif width < ResponsiveBreakpoint.DESKTOP.value:
            return ResponsiveBreakpoint.DESKTOP
        elif width < ResponsiveBreakpoint.WIDE.value:
            return ResponsiveBreakpoint.WIDE
        else:
            return ResponsiveBreakpoint.ULTRA_WIDE
    
    def _apply_responsive_overrides(self, 
                                   css: str,
                                   theme: ComponentTheme,
                                   breakpoint: ResponsiveBreakpoint) -> str:
        """Apply responsive design overrides"""
        if breakpoint in theme.responsive_overrides:
            overrides = theme.responsive_overrides[breakpoint]
            # Apply responsive modifications to CSS
            # Implementation depends on specific override requirements
            pass
        
        return css
    
    def _apply_css_to_widget(self, widget: QWidget, css: str):
        """Apply CSS to widget with error handling"""
        try:
            widget.setStyleSheet(css)
        except Exception as e:
            print(f"Error applying CSS to widget: {e}")
    
    def _setup_state_animations(self, widget: QWidget, theme: ComponentTheme):
        """Setup state change animations for widget"""
        # Create property animations for smooth state transitions
        # Implementation depends on specific animation requirements
        pass
    
    def _emit_theme_changed(self, 
                           component_id: str,
                           theme_name: str,
                           component_type: ComponentThemeType):
        """Emit theme change event"""
        event = ComponentEvent(
            event_type=EventType.THEME_CHANGED,
            source_component=component_id,
            data={
                'theme_name': theme_name,
                'component_type': component_type.value,
                'timestamp': datetime.now().isoformat()
            }
        )
        self.event_bus.emit_event(event)
    
    def _clear_style_cache(self):
        """Clear cached styles"""
        self._style_cache.clear()
        self._responsive_cache.clear()
        self._last_cache_clear = datetime.now()
    
    def set_component_state(self, 
                           component_id: str,
                           state: ComponentState,
                           widget: QWidget = None):
        """Update component state and reapply theme"""
        if component_id in self._active_themes:
            theme_name = self._active_themes[component_id]
            component_type = ComponentThemeType.WIDGET  # Default, can be enhanced
            
            return self.apply_theme_to_component(
                component_id, theme_name, component_type, widget, state
            )
    
    def get_component_theme_info(self, component_id: str) -> Dict[str, Any]:
        """Get theme information for a component"""
        return {
            'active_theme': self._active_themes.get(component_id),
            'current_state': self._component_states.get(component_id),
            'available_themes': self.get_available_themes()
        }
    
    def export_theme(self, theme_name: str) -> Optional[Dict[str, Any]]:
        """Export theme configuration as JSON"""
        theme = self.get_theme(theme_name)
        if theme:
            return asdict(theme)
        return None
    
    def import_theme(self, theme_data: Dict[str, Any]) -> bool:
        """Import theme configuration from JSON"""
        try:
            theme = ComponentTheme(**theme_data)
            self.register_theme(theme)
            return True
        except Exception as e:
            print(f"Error importing theme: {e}")
            return False


# Global component theme manager instance
_component_theme_manager = None

def get_component_theme_manager() -> ComponentThemeManager:
    """Get global component theme manager instance"""
    global _component_theme_manager
    if _component_theme_manager is None:
        _component_theme_manager = ComponentThemeManager()
    return _component_theme_manager

def initialize_component_theming():
    """Initialize component theming system"""
    return get_component_theme_manager()

def apply_component_theme(widget: QWidget,
                         component_id: str,
                         theme_name: str,
                         component_type: ComponentThemeType,
                         state: ComponentState = ComponentState.NORMAL) -> str:
    """Convenience function to apply theme to component"""
    manager = get_component_theme_manager()
    return manager.apply_theme_to_component(
        component_id, theme_name, component_type, widget, state
    ) 