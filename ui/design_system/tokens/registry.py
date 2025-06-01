"""
Token Registry

Central registration system for loading primitive tokens into the TokenManager.
Provides initialization and management of the token system.
"""

import logging
from typing import Dict, Any, Set
from .manager import TokenManager
from .primitives import PrimitiveTokens
from .semantic import SemanticTokens


class TokenRegistry:
    """
    Token registration and initialization system
    
    Handles loading primitive tokens into the TokenManager and provides
    initialization utilities for the design system.
    """
    
    def __init__(self, token_manager: TokenManager):
        self.token_manager = token_manager
        self.logger = logging.getLogger(__name__)
        self._primitives_initialized = False
        self._semantics_initialized = False
        
    def initialize_primitive_tokens(self) -> Dict[str, Any]:
        """
        Initialize all primitive design tokens
        
        Returns:
            Dict with statistics about loaded tokens
        """
        if self._primitives_initialized:
            self.logger.warning("Primitive tokens already initialized")
            return self.get_initialization_stats()
        
        try:
            # Create all primitive tokens
            primitive_tokens = PrimitiveTokens.create_all_primitives()
            
            # Register tokens with the manager
            registered_count = 0
            failed_registrations = []
            
            for token_name, token in primitive_tokens.items():
                try:
                    self.token_manager.register_token(token)
                    registered_count += 1
                except Exception as e:
                    failed_registrations.append((token_name, str(e)))
                    self.logger.error(f"Failed to register token {token_name}: {e}")
            
            self._primitives_initialized = True
            
            stats = {
                'total_tokens': len(primitive_tokens),
                'registered': registered_count,
                'failed': len(failed_registrations),
                'failed_tokens': failed_registrations,
                'manager_stats': self.token_manager.get_stats()
            }
            
            self.logger.info(f"Initialized primitive tokens: {registered_count}/{len(primitive_tokens)} registered")
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to initialize primitive tokens: {e}")
            raise
    
    def initialize_semantic_tokens(self) -> Dict[str, Any]:
        """
        Initialize all semantic design tokens
        
        Note: Requires primitive tokens to be initialized first
        
        Returns:
            Dict with statistics about loaded tokens
        """
        if not self._primitives_initialized:
            raise RuntimeError("Primitive tokens must be initialized before semantic tokens")
        
        if self._semantics_initialized:
            self.logger.warning("Semantic tokens already initialized")
            return self.get_initialization_stats()
        
        try:
            # Create all semantic tokens
            semantic_tokens = SemanticTokens.create_all_semantic_tokens()
            
            # Register tokens with the manager
            registered_count = 0
            failed_registrations = []
            
            for token_name, token in semantic_tokens.items():
                try:
                    # Update token references in manager
                    for ref_name in token.references:
                        ref_token = self.token_manager.get_token(ref_name)
                        if ref_token:
                            ref_token.add_dependent(token.name)
                    
                    self.token_manager.register_token(token)
                    registered_count += 1
                except Exception as e:
                    failed_registrations.append((token_name, str(e)))
                    self.logger.error(f"Failed to register semantic token {token_name}: {e}")
            
            self._semantics_initialized = True
            
            stats = {
                'total_tokens': len(semantic_tokens),
                'registered': registered_count,
                'failed': len(failed_registrations),
                'failed_tokens': failed_registrations,
                'manager_stats': self.token_manager.get_stats()
            }
            
            self.logger.info(f"Initialized semantic tokens: {registered_count}/{len(semantic_tokens)} registered")
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to initialize semantic tokens: {e}")
            raise
    
    def initialize_all_tokens(self) -> Dict[str, Any]:
        """
        Initialize both primitive and semantic tokens
        
        Returns:
            Combined statistics
        """
        primitive_stats = self.initialize_primitive_tokens()
        semantic_stats = self.initialize_semantic_tokens()
        
        combined_stats = {
            'primitive_tokens': primitive_stats,
            'semantic_tokens': semantic_stats,
            'total_registered': primitive_stats['registered'] + semantic_stats['registered'],
            'manager_stats': self.token_manager.get_stats()
        }
        
        self.logger.info(f"Initialized complete token system: {combined_stats['total_registered']} tokens total")
        
        return combined_stats
    
    def get_initialization_stats(self) -> Dict[str, Any]:
        """Get current initialization statistics"""
        return {
            'primitives_initialized': self._primitives_initialized,
            'semantics_initialized': self._semantics_initialized,
            'manager_stats': self.token_manager.get_stats()
        }
    
    def validate_token_system(self) -> Dict[str, Any]:
        """
        Validate the entire token system
        
        Returns:
            Validation results including errors and warnings
        """
        validation_results = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'token_errors': {},
            'dependency_cycles': []
        }
        
        try:
            # Validate all tokens
            token_errors = self.token_manager.validate_all_tokens()
            if token_errors:
                validation_results['token_errors'] = token_errors
                validation_results['is_valid'] = False
                validation_results['errors'].append(f"Token validation failed for {len(token_errors)} tokens")
            
            # Check for circular dependencies
            cycles = self.token_manager.detect_circular_dependencies()
            if cycles:
                validation_results['dependency_cycles'] = cycles
                validation_results['is_valid'] = False
                validation_results['errors'].append(f"Found {len(cycles)} circular dependencies")
            
            # Check for missing references
            missing_refs = self._check_missing_references()
            if missing_refs:
                validation_results['warnings'].append(f"Found {len(missing_refs)} missing token references")
            
            self.logger.info(f"Token system validation completed: {'PASSED' if validation_results['is_valid'] else 'FAILED'}")
            
        except Exception as e:
            validation_results['is_valid'] = False
            validation_results['errors'].append(f"Validation error: {e}")
            self.logger.error(f"Token system validation failed: {e}")
        
        return validation_results
    
    def _check_missing_references(self) -> Set[str]:
        """Check for missing token references"""
        missing_refs = set()
        all_tokens = self.token_manager.get_all_tokens()
        
        for token in all_tokens.values():
            for ref_name in token.references:
                if ref_name not in all_tokens:
                    missing_refs.add(ref_name)
        
        return missing_refs
    
    def get_tokens_by_category_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get summary of tokens organized by category"""
        from .base import TokenCategory
        
        summary = {}
        
        for category in TokenCategory:
            tokens = self.token_manager.get_tokens_by_category(category)
            
            summary[category.value] = {
                'count': len(tokens),
                'tokens': [token.name for token in tokens],
                'primitive_count': len([t for t in tokens if t.is_primitive()]),
                'semantic_count': len([t for t in tokens if t.is_semantic()]),
                'component_count': len([t for t in tokens if t.is_component()])
            }
        
        return summary
    
    def export_token_documentation(self, format: str = 'dict') -> Dict[str, Any]:
        """
        Export comprehensive token documentation
        
        Args:
            format: Export format ('dict', 'json')
            
        Returns:
            Documentation data
        """
        documentation = {
            'system_info': {
                'primitives_initialized': self._primitives_initialized,
                'semantics_initialized': self._semantics_initialized,
                'total_tokens': len(self.token_manager.get_all_tokens()),
                'version': '1.0.0'
            },
            'categories': self.get_tokens_by_category_summary(),
            'tokens': {}
        }
        
        # Add detailed token information
        all_tokens = self.token_manager.get_all_tokens()
        for token_name, token in all_tokens.items():
            documentation['tokens'][token_name] = {
                'name': token.name,
                'value': str(token.value),
                'category': token.metadata.category.value if token.metadata.category else None,
                'type': token.metadata.token_type.value if token.metadata.token_type else None,
                'description': token.metadata.description,
                'tags': list(token.metadata.tags),
                'aliases': list(token.metadata.aliases),
                'deprecated': token.metadata.deprecated,
                'css_value': token.to_css_value(),
                'references': list(token.references),
                'dependents': list(token.dependents)
            }
        
        return documentation


def initialize_design_system(token_manager: TokenManager = None) -> TokenRegistry:
    """
    Initialize the complete design system with primitive and semantic tokens
    
    Args:
        token_manager: Optional TokenManager instance
        
    Returns:
        Configured TokenRegistry
    """
    if token_manager is None:
        token_manager = TokenManager()
    
    registry = TokenRegistry(token_manager)
    registry.initialize_all_tokens()
    
    return registry 