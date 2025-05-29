#!/usr/bin/env python3
"""
Check current database structure
"""

import sqlite3
import os

print("=== Current Database Check ===")

if not os.path.exists("test.db"):
    print("❌ test.db does not exist")
    exit(1)

size = os.path.getsize("test.db")
print(f"📊 Database size: {size} bytes")

try:
    conn = sqlite3.connect("test.db")
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"\n📋 Tables found: {len(tables)}")
    for table in tables:
        print(f"   - {table}")
        
    # Check if it looks like v1.2.1 or v2.0
    if "downloads" in tables and "content" not in tables:
        print("\n🔍 Database appears to be v1.2.1 format")
        # Get sample data
        cursor.execute("SELECT COUNT(*) FROM downloads")
        count = cursor.fetchone()[0]
        print(f"   Downloads table has {count} records")
        
        if count > 0:
            cursor.execute("PRAGMA table_info(downloads)")
            columns = [row[1] for row in cursor.fetchall()]
            print(f"   Columns: {columns}")
            
    elif "content" in tables and "downloads" in tables:
        print("\n🔍 Database appears to be v2.0 format")
        cursor.execute("SELECT COUNT(*) FROM content")
        content_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM downloads") 
        download_count = cursor.fetchone()[0]
        print(f"   Content table: {content_count} records")
        print(f"   Downloads table: {download_count} records")
        
    else:
        print("\n❓ Database format unclear or empty")
        
    conn.close()
    print("\n✅ Database check complete")
    
except Exception as e:
    print(f"❌ Database check failed: {e}")
    import traceback
    traceback.print_exc() 