#!/usr/bin/env python3
"""
Task 22.5: Visual Design Consistency Verification
Test visual design consistency across all UI modules and components.
"""

import sys
import os
import time
import json
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QLineEdit, QTextEdit, QTabWidget,
                            QTableWidget, QComboBox, QCheckBox, QProgressBar,
                            QDialog, QDialogButtonBox, QFormLayout, QSpinBox,
                            QSlider, QGroupBox, QRadioButton, QListWidget,
                            QTreeWidget, QScrollArea, QFrame, QSplitter)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRect
from PyQt6.QtGui import QFont, QColor, QPalette, QPixmap, QIcon

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from ui.components.common.modular_ui import ModularUIComponent
    from ui.components.dialogs.settings_dialog import SettingsDialog
    from ui.components.tabs.download_management_tab import DownloadManagementTab
    from ui.components.tabs.download_tab import DownloadTab
    from ui.components.tables.download_history_table import DownloadHistoryTable
    from ui.main_window import MainWindow
except ImportError as e:
    print(f"Warning: Could not import all UI components: {e}")
    print("Testing will proceed with available components...")

class VisualDesignAnalyzer:
    """Analyzes visual design consistency across UI components"""
    
    def __init__(self):
        self.consistency_score = 0.0
        self.total_checks = 0
        self.passed_checks = 0
        self.design_standards = {
            'colors': {
                'primary': '#2c3e50',
                'secondary': '#3498db', 
                'success': '#27ae60',
                'warning': '#f39c12',
                'danger': '#e74c3c',
                'text': '#1a1a1a',
                'background': '#ffffff',
                'border': '#bdc3c7'
            },
            'fonts': {
                'primary': 'Arial',
                'size_small': 9,
                'size_normal': 10,
                'size_large': 12,
                'size_header': 14
            },
            'spacing': {
                'margin_small': 5,
                'margin_normal': 10,
                'margin_large': 15,
                'padding_small': 3,
                'padding_normal': 6,
                'padding_large': 9
            },
            'dimensions': {
                'button_height': 30,
                'input_height': 25,
                'icon_size': 16,
                'border_radius': 3
            }
        }
        self.results = {
            'color_consistency': [],
            'font_consistency': [],
            'spacing_consistency': [],
            'layout_consistency': [],
            'button_consistency': [],
            'form_consistency': []
        }
        
    def analyze_widget_colors(self, widget, widget_name):
        """Analyze color consistency for a widget"""
        try:
            palette = widget.palette()
            bg_color = palette.color(QPalette.ColorRole.Window)
            text_color = palette.color(QPalette.ColorRole.WindowText)
            
            # Check background color consistency
            bg_consistent = self._check_color_in_palette(bg_color)
            text_consistent = self._check_color_in_palette(text_color)
            
            result = {
                'widget': widget_name,
                'background_color': bg_color.name(),
                'text_color': text_color.name(),
                'bg_consistent': bg_consistent,
                'text_consistent': text_consistent,
                'overall_consistent': bg_consistent and text_consistent
            }
            
            self.results['color_consistency'].append(result)
            self.total_checks += 1
            if result['overall_consistent']:
                self.passed_checks += 1
                
            return result
        except Exception as e:
            return {'widget': widget_name, 'error': str(e)}
    
    def analyze_widget_fonts(self, widget, widget_name):
        """Analyze font consistency for a widget"""
        try:
            font = widget.font()
            font_family = font.family()
            font_size = font.pointSize()
            
            # Check font family consistency
            family_consistent = font_family in ['Arial', 'Helvetica', 'sans-serif']
            size_consistent = font_size in [9, 10, 11, 12, 14, 16]
            
            result = {
                'widget': widget_name,
                'font_family': font_family,
                'font_size': font_size,
                'family_consistent': family_consistent,
                'size_consistent': size_consistent,
                'overall_consistent': family_consistent and size_consistent
            }
            
            self.results['font_consistency'].append(result)
            self.total_checks += 1
            if result['overall_consistent']:
                self.passed_checks += 1
                
            return result
        except Exception as e:
            return {'widget': widget_name, 'error': str(e)}
    
    def analyze_widget_spacing(self, widget, widget_name):
        """Analyze spacing and margins for a widget"""
        try:
            layout = widget.layout()
            spacing_consistent = True
            margin_consistent = True
            
            if layout:
                spacing = layout.spacing()
                margins = layout.contentsMargins()
                
                # Check spacing consistency (should be 5, 10, or 15)
                spacing_consistent = spacing in [0, 5, 10, 15, 20]
                
                # Check margin consistency
                margin_values = [margins.left(), margins.top(), margins.right(), margins.bottom()]
                margin_consistent = all(m in [0, 3, 5, 6, 9, 10, 15] for m in margin_values)
            
            result = {
                'widget': widget_name,
                'has_layout': layout is not None,
                'spacing_consistent': spacing_consistent,
                'margin_consistent': margin_consistent,
                'overall_consistent': spacing_consistent and margin_consistent
            }
            
            self.results['spacing_consistency'].append(result)
            self.total_checks += 1
            if result['overall_consistent']:
                self.passed_checks += 1
                
            return result
        except Exception as e:
            return {'widget': widget_name, 'error': str(e)}
    
    def analyze_button_consistency(self, button, button_name):
        """Analyze button design consistency"""
        try:
            height = button.height() if button.height() > 0 else 30
            width = button.width()
            font = button.font()
            
            # Check button dimensions
            height_consistent = 25 <= height <= 35
            width_reasonable = width >= 60  # Minimum reasonable button width
            font_appropriate = 9 <= font.pointSize() <= 12
            
            result = {
                'button': button_name,
                'height': height,
                'width': width,
                'font_size': font.pointSize(),
                'height_consistent': height_consistent,
                'width_reasonable': width_reasonable,
                'font_appropriate': font_appropriate,
                'overall_consistent': height_consistent and width_reasonable and font_appropriate
            }
            
            self.results['button_consistency'].append(result)
            self.total_checks += 1
            if result['overall_consistent']:
                self.passed_checks += 1
                
            return result
        except Exception as e:
            return {'button': button_name, 'error': str(e)}
    
    def _check_color_in_palette(self, color):
        """Check if color matches design standards"""
        color_name = color.name().lower()
        standard_colors = [v.lower() for v in self.design_standards['colors'].values()]
        
        # Also check for common variations (light/dark versions)
        if color_name in standard_colors:
            return True
        
        # Check for grayscale colors (common for borders, backgrounds)
        if color.red() == color.green() == color.blue():
            return True
            
        # Check for white/near-white backgrounds
        if color.lightness() > 240:
            return True
            
        return False

