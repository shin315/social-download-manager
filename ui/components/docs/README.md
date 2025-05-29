# UI Components Documentation

## Overview

This comprehensive UI components system provides reusable, accessible, and themeable components for the Social Download Manager application. The system is built on PyQt6 and follows enterprise-grade design patterns with extensive testing and documentation.

## 🏗️ Architecture

### Core Systems

- **Base Components**: Foundation classes and interfaces
- **Common Components**: Shared utilities and managers
- **Mixins**: Reusable behavior modules  
- **Tables**: Advanced table components with filtering and selection
- **Widgets**: Specialized UI widgets
- **Testing**: Comprehensive testing framework
- **Theming**: Advanced theming and styling system
- **Accessibility**: WCAG 2.1 compliant accessibility features

### Design Principles

1. **Modularity**: Components are self-contained and composable
2. **Accessibility**: WCAG 2.1 AA compliance by default
3. **Theming**: Consistent visual design with theme support
4. **Testing**: Comprehensive test coverage with automated testing
5. **Performance**: Optimized for large datasets and smooth interactions
6. **Internationalization**: Multi-language support throughout

## 📚 Component Categories

### Table Components

#### VideoTable
Advanced table component for displaying video data with sorting, filtering, and selection.

**Features:**
- Real-time data updates
- Multi-column sorting
- Advanced filtering
- Bulk selection
- Context menus
- Accessibility support

**Usage:**
```python
from ui.components.tables import VideoTable

# Create table
table = VideoTable()

# Set data
table.set_data([
    {"title": "Sample Video", "platform": "youtube", "duration": 180},
    {"title": "Another Video", "platform": "tiktok", "duration": 60}
])

# Configure columns
table.set_columns([
    {"key": "title", "label": "Title", "width": 300},
    {"key": "platform", "label": "Platform", "width": 100},
    {"key": "duration", "label": "Duration", "width": 80}
])
```

#### FilterableVideoTable
Extended video table with built-in filtering capabilities.

**Features:**
- Text search across all columns
- Platform filtering
- Date range filtering
- Duration filtering
- Custom filter presets

**Usage:**
```python
from ui.components.tables import FilterableVideoTable

# Create filterable table
table = FilterableVideoTable()

# Add filter presets
table.add_filter_preset("Recent Videos", {
    "date_range": "last_week",
    "platforms": ["youtube", "tiktok"]
})

# Apply filters
table.apply_filters({
    "search_query": "tutorial",
    "platform": "youtube",
    "min_duration": 60
})
```

### Widget Components

#### PlatformSelector
Component for selecting video platforms with multiple display modes.

**Features:**
- ComboBox mode for compact display
- Button mode for quick access
- Auto-detection mode with URL parsing
- Multi-platform support

**Usage:**
```python
from ui.components.widgets import PlatformSelector

# Create selector
selector = PlatformSelector()

# Set mode
selector.set_mode("buttons")  # "combo", "buttons", "auto"

# Connect signals
selector.platform_changed.connect(on_platform_changed)
selector.url_detected.connect(on_url_detected)

# Get selected platform
platform = selector.get_selected_platform()
```

#### FilterPopup
Professional popup for advanced filtering options.

**Features:**
- Dynamic filter types
- Visual feedback
- Keyboard navigation
- Responsive layout

**Usage:**
```python
from ui.components.widgets import FilterPopup

# Create popup
popup = FilterPopup(parent_widget)

# Add filter types
popup.add_filter_type("text", "Search", placeholder="Enter search terms")
popup.add_filter_type("select", "Platform", options=["youtube", "tiktok"])
popup.add_filter_type("range", "Duration", min_val=0, max_val=3600)

# Show popup
popup.show_popup()
```

#### ProgressTracker
Advanced progress tracking with multiple visualizations.

**Features:**
- Circular and linear progress bars
- ETA calculations
- Speed monitoring
- Visual customization

**Usage:**
```python
from ui.components.widgets import ProgressTracker

# Create tracker
tracker = ProgressTracker()

# Set progress
tracker.set_progress(45, 100)  # 45% complete
tracker.set_speed(1.5)  # 1.5 MB/s
tracker.set_eta(120)  # 2 minutes remaining

# Customize appearance
tracker.set_style("circular")  # "linear", "circular"
tracker.set_color_scheme("blue")
```

### Common Components

#### ComponentStateManager
Centralized state management for components.

**Features:**
- Individual component state tracking
- Inter-component synchronization
- State change history with rollback
- Automatic persistence
- Real-time state watchers

**Usage:**
```python
from ui.components.common import ComponentStateManager

# Get manager instance
state_manager = ComponentStateManager()

# Register component
state_manager.register_component("video_table", table_widget)

# Set state
state_manager.set_component_state("video_table", {
    "selected_rows": [1, 3, 5],
    "sort_column": "title",
    "filter_active": True
})

# Get state
current_state = state_manager.get_component_state("video_table")

# Add state watcher
state_manager.add_state_watcher("video_table", on_state_changed)
```

