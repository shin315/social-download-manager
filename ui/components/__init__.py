"""
UI Components Package

This package contains modular, reusable UI components extracted from the large UI files.
Components are organized by type: mixins, widgets, tables, and dialogs.
"""

from .mixins import *
from .widgets import *
from .tables import *
from .dialogs import *

__all__ = [
    # Mixins
    'LanguageSupport',
    'ThemeSupport', 
    'TooltipSupport',
    
    # Widgets
    'ActionButtonGroup',
    'StatisticsWidget',
    'ThumbnailWidget',
    'ProgressTracker',
    
    # Tables
    'VideoTable',
    'FilterableVideoTable',
    
    # Dialogs
    'FilterPopup',
    'CopyDialog',
    'ConfirmationDialog'
] 