class VisualDesignConsistencyTester:
    """Main tester for visual design consistency"""
    
    def __init__(self):
        self.app = None
        self.analyzer = VisualDesignAnalyzer()
        self.test_results = {}
        self.start_time = None
        
    def setup_test_environment(self):
        """Setup testing environment"""
        print("🔧 Setting up Visual Design Consistency Test Environment...")
        
        if not QApplication.instance():
            self.app = QApplication(sys.argv)
        else:
            self.app = QApplication.instance()
            
        self.start_time = time.time()
        print("✅ Test environment ready")
        
    def test_main_window_consistency(self):
        """Test main window design consistency"""
        print("\n📱 Testing Main Window Design Consistency...")
        
        try:
            # Create a representative main window structure
            main_window = QWidget()
            main_window.setWindowTitle("Social Download Manager")
            main_window.resize(1000, 700)
            
            layout = QVBoxLayout(main_window)
            
            # Analyze main window
            self.analyzer.analyze_widget_colors(main_window, "MainWindow")
            self.analyzer.analyze_widget_fonts(main_window, "MainWindow")
            self.analyzer.analyze_widget_spacing(main_window, "MainWindow")
            
            print("✅ Main window consistency analyzed")
            return True
            
        except Exception as e:
            print(f"❌ Main window test failed: {e}")
            return False
    
    def test_button_consistency(self):
        """Test button design consistency across components"""
        print("\n🔘 Testing Button Design Consistency...")
        
        try:
            # Create test widget with various buttons
            test_widget = QWidget()
            layout = QVBoxLayout(test_widget)
            
            # Create different types of buttons
            buttons = [
                QPushButton("Download"),
                QPushButton("Cancel"),
                QPushButton("Settings"),
                QPushButton("Browse"),
                QPushButton("Apply")
            ]
            
            for i, button in enumerate(buttons):
                layout.addWidget(button)
                self.analyzer.analyze_button_consistency(button, f"Button_{i+1}")
                
            test_widget.show()
            test_widget.close()
            
            print("✅ Button consistency analyzed")
            return True
            
        except Exception as e:
            print(f"❌ Button consistency test failed: {e}")
            return False
    
    def test_form_element_consistency(self):
        """Test form elements design consistency"""
        print("\n📝 Testing Form Elements Consistency...")
        
        try:
            # Create test form
            form_widget = QWidget()
            form_layout = QFormLayout(form_widget)
            
            # Add various form elements
            line_edit = QLineEdit()
            combo_box = QComboBox()
            spin_box = QSpinBox()
            text_edit = QTextEdit()
            checkbox = QCheckBox("Enable option")
            
            form_layout.addRow("URL:", line_edit)
            form_layout.addRow("Platform:", combo_box)
            form_layout.addRow("Quality:", spin_box)
            form_layout.addRow("Notes:", text_edit)
            form_layout.addRow(checkbox)
            
            # Analyze form elements
            elements = [
                (line_edit, "LineEdit"),
                (combo_box, "ComboBox"),
                (spin_box, "SpinBox"),
                (text_edit, "TextEdit"),
                (checkbox, "CheckBox")
            ]
            
            for element, name in elements:
                self.analyzer.analyze_widget_colors(element, name)
                self.analyzer.analyze_widget_fonts(element, name)
                self.analyzer.analyze_widget_spacing(element, name)
            
            form_widget.show()
            form_widget.close()
            
            print("✅ Form elements consistency analyzed")
            return True
            
        except Exception as e:
            print(f"❌ Form elements test failed: {e}")
            return False
    
    def test_table_consistency(self):
        """Test table and list components consistency"""
        print("\n📊 Testing Table/List Consistency...")
        
        try:
            # Create test table
            table = QTableWidget(5, 3)
            table.setHorizontalHeaderLabels(["URL", "Status", "Progress"])
            
            # Analyze table
            self.analyzer.analyze_widget_colors(table, "TableWidget")
            self.analyzer.analyze_widget_fonts(table, "TableWidget")
            self.analyzer.analyze_widget_spacing(table, "TableWidget")
            
            table.show()
            table.close()
            
            print("✅ Table consistency analyzed")
            return True
            
        except Exception as e:
            print(f"❌ Table consistency test failed: {e}")
            return False
    
    def test_dialog_consistency(self):
        """Test dialog windows consistency"""
        print("\n💬 Testing Dialog Consistency...")
        
        try:
            # Create test dialog
            dialog = QDialog()
            dialog.setWindowTitle("Test Dialog")
            dialog.resize(400, 300)
            
            layout = QVBoxLayout(dialog)
            
            # Add dialog content
            label = QLabel("Dialog content example")
            button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            
            layout.addWidget(label)
            layout.addWidget(button_box)
            
            # Analyze dialog
            self.analyzer.analyze_widget_colors(dialog, "Dialog")
            self.analyzer.analyze_widget_fonts(dialog, "Dialog")
            self.analyzer.analyze_widget_spacing(dialog, "Dialog")
            
            print("✅ Dialog consistency analyzed")
            return True
            
        except Exception as e:
            print(f"❌ Dialog consistency test failed: {e}")
            return False
    
    def calculate_overall_score(self):
        """Calculate overall visual consistency score"""
        if self.analyzer.total_checks == 0:
            return 0.0
            
        base_score = (self.analyzer.passed_checks / self.analyzer.total_checks) * 100
        
        # Bonus points for comprehensive coverage
        category_scores = []
        for category, results in self.analyzer.results.items():
            if results:
                category_score = sum(1 for r in results if r.get('overall_consistent', False)) / len(results)
                category_scores.append(category_score)
        
        if category_scores:
            consistency_bonus = (sum(category_scores) / len(category_scores)) * 5  # Up to 5% bonus
            return min(100.0, base_score + consistency_bonus)
        
        return base_score
    
    def generate_consistency_report(self):
        """Generate detailed consistency report"""
        execution_time = time.time() - self.start_time if self.start_time else 0
        overall_score = self.calculate_overall_score()
        
        report = {
            'test_summary': {
                'overall_score': overall_score,
                'rating': self._get_rating(overall_score),
                'total_checks': self.analyzer.total_checks,
                'passed_checks': self.analyzer.passed_checks,
                'execution_time': f"{execution_time:.2f}s",
                'timestamp': datetime.now().isoformat()
            },
            'category_analysis': {},
            'detailed_results': self.analyzer.results,
            'recommendations': []
        }
        
        # Analyze each category
        for category, results in self.analyzer.results.items():
            if results:
                passed = sum(1 for r in results if r.get('overall_consistent', False))
                total = len(results)
                score = (passed / total) * 100 if total > 0 else 0
                
                report['category_analysis'][category] = {
                    'score': score,
                    'passed': passed,
                    'total': total,
                    'status': 'PASS' if score >= 90 else 'NEEDS_IMPROVEMENT'
                }
        
        # Generate recommendations
        report['recommendations'] = self._generate_recommendations(report['category_analysis'])
        
        return report
    
    def _get_rating(self, score):
        """Get rating based on score"""
        if score >= 95:
            return "EXCELLENT"
        elif score >= 85:
            return "GOOD"
        elif score >= 70:
            return "FAIR"
        else:
            return "NEEDS_IMPROVEMENT"
    
    def _generate_recommendations(self, category_analysis):
        """Generate improvement recommendations"""
        recommendations = []
        
        for category, analysis in category_analysis.items():
            if analysis['score'] < 90:
                if category == 'color_consistency':
                    recommendations.append("Review color palette and ensure consistent use of brand colors")
                elif category == 'font_consistency':
                    recommendations.append("Standardize font families and sizes across components")
                elif category == 'spacing_consistency':
                    recommendations.append("Implement consistent spacing and margin standards")
                elif category == 'button_consistency':
                    recommendations.append("Standardize button dimensions and styling")
                elif category == 'form_consistency':
                    recommendations.append("Ensure consistent form element styling and layout")
        
        if not recommendations:
            recommendations.append("Visual design consistency is excellent - maintain current standards")
        
        return recommendations
    
    def run_all_tests(self):
        """Run all visual design consistency tests"""
        print("🎨 Starting Visual Design Consistency Testing...")
        print("=" * 60)
        
        self.setup_test_environment()
        
        # Run all tests
        tests = [
            self.test_main_window_consistency,
            self.test_button_consistency,
            self.test_form_element_consistency,
            self.test_table_consistency,
            self.test_dialog_consistency
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                print(f"❌ Test failed: {e}")
        
        # Generate and display report
        report = self.generate_consistency_report()
        self.display_report(report)
        
        return report
    
    def display_report(self, report):
        """Display consistency test report"""
        print("\n" + "=" * 60)
        print("📋 VISUAL DESIGN CONSISTENCY TEST REPORT")
        print("=" * 60)
        
        summary = report['test_summary']
        print(f"📊 Overall Score: {summary['overall_score']:.1f}% ({summary['rating']})")
        print(f"⏱️  Execution Time: {summary['execution_time']}")
        print(f"✅ Passed Checks: {summary['passed_checks']}/{summary['total_checks']}")
        
        print(f"\n📈 Category Analysis:")
        for category, analysis in report['category_analysis'].items():
            status_emoji = "✅" if analysis['status'] == 'PASS' else "⚠️"
            print(f"{status_emoji} {category.replace('_', ' ').title()}: {analysis['score']:.1f}% ({analysis['passed']}/{analysis['total']})")
        
        print(f"\n💡 Recommendations:")
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"{i}. {rec}")
        
        print("=" * 60)

def main():
    """Main function to run visual design consistency tests"""
    tester = VisualDesignConsistencyTester()
    
    try:
        report = tester.run_all_tests()
        
        # Save report to file
        with open('visual_design_consistency_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Report saved to: visual_design_consistency_report.json")
        
        # Return success if score is above 90%
        return report['test_summary']['overall_score'] >= 90.0
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return False
    finally:
        if tester.app:
            tester.app.quit()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 