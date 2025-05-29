"""
Widget Testing Framework

Specialized testing for UI widgets including:
- User interaction simulation (clicks, key presses, etc.)
- Rendering validation and visual testing
- Widget state verification
- Event handling testing
- UI behavior validation
"""

import time
from typing import Dict, Any, List, Optional, Callable, Union, Tuple
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtWidgets import (
    QWidget, QApplication, QPushButton, QLineEdit, QTableWidget,
    QComboBox, QProgressBar, QLabel, QTextEdit
)
from PyQt6.QtCore import Qt, QPoint, QTimer, QEventLoop
from PyQt6.QtGui import QKeyEvent, QMouseEvent, QResizeEvent, QPaintEvent
from PyQt6.QtTest import QTest

from .component_tester import ComponentTestCase, TestResult, TestCategory, TestPriority


class InteractionType(Enum):
    """Types of user interactions"""
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    KEY_PRESS = "key_press"
    KEY_SEQUENCE = "key_sequence"
    MOUSE_MOVE = "mouse_move"
    DRAG_DROP = "drag_drop"
    SCROLL = "scroll"
    RESIZE = "resize"


class ValidationResult(Enum):
    """Widget validation results"""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    SKIP = "skip"


@dataclass
class InteractionTest:
    """Test case for user interactions"""
    interaction_type: InteractionType
    target_element: Optional[str] = None  # Element name or selector
    parameters: Dict[str, Any] = None  # Interaction parameters
    expected_result: Any = None
    timeout_ms: int = 1000


@dataclass
class RenderingTest:
    """Test case for rendering validation"""
    test_name: str
    validation_function: Callable
    expected_state: Dict[str, Any]
    tolerance: float = 0.0  # For numeric comparisons


@dataclass
class ValidationTest:
    """Test case for widget state validation"""
    property_name: str
    expected_value: Any
    comparison_type: str = "equal"  # equal, not_equal, greater, less, contains


class WidgetTestCase(ComponentTestCase):
    """Base class for widget-specific test cases"""
    
    def __init__(self, name: str, description: str, widget: QWidget,
                 category: TestCategory = TestCategory.WIDGET,
                 priority: TestPriority = TestPriority.MEDIUM,
                 tags: Optional[List[str]] = None):
        super().__init__(name, description, category, priority, tags)
        self.widget = widget
        self.interaction_tests: List[InteractionTest] = []
        self.rendering_tests: List[RenderingTest] = []
        self.validation_tests: List[ValidationTest] = []
        
        # Test configuration
        self.auto_show_widget = True
        self.auto_process_events = True
        self.event_processing_timeout = 100
    
    def add_interaction_test(self, interaction_test: InteractionTest):
        """Add an interaction test"""
        self.interaction_tests.append(interaction_test)
    
    def add_rendering_test(self, rendering_test: RenderingTest):
        """Add a rendering test"""
        self.rendering_tests.append(rendering_test)
    
    def add_validation_test(self, validation_test: ValidationTest):
        """Add a validation test"""
        self.validation_tests.append(validation_test)
    
    def setup(self):
        """Setup widget for testing"""
        super().setup()
        
        if self.auto_show_widget and not self.widget.isVisible():
            self.widget.show()
        
        if self.auto_process_events:
            QApplication.processEvents()
            QTest.qWait(self.event_processing_timeout)
    
    def teardown(self):
        """Cleanup after testing"""
        try:
            if self.widget.isVisible():
                self.widget.hide()
        except:
            pass
        
        super().teardown()


