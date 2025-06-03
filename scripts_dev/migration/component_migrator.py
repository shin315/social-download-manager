"""
Component Migrator for UI Migration

Handles the migration of individual UI components from legacy v1.2.1 architecture
to the new v2.0 component-based architecture with proper validation and error handling.
"""

import os
import re
import ast
import shutil
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MigrationResult:
    """Result of a migration operation"""
    success: bool
    component: str
    errors: List[str] = None
    warnings: List[str] = None
    files_modified: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.files_modified is None:
            self.files_modified = []


@dataclass
class ComponentMapping:
    """Mapping between legacy and v2.0 components"""
    legacy_path: str
    v2_path: str
    adapter_path: str
    import_mappings: Dict[str, str]
    class_mappings: Dict[str, str]


class ComponentMigrator:
    """
    Handles migration of UI components from legacy to v2.0 architecture
    
    Features:
    - Component replacement with adapter integration
    - Import statement updates
    - Class instantiation updates
    - File content migration
    - Rollback support
    """
    
    def __init__(self, project_root: str, logger: logging.Logger):
        self.project_root = project_root
        self.logger = logger
        self.migration_mappings = self._define_migration_mappings()
    
    def _define_migration_mappings(self) -> Dict[str, ComponentMapping]:
        """Define mappings between legacy and v2.0 components"""
        return {
            'video_info_tab': ComponentMapping(
                legacy_path='ui/video_info_tab.py',
                v2_path='ui/components/tabs/video_info_tab.py',
                adapter_path='ui/adapters/video_info_tab_adapter.py',
                import_mappings={
                    'from ui.video_info_tab import VideoInfoTab': 'from ui.adapters.video_info_tab_adapter import VideoInfoTabAdapter',
                    'ui.video_info_tab.VideoInfoTab': 'ui.adapters.video_info_tab_adapter.VideoInfoTabAdapter',
                    'VideoInfoTab': 'VideoInfoTabAdapter'
                },
                class_mappings={
                    'VideoInfoTab': 'VideoInfoTabAdapter'
                }
            ),
            'downloaded_videos_tab': ComponentMapping(
                legacy_path='ui/downloaded_videos_tab.py',
                v2_path='ui/components/tabs/downloaded_videos_tab.py',
                adapter_path='ui/adapters/downloaded_videos_tab_adapter.py',
                import_mappings={
                    'from ui.downloaded_videos_tab import DownloadedVideosTab': 'from ui.adapters.downloaded_videos_tab_adapter import DownloadedVideosTabAdapter',
                    'ui.downloaded_videos_tab.DownloadedVideosTab': 'ui.adapters.downloaded_videos_tab_adapter.DownloadedVideosTabAdapter',
                    'DownloadedVideosTab': 'DownloadedVideosTabAdapter'
                },
                class_mappings={
                    'DownloadedVideosTab': 'DownloadedVideosTabAdapter'
                }
            ),
            'main_window': ComponentMapping(
                legacy_path='ui/main_window.py',
                v2_path='ui/main_window.py',  # Main window stays in place but gets updated
                adapter_path='',  # No adapter for main window
                import_mappings={
                    'from ui.video_info_tab import VideoInfoTab': 'from ui.adapters.video_info_tab_adapter import VideoInfoTabAdapter',
                    'from ui.downloaded_videos_tab import DownloadedVideosTab': 'from ui.adapters.downloaded_videos_tab_adapter import DownloadedVideosTabAdapter'
                },
                class_mappings={
                    'VideoInfoTab': 'VideoInfoTabAdapter',
                    'DownloadedVideosTab': 'DownloadedVideosTabAdapter'
                }
            )
        }
    
    def migrate_component(self, component_name: str) -> MigrationResult:
        """
        Migrate a specific component from legacy to v2.0
        
        Args:
            component_name: Name of component to migrate
            
        Returns:
            MigrationResult: Result of migration operation
        """
        result = MigrationResult(success=True, component=component_name)
        
        try:
            if component_name not in self.migration_mappings:
                result.success = False
                result.errors.append(f"Unknown component: {component_name}")
                return result
            
            mapping = self.migration_mappings[component_name]
            
            self.logger.info(f"Starting migration of {component_name}")
            
            # Step 1: Validate component exists
            if not self._validate_component_exists(mapping, result):
                return result
            
            # Step 2: Create temporary backup for this component
            temp_backup_path = self._create_temp_backup(mapping, result)
            if not temp_backup_path:
                return result
            
            # Step 3: Perform component-specific migration
            if component_name == 'main_window':
                success = self._migrate_main_window(mapping, result)
            else:
                success = self._migrate_tab_component(mapping, result)
            
            if not success:
                self._restore_from_temp_backup(temp_backup_path, mapping)
                return result
            
            # Step 4: Update any files that reference this component
            self._update_component_references(component_name, mapping, result)
            
            # Step 5: Clean up temp backup on success
            self._cleanup_temp_backup(temp_backup_path)
            
            self.logger.info(f"✅ Component migration completed: {component_name}")
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Exception during migration: {str(e)}")
            self.logger.error(f"Exception migrating {component_name}: {e}")
        
        return result
    
    def _validate_component_exists(self, mapping: ComponentMapping, result: MigrationResult) -> bool:
        """Validate that required files exist for migration"""
        legacy_file = os.path.join(self.project_root, mapping.legacy_path)
        v2_file = os.path.join(self.project_root, mapping.v2_path)
        
        if not os.path.exists(legacy_file):
            result.errors.append(f"Legacy file not found: {mapping.legacy_path}")
            return False
        
        if not os.path.exists(v2_file):
            result.errors.append(f"V2.0 file not found: {mapping.v2_path}")
            return False
        
        if mapping.adapter_path and not os.path.exists(os.path.join(self.project_root, mapping.adapter_path)):
            result.errors.append(f"Adapter file not found: {mapping.adapter_path}")
            return False
        
        return True
    
    def _create_temp_backup(self, mapping: ComponentMapping, result: MigrationResult) -> Optional[str]:
        """Create temporary backup of component before migration"""
        try:
            temp_backup_dir = os.path.join(self.project_root, '.migration_temp')
            os.makedirs(temp_backup_dir, exist_ok=True)
            
            # Backup legacy file
            legacy_file = os.path.join(self.project_root, mapping.legacy_path)
            temp_legacy = os.path.join(temp_backup_dir, f"legacy_{os.path.basename(mapping.legacy_path)}")
            shutil.copy2(legacy_file, temp_legacy)
            
            return temp_backup_dir
            
        except Exception as e:
            result.errors.append(f"Failed to create temp backup: {str(e)}")
            return None
    
    def _migrate_tab_component(self, mapping: ComponentMapping, result: MigrationResult) -> bool:
        """Migrate a tab component (video_info_tab or downloaded_videos_tab)"""
        try:
            legacy_file = os.path.join(self.project_root, mapping.legacy_path)
            
            # Step 1: Rename legacy file to .legacy extension
            legacy_backup = f"{legacy_file}.legacy"
            shutil.move(legacy_file, legacy_backup)
            result.files_modified.append(f"{mapping.legacy_path}.legacy")
            
            # Step 2: Create adapter-based replacement file
            adapter_content = self._generate_adapter_wrapper(mapping)
            
            with open(legacy_file, 'w', encoding='utf-8') as f:
                f.write(adapter_content)
            
            result.files_modified.append(mapping.legacy_path)
            
            self.logger.info(f"✅ Tab component migrated: {mapping.legacy_path}")
            return True
            
        except Exception as e:
            result.errors.append(f"Failed to migrate tab component: {str(e)}")
            return False
    
    def _migrate_main_window(self, mapping: ComponentMapping, result: MigrationResult) -> bool:
        """Migrate main window with import updates"""
        try:
            main_window_file = os.path.join(self.project_root, mapping.legacy_path)
            
            # Read current content
            with open(main_window_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Create backup
            backup_file = f"{main_window_file}.legacy"
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(content)
            result.files_modified.append(f"{mapping.legacy_path}.legacy")
            
            # Update imports and class references
            updated_content = self._update_file_content(content, mapping)
            
            # Write updated content
            with open(main_window_file, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            result.files_modified.append(mapping.legacy_path)
            
            self.logger.info(f"✅ Main window migrated: {mapping.legacy_path}")
            return True
            
        except Exception as e:
            result.errors.append(f"Failed to migrate main window: {str(e)}")
            return False
    
    def _generate_adapter_wrapper(self, mapping: ComponentMapping) -> str:
        """Generate adapter wrapper content for replaced component"""
        component_name = os.path.splitext(os.path.basename(mapping.legacy_path))[0]
        adapter_name = os.path.splitext(os.path.basename(mapping.adapter_path))[0]
        
        return f'''"""
Legacy Component Wrapper: {component_name}

This file provides backward compatibility by wrapping the v2.0 adapter.
The original component has been migrated to the v2.0 architecture.

Legacy file backed up as: {mapping.legacy_path}.legacy
New v2.0 component: {mapping.v2_path}
Adapter implementation: {mapping.adapter_path}
"""

# Import the adapter as the legacy class name for compatibility
from {mapping.adapter_path.replace('/', '.').replace('.py', '')} import {list(mapping.class_mappings.values())[0]} as {list(mapping.class_mappings.keys())[0]}

# Export the adapter with legacy name for backward compatibility
__all__ = ['{list(mapping.class_mappings.keys())[0]}']

# Legacy compatibility notice
import warnings
warnings.warn(
    f"Using legacy import path for {{'{list(mapping.class_mappings.keys())[0]}'}}. "
    f"Consider updating to use the adapter directly: {{'{mapping.adapter_path}'}}", 
    DeprecationWarning, 
    stacklevel=2
)
'''
    
    def _update_file_content(self, content: str, mapping: ComponentMapping) -> str:
        """Update file content with new imports and class references"""
        updated_content = content
        
        # Update imports
        for old_import, new_import in mapping.import_mappings.items():
            # Handle different import formats
            import_patterns = [
                f"^{re.escape(old_import)}$",
                f"^{re.escape(old_import)},",
                f", {re.escape(old_import)}$",
                f", {re.escape(old_import)},",
            ]
            
            for pattern in import_patterns:
                updated_content = re.sub(
                    pattern,
                    lambda m: m.group(0).replace(old_import, new_import),
                    updated_content,
                    flags=re.MULTILINE
                )
        
        # Update class instantiations and references
        for old_class, new_class in mapping.class_mappings.items():
            # Update instantiations: ClassName( -> NewClassName(
            updated_content = re.sub(
                rf'\b{re.escape(old_class)}\s*\(',
                f'{new_class}(',
                updated_content
            )
            
            # Update type annotations: : ClassName -> : NewClassName
            updated_content = re.sub(
                rf':\s*{re.escape(old_class)}\b',
                f': {new_class}',
                updated_content
            )
            
            # Update isinstance checks: isinstance(obj, ClassName) -> isinstance(obj, NewClassName)
            updated_content = re.sub(
                rf'\bisinstance\s*\(\s*[^,]+,\s*{re.escape(old_class)}\s*\)',
                lambda m: m.group(0).replace(old_class, new_class),
                updated_content
            )
        
        return updated_content
    
    def _update_component_references(self, component_name: str, mapping: ComponentMapping, result: MigrationResult):
        """Update references to the component in other files"""
        try:
            # Files that commonly reference UI components
            reference_files = [
                'main.py',
                'ui/main_window.py',
                'tests/ui/test_main_window.py',
                'tests/integration/test_ui_integration.py'
            ]
            
            for ref_file in reference_files:
                ref_path = os.path.join(self.project_root, ref_file)
                if os.path.exists(ref_path):
                    if self._update_file_references(ref_path, mapping):
                        result.files_modified.append(ref_file)
                        
        except Exception as e:
            result.warnings.append(f"Failed to update references: {str(e)}")
    
    def _update_file_references(self, file_path: str, mapping: ComponentMapping) -> bool:
        """Update references in a specific file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            updated_content = self._update_file_content(content, mapping)
            
            if updated_content != original_content:
                # Create backup
                backup_path = f"{file_path}.migration_backup"
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                
                # Write updated content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                
                self.logger.debug(f"Updated references in: {file_path}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.warning(f"Failed to update references in {file_path}: {e}")
            return False
    
    def _restore_from_temp_backup(self, temp_backup_path: str, mapping: ComponentMapping):
        """Restore component from temporary backup"""
        try:
            temp_legacy = os.path.join(temp_backup_path, f"legacy_{os.path.basename(mapping.legacy_path)}")
            if os.path.exists(temp_legacy):
                legacy_file = os.path.join(self.project_root, mapping.legacy_path)
                shutil.copy2(temp_legacy, legacy_file)
                self.logger.info(f"Restored from backup: {mapping.legacy_path}")
        except Exception as e:
            self.logger.error(f"Failed to restore from backup: {e}")
    
    def _cleanup_temp_backup(self, temp_backup_path: str):
        """Clean up temporary backup directory"""
        try:
            if os.path.exists(temp_backup_path):
                shutil.rmtree(temp_backup_path)
        except Exception as e:
            self.logger.warning(f"Failed to cleanup temp backup: {e}")
    
    def update_imports(self) -> MigrationResult:
        """Update all import statements across the project"""
        result = MigrationResult(success=True, component="project_imports")
        
        try:
            # Find all Python files that might need import updates
            python_files = []
            for root, dirs, files in os.walk(self.project_root):
                # Skip backup and temp directories
                if any(skip in root for skip in ['.git', '__pycache__', '.migration_temp', 'backups']):
                    continue
                
                for file in files:
                    if file.endswith('.py'):
                        python_files.append(os.path.join(root, file))
            
            # Update imports in each file
            for file_path in python_files:
                try:
                    if self._update_file_imports(file_path):
                        relative_path = os.path.relpath(file_path, self.project_root)
                        result.files_modified.append(relative_path)
                except Exception as e:
                    result.warnings.append(f"Failed to update imports in {file_path}: {str(e)}")
            
            self.logger.info(f"✅ Updated imports in {len(result.files_modified)} files")
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Failed to update imports: {str(e)}")
        
        return result
    
    def _update_file_imports(self, file_path: str) -> bool:
        """Update imports in a specific file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Apply all import mappings
            for mapping in self.migration_mappings.values():
                content = self._update_file_content(content, mapping)
            
            if content != original_content:
                # Create backup
                backup_path = f"{file_path}.import_backup"
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                
                # Write updated content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Skipped updating imports in {file_path}: {e}")
            return False
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status"""
        status = {
            'available_components': list(self.migration_mappings.keys()),
            'legacy_files_exist': {},
            'v2_files_exist': {},
            'adapter_files_exist': {}
        }
        
        for component, mapping in self.migration_mappings.items():
            legacy_path = os.path.join(self.project_root, mapping.legacy_path)
            v2_path = os.path.join(self.project_root, mapping.v2_path)
            
            status['legacy_files_exist'][component] = os.path.exists(legacy_path)
            status['v2_files_exist'][component] = os.path.exists(v2_path)
            
            if mapping.adapter_path:
                adapter_path = os.path.join(self.project_root, mapping.adapter_path)
                status['adapter_files_exist'][component] = os.path.exists(adapter_path)
        
        return status 