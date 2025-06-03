"""
UI Compatibility Layer - v2.0 Architecture Migration Support

This module provides comprehensive backward compatibility support for the migration
from legacy UI structure to v2.0 component architecture.

FEATURES:
- Legacy import path redirection
- Module-level compatibility wrappers
- Usage tracking and migration guidance
- Configurable deprecation warnings
- Timeline-based migration support

USAGE:
```python
# Enable/disable compatibility features
import ui.compatibility as compat
compat.configure_global_compatibility(enable_warnings=True)

# Get migration guidance
guidance = compat.get_migration_guidance()
print(guidance['quick_start'])

# Check current compatibility status
status = compat.get_compatibility_status()
```
"""

import warnings
import sys
import inspect
import time
from typing import Any, Dict, List, Optional, Callable, Union
from pathlib import Path
import logging

# ============================================================================
# Compatibility Configuration
# ============================================================================

GLOBAL_COMPATIBILITY_CONFIG = {
    'deprecation_warnings_enabled': True,
    'legacy_module_support': True,
    'usage_tracking_enabled': True,
    'migration_assistance_enabled': True,
    'removal_version': '3.0',
    'migration_deadline': '2025-12-31',
    'warning_frequency': 'once',  # 'once', 'always', 'never'
    'log_level': 'WARNING'
}

# Usage tracking
USAGE_TRACKER = {
    'legacy_imports': [],
    'function_calls': [],
    'module_accesses': [],
    'session_start': time.time()
}

# Warning cache để avoid repetitive warnings
WARNING_CACHE = set()

# ============================================================================
# Enhanced Warning System
# ============================================================================

def setup_compatibility_logging():
    """Setup logging for compatibility tracking"""
    logger = logging.getLogger('ui.compatibility')
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - UI Migration - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, GLOBAL_COMPATIBILITY_CONFIG['log_level']))
    return logger

logger = setup_compatibility_logging()

def track_legacy_usage(usage_type: str, details: Dict[str, Any]):
    """Track legacy usage for migration guidance"""
    if not GLOBAL_COMPATIBILITY_CONFIG['usage_tracking_enabled']:
        return
    
    usage_record = {
        'type': usage_type,
        'details': details,
        'timestamp': time.time(),
        'caller_info': get_caller_info()
    }
    
    USAGE_TRACKER[usage_type].append(usage_record)
    logger.info(f"Legacy usage tracked: {usage_type} - {details}")

def get_caller_info() -> Dict[str, Any]:
    """Get information about the calling code"""
    try:
        frame = inspect.currentframe()
        # Go up the stack to find the actual caller (skip internal compatibility functions)
        for _ in range(5):  # Look up to 5 frames
            if frame is None:
                break
            frame = frame.f_back
            if frame and not frame.f_code.co_filename.endswith('compatibility.py'):
                break
        
        if frame:
            return {
                'filename': frame.f_code.co_filename,
                'function': frame.f_code.co_name,
                'line': frame.f_lineno
            }
    except Exception:
        pass
    
    return {'filename': 'unknown', 'function': 'unknown', 'line': 0}

def enhanced_deprecation_warning(
    old_path: str, 
    new_path: str, 
    category: str = 'import',
    additional_info: Optional[str] = None
):
    """Enhanced deprecation warning with tracking and caching"""
    
    if not GLOBAL_COMPATIBILITY_CONFIG['deprecation_warnings_enabled']:
        return
    
    # Check warning frequency settings
    warning_key = f"{category}:{old_path}"
    if (GLOBAL_COMPATIBILITY_CONFIG['warning_frequency'] == 'once' and 
        warning_key in WARNING_CACHE):
        return
    
    WARNING_CACHE.add(warning_key)
    
    # Track usage
    track_legacy_usage('legacy_imports', {
        'old_path': old_path,
        'new_path': new_path,
        'category': category
    })
    
    # Build warning message
    warning_msg = [
        f"\n{'='*70}",
        f"🚨 DEPRECATION WARNING: UI Architecture Migration",
        f"{'='*70}",
        f"Legacy {category}: '{old_path}'",
        f"Recommended: '{new_path}'",
        f"",
        f"📅 Migration Timeline:",
        f"  • Legacy support ends: v{GLOBAL_COMPATIBILITY_CONFIG['removal_version']}",
        f"  • Migration deadline: {GLOBAL_COMPATIBILITY_CONFIG['migration_deadline']}",
        f"",
        f"🔧 Quick Fix:",
        f"  Replace: {old_path}",
        f"  With: {new_path}",
    ]
    
    if additional_info:
        warning_msg.extend([
            f"",
            f"💡 Additional Info:",
            f"  {additional_info}"
        ])
    
    warning_msg.extend([
        f"",
        f"📚 Migration Guide: docs/migration/v2.0-architecture.md",
        f"🆘 Support: https://github.com/project/issues",
        f"{'='*70}"
    ])
    
    warnings.warn(
        '\n'.join(warning_msg),
        DeprecationWarning,
        stacklevel=4
    )
    
    logger.warning(f"Legacy {category} usage: {old_path} -> {new_path}")