class WidgetTester:
    """
    Specialized widget testing framework
    """
    
    def __init__(self):
        self._app = QApplication.instance()
        if self._app is None:
            self._app = QApplication([])
        
        # Test settings
        self.default_timeout = 5000  # 5 seconds
        self.event_delay = 10  # milliseconds between events
        self.verbose_interactions = False
    
    # =========================================================================
    # Interaction Simulation
    # =========================================================================
    
    def click_widget(self, widget: QWidget, position: Optional[QPoint] = None,
                    button: Qt.MouseButton = Qt.MouseButton.LeftButton) -> bool:
        """Simulate mouse click on widget"""
        try:
            if position is None:
                position = widget.rect().center()
            
            if self.verbose_interactions:
                print(f"Clicking widget {widget.__class__.__name__} at {position}")
            
            QTest.mouseClick(widget, button, Qt.KeyboardModifier.NoModifier, position)
            self._process_events()
            return True
            
        except Exception as e:
            if self.verbose_interactions:
                print(f"Click failed: {e}")
            return False
    
    def double_click_widget(self, widget: QWidget, position: Optional[QPoint] = None) -> bool:
        """Simulate double click on widget"""
        try:
            if position is None:
                position = widget.rect().center()
            
            if self.verbose_interactions:
                print(f"Double-clicking widget {widget.__class__.__name__} at {position}")
            
            QTest.mouseDClick(widget, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, position)
            self._process_events()
            return True
            
        except Exception as e:
            if self.verbose_interactions:
                print(f"Double-click failed: {e}")
            return False
    
    def right_click_widget(self, widget: QWidget, position: Optional[QPoint] = None) -> bool:
        """Simulate right click on widget"""
        try:
            if position is None:
                position = widget.rect().center()
            
            if self.verbose_interactions:
                print(f"Right-clicking widget {widget.__class__.__name__} at {position}")
            
            QTest.mouseClick(widget, Qt.MouseButton.RightButton, Qt.KeyboardModifier.NoModifier, position)
            self._process_events()
            return True
            
        except Exception as e:
            if self.verbose_interactions:
                print(f"Right-click failed: {e}")
            return False
    
    def send_key_to_widget(self, widget: QWidget, key: Union[str, Qt.Key],
                          modifier: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> bool:
        """Send key press to widget"""
        try:
            if isinstance(key, str):
                if self.verbose_interactions:
                    print(f"Sending key '{key}' to widget {widget.__class__.__name__}")
                QTest.keyClicks(widget, key, modifier)
            else:
                if self.verbose_interactions:
                    print(f"Sending key {key} to widget {widget.__class__.__name__}")
                QTest.keyClick(widget, key, modifier)
            
            self._process_events()
            return True
            
        except Exception as e:
            if self.verbose_interactions:
                print(f"Key send failed: {e}")
            return False
    
    def send_key_sequence(self, widget: QWidget, sequence: str) -> bool:
        """Send a sequence of keys to widget"""
        try:
            if self.verbose_interactions:
                print(f"Sending key sequence '{sequence}' to widget {widget.__class__.__name__}")
            
            QTest.keyClicks(widget, sequence)
            self._process_events()
            return True
            
        except Exception as e:
            if self.verbose_interactions:
                print(f"Key sequence failed: {e}")
            return False
    
    def move_mouse_to_widget(self, widget: QWidget, position: Optional[QPoint] = None) -> bool:
        """Move mouse to widget position"""
        try:
            if position is None:
                position = widget.rect().center()
            
            if self.verbose_interactions:
                print(f"Moving mouse to {position} on widget {widget.__class__.__name__}")
            
            QTest.mouseMove(widget, position)
            self._process_events()
            return True
            
        except Exception as e:
            if self.verbose_interactions:
                print(f"Mouse move failed: {e}")
            return False
    
    def drag_and_drop(self, source_widget: QWidget, target_widget: QWidget,
                     source_pos: Optional[QPoint] = None,
                     target_pos: Optional[QPoint] = None) -> bool:
        """Simulate drag and drop between widgets"""
        try:
            if source_pos is None:
                source_pos = source_widget.rect().center()
            if target_pos is None:
                target_pos = target_widget.rect().center()
            
            if self.verbose_interactions:
                print(f"Dragging from {source_widget.__class__.__name__} to {target_widget.__class__.__name__}")
            
            # Start drag
            QTest.mousePress(source_widget, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, source_pos)
            self._process_events()
            
            # Move to target
            QTest.mouseMove(target_widget, target_pos)
            self._process_events()
            
            # Drop
            QTest.mouseRelease(target_widget, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, target_pos)
            self._process_events()
            
            return True
            
        except Exception as e:
            if self.verbose_interactions:
                print(f"Drag and drop failed: {e}")
            return False
    
    def resize_widget(self, widget: QWidget, width: int, height: int) -> bool:
        """Resize widget to specified dimensions"""
        try:
            if self.verbose_interactions:
                print(f"Resizing widget {widget.__class__.__name__} to {width}x{height}")
            
            widget.resize(width, height)
            self._process_events()
            return True
            
        except Exception as e:
            if self.verbose_interactions:
                print(f"Widget resize failed: {e}")
            return False
    
    # =========================================================================
    # Widget State Validation
    # =========================================================================
    
    def validate_widget_property(self, widget: QWidget, property_name: str,
                                expected_value: Any, comparison_type: str = "equal") -> ValidationResult:
        """Validate widget property value"""
        try:
            if not hasattr(widget, property_name):
                return ValidationResult.FAIL
            
            actual_value = getattr(widget, property_name)
            
            if comparison_type == "equal":
                return ValidationResult.PASS if actual_value == expected_value else ValidationResult.FAIL
            elif comparison_type == "not_equal":
                return ValidationResult.PASS if actual_value != expected_value else ValidationResult.FAIL
            elif comparison_type == "greater":
                return ValidationResult.PASS if actual_value > expected_value else ValidationResult.FAIL
            elif comparison_type == "less":
                return ValidationResult.PASS if actual_value < expected_value else ValidationResult.FAIL
            elif comparison_type == "contains":
                return ValidationResult.PASS if expected_value in actual_value else ValidationResult.FAIL
            else:
                return ValidationResult.FAIL
                
        except Exception:
            return ValidationResult.FAIL
    
    def validate_widget_visibility(self, widget: QWidget, should_be_visible: bool) -> ValidationResult:
        """Validate widget visibility state"""
        try:
            is_visible = widget.isVisible()
            return ValidationResult.PASS if is_visible == should_be_visible else ValidationResult.FAIL
        except Exception:
            return ValidationResult.FAIL
    
    def validate_widget_enabled(self, widget: QWidget, should_be_enabled: bool) -> ValidationResult:
        """Validate widget enabled state"""
        try:
            is_enabled = widget.isEnabled()
            return ValidationResult.PASS if is_enabled == should_be_enabled else ValidationResult.FAIL
        except Exception:
            return ValidationResult.FAIL
    
    def validate_widget_size(self, widget: QWidget, expected_width: int, expected_height: int,
                           tolerance: int = 0) -> ValidationResult:
        """Validate widget size"""
        try:
            size = widget.size()
            width_ok = abs(size.width() - expected_width) <= tolerance
            height_ok = abs(size.height() - expected_height) <= tolerance
            return ValidationResult.PASS if width_ok and height_ok else ValidationResult.FAIL
        except Exception:
            return ValidationResult.FAIL
    
    def validate_widget_position(self, widget: QWidget, expected_x: int, expected_y: int,
                               tolerance: int = 0) -> ValidationResult:
        """Validate widget position"""
        try:
            pos = widget.pos()
            x_ok = abs(pos.x() - expected_x) <= tolerance
            y_ok = abs(pos.y() - expected_y) <= tolerance
            return ValidationResult.PASS if x_ok and y_ok else ValidationResult.FAIL
        except Exception:
            return ValidationResult.FAIL
    
    # =========================================================================
    # Widget-Specific Testing
    # =========================================================================
    
    def test_button_functionality(self, button: QPushButton) -> Dict[str, ValidationResult]:
        """Test button-specific functionality"""
        results = {}
        
        # Test click functionality
        clicked = False
        button.clicked.connect(lambda: setattr(self, '_button_clicked', True))
        
        self._button_clicked = False
        self.click_widget(button)
        results['click_signal'] = ValidationResult.PASS if self._button_clicked else ValidationResult.FAIL
        
        # Test enabled/disabled states
        button.setEnabled(False)
        results['disable_state'] = self.validate_widget_enabled(button, False)
        
        button.setEnabled(True)
        results['enable_state'] = self.validate_widget_enabled(button, True)
        
        # Test text property
        original_text = button.text()
        test_text = "Test Button"
        button.setText(test_text)
        results['text_property'] = self.validate_widget_property(button, 'text', test_text)
        button.setText(original_text)
        
        return results
    
    def test_line_edit_functionality(self, line_edit: QLineEdit) -> Dict[str, ValidationResult]:
        """Test line edit functionality"""
        results = {}
        
        # Test text input
        test_text = "Hello World"
        line_edit.clear()
        self.send_key_sequence(line_edit, test_text)
        results['text_input'] = self.validate_widget_property(line_edit, 'text', test_text)
        
        # Test clear functionality
        line_edit.clear()
        results['clear_text'] = self.validate_widget_property(line_edit, 'text', "")
        
        # Test selection
        line_edit.setText(test_text)
        line_edit.selectAll()
        results['text_selection'] = ValidationResult.PASS if line_edit.hasSelectedText() else ValidationResult.FAIL
        
        # Test readonly state
        line_edit.setReadOnly(True)
        results['readonly_state'] = ValidationResult.PASS if line_edit.isReadOnly() else ValidationResult.FAIL
        
        line_edit.setReadOnly(False)
        results['editable_state'] = ValidationResult.PASS if not line_edit.isReadOnly() else ValidationResult.FAIL
        
        return results
    
    def test_table_functionality(self, table: QTableWidget) -> Dict[str, ValidationResult]:
        """Test table widget functionality"""
        results = {}
        
        # Test basic properties
        results['row_count'] = ValidationResult.PASS if table.rowCount() >= 0 else ValidationResult.FAIL
        results['column_count'] = ValidationResult.PASS if table.columnCount() >= 0 else ValidationResult.FAIL
        
        # Test cell selection if table has content
        if table.rowCount() > 0 and table.columnCount() > 0:
            table.setCurrentCell(0, 0)
            results['cell_selection'] = ValidationResult.PASS if table.currentRow() == 0 and table.currentColumn() == 0 else ValidationResult.FAIL
        else:
            results['cell_selection'] = ValidationResult.SKIP
        
        # Test sorting if headers are visible
        if table.horizontalHeader().isVisible():
            table.setSortingEnabled(True)
            results['sorting_enabled'] = ValidationResult.PASS if table.isSortingEnabled() else ValidationResult.FAIL
        else:
            results['sorting_enabled'] = ValidationResult.SKIP
        
        return results
    
    def test_combo_box_functionality(self, combo_box: QComboBox) -> Dict[str, ValidationResult]:
        """Test combo box functionality"""
        results = {}
        
        # Test item count
        results['item_count'] = ValidationResult.PASS if combo_box.count() >= 0 else ValidationResult.FAIL
        
        # Test selection if items exist
        if combo_box.count() > 0:
            original_index = combo_box.currentIndex()
            combo_box.setCurrentIndex(0)
            results['item_selection'] = ValidationResult.PASS if combo_box.currentIndex() == 0 else ValidationResult.FAIL
            combo_box.setCurrentIndex(original_index)
        else:
            results['item_selection'] = ValidationResult.SKIP
        
        # Test editable state
        if combo_box.isEditable():
            test_text = "Test Item"
            combo_box.setEditText(test_text)
            results['editable_text'] = self.validate_widget_property(combo_box, 'currentText', test_text)
        else:
            results['editable_text'] = ValidationResult.SKIP
        
        return results
    
    def test_progress_bar_functionality(self, progress_bar: QProgressBar) -> Dict[str, ValidationResult]:
        """Test progress bar functionality"""
        results = {}
        
        # Test value range
        min_val = progress_bar.minimum()
        max_val = progress_bar.maximum()
        results['range_validity'] = ValidationResult.PASS if min_val <= max_val else ValidationResult.FAIL
        
        # Test value setting
        test_value = min_val + (max_val - min_val) // 2
        progress_bar.setValue(test_value)
        results['value_setting'] = self.validate_widget_property(progress_bar, 'value', test_value)
        
        # Test percentage calculation
        expected_percentage = int((test_value - min_val) / (max_val - min_val) * 100) if max_val > min_val else 0
        actual_percentage = int(progress_bar.value() / progress_bar.maximum() * 100) if progress_bar.maximum() > 0 else 0
        results['percentage_calculation'] = ValidationResult.PASS if abs(actual_percentage - expected_percentage) <= 1 else ValidationResult.FAIL
        
        return results
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def _process_events(self):
        """Process pending events"""
        QApplication.processEvents()
        if self.event_delay > 0:
            QTest.qWait(self.event_delay)
    
    def wait_for_condition(self, condition: Callable[[], bool], timeout_ms: int = None) -> bool:
        """Wait for a condition to become true"""
        if timeout_ms is None:
            timeout_ms = self.default_timeout
        
        start_time = time.time()
        while time.time() - start_time < timeout_ms / 1000:
            if condition():
                return True
            self._process_events()
            QTest.qWait(10)
        
        return False
    
    def wait_for_widget_property(self, widget: QWidget, property_name: str,
                                expected_value: Any, timeout_ms: int = None) -> bool:
        """Wait for widget property to reach expected value"""
        return self.wait_for_condition(
            lambda: hasattr(widget, property_name) and getattr(widget, property_name) == expected_value,
            timeout_ms
        )
    
    def capture_widget_state(self, widget: QWidget) -> Dict[str, Any]:
        """Capture current widget state for comparison"""
        state = {
            'class_name': widget.__class__.__name__,
            'visible': widget.isVisible(),
            'enabled': widget.isEnabled(),
            'size': (widget.width(), widget.height()),
            'position': (widget.x(), widget.y()),
        }
        
        # Add widget-specific properties
        if isinstance(widget, QPushButton):
            state.update({
                'text': widget.text(),
                'checkable': widget.isCheckable(),
                'checked': widget.isChecked() if widget.isCheckable() else None
            })
        elif isinstance(widget, QLineEdit):
            state.update({
                'text': widget.text(),
                'placeholder_text': widget.placeholderText(),
                'readonly': widget.isReadOnly(),
                'has_selection': widget.hasSelectedText()
            })
        elif isinstance(widget, QTableWidget):
            state.update({
                'row_count': widget.rowCount(),
                'column_count': widget.columnCount(),
                'current_row': widget.currentRow(),
                'current_column': widget.currentColumn(),
                'sorting_enabled': widget.isSortingEnabled()
            })
        elif isinstance(widget, QComboBox):
            state.update({
                'count': widget.count(),
                'current_index': widget.currentIndex(),
                'current_text': widget.currentText(),
                'editable': widget.isEditable()
            })
        elif isinstance(widget, QProgressBar):
            state.update({
                'value': widget.value(),
                'minimum': widget.minimum(),
                'maximum': widget.maximum(),
                'text_visible': widget.isTextVisible()
            })
        
        return state


# =============================================================================
# Convenience Functions
# =============================================================================

def create_widget_test_case(name: str, widget: QWidget, 
                           test_function: Callable[[WidgetTester, QWidget], Dict[str, ValidationResult]],
                           description: str = "") -> WidgetTestCase:
    """Create a widget test case from a test function"""
    
    class CustomWidgetTestCase(WidgetTestCase):
        def execute(self) -> TestResult:
            try:
                tester = WidgetTester()
                validation_results = test_function(tester, self.widget)
                
                # Check if all validations passed
                all_passed = all(result == ValidationResult.PASS for result in validation_results.values())
                
                # Create summary message
                passed_count = sum(1 for r in validation_results.values() if r == ValidationResult.PASS)
                total_count = len(validation_results)
                skipped_count = sum(1 for r in validation_results.values() if r == ValidationResult.SKIP)
                
                message = f"Widget test completed: {passed_count}/{total_count} validations passed"
                if skipped_count > 0:
                    message += f", {skipped_count} skipped"
                
                return TestResult(
                    test_name=self.name,
                    category=self.category,
                    passed=all_passed,
                    message=message,
                    execution_time=0.0,  # Will be set by runner
                    actual_result=validation_results,
                    priority=self.priority
                )
                
            except Exception as e:
                return TestResult(
                    test_name=self.name,
                    category=self.category,
                    passed=False,
                    message=str(e),
                    execution_time=0.0,  # Will be set by runner
                    priority=self.priority
                )
    
    return CustomWidgetTestCase(name, description or f"Widget test: {name}", widget)


def test_widget_quickly(widget: QWidget, test_name: str = "Quick Widget Test") -> TestResult:
    """Perform a quick basic test on any widget"""
    tester = WidgetTester()
    
    def quick_test(widget_tester: WidgetTester, test_widget: QWidget) -> Dict[str, ValidationResult]:
        results = {}
        
        # Basic state tests
        results['widget_exists'] = ValidationResult.PASS if test_widget is not None else ValidationResult.FAIL
        results['widget_visible'] = widget_tester.validate_widget_visibility(test_widget, True)
        results['widget_enabled'] = widget_tester.validate_widget_enabled(test_widget, True)
        
        # Widget-specific tests
        if isinstance(test_widget, QPushButton):
            results.update(widget_tester.test_button_functionality(test_widget))
        elif isinstance(test_widget, QLineEdit):
            results.update(widget_tester.test_line_edit_functionality(test_widget))
        elif isinstance(test_widget, QTableWidget):
            results.update(widget_tester.test_table_functionality(test_widget))
        elif isinstance(test_widget, QComboBox):
            results.update(widget_tester.test_combo_box_functionality(test_widget))
        elif isinstance(test_widget, QProgressBar):
            results.update(widget_tester.test_progress_bar_functionality(test_widget))
        
        return results
    
    test_case = create_widget_test_case(test_name, widget, quick_test)
 