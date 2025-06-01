"""
Enhanced Tab System

Modern tab enhancements including icons, visual indicators, hover states,
and improved accessibility for the Social Download Manager application.
"""

from typing import Dict, Optional, Tuple
from PyQt6.QtWidgets import QTabWidget, QWidget, QTabBar
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QIcon, QPainter, QPen, QColor, QFont
from .style_manager import StyleManager
from .theme_styles import ThemeStyler

class ModernTabWidget(QTabWidget):
    """
    Enhanced QTabWidget with modern design features
    
    Features:
    - Tab icons with theme-appropriate colors
    - Enhanced hover effects with animations
    - Visual indicators for active/inactive states
    - Improved accessibility with better contrast
    - Modern spacing and typography
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialize design system
        self.style_manager = StyleManager()
        self.theme_styler = ThemeStyler(self.style_manager)
        
        # Tab configuration
        self.tab_icons = {}  # Tab index -> icon path mapping
        self.tab_indicators = {}  # Tab index -> indicator color mapping
        
        # Apply modern tab styling
        self._setup_modern_styling()
        
        # Connect theme change signal
        if hasattr(parent, 'styler') and hasattr(parent.styler, 'theme_changed'):
            parent.styler.theme_changed.connect(self._on_theme_changed)
    
    def _setup_modern_styling(self):
        """Setup modern tab styling using design system"""
        # Get enhanced tab stylesheet
        enhanced_styles = self._get_enhanced_tab_styles()
        self.setStyleSheet(enhanced_styles)
        
        # Configure tab behavior
        self.setTabsClosable(False)
        self.setMovable(False)
        self.setElideMode(Qt.TextElideMode.ElideRight)
        
        # Set modern spacing
        tab_bar = self.tabBar()
        if tab_bar:
            tab_bar.setExpanding(False)
            tab_bar.setDrawBase(True)
    
    def _get_enhanced_tab_styles(self) -> str:
        """Generate enhanced tab styles using design tokens"""
        base_styles = self.style_manager.generate_stylesheet('tab')
        
        # Get theme-specific colors
        primary_color = self.style_manager.get_token_value('color-brand-primary-500', '#3B82F6')
        text_primary = self.style_manager.get_token_value('color-text-primary', '#333333')
        text_secondary = self.style_manager.get_token_value('color-text-secondary', '#666666')
        background_primary = self.style_manager.get_token_value('color-background-primary', '#ffffff')
        background_secondary = self.style_manager.get_token_value('color-background-secondary', '#f5f5f5')
        border_color = self.style_manager.get_token_value('color-border-default', '#e5e5e5')
        
        enhanced_styles = f"""
            {base_styles}
            
            /* Enhanced Tab Styling */
            QTabWidget::pane {{
                border: 1px solid {border_color};
                background-color: {background_primary};
                border-radius: 8px;
                padding: 4px;
            }}
            
            QTabBar::tab {{
                background-color: {background_secondary};
                color: {text_secondary};
                border: 1px solid {border_color};
                border-bottom: none;
                padding: 12px 20px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: 500;
                font-size: 13px;
                min-width: 120px;
                max-width: 200px;
                text-align: center;
            }}
            
            QTabBar::tab:selected {{
                background-color: {primary_color};
                color: #ffffff;
                border-color: {primary_color};
                font-weight: 600;
            }}
            
            QTabBar::tab:hover:!selected {{
                background-color: {background_primary};
                color: {text_primary};
                border-color: {primary_color};
                transform: translateY(-1px);
            }}
            
            QTabBar::tab:disabled {{
                background-color: #f0f0f0;
                color: #a0a0a0;
                border-color: #e0e0e0;
            }}
            
            /* Tab close button (if enabled) */
            QTabBar::close-button {{
                image: none;
                background-color: transparent;
                border-radius: 3px;
                margin: 2px;
            }}
            
            QTabBar::close-button:hover {{
                background-color: rgba(255, 255, 255, 0.2);
            }}
        """
        
        return enhanced_styles
    
    def add_tab_with_icon(self, widget: QWidget, icon_path: str, title: str, indicator_color: str = None) -> int:
        """
        Add a tab with an icon and optional indicator
        
        Args:
            widget: Widget to add as tab content
            icon_path: Path to tab icon
            title: Tab title text
            indicator_color: Optional color for tab indicator
            
        Returns:
            Index of added tab
        """
        # Create icon if path provided
        icon = QIcon(icon_path) if icon_path else QIcon()
        
        # Add tab with icon
        tab_index = self.addTab(widget, icon, title)
        
        # Store tab configuration
        if icon_path:
            self.tab_icons[tab_index] = icon_path
        if indicator_color:
            self.tab_indicators[tab_index] = indicator_color
        
        return tab_index
    
    def set_tab_indicator(self, index: int, color: str, visible: bool = True):
        """
        Set visual indicator for a tab
        
        Args:
            index: Tab index
            color: Indicator color
            visible: Whether indicator is visible
        """
        if visible:
            self.tab_indicators[index] = color
        elif index in self.tab_indicators:
            del self.tab_indicators[index]
        
        self._update_tab_styling(index)
    
    def _update_tab_styling(self, index: int):
        """Update styling for a specific tab"""
        tab_bar = self.tabBar()
        if not tab_bar:
            return
        
        # Update tab with indicator if present
        if index in self.tab_indicators:
            indicator_color = self.tab_indicators[index]
            # Add custom styling for this specific tab
            # This would require custom painting which is complex in stylesheets
            # For now, we'll handle this through the general styling
    
    def _on_theme_changed(self, theme_name: str):
        """Handle theme change event"""
        # Update styling for new theme
        self._setup_modern_styling()
        
        # Update icons for new theme if they're theme-dependent
        self._update_theme_dependent_icons()
    
    def _update_theme_dependent_icons(self):
        """Update icons that change based on theme"""
        icon_suffix = self.theme_styler.get_icon_suffix_for_theme()
        
        for tab_index, base_icon_path in self.tab_icons.items():
            # Replace icon suffix if the icon path follows the platform pattern
            if "platforms/" in base_icon_path and ("-bw" in base_icon_path or "-outlined" in base_icon_path):
                # Remove existing suffix and add new one
                base_path = base_icon_path.replace("-bw", "").replace("-outlined", "")
                new_icon_path = base_path.replace(".png", f"{icon_suffix}.png")
                
                # Update tab icon
                new_icon = QIcon(new_icon_path)
                self.setTabIcon(tab_index, new_icon)
                self.tab_icons[tab_index] = new_icon_path


class TabSystemIntegrator:
    """
    Integration helper for modernizing existing tab systems
    
    Provides utilities to upgrade existing QTabWidget instances
    to use the enhanced design system styling.
    """
    
    def __init__(self, style_manager: StyleManager = None):
        self.style_manager = style_manager or StyleManager()
        self.theme_styler = ThemeStyler(self.style_manager)
    
    def modernize_tab_widget(self, tab_widget: QTabWidget, tab_configs: Dict = None):
        """
        Modernize an existing QTabWidget with design system styling
        
        Args:
            tab_widget: Existing QTabWidget to modernize
            tab_configs: Optional dict with tab configuration
                        {index: {'icon': 'path', 'indicator': 'color'}}
        """
        # Apply modern styling
        enhanced_styles = self._get_tab_styles_for_widget(tab_widget)
        tab_widget.setStyleSheet(enhanced_styles)
        
        # Configure tab behavior
        tab_widget.setTabsClosable(False)
        tab_widget.setMovable(False)
        tab_widget.setElideMode(Qt.TextElideMode.ElideRight)
        
        # Apply tab configurations if provided
        if tab_configs:
            for index, config in tab_configs.items():
                if index < tab_widget.count():
                    # Set icon if provided
                    if 'icon' in config:
                        icon = QIcon(config['icon'])
                        tab_widget.setTabIcon(index, icon)
                    
                    # Set tooltip if provided
                    if 'tooltip' in config:
                        tab_widget.setTabToolTip(index, config['tooltip'])
    
    def _get_tab_styles_for_widget(self, tab_widget: QTabWidget) -> str:
        """Generate enhanced styles for an existing tab widget"""
        # Use the component styler to get base tab styles
        base_styles = self.style_manager.generate_stylesheet('tab')
        
        # Add enhanced features
        theme_adjustments = self.theme_styler.get_theme_specific_stylesheet('tab')
        
        return base_styles + "\n" + theme_adjustments
    
    def add_tab_icons_from_config(self, tab_widget: QTabWidget, icons_config: Dict[int, str]):
        """
        Add icons to existing tabs
        
        Args:
            tab_widget: Tab widget to update
            icons_config: Dict mapping tab index to icon path
        """
        for index, icon_path in icons_config.items():
            if index < tab_widget.count():
                # Get theme-appropriate icon path
                themed_icon_path = self._get_themed_icon_path(icon_path)
                icon = QIcon(themed_icon_path)
                tab_widget.setTabIcon(index, icon)
    
    def _get_themed_icon_path(self, base_icon_path: str) -> str:
        """Get theme-appropriate icon path"""
        if "platforms/" in base_icon_path:
            # Platform icons change based on theme
            icon_suffix = self.theme_styler.get_icon_suffix_for_theme()
            # Remove existing suffix and add new one
            base_path = base_icon_path.replace("-bw", "").replace("-outlined", "")
            return base_path.replace(".png", f"{icon_suffix}.png")
        
        return base_icon_path
    
    def create_tab_config_for_main_window(self) -> Dict[int, Dict]:
        """
        Create tab configuration for the main window tabs
        
        Returns:
            Dict with tab configurations for video info and downloaded videos tabs
        """
        return {
            0: {  # Video Info Tab
                'icon': 'assets/icons/video-info.png',
                'tooltip': 'Video Information and Download',
                'indicator': None
            },
            1: {  # Downloaded Videos Tab  
                'icon': 'assets/icons/downloads.png',
                'tooltip': 'Manage Downloaded Videos',
                'indicator': None
            }
        } 