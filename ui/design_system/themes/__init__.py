"""
Theme System

Theme management system for the Social Download Manager design system.
Provides theme definitions, management, and preset themes.
"""

from .base import (
    ThemeDefinition,
    ThemeManager,
    ThemeMetadata,
    ThemeType
)

from .presets import (
    ThemePresets,
    initialize_preset_themes
)

__all__ = [
    "ThemeDefinition",
    "ThemeManager",
    "ThemeMetadata",
    "ThemeType",
    "ThemePresets",
    "initialize_preset_themes"
] 