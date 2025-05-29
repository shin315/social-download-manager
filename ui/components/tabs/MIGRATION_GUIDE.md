# Tab Migration Guide

This guide explains how to migrate existing tabs to the new BaseTab architecture and how to use the migrated tabs.

## Overview

The new tab architecture provides:
- **Lifecycle Management**: Automatic handling of tab activation, deactivation, and cleanup
- **State Persistence**: Automatic saving and restoring of tab state
- **Component Integration**: Event-driven communication between tabs
- **Performance Monitoring**: Built-in performance tracking and debugging
- **Enhanced Theming**: Automatic theme application and language updates
- **Validation**: Comprehensive input validation and error handling

## Migration Process

### 1. Original Tab Structure
```python
# OLD: Direct QWidget inheritance
class MyTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.lang_manager = parent.lang_manager if parent else None
        self.init_ui()
```

### 2. New Tab Structure
```python
# NEW: BaseTab inheritance with component integration
from ..common import BaseTab, TabConfig, create_standard_tab_config

class MyTab(BaseTab):
    def __init__(self, config: Optional[TabConfig] = None, parent=None):
        if config is None:
            config = create_standard_tab_config(
                tab_id="my_tab",
                title_key="TAB_MY_TAB",
                auto_save=True,
                state_persistence=True
            )
        super().__init__(config, parent)
```

## Required Method Implementations

### 1. Abstract Methods (Must Implement)
```python
def get_tab_id(self) -> str:
    """Return unique identifier for this tab"""
    return "my_tab"

def setup_ui(self) -> None:
    """Initialize the tab's UI components"""
    # Create your UI here
    pass

def load_data(self) -> None:
    """Load tab-specific data"""
    # Load your data here
    pass

def save_data(self) -> bool:
    """Save tab data, return success status"""
    # Save your data here
    return True

def refresh_data(self) -> None:
    """Refresh/reload tab data"""
    # Refresh your data here
    pass

def validate_input(self) -> List[str]:
    """Validate tab input, return list of error messages"""
    errors = []
    # Add your validation logic
    return errors
```

### 2. Enhanced Lifecycle Methods (Optional Override)
```python
@tab_lifecycle_handler('activated')
def on_tab_activated(self) -> None:
    """Called when tab becomes active"""
    super().on_tab_activated()
    # Your activation logic here

@tab_lifecycle_handler('deactivated')
def on_tab_deactivated(self) -> None:
    """Called when tab becomes inactive"""
    super().on_tab_deactivated()
    # Your deactivation logic here
```

## Available Decorators

### 1. Lifecycle Handler
```python
@tab_lifecycle_handler('activated')
def on_my_tab_activated(self):
    # Handle activation with automatic error tracking
    pass
```

### 2. Auto-save on Change
```python
@auto_save_on_change(['field1', 'field2'], delay_ms=1000)
def update_field(self, value):
    # Automatic save after field changes
    self.field1 = value
```

### 3. Validation Before Action
```python
@validate_before_action()
def delete_item(self):
    # Automatically validates before executing
    pass
```

### 4. State Backup
```python
@with_state_backup(create_snapshot=True)
def risky_operation(self):
    # Automatically creates backup and restores on failure
    pass
```

## State Management

### 1. Using Tab State
```python
def get_tab_state(self) -> TabState:
    """Get complete tab state"""
    # Update state with current data
    self._tab_state.videos = self.all_videos.copy()
    self._tab_state.filtered_videos = self.filtered_videos.copy()
    return self._tab_state

def set_tab_state(self, state: TabState) -> None:
    """Set tab state from TabState object"""
    self._tab_state = state
    # Restore data from state
    if state.videos:
        self.all_videos = state.videos.copy()
    # Update display
    self.display_data()
```

### 2. State Manager Integration
```python
# Connect to state manager (done automatically)
def save_to_state_manager(self):
    return self._state_manager.save_tab_state(self.get_tab_id())

def load_from_state_manager(self):
    return self._state_manager.load_tab_state(self.get_tab_id())
```

## Inter-Tab Communication

### 1. Event Helper Usage
```python
def __init__(self, config, parent):
    super().__init__(config, parent)
    # Event helper created automatically
    self.event_helper = TabEventHelper(self)

def broadcast_update(self, data):
    """Broadcast update to other tabs"""
    self.event_helper.broadcast_tab_update('data_updated', data)

def on_external_tab_event(self, event):
    """Handle events from other tabs"""
    if event.event_type.value == 'video_download_completed':
        self.refresh_data()
```

### 2. Component Bus Events
```python
def emit_custom_event(self, data):
    """Emit custom event through component bus"""
    self.emit_tab_event('custom_event', {
        'tab_id': self.get_tab_id(),
        'data': data
    })
```

## Performance Monitoring

### 1. Built-in Monitoring
```python
def expensive_operation(self):
    self.performance_monitor.start_timing('operation')
    try:
        # Your expensive operation
        pass
    finally:
        self.performance_monitor.end_timing('operation')

def get_metrics(self):
    return self.performance_monitor.get_performance_report()
```

