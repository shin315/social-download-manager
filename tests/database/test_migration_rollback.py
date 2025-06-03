#!/usr/bin/env python3
"""
Test Script for Migration Rollback Mechanism

Tests the comprehensive rollback system including backup management, error handling,
rollback execution, and edge cases for the migration system.
"""

import sys
import os
import tempfile
import sqlite3
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone

# Add the project root to Python path
sys.path.insert(0, '.')

from data.database.connection import ConnectionConfig, SQLiteConnectionManager
from data.database.version_detection import VersionManager, DatabaseVersion
from data.database.migration_rollback import (
    MigrationSafetyManager, BackupManager, SQLiteErrorHandler, SQLiteRollbackManager,
    MigrationStage, MigrationError, MigrationState, RollbackOperation, RollbackStep
)


def setup_test_v121_database(db_path: str) -> int:
    """Create a test v1.2.1 database with sample data"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create v1.2.1 schema
    cursor.execute('''
        CREATE TABLE downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            local_path TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT
        )
    ''')
    
    # Add sample data
    test_data = [
        (1, 'https://tiktok.com/@user/video/123456789', '/downloads/cat_video.mp4', 'completed', 
         '2024-12-25T10:30:00', '{"platform": "tiktok", "title": "Funny Cat Video", "size": 8597504}'),
        (2, 'https://youtube.com/watch?v=dQw4w9WgXcQ', '/downloads/rick_roll.mp4', 'completed',
         '2024-12-26T15:45:00', '{"platform": "youtube", "title": "Never Gonna Give You Up", "size": 26673152}'),
        (3, 'https://instagram.com/p/ABC123DEF456/', '/downloads/sunset.mp4', 'failed',
         '2024-12-27T08:15:00', '{"platform": "instagram", "title": "Beautiful Sunset", "size": 13421772}')
    ]
    
    for data in test_data:
        cursor.execute('''
            INSERT INTO downloads (id, url, local_path, status, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', data)
    
    conn.commit()
    conn.close()
    
    print(f"✓ Created test v1.2.1 database: {db_path}")
    return len(test_data)


def test_backup_manager():
    """Test backup creation and restoration functionality"""
    print(f"\n💾 Testing Backup Manager")
    print("-" * 50)
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "backup_test.db")
    backup_dir = os.path.join(temp_dir, "backups")
    
    try:
        # Setup test database
        record_count = setup_test_v121_database(db_path)
        
        config = ConnectionConfig(database_path=db_path)
        connection_manager = SQLiteConnectionManager(config)
        connection_manager.initialize()
        
        backup_manager = BackupManager(connection_manager, backup_dir)
        
        # Test backup creation
        print("  📦 Testing backup creation...")
        backup_path = backup_manager.create_full_backup("test_migration_001")
        
        backup_exists = os.path.exists(backup_path)
        print(f"    Backup created: {'✅' if backup_exists else '❌'} {backup_path}")
        
        # Verify backup content
        backup_conn = sqlite3.connect(backup_path)
        backup_cursor = backup_conn.cursor()
        backup_cursor.execute("SELECT COUNT(*) FROM downloads")
        backup_count = backup_cursor.fetchone()[0]
        backup_conn.close()
        
        content_match = backup_count == record_count
        print(f"    Backup content match: {'✅' if content_match else '❌'} ({backup_count} == {record_count})")
        
        # Test data modification
        print("  🔧 Modifying original database...")
        with connection_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM downloads WHERE id = 1")
            cursor.execute("UPDATE downloads SET status = 'corrupted' WHERE id = 2")
            conn.commit()
        
        # Verify modification
        with connection_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM downloads")
            modified_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM downloads WHERE status = 'corrupted'")
            corrupted_count = cursor.fetchone()[0]
        
        print(f"    Original modified: {'✅' if modified_count < record_count else '❌'} (deleted 1 record)")
        print(f"    Corruption added: {'✅' if corrupted_count > 0 else '❌'} (corrupted 1 record)")
        
        # Test backup restoration
        print("  🔄 Testing backup restoration...")
        restore_success = backup_manager.restore_from_backup(backup_path)
        print(f"    Restore operation: {'✅' if restore_success else '❌'}")
        
        # Verify restoration
        connection_manager.initialize()  # Reinitialize after restore
        with connection_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM downloads")
            restored_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM downloads WHERE status = 'corrupted'")
            corrupted_after_restore = cursor.fetchone()[0]
        
        restore_complete = restored_count == record_count and corrupted_after_restore == 0
        print(f"    Data restored: {'✅' if restore_complete else '❌'} ({restored_count} records, {corrupted_after_restore} corrupted)")
        
        # Test backup cleanup
        print("  🧹 Testing backup cleanup...")
        
        # Create multiple backups
        backup_paths = []
        for i in range(7):
            backup_path = backup_manager.create_full_backup(f"test_cleanup_{i}")
            backup_paths.append(backup_path)
        
        initial_backup_count = len([f for f in os.listdir(backup_dir) if f.endswith('.db')])
        print(f"    Backups created: {initial_backup_count}")
        
        # Cleanup old backups (keep 5)
        removed_backups = backup_manager.cleanup_old_backups(keep_count=5)
        remaining_backup_count = len([f for f in os.listdir(backup_dir) if f.endswith('.db')])
        
        cleanup_success = remaining_backup_count == 5 and len(removed_backups) > 0
        print(f"    Cleanup successful: {'✅' if cleanup_success else '❌'} ({remaining_backup_count} remaining, {len(removed_backups)} removed)")
        
        connection_manager.shutdown()
        
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_error_handler():
    """Test error handling logic and rollback decision making"""
    print(f"\n⚠️ Testing Error Handler")
    print("-" * 50)
    
    error_handler = SQLiteErrorHandler()
    
    # Create mock migration state
    migration_state = MigrationState(
        migration_id="test_migration_error_handling",
        source_version=DatabaseVersion.V1_2_1,
        target_version=DatabaseVersion.V2_0_0,
        current_stage=MigrationStage.PREPARATION,
        started_at=datetime.now(timezone.utc)
    )
    
    # Test 1: Recoverable error handling
    print("  🔄 Testing recoverable error handling...")
    
    recoverable_error = MigrationError(
        stage=MigrationStage.CLEANUP,
        error_type="MinorError",
        error_message="Non-critical cleanup failed",
        recoverable=True
    )
    
    should_continue, action = error_handler.handle_error(recoverable_error, migration_state)
    print(f"    Recoverable error continues: {'✅' if should_continue else '❌'}")
    print(f"    Action taken: {action}")
    
    # Test 2: Fatal error handling
    print("  💥 Testing fatal error handling...")
    
    fatal_error = MigrationError(
        stage=MigrationStage.SCHEMA_TRANSFORMATION,
        error_type="DatabaseCorruption",
        error_message="Critical schema transformation failed",
        recoverable=False
    )
    
    should_continue, action = error_handler.handle_error(fatal_error, migration_state)
    print(f"    Fatal error stops: {'✅' if not should_continue else '❌'}")
    print(f"    Action taken: {action}")
    
    # Test 3: Rollback decision logic
    print("  🔙 Testing rollback decision logic...")
    
    # Test with no errors
    should_rollback = error_handler.should_rollback([], MigrationStage.DATA_CONVERSION)
    print(f"    No errors, no rollback: {'✅' if not should_rollback else '❌'}")
    
    # Test with recoverable errors only
    recoverable_errors = [
        MigrationError(MigrationStage.PREPARATION, "Warning", "Minor issue 1"),
        MigrationError(MigrationStage.CLEANUP, "Warning", "Minor issue 2")
    ]
    should_rollback = error_handler.should_rollback(recoverable_errors, MigrationStage.DATA_CONVERSION)
    print(f"    Recoverable errors only, no rollback: {'✅' if not should_rollback else '❌'}")
    
    # Test with fatal error
    fatal_errors = recoverable_errors + [fatal_error]
    should_rollback = error_handler.should_rollback(fatal_errors, MigrationStage.DATA_CONVERSION)
    print(f"    Fatal error triggers rollback: {'✅' if should_rollback else '❌'}")
    
    # Test with too many errors in critical stage
    many_critical_errors = [
        MigrationError(MigrationStage.SCHEMA_TRANSFORMATION, "Error", "Issue 1"),
        MigrationError(MigrationStage.SCHEMA_TRANSFORMATION, "Error", "Issue 2"),
        MigrationError(MigrationStage.DATA_CONVERSION, "Error", "Issue 3")
    ]
    should_rollback = error_handler.should_rollback(many_critical_errors, MigrationStage.DATA_CONVERSION)
    print(f"    Many critical errors trigger rollback: {'✅' if should_rollback else '❌'}")


def test_rollback_manager():
    """Test rollback plan creation and execution"""
    print(f"\n🔄 Testing Rollback Manager")
    print("-" * 50)
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "rollback_test.db")
    backup_dir = os.path.join(temp_dir, "backups")
    
    try:
        # Setup test database
        setup_test_v121_database(db_path)
        
        config = ConnectionConfig(database_path=db_path)
        connection_manager = SQLiteConnectionManager(config)
        connection_manager.initialize()
        
        backup_manager = BackupManager(connection_manager, backup_dir)
        rollback_manager = SQLiteRollbackManager(connection_manager, backup_manager)
        
        # Test 1: Early stage rollback plan
        print("  📋 Testing early stage rollback plan...")
        
        early_migration_state = MigrationState(
            migration_id="test_early_rollback",
            source_version=DatabaseVersion.V1_2_1,
            target_version=DatabaseVersion.V2_0_0,
            current_stage=MigrationStage.PREPARATION,
            started_at=datetime.now(timezone.utc)
        )
        
        early_plan = rollback_manager.create_rollback_plan(early_migration_state)
        has_cleanup_steps = any(step.operation == RollbackOperation.REMOVE_MIGRATION_RECORDS for step in early_plan)
        print(f"    Early stage plan created: {'✅' if len(early_plan) > 0 else '❌'} ({len(early_plan)} steps)")
        print(f"    Has cleanup steps: {'✅' if has_cleanup_steps else '❌'}")
        
        # Test 2: Schema transformation rollback plan
        print("  🏗️ Testing schema transformation rollback plan...")
        
        # Create backup for schema stage
        backup_path = backup_manager.create_full_backup("test_schema_rollback")
        
        schema_migration_state = MigrationState(
            migration_id="test_schema_rollback",
            source_version=DatabaseVersion.V1_2_1,
            target_version=DatabaseVersion.V2_0_0,
            current_stage=MigrationStage.SCHEMA_TRANSFORMATION,
            started_at=datetime.now(timezone.utc),
            backup_paths=[backup_path]
        )
        
        schema_plan = rollback_manager.create_rollback_plan(schema_migration_state)
        has_backup_restore = any(step.operation == RollbackOperation.RESTORE_FROM_BACKUP for step in schema_plan)
        print(f"    Schema stage plan created: {'✅' if len(schema_plan) > 0 else '❌'} ({len(schema_plan)} steps)")
        print(f"    Has backup restore: {'✅' if has_backup_restore else '❌'}")
        
        # Test 3: Rollback execution
        print("  ⚡ Testing rollback execution...")
        
        # Modify database to simulate partial migration
        with connection_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("ALTER TABLE downloads ADD COLUMN test_column TEXT")
            cursor.execute("UPDATE downloads SET test_column = 'test_value' WHERE id = 1")
            conn.commit()
        
        # Verify modification
        with connection_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(downloads)")
            columns = [row[1] for row in cursor.fetchall()]
            has_test_column = 'test_column' in columns
        
        print(f"    Database modified: {'✅' if has_test_column else '❌'} (added test_column)")
        
        # Execute rollback
        rollback_success, rollback_errors = rollback_manager.execute_rollback(schema_plan)
        print(f"    Rollback execution: {'✅' if rollback_success else '❌'}")
        
        if rollback_errors:
            print(f"    Rollback errors: {len(rollback_errors)}")
            for error in rollback_errors[:2]:  # Show first 2 errors
                print(f"      - {error}")
        
        # Verify rollback (database should be restored)
        connection_manager.initialize()  # Reinitialize after restore
        with connection_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(downloads)")
            columns_after = [row[1] for row in cursor.fetchall()]
            test_column_removed = 'test_column' not in columns_after
            
            cursor.execute("SELECT COUNT(*) FROM downloads")
            record_count_after = cursor.fetchone()[0]
        
        rollback_verified = test_column_removed and record_count_after == 3
        print(f"    Rollback verified: {'✅' if rollback_verified else '❌'} (test_column removed, {record_count_after} records)")
        
        connection_manager.shutdown()
        
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_migration_safety_manager():
    """Test high-level migration safety orchestration"""
    print(f"\n🛡️ Testing Migration Safety Manager")
    print("-" * 50)
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "safety_test.db")
    backup_dir = os.path.join(temp_dir, "backups")
    
    try:
        # Setup test database
        setup_test_v121_database(db_path)
        
        config = ConnectionConfig(database_path=db_path)
        connection_manager = SQLiteConnectionManager(config)
        connection_manager.initialize()
        
        safety_manager = MigrationSafetyManager(connection_manager, backup_dir)
        
        # Test 1: Start safe migration
        print("  🚀 Testing safe migration start...")
        
        migration_id = safety_manager.start_safe_migration(DatabaseVersion.V1_2_1, DatabaseVersion.V2_0_0)
        migration_started = migration_id is not None and len(migration_id) > 0
        print(f"    Migration started: {'✅' if migration_started else '❌'} (ID: {migration_id})")
        
        # Test 2: Successful stage execution
        print("  ✅ Testing successful stage execution...")
        
        def successful_operation():
            return "Operation completed successfully"
        
        success, result = safety_manager.execute_stage_with_safety(
            MigrationStage.PREPARATION, 
            successful_operation
        )
        
        print(f"    Successful stage: {'✅' if success else '❌'}")
        print(f"    Result: {result}")
        
        # Test 3: Failed stage execution with rollback
        print("  💥 Testing failed stage execution...")
        
        def failing_operation():
            raise RuntimeError("Simulated critical failure")
        
        success, result = safety_manager.execute_stage_with_safety(
            MigrationStage.SCHEMA_TRANSFORMATION,
            failing_operation
        )
        
        print(f"    Failed stage handled: {'✅' if not success else '❌'}")
        print(f"    Error captured: {'✅' if isinstance(result, MigrationError) else '❌'}")
        
        # Check migration status after failure
        migration_status = safety_manager.get_migration_status()
        rolled_back = migration_status.current_stage == MigrationStage.ROLLED_BACK
        print(f"    Migration rolled back: {'✅' if rolled_back else '❌'}")
        
        # Test 4: Start new migration after rollback
        print("  🔄 Testing new migration after rollback...")
        
        new_migration_id = safety_manager.start_safe_migration(DatabaseVersion.V1_2_1, DatabaseVersion.V2_0_0)
        new_migration_started = new_migration_id != migration_id
        print(f"    New migration started: {'✅' if new_migration_started else '❌'}")
        
        # Test 5: Complete successful migration
        print("  🎯 Testing migration completion...")
        
        # Execute some successful stages
        for stage in [MigrationStage.PREPARATION, MigrationStage.SCHEMA_VALIDATION]:
            success, _ = safety_manager.execute_stage_with_safety(stage, successful_operation)
            if not success:
                print(f"    Unexpected failure in {stage.value}")
                break
        
        completion_success, completion_message = safety_manager.complete_migration()
        print(f"    Migration completed: {'✅' if completion_success else '❌'}")
        print(f"    Completion message: {completion_message}")
        
        connection_manager.shutdown()
        
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_edge_cases():
    """Test edge cases and error scenarios"""
    print(f"\n🧪 Testing Edge Cases")
    print("-" * 50)
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "edge_case_test.db")
    backup_dir = os.path.join(temp_dir, "backups")
    
    try:
        # Setup test database
        setup_test_v121_database(db_path)
        
        config = ConnectionConfig(database_path=db_path)
        connection_manager = SQLiteConnectionManager(config)
        connection_manager.initialize()
        
        backup_manager = BackupManager(connection_manager, backup_dir)
        
        # Test 1: Backup of non-existent database
        print("  👻 Testing backup of non-existent database...")
        
        fake_config = ConnectionConfig(database_path="/non/existent/database.db")
        fake_connection_manager = SQLiteConnectionManager(fake_config)
        fake_backup_manager = BackupManager(fake_connection_manager, backup_dir)
        
        try:
            fake_backup_manager.create_full_backup("fake_migration")
            backup_fake_failed = False
        except Exception:
            backup_fake_failed = True
        
        print(f"    Non-existent DB backup fails: {'✅' if backup_fake_failed else '❌'}")
        
        # Test 2: Restore from non-existent backup
        print("  🔍 Testing restore from non-existent backup...")
        
        restore_fake_success = backup_manager.restore_from_backup("/non/existent/backup.db")
        print(f"    Non-existent backup restore fails: {'✅' if not restore_fake_success else '❌'}")
        
        # Test 3: Rollback without backup paths
        print("  🔄 Testing rollback without backup paths...")
        
        rollback_manager = SQLiteRollbackManager(connection_manager, backup_manager)
        
        no_backup_state = MigrationState(
            migration_id="test_no_backup",
            source_version=DatabaseVersion.V1_2_1,
            target_version=DatabaseVersion.V2_0_0,
            current_stage=MigrationStage.SCHEMA_TRANSFORMATION,
            started_at=datetime.now(timezone.utc),
            backup_paths=[]  # No backup paths
        )
        
        no_backup_plan = rollback_manager.create_rollback_plan(no_backup_state)
        has_manual_steps = any(step.operation in [
            RollbackOperation.DROP_NEW_TABLES, 
            RollbackOperation.RENAME_TABLES_BACK
        ] for step in no_backup_plan)
        
        print(f"    Manual rollback plan created: {'✅' if has_manual_steps else '❌'} ({len(no_backup_plan)} steps)")
        
        # Test 4: Multiple backup cleanup
        print("  🧹 Testing cleanup with no backups...")
        
        empty_backup_dir = os.path.join(temp_dir, "empty_backups")
        os.makedirs(empty_backup_dir, exist_ok=True)
        
        empty_backup_manager = BackupManager(connection_manager, empty_backup_dir)
        removed_backups = empty_backup_manager.cleanup_old_backups()
        
        empty_cleanup_handled = len(removed_backups) == 0
        print(f"    Empty backup cleanup handled: {'✅' if empty_cleanup_handled else '❌'}")
        
        # Test 5: Migration state without active migration
        print("  ⚠️ Testing operations without active migration...")
        
        safety_manager = MigrationSafetyManager(connection_manager, backup_dir)
        
        # Try to execute stage without starting migration
        try:
            safety_manager.execute_stage_with_safety(MigrationStage.PREPARATION, lambda: "test")
            no_migration_handled = False
        except RuntimeError:
            no_migration_handled = True
        
        print(f"    No active migration error: {'✅' if no_migration_handled else '❌'}")
        
        # Try to complete migration without starting it
        completion_success, completion_message = safety_manager.complete_migration()
        no_migration_completion = not completion_success and "No active migration" in completion_message
        print(f"    No migration completion error: {'✅' if no_migration_completion else '❌'}")
        
        connection_manager.shutdown()
        
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    try:
        print("🔄 Migration Rollback Mechanism Test Suite")
        print("=" * 60)
        
        test_backup_manager()
        test_error_handler()
        test_rollback_manager()
        test_migration_safety_manager()
        test_edge_cases()
        
        print(f"\n🎉 All migration rollback tests completed!")
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 