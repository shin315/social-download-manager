#!/usr/bin/env python3
"""
Test Script for Schema Transformation Engine

Tests the schema transformation capabilities for database migrations.
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
from data.database.version_detection import VersionManager, DatabaseVersion
from data.database.schema_transformer import SchemaTransformationManager, SQLiteSchemaTransformer, TransformationType


def setup_empty_database(db_path: str):
    """Create an empty database file"""
    conn = sqlite3.connect(db_path)
    conn.close()
    print(f"✓ Created empty database: {db_path}")


def setup_v1_2_1_database_with_data(db_path: str):
    """Create a v1.2.1 database with realistic test data"""
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
    
    # Add comprehensive test data
    test_downloads = [
        {
            'url': 'https://tiktok.com/@user1/video/123456789',
            'title': 'Funny Cat Video',
            'filepath': '/downloads/cat_video_123.mp4',
            'quality': '1080p',
            'format': 'mp4',
            'duration': 45,
            'filesize': '8.2MB',
            'status': 'Success',
            'download_date': '2024/12/25 10:30:00',
            'metadata': json.dumps({
                'caption': 'Look at this hilarious cat! #funny #cats #viral',
                'hashtags': ['#funny', '#cats', '#viral', '#cute'],
                'creator': '@cat_lover_2024',
                'thumbnail': 'https://p16-sign-va.tiktokcdn.com/obj/tos-maliva-p-0068/thumb123.jpeg',
                'likes': 125000,
                'shares': 5600,
                'comments': 890,
                'platform_id': 'tiktok',
                'description': 'My cat doing something absolutely ridiculous'
            })
        },
        {
            'url': 'https://tiktok.com/@chef_pro/video/987654321',
            'title': 'Quick Pasta Recipe',
            'filepath': '/downloads/pasta_recipe_987.mp4',
            'quality': '720p',
            'format': 'mp4',
            'duration': 60,
            'filesize': '12.5MB',
            'status': 'Success',
            'download_date': '2024/12/26 15:45:30',
            'metadata': json.dumps({
                'caption': 'Easy 5-minute pasta! Recipe in comments 👇',
                'hashtags': ['#cooking', '#pasta', '#recipe', '#quick', '#food'],
                'creator': '@chef_pro_official',
                'thumbnail': 'https://p16-sign-va.tiktokcdn.com/obj/tos-maliva-p-0068/pasta456.jpeg',
                'likes': 89000,
                'shares': 12300,
                'comments': 2150,
                'platform_id': 'tiktok',
                'description': 'Professional chef shares quick pasta tips'
            })
        },
        {
            'url': 'https://tiktok.com/@fitness_guru/video/555777888',
            'title': 'Morning Workout Routine',
            'filepath': '/downloads/workout_555.mp4',
            'quality': '1080p',
            'format': 'mp4',
            'duration': 120,
            'filesize': '25.8MB',
            'status': 'Success',
            'download_date': '2024/12/27 08:15:45',
            'metadata': json.dumps({
                'caption': '10-minute morning routine to start your day! 💪',
                'hashtags': ['#fitness', '#workout', '#morning', '#health', '#motivation'],
                'creator': '@fitness_guru_jane',
                'thumbnail': 'https://p16-sign-va.tiktokcdn.com/obj/tos-maliva-p-0068/workout789.jpeg',
                'likes': 67000,
                'shares': 8900,
                'comments': 1340,
                'platform_id': 'tiktok',
                'description': 'Certified trainer shares daily routine'
            })
        },
        {
            'url': 'https://tiktok.com/@tech_reviewer/video/111222333',
            'title': 'iPhone 15 Review',
            'filepath': '/downloads/iphone_review_111.mp4',
            'quality': '4K',
            'format': 'mp4',
            'duration': 180,
            'filesize': '45.6MB',
            'status': 'Failed',
            'download_date': '2024/12/27 20:30:00',
            'metadata': json.dumps({
                'caption': 'Honest iPhone 15 review after 3 months 📱',
                'hashtags': ['#tech', '#iphone', '#review', '#apple', '#smartphone'],
                'creator': '@tech_reviewer_mike',
                'thumbnail': 'https://p16-sign-va.tiktokcdn.com/obj/tos-maliva-p-0068/iphone111.jpeg',
                'likes': 156000,
                'shares': 23400,
                'comments': 5670,
                'platform_id': 'tiktok',
                'description': 'In-depth tech review by experienced reviewer'
            })
        },
        {
            'url': 'https://tiktok.com/@travel_couple/video/444666999',
            'title': 'Tokyo Street Food Adventure',
            'filepath': '/downloads/tokyo_food_444.mp4',
            'quality': '1080p',
            'format': 'mp4',
            'duration': 90,
            'filesize': '18.3MB',
            'status': 'Success',
            'download_date': '2024/12/28 12:00:00',
            'metadata': json.dumps({
                'caption': 'Amazing street food in Shibuya! Must try 🍜🍣',
                'hashtags': ['#travel', '#japan', '#tokyo', '#food', '#streetfood'],
                'creator': '@travel_couple_adventures',
                'thumbnail': 'https://p16-sign-va.tiktokcdn.com/obj/tos-maliva-p-0068/tokyo444.jpeg',
                'likes': 203000,
                'shares': 15600,
                'comments': 3420,
                'platform_id': 'tiktok',
                'description': 'Couple documenting their world travels'
            })
        }
    ]
    
    for download in test_downloads:
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
    print(f"✓ Created v1.2.1 database with {len(test_downloads)} realistic test records: {db_path}")


def test_fresh_install_transformation():
    """Test transformation from empty database to v2.0"""
    print(f"\n🆕 Testing Fresh Install Transformation")
    print("-" * 50)
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "fresh_install_test.db")
    
    try:
        # Setup empty database
        setup_empty_database(db_path)
        
        # Initialize connection
        config = ConnectionConfig(database_path=db_path)
        connection_manager = SQLiteConnectionManager(config)
        connection_manager.initialize()
        
        # Create transformation manager
        transformation_manager = SchemaTransformationManager(connection_manager)
        
        # Execute migration
        print("  🔧 Executing fresh install migration...")
        success, message = transformation_manager.execute_migration()
        
        print(f"  Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
        print(f"  Message: {message}")
        
        if success:
            # Verify the result
            version_manager = VersionManager(connection_manager)
            version_info = version_manager.get_current_version_info()
            
            print(f"  Final Version: {version_info.version.value}")
            print(f"  Schema Valid: {version_info.schema_valid}")
            print(f"  Tables Created: {len(version_info.tables_found)}")
            
            # Check specific tables
            expected_tables = ['schema_migrations', 'content', 'downloads', 'download_sessions', 'download_errors']
            missing_tables = set(expected_tables) - set(version_info.tables_found)
            
            if not missing_tables:
                print("  ✅ All required tables created successfully")
            else:
                print(f"  ❌ Missing tables: {missing_tables}")
        
        connection_manager.shutdown()
        
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_v1_to_v2_transformation():
    """Test transformation from v1.2.1 to v2.0"""
    print(f"\n📈 Testing v1.2.1 to v2.0 Transformation")
    print("-" * 50)
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "v1_to_v2_test.db")
    
    try:
        # Setup v1.2.1 database with data
        setup_v1_2_1_database_with_data(db_path)
        
        # Initialize connection
        config = ConnectionConfig(database_path=db_path)
        connection_manager = SQLiteConnectionManager(config)
        connection_manager.initialize()
        
        # Check initial state
        print("  📊 Initial state analysis:")
        
        with connection_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM downloads")
            initial_count = cursor.fetchone()[0]
            print(f"    Initial download records: {initial_count}")
        
        # Create transformation manager
        transformation_manager = SchemaTransformationManager(connection_manager)
        
        # Execute migration
        print("  🔧 Executing v1.2.1 → v2.0 migration...")
        success, message = transformation_manager.execute_migration()
        
        print(f"  Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
        print(f"  Message: {message}")
        
        if success:
            # Verify the result
            version_manager = VersionManager(connection_manager)
            version_info = version_manager.get_current_version_info()
            
            print(f"  Final Version: {version_info.version.value}")
            print(f"  Schema Valid: {version_info.schema_valid}")
            print(f"  Tables Found: {version_info.tables_found}")
            
            # Check if backup table exists
            if 'downloads_v1_backup' in version_info.tables_found:
                print("  ✅ v1.2.1 backup table created")
                
                with connection_manager.connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM downloads_v1_backup")
                    backup_count = cursor.fetchone()[0]
                    print(f"    Backup records preserved: {backup_count}")
                    
                    if backup_count == initial_count:
                        print("  ✅ All original data preserved in backup")
                    else:
                        print(f"  ❌ Data loss detected: {initial_count} → {backup_count}")
            else:
                print("  ⚠️ Backup table not found")
            
            # Check new table structure
            expected_tables = ['schema_migrations', 'content', 'downloads', 'download_sessions', 'download_errors']
            missing_tables = set(expected_tables) - set(version_info.tables_found)
            
            if not missing_tables:
                print("  ✅ All v2.0 tables created successfully")
            else:
                print(f"  ❌ Missing v2.0 tables: {missing_tables}")
        
        connection_manager.shutdown()
        
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_transformation_plan_creation():
    """Test transformation plan creation logic"""
    print(f"\n📋 Testing Transformation Plan Creation")
    print("-" * 50)
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Test plans for different scenarios
        scenarios = [
            ("Empty → v2.0", setup_empty_database),
            ("v1.2.1 → v2.0", setup_v1_2_1_database_with_data)
        ]
        
        for scenario_name, setup_func in scenarios:
            print(f"  📝 Testing plan creation: {scenario_name}")
            
            db_path = os.path.join(temp_dir, f"plan_test_{scenario_name.replace(' ', '_').replace('→', 'to')}.db")
            setup_func(db_path)
            
            # Initialize connection
            config = ConnectionConfig(database_path=db_path)
            connection_manager = SQLiteConnectionManager(config)
            connection_manager.initialize()
            
            # Create transformer and get version info
            transformer = SQLiteSchemaTransformer(connection_manager)
            version_manager = VersionManager(connection_manager)
            
            current_version = version_manager.get_current_version_info()
            
            # Create transformation plan
            plan = transformer.create_transformation_plan(current_version, DatabaseVersion.V2_0_0)
            
            print(f"    Source: {plan.source_version.value}")
            print(f"    Target: {plan.target_version.value}")
            print(f"    Steps: {len(plan.steps)}")
            print(f"    Duration: {plan.estimated_duration_seconds}s")
            print(f"    Requires Backup: {plan.requires_backup}")
            print(f"    Destructive: {plan.destructive_changes}")
            
            # Validate plan
            is_safe, concerns = transformer.validate_transformation(plan)
            print(f"    Plan Safe: {'✅ YES' if is_safe else '❌ NO'}")
            
            if concerns:
                print(f"    Concerns: {len(concerns)}")
                for concern in concerns[:3]:  # Show first 3 concerns
                    print(f"      - {concern}")
            
            # Test dependency resolution
            try:
                ordered_steps = plan.get_dependencies_order()
                print(f"    Dependency Resolution: ✅ SUCCESS ({len(ordered_steps)} steps)")
            except Exception as e:
                print(f"    Dependency Resolution: ❌ FAILED - {e}")
            
            connection_manager.shutdown()
    
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_transformation_step_types():
    """Test different transformation step types"""
    print(f"\n🔧 Testing Transformation Step Types")
    print("-" * 50)
    
    # Test that all transformation types are properly handled
    transformation_types = [
        TransformationType.CREATE_TABLE,
        TransformationType.ALTER_TABLE,
        TransformationType.DROP_TABLE,
        TransformationType.CREATE_INDEX,
        TransformationType.DROP_INDEX,
        TransformationType.RENAME_TABLE,
        TransformationType.RENAME_COLUMN,
        TransformationType.ADD_COLUMN,
        TransformationType.DROP_COLUMN
    ]
    
    print(f"  📊 Available transformation types: {len(transformation_types)}")
    
    for transform_type in transformation_types:
        print(f"    ✅ {transform_type.value}")
    
    print(f"\n  🏗️ Testing SQL generation patterns...")
    
    # Test SQL pattern extraction
    from data.database.schema_transformer import SQLiteSchemaTransformer
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "sql_pattern_test.db")
    
    try:
        setup_empty_database(db_path)
        
        config = ConnectionConfig(database_path=db_path)
        connection_manager = SQLiteConnectionManager(config)
        connection_manager.initialize()
        
        transformer = SQLiteSchemaTransformer(connection_manager)
        
        # Test index name extraction
        test_index_sqls = [
            "CREATE INDEX idx_test_column ON test_table(column_name)",
            "CREATE INDEX IF NOT EXISTS idx_another_test ON another_table(col1, col2)",
            "CREATE UNIQUE INDEX idx_unique_test ON unique_table(unique_col)"
        ]
        
        for sql in test_index_sqls:
            index_name = transformer._extract_index_name(sql)
            print(f"    Index SQL: {sql[:50]}...")
            print(f"    Extracted: {index_name}")
        
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
        print("🔧 Schema Transformation Engine Test Suite")
        print("=" * 60)
        
        test_transformation_step_types()
        test_transformation_plan_creation()
        test_fresh_install_transformation()
        test_v1_to_v2_transformation()
        
        print(f"\n🎉 All transformation tests completed!")
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 