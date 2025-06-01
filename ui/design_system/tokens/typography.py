"""
Typography Tokens

Typography-specific design token implementation for font sizes,
weights, families, line heights, and other text styling.
"""

import re
from typing import Any, Dict, Optional, Union
from .base import DesignToken, TokenCategory, TokenType, TokenMetadata, TokenReference


class TypographyToken(DesignToken):
    """Design token for typography values"""
    
    # Font size patterns
    FONT_SIZE_PATTERN = re.compile(r'^-?\d*\.?\d+(px|rem|em|%|pt|pc|in|cm|mm|ex|ch)$')
    
    # Font weight values
    FONT_WEIGHTS = {
        'thin': 100, 'extralight': 200, 'light': 300, 'normal': 400,
        'medium': 500, 'semibold': 600, 'bold': 700, 'extrabold': 800,
        'black': 900, 'lighter': 'lighter', 'bolder': 'bolder'
    }
    
    def __init__(self, name: str, value: Union[str, int, float, TokenReference], 
                 metadata: Optional[TokenMetadata] = None):
        if metadata is None:
            metadata = TokenMetadata()
        metadata.category = TokenCategory.TYPOGRAPHY
        
        super().__init__(name, value, metadata)
    
    def _validate_value(self, value: Any) -> bool:
        """Validate typography value format"""
        if isinstance(value, TokenReference):
            return True
        
        # Font size (numeric or with units)
        if isinstance(value, (int, float)):
            return value > 0
        
        if isinstance(value, str):
            value = value.strip().lower()
            
            # Check font size patterns
            if self.FONT_SIZE_PATTERN.match(value):
                return True
            
            # Check font weights
            if value in self.FONT_WEIGHTS or value.isdigit():
                return True
            
            # Font family names (allow most strings)
            return True
        
        return False
    
    def resolve_value(self, token_registry: Dict[str, DesignToken]) -> str:
        """Resolve typography value, handling references"""
        if isinstance(self._value, TokenReference):
            ref_token = token_registry.get(self._value.token_name)
            if ref_token:
                return ref_token.resolve_value(token_registry)
            else:
                raise ValueError(f"Referenced token not found: {self._value.token_name}")
        
        # Convert numeric font sizes to pt (for PyQt)
        if isinstance(self._value, (int, float)):
            return f"{self._value}pt"
        
        return str(self._value)
    
    def to_css_value(self, token_registry: Optional[Dict[str, DesignToken]] = None) -> str:
        """Convert to CSS typography value"""
        if token_registry:
            return self.resolve_value(token_registry)
        
        if isinstance(self._value, (int, float)):
            return f"{self._value}pt"
        
        return str(self._value)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TypographyToken':
        """Create TypographyToken from dictionary"""
        metadata = TokenMetadata(
            description=data.get('description'),
            category=TokenCategory.TYPOGRAPHY,
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