#### ComponentThemeManager
Advanced theming system with responsive design.

**Features:**
- 10 component-specific theme types
- 10 component states (normal, hover, active, etc.)
- 5 responsive breakpoints
- CSS generation for all components
- Style caching for performance
- Theme import/export

**Usage:**
```python
from ui.components.common import ComponentThemeManager

# Get manager instance
theme_manager = ComponentThemeManager()

# Apply theme to component
theme_manager.apply_theme_to_component(widget, "TABLE", "NORMAL")

# Switch themes
theme_manager.switch_theme("dark")

# Generate CSS
css = theme_manager.generate_component_css("BUTTON", "HOVER")

# Handle responsive breakpoints
theme_manager.handle_breakpoint_change("TABLET")
```

#### AccessibilityManager
Comprehensive accessibility support system.

**Features:**
- WCAG 2.1 compliance
- Screen reader support
- Keyboard navigation
- Focus management
- Accessibility testing

**Usage:**
```python
from ui.components.common import AccessibilityManager

# Get manager instance
accessibility_manager = AccessibilityManager()

# Register component for accessibility
accessibility_manager.register_component(
    "my_button", 
    button_widget,
    role=AccessibilityRole.BUTTON,
    label="Save File"
)

# Set keyboard shortcuts
accessibility_manager.add_keyboard_shortcut(
    "my_button",
    "Ctrl+S",
    save_action
)

# Run accessibility validation
validation_result = accessibility_manager.validate_component("my_button")
```

## 🎭 Mixins

### Language Support
Provides internationalization capabilities.

**Usage:**
```python
from ui.components.mixins import LanguageSupport

class MyComponent(QWidget, LanguageSupport):
    def __init__(self):
        super().__init__(supported_languages=["en", "vi", "fr"])
        
    def setup_ui(self):
        self.label.setText(self.tr("Hello World"))
        
    def on_language_changed(self, language_code):
        self.update_text_content()
```

### Theme Support
Provides theming capabilities.

**Usage:**
```python
from ui.components.mixins import ThemeSupport

class MyComponent(QWidget, ThemeSupport):
    def __init__(self):
        super().__init__(theme_enabled=True)
        
    def on_theme_changed(self, theme_name):
        self.apply_theme_styles(theme_name)
```

### State Management
Provides state management capabilities.

**Usage:**
```python
from ui.components.mixins import StatefulComponentMixin

class MyComponent(QWidget, StatefulComponentMixin):
    def __init__(self):
        super().__init__(enable_state_management=True)
        
    def on_data_changed(self, new_data):
        self.update_component_state({"data": new_data})
```

### Accessibility Support
Provides accessibility features.

**Usage:**
```python
from ui.components.mixins import AccessibilitySupport

class MyComponent(QWidget, AccessibilitySupport):
    def __init__(self):
        super().__init__(accessibility_role=AccessibilityRole.BUTTON)
        self.setup_accessibility()
```

## 🧪 Testing Framework

### Component Testing
Comprehensive testing utilities for UI components.

**Features:**
- Unit testing for component logic
- Widget testing for UI interactions
- Integration testing for component communication
- Performance testing with metrics
- Accessibility testing integration

**Usage:**
```python
from ui.components.testing import ComponentTester, create_simple_test_case

# Create tester
tester = ComponentTester()

# Create test case
def test_button_click():
    button.click()
    assert button.was_clicked

test_case = create_simple_test_case("test_button_click", test_button_click)

# Run test
result = tester.run_test_case(test_case)
print(f"Test {'PASSED' if result.passed else 'FAILED'}")
```

### Widget Testing
Specialized testing for UI widgets.

**Usage:**
```python
from ui.components.testing import WidgetTester, test_widget_quickly

# Quick widget test
result = test_widget_quickly(my_button, "Button Functionality Test")

# Detailed widget testing
widget_tester = WidgetTester()
widget_tester.click_widget(button)
widget_tester.send_key_sequence(line_edit, "Hello World")
validation = widget_tester.validate_widget_property(button, 'text', 'Click Me')
```

### Mock Utilities
Mock objects and data generation for testing.

**Usage:**
```python
from ui.components.testing import MockComponent, MockDataGenerator

# Create mock component
mock_comp = MockComponent("table")
mock_comp.set_mock_data({"rows": 10, "columns": 5})

# Generate test data
generator = MockDataGenerator()
video_data = generator.generate_video_data(10)
user_data = generator.generate_user_data(5)
```

## 🎨 Theming System

### Theme Types
- **Light Theme**: Clean, bright interface
- **Dark Theme**: Dark background, light text
- **High Contrast**: Maximum accessibility

### Component States
- NORMAL, HOVER, ACTIVE, PRESSED, DISABLED
- FOCUSED, LOADING, ERROR, SUCCESS, WARNING

### Responsive Breakpoints
- MOBILE (< 768px)
- TABLET (768px - 1024px)  
- DESKTOP (1024px - 1440px)
- WIDE (1440px - 1920px)
- ULTRA_WIDE (> 1920px)

