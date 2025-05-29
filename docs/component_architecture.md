# Component Architecture Documentation

## Overview

The UI component architecture provides a modular, reusable, and maintainable approach to building the Social Download Manager interface. The architecture follows a 3-layer approach with mixins, widgets, and core interfaces.

## Architecture Principles

### 1. **Separation of Concerns**
- Each component has a single, well-defined responsibility
- Business logic is separated from UI presentation
- Event handling is decoupled from component implementation

### 2. **Composition over Inheritance**
- Components use mixins for shared functionality
- Multiple interfaces can be implemented per component
- Flexible component assembly through configuration

### 3. **Event-Driven Communication**
- Components communicate through events, not direct references
- Loose coupling between components
- Centralized event bus for system-wide communication

### 4. **Configuration-Driven Design**
- Components are configured through data models
- Factory functions provide common configurations
- Theme and language support through configuration

## Directory Structure

```
ui/components/
├── __init__.py                 # Main package exports
├── common/                     # Shared utilities
│   ├── __init__.py
│   ├── models.py              # Data models and enums
│   ├── interfaces.py          # Component interfaces
│   └── events.py              # Event system
├── mixins/                     # Reusable mixins
│   ├── __init__.py
│   ├── language_support.py    # Translation support
│   ├── theme_support.py       # Theme management
│   └── tooltip_support.py     # Tooltip formatting
└── widgets/                    # UI widgets
    ├── __init__.py
    ├── action_button_group.py  # Button groups
    ├── statistics_widget.py    # Statistics display
    ├── thumbnail_widget.py     # Thumbnail management
    └── progress_tracker.py     # Progress indication
```

## Core Components

### Event System

The event system provides decoupled communication between components.

#### Key Classes:
- **`ComponentBus`**: Central event dispatcher
- **`EventType`**: Enumeration of standard events
- **`ComponentEvent`**: Event data structure
- **`EventEmitter`**: Mixin for emitting events
- **`EventSubscriber`**: Mixin for receiving events

#### Example Usage:
```python
from ui.components.common.events import get_event_bus, EventType

# Get global event bus
bus = get_event_bus()

# Subscribe to events
def handle_language_change(event):
    print(f"Language changed: {event.data['language']}")

bus.subscribe(EventType.LANGUAGE_CHANGED, handle_language_change)

# Emit events
bus.emit_event(
    EventType.LANGUAGE_CHANGED,
    "settings_component",
    {"language": "vi"}
)
```

### Mixins

Mixins provide shared functionality that can be composed into components.

#### LanguageSupport
Provides standardized translation functionality.

```python
from ui.components.mixins.language_support import LanguageSupport

class MyComponent(QWidget, LanguageSupport):
    def __init__(self, lang_manager=None):
        QWidget.__init__(self)
        LanguageSupport.__init__(self, "MyComponent", lang_manager)
    
    def setup_ui(self):
        self.label = QLabel(self.tr_("WELCOME_MESSAGE"))
    
    def update_language(self):
        self.label.setText(self.tr_("WELCOME_MESSAGE"))
```

#### ThemeSupport
Provides theme management and application.

```python
from ui.components.mixins.theme_support import ThemeSupport

class MyWidget(QWidget, ThemeSupport):
    def __init__(self):
        QWidget.__init__(self)
        ThemeSupport.__init__(self, "MyWidget")
    
    def _apply_component_theme(self, theme):
        # Apply component-specific theming
        self.setStyleSheet(f"background-color: {theme['background_color']};")
```

#### TooltipSupport
Provides enhanced tooltip formatting and display.

```python
from ui.components.mixins.tooltip_support import TooltipSupport

class MyComponent(QWidget, TooltipSupport):
    def __init__(self):
        QWidget.__init__(self)
        TooltipSupport.__init__(self, "MyComponent")
    
    def show_formatted_tooltip(self, text):
        formatted = self.format_tooltip_text(text)
        self.show_tooltip(formatted)
```

### Widgets

#### ActionButtonGroup
Configurable button groups for common actions.

