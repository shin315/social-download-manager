"""
Database Migration Framework for Social Download Manager v2.0

Provides version-controlled database migrations with support for 
up/down scripts, schema validation, and rollback capabilities.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
import logging
import sqlite3
import hashlib
import json
import re
import os

from .connection import SQLiteConnectionManager, ConnectionConfig


class MigrationStatus(Enum):
    """Migration execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class MigrationDirection(Enum):
    """Migration direction"""
    UP = "up"
    DOWN = "down"


@dataclass
class MigrationRecord:
    """Database record of executed migrations"""
    id: Optional[int] = None
    version: str = ""
    name: str = ""
    checksum: str = ""
    status: MigrationStatus = MigrationStatus.PENDING
    executed_at: Optional[datetime] = None
    execution_time_ms: Optional[int] = None
    rollback_sql: Optional[str] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'id': self.id,
            'version': self.version,
            'name': self.name,
            'checksum': self.checksum,
            'status': self.status.value,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'execution_time_ms': self.execution_time_ms,
            'rollback_sql': self.rollback_sql,
            'error_message': self.error_message
        }
    
    @classmethod
    def from_row(cls, row: sqlite3.Row) -> 'MigrationRecord':
        """Create from database row"""
        return cls(
            id=row['id'],
            version=row['version'],
            name=row['name'],
            checksum=row['checksum'],
            status=MigrationStatus(row['status']),
            executed_at=datetime.fromisoformat(row['executed_at']) if row['executed_at'] else None,
            execution_time_ms=row['execution_time_ms'],
            rollback_sql=row['rollback_sql'],
            error_message=row['error_message']
        )


@dataclass
class Migration:
    """Migration definition with up/down scripts"""
    version: str
    name: str
    description: str
    up_sql: str
    down_sql: str = ""
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    def get_checksum(self) -> str:
        """Calculate checksum of migration content"""
        content = f"{self.version}{self.name}{self.up_sql}{self.down_sql}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def validate(self) -> List[str]:
        """Validate migration definition"""
        errors = []
        
        if not self.version:
            errors.append("Migration version is required")
        elif not re.match(r'^\d{4}\.\d{2}\.\d{2}\.\d{3}$', self.version):
            errors.append("Migration version must follow format YYYY.MM.DD.NNN")
        
        if not self.name:
            errors.append("Migration name is required")
        elif not re.match(r'^[a-zA-Z0-9_]+$', self.name):
            errors.append("Migration name must contain only alphanumeric characters and underscores")
        
        if not self.up_sql:
            errors.append("Migration up_sql is required")
        
        return errors


class MigrationError(Exception):
    """Base exception for migration errors"""
    pass


class MigrationValidationError(MigrationError):
    """Exception for migration validation errors"""
    pass


class MigrationExecutionError(MigrationError):
    """Exception for migration execution errors"""
    pass


