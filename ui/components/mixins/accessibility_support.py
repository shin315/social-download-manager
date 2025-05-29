"""
Accessibility Support Mixin

Provides comprehensive accessibility features that components can inherit
to automatically integrate with the AccessibilityManager system and ensure
WCAG 2.1 compliance.
"""

from typing import Dict, Any, List, Optional, Callable
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QObject, pyqtSignal, QEvent
from PyQt6.QtGui import QKeyEvent, QFocusEvent
from abc import ABC, abstractmethod

from ..common.accessibility import (
    AccessibilityManager, AccessibilityInfo, AccessibilityRole, 
    AccessibilityState, AccessibilityProperty, KeyboardShortcut,
    get_accessibility_manager
)


class AccessibilitySupport:
    """
    Accessibility support mixin providing automatic accessibility features
    
    Features provided:
    - Automatic registration with AccessibilityManager
    - ARIA attributes and semantic markup
    - Keyboard navigation support
    - Focus management
    - Screen reader announcements
    - Accessibility validation
    - High contrast and visual accessibility modes
    """
    
    # Accessibility signals
    accessibility_focus_changed = pyqtSignal(bool)  # gained/lost focus
    accessibility_shortcut_triggered = pyqtSignal(str)  # shortcut keys
    accessibility_announced = pyqtSignal(str)  # announcement text
    
    def __init__(self, 
                 accessibility_role: AccessibilityRole = AccessibilityRole.REGION,
                 auto_register: bool = True):
        super().__init__()
        
        # Accessibility configuration
        self._accessibility_role = accessibility_role
        self._auto_register = auto_register
        self._accessibility_manager = get_accessibility_manager()
        
        # Component identification
        self._accessibility_component_id = f"{self.__class__.__name__}_{id(self)}"
        self._accessibility_registered = False
        
        # Accessibility information
        self._accessibility_info = AccessibilityInfo(
            role=accessibility_role,
            is_focusable=True
        )
        
        # Keyboard shortcuts
        self._component_shortcuts: List[KeyboardShortcut] = []
        
        # State tracking
        self._accessibility_states: Dict[AccessibilityState, bool] = {}
        self._accessibility_properties: Dict[AccessibilityProperty, str] = {}
        
        # Initialize accessibility if auto-register is enabled
        if self._auto_register and isinstance(self, QWidget):
            self._initialize_accessibility()
    
    def _initialize_accessibility(self):
        """Initialize accessibility features for this component"""
        try:
            # Setup default accessibility information
            self._setup_default_accessibility_info()
            
            # Register with accessibility manager
            if self._register_with_accessibility_manager():
                self._accessibility_registered = True
                
                # Setup keyboard navigation
                self._setup_accessibility_keyboard_navigation()
                
                # Apply initial accessibility attributes
                self._apply_accessibility_attributes()
                
                # Setup focus event handling
                self._setup_accessibility_focus_handling()
                
        except Exception as e:
            print(f"Error initializing accessibility for {self._accessibility_component_id}: {e}")
    
    def _setup_default_accessibility_info(self):
        """Setup default accessibility information based on component type"""
        if isinstance(self, QWidget):
            widget_class = self.__class__.__name__
            
            # Set appropriate role based on widget type
            if 'Button' in widget_class:
                self._accessibility_info.role = AccessibilityRole.BUTTON
            elif 'Table' in widget_class:
                self._accessibility_info.role = AccessibilityRole.TABLE
            elif 'Edit' in widget_class or 'Input' in widget_class:
                self._accessibility_info.role = AccessibilityRole.TEXTBOX
            elif 'Combo' in widget_class or 'Selector' in widget_class:
                self._accessibility_info.role = AccessibilityRole.COMBOBOX
            elif 'Progress' in widget_class:
                self._accessibility_info.role = AccessibilityRole.PROGRESSBAR
            elif 'Dialog' in widget_class or 'Popup' in widget_class:
                self._accessibility_info.role = AccessibilityRole.DIALOG
            
            # Set default label if none exists
            if not self._accessibility_info.label:
                # Try to get text from widget
                if hasattr(self, 'text') and callable(getattr(self, 'text')):
                    text = self.text()
                    if text:
                        self._accessibility_info.label = text
                elif hasattr(self, 'windowTitle'):
                    title = self.windowTitle()
                    if title:
                        self._accessibility_info.label = title
                else:
                    # Fallback to class name
                    self._accessibility_info.label = widget_class
            
            # Set focus order based on tab order
            if hasattr(self, 'tabOrder'):
                # This is a simplified approach
                self._accessibility_info.focus_order = 0
    
    def _register_with_accessibility_manager(self) -> bool:
        """Register this component with the accessibility manager"""
        if not isinstance(self, QWidget):
            return False
        
        return self._accessibility_manager.register_component(
            self._accessibility_component_id,
            self,
            self._accessibility_info
        )
    
    def _setup_accessibility_keyboard_navigation(self):
        """Setup keyboard navigation for accessibility"""
        if isinstance(self, QWidget):
            # Install event filter for keyboard events
            self.installEventFilter(self)
    
    def _apply_accessibility_attributes(self):
        """Apply accessibility attributes to the widget"""
        if isinstance(self, QWidget):
            # Apply ARIA states
            for state, value in self._accessibility_states.items():
                self.setProperty(f"aria_{state.value.replace('-', '_')}", value)
            
            # Apply ARIA properties
            for prop, value in self._accessibility_properties.items():
                self.setProperty(f"aria_{prop.value.replace('-', '_')}", value)
    
    def _setup_accessibility_focus_handling(self):
        """Setup focus event handling for accessibility"""
        if isinstance(self, QWidget):
            # Override focus events if possible
            if hasattr(self, 'focusInEvent'):
                original_focus_in = self.focusInEvent
                def accessibility_focus_in(event):
                    self._handle_accessibility_focus_in(event)
                    original_focus_in(event)
                self.focusInEvent = accessibility_focus_in
            
            if hasattr(self, 'focusOutEvent'):
                original_focus_out = self.focusOutEvent
                def accessibility_focus_out(event):
                    self._handle_accessibility_focus_out(event)
                    original_focus_out(event)
                self.focusOutEvent = accessibility_focus_out
    
    def _handle_accessibility_focus_in(self, event: QFocusEvent):
        """Handle focus in event for accessibility"""
        self.accessibility_focus_changed.emit(True)
        
        # Announce focus change
        if self._accessibility_info.label:
            self._announce_for_accessibility(f"Focused: {self._accessibility_info.label}")
    
    def _handle_accessibility_focus_out(self, event: QFocusEvent):
        """Handle focus out event for accessibility"""
        self.accessibility_focus_changed.emit(False)
    
    # =========================================================================
    # Public Accessibility API
    # =========================================================================
    
    def set_accessibility_label(self, label: str):
        """Set accessible label for this component"""
        self._accessibility_info.label = label
        
        if isinstance(self, QWidget):
            self.setAccessibleName(label)
        
        # Update with accessibility manager
        if self._accessibility_registered:
            self._accessibility_manager.update_accessibility_info(
                self._accessibility_component_id,
                self._accessibility_info
            )
    
    def set_accessibility_description(self, description: str):
        """Set accessible description for this component"""
        self._accessibility_info.description = description
        
        if isinstance(self, QWidget):
            self.setAccessibleDescription(description)
        
        # Update with accessibility manager
        if self._accessibility_registered:
            self._accessibility_manager.update_accessibility_info(
                self._accessibility_component_id,
                self._accessibility_info
            )
    
    def set_accessibility_role(self, role: AccessibilityRole):
        """Set accessibility role for this component"""
        self._accessibility_info.role = role
        
        if isinstance(self, QWidget):
            self.setProperty("accessibility_role", role.value)
        
        # Update with accessibility manager
        if self._accessibility_registered:
            self._accessibility_manager.update_accessibility_info(
                self._accessibility_component_id,
                self._accessibility_info
            )
    
    def set_accessibility_state(self, state: AccessibilityState, value: bool):
        """Set accessibility state for this component"""
        self._accessibility_states[state] = value
        self._accessibility_info.states[state] = value
        
        if isinstance(self, QWidget):
            self.setProperty(f"aria_{state.value.replace('-', '_')}", value)
        
        # Update with accessibility manager
        if self._accessibility_registered:
            self._accessibility_manager.update_accessibility_info(
                self._accessibility_component_id,
                self._accessibility_info
            )
    
    def set_accessibility_property(self, prop: AccessibilityProperty, value: str):
        """Set accessibility property for this component"""
        self._accessibility_properties[prop] = value
        self._accessibility_info.properties[prop] = value
        
        if isinstance(self, QWidget):
            self.setProperty(f"aria_{prop.value.replace('-', '_')}", value)
        
        # Update with accessibility manager
        if self._accessibility_registered:
            self._accessibility_manager.update_accessibility_info(
                self._accessibility_component_id,
                self._accessibility_info
            )
    
    def add_accessibility_shortcut(self, 
                                  keys: str,
                                  action: str,
                                  description: str,
                                  callback: Optional[Callable] = None):
        """Add keyboard shortcut for this component"""
        shortcut = KeyboardShortcut(
            keys=keys,
            action=action,
            description=description,
            component_id=self._accessibility_component_id
        )
        
        self._component_shortcuts.append(shortcut)
        self._accessibility_info.keyboard_shortcuts.append(keys)
        
        # Register with accessibility manager
        if self._accessibility_registered:
            self._accessibility_manager.register_component_shortcut(
                self._accessibility_component_id,
                shortcut
            )
        
        # Connect callback if provided
        if callback:
            self.accessibility_shortcut_triggered.connect(
                lambda triggered_keys: callback() if triggered_keys == keys else None
            )
    
    def set_accessibility_focus_order(self, order: int):
        """Set focus order for this component"""
        self._accessibility_info.focus_order = order
        
        # Update with accessibility manager
        if self._accessibility_registered:
            self._accessibility_manager.update_accessibility_info(
                self._accessibility_component_id,
                self._accessibility_info
            )
    
    def announce_for_accessibility(self, message: str):
        """Announce message for screen readers"""
        self._announce_for_accessibility(message)
    
    def _announce_for_accessibility(self, message: str):
        """Internal method to announce for accessibility"""
        # Emit signal
        self.accessibility_announced.emit(message)
        
        # Send to accessibility manager
        if self._accessibility_registered:
            # The accessibility manager handles screen reader announcements
            # This is done through the focus events and internal announcement system
            pass
    
    # =========================================================================
    # Focus Navigation Methods
    # =========================================================================
    
    def navigate_to_next_accessible_component(self) -> bool:
        """Navigate to next accessible component"""
        if self._accessibility_registered:
            return self._accessibility_manager.navigate_next()
        return False
    
    def navigate_to_previous_accessible_component(self) -> bool:
        """Navigate to previous accessible component"""
        if self._accessibility_registered:
            return self._accessibility_manager.navigate_previous()
        return False
    
    def navigate_to_specific_component(self, component_id: str) -> bool:
        """Navigate to specific accessible component"""
        if self._accessibility_registered:
            return self._accessibility_manager.navigate_to_component(component_id)
        return False
    
    # =========================================================================
    # Visual Accessibility Support
    # =========================================================================
    
    def enable_high_contrast_mode(self, enabled: bool = True):
        """Enable high contrast mode for this component"""
        if self._accessibility_registered:
            # The accessibility manager handles high contrast for all components
            self._accessibility_manager.enable_high_contrast_mode(enabled)
    
    def enable_large_text_mode(self, enabled: bool = True):
        """Enable large text mode for this component"""
        if self._accessibility_registered:
            # The accessibility manager handles large text for all components
            self._accessibility_manager.enable_large_text_mode(enabled)
    
    def enable_reduced_motion_mode(self, enabled: bool = True):
        """Enable reduced motion mode for this component"""
        if self._accessibility_registered:
            # The accessibility manager handles reduced motion for all components
            self._accessibility_manager.enable_reduced_motion(enabled)
    
    # =========================================================================
    # Event Handling
    # =========================================================================
    
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Event filter for accessibility keyboard shortcuts"""
        if event.type() == QEvent.Type.KeyPress and obj == self:
            key_event = event
            
            # Let accessibility manager handle shortcuts
            # The manager will emit signals that we can connect to
            pass
        
        # Call parent event filter if it exists
        if hasattr(super(), 'eventFilter'):
            return super().eventFilter(obj, event)
        
        return False
    
    # =========================================================================
    # Accessibility Information and Status
    # =========================================================================
    
    def get_accessibility_info(self) -> AccessibilityInfo:
        """Get accessibility information for this component"""
        return self._accessibility_info
    
    def get_accessibility_component_id(self) -> str:
        """Get accessibility component ID"""
        return self._accessibility_component_id
    
    def is_accessibility_registered(self) -> bool:
        """Check if component is registered with accessibility manager"""
        return self._accessibility_registered
    
    def get_accessibility_shortcuts(self) -> List[KeyboardShortcut]:
        """Get keyboard shortcuts for this component"""
        return self._component_shortcuts.copy()
    
    def validate_accessibility(self) -> Dict[str, Any]:
        """Validate accessibility compliance for this component"""
        if self._accessibility_registered:
            return self._accessibility_manager._validate_component_accessibility(
                self._accessibility_component_id
            )
        return {}
    
    def get_accessibility_status(self) -> Dict[str, Any]:
        """Get accessibility status for this component"""
        return {
            'component_id': self._accessibility_component_id,
            'registered': self._accessibility_registered,
            'role': self._accessibility_info.role.value if self._accessibility_info.role else None,
            'label': self._accessibility_info.label,
            'description': self._accessibility_info.description,
            'is_focusable': self._accessibility_info.is_focusable,
            'focus_order': self._accessibility_info.focus_order,
            'shortcuts_count': len(self._component_shortcuts),
            'states_count': len(self._accessibility_states),
            'properties_count': len(self._accessibility_properties)
        }
    
    # =========================================================================
    # Component-Specific Accessibility Features
    # =========================================================================
    
    def setup_table_accessibility(self, 
                                 row_count: int, 
                                 column_count: int,
                                 has_headers: bool = True):
        """Setup accessibility for table components"""
        if self._accessibility_info.role != AccessibilityRole.TABLE:
            self.set_accessibility_role(AccessibilityRole.TABLE)
        
        # Set table properties
        self.set_accessibility_property(AccessibilityProperty.ROWCOUNT, str(row_count))
        self.set_accessibility_property(AccessibilityProperty.COLCOUNT, str(column_count))
        
        # Add table navigation shortcuts
        self.add_accessibility_shortcut(
            "Ctrl+Home", "navigate_to_first_cell", "Navigate to first cell"
        )
        self.add_accessibility_shortcut(
            "Ctrl+End", "navigate_to_last_cell", "Navigate to last cell"
        )
        self.add_accessibility_shortcut(
            "Up", "navigate_up", "Navigate up one row"
        )
        self.add_accessibility_shortcut(
            "Down", "navigate_down", "Navigate down one row"
        )
        self.add_accessibility_shortcut(
            "Left", "navigate_left", "Navigate left one column"
        )
        self.add_accessibility_shortcut(
            "Right", "navigate_right", "Navigate right one column"
        )
    
    def setup_button_accessibility(self, button_text: str, button_action: str):
        """Setup accessibility for button components"""
        if self._accessibility_info.role != AccessibilityRole.BUTTON:
            self.set_accessibility_role(AccessibilityRole.BUTTON)
        
        # Set button label
        self.set_accessibility_label(button_text)
        
        # Add button shortcuts
        self.add_accessibility_shortcut(
            "Space", button_action, f"Activate {button_text}"
        )
        self.add_accessibility_shortcut(
            "Enter", button_action, f"Activate {button_text}"
        )
    
    def setup_input_accessibility(self, 
                                 input_label: str,
                                 is_required: bool = False,
                                 input_type: str = "text"):
        """Setup accessibility for input components"""
        role = AccessibilityRole.SEARCH if input_type == "search" else AccessibilityRole.TEXTBOX
        
        if self._accessibility_info.role != role:
            self.set_accessibility_role(role)
        
        # Set input label
        self.set_accessibility_label(input_label)
        
        # Set required state
        if is_required:
            self.set_accessibility_state(AccessibilityState.REQUIRED, True)
        
        # Add input shortcuts
        self.add_accessibility_shortcut(
            "Ctrl+A", "select_all", "Select all text"
        )
        self.add_accessibility_shortcut(
            "Escape", "clear_input", "Clear input"
        )
    
    def setup_progress_accessibility(self, 
                                   current_value: int,
                                   max_value: int,
                                   progress_label: str):
        """Setup accessibility for progress components"""
        if self._accessibility_info.role != AccessibilityRole.PROGRESSBAR:
            self.set_accessibility_role(AccessibilityRole.PROGRESSBAR)
        
        # Set progress label
        self.set_accessibility_label(progress_label)
        
        # Set progress description
        progress_text = f"{current_value} of {max_value}"
        self.set_accessibility_description(progress_text)
        
        # Announce progress changes
        percentage = (current_value / max_value) * 100 if max_value > 0 else 0
        self.announce_for_accessibility(f"Progress: {percentage:.0f}% complete")
    
    # =========================================================================
    # Lifecycle Management
    # =========================================================================
    
    def cleanup_accessibility_support(self):
        """Cleanup accessibility support resources"""
        try:
            # Unregister from accessibility manager
            if self._accessibility_registered:
                self._accessibility_manager.unregister_component(
                    self._accessibility_component_id
                )
                self._accessibility_registered = False
            
            # Clear shortcuts and state
            self._component_shortcuts.clear()
            self._accessibility_states.clear()
            self._accessibility_properties.clear()
            
        except Exception as e:
            print(f"Error cleaning up accessibility support: {e}")
    
    def __del__(self):
        """Destructor with accessibility cleanup"""
        try:
            self.cleanup_accessibility_support()
        except:
            pass  # Ignore errors during destruction


# =============================================================================
# Convenience Functions
# =============================================================================

def apply_accessibility_to_widget(widget: QWidget,
                                 role: AccessibilityRole,
                                 label: str,
                                 description: Optional[str] = None) -> bool:
    """Apply accessibility features to any widget"""
    try:
        # Set accessible name and description
        widget.setAccessibleName(label)
        if description:
            widget.setAccessibleDescription(description)
        
        # Set role property
        widget.setProperty("accessibility_role", role.value)
        
        # Create accessibility info
        accessibility_info = AccessibilityInfo(
            role=role,
            label=label,
            description=description
        )
        
        # Register with accessibility manager
        component_id = f"{widget.__class__.__name__}_{id(widget)}"
        manager = get_accessibility_manager()
        
        return manager.register_component(component_id, widget, accessibility_info)
        
    except Exception as e:
        print(f"Error applying accessibility to widget: {e}")
        return False

def create_accessible_widget(widget_class,
                           role: AccessibilityRole,
                           label: str,
                           description: Optional[str] = None,
                           *args, **kwargs):
    """Create a widget with accessibility features applied"""
    try:
        # Create widget instance
        widget = widget_class(*args, **kwargs)
        
        # Apply accessibility
        apply_accessibility_to_widget(widget, role, label, description)
        
        return widget
        
    except Exception as e:
        print(f"Error creating accessible widget: {e}")
        return None 