```python
from ui.components.widgets.action_button_group import ActionButtonGroup, create_download_tab_buttons
from ui.components.common.models import ButtonConfig, ButtonType

# Using factory function
button_group = create_download_tab_buttons(lang_manager)

# Custom configuration
buttons_config = [
    ButtonConfig(ButtonType.SELECT_ALL, "BUTTON_SELECT_ALL", 150),
    ButtonConfig(ButtonType.DELETE_SELECTED, "BUTTON_DELETE_SELECTED", 150)
]
custom_group = ActionButtonGroup(buttons_config, lang_manager=lang_manager)

# Connect signals
button_group.select_all_clicked.connect(self.handle_select_all)
button_group.delete_selected_clicked.connect(self.handle_delete_selected)
```

#### StatisticsWidget
Displays video statistics with automatic calculation.

```python
from ui.components.widgets.statistics_widget import StatisticsWidget

stats_widget = StatisticsWidget(lang_manager=lang_manager)

# Update with video data
video_data = [
    {'title': 'Video 1', 'size': '50 MB', 'download_date': '2025-01-01'},
    {'title': 'Video 2', 'size': '1.2 GB', 'download_date': '2025-01-02'}
]
stats_widget.update_statistics(video_data)

# Get current statistics
stats = stats_widget.get_statistics()
print(f"Total videos: {stats.total_videos}")
print(f"Total size: {stats.total_size}")
```

#### ThumbnailWidget
Manages thumbnail display with loading states.

```python
from ui.components.widgets.thumbnail_widget import ThumbnailWidget, create_medium_thumbnail

# Using factory function
thumbnail = create_medium_thumbnail(lang_manager=lang_manager)

# Load thumbnail from URL
thumbnail.load_thumbnail("https://example.com/thumbnail.jpg")

# Handle thumbnail events
thumbnail.thumbnail_loaded.connect(self.handle_thumbnail_loaded)
thumbnail.thumbnail_failed.connect(self.handle_thumbnail_failed)
```

#### ProgressTracker
Tracks download progress with speed indicators.

```python
from ui.components.widgets.progress_tracker import ProgressTracker, create_download_progress_tracker

# Using factory function
progress = create_download_progress_tracker(lang_manager=lang_manager)

# Update progress
progress.update_progress(50, "Downloading video...")
progress.set_speed("2.5 MB/s")

# Handle completion
progress.progress_completed.connect(self.handle_download_complete)
```

## Configuration Models

### ButtonConfig
Configures button appearance and behavior.

```python
from ui.components.common.models import ButtonConfig, ButtonType

config = ButtonConfig(
    button_type=ButtonType.SELECT_ALL,
    text_key="BUTTON_SELECT_ALL",
    width=150,
    enabled=True,
    visible=True
)
```

### StatisticsData
Holds statistical information.

```python
from ui.components.common.models import StatisticsData

stats = StatisticsData(
    total_videos=42,
    total_size="2.5 GB",
    last_download="2025-01-15",
    filtered_count=10,
    selected_count=5
)
```

## Best Practices

### 1. **Component Creation**
- Always inherit from appropriate interfaces
- Use mixins for shared functionality
- Initialize mixins in `__init__` method
- Call `setup_ui()` after initialization

### 2. **Event Handling**
- Use event bus for component communication
- Subscribe to relevant events in constructor
- Clean up subscriptions in destructor
- Emit events for state changes

### 3. **Language Support**
- Use `tr_()` method for all user-visible text
- Implement `update_language()` method
- Subscribe to language change events
- Provide fallback text for missing translations

### 4. **Theme Support**
- Implement `_apply_component_theme()` for custom theming
- Use theme dictionary keys consistently
- Apply themes in component initialization
- Subscribe to theme change events

### 5. **Configuration**
- Use data models for component configuration
- Provide factory functions for common use cases
- Make components configurable through constructor
- Support runtime configuration changes

## Migration Guide

### From Legacy UI Files

1. **Identify Reusable Patterns**
   ```python
   # Legacy pattern
   select_all_button = QPushButton("Select All")
   select_all_button.clicked.connect(self.select_all)
   
   # Component approach
   button_group = create_download_tab_buttons(lang_manager)
   button_group.select_all_clicked.connect(self.select_all)
   ```

2. **Extract Statistics Logic**
   ```python
   # Legacy pattern
   total_videos = len(self.videos)
   total_size = sum(video.size for video in self.videos)
   
   # Component approach
   stats_widget = StatisticsWidget(lang_manager)
   stats_widget.update_statistics(self.videos)
   ```

