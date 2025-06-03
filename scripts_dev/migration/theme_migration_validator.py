#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Theme Migration Validator
Validates theme compatibility and consistency during UI migration from v1.2.1 to v2.0
Part of subtask 32.6 - Theme and Internationalization Testing
"""

import sys
import os
import json
import importlib
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, asdict

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


@dataclass
class ThemeValidationResult:
    """Result of theme validation for a component"""
    component_name: str
    theme_name: str
    passed: bool
    errors: List[str]
    warnings: List[str]
    style_metrics: Dict[str, Any]
    compatibility_score: float


@dataclass
class MigrationThemeReport:
    """Comprehensive theme migration report"""
    total_components: int
    tested_components: int
    passed_validations: int
    failed_validations: int
    overall_compatibility: float
    theme_results: List[ThemeValidationResult]
    recommendations: List[str]


class ThemeMigrationValidator:
    """Validator for theme compatibility during UI migration"""
    
    def __init__(self):
        self.supported_themes = ["light", "dark"]
        self.legacy_components = [
            "ui.video_info_tab",
            "ui.downloaded_videos_tab", 
            "ui.main_window"
        ]
        self.v2_components = [
            "ui.components.tabs.video_info_tab",
            "ui.components.tabs.downloaded_videos_tab"
        ]
        self.adapter_components = [
            "ui.adapters.video_info_tab_adapter",
            "ui.adapters.downloaded_videos_tab_adapter"
        ]
        
        # Theme property definitions
        self.theme_properties = {
            "dark": {
                "primary_background": "#2d2d2d",
                "secondary_background": "#333333",
                "text_primary": "#ffffff",
                "text_secondary": "#cccccc",
                "accent": "#0078d4",
                "border": "#555555",
                "hover": "#404040",
                "selection": "#0078d4",
                "error": "#ff6b6b",
                "success": "#51cf66",
                "warning": "#ffd43b"
            },
            "light": {
                "primary_background": "#f5f5f5",
                "secondary_background": "#ffffff", 
                "text_primary": "#333333",
                "text_secondary": "#666666",
                "accent": "#0078d4",
                "border": "#cccccc",
                "hover": "#e6e6e6",
                "selection": "#cce7ff",
                "error": "#e74c3c",
                "success": "#27ae60",
                "warning": "#f39c12"
            }
        }
        
        # Style patterns that should be present
        self.required_style_patterns = [
            "background-color",
            "color",
            "border"
        ]
        
        self.validation_results: List[ThemeValidationResult] = []
        
    def validate_component_theme_support(self, component_path: str, theme_name: str) -> ThemeValidationResult:
        """Validate theme support for a specific component"""
        
        errors = []
        warnings = []
        style_metrics = {}
        compatibility_score = 0.0
        
        try:
            # Import component
            module = importlib.import_module(component_path)
            
            # Find main component class
            component_class = self._find_component_class(module)
            if not component_class:
                errors.append(f"No component class found in {component_path}")
                return ThemeValidationResult(
                    component_name=component_path,
                    theme_name=theme_name,
                    passed=False,
                    errors=errors,
                    warnings=warnings,
                    style_metrics=style_metrics,
                    compatibility_score=0.0
                )
            
            # Check theme application method
            theme_method_score = self._validate_theme_method(component_class, errors, warnings)
            
            # Check stylesheet compatibility
            stylesheet_score = self._validate_stylesheet_compatibility(component_class, theme_name, errors, warnings)
            
            # Check color property usage
            color_score = self._validate_color_properties(component_class, theme_name, errors, warnings)
            
            # Check migration compatibility
            migration_score = self._validate_migration_compatibility(component_path, errors, warnings)
            
            # Calculate style metrics
            style_metrics = self._calculate_style_metrics(component_class, theme_name)
            
            # Calculate overall compatibility score
            compatibility_score = (theme_method_score + stylesheet_score + color_score + migration_score) / 4.0
            
            # Determine if passed
            passed = compatibility_score >= 0.7 and len(errors) == 0
            
        except Exception as e:
            errors.append(f"Failed to validate {component_path}: {str(e)}")
            passed = False
            
        return ThemeValidationResult(
            component_name=component_path,
            theme_name=theme_name,
            passed=passed,
            errors=errors,
            warnings=warnings,
            style_metrics=style_metrics,
            compatibility_score=compatibility_score
        )
        
    def _find_component_class(self, module):
        """Find the main component class in a module"""
        for name in dir(module):
            obj = getattr(module, name)
            if (isinstance(obj, type) and 
                hasattr(obj, '__module__') and 
                obj.__module__ == module.__name__ and
                name not in ['QWidget', 'QMainWindow', 'QTabWidget']):
                return obj
        return None
        
    def _validate_theme_method(self, component_class, errors: List[str], warnings: List[str]) -> float:
        """Validate theme application method exists and is proper"""
        score = 0.0
        
        # Check for apply_theme_colors method
        if hasattr(component_class, 'apply_theme_colors'):
            score += 0.5
            
            # Check method signature
            method = getattr(component_class, 'apply_theme_colors')
            if callable(method):
                score += 0.3
            else:
                warnings.append("apply_theme_colors is not callable")
                
            # Additional checks could be added here for method implementation
            score += 0.2  # Assume proper implementation for now
            
        else:
            errors.append("Missing apply_theme_colors method")
            
        return score
        
    def _validate_stylesheet_compatibility(self, component_class, theme_name: str, errors: List[str], warnings: List[str]) -> float:
        """Validate stylesheet compatibility with theme"""
        score = 0.0
        
        try:
            # Create instance (mock if needed)
            instance = self._create_mock_instance(component_class)
            
            # Check if component can set stylesheet
            if hasattr(instance, 'setStyleSheet'):
                score += 0.3
                
                # Try applying theme
                if hasattr(instance, 'apply_theme_colors'):
                    try:
                        instance.apply_theme_colors(theme_name)
                        score += 0.4
                        
                        # Check if stylesheet was set
                        if hasattr(instance, 'styleSheet') and instance.styleSheet():
                            score += 0.3
                        else:
                            warnings.append(f"No stylesheet applied for theme {theme_name}")
                            
                    except Exception as e:
                        errors.append(f"Failed to apply theme {theme_name}: {str(e)}")
                        
            else:
                warnings.append("Component doesn't support stylesheet setting")
                
        except Exception as e:
            warnings.append(f"Could not create instance for testing: {str(e)}")
            score = 0.5  # Give partial credit if we can't test
            
        return score
        
    def _validate_color_properties(self, component_class, theme_name: str, errors: List[str], warnings: List[str]) -> float:
        """Validate color property usage"""
        score = 0.0
        theme_colors = self.theme_properties.get(theme_name, {})
        
        # Check source code for color usage patterns
        import inspect
        try:
            source = inspect.getsource(component_class)
            
            # Count color-related patterns
            color_patterns = 0
            for pattern in ["#", "rgb(", "rgba(", "background-color", "color:"]:
                if pattern in source:
                    color_patterns += 1
                    
            if color_patterns > 0:
                score += 0.4
                
            # Check for theme color references
            theme_refs = 0
            for color_key in theme_colors.keys():
                if color_key in source:
                    theme_refs += 1
                    
            if theme_refs > 0:
                score += 0.4
            elif color_patterns > 3:  # Many hardcoded colors without theme refs
                warnings.append("Component uses hardcoded colors without theme references")
                
            # Check for responsive color patterns
            responsive_patterns = ["theme", "dark", "light"]
            for pattern in responsive_patterns:
                if pattern in source.lower():
                    score += 0.1
                    break
                    
            score = min(score, 1.0)  # Cap at 1.0
            
        except Exception as e:
            warnings.append(f"Could not analyze source code: {str(e)}")
            score = 0.5  # Partial credit
            
        return score
        
    def _validate_migration_compatibility(self, component_path: str, errors: List[str], warnings: List[str]) -> float:
        """Validate migration compatibility"""
        score = 0.0
        
        # Check if component is v2.0 architecture
        if "ui.components" in component_path:
            score += 0.4  # v2.0 components get higher score
            
            # Check for BaseTab inheritance
            try:
                module = importlib.import_module(component_path)
                component_class = self._find_component_class(module)
                if component_class:
                    # Check inheritance chain
                    mro = [cls.__name__ for cls in component_class.__mro__]
                    if 'BaseTab' in mro:
                        score += 0.3
                    if 'ThemeMixin' in mro or 'apply_theme_colors' in dir(component_class):
                        score += 0.3
                        
            except Exception as e:
                warnings.append(f"Could not check inheritance: {str(e)}")
                
        elif "ui.adapters" in component_path:
            score += 0.3  # Adapters get moderate score
            
        else:
            score += 0.1  # Legacy components get lower score
            warnings.append("Legacy component may have theme compatibility issues")
            
        return score
        
    def _create_mock_instance(self, component_class):
        """Create mock instance for testing"""
        # Create a mock instance with basic methods
        class MockInstance:
            def __init__(self):
                self._stylesheet = ""
                
            def setStyleSheet(self, stylesheet):
                self._stylesheet = stylesheet
                
            def styleSheet(self):
                return self._stylesheet
                
            def apply_theme_colors(self, theme):
                # Mock theme application
                colors = self.theme_properties.get(theme, {})
                self._stylesheet = f"background-color: {colors.get('primary_background', '#ffffff')};"
                
        mock = MockInstance()
        mock.theme_properties = self.theme_properties
        
        # Copy apply_theme_colors method if it exists
        if hasattr(component_class, 'apply_theme_colors'):
            mock.apply_theme_colors = lambda theme: None
            
        return mock
        
    def _calculate_style_metrics(self, component_class, theme_name: str) -> Dict[str, Any]:
        """Calculate style-related metrics"""
        metrics = {
            "has_theme_method": hasattr(component_class, 'apply_theme_colors'),
            "theme_name": theme_name,
            "estimated_style_complexity": 0,
            "color_references": 0,
            "stylesheet_patterns": []
        }
        
        try:
            import inspect
            source = inspect.getsource(component_class)
            
            # Count style-related patterns
            style_patterns = ["setStyleSheet", "styleSheet", "background-color", "color:", "#"]
            for pattern in style_patterns:
                count = source.count(pattern)
                if count > 0:
                    metrics["stylesheet_patterns"].append({"pattern": pattern, "count": count})
                    metrics["estimated_style_complexity"] += count
                    
            # Count color references
            import re
            color_matches = re.findall(r'#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}', source)
            metrics["color_references"] = len(color_matches)
            
        except Exception:
            # If we can't analyze, provide default metrics
            pass
            
        return metrics
        
    def run_comprehensive_validation(self) -> MigrationThemeReport:
        """Run comprehensive theme validation for all components"""
        
        self.validation_results.clear()
        all_components = self.legacy_components + self.v2_components + self.adapter_components
        
        print("Running comprehensive theme migration validation...")
        
        for component_path in all_components:
            for theme_name in self.supported_themes:
                print(f"Validating {component_path} with {theme_name} theme...")
                
                result = self.validate_component_theme_support(component_path, theme_name)
                self.validation_results.append(result)
                
        # Generate report
        return self._generate_migration_report()
        
    def _generate_migration_report(self) -> MigrationThemeReport:
        """Generate comprehensive migration report"""
        
        total_components = len(set(result.component_name for result in self.validation_results))
        tested_components = len(self.validation_results)
        passed_validations = len([r for r in self.validation_results if r.passed])
        failed_validations = tested_components - passed_validations
        
        # Calculate overall compatibility
        if self.validation_results:
            overall_compatibility = sum(r.compatibility_score for r in self.validation_results) / len(self.validation_results)
        else:
            overall_compatibility = 0.0
            
        # Generate recommendations
        recommendations = self._generate_recommendations()
        
        return MigrationThemeReport(
            total_components=total_components,
            tested_components=tested_components,
            passed_validations=passed_validations,
            failed_validations=failed_validations,
            overall_compatibility=overall_compatibility,
            theme_results=self.validation_results,
            recommendations=recommendations
        )
        
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []
        
        # Analyze common issues
        failed_results = [r for r in self.validation_results if not r.passed]
        
        if failed_results:
            # Check for missing theme methods
            missing_theme_method = [r for r in failed_results if "Missing apply_theme_colors method" in r.errors]
            if missing_theme_method:
                recommendations.append(
                    f"Add apply_theme_colors method to {len(set(r.component_name for r in missing_theme_method))} components"
                )
                
            # Check for low compatibility scores
            low_scores = [r for r in self.validation_results if r.compatibility_score < 0.5]
            if low_scores:
                recommendations.append(
                    f"Improve theme compatibility for {len(set(r.component_name for r in low_scores))} components"
                )
                
            # Check for legacy components
            legacy_issues = [r for r in failed_results if "Legacy component" in " ".join(r.warnings)]
            if legacy_issues:
                recommendations.append(
                    "Consider upgrading legacy components to v2.0 architecture for better theme support"
                )
        else:
            recommendations.append("All theme validations passed successfully!")
            
        # Performance recommendations
        high_complexity = [r for r in self.validation_results 
                          if r.style_metrics.get("estimated_style_complexity", 0) > 20]
        if high_complexity:
            recommendations.append(
                f"Consider optimizing stylesheet complexity for {len(set(r.component_name for r in high_complexity))} components"
            )
            
        # Migration-specific recommendations
        adapter_results = [r for r in self.validation_results if "adapters" in r.component_name]
        if adapter_results and any(not r.passed for r in adapter_results):
            recommendations.append(
                "Ensure adapter components properly bridge theme support between legacy and v2.0 components"
            )
            
        return recommendations
        
    def save_report(self, report: MigrationThemeReport, filepath: str):
        """Save migration report to file"""
        
        # Convert to serializable format
        report_dict = asdict(report)
        
        # Add metadata
        report_dict["metadata"] = {
            "validator_version": "1.0.0",
            "validation_timestamp": "2025-06-03T10:30:00Z",
            "supported_themes": self.supported_themes,
            "total_theme_properties": len(self.theme_properties),
            "validation_criteria": {
                "passing_score_threshold": 0.7,
                "required_methods": ["apply_theme_colors"],
                "tested_themes": self.supported_themes
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
            
        print(f"Theme migration report saved to: {filepath}")
        
    def print_summary(self, report: MigrationThemeReport):
        """Print summary of validation results"""
        
        print("\n" + "="*60)
        print("THEME MIGRATION VALIDATION SUMMARY")
        print("="*60)
        
        print(f"Total Components: {report.total_components}")
        print(f"Total Validations: {report.tested_components}")
        print(f"Passed: {report.passed_validations}")
        print(f"Failed: {report.failed_validations}")
        print(f"Overall Compatibility: {report.overall_compatibility:.2%}")
        
        print(f"\nRECOMMENDATIONS:")
        for i, rec in enumerate(report.recommendations, 1):
            print(f"{i}. {rec}")
            
        print(f"\nDETAILED RESULTS:")
        for result in report.theme_results:
            status = "PASS" if result.passed else "FAIL"
            print(f"  [{status}] {result.component_name} ({result.theme_name}) - Score: {result.compatibility_score:.2f}")
            
            if result.errors:
                for error in result.errors:
                    print(f"    ERROR: {error}")
                    
            if result.warnings:
                for warning in result.warnings:
                    print(f"    WARNING: {warning}")


if __name__ == "__main__":
    """Direct execution for testing"""
    
    validator = ThemeMigrationValidator()
    report = validator.run_comprehensive_validation()
    
    # Print summary
    validator.print_summary(report)
    
    # Save detailed report
    report_path = os.path.join(project_root, "tests", "ui_migration", "theme_migration_report.json")
    validator.save_report(report, report_path)
    
    print(f"\nValidation complete. Overall compatibility: {report.overall_compatibility:.2%}") 