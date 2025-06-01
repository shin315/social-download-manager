"""
Component Validator

Testing utilities for validating refactored UI components to ensure they
properly use design tokens and maintain visual consistency.
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Any
from ..styles import StyleManager, ComponentStyler, ThemeStyler


class ComponentValidator:
    """
    Validates that UI components properly use design tokens and maintain consistency
    
    Features:
    - Token usage validation across components
    - CSS hardcoding detection
    - Theme consistency checking
    - Component style validation
    - Performance impact assessment
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.style_manager = StyleManager()
        self.component_styler = ComponentStyler(self.style_manager)
        self.theme_styler = ThemeStyler(self.style_manager)
        
        # Define component types to validate
        self.component_types = [
            'button', 'input', 'table', 'tab', 'checkbox', 
            'menu', 'statusbar', 'dialog', 'tooltip', 'main_window'
        ]
        
        # Define validation rules
        self.validation_rules = {
            'no_hardcoded_colors': self._check_hardcoded_colors,
            'token_usage': self._check_token_usage,
            'theme_consistency': self._check_theme_consistency,
            'css_structure': self._check_css_structure,
            'accessibility': self._check_accessibility
        }
    
    def validate_all_components(self) -> Dict[str, Any]:
        """
        Run complete validation suite on all components
        
        Returns:
            Comprehensive validation report
        """
        results = {
            'summary': {
                'total_components': len(self.component_types),
                'passed': 0,
                'failed': 0,
                'warnings': 0
            },
            'components': {},
            'overall_score': 0.0,
            'recommendations': []
        }
        
        for component_type in self.component_types:
            component_results = self.validate_component(component_type)
            results['components'][component_type] = component_results
            
            # Update summary
            if component_results['status'] == 'passed':
                results['summary']['passed'] += 1
            elif component_results['status'] == 'failed':
                results['summary']['failed'] += 1
            else:
                results['summary']['warnings'] += 1
        
        # Calculate overall score
        total_score = sum(comp['score'] for comp in results['components'].values())
        results['overall_score'] = total_score / len(self.component_types)
        
        # Generate recommendations
        results['recommendations'] = self._generate_recommendations(results)
        
        return results
    
    def validate_component(self, component_type: str) -> Dict[str, Any]:
        """
        Validate a specific component type
        
        Args:
            component_type: Type of component to validate
            
        Returns:
            Component validation results
        """
        results = {
            'component': component_type,
            'status': 'passed',  # passed, warned, failed
            'score': 100.0,
            'checks': {},
            'issues': [],
            'suggestions': []
        }
        
        try:
            # Generate stylesheet for component
            stylesheet = self.style_manager.generate_stylesheet(component_type)
            
            if not stylesheet:
                results['status'] = 'failed'
                results['score'] = 0.0
                results['issues'].append(f"No stylesheet generated for {component_type}")
                return results
            
            # Run validation rules
            for rule_name, rule_func in self.validation_rules.items():
                try:
                    check_result = rule_func(component_type, stylesheet)
                    results['checks'][rule_name] = check_result
                    
                    # Adjust score based on check results
                    if not check_result['passed']:
                        penalty = check_result.get('penalty', 20)
                        results['score'] -= penalty
                        results['issues'].extend(check_result.get('issues', []))
                        
                        if check_result.get('severity') == 'critical':
                            results['status'] = 'failed'
                        elif results['status'] == 'passed':
                            results['status'] = 'warned'
                    
                    results['suggestions'].extend(check_result.get('suggestions', []))
                    
                except Exception as e:
                    self.logger.error(f"Error in rule {rule_name} for {component_type}: {e}")
                    results['checks'][rule_name] = {
                        'passed': False,
                        'error': str(e),
                        'severity': 'critical'
                    }
                    results['score'] -= 10
            
            # Ensure score doesn't go below 0
            results['score'] = max(0.0, results['score'])
            
        except Exception as e:
            self.logger.error(f"Error validating component {component_type}: {e}")
            results['status'] = 'failed'
            results['score'] = 0.0
            results['issues'].append(f"Validation error: {e}")
        
        return results
    
    def _check_hardcoded_colors(self, component_type: str, stylesheet: str) -> Dict[str, Any]:
        """Check for hardcoded color values in CSS"""
        hardcoded_patterns = [
            r'#[0-9a-fA-F]{3,6}',  # Hex colors
            r'rgb\([^)]+\)',        # RGB colors
            r'rgba\([^)]+\)',       # RGBA colors
            r'hsl\([^)]+\)',        # HSL colors
        ]
        
        issues = []
        for pattern in hardcoded_patterns:
            matches = re.findall(pattern, stylesheet)
            if matches:
                issues.extend([f"Hardcoded color found: {match}" for match in matches])
        
        return {
            'passed': len(issues) == 0,
            'issues': issues,
            'severity': 'high' if issues else 'none',
            'penalty': len(issues) * 5,
            'suggestions': ["Replace hardcoded colors with design tokens"] if issues else []
        }
    
    def _check_token_usage(self, component_type: str, stylesheet: str) -> Dict[str, Any]:
        """Check if component properly uses design tokens"""
        # Look for token references in the stylesheet
        token_patterns = [
            r'color-[a-z-]+',      # Color tokens
            r'spacing-[a-z-]+',    # Spacing tokens
            r'typography-[a-z-]+', # Typography tokens
            r'sizing-[a-z-]+'      # Sizing tokens
        ]
        
        token_count = 0
        for pattern in token_patterns:
            matches = re.findall(pattern, stylesheet)
            token_count += len(matches)
        
        # Components should use multiple tokens
        min_expected_tokens = 5
        passed = token_count >= min_expected_tokens
        
        return {
            'passed': passed,
            'token_count': token_count,
            'expected_minimum': min_expected_tokens,
            'severity': 'medium' if not passed else 'none',
            'penalty': 15 if not passed else 0,
            'suggestions': [
                f"Consider using more design tokens (found {token_count}, expected >= {min_expected_tokens})"
            ] if not passed else []
        }
    
    def _check_theme_consistency(self, component_type: str, stylesheet: str) -> Dict[str, Any]:
        """Check theme consistency across different themes"""
        themes = ['light', 'dark', 'high_contrast', 'blue']
        stylesheets = {}
        
        current_theme = self.style_manager.get_current_theme_name()
        
        issues = []
        for theme in themes:
            try:
                self.style_manager.switch_theme(theme)
                theme_stylesheet = self.style_manager.generate_stylesheet(component_type)
                stylesheets[theme] = theme_stylesheet
                
                if not theme_stylesheet:
                    issues.append(f"No stylesheet generated for theme: {theme}")
                    
            except Exception as e:
                issues.append(f"Error generating stylesheet for theme {theme}: {e}")
        
        # Restore original theme
        if current_theme:
            self.style_manager.switch_theme(current_theme)
        
        # Check if all themes have stylesheets
        all_themes_supported = len(stylesheets) == len(themes)
        
        return {
            'passed': all_themes_supported and len(issues) == 0,
            'themes_supported': len(stylesheets),
            'total_themes': len(themes),
            'issues': issues,
            'severity': 'high' if not all_themes_supported else 'none',
            'penalty': 25 if not all_themes_supported else 0,
            'suggestions': [
                "Ensure component styling works across all themes"
            ] if not all_themes_supported else []
        }
    
    def _check_css_structure(self, component_type: str, stylesheet: str) -> Dict[str, Any]:
        """Check CSS structure and best practices"""
        issues = []
        suggestions = []
        
        # Check for empty stylesheets
        if not stylesheet.strip():
            issues.append("Empty stylesheet generated")
            return {
                'passed': False,
                'issues': issues,
                'severity': 'critical',
                'penalty': 50
            }
        
        # Check for proper CSS syntax
        if stylesheet.count('{') != stylesheet.count('}'):
            issues.append("Unbalanced CSS braces")
        
        # Check for !important usage (should be minimal)
        important_count = stylesheet.count('!important')
        if important_count > 2:
            issues.append(f"Excessive use of !important ({important_count} times)")
            suggestions.append("Reduce !important usage for better CSS specificity")
        
        # Check for reasonable length
        if len(stylesheet) < 50:
            issues.append("Stylesheet seems too short")
            suggestions.append("Ensure component has sufficient styling")
        
        return {
            'passed': len(issues) == 0,
            'issues': issues,
            'suggestions': suggestions,
            'stylesheet_length': len(stylesheet),
            'important_count': important_count,
            'severity': 'medium' if issues else 'none',
            'penalty': len(issues) * 10
        }
    
    def _check_accessibility(self, component_type: str, stylesheet: str) -> Dict[str, Any]:
        """Check accessibility features in component styling"""
        accessibility_features = [
            ('focus', r'focus'),
            ('hover', r'hover'),
            ('disabled', r'disabled'),
            ('contrast', r'color|background')
        ]
        
        features_found = []
        for feature_name, pattern in accessibility_features:
            if re.search(pattern, stylesheet, re.IGNORECASE):
                features_found.append(feature_name)
        
        # Buttons and inputs should have focus states
        critical_components = ['button', 'input', 'checkbox']
        requires_focus = component_type in critical_components
        has_focus = 'focus' in features_found
        
        issues = []
        if requires_focus and not has_focus:
            issues.append(f"{component_type} should have focus states for accessibility")
        
        suggestions = []
        if len(features_found) < 2:
            suggestions.append("Consider adding more accessibility features (focus, hover, disabled states)")
        
        return {
            'passed': len(issues) == 0,
            'features_found': features_found,
            'accessibility_score': len(features_found) / len(accessibility_features) * 100,
            'issues': issues,
            'suggestions': suggestions,
            'severity': 'medium' if issues else 'none',
            'penalty': len(issues) * 15
        }
    
    def _generate_recommendations(self, validation_results: Dict[str, Any]) -> List[str]:
        """Generate overall recommendations based on validation results"""
        recommendations = []
        
        # Check overall score
        overall_score = validation_results['overall_score']
        if overall_score < 70:
            recommendations.append("Overall component quality needs improvement")
        
        # Check failed components
        failed_components = [
            name for name, result in validation_results['components'].items()
            if result['status'] == 'failed'
        ]
        
        if failed_components:
            recommendations.append(f"Critical issues found in: {', '.join(failed_components)}")
        
        # Check common issues
        all_issues = []
        for component_result in validation_results['components'].values():
            all_issues.extend(component_result['issues'])
        
        # Count issue types
        hardcoded_color_count = sum(1 for issue in all_issues if 'hardcoded color' in issue.lower())
        if hardcoded_color_count > 3:
            recommendations.append("Multiple hardcoded colors found - prioritize token migration")
        
        token_usage_issues = sum(1 for issue in all_issues if 'token' in issue.lower())
        if token_usage_issues > 2:
            recommendations.append("Improve design token usage across components")
        
        return recommendations
    
    def generate_validation_report(self, save_path: str = None) -> str:
        """Generate a comprehensive validation report"""
        results = self.validate_all_components()
        
        report_lines = [
            "=" * 60,
            "DESIGN SYSTEM COMPONENT VALIDATION REPORT",
            "=" * 60,
            "",
            f"Overall Score: {results['overall_score']:.1f}/100",
            f"Components Passed: {results['summary']['passed']}/{results['summary']['total_components']}",
            f"Components Failed: {results['summary']['failed']}/{results['summary']['total_components']}",
            f"Components with Warnings: {results['summary']['warnings']}/{results['summary']['total_components']}",
            "",
            "COMPONENT DETAILS:",
            "-" * 40
        ]
        
        for component_name, component_result in results['components'].items():
            status_icon = "✅" if component_result['status'] == 'passed' else "⚠️" if component_result['status'] == 'warned' else "❌"
            report_lines.append(f"{status_icon} {component_name.upper()}: {component_result['score']:.1f}/100")
            
            if component_result['issues']:
                for issue in component_result['issues'][:3]:  # Show max 3 issues per component
                    report_lines.append(f"    - {issue}")
        
        report_lines.extend([
            "",
            "RECOMMENDATIONS:",
            "-" * 40
        ])
        
        for i, rec in enumerate(results['recommendations'], 1):
            report_lines.append(f"{i}. {rec}")
        
        report_content = "\n".join(report_lines)
        
        if save_path:
            try:
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(report_content)
                print(f"Validation report saved to: {save_path}")
            except Exception as e:
                print(f"Failed to save report: {e}")
        
        return report_content 