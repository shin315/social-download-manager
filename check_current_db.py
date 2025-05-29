import sqlite3
import os

def check_database():
    db_path = "test.db"
    
    print(f"🔍 Starting database check...")
    print(f"📁 Current directory: {os.getcwd()}")
    print(f"📂 Checking for: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"❌ Database file {db_path} not found")
        return
    
    file_size = os.path.getsize(db_path)
    print(f"📊 Database file exists, size: {file_size} bytes")
    
    try:
        print("🔌 Connecting to database...")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("📋 Querying tables...")
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        
        print(f"\n📋 Found {len(tables)} tables:")
        for table in tables:
            print(f"  - {table[0]}")
        
        if len(tables) == 0:
            print("⚠️ Database appears to be empty (no tables found)")
            # Try to see what's in sqlite_master
            cursor.execute("SELECT * FROM sqlite_master")
            all_objects = cursor.fetchall()
            print(f"📝 All objects in sqlite_master: {len(all_objects)}")
            for obj in all_objects:
                print(f"    {obj}")
        
        # Check each table structure
        for table in tables:
            table_name = table[0]
            print(f"\n🔧 Structure of table '{table_name}':")
            
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            for col in columns:
                col_id, name, data_type, not_null, default_val, primary_key = col
                pk_str = " (PRIMARY KEY)" if primary_key else ""
                null_str = " NOT NULL" if not_null else ""
                default_str = f" DEFAULT {default_val}" if default_val else ""
                print(f"    {name}: {data_type}{null_str}{default_str}{pk_str}")
            
            # Check row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"    📊 Row count: {count}")
        
        # Check for schema_migrations table specifically
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'")
        migration_table = cursor.fetchone()
        
        if migration_table:
            print(f"\n🏗️ Migration tracking enabled")
            cursor.execute("SELECT version, executed_at, success FROM schema_migrations ORDER BY version")
            migrations = cursor.fetchall()
            
            if migrations:
                print(f"📈 Migration history ({len(migrations)} entries):")
                for version, executed_at, success in migrations:
                    status = "✅" if success else "❌"
                    print(f"    {status} {version} - {executed_at}")
            else:
                print("📭 No migrations executed yet")
        else:
            print(f"\n⚠️ No migration tracking table found")
        
        conn.close()
        print(f"\n✅ Database inspection complete")
        
    except Exception as e:
        print(f"❌ Error inspecting database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_database() 