"""
Theme Presets

Predefined theme configurations for the Social Download Manager.
Includes Light, Dark, and High Contrast themes using semantic tokens.
"""

from typing import Dict, Any
from .base import ThemeDefinition, ThemeMetadata, ThemeType
from datetime import datetime


class ThemePresets:
    """Factory for creating preset theme configurations"""
    
    @staticmethod
    def create_light_theme() -> ThemeDefinition:
        """
        Create the default light theme
        
        This theme uses the default semantic token values without overrides,
        representing the standard light appearance.
        """
        light_overrides = {
            # Background colors - light theme defaults
            'color-background-primary': '#FFFFFF',
            'color-background-secondary': '#F8FAFC',  # neutral-50
            'color-background-tertiary': '#F1F5F9',   # neutral-100
            'color-background-inverse': '#0F172A',     # neutral-900
            
            # Text colors - dark text on light backgrounds
            'color-text-primary': '#0F172A',      # neutral-900
            'color-text-secondary': '#475569',    # neutral-600
            'color-text-tertiary': '#94A3B8',     # neutral-400
            'color-text-inverse': '#FFFFFF',      # white
            'color-text-link': '#3B82F6',         # brand-primary-600
            'color-text-link-hover': '#2563EB',   # brand-primary-700
            
            # Border colors - subtle borders for light theme
            'color-border-default': '#E2E8F0',    # neutral-200
            'color-border-strong': '#CBD5E1',     # neutral-300
            'color-border-focus': '#3B82F6',      # brand-primary-500
            
            # Button colors - maintain brand identity
            'color-button-primary-background': '#3B82F6',         # brand-primary-500
            'color-button-primary-background-hover': '#2563EB',   # brand-primary-600
            'color-button-primary-text': '#FFFFFF',
            'color-button-secondary-background': '#F1F5F9',       # neutral-100
            'color-button-secondary-text': '#374151',             # neutral-700
            
            # Status colors - standard semantic colors
            'color-status-success': '#10B981',    # success-500
            'color-status-warning': '#F59E0B',    # warning-500
            'color-status-error': '#EF4444',      # error-500
            'color-status-info': '#06B6D4',       # info-500
        }
        
        metadata = ThemeMetadata(
            name="light",
            display_name="Light Theme",
            description="Clean, modern light theme for daily use",
            theme_type=ThemeType.LIGHT,
            author="Social Download Manager",
            version="1.0.0",
            created_at=datetime.now(),
            tags={'default', 'light', 'clean', 'modern'}
        )
        
        return ThemeDefinition("light", light_overrides, metadata)
    
    @staticmethod
    def create_dark_theme() -> ThemeDefinition:
        """
        Create the dark theme
        
        Provides a comfortable dark appearance for low-light environments
        while maintaining visual hierarchy and brand consistency.
        """
        dark_overrides = {
            # Background colors - dark theme backgrounds
            'color-background-primary': '#0F172A',      # neutral-900
            'color-background-secondary': '#1E293B',    # neutral-800
            'color-background-tertiary': '#334155',     # neutral-700
            'color-background-inverse': '#FFFFFF',      # white
            
            # Text colors - light text on dark backgrounds
            'color-text-primary': '#F8FAFC',       # neutral-50
            'color-text-secondary': '#CBD5E1',     # neutral-300
            'color-text-tertiary': '#64748B',      # neutral-500
            'color-text-inverse': '#0F172A',       # neutral-900
            'color-text-link': '#60A5FA',          # blue-400 (lighter for dark bg)
            'color-text-link-hover': '#93C5FD',    # blue-300 (even lighter on hover)
            
            # Border colors - subtle borders for dark theme
            'color-border-default': '#475569',     # neutral-600
            'color-border-strong': '#64748B',      # neutral-500
            'color-border-focus': '#60A5FA',       # blue-400 (lighter for visibility)
            
            # Button colors - adjusted for dark theme
            'color-button-primary-background': '#3B82F6',         # brand-primary-500 (keep brand)
            'color-button-primary-background-hover': '#60A5FA',   # blue-400 (lighter on hover)
            'color-button-primary-text': '#FFFFFF',
            'color-button-secondary-background': '#374151',       # neutral-700
            'color-button-secondary-text': '#F8FAFC',             # neutral-50
            
            # Status colors - adjusted for dark theme visibility
            'color-status-success': '#34D399',     # emerald-400 (lighter green)
            'color-status-warning': '#FBBF24',     # amber-400 (lighter yellow)
            'color-status-error': '#F87171',       # red-400 (lighter red)
            'color-status-info': '#22D3EE',        # cyan-400 (lighter cyan)
        }
        
        metadata = ThemeMetadata(
            name="dark",
            display_name="Dark Theme",
            description="Comfortable dark theme for low-light environments",
            theme_type=ThemeType.DARK,
            author="Social Download Manager",
            version="1.0.0",
            created_at=datetime.now(),
            tags={'dark', 'comfortable', 'low-light', 'modern'}
        )
        
        return ThemeDefinition("dark", dark_overrides, metadata)
    
    @staticmethod
    def create_high_contrast_theme() -> ThemeDefinition:
        """
        Create the high contrast theme
        
        Provides maximum contrast for accessibility and users with
        visual impairments or in bright lighting conditions.
        """
        high_contrast_overrides = {
            # Background colors - pure black/white for maximum contrast
            'color-background-primary': '#000000',      # pure black
            'color-background-secondary': '#111111',    # very dark gray
            'color-background-tertiary': '#222222',     # dark gray
            'color-background-inverse': '#FFFFFF',      # pure white
            
            # Text colors - pure white/black for maximum contrast
            'color-text-primary': '#FFFFFF',       # pure white
            'color-text-secondary': '#FFFFFF',     # pure white (no secondary in high contrast)
            'color-text-tertiary': '#CCCCCC',      # light gray (minimal difference)
            'color-text-inverse': '#000000',       # pure black
            'color-text-link': '#00FFFF',          # bright cyan (high visibility)
            'color-text-link-hover': '#FFFF00',    # bright yellow (high visibility)
            
            # Border colors - high contrast borders
            'color-border-default': '#FFFFFF',     # white borders on dark
            'color-border-strong': '#FFFFFF',      # white borders
            'color-border-focus': '#FFFF00',       # bright yellow focus
            
            # Button colors - high contrast buttons
            'color-button-primary-background': '#FFFFFF',    # white background
            'color-button-primary-background-hover': '#FFFF00',  # yellow on hover
            'color-button-primary-text': '#000000',          # black text
            'color-button-secondary-background': '#000000',  # black background
            'color-button-secondary-text': '#FFFFFF',        # white text
            
            # Status colors - high contrast status colors
            'color-status-success': '#00FF00',     # bright green
            'color-status-warning': '#FFFF00',     # bright yellow
            'color-status-error': '#FF0000',       # bright red
            'color-status-info': '#00FFFF',        # bright cyan
        }
        
        metadata = ThemeMetadata(
            name="high_contrast",
            display_name="High Contrast Theme",
            description="Maximum contrast theme for accessibility and bright environments",
            theme_type=ThemeType.HIGH_CONTRAST,
            author="Social Download Manager",
            version="1.0.0",
            created_at=datetime.now(),
            tags={'accessibility', 'high-contrast', 'a11y', 'bright', 'visibility'}
        )
        
        return ThemeDefinition("high_contrast", high_contrast_overrides, metadata)
    
    @staticmethod
    def create_blue_theme() -> ThemeDefinition:
        """
        Create a custom blue-focused theme
        
        Emphasizes blue tones throughout the interface while maintaining usability.
        """
        blue_overrides = {
            # Background colors - blue-tinted backgrounds
            'color-background-primary': '#F0F9FF',      # blue-50
            'color-background-secondary': '#E0F2FE',    # sky-100
            'color-background-tertiary': '#BAE6FD',     # sky-200
            'color-background-inverse': '#0C4A6E',      # sky-900
            
            # Text colors - blue-tinted text
            'color-text-primary': '#0C4A6E',       # sky-900
            'color-text-secondary': '#075985',     # sky-800
            'color-text-tertiary': '#0369A1',      # sky-700
            'color-text-inverse': '#F0F9FF',       # blue-50
            'color-text-link': '#0284C7',          # sky-600
            'color-text-link-hover': '#0369A1',    # sky-700
            
            # Border colors - blue borders
            'color-border-default': '#7DD3FC',     # sky-300
            'color-border-strong': '#38BDF8',      # sky-400
            'color-border-focus': '#0284C7',       # sky-600
            
            # Button colors - blue button scheme
            'color-button-primary-background': '#0284C7',         # sky-600
            'color-button-primary-background-hover': '#0369A1',   # sky-700
            'color-button-primary-text': '#F0F9FF',              # blue-50
            'color-button-secondary-background': '#BAE6FD',       # sky-200
            'color-button-secondary-text': '#0C4A6E',             # sky-900
            
            # Status colors - maintain standard semantic colors
            'color-status-success': '#10B981',     # emerald-500
            'color-status-warning': '#F59E0B',     # amber-500
            'color-status-error': '#EF4444',       # red-500
            'color-status-info': '#06B6D4',        # cyan-500
        }
        
        metadata = ThemeMetadata(
            name="blue",
            display_name="Blue Theme",
            description="Blue-focused theme with calming blue tones throughout",
            theme_type=ThemeType.CUSTOM,
            author="Social Download Manager",
            version="1.0.0",
            created_at=datetime.now(),
            tags={'blue', 'calming', 'custom', 'tinted', 'cool'}
        )
        
        return ThemeDefinition("blue", blue_overrides, metadata)
    
    @classmethod
    def create_all_presets(cls) -> Dict[str, ThemeDefinition]:
        """Create all preset themes"""
        return {
            'light': cls.create_light_theme(),
            'dark': cls.create_dark_theme(),
            'high_contrast': cls.create_high_contrast_theme(),
            'blue': cls.create_blue_theme()
        }
    
    @classmethod
    def get_default_theme_name(cls) -> str:
        """Get the name of the default theme"""
        return "light"
    
    @classmethod
    def get_preset_names(cls) -> list[str]:
        """Get list of all preset theme names"""
        return ['light', 'dark', 'high_contrast', 'blue']
    
    @classmethod
    def is_preset_theme(cls, theme_name: str) -> bool:
        """Check if a theme name is a preset theme"""
        return theme_name in cls.get_preset_names()


def initialize_preset_themes(theme_manager) -> Dict[str, bool]:
    """
    Initialize all preset themes in a ThemeManager
    
    Args:
        theme_manager: ThemeManager instance to register presets in
        
    Returns:
        Dict mapping theme names to registration success status
    """
    preset_themes = ThemePresets.create_all_presets()
    registration_results = {}
    
    for theme_name, theme in preset_themes.items():
        success = theme_manager.register_theme(theme)
        registration_results[theme_name] = success
    
    # Set default theme if successful
    if registration_results.get('light', False):
        theme_manager.switch_theme('light')
    
    return registration_results 