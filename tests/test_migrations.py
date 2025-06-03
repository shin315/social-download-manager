"""
Test suite for Database Migration Framework

Tests migration engine functionality, file parsing, 
execution, rollback, and validation capabilities.
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path
import shutil
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.database.connection import SQLiteConnectionManager, ConnectionConfig
from data.database.migrations import (
    SQLiteMigrationEngine, 
    Migration, 
    MigrationRecord,
    MigrationStatus,
    MigrationDirection,
    MigrationError,
    create_migration_engine
)


class TestMigration(unittest.TestCase):
    """Test Migration class functionality"""
    
    def test_migration_creation(self):
        """Test basic migration creation"""
        migration = Migration(
            version="2024.01.01.001",
            name="test_migration",
            description="Test migration",
            up_sql="CREATE TABLE test (id INTEGER);",
            down_sql="DROP TABLE test;"
        )
        
        self.assertEqual(migration.version, "2024.01.01.001")
        self.assertEqual(migration.name, "test_migration")
        self.assertIsNotNone(migration.get_checksum())
    
    def test_migration_validation(self):
        """Test migration validation"""
        # Valid migration
        valid_migration = Migration(
            version="2024.01.01.001",
            name="valid_migration",
            description="Valid migration",
            up_sql="CREATE TABLE test (id INTEGER);"
        )
        
        errors = valid_migration.validate()
        self.assertEqual(len(errors), 0)
        
        # Invalid version format
        invalid_version = Migration(
            version="invalid_version",
            name="test_migration",
            description="Test",
            up_sql="CREATE TABLE test (id INTEGER);"
        )
        
        errors = invalid_version.validate()
        self.assertGreater(len(errors), 0)
        
        # Missing up_sql
        missing_sql = Migration(
            version="2024.01.01.001",
            name="test_migration",
            description="Test",
            up_sql=""
        )
        
        errors = missing_sql.validate()
        self.assertGreater(len(errors), 0)
    
    def test_migration_checksum(self):
        """Test migration checksum calculation"""
        migration1 = Migration(
            version="2024.01.01.001",
            name="test",
            description="Test",
            up_sql="CREATE TABLE test (id INTEGER);"
        )
        
        migration2 = Migration(
            version="2024.01.01.001",
            name="test",
            description="Test",
            up_sql="CREATE TABLE test (id INTEGER);"
        )
        
        # Same content should produce same checksum
        self.assertEqual(migration1.get_checksum(), migration2.get_checksum())
        
        # Different content should produce different checksum
        migration2.up_sql = "CREATE TABLE test2 (id INTEGER);"
        self.assertNotEqual(migration1.get_checksum(), migration2.get_checksum())


class TestMigrationRecord(unittest.TestCase):
    """Test MigrationRecord class functionality"""
    
    def test_migration_record_creation(self):
        """Test migration record creation"""
        record = MigrationRecord(
            version="2024.01.01.001",
            name="test_migration",
            checksum="abc123",
            status=MigrationStatus.COMPLETED
        )
        
        self.assertEqual(record.version, "2024.01.01.001")
        self.assertEqual(record.status, MigrationStatus.COMPLETED)
    
    def test_migration_record_to_dict(self):
        """Test migration record serialization"""
        record = MigrationRecord(
            version="2024.01.01.001",
            name="test_migration",
            checksum="abc123",
            status=MigrationStatus.COMPLETED,
            executed_at=datetime.now()
        )
        
        data = record.to_dict()
        
        self.assertIn('version', data)
        self.assertIn('status', data)
        self.assertEqual(data['status'], 'completed')


class TestSQLiteMigrationEngine(unittest.TestCase):
    """Test SQLiteMigrationEngine functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database and migration directory
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_migrations.db")
        self.migration_dir = os.path.join(self.temp_dir, "migrations")
        
        os.makedirs(self.migration_dir, exist_ok=True)
        
        # Create connection manager
        config = ConnectionConfig(
            database_path=self.db_path,
            max_pool_size=3,
            min_pool_size=1
        )
        
        self.connection_manager = SQLiteConnectionManager(config)
        self.connection_manager.initialize()
        
        # Create migration engine
        self.migration_engine = SQLiteMigrationEngine(
            self.connection_manager,
            self.migration_dir
        )
    
    def tearDown(self):
        """Clean up test environment"""
        try:
            self.connection_manager.shutdown()
        except:
            pass
        
        # Clean up temp files
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_migration_file(self, version: str, name: str, 
                                   up_sql: str, down_sql: str = "",
                                   dependencies: str = "", tags: str = "") -> Path:
        """Helper to create test migration files"""
        filename = f"{version}_{name}.sql"
        file_path = Path(self.migration_dir) / filename
        
        content = f"""-- version: {version}
-- name: {name}
-- description: Test migration for {name}
-- dependencies: {dependencies}
-- tags: {tags}

{up_sql}

-- DOWN
{down_sql}
"""
        
        file_path.write_text(content, encoding='utf-8')
        return file_path
    
    def test_migration_engine_initialization(self):
        """Test migration engine initialization"""
        success = self.migration_engine.initialize()
        self.assertTrue(success)
        
        # Check if schema_migrations table was created
        with self.connection_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'")
            result = cursor.fetchone()
            self.assertIsNotNone(result)
    
    def test_migration_file_parsing(self):
        """Test parsing of migration files"""
        # Create test migration file
        up_sql = "CREATE TABLE test_table (id INTEGER PRIMARY KEY);"
        down_sql = "DROP TABLE IF EXISTS test_table;"
        
        file_path = self.create_test_migration_file(
            "2024.01.01.001", 
            "test_migration",
            up_sql,
            down_sql,
            dependencies="",
            tags="test, initial"
        )
        
        # Parse migration
        migration = self.migration_engine._parse_migration_file(file_path)
        
        self.assertIsNotNone(migration)
        self.assertEqual(migration.version, "2024.01.01.001")
        self.assertEqual(migration.name, "test_migration")
        self.assertIn("CREATE TABLE test_table", migration.up_sql)
        self.assertIn("DROP TABLE", migration.down_sql)
        self.assertIn("test", migration.tags)
    
    def test_load_migrations(self):
        """Test loading all migrations from directory"""
        # Create multiple migration files
        self.create_test_migration_file(
            "2024.01.01.001", "first_migration",
            "CREATE TABLE table1 (id INTEGER);",
            "DROP TABLE table1;"
        )
        
        self.create_test_migration_file(
            "2024.01.01.002", "second_migration",
            "CREATE TABLE table2 (id INTEGER);",
            "DROP TABLE table2;"
        )
        
        migrations = self.migration_engine.load_migrations()
        
        self.assertEqual(len(migrations), 2)
        self.assertEqual(migrations[0].version, "2024.01.01.001")
        self.assertEqual(migrations[1].version, "2024.01.01.002")
    
    def test_migration_execution(self):
        """Test executing migrations"""
        # Initialize migration system
        self.migration_engine.initialize()
        
        # Create test migration
        migration = Migration(
            version="2024.01.01.001",
            name="test_execution",
            description="Test migration execution",
            up_sql="CREATE TABLE test_execution (id INTEGER PRIMARY KEY, name TEXT);",
            down_sql="DROP TABLE IF EXISTS test_execution;"
        )
        
        # Execute migration
        success = self.migration_engine.execute_migration(migration)
        self.assertTrue(success)
        
        # Verify table was created
        with self.connection_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test_execution'")
            result = cursor.fetchone()
            self.assertIsNotNone(result)
        
        # Verify migration was recorded
        executed_migrations = self.migration_engine.get_executed_migrations()
        self.assertEqual(len(executed_migrations), 1)
        self.assertEqual(executed_migrations[0].version, "2024.01.01.001")
        self.assertEqual(executed_migrations[0].status, MigrationStatus.COMPLETED)
    
    def test_migration_rollback(self):
        """Test rolling back migrations"""
        # Initialize and execute migration first
        self.migration_engine.initialize()
        
        # Create migration file for rollback test
        self.create_test_migration_file(
            "2024.01.01.001", "rollback_test",
            "CREATE TABLE rollback_test (id INTEGER PRIMARY KEY);",
            "DROP TABLE IF EXISTS rollback_test;"
        )
        
        migrations = self.migration_engine.load_migrations()
        migration = migrations[0]
        
        # Execute migration
        success = self.migration_engine.execute_migration(migration)
        self.assertTrue(success)
        
        # Verify table exists
        with self.connection_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rollback_test'")
            result = cursor.fetchone()
            self.assertIsNotNone(result)
        
        # Rollback migration
        success = self.migration_engine.rollback_migration("2024.01.01.001")
        self.assertTrue(success)
        
        # Verify table was dropped
        with self.connection_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rollback_test'")
            result = cursor.fetchone()
            self.assertIsNone(result)
    
    def test_migration_dependencies(self):
        """Test migration dependency checking"""
        # Initialize migration system
        self.migration_engine.initialize()
        
        # Create migration with dependency
        migration_with_dep = Migration(
            version="2024.01.01.002",
            name="dependent_migration",
            description="Migration with dependency",
            up_sql="CREATE TABLE dependent_table (id INTEGER);",
            dependencies=["2024.01.01.001"]
        )
        
        # Try to execute without dependency - should fail
        with self.assertRaises(Exception):
            self.migration_engine.execute_migration(migration_with_dep)
        
        # Execute dependency first
        dependency_migration = Migration(
            version="2024.01.01.001",
            name="dependency_migration",
            description="Dependency migration",
            up_sql="CREATE TABLE dependency_table (id INTEGER);"
        )
        
        success = self.migration_engine.execute_migration(dependency_migration)
        self.assertTrue(success)
        
        # Now dependent migration should work
        success = self.migration_engine.execute_migration(migration_with_dep)
        self.assertTrue(success)
    
    def test_migration_status(self):
        """Test getting migration status"""
        # Initialize migration system
        self.migration_engine.initialize()
        
        # Create some migration files
        self.create_test_migration_file(
            "2024.01.01.001", "migration1",
            "CREATE TABLE test1 (id INTEGER);",
            "DROP TABLE test1;"
        )
        
        self.create_test_migration_file(
            "2024.01.01.002", "migration2", 
            "CREATE TABLE test2 (id INTEGER);",
            "DROP TABLE test2;"
        )
        
        # Get initial status
        status = self.migration_engine.get_migration_status()
        
        self.assertEqual(status['total_migrations'], 2)
        self.assertEqual(status['executed_count'], 0)
        self.assertEqual(status['pending_count'], 2)
        self.assertEqual(status['failed_count'], 0)
        
        # Execute one migration
        migrations = self.migration_engine.load_migrations()
        success = self.migration_engine.execute_migration(migrations[0])
        self.assertTrue(success)
        
        # Check status again
        status = self.migration_engine.get_migration_status()
        
        self.assertEqual(status['executed_count'], 1)
        self.assertEqual(status['pending_count'], 1)
    
    def test_schema_validation(self):
        """Test database schema validation"""
        # Initialize migration system
        self.migration_engine.initialize()
        
        # Create and execute migrations to set up expected schema
        self.create_test_migration_file(
            "2024.01.01.001", "initial_schema",
            """
            CREATE TABLE content (id INTEGER PRIMARY KEY);
            CREATE TABLE downloads (id INTEGER PRIMARY KEY);
            CREATE TABLE download_sessions (id INTEGER PRIMARY KEY);
            CREATE TABLE download_errors (id INTEGER PRIMARY KEY);
            """,
            """
            DROP TABLE download_errors;
            DROP TABLE download_sessions;
            DROP TABLE downloads;
            DROP TABLE content;
            """
        )
        
        migrations = self.migration_engine.load_migrations()
        success = self.migration_engine.execute_migration(migrations[0])
        self.assertTrue(success)
        
        # Validation should pass now
        is_valid = self.migration_engine.validate_schema()
        self.assertTrue(is_valid)
    
    def test_pending_migrations(self):
        """Test getting pending migrations"""
        # Initialize migration system
        self.migration_engine.initialize()
        
        # Create migration files
        self.create_test_migration_file(
            "2024.01.01.001", "migration1",
            "CREATE TABLE test1 (id INTEGER);",
            "DROP TABLE test1;"
        )
        
        self.create_test_migration_file(
            "2024.01.01.002", "migration2",
            "CREATE TABLE test2 (id INTEGER);", 
            "DROP TABLE test2;"
        )
        
        # All should be pending initially
        pending = self.migration_engine.get_pending_migrations()
        self.assertEqual(len(pending), 2)
        
        # Execute first migration
        migrations = self.migration_engine.load_migrations()
        success = self.migration_engine.execute_migration(migrations[0])
        self.assertTrue(success)
        
        # Only one should be pending now
        pending = self.migration_engine.get_pending_migrations()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].version, "2024.01.01.002")
    
    def test_migrate_to_version(self):
        """Test migrating to specific version"""
        # Initialize migration system
        self.migration_engine.initialize()
        
        # Create multiple migration files
        for i in range(1, 4):
            self.create_test_migration_file(
                f"2024.01.01.{i:03d}", f"migration{i}",
                f"CREATE TABLE test{i} (id INTEGER);",
                f"DROP TABLE test{i};"
            )
        
        # Migrate to version 002
        success = self.migration_engine.migrate_to_version("2024.01.01.002")
        self.assertTrue(success)
        
        # Check that only first two migrations were executed
        executed = self.migration_engine.get_executed_migrations()
        completed_migrations = [m for m in executed if m.status == MigrationStatus.COMPLETED]
        self.assertEqual(len(completed_migrations), 2)
        
        # Third migration should still be pending
        pending = self.migration_engine.get_pending_migrations()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].version, "2024.01.01.003")


class TestMigrationFactory(unittest.TestCase):
    """Test migration factory functions"""
    
    def test_create_migration_engine(self):
        """Test migration engine factory function"""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test.db")
        
        try:
            config = ConnectionConfig(database_path=db_path)
            connection_manager = SQLiteConnectionManager(config)
            connection_manager.initialize()
            
            engine = create_migration_engine(connection_manager)
            
            self.assertIsInstance(engine, SQLiteMigrationEngine)
            
            connection_manager.shutdown()
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == '__main__':
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.ERROR)  # Reduce log noise during tests
    
    # Run tests
    unittest.main() 