"""
Sizing Tokens

Sizing-specific design token implementation for dimensions,
widths, heights, and other size-related measurements.
"""

import re
from typing import Any, Dict, Optional, Union
from .base import DesignToken, TokenCategory, TokenType, TokenMetadata, TokenReference


class SizingToken(DesignToken):
    """Design token for sizing values"""
    
    # Sizing value patterns
    SIZING_PATTERN = re.compile(r'^-?\d*\.?\d+(px|rem|em|%|vh|vw|pt|pc|in|cm|mm|ex|ch)$')
    
    def __init__(self, name: str, value: Union[str, int, float, TokenReference], 
                 metadata: Optional[TokenMetadata] = None):
        if metadata is None:
            metadata = TokenMetadata()
        metadata.category = TokenCategory.SIZING
        
        super().__init__(name, value, metadata)
    
    def _validate_value(self, value: Any) -> bool:
        """Validate sizing value format"""
        if isinstance(value, TokenReference):
            return True
        
        # Allow numeric values (will be converted to px)
        if isinstance(value, (int, float)):
            return value >= 0  # Only positive sizing values
        
        if isinstance(value, str):
            value = value.strip().lower()
            
            # Check CSS unit patterns
            if self.SIZING_PATTERN.match(value):
                return True
            
            # Allow keywords like 'auto', 'inherit', 'initial'
            if value in {'auto', 'inherit', 'initial', 'unset', 'min-content', 'max-content'}:
                return True
        
        return False
    
    def resolve_value(self, token_registry: Dict[str, DesignToken]) -> str:
        """Resolve sizing value, handling references"""
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
        """Convert to CSS sizing value"""
        if token_registry:
            return self.resolve_value(token_registry)
        
        if isinstance(self._value, (int, float)):
            return f"{self._value}px"
        
        return str(self._value)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SizingToken':
        """Create SizingToken from dictionary"""
        metadata = TokenMetadata(
            description=data.get('description'),
            category=TokenCategory.SIZING,
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