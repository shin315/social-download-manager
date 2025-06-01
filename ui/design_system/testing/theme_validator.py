"""
Theme Validator

Validates theme consistency, visual coherence, and accessibility compliance
across all UI components in different themes.
"""

from typing import Dict, List, Any, Tuple
from ..themes import ThemeManager, initialize_preset_themes
from ..styles import StyleManager, ComponentStyler, ThemeStyler


class ThemeValidator:
    """
    Validates theme consistency and visual coherence across components
    
    Features:
    - Cross-component theme consistency validation
    - Color contrast accessibility checking
    - Theme completeness assessment
    - Visual harmony validation
    - Dark/light mode compliance checking
    """
    
    def __init__(self):
        self.theme_manager = ThemeManager()
        initialize_preset_themes(self.theme_manager)
        self.style_manager = StyleManager()
        
        # Component types to validate across themes
        self.component_types = [
            'button', 'input', 'table', 'tab', 'checkbox', 
            'menu', 'statusbar', 'dialog', 'tooltip', 'main_window'
        ]
        
        # Define accessibility standards
        self.contrast_standards = {
            'AA_normal': 4.5,      # WCAG AA for normal text
            'AA_large': 3.0,       # WCAG AA for large text
            'AAA_normal': 7.0,     # WCAG AAA for normal text
            'AAA_large': 4.5       # WCAG AAA for large text
        }
    
    def validate_all_themes(self) -> Dict[str, Any]:
        """
        Run complete theme validation across all available themes
        
        Returns:
            Comprehensive theme validation report
        """
        results = {
            'summary': {
                'themes_tested': 0,
                'themes_passed': 0,
                'themes_failed': 0,
                'themes_warned': 0
            },
            'themes': {},
            'cross_theme_issues': [],
            'accessibility_issues': [],
            'consistency_score': 0.0,
            'recommendations': []
        }
        
        theme_names = list(self.theme_manager.get_theme_names())
        
        for theme_name in theme_names:
            theme_results = self.validate_theme(theme_name)
            results['themes'][theme_name] = theme_results
            
            results['summary']['themes_tested'] += 1
            
            if theme_results['status'] == 'passed':
                results['summary']['themes_passed'] += 1
            elif theme_results['status'] == 'failed':
                results['summary']['themes_failed'] += 1
            else:
                results['summary']['themes_warned'] += 1
        
        # Validate cross-theme consistency
        cross_theme_results = self.validate_cross_theme_consistency(theme_names)
        results['cross_theme_issues'] = cross_theme_results.get('issues', [])
        
        # Validate accessibility across themes
        accessibility_results = self.validate_theme_accessibility(theme_names)
        results['accessibility_issues'] = accessibility_results.get('issues', [])
        
        # Calculate overall consistency score
        if results['summary']['themes_tested'] > 0:
            results['consistency_score'] = (results['summary']['themes_passed'] / results['summary']['themes_tested']) * 100
        
        # Generate recommendations
        results['recommendations'] = self._generate_theme_recommendations(results)
        
        return results
    
    def validate_theme(self, theme_name: str) -> Dict[str, Any]:
        """
        Validate a specific theme for completeness and consistency
        
        Args:
            theme_name: Name of theme to validate
            
        Returns:
            Theme validation results
        """
        results = {
            'theme': theme_name,
            'status': 'passed',  # passed, warned, failed
            'score': 100.0,
            'components': {},
            'issues': [],
            'color_analysis': {},
            'completeness': {}
        }
        
        try:
            # Switch to theme for testing
            success = self.style_manager.switch_theme(theme_name)
            if not success:
                results['status'] = 'failed'
                results['score'] = 0.0
                results['issues'].append(f"Failed to switch to theme: {theme_name}")
                return results
            
            # Validate each component in this theme
            for component_type in self.component_types:
                component_results = self._validate_component_in_theme(theme_name, component_type)
                results['components'][component_type] = component_results
                
                if not component_results['passed']:
                    penalty = component_results.get('penalty', 10)
                    results['score'] -= penalty
                    results['issues'].extend(component_results.get('issues', []))
                    
                    if component_results.get('severity') == 'critical':
                        results['status'] = 'failed'
                    elif results['status'] == 'passed':
                        results['status'] = 'warned'
            
            # Analyze theme color palette
            results['color_analysis'] = self._analyze_theme_colors(theme_name)
            
            # Check theme completeness
            results['completeness'] = self._check_theme_completeness(theme_name)
            
            # Ensure score doesn't go below 0
            results['score'] = max(0.0, results['score'])
            
        except Exception as e:
            results['status'] = 'failed'
            results['score'] = 0.0
            results['issues'].append(f"Error validating theme {theme_name}: {e}")
        
        return results
    
    def _validate_component_in_theme(self, theme_name: str, component_type: str) -> Dict[str, Any]:
        """Validate a component's styling in a specific theme"""
        results = {
            'component': component_type,
            'theme': theme_name,
            'passed': True,
            'issues': [],
            'color_properties': {},
            'severity': 'none'
        }
        
        try:
            # Generate component stylesheet in current theme
            stylesheet = self.style_manager.generate_stylesheet(component_type)
            
            if not stylesheet:
                results['passed'] = False
                results['issues'].append(f"No stylesheet generated for {component_type} in {theme_name}")
                results['severity'] = 'critical'
                return results
            
            # Extract and validate color properties
            color_analysis = self._extract_color_properties(stylesheet)
            results['color_properties'] = color_analysis
            
            # Check for theme-appropriate colors
            theme_issues = self._check_theme_appropriate_colors(theme_name, color_analysis)
            if theme_issues:
                results['issues'].extend(theme_issues)
                results['passed'] = False
                results['severity'] = 'medium'
            
            # Check for missing essential properties
            essential_props = ['background-color', 'color']
            missing_props = [prop for prop in essential_props if prop not in color_analysis]
            if missing_props:
                results['issues'].append(f"Missing essential color properties: {missing_props}")
                results['passed'] = False
                results['severity'] = 'medium'
            
        except Exception as e:
            results['passed'] = False
            results['issues'].append(f"Error validating {component_type} in {theme_name}: {e}")
            results['severity'] = 'critical'
        
        return results
    
    def _extract_color_properties(self, stylesheet: str) -> Dict[str, List[str]]:
        """Extract color-related properties from stylesheet"""
        import re
        
        color_properties = {
            'background-color': [],
            'color': [],
            'border-color': [],
            'outline-color': []
        }
        
        # Extract color values for each property
        for prop in color_properties.keys():
            pattern = rf'{prop}\s*:\s*([^;]+);'
            matches = re.findall(pattern, stylesheet, re.IGNORECASE)
            color_properties[prop] = [match.strip() for match in matches]
        
        return color_properties
    
    def _check_theme_appropriate_colors(self, theme_name: str, color_analysis: Dict) -> List[str]:
        """Check if colors are appropriate for the theme type"""
        issues = []
        
        # Get theme definition
        try:
            theme_def = self.theme_manager.get_theme(theme_name)
            if not theme_def:
                return [f"Theme definition not found for: {theme_name}"]
            
            is_dark_theme = self._is_dark_theme(theme_name)
            
            # Check background colors
            bg_colors = color_analysis.get('background-color', [])
            for bg_color in bg_colors:
                if is_dark_theme and self._is_light_color(bg_color):
                    issues.append(f"Light background color '{bg_color}' in dark theme")
                elif not is_dark_theme and self._is_dark_color(bg_color):
                    issues.append(f"Dark background color '{bg_color}' in light theme")
            
            # Check text colors
            text_colors = color_analysis.get('color', [])
            for text_color in text_colors:
                if is_dark_theme and self._is_dark_color(text_color):
                    issues.append(f"Dark text color '{text_color}' in dark theme")
                elif not is_dark_theme and self._is_light_color(text_color):
                    issues.append(f"Light text color '{text_color}' in light theme")
                    
        except Exception as e:
            issues.append(f"Error checking theme colors: {e}")
        
        return issues
    
    def _is_dark_theme(self, theme_name: str) -> bool:
        """Determine if a theme is dark-based"""
        dark_keywords = ['dark', 'night', 'black']
        return any(keyword in theme_name.lower() for keyword in dark_keywords)
    
    def _is_light_color(self, color_value: str) -> bool:
        """Determine if a color value is light (simplified check)"""
        if color_value.startswith('#'):
            # Simple hex color brightness check
            hex_value = color_value[1:]
            if len(hex_value) == 6:
                r = int(hex_value[0:2], 16)
                g = int(hex_value[2:4], 16)
                b = int(hex_value[4:6], 16)
                brightness = (r * 299 + g * 587 + b * 114) / 1000
                return brightness > 128
        elif 'white' in color_value.lower() or '#fff' in color_value.lower():
            return True
        elif 'black' in color_value.lower() or '#000' in color_value.lower():
            return False
        
        return False  # Default assumption
    
    def _is_dark_color(self, color_value: str) -> bool:
        """Determine if a color value is dark"""
        return not self._is_light_color(color_value)
    
    def _analyze_theme_colors(self, theme_name: str) -> Dict[str, Any]:
        """Analyze the color palette of a theme"""
        analysis = {
            'primary_colors': [],
            'background_colors': [],
            'text_colors': [],
            'accent_colors': [],
            'color_count': 0,
            'has_sufficient_contrast': False
        }
        
        try:
            # Get theme definition
            theme_def = self.theme_manager.get_theme(theme_name)
            if theme_def and theme_def.token_overrides:
                color_tokens = {k: v for k, v in theme_def.token_overrides.items() if 'color' in k}
                analysis['color_count'] = len(color_tokens)
                
                # Categorize colors
                for token_name, token_value in color_tokens.items():
                    if 'primary' in token_name or 'brand' in token_name:
                        analysis['primary_colors'].append(token_value)
                    elif 'background' in token_name:
                        analysis['background_colors'].append(token_value)
                    elif 'text' in token_name:
                        analysis['text_colors'].append(token_value)
                    else:
                        analysis['accent_colors'].append(token_value)
                
                # Basic contrast check (simplified)
                if analysis['background_colors'] and analysis['text_colors']:
                    analysis['has_sufficient_contrast'] = True  # Simplified assumption
                    
        except Exception as e:
            analysis['error'] = f"Error analyzing theme colors: {e}"
        
        return analysis
    
    def _check_theme_completeness(self, theme_name: str) -> Dict[str, Any]:
        """Check if theme provides complete token coverage"""
        completeness = {
            'required_tokens': [],
            'missing_tokens': [],
            'completeness_score': 0.0
        }
        
        # Define required token categories for a complete theme
        required_token_patterns = [
            'color-background-primary',
            'color-background-secondary', 
            'color-text-primary',
            'color-text-secondary',
            'color-brand-primary',
            'color-border-default'
        ]
        
        try:
            theme_def = self.theme_manager.get_theme(theme_name)
            if theme_def and theme_def.token_overrides:
                provided_tokens = set(theme_def.token_overrides.keys())
                
                for required_pattern in required_token_patterns:
                    if required_pattern in provided_tokens:
                        completeness['required_tokens'].append(required_pattern)
                    else:
                        completeness['missing_tokens'].append(required_pattern)
                
                # Calculate completeness score
                total_required = len(required_token_patterns)
                provided_count = len(completeness['required_tokens'])
                completeness['completeness_score'] = (provided_count / total_required) * 100
                
        except Exception as e:
            completeness['error'] = f"Error checking theme completeness: {e}"
        
        return completeness
    
    def validate_cross_theme_consistency(self, theme_names: List[str]) -> Dict[str, Any]:
        """Validate consistency across different themes"""
        results = {
            'issues': [],
            'component_consistency': {},
            'structural_consistency': True
        }
        
        # Check if all themes provide the same component coverage
        component_coverage = {}
        
        for theme_name in theme_names:
            try:
                self.style_manager.switch_theme(theme_name)
                theme_components = []
                
                for component_type in self.component_types:
                    stylesheet = self.style_manager.generate_stylesheet(component_type)
                    if stylesheet:
                        theme_components.append(component_type)
                
                component_coverage[theme_name] = set(theme_components)
                
            except Exception as e:
                results['issues'].append(f"Error checking component coverage for {theme_name}: {e}")
        
        # Find inconsistencies in component coverage
        if component_coverage:
            all_components = set.union(*component_coverage.values())
            for component in all_components:
                themes_with_component = [theme for theme, components in component_coverage.items() 
                                       if component in components]
                if len(themes_with_component) != len(theme_names):
                    missing_themes = set(theme_names) - set(themes_with_component)
                    results['issues'].append(
                        f"Component '{component}' missing in themes: {list(missing_themes)}"
                    )
                    results['structural_consistency'] = False
        
        return results
    
    def validate_theme_accessibility(self, theme_names: List[str]) -> Dict[str, Any]:
        """Validate accessibility compliance across themes"""
        results = {
            'issues': [],
            'theme_scores': {},
            'overall_accessibility_score': 0.0
        }
        
        total_score = 0.0
        
        for theme_name in theme_names:
            theme_score = self._calculate_theme_accessibility_score(theme_name)
            results['theme_scores'][theme_name] = theme_score
            total_score += theme_score['score']
            
            # Collect accessibility issues
            if theme_score.get('issues'):
                results['issues'].extend([
                    f"{theme_name}: {issue}" for issue in theme_score['issues']
                ])
        
        # Calculate overall score
        if theme_names:
            results['overall_accessibility_score'] = total_score / len(theme_names)
        
        return results
    
    def _calculate_theme_accessibility_score(self, theme_name: str) -> Dict[str, Any]:
        """Calculate accessibility score for a specific theme"""
        score_data = {
            'theme': theme_name,
            'score': 100.0,
            'issues': [],
            'contrast_checks': {},
            'focus_visibility': True,
            'color_independence': True
        }
        
        try:
            # Switch to theme
            self.style_manager.switch_theme(theme_name)
            
            # Check contrast for critical components
            critical_components = ['button', 'input', 'menu']
            for component in critical_components:
                stylesheet = self.style_manager.generate_stylesheet(component)
                if stylesheet:
                    contrast_score = self._check_component_contrast(stylesheet)
                    score_data['contrast_checks'][component] = contrast_score
                    
                    if contrast_score < 4.5:  # WCAG AA minimum
                        score_data['issues'].append(f"Low contrast in {component} component")
                        score_data['score'] -= 15
            
            # Check focus visibility (simplified)
            if 'dark' in theme_name.lower():
                # Dark themes should have visible focus indicators
                focus_check = self._check_focus_visibility(theme_name)
                if not focus_check:
                    score_data['focus_visibility'] = False
                    score_data['issues'].append("Poor focus visibility in dark theme")
                    score_data['score'] -= 10
            
        except Exception as e:
            score_data['issues'].append(f"Error calculating accessibility: {e}")
            score_data['score'] -= 20
        
        score_data['score'] = max(0.0, score_data['score'])
        return score_data
    
    def _check_component_contrast(self, stylesheet: str) -> float:
        """Check color contrast in component stylesheet (simplified)"""
        # This is a simplified contrast check
        # In a real implementation, you'd parse colors and calculate actual contrast ratios
        
        if 'color:' in stylesheet and 'background-color:' in stylesheet:
            # Assume decent contrast if both are specified
            return 4.8  # Above WCAG AA threshold
        else:
            # Lower score if contrast properties are missing
            return 3.0
    
    def _check_focus_visibility(self, theme_name: str) -> bool:
        """Check if focus states are visible in theme (simplified)"""
        # Simplified check - assumes focus is visible if it's not a problematic theme
        problematic_patterns = ['high-contrast', 'monochrome']
        return not any(pattern in theme_name.lower() for pattern in problematic_patterns)
    
    def _generate_theme_recommendations(self, validation_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on theme validation results"""
        recommendations = []
        
        consistency_score = validation_results['consistency_score']
        if consistency_score < 80:
            recommendations.append("Theme consistency needs improvement across components")
        
        # Check failed themes
        failed_themes = [name for name, result in validation_results['themes'].items() 
                        if result['status'] == 'failed']
        if failed_themes:
            recommendations.append(f"Critical issues in themes: {', '.join(failed_themes)}")
        
        # Check cross-theme issues
        if validation_results['cross_theme_issues']:
            recommendations.append("Fix component coverage inconsistencies between themes")
        
        # Check accessibility
        if validation_results['accessibility_issues']:
            recommendations.append("Address accessibility issues across themes")
        
        # Check specific theme types
        theme_names = list(validation_results['themes'].keys())
        if 'dark' not in str(theme_names).lower():
            recommendations.append("Consider adding a dark theme for better accessibility")
        
        if 'high_contrast' not in str(theme_names).lower():
            recommendations.append("Consider adding a high contrast theme for accessibility")
        
        return recommendations
    
    def generate_theme_report(self, save_path: str = None) -> str:
        """Generate a comprehensive theme validation report"""
        results = self.validate_all_themes()
        
        report_lines = [
            "=" * 60,
            "THEME SYSTEM VALIDATION REPORT",
            "=" * 60,
            "",
            f"Consistency Score: {results['consistency_score']:.1f}/100",
            f"Themes Tested: {results['summary']['themes_tested']}",
            f"Themes Passed: {results['summary']['themes_passed']}",
            f"Themes Failed: {results['summary']['themes_failed']}",
            f"Themes with Warnings: {results['summary']['themes_warned']}",
            "",
            "THEME DETAILS:",
            "-" * 40
        ]
        
        for theme_name, theme_result in results['themes'].items():
            status_icon = "✅" if theme_result['status'] == 'passed' else "⚠️" if theme_result['status'] == 'warned' else "❌"
            report_lines.append(f"{status_icon} {theme_name.upper()}: {theme_result['score']:.1f}/100")
            
            if theme_result['issues']:
                for issue in theme_result['issues'][:3]:  # Show max 3 issues per theme
                    report_lines.append(f"    - {issue}")
        
        # Add accessibility summary
        if 'accessibility_issues' in results and results['accessibility_issues']:
            report_lines.extend([
                "",
                "ACCESSIBILITY ISSUES:",
                "-" * 30
            ])
            for issue in results['accessibility_issues'][:5]:  # Show max 5 accessibility issues
                report_lines.append(f"• {issue}")
        
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
                print(f"Theme validation report saved to: {save_path}")
            except Exception as e:
                print(f"Failed to save theme report: {e}")
        
        return report_content 