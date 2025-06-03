#!/usr/bin/env python3
"""
Task 13 → Task 14 Preparation Check
Verify migration system components are properly set up and ready for testing
"""

import sys
import os
from pathlib import Path

print("=== Task 13 → Task 14 Preparation Check ===")

# Environment check
print(f"Python version: {sys.version}")
print(f"Working directory: {os.getcwd()}")

# Database file check
print(f"\n1. Checking current database state...")
if os.path.exists("test.db"):
    size = os.path.getsize("test.db")
    print(f"✅ test.db exists ({size} bytes)")
else:
    print("⚠️  test.db not found")

# Migration system import check
print(f"\n2. Checking migration system components...")
try:
    from data.database.migration_system import (
        VersionManager,
        SchemaTransformationManager,
        DataConversionManager, 
        DataIntegrityManager,
        DatabaseVersion,
        VersionInfo
    )
    print("✅ All migration system components imported successfully")
    
    # Test version detection
    print(f"\n3. Testing version detection...")
    from data.database.connection import SQLiteConnectionManager, ConnectionConfig
    
    config = ConnectionConfig(database_path="test.db")
    conn_manager = SQLiteConnectionManager(config)
    version_manager = VersionManager(conn_manager)
    
    version_info = version_manager.get_current_version_info()
    print(f"✅ Current database version: {version_info.version}")
    print(f"   Tables found: {version_info.tables_found}")
    print(f"   Migration required: {version_info.requires_migration}")
    print(f"   Migration path: {version_info.migration_path}")
    
    print(f"\n4. Testing schema transformation...")
    schema_manager = SchemaTransformationManager(conn_manager)
    print("✅ Schema transformation manager initialized")
    
    print(f"\n5. Testing data conversion...")
    data_manager = DataConversionManager(conn_manager)
    print("✅ Data conversion manager initialized")
    
    print(f"\n6. Testing data integrity...")
    integrity_manager = DataIntegrityManager(conn_manager)
    print("✅ Data integrity manager initialized")
    
    print(f"\n🎉 All migration system components are ready for Task 14!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("   Migration system components may not be properly installed")
except Exception as e:
    print(f"❌ Test error: {e}")
    print("   Migration system may not be properly configured")

print("\n=== Task 14 Preparation Complete ===") 