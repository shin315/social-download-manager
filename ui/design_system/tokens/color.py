"""
Color Tokens

Color-specific design token implementation with validation,
conversion utilities, and theme support.
"""

import re
from typing import Any, Dict, Optional, Union
from .base import DesignToken, TokenCategory, TokenType, TokenMetadata, TokenReference


class ColorToken(DesignToken):
    """Design token for color values"""
    
    # Color validation patterns
    HEX_PATTERN = re.compile(r'^#[0-9A-Fa-f]{3,8}$')
    RGB_PATTERN = re.compile(r'^rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)$')
    RGBA_PATTERN = re.compile(r'^rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*[\d.]+\s*\)$')
    HSL_PATTERN = re.compile(r'^hsl\(\s*\d+\s*,\s*\d+%\s*,\s*\d+%\s*\)$')
    HSLA_PATTERN = re.compile(r'^hsla\(\s*\d+\s*,\s*\d+%\s*,\s*\d+%\s*,\s*[\d.]+\s*\)$')
    
    def __init__(self, name: str, value: Union[str, TokenReference], 
                 metadata: Optional[TokenMetadata] = None):
        if metadata is None:
            metadata = TokenMetadata()
        metadata.category = TokenCategory.COLOR
        
        super().__init__(name, value, metadata)
    
    def _validate_value(self, value: Any) -> bool:
        """Validate color value format"""
        if isinstance(value, TokenReference):
            return True  # References are validated elsewhere
        
        if not isinstance(value, str):
            return False
        
        value = value.strip()
        
        # Check various color formats
        return (self.HEX_PATTERN.match(value) or
                self.RGB_PATTERN.match(value) or  
                self.RGBA_PATTERN.match(value) or
                self.HSL_PATTERN.match(value) or
                self.HSLA_PATTERN.match(value) or
                value.lower() in self._get_named_colors())
    
    def resolve_value(self, token_registry: Dict[str, DesignToken]) -> str:
        """Resolve color value, handling references"""
        if isinstance(self._value, TokenReference):
            ref_token = token_registry.get(self._value.token_name)
            if ref_token:
                return ref_token.resolve_value(token_registry)
            else:
                raise ValueError(f"Referenced token not found: {self._value.token_name}")
        
        return str(self._value)
    
    def to_css_value(self, token_registry: Optional[Dict[str, DesignToken]] = None) -> str:
        """Convert to CSS color value"""
        if token_registry:
            return self.resolve_value(token_registry)
        return str(self._value)
    
    def _get_named_colors(self) -> set:
        """Get set of valid CSS named colors"""
        return {
            'transparent', 'black', 'white', 'red', 'green', 'blue',
            'cyan', 'magenta', 'yellow', 'gray', 'grey', 'maroon',
            'navy', 'olive', 'lime', 'aqua', 'fuchsia', 'silver',
            'teal', 'purple', 'orange', 'pink', 'brown', 'gold'
            # Add more as needed
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ColorToken':
        """Create ColorToken from dictionary"""
        metadata = TokenMetadata(
            description=data.get('description'),
            category=TokenCategory.COLOR,
            token_type=TokenType(data['type']) if data.get('type') else None,
            deprecated=data.get('deprecated', False),
            deprecation_message=data.get('deprecation_message'),
            source=data.get('source'),
            tags=set(data.get('tags', [])),
            aliases=set(data.get('aliases', []))
        )
        
        value = data['value']
        if isinstance(value, str) and value.startswith('{') and value.endswith('}'):
            value = TokenReference(value[1:-1])
        
        return cls(data['name'], value, metadata) 