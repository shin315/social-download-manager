#!/usr/bin/env python3
"""
Simple migration system test
"""

print("=== Simple Migration Test ===")

try:
    print("1. Testing imports...")
    from data.database.migration_system import VersionManager
    print("✅ VersionManager imported")
    
    from data.database.connection import SQLiteConnectionManager, ConnectionConfig
    print("✅ Connection components imported")
    
    print("\n2. Creating connection...")
    config = ConnectionConfig(database_path="test.db")
    print(f"✅ Config created: {config.database_path}")
    
    conn_manager = SQLiteConnectionManager(config)
    print("✅ Connection manager created")
    
    print("\n3. Creating version manager...")
    version_manager = VersionManager(conn_manager)
    print("✅ Version manager created")
    
    print("\n4. Detecting version...")
    version_info = version_manager.get_current_version_info()
    print(f"✅ Version detected: {version_info.version}")
    print(f"   Tables: {version_info.tables_found}")
    print(f"   Migration needed: {version_info.requires_migration}")
    
    print("\n🎉 Migration system is working!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Test Complete ===") 