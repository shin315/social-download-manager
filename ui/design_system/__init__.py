"""
Social Download Manager - Design System

A comprehensive design token system providing:
- Centralized design tokens (colors, spacing, typography, sizing)
- Semantic naming conventions
- Multi-theme support
- Component-specific theming
- Responsive design capabilities

This system ensures visual consistency and maintainability across the entire application.
"""

from .tokens import (
    DesignToken,
    ColorToken,
    SpacingToken,
    TypographyToken,
    SizingToken,
    TokenManager,
    TokenCategory,
    initialize_design_system
)

from .themes import (
    ThemeDefinition,
    ThemeManager,
    ThemeType,
    ThemePresets,
    initialize_preset_themes
)

from .styles import (
    StyleManager,
    ComponentStyler,
    ThemeStyler
)

__version__ = "1.0.0"
__all__ = [
    # Core Token Classes
    "DesignToken",
    "ColorToken", 
    "SpacingToken",
    "TypographyToken",
    "SizingToken",
    "TokenManager",
    "TokenCategory",
    "initialize_design_system",
    
    # Theme System
    "ThemeDefinition",
    "ThemeManager",
    "ThemeType",
    "ThemePresets",
    "initialize_preset_themes",
    
    # Style System
    "StyleManager",
    "ComponentStyler",
    "ThemeStyler"
]

# Default token manager instance
default_token_manager = None

def get_token_manager() -> TokenManager:
    """Get the default token manager instance"""
    global default_token_manager
    if default_token_manager is None:
        default_token_manager = TokenManager()
    return default_token_manager

def get_theme_manager() -> ThemeManager:
    """Get the default theme manager instance"""
    return get_token_manager().theme_manager 