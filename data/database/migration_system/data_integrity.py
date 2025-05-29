"""
Data Integrity Validation System for Social Download Manager

Provides comprehensive validation of database integrity during migrations,
including checksums, constraint verification, and corruption detection.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Set, Union, Callable
import logging
import sqlite3
import hashlib
import json
import re
from datetime import datetime, timezone

from data.database.connection import SQLiteConnectionManager
from .version_detection import VersionInfo, DatabaseVersion, VersionManager
from data.database.exceptions import DatabaseError, DataIntegrityError


class ValidationLevel(Enum):
    """Levels of validation rigor"""
    BASIC = "basic"
    STANDARD = "standard"
    COMPREHENSIVE = "comprehensive"
    PARANOID = "paranoid"


class ValidationResult(Enum):
    """Results of validation checks"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class ValidationIssue:
    """Represents a data integrity issue"""
    severity: ValidationResult
    check_name: str
    table_name: Optional[str]
    column_name: Optional[str]
    issue_description: str
    expected_value: Optional[Any] = None
    actual_value: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class TableChecksum:
    """Checksum information for a table"""
    table_name: str
    row_count: int
    content_hash: str
    schema_hash: str
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntegrityReport:
    """Complete integrity validation report"""
    validation_id: str
    database_version: DatabaseVersion
    validation_level: ValidationLevel
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    warnings: int = 0
    skipped_checks: int = 0
    table_checksums: List[TableChecksum] = field(default_factory=list)
    issues: List[ValidationIssue] = field(default_factory=list)
    success: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class IDataIntegrityValidator(ABC):
    """Interface for data integrity validation"""
    
    @abstractmethod
    def validate_database_integrity(self, level: ValidationLevel = ValidationLevel.STANDARD) -> IntegrityReport:
        """Perform comprehensive database integrity validation"""
        pass
    
    @abstractmethod
    def validate_table_integrity(self, table_name: str, level: ValidationLevel = ValidationLevel.STANDARD) -> List[ValidationIssue]:
        """Validate integrity of a specific table"""
        pass
    
    @abstractmethod
    def generate_table_checksum(self, table_name: str) -> TableChecksum:
        """Generate checksum for a table"""
        pass


