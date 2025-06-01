"""
Visual Regression Tester

Provides visual regression testing capabilities for UI components to ensure
design consistency and detect unexpected visual changes during development.
"""

import os
import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtGui import QPixmap, QPainter
from PyQt6.QtCore import QSize, QRect
from ..styles import StyleManager
from ..themes import ThemeManager, initialize_preset_themes


class VisualRegressionTester:
    """
    Visual regression testing for UI components
    
    Features:
    - Component screenshot capture
    - Visual diff comparison
    - Baseline management
    - Cross-theme visual testing
    - Automated regression detection
    """
    
    def __init__(self, baseline_dir: str = "ui/design_system/testing/baselines"):
        self.baseline_dir = baseline_dir
        self.style_manager = StyleManager()
        self.theme_manager = ThemeManager()
        initialize_preset_themes(self.theme_manager)
        
        # Ensure baseline directory exists
        os.makedirs(self.baseline_dir, exist_ok=True)
        
        # Test configurations
        self.test_sizes = [
            QSize(300, 200),  # Small component
            QSize(500, 300),  # Medium component
            QSize(800, 600),  # Large component
        ]
        
        self.component_types = [
            'button', 'input', 'table', 'tab', 'checkbox', 
            'menu', 'statusbar', 'dialog', 'tooltip'
        ]
    
    def run_full_regression_suite(self) -> Dict[str, Any]:
        """
        Run complete visual regression testing suite
        
        Returns:
            Comprehensive regression test results
        """
        results = {
            'summary': {
                'total_tests': 0,
                'passed': 0,
                'failed': 0,
                'new_baselines': 0
            },
            'themes': {},
            'components': {},
            'visual_diffs': [],
            'recommendations': []
        }
        
        theme_names = list(self.theme_manager.get_theme_names())
        
        for theme_name in theme_names:
            theme_results = self.test_theme_visuals(theme_name)
            results['themes'][theme_name] = theme_results
            
            # Update summary
            results['summary']['total_tests'] += theme_results.get('total_tests', 0)
            results['summary']['passed'] += theme_results.get('passed', 0)
            results['summary']['failed'] += theme_results.get('failed', 0)
            results['summary']['new_baselines'] += theme_results.get('new_baselines', 0)
            
            # Collect visual diffs
            if 'visual_diffs' in theme_results:
                results['visual_diffs'].extend(theme_results['visual_diffs'])
        
        # Generate recommendations
        results['recommendations'] = self._generate_regression_recommendations(results)
        
        return results
    
    def test_theme_visuals(self, theme_name: str) -> Dict[str, Any]:
        """
        Test visual consistency for all components in a specific theme
        
        Args:
            theme_name: Name of theme to test
            
        Returns:
            Theme visual test results
        """
        results = {
            'theme': theme_name,
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'new_baselines': 0,
            'components': {},
            'visual_diffs': []
        }
        
        try:
            # Switch to theme
            self.style_manager.switch_theme(theme_name)
            
            # Test each component
            for component_type in self.component_types:
                component_results = self.test_component_visuals(component_type, theme_name)
                results['components'][component_type] = component_results
                
                # Update counters
                results['total_tests'] += component_results.get('total_tests', 0)
                results['passed'] += component_results.get('passed', 0)
                results['failed'] += component_results.get('failed', 0)
                results['new_baselines'] += component_results.get('new_baselines', 0)
                
                # Collect visual diffs
                if 'visual_diffs' in component_results:
                    results['visual_diffs'].extend(component_results['visual_diffs'])
                    
        except Exception as e:
            results['error'] = f"Error testing theme {theme_name}: {e}"
        
        return results
    
    def test_component_visuals(self, component_type: str, theme_name: str) -> Dict[str, Any]:
        """
        Test visual consistency for a specific component in a theme
        
        Args:
            component_type: Type of component to test
            theme_name: Theme to test in
            
        Returns:
            Component visual test results
        """
        results = {
            'component': component_type,
            'theme': theme_name,
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'new_baselines': 0,
            'size_tests': {},
            'visual_diffs': []
        }
        
        for test_size in self.test_sizes:
            size_key = f"{test_size.width()}x{test_size.height()}"
            
            try:
                # Create test widget
                test_widget = self._create_test_widget(component_type, test_size)
                
                # Capture current screenshot
                current_screenshot = self._capture_widget_screenshot(test_widget)
                
                # Generate baseline path
                baseline_path = self._get_baseline_path(component_type, theme_name, size_key)
                
                # Compare with baseline
                comparison_result = self._compare_with_baseline(
                    current_screenshot, baseline_path, component_type, theme_name, size_key
                )
                
                results['size_tests'][size_key] = comparison_result
                results['total_tests'] += 1
                
                if comparison_result['status'] == 'passed':
                    results['passed'] += 1
                elif comparison_result['status'] == 'failed':
                    results['failed'] += 1
                    results['visual_diffs'].append({
                        'component': component_type,
                        'theme': theme_name,
                        'size': size_key,
                        'diff_score': comparison_result.get('diff_score', 0),
                        'baseline_path': baseline_path
                    })
                elif comparison_result['status'] == 'new_baseline':
                    results['new_baselines'] += 1
                
                # Clean up test widget
                test_widget.deleteLater()
                
            except Exception as e:
                results['size_tests'][size_key] = {
                    'status': 'error',
                    'error': str(e)
                }
                results['failed'] += 1
        
        return results
    
    def _create_test_widget(self, component_type: str, size: QSize) -> QWidget:
        """Create a test widget for visual testing"""
        widget = QWidget()
        widget.resize(size)
        
        # Apply component styling
        stylesheet = self.style_manager.generate_stylesheet(component_type)
        if stylesheet:
            widget.setStyleSheet(stylesheet)
        
        # Set basic properties for testing
        widget.setObjectName(f"test_{component_type}")
        
        # Add some content for visual testing
        if component_type == 'button':
            widget.setProperty('text', 'Test Button')
        elif component_type == 'input':
            widget.setProperty('placeholder', 'Test Input')
        
        # Ensure widget is shown for screenshot
        widget.show()
        QApplication.processEvents()  # Process any pending events
        
        return widget
    
    def _capture_widget_screenshot(self, widget: QWidget) -> QPixmap:
        """Capture a screenshot of a widget"""
        # Ensure widget is visible and updated
        widget.update()
        QApplication.processEvents()
        
        # Create pixmap with widget size
        pixmap = QPixmap(widget.size())
        pixmap.fill()  # Fill with default background
        
        # Render widget to pixmap
        painter = QPainter(pixmap)
        widget.render(painter)
        painter.end()
        
        return pixmap
    
    def _get_baseline_path(self, component_type: str, theme_name: str, size_key: str) -> str:
        """Generate baseline file path"""
        filename = f"{component_type}_{theme_name}_{size_key}.png"
        return os.path.join(self.baseline_dir, filename)
    
    def _compare_with_baseline(self, current_screenshot: QPixmap, baseline_path: str, 
                              component_type: str, theme_name: str, size_key: str) -> Dict[str, Any]:
        """Compare current screenshot with baseline"""
        result = {
            'status': 'unknown',
            'diff_score': 0.0,
            'baseline_exists': False,
            'baseline_path': baseline_path
        }
        
        try:
            if not os.path.exists(baseline_path):
                # No baseline exists, create one
                current_screenshot.save(baseline_path)
                result['status'] = 'new_baseline'
                result['message'] = f"Created new baseline for {component_type} in {theme_name}"
                return result
            
            result['baseline_exists'] = True
            
            # Load baseline
            baseline_screenshot = QPixmap(baseline_path)
            
            # Check if sizes match
            if current_screenshot.size() != baseline_screenshot.size():
                result['status'] = 'failed'
                result['diff_score'] = 100.0
                result['message'] = "Screenshot size mismatch"
                return result
            
            # Calculate visual difference
            diff_score = self._calculate_visual_diff(current_screenshot, baseline_screenshot)
            result['diff_score'] = diff_score
            
            # Determine status based on difference threshold
            if diff_score < 1.0:  # Less than 1% difference
                result['status'] = 'passed'
                result['message'] = "Visual match within tolerance"
            elif diff_score < 5.0:  # Less than 5% difference
                result['status'] = 'warning'
                result['message'] = f"Minor visual differences ({diff_score:.2f}%)"
            else:
                result['status'] = 'failed'
                result['message'] = f"Significant visual differences ({diff_score:.2f}%)"
                
                # Save current screenshot for comparison
                current_path = baseline_path.replace('.png', '_current.png')
                current_screenshot.save(current_path)
                result['current_screenshot'] = current_path
            
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
        
        return result
    
    def _calculate_visual_diff(self, screenshot1: QPixmap, screenshot2: QPixmap) -> float:
        """
        Calculate visual difference between two screenshots
        
        Returns:
            Difference percentage (0-100)
        """
        # Convert pixmaps to images for comparison
        img1 = screenshot1.toImage()
        img2 = screenshot2.toImage()
        
        if img1.size() != img2.size():
            return 100.0  # Complete difference if sizes don't match
        
        width = img1.width()
        height = img1.height()
        total_pixels = width * height
        different_pixels = 0
        
        # Compare pixel by pixel (simplified)
        for x in range(width):
            for y in range(height):
                pixel1 = img1.pixel(x, y)
                pixel2 = img2.pixel(x, y)
                
                if pixel1 != pixel2:
                    # Could implement more sophisticated color difference calculation
                    different_pixels += 1
        
        # Calculate percentage difference
        diff_percentage = (different_pixels / total_pixels) * 100
        return diff_percentage
    
    def update_baselines(self, component_type: str = None, theme_name: str = None) -> Dict[str, Any]:
        """
        Update baseline screenshots for regression testing
        
        Args:
            component_type: Specific component to update (None for all)
            theme_name: Specific theme to update (None for all)
            
        Returns:
            Update results
        """
        results = {
            'updated_baselines': [],
            'errors': [],
            'total_updated': 0
        }
        
        # Determine which components and themes to update
        components_to_update = [component_type] if component_type else self.component_types
        themes_to_update = [theme_name] if theme_name else list(self.theme_manager.get_theme_names())
        
        for theme in themes_to_update:
            try:
                self.style_manager.switch_theme(theme)
                
                for component in components_to_update:
                    for test_size in self.test_sizes:
                        size_key = f"{test_size.width()}x{test_size.height()}"
                        
                        try:
                            # Create test widget
                            test_widget = self._create_test_widget(component, test_size)
                            
                            # Capture screenshot
                            screenshot = self._capture_widget_screenshot(test_widget)
                            
                            # Save as baseline
                            baseline_path = self._get_baseline_path(component, theme, size_key)
                            screenshot.save(baseline_path)
                            
                            results['updated_baselines'].append({
                                'component': component,
                                'theme': theme,
                                'size': size_key,
                                'path': baseline_path
                            })
                            results['total_updated'] += 1
                            
                            # Clean up
                            test_widget.deleteLater()
                            
                        except Exception as e:
                            results['errors'].append({
                                'component': component,
                                'theme': theme,
                                'size': size_key,
                                'error': str(e)
                            })
                            
            except Exception as e:
                results['errors'].append({
                    'theme': theme,
                    'error': f"Failed to switch to theme: {e}"
                })
        
        return results
    
    def get_baseline_info(self) -> Dict[str, Any]:
        """Get information about existing baselines"""
        info = {
            'baseline_directory': self.baseline_dir,
            'total_baselines': 0,
            'themes': {},
            'components': set(),
            'sizes': set()
        }
        
        if not os.path.exists(self.baseline_dir):
            return info
        
        for filename in os.listdir(self.baseline_dir):
            if filename.endswith('.png') and '_current.png' not in filename:
                info['total_baselines'] += 1
                
                # Parse filename to extract info
                parts = filename.replace('.png', '').split('_')
                if len(parts) >= 3:
                    component = parts[0]
                    theme = parts[1]
                    size = '_'.join(parts[2:])
                    
                    info['components'].add(component)
                    info['sizes'].add(size)
                    
                    if theme not in info['themes']:
                        info['themes'][theme] = {
                            'components': set(),
                            'baseline_count': 0
                        }
                    
                    info['themes'][theme]['components'].add(component)
                    info['themes'][theme]['baseline_count'] += 1
        
        # Convert sets to lists for JSON serialization
        info['components'] = list(info['components'])
        info['sizes'] = list(info['sizes'])
        for theme_data in info['themes'].values():
            theme_data['components'] = list(theme_data['components'])
        
        return info
    
    def _generate_regression_recommendations(self, test_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on regression test results"""
        recommendations = []
        
        summary = test_results['summary']
        
        # Check overall pass rate
        if summary['total_tests'] > 0:
            pass_rate = (summary['passed'] / summary['total_tests']) * 100
            if pass_rate < 80:
                recommendations.append(f"Low visual consistency pass rate ({pass_rate:.1f}%) - review failed tests")
        
        # Check for visual differences
        visual_diffs = test_results.get('visual_diffs', [])
        if len(visual_diffs) > 5:
            recommendations.append(f"High number of visual differences ({len(visual_diffs)}) detected")
        
        # Check for new baselines
        if summary['new_baselines'] > 10:
            recommendations.append(f"Many new baselines created ({summary['new_baselines']}) - verify visual correctness")
        
        # Check theme-specific issues
        for theme_name, theme_results in test_results.get('themes', {}).items():
            if theme_results.get('failed', 0) > theme_results.get('passed', 0):
                recommendations.append(f"Theme '{theme_name}' has more failures than passes")
        
        return recommendations
    
    def generate_regression_report(self, save_path: str = None) -> str:
        """Generate a comprehensive visual regression report"""
        test_results = self.run_full_regression_suite()
        baseline_info = self.get_baseline_info()
        
        report_lines = [
            "=" * 60,
            "VISUAL REGRESSION TEST REPORT",
            "=" * 60,
            "",
            f"Total Tests: {test_results['summary']['total_tests']}",
            f"Passed: {test_results['summary']['passed']}",
            f"Failed: {test_results['summary']['failed']}",
            f"New Baselines: {test_results['summary']['new_baselines']}",
            "",
            f"Baseline Directory: {baseline_info['baseline_directory']}",
            f"Total Baselines: {baseline_info['total_baselines']}",
            "",
            "THEME RESULTS:",
            "-" * 40
        ]
        
        for theme_name, theme_results in test_results['themes'].items():
            total = theme_results.get('total_tests', 0)
            passed = theme_results.get('passed', 0)
            failed = theme_results.get('failed', 0)
            
            pass_rate = (passed / total * 100) if total > 0 else 0
            status_icon = "✅" if pass_rate >= 90 else "⚠️" if pass_rate >= 70 else "❌"
            
            report_lines.append(f"{status_icon} {theme_name.upper()}: {pass_rate:.1f}% ({passed}/{total})")
        
        # Add visual differences
        visual_diffs = test_results.get('visual_diffs', [])
        if visual_diffs:
            report_lines.extend([
                "",
                "VISUAL DIFFERENCES:",
                "-" * 30
            ])
            for diff in visual_diffs[:10]:  # Show max 10
                report_lines.append(
                    f"• {diff['component']} ({diff['theme']}, {diff['size']}): {diff['diff_score']:.2f}% difference"
                )
        
        # Add recommendations
        if test_results['recommendations']:
            report_lines.extend([
                "",
                "RECOMMENDATIONS:",
                "-" * 30
            ])
            for i, rec in enumerate(test_results['recommendations'], 1):
                report_lines.append(f"{i}. {rec}")
        
        report_content = "\n".join(report_lines)
        
        if save_path:
            try:
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(report_content)
                print(f"Visual regression report saved to: {save_path}")
            except Exception as e:
                print(f"Failed to save regression report: {e}")
        
        return report_content 