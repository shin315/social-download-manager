#!/usr/bin/env python3
"""
Create simple test database for optimization testing
"""

import sqlite3
from pathlib import Path

def create_simple_test_db():
    db_path = 'test_optimization.db'
    if Path(db_path).exists():
        Path(db_path).unlink()
        print(f"Removed existing {db_path}")

    print(f"Creating simple test database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create tables with simple schema
        print("Creating tables...")
        
        # Content table
        cursor.execute("""
        CREATE TABLE content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            platform TEXT NOT NULL,
            content_type TEXT NOT NULL DEFAULT 'video',
            status TEXT NOT NULL DEFAULT 'pending',
            title TEXT,
            description TEXT,
            author TEXT,
            view_count INTEGER DEFAULT 0,
            like_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        print("✅ Created content table")
        
        # Downloads table
        cursor.execute("""
        CREATE TABLE downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id INTEGER NOT NULL,
            url TEXT NOT NULL,
            quality TEXT,
            format TEXT,
            output_directory TEXT DEFAULT 'downloads',
            status TEXT NOT NULL DEFAULT 'queued',
            progress_percentage REAL DEFAULT 0.0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (content_id) REFERENCES content(id)
        )
        """)
        print("✅ Created downloads table")
        
        # Download errors table
        cursor.execute("""
        CREATE TABLE download_errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            download_id INTEGER NOT NULL,
            error_type TEXT NOT NULL,
            error_message TEXT NOT NULL,
            error_code TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (download_id) REFERENCES downloads(id)
        )
        """)
        print("✅ Created download_errors table")
        
        # Add some test data
        print("Inserting test data...")
        
        # Insert content
        content_data = [
            ('https://youtube.com/watch?v=test1', 'youtube', 'video', 'completed', 'Test Video 1', 'Description 1', 'Creator 1', 1000, 50),
            ('https://youtube.com/watch?v=test2', 'youtube', 'video', 'pending', 'Test Video 2', 'Description 2', 'Creator 2', 500, 25),
            ('https://youtube.com/watch?v=test3', 'youtube', 'video', 'completed', 'Test Video 3', 'Description 3', 'Creator 3', 2000, 100),
            ('https://youtube.com/watch?v=test4', 'youtube', 'video', 'failed', 'Test Video 4', 'Description 4', 'Creator 1', 750, 30),
            ('https://youtube.com/watch?v=test5', 'youtube', 'video', 'downloading', 'Test Video 5', 'Description 5', 'Creator 2', 1200, 60)
        ]
        
        cursor.executemany("""
        INSERT INTO content (url, platform, content_type, status, title, description, author, view_count, like_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, content_data)
        print("✅ Inserted content data")
        
        # Insert downloads
        download_data = [
            (1, 'https://youtube.com/watch?v=test1', '720p', 'mp4', 'downloads', 'completed', 100.0),
            (2, 'https://youtube.com/watch?v=test2', '1080p', 'mp4', 'downloads', 'downloading', 45.5),
            (3, 'https://youtube.com/watch?v=test3', '720p', 'mp4', 'downloads', 'queued', 0.0),
            (4, 'https://youtube.com/watch?v=test4', '480p', 'mp4', 'downloads', 'failed', 15.0),
            (5, 'https://youtube.com/watch?v=test5', '1080p', 'webm', 'downloads', 'downloading', 78.3)
        ]
        
        cursor.executemany("""
        INSERT INTO downloads (content_id, url, quality, format, output_directory, status, progress_percentage)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, download_data)
        print("✅ Inserted download data")
        
        # Insert errors
        error_data = [
            (4, 'network_error', 'Connection timeout after 30 seconds', 'TIMEOUT'),
            (2, 'rate_limit', 'Rate limit exceeded, retry after 60 seconds', 'RATE_LIMIT')
        ]
        
        cursor.executemany("""
        INSERT INTO download_errors (download_id, error_type, error_message, error_code)
        VALUES (?, ?, ?, ?)
        """, error_data)
        print("✅ Inserted error data")
        
        conn.commit()
        
        # Verify data
        cursor.execute("SELECT COUNT(*) FROM content")
        content_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM downloads")
        downloads_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM download_errors")
        errors_count = cursor.fetchone()[0]
        
        print(f"\n✅ Database created successfully:")
        print(f"  - Content records: {content_count}")
        print(f"  - Download records: {downloads_count}")
        print(f"  - Error records: {errors_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = create_simple_test_db()
    if success:
        print("✅ Test database ready for optimization testing!")
    else:
        print("❌ Failed to create test database") 