# Component API Reference

## CardComponent

### Class: `CardComponent(elevation=ElevationLevel.SUBTLE, title="")`

Modern card component with Material Design elevation levels.

#### Parameters:
- `elevation` (ElevationLevel): Card elevation level (FLAT, SUBTLE, RAISED, ELEVATED, FLOATING)
- `title` (str): Optional card title

#### Methods:
- `add_content_layout(layout)`: Add content layout to card
- `set_elevation(level)`: Change elevation level
- `get_elevation()`: Get current elevation level

#### Example:
```python
card = CardComponent(title="Download Progress", elevation=ElevationLevel.RAISED)
layout = QVBoxLayout()
card.add_content_layout(layout)
```

---

## IconComponent

### Class: `IconComponent(icon_name, size=IconSize.MD, style=IconStyle.OUTLINE)`

Professional icon system with SVG support.

#### Parameters:
- `icon_name` (str): Icon identifier ('download', 'play', 'pause', etc.)
- `size` (IconSize): Icon size (XS, SM, MD, LG, XL, XXL)
- `style` (IconStyle): Icon style (OUTLINE, FILLED, DUOTONE, MINIMAL)

#### Methods:
- `set_icon(icon_name)`: Change icon
- `set_size(size)`: Change icon size
- `set_style(style)`: Change icon style
- `get_svg_content()`: Get SVG content

#### Example:
```python
icon = IconComponent('download', IconSize.LG, IconStyle.FILLED)
icon.set_icon('pause')
```

---

## EnhancedButton

### Class: `EnhancedButton(text, icon=None, primary=True)`

Enhanced button with animations and workflow features.

#### Parameters:
- `text` (str): Button text
- `icon` (str): Optional icon name
- `primary` (bool): Primary or secondary styling

#### Methods:
- `set_loading_state(loading, text="")`: Show loading state
- `set_success_state(success)`: Show success feedback
- `set_error_state(error)`: Show error feedback
- `set_icon(icon_name)`: Change button icon

#### Example:
```python
button = EnhancedButton("Download", "download", primary=True)
button.set_loading_state(True, "Downloading...")
```

---

## EnhancedInput

### Class: `EnhancedInput(text="", placeholder="", label="", validation_type=None)`

Enhanced input with validation and focus effects.

#### Parameters:
- `text` (str): Initial text value
- `placeholder` (str): Placeholder text
- `label` (str): Input label
- `validation_type` (str): Validation type ('url', 'email', 'number')

#### Methods:
- `set_validation_state(state)`: Set validation state ('success', 'error', 'neutral')
- `get_validation_state()`: Get current validation state
- `validate()`: Validate current input

#### Example:
```python
input_field = EnhancedInput(
    placeholder="Enter video URL...",
    label="Video URL",
    validation_type="url"
)
```

---

## AnimationManager

### Class: `AnimationManager()`

Central animation management system.

#### Methods:
- `fade_in(widget, duration=250)`: Fade in animation
- `fade_out(widget, duration=250)`: Fade out animation
- `slide_in(widget, direction, duration=250)`: Slide in animation
- `scale_animation(widget, from_scale, to_scale, duration=250)`: Scale animation
- `cleanup()`: Clean up all animations

#### Example:
```python
animation_manager = AnimationManager()
animation_manager.fade_in(my_widget, duration=300)
```

---

## SmartDefaults

### Class: `SmartDefaults()`

Smart defaults system with machine learning capabilities.

#### Methods:
- `suggest_output_path(video_url, video_title="")`: Suggest output filename
- `suggest_quality_setting(video_url)`: Suggest quality based on platform
- `suggest_download_folder(video_url)`: Suggest download folder
- `learn_user_choice(choice_type, value, context="")`: Learn from user choices

#### Example:
```python
smart_defaults = SmartDefaults()
quality = smart_defaults.suggest_quality_setting("https://youtube.com/watch?v=abc")
smart_defaults.learn_user_choice("quality", "1080p", "youtube")
```

