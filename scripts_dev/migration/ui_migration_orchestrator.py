#!/usr/bin/env python3
"""
UI Migration Orchestrator: v1.2.1 → v2.0 Architecture

This script orchestrates the complete migration from legacy v1.2.1 UI components
to the new v2.0 component-based architecture with proper backup, validation,
and rollback mechanisms.

Usage:
    python ui_migration_orchestrator.py [--dry-run] [--rollback] [--force]
"""

import os
import sys
import json
import shutil
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import argparse
from dataclasses import dataclass, asdict
from enum import Enum

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts_dev.migration.backup_manager import BackupManager
from scripts_dev.migration.component_migrator import ComponentMigrator
from scripts_dev.migration.config_migrator import ConfigMigrator
from scripts_dev.migration.validation_engine import ValidationEngine
from scripts_dev.migration.rollback_manager import RollbackManager


class MigrationPhase(Enum):
    """Migration phases for tracking progress"""
    PREPARING = "preparing"
    BACKING_UP = "backing_up"
    VALIDATING_PRECONDITIONS = "validating_preconditions"
    MIGRATING_COMPONENTS = "migrating_components"
    MIGRATING_CONFIG = "migrating_config"
    UPDATING_IMPORTS = "updating_imports"
    VALIDATING_MIGRATION = "validating_migration"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class MigrationConfig:
    """Configuration for migration process"""
    project_root: str
    backup_enabled: bool = True
    validation_enabled: bool = True
    force_migration: bool = False
    dry_run: bool = False
    keep_legacy_backup: bool = True
    rollback_on_failure: bool = True
    migration_timestamp: str = ""
    components_to_migrate: List[str] = None
    
    def __post_init__(self):
        if not self.migration_timestamp:
            self.migration_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if self.components_to_migrate is None:
            self.components_to_migrate = ["video_info_tab", "downloaded_videos_tab", "main_window"]


@dataclass
class MigrationStatus:
    """Track migration progress and status"""
    phase: MigrationPhase = MigrationPhase.PREPARING
    total_steps: int = 0
    completed_steps: int = 0
    current_step: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    errors: List[str] = None
    warnings: List[str] = None
    backup_path: Optional[str] = None
    migrated_components: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.migrated_components is None:
            self.migrated_components = []


