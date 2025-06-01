"""
Main Window Styling

Replacement for the massive inline CSS in main_window.py.
Uses design tokens and modular styling instead of hardcoded values.
"""

from typing import Optional
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal
from .style_manager import StyleManager
from .theme_styles import ThemeStyler
from .tab_enhancements import TabSystemIntegrator


class MainWindowStyler(QObject):
    """
    Modern styling system for MainWindow
    
    Replaces the 400+ lines of inline CSS with modular, token-based styling
    that automatically adapts to theme changes.
    """
    
    # Signal emitted when theme changes
    theme_changed = pyqtSignal(str)  # theme_name
    
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.style_manager = StyleManager()
        self.theme_styler = ThemeStyler(self.style_manager)
        
        # Initialize tab system integrator
        self.tab_integrator = TabSystemIntegrator(self.style_manager)
        
        # Connect theme change signal
        self.theme_changed.connect(self._on_theme_changed)
    
    def set_theme(self, theme_name: str) -> bool:
        """
        Set the application theme using the design system
        
        Args:
            theme_name: Name of theme ('light', 'dark', 'high_contrast', 'blue')
            
        Returns:
            True if theme was set successfully
        """
        success = self.style_manager.switch_theme(theme_name)
        
        if success and self.main_window:
            # Apply complete themed stylesheet to main window
            complete_stylesheet = self._generate_complete_stylesheet()
            self.main_window.setStyleSheet(complete_stylesheet)
            
            # Update application-wide tooltip styles
            tooltip_styles = self.theme_styler.get_tooltip_style_for_theme()
            QApplication.instance().setStyleSheet(tooltip_styles)
            
            # Update platform icons based on theme
            self._update_platform_icons()
            
            # Modernize tab system with new theme
            self._modernize_tab_system()
            
            # Emit theme changed signal
            self.theme_changed.emit(theme_name)
            
            # Update status message
            if hasattr(self.main_window, 'status_bar'):
                if theme_name == 'dark':
                    self.main_window.status_bar.showMessage(
                        self.main_window.tr_("STATUS_DARK_MODE_ENABLED")
                    )
                elif theme_name == 'light':
                    self.main_window.status_bar.showMessage(
                        self.main_window.tr_("STATUS_LIGHT_MODE_ENABLED")
                    )
                else:
                    self.main_window.status_bar.showMessage(
                        f"Theme changed to: {theme_name.title()}"
                    )
        
        return success
    
    def get_current_theme(self) -> Optional[str]:
        """Get the current theme name"""
        return self.style_manager.get_current_theme_name()
    
    def _generate_complete_stylesheet(self) -> str:
        """Generate complete stylesheet for main window"""
        from .component_styles import ComponentStyler
        
        styler = ComponentStyler(self.style_manager)
        
        # Include all main window components
        components = [
            'main_window', 'button', 'input', 'table', 'tab',
            'checkbox', 'menu', 'statusbar', 'dialog'
        ]
        
        return styler.get_complete_stylesheet(components)
    
    def _modernize_tab_system(self):
        """Apply modern styling to the tab system"""
        if not self.main_window or not hasattr(self.main_window, 'tab_widget'):
            return
        
        # Create tab configuration with icons and tooltips
        tab_configs = self._create_tab_configs()
        
        # Modernize the main tab widget
        self.tab_integrator.modernize_tab_widget(
            self.main_window.tab_widget, 
            tab_configs
        )
    
    def _create_tab_configs(self) -> dict:
        """Create tab configuration for main window tabs"""
        # Get theme-appropriate icon suffix
        icon_suffix = self.theme_styler.get_icon_suffix_for_theme()
        
        return {
            0: {  # Video Info Tab
                'tooltip': 'Video Information and Download Manager',
                # Could add icon here if we have tab-specific icons
            },
            1: {  # Downloaded Videos Tab  
                'tooltip': 'View and Manage Downloaded Videos',
                # Could add icon here if we have tab-specific icons
            }
        }
    
    def _update_platform_icons(self):
        """Update platform menu icons based on current theme"""
        if not self.main_window or not hasattr(self.main_window, 'platform_actions'):
            return
        
        from ui.main_window import get_resource_path
        from PyQt6.QtGui import QIcon
        
        # Get appropriate icon suffix for current theme
        icon_suffix = self.theme_styler.get_icon_suffix_for_theme()
        
        # Update each platform action icon
        for platform, action in self.main_window.platform_actions.items():
            icon_path = get_resource_path(f"assets/platforms/{platform}{icon_suffix}.png")
            action.setIcon(QIcon(icon_path))
    
    def apply_theme_to_child_tabs(self, theme_name: str):
        """Apply theme to child tabs that have apply_theme_colors method"""
        if not self.main_window:
            return
        
        # Update video info tab
        if hasattr(self.main_window, 'video_info_tab') and \
           hasattr(self.main_window.video_info_tab, 'apply_theme_colors'):
            self.main_window.video_info_tab.apply_theme_colors(theme_name)
        
        # Update downloaded videos tab
        if hasattr(self.main_window, 'downloaded_videos_tab') and \
           hasattr(self.main_window.downloaded_videos_tab, 'apply_theme_colors'):
            self.main_window.downloaded_videos_tab.apply_theme_colors(theme_name)
        
        # Update donate dialog if exists
        if hasattr(self.main_window, 'donate_dialog') and self.main_window.donate_dialog:
            dialog_styles = self.style_manager.generate_stylesheet('dialog')
            self.main_window.donate_dialog.setStyleSheet(dialog_styles)
            
            if hasattr(self.main_window, 'donate_tab'):
                self.main_window.donate_tab.apply_theme_colors(theme_name)
    
    def _on_theme_changed(self, theme_name: str):
        """Handle theme change event"""
        # Apply theme to child components
        self.apply_theme_to_child_tabs(theme_name)
        
        # Save theme preference if main window has save_config method
        if self.main_window and hasattr(self.main_window, 'save_config'):
            self.main_window.save_config('theme', theme_name)
    
    def export_current_theme_css(self, file_path: str) -> bool:
        """Export current theme as CSS file"""
        try:
            css_content = self.theme_styler.export_current_theme_css(file_path)
            return True
        except Exception as e:
            print(f"Failed to export CSS: {e}")
            return False
    
    def get_theme_stats(self) -> dict:
        """Get comprehensive theme and styling statistics"""
        return {
            'style_system': self.style_manager.get_stats(),
            'current_theme': self.get_current_theme(),
            'available_themes': list(self.style_manager.theme_manager.get_theme_names()),
            'is_dark_theme': self.theme_styler.is_dark_theme(),
            'icon_suffix': self.theme_styler.get_icon_suffix_for_theme(),
            'tab_integration': {
                'integrator_available': self.tab_integrator is not None,
                'themes_supported': 2  # Light and Dark themes only
            }
        }
    
    def set_tab_indicator(self, tab_index: int, color: str, visible: bool = True):
        """
        Set visual indicator for a specific tab
        
        Args:
            tab_index: Index of tab to update
            color: Indicator color (hex code)
            visible: Whether indicator should be visible
        """
        if not self.main_window or not hasattr(self.main_window, 'tab_widget'):
            return
        
        # This would be implemented if we convert to ModernTabWidget
        # For now, we could set a special property or class on the tab
        tab_widget = self.main_window.tab_widget
        if hasattr(tab_widget, 'set_tab_indicator'):
            tab_widget.set_tab_indicator(tab_index, color, visible)
    
    @staticmethod
    def create_for_main_window(main_window):
        """
        Factory method to create a MainWindowStyler for a MainWindow instance
        
        Args:
            main_window: MainWindow instance to style
            
        Returns:
            Configured MainWindowStyler
        """
        styler = MainWindowStyler(main_window)
        
        # Set initial theme (try to load from config or default to light)
        initial_theme = 'light'
        if hasattr(main_window, 'current_theme'):
            initial_theme = main_window.current_theme
        
        styler.set_theme(initial_theme)
        
        return styler 