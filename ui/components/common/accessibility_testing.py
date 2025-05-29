"""
Accessibility Testing Utilities

Comprehensive tools for testing accessibility compliance including:
- Automated accessibility testing
- Accessibility audit reports
- WCAG 2.1 compliance checking
- Performance analysis for accessibility features
"""

import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from pathlib import Path

from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtGui import QKeyEvent, QFocusEvent

from .accessibility import (
    AccessibilityManager, AccessibilityValidator, AccessibilityInfo,
    AccessibilityRole, AccessibilityState, AccessibilityProperty,
    get_accessibility_manager
)


@dataclass
class AccessibilityTestCase:
    """Test case for accessibility validation"""
    component_id: str
    test_name: str
    test_function: Callable
    expected_result: bool
    description: str
    severity: str = "error"  # error, warning, info
    wcag_reference: Optional[str] = None


@dataclass
class AccessibilityTestResult:
    """Result of an accessibility test"""
    test_case: AccessibilityTestCase
    passed: bool
    actual_result: Any
    message: str
    execution_time: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AccessibilityAuditReport:
    """Comprehensive accessibility audit report"""
    component_id: str
    component_type: str
    test_results: List[AccessibilityTestResult] = field(default_factory=list)
    compliance_score: float = 0.0
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    warnings: int = 0
    errors: int = 0
    recommendations: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class AccessibilityTester:
    """
    Comprehensive accessibility testing framework for UI components
    """
    
    def __init__(self):
        self._accessibility_manager = get_accessibility_manager()
        self._validator = AccessibilityValidator()
        self._test_cases: Dict[str, List[AccessibilityTestCase]] = {}
        self._custom_tests: List[AccessibilityTestCase] = []
        
        # Setup default test cases
        self._setup_default_tests()
    
    def _setup_default_tests(self):
        """Setup default accessibility test cases"""
        # Keyboard accessibility tests
        self._test_cases['keyboard'] = [
            AccessibilityTestCase(
                component_id="*",
                test_name="keyboard_focus_policy",
                test_function=self._test_keyboard_focus_policy,
                expected_result=True,
                description="Component accepts keyboard focus when focusable",
                severity="error",
                wcag_reference="2.1.1"
            ),
            AccessibilityTestCase(
                component_id="*",
                test_name="keyboard_navigation",
                test_function=self._test_keyboard_navigation,
                expected_result=True,
                description="Component supports keyboard navigation",
                severity="error",
                wcag_reference="2.1.1"
            )
        ]
        
        # ARIA tests
        self._test_cases['aria'] = [
            AccessibilityTestCase(
                component_id="*",
                test_name="aria_role",
                test_function=self._test_aria_role,
                expected_result=True,
                description="Component has appropriate ARIA role",
                severity="warning",
                wcag_reference="4.1.2"
            ),
            AccessibilityTestCase(
                component_id="*",
                test_name="aria_label",
                test_function=self._test_aria_label,
                expected_result=True,
                description="Interactive component has accessible label",
                severity="error",
                wcag_reference="4.1.2"
            )
        ]
        
        # Focus indicator tests
        self._test_cases['focus'] = [
            AccessibilityTestCase(
                component_id="*",
                test_name="focus_visible",
                test_function=self._test_focus_visible,
                expected_result=True,
                description="Component has visible focus indicators",
                severity="error",
                wcag_reference="2.4.7"
            ),
            AccessibilityTestCase(
                component_id="*",
                test_name="focus_order",
                test_function=self._test_focus_order,
                expected_result=True,
                description="Component has logical focus order",
                severity="warning",
                wcag_reference="2.4.3"
            )
        ]
        
        # Semantic markup tests
        self._test_cases['semantic'] = [
            AccessibilityTestCase(
                component_id="*",
                test_name="semantic_markup",
                test_function=self._test_semantic_markup,
                expected_result=True,
                description="Component uses appropriate semantic markup",
                severity="warning",
                wcag_reference="1.3.1"
            )
        ]
    
    # =========================================================================
    # Test Functions
    # =========================================================================
    
    def _test_keyboard_focus_policy(self, widget: QWidget, info: AccessibilityInfo) -> Tuple[bool, str]:
        """Test keyboard focus policy"""
        if not info.is_focusable:
            return True, "Component is not focusable by design"
        
        from PyQt6.QtCore import Qt
        focus_policy = widget.focusPolicy()
        
        if focus_policy == Qt.FocusPolicy.NoFocus:
            return False, "Focusable component does not accept keyboard focus"
        
        return True, "Component has appropriate focus policy"
    
    def _test_keyboard_navigation(self, widget: QWidget, info: AccessibilityInfo) -> Tuple[bool, str]:
        """Test keyboard navigation support"""
        shortcuts = info.keyboard_shortcuts
        
        if info.is_focusable and not shortcuts:
            return False, "Focusable component lacks keyboard shortcuts"
        
        # Check for basic navigation shortcuts based on component type
        widget_type = type(widget).__name__
        
        if 'Table' in widget_type:
            required_shortcuts = ['Up', 'Down', 'Left', 'Right']
            missing = [s for s in required_shortcuts if s not in shortcuts]
            if missing:
                return False, f"Table component missing navigation shortcuts: {missing}"
        
        return True, "Component supports appropriate keyboard navigation"
    
    def _test_aria_role(self, widget: QWidget, info: AccessibilityInfo) -> Tuple[bool, str]:
        """Test ARIA role appropriateness"""
        if not info.role:
            return False, "Component lacks ARIA role"
        
        # Check role appropriateness based on widget type
        widget_type = type(widget).__name__
        appropriate_roles = self._get_appropriate_roles(widget_type)
        
        if appropriate_roles and info.role not in appropriate_roles:
            return False, f"Role {info.role.value} may not be appropriate for {widget_type}"
        
        return True, "Component has appropriate ARIA role"
    
    def _test_aria_label(self, widget: QWidget, info: AccessibilityInfo) -> Tuple[bool, str]:
        """Test ARIA label presence"""
        interactive_roles = [
            AccessibilityRole.BUTTON, AccessibilityRole.TEXTBOX,
            AccessibilityRole.COMBOBOX, AccessibilityRole.SEARCH
        ]
        
        if info.role in interactive_roles or info.is_focusable:
            if not info.label and AccessibilityProperty.LABELLEDBY not in info.properties:
                return False, "Interactive component lacks accessible label"
        
        return True, "Component has appropriate labeling"
    
    def _test_focus_visible(self, widget: QWidget, info: AccessibilityInfo) -> Tuple[bool, str]:
        """Test focus visibility"""
        if not info.is_focusable:
            return True, "Component is not focusable"
        
        # Check for focus styles in stylesheet
        style_sheet = widget.styleSheet()
        has_focus_style = ':focus' in style_sheet or 'focus' in style_sheet.lower()
        
        if not has_focus_style:
            return False, "Component may lack visible focus indicators"
        
        return True, "Component has focus indicators"
    
    def _test_focus_order(self, widget: QWidget, info: AccessibilityInfo) -> Tuple[bool, str]:
        """Test focus order logic"""
        if info.focus_order < 0:
            return False, "Component has negative focus order"
        
        return True, "Component has appropriate focus order"
    
    def _test_semantic_markup(self, widget: QWidget, info: AccessibilityInfo) -> Tuple[bool, str]:
        """Test semantic markup"""
        if not info.role:
            return False, "Component lacks semantic role"
        
        # Check for appropriate properties based on role
        if info.role == AccessibilityRole.TABLE:
            if AccessibilityProperty.ROWCOUNT not in info.properties:
                return False, "Table component lacks row count property"
            if AccessibilityProperty.COLCOUNT not in info.properties:
                return False, "Table component lacks column count property"
        
        return True, "Component has appropriate semantic markup"
    
    def _get_appropriate_roles(self, widget_type: str) -> List[AccessibilityRole]:
        """Get appropriate ARIA roles for widget type"""
        role_mapping = {
            'QPushButton': [AccessibilityRole.BUTTON],
            'QLineEdit': [AccessibilityRole.TEXTBOX, AccessibilityRole.SEARCH],
            'QTextEdit': [AccessibilityRole.TEXTBOX],
            'QComboBox': [AccessibilityRole.COMBOBOX],
            'QTableWidget': [AccessibilityRole.TABLE, AccessibilityRole.GRID],
            'QProgressBar': [AccessibilityRole.PROGRESSBAR],
        }
        
        return role_mapping.get(widget_type, [])
    
    # =========================================================================
    # Test Execution
    # =========================================================================
    
    def test_component(self, component_id: str, 
                      test_categories: Optional[List[str]] = None) -> AccessibilityAuditReport:
        """Test accessibility compliance for a specific component"""
        # Get component info
        widget = self._accessibility_manager._registered_components.get(component_id)
        info = self._accessibility_manager._accessibility_info.get(component_id)
        
        if not widget or not info:
            raise ValueError(f"Component {component_id} not found or not registered")
        
        # Create audit report
        report = AccessibilityAuditReport(
            component_id=component_id,
            component_type=type(widget).__name__
        )
        
        # Determine which test categories to run
        categories = test_categories or list(self._test_cases.keys())
        
        # Run tests
        for category in categories:
            if category in self._test_cases:
                for test_case in self._test_cases[category]:
                    if test_case.component_id == "*" or test_case.component_id == component_id:
                        result = self._execute_test(test_case, widget, info)
                        report.test_results.append(result)
        
        # Run custom tests
        for test_case in self._custom_tests:
            if test_case.component_id == "*" or test_case.component_id == component_id:
                result = self._execute_test(test_case, widget, info)
                report.test_results.append(result)
        
        # Calculate report statistics
        self._calculate_report_statistics(report)
        
        return report
    
    def _execute_test(self, test_case: AccessibilityTestCase, 
                     widget: QWidget, info: AccessibilityInfo) -> AccessibilityTestResult:
        """Execute a single test case"""
        start_time = time.time()
        
        try:
            passed, message = test_case.test_function(widget, info)
            
            result = AccessibilityTestResult(
                test_case=test_case,
                passed=passed,
                actual_result=passed,
                message=message,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            result = AccessibilityTestResult(
                test_case=test_case,
                passed=False,
                actual_result=str(e),
                message=f"Test execution failed: {e}",
                execution_time=time.time() - start_time
            )
        
        return result
    
    def _calculate_report_statistics(self, report: AccessibilityAuditReport):
        """Calculate statistics for audit report"""
        report.total_tests = len(report.test_results)
        report.passed_tests = sum(1 for r in report.test_results if r.passed)
        report.failed_tests = report.total_tests - report.passed_tests
        
        # Count errors and warnings
        for result in report.test_results:
            if not result.passed:
                if result.test_case.severity == "error":
                    report.errors += 1
                elif result.test_case.severity == "warning":
                    report.warnings += 1
        
        # Calculate compliance score
        if report.total_tests > 0:
            report.compliance_score = (report.passed_tests / report.total_tests) * 100
        
        # Generate recommendations
        report.recommendations = self._generate_recommendations(report)
    
    def _generate_recommendations(self, report: AccessibilityAuditReport) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        failed_tests = [r for r in report.test_results if not r.passed]
        
        # Group by test category
        test_categories = {}
        for result in failed_tests:
            category = result.test_case.test_name.split('_')[0]
            if category not in test_categories:
                test_categories[category] = []
            test_categories[category].append(result)
        
        # Generate category-specific recommendations
        if 'keyboard' in test_categories:
            recommendations.append("Implement proper keyboard navigation and focus management")
        
        if 'aria' in test_categories:
            recommendations.append("Add appropriate ARIA attributes and labels")
        
        if 'focus' in test_categories:
            recommendations.append("Ensure focus indicators are visible and logical")
        
        if 'semantic' in test_categories:
            recommendations.append("Use proper semantic markup and roles")
        
        # Add specific recommendations based on component type
        widget_type = report.component_type
        
        if 'Table' in widget_type:
            recommendations.append("Implement table-specific accessibility features")
        elif 'Button' in widget_type:
            recommendations.append("Ensure button has clear action description")
        elif 'Input' in widget_type or 'Edit' in widget_type:
            recommendations.append("Add input validation and error messaging")
        
        return recommendations
    
    # =========================================================================
    # Custom Test Management
    # =========================================================================
    
    def add_custom_test(self, test_case: AccessibilityTestCase):
        """Add a custom test case"""
        self._custom_tests.append(test_case)
    
    def remove_custom_test(self, test_name: str):
        """Remove a custom test case"""
        self._custom_tests = [t for t in self._custom_tests if t.test_name != test_name]
    
    # =========================================================================
    # Batch Testing
    # =========================================================================
    
    def test_all_components(self, test_categories: Optional[List[str]] = None) -> Dict[str, AccessibilityAuditReport]:
        """Test all registered components"""
        reports = {}
        
        for component_id in self._accessibility_manager._registered_components:
            try:
                report = self.test_component(component_id, test_categories)
                reports[component_id] = report
            except Exception as e:
                print(f"Error testing component {component_id}: {e}")
        
        return reports
    
    # =========================================================================
    # Report Generation
    # =========================================================================
    
    def generate_comprehensive_report(self, reports: Dict[str, AccessibilityAuditReport]) -> str:
        """Generate comprehensive accessibility report"""
        lines = []
        lines.append("# Comprehensive Accessibility Report")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Overall statistics
        total_components = len(reports)
        total_tests = sum(r.total_tests for r in reports.values())
        total_passed = sum(r.passed_tests for r in reports.values())
        total_errors = sum(r.errors for r in reports.values())
        total_warnings = sum(r.warnings for r in reports.values())
        
        avg_compliance = sum(r.compliance_score for r in reports.values()) / total_components if total_components > 0 else 0
        
        lines.append("## Overall Statistics")
        lines.append(f"- **Total Components Tested:** {total_components}")
        lines.append(f"- **Total Tests Executed:** {total_tests}")
        lines.append(f"- **Tests Passed:** {total_passed}")
        lines.append(f"- **Total Errors:** {total_errors}")
        lines.append(f"- **Total Warnings:** {total_warnings}")
        lines.append(f"- **Average Compliance Score:** {avg_compliance:.1f}%\n")
        
        # Component details
        lines.append("## Component Reports")
        
        for component_id, report in reports.items():
            lines.append(f"### {component_id} ({report.component_type})")
            lines.append(f"- **Compliance Score:** {report.compliance_score:.1f}%")
            lines.append(f"- **Tests:** {report.passed_tests}/{report.total_tests} passed")
            lines.append(f"- **Errors:** {report.errors}")
            lines.append(f"- **Warnings:** {report.warnings}")
            
            # Failed tests
            failed_tests = [r for r in report.test_results if not r.passed]
            if failed_tests:
                lines.append("- **Failed Tests:**")
                for result in failed_tests:
                    lines.append(f"  - {result.test_case.test_name}: {result.message}")
            
            # Recommendations
            if report.recommendations:
                lines.append("- **Recommendations:**")
                for rec in report.recommendations:
                    lines.append(f"  - {rec}")
            
            lines.append("")
        
        # WCAG Guidelines Summary
        lines.append("## WCAG 2.1 Guidelines Summary")
        lines.append("- **2.1.1** Keyboard: All functionality available from keyboard")
        lines.append("- **2.4.3** Focus Order: Focus order preserves meaning and operability")
        lines.append("- **2.4.7** Focus Visible: Keyboard focus indicator is visible")
        lines.append("- **4.1.2** Name, Role, Value: For all UI components, name and role can be determined")
        lines.append("- **1.3.1** Info and Relationships: Information conveyed through presentation is available in text")
        
        return "\n".join(lines)
    
    def save_report_to_file(self, report_content: str, filename: str):
        """Save report to file"""
        filepath = Path(filename)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_content)
    
    def export_json_report(self, reports: Dict[str, AccessibilityAuditReport], filename: str):
        """Export reports as JSON"""
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'total_components': len(reports),
            'reports': {}
        }
        
        for component_id, report in reports.items():
            export_data['reports'][component_id] = {
                'component_type': report.component_type,
                'compliance_score': report.compliance_score,
                'total_tests': report.total_tests,
                'passed_tests': report.passed_tests,
                'failed_tests': report.failed_tests,
                'errors': report.errors,
                'warnings': report.warnings,
                'recommendations': report.recommendations,
                'test_results': [
                    {
                        'test_name': r.test_case.test_name,
                        'passed': r.passed,
                        'message': r.message,
                        'severity': r.test_case.severity,
                        'wcag_reference': r.test_case.wcag_reference,
                        'execution_time': r.execution_time
                    }
                    for r in report.test_results
                ]
            }
        
        filepath = Path(filename)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)


# =============================================================================
# Convenience Functions
# =============================================================================

def quick_accessibility_test(component_id: str) -> AccessibilityAuditReport:
    """Quick accessibility test for a component"""
    tester = AccessibilityTester()
    return tester.test_component(component_id)

def generate_accessibility_report(output_dir: str = "accessibility_reports") -> str:
    """Generate comprehensive accessibility report for all components"""
    tester = AccessibilityTester()
    reports = tester.test_all_components()
    
    # Generate text report
    report_content = tester.generate_comprehensive_report(reports)
    text_file = f"{output_dir}/accessibility_report.md"
    tester.save_report_to_file(report_content, text_file)
    
    # Generate JSON report
    json_file = f"{output_dir}/accessibility_report.json"
    tester.export_json_report(reports, json_file)
    
    return report_content 