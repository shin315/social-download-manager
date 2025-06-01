"""
Style Manager

Central manager for coordinating design tokens with component styling.
Provides a bridge between the token system and PyQt stylesheets.
"""

import logging
from typing import Dict, Any, Optional
from ..tokens import TokenManager, initialize_design_system
from ..themes import ThemeManager, initialize_preset_themes


class StyleManager:
    """
    Central style management system
    
    Coordinates design tokens, themes, and component styling to provide
    consistent, maintainable styles across the application.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize token and theme systems
        self.token_registry = initialize_design_system()
        self.token_manager = self.token_registry.token_manager
        
        self.theme_manager = ThemeManager(self.token_manager)
        initialize_preset_themes(self.theme_manager)
        
        # Set default theme
        self.theme_manager.switch_theme('light')
        
        self._style_cache = {}
    
    def get_token_value(self, token_name: str, fallback: Any = None) -> Any:
        """
        Get a token value with current theme applied
        
        Args:
            token_name: Name of the token to resolve
            fallback: Fallback value if token not found
            
        Returns:
            Themed token value or fallback
        """
        return self.theme_manager.get_themed_token_value(token_name, fallback)
    
    def switch_theme(self, theme_name: str) -> bool:
        """
        Switch to a different theme and clear style cache
        
        Args:
            theme_name: Name of theme to switch to
            
        Returns:
            True if switch successful
        """
        success = self.theme_manager.switch_theme(theme_name)
        if success:
            self._style_cache.clear()  # Clear cache when theme changes
            self.logger.info(f"Switched to theme '{theme_name}' and cleared style cache")
        return success
    
    def get_current_theme_name(self) -> Optional[str]:
        """Get the name of the currently active theme"""
        return self.theme_manager.get_active_theme_name()
    
    def generate_stylesheet(self, component_type: str, **overrides) -> str:
        """
        Generate a complete stylesheet for a component using design tokens
        
        Args:
            component_type: Type of component (button, input, table, etc.)
            **overrides: Optional style overrides
            
        Returns:
            Complete CSS stylesheet string
        """
        cache_key = f"{component_type}_{self.get_current_theme_name()}_{hash(str(overrides))}"
        
        if cache_key in self._style_cache:
            return self._style_cache[cache_key]
        
        from .component_styles import ComponentStyler
        styler = ComponentStyler(self)
        
        if hasattr(styler, f"get_{component_type}_styles"):
            method = getattr(styler, f"get_{component_type}_styles")
            stylesheet = method(**overrides)
        else:
            self.logger.warning(f"No style method found for component type: {component_type}")
            stylesheet = ""
        
        self._style_cache[cache_key] = stylesheet
        return stylesheet
    
    def get_component_styles(self, component_names: list, **overrides) -> Dict[str, str]:
        """
        Get stylesheets for multiple components
        
        Args:
            component_names: List of component types
            **overrides: Optional style overrides
            
        Returns:
            Dict mapping component names to their stylesheets
        """
        styles = {}
        for component in component_names:
            styles[component] = self.generate_stylesheet(component, **overrides)
        return styles
    
    def create_color_palette_css(self) -> str:
        """Create CSS custom properties from color tokens"""
        css_vars = []
        
        # Get all color tokens
        color_tokens = self.token_manager.get_tokens_by_name_pattern("color-*")
        
        for token in color_tokens:
            themed_value = self.get_token_value(token.name, token.value)
            css_var = f"  --{token.name}: {themed_value};"
            css_vars.append(css_var)
        
        if css_vars:
            return ":root {\n" + "\n".join(css_vars) + "\n}"
        return ""
    
    def resolve_token_reference(self, value: Any) -> Any:
        """
        Resolve a token reference to its actual value
        
        Args:
            value: Value that might contain token references like {token-name}
            
        Returns:
            Resolved value with token references replaced
        """
        if isinstance(value, str) and value.startswith('{') and value.endswith('}'):
            token_name = value[1:-1]  # Remove { and }
            return self.get_token_value(token_name, value)
        return value
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive style system statistics"""
        return {
            'token_system': self.token_registry.get_initialization_stats(),
            'theme_system': self.theme_manager.get_stats(),
            'style_cache_size': len(self._style_cache),
            'current_theme': self.get_current_theme_name()
        }
    
    def clear_cache(self):
        """Clear the style cache"""
        self._style_cache.clear()
        self.logger.info("Style cache cleared")
    
    def validate_system(self) -> Dict[str, Any]:
        """Validate the entire styling system"""
        validation_results = {
            'token_validation': self.token_registry.validate_token_system(),
            'theme_validation': {
                'themes_loaded': len(self.theme_manager.get_all_themes()),
                'active_theme': self.get_current_theme_name(),
                'has_active_theme': self.get_current_theme_name() is not None
            }
        }
        
        return validation_results 