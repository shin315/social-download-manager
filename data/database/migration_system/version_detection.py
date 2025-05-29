"""
Database Version Detection System for Social Download Manager

Provides version detection capabilities to identify current database schema
version and determine required migration paths.
"""

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import logging
import sqlite3
import re
from datetime import datetime, timezone

from data.database.connection import SQLiteConnectionManager
from data.database.exceptions import DatabaseError, VersionMismatchError


class DatabaseVersion(Enum):
    """Supported database versions"""
    EMPTY = "empty"                    # Fresh install, no tables
    V1_2_1 = "v1.2.1"                 # Original schema with downloads table
    V2_0_0 = "v2.0.0"                 # New normalized schema
    UNKNOWN = "unknown"                # Unrecognized schema
    CORRUPTED = "corrupted"            # Database corruption detected


@dataclass
class VersionInfo:
    """Information about detected database version"""
    version: DatabaseVersion
    version_string: Optional[str] = None       # Actual version string (e.g., "2024.12.28.001")
    schema_valid: bool = True
    tables_found: List[str] = None
    migration_records: List[str] = None
    last_migration: Optional[str] = None
    requires_migration: bool = False
    migration_path: Optional[str] = None       # Description of required migration
    validation_errors: List[str] = None
    detected_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.tables_found is None:
            self.tables_found = []
        if self.migration_records is None:
            self.migration_records = []
        if self.validation_errors is None:
            self.validation_errors = []
        if self.detected_at is None:
            self.detected_at = datetime.now(timezone.utc)


