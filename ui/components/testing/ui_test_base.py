# UI Test Base Class
# Task 22.2 - UI Responsiveness Testing Infrastructure

"""
Base class for all UI tests providing common setup, teardown, and utility methods.
"""

import sys
import time
import pytest
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from PyQt6.QtWidgets import QApplication, QWidget, QMainWindow
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QScreen
import psutil
import threading


@dataclass
class UIMetrics:
    """Data class for UI performance metrics"""
    response_time: float = 0.0        # Button click to UI update (ms)
    render_time: float = 0.0          # Component render duration (ms)
    memory_usage: float = 0.0         # UI component memory (MB)
    fps: float = 0.0                  # Frame rate during operations
    load_time: float = 0.0            # Initial component load (ms)
    accessibility_score: int = 0      # WCAG compliance (0-100)
    usability_score: int = 0          # Task completion rate (%)


class UITestBase:
    """Base class for all UI tests with common functionality"""
    
    def __init__(self):
        self.app: Optional[QApplication] = None
        self.main_window: Optional[QMainWindow] = None
        self.test_widget: Optional[QWidget] = None
        self.metrics: UIMetrics = UIMetrics()
        self.start_time: float = 0.0
        self.process = psutil.Process()
        
    def setup_test_environment(self, widget_class=None, **kwargs) -> QApplication:
        """Setup test environment with QApplication and test widget"""
        
        # Create QApplication if not exists
        if not QApplication.instance():
            self.app = QApplication(sys.argv if sys.argv else ['test'])
        else:
            self.app = QApplication.instance()
            
        # Set application properties for testing
        self.app.setApplicationName("SDM-UITest")
        self.app.setApplicationVersion("2.0.0")
        
        # Create test widget if specified
        if widget_class:
            self.test_widget = widget_class(**kwargs)
            self.test_widget.show()
            
        # Wait for UI to stabilize
        QTest.qWait(100)
        
        return self.app
    
    def teardown_test_environment(self):
        """Clean up test environment"""
        if self.test_widget:
            self.test_widget.close()
            self.test_widget = None
            
        if self.main_window:
            self.main_window.close()
            self.main_window = None
            
        # Process pending events
        if self.app:
            self.app.processEvents()
            
        # Force garbage collection
        import gc
        gc.collect()
    
    def measure_response_time(self, action_func, *args, **kwargs) -> float:
        """Measure UI response time for an action"""
        start_time = time.perf_counter()
        
        # Execute action
        result = action_func(*args, **kwargs)
        
        # Wait for UI to update
        self.app.processEvents()
        
        end_time = time.perf_counter()
        response_time = (end_time - start_time) * 1000  # Convert to ms
        
        self.metrics.response_time = response_time
        return response_time
    
    def measure_render_time(self, widget: QWidget) -> float:
        """Measure widget render time"""
        start_time = time.perf_counter()
        
        # Force repaint
        widget.repaint()
        self.app.processEvents()
        
        end_time = time.perf_counter()
        render_time = (end_time - start_time) * 1000  # Convert to ms
        
        self.metrics.render_time = render_time
        return render_time
    
    def measure_memory_usage(self) -> float:
        """Measure current memory usage in MB"""
        memory_info = self.process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)  # Convert to MB
        
        self.metrics.memory_usage = memory_mb
        return memory_mb
    
    def measure_fps(self, duration_seconds: float = 1.0) -> float:
        """Measure frame rate during operations"""
        frame_count = 0
        start_time = time.perf_counter()
        end_time = start_time + duration_seconds
        
        while time.perf_counter() < end_time:
            self.app.processEvents()
            frame_count += 1
            
        actual_duration = time.perf_counter() - start_time
        fps = frame_count / actual_duration
        
        self.metrics.fps = fps
        return fps
    
    def get_screen_resolutions(self) -> List[QSize]:
        """Get available screen resolutions for testing"""
        screens = self.app.screens()
        resolutions = []
        
        for screen in screens:
            geometry = screen.geometry()
            resolutions.append(QSize(geometry.width(), geometry.height()))
            
        # Add common test resolutions
        common_resolutions = [
            QSize(1920, 1080),
            QSize(1366, 768),
            QSize(2560, 1440),
            QSize(3840, 2160),
            QSize(800, 600),  # Minimum size
        ]
        
        for res in common_resolutions:
            if res not in resolutions:
                resolutions.append(res)
                
        return resolutions
    
    def simulate_screen_resolution(self, width: int, height: int):
        """Simulate different screen resolution"""
        if self.test_widget:
            self.test_widget.resize(width, height)
            self.app.processEvents()
            QTest.qWait(100)  # Wait for resize to complete
    
    def simulate_window_resize(self, widget: QWidget, target_size: QSize, 
                             steps: int = 10) -> List[float]:
        """Simulate gradual window resize and measure performance"""
        initial_size = widget.size()
        resize_times = []
        
        for i in range(steps + 1):
            # Calculate intermediate size
            progress = i / steps
            current_width = int(initial_size.width() + 
                              (target_size.width() - initial_size.width()) * progress)
            current_height = int(initial_size.height() + 
                               (target_size.height() - initial_size.height()) * progress)
            
            # Measure resize time
            start_time = time.perf_counter()
            widget.resize(current_width, current_height)
            self.app.processEvents()
            end_time = time.perf_counter()
            
            resize_time = (end_time - start_time) * 1000  # Convert to ms
            resize_times.append(resize_time)
            
            # Small delay between resizes
            QTest.qWait(10)
            
        return resize_times
    
    def check_ui_elements_visible(self, widget: QWidget) -> Dict[str, bool]:
        """Check if all UI elements are visible and properly positioned"""
        results = {}
        
        # Check widget visibility
        results['widget_visible'] = widget.isVisible()
        results['widget_size_valid'] = widget.size().isValid()
        
        # Check child widgets
        child_widgets = widget.findChildren(QWidget)
        visible_children = 0
        total_children = len(child_widgets)
        
        for child in child_widgets:
            if child.isVisible():
                visible_children += 1
                
        results['children_visible_ratio'] = visible_children / max(total_children, 1)
        results['all_children_visible'] = visible_children == total_children
        
        # Check if widget fits in parent
        if widget.parent():
            parent_rect = widget.parent().rect()
            widget_rect = widget.geometry()
            results['fits_in_parent'] = parent_rect.contains(widget_rect)
        else:
            results['fits_in_parent'] = True
            
        return results
    
    def verify_performance_targets(self, targets: Dict[str, float]) -> Dict[str, bool]:
        """Verify current metrics against performance targets"""
        results = {}
        
        metrics_dict = {
            'response_time': self.metrics.response_time,
            'render_time': self.metrics.render_time,
            'memory_usage': self.metrics.memory_usage,
            'fps': self.metrics.fps,
            'load_time': self.metrics.load_time
        }
        
        for metric, target in targets.items():
            if metric in metrics_dict:
                actual = metrics_dict[metric]
                if metric == 'fps':
                    # For FPS, higher is better
                    results[metric] = actual >= target
                else:
                    # For other metrics, lower is better
                    results[metric] = actual <= target
            else:
                results[metric] = False
                
        return results
    
    def log_test_results(self, test_name: str, results: Dict[str, Any]):
        """Log test results for analysis"""
        print(f"\n{'='*50}")
        print(f"TEST: {test_name}")
        print(f"{'='*50}")
        
        # Log metrics
        print(f"Response Time: {self.metrics.response_time:.2f}ms")
        print(f"Render Time: {self.metrics.render_time:.2f}ms")
        print(f"Memory Usage: {self.metrics.memory_usage:.2f}MB")
        print(f"FPS: {self.metrics.fps:.2f}")
        print(f"Load Time: {self.metrics.load_time:.2f}ms")
        
        # Log results
        print(f"\nRESULTS:")
        for key, value in results.items():
            status = "✅ PASS" if value else "❌ FAIL"
            print(f"  {key}: {status}")
            
        print(f"{'='*50}\n")


