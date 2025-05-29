#!/usr/bin/env python3

print("Testing imports...")

try:
    from data.database.migration_system.version_detection import VersionManager
    print("✓ Version detection import successful")
except ImportError as e:
    print(f"❌ Version detection import failed: {e}")

try:
    from data.database.migration_system.schema_transformation import SchemaTransformationManager
    print("✓ Schema transformation import successful")
except ImportError as e:
    print(f"❌ Schema transformation import failed: {e}")

try:
    from data.database.migration_system.data_conversion import DataConversionManager
    print("✓ Data conversion import successful")
except ImportError as e:
    print(f"❌ Data conversion import failed: {e}")

try:
    from data.database.migration_system.data_integrity import DataIntegrityManager
    print("✓ Data integrity import successful")
except ImportError as e:
    print(f"❌ Data integrity import failed: {e}")

try:
    from data.database.migration_rollback import MigrationSafetyManager
    print("✓ Rollback mechanism import successful")
except ImportError as e:
    print(f"❌ Rollback mechanism import failed: {e}")

print("Import test complete!") 