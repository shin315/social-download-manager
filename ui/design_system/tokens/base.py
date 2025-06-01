"""
Base Design Token System

Foundation classes and interfaces for the design token architecture.
Provides the core abstractions that all token types inherit from.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Set
from dataclasses import dataclass, field
import json
import re
from datetime import datetime


class TokenCategory(Enum):
    """Categories of design tokens"""
    COLOR = "color"
    SPACING = "spacing"
    TYPOGRAPHY = "typography"
    SIZING = "sizing"
    ANIMATION = "animation"
    BORDER = "border"
    SHADOW = "shadow"
    Z_INDEX = "z-index"


class TokenType(Enum):
    """Token type classification"""
    PRIMITIVE = "primitive"    # Base values (hex colors, px values)
    SEMANTIC = "semantic"      # Contextual references (primary-color, button-padding)
    COMPONENT = "component"    # Component-specific tokens (table-border, input-background)


@dataclass
class TokenMetadata:
    """Metadata for design tokens"""
    description: Optional[str] = None
    category: Optional[TokenCategory] = None
    token_type: Optional[TokenType] = None
    deprecated: bool = False
    deprecation_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    source: Optional[str] = None  # Source file or system
    tags: Set[str] = field(default_factory=set)
    aliases: Set[str] = field(default_factory=set)


class TokenValidator:
    """Validates token values and names"""
    
    # Token naming convention: category-context-property-modifier-state
    # Examples: color-button-background-primary-hover, spacing-component-padding-large
    NAMING_PATTERN = re.compile(r'^[a-z]+(-[a-z0-9]+)*$')
    
    @classmethod
    def validate_name(cls, name: str) -> bool:
        """Validate token name follows naming convention"""
        if not name or not isinstance(name, str):
            return False
        return bool(cls.NAMING_PATTERN.match(name.lower()))
    
    @classmethod
    def validate_reference(cls, reference: str, available_tokens: Set[str]) -> bool:
        """Validate token reference exists"""
        if not reference.startswith('{') or not reference.endswith('}'):
            return False
        
        token_name = reference[1:-1]  # Remove { }
        return token_name in available_tokens
    
    @classmethod
    def suggest_name(cls, category: TokenCategory, context: str, property: str, 
                    modifier: Optional[str] = None, state: Optional[str] = None) -> str:
        """Suggest a token name following conventions"""
        parts = [category.value, context, property]
        if modifier:
            parts.append(modifier)
        if state:
            parts.append(state)
        return '-'.join(parts)


class DesignToken(ABC):
    """
    Abstract base class for all design tokens
    
    Design tokens are the visual design atoms of the design system.
    They store visual design attributes and serve as a single source of truth.
    """
    
    def __init__(self, 
                 name: str,
                 value: Any,
                 metadata: Optional[TokenMetadata] = None):
        if not TokenValidator.validate_name(name):
            raise ValueError(f"Invalid token name: {name}. Must follow naming convention.")
        
        self._name = name
        self._value = value
        self._metadata = metadata or TokenMetadata()
        self._references: Set[str] = set()
        self._dependents: Set[str] = set()
        
        # Auto-populate metadata if not provided
        if not self._metadata.created_at:
            self._metadata.created_at = datetime.now()
        self._metadata.updated_at = datetime.now()
    
    @property
    def name(self) -> str:
        """Token name"""
        return self._name
    
    @property
    def value(self) -> Any:
        """Token value"""
        return self._value
    
    @value.setter
    def value(self, new_value: Any):
        """Set token value with validation"""
        self._validate_value(new_value)
        self._value = new_value
        self._metadata.updated_at = datetime.now()
    
    @property
    def metadata(self) -> TokenMetadata:
        """Token metadata"""
        return self._metadata
    
    @property
    def references(self) -> Set[str]:
        """Tokens this token references"""
        return self._references.copy()
    
    @property
    def dependents(self) -> Set[str]:
        """Tokens that reference this token"""
        return self._dependents.copy()
    
    @abstractmethod
    def _validate_value(self, value: Any) -> bool:
        """Validate the token value is appropriate for this token type"""
        pass
    
    @abstractmethod
    def resolve_value(self, token_registry: Dict[str, 'DesignToken']) -> Any:
        """Resolve the final value, handling references to other tokens"""
        pass
    
    @abstractmethod
    def to_css_value(self, token_registry: Optional[Dict[str, 'DesignToken']] = None) -> str:
        """Convert token to CSS-compatible value"""
        pass
    
    def add_reference(self, token_name: str):
        """Add a reference to another token"""
        self._references.add(token_name)
    
    def remove_reference(self, token_name: str):
        """Remove a reference to another token"""
        self._references.discard(token_name)
    
    def add_dependent(self, token_name: str):
        """Add a token that depends on this one"""
        self._dependents.add(token_name)
    
    def remove_dependent(self, token_name: str):
        """Remove a dependent token"""
        self._dependents.discard(token_name)
    
    def is_primitive(self) -> bool:
        """Check if this is a primitive token"""
        return self._metadata.token_type == TokenType.PRIMITIVE
    
    def is_semantic(self) -> bool:
        """Check if this is a semantic token"""
        return self._metadata.token_type == TokenType.SEMANTIC
    
    def is_component(self) -> bool:
        """Check if this is a component token"""
        return self._metadata.token_type == TokenType.COMPONENT
    
    def is_deprecated(self) -> bool:
        """Check if this token is deprecated"""
        return self._metadata.deprecated
    
    def deprecate(self, message: str = "This token has been deprecated"):
        """Mark token as deprecated"""
        self._metadata.deprecated = True
        self._metadata.deprecation_message = message
        self._metadata.updated_at = datetime.now()
    
    def add_alias(self, alias: str):
        """Add an alias for this token"""
        if TokenValidator.validate_name(alias):
            self._metadata.aliases.add(alias)
    
    def add_tag(self, tag: str):
        """Add a tag to this token"""
        self._metadata.tags.add(tag)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert token to dictionary representation"""
        return {
            'name': self._name,
            'value': self._value,
            'category': self._metadata.category.value if self._metadata.category else None,
            'type': self._metadata.token_type.value if self._metadata.token_type else None,
            'description': self._metadata.description,
            'deprecated': self._metadata.deprecated,
            'deprecation_message': self._metadata.deprecation_message,
            'created_at': self._metadata.created_at.isoformat() if self._metadata.created_at else None,
            'updated_at': self._metadata.updated_at.isoformat() if self._metadata.updated_at else None,
            'source': self._metadata.source,
            'tags': list(self._metadata.tags),
            'aliases': list(self._metadata.aliases),
            'references': list(self._references),
            'dependents': list(self._dependents)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DesignToken':
        """Create token from dictionary representation"""
        metadata = TokenMetadata(
            description=data.get('description'),
            category=TokenCategory(data['category']) if data.get('category') else None,
            token_type=TokenType(data['type']) if data.get('type') else None,
            deprecated=data.get('deprecated', False),
            deprecation_message=data.get('deprecation_message'),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None,
            source=data.get('source'),
            tags=set(data.get('tags', [])),
            aliases=set(data.get('aliases', []))
        )
        
        # This will be implemented by subclasses
        raise NotImplementedError("Subclasses must implement from_dict")
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name='{self._name}', value='{self._value}')"
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, DesignToken):
            return False
        return self._name == other._name and self._value == other._value
    
    def __hash__(self) -> str:
        return hash((self._name, str(self._value)))


class TokenReference:
    """Represents a reference to another token"""
    
    def __init__(self, token_name: str):
        self.token_name = token_name
    
    def __str__(self) -> str:
        return f"{{{self.token_name}}}"
    
    def __repr__(self) -> str:
        return f"TokenReference('{self.token_name}')"
    
    @classmethod
    def parse(cls, value: str) -> Optional['TokenReference']:
        """Parse a string value and return TokenReference if it's a reference"""
        if isinstance(value, str) and value.startswith('{') and value.endswith('}'):
            token_name = value[1:-1]
            if TokenValidator.validate_name(token_name):
                return cls(token_name)
        return None
    
    @classmethod
    def is_reference(cls, value: Any) -> bool:
        """Check if a value is a token reference"""
        return cls.parse(str(value)) is not None 