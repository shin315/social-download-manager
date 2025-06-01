# Social Download Manager Design System

## Overview

The Social Download Manager Design System is a comprehensive UI framework built on PyQt6, providing modern, accessible, and consistent user interface components for video downloading applications.

## Quick Start

### Installation & Setup

```python
from ui.design_system.tokens import initialize_design_system
from ui.design_system.components import *

# Initialize the design system
design_system = initialize_design_system()

# Start using components
card = CardComponent(title="My Card", elevation=ElevationLevel.RAISED)
button = EnhancedButton("Download", "download", primary=True)
```

### Core Principles

1. **Consistency**: Unified visual language across all components
2. **Accessibility**: WCAG 2.1 AA compliance with keyboard navigation
3. **Performance**: Optimized animations and efficient rendering
4. **Modularity**: Composable components with clear APIs
5. **Extensibility**: Easy to customize and extend

## Design Tokens

The design system uses centralized design tokens for:

- **Colors**: Primary, secondary, accent, status colors
- **Typography**: Font sizes, weights, line heights
- **Spacing**: Consistent padding and margin values
- **Elevation**: Shadow levels and depth
- **Animation**: Duration and easing presets

## Component Architecture

### Card System
Modern card-based layouts with 5 elevation levels:
- `FLAT`: No shadow
- `SUBTLE`: Light shadow
- `RAISED`: Medium shadow
- `ELEVATED`: Strong shadow
- `FLOATING`: Maximum shadow

### Icon System
Professional iconography with:
- 18 carefully selected icons
- 6 size variants (XS to XXL)
- 4 style variations (Outline, Filled, Duotone, Minimal)
- SVG-based scalable graphics

### Animation System
Smooth micro-interactions featuring:
- 5 duration presets (INSTANT to DELIBERATE)
- 6 easing curves for natural motion
- Performance-optimized with GPU acceleration
- Automatic cleanup and memory management

### Enhanced Widgets
Modern PyQt6 components with:
- Built-in animations and micro-interactions
- Theme-aware styling
- Validation and feedback states
- Accessibility support

### Workflow Optimization
Advanced UX features including:
- Smart defaults with machine learning
- 25+ keyboard shortcuts
- Bulk operation support
- Enhanced error handling

## Theme System

Supports both light and dark themes with automatic adaptation:

```python
# Theme colors adapt automatically
card = CardComponent()  # Uses current theme colors
icon = IconComponent('download')  # Inherits theme-appropriate colors
```

## Best Practices

### Component Usage
- Always use factory functions for quick component creation
- Apply hover animations to interactive elements
- Use appropriate elevation levels for visual hierarchy
- Combine icons with text for better accessibility

### Animation Guidelines
- Use FAST duration (150ms) for hover effects
- Use NORMAL duration (250ms) for state transitions
- Use DELIBERATE duration (500ms) for important changes
- Prefer EASE_OUT easing for most UI interactions

### Accessibility
- Ensure keyboard navigation works for all interactive elements
- Provide text alternatives for visual elements
- Use sufficient color contrast ratios
- Include focus indicators for all controls

## Integration Guide

### Adding to Existing PyQt6 Applications

```python
class MyWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        # Initialize design system
        self.design_system = initialize_design_system()
        
        # Use enhanced components
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Create enhanced components
        card = CardComponent(title="Downloads")
        button = EnhancedButton("Start", "play", primary=True)
        
        # Add animations
        apply_hover_animations(button, scale=True)
        
        layout.addWidget(card)
        layout.addWidget(button)
```

### Custom Component Development

```python
class MyCustomWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        # Inherit design system styling
        self.style_manager = StyleManager()
        
        # Apply design tokens
        self.apply_styling()
    
    def apply_styling(self):
        bg_color = self.style_manager.get_token_value(
            'color-background-primary', '#FFFFFF'
        )
        self.setStyleSheet(f"background-color: {bg_color};")
```

## Migration from Legacy UI

### Step 1: Component Replacement
Replace basic PyQt6 widgets with enhanced equivalents:
- `QPushButton` → `EnhancedButton`
- `QLineEdit` → `EnhancedInput`
- `QProgressBar` → `EnhancedProgressBar`

### Step 2: Layout Modernization
Transform flat layouts into card-based structures:
```python
# Old approach
layout = QVBoxLayout()
layout.addWidget(QLabel("Title"))
layout.addWidget(content_widget)

# New approach
card = CardComponent(title="Title")
card.add_content_layout(content_layout)
```

### Step 3: Add Interactions
Enhance user experience with animations:
```python
# Add hover effects
apply_hover_animations(widget)

# Add loading states
loader = apply_loading_animation(widget, "pulse")

# Add micro-interactions
enhance_widget_interactions(widget)
```

## Performance Considerations

- **Animation Registry**: Prevents memory leaks through centralized management
- **GPU Acceleration**: Leverages Qt's graphics system for smooth animations
- **Lazy Loading**: Components initialize styling only when needed
- **Efficient Cleanup**: Automatic disposal of animations and effects

## Contributing

When adding new components:

1. Follow the established naming conventions
2. Integrate with the design token system
3. Include comprehensive documentation
4. Add test demonstrations
5. Ensure accessibility compliance

## Support

For issues and questions:
- Check the Component API Reference for detailed usage
- Review practical examples for implementation patterns
- Refer to test demonstrations for working code

---

*This design system empowers developers to create modern, accessible, and visually appealing user interfaces with minimal effort while maintaining consistency and performance.* 