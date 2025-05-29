"""
Schema Transformation Engine for Social Download Manager

Handles transformation of database schemas between different versions,
including table creation, column modifications, index creation, and data preservation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Callable
import logging
import sqlite3
import json
import re
from datetime import datetime, timezone

from data.database.connection import SQLiteConnectionManager
from .version_detection import VersionInfo, DatabaseVersion, VersionManager
from data.database.exceptions import DatabaseError, MigrationError


class TransformationType(Enum):
    """Types of schema transformations"""
    CREATE_TABLE = "create_table"
    ALTER_TABLE = "alter_table"
    DROP_TABLE = "drop_table"
    CREATE_INDEX = "create_index"
    DROP_INDEX = "drop_index"
    RENAME_TABLE = "rename_table"
    RENAME_COLUMN = "rename_column"
    ADD_COLUMN = "add_column"
    DROP_COLUMN = "drop_column"


@dataclass
class TransformationStep:
    """Single transformation operation"""
    step_type: TransformationType
    table_name: str
    sql_command: str
    description: str
    rollback_sql: Optional[str] = None
    depends_on: List[str] = field(default_factory=list)
    validates_with: Optional[Callable] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TransformationPlan:
    """Complete transformation plan between database versions"""
    source_version: DatabaseVersion
    target_version: DatabaseVersion
    steps: List[TransformationStep] = field(default_factory=list)
    estimated_duration_seconds: int = 60
    requires_backup: bool = True
    destructive_changes: bool = False
    validation_queries: List[str] = field(default_factory=list)
    
    def add_step(self, step: TransformationStep) -> None:
        """Add a transformation step to the plan"""
        self.steps.append(step)
    
    def get_dependencies_order(self) -> List[TransformationStep]:
        """Get steps in dependency-resolved order"""
        # Simple topological sort for dependency resolution
        resolved = []
        remaining = self.steps.copy()
        
        while remaining:
            # Find steps with no unresolved dependencies
            ready_steps = []
            for step in remaining:
                dependencies_resolved = all(
                    any(resolved_step.table_name == dep for resolved_step in resolved)
                    for dep in step.depends_on
                ) if step.depends_on else True
                
                if dependencies_resolved:
                    ready_steps.append(step)
            
            if not ready_steps:
                # Circular dependency or missing dependency
                remaining_tables = [step.table_name for step in remaining]
                raise MigrationError(f"Circular dependency detected in transformation plan: {remaining_tables}")
            
            # Add ready steps to resolved list
            for step in ready_steps:
                resolved.append(step)
                remaining.remove(step)
        
        return resolved


class ISchemaTransformer(ABC):
    """Interface for schema transformation engines"""
    
    @abstractmethod
    def create_transformation_plan(self, source_version: VersionInfo, target_version: DatabaseVersion) -> TransformationPlan:
        """Create a transformation plan between versions"""
        pass
    
    @abstractmethod
    def execute_transformation_plan(self, plan: TransformationPlan) -> bool:
        """Execute a transformation plan"""
        pass
    
    @abstractmethod
    def validate_transformation(self, plan: TransformationPlan) -> Tuple[bool, List[str]]:
        """Validate a transformation can be safely executed"""
        pass


class SQLiteSchemaTransformer(ISchemaTransformer):
    """SQLite-specific schema transformation implementation"""
    
    def __init__(self, connection_manager: SQLiteConnectionManager):
        self.connection_manager = connection_manager
        self.logger = logging.getLogger(__name__)
        
        # v2.0 Schema definitions for reference
        self.v2_schema_definitions = {
            'schema_migrations': '''
                CREATE TABLE schema_migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    executed_at TEXT,
                    execution_time_ms INTEGER,
                    rollback_sql TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            ''',
            'content': '''
                CREATE TABLE content (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform_id TEXT NOT NULL,
                    platform_content_id TEXT NOT NULL,
                    original_url TEXT NOT NULL,
                    title TEXT,
                    description TEXT,
                    author_name TEXT,
                    author_url TEXT,
                    thumbnail_url TEXT,
                    duration_seconds INTEGER,
                    view_count INTEGER,
                    like_count INTEGER,
                    content_type TEXT DEFAULT 'video',
                    published_at TEXT,
                    metadata_json TEXT,
                    status TEXT DEFAULT 'active',
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                )
            ''',
            'downloads': '''
                CREATE TABLE downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_id INTEGER NOT NULL,
                    file_path TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_size_bytes INTEGER,
                    format TEXT,
                    quality TEXT,
                    status TEXT DEFAULT 'pending',
                    download_started_at TEXT,
                    download_completed_at TEXT,
                    download_progress REAL DEFAULT 0.0,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    metadata_json TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (content_id) REFERENCES content(id)
                )
            ''',
            'download_sessions': '''
                CREATE TABLE download_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_name TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'active',
                    total_downloads INTEGER DEFAULT 0,
                    successful_downloads INTEGER DEFAULT 0,
                    failed_downloads INTEGER DEFAULT 0,
                    total_size_bytes INTEGER DEFAULT 0,
                    started_at TEXT,
                    completed_at TEXT,
                    metadata_json TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                )
            ''',
            'download_errors': '''
                CREATE TABLE download_errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    download_id INTEGER,
                    error_type TEXT NOT NULL,
                    error_message TEXT NOT NULL,
                    error_code TEXT,
                    stack_trace TEXT,
                    context_data TEXT,
                    retry_attempt INTEGER DEFAULT 0,
                    occurred_at TEXT DEFAULT (datetime('now')),
                    resolved BOOLEAN DEFAULT FALSE,
                    resolution_notes TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (download_id) REFERENCES downloads(id)
                )
            '''
        }
        
        # Index definitions for performance optimization
        self.v2_index_definitions = [
            "CREATE INDEX idx_content_platform ON content(platform_id)",
            "CREATE INDEX idx_content_status ON content(status)",
            "CREATE INDEX idx_content_platform_content_id ON content(platform_id, platform_content_id)",
            "CREATE INDEX idx_content_url ON content(original_url)",
            "CREATE INDEX idx_downloads_content_id ON downloads(content_id)",
            "CREATE INDEX idx_downloads_status ON downloads(status)",
            "CREATE INDEX idx_downloads_file_path ON downloads(file_path)",
            "CREATE INDEX idx_download_sessions_status ON download_sessions(status)",
            "CREATE INDEX idx_download_errors_download_id ON download_errors(download_id)",
            "CREATE INDEX idx_download_errors_occurred_at ON download_errors(occurred_at)",
            "CREATE INDEX idx_migrations_version ON schema_migrations(version)",
            "CREATE INDEX idx_migrations_status ON schema_migrations(status)",
            "CREATE INDEX idx_migrations_executed_at ON schema_migrations(executed_at)"
        ]
    
    def create_transformation_plan(self, source_version: VersionInfo, target_version: DatabaseVersion) -> TransformationPlan:
        """Create a transformation plan based on source and target versions"""
        
        if target_version != DatabaseVersion.V2_0_0:
            raise MigrationError(f"Unsupported target version: {target_version}")
        
        if source_version.version == DatabaseVersion.EMPTY:
            return self._create_fresh_install_plan()
        elif source_version.version == DatabaseVersion.V1_2_1:
            return self._create_v1_to_v2_migration_plan(source_version)
        elif source_version.version == DatabaseVersion.V2_0_0:
            return self._create_v2_repair_plan(source_version)
        else:
            raise MigrationError(f"Unsupported source version: {source_version.version}")
    
    def _create_fresh_install_plan(self) -> TransformationPlan:
        """Create transformation plan for fresh v2.0 installation"""
        plan = TransformationPlan(
            source_version=DatabaseVersion.EMPTY,
            target_version=DatabaseVersion.V2_0_0,
            estimated_duration_seconds=10,
            requires_backup=False,
            destructive_changes=False
        )
        
        # Create all v2.0 tables in dependency order
        table_order = ['schema_migrations', 'content', 'downloads', 'download_sessions', 'download_errors']
        
        for table_name in table_order:
            step = TransformationStep(
                step_type=TransformationType.CREATE_TABLE,
                table_name=table_name,
                sql_command=self.v2_schema_definitions[table_name].strip(),
                description=f"Create {table_name} table",
                rollback_sql=f"DROP TABLE IF EXISTS {table_name}"
            )
            plan.add_step(step)
        
        # Add indexes
        for index_sql in self.v2_index_definitions:
            index_name = self._extract_index_name(index_sql)
            step = TransformationStep(
                step_type=TransformationType.CREATE_INDEX,
                table_name="indexes",
                sql_command=index_sql,
                description=f"Create index {index_name}",
                rollback_sql=f"DROP INDEX IF EXISTS {index_name}"
            )
            plan.add_step(step)
        
        # Add validation queries
        plan.validation_queries = [
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name IN ('content', 'downloads', 'download_sessions', 'download_errors', 'schema_migrations')",
            "SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        ]
        
        return plan
    
    def _create_v1_to_v2_migration_plan(self, source_version: VersionInfo) -> TransformationPlan:
        """Create transformation plan for v1.2.1 to v2.0 migration"""
        plan = TransformationPlan(
            source_version=DatabaseVersion.V1_2_1,
            target_version=DatabaseVersion.V2_0_0,
            estimated_duration_seconds=120,
            requires_backup=True,
            destructive_changes=True
        )
        
        # Step 1: Create backup table for v1.2.1 data
        backup_step = TransformationStep(
            step_type=TransformationType.CREATE_TABLE,
            table_name="downloads_v1_backup",
            sql_command="""
                CREATE TABLE downloads_v1_backup AS 
                SELECT * FROM downloads
            """,
            description="Create backup of v1.2.1 downloads table",
            rollback_sql="DROP TABLE IF EXISTS downloads_v1_backup"
        )
        plan.add_step(backup_step)
        
        # Step 2: Create v2.0 tables (except downloads which needs special handling)
        table_order = ['schema_migrations', 'content', 'download_sessions', 'download_errors']
        
        for table_name in table_order:
            step = TransformationStep(
                step_type=TransformationType.CREATE_TABLE,
                table_name=table_name,
                sql_command=self.v2_schema_definitions[table_name].strip(),
                description=f"Create v2.0 {table_name} table",
                rollback_sql=f"DROP TABLE IF EXISTS {table_name}",
                depends_on=["downloads_v1_backup"]
            )
            plan.add_step(step)
        
        # Step 3: Rename old downloads table
        rename_step = TransformationStep(
            step_type=TransformationType.RENAME_TABLE,
            table_name="downloads_old",
            sql_command="ALTER TABLE downloads RENAME TO downloads_old",
            description="Rename old downloads table",
            rollback_sql="ALTER TABLE downloads_old RENAME TO downloads",
            depends_on=["content"]
        )
        plan.add_step(rename_step)
        
        # Step 4: Create new downloads table
        downloads_step = TransformationStep(
            step_type=TransformationType.CREATE_TABLE,
            table_name="downloads",
            sql_command=self.v2_schema_definitions['downloads'].strip(),
            description="Create v2.0 downloads table",
            rollback_sql="DROP TABLE IF EXISTS downloads",
            depends_on=["downloads_old"]
        )
        plan.add_step(downloads_step)
        
        # Step 5: Add indexes
        for index_sql in self.v2_index_definitions:
            index_name = self._extract_index_name(index_sql)
            step = TransformationStep(
                step_type=TransformationType.CREATE_INDEX,
                table_name="indexes",
                sql_command=index_sql,
                description=f"Create index {index_name}",
                rollback_sql=f"DROP INDEX IF EXISTS {index_name}",
                depends_on=["downloads"]
            )
            plan.add_step(step)
        
        # Validation queries for v1 to v2 migration
        plan.validation_queries = [
            "SELECT COUNT(*) FROM downloads_v1_backup",
            "SELECT COUNT(*) FROM content",
            "SELECT COUNT(*) FROM downloads",
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name IN ('content', 'downloads', 'download_sessions', 'download_errors', 'schema_migrations')"
        ]
        
        return plan
    
    def _create_v2_repair_plan(self, source_version: VersionInfo) -> TransformationPlan:
        """Create transformation plan for v2.0 schema repair"""
        plan = TransformationPlan(
            source_version=DatabaseVersion.V2_0_0,
            target_version=DatabaseVersion.V2_0_0,
            estimated_duration_seconds=30,
            requires_backup=False,
            destructive_changes=False
        )
        
        # Analyze what needs to be repaired based on validation errors
        missing_tables = []
        missing_indexes = []
        
        for error in source_version.validation_errors:
            if "Missing v2.0 tables:" in error:
                # Extract missing table names
                tables_str = error.split("Missing v2.0 tables: ")[1]
                missing_tables = [t.strip("{}''\"") for t in tables_str.split("'") if t.strip("{},'\"")]
            elif "Missing columns" in error:
                # Handle missing columns - would need more complex logic
                pass
        
        # Add missing tables
        for table_name in missing_tables:
            if table_name in self.v2_schema_definitions:
                step = TransformationStep(
                    step_type=TransformationType.CREATE_TABLE,
                    table_name=table_name,
                    sql_command=self.v2_schema_definitions[table_name].strip(),
                    description=f"Repair missing {table_name} table",
                    rollback_sql=f"DROP TABLE IF EXISTS {table_name}"
                )
                plan.add_step(step)
        
        # Add missing indexes (simplified - add all if any are missing)
        if missing_indexes or "index" in str(source_version.validation_errors).lower():
            for index_sql in self.v2_index_definitions:
                index_name = self._extract_index_name(index_sql)
                step = TransformationStep(
                    step_type=TransformationType.CREATE_INDEX,
                    table_name="indexes",
                    sql_command=f"CREATE INDEX IF NOT EXISTS {index_sql.split('CREATE INDEX ')[1]}",
                    description=f"Repair/create index {index_name}",
                    rollback_sql=f"DROP INDEX IF EXISTS {index_name}"
                )
                plan.add_step(step)
        
        return plan
    
    def execute_transformation_plan(self, plan: TransformationPlan) -> bool:
        """Execute a transformation plan with transaction safety"""
        start_time = datetime.now()
        
        try:
            # Get steps in dependency order
            ordered_steps = plan.get_dependencies_order()
            
            self.logger.info(f"Starting schema transformation: {plan.source_version} → {plan.target_version}")
            self.logger.info(f"Plan contains {len(ordered_steps)} steps")
            
            with self.connection_manager.connection() as conn:
                # Enable foreign key constraints
                conn.execute("PRAGMA foreign_keys = ON")
                
                # Execute each step
                for i, step in enumerate(ordered_steps, 1):
                    self.logger.info(f"Step {i}/{len(ordered_steps)}: {step.description}")
                    
                    try:
                        # Execute the transformation step
                        conn.execute(step.sql_command)
                        
                        # Run step validation if provided
                        if step.validates_with:
                            validation_result = step.validates_with(conn)
                            if not validation_result:
                                raise MigrationError(f"Step validation failed: {step.description}")
                        
                        self.logger.debug(f"Completed step: {step.description}")
                        
                    except Exception as e:
                        self.logger.error(f"Step failed: {step.description} - {e}")
                        raise MigrationError(f"Transformation step failed: {step.description} - {e}")
                
                # Run final validation queries
                if plan.validation_queries:
                    self.logger.info("Running final validation queries...")
                    for query in plan.validation_queries:
                        try:
                            result = conn.execute(query).fetchone()
                            self.logger.debug(f"Validation query result: {query} → {result}")
                        except Exception as e:
                            self.logger.warning(f"Validation query failed: {query} - {e}")
                
                # Commit all changes
                conn.commit()
                
                execution_time = (datetime.now() - start_time).total_seconds()
                self.logger.info(f"Schema transformation completed successfully in {execution_time:.2f} seconds")
                
                return True
                
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"Schema transformation failed after {execution_time:.2f} seconds: {e}")
            return False
    
    def validate_transformation(self, plan: TransformationPlan) -> Tuple[bool, List[str]]:
        """Validate that a transformation plan can be safely executed"""
        concerns = []
        
        try:
            # Check if we have database access
            with self.connection_manager.connection() as conn:
                cursor = conn.cursor()
                
                # Validate source state
                if plan.source_version == DatabaseVersion.V1_2_1:
                    # Check if v1.2.1 downloads table exists
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='downloads'")
                    if not cursor.fetchone():
                        concerns.append("v1.2.1 downloads table not found")
                    
                    # Check for data that would be affected
                    cursor.execute("SELECT COUNT(*) FROM downloads")
                    row_count = cursor.fetchone()[0]
                    if row_count > 10000:
                        concerns.append(f"Large dataset detected ({row_count} rows) - migration may take longer")
                
                # Check for conflicting tables (but allow existing downloads table for v1.2.1 migration)
                for step in plan.steps:
                    if step.step_type == TransformationType.CREATE_TABLE:
                        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{step.table_name}'")
                        table_exists = cursor.fetchone()
                        
                        # Allow existing downloads table if we're doing v1.2.1 migration and this is creating a backup or new tables
                        if table_exists and not step.table_name.endswith('_backup'):
                            # For v1.2.1 migration, we expect downloads table to exist initially
                            if plan.source_version == DatabaseVersion.V1_2_1 and step.table_name == 'downloads':
                                # This is expected - the new downloads table creation step will handle the existing one
                                continue
                            else:
                                concerns.append(f"Table {step.table_name} already exists")
                
                # Check disk space (simplified check)
                cursor.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]
                cursor.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]
                
                current_size = page_count * page_size
                if current_size > 100 * 1024 * 1024:  # 100MB
                    concerns.append("Large database detected - ensure sufficient disk space")
                
                # Check SQLite version compatibility
                cursor.execute("SELECT sqlite_version()")
                sqlite_version = cursor.fetchone()[0]
                major_version = int(sqlite_version.split('.')[0])
                if major_version < 3:
                    concerns.append(f"SQLite version {sqlite_version} may not support all required features")
        
        except Exception as e:
            concerns.append(f"Failed to validate transformation plan: {e}")
            return False, concerns
        
        # Determine if transformation is safe
        blocking_concerns = [c for c in concerns if any(keyword in c.lower() for keyword in ['failed', 'not found']) and 'already exists' not in c.lower()]
        is_safe = len(blocking_concerns) == 0
        
        return is_safe, concerns
    
    def _extract_index_name(self, index_sql: str) -> str:
        """Extract index name from CREATE INDEX SQL"""
        match = re.search(r'CREATE INDEX (?:IF NOT EXISTS )?(\w+)', index_sql, re.IGNORECASE)
        return match.group(1) if match else "unknown_index"


class SchemaTransformationManager:
    """High-level manager for schema transformations"""
    
    def __init__(self, connection_manager: SQLiteConnectionManager):
        self.connection_manager = connection_manager
        self.transformer = SQLiteSchemaTransformer(connection_manager)
        self.version_manager = VersionManager(connection_manager)
        self.logger = logging.getLogger(__name__)
    
    def execute_migration(self, target_version: DatabaseVersion = DatabaseVersion.V2_0_0) -> Tuple[bool, str]:
        """
        Execute complete migration to target version
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Detect current version
            current_version = self.version_manager.get_current_version_info()
            self.logger.info(f"Current database version: {current_version.version.value}")
            
            # Check if migration is needed
            if current_version.version == target_version and current_version.schema_valid:
                return True, "Database is already at target version and schema is valid"
            
            # Create transformation plan
            plan = self.transformer.create_transformation_plan(current_version, target_version)
            self.logger.info(f"Created transformation plan with {len(plan.steps)} steps")
            
            # Validate transformation safety
            is_safe, concerns = self.transformer.validate_transformation(plan)
            if not is_safe:
                return False, f"Migration validation failed: {concerns}"
            
            if concerns:
                self.logger.warning(f"Migration concerns detected: {concerns}")
            
            # Execute transformation
            success = self.transformer.execute_transformation_plan(plan)
            
            if success:
                # Update migration tracking if we have it
                if target_version == DatabaseVersion.V2_0_0:
                    self._record_migration_completion(plan)
                
                return True, f"Successfully migrated to {target_version.value}"
            else:
                return False, "Schema transformation failed"
                
        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            return False, f"Migration error: {e}"
    
    def _record_migration_completion(self, plan: TransformationPlan) -> None:
        """Record migration completion in schema_migrations table"""
        try:
            version_string = f"{datetime.now().strftime('%Y.%m.%d')}.001"
            
            with self.connection_manager.connection() as conn:
                cursor = conn.cursor()
                
                # Check if schema_migrations table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'")
                if cursor.fetchone():
                    cursor.execute("""
                        INSERT OR REPLACE INTO schema_migrations 
                        (version, name, checksum, status, executed_at, execution_time_ms)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        version_string,
                        f"schema_transformation_{plan.source_version.value}_to_{plan.target_version.value}",
                        "schema_transform_001",
                        "completed",
                        datetime.now(timezone.utc).isoformat(),
                        1000  # Placeholder execution time
                    ))
                    conn.commit()
                    self.logger.info(f"Recorded migration completion: {version_string}")
                    
        except Exception as e:
            self.logger.warning(f"Failed to record migration completion: {e}") 