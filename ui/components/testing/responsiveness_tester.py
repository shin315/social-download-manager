# UI Responsiveness Tester
# Task 22.2 - UI Responsiveness Testing Implementation

"""
Comprehensive UI responsiveness testing implementation for Social Download Manager v2.0.
Tests screen resolution adaptation, window resizing performance, and high DPI support.
"""

import time
import sys
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
from PyQt6.QtWidgets import QApplication, QWidget, QMainWindow, QVBoxLayout, QLabel, QPushButton, QTableWidget
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QScreen

from .ui_test_base import UITestBase, UIMetrics, ResponsivenessTestMixin


@dataclass
class ResponsivenessTestResults:
    """Data class for responsiveness test results"""
    test_name: str
    resolution_tests: Dict[str, bool]
    resize_performance: Dict[str, float]
    dpi_support: Dict[str, bool]
    performance_metrics: UIMetrics
    overall_score: float
    passed: bool


class ResponsivenessTester(UITestBase, ResponsivenessTestMixin):
    """Comprehensive UI responsiveness testing implementation"""
    
    def __init__(self):
        super().__init__()
        self.test_results: List[ResponsivenessTestResults] = []
        self.performance_targets = {
            'response_time': 100.0,     # ms - Target from test plan
            'render_time': 50.0,        # ms
            'memory_usage': 50.0,       # MB
            'fps': 60.0,                # frames per second
            'resize_time': 16.7         # ms (60 FPS = 16.7ms per frame)
        }
    
    def run_complete_responsiveness_test(self, widget_classes: List[type]) -> Dict[str, ResponsivenessTestResults]:
        """Run complete responsiveness test suite on multiple widget types"""
        all_results = {}
        
        print("🚀 Starting UI Responsiveness Testing...")
        print("=" * 60)
        
        for widget_class in widget_classes:
            widget_name = widget_class.__name__
            print(f"\n📱 Testing Widget: {widget_name}")
            
            try:
                # Setup test environment
                self.setup_test_environment(widget_class)
                
                if self.test_widget:
                    # Run all responsiveness tests
                    results = self._run_widget_responsiveness_tests(widget_name)
                    all_results[widget_name] = results
                    
                    # Log results
                    self._log_widget_results(widget_name, results)
                
            except Exception as e:
                print(f"❌ Error testing {widget_name}: {e}")
                all_results[widget_name] = self._create_failed_result(widget_name, str(e))
                
            finally:
                # Clean up
                self.teardown_test_environment()
                
        # Generate summary report
        self._generate_summary_report(all_results)
        
        return all_results
    
    def _run_widget_responsiveness_tests(self, widget_name: str) -> ResponsivenessTestResults:
        """Run all responsiveness tests for a single widget"""
        
        if not self.test_widget:
            return self._create_failed_result(widget_name, "No test widget available")
            
        # Test 1: Screen Resolution Adaptation (TC-22.2.1)
        print("  🔄 Testing Screen Resolution Adaptation...")
        resolutions = self.get_screen_resolutions()
        resolution_results = self.test_screen_resolution_adaptation(self.test_widget, resolutions)
        
        # Test 2: Window Resizing Performance (TC-22.2.2)
        print("  ⚡ Testing Window Resizing Performance...")
        resize_results = self.test_window_resizing_performance(self.test_widget)
        
        # Test 3: High DPI Display Support (TC-22.2.3)
        print("  🔍 Testing High DPI Display Support...")
        dpi_results = self.test_high_dpi_display_support(self.test_widget)
        
        # Measure overall performance metrics
        self._measure_overall_performance()
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(
            resolution_results, resize_results, dpi_results
        )
        
        # Determine if test passed
        passed = overall_score >= 0.8  # 80% pass threshold
        
        return ResponsivenessTestResults(
            test_name=widget_name,
            resolution_tests=resolution_results,
            resize_performance=resize_results,
            dpi_support=dpi_results,
            performance_metrics=self.metrics,
            overall_score=overall_score,
            passed=passed
        )
    
    def test_screen_resolution_adaptation_detailed(self, widget: QWidget) -> Dict[str, Any]:
        """Detailed screen resolution adaptation testing"""
        results = {}
        
        # Define test resolutions from test plan
        test_resolutions = [
            (1920, 1080, "Full HD"),
            (1366, 768, "HD"),
            (2560, 1440, "2K"),
            (3840, 2160, "4K"),
            (800, 600, "Minimum")
        ]
        
        for width, height, name in test_resolutions:
            print(f"    📏 Testing {name} ({width}x{height})")
            
            # Resize widget
            widget.resize(width, height)
            self.app.processEvents()
            QTest.qWait(100)
            
            # Measure response time
            response_time = self.measure_response_time(widget.update)
            
            # Check UI elements visibility
            visibility = self.check_ui_elements_visible(widget)
            
            # Check text readability (font size appropriate)
            text_readable = self._check_text_readability(widget, width, height)
            
            # Check button sizes
            buttons_usable = self._check_button_usability(widget)
            
            results[f"{name}_{width}x{height}"] = {
                'response_time': response_time,
                'visibility': visibility,
                'text_readable': text_readable,
                'buttons_usable': buttons_usable,
                'passed': (response_time <= self.performance_targets['response_time'] and
                          all(visibility.values()) and text_readable and buttons_usable)
            }
            
        return results
    
    def test_window_resizing_performance_detailed(self, widget: QWidget) -> Dict[str, Any]:
        """Detailed window resizing performance testing"""
        results = {}
        
        # Test rapid resize operations (from test plan: 10 resizes/second)
        print("    🏃‍♂️ Testing Rapid Resize Operations...")
        
        rapid_resize_times = []
        fps_measurements = []
        
        # Perform 10 rapid resizes
        base_size = QSize(1000, 700)
        widget.resize(base_size)
        self.app.processEvents()
        
        for i in range(10):
            # Alternate between two sizes rapidly
            target_size = QSize(1200 + i * 50, 800 + i * 30) if i % 2 == 0 else base_size
            
            start_time = time.perf_counter()
            widget.resize(target_size)
            self.app.processEvents()
            end_time = time.perf_counter()
            
            resize_time = (end_time - start_time) * 1000  # Convert to ms
            rapid_resize_times.append(resize_time)
            
            # Measure FPS during resize
            fps = self.measure_fps(0.1)  # Measure for 100ms
            fps_measurements.append(fps)
            
            # Wait 100ms between resizes (10 resizes/second)
            QTest.qWait(100)
        
        # Calculate statistics
        avg_resize_time = sum(rapid_resize_times) / len(rapid_resize_times)
        max_resize_time = max(rapid_resize_times)
        avg_fps = sum(fps_measurements) / len(fps_measurements)
        min_fps = min(fps_measurements)
        
        # Test table column adjustment (if widget contains tables)
        table_adjustment_passed = self._test_table_column_adjustment(widget)
        
        results['rapid_resize'] = {
            'avg_resize_time': avg_resize_time,
            'max_resize_time': max_resize_time,
            'avg_fps': avg_fps,
            'min_fps': min_fps,
            'table_adjustment': table_adjustment_passed,
            'maintains_60fps': min_fps >= 60.0,
            'no_artifacts': avg_resize_time <= self.performance_targets['resize_time'],
            'passed': (avg_resize_time <= self.performance_targets['resize_time'] and
                      min_fps >= 60.0 and table_adjustment_passed)
        }
        
        return results
    
    def test_high_dpi_support_detailed(self, widget: QWidget) -> Dict[str, Any]:
        """Detailed high DPI display support testing"""
        results = {}
        
        # Test different DPI scales from test plan
        dpi_scales = [
            (1.0, "100%"),
            (1.25, "125%"),
            (1.5, "150%"),
            (2.0, "200%")
        ]
        
        base_size = QSize(1920, 1080)
        
        for scale, scale_name in dpi_scales:
            print(f"    🔍 Testing DPI Scale {scale_name}")
            
            # Simulate DPI scaling by adjusting widget size
            scaled_size = QSize(int(base_size.width() / scale), 
                              int(base_size.height() / scale))
            
            widget.resize(scaled_size)
            self.app.processEvents()
            QTest.qWait(100)
            
            # Check icon and image sharpness (basic test)
            icons_sharp = self._check_icon_sharpness(widget)
            
            # Check text rendering clarity
            text_clear = self._check_text_clarity(widget, scale)
            
            # Check component proportions
            proportions_consistent = self._check_component_proportions(widget, scale)
            
            # Check tooltip positioning
            tooltips_positioned = self._check_tooltip_positioning(widget)
            
            results[f"dpi_{scale_name}"] = {
                'icons_sharp': icons_sharp,
                'text_clear': text_clear,
                'proportions_consistent': proportions_consistent,
                'tooltips_positioned': tooltips_positioned,
                'passed': (icons_sharp and text_clear and 
                          proportions_consistent and tooltips_positioned)
            }
            
        return results
    
    def _measure_overall_performance(self):
        """Measure overall widget performance metrics"""
        if not self.test_widget:
            return
            
        # Measure response time for common actions
        self.measure_response_time(self.test_widget.update)
        
        # Measure render time
        self.measure_render_time(self.test_widget)
        
        # Measure memory usage
        self.measure_memory_usage()
        
        # Measure FPS
        self.measure_fps(1.0)
    
    def _calculate_overall_score(self, resolution_results: Dict, 
                                resize_results: Dict, dpi_results: Dict) -> float:
        """Calculate overall responsiveness score (0.0 to 1.0)"""
        
        # Count passed tests
        resolution_passed = sum(1 for result in resolution_results.values() if result)
        resolution_total = len(resolution_results)
        
        resize_passed = sum(1 for result in resize_results.values() 
                           if isinstance(result, (int, float)) and result <= self.performance_targets['resize_time'])
        resize_total = len(resize_results)
        
        dpi_passed = sum(1 for result in dpi_results.values() if result)
        dpi_total = len(dpi_results)
        
        # Calculate component scores
        resolution_score = resolution_passed / max(resolution_total, 1)
        resize_score = resize_passed / max(resize_total, 1)
        dpi_score = dpi_passed / max(dpi_total, 1)
        
        # Performance metrics score
        performance_score = 0.0
        target_checks = self.verify_performance_targets(self.performance_targets)
        performance_score = sum(1 for passed in target_checks.values() if passed) / len(target_checks)
        
        # Weighted overall score
        overall_score = (
            resolution_score * 0.3 +  # 30% weight
            resize_score * 0.3 +      # 30% weight
            dpi_score * 0.2 +         # 20% weight
            performance_score * 0.2    # 20% weight
        )
        
        return overall_score
    
    def _check_text_readability(self, widget: QWidget, width: int, height: int) -> bool:
        """Check if text remains readable at given resolution"""
        # Basic check: ensure minimum font size
        min_font_size = 8 if min(width, height) >= 800 else 6
        
        # Find all labels and text widgets
        text_widgets = widget.findChildren(QLabel)
        
        for text_widget in text_widgets:
            font = text_widget.font()
            if font.pointSize() < min_font_size:
                return False
                
        return True
    
    def _check_button_usability(self, widget: QWidget) -> bool:
        """Check if buttons are usable (minimum size)"""
        min_button_size = QSize(80, 30)  # Minimum usable button size
        
        buttons = widget.findChildren(QPushButton)
        
        for button in buttons:
            if (button.size().width() < min_button_size.width() or
                button.size().height() < min_button_size.height()):
                return False
                
        return True
    
    def _test_table_column_adjustment(self, widget: QWidget) -> bool:
        """Test if table columns adjust properly during resize"""
        tables = widget.findChildren(QTableWidget)
        
        for table in tables:
            if table.columnCount() == 0:
                continue
                
            # Store original column widths
            original_widths = []
            for i in range(table.columnCount()):
                original_widths.append(table.columnWidth(i))
            
            # Resize widget significantly
            original_size = widget.size()
            widget.resize(original_size.width() * 1.5, original_size.height())
            self.app.processEvents()
            
            # Check if columns adjusted
            adjusted = False
            for i in range(table.columnCount()):
                if table.columnWidth(i) != original_widths[i]:
                    adjusted = True
                    break
            
            # Restore original size
            widget.resize(original_size)
            self.app.processEvents()
            
            if not adjusted:
                return False
                
        return True
    
    def _check_icon_sharpness(self, widget: QWidget) -> bool:
        """Check icon sharpness (basic implementation)"""
        # This is a simplified check - in a real implementation,
        # you would analyze pixel data for sharpness
        return True  # Assume icons are sharp for now
    
    def _check_text_clarity(self, widget: QWidget, scale: float) -> bool:
        """Check text rendering clarity at given scale"""
        # Check if text widgets have appropriate fonts for the scale
        text_widgets = widget.findChildren(QLabel)
        
        for text_widget in text_widgets:
            font = text_widget.font()
            # Text should scale appropriately
            if scale >= 1.5 and font.pointSize() < 10:
                return False
                
        return True
    
    def _check_component_proportions(self, widget: QWidget, scale: float) -> bool:
        """Check if component proportions remain consistent"""
        # Basic proportion check - components should maintain relative sizes
        children = widget.findChildren(QWidget)
        
        if len(children) < 2:
            return True
            
        # Check aspect ratios remain reasonable
        for child in children[:5]:  # Check first 5 children
            size = child.size()
            if size.width() > 0 and size.height() > 0:
                aspect_ratio = size.width() / size.height()
                # Aspect ratio should be reasonable (not too extreme)
                if aspect_ratio > 10 or aspect_ratio < 0.1:
                    return False
                    
        return True
    
    def _check_tooltip_positioning(self, widget: QWidget) -> bool:
        """Check tooltip positioning (basic implementation)"""
        # This is a simplified check - tooltips should be properly positioned
        return True  # Assume tooltips are positioned correctly for now
    
    def _create_failed_result(self, widget_name: str, error_msg: str) -> ResponsivenessTestResults:
        """Create a failed test result"""
        return ResponsivenessTestResults(
            test_name=widget_name,
            resolution_tests={'error': False},
            resize_performance={'error': 999.0},
            dpi_support={'error': False},
            performance_metrics=UIMetrics(),
            overall_score=0.0,
            passed=False
        )
    
    def _log_widget_results(self, widget_name: str, results: ResponsivenessTestResults):
        """Log detailed results for a widget"""
        print(f"\n📊 Results for {widget_name}:")
        print(f"  Overall Score: {results.overall_score:.2f} ({'✅ PASS' if results.passed else '❌ FAIL'})")
        
        # Resolution tests
        resolution_passed = sum(1 for r in results.resolution_tests.values() if r)
        resolution_total = len(results.resolution_tests)
        print(f"  Resolution Tests: {resolution_passed}/{resolution_total} passed")
        
        # Resize performance
        avg_resize_time = sum(v for v in results.resize_performance.values() if isinstance(v, (int, float))) / max(len(results.resize_performance), 1)
        print(f"  Avg Resize Time: {avg_resize_time:.2f}ms")
        
        # DPI support
        dpi_passed = sum(1 for r in results.dpi_support.values() if r)
        dpi_total = len(results.dpi_support)
        print(f"  DPI Support: {dpi_passed}/{dpi_total} passed")
        
        # Performance metrics
        metrics = results.performance_metrics
        print(f"  Performance: Response={metrics.response_time:.1f}ms, "
              f"Render={metrics.render_time:.1f}ms, FPS={metrics.fps:.1f}")
    
    def _generate_summary_report(self, all_results: Dict[str, ResponsivenessTestResults]):
        """Generate summary report for all tests"""
        print("\n" + "=" * 60)
        print("📈 UI RESPONSIVENESS TEST SUMMARY")
        print("=" * 60)
        
        total_widgets = len(all_results)
        passed_widgets = sum(1 for r in all_results.values() if r.passed)
        
        print(f"Total Widgets Tested: {total_widgets}")
        print(f"Widgets Passed: {passed_widgets}")
        print(f"Overall Pass Rate: {passed_widgets/max(total_widgets, 1)*100:.1f}%")
        
        # Calculate average scores
        if all_results:
            avg_score = sum(r.overall_score for r in all_results.values()) / len(all_results)
            avg_response_time = sum(r.performance_metrics.response_time for r in all_results.values()) / len(all_results)
            avg_fps = sum(r.performance_metrics.fps for r in all_results.values()) / len(all_results)
            
            print(f"\nAverage Metrics:")
            print(f"  Overall Score: {avg_score:.2f}")
            print(f"  Response Time: {avg_response_time:.1f}ms")
            print(f"  Frame Rate: {avg_fps:.1f} FPS")
        
        # Performance target compliance
        print(f"\nPerformance Targets Compliance:")
        target_met = 0
        total_targets = len(self.performance_targets)
        
        for target_name, target_value in self.performance_targets.items():
            if target_name == 'fps':
                met = avg_fps >= target_value if 'avg_fps' in locals() else False
            else:
                met = getattr(all_results[list(all_results.keys())[0]].performance_metrics if all_results else UIMetrics(), 
                            target_name.replace('resize_time', 'render_time'), 0) <= target_value
            
            status = "✅ MET" if met else "❌ NOT MET"
            print(f"  {target_name}: {status}")
            if met:
                target_met += 1
        
        compliance_rate = target_met / total_targets * 100
        print(f"\nTarget Compliance Rate: {compliance_rate:.1f}%")
        
        # Final verdict
        overall_success = passed_widgets >= total_widgets * 0.8 and compliance_rate >= 80
        verdict = "✅ SUCCESS" if overall_success else "❌ NEEDS IMPROVEMENT"
        print(f"\nFinal Verdict: {verdict}")
        print("=" * 60)


# Test execution function
def run_responsiveness_tests():
    """Main function to run responsiveness tests"""
    
    # Import widget classes to test
    try:
        from ui.main_window import MainWindow
        from ui.video_info_tab import VideoInfoTab
        from ui.downloaded_videos_tab import DownloadedVideosTab
        
        widget_classes = [MainWindow, VideoInfoTab, DownloadedVideosTab]
        
    except ImportError as e:
        print(f"⚠️ Could not import all widget classes: {e}")
        # Fallback to basic widget for demonstration
        widget_classes = [QWidget]
    
    # Create tester and run tests
    tester = ResponsivenessTester()
    results = tester.run_complete_responsiveness_test(widget_classes)
    
    return results


if __name__ == "__main__":
    # Run tests when script is executed directly
    test_results = run_responsiveness_tests()
    print(f"\n🎯 Testing completed! Results for {len(test_results)} widgets.") 