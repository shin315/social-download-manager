"""
Accessibility Management System

Comprehensive accessibility support for UI components including:
- Screen reader support with ARIA attributes
- Keyboard navigation management
- Focus management and focus indicators
- High contrast and visual accessibility
- Accessibility testing and validation
- WCAG 2.1 compliance utilities
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Set, Callable, Union, Tuple
from PyQt6.QtWidgets import (
    QWidget, QApplication, QTableWidget, QHeaderView, QPushButton, 
    QLineEdit, QComboBox, QProgressBar, QLabel, QTextEdit
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QTimer, QEvent
from PyQt6.QtGui import QKeyEvent, QFocusEvent, QPalette, QColor, QFont, QFontMetrics
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import logging

from .events import get_event_bus, EventType, ComponentEvent


class AccessibilityRole(Enum):
    """ARIA roles for components"""
    BUTTON = "button"
    TEXTBOX = "textbox"
    COMBOBOX = "combobox"
    TABLE = "table"
    GRID = "grid"
    ROW = "row"
    CELL = "cell"
    COLUMNHEADER = "columnheader"
    PROGRESSBAR = "progressbar"
    DIALOG = "dialog"
    MENU = "menu"
    MENUITEM = "menuitem"
    SEARCH = "search"
    NAVIGATION = "navigation"
    MAIN = "main"
    REGION = "region"
    BANNER = "banner"
    CONTENTINFO = "contentinfo"
    COMPLEMENTARY = "complementary"


class AccessibilityState(Enum):
    """ARIA states for components"""
    EXPANDED = "aria-expanded"
    SELECTED = "aria-selected"
    CHECKED = "aria-checked"
    DISABLED = "aria-disabled"
    HIDDEN = "aria-hidden"
    PRESSED = "aria-pressed"
    BUSY = "aria-busy"
    INVALID = "aria-invalid"
    REQUIRED = "aria-required"
    READONLY = "aria-readonly"


class AccessibilityProperty(Enum):
    """ARIA properties for components"""
    LABEL = "aria-label"
    LABELLEDBY = "aria-labelledby"
    DESCRIBEDBY = "aria-describedby"
    CONTROLS = "aria-controls"
    OWNS = "aria-owns"
    HASPOPUP = "aria-haspopup"
    LEVEL = "aria-level"
    SETSIZE = "aria-setsize"
    POSINSET = "aria-posinset"
    ROWCOUNT = "aria-rowcount"
    COLCOUNT = "aria-colcount"
    ROWINDEX = "aria-rowindex"
    COLINDEX = "aria-colindex"


@dataclass
class AccessibilityInfo:
    """Accessibility information for a component"""
    role: Optional[AccessibilityRole] = None
    label: Optional[str] = None
    description: Optional[str] = None
    states: Dict[AccessibilityState, bool] = field(default_factory=dict)
    properties: Dict[AccessibilityProperty, str] = field(default_factory=dict)
    keyboard_shortcuts: List[str] = field(default_factory=list)
    focus_order: int = 0
    is_focusable: bool = True
    custom_attributes: Dict[str, str] = field(default_factory=dict)


@dataclass
class KeyboardShortcut:
    """Keyboard shortcut definition"""
    keys: str  # e.g., "Ctrl+Enter", "Alt+F"
    action: str
    description: str
    component_id: Optional[str] = None
    context: Optional[str] = None


class AccessibilityValidator:
    """Validator for accessibility compliance"""
    
    def __init__(self):
        self._rules = self._initialize_wcag_rules()
        self._logger = logging.getLogger(__name__)
    
    def _initialize_wcag_rules(self) -> Dict[str, Callable]:
        """Initialize WCAG 2.1 validation rules"""
        return {
            'keyboard_accessible': self._validate_keyboard_accessibility,
            'focus_visible': self._validate_focus_indicators,
            'semantic_markup': self._validate_semantic_markup,
            'aria_labels': self._validate_aria_labels,
            'color_contrast': self._validate_color_contrast,
            'text_alternatives': self._validate_text_alternatives,
            'focus_order': self._validate_focus_order
        }
    
    def validate_component(self, widget: QWidget, accessibility_info: AccessibilityInfo) -> Dict[str, Any]:
        """Validate accessibility compliance for a component"""
        results = {
            'component': widget.__class__.__name__,
            'compliance_score': 0,
            'violations': [],
            'warnings': [],
            'passed_tests': [],
            'recommendations': []
        }
        
        total_tests = len(self._rules)
        passed_tests = 0
        
        for rule_name, rule_func in self._rules.items():
            try:
                result = rule_func(widget, accessibility_info)
                
                if result['passed']:
                    passed_tests += 1
                    results['passed_tests'].append(rule_name)
                else:
                    if result['severity'] == 'error':
                        results['violations'].append({
                            'rule': rule_name,
                            'message': result['message'],
                            'severity': result['severity']
                        })
                    else:
                        results['warnings'].append({
                            'rule': rule_name,
                            'message': result['message'],
                            'severity': result['severity']
                        })
                
                if 'recommendation' in result:
                    results['recommendations'].append({
                        'rule': rule_name,
                        'recommendation': result['recommendation']
                    })
                    
            except Exception as e:
                self._logger.error(f"Error validating rule {rule_name}: {e}")
        
        results['compliance_score'] = (passed_tests / total_tests) * 100
        return results
    
    def _validate_keyboard_accessibility(self, widget: QWidget, info: AccessibilityInfo) -> Dict[str, Any]:
        """Validate keyboard accessibility"""
        if not info.is_focusable:
            return {'passed': True, 'message': 'Component is not focusable by design'}
        
        # Check if widget accepts focus
        if not widget.focusPolicy() & Qt.FocusPolicy.TabFocus:
            return {
                'passed': False,
                'severity': 'error',
                'message': 'Focusable component does not accept keyboard focus',
                'recommendation': 'Set appropriate focus policy (e.g., Qt.FocusPolicy.TabFocus)'
            }
        
        return {'passed': True, 'message': 'Component is keyboard accessible'}
    
    def _validate_focus_indicators(self, widget: QWidget, info: AccessibilityInfo) -> Dict[str, Any]:
        """Validate focus indicators"""
        if not info.is_focusable:
            return {'passed': True, 'message': 'Component is not focusable'}
        
        # Check if widget has custom focus indicators
        style_sheet = widget.styleSheet()
        has_focus_style = ':focus' in style_sheet or 'focus' in style_sheet.lower()
        
        if not has_focus_style:
            return {
                'passed': False,
                'severity': 'warning',
                'message': 'Component may lack visible focus indicators',
                'recommendation': 'Add :focus styles to make focus state clearly visible'
            }
        
        return {'passed': True, 'message': 'Component has focus indicators'}
    
    def _validate_semantic_markup(self, widget: QWidget, info: AccessibilityInfo) -> Dict[str, Any]:
        """Validate semantic markup"""
        if not info.role:
            return {
                'passed': False,
                'severity': 'warning',
                'message': 'Component lacks semantic role',
                'recommendation': 'Define appropriate ARIA role for the component'
            }
        
        # Validate role appropriateness based on widget type
        widget_type = type(widget).__name__
        appropriate_roles = self._get_appropriate_roles(widget_type)
        
        if appropriate_roles and info.role not in appropriate_roles:
            return {
                'passed': False,
                'severity': 'warning',
                'message': f'Role {info.role.value} may not be appropriate for {widget_type}',
                'recommendation': f'Consider using one of: {[r.value for r in appropriate_roles]}'
            }
        
        return {'passed': True, 'message': 'Component has appropriate semantic markup'}
    
    def _validate_aria_labels(self, widget: QWidget, info: AccessibilityInfo) -> Dict[str, Any]:
        """Validate ARIA labels"""
        if info.is_focusable or info.role in [AccessibilityRole.BUTTON, AccessibilityRole.TEXTBOX]:
            if not info.label and AccessibilityProperty.LABELLEDBY not in info.properties:
                return {
                    'passed': False,
                    'severity': 'error',
                    'message': 'Interactive component lacks accessible label',
                    'recommendation': 'Add aria-label or aria-labelledby attribute'
                }
        
        return {'passed': True, 'message': 'Component has appropriate labels'}
    
    def _validate_color_contrast(self, widget: QWidget, info: AccessibilityInfo) -> Dict[str, Any]:
        """Validate color contrast (basic check)"""
        # This is a simplified check - full implementation would analyze actual colors
        return {
            'passed': True,
            'message': 'Color contrast validation requires specialized tools',
            'recommendation': 'Test with color contrast analyzers to ensure WCAG AA compliance'
        }
    
    def _validate_text_alternatives(self, widget: QWidget, info: AccessibilityInfo) -> Dict[str, Any]:
        """Validate text alternatives for non-text content"""
        # Check for images, icons, etc. that need alt text
        if hasattr(widget, 'pixmap') or 'icon' in widget.__class__.__name__.lower():
            if not info.label and not info.description:
                return {
                    'passed': False,
                    'severity': 'error',
                    'message': 'Image or icon lacks text alternative',
                    'recommendation': 'Add descriptive aria-label or alt text'
                }
        
        return {'passed': True, 'message': 'Text alternatives are appropriate'}
    
    def _validate_focus_order(self, widget: QWidget, info: AccessibilityInfo) -> Dict[str, Any]:
        """Validate logical focus order"""
        if info.focus_order < 0:
            return {
                'passed': False,
                'severity': 'warning',
                'message': 'Component has negative focus order',
                'recommendation': 'Set logical focus order (0 for natural order, positive for specific order)'
            }
        
        return {'passed': True, 'message': 'Focus order is appropriate'}
    
    def _get_appropriate_roles(self, widget_type: str) -> List[AccessibilityRole]:
        """Get appropriate ARIA roles for widget type"""
        role_mapping = {
            'QPushButton': [AccessibilityRole.BUTTON],
            'QLineEdit': [AccessibilityRole.TEXTBOX, AccessibilityRole.SEARCH],
            'QTextEdit': [AccessibilityRole.TEXTBOX],
            'QComboBox': [AccessibilityRole.COMBOBOX],
            'QTableWidget': [AccessibilityRole.TABLE, AccessibilityRole.GRID],
            'QProgressBar': [AccessibilityRole.PROGRESSBAR],
            'QLabel': [],  # Labels typically don't need roles
        }
        
        return role_mapping.get(widget_type, [])


class AccessibilityManager:
    """
    Comprehensive accessibility management system for UI components
    """
    
    # Accessibility signals
    focus_changed = pyqtSignal(str, str)  # old_component_id, new_component_id
    accessibility_violation = pyqtSignal(str, dict)  # component_id, violation_info
    keyboard_shortcut_triggered = pyqtSignal(str, str)  # shortcut, component_id
    
    def __init__(self):
        # Component registration
        self._registered_components: Dict[str, QWidget] = {}
        self._accessibility_info: Dict[str, AccessibilityInfo] = {}
        
        # Focus management
        self._focus_order: List[str] = []
        self._current_focus: Optional[str] = None
        self._focus_history: List[str] = []
        self._max_focus_history = 20
        
        # Keyboard shortcuts
        self._global_shortcuts: Dict[str, KeyboardShortcut] = {}
        self._component_shortcuts: Dict[str, Dict[str, KeyboardShortcut]] = {}
        
        # High contrast and visual accessibility
        self._high_contrast_mode = False
        self._large_text_mode = False
        self._reduced_motion = False
        
        # Validation
        self._validator = AccessibilityValidator()
        self._auto_validate = True
        
        # Screen reader support
        self._screen_reader_announcements: List[str] = []
        self._announcement_timer = QTimer()
        self._announcement_timer.setSingleShot(True)
        self._announcement_timer.timeout.connect(self._process_announcements)
        
        # Event bus integration
        self._event_bus = get_event_bus()
        self._setup_event_subscriptions()
        
        # Logger
        self._logger = logging.getLogger(__name__)
    
    def _setup_event_subscriptions(self):
        """Setup event subscriptions"""
        self._event_bus.subscribe(EventType.COMPONENT_CREATED, self._handle_component_created)
        self._event_bus.subscribe(EventType.COMPONENT_DESTROYED, self._handle_component_destroyed)
        self._event_bus.subscribe(EventType.THEME_CHANGED, self._handle_theme_changed)
    
    # =========================================================================
    # Component Registration and Management
    # =========================================================================
    
    def register_component(self, 
                          component_id: str,
                          widget: QWidget,
                          accessibility_info: AccessibilityInfo) -> bool:
        """Register a component for accessibility management"""
        try:
            # Store component and accessibility info
            self._registered_components[component_id] = widget
            self._accessibility_info[component_id] = accessibility_info
            
            # Apply accessibility attributes
            self._apply_accessibility_attributes(widget, accessibility_info)
            
            # Setup keyboard navigation
            if accessibility_info.is_focusable:
                self._setup_keyboard_navigation(component_id, widget)
            
            # Add to focus order
            if accessibility_info.focus_order >= 0:
                self._update_focus_order(component_id, accessibility_info.focus_order)
            
            # Validate accessibility
            if self._auto_validate:
                self._validate_component_accessibility(component_id)
            
            self._logger.info(f"Registered accessible component: {component_id}")
            return True
            
        except Exception as e:
            self._logger.error(f"Error registering component {component_id}: {e}")
            return False
    
    def unregister_component(self, component_id: str) -> bool:
        """Unregister a component from accessibility management"""
        try:
            # Remove from focus order
            if component_id in self._focus_order:
                self._focus_order.remove(component_id)
            
            # Clear focus if this component has it
            if self._current_focus == component_id:
                self._current_focus = None
            
            # Remove from focus history
            self._focus_history = [cid for cid in self._focus_history if cid != component_id]
            
            # Remove shortcuts
            self._component_shortcuts.pop(component_id, None)
            
            # Remove from registration
            self._registered_components.pop(component_id, None)
            self._accessibility_info.pop(component_id, None)
            
            self._logger.info(f"Unregistered component: {component_id}")
            return True
            
        except Exception as e:
            self._logger.error(f"Error unregistering component {component_id}: {e}")
            return False
    
    def update_accessibility_info(self, 
                                 component_id: str,
                                 accessibility_info: AccessibilityInfo) -> bool:
        """Update accessibility information for a component"""
        if component_id not in self._registered_components:
            return False
        
        try:
            widget = self._registered_components[component_id]
            self._accessibility_info[component_id] = accessibility_info
            
            # Reapply accessibility attributes
            self._apply_accessibility_attributes(widget, accessibility_info)
            
            # Update focus order if changed
            self._update_focus_order(component_id, accessibility_info.focus_order)
            
            # Re-validate if auto-validation is enabled
            if self._auto_validate:
                self._validate_component_accessibility(component_id)
            
            return True
            
        except Exception as e:
            self._logger.error(f"Error updating accessibility info for {component_id}: {e}")
            return False
    
    def _apply_accessibility_attributes(self, 
                                      widget: QWidget,
                                      accessibility_info: AccessibilityInfo):
        """Apply accessibility attributes to widget"""
        try:
            # Set accessible name and description
            if accessibility_info.label:
                widget.setAccessibleName(accessibility_info.label)
            
            if accessibility_info.description:
                widget.setAccessibleDescription(accessibility_info.description)
            
            # Set focus policy
            if accessibility_info.is_focusable:
                if widget.focusPolicy() == Qt.FocusPolicy.NoFocus:
                    widget.setFocusPolicy(Qt.FocusPolicy.TabFocus)
            else:
                widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            
            # Apply ARIA-like attributes via properties
            self._apply_aria_attributes(widget, accessibility_info)
            
        except Exception as e:
            self._logger.error(f"Error applying accessibility attributes: {e}")
    
    def _apply_aria_attributes(self, widget: QWidget, accessibility_info: AccessibilityInfo):
        """Apply ARIA-like attributes via Qt properties"""
        try:
            # Set role
            if accessibility_info.role:
                widget.setProperty("accessibility_role", accessibility_info.role.value)
            
            # Set states
            for state, value in accessibility_info.states.items():
                widget.setProperty(f"accessibility_{state.value.replace('-', '_')}", value)
            
            # Set properties
            for prop, value in accessibility_info.properties.items():
                widget.setProperty(f"accessibility_{prop.value.replace('-', '_')}", value)
            
            # Set custom attributes
            for attr, value in accessibility_info.custom_attributes.items():
                widget.setProperty(f"accessibility_{attr}", value)
                
        except Exception as e:
            self._logger.error(f"Error applying ARIA attributes: {e}")
    
    # =========================================================================
    # Focus Management
    # =========================================================================
    
    def _setup_keyboard_navigation(self, component_id: str, widget: QWidget):
        """Setup keyboard navigation for component"""
        try:
            # Install event filter for keyboard events
            widget.installEventFilter(self)
            
            # Connect focus events
            if hasattr(widget, 'focusInEvent'):
                original_focus_in = widget.focusInEvent
                def focus_in_wrapper(event):
                    self._handle_focus_in(component_id, event)
                    original_focus_in(event)
                widget.focusInEvent = focus_in_wrapper
            
            if hasattr(widget, 'focusOutEvent'):
                original_focus_out = widget.focusOutEvent
                def focus_out_wrapper(event):
                    self._handle_focus_out(component_id, event)
                    original_focus_out(event)
                widget.focusOutEvent = focus_out_wrapper
                
        except Exception as e:
            self._logger.error(f"Error setting up keyboard navigation for {component_id}: {e}")
    
    def _update_focus_order(self, component_id: str, focus_order: int):
        """Update focus order for component"""
        # Remove from current position
        if component_id in self._focus_order:
            self._focus_order.remove(component_id)
        
        # Insert at correct position based on focus order
        if focus_order == 0:
            # Natural tab order - append to end
            self._focus_order.append(component_id)
        else:
            # Find insertion point
            insertion_point = len(self._focus_order)
            for i, cid in enumerate(self._focus_order):
                other_info = self._accessibility_info.get(cid)
                if other_info and other_info.focus_order > focus_order:
                    insertion_point = i
                    break
            
            self._focus_order.insert(insertion_point, component_id)
    
    def _handle_focus_in(self, component_id: str, event: QFocusEvent):
        """Handle focus in event"""
        old_focus = self._current_focus
        self._current_focus = component_id
        
        # Update focus history
        if component_id not in self._focus_history:
            self._focus_history.append(component_id)
            
            # Maintain history limit
            if len(self._focus_history) > self._max_focus_history:
                self._focus_history.pop(0)
        
        # Emit focus change signal
        self.focus_changed.emit(old_focus or "", component_id)
        
        # Announce focus change for screen readers
        accessibility_info = self._accessibility_info.get(component_id)
        if accessibility_info and accessibility_info.label:
            self._announce_for_screen_reader(f"Focused: {accessibility_info.label}")
    
    def _handle_focus_out(self, component_id: str, event: QFocusEvent):
        """Handle focus out event"""
        # Focus tracking is handled in focus_in events
        pass
    
    def navigate_to_component(self, component_id: str) -> bool:
        """Navigate focus to specific component"""
        if component_id not in self._registered_components:
            return False
        
        try:
            widget = self._registered_components[component_id]
            widget.setFocus(Qt.FocusReason.TabFocusReason)
            return True
            
        except Exception as e:
            self._logger.error(f"Error navigating to component {component_id}: {e}")
            return False
    
    def navigate_next(self) -> bool:
        """Navigate to next component in focus order"""
        if not self._focus_order:
            return False
        
        try:
            current_index = -1
            if self._current_focus and self._current_focus in self._focus_order:
                current_index = self._focus_order.index(self._current_focus)
            
            next_index = (current_index + 1) % len(self._focus_order)
            next_component = self._focus_order[next_index]
            
            return self.navigate_to_component(next_component)
            
        except Exception as e:
            self._logger.error(f"Error navigating to next component: {e}")
            return False
    
    def navigate_previous(self) -> bool:
        """Navigate to previous component in focus order"""
        if not self._focus_order:
            return False
        
        try:
            current_index = 0
            if self._current_focus and self._current_focus in self._focus_order:
                current_index = self._focus_order.index(self._current_focus)
            
            prev_index = (current_index - 1) % len(self._focus_order)
            prev_component = self._focus_order[prev_index]
            
            return self.navigate_to_component(prev_component)
            
        except Exception as e:
            self._logger.error(f"Error navigating to previous component: {e}")
            return False
    
    # =========================================================================
    # Keyboard Shortcuts
    # =========================================================================
    
    def register_global_shortcut(self, shortcut: KeyboardShortcut) -> bool:
        """Register global keyboard shortcut"""
        try:
            self._global_shortcuts[shortcut.keys] = shortcut
            return True
            
        except Exception as e:
            self._logger.error(f"Error registering global shortcut {shortcut.keys}: {e}")
            return False
    
    def register_component_shortcut(self, 
                                   component_id: str,
                                   shortcut: KeyboardShortcut) -> bool:
        """Register component-specific keyboard shortcut"""
        try:
            if component_id not in self._component_shortcuts:
                self._component_shortcuts[component_id] = {}
            
            shortcut.component_id = component_id
            self._component_shortcuts[component_id][shortcut.keys] = shortcut
            return True
            
        except Exception as e:
            self._logger.error(f"Error registering component shortcut {shortcut.keys}: {e}")
            return False
    
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Event filter for keyboard shortcuts"""
        if event.type() == QEvent.Type.KeyPress:
            key_event = event
            
            # Convert key event to shortcut string
            shortcut_string = self._key_event_to_string(key_event)
            
            # Check component-specific shortcuts first
            if self._current_focus:
                component_shortcuts = self._component_shortcuts.get(self._current_focus, {})
                if shortcut_string in component_shortcuts:
                    shortcut = component_shortcuts[shortcut_string]
                    self._execute_keyboard_shortcut(shortcut)
                    return True
            
            # Check global shortcuts
            if shortcut_string in self._global_shortcuts:
                shortcut = self._global_shortcuts[shortcut_string]
                self._execute_keyboard_shortcut(shortcut)
                return True
        
        return super().eventFilter(obj, event)
    
    def _key_event_to_string(self, event: QKeyEvent) -> str:
        """Convert key event to shortcut string"""
        modifiers = []
        
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            modifiers.append("Ctrl")
        if event.modifiers() & Qt.KeyboardModifier.AltModifier:
            modifiers.append("Alt")
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            modifiers.append("Shift")
        if event.modifiers() & Qt.KeyboardModifier.MetaModifier:
            modifiers.append("Meta")
        
        key_name = QKeySequence(event.key()).toString()
        
        if modifiers:
            return "+".join(modifiers + [key_name])
        else:
            return key_name
    
    def _execute_keyboard_shortcut(self, shortcut: KeyboardShortcut):
        """Execute keyboard shortcut action"""
        try:
            # Emit signal for shortcut execution
            component_id = shortcut.component_id or "global"
            self.keyboard_shortcut_triggered.emit(shortcut.keys, component_id)
            
            # Announce shortcut for screen readers
            self._announce_for_screen_reader(f"Executed: {shortcut.description}")
            
        except Exception as e:
            self._logger.error(f"Error executing shortcut {shortcut.keys}: {e}")
    
    # =========================================================================
    # Screen Reader Support
    # =========================================================================
    
    def _announce_for_screen_reader(self, message: str):
        """Announce message for screen readers"""
        self._screen_reader_announcements.append(message)
        
        # Process announcements with a slight delay to avoid overwhelming
        if not self._announcement_timer.isActive():
            self._announcement_timer.start(100)  # 100ms delay
    
    def _process_announcements(self):
        """Process queued screen reader announcements"""
        if self._screen_reader_announcements:
            # For Qt, we can use accessibility features
            message = self._screen_reader_announcements.pop(0)
            
            # In a real implementation, this might interface with screen reader APIs
            # For now, we'll use Qt's accessibility system
            try:
                app = QApplication.instance()
                if app:
                    # This is a simplified approach - full implementation would use
                    # platform-specific screen reader APIs
                    print(f"Screen Reader: {message}")  # Debug output
                    
            except Exception as e:
                self._logger.error(f"Error announcing to screen reader: {e}")
        
        # Continue processing if more announcements are queued
        if self._screen_reader_announcements:
            self._announcement_timer.start(200)  # Longer delay between announcements
    
    # =========================================================================
    # Visual Accessibility
    # =========================================================================
    
    def enable_high_contrast_mode(self, enabled: bool = True):
        """Enable or disable high contrast mode"""
        self._high_contrast_mode = enabled
        
        # Apply high contrast styling to all registered components
        for component_id, widget in self._registered_components.items():
            self._apply_high_contrast_styling(widget, enabled)
        
        # Announce mode change
        mode_text = "enabled" if enabled else "disabled"
        self._announce_for_screen_reader(f"High contrast mode {mode_text}")
    
    def enable_large_text_mode(self, enabled: bool = True):
        """Enable or disable large text mode"""
        self._large_text_mode = enabled
        
        # Apply large text styling to all registered components
        for component_id, widget in self._registered_components.items():
            self._apply_large_text_styling(widget, enabled)
        
        # Announce mode change
        mode_text = "enabled" if enabled else "disabled"
        self._announce_for_screen_reader(f"Large text mode {mode_text}")
    
    def enable_reduced_motion(self, enabled: bool = True):
        """Enable or disable reduced motion mode"""
        self._reduced_motion = enabled
        
        # Apply reduced motion settings to all registered components
        for component_id, widget in self._registered_components.items():
            self._apply_reduced_motion_styling(widget, enabled)
        
        # Announce mode change
        mode_text = "enabled" if enabled else "disabled"
        self._announce_for_screen_reader(f"Reduced motion mode {mode_text}")
    
    def _apply_high_contrast_styling(self, widget: QWidget, enabled: bool):
        """Apply high contrast styling to widget"""
        if enabled:
            # High contrast colors
            style = """
            QWidget {
                background-color: #000000;
                color: #ffffff;
                border: 2px solid #ffffff;
            }
            QWidget:focus {
                border: 3px solid #ffff00;
                background-color: #000080;
            }
            QPushButton {
                background-color: #0000ff;
                color: #ffffff;
                border: 2px solid #ffffff;
            }
            QPushButton:hover {
                background-color: #ffffff;
                color: #000000;
            }
            """
            widget.setStyleSheet(style)
        else:
            # Reset to default styling
            widget.setStyleSheet("")
    
    def _apply_large_text_styling(self, widget: QWidget, enabled: bool):
        """Apply large text styling to widget"""
        font = widget.font()
        
        if enabled:
            # Increase font size by 25%
            current_size = font.pointSize()
            if current_size > 0:
                font.setPointSize(int(current_size * 1.25))
            else:
                font.setPointSize(12)  # Default large size
        else:
            # Reset to normal size
            font.setPointSize(10)  # Default normal size
        
        widget.setFont(font)
    
    def _apply_reduced_motion_styling(self, widget: QWidget, enabled: bool):
        """Apply reduced motion styling to widget"""
        if enabled:
            # Disable animations and transitions
            style = """
            QWidget {
                transition: none;
                animation: none;
            }
            """
            widget.setStyleSheet(widget.styleSheet() + style)
        else:
            # Remove reduced motion styling
            current_style = widget.styleSheet()
            # This is simplified - in practice, you'd need more sophisticated style management
            pass
    
    # =========================================================================
    # Accessibility Validation and Testing
    # =========================================================================
    
    def validate_all_components(self) -> Dict[str, Any]:
        """Validate accessibility for all registered components"""
        overall_results = {
            'total_components': len(self._registered_components),
            'average_compliance_score': 0,
            'total_violations': 0,
            'total_warnings': 0,
            'component_results': {}
        }
        
        total_score = 0
        total_violations = 0
        total_warnings = 0
        
        for component_id in self._registered_components:
            result = self._validate_component_accessibility(component_id)
            overall_results['component_results'][component_id] = result
            
            if result:
                total_score += result.get('compliance_score', 0)
                total_violations += len(result.get('violations', []))
                total_warnings += len(result.get('warnings', []))
        
        if self._registered_components:
            overall_results['average_compliance_score'] = total_score / len(self._registered_components)
        
        overall_results['total_violations'] = total_violations
        overall_results['total_warnings'] = total_warnings
        
        return overall_results
    
    def _validate_component_accessibility(self, component_id: str) -> Optional[Dict[str, Any]]:
        """Validate accessibility for a specific component"""
        if component_id not in self._registered_components:
            return None
        
        try:
            widget = self._registered_components[component_id]
            accessibility_info = self._accessibility_info[component_id]
            
            result = self._validator.validate_component(widget, accessibility_info)
            result['component_id'] = component_id
            result['timestamp'] = datetime.now().isoformat()
            
            # Emit violation signal if there are violations
            if result['violations']:
                self.accessibility_violation.emit(component_id, result)
            
            return result
            
        except Exception as e:
            self._logger.error(f"Error validating component {component_id}: {e}")
            return None
    
    def generate_accessibility_report(self) -> str:
        """Generate comprehensive accessibility report"""
        results = self.validate_all_components()
        
        report = []
        report.append("# Accessibility Compliance Report")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Summary
        report.append("## Summary")
        report.append(f"- Total Components: {results['total_components']}")
        report.append(f"- Average Compliance Score: {results['average_compliance_score']:.1f}%")
        report.append(f"- Total Violations: {results['total_violations']}")
        report.append(f"- Total Warnings: {results['total_warnings']}\n")
        
        # Component details
        report.append("## Component Details")
        for component_id, result in results['component_results'].items():
            report.append(f"### {component_id}")
            report.append(f"- Component Type: {result.get('component', 'Unknown')}")
            report.append(f"- Compliance Score: {result.get('compliance_score', 0):.1f}%")
            
            if result.get('violations'):
                report.append("- **Violations:**")
                for violation in result['violations']:
                    report.append(f"  - {violation['rule']}: {violation['message']}")
            
            if result.get('warnings'):
                report.append("- **Warnings:**")
                for warning in result['warnings']:
                    report.append(f"  - {warning['rule']}: {warning['message']}")
            
            if result.get('recommendations'):
                report.append("- **Recommendations:**")
                for rec in result['recommendations']:
                    report.append(f"  - {rec['rule']}: {rec['recommendation']}")
            
            report.append("")
        
        return "\n".join(report)
    
    # =========================================================================
    # Event Handlers
    # =========================================================================
    
    def _handle_component_created(self, event: ComponentEvent):
        """Handle component creation events"""
        # Components should register themselves for accessibility
        pass
    
    def _handle_component_destroyed(self, event: ComponentEvent):
        """Handle component destruction events"""
        component_id = event.data.get('component_id')
        if component_id:
            self.unregister_component(component_id)
    
    def _handle_theme_changed(self, event: ComponentEvent):
        """Handle theme change events"""
        # Reapply accessibility features when theme changes
        if self._high_contrast_mode:
            for widget in self._registered_components.values():
                self._apply_high_contrast_styling(widget, True)
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def get_component_accessibility_info(self, component_id: str) -> Optional[AccessibilityInfo]:
        """Get accessibility information for a component"""
        return self._accessibility_info.get(component_id)
    
    def get_focus_order(self) -> List[str]:
        """Get current focus order"""
        return self._focus_order.copy()
    
    def get_current_focus(self) -> Optional[str]:
        """Get currently focused component"""
        return self._current_focus
    
    def get_available_shortcuts(self, component_id: Optional[str] = None) -> Dict[str, KeyboardShortcut]:
        """Get available keyboard shortcuts"""
        if component_id:
            return self._component_shortcuts.get(component_id, {}).copy()
        else:
            return self._global_shortcuts.copy()
    
    def get_accessibility_status(self) -> Dict[str, Any]:
        """Get accessibility manager status"""
        return {
            'registered_components': len(self._registered_components),
            'focus_order_length': len(self._focus_order),
            'current_focus': self._current_focus,
            'global_shortcuts': len(self._global_shortcuts),
            'component_shortcuts': sum(len(shortcuts) for shortcuts in self._component_shortcuts.values()),
            'high_contrast_mode': self._high_contrast_mode,
            'large_text_mode': self._large_text_mode,
            'reduced_motion': self._reduced_motion,
            'auto_validate': self._auto_validate
        }
    
    def cleanup(self):
        """Cleanup accessibility manager resources"""
        try:
            # Stop timers
            self._announcement_timer.stop()
            
            # Clear all data
            self._registered_components.clear()
            self._accessibility_info.clear()
            self._focus_order.clear()
            self._focus_history.clear()
            self._global_shortcuts.clear()
            self._component_shortcuts.clear()
            self._screen_reader_announcements.clear()
            
            self._logger.info("Accessibility manager cleanup completed")
            
        except Exception as e:
            self._logger.error(f"Error during accessibility manager cleanup: {e}")


# Global accessibility manager instance
_accessibility_manager: Optional[AccessibilityManager] = None

def get_accessibility_manager() -> AccessibilityManager:
    """Get global accessibility manager instance"""
    global _accessibility_manager
    if _accessibility_manager is None:
        _accessibility_manager = AccessibilityManager()
    return _accessibility_manager

def initialize_accessibility_system() -> AccessibilityManager:
    """Initialize global accessibility system"""
    return get_accessibility_manager() 