class UIMigrationOrchestrator:
    """
    Main orchestrator for UI migration from v1.2.1 to v2.0 architecture
    
    Coordinates all migration phases including backup, validation, 
    component migration, configuration updates, and rollback procedures.
    """
    
    def __init__(self, config: MigrationConfig):
        self.config = config
        self.status = MigrationStatus()
        self.logger = self._setup_logging()
        
        # Initialize migration managers
        self.backup_manager = BackupManager(config.project_root, self.logger)
        self.component_migrator = ComponentMigrator(config.project_root, self.logger)
        self.config_migrator = ConfigMigrator(config.project_root, self.logger)
        self.validation_engine = ValidationEngine(config.project_root, self.logger)
        self.rollback_manager = RollbackManager(config.project_root, self.logger)
        
        # Migration state file
        self.state_file = os.path.join(config.project_root, '.migration_state.json')
        
        self.logger.info(f"UI Migration Orchestrator initialized for: {config.project_root}")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive logging for migration process"""
        logger = logging.getLogger('ui_migration')
        logger.setLevel(logging.DEBUG)
        
        # Create logs directory if it doesn't exist
        log_dir = os.path.join(self.config.project_root, 'logs', 'migration')
        os.makedirs(log_dir, exist_ok=True)
        
        # File handler for detailed logging
        log_file = os.path.join(log_dir, f'migration_{self.config.migration_timestamp}.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler for user feedback
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        )
        simple_formatter = logging.Formatter('%(levelname)s: %(message)s')
        
        file_handler.setFormatter(detailed_formatter)
        console_handler.setFormatter(simple_formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def save_migration_state(self):
        """Save current migration state to file"""
        try:
            state_data = {
                'config': asdict(self.config),
                'status': asdict(self.status),
                'timestamp': datetime.now().isoformat()
            }
            with open(self.state_file, 'w') as f:
                json.dump(state_data, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to save migration state: {e}")
    
    def load_migration_state(self) -> bool:
        """Load previous migration state if available"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state_data = json.load(f)
                
                # Restore status
                status_dict = state_data.get('status', {})
                if status_dict.get('phase'):
                    status_dict['phase'] = MigrationPhase(status_dict['phase'])
                    
                for key, value in status_dict.items():
                    if hasattr(self.status, key):
                        setattr(self.status, key, value)
                
                self.logger.info(f"Loaded previous migration state: {self.status.phase}")
                return True
        except Exception as e:
            self.logger.warning(f"Could not load migration state: {e}")
        
        return False
    
    def run_migration(self) -> bool:
        """
        Execute the complete migration process
        
        Returns:
            bool: True if migration successful, False otherwise
        """
        try:
            self.logger.info("🚀 Starting UI Migration: v1.2.1 → v2.0")
            self.status.start_time = datetime.now()
            self.status.total_steps = 8  # Total migration phases
            
            # Check for existing migration state
            if not self.config.force_migration:
                self.load_migration_state()
                if self.status.phase in [MigrationPhase.COMPLETED, MigrationPhase.FAILED]:
                    self.logger.info(f"Previous migration found in state: {self.status.phase}")
                    if self.status.phase == MigrationPhase.COMPLETED:
                        self.logger.info("Migration already completed successfully!")
                        return True
                    else:
                        self.logger.warning("Previous migration failed. Use --force to retry.")
                        return False
            
            # Execute migration phases
            migration_steps = [
                (MigrationPhase.PREPARING, self._phase_prepare),
                (MigrationPhase.BACKING_UP, self._phase_backup),
                (MigrationPhase.VALIDATING_PRECONDITIONS, self._phase_validate_preconditions),
                (MigrationPhase.MIGRATING_COMPONENTS, self._phase_migrate_components),
                (MigrationPhase.MIGRATING_CONFIG, self._phase_migrate_config),
                (MigrationPhase.UPDATING_IMPORTS, self._phase_update_imports),
                (MigrationPhase.VALIDATING_MIGRATION, self._phase_validate_migration),
                (MigrationPhase.FINALIZING, self._phase_finalize)
            ]
            
            for phase, phase_func in migration_steps:
                if not self._execute_phase(phase, phase_func):
                    self.status.phase = MigrationPhase.FAILED
                    self.save_migration_state()
                    
                    if self.config.rollback_on_failure and not self.config.dry_run:
                        self.logger.warning("Migration failed. Initiating rollback...")
                        self.rollback_migration()
                    
                    return False
            
            # Migration completed successfully
            self.status.phase = MigrationPhase.COMPLETED
            self.status.end_time = datetime.now()
            self.save_migration_state()
            
            duration = self.status.end_time - self.status.start_time
            self.logger.info(f"🎉 Migration completed successfully in {duration}")
            self.logger.info(f"Backup available at: {self.status.backup_path}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Migration failed with exception: {e}")
            self.logger.error(traceback.format_exc())
            self.status.phase = MigrationPhase.FAILED
            self.status.errors.append(str(e))
            self.save_migration_state()
            return False
    
    def _execute_phase(self, phase: MigrationPhase, phase_func) -> bool:
        """Execute a migration phase with error handling"""
        try:
            self.status.phase = phase
            self.status.current_step = phase.value.replace('_', ' ').title()
            self.logger.info(f"📋 Phase {self.status.completed_steps + 1}/{self.status.total_steps}: {self.status.current_step}")
            
            self.save_migration_state()
            
            result = phase_func()
            
            if result:
                self.status.completed_steps += 1
                self.logger.info(f"✅ Phase completed: {self.status.current_step}")
            else:
                self.logger.error(f"❌ Phase failed: {self.status.current_step}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Exception in phase {phase}: {e}")
            self.status.errors.append(f"{phase}: {str(e)}")
            return False
    
    def _phase_prepare(self) -> bool:
        """Phase 1: Prepare for migration"""
        self.logger.info("Preparing migration environment...")
        
        # Verify project structure
        required_dirs = ['ui', 'ui/components', 'ui/adapters']
        for directory in required_dirs:
            dir_path = os.path.join(self.config.project_root, directory)
            if not os.path.exists(dir_path):
                self.logger.error(f"Required directory not found: {directory}")
                return False
        
        # Check for required files
        required_files = [
            'ui/video_info_tab.py',
            'ui/downloaded_videos_tab.py', 
            'ui/components/tabs/video_info_tab.py',
            'ui/components/tabs/downloaded_videos_tab.py'
        ]
        
        for file_path in required_files:
            full_path = os.path.join(self.config.project_root, file_path)
            if not os.path.exists(full_path):
                self.logger.error(f"Required file not found: {file_path}")
                return False
        
        self.logger.info("✅ Environment preparation completed")
        return True
    
    def _phase_backup(self) -> bool:
        """Phase 2: Create backup of current state"""
        if not self.config.backup_enabled:
            self.logger.info("Backup disabled, skipping...")
            return True
        
        self.logger.info("Creating backup of current UI components...")
        
        backup_path = self.backup_manager.create_backup(
            components=self.config.components_to_migrate,
            timestamp=self.config.migration_timestamp
        )
        
        if backup_path:
            self.status.backup_path = backup_path
            self.logger.info(f"✅ Backup created: {backup_path}")
            return True
        else:
            self.logger.error("❌ Backup creation failed")
            return False
    
    def _phase_validate_preconditions(self) -> bool:
        """Phase 3: Validate preconditions for migration"""
        if not self.config.validation_enabled:
            self.logger.info("Validation disabled, skipping...")
            return True
        
        self.logger.info("Validating migration preconditions...")
        
        validation_result = self.validation_engine.validate_preconditions(
            components=self.config.components_to_migrate
        )
        
        if validation_result.success:
            self.logger.info("✅ Precondition validation passed")
            for warning in validation_result.warnings:
                self.logger.warning(f"⚠️ {warning}")
                self.status.warnings.append(warning)
            return True
        else:
            self.logger.error("❌ Precondition validation failed")
            for error in validation_result.errors:
                self.logger.error(f"❌ {error}")
                self.status.errors.append(error)
            return False
    
    def _phase_migrate_components(self) -> bool:
        """Phase 4: Migrate UI components"""
        self.logger.info("Migrating UI components...")
        
        for component in self.config.components_to_migrate:
            self.logger.info(f"Migrating component: {component}")
            
            if self.config.dry_run:
                self.logger.info(f"[DRY RUN] Would migrate {component}")
                self.status.migrated_components.append(component)
                continue
            
            result = self.component_migrator.migrate_component(component)
            
            if result.success:
                self.logger.info(f"✅ Component migrated: {component}")
                self.status.migrated_components.append(component)
            else:
                self.logger.error(f"❌ Component migration failed: {component}")
                for error in result.errors:
                    self.logger.error(f"  - {error}")
                    self.status.errors.append(f"{component}: {error}")
                return False
        
        return True
    
    def _phase_migrate_config(self) -> bool:
        """Phase 5: Migrate configuration files"""
        self.logger.info("Migrating configuration...")
        
        if self.config.dry_run:
            self.logger.info("[DRY RUN] Would migrate configuration")
            return True
        
        result = self.config_migrator.migrate_config()
        
        if result.success:
            self.logger.info("✅ Configuration migrated")
            return True
        else:
            self.logger.error("❌ Configuration migration failed")
            for error in result.errors:
                self.logger.error(f"  - {error}")
                self.status.errors.append(f"Config: {error}")
            return False
    
    def _phase_update_imports(self) -> bool:
        """Phase 6: Update import statements"""
        self.logger.info("Updating import statements...")
        
        if self.config.dry_run:
            self.logger.info("[DRY RUN] Would update imports")
            return True
        
        result = self.component_migrator.update_imports()
        
        if result.success:
            self.logger.info("✅ Imports updated")
            return True
        else:
            self.logger.error("❌ Import update failed")
            for error in result.errors:
                self.logger.error(f"  - {error}")
                self.status.errors.append(f"Imports: {error}")
            return False
    
    def _phase_validate_migration(self) -> bool:
        """Phase 7: Validate migration results"""
        if not self.config.validation_enabled:
            self.logger.info("Validation disabled, skipping...")
            return True
        
        self.logger.info("Validating migration results...")
        
        validation_result = self.validation_engine.validate_migration(
            components=self.status.migrated_components,
            dry_run=self.config.dry_run
        )
        
        if validation_result.success:
            self.logger.info("✅ Migration validation passed")
            return True
        else:
            self.logger.error("❌ Migration validation failed")
            for error in validation_result.errors:
                self.logger.error(f"❌ {error}")
                self.status.errors.append(error)
            return False
    
    def _phase_finalize(self) -> bool:
        """Phase 8: Finalize migration"""
        self.logger.info("Finalizing migration...")
        
        if self.config.dry_run:
            self.logger.info("[DRY RUN] Migration simulation completed")
            return True
        
        # Clean up temporary files
        temp_files = ['.migration_temp', '.component_backup']
        for temp_file in temp_files:
            temp_path = os.path.join(self.config.project_root, temp_file)
            if os.path.exists(temp_path):
                try:
                    if os.path.isdir(temp_path):
                        shutil.rmtree(temp_path)
                    else:
                        os.remove(temp_path)
                except Exception as e:
                    self.logger.warning(f"Failed to clean up {temp_file}: {e}")
        
        # Update version information
        self._update_version_info()
        
        self.logger.info("✅ Migration finalized")
        return True
    
    def _update_version_info(self):
        """Update version information to reflect v2.0"""
        try:
            version_file = os.path.join(self.config.project_root, 'version.json')
            if os.path.exists(version_file):
                with open(version_file, 'r') as f:
                    version_data = json.load(f)
                
                version_data['ui_version'] = '2.0.0'
                version_data['migration_date'] = datetime.now().isoformat()
                version_data['legacy_version'] = '1.2.1'
                
                with open(version_file, 'w') as f:
                    json.dump(version_data, f, indent=2)
                
                self.logger.info("Version information updated")
        except Exception as e:
            self.logger.warning(f"Failed to update version info: {e}")
    
    def rollback_migration(self) -> bool:
        """Rollback migration to previous state"""
        try:
            self.logger.info("🔄 Starting migration rollback...")
            
            if not self.status.backup_path:
                self.logger.error("No backup path available for rollback")
                return False
            
            result = self.rollback_manager.rollback_from_backup(
                backup_path=self.status.backup_path,
                components=self.status.migrated_components
            )
            
            if result.success:
                self.status.phase = MigrationPhase.ROLLED_BACK
                self.save_migration_state()
                self.logger.info("✅ Rollback completed successfully")
                return True
            else:
                self.logger.error("❌ Rollback failed")
                for error in result.errors:
                    self.logger.error(f"  - {error}")
                return False
                
        except Exception as e:
            self.logger.error(f"Rollback failed with exception: {e}")
            return False
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status"""
        return {
            'phase': self.status.phase.value,
            'progress': f"{self.status.completed_steps}/{self.status.total_steps}",
            'current_step': self.status.current_step,
            'errors': self.status.errors,
            'warnings': self.status.warnings,
            'migrated_components': self.status.migrated_components,
            'backup_path': self.status.backup_path
        }


def main():
    """Main entry point for UI migration"""
    parser = argparse.ArgumentParser(description='UI Migration Orchestrator: v1.2.1 → v2.0')
    parser.add_argument('--project-root', default='.', help='Project root directory')
    parser.add_argument('--dry-run', action='store_true', help='Simulate migration without making changes')
    parser.add_argument('--rollback', action='store_true', help='Rollback previous migration')
    parser.add_argument('--force', action='store_true', help='Force migration even if already completed')
    parser.add_argument('--no-backup', action='store_true', help='Skip backup creation')
    parser.add_argument('--no-validation', action='store_true', help='Skip validation steps')
    parser.add_argument('--components', nargs='+', help='Specific components to migrate')
    parser.add_argument('--status', action='store_true', help='Show migration status')
    
    args = parser.parse_args()
    
    # Convert to absolute path
    project_root = os.path.abspath(args.project_root)
    
    # Create migration configuration
    config = MigrationConfig(
        project_root=project_root,
        backup_enabled=not args.no_backup,
        validation_enabled=not args.no_validation,
        force_migration=args.force,
        dry_run=args.dry_run,
        components_to_migrate=args.components
    )
    
    # Initialize orchestrator
    orchestrator = UIMigrationOrchestrator(config)
    
    try:
        if args.status:
            # Show current status
            orchestrator.load_migration_state()
            status = orchestrator.get_migration_status()
            print(json.dumps(status, indent=2))
            return
        
        if args.rollback:
            # Perform rollback
            success = orchestrator.rollback_migration()
            sys.exit(0 if success else 1)
        
        # Run migration
        success = orchestrator.run_migration()
        
        if success:
            print("\n🎉 Migration completed successfully!")
            if config.dry_run:
                print("This was a dry run. Use without --dry-run to perform actual migration.")
        else:
            print("\n❌ Migration failed. Check logs for details.")
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️ Migration interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 