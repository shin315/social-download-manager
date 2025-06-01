"""
Design System Components

Modern UI components for the Social Download Manager, implementing
card-based layouts, contemporary design patterns, enhanced animations,
micro-interactions, workflow optimization, and sophisticated user experience.
"""

from .cards import (
    CardComponent,
    CardContainer,
    CardLayout,
    ElevationLevel
)

from .icons import (
    IconComponent,
    IconButton,
    IconSize,
    IconStyle,
    create_icon,
    create_icon_button
)

from .animations import (
    AnimationManager,
    HoverAnimator,
    LoadingAnimator,
    MicroInteractionManager,
    AnimationDuration,
    EasingType,
    apply_hover_animations,
    apply_loading_animation,
    enhance_widget_interactions
)

from .enhanced_widgets import (
    EnhancedButton,
    EnhancedInput,
    EnhancedProgressBar,
    EnhancedCard,
    create_enhanced_button,
    create_enhanced_input,
    create_enhanced_progress
)

from .workflow_optimization import (
    SmartDefaults,
    KeyboardShortcuts,
    BulkActions,
    ErrorStateManager,
    create_workflow_optimized_widget
)

__all__ = [
    # Card System
    "CardComponent",
    "CardContainer", 
    "CardLayout",
    "ElevationLevel",
    
    # Icon System
    "IconComponent",
    "IconButton",
    "IconSize",
    "IconStyle", 
    "create_icon",
    "create_icon_button",
    
    # Animation System
    "AnimationManager",
    "HoverAnimator",
    "LoadingAnimator",
    "MicroInteractionManager",
    "AnimationDuration",
    "EasingType",
    "apply_hover_animations",
    "apply_loading_animation",
    "enhance_widget_interactions",
    
    # Enhanced Widgets
    "EnhancedButton",
    "EnhancedInput",
    "EnhancedProgressBar",
    "EnhancedCard",
    "create_enhanced_button",
    "create_enhanced_input",
    "create_enhanced_progress",
    
    # Workflow Optimization
    "SmartDefaults",
    "KeyboardShortcuts",
    "BulkActions",
    "ErrorStateManager",
    "create_workflow_optimized_widget"
] 