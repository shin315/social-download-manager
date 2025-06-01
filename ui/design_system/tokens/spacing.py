"""
Spacing Tokens

Spacing-specific design token implementation for margins, padding,
gaps, and other spatial measurements.
"""

import re
from typing import Any, Dict, Optional, Union
from .base import DesignToken, TokenCategory, TokenType, TokenMetadata, TokenReference


class SpacingToken(DesignToken):
    """Design token for spacing values"""
    
    # Spacing value patterns (px, rem, em, %, etc.)
    SPACING_PATTERN = re.compile(r'^-?\d*\.?\d+(px|rem|em|%|vh|vw|pt|pc|in|cm|mm|ex|ch)$')
    
    def __init__(self, name: str, value: Union[str, int, float, TokenReference], 
                 metadata: Optional[TokenMetadata] = None):
        if metadata is None:
            metadata = TokenMetadata()
        metadata.category = TokenCategory.SPACING
        
        super().__init__(name, value, metadata)
    
    def _validate_value(self, value: Any) -> bool:
        """Validate spacing value format"""
        if isinstance(value, TokenReference):
            return True
        
        # Allow numeric values (will be converted to px)
        if isinstance(value, (int, float)):
            return value >= 0  # Only positive spacing values
        
        if isinstance(value, str):
            value = value.strip()
            # Check CSS unit patterns
            return bool(self.SPACING_PATTERN.match(value))
        
        return False
    
    def resolve_value(self, token_registry: Dict[str, DesignToken]) -> str:
        """Resolve spacing value, handling references"""
        if isinstance(self._value, TokenReference):
            ref_token = token_registry.get(self._value.token_name)
            if ref_token:
                return ref_token.resolve_value(token_registry)
            else:
                raise ValueError(f"Referenced token not found: {self._value.token_name}")
        
        # Convert numeric values to px
        if isinstance(self._value, (int, float)):
            return f"{self._value}px"
        
        return str(self._value)
    
    def to_css_value(self, token_registry: Optional[Dict[str, DesignToken]] = None) -> str:
        """Convert to CSS spacing value"""
        if token_registry:
            return self.resolve_value(token_registry)
        
        if isinstance(self._value, (int, float)):
            return f"{self._value}px"
        
        return str(self._value)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SpacingToken':
        """Create SpacingToken from dictionary"""
        metadata = TokenMetadata(
            description=data.get('description'),
            category=TokenCategory.SPACING,
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