### 2. Debug Information
```python
def debug_tab(self):
    debug_info = self.get_debug_info()
    print(f"Tab State: {debug_info}")
```

## Theme and Language Support

### 1. Language Updates (Automatic)
```python
def update_language(self):
    """Called automatically when language changes"""
    # Update your UI text
    self.search_label.setText(self.tr_("LABEL_SEARCH"))
    # Call parent implementation
    super().update_language()
```

### 2. Theme Application (Automatic)
```python
def apply_theme_colors(self, theme: dict):
    """Called automatically when theme changes"""
    # Apply base theme
    super().apply_theme_colors(theme)
    
    # Apply custom styling
    if hasattr(self, 'my_widget'):
        style = f"background-color: {theme.get('background', '#ffffff')}"
        self.my_widget.setStyleSheet(style)
```

## Validation System

### 1. Input Validation
```python
def validate_input(self) -> List[str]:
    errors = []
    
    # Check data consistency
    if not self.data_is_valid():
        errors.append("Data is invalid")
    
    # Check required fields
    if not self.required_field:
        errors.append("Required field is missing")
    
    return errors
```

### 2. Validation Helpers
```python
from ..common import TabValidationHelper

# Create validation chain
validator = TabValidationHelper.create_validation_chain(
    TabValidationHelper.required_fields_validator(['field1', 'field2']),
    TabValidationHelper.data_consistency_validator(),
    custom_validator
)

errors = validator(self)
```

## Factory Pattern Usage

### 1. Register Tab Class
```python
from ..common import TabFactory

# Register your tab
TabFactory.register_tab_class(
    'my_tab',
    MyTab,
    create_standard_tab_config('my_tab', 'TAB_MY_TAB')
)
```

### 2. Create Tab Instance
```python
# Create tab using factory
tab = TabFactory.create_tab('my_tab', parent=main_window)
```

## Migration Checklist

- [ ] Change inheritance from `QWidget` to `BaseTab`
- [ ] Implement required abstract methods
- [ ] Add `TabConfig` parameter to constructor
- [ ] Move UI creation to `setup_ui()` method
- [ ] Move data loading to `load_data()` method
- [ ] Implement `save_data()` and `refresh_data()` methods
- [ ] Add input validation in `validate_input()` method
- [ ] Update language support to use enhanced methods
- [ ] Add theme support for custom styling
- [ ] Test lifecycle events (activation/deactivation)
- [ ] Test state persistence and recovery
- [ ] Test inter-tab communication if needed
- [ ] Add performance monitoring for expensive operations
- [ ] Update imports to use new component architecture

## Best Practices

1. **Use Decorators**: Leverage the provided decorators for common patterns
2. **State Management**: Always implement proper state saving/loading
3. **Error Handling**: Use the built-in logging system for errors
4. **Performance**: Monitor expensive operations
5. **Validation**: Implement comprehensive input validation
6. **Events**: Use component bus for inter-tab communication
7. **Testing**: Test all lifecycle events and state transitions

## Example: Complete Migration

```python
"""
Example of a fully migrated tab
"""
from typing import List, Optional
from PyQt6.QtWidgets import QVBoxLayout, QLabel, QPushButton
from ..common import (
    BaseTab, TabConfig, create_standard_tab_config,
    tab_lifecycle_handler, auto_save_on_change, validate_before_action
)

class ExampleTab(BaseTab):
    def __init__(self, config: Optional[TabConfig] = None, parent=None):
        if config is None:
            config = create_standard_tab_config(
                tab_id="example",
                title_key="TAB_EXAMPLE",
                auto_save=True,
                validation_required=True,
                state_persistence=True
            )
        super().__init__(config, parent)
        
        self.data = []
    
    def get_tab_id(self) -> str:
        return "example"
    
    def setup_ui(self) -> None:
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        self.label = QLabel(self.tr_("EXAMPLE_LABEL"))
        layout.addWidget(self.label)
        
        self.button = QPushButton(self.tr_("EXAMPLE_BUTTON"))
        self.button.clicked.connect(self.on_button_click)
        layout.addWidget(self.button)
    
    @tab_lifecycle_handler('load_data')
    def load_data(self) -> None:
        # Load your data
        self.data = self.load_from_database()
    
    @auto_save_on_change(['data'])
    def save_data(self) -> bool:
        try:
            self.save_to_database(self.data)
            return True
        except Exception as e:
            self.log_error(f"Save failed: {e}")
            return False
    
    def refresh_data(self) -> None:
        self.data.clear()
        self.load_data()
    
    def validate_input(self) -> List[str]:
        errors = []
        if not self.data:
            errors.append("No data available")
        return errors
    
    @validate_before_action()
    def on_button_click(self):
        # Button click with automatic validation
        self.process_data()
    
    def update_language(self):
        super().update_language()
        self.label.setText(self.tr_("EXAMPLE_LABEL"))
        self.button.setText(self.tr_("EXAMPLE_BUTTON"))
```

This migration provides a robust, maintainable, and feature-rich tab system that integrates seamlessly with the overall component architecture. 