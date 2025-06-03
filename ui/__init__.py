# UI Module - v2.0 Component Architecture
"""
Main UI Module with v2.0 Component Architecture Support

This module provides the main UI components and maintains backward compatibility
for existing imports while supporting the new component architecture.

NEW v2.0 ARCHITECTURE:
- Components organized in ui.components.*
- Modular, reusable components
- Enhanced testability and maintainability

BACKWARD COMPATIBILITY:
- Legacy import paths still supported during transition
- Deprecation warnings guide migration to new paths
- Compatibility wrappers for module-level imports
- Timeline for removal: Legacy support until v3.0 (estimated 2025)
"""

import warnings
import sys
from typing import TYPE_CHECKING, Any, Dict, Optional

# ============================================================================
# v2.0 Component Architecture Imports
# ============================================================================

# Main window (unchanged location)
from .main_window import MainWindow

# v2.0 Component architecture - preferred imports
from .components.tabs import VideoInfoTab, DownloadedVideosTab
from .components import (
    # Export commonly used components for convenience
    VideoTable, FilterableVideoTable,
    ActionButtonGroup, ProgressTracker, 
    LanguageSupport, ThemeSupport,
    BaseTab, TabConfig
)

# ============================================================================
# Enhanced Backward Compatibility Layer
# ============================================================================

# Compatibility configuration
COMPATIBILITY_CONFIG = {
    'deprecation_warnings_enabled': True,
    'legacy_module_support': True,
    'removal_version': '3.0',
    'migration_deadline': '2025-12-31'
}

def _deprecated_import_warning(old_path: str, new_path: str, removal_version: str = "3.0"):
    """Issue enhanced deprecation warning for legacy imports"""
    if not COMPATIBILITY_CONFIG['deprecation_warnings_enabled']:
        return
        
    warnings.warn(
        f"\n{'='*60}\n"
        f"DEPRECATION WARNING: UI Architecture Migration\n"
        f"{'='*60}\n"
        f"Legacy import: '{old_path}'\n"
        f"New import: '{new_path}'\n"
        f"Removal version: v{removal_version}\n"
        f"Migration deadline: {COMPATIBILITY_CONFIG['migration_deadline']}\n"
        f"\nTo update your code:\n"
        f"1. Replace '{old_path}' with '{new_path}'\n"
        f"2. Review v2.0 architecture documentation\n"
        f"3. Test your changes thoroughly\n"
        f"{'='*60}",
        DeprecationWarning,
        stacklevel=3
    )

def _legacy_module_warning(module_name: str, recommended_import: str):
    """Issue warning for legacy module-level imports"""
    _deprecated_import_warning(
        f"import ui.{module_name}",
        recommended_import,
        COMPATIBILITY_CONFIG['removal_version']
    )

# Legacy access functions for backward compatibility
def get_main_window():
    """Get MainWindow class (legacy compatibility function)"""
    _deprecated_import_warning(
        'ui.get_main_window()', 
        'from ui import MainWindow'
    )
    return MainWindow

def get_video_info_tab():
    """Get VideoInfoTab class (legacy compatibility function)"""
    _deprecated_import_warning(
        'ui.get_video_info_tab()', 
        'from ui.components.tabs import VideoInfoTab'
    )
    return VideoInfoTab

def get_downloaded_videos_tab():
    """Get DownloadedVideosTab class (legacy compatibility function)"""
    _deprecated_import_warning(
        'ui.get_downloaded_videos_tab()', 
        'from ui.components.tabs import DownloadedVideosTab'
    )
    return DownloadedVideosTab

# Enhanced legacy support functions
def get_video_table():
    """Get VideoTable class (legacy compatibility function)"""
    _deprecated_import_warning(
        'ui.get_video_table()', 
        'from ui.components.tables import VideoTable'
    )
    return VideoTable

def get_action_button_group():
    """Get ActionButtonGroup class (legacy compatibility function)"""
    _deprecated_import_warning(
        'ui.get_action_button_group()', 
        'from ui.components.widgets import ActionButtonGroup'
    )
    return ActionButtonGroup

def get_progress_tracker():
    """Get ProgressTracker class (legacy compatibility function)"""
    _deprecated_import_warning(
        'ui.get_progress_tracker()', 
        'from ui.components.widgets import ProgressTracker'
    )
    return ProgressTracker

# ============================================================================
# Legacy Module Compatibility Layer
# ============================================================================

