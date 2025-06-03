#!/usr/bin/env python3
"""
Test Script for Data Integrity Validation System

Tests the comprehensive data integrity validation capabilities including
checksums, constraint checking, and corruption detection.
"""

import sys
import os
import tempfile
import sqlite3
import json
import shutil
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, '.')

from data.database.connection import ConnectionConfig, SQLiteConnectionManager
from data.database.version_detection import VersionManager, DatabaseVersion
from data.database.schema_transformer import SchemaTransformationManager
from data.database.data_converter import DataConversionManager
from data.database.data_integrity import (
    DataIntegrityManager, SQLiteIntegrityValidator, ValidationLevel,
    ValidationResult, ValidationIssue, TableChecksum, IntegrityReport
)


def setup_clean_v2_database(db_path: str) -> int:
    """Create a clean v2.0 database with test data"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create v2.0 schema
    cursor.execute('''
        CREATE TABLE content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform_id TEXT NOT NULL,
            platform_content_id TEXT NOT NULL,
            original_url TEXT NOT NULL UNIQUE,
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
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
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
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (content_id) REFERENCES content (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE download_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_name TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE download_errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            download_id INTEGER,
            error_type TEXT NOT NULL,
            error_message TEXT NOT NULL,
            stack_trace TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (download_id) REFERENCES downloads (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE schema_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'pending',
            executed_at TEXT DEFAULT CURRENT_TIMESTAMP,
            execution_time_ms INTEGER
        )
    ''')
    
    # Add test data
    content_data = [
        (1, 'tiktok', '123456789', 'https://tiktok.com/@user/video/123456789', 'Funny Cat Video', 
         'A hilarious cat video', '@cat_lover', None, 'https://example.com/thumb1.jpg', 
         45, 125000, 5600, 'video', '2024-12-25T10:00:00', '{}', 'active'),
        (2, 'youtube', 'dQw4w9WgXcQ', 'https://youtube.com/watch?v=dQw4w9WgXcQ', 'Never Gonna Give You Up',
         'Rick Astley music video', 'Rick Astley', 'https://youtube.com/c/RickAstley', 
         'https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg', 212, 1200000000, 15000000, 
         'video', '1987-07-27T00:00:00', '{}', 'active'),
        (3, 'instagram', 'ABC123DEF456', 'https://instagram.com/p/ABC123DEF456/', 'Beautiful Sunset',
         'Amazing sunset from the beach', '@nature_photographer', None, 'https://example.com/thumb3.jpg',
         30, 5600, 234, 'video', '2024-12-26T08:00:00', '{}', 'active')
    ]
    
    for content in content_data:
        cursor.execute('''
            INSERT INTO content (id, platform_id, platform_content_id, original_url, title,
                               description, author_name, author_url, thumbnail_url, duration_seconds,
                               view_count, like_count, content_type, published_at, metadata_json, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', content)
    
    download_data = [
        (1, 1, '/downloads/cat_video.mp4', 'cat_video.mp4', 8597504, 'mp4', '1080p', 'completed',
         '2024-12-25T10:30:00', '2024-12-25T10:31:00', 1.0, None, 0, '{}'),
        (2, 2, '/downloads/rick_roll.mp4', 'rick_roll.mp4', 26673152, 'mp4', '720p', 'completed',
         '2024-12-26T15:45:00', '2024-12-26T15:47:00', 1.0, None, 0, '{}'),
        (3, 3, '/downloads/sunset.mp4', 'sunset.mp4', 13421772, 'mp4', '1080p', 'failed',
         '2024-12-27T08:15:00', None, 0.5, 'Network timeout', 2, '{}')
    ]
    
    for download in download_data:
        cursor.execute('''
            INSERT INTO downloads (id, content_id, file_path, file_name, file_size_bytes, format,
                                 quality, status, download_started_at, download_completed_at,
                                 download_progress, error_message, retry_count, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', download)
    
    # Add session data
    cursor.execute('''
        INSERT INTO download_sessions (id, session_name, description, status)
        VALUES (1, 'Test Session', 'Testing session for integrity validation', 'active')
    ''')
    
    # Add migration record
    cursor.execute('''
        INSERT INTO schema_migrations (version, description, status, execution_time_ms)
        VALUES ('2.0.0', 'Initial v2.0 schema creation', 'completed', 1500)
    ''')
    
    conn.commit()
    conn.close()
    
    print(f"✓ Created clean v2.0 database: {db_path}")
    return len(content_data)


def setup_corrupted_database(db_path: str):
    """Create a database with integrity issues for testing"""
    # First create clean database
    setup_clean_v2_database(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Disable foreign keys temporarily to allow orphaned records
    cursor.execute("PRAGMA foreign_keys = OFF")
    
    # Add orphaned download record (content_id that doesn't exist)
    cursor.execute('''
        INSERT INTO downloads (content_id, file_path, file_name, status)
        VALUES (999, '/downloads/orphaned.mp4', 'orphaned.mp4', 'pending')
    ''')
    
    # Temporarily disable UNIQUE constraint by recreating content table without constraint
    cursor.execute("ALTER TABLE content RENAME TO content_temp")
    
    # Create new content table without UNIQUE constraint
    cursor.execute('''
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
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Copy data back
    cursor.execute('''
        INSERT INTO content SELECT * FROM content_temp
    ''')
    
    # Add duplicate content URL (now it's allowed)
    cursor.execute('''
        INSERT INTO content (platform_id, platform_content_id, original_url, title, status)
        VALUES ('tiktok', '987654321', 'https://tiktok.com/@user/video/123456789', 'Duplicate Video', 'active')
    ''')
    
    # Drop temp table
    cursor.execute("DROP TABLE content_temp")
    
    # Add invalid error record (download_id that doesn't exist)
    cursor.execute('''
        INSERT INTO download_errors (download_id, error_type, error_message)
        VALUES (999, 'TestError', 'Error for non-existent download')
    ''')
    
    # Re-enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")
    
    conn.commit()
    conn.close()
    
    print(f"✓ Created corrupted database for testing: {db_path}")


def test_basic_integrity_validation():
    """Test basic integrity validation functionality"""
    print(f"\n🔍 Testing Basic Integrity Validation")
    print("-" * 50)
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "basic_integrity_test.db")
    
    try:
        # Setup clean database
        record_count = setup_clean_v2_database(db_path)
        
        # Initialize integrity validator
        config = ConnectionConfig(database_path=db_path)
        connection_manager = SQLiteConnectionManager(config)
        connection_manager.initialize()
        
        integrity_manager = DataIntegrityManager(connection_manager)
        
        # Test basic validation
        print("  📋 Running basic integrity validation...")
        success, message, report = integrity_manager.validate_migration_integrity(ValidationLevel.BASIC)
        
        print(f"    Validation result: {'✅ SUCCESS' if success else '❌ FAILED'}")
        print(f"    Message: {message}")
        print(f"    Total checks: {report.total_checks}")
        print(f"    Passed: {report.passed_checks}")
        print(f"    Failed: {report.failed_checks}")
        print(f"    Warnings: {report.warnings}")
        
        if report.issues:
            print(f"    Issues found: {len(report.issues)}")
            for issue in report.issues[:3]:  # Show first 3 issues
                print(f"      - {issue.check_name}: {issue.issue_description}")
        
        # Test standard validation
        print("  📋 Running standard integrity validation...")
        success, message, report = integrity_manager.validate_migration_integrity(ValidationLevel.STANDARD)
        
        print(f"    Validation result: {'✅ SUCCESS' if success else '❌ FAILED'}")
        print(f"    Total checks: {report.total_checks}")
        print(f"    Passed: {report.passed_checks}")
        print(f"    Failed: {report.failed_checks}")
        print(f"    Warnings: {report.warnings}")
        
        connection_manager.shutdown()
        
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_checksum_generation():
    """Test table checksum generation"""
    print(f"\n🔐 Testing Checksum Generation")
    print("-" * 50)
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "checksum_test.db")
    
    try:
        # Setup test database
        setup_clean_v2_database(db_path)
        
        config = ConnectionConfig(database_path=db_path)
        connection_manager = SQLiteConnectionManager(config)
        connection_manager.initialize()
        
        validator = SQLiteIntegrityValidator(connection_manager)
        
        # Test checksum generation for different tables
        tables_to_test = ['content', 'downloads', 'download_sessions']
        
        for table_name in tables_to_test:
            print(f"  📊 Generating checksum for table: {table_name}")
            
            try:
                checksum = validator.generate_table_checksum(table_name)
                
                print(f"    Table: {checksum.table_name}")
                print(f"    Row count: {checksum.row_count}")
                print(f"    Content hash: {checksum.content_hash[:16]}...")
                print(f"    Schema hash: {checksum.schema_hash[:16]}...")
                print(f"    Timestamp: {checksum.timestamp}")
                
                # Verify checksum properties
                validations = [
                    (checksum.row_count >= 0, "Row count non-negative"),
                    (len(checksum.content_hash) == 64, "Content hash length correct"),
                    (len(checksum.schema_hash) == 64, "Schema hash length correct"),
                    (checksum.timestamp is not None, "Timestamp present")
                ]
                
                for is_valid, description in validations:
                    status = "✅" if is_valid else "❌"
                    print(f"      {status} {description}")
                
            except Exception as e:
                print(f"    ❌ ERROR generating checksum: {e}")
        
        # Test checksum consistency
        print("  🔄 Testing checksum consistency...")
        
        # Generate checksum twice for same table
        checksum1 = validator.generate_table_checksum('content')
        checksum2 = validator.generate_table_checksum('content')
        
        consistency_checks = [
            (checksum1.row_count == checksum2.row_count, "Row count consistent"),
            (checksum1.content_hash == checksum2.content_hash, "Content hash consistent"),
            (checksum1.schema_hash == checksum2.schema_hash, "Schema hash consistent")
        ]
        
        for is_consistent, description in consistency_checks:
            status = "✅" if is_consistent else "❌"
            print(f"    {status} {description}")
        
        # Test checksum change detection
        print("  🔧 Testing checksum change detection...")
        
        # Get initial checksum
        initial_checksum = validator.generate_table_checksum('content')
        
        # Modify data
        with connection_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE content SET view_count = view_count + 1 WHERE id = 1")
            conn.commit()
        
        # Get modified checksum
        modified_checksum = validator.generate_table_checksum('content')
        
        change_detections = [
            (initial_checksum.row_count == modified_checksum.row_count, "Row count unchanged"),
            (initial_checksum.content_hash != modified_checksum.content_hash, "Content hash changed"),
            (initial_checksum.schema_hash == modified_checksum.schema_hash, "Schema hash unchanged")
        ]
        
        for is_correct, description in change_detections:
            status = "✅" if is_correct else "❌"
            print(f"    {status} {description}")
        
        connection_manager.shutdown()
        
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_corruption_detection():
    """Test corruption and integrity issue detection"""
    print(f"\n🚨 Testing Corruption Detection")
    print("-" * 50)
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "corruption_test.db")
    
    try:
        # Setup corrupted database
        setup_corrupted_database(db_path)
        
        config = ConnectionConfig(database_path=db_path)
        connection_manager = SQLiteConnectionManager(config)
        connection_manager.initialize()
        
        integrity_manager = DataIntegrityManager(connection_manager)
        
        # Test comprehensive validation (should detect issues)
        print("  🔍 Running comprehensive integrity validation...")
        success, message, report = integrity_manager.validate_migration_integrity(ValidationLevel.COMPREHENSIVE)
        
        print(f"    Validation result: {'❌ FAILED (as expected)' if not success else '⚠️ Should have failed'}")
        print(f"    Message: {message}")
        print(f"    Total checks: {report.total_checks}")
        print(f"    Passed: {report.passed_checks}")
        print(f"    Failed: {report.failed_checks}")
        print(f"    Warnings: {report.warnings}")
        
        # Analyze detected issues
        print("  📋 Analyzing detected issues...")
        
        issue_types = {}
        for issue in report.issues:
            issue_type = issue.check_name
            if issue_type not in issue_types:
                issue_types[issue_type] = []
            issue_types[issue_type].append(issue)
        
        for issue_type, issues in issue_types.items():
            print(f"    {issue_type}: {len(issues)} issues")
            for issue in issues[:2]:  # Show first 2 issues of each type
                severity_icon = "❌" if issue.severity == ValidationResult.FAILED else "⚠️"
                print(f"      {severity_icon} {issue.issue_description}")
        
        # Test specific issue detection
        expected_issues = [
            "orphaned_records_check",
            "duplicate_records_check",
            "foreign_key_check"
        ]
        
        detected_issue_types = set(issue.check_name for issue in report.issues)
        
        print("  ✅ Expected issue detection:")
        for expected_issue in expected_issues:
            detected = expected_issue in detected_issue_types
            status = "✅" if detected else "❌"
            print(f"    {status} {expected_issue}: {'Detected' if detected else 'Not detected'}")
        
        connection_manager.shutdown()
        
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_foreign_key_validation():
    """Test foreign key constraint validation"""
    print(f"\n🔗 Testing Foreign Key Validation")
    print("-" * 50)
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "fk_validation_test.db")
    
    try:
        # Setup database with foreign key violations
        setup_clean_v2_database(db_path)
        
        config = ConnectionConfig(database_path=db_path)
        connection_manager = SQLiteConnectionManager(config)
        connection_manager.initialize()
        
        # Enable foreign keys for testing
        with connection_manager.connection() as conn:
            # Disable foreign keys temporarily to insert orphaned record
            conn.execute("PRAGMA foreign_keys = OFF")
            
            # Add orphaned download (content_id doesn't exist)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO downloads (content_id, file_path, file_name, status)
                VALUES (999, '/downloads/orphaned.mp4', 'orphaned.mp4', 'pending')
            ''')
            conn.commit()
            
            # Re-enable foreign keys for validation
            conn.execute("PRAGMA foreign_keys = ON")
        
        validator = SQLiteIntegrityValidator(connection_manager)
        
        # Test foreign key validation
        print("  🔍 Testing foreign key constraint checking...")
        
        with connection_manager.connection() as conn:
            issues = validator._check_foreign_keys(conn)
        
        print(f"    Foreign key violations found: {len(issues)}")
        
        for issue in issues:
            print(f"      - Table: {issue.table_name}")
            print(f"        Description: {issue.issue_description}")
            print(f"        Severity: {issue.severity.value}")
        
        # Verify that violations are detected
        fk_violations_found = len(issues) > 0
        print(f"    Foreign key violations detected: {'✅' if fk_violations_found else '❌'}")
        
        # Test table-specific foreign key validation
        print("  📋 Testing table-specific foreign key validation...")
        
        table_issues = validator.validate_table_integrity('downloads', ValidationLevel.COMPREHENSIVE)
        
        fk_issues = [issue for issue in table_issues if 'foreign_key' in issue.check_name]
        print(f"    Table-specific FK issues: {len(fk_issues)}")
        
        for issue in fk_issues:
            print(f"      - {issue.issue_description}")
        
        connection_manager.shutdown()
        
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_checksum_comparison():
    """Test checksum comparison functionality"""
    print(f"\n🔄 Testing Checksum Comparison")
    print("-" * 50)
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "checksum_comparison_test.db")
    
    try:
        # Setup test database
        setup_clean_v2_database(db_path)
        
        config = ConnectionConfig(database_path=db_path)
        connection_manager = SQLiteConnectionManager(config)
        connection_manager.initialize()
        
        validator = SQLiteIntegrityValidator(connection_manager)
        integrity_manager = DataIntegrityManager(connection_manager)
        
        # Generate initial checksums
        print("  📊 Generating initial checksums...")
        before_checksums = []
        tables = ['content', 'downloads', 'download_sessions']
        
        for table in tables:
            checksum = validator.generate_table_checksum(table)
            before_checksums.append(checksum)
            print(f"    {table}: {checksum.row_count} rows, hash: {checksum.content_hash[:16]}...")
        
        # Simulate migration changes
        print("  🔧 Simulating migration changes...")
        
        with connection_manager.connection() as conn:
            cursor = conn.cursor()
            
            # Add new content record
            cursor.execute('''
                INSERT INTO content (platform_id, platform_content_id, original_url, title, status)
                VALUES ('twitter', '123456789', 'https://twitter.com/user/status/123456789', 'Tweet Video', 'active')
            ''')
            
            # Update existing record
            cursor.execute("UPDATE content SET view_count = view_count + 1000 WHERE id = 1")
            
            # Add corresponding download
            cursor.execute('''
                INSERT INTO downloads (content_id, file_path, file_name, status)
                VALUES (4, '/downloads/tweet.mp4', 'tweet.mp4', 'completed')
            ''')
            
            conn.commit()
        
        # Generate after checksums
        print("  📊 Generating post-migration checksums...")
        after_checksums = []
        
        for table in tables:
            checksum = validator.generate_table_checksum(table)
            after_checksums.append(checksum)
            print(f"    {table}: {checksum.row_count} rows, hash: {checksum.content_hash[:16]}...")
        
        # Compare checksums
        print("  🔍 Comparing checksums...")
        comparison_issues = integrity_manager.compare_checksums(before_checksums, after_checksums)
        
        print(f"    Comparison issues found: {len(comparison_issues)}")
        
        for issue in comparison_issues:
            severity_icon = "❌" if issue.severity == ValidationResult.FAILED else "⚠️"
            print(f"      {severity_icon} {issue.table_name}: {issue.issue_description}")
            if issue.expected_value is not None and issue.actual_value is not None:
                print(f"        Expected: {issue.expected_value}, Actual: {issue.actual_value}")
        
        # Verify expected changes are detected
        expected_changes = ['content', 'downloads']  # These tables should have changes
        detected_changes = set()
        
        for issue in comparison_issues:
            if 'changed' in issue.issue_description.lower() and issue.table_name:
                detected_changes.add(issue.table_name)
        
        print("  ✅ Change detection verification:")
        for table in expected_changes:
            detected = table in detected_changes
            status = "✅" if detected else "❌"
            print(f"    {status} {table}: {'Changes detected' if detected else 'Changes not detected'}")
        
        connection_manager.shutdown()
        
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_validation_levels():
    """Test different validation levels"""
    print(f"\n📊 Testing Validation Levels")
    print("-" * 50)
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "validation_levels_test.db")
    
    try:
        # Setup test database
        setup_clean_v2_database(db_path)
        
        config = ConnectionConfig(database_path=db_path)
        connection_manager = SQLiteConnectionManager(config)
        connection_manager.initialize()
        
        integrity_manager = DataIntegrityManager(connection_manager)
        
        # Test all validation levels
        levels = [ValidationLevel.BASIC, ValidationLevel.STANDARD, ValidationLevel.COMPREHENSIVE, ValidationLevel.PARANOID]
        
        for level in levels:
            print(f"  📋 Testing {level.value} validation level...")
            
            success, message, report = integrity_manager.validate_migration_integrity(level)
            
            print(f"    Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
            print(f"    Total checks: {report.total_checks}")
            print(f"    Duration: {(report.completed_at - report.started_at).total_seconds():.2f}s")
            print(f"    Checksums generated: {len(report.table_checksums)}")
            
            # Verify that higher levels run more checks
            if level == ValidationLevel.BASIC:
                basic_checks = report.total_checks
            elif level == ValidationLevel.STANDARD:
                standard_checks = report.total_checks
                more_checks = standard_checks >= basic_checks
                print(f"    More checks than BASIC: {'✅' if more_checks else '❌'} ({standard_checks} vs {basic_checks})")
            elif level == ValidationLevel.COMPREHENSIVE:
                comprehensive_checks = report.total_checks
                more_checks = comprehensive_checks >= standard_checks
                print(f"    More checks than STANDARD: {'✅' if more_checks else '❌'} ({comprehensive_checks} vs {standard_checks})")
                has_checksums = len(report.table_checksums) > 0
                print(f"    Checksums generated: {'✅' if has_checksums else '❌'}")
            elif level == ValidationLevel.PARANOID:
                paranoid_checks = report.total_checks
                more_checks = paranoid_checks >= comprehensive_checks
                print(f"    More checks than COMPREHENSIVE: {'✅' if more_checks else '❌'} ({paranoid_checks} vs {comprehensive_checks})")
        
        connection_manager.shutdown()
        
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    try:
        print("🔍 Data Integrity Validation Test Suite")
        print("=" * 60)
        
        test_basic_integrity_validation()
        test_checksum_generation()
        test_corruption_detection()
        test_foreign_key_validation()
        test_checksum_comparison()
        test_validation_levels()
        
        print(f"\n🎉 All data integrity validation tests completed!")
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 