class IMigrationEngine(ABC):
    """Interface for migration engines"""
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize migration system"""
        pass
    
    @abstractmethod
    def get_pending_migrations(self) -> List[Migration]:
        """Get list of pending migrations"""
        pass
    
    @abstractmethod
    def execute_migration(self, migration: Migration, direction: MigrationDirection = MigrationDirection.UP) -> bool:
        """Execute a single migration"""
        pass
    
    @abstractmethod
    def migrate_to_version(self, target_version: str) -> bool:
        """Migrate to specific version"""
        pass
    
    @abstractmethod
    def rollback_migration(self, version: str) -> bool:
        """Rollback specific migration"""
        pass
    
    @abstractmethod
    def validate_schema(self) -> bool:
        """Validate current database schema"""
        pass


class SQLiteMigrationEngine(IMigrationEngine):
    """SQLite-specific migration engine implementation"""
    
    def __init__(self, connection_manager: SQLiteConnectionManager, migration_dir: str = "data/database/migration_scripts"):
        self.connection_manager = connection_manager
        self.migration_dir = Path(migration_dir)
        self.logger = logging.getLogger(__name__)
        self._migrations_cache: Optional[List[Migration]] = None
        
        # Ensure migration directory exists
        self.migration_dir.mkdir(parents=True, exist_ok=True)
    
    def initialize(self) -> bool:
        """Initialize migration system by creating migration tracking table"""
        try:
            with self.connection_manager.connection() as conn:
                cursor = conn.cursor()
                
                # Create schema_migrations table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
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
                """)
                
                # Create indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_migrations_version ON schema_migrations(version)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_migrations_status ON schema_migrations(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_migrations_executed_at ON schema_migrations(executed_at)")
                
                conn.commit()
                
                self.logger.info("Migration system initialized successfully")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to initialize migration system: {e}")
            return False
    
    def load_migrations(self) -> List[Migration]:
        """Load all migration files from migration directory"""
        if self._migrations_cache is not None:
            return self._migrations_cache
        
        migrations = []
        
        # Scan migration directory for .sql files
        for migration_file in sorted(self.migration_dir.glob("*.sql")):
            try:
                migration = self._parse_migration_file(migration_file)
                if migration:
                    migrations.append(migration)
            except Exception as e:
                self.logger.error(f"Failed to parse migration file {migration_file}: {e}")
        
        # Sort by version
        migrations.sort(key=lambda m: m.version)
        
        self._migrations_cache = migrations
        return migrations
    
    def _parse_migration_file(self, file_path: Path) -> Optional[Migration]:
        """Parse migration file and extract metadata"""
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Extract metadata from comments
            version_match = re.search(r'-- version:\s*([^\r\n]*)', content, re.IGNORECASE)
            name_match = re.search(r'-- name:\s*([^\r\n]*)', content, re.IGNORECASE)
            description_match = re.search(r'-- description:\s*([^\r\n]*)', content, re.IGNORECASE)
            dependencies_match = re.search(r'-- dependencies:\s*([^\r\n]*)', content, re.IGNORECASE)
            tags_match = re.search(r'-- tags:\s*([^\r\n]*)', content, re.IGNORECASE)
            
            # Split UP and DOWN sections
            up_down_split = re.split(r'-- DOWN\b', content, flags=re.IGNORECASE)
            up_sql = up_down_split[0]
            down_sql = up_down_split[1] if len(up_down_split) > 1 else ""
            
            # Clean up SQL (remove metadata comments)
            up_sql = re.sub(r'-- (version|name|description|dependencies|tags):.+\n', '', up_sql, flags=re.IGNORECASE)
            up_sql = up_sql.strip()
            down_sql = down_sql.strip()
            
            # Extract values
            version = version_match.group(1).strip() if version_match else ""
            name = name_match.group(1).strip() if name_match else file_path.stem
            description = description_match.group(1).strip() if description_match else ""
            
            dependencies = []
            if dependencies_match:
                deps_str = dependencies_match.group(1).strip()
                # Filter out false positives like "-- tags:" that may be captured
                if deps_str and not deps_str.startswith('--'):
                    dependencies = [dep.strip() for dep in deps_str.split(',') if dep.strip()]
            
            tags = []
            if tags_match:
                tags_str = tags_match.group(1).strip()
                # Filter out false positives  
                if tags_str and not tags_str.startswith('--'):
                    tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
            
            migration = Migration(
                version=version,
                name=name,
                description=description,
                up_sql=up_sql,
                down_sql=down_sql,
                dependencies=dependencies,
                tags=tags
            )
            
            # Validate migration
            validation_errors = migration.validate()
            if validation_errors:
                self.logger.error(f"Migration validation failed for {file_path}: {validation_errors}")
                return None
            
            return migration
            
        except Exception as e:
            self.logger.error(f"Failed to parse migration file {file_path}: {e}")
            return None
    
    def get_executed_migrations(self) -> List[MigrationRecord]:
        """Get list of executed migrations from database"""
        try:
            with self.connection_manager.connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM schema_migrations 
                    ORDER BY version ASC
                """)
                
                return [MigrationRecord.from_row(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Failed to get executed migrations: {e}")
            return []
    
    def get_pending_migrations(self) -> List[Migration]:
        """Get list of pending migrations"""
        # Clear cache to get fresh data
        self._migrations_cache = None
        all_migrations = self.load_migrations()
        executed_migrations = self.get_executed_migrations()
        executed_versions = {m.version for m in executed_migrations if m.status == MigrationStatus.COMPLETED}
        
        pending = [m for m in all_migrations if m.version not in executed_versions]
        return pending
    
    def execute_migration(self, migration: Migration, direction: MigrationDirection = MigrationDirection.UP) -> bool:
        """Execute a single migration"""
        start_time = datetime.now()
        
        try:
            # Check dependencies for UP migrations
            if direction == MigrationDirection.UP:
                if not self._check_dependencies(migration):
                    raise MigrationExecutionError(f"Migration dependencies not satisfied: {migration.dependencies}")
            
            # Record migration start
            self._record_migration_start(migration)
            
            # Execute SQL
            sql_to_execute = migration.up_sql if direction == MigrationDirection.UP else migration.down_sql
            
            if not sql_to_execute:
                raise MigrationExecutionError(f"No {direction.value} SQL provided for migration {migration.version}")
            
            with self.connection_manager.transaction() as conn:
                # Split and execute SQL statements
                statements = [stmt.strip() for stmt in sql_to_execute.split(';') if stmt.strip()]
                
                for statement in statements:
                    # Remove inline comments from statement first
                    lines = statement.split('\n')
                    cleaned_lines = []
                    for line in lines:
                        # Remove comments but preserve the SQL
                        if '--' in line:
                            # Find comment start, but not if it's within quotes
                            in_quotes = False
                            quote_char = None
                            comment_pos = -1
                            
                            for i, char in enumerate(line):
                                if char in ('"', "'") and (i == 0 or line[i-1] != '\\'):
                                    if not in_quotes:
                                        in_quotes = True
                                        quote_char = char
                                    elif char == quote_char:
                                        in_quotes = False
                                        quote_char = None
                                elif char == '-' and not in_quotes and i < len(line) - 1 and line[i+1] == '-':
                                    comment_pos = i
                                    break
                            
                            if comment_pos >= 0:
                                line = line[:comment_pos].rstrip()
                        
                        if line.strip():
                            cleaned_lines.append(line)
                    
                    cleaned_statement = '\n'.join(cleaned_lines).strip()
                    
                    # Execute only non-empty statements
                    if cleaned_statement:
                        conn.execute(cleaned_statement)
                
                # Record successful execution
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                self._record_migration_completion(migration, execution_time, direction)
                
                self.logger.info(f"Successfully executed migration {migration.version} ({direction.value})")
                return True
                
        except Exception as e:
            # Record failure
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            self._record_migration_failure(migration, str(e), execution_time)
            
            self.logger.error(f"Failed to execute migration {migration.version}: {e}")
            raise MigrationExecutionError(f"Migration {migration.version} failed: {e}")
    
    def _check_dependencies(self, migration: Migration) -> bool:
        """Check if migration dependencies are satisfied"""
        if not migration.dependencies:
            return True
        
        executed_migrations = self.get_executed_migrations()
        executed_versions = {m.version for m in executed_migrations if m.status == MigrationStatus.COMPLETED}
        
        for dependency in migration.dependencies:
            if dependency not in executed_versions:
                return False
        
        return True
    
    def _record_migration_start(self, migration: Migration) -> None:
        """Record migration execution start"""
        try:
            with self.connection_manager.connection() as conn:
                cursor = conn.cursor()
                
                # Check if migration record exists
                cursor.execute("SELECT id FROM schema_migrations WHERE version = ?", (migration.version,))
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing record
                    cursor.execute("""
                        UPDATE schema_migrations 
                        SET status = ?, executed_at = ?, error_message = NULL
                        WHERE version = ?
                    """, (MigrationStatus.RUNNING.value, datetime.now(timezone.utc).isoformat(), migration.version))
                else:
                    # Insert new record
                    cursor.execute("""
                        INSERT INTO schema_migrations (version, name, checksum, status, executed_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        migration.version,
                        migration.name,
                        migration.get_checksum(),
                        MigrationStatus.RUNNING.value,
                        datetime.now(timezone.utc).isoformat()
                    ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to record migration start: {e}")
    
    def _record_migration_completion(self, migration: Migration, execution_time: float, direction: MigrationDirection) -> None:
        """Record successful migration completion"""
        try:
            with self.connection_manager.connection() as conn:
                cursor = conn.cursor()
                
                status = MigrationStatus.COMPLETED if direction == MigrationDirection.UP else MigrationStatus.ROLLED_BACK
                rollback_sql = migration.down_sql if direction == MigrationDirection.UP else None
                
                cursor.execute("""
                    UPDATE schema_migrations 
                    SET status = ?, execution_time_ms = ?, rollback_sql = ?, error_message = NULL
                    WHERE version = ?
                """, (status.value, int(execution_time), rollback_sql, migration.version))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to record migration completion: {e}")
    
    def _record_migration_failure(self, migration: Migration, error_message: str, execution_time: float) -> None:
        """Record migration failure"""
        try:
            with self.connection_manager.connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE schema_migrations 
                    SET status = ?, execution_time_ms = ?, error_message = ?
                    WHERE version = ?
                """, (MigrationStatus.FAILED.value, int(execution_time), error_message, migration.version))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to record migration failure: {e}")
    
    def migrate_to_version(self, target_version: str) -> bool:
        """Migrate to specific version"""
        try:
            pending_migrations = self.get_pending_migrations()
            
            # Filter migrations up to target version
            migrations_to_run = [
                m for m in pending_migrations 
                if m.version <= target_version
            ]
            
            if not migrations_to_run:
                self.logger.info(f"No migrations to run to reach version {target_version}")
                return True
            
            self.logger.info(f"Running {len(migrations_to_run)} migrations to reach version {target_version}")
            
            for migration in migrations_to_run:
                if not self.execute_migration(migration, MigrationDirection.UP):
                    return False
            
            self.logger.info(f"Successfully migrated to version {target_version}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to migrate to version {target_version}: {e}")
            return False
    
    def rollback_migration(self, version: str) -> bool:
        """Rollback specific migration"""
        try:
            # Find the migration
            all_migrations = self.load_migrations()
            migration = next((m for m in all_migrations if m.version == version), None)
            
            if not migration:
                raise MigrationError(f"Migration {version} not found")
            
            # Check if migration is executed
            executed_migrations = self.get_executed_migrations()
            executed_migration = next((m for m in executed_migrations if m.version == version), None)
            
            if not executed_migration or executed_migration.status != MigrationStatus.COMPLETED:
                raise MigrationError(f"Migration {version} is not in completed state")
            
            # Execute rollback
            return self.execute_migration(migration, MigrationDirection.DOWN)
            
        except Exception as e:
            self.logger.error(f"Failed to rollback migration {version}: {e}")
            return False
    
    def validate_schema(self) -> bool:
        """Validate current database schema"""
        try:
            with self.connection_manager.connection() as conn:
                cursor = conn.cursor()
                
                # Check if all expected tables exist
                expected_tables = ['schema_migrations', 'content', 'downloads', 'download_sessions', 'download_errors']
                
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                existing_tables = {row[0] for row in cursor.fetchall()}
                
                missing_tables = set(expected_tables) - existing_tables
                if missing_tables:
                    self.logger.error(f"Missing expected tables: {missing_tables}")
                    return False
                
                # Validate migration consistency
                executed_migrations = self.get_executed_migrations()
                all_migrations = self.load_migrations()
                
                for executed in executed_migrations:
                    if executed.status == MigrationStatus.COMPLETED:
                        # Find corresponding migration file
                        file_migration = next((m for m in all_migrations if m.version == executed.version), None)
                        if file_migration:
                            # Check checksum consistency
                            if file_migration.get_checksum() != executed.checksum:
                                self.logger.error(f"Checksum mismatch for migration {executed.version}")
                                return False
                        else:
                            self.logger.warning(f"Migration file not found for executed migration {executed.version}")
                
                self.logger.info("Schema validation passed")
                return True
                
        except Exception as e:
            self.logger.error(f"Schema validation failed: {e}")
            return False
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get comprehensive migration status"""
        try:
            all_migrations = self.load_migrations()
            executed_migrations = self.get_executed_migrations()
            pending_migrations = self.get_pending_migrations()
            
            executed_count = len([m for m in executed_migrations if m.status == MigrationStatus.COMPLETED])
            failed_count = len([m for m in executed_migrations if m.status == MigrationStatus.FAILED])
            
            latest_executed = None
            if executed_migrations:
                completed_migrations = [m for m in executed_migrations if m.status == MigrationStatus.COMPLETED]
                if completed_migrations:
                    latest_executed = max(completed_migrations, key=lambda m: m.version)
            
            return {
                'total_migrations': len(all_migrations),
                'executed_count': executed_count,
                'pending_count': len(pending_migrations),
                'failed_count': failed_count,
                'latest_executed_version': latest_executed.version if latest_executed else None,
                'latest_executed_at': latest_executed.executed_at if latest_executed else None,
                'pending_versions': [m.version for m in pending_migrations],
                'schema_valid': self.validate_schema()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get migration status: {e}")
            return {
                'error': str(e),
                'schema_valid': False
            }


def create_migration_engine(connection_manager: SQLiteConnectionManager) -> IMigrationEngine:
    """Factory function to create migration engine"""
    return SQLiteMigrationEngine(connection_manager) 