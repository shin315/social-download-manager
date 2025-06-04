"""
Core Components Module

This module contains advanced management systems for the v2.0 UI architecture,
including lifecycle management, component bus, theme management, state management,
performance monitoring, and other core infrastructure components.

All components in this module are designed to work together to provide:
- Advanced tab lifecycle management with hibernation and recovery
- Cross-component communication via component bus
- Dynamic theme switching and customization
- Comprehensive state management and recovery
- Real-time performance monitoring and optimization
- Dynamic component loading and resource management
- Enhanced internationalization support
- Optimized startup and shutdown sequences
"""

from .tab_lifecycle_manager import TabLifecycleManager
from .component_bus import ComponentBus
from .theme_manager import ThemeManager
from .state_manager import StateManager
from .performance_monitor import PerformanceMonitor
from .component_loader import ComponentLoader
from .i18n_manager import I18nManager
from .lifecycle_manager import LifecycleManager
from .app_controller import AppController

__all__ = [
    'TabLifecycleManager',
    'ComponentBus', 
    'ThemeManager',
    'StateManager',
    'PerformanceMonitor',
    'ComponentLoader',
    'I18nManager',
    'LifecycleManager',
    'AppController'
] 