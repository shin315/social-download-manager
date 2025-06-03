#!/usr/bin/env python3
"""
Test Script for Database Version Detection System

This script tests the version detection capabilities for different database states.
"""

import sys
import os
import tempfile
import sqlite3
import json
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, '.')

from data.database.connection import ConnectionConfig, SQLiteConnectionManager
from data.database.version_detection import VersionManager, VersionDetector, DatabaseVersion


def setup_empty_database(db_path: str):
    """Create an empty database file"""
    conn = sqlite3.connect(db_path)
    conn.close()
    print(f"✓ Created empty database: {db_path}")


def setup_v1_2_1_database(db_path: str):
    """Create a v1.2.1 style database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create v1.2.1 downloads table
    cursor.execute('''
        CREATE TABLE downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            title TEXT NOT NULL,
            filepath TEXT NOT NULL,
            quality TEXT,
            format TEXT,
            duration INTEGER,
            filesize TEXT,
            status TEXT,
            download_date TEXT,
            metadata TEXT
        )
    ''')
    
    # Add some sample data
    sample_downloads = [
        {
            'url': 'https://tiktok.com/@user/video/123',
            'title': 'Sample TikTok Video',
            'filepath': '/downloads/sample_video.mp4',
            'quality': '1080p',
            'format': 'mp4',
            'duration': 30,
            'filesize': '5.2MB',
            'status': 'Success',
            'download_date': '2024/12/28 15:30',
            'metadata': json.dumps({
                'caption': 'Sample video caption',
                'hashtags': ['#viral', '#funny'],
                'creator': '@sampleuser',
                'thumbnail': 'https://example.com/thumb.jpg'
            })
        },
        {
            'url': 'https://tiktok.com/@user/video/456',
            'title': 'Another TikTok Video',
            'filepath': '/downloads/another_video.mp4',
            'quality': '720p',
            'format': 'mp4',
            'duration': 15,
            'filesize': '2.8MB',
            'status': 'Success',
            'download_date': '2024/12/28 16:45',
            'metadata': json.dumps({
                'caption': 'Another sample caption',
                'hashtags': ['#trending'],
                'creator': '@anotheruser'
            })
        }
    ]
    
    for download in sample_downloads:
        cursor.execute('''
            INSERT INTO downloads (url, title, filepath, quality, format, duration, 
                                   filesize, status, download_date, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            download['url'], download['title'], download['filepath'],
            download['quality'], download['format'], download['duration'],
            download['filesize'], download['status'], download['download_date'],
            download['metadata']
        ))
    
    conn.commit()
    conn.close()
    print(f"✓ Created v1.2.1 database with {len(sample_downloads)} sample records: {db_path}")


def setup_v2_0_database(db_path: str):
    """Create a v2.0 style database with migration tracking"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create schema_migrations table
    cursor.execute('''
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
    ''')
    
    # Create v2.0 content table
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
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    ''')
    
    # Create v2.0 downloads table
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
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (content_id) REFERENCES content(id)
        )
    ''')
    
    # Create other v2.0 tables
    cursor.execute('''
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
    ''')
    
    cursor.execute('''
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
    ''')
    
    # Add migration record
    cursor.execute('''
        INSERT INTO schema_migrations (version, name, checksum, status, executed_at, execution_time_ms)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        '2024.12.28.001',
        'initial_v2_schema',
        'abc123def456',
        'completed',
        '2024-12-28T10:00:00Z',
        1500
    ))
    
    conn.commit()
    conn.close()
    print(f"✓ Created v2.0 database with migration tracking: {db_path}")


def setup_corrupted_database(db_path: str):
    """Create a corrupted/unknown database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create some random tables that don't match any known schema
    cursor.execute('''
        CREATE TABLE random_table (
            id INTEGER PRIMARY KEY,
            random_data TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE another_table (
            uuid TEXT PRIMARY KEY,
            weird_column BLOB
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"✓ Created unknown/corrupted database: {db_path}")


def test_version_detection():
    """Test version detection for all database types"""
    
    print("🔍 Testing Database Version Detection System")
    print("=" * 60)
    
    test_cases = [
        ("Empty Database", setup_empty_database, DatabaseVersion.EMPTY),
        ("v1.2.1 Database", setup_v1_2_1_database, DatabaseVersion.V1_2_1),
        ("v2.0 Database", setup_v2_0_database, DatabaseVersion.V2_0_0),
        ("Unknown Database", setup_corrupted_database, DatabaseVersion.UNKNOWN)
    ]
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        for test_name, setup_func, expected_version in test_cases:
            print(f"\n📋 Testing: {test_name}")
            print("-" * 40)
            
            # Setup test database
            db_path = os.path.join(temp_dir, f"test_{test_name.lower().replace(' ', '_')}.db")
            setup_func(db_path)
            
            # Test version detection
            config = ConnectionConfig(database_path=db_path)
            connection_manager = SQLiteConnectionManager(config)
            
            try:
                connection_manager.initialize()
                version_manager = VersionManager(connection_manager)
                
                # Get version info
                version_info = version_manager.get_current_version_info()
                
                print(f"  Detected Version: {version_info.version.value}")
                print(f"  Schema Valid: {version_info.schema_valid}")
                print(f"  Tables Found: {version_info.tables_found}")
                print(f"  Requires Migration: {version_info.requires_migration}")
                
                if version_info.migration_path:
                    print(f"  Migration Path: {version_info.migration_path}")
                
                if version_info.validation_errors:
                    print(f"  Validation Errors: {version_info.validation_errors}")
                
                if version_info.migration_records:
                    print(f"  Migration Records: {version_info.migration_records}")
                
                # Check migration requirements
                requirements = version_manager.check_migration_requirements()
                print(f"  Migration Safe: {requirements['migration_safe']}")
                
                if requirements['safety_concerns']:
                    print(f"  Safety Concerns: {requirements['safety_concerns']}")
                
                # Verify expected result
                if version_info.version == expected_version:
                    print(f"  ✅ PASS: Correctly detected {expected_version.value}")
                else:
                    print(f"  ❌ FAIL: Expected {expected_version.value}, got {version_info.version.value}")
                
            except Exception as e:
                print(f"  ❌ ERROR: {e}")
                import traceback
                traceback.print_exc()
            
            finally:
                connection_manager.shutdown()
    
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    print(f"\n✅ Version detection testing complete!")


def test_migration_tracking():
    """Test migration tracking table creation"""
    print(f"\n🏗️ Testing Migration Tracking Creation")
    print("-" * 40)
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "migration_tracking_test.db")
    
    try:
        # Start with empty database
        setup_empty_database(db_path)
        
        config = ConnectionConfig(database_path=db_path)
        connection_manager = SQLiteConnectionManager(config)
        
        connection_manager.initialize()
        version_manager = VersionManager(connection_manager)
        
        # Create migration tracking
        success = version_manager.create_migration_tracking()
        print(f"  Migration tracking creation: {'✅ SUCCESS' if success else '❌ FAILED'}")
        
        # Verify it was created
        version_info = version_manager.get_current_version_info()
        has_migration_table = 'schema_migrations' in version_info.tables_found
        print(f"  Migration table exists: {'✅ YES' if has_migration_table else '❌ NO'}")
        
        connection_manager.shutdown()
        
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    try:
        test_version_detection()
        test_migration_tracking()
        
        print(f"\n🎉 All tests completed!")
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 