class VersionDetector:
    """Database version detection and validation"""
    
    # Expected table structures for different versions
    V1_2_1_SCHEMA = {
        'downloads': [
            'id', 'url', 'title', 'filepath', 'quality', 'format',
            'duration', 'filesize', 'status', 'download_date', 'metadata'
        ]
    }
    
    V2_0_SCHEMA = {
        'schema_migrations': ['id', 'version', 'name', 'checksum', 'status', 'executed_at', 'execution_time_ms', 'rollback_sql', 'error_message', 'created_at'],
        'content': ['id', 'platform_id', 'platform_content_id', 'original_url', 'title', 'description', 'author_name', 'author_url', 'thumbnail_url', 'duration_seconds', 'view_count', 'like_count', 'content_type', 'published_at', 'metadata_json', 'status', 'created_at', 'updated_at'],
        'downloads': ['id', 'content_id', 'file_path', 'file_name', 'file_size_bytes', 'format', 'quality', 'status', 'download_started_at', 'download_completed_at', 'download_progress', 'error_message', 'retry_count', 'metadata_json', 'created_at', 'updated_at'],
        'download_sessions': ['id', 'session_name', 'description', 'status', 'total_downloads', 'successful_downloads', 'failed_downloads', 'total_size_bytes', 'started_at', 'completed_at', 'metadata_json', 'created_at', 'updated_at'],
        'download_errors': ['id', 'download_id', 'error_type', 'error_message', 'error_code', 'stack_trace', 'context_data', 'retry_attempt', 'occurred_at', 'resolved', 'resolution_notes', 'created_at']
    }
    
    def __init__(self, connection_manager: SQLiteConnectionManager):
        self.connection_manager = connection_manager
        self.logger = logging.getLogger(__name__)
    
    def detect_version(self) -> VersionInfo:
        """
        Detect current database version and schema state
        
        Returns:
            VersionInfo: Comprehensive version information
        """
        try:
            with self.connection_manager.connection() as conn:
                return self._analyze_database(conn)
                
        except Exception as e:
            self.logger.error(f"Failed to detect database version: {e}")
            return VersionInfo(
                version=DatabaseVersion.CORRUPTED,
                schema_valid=False,
                validation_errors=[f"Database access failed: {e}"]
            )
    
    def _analyze_database(self, conn: sqlite3.Connection) -> VersionInfo:
        """Analyze database structure to determine version"""
        cursor = conn.cursor()
        
        try:
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]
            
            # Check if database is empty
            if not tables:
                return VersionInfo(
                    version=DatabaseVersion.EMPTY,
                    tables_found=tables,
                    requires_migration=True,
                    migration_path="Fresh install - requires initial v2.0 schema creation"
                )
            
            # Check for schema_migrations table (indicates v2.0+)
            if 'schema_migrations' in tables:
                return self._analyze_v2_database(conn, cursor, tables)
            
            # Check for v1.2.1 schema
            if 'downloads' in tables:
                return self._analyze_v1_2_1_database(conn, cursor, tables)
            
            # Unknown schema
            return VersionInfo(
                version=DatabaseVersion.UNKNOWN,
                tables_found=tables,
                schema_valid=False,
                validation_errors=["Unrecognized database schema"],
                migration_path="Unknown schema - manual migration may be required"
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing database: {e}")
            return VersionInfo(
                version=DatabaseVersion.CORRUPTED,
                schema_valid=False,
                validation_errors=[f"Database analysis failed: {e}"]
            )
    
    def _analyze_v2_database(self, conn: sqlite3.Connection, cursor: sqlite3.Cursor, tables: List[str]) -> VersionInfo:
        """Analyze v2.0+ database with migration tracking"""
        try:
            # Get migration records
            cursor.execute("""
                SELECT version, status, executed_at 
                FROM schema_migrations 
                ORDER BY version DESC
            """)
            migration_rows = cursor.fetchall()
            
            migration_records = []
            completed_migrations = []
            
            for version, status, executed_at in migration_rows:
                migration_records.append(f"{version} ({status})")
                if status == 'completed':
                    completed_migrations.append(version)
            
            # Get latest completed migration
            latest_migration = completed_migrations[0] if completed_migrations else None
            
            # Validate schema structure
            validation_errors = self._validate_v2_schema(cursor, tables)
            
            # Determine version string
            version_string = latest_migration or "v2.0.0"
            
            return VersionInfo(
                version=DatabaseVersion.V2_0_0,
                version_string=version_string,
                tables_found=tables,
                migration_records=migration_records,
                last_migration=latest_migration,
                schema_valid=len(validation_errors) == 0,
                validation_errors=validation_errors,
                requires_migration=len(validation_errors) > 0,
                migration_path="v2.0 schema - check for pending migrations" if validation_errors else None
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing v2 database: {e}")
            return VersionInfo(
                version=DatabaseVersion.CORRUPTED,
                schema_valid=False,
                validation_errors=[f"v2 database analysis failed: {e}"]
            )
    
    def _analyze_v1_2_1_database(self, conn: sqlite3.Connection, cursor: sqlite3.Cursor, tables: List[str]) -> VersionInfo:
        """Analyze v1.2.1 database schema"""
        try:
            # Validate downloads table structure
            cursor.execute("PRAGMA table_info(downloads)")
            columns = [row[1] for row in cursor.fetchall()]  # row[1] is column name
            
            expected_columns = self.V1_2_1_SCHEMA['downloads']
            validation_errors = []
            
            # Check for required columns
            missing_columns = set(expected_columns) - set(columns)
            if missing_columns:
                validation_errors.append(f"Missing columns in downloads table: {missing_columns}")
            
            # Check for unexpected columns (might indicate partial migration)
            extra_columns = set(columns) - set(expected_columns)
            if extra_columns:
                validation_errors.append(f"Unexpected columns in downloads table: {extra_columns}")
            
            # Check for other v1.2.1 anomalies
            for table in tables:
                if table not in ['downloads']:
                    validation_errors.append(f"Unexpected table for v1.2.1: {table}")
            
            return VersionInfo(
                version=DatabaseVersion.V1_2_1,
                version_string="v1.2.1",
                tables_found=tables,
                schema_valid=len(validation_errors) == 0,
                validation_errors=validation_errors,
                requires_migration=True,
                migration_path="v1.2.1 → v2.0.0 (requires data migration and schema transformation)"
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing v1.2.1 database: {e}")
            return VersionInfo(
                version=DatabaseVersion.CORRUPTED,
                schema_valid=False,
                validation_errors=[f"v1.2.1 database analysis failed: {e}"]
            )
    
    def _validate_v2_schema(self, cursor: sqlite3.Cursor, tables: List[str]) -> List[str]:
        """Validate v2.0 schema structure"""
        validation_errors = []
        
        # Check for required tables
        expected_tables = set(self.V2_0_SCHEMA.keys())
        actual_tables = set(tables)
        
        missing_tables = expected_tables - actual_tables
        if missing_tables:
            validation_errors.append(f"Missing v2.0 tables: {missing_tables}")
        
        # Validate table structures
        for table_name, expected_columns in self.V2_0_SCHEMA.items():
            if table_name in tables:
                try:
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    actual_columns = [row[1] for row in cursor.fetchall()]
                    
                    missing_columns = set(expected_columns) - set(actual_columns)
                    if missing_columns:
                        validation_errors.append(f"Missing columns in {table_name}: {missing_columns}")
                        
                except Exception as e:
                    validation_errors.append(f"Failed to validate table {table_name}: {e}")
        
        return validation_errors
    
    def get_migration_requirements(self, version_info: VersionInfo) -> Dict[str, Any]:
        """
        Determine what migrations are required based on version info
        
        Args:
            version_info: Current version information
            
        Returns:
            Dict containing migration requirements
        """
        requirements = {
            'requires_migration': version_info.requires_migration,
            'source_version': version_info.version.value,
            'target_version': 'v2.0.0',
            'migration_type': None,
            'estimated_duration': 'unknown',
            'data_backup_required': False,
            'destructive_changes': False,
            'steps': []
        }
        
        if version_info.version == DatabaseVersion.EMPTY:
            requirements.update({
                'migration_type': 'fresh_install',
                'estimated_duration': 'seconds',
                'steps': [
                    'Create v2.0 schema',
                    'Initialize migration tracking',
                    'Setup default configuration'
                ]
            })
            
        elif version_info.version == DatabaseVersion.V1_2_1:
            requirements.update({
                'migration_type': 'schema_upgrade',
                'estimated_duration': 'minutes',
                'data_backup_required': True,
                'destructive_changes': True,
                'steps': [
                    'Backup existing v1.2.1 data',
                    'Create v2.0 schema structure',
                    'Transform and migrate data',
                    'Validate data integrity',
                    'Initialize migration tracking'
                ]
            })
            
        elif version_info.version == DatabaseVersion.V2_0_0:
            if version_info.schema_valid:
                requirements['requires_migration'] = False
            else:
                requirements.update({
                    'migration_type': 'schema_repair',
                    'estimated_duration': 'minutes',
                    'steps': [
                        'Validate current schema',
                        'Repair missing components',
                        'Update migration tracking'
                    ]
                })
        
        return requirements
    
    def validate_migration_safety(self, version_info: VersionInfo) -> Tuple[bool, List[str]]:
        """
        Validate that migration can be performed safely
        
        Args:
            version_info: Current version information
            
        Returns:
            Tuple of (is_safe, list_of_concerns)
        """
        concerns = []
        
        # Check for corruption
        if version_info.version == DatabaseVersion.CORRUPTED:
            concerns.append("Database appears to be corrupted")
            return False, concerns
        
        # Check for unknown schema
        if version_info.version == DatabaseVersion.UNKNOWN:
            concerns.append("Database schema is not recognized")
            concerns.append("Manual inspection may be required before migration")
        
        # Check validation errors
        if version_info.validation_errors:
            concerns.extend([f"Schema validation error: {error}" for error in version_info.validation_errors])
        
        # Check for partial migrations
        if version_info.version == DatabaseVersion.V2_0_0 and not version_info.schema_valid:
            concerns.append("Incomplete v2.0 schema detected - may indicate failed previous migration")
        
        # Safety assessment
        is_safe = len(concerns) == 0 or (
            version_info.version in [DatabaseVersion.EMPTY, DatabaseVersion.V1_2_1] and 
            not any("corrupted" in concern.lower() for concern in concerns)
        )
        
        return is_safe, concerns


class VersionManager:
    """High-level version management operations"""
    
    def __init__(self, connection_manager: SQLiteConnectionManager):
        self.connection_manager = connection_manager
        self.detector = VersionDetector(connection_manager)
        self.logger = logging.getLogger(__name__)
    
    def get_current_version_info(self) -> VersionInfo:
        """Get current database version information"""
        return self.detector.detect_version()
    
    def check_migration_requirements(self) -> Dict[str, Any]:
        """Check what migrations are required"""
        version_info = self.get_current_version_info()
        requirements = self.detector.get_migration_requirements(version_info)
        is_safe, concerns = self.detector.validate_migration_safety(version_info)
        
        return {
            'version_info': version_info,
            'requirements': requirements,
            'migration_safe': is_safe,
            'safety_concerns': concerns
        }
    
    def create_migration_tracking(self) -> bool:
        """Create migration tracking table if it doesn't exist"""
        try:
            with self.connection_manager.connection() as conn:
                cursor = conn.cursor()
                
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
                
                self.logger.info("Migration tracking table created successfully")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to create migration tracking: {e}")
            return False 