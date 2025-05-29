# UI Component System

A modern, modular component architecture for the Social Download Manager.

## 🚀 Quick Start

### Running the Component Showcase

```bash
# From project root
cd docs
python component_showcase.py
```

This will launch an interactive demonstration of all components.

### Running Tests

```bash
# Run all component tests
python scripts/run_component_tests.py

# Run with coverage report
python scripts/run_component_tests.py --report

# Run specific component tests
python scripts/run_component_tests.py --component buttons
python scripts/run_component_tests.py --component statistics

# Validate component structure
python scripts/run_component_tests.py --validate
```

## 📁 Project Structure

```
ui/components/
├── common/              # Shared utilities and models
│   ├── models.py       # Data models (ButtonConfig, StatisticsData, etc.)
│   ├── interfaces.py   # Component interfaces and protocols
│   └── events.py       # Event system (ComponentBus, EventType)
├── mixins/             # Reusable functionality mixins
│   ├── language_support.py  # Translation support
│   ├── theme_support.py     # Theme management
│   └── tooltip_support.py   # Enhanced tooltips
└── widgets/            # UI widget components
    ├── action_button_group.py  # Configurable button groups
    ├── statistics_widget.py    # Statistics display
    ├── thumbnail_widget.py     # Thumbnail management
    └── progress_tracker.py     # Progress indication
```

## 🧩 Components Overview

### Mixins (Phase 1 - Complete ✅)

**LanguageSupport**: Standardized translation management
- Unified `tr_()` method across all components
- Event-driven language change handling
- Fallback support for missing translations

**ThemeSupport**: Consistent theming system
- Base and component-specific theme application
- Event-driven theme synchronization
- Predefined dark/light themes

**TooltipSupport**: Enhanced tooltip formatting
- Automatic text formatting with regex processing
- Rich tooltip support with HTML
- Configurable length limits

### Widgets (Phase 2 - Complete ✅)

**ActionButtonGroup**: Configurable button collections
- Factory functions for common configurations
- Dynamic state management
- Signal-based communication

**StatisticsWidget**: Intelligent data statistics
- Automatic size calculation and formatting
- Multi-format video data support
- Real-time updates with filtering/selection counts

**ThumbnailWidget**: Advanced thumbnail management
- Background loading with network handling
- Multiple visual states (placeholder, loading, error)
- Configurable sizes through factory functions

**ProgressTracker**: Comprehensive progress tracking
- Multiple display modes (full, simple, compact)
- Speed indicators and status messages
- Indeterminate progress support

## 🔧 Usage Examples

### Basic Component Usage

```python
from ui.components.widgets.action_button_group import create_download_tab_buttons
from ui.components.widgets.statistics_widget import StatisticsWidget

# Create button group with factory function
buttons = create_download_tab_buttons(lang_manager)
buttons.select_all_clicked.connect(self.handle_select_all)

# Create statistics widget
stats = StatisticsWidget(lang_manager=lang_manager)
stats.update_statistics(video_data)
```

### Custom Component with Mixins

```python
from ui.components.mixins.language_support import LanguageSupport
from ui.components.mixins.theme_support import ThemeSupport

class MyCustomWidget(QWidget, LanguageSupport, ThemeSupport):
    def __init__(self, lang_manager=None):
        QWidget.__init__(self)
        LanguageSupport.__init__(self, "MyWidget", lang_manager)
        ThemeSupport.__init__(self, "MyWidget")
        
        self.setup_ui()
    
    def setup_ui(self):
        self.label = QLabel(self.tr_("WELCOME_MESSAGE"))
    
    def update_language(self):
        self.label.setText(self.tr_("WELCOME_MESSAGE"))
    
    def _apply_component_theme(self, theme):
        self.setStyleSheet(f"background-color: {theme['background_color']};")
```

### Event System Usage

```python
from ui.components.common.events import get_event_bus, EventType

# Subscribe to events
bus = get_event_bus()

def handle_theme_change(event):
    print(f"Theme changed: {event.data['theme']}")

bus.subscribe(EventType.THEME_CHANGED, handle_theme_change)

# Emit events
bus.emit_event(
    EventType.THEME_CHANGED,
    "settings_component",
    {"theme": dark_theme}
)
```

## 🧪 Testing

### Test Categories

- **Unit Tests**: Individual component functionality
- **Integration Tests**: Component interaction and communication
- **Performance Tests**: Large dataset handling (1000+ items)
- **Mock Tests**: External dependency simulation

