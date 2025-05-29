import sys

# Redirect output to file
with open("test_log.txt", "w") as f:
    f.write("Starting migration test\n")
    f.flush()
    
    try:
        f.write("Importing VersionManager...\n")
        f.flush()
        
        from data.database.migration_system.version_detection import VersionManager
        
        f.write("SUCCESS: VersionManager imported\n")
        f.flush()
        
    except Exception as e:
        f.write(f"IMPORT ERROR: {e}\n")
        import traceback
        f.write(f"TRACEBACK:\n{traceback.format_exc()}\n")
        f.flush()
    
    f.write("Test complete\n")

print("Check test_log.txt for results") 