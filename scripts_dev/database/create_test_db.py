#!/usr/bin/env python3
"""
Create test database with simple schema and sample data for optimization testing
"""

import sqlite3
import json
from pathlib import Path

def create_test_database():
    # Create test database with simple schema
    db_path = 'test_optimization.db'
    if Path(db_path).exists():
        Path(db_path).unlink()
        print(f"Removed existing {db_path}")

    print(f"Creating test database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Use simpler migration script instead of full v2.0 schema
        schema_file = Path('data/database/migration_scripts/2024.01.01.001_initial_schema.sql')
        if not schema_file.exists():
            print(f"Schema file not found: {schema_file}")
            return False
            
        print(f"Reading schema from: {schema_file}")
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema_sql = f.read()

        print(f"Schema file size: {len(schema_sql)} characters")

        # Remove the "DOWN" section and anything after it
        schema_sql = schema_sql.split('-- DOWN')[0]

        # Execute schema in parts to handle any issues
        statements = schema_sql.split(';')
        successful_statements = 0
        
        print(f"Found {len(statements)} SQL statements")
        
        for i, stmt in enumerate(statements):
            stmt = stmt.strip()
            if stmt and not stmt.startswith('--'):
                try:
                    cursor.execute(stmt)
                    successful_statements += 1
                    if 'CREATE TABLE' in stmt.upper() or 'PRAGMA' in stmt.upper():
                        print(f"  ✅ Statement {i+1}: {stmt[:60]}...")
                except Exception as e:
                    if 'already exists' not in str(e):
                        print(f"  ❌ Statement {i+1}: {stmt[:60]}...")
                        print(f"     Error: {e}")

        print(f"Executed {successful_statements} SQL statements successfully")
        
        # Check if tables were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"Tables created: {[t[0] for t in tables]}")

        if not tables:
            print("❌ No tables were created. Schema execution failed.")
            return False

        # Insert some test data for optimization testing
        test_data_queries = [
            # Insert test content
            """INSERT INTO content (url, platform, content_type, status, title, description, author, view_count, like_count, created_at, updated_at) VALUES 
            ('https://youtube.com/watch?v=test1', 'youtube', 'video', 'completed', 'Test Video 1', 'Description 1', 'Creator 1', 1000, 50, datetime('now'), datetime('now')),
            ('https://youtube.com/watch?v=test2', 'youtube', 'video', 'pending', 'Test Video 2', 'Description 2', 'Creator 2', 500, 25, datetime('now'), datetime('now')),
            ('https://youtube.com/watch?v=test3', 'youtube', 'video', 'completed', 'Test Video 3', 'Description 3', 'Creator 3', 2000, 100, datetime('now'), datetime('now')),
            ('https://youtube.com/watch?v=test4', 'youtube', 'video', 'failed', 'Test Video 4', 'Description 4', 'Creator 1', 750, 30, datetime('now'), datetime('now')),
            ('https://youtube.com/watch?v=test5', 'youtube', 'video', 'downloading', 'Test Video 5', 'Description 5', 'Creator 2', 1200, 60, datetime('now'), datetime('now'))""",
            
            # Insert test downloads
            """INSERT INTO downloads (content_id, url, quality, format, output_directory, status, progress_percentage, created_at, updated_at) VALUES
            (1, 'https://youtube.com/watch?v=test1', '720p', 'mp4', 'downloads', 'completed', 100.0, datetime('now'), datetime('now')),
            (2, 'https://youtube.com/watch?v=test2', '1080p', 'mp4', 'downloads', 'downloading', 45.5, datetime('now'), datetime('now')),
            (3, 'https://youtube.com/watch?v=test3', '720p', 'mp4', 'downloads', 'queued', 0.0, datetime('now'), datetime('now')),
            (4, 'https://youtube.com/watch?v=test4', '480p', 'mp4', 'downloads', 'failed', 15.0, datetime('now'), datetime('now')),
            (5, 'https://youtube.com/watch?v=test5', '1080p', 'webm', 'downloads', 'downloading', 78.3, datetime('now'), datetime('now'))""",
            
            # Insert test download errors
            """INSERT INTO download_errors (download_id, error_type, error_message, error_code, created_at, updated_at) VALUES
            (4, 'network_error', 'Connection timeout after 30 seconds', 'TIMEOUT', datetime('now'), datetime('now')),
            (2, 'rate_limit', 'Rate limit exceeded, retry after 60 seconds', 'RATE_LIMIT', datetime('now'), datetime('now'))"""
        ]

        for i, data_sql in enumerate(test_data_queries):
            try:
                cursor.execute(data_sql)
                print(f"✅ Inserted test data batch {i+1}")
            except Exception as e:
                print(f'❌ Error inserting data batch {i+1}: {e}')

        conn.commit()
        
        # Verify data was inserted
        cursor.execute("SELECT COUNT(*) FROM content")
        content_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM downloads")
        downloads_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM download_errors")
        errors_count = cursor.fetchone()[0]
        
        print(f"✅ Database created successfully:")
        print(f"  - Content records: {content_count}")
        print(f"  - Download records: {downloads_count}")
        print(f"  - Error records: {errors_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = create_test_database()
    if success:
        print("✅ Test database created successfully!")
    else:
        print("❌ Failed to create test database") 