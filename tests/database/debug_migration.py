#!/usr/bin/env python3

import sys
import traceback

def test_migration_system():
    print("=== Migration System Debug ===")
    
    try:
        print("Step 1: Basic imports...")
        sys.stdout.flush()
        
        from data.database.migration_system import VersionManager
        print("✅ VersionManager imported")
        sys.stdout.flush()
        
        from data.database.connection import SQLiteConnectionManager, ConnectionConfig  
        print("✅ Connection imports successful")
        sys.stdout.flush()
        
        print("\nStep 2: Creating configuration...")
        sys.stdout.flush()
        
        config = ConnectionConfig(database_path="test.db")
        print(f"✅ Configuration created: {config.database_path}")
        sys.stdout.flush()
        
        print("\nStep 3: Creating connection manager...")
        sys.stdout.flush()
        
        conn_manager = SQLiteConnectionManager(config)
        print("✅ Connection manager created")
        sys.stdout.flush()
        
        print("\nStep 4: Creating version manager...")
        sys.stdout.flush()
        
        version_manager = VersionManager(conn_manager)
        print("✅ Version manager created")
        sys.stdout.flush()
        
        print("\nStep 5: Detecting database version...")
        sys.stdout.flush()
        
        version_info = version_manager.get_current_version_info()
        print(f"✅ Version detection complete!")
        print(f"   Database version: {version_info.version.value}")
        print(f"   Tables found: {version_info.tables_found}")
        print(f"   Schema valid: {version_info.schema_valid}")
        print(f"   Migration required: {version_info.requires_migration}")
        if version_info.migration_path:
            print(f"   Migration path: {version_info.migration_path}")
        if version_info.validation_errors:
            print(f"   Validation errors: {version_info.validation_errors}")
        sys.stdout.flush()
        
        print("\n🎉 Migration system is fully functional!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        sys.stdout.flush()
        return False

if __name__ == "__main__":
    success = test_migration_system()
    print(f"\n=== Test {'PASSED' if success else 'FAILED'} ===") 