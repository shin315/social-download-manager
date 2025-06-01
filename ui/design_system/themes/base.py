"""
Theme Base Classes

Core theme system classes that work with design tokens to provide
consistent theming across the Social Download Manager application.
"""

from typing import Dict, Any, Optional, Set, List
from enum import Enum
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime


class ThemeType(Enum):
    """Types of themes available"""
    LIGHT = "light"
    DARK = "dark"
    HIGH_CONTRAST = "high_contrast"
    CUSTOM = "custom"


@dataclass
class ThemeMetadata:
    """Metadata for theme definitions"""
    name: str
    display_name: str
    description: Optional[str] = None
    theme_type: ThemeType = ThemeType.CUSTOM
    author: Optional[str] = None
    version: str = "1.0.0"
    created_at: Optional[datetime] = None
    tags: Set[str] = field(default_factory=set)


class ThemeDefinition:
    """
    Theme definition that maps semantic token names to values
    
    A theme defines how semantic tokens should be resolved for a specific
    visual appearance (light, dark, high contrast, etc.)
    """
    
    def __init__(self, 
                 name: str,
                 token_overrides: Dict[str, Any],
                 metadata: Optional[ThemeMetadata] = None):
        self.name = name
        self.token_overrides = token_overrides
        self.metadata = metadata or ThemeMetadata(
            name=name,
            display_name=name.title(),
            created_at=datetime.now()
        )
        self._logger = logging.getLogger(__name__)
    
    def get_token_value(self, token_name: str, fallback: Any = None) -> Any:
        """
        Get the themed value for a token
        
        Args:
            token_name: Name of the token to get value for
            fallback: Fallback value if token not found in theme
            
        Returns:
            The themed value or fallback
        """
        return self.token_overrides.get(token_name, fallback)
    
    def has_token_override(self, token_name: str) -> bool:
        """Check if theme has an override for the given token"""
        return token_name in self.token_overrides
    
    def set_token_override(self, token_name: str, value: Any):
        """Set a token override value"""
        self.token_overrides[token_name] = value
    
    def remove_token_override(self, token_name: str):
        """Remove a token override"""
        self.token_overrides.pop(token_name, None)
    
    def get_all_overrides(self) -> Dict[str, Any]:
        """Get all token overrides in this theme"""
        return self.token_overrides.copy()
    
    def merge_overrides(self, other_overrides: Dict[str, Any]):
        """Merge additional token overrides into this theme"""
        self.token_overrides.update(other_overrides)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert theme to dictionary representation"""
        return {
            'name': self.name,
            'metadata': {
                'display_name': self.metadata.display_name,
                'description': self.metadata.description,
                'theme_type': self.metadata.theme_type.value,
                'author': self.metadata.author,
                'version': self.metadata.version,
                'created_at': self.metadata.created_at.isoformat() if self.metadata.created_at else None,
                'tags': list(self.metadata.tags)
            },
            'token_overrides': self.token_overrides
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ThemeDefinition':
        """Create theme from dictionary representation"""
        metadata_data = data.get('metadata', {})
        metadata = ThemeMetadata(
            name=data['name'],
            display_name=metadata_data.get('display_name', data['name'].title()),
            description=metadata_data.get('description'),
            theme_type=ThemeType(metadata_data.get('theme_type', 'custom')),
            author=metadata_data.get('author'),
            version=metadata_data.get('version', '1.0.0'),
            created_at=datetime.fromisoformat(metadata_data['created_at']) if metadata_data.get('created_at') else None,
            tags=set(metadata_data.get('tags', []))
        )
        
        return cls(
            name=data['name'],
            token_overrides=data.get('token_overrides', {}),
            metadata=metadata
        )
    
    def __str__(self) -> str:
        return f"ThemeDefinition(name='{self.name}', overrides={len(self.token_overrides)})"
    
    def __repr__(self) -> str:
        return self.__str__()


class ThemeManager:
    """
    Theme management system that coordinates themes with the token system
    
    Manages theme registration, switching, and persistence while working
    with the TokenManager to provide themed token resolution.
    """
    
    def __init__(self, token_manager=None):
        self.token_manager = token_manager
        self._themes: Dict[str, ThemeDefinition] = {}
        self._active_theme: Optional[str] = None
        self._logger = logging.getLogger(__name__)
        
        # Theme persistence settings
        self._persistence_enabled = True
        self._persistence_file = "themes.json"
    
    def register_theme(self, theme: ThemeDefinition) -> bool:
        """
        Register a new theme
        
        Args:
            theme: ThemeDefinition to register
            
        Returns:
            True if registration successful
        """
        try:
            if theme.name in self._themes:
                self._logger.warning(f"Theme '{theme.name}' already exists, overwriting")
            
            self._themes[theme.name] = theme
            self._logger.info(f"Registered theme: {theme.name}")
            
            return True
        except Exception as e:
            self._logger.error(f"Failed to register theme {theme.name}: {e}")
            return False
    
    def unregister_theme(self, theme_name: str) -> bool:
        """Unregister a theme"""
        if theme_name not in self._themes:
            return False
        
        # Can't unregister the active theme
        if theme_name == self._active_theme:
            self._logger.warning(f"Cannot unregister active theme '{theme_name}'")
            return False
        
        del self._themes[theme_name]
        self._logger.info(f"Unregistered theme: {theme_name}")
        return True
    
    def get_theme(self, theme_name: str) -> Optional[ThemeDefinition]:
        """Get a theme by name"""
        return self._themes.get(theme_name)
    
    def get_all_themes(self) -> Dict[str, ThemeDefinition]:
        """Get all registered themes"""
        return self._themes.copy()
    
    def get_theme_names(self) -> List[str]:
        """Get list of all theme names"""
        return list(self._themes.keys())
    
    def get_active_theme(self) -> Optional[ThemeDefinition]:
        """Get the currently active theme"""
        if self._active_theme:
            return self._themes.get(self._active_theme)
        return None
    
    def get_active_theme_name(self) -> Optional[str]:
        """Get the name of the currently active theme"""
        return self._active_theme
    
    def switch_theme(self, theme_name: str) -> bool:
        """
        Switch to a different theme
        
        Args:
            theme_name: Name of theme to switch to
            
        Returns:
            True if switch successful
        """
        if theme_name not in self._themes:
            self._logger.error(f"Theme '{theme_name}' not found")
            return False
        
        old_theme = self._active_theme
        self._active_theme = theme_name
        
        # Apply theme to token manager if available
        if self.token_manager:
            self._apply_theme_to_tokens(theme_name)
        
        self._logger.info(f"Switched theme: {old_theme} → {theme_name}")
        
        # Save theme preference
        if self._persistence_enabled:
            self._save_theme_preference(theme_name)
        
        return True
    
    def get_themed_token_value(self, token_name: str, fallback: Any = None) -> Any:
        """
        Get a token value with current theme applied
        
        Args:
            token_name: Name of token to resolve
            fallback: Fallback value if not found
            
        Returns:
            Themed token value or original token value or fallback
        """
        # Check if current theme has an override
        active_theme = self.get_active_theme()
        if active_theme and active_theme.has_token_override(token_name):
            return active_theme.get_token_value(token_name)
        
        # Fall back to token manager if available
        if self.token_manager:
            try:
                return self.token_manager.resolve_token_value(token_name)
            except Exception:
                pass
        
        return fallback
    
    def create_theme_from_overrides(self, 
                                  name: str,
                                  overrides: Dict[str, Any],
                                  base_theme: Optional[str] = None) -> ThemeDefinition:
        """
        Create a new theme from token overrides
        
        Args:
            name: Name for the new theme
            overrides: Token overrides for the theme
            base_theme: Optional base theme to inherit from
            
        Returns:
            New ThemeDefinition
        """
        final_overrides = {}
        
        # Inherit from base theme if specified
        if base_theme and base_theme in self._themes:
            base = self._themes[base_theme]
            final_overrides.update(base.get_all_overrides())
        
        # Apply new overrides
        final_overrides.update(overrides)
        
        metadata = ThemeMetadata(
            name=name,
            display_name=name.title(),
            theme_type=ThemeType.CUSTOM,
            created_at=datetime.now()
        )
        
        return ThemeDefinition(name, final_overrides, metadata)
    
    def _apply_theme_to_tokens(self, theme_name: str):
        """Apply theme overrides to token manager (internal)"""
        # This would integrate with the token manager to apply overrides
        # For now, we'll log the action
        theme = self._themes.get(theme_name)
        if theme:
            override_count = len(theme.get_all_overrides())
            self._logger.debug(f"Applied theme '{theme_name}' with {override_count} overrides")
    
    def _save_theme_preference(self, theme_name: str):
        """Save theme preference to persistence file (internal)"""
        try:
            preference_data = {
                'active_theme': theme_name,
                'saved_at': datetime.now().isoformat()
            }
            
            # In a real implementation, this would save to a file
            self._logger.debug(f"Saved theme preference: {theme_name}")
        except Exception as e:
            self._logger.error(f"Failed to save theme preference: {e}")
    
    def load_theme_preference(self) -> Optional[str]:
        """Load saved theme preference"""
        try:
            # In a real implementation, this would load from a file
            # For now, return None (no saved preference)
            return None
        except Exception as e:
            self._logger.error(f"Failed to load theme preference: {e}")
            return None
    
    def export_theme(self, theme_name: str, file_path: str) -> bool:
        """Export a theme to file"""
        theme = self.get_theme(theme_name)
        if not theme:
            return False
        
        try:
            theme_data = theme.to_dict()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(theme_data, f, indent=2, ensure_ascii=False)
            
            self._logger.info(f"Exported theme '{theme_name}' to {file_path}")
            return True
        except Exception as e:
            self._logger.error(f"Failed to export theme: {e}")
            return False
    
    def import_theme(self, file_path: str) -> Optional[str]:
        """Import a theme from file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                theme_data = json.load(f)
            
            theme = ThemeDefinition.from_dict(theme_data)
            
            if self.register_theme(theme):
                self._logger.info(f"Imported theme '{theme.name}' from {file_path}")
                return theme.name
            
        except Exception as e:
            self._logger.error(f"Failed to import theme: {e}")
        
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get theme system statistics"""
        return {
            'total_themes': len(self._themes),
            'active_theme': self._active_theme,
            'theme_types': self._get_theme_type_counts(),
            'persistence_enabled': self._persistence_enabled
        }
    
    def _get_theme_type_counts(self) -> Dict[str, int]:
        """Get count of themes by type"""
        counts = {theme_type.value: 0 for theme_type in ThemeType}
        
        for theme in self._themes.values():
            theme_type = theme.metadata.theme_type.value
            counts[theme_type] = counts.get(theme_type, 0) + 1
        
        return counts 