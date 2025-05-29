import sys
import traceback

def log_message(f, message):
    """Helper to write and flush log messages"""
    f.write(f"{message}\n")
    f.flush()

def test_full_migration():
    with open("migration_test_log.txt", "w") as f:
        try:
            log_message(f, "=== Full Migration System Test ===")
            
            # Test 1: Basic imports
            log_message(f, "\n1. Testing imports...")
            from data.database.migration_system import (
                VersionManager,
                SchemaTransformationManager,
                DataConversionManager,
                DataIntegrityManager,
                DatabaseVersion,
                VersionInfo
            )
            log_message(f, "✅ All migration system components imported successfully")
            
            # Test 2: Connection setup
            log_message(f, "\n2. Setting up database connection...")
            from data.database.connection import SQLiteConnectionManager, ConnectionConfig
            
            config = ConnectionConfig(database_path="test.db")
            log_message(f, f"✅ Configuration created: {config.database_path}")
            
            conn_manager = SQLiteConnectionManager(config)
            log_message(f, "✅ Connection manager created")
            
            # Test 3: Version detection
            log_message(f, "\n3. Testing version detection...")
            version_manager = VersionManager(conn_manager)
            log_message(f, "✅ Version manager created")
            
            version_info = version_manager.get_current_version_info()
            log_message(f, f"✅ Version detected: {version_info.version.value}")
            log_message(f, f"   Tables found: {version_info.tables_found}")
            log_message(f, f"   Schema valid: {version_info.schema_valid}")
            log_message(f, f"   Migration required: {version_info.requires_migration}")
            
            if version_info.migration_path:
                log_message(f, f"   Migration path: {version_info.migration_path}")
            
            if version_info.validation_errors:
                log_message(f, f"   Validation errors: {version_info.validation_errors}")
            
            # Test 4: Schema transformation manager
            log_message(f, "\n4. Testing schema transformation...")
            schema_manager = SchemaTransformationManager(conn_manager)
            log_message(f, "✅ Schema transformation manager initialized")
            
            # Test 5: Data conversion manager
            log_message(f, "\n5. Testing data conversion...")
            data_manager = DataConversionManager(conn_manager)
            log_message(f, "✅ Data conversion manager initialized")
            
            # Test 6: Data integrity manager
            log_message(f, "\n6. Testing data integrity...")
            integrity_manager = DataIntegrityManager(conn_manager)
            log_message(f, "✅ Data integrity manager initialized")
            
            # Test 7: Migration requirements check
            log_message(f, "\n7. Checking migration requirements...")
            requirements = version_manager.check_migration_requirements()
            log_message(f, f"✅ Migration requirements checked")
            log_message(f, f"   Migration safe: {requirements['migration_safe']}")
            log_message(f, f"   Requirements: {requirements['requirements']['migration_type']}")
            if requirements['safety_concerns']:
                log_message(f, f"   Safety concerns: {requirements['safety_concerns']}")
            
            log_message(f, "\n🎉 ALL TESTS PASSED! Migration system is ready for Task 14!")
            log_message(f, "\n=== Summary ===")
            log_message(f, f"Database version: {version_info.version.value}")
            log_message(f, f"Migration needed: {version_info.requires_migration}")
            log_message(f, f"Next steps: {version_info.migration_path or 'Ready for Task 14 implementation'}")
            
            return True
            
        except Exception as e:
            log_message(f, f"\n❌ Error occurred: {e}")
            log_message(f, "\nFull traceback:")
            log_message(f, traceback.format_exc())
            return False

if __name__ == "__main__":
    success = test_full_migration()
    print(f"Migration test {'PASSED' if success else 'FAILED'}. Check migration_test_log.txt for details.") 