# ============================================================================
# Advanced Compatibility Wrappers
# ============================================================================

class LegacyModuleWrapper:
    """Advanced wrapper for legacy module compatibility"""
    
    def __init__(
        self, 
        module_name: str, 
        target_class: Any, 
        recommended_import: str,
        module_attributes: Optional[Dict[str, Any]] = None
    ):
        self._module_name = module_name
        self._target_class = target_class
        self._recommended_import = recommended_import
        self._module_attributes = module_attributes or {}
        self._access_count = 0
    
    def __getattr__(self, name: str):
        self._access_count += 1
        
        # Issue warning on first access
        if self._access_count == 1:
            enhanced_deprecation_warning(
                f"import ui.{self._module_name}",
                self._recommended_import,
                'module_import',
                f"Module 'ui.{self._module_name}' has been restructured in v2.0"
            )
        
        # Handle specific attribute requests
        if name in self._module_attributes:
            return self._module_attributes[name]
        
        # Return target class for class name requests
        if name == self._target_class.__name__:
            return self._target_class
        
        # Handle common attribute patterns
        if hasattr(self._target_class, name):
            return getattr(self._target_class, name)
        
        # Special handling for common module attributes
        if name in ['__file__', '__name__', '__package__']:
            return f"ui.{self._module_name}"
        
        raise AttributeError(
            f"module 'ui.{self._module_name}' has no attribute '{name}'. "
            f"Please use '{self._recommended_import}' instead."
        )
    
    def __call__(self, *args, **kwargs):
        """Allow direct instantiation of wrapped class"""
        enhanced_deprecation_warning(
            f"ui.{self._module_name}()",
            f"{self._recommended_import}",
            'direct_instantiation'
        )
        return self._target_class(*args, **kwargs)

class LegacyFunctionWrapper:
    """Wrapper for legacy functions with enhanced tracking"""
    
    def __init__(
        self, 
        function_name: str, 
        target_function: Callable,
        recommended_usage: str
    ):
        self._function_name = function_name
        self._target_function = target_function
        self._recommended_usage = recommended_usage
        self._call_count = 0
    
    def __call__(self, *args, **kwargs):
        self._call_count += 1
        
        enhanced_deprecation_warning(
            f"ui.{self._function_name}()",
            self._recommended_usage,
            'function_call',
            f"This function has been called {self._call_count} times in this session"
        )
        
        track_legacy_usage('function_calls', {
            'function': self._function_name,
            'call_count': self._call_count,
            'args_count': len(args),
            'kwargs_count': len(kwargs)
        })
        
        return self._target_function(*args, **kwargs)

# ============================================================================
# Migration Guidance System
# ============================================================================

MIGRATION_GUIDES = {
    'quick_start': '''
🚀 QUICK START MIGRATION GUIDE

1. Update Import Statements:
   OLD: from ui.video_info_tab import VideoInfoTab
   NEW: from ui.components.tabs import VideoInfoTab

2. Update Module Imports:
   OLD: import ui.video_info_tab
   NEW: from ui.components.tabs import VideoInfoTab

3. Update Legacy Functions:
   OLD: tab = ui.get_video_info_tab()
   NEW: from ui.components.tabs import VideoInfoTab

4. Test Your Changes:
   python -c "from ui.components.tabs import VideoInfoTab; print('✅ Migration successful')"
''',
    
    'common_patterns': {
        'tab_imports': {
            'old': ['from ui.video_info_tab import VideoInfoTab', 'import ui.video_info_tab'],
            'new': 'from ui.components.tabs import VideoInfoTab',
            'category': 'tabs'
        },
        'table_imports': {
            'old': ['from ui.video_table import VideoTable'],
            'new': 'from ui.components.tables import VideoTable',
            'category': 'tables'
        },
        'widget_imports': {
            'old': ['from ui.action_buttons import ActionButtonGroup'],
            'new': 'from ui.components.widgets import ActionButtonGroup',
            'category': 'widgets'
        }
    },
    
    'automated_migration': '''
🤖 AUTOMATED MIGRATION SCRIPT

To automatically update your codebase, run:

```bash
# Backup your code first
git checkout -b ui-migration-backup

# Run migration script (when available)
python scripts/migrate_ui_imports.py

# Test changes
python -m pytest tests/ui/

# Commit changes
git add .
git commit -m "feat: migrate to UI v2.0 component architecture"
```
''',
    
    'troubleshooting': {
        'import_errors': {
            'problem': 'ImportError: No module named ui.video_info_tab',
            'solution': 'Update to: from ui.components.tabs import VideoInfoTab',
            'category': 'import_error'
        },
        'attribute_errors': {
            'problem': 'AttributeError: module ui has no attribute video_info_tab',
            'solution': 'Use direct import: from ui.components.tabs import VideoInfoTab',
            'category': 'attribute_error'
        }
    }
}