class LegacyModuleProxy:
    """Proxy class to handle legacy module imports with deprecation warnings"""
    
    def __init__(self, module_name: str, target_class: Any, recommended_import: str):
        self._module_name = module_name
        self._target_class = target_class
        self._recommended_import = recommended_import
        self._warned = False
    
    def __getattr__(self, name: str):
        if not self._warned:
            _legacy_module_warning(self._module_name, self._recommended_import)
            self._warned = True
        
        # Return the target class if the name matches the expected class name
        if hasattr(self._target_class, name) or name == self._target_class.__name__:
            return getattr(self._target_class, name, self._target_class)
        
        raise AttributeError(f"module 'ui.{self._module_name}' has no attribute '{name}'")

# Create legacy module proxies
video_info_tab = LegacyModuleProxy(
    'video_info_tab', 
    VideoInfoTab, 
    'from ui.components.tabs import VideoInfoTab'
)

downloaded_videos_tab = LegacyModuleProxy(
    'downloaded_videos_tab', 
    DownloadedVideosTab, 
    'from ui.components.tabs import DownloadedVideosTab'
)

# ============================================================================
# Compatibility Management Functions
# ============================================================================

def configure_compatibility(
    enable_warnings: bool = True,
    enable_legacy_modules: bool = True
) -> None:
    """Configure backward compatibility behavior"""
    COMPATIBILITY_CONFIG['deprecation_warnings_enabled'] = enable_warnings
    COMPATIBILITY_CONFIG['legacy_module_support'] = enable_legacy_modules

def get_compatibility_info() -> Dict[str, Any]:
    """Get information about current compatibility configuration"""
    return {
        'config': COMPATIBILITY_CONFIG.copy(),
        'legacy_functions_available': [
            'get_main_window', 'get_video_info_tab', 'get_downloaded_videos_tab',
            'get_video_table', 'get_action_button_group', 'get_progress_tracker'
        ],
        'legacy_modules_available': ['video_info_tab', 'downloaded_videos_tab'],
        'migration_guide': {
            'documentation': 'docs/migration/v2.0-architecture.md',
            'examples': 'docs/examples/component-migration.md',
            'support': 'https://github.com/project/issues'
        }
    }

def check_legacy_usage() -> Dict[str, Any]:
    """Check for legacy usage patterns in the current session"""
    # This would be enhanced to actually track usage in a real implementation
    return {
        'legacy_imports_detected': False,
        'warnings_issued': 0,
        'recommendations': [
            'Update import statements to use v2.0 architecture',
            'Review component documentation for new features',
            'Test migrated code thoroughly'
        ]
    }

# ============================================================================
# Module Exports
# ============================================================================

# Primary exports - v2.0 architecture
__all__ = [
    # Main components
    'MainWindow',
    'VideoInfoTab', 
    'DownloadedVideosTab',
    
    # Common components for convenience
    'VideoTable', 'FilterableVideoTable',
    'ActionButtonGroup', 'ProgressTracker',
    'LanguageSupport', 'ThemeSupport',
    'BaseTab', 'TabConfig',
    
    # Legacy compatibility functions
    'get_main_window',
    'get_video_info_tab', 
    'get_downloaded_videos_tab',
    'get_video_table',
    'get_action_button_group',
    'get_progress_tracker',
    
    # Legacy module proxies
    'video_info_tab',
    'downloaded_videos_tab',
    
    # Compatibility management
    'configure_compatibility',
    'get_compatibility_info',
    'check_legacy_usage'
]

# ============================================================================
# Type Checking Support
# ============================================================================

if TYPE_CHECKING:
    # Import types for better IDE support
    from .components.common import TabState, EventType
    from .components.widgets import ButtonConfig, ButtonType
    from .components.mixins import StatefulComponentMixin 

# ============================================================================
# Module-Level Import Interception (Advanced Compatibility)
# ============================================================================

def __getattr__(name: str) -> Any:
    """Handle dynamic attribute access for legacy module imports"""
    
    # Legacy module mappings
    legacy_modules = {
        'video_info_tab': video_info_tab,
        'downloaded_videos_tab': downloaded_videos_tab
    }
    
    if name in legacy_modules:
        return legacy_modules[name]
    
    # Legacy class mappings for direct access
    legacy_classes = {
        'VideoInfoTab': VideoInfoTab,
        'DownloadedVideosTab': DownloadedVideosTab,
        'VideoTable': VideoTable,
        'ActionButtonGroup': ActionButtonGroup,
        'ProgressTracker': ProgressTracker
    }
    
    if name in legacy_classes:
        return legacy_classes[name]
    
    raise AttributeError(f"module 'ui' has no attribute '{name}'") 