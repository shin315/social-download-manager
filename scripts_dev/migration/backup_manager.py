"""
Backup Manager for UI Migration

Handles backup creation, restoration, and management for UI migration process.
Provides comprehensive backup strategies with integrity checking and rollback support.
"""

import os
import shutil
import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass


@dataclass
class BackupResult:
    """Result of backup operation"""
    success: bool
    backup_path: Optional[str] = None
    backup_size: int = 0
    files_backed_up: int = 0
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


@dataclass
class BackupMetadata:
    """Metadata for backup tracking"""
    timestamp: str
    project_root: str
    components: List[str]
    backup_type: str = "ui_migration"
    file_count: int = 0
    total_size: int = 0
    file_hashes: Dict[str, str] = None
    
    def __post_init__(self):
        if self.file_hashes is None:
            self.file_hashes = {}


class BackupManager:
    """
    Manages backup operations for UI migration
    
    Features:
    - Component-specific backups
    - Integrity verification with checksums
    - Incremental backup support
    - Structured backup organization
    - Metadata tracking
    """
    
    def __init__(self, project_root: str, logger: logging.Logger):
        self.project_root = project_root
        self.logger = logger
        self.backup_root = os.path.join(project_root, 'backups')
        self.ensure_backup_directory()
    
    def ensure_backup_directory(self):
        """Ensure backup directory structure exists"""
        os.makedirs(self.backup_root, exist_ok=True)
        
        # Create subdirectories for organization
        subdirs = ['ui_migration', 'emergency', 'incremental', 'metadata']
        for subdir in subdirs:
            os.makedirs(os.path.join(self.backup_root, subdir), exist_ok=True)
    
    def create_backup(self, components: List[str], timestamp: str, backup_type: str = "ui_migration") -> Optional[str]:
        """
        Create comprehensive backup of specified components
        
        Args:
            components: List of component names to backup
            timestamp: Timestamp for backup identification
            backup_type: Type of backup (ui_migration, emergency, etc.)
            
        Returns:
            str: Path to created backup directory, None if failed
        """
        try:
            backup_name = f"{backup_type}_{timestamp}"
            backup_path = os.path.join(self.backup_root, backup_type, backup_name)
            
            self.logger.info(f"Creating backup: {backup_name}")
            
            # Create backup directory
            os.makedirs(backup_path, exist_ok=True)
            
            # Initialize metadata
            metadata = BackupMetadata(
                timestamp=timestamp,
                project_root=self.project_root,
                components=components,
                backup_type=backup_type
            )
            
            result = BackupResult(success=True)
            
            # Backup each component
            for component in components:
                component_result = self._backup_component(component, backup_path, metadata)
                
                if not component_result.success:
                    result.success = False
                    result.errors.extend(component_result.errors)
                else:
                    result.files_backed_up += component_result.files_backed_up
                    result.backup_size += component_result.backup_size
            
            # Backup additional critical files
            self._backup_critical_files(backup_path, metadata)
            
            # Save metadata
            self._save_backup_metadata(backup_path, metadata)
            
            # Verify backup integrity
            if not self._verify_backup_integrity(backup_path, metadata):
                result.success = False
                result.errors.append("Backup integrity verification failed")
            
            if result.success:
                result.backup_path = backup_path
                self.logger.info(f"✅ Backup created successfully: {backup_path}")
                self.logger.info(f"Files backed up: {result.files_backed_up}, Size: {result.backup_size/1024/1024:.1f}MB")
                return backup_path
            else:
                self.logger.error(f"❌ Backup creation failed")
                # Clean up failed backup
                if os.path.exists(backup_path):
                    shutil.rmtree(backup_path)
                return None
                
        except Exception as e:
            self.logger.error(f"Exception during backup creation: {e}")
            return None
    
    def _backup_component(self, component: str, backup_path: str, metadata: BackupMetadata) -> BackupResult:
        """Backup a specific UI component"""
        result = BackupResult(success=True)
        
        try:
            # Define component file patterns
            component_patterns = {
                'video_info_tab': [
                    'ui/video_info_tab.py',
                    'ui/components/tabs/video_info_tab.py',
                    'ui/adapters/video_info_tab_adapter.py'
                ],
                'downloaded_videos_tab': [
                    'ui/downloaded_videos_tab.py',
                    'ui/components/tabs/downloaded_videos_tab.py',
                    'ui/adapters/downloaded_videos_tab_adapter.py'
                ],
                'main_window': [
                    'ui/main_window.py',
                    'main.py'
                ]
            }
            
            patterns = component_patterns.get(component, [])
            if not patterns:
                result.warnings.append(f"Unknown component: {component}")
                return result
            
            component_backup_path = os.path.join(backup_path, component)
            os.makedirs(component_backup_path, exist_ok=True)
            
            # Backup files matching patterns
            for pattern in patterns:
                source_path = os.path.join(self.project_root, pattern)
                
                if os.path.exists(source_path):
                    # Create target directory structure
                    relative_dir = os.path.dirname(pattern)
                    if relative_dir:
                        target_dir = os.path.join(component_backup_path, relative_dir)
                        os.makedirs(target_dir, exist_ok=True)
                    
                    # Copy file
                    target_path = os.path.join(component_backup_path, pattern)
                    shutil.copy2(source_path, target_path)
                    
                    # Calculate file hash for integrity
                    file_hash = self._calculate_file_hash(source_path)
                    metadata.file_hashes[pattern] = file_hash
                    
                    # Update stats
                    file_size = os.path.getsize(source_path)
                    result.files_backed_up += 1
                    result.backup_size += file_size
                    metadata.file_count += 1
                    metadata.total_size += file_size
                    
                    self.logger.debug(f"Backed up: {pattern}")
                else:
                    result.warnings.append(f"File not found: {pattern}")
            
            # Backup related test files
            self._backup_component_tests(component, component_backup_path, metadata, result)
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Failed to backup component {component}: {str(e)}")
        
        return result
    
    def _backup_component_tests(self, component: str, backup_path: str, metadata: BackupMetadata, result: BackupResult):
        """Backup test files related to component"""
        try:
            test_patterns = {
                'video_info_tab': ['tests/ui/test_video_info_tab.py', 'tests/ui_migration/test_video_info_*'],
                'downloaded_videos_tab': ['tests/ui/test_downloaded_videos_tab.py', 'tests/ui_migration/test_downloaded_videos_*'],
                'main_window': ['tests/ui/test_main_window.py']
            }
            
            patterns = test_patterns.get(component, [])
            test_backup_path = os.path.join(backup_path, 'tests')
            
            for pattern in patterns:
                if '*' in pattern:
                    # Handle wildcard patterns
                    base_dir = os.path.dirname(pattern)
                    pattern_name = os.path.basename(pattern)
                    search_dir = os.path.join(self.project_root, base_dir)
                    
                    if os.path.exists(search_dir):
                        for file_name in os.listdir(search_dir):
                            if file_name.startswith(pattern_name.replace('*', '')):
                                source_file = os.path.join(search_dir, file_name)
                                if os.path.isfile(source_file):
                                    target_dir = os.path.join(test_backup_path, base_dir)
                                    os.makedirs(target_dir, exist_ok=True)
                                    shutil.copy2(source_file, os.path.join(target_dir, file_name))
                                    result.files_backed_up += 1
                else:
                    source_file = os.path.join(self.project_root, pattern)
                    if os.path.exists(source_file):
                        target_dir = os.path.join(test_backup_path, os.path.dirname(pattern))
                        os.makedirs(target_dir, exist_ok=True)
                        shutil.copy2(source_file, os.path.join(target_dir, os.path.basename(pattern)))
                        result.files_backed_up += 1
                        
        except Exception as e:
            self.logger.warning(f"Failed to backup tests for {component}: {e}")
    
    def _backup_critical_files(self, backup_path: str, metadata: BackupMetadata):
        """Backup critical project files"""
        try:
            critical_files = [
                'requirements.txt',
                'pyproject.toml',
                'config.json',
                'version.json',
                '.env',
                'main.py'
            ]
            
            critical_backup_path = os.path.join(backup_path, 'critical_files')
            os.makedirs(critical_backup_path, exist_ok=True)
            
            for file_name in critical_files:
                source_path = os.path.join(self.project_root, file_name)
                if os.path.exists(source_path):
                    shutil.copy2(source_path, os.path.join(critical_backup_path, file_name))
                    
                    # Add to metadata
                    file_hash = self._calculate_file_hash(source_path)
                    metadata.file_hashes[file_name] = file_hash
                    
                    file_size = os.path.getsize(source_path)
                    metadata.file_count += 1
                    metadata.total_size += file_size
                    
        except Exception as e:
            self.logger.warning(f"Failed to backup critical files: {e}")
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file for integrity verification"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception:
            return ""
    
    def _save_backup_metadata(self, backup_path: str, metadata: BackupMetadata):
        """Save backup metadata to JSON file"""
        try:
            metadata_file = os.path.join(backup_path, 'backup_metadata.json')
            metadata_dict = {
                'timestamp': metadata.timestamp,
                'project_root': metadata.project_root,
                'components': metadata.components,
                'backup_type': metadata.backup_type,
                'file_count': metadata.file_count,
                'total_size': metadata.total_size,
                'file_hashes': metadata.file_hashes,
                'created_at': datetime.now().isoformat(),
                'version': '1.0'
            }
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata_dict, f, indent=2)
                
        except Exception as e:
            self.logger.warning(f"Failed to save backup metadata: {e}")
    
    def _verify_backup_integrity(self, backup_path: str, metadata: BackupMetadata) -> bool:
        """Verify backup integrity using checksums"""
        try:
            for relative_path, expected_hash in metadata.file_hashes.items():
                # Find the backed up file
                backup_file_path = None
                
                # Check in component directories
                for component in metadata.components:
                    component_path = os.path.join(backup_path, component, relative_path)
                    if os.path.exists(component_path):
                        backup_file_path = component_path
                        break
                
                # Check in critical files
                if not backup_file_path:
                    critical_path = os.path.join(backup_path, 'critical_files', os.path.basename(relative_path))
                    if os.path.exists(critical_path):
                        backup_file_path = critical_path
                
                if backup_file_path and os.path.exists(backup_file_path):
                    actual_hash = self._calculate_file_hash(backup_file_path)
                    if actual_hash != expected_hash:
                        self.logger.error(f"Hash mismatch for {relative_path}")
                        return False
                else:
                    self.logger.error(f"Backup file not found: {relative_path}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Integrity verification failed: {e}")
            return False
    
    def list_backups(self, backup_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available backups"""
        backups = []
        
        try:
            search_dirs = [backup_type] if backup_type else ['ui_migration', 'emergency', 'incremental']
            
            for backup_dir in search_dirs:
                backup_type_path = os.path.join(self.backup_root, backup_dir)
                if not os.path.exists(backup_type_path):
                    continue
                
                for backup_name in os.listdir(backup_type_path):
                    backup_path = os.path.join(backup_type_path, backup_name)
                    if os.path.isdir(backup_path):
                        metadata_file = os.path.join(backup_path, 'backup_metadata.json')
                        
                        if os.path.exists(metadata_file):
                            try:
                                with open(metadata_file, 'r') as f:
                                    metadata = json.load(f)
                                
                                backups.append({
                                    'name': backup_name,
                                    'path': backup_path,
                                    'type': backup_dir,
                                    'timestamp': metadata.get('timestamp', ''),
                                    'components': metadata.get('components', []),
                                    'file_count': metadata.get('file_count', 0),
                                    'size': metadata.get('total_size', 0),
                                    'created_at': metadata.get('created_at', '')
                                })
                            except Exception as e:
                                self.logger.warning(f"Failed to read metadata for {backup_name}: {e}")
        
        except Exception as e:
            self.logger.error(f"Failed to list backups: {e}")
        
        return sorted(backups, key=lambda x: x['timestamp'], reverse=True)
    
    def create_emergency_backup(self) -> Optional[str]:
        """Create emergency backup of current state"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.logger.info("Creating emergency backup...")
        
        return self.create_backup(
            components=['video_info_tab', 'downloaded_videos_tab', 'main_window'],
            timestamp=timestamp,
            backup_type='emergency'
        )
    
    def get_backup_info(self, backup_path: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a backup"""
        try:
            metadata_file = os.path.join(backup_path, 'backup_metadata.json')
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to get backup info: {e}")
        
        return None 