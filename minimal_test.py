print("Starting test")

try:
    print("Importing version detection...")
    from data.database.migration_system.version_detection import VersionManager
    print("SUCCESS: VersionManager imported")
except Exception as e:
    print(f"FAILED: {e}")

print("Test complete") 