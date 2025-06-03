#!/usr/bin/env python3
"""
Test Current Database Version Detection

Check the version of the current test.db database.
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, '.')

from data.database.connection import ConnectionConfig, SQLiteConnectionManager
from data.database.version_detection import VersionManager


def test_current_database():
    """Test version detection on current database"""
    
    db_path = "test.db"
    
    print("🔍 Testing Current Database Version Detection")
    print("=" * 50)
    print(f"Database file: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"❌ Database file {db_path} not found")
        return
    
    file_size = os.path.getsize(db_path)
    print(f"File size: {file_size} bytes")
    
    try:
        config = ConnectionConfig(database_path=db_path)
        connection_manager = SQLiteConnectionManager(config)
        
        connection_manager.initialize()
        version_manager = VersionManager(connection_manager)
        
        # Get version info
        print(f"\n📊 Version Analysis:")
        print("-" * 30)
        
        version_info = version_manager.get_current_version_info()
        
        print(f"🔢 Detected Version: {version_info.version.value}")
        print(f"📋 Schema Valid: {version_info.schema_valid}")
        print(f"📂 Tables Found: {version_info.tables_found}")
        print(f"🔄 Requires Migration: {version_info.requires_migration}")
        print(f"⏰ Detected At: {version_info.detected_at}")
        
        if version_info.version_string:
            print(f"🏷️ Version String: {version_info.version_string}")
        
        if version_info.migration_path:
            print(f"🛤️ Migration Path: {version_info.migration_path}")
        
        if version_info.validation_errors:
            print(f"❌ Validation Errors:")
            for error in version_info.validation_errors:
                print(f"   - {error}")
        
        if version_info.migration_records:
            print(f"📈 Migration Records:")
            for record in version_info.migration_records:
                print(f"   - {record}")
        
        if version_info.last_migration:
            print(f"🏁 Last Migration: {version_info.last_migration}")
        
        # Check migration requirements
        print(f"\n📋 Migration Requirements:")
        print("-" * 30)
        
        requirements = version_manager.check_migration_requirements()
        
        print(f"🔄 Requires Migration: {requirements['requirements']['requires_migration']}")
        print(f"📊 Source Version: {requirements['requirements']['source_version']}")
        print(f"🎯 Target Version: {requirements['requirements']['target_version']}")
        print(f"🛠️ Migration Type: {requirements['requirements']['migration_type']}")
        print(f"⏱️ Estimated Duration: {requirements['requirements']['estimated_duration']}")
        print(f"💾 Data Backup Required: {requirements['requirements']['data_backup_required']}")
        print(f"⚠️ Destructive Changes: {requirements['requirements']['destructive_changes']}")
        print(f"🔒 Migration Safe: {requirements['migration_safe']}")
        
        if requirements['requirements']['steps']:
            print(f"📝 Steps:")
            for i, step in enumerate(requirements['requirements']['steps'], 1):
                print(f"   {i}. {step}")
        
        if requirements['safety_concerns']:
            print(f"⚠️ Safety Concerns:")
            for concern in requirements['safety_concerns']:
                print(f"   - {concern}")
        
        connection_manager.shutdown()
        
        print(f"\n✅ Analysis complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_current_database() 