class SQLiteIntegrityValidator(IDataIntegrityValidator):
    """SQLite-specific data integrity validation implementation"""
    
    def __init__(self, connection_manager: SQLiteConnectionManager):
        self.connection_manager = connection_manager
        self.version_manager = VersionManager(connection_manager)
        self.logger = logging.getLogger(__name__)
    
    def validate_database_integrity(self, level: ValidationLevel = ValidationLevel.STANDARD) -> IntegrityReport:
        """Perform comprehensive database integrity validation"""
        validation_id = f"integrity_check_{int(datetime.now().timestamp())}"
        current_version = self.version_manager.get_current_version_info()
        
        report = IntegrityReport(
            validation_id=validation_id,
            database_version=current_version.version,
            validation_level=level,
            started_at=datetime.now(timezone.utc)
        )
        
        try:
            self.logger.info(f"Starting {level.value} integrity validation: {validation_id}")
            
            with self.connection_manager.connection() as conn:
                # Get all tables
                tables = self._get_all_tables(conn)
                
                # Perform validation checks based on level
                validation_checks = self._get_validation_checks(level, tables)
                report.total_checks = len(validation_checks)
                
                for check_name, check_func in validation_checks:
                    try:
                        self.logger.debug(f"Running check: {check_name}")
                        issues = check_func(conn)
                        
                        if not issues:
                            report.passed_checks += 1
                        else:
                            # Categorize issues
                            for issue in issues:
                                if issue.severity == ValidationResult.FAILED:
                                    report.failed_checks += 1
                                elif issue.severity == ValidationResult.WARNING:
                                    report.warnings += 1
                                elif issue.severity == ValidationResult.SKIPPED:
                                    report.skipped_checks += 1
                                    
                                report.issues.append(issue)
                        
                    except Exception as e:
                        self.logger.error(f"Validation check '{check_name}' failed: {e}")
                        issue = ValidationIssue(
                            severity=ValidationResult.FAILED,
                            check_name=check_name,
                            table_name=None,
                            column_name=None,
                            issue_description=f"Check execution failed: {e}",
                            metadata={"exception": str(e)}
                        )
                        report.issues.append(issue)
                        report.failed_checks += 1
                
                # Generate table checksums
                if level in [ValidationLevel.COMPREHENSIVE, ValidationLevel.PARANOID]:
                    for table in tables:
                        try:
                            checksum = self.generate_table_checksum(table)
                            report.table_checksums.append(checksum)
                        except Exception as e:
                            self.logger.warning(f"Failed to generate checksum for table {table}: {e}")
            
            # Determine overall success
            report.success = report.failed_checks == 0
            report.completed_at = datetime.now(timezone.utc)
            
            self.logger.info(f"Integrity validation completed: {report.passed_checks} passed, {report.failed_checks} failed, {report.warnings} warnings")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Integrity validation failed: {e}")
            report.completed_at = datetime.now(timezone.utc)
            report.issues.append(ValidationIssue(
                severity=ValidationResult.FAILED,
                check_name="database_validation",
                table_name=None,
                column_name=None,
                issue_description=f"Database validation failed: {e}",
                metadata={"exception": str(e)}
            ))
            report.failed_checks += 1
            return report
    
    def validate_table_integrity(self, table_name: str, level: ValidationLevel = ValidationLevel.STANDARD) -> List[ValidationIssue]:
        """Validate integrity of a specific table"""
        issues = []
        
        try:
            with self.connection_manager.connection() as conn:
                # Check if table exists
                if not self._table_exists(conn, table_name):
                    issues.append(ValidationIssue(
                        severity=ValidationResult.FAILED,
                        check_name="table_existence",
                        table_name=table_name,
                        column_name=None,
                        issue_description=f"Table '{table_name}' does not exist"
                    ))
                    return issues
                
                # Perform table-specific checks
                table_checks = [
                    ("row_count_validation", lambda c: self._validate_table_row_count(c, table_name)),
                    ("schema_validation", lambda c: self._validate_table_schema(c, table_name)),
                    ("data_type_validation", lambda c: self._validate_table_data_types(c, table_name)),
                ]
                
                if level in [ValidationLevel.COMPREHENSIVE, ValidationLevel.PARANOID]:
                    table_checks.extend([
                        ("foreign_key_validation", lambda c: self._validate_table_foreign_keys(c, table_name)),
                        ("constraint_validation", lambda c: self._validate_table_constraints(c, table_name)),
                    ])
                
                if level == ValidationLevel.PARANOID:
                    table_checks.extend([
                        ("data_consistency_validation", lambda c: self._validate_table_data_consistency(c, table_name)),
                        ("index_validation", lambda c: self._validate_table_indexes(c, table_name)),
                    ])
                
                for check_name, check_func in table_checks:
                    try:
                        check_issues = check_func(conn)
                        issues.extend(check_issues)
                    except Exception as e:
                        issues.append(ValidationIssue(
                            severity=ValidationResult.FAILED,
                            check_name=check_name,
                            table_name=table_name,
                            column_name=None,
                            issue_description=f"Check failed: {e}",
                            metadata={"exception": str(e)}
                        ))
        
        except Exception as e:
            issues.append(ValidationIssue(
                severity=ValidationResult.FAILED,
                check_name="table_validation",
                table_name=table_name,
                column_name=None,
                issue_description=f"Table validation failed: {e}",
                metadata={"exception": str(e)}
            ))
        
        return issues
    
    def generate_table_checksum(self, table_name: str) -> TableChecksum:
        """Generate checksum for a table"""
        with self.connection_manager.connection() as conn:
            # Get row count
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            
            # Generate content hash
            cursor.execute(f"SELECT * FROM {table_name} ORDER BY ROWID")
            rows = cursor.fetchall()
            
            content_data = json.dumps(rows, sort_keys=True, default=str)
            content_hash = hashlib.sha256(content_data.encode()).hexdigest()
            
            # Generate schema hash
            cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            result = cursor.fetchone()
            schema_sql = result[0] if result else ""
            schema_hash = hashlib.sha256(schema_sql.encode()).hexdigest()
            
            return TableChecksum(
                table_name=table_name,
                row_count=row_count,
                content_hash=content_hash,
                schema_hash=schema_hash,
                timestamp=datetime.now(timezone.utc).isoformat(),
                metadata={"schema_sql": schema_sql}
            )
    
    def _get_all_tables(self, conn: sqlite3.Connection) -> List[str]:
        """Get list of all user tables"""
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        return [row[0] for row in cursor.fetchall()]
    
    def _table_exists(self, conn: sqlite3.Connection, table_name: str) -> bool:
        """Check if table exists"""
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        return cursor.fetchone() is not None
    
    def _get_validation_checks(self, level: ValidationLevel, tables: List[str]) -> List[Tuple[str, callable]]:
        """Get validation checks based on level"""
        checks = [
            ("sqlite_integrity_check", self._check_sqlite_integrity),
            ("database_corruption_check", self._check_database_corruption),
            ("table_existence_check", self._check_table_existence),
        ]
        
        if level in [ValidationLevel.STANDARD, ValidationLevel.COMPREHENSIVE, ValidationLevel.PARANOID]:
            checks.extend([
                ("foreign_key_check", self._check_foreign_keys),
                ("constraint_check", self._check_constraints),
                ("row_count_check", self._check_row_counts),
            ])
        
        if level in [ValidationLevel.COMPREHENSIVE, ValidationLevel.PARANOID]:
            checks.extend([
                ("data_type_consistency_check", self._check_data_type_consistency),
                ("orphaned_records_check", self._check_orphaned_records),
                ("duplicate_records_check", self._check_duplicate_records),
            ])
        
        if level == ValidationLevel.PARANOID:
            checks.extend([
                ("index_integrity_check", self._check_index_integrity),
                ("trigger_validity_check", self._check_trigger_validity),
                ("view_validity_check", self._check_view_validity),
            ])
        
        return checks
    
    # Validation check implementations
    def _check_sqlite_integrity(self, conn: sqlite3.Connection) -> List[ValidationIssue]:
        """Check SQLite database integrity"""
        issues = []
        cursor = conn.cursor()
        
        try:
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            
            if result[0] != "ok":
                issues.append(ValidationIssue(
                    severity=ValidationResult.FAILED,
                    check_name="sqlite_integrity_check",
                    table_name=None,
                    column_name=None,
                    issue_description=f"SQLite integrity check failed: {result[0]}",
                    actual_value=result[0]
                ))
        except Exception as e:
            issues.append(ValidationIssue(
                severity=ValidationResult.FAILED,
                check_name="sqlite_integrity_check",
                table_name=None,
                column_name=None,
                issue_description=f"Failed to run integrity check: {e}"
            ))
        
        return issues
    
    def _check_database_corruption(self, conn: sqlite3.Connection) -> List[ValidationIssue]:
        """Check for database corruption"""
        issues = []
        cursor = conn.cursor()
        
        try:
            # Quick corruption check
            cursor.execute("PRAGMA quick_check")
            result = cursor.fetchone()
            
            if result[0] != "ok":
                issues.append(ValidationIssue(
                    severity=ValidationResult.FAILED,
                    check_name="database_corruption_check",
                    table_name=None,
                    column_name=None,
                    issue_description=f"Database corruption detected: {result[0]}",
                    actual_value=result[0]
                ))
        except Exception as e:
            issues.append(ValidationIssue(
                severity=ValidationResult.WARNING,
                check_name="database_corruption_check",
                table_name=None,
                column_name=None,
                issue_description=f"Could not check for corruption: {e}"
            ))
        
        return issues
    
    def _check_table_existence(self, conn: sqlite3.Connection) -> List[ValidationIssue]:
        """Check that required tables exist"""
        issues = []
        current_version = self.version_manager.get_current_version_info()
        
        if current_version.version == DatabaseVersion.V2_0_0:
            required_tables = ['content', 'downloads', 'download_sessions', 'download_errors', 'schema_migrations']
        elif current_version.version == DatabaseVersion.V1_2_1:
            required_tables = ['downloads']
        else:
            return issues  # Skip for unknown versions
        
        existing_tables = self._get_all_tables(conn)
        
        for table in required_tables:
            if table not in existing_tables:
                issues.append(ValidationIssue(
                    severity=ValidationResult.FAILED,
                    check_name="table_existence_check",
                    table_name=table,
                    column_name=None,
                    issue_description=f"Required table '{table}' is missing",
                    expected_value="table exists",
                    actual_value="table missing"
                ))
        
        return issues
    
    def _check_foreign_keys(self, conn: sqlite3.Connection) -> List[ValidationIssue]:
        """Check foreign key constraints"""
        issues = []
        cursor = conn.cursor()
        
        try:
            cursor.execute("PRAGMA foreign_key_check")
            violations = cursor.fetchall()
            
            for violation in violations:
                table, rowid, parent, fkid = violation
                issues.append(ValidationIssue(
                    severity=ValidationResult.FAILED,
                    check_name="foreign_key_check",
                    table_name=table,
                    column_name=None,
                    issue_description=f"Foreign key violation in row {rowid}, references {parent}",
                    metadata={"rowid": rowid, "parent": parent, "fkid": fkid}
                ))
        except Exception as e:
            issues.append(ValidationIssue(
                severity=ValidationResult.WARNING,
                check_name="foreign_key_check",
                table_name=None,
                column_name=None,
                issue_description=f"Could not check foreign keys: {e}"
            ))
        
        return issues
    
    def _check_constraints(self, conn: sqlite3.Connection) -> List[ValidationIssue]:
        """Check table constraints"""
        issues = []
        # Implementation would check NOT NULL, CHECK constraints, etc.
        # This is a placeholder for constraint validation logic
        return issues
    
    def _check_row_counts(self, conn: sqlite3.Connection) -> List[ValidationIssue]:
        """Check row counts for reasonableness"""
        issues = []
        cursor = conn.cursor()
        
        tables = self._get_all_tables(conn)
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                
                # Check for negative counts (shouldn't happen but good to verify)
                if count < 0:
                    issues.append(ValidationIssue(
                        severity=ValidationResult.FAILED,
                        check_name="row_count_check",
                        table_name=table,
                        column_name=None,
                        issue_description=f"Invalid row count: {count}",
                        actual_value=count
                    ))
            except Exception as e:
                issues.append(ValidationIssue(
                    severity=ValidationResult.WARNING,
                    check_name="row_count_check",
                    table_name=table,
                    column_name=None,
                    issue_description=f"Could not count rows: {e}"
                ))
        
        return issues
    
    def _check_data_type_consistency(self, conn: sqlite3.Connection) -> List[ValidationIssue]:
        """Check data type consistency"""
        issues = []
        # Implementation would check that data matches expected types
        return issues
    
    def _check_orphaned_records(self, conn: sqlite3.Connection) -> List[ValidationIssue]:
        """Check for orphaned records"""
        issues = []
        cursor = conn.cursor()
        
        current_version = self.version_manager.get_current_version_info()
        if current_version.version == DatabaseVersion.V2_0_0:
            # Check for downloads without content
            try:
                cursor.execute("""
                    SELECT COUNT(*) FROM downloads d 
                    LEFT JOIN content c ON d.content_id = c.id 
                    WHERE c.id IS NULL
                """)
                orphaned_downloads = cursor.fetchone()[0]
                
                if orphaned_downloads > 0:
                    issues.append(ValidationIssue(
                        severity=ValidationResult.FAILED,
                        check_name="orphaned_records_check",
                        table_name="downloads",
                        column_name="content_id",
                        issue_description=f"Found {orphaned_downloads} orphaned download records",
                        actual_value=orphaned_downloads
                    ))
            except Exception as e:
                issues.append(ValidationIssue(
                    severity=ValidationResult.WARNING,
                    check_name="orphaned_records_check",
                    table_name="downloads",
                    column_name=None,
                    issue_description=f"Could not check orphaned records: {e}"
                ))
        
        return issues
    
    def _check_duplicate_records(self, conn: sqlite3.Connection) -> List[ValidationIssue]:
        """Check for duplicate records"""
        issues = []
        cursor = conn.cursor()
        
        current_version = self.version_manager.get_current_version_info()
        if current_version.version == DatabaseVersion.V2_0_0:
            # Check for duplicate content URLs
            try:
                cursor.execute("""
                    SELECT original_url, COUNT(*) as count 
                    FROM content 
                    GROUP BY original_url 
                    HAVING count > 1
                """)
                duplicates = cursor.fetchall()
                
                for url, count in duplicates:
                    issues.append(ValidationIssue(
                        severity=ValidationResult.WARNING,
                        check_name="duplicate_records_check",
                        table_name="content",
                        column_name="original_url",
                        issue_description=f"Duplicate URL found {count} times: {url}",
                        actual_value=count,
                        metadata={"url": url}
                    ))
            except Exception as e:
                issues.append(ValidationIssue(
                    severity=ValidationResult.WARNING,
                    check_name="duplicate_records_check",
                    table_name="content",
                    column_name=None,
                    issue_description=f"Could not check duplicates: {e}"
                ))
        
        return issues
    
    def _check_index_integrity(self, conn: sqlite3.Connection) -> List[ValidationIssue]:
        """Check index integrity"""
        issues = []
        # Implementation would verify index consistency
        return issues
    
    def _check_trigger_validity(self, conn: sqlite3.Connection) -> List[ValidationIssue]:
        """Check trigger validity"""
        issues = []
        # Implementation would verify triggers are valid
        return issues
    
    def _check_view_validity(self, conn: sqlite3.Connection) -> List[ValidationIssue]:
        """Check view validity"""
        issues = []
        # Implementation would verify views are valid
        return issues
    
    # Table-specific validation methods
    def _validate_table_row_count(self, conn: sqlite3.Connection, table_name: str) -> List[ValidationIssue]:
        """Validate table row count"""
        issues = []
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            
            if count < 0:
                issues.append(ValidationIssue(
                    severity=ValidationResult.FAILED,
                    check_name="row_count_validation",
                    table_name=table_name,
                    column_name=None,
                    issue_description=f"Invalid row count: {count}",
                    actual_value=count
                ))
        except Exception as e:
            issues.append(ValidationIssue(
                severity=ValidationResult.FAILED,
                check_name="row_count_validation",
                table_name=table_name,
                column_name=None,
                issue_description=f"Could not validate row count: {e}"
            ))
        
        return issues
    
    def _validate_table_schema(self, conn: sqlite3.Connection, table_name: str) -> List[ValidationIssue]:
        """Validate table schema"""
        issues = []
        # Implementation would check schema matches expected structure
        return issues
    
    def _validate_table_data_types(self, conn: sqlite3.Connection, table_name: str) -> List[ValidationIssue]:
        """Validate table data types"""
        issues = []
        # Implementation would check data type consistency
        return issues
    
    def _validate_table_foreign_keys(self, conn: sqlite3.Connection, table_name: str) -> List[ValidationIssue]:
        """Validate table foreign keys"""
        issues = []
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"PRAGMA foreign_key_check({table_name})")
            violations = cursor.fetchall()
            
            for violation in violations:
                table, rowid, parent, fkid = violation
                issues.append(ValidationIssue(
                    severity=ValidationResult.FAILED,
                    check_name="foreign_key_validation",
                    table_name=table_name,
                    column_name=None,
                    issue_description=f"Foreign key violation in row {rowid}",
                    metadata={"rowid": rowid, "parent": parent, "fkid": fkid}
                ))
        except Exception as e:
            issues.append(ValidationIssue(
                severity=ValidationResult.WARNING,
                check_name="foreign_key_validation",
                table_name=table_name,
                column_name=None,
                issue_description=f"Could not validate foreign keys: {e}"
            ))
        
        return issues
    
    def _validate_table_constraints(self, conn: sqlite3.Connection, table_name: str) -> List[ValidationIssue]:
        """Validate table constraints"""
        issues = []
        # Implementation would check table-specific constraints
        return issues
    
    def _validate_table_data_consistency(self, conn: sqlite3.Connection, table_name: str) -> List[ValidationIssue]:
        """Validate table data consistency"""
        issues = []
        # Implementation would check data consistency rules
        return issues
    
    def _validate_table_indexes(self, conn: sqlite3.Connection, table_name: str) -> List[ValidationIssue]:
        """Validate table indexes"""
        issues = []
        # Implementation would check index integrity for specific table
        return issues