class ResponsivenessTestMixin:
    """Mixin class providing responsiveness testing capabilities"""
    
    def test_screen_resolution_adaptation(self, widget: QWidget, 
                                        resolutions: List[QSize]) -> Dict[str, bool]:
        """Test widget adaptation to different screen resolutions"""
        results = {}
        
        for resolution in resolutions:
            test_name = f"{resolution.width()}x{resolution.height()}"
            
            # Resize widget to resolution
            widget.resize(resolution)
            self.app.processEvents()
            QTest.qWait(100)
            
            # Check if UI adapts properly
            visibility_results = self.check_ui_elements_visible(widget)
            results[test_name] = all(visibility_results.values())
            
        return results
    
    def test_window_resizing_performance(self, widget: QWidget) -> Dict[str, float]:
        """Test window resizing performance"""
        results = {}
        
        # Test resize scenarios
        resize_scenarios = [
            (QSize(800, 600), QSize(1920, 1080)),    # Small to large
            (QSize(1920, 1080), QSize(800, 600)),    # Large to small
            (QSize(1366, 768), QSize(2560, 1440)),   # Medium to very large
        ]
        
        for i, (start_size, end_size) in enumerate(resize_scenarios):
            scenario_name = f"resize_scenario_{i+1}"
            
            # Set initial size
            widget.resize(start_size)
            self.app.processEvents()
            QTest.qWait(100)
            
            # Measure resize performance
            resize_times = self.simulate_window_resize(widget, end_size)
            avg_resize_time = sum(resize_times) / len(resize_times)
            max_resize_time = max(resize_times)
            
            results[f"{scenario_name}_avg"] = avg_resize_time
            results[f"{scenario_name}_max"] = max_resize_time
            
        return results
    
    def test_high_dpi_display_support(self, widget: QWidget) -> Dict[str, bool]:
        """Test high DPI display support"""
        results = {}
        
        # Simulate different DPI scales
        dpi_scales = [1.0, 1.25, 1.5, 2.0]
        
        for scale in dpi_scales:
            scale_name = f"dpi_scale_{scale}"
            
            # Note: Actual DPI scaling would require system-level changes
            # For testing, we simulate by scaling widget size
            base_size = QSize(1920, 1080)
            scaled_size = QSize(int(base_size.width() * scale), 
                              int(base_size.height() * scale))
            
            widget.resize(scaled_size)
            self.app.processEvents()
            QTest.qWait(100)
            
            # Check if UI remains usable at scale
            visibility_results = self.check_ui_elements_visible(widget)
            results[scale_name] = all(visibility_results.values())
            
        return results 