"""
Common Components and Interfaces

Shared interfaces, models, and utilities used across all component types.
"""

from .models import *
from .interfaces import *
from .events import *
from .tab_interfaces import *
from .base_tab import BaseTab
from .tab_state_manager import TabStateManager, TabStatePersistence, FileBasedStatePersistence, TabStateSnapshot, TabStateTransaction
from .tab_utilities import (
    TabFactory, TabEventHelper, TabDataSynchronizer, TabValidationHelper, TabPerformanceMonitor,
    tab_lifecycle_handler, auto_save_on_change, validate_before_action, with_state_backup,
    create_standard_tab_config, setup_tab_logging, apply_theme_to_tab, connect_tab_to_state_manager
)
from .tab_styling import (
    TabStyleManager, TabStyleHelper, TabStyleVariant, TabColorScheme,
    apply_tab_theme, set_global_tab_theme, get_tab_style_manager
)
from .tab_manager import TabManager, TabRegistration, get_tab_manager, initialize_tab_manager

# Import new component interfaces
from .component_interfaces import *

# Import state management system
from .component_state_manager import (
    ComponentStateManager, ComponentStateInterface, ComponentStateSnapshot, ComponentStateChange,
    get_component_state_manager, initialize_component_state_manager
)

# Import state management mixins  
from ..mixins.state_management import (
    StatefulComponentMixin, FilterableStateMixin, SelectableStateMixin
)

# Import accessibility management system
from .accessibility import (
    AccessibilityManager, AccessibilityValidator, AccessibilityRole, AccessibilityState,
    AccessibilityProperty, AccessibilityInfo, KeyboardShortcut,
    get_accessibility_manager, initialize_accessibility_system
)

# Import accessibility mixin
from ..mixins.accessibility_support import (
    AccessibilitySupport, apply_accessibility_to_widget, create_accessible_widget
)

# Import component theming system
from .component_theming import (
    ComponentThemeManager, ComponentThemeType, ComponentState, ResponsiveBreakpoint,
    ComponentColorPalette, ComponentTypography, ComponentSpacing, ComponentAnimations,
    ComponentTheme, get_component_theme_manager, initialize_component_theming,
    apply_component_theme
)

# Import enhanced theme support
from ..mixins.enhanced_theme_support import EnhancedThemeSupport, apply_enhanced_theme, create_themed_widget

__all__ = [
    # Models
    'TableConfig',
    'ColumnConfig',
    'ButtonConfig',
    'TabState',
    'TabConfig',
    'StatisticsData',
    
    # Interfaces
    'ComponentInterface',
    'TableInterface',
    'FilterInterface',
    'StateManagerInterface',
    
    # Tab Interfaces
    'TabInterface',
    'TabLifecycleInterface',
    'TabNavigationInterface',
    'TabDataInterface',
    'TabValidationInterface',
    'TabStateInterface',
    'FullTabProtocol',
    
    # Protocols
    'TabLanguageSupport',
    'TabThemeSupport',
    'TabParentSupport',
    'TabSignalSupport',
    
    # Base Classes
    'BaseTab',
    
    # State Management
    'TabStateManager',
    'TabStatePersistence',
    'FileBasedStatePersistence',
    'TabStateSnapshot',
    'TabStateTransaction',
    
    # Tab Utilities
    'TabFactory',
    'TabEventHelper',
    'TabDataSynchronizer',
    'TabValidationHelper',
    'TabPerformanceMonitor',
    
    # Decorators
    'tab_lifecycle_handler',
    'auto_save_on_change',
    'validate_before_action',
    'with_state_backup',
    
    # Utility Functions
    'create_standard_tab_config',
    'setup_tab_logging',
    'apply_theme_to_tab',
    'connect_tab_to_state_manager',
    
    # Styling Framework
    'TabStyleManager',
    'TabStyleHelper',
    'TabStyleVariant',
    'TabColorScheme',
    'apply_tab_theme',
    'set_global_tab_theme',
    'get_tab_style_manager',
    
    # Tab Manager
    'TabManager',
    'TabRegistration',
    'get_tab_manager',
    'initialize_tab_manager',
    
    # Events
    'ComponentEvent',
    'ComponentBus',
    'EventType',
    'get_event_bus',
    
    # New component interfaces
    'TableInterface',
    'FilterableTableInterface',
    'PlatformSelectorInterface',
    'ProgressTrackerInterface',
    'SearchInterface',
    'FilterInterface',
    'VideoDetailsInterface',
    'StatisticsInterface',
    'ActionButtonGroupInterface',
    'ThumbnailInterface',
    
    # Platform types and models
    'PlatformType',
    'PlatformCapability',
    'PlatformInfo',
    
    # Configuration models
    'PlatformSelectorConfig',
    'SearchConfig',
    'FilterWidgetConfig',
    'VideoDetailsConfig',
    'ThumbnailConfig',
    
    # Interface registry
    'ComponentInterfaceRegistry',
    
    # Accessibility system
    'AccessibilityManager',
    'AccessibilityValidator', 
    'AccessibilityRole',
    'AccessibilityState',
    'AccessibilityProperty',
    'AccessibilityInfo',
    'KeyboardShortcut',
    'get_accessibility_manager',
    'initialize_accessibility_system',
    'AccessibilitySupport',
    'apply_accessibility_to_widget',
    'create_accessible_widget',
    
    # Enhanced theming
    'EnhancedThemeSupport',
    'apply_enhanced_theme', 
    'create_themed_widget'
] 