### Custom Themes
```python
# Create custom theme
custom_theme = {
    "name": "custom",
    "colors": {
        "primary": "#007ACC",
        "secondary": "#FFA500",
        "background": "#F5F5F5",
        "text": "#333333"
    },
    "typography": {
        "font_family": "Segoe UI",
        "font_size_base": 14
    }
}

theme_manager.add_custom_theme(custom_theme)
```

## ♿ Accessibility Features

### WCAG 2.1 Compliance
- **2.1.1** Keyboard accessibility
- **2.4.3** Focus order management  
- **2.4.7** Focus visible indicators
- **4.1.2** Name, role, value attributes
- **1.3.1** Information and relationships

### Screen Reader Support
- Automatic ARIA attribute generation
- Structured navigation landmarks
- Dynamic content announcements
- Custom screen reader messages

### Keyboard Navigation
- Tab order management
- Keyboard shortcuts
- Focus indicators
- Skip links for efficiency

## 🚀 Performance Optimization

### Lazy Loading
Components support lazy loading for large datasets:

```python
table.enable_lazy_loading(chunk_size=100)
table.set_data_provider(data_provider_function)
```

### Virtual Scrolling
Efficient rendering of large lists:

```python
table.enable_virtual_scrolling(visible_rows=50)
```

### State Caching
Automatic state caching for performance:

```python
state_manager.enable_caching(ttl_seconds=300)
```

## 🔧 Integration Patterns

### BaseTab Integration
Components integrate seamlessly with the BaseTab architecture:

```python
from ui.components.common import BaseTab
from ui.components.tables import VideoTable

class VideoTab(BaseTab):
    def __init__(self):
        super().__init__()
        self.video_table = VideoTable()
        self.setup_component_integration()
        
    def setup_component_integration(self):
        # Components automatically inherit tab's theme and language settings
        # State management is shared across tab components
        # Event bus integration for component communication
        pass
```

### Event Bus Communication
Components communicate through a centralized event bus:

```python
from ui.components.common import get_event_bus

# Component A emits event
event_bus = get_event_bus()
event_bus.emit('video_selected', video_data)

# Component B receives event  
event_bus.subscribe('video_selected', self.on_video_selected)
```

## 📋 Best Practices

### Component Development
1. **Inherit from appropriate mixins** for shared functionality
2. **Register with managers** for state, theme, and accessibility
3. **Emit events** for component communication
4. **Handle errors gracefully** with user feedback
5. **Test thoroughly** with the testing framework

### Performance
1. **Use lazy loading** for large datasets
2. **Cache computed values** where appropriate
3. **Debounce user input** for search and filtering
4. **Optimize paint events** for smooth scrolling
5. **Profile memory usage** during development

### Accessibility
1. **Set appropriate ARIA roles** for all components
2. **Provide keyboard alternatives** for mouse actions
3. **Test with screen readers** during development
4. **Ensure sufficient color contrast** in all themes
5. **Validate accessibility** using the testing framework

### Theming
1. **Use theme variables** instead of hardcoded colors
2. **Test all themes** during development
3. **Support high contrast mode** for accessibility
4. **Respond to system theme changes** automatically
5. **Cache theme styles** for performance

## 🐛 Troubleshooting

### Common Issues

#### Components not registering with managers
**Problem**: Component features not working
**Solution**: Ensure proper mixin inheritance and manager registration

```python
# ✅ Correct
class MyComponent(QWidget, StatefulComponentMixin, AccessibilitySupport):
    def __init__(self):
        super().__init__(enable_state_management=True)

# ❌ Incorrect  
class MyComponent(QWidget):
    def __init__(self):
        super().__init__()
        # Missing mixin inheritance
```

#### Theme not applying
**Problem**: Component not reflecting theme changes
**Solution**: Implement theme change handlers

```python
def on_theme_changed(self, theme_name):
    self.apply_theme_styles(theme_name)
    self.update()  # Force repaint
```

#### Accessibility issues
**Problem**: Screen reader not working properly
**Solution**: Check ARIA attribute setup and component registration

```python
# Ensure proper accessibility setup
accessibility_manager.register_component(
    component_id, 
    widget,
    role=AccessibilityRole.BUTTON,  # Set appropriate role
    label="Button description"      # Provide clear label
)
```

## 📞 Support

For questions and support:

1. Check this documentation first
2. Review component examples in `/examples`
3. Run component tests to verify functionality
4. Check accessibility compliance with testing tools
5. Review integration patterns for BaseTab compatibility

## 🔄 Contributing

When extending or modifying components:

1. **Follow existing patterns** and conventions
2. **Add comprehensive tests** for new functionality  
3. **Update documentation** with examples
4. **Ensure accessibility compliance**
5. **Test with all themes** and languages
6. **Profile performance** impact
7. **Review with team** before integration

---

*This documentation covers the comprehensive UI components system. Each component is designed for enterprise-grade applications with full accessibility, theming, testing, and performance optimization.* 