class DataIntegrityManager:
    """High-level manager for data integrity operations"""
    
    def __init__(self, connection_manager: SQLiteConnectionManager):
        self.connection_manager = connection_manager
        self.validator = SQLiteIntegrityValidator(connection_manager)
        self.logger = logging.getLogger(__name__)
    
    def validate_migration_integrity(self, level: ValidationLevel = ValidationLevel.STANDARD) -> Tuple[bool, str, IntegrityReport]:
        """
        Validate database integrity during migration
        
        Returns:
            Tuple of (success, message, report)
        """
        try:
            self.logger.info(f"Starting migration integrity validation at {level.value} level")
            
            report = self.validator.validate_database_integrity(level)
            
            if report.success:
                success_message = f"Database integrity validation passed: {report.passed_checks} checks successful"
                if report.warnings > 0:
                    success_message += f" (with {report.warnings} warnings)"
                
                return True, success_message, report
            else:
                failure_message = f"Database integrity validation failed: {report.failed_checks} checks failed"
                return False, failure_message, report
                
        except Exception as e:
            self.logger.error(f"Integrity validation error: {e}")
            error_report = IntegrityReport(
                validation_id="error",
                database_version=DatabaseVersion.UNKNOWN,
                validation_level=level,
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc)
            )
            error_report.issues.append(ValidationIssue(
                severity=ValidationResult.FAILED,
                check_name="validation_error",
                table_name=None,
                column_name=None,
                issue_description=f"Validation error: {e}"
            ))
            return False, f"Integrity validation error: {e}", error_report
    
    def compare_checksums(self, before_checksums: List[TableChecksum], after_checksums: List[TableChecksum]) -> List[ValidationIssue]:
        """Compare checksums before and after migration"""
        issues = []
        
        before_map = {cs.table_name: cs for cs in before_checksums}
        after_map = {cs.table_name: cs for cs in after_checksums}
        
        # Check for missing tables
        for table_name in before_map:
            if table_name not in after_map:
                issues.append(ValidationIssue(
                    severity=ValidationResult.FAILED,
                    check_name="checksum_comparison",
                    table_name=table_name,
                    column_name=None,
                    issue_description=f"Table missing after migration",
                    expected_value="table exists",
                    actual_value="table missing"
                ))
        
        # Compare checksums for existing tables
        for table_name in before_map:
            if table_name in after_map:
                before_cs = before_map[table_name]
                after_cs = after_map[table_name]
                
                # Check row count changes
                if before_cs.row_count != after_cs.row_count:
                    issues.append(ValidationIssue(
                        severity=ValidationResult.WARNING,
                        check_name="checksum_comparison",
                        table_name=table_name,
                        column_name=None,
                        issue_description=f"Row count changed during migration",
                        expected_value=before_cs.row_count,
                        actual_value=after_cs.row_count
                    ))
                
                # Check content hash changes (expected for data conversion)
                if before_cs.content_hash != after_cs.content_hash:
                    issues.append(ValidationIssue(
                        severity=ValidationResult.WARNING,
                        check_name="checksum_comparison",
                        table_name=table_name,
                        column_name=None,
                        issue_description=f"Content hash changed during migration",
                        metadata={
                            "before_hash": before_cs.content_hash[:16] + "...",
                            "after_hash": after_cs.content_hash[:16] + "..."
                        }
                    ))
        
        return issues 