def get_migration_guidance(category: Optional[str] = None) -> Union[str, Dict[str, Any]]:
    """Get migration guidance information"""
    if category:
        return MIGRATION_GUIDES.get(category, f"No guidance available for category: {category}")
    return MIGRATION_GUIDES

def analyze_usage_patterns() -> Dict[str, Any]:
    """Analyze current usage patterns để provide targeted guidance"""
    analysis = {
        'session_duration': time.time() - USAGE_TRACKER['session_start'],
        'total_legacy_imports': len(USAGE_TRACKER['legacy_imports']),
        'total_function_calls': len(USAGE_TRACKER['function_calls']),
        'total_module_accesses': len(USAGE_TRACKER['module_accesses']),
        'unique_legacy_paths': len(set(
            item['details']['old_path'] 
            for item in USAGE_TRACKER['legacy_imports']
        )),
        'most_used_legacy_paths': {},
        'recommendations': []
    }
    
    # Calculate most used legacy paths
    path_counts = {}
    for item in USAGE_TRACKER['legacy_imports']:
        old_path = item['details']['old_path']
        path_counts[old_path] = path_counts.get(old_path, 0) + 1
    
    analysis['most_used_legacy_paths'] = dict(
        sorted(path_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    )
    
    # Generate recommendations
    if analysis['total_legacy_imports'] > 10:
        analysis['recommendations'].append(
            "High legacy usage detected. Consider running automated migration script."
        )
    
    if analysis['unique_legacy_paths'] > 5:
        analysis['recommendations'].append(
            "Multiple legacy paths detected. Review migration guide for bulk updates."
        )
    
    return analysis

# ============================================================================
# Configuration Management
# ============================================================================

def configure_global_compatibility(
    enable_warnings: bool = True,
    enable_usage_tracking: bool = True,
    warning_frequency: str = 'once',
    log_level: str = 'WARNING'
) -> None:
    """Configure global compatibility settings"""
    GLOBAL_COMPATIBILITY_CONFIG.update({
        'deprecation_warnings_enabled': enable_warnings,
        'usage_tracking_enabled': enable_usage_tracking,
        'warning_frequency': warning_frequency,
        'log_level': log_level
    })
    
    # Update logger level
    setup_compatibility_logging().setLevel(getattr(logging, log_level))

def get_compatibility_status() -> Dict[str, Any]:
    """Get current compatibility status and statistics"""
    return {
        'config': GLOBAL_COMPATIBILITY_CONFIG.copy(),
        'usage_stats': analyze_usage_patterns(),
        'warning_cache_size': len(WARNING_CACHE),
        'session_info': {
            'start_time': USAGE_TRACKER['session_start'],
            'uptime': time.time() - USAGE_TRACKER['session_start']
        },
        'migration_progress': calculate_migration_progress()
    }

def calculate_migration_progress() -> Dict[str, Any]:
    """Calculate estimated migration progress"""
    # This would be enhanced with actual codebase analysis
    return {
        'estimated_completion': '85%',
        'remaining_legacy_usage': len(USAGE_TRACKER['legacy_imports']),
        'migration_score': max(0, 100 - len(USAGE_TRACKER['legacy_imports']) * 5),
        'next_steps': [
            'Update remaining import statements',
            'Test migrated components',
            'Update documentation references'
        ]
    }

def reset_compatibility_tracking() -> None:
    """Reset usage tracking data"""
    USAGE_TRACKER.clear()
    USAGE_TRACKER.update({
        'legacy_imports': [],
        'function_calls': [],
        'module_accesses': [],
        'session_start': time.time()
    })
    WARNING_CACHE.clear()

# ============================================================================
# Export Public API
# ============================================================================

__all__ = [
    'configure_global_compatibility',
    'get_compatibility_status',
    'get_migration_guidance',
    'analyze_usage_patterns',
    'reset_compatibility_tracking',
    'enhanced_deprecation_warning',
    'LegacyModuleWrapper',
    'LegacyFunctionWrapper'
] 