### Test Coverage

- ✅ Event system reliability and performance
- ✅ Mixin integration and functionality
- ✅ Widget creation and signal handling
- ✅ Component lifecycle management
- ✅ Error handling and graceful degradation
- ✅ Theme application and propagation
- ✅ Network simulation for thumbnails

### Running Specific Tests

```bash
# Test individual components
python scripts/run_component_tests.py --component events
python scripts/run_component_tests.py --component language
python scripts/run_component_tests.py --component theme
python scripts/run_component_tests.py --component buttons
python scripts/run_component_tests.py --component statistics
python scripts/run_component_tests.py --component thumbnail
python scripts/run_component_tests.py --component progress

# Test categories
python scripts/run_component_tests.py --component integration
python scripts/run_component_tests.py --component performance
python scripts/run_component_tests.py --component mock
```

## 📈 Performance Metrics

### Code Reduction Achieved

- **500+ lines** of duplicate code eliminated
- **80+ lines** from Phase 1 mixin extraction
- **400+ lines** from Phase 2 widget consolidation
- **Significant complexity reduction** in main UI files

### Performance Benchmarks

- Statistics calculation: **< 1 second** for 1000 items
- Event bus handling: **< 1 second** for 100 events × 100 subscribers
- Component initialization: **< 100ms** per widget
- Theme application: **< 50ms** across all components

## 🎯 Architecture Benefits

### 1. **Modularity**
- Components are self-contained and reusable
- Clear separation of concerns
- Easy to test in isolation

### 2. **Maintainability**
- Consistent patterns across all components
- Centralized functionality through mixins
- Event-driven communication reduces coupling

### 3. **Scalability**
- Easy to add new components
- Factory functions for common configurations
- Performance optimized for large datasets

### 4. **Developer Experience**
- Comprehensive documentation and examples
- Interactive showcase for testing
- Type hints and clear interfaces

## 🔮 Future Enhancements

### Phase 3 (Planned)
- **FilterWidget**: Advanced filtering capabilities
- **TableComponents**: Core table functionality extraction
- **DialManager**: Reusable dialog components
- **ContextMenuManager**: Standardized context menus

### Architecture Improvements
- Plugin system for component extensions
- Dynamic component loading
- Component dependency injection
- Advanced state management patterns

## 🐛 Troubleshooting

### Common Issues

**Import Errors**
```
ModuleNotFoundError: No module named 'ui.components'
```
- Ensure project root is in Python path
- Verify all `__init__.py` files exist

**Missing Translations**
```
Button shows 'BUTTON_SELECT_ALL' instead of translated text
```
- Verify language manager is passed to components
- Check translation keys exist in language files

**Theme Not Applied**
```
Component doesn't reflect theme changes
```
- Ensure component inherits from ThemeSupport
- Implement `_apply_component_theme()` method
- Subscribe to theme change events

**Events Not Received**
```
Component doesn't respond to events
```
- Check event subscription in constructor
- Verify event type matches emission
- Ensure event bus is initialized

### Debugging Tools

```python
# Enable event logging
def debug_handler(event):
    print(f"Event: {event.event_type} from {event.source_component}")

get_event_bus().subscribe(EventType.STATE_CHANGED, debug_handler)

# Component state inspection
print(f"Language manager: {component.get_language_manager()}")
print(f"Current theme: {component.get_current_theme()}")
print(f"Statistics: {stats_widget.get_statistics()}")
```

## 📚 Documentation

- **[Component Architecture](component_architecture.md)**: Detailed architecture documentation
- **[Component Showcase](component_showcase.py)**: Interactive demonstration
- **[Test Suite](../tests/test_components.py)**: Comprehensive test examples
- **[Test Runner](../scripts/run_component_tests.py)**: Testing utilities

## 🤝 Contributing

When adding new components:

1. Follow the established interface patterns
2. Include comprehensive tests
3. Add factory functions for common use cases
4. Update the showcase demo
5. Document usage examples

### Component Checklist

- [ ] Inherits from appropriate interfaces
- [ ] Uses mixins for shared functionality
- [ ] Implements proper signal/slot communication
- [ ] Includes factory functions
- [ ] Has comprehensive test coverage
- [ ] Follows naming conventions
- [ ] Includes usage documentation

---

**Built with ❤️ for the Social Download Manager project** 