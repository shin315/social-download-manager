"""
Migration Error Handling & Rollback System for Social Download Manager

Provides comprehensive error handling and rollback capabilities for database migrations,
ensuring data safety and recovery options when migrations fail.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Callable
import logging
import sqlite3
import json
import shutil
import os
import time
from datetime import datetime, timezone

from .connection import SQLiteConnectionManager
from .migration_system.version_detection import DatabaseVersion, VersionManager
from .migration_system.schema_transformation import SchemaTransformationManager, TransformationPlan
from .migration_system.data_conversion import DataConversionManager, ConversionStats
from .exceptions import DatabaseError, MigrationError as BaseMigrationError


class MigrationStage(Enum):
    """Stages in the migration process"""
    PREPARATION = "preparation"
    BACKUP_CREATION = "backup_creation"
    SCHEMA_VALIDATION = "schema_validation"
    SCHEMA_TRANSFORMATION = "schema_transformation"
    DATA_CONVERSION = "data_conversion"
    FINAL_VALIDATION = "final_validation"
    CLEANUP = "cleanup"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class RollbackOperation(Enum):
    """Types of rollback operations"""
    RESTORE_FROM_BACKUP = "restore_from_backup"
    DROP_NEW_TABLES = "drop_new_tables"
    RENAME_TABLES_BACK = "rename_tables_back"
    REMOVE_MIGRATION_RECORDS = "remove_migration_records"
    RESTORE_ORIGINAL_FILE = "restore_original_file"


@dataclass
class MigrationError:
    """Represents a migration error with context"""
    stage: MigrationStage
    error_type: str
    error_message: str
    exception_details: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    recoverable: bool = True
    suggested_action: Optional[str] = None
    context_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RollbackStep:
    """Single rollback operation"""
    operation: RollbackOperation
    description: str
    sql_commands: List[str] = field(default_factory=list)
    file_operations: List[Tuple[str, str]] = field(default_factory=list)  # (source, destination)
    validation_query: Optional[str] = None
    error_on_failure: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MigrationState:
    """Complete state of a migration process"""
    migration_id: str
    source_version: DatabaseVersion
    target_version: DatabaseVersion
    current_stage: MigrationStage
    started_at: datetime
    completed_at: Optional[datetime] = None
    backup_paths: List[str] = field(default_factory=list)
    errors: List[MigrationError] = field(default_factory=list)
    rollback_plan: List[RollbackStep] = field(default_factory=list)
    success: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class IErrorHandler(ABC):
    """Interface for migration error handling"""
    
    @abstractmethod
    def handle_error(self, error: MigrationError, state: MigrationState) -> Tuple[bool, str]:
        """Handle migration error, return (should_continue, action_taken)"""
        pass
    
    @abstractmethod
    def should_rollback(self, errors: List[MigrationError], stage: MigrationStage) -> bool:
        """Determine if rollback should be triggered"""
        pass


class IRollbackManager(ABC):
    """Interface for rollback management"""
    
    @abstractmethod
    def create_rollback_plan(self, state: MigrationState) -> List[RollbackStep]:
        """Create rollback plan for current migration state"""
        pass
    
    @abstractmethod
    def execute_rollback(self, rollback_plan: List[RollbackStep]) -> Tuple[bool, List[str]]:
        """Execute rollback plan, return (success, error_messages)"""
        pass


class BackupManager:
    """Manages database backups for migration safety"""
    
    def __init__(self, connection_manager: SQLiteConnectionManager, backup_directory: str = "backups"):
        self.connection_manager = connection_manager
        self.backup_directory = Path(backup_directory)
        self.backup_directory.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    def create_full_backup(self, migration_id: str) -> str:
        """Create a complete database backup"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"migration_backup_{migration_id}_{timestamp}.db"
        backup_path = self.backup_directory / backup_filename
        
        try:
            # Get current database path - use the correct attribute
            db_path = self.connection_manager._config.database_path
            
            if not os.path.exists(db_path):
                raise BaseMigrationError(
                    message=f"Source database not found: {db_path}",
                    context=None
                )
            
            # Create backup using file copy (safer than SQL backup for SQLite)
            shutil.copy2(db_path, backup_path)
            
            # Verify backup integrity
            self._verify_backup_integrity(backup_path, db_path)
            
            self.logger.info(f"Created database backup: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            error_msg = f"Failed to create database backup: {e}"
            self.logger.error(error_msg)
            raise BaseMigrationError(
                message=error_msg,
                context=None,
                original_error=e
            )
    
    def restore_from_backup(self, backup_path: str) -> bool:
        """Restore database from backup"""
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_path}")
            
            # Verify backup before restoration
            self._verify_backup_integrity(backup_path)
            
            # Get current database path - use the correct attribute
            db_path = self.connection_manager._config.database_path
            
            # Close any existing connections
            self.connection_manager.shutdown()
            
            # Replace current database with backup
            shutil.copy2(backup_path, db_path)
            
            # Reinitialize connection
            self.connection_manager.initialize()
            
            self.logger.info(f"Successfully restored database from backup: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore from backup {backup_path}: {e}")
            return False
    
    def _verify_backup_integrity(self, backup_path: str, original_path: str = None) -> None:
        """Verify backup file integrity"""
        try:
            # Basic file size check
            backup_size = os.path.getsize(backup_path)
            if backup_size == 0:
                raise ValueError("Backup file is empty")
            
            # SQLite integrity check
            temp_conn = sqlite3.connect(backup_path)
            cursor = temp_conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            temp_conn.close()
            
            if result[0] != "ok":
                raise ValueError(f"Backup integrity check failed: {result[0]}")
            
            # Size comparison if original provided
            if original_path and os.path.exists(original_path):
                original_size = os.path.getsize(original_path)
                size_difference_pct = abs(backup_size - original_size) / original_size * 100
                
                if size_difference_pct > 10:  # Allow 10% difference
                    self.logger.warning(f"Backup size differs significantly from original: {size_difference_pct:.1f}%")
            
        except Exception as e:
            raise ValueError(f"Backup integrity verification failed: {e}")
    
    def cleanup_old_backups(self, keep_count: int = 5) -> List[str]:
        """Clean up old backup files, keeping only the most recent ones"""
        try:
            backup_files = list(self.backup_directory.glob("migration_backup_*.db"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            removed_files = []
            for backup_file in backup_files[keep_count:]:
                backup_file.unlink()
                removed_files.append(str(backup_file))
            
            if removed_files:
                self.logger.info(f"Cleaned up {len(removed_files)} old backup files")
            
            return removed_files
            
        except Exception as e:
            self.logger.warning(f"Failed to cleanup old backups: {e}")
            return []


class SQLiteErrorHandler(IErrorHandler):
    """SQLite-specific error handling implementation"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Define which errors are recoverable vs fatal
        self.fatal_error_patterns = [
            "disk full",
            "database disk image is malformed",
            "file is encrypted",
            "permission denied",
            "access denied"
        ]
        
        self.recoverable_error_patterns = [
            "table already exists",
            "column already exists",
            "no such table",
            "syntax error"
        ]
    
    def handle_error(self, error: MigrationError, state: MigrationState) -> Tuple[bool, str]:
        """Handle migration error and determine if process should continue"""
        
        error_msg_lower = error.error_message.lower()
        
        # Check for fatal errors
        for pattern in self.fatal_error_patterns:
            if pattern in error_msg_lower:
                error.recoverable = False
                action = f"Fatal error detected ({pattern}), migration must be aborted"
                self.logger.error(f"Fatal migration error: {action}")
                return False, action
        
        # Check for recoverable errors
        for pattern in self.recoverable_error_patterns:
            if pattern in error_msg_lower:
                error.recoverable = True
                action = f"Recoverable error detected ({pattern}), attempting to continue"
                self.logger.warning(f"Recoverable migration error: {action}")
                return True, action
        
        # For unknown errors, be conservative
        if error.stage in [MigrationStage.BACKUP_CREATION, MigrationStage.SCHEMA_TRANSFORMATION]:
            error.recoverable = False
            action = "Unknown error in critical stage, aborting migration"
            return False, action
        else:
            error.recoverable = True
            action = "Unknown error in non-critical stage, attempting to continue"
            return True, action
    
    def should_rollback(self, errors: List[MigrationError], stage: MigrationStage) -> bool:
        """Determine if rollback should be triggered based on errors"""
        
        # Always rollback if any fatal errors
        fatal_errors = [e for e in errors if not e.recoverable]
        if fatal_errors:
            return True
        
        # Rollback if too many errors in critical stages
        critical_stage_errors = [e for e in errors if e.stage in [
            MigrationStage.SCHEMA_TRANSFORMATION,
            MigrationStage.DATA_CONVERSION,
            MigrationStage.FINAL_VALIDATION
        ]]
        
        if len(critical_stage_errors) >= 3:
            return True
        
        # Rollback if current stage is critical and has errors
        if stage in [MigrationStage.SCHEMA_TRANSFORMATION, MigrationStage.DATA_CONVERSION]:
            stage_errors = [e for e in errors if e.stage == stage]
            if len(stage_errors) >= 2:
                return True
        
        return False


class SQLiteRollbackManager(IRollbackManager):
    """SQLite-specific rollback management implementation"""
    
    def __init__(self, connection_manager: SQLiteConnectionManager, backup_manager: BackupManager):
        self.connection_manager = connection_manager
        self.backup_manager = backup_manager
        self.logger = logging.getLogger(__name__)
    
    def create_rollback_plan(self, state: MigrationState) -> List[RollbackStep]:
        """Create rollback plan based on migration state"""
        rollback_steps = []
        
        # Determine rollback strategy based on current stage
        if state.current_stage in [MigrationStage.PREPARATION, MigrationStage.BACKUP_CREATION]:
            # Early stage - just cleanup any temp files
            rollback_steps.append(RollbackStep(
                operation=RollbackOperation.REMOVE_MIGRATION_RECORDS,
                description="Clean up migration preparation artifacts",
                sql_commands=["DELETE FROM schema_migrations WHERE status = 'pending'"],
                error_on_failure=False
            ))
            
        elif state.current_stage in [MigrationStage.SCHEMA_VALIDATION, MigrationStage.SCHEMA_TRANSFORMATION]:
            # Schema transformation in progress - restore from backup
            if state.backup_paths:
                rollback_steps.append(RollbackStep(
                    operation=RollbackOperation.RESTORE_FROM_BACKUP,
                    description=f"Restore database from backup: {state.backup_paths[-1]}",
                    metadata={"backup_path": state.backup_paths[-1]}
                ))
            else:
                # Try to manually rollback schema changes
                rollback_steps.extend(self._create_schema_rollback_steps(state))
                
        elif state.current_stage in [MigrationStage.DATA_CONVERSION, MigrationStage.FINAL_VALIDATION]:
            # Data conversion stage - restore from backup (safest option)
            if state.backup_paths:
                rollback_steps.append(RollbackStep(
                    operation=RollbackOperation.RESTORE_FROM_BACKUP,
                    description=f"Restore database from backup: {state.backup_paths[-1]}",
                    metadata={"backup_path": state.backup_paths[-1]}
                ))
            
        elif state.current_stage == MigrationStage.CLEANUP:
            # Almost complete - just remove migration records
            rollback_steps.append(RollbackStep(
                operation=RollbackOperation.REMOVE_MIGRATION_RECORDS,
                description="Remove incomplete migration records",
                sql_commands=["UPDATE schema_migrations SET status = 'failed' WHERE status = 'pending'"],
                error_on_failure=False
            ))
        
        return rollback_steps
    
    def execute_rollback(self, rollback_plan: List[RollbackStep]) -> Tuple[bool, List[str]]:
        """Execute rollback plan"""
        error_messages = []
        
        try:
            self.logger.info(f"Starting rollback execution with {len(rollback_plan)} steps")
            
            for i, step in enumerate(rollback_plan, 1):
                self.logger.info(f"Rollback step {i}/{len(rollback_plan)}: {step.description}")
                
                try:
                    if step.operation == RollbackOperation.RESTORE_FROM_BACKUP:
                        self._execute_backup_restore(step)
                    elif step.operation == RollbackOperation.DROP_NEW_TABLES:
                        self._execute_sql_commands(step.sql_commands)
                    elif step.operation == RollbackOperation.RENAME_TABLES_BACK:
                        self._execute_sql_commands(step.sql_commands)
                    elif step.operation == RollbackOperation.REMOVE_MIGRATION_RECORDS:
                        self._execute_sql_commands(step.sql_commands)
                    elif step.operation == RollbackOperation.RESTORE_ORIGINAL_FILE:
                        self._execute_file_operations(step.file_operations)
                    
                    # Run validation if provided
                    if step.validation_query:
                        self._validate_rollback_step(step.validation_query)
                    
                    self.logger.info(f"Rollback step {i} completed successfully")
                    
                except Exception as e:
                    error_msg = f"Rollback step {i} failed: {e}"
                    error_messages.append(error_msg)
                    self.logger.error(error_msg)
                    
                    if step.error_on_failure:
                        return False, error_messages
                    else:
                        self.logger.warning(f"Continuing rollback despite step {i} failure")
            
            self.logger.info("Rollback execution completed successfully")
            return True, error_messages
            
        except Exception as e:
            error_msg = f"Critical rollback failure: {e}"
            error_messages.append(error_msg)
            self.logger.error(error_msg)
            return False, error_messages
    
    def _create_schema_rollback_steps(self, state: MigrationState) -> List[RollbackStep]:
        """Create manual schema rollback steps"""
        steps = []
        
        # Drop v2.0 tables if they exist
        v2_tables = ['schema_migrations', 'content', 'downloads', 'download_sessions', 'download_errors']
        
        for table in reversed(v2_tables):  # Reverse order for foreign key dependencies
            steps.append(RollbackStep(
                operation=RollbackOperation.DROP_NEW_TABLES,
                description=f"Drop v2.0 table: {table}",
                sql_commands=[f"DROP TABLE IF EXISTS {table}"],
                error_on_failure=False
            ))
        
        # Restore original downloads table if it was renamed
        steps.append(RollbackStep(
            operation=RollbackOperation.RENAME_TABLES_BACK,
            description="Restore original downloads table",
            sql_commands=["ALTER TABLE downloads_old RENAME TO downloads"],
            validation_query="SELECT COUNT(*) FROM downloads",
            error_on_failure=False
        ))
        
        return steps
    
    def _execute_backup_restore(self, step: RollbackStep) -> None:
        """Execute backup restoration"""
        backup_path = step.metadata.get("backup_path")
        if not backup_path:
            raise ValueError("Backup path not provided in rollback step")
        
        success = self.backup_manager.restore_from_backup(backup_path)
        if not success:
            raise RuntimeError(f"Failed to restore from backup: {backup_path}")
    
    def _execute_sql_commands(self, sql_commands: List[str]) -> None:
        """Execute SQL commands for rollback"""
        with self.connection_manager.connection() as conn:
            cursor = conn.cursor()
            for sql in sql_commands:
                cursor.execute(sql)
            conn.commit()
    
    def _execute_file_operations(self, file_operations: List[Tuple[str, str]]) -> None:
        """Execute file operations for rollback"""
        for source, destination in file_operations:
            if os.path.exists(source):
                shutil.copy2(source, destination)
            else:
                raise FileNotFoundError(f"Rollback source file not found: {source}")
    
    def _validate_rollback_step(self, validation_query: str) -> None:
        """Validate rollback step execution"""
        with self.connection_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(validation_query)
            result = cursor.fetchone()
            if not result:
                raise ValueError(f"Rollback validation failed: {validation_query}")


class MigrationSafetyManager:
    """High-level manager for migration safety, error handling, and rollback"""
    
    def __init__(self, connection_manager: SQLiteConnectionManager, backup_directory: str = "backups"):
        self.connection_manager = connection_manager
        self.backup_manager = BackupManager(connection_manager, backup_directory)
        self.error_handler = SQLiteErrorHandler()
        self.rollback_manager = SQLiteRollbackManager(connection_manager, self.backup_manager)
        self.logger = logging.getLogger(__name__)
        
        # Current migration state
        self.current_migration: Optional[MigrationState] = None
    
    def start_safe_migration(self, source_version: DatabaseVersion, target_version: DatabaseVersion) -> str:
        """Start a migration with safety measures"""
        migration_id = f"migration_{source_version.value}_to_{target_version.value}_{int(time.time())}"
        
        self.current_migration = MigrationState(
            migration_id=migration_id,
            source_version=source_version,
            target_version=target_version,
            current_stage=MigrationStage.PREPARATION,
            started_at=datetime.now(timezone.utc)
        )
        
        self.logger.info(f"Starting safe migration: {migration_id}")
        return migration_id
    
    def execute_stage_with_safety(self, stage: MigrationStage, operation: Callable, *args, **kwargs) -> Tuple[bool, Any]:
        """Execute a migration stage with error handling and rollback preparation"""
        if not self.current_migration:
            raise RuntimeError("No active migration - call start_safe_migration first")
        
        self.current_migration.current_stage = stage
        self.logger.info(f"Executing migration stage: {stage.value}")
        
        try:
            # Create backup if entering critical stage
            if stage in [MigrationStage.SCHEMA_TRANSFORMATION, MigrationStage.DATA_CONVERSION]:
                if not self.current_migration.backup_paths:
                    backup_path = self.backup_manager.create_full_backup(self.current_migration.migration_id)
                    self.current_migration.backup_paths.append(backup_path)
            
            # Execute the operation
            result = operation(*args, **kwargs)
            
            self.logger.info(f"Migration stage {stage.value} completed successfully")
            return True, result
            
        except Exception as e:
            # Create migration error
            migration_error = MigrationError(
                stage=stage,
                error_type=type(e).__name__,
                error_message=str(e),
                exception_details=repr(e),
                context_data={"args": str(args), "kwargs": str(kwargs)}
            )
            
            self.current_migration.errors.append(migration_error)
            
            # Handle the error
            should_continue, action_taken = self.error_handler.handle_error(migration_error, self.current_migration)
            
            if not should_continue or self.error_handler.should_rollback(self.current_migration.errors, stage):
                self.logger.error(f"Migration stage {stage.value} failed, initiating rollback")
                rollback_success, rollback_errors = self._execute_rollback()
                
                if rollback_success:
                    self.current_migration.current_stage = MigrationStage.ROLLED_BACK
                    self.logger.info("Migration rolled back successfully")
                else:
                    self.current_migration.current_stage = MigrationStage.FAILED
                    self.logger.error(f"Migration rollback failed: {rollback_errors}")
                
                return False, migration_error
            else:
                self.logger.warning(f"Migration stage {stage.value} had errors but continuing: {action_taken}")
                return True, result
    
    def complete_migration(self) -> Tuple[bool, str]:
        """Complete the migration and cleanup"""
        if not self.current_migration:
            return False, "No active migration"
        
        try:
            if self.current_migration.current_stage == MigrationStage.ROLLED_BACK:
                return False, "Migration was rolled back due to errors"
            
            if self.current_migration.errors:
                fatal_errors = [e for e in self.current_migration.errors if not e.recoverable]
                if fatal_errors:
                    return False, f"Migration completed with fatal errors: {len(fatal_errors)}"
            
            # Mark as completed
            self.current_migration.current_stage = MigrationStage.COMPLETED
            self.current_migration.completed_at = datetime.now(timezone.utc)
            self.current_migration.success = True
            
            # Cleanup old backups
            self.backup_manager.cleanup_old_backups()
            
            success_msg = f"Migration {self.current_migration.migration_id} completed successfully"
            if self.current_migration.errors:
                success_msg += f" with {len(self.current_migration.errors)} recoverable errors"
            
            self.logger.info(success_msg)
            return True, success_msg
            
        except Exception as e:
            self.logger.error(f"Failed to complete migration: {e}")
            return False, f"Migration completion failed: {e}"
    
    def _execute_rollback(self) -> Tuple[bool, List[str]]:
        """Execute rollback for current migration"""
        if not self.current_migration:
            return False, ["No active migration to rollback"]
        
        rollback_plan = self.rollback_manager.create_rollback_plan(self.current_migration)
        self.current_migration.rollback_plan = rollback_plan
        
        return self.rollback_manager.execute_rollback(rollback_plan)
    
    def get_migration_status(self) -> Optional[MigrationState]:
        """Get current migration status"""
        return self.current_migration 