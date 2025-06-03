import sys
import os
import tempfile
sys.path.insert(0, '.')

print("=== Database Connection Manager Debug ===")

try:
    from data.database.connection import ConnectionConfig, SQLiteConnectionManager
    print("✓ Import successful")
    
    # Create temp db path
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test.db")
    print(f"✓ Using db path: {db_path}")
    
    # Test basic config
    config = ConnectionConfig(database_path=db_path, max_pool_size=2, min_pool_size=1)
    print(f"✓ Config created: {config.database_path}")
    
    # Test manager creation
    manager = SQLiteConnectionManager(config)
    print(f"✓ Manager created, state: {manager._state}")
    
    # Test initialization
    print("⏳ Attempting initialization...")
    result = manager.initialize()
    print(f"✓ Init result: {result}, state: {manager._state}")
    
    if result:
        # Test basic functionality
        health = manager.health_check()
        print(f"✓ Health check: {health}")
        
        stats = manager.get_stats()
        print(f"✓ Stats: {stats.total_connections} total, {stats.idle_connections} idle")
        
        # Test shutdown
        shutdown_result = manager.shutdown()
        print(f"✓ Shutdown: {shutdown_result}")
    
    print("=== Test complete ===")
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc() 