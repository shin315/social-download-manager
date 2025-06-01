"""
Token Validator

Validates design token consistency, usage patterns, and ensures proper
token structure across the design system.
"""

import re
from typing import Dict, List, Any, Set, Tuple
from ..tokens import TokenManager, initialize_design_system
from ..themes import ThemeManager, initialize_preset_themes


class TokenValidator:
    """
    Validates design token system integrity and usage patterns
    
    Features:
    - Token structure validation
    - Cross-reference checking between tokens
    - Theme token override validation
    - Token naming convention enforcement
    - Circular dependency detection
    """
    
    def __init__(self):
        self.token_registry = initialize_design_system()
        self.token_manager = self.token_registry.token_manager
        self.theme_manager = ThemeManager()
        initialize_preset_themes(self.theme_manager)
        
        # Define naming conventions
        self.naming_patterns = {
            'color': r'^color-(brand|neutral|semantic|status)-[a-z0-9-]+$',
            'spacing': r'^spacing-(xs|sm|md|lg|xl|2xl|3xl|4xl|5xl|6xl)$',
            'typography': r'^typography-(display|heading|body|label|ui)-[a-z0-9-]*$',
            'sizing': r'^sizing-(xs|sm|md|lg|xl|2xl|3xl|4xl|5xl|6xl|screen)-[a-z]*$'
        }
    
    def validate_all_tokens(self) -> Dict[str, Any]:
        """
        Validate all tokens in the design system
        
        Returns:
            Comprehensive token validation results
        """
        results = {
            'overall_score': 0.0,
            'summary': {
                'total_tokens': 0,
                'valid_tokens': 0,
                'invalid_tokens': 0,
                'warnings': 0
            },
            'categories': {},
            'naming_violations': [],
            'reference_issues': [],
            'theme_issues': [],
            'recommendations': []
        }
        
        # Get tokens by category from the token registry
        category_summary = self.token_registry.get_tokens_by_category_summary()
        
        for category_name, category_info in category_summary.items():
            # Get actual tokens for this category
            from ..tokens.base import TokenCategory
            try:
                category_enum = TokenCategory(category_name)
                tokens = self.token_manager.get_tokens_by_category(category_enum)
                
                category_results = self.validate_token_category(category_name, tokens)
                results['categories'][category_name] = category_results
                
                # Update summary - count actual tokens processed
                token_count = len(tokens) if tokens else 0
                results['summary']['total_tokens'] += token_count
                results['summary']['valid_tokens'] += category_results['valid_count']
                results['summary']['invalid_tokens'] += category_results['invalid_count']
                results['summary']['warnings'] += category_results['warning_count']
                
                # Collect issues
                results['naming_violations'].extend(category_results.get('naming_violations', []))
                results['reference_issues'].extend(category_results.get('reference_issues', []))
                
            except ValueError:
                # Skip invalid category
                self.logger.warning(f"Skipping invalid category: {category_name}")
                continue
        
        # Validate theme token overrides
        theme_validation = self.validate_theme_tokens()
        results['theme_issues'] = theme_validation.get('issues', [])
        
        # Calculate overall score
        if results['summary']['total_tokens'] > 0:
            results['overall_score'] = (results['summary']['valid_tokens'] / results['summary']['total_tokens']) * 100
        
        # Generate recommendations
        results['recommendations'] = self._generate_token_recommendations(results)
        
        return results
    
    def _count_tokens(self, tokens) -> int:
        """
        Count the number of tokens in a collection, handling different types
        
        Args:
            tokens: Token collection (dict, object, list, or single token)
            
        Returns:
            Number of tokens
        """
        if tokens is None:
            return 0
        
        # Handle different token input types
        if hasattr(tokens, '__dict__'):
            # Count non-private attributes
            return len([k for k in tokens.__dict__.keys() if not k.startswith('_')])
        elif hasattr(tokens, 'items'):
            # Dictionary of tokens
            return len(tokens)
        elif hasattr(tokens, '__iter__') and not isinstance(tokens, str):
            # Iterable collection (but not string)
            return len(list(tokens))
        else:
            # Single token object
            return 1
    
    def validate_token_category(self, category: str, tokens) -> Dict[str, Any]:
        """
        Validate all tokens in a specific category
        
        Args:
            category: Token category to validate
            tokens: List or collection of token objects to validate
            
        Returns:
            Category validation results
        """
        results = {
            'category': category,
            'valid_count': 0,
            'invalid_count': 0,
            'warning_count': 0,
            'tokens': {},
            'naming_violations': [],
            'reference_issues': []
        }
        
        # Handle different token input types
        if tokens is None:
            return results
        
        if isinstance(tokens, list):
            # List of token objects
            token_items = [(token.name, token) for token in tokens]
        elif hasattr(tokens, '__dict__'):
            # If tokens is an object with attributes, get its __dict__
            token_items = [(k, v) for k, v in tokens.__dict__.items() if not k.startswith('_')]
        elif hasattr(tokens, 'items'):
            # If tokens is a dictionary
            token_items = list(tokens.items())
        elif hasattr(tokens, '__iter__') and not isinstance(tokens, str):
            # If tokens is iterable but not a dict, create name-value pairs
            token_items = [(f"{category}_{i}", token) for i, token in enumerate(tokens)]
        else:
            # Single token object
            token_items = [(getattr(tokens, 'name', f"{category}_token"), tokens)]
        
        for token_name, token in token_items:
            # Skip private/internal attributes
            if token_name.startswith('_'):
                continue
                
            token_results = self.validate_individual_token(token_name, token, category)
            results['tokens'][token_name] = token_results
            
            if token_results['status'] == 'valid':
                results['valid_count'] += 1
            elif token_results['status'] == 'invalid':
                results['invalid_count'] += 1
            else:
                results['warning_count'] += 1
            
            # Collect violations
            if token_results.get('naming_violation'):
                results['naming_violations'].append({
                    'token': token_name,
                    'category': category,
                    'violation': token_results['naming_violation']
                })
            
            if token_results.get('reference_issues'):
                results['reference_issues'].extend([
                    {
                        'token': token_name,
                        'category': category,
                        'issue': issue
                    } for issue in token_results['reference_issues']
                ])
        
        return results
    
    def validate_individual_token(self, token_name: str, token, category: str) -> Dict[str, Any]:
        """
        Validate an individual token
        
        Args:
            token_name: Name of the token
            token: Token object
            category: Token category
            
        Returns:
            Token validation results
        """
        results = {
            'name': token_name,
            'status': 'valid',  # valid, invalid, warning
            'issues': [],
            'reference_issues': []
        }
        
        # Check naming convention
        naming_issue = self._check_naming_convention(token_name, category)
        if naming_issue:
            results['naming_violation'] = naming_issue
            results['status'] = 'warning'
            results['issues'].append(f"Naming convention violation: {naming_issue}")
        
        # Check token structure
        structure_issues = self._check_token_structure(token, category)
        if structure_issues:
            results['issues'].extend(structure_issues)
            if any('critical' in issue.lower() for issue in structure_issues):
                results['status'] = 'invalid'
            elif results['status'] == 'valid':
                results['status'] = 'warning'
        
        # Check token references
        reference_issues = self._check_token_references(token)
        if reference_issues:
            results['reference_issues'] = reference_issues
            results['issues'].extend(reference_issues)
            if results['status'] == 'valid':
                results['status'] = 'warning'
        
        return results
    
    def _check_naming_convention(self, token_name: str, category: str) -> str:
        """Check if token follows naming conventions"""
        if category not in self.naming_patterns:
            return f"No naming pattern defined for category '{category}'"
        
        pattern = self.naming_patterns[category]
        if not re.match(pattern, token_name):
            return f"Token name '{token_name}' doesn't match expected pattern for {category} tokens"
        
        return ""
    
    def _check_token_structure(self, token, category: str) -> List[str]:
        """Check token internal structure"""
        issues = []
        
        # Check if token has required attributes
        required_attrs = ['name', 'value']
        for attr in required_attrs:
            if not hasattr(token, attr):
                issues.append(f"CRITICAL: Missing required attribute '{attr}'")
        
        # Check value validity
        if hasattr(token, 'value'):
            value_issue = self._validate_token_value(token.value, category)
            if value_issue:
                issues.append(value_issue)
        
        # Check metadata if present
        if hasattr(token, 'metadata') and token.metadata:
            metadata_issues = self._validate_token_metadata(token.metadata)
            issues.extend(metadata_issues)
        
        return issues
    
    def _validate_token_value(self, value: Any, category: str) -> str:
        """Validate token value based on category"""
        if value is None:
            return "Token value is None"
        
        # Category-specific validation
        if category == 'color':
            if isinstance(value, str):
                # Check if it's a valid hex color or token reference
                if not (value.startswith('#') or value.startswith('{') or 
                       value.startswith('rgb') or value.startswith('hsl')):
                    return f"Invalid color value format: {value}"
            else:
                return f"Color token value should be string, got {type(value)}"
        
        elif category == 'spacing':
            if isinstance(value, str):
                # Should end with px, rem, em, etc.
                if not re.match(r'^\d+(\.\d+)?(px|rem|em|%)$', value):
                    return f"Invalid spacing value format: {value}"
            else:
                return f"Spacing token value should be string, got {type(value)}"
        
        elif category == 'typography':
            if isinstance(value, dict):
                # Should have font properties
                required_props = ['fontSize', 'fontFamily']
                for prop in required_props:
                    if prop not in value:
                        return f"Typography token missing property: {prop}"
            else:
                return f"Typography token value should be dict, got {type(value)}"
        
        return ""
    
    def _validate_token_metadata(self, metadata) -> List[str]:
        """Validate token metadata"""
        issues = []
        
        # Handle both dict and object metadata
        if metadata is None:
            issues.append("Missing token metadata")
            return issues
        
        # Check for recommended metadata fields
        recommended_fields = ['description', 'category']
        
        for field in recommended_fields:
            # Handle both dict and object metadata
            if hasattr(metadata, field):
                # Object-style metadata
                field_value = getattr(metadata, field)
                if field_value is None or (isinstance(field_value, str) and not field_value.strip()):
                    issues.append(f"Missing or empty metadata field: {field}")
            elif isinstance(metadata, dict) and field not in metadata:
                # Dict-style metadata
                issues.append(f"Missing recommended metadata field: {field}")
            elif not isinstance(metadata, dict):
                # Unknown metadata format
                issues.append(f"Cannot check metadata field '{field}' - unknown metadata format")
        
        return issues
    
    def _check_token_references(self, token) -> List[str]:
        """Check for invalid token references"""
        issues = []
        
        if not hasattr(token, 'value'):
            return issues
        
        value_str = str(token.value)
        
        # Find token references in the format {token-name}
        references = re.findall(r'\{([^}]+)\}', value_str)
        
        for ref in references:
            # Check if referenced token exists
            if not self._token_exists(ref):
                issues.append(f"Reference to non-existent token: {ref}")
            else:
                # Check for circular references
                if self._has_circular_reference(token.name, ref):
                    issues.append(f"Circular reference detected with token: {ref}")
        
        return issues
    
    def _token_exists(self, token_name: str) -> bool:
        """Check if a token exists in the system"""
        try:
            # Try to get the token from token manager
            self.token_manager.get_token_value(token_name)
            return True
        except:
            return False
    
    def _has_circular_reference(self, token_name: str, reference_name: str, visited: Set[str] = None) -> bool:
        """Check for circular references between tokens"""
        if visited is None:
            visited = set()
        
        if token_name in visited:
            return True
        
        visited.add(token_name)
        
        # Get the referenced token and check its references
        try:
            ref_token = self.token_manager.get_token(reference_name)
            if ref_token and hasattr(ref_token, 'value'):
                ref_value_str = str(ref_token.value)
                sub_references = re.findall(r'\{([^}]+)\}', ref_value_str)
                
                for sub_ref in sub_references:
                    if self._has_circular_reference(sub_ref, reference_name, visited.copy()):
                        return True
        except:
            pass
        
        return False
    
    def validate_theme_tokens(self) -> Dict[str, Any]:
        """Validate theme-specific token overrides"""
        results = {
            'themes_checked': [],
            'issues': [],
            'warnings': []
        }
        
        theme_names = list(self.theme_manager.get_theme_names())
        
        for theme_name in theme_names:
            try:
                theme_def = self.theme_manager.get_theme(theme_name)
                if theme_def and theme_def.token_overrides:
                    theme_issues = self._validate_theme_overrides(theme_name, theme_def.token_overrides)
                    results['issues'].extend(theme_issues)
                
                results['themes_checked'].append(theme_name)
                
            except Exception as e:
                results['issues'].append(f"Error validating theme '{theme_name}': {e}")
        
        return results
    
    def _validate_theme_overrides(self, theme_name: str, overrides: Dict) -> List[str]:
        """Validate token overrides for a specific theme"""
        issues = []
        
        for token_name, override_value in overrides.items():
            # Check if the token being overridden exists
            if not self._token_exists(token_name):
                issues.append(f"Theme '{theme_name}' overrides non-existent token: {token_name}")
            
            # Check if override value is valid
            if override_value is None:
                issues.append(f"Theme '{theme_name}' has null override for token: {token_name}")
            
            # Check for theme-specific naming
            if theme_name in token_name.lower():
                issues.append(f"Theme '{theme_name}' may have theme-specific token name: {token_name}")
        
        return issues
    
    def _generate_token_recommendations(self, validation_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []
        
        overall_score = validation_results['overall_score']
        if overall_score < 80:
            recommendations.append("Token system quality needs improvement")
        
        # Check naming violations
        naming_violations = len(validation_results['naming_violations'])
        if naming_violations > 5:
            recommendations.append(f"High number of naming violations ({naming_violations}) - review naming conventions")
        
        # Check reference issues
        ref_issues = len(validation_results['reference_issues'])
        if ref_issues > 0:
            recommendations.append(f"Token reference issues found ({ref_issues}) - check for broken references")
        
        # Check theme issues
        theme_issues = len(validation_results['theme_issues'])
        if theme_issues > 3:
            recommendations.append(f"Multiple theme token issues ({theme_issues}) - review theme overrides")
        
        # Check categories with low scores
        for category, cat_results in validation_results['categories'].items():
            total_tokens = cat_results['valid_count'] + cat_results['invalid_count'] + cat_results['warning_count']
            if total_tokens > 0:
                category_score = (cat_results['valid_count'] / total_tokens) * 100
                if category_score < 70:
                    recommendations.append(f"Category '{category}' has low quality score ({category_score:.1f}%)")
        
        return recommendations
    
    def generate_token_report(self, save_path: str = None) -> str:
        """Generate a comprehensive token validation report"""
        results = self.validate_all_tokens()
        
        report_lines = [
            "=" * 60,
            "DESIGN TOKEN SYSTEM VALIDATION REPORT",
            "=" * 60,
            "",
            f"Overall Score: {results['overall_score']:.1f}/100",
            f"Total Tokens: {results['summary']['total_tokens']}",
            f"Valid Tokens: {results['summary']['valid_tokens']}",
            f"Invalid Tokens: {results['summary']['invalid_tokens']}",
            f"Warnings: {results['summary']['warnings']}",
            "",
            "CATEGORY BREAKDOWN:",
            "-" * 40
        ]
        
        for category, cat_results in results['categories'].items():
            total = cat_results['valid_count'] + cat_results['invalid_count'] + cat_results['warning_count']
            score = (cat_results['valid_count'] / total * 100) if total > 0 else 0
            
            status_icon = "✅" if score >= 90 else "⚠️" if score >= 70 else "❌"
            report_lines.append(f"{status_icon} {category.upper()}: {score:.1f}% ({cat_results['valid_count']}/{total})")
        
        # Add naming violations
        if results['naming_violations']:
            report_lines.extend([
                "",
                "NAMING VIOLATIONS:",
                "-" * 30
            ])
            for violation in results['naming_violations'][:10]:  # Show max 10
                report_lines.append(f"• {violation['token']} ({violation['category']}): {violation['violation']}")
        
        # Add recommendations
        if results['recommendations']:
            report_lines.extend([
                "",
                "RECOMMENDATIONS:",
                "-" * 30
            ])
            for i, rec in enumerate(results['recommendations'], 1):
                report_lines.append(f"{i}. {rec}")
        
        report_content = "\n".join(report_lines)
        
        if save_path:
            try:
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(report_content)
                print(f"Token validation report saved to: {save_path}")
            except Exception as e:
                print(f"Failed to save token report: {e}")
        
        return report_content 