---

## KeyboardShortcuts

### Class: `KeyboardShortcuts(parent_widget)`

Comprehensive keyboard shortcuts system.

#### Parameters:
- `parent_widget` (QWidget): Parent widget for shortcuts

#### Methods:
- `add_shortcut(key_combination, action_name, action_func=None)`: Add shortcut
- `register_action(action_name, action_func)`: Register action function
- `get_shortcut_help()`: Get list of shortcuts for help

#### Example:
```python
shortcuts = KeyboardShortcuts(main_window)
shortcuts.add_shortcut("Ctrl+D", "start_download", start_download_func)
```

---

## BulkActions

### Class: `BulkActions(parent_widget)`

Bulk operation system for multi-item management.

#### Parameters:
- `parent_widget` (QWidget): Parent widget

#### Methods:
- `set_selected_items(items)`: Set selected items
- `execute_bulk_operation(operation_name, **kwargs)`: Execute bulk operation
- `get_available_operations()`: Get list of available operations

#### Example:
```python
bulk_actions = BulkActions(main_window)
bulk_actions.set_selected_items(selected_downloads)
bulk_actions.execute_bulk_operation("download_all")
```

---

## ErrorStateManager

### Class: `ErrorStateManager(parent_widget)`

Enhanced error state management with user guidance.

#### Parameters:
- `parent_widget` (QWidget): Parent widget

#### Methods:
- `show_error_state(error_type, error_message, recovery_suggestions=None, auto_retry=False)`: Show error
- `get_error_recovery_suggestions(error_type)`: Get recovery suggestions

#### Example:
```python
error_manager = ErrorStateManager(main_window)
error_manager.show_error_state(
    "network",
    "Connection timeout",
    ["Check internet connection", "Try again later"],
    auto_retry=True
)
```

---

## Factory Functions

### `create_icon(icon_name, size=IconSize.MD, style=IconStyle.OUTLINE)`
Create icon component quickly.

### `create_icon_button(icon_name, size=IconSize.MD, style=IconStyle.OUTLINE)`
Create icon button component.

### `create_enhanced_button(text, icon=None, primary=True)`
Create enhanced button with default settings.

### `create_enhanced_input(placeholder="", label="", validation_type=None)`
Create enhanced input with validation.

### `create_workflow_optimized_widget(widget_type, **kwargs)`
Create workflow-optimized widgets ('download_input', 'settings_panel', 'bulk_actions_toolbar').

---

## Utility Functions

### `apply_hover_animations(widget, scale=False, elevation=False, glow=False)`
Apply hover animations to any widget.

### `apply_loading_animation(widget, pulse=False, shimmer=False)`
Apply loading animations to any widget.

### `enhance_widget_interactions(widget)`
Add comprehensive micro-interactions to widget.

---

## Constants

### ElevationLevel
- `FLAT`: No shadow
- `SUBTLE`: Light shadow
- `RAISED`: Medium shadow  
- `ELEVATED`: Strong shadow
- `FLOATING`: Maximum shadow

### IconSize
- `XS`: 12px
- `SM`: 16px
- `MD`: 20px
- `LG`: 24px
- `XL`: 32px
- `XXL`: 48px

### IconStyle
- `OUTLINE`: Outlined icons
- `FILLED`: Filled icons
- `DUOTONE`: Two-tone icons
- `MINIMAL`: Minimal line icons

### AnimationDuration
- `INSTANT`: 0ms
- `FAST`: 150ms
- `NORMAL`: 250ms
- `SLOW`: 350ms
- `DELIBERATE`: 500ms

### EasingType
- `LINEAR`: Constant speed
- `EASE_OUT`: Fast start, slow end
- `EASE_IN`: Slow start, fast end
- `EASE_IN_OUT`: Slow start/end, fast middle
- `BOUNCE`: Spring-like bounce
- `ELASTIC`: Overshoots with snap-back 