3. **Standardize Language Support**
   ```python
   # Legacy pattern
   self.label.setText(self.lang_manager.tr("LABEL_TEXT"))
   
   # Component approach (with mixin)
   self.label.setText(self.tr_("LABEL_TEXT"))
   ```

### Integration Steps

1. **Add Component Imports**
   ```python
   from ui.components.widgets.action_button_group import create_download_tab_buttons
   from ui.components.widgets.statistics_widget import StatisticsWidget
   from ui.components.mixins.language_support import LanguageSupport
   ```

2. **Replace Legacy UI Elements**
   ```python
   # Replace button creation
   self.button_group = create_download_tab_buttons(self.lang_manager)
   self.layout.addWidget(self.button_group)
   
   # Replace statistics display
   self.stats_widget = StatisticsWidget(self.lang_manager)
   self.layout.addWidget(self.stats_widget)
   ```

3. **Connect Component Signals**
   ```python
   # Connect button signals
   self.button_group.select_all_clicked.connect(self.select_all_videos)
   self.button_group.delete_selected_clicked.connect(self.delete_selected_videos)
   
   # Connect statistics signals
   self.stats_widget.statistics_updated.connect(self.handle_statistics_update)
   ```

## Testing

### Unit Testing
```python
def test_button_group_creation(qapp, mock_lang_manager):
    buttons_config = [
        ButtonConfig(ButtonType.SELECT_ALL, "BUTTON_SELECT_ALL", 150)
    ]
    group = ActionButtonGroup(buttons_config, lang_manager=mock_lang_manager)
    assert len(group.buttons) == 1
```

### Integration Testing
```python
def test_component_communication(qapp, mock_lang_manager, sample_theme):
    button_group = ActionButtonGroup([...], lang_manager=mock_lang_manager)
    stats_widget = StatisticsWidget(lang_manager=mock_lang_manager)
    
    # Test theme propagation
    button_group.apply_theme(sample_theme)
    stats_widget.apply_theme(sample_theme)
    
    assert button_group.get_current_theme() == sample_theme
    assert stats_widget.get_current_theme() == sample_theme
```

## Performance Considerations

### 1. **Event Bus Optimization**
- Use specific event types instead of generic events
- Unsubscribe from events when components are destroyed
- Avoid creating excessive event emissions in loops

### 2. **Widget Optimization**
- Use factory functions for common configurations
- Cache expensive calculations in widgets
- Implement lazy loading for large datasets

### 3. **Memory Management**
- Clean up component subscriptions in destructors
- Release references to large data structures
- Use weak references for parent-child relationships

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```
   ModuleNotFoundError: No module named 'ui.components'
   ```
   - Ensure project root is in Python path
   - Check that `__init__.py` files exist in all directories

2. **Missing Translations**
   ```
   Button shows 'BUTTON_SELECT_ALL' instead of translated text
   ```
   - Verify language manager is passed to components
   - Check that translation keys exist in language files

3. **Theme Not Applied**
   ```
   Component doesn't reflect theme changes
   ```
   - Ensure component inherits from ThemeSupport
   - Implement `_apply_component_theme()` method
   - Subscribe to theme change events

4. **Event Not Received**
   ```
   Component doesn't respond to events
   ```
   - Check event subscription in component constructor
   - Verify event type matches emission
   - Ensure event bus is properly initialized

### Debugging Tips

1. **Enable Event Logging**
   ```python
   def debug_event_handler(event):
       print(f"Event: {event.event_type} from {event.source_component}")
   
   get_event_bus().subscribe(EventType.STATE_CHANGED, debug_event_handler)
   ```

2. **Component State Inspection**
   ```python
   # Check component state
   print(f"Language manager: {component.get_language_manager()}")
   print(f"Current theme: {component.get_current_theme()}")
   print(f"Statistics: {stats_widget.get_statistics()}")
   ```

3. **Test Component Isolation**
   ```python
   # Test component independently
   app = QApplication([])
   widget = StatisticsWidget()
   widget.show()
   app.exec()
   ```

## Future Enhancements

### Planned Components
- **FilterWidget**: Advanced filtering capabilities
- **ContextMenuManager**: Standardized context menus
- **DialogManager**: Reusable dialog components
- **TableComponents**: Advanced table functionality

### Architecture Improvements
- Plugin system for component extensions
- Dynamic component loading
- Component dependency injection
- Advanced state management patterns

---

For more information, see the individual component documentation and the test suite in `tests/test_components.py`. 