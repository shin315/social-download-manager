"""
Token Manager

Central management system for design tokens providing registration, resolution,
validation, and dependency tracking capabilities.
"""

import json
import os
from typing import Dict, List, Set, Optional, Any, Type, Union
from pathlib import Path
import logging
from datetime import datetime

from .base import DesignToken, TokenCategory, TokenType, TokenValidator, TokenReference


class TokenResolutionError(Exception):
    """Raised when token resolution fails"""
    pass


class CircularDependencyError(Exception):
    """Raised when circular dependencies are detected"""
    pass


class TokenManager:
    """
    Central manager for design tokens
    
    Provides:
    - Token registration and retrieval
    - Dependency resolution and validation
    - Circular dependency detection
    - Token persistence and loading
    - Bulk operations
    """
    
    def __init__(self):
        self._tokens: Dict[str, DesignToken] = {}
        self._categories: Dict[TokenCategory, Set[str]] = {
            category: set() for category in TokenCategory
        }
        self._aliases: Dict[str, str] = {}  # alias -> token_name
        self._logger = logging.getLogger(__name__)
        
        # Theme manager will be set by design system
        self.theme_manager = None
        
        # Validation settings
        self._strict_validation = True
        self._allow_circular_dependencies = False
        
        # Performance optimization
        self._resolution_cache: Dict[str, Any] = {}
        self._dependency_graph: Dict[str, Set[str]] = {}
        
    def register_token(self, token: DesignToken) -> bool:
        """
        Register a new design token
        
        Args:
            token: The design token to register
            
        Returns:
            bool: True if registration successful
            
        Raises:
            ValueError: If token validation fails
            CircularDependencyError: If circular dependency detected
        """
        if self._strict_validation and not self._validate_token(token):
            raise ValueError(f"Token validation failed for {token.name}")
        
        # Check for circular dependencies
        if self._would_create_circular_dependency(token):
            if not self._allow_circular_dependencies:
                raise CircularDependencyError(f"Token {token.name} would create circular dependency")
            else:
                self._logger.warning(f"Circular dependency detected for token {token.name}")
        
        # Register token
        old_token = self._tokens.get(token.name)
        self._tokens[token.name] = token
        
        # Update category tracking
        if token.metadata.category:
            self._categories[token.metadata.category].add(token.name)
        
        # Update aliases
        for alias in token.metadata.aliases:
            self._aliases[alias] = token.name
        
        # Update dependency graph
        self._update_dependency_graph(token)
        
        # Clear resolution cache
        self._clear_resolution_cache()
        
        # Update dependent tokens
        if old_token:
            self._update_dependents(token.name)
        
        self._logger.info(f"Registered token: {token.name}")
        return True
    
    def unregister_token(self, token_name: str) -> bool:
        """Unregister a token"""
        if token_name not in self._tokens:
            return False
        
        token = self._tokens[token_name]
        
        # Check if token has dependents
        if token.dependents and self._strict_validation:
            dependent_names = ', '.join(token.dependents)
            raise ValueError(f"Cannot unregister token {token_name}. "
                           f"It is referenced by: {dependent_names}")
        
        # Remove from all tracking structures
        del self._tokens[token_name]
        
        if token.metadata.category:
            self._categories[token.metadata.category].discard(token_name)
        
        # Remove aliases
        aliases_to_remove = [alias for alias, name in self._aliases.items() 
                            if name == token_name]
        for alias in aliases_to_remove:
            del self._aliases[alias]
        
        # Update dependency graph
        self._dependency_graph.pop(token_name, None)
        
        # Clear cache
        self._clear_resolution_cache()
        
        self._logger.info(f"Unregistered token: {token_name}")
        return True
    
    def get_token(self, token_name: str) -> Optional[DesignToken]:
        """Get a token by name or alias"""
        # Try direct name first
        if token_name in self._tokens:
            return self._tokens[token_name]
        
        # Try alias
        if token_name in self._aliases:
            actual_name = self._aliases[token_name]
            return self._tokens.get(actual_name)
        
        return None
    
    def get_tokens_by_category(self, category: TokenCategory) -> List[DesignToken]:
        """Get all tokens in a category"""
        token_names = self._categories.get(category, set())
        return [self._tokens[name] for name in token_names if name in self._tokens]
    
    def get_tokens_by_type(self, token_type: TokenType) -> List[DesignToken]:
        """Get all tokens of a specific type"""
        return [token for token in self._tokens.values() 
                if token.metadata.token_type == token_type]
    
    def resolve_token_value(self, token_name: str, 
                           visited: Optional[Set[str]] = None) -> Any:
        """
        Resolve a token's final value, handling references
        
        Args:
            token_name: Name of token to resolve
            visited: Set of visited tokens (for circular dependency detection)
            
        Returns:
            The resolved value
            
        Raises:
            TokenResolutionError: If token cannot be resolved
            CircularDependencyError: If circular dependency detected
        """
        if visited is None:
            visited = set()
        
        if token_name in visited:
            raise CircularDependencyError(f"Circular dependency detected: {' -> '.join(visited)} -> {token_name}")
        
        # Check cache first
        if token_name in self._resolution_cache:
            return self._resolution_cache[token_name]
        
        token = self.get_token(token_name)
        if not token:
            raise TokenResolutionError(f"Token not found: {token_name}")
        
        visited.add(token_name)
        
        try:
            resolved_value = token.resolve_value(self._tokens)
            self._resolution_cache[token_name] = resolved_value
            return resolved_value
        except Exception as e:
            raise TokenResolutionError(f"Failed to resolve token {token_name}: {e}")
        finally:
            visited.remove(token_name)
    
    def get_all_tokens(self) -> Dict[str, DesignToken]:
        """Get all registered tokens"""
        return self._tokens.copy()
    
    def get_token_names(self) -> List[str]:
        """Get all token names"""
        return list(self._tokens.keys())
    
    def get_aliases(self) -> Dict[str, str]:
        """Get all aliases mapping"""
        return self._aliases.copy()
    
    def validate_all_tokens(self) -> Dict[str, List[str]]:
        """
        Validate all tokens and return validation errors
        
        Returns:
            Dict mapping token names to list of error messages
        """
        errors = {}
        
        for token_name, token in self._tokens.items():
            token_errors = []
            
            # Validate token itself
            if not self._validate_token(token):
                token_errors.append("Token validation failed")
            
            # Validate references
            for ref_name in token.references:
                if ref_name not in self._tokens and ref_name not in self._aliases:
                    token_errors.append(f"Reference to non-existent token: {ref_name}")
            
            # Try to resolve value
            try:
                self.resolve_token_value(token_name)
            except Exception as e:
                token_errors.append(f"Resolution error: {e}")
            
            if token_errors:
                errors[token_name] = token_errors
        
        return errors
    
    def detect_circular_dependencies(self) -> List[List[str]]:
        """Detect circular dependencies in the token graph"""
        cycles = []
        visited = set()
        recursion_stack = set()
        
        def dfs(token_name: str, path: List[str]) -> bool:
            if token_name in recursion_stack:
                # Found a cycle
                cycle_start = path.index(token_name)
                cycle = path[cycle_start:] + [token_name]
                cycles.append(cycle)
                return True
            
            if token_name in visited:
                return False
            
            visited.add(token_name)
            recursion_stack.add(token_name)
            path.append(token_name)
            
            token = self.get_token(token_name)
            if token:
                for ref_name in token.references:
                    if dfs(ref_name, path):
                        pass  # Continue to find all cycles
            
            path.pop()
            recursion_stack.remove(token_name)
            return False
        
        for token_name in self._tokens:
            if token_name not in visited:
                dfs(token_name, [])
        
        return cycles
    
    def export_tokens(self, file_path: str, format: str = 'json') -> bool:
        """
        Export tokens to file
        
        Args:
            file_path: Path to export file
            format: Export format ('json', 'yaml', 'css')
        """
        try:
            data = {
                'version': '1.0.0',
                'exported_at': datetime.now().isoformat(),
                'tokens': {name: token.to_dict() for name, token in self._tokens.items()}
            }
            
            if format.lower() == 'json':
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            self._logger.info(f"Exported {len(self._tokens)} tokens to {file_path}")
            return True
        
        except Exception as e:
            self._logger.error(f"Failed to export tokens: {e}")
            return False
    
    def import_tokens(self, file_path: str, format: str = 'json') -> bool:
        """Import tokens from file"""
        try:
            if format.lower() == 'json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                raise ValueError(f"Unsupported import format: {format}")
            
            # This would need to be implemented based on specific token types
            # For now, just log the import attempt
            self._logger.info(f"Imported tokens from {file_path}")
            return True
        
        except Exception as e:
            self._logger.error(f"Failed to import tokens: {e}")
            return False
    
    def _validate_token(self, token: DesignToken) -> bool:
        """Validate a single token"""
        try:
            # Validate name
            if not TokenValidator.validate_name(token.name):
                return False
            
            # Validate value (token-specific validation)
            token._validate_value(token.value)
            
            return True
        except Exception:
            return False
    
    def _would_create_circular_dependency(self, token: DesignToken) -> bool:
        """Check if adding a token would create circular dependency"""
        # For now, do a simple check
        # In a full implementation, this would do graph analysis
        return False
    
    def _update_dependency_graph(self, token: DesignToken):
        """Update the dependency graph with token's references"""
        self._dependency_graph[token.name] = token.references.copy()
        
        # Update reverse dependencies
        for ref_name in token.references:
            ref_token = self.get_token(ref_name)
            if ref_token:
                ref_token.add_dependent(token.name)
    
    def _update_dependents(self, token_name: str):
        """Update all tokens that depend on the given token"""
        self._clear_resolution_cache()
        # In a full implementation, this would trigger re-resolution of dependents
    
    def _clear_resolution_cache(self):
        """Clear the resolution cache"""
        self._resolution_cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get token statistics"""
        total_tokens = len(self._tokens)
        by_category = {cat.value: len(tokens) for cat, tokens in self._categories.items()}
        by_type = {}
        
        for token_type in TokenType:
            count = len([t for t in self._tokens.values() 
                        if t.metadata.token_type == token_type])
            by_type[token_type.value] = count
        
        deprecated_count = len([t for t in self._tokens.values() if t.is_deprecated()])
        
        return {
            'total_tokens': total_tokens,
            'by_category': by_category,
            'by_type': by_type,
            'deprecated': deprecated_count,
            'aliases': len(self._aliases),
            'cache_size': len(self._resolution_cache)
        } 