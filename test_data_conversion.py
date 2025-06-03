#!/usr/bin/env python3
"""
Test Script for Data Conversion Logic

Tests the data conversion capabilities for migrating v1.2.1 data to v2.0 normalized structure.
"""

import sys
import os
import tempfile
import sqlite3
import json
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, '.')

from data.database.connection import ConnectionConfig, SQLiteConnectionManager
from data.database.version_detection import VersionManager, DatabaseVersion
from data.database.schema_transformer import SchemaTransformationManager
from data.database.data_converter import (
    DataConversionManager, SQLiteDataConverter, PlatformDetector, 
    MetadataParser, V1DownloadRecord, ConversionStats
)


def setup_v1_to_v2_migrated_database(db_path: str):
    """Create a database that has been schema-migrated but needs data conversion"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create v1.2.1 downloads table
    cursor.execute('''
        CREATE TABLE downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            title TEXT NOT NULL,
            filepath TEXT NOT NULL,
            quality TEXT,
            format TEXT,
            duration INTEGER,
            filesize TEXT,
            status TEXT,
            download_date TEXT,
            metadata TEXT
        )
    ''')
    
    # Add comprehensive test data with realistic scenarios
    test_downloads = [
        {
            'url': 'https://tiktok.com/@cat_lover_2024/video/123456789',
            'title': 'Funny Cat Video',
            'filepath': '/downloads/cat_video_123.mp4',
            'quality': '1080p',
            'format': 'mp4',
            'duration': 45,
            'filesize': '8.2MB',
            'status': 'Success',
            'download_date': '2024/12/25 10:30:00',
            'metadata': json.dumps({
                'caption': 'Look at this hilarious cat! #funny #cats #viral',
                'hashtags': ['#funny', '#cats', '#viral', '#cute'],
                'creator': '@cat_lover_2024',
                'thumbnail': 'https://p16-sign-va.tiktokcdn.com/obj/tos-maliva-p-0068/thumb123.jpeg',
                'likes': 125000,
                'shares': 5600,
                'comments': 890,
                'platform_id': 'tiktok',
                'description': 'My cat doing something absolutely ridiculous'
            })
        },
        {
            'url': 'https://youtube.com/watch?v=dQw4w9WgXcQ',
            'title': 'Never Gonna Give You Up',
            'filepath': '/downloads/rick_roll.mp4',
            'quality': '720p',
            'format': 'mp4',
            'duration': 212,
            'filesize': '25.4MB',
            'status': 'Success',
            'download_date': '2024/12/26 15:45:30',
            'metadata': json.dumps({
                'description': 'The official Rick Astley music video',
                'creator': 'Rick Astley',
                'thumbnail': 'https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg',
                'views': 1200000000,
                'likes': 15000000,
                'channel_url': 'https://youtube.com/c/RickAstley'
            })
        },
        {
            'url': 'https://instagram.com/p/ABC123DEF456/',
            'title': 'Beautiful Sunset',
            'filepath': '/downloads/sunset_ig.mp4',
            'quality': '1080p',
            'format': 'mp4',
            'duration': 30,
            'filesize': '12.8MB',
            'status': 'Success',
            'download_date': '2024/12/27 08:15:45',
            'metadata': json.dumps({
                'caption': 'Amazing sunset from the beach 🌅 #sunset #beach #nature',
                'author': '@nature_photographer',
                'likes': 5600,
                'comments': 234,
                'hashtags': ['#sunset', '#beach', '#nature']
            })
        },
        {
            'url': 'https://vm.tiktok.com/ZMJR8k2Nf/',
            'title': 'Dance Challenge',
            'filepath': '/downloads/dance_challenge.mp4',
            'quality': '720p',
            'format': 'mp4',
            'duration': 15,
            'filesize': '3.2MB',
            'status': 'Failed',
            'download_date': '2024/12/27 20:30:00',
            'metadata': json.dumps({
                'caption': 'New dance trend! Try it out 💃',
                'creator': '@dance_queen_99',
                'likes': 89000,
                'shares': 12000
            })
        },
        {
            'url': 'https://unknown-platform.com/video/xyz789',
            'title': 'Unknown Platform Video',
            'filepath': '/downloads/unknown_video.mp4',
            'quality': '480p',
            'format': 'mp4',
            'duration': 60,
            'filesize': '15.6MB',
            'status': 'Success',
            'download_date': '2024/12/28 12:00:00',
            'metadata': json.dumps({
                'title': 'Test video from unknown platform',
                'uploader': 'TestUser123'
            })
        },
        {
            'url': 'https://tiktok.com/@cat_lover_2024/video/123456789',  # Duplicate URL
            'title': 'Funny Cat Video (Duplicate)',
            'filepath': '/downloads/cat_video_duplicate.mp4',
            'quality': '720p',  # Different quality
            'format': 'mp4',
            'duration': 45,
            'filesize': '6.1MB',
            'status': 'Success',
            'download_date': '2024/12/29 09:15:00',
            'metadata': json.dumps({
                'caption': 'Same video, different download',
                'creator': '@cat_lover_2024'
            })
        }
    ]
    
    for download in test_downloads:
        cursor.execute('''
            INSERT INTO downloads (url, title, filepath, quality, format, duration, 
                                   filesize, status, download_date, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            download['url'], download['title'], download['filepath'],
            download['quality'], download['format'], download['duration'],
            download['filesize'], download['status'], download['download_date'],
            download['metadata']
        ))
    
    conn.commit()
    conn.close()
    
    # Now perform schema migration to create v2.0 structure
    config = ConnectionConfig(database_path=db_path)
    connection_manager = SQLiteConnectionManager(config)
    connection_manager.initialize()
    
    transformation_manager = SchemaTransformationManager(connection_manager)
    success, message = transformation_manager.execute_migration()
    
    connection_manager.shutdown()
    
    if not success:
        raise Exception(f"Failed to setup migrated database: {message}")
    
    print(f"✓ Created v1→v2 migrated database with {len(test_downloads)} test records: {db_path}")
    return len(test_downloads)


def test_platform_detection():
    """Test platform detection and content ID extraction"""
    print(f"\n🔍 Testing Platform Detection")
    print("-" * 50)
    
    test_urls = [
        ('https://tiktok.com/@user123/video/7234567890123456789', 'tiktok', '7234567890123456789'),
        ('https://vm.tiktok.com/ZMJR8k2Nf/', 'tiktok', 'ZMJR8k2Nf'),
        ('https://youtube.com/watch?v=dQw4w9WgXcQ', 'youtube', 'dQw4w9WgXcQ'),
        ('https://youtu.be/dQw4w9WgXcQ', 'youtube', 'dQw4w9WgXcQ'),
        ('https://instagram.com/p/ABC123DEF456/', 'instagram', 'ABC123DEF456'),
        ('https://instagram.com/reel/XYZ789UVW012/', 'instagram', 'XYZ789UVW012'),
        ('https://twitter.com/user/status/1234567890123456789', 'twitter', '1234567890123456789'),
        ('https://x.com/user/status/9876543210987654321', 'twitter', '9876543210987654321'),
        ('https://unknown-platform.com/video/xyz789', 'unknown-platform.com', None)  # Will generate hash
    ]
    
    for url, expected_platform, expected_content_id in test_urls:
        platform, content_id = PlatformDetector.detect_platform_and_id(url)
        
        platform_match = platform == expected_platform
        content_match = content_id == expected_content_id if expected_content_id else len(content_id) > 0
        
        status = "✅" if platform_match and content_match else "❌"
        print(f"  {status} URL: {url[:50]}{'...' if len(url) > 50 else ''}")
        print(f"    Platform: {platform} (expected: {expected_platform})")
        print(f"    Content ID: {content_id} (expected: {expected_content_id or 'hash'})")
        
        if not platform_match:
            print(f"    ❌ Platform mismatch!")
        if not content_match:
            print(f"    ❌ Content ID mismatch!")


def test_metadata_parsing():
    """Test metadata parsing utilities"""
    print(f"\n📝 Testing Metadata Parsing")
    print("-" * 50)
    
    # Test filesize parsing
    print("  📊 Testing filesize parsing:")
    filesize_tests = [
        ('8.2MB', 8597504),  # 8.2 * 1024 * 1024
        ('1.5GB', 1610612736),  # 1.5 * 1024^3
        ('512KB', 524288),  # 512 * 1024
        ('750B', 750),
        ('invalid', None),
        ('', None),
        (None, None)
    ]
    
    for filesize_str, expected_bytes in filesize_tests:
        result = MetadataParser.parse_filesize_to_bytes(filesize_str)
        status = "✅" if result == expected_bytes else "❌"
        print(f"    {status} '{filesize_str}' → {result} bytes (expected: {expected_bytes})")
    
    # Test filename extraction
    print("  📁 Testing filename extraction:")
    filepath_tests = [
        ('/downloads/cat_video_123.mp4', 'cat_video_123.mp4'),
        ('C:\\Downloads\\video.mp4', 'video.mp4'),
        ('video.mp4', 'video.mp4'),
        ('/path/to/file.mkv', 'file.mkv'),
        ('', 'unknown_file'),
        (None, 'unknown_file')
    ]
    
    for filepath, expected_filename in filepath_tests:
        result = MetadataParser.extract_filename_from_path(filepath)
        status = "✅" if result == expected_filename else "❌"
        print(f"    {status} '{filepath}' → '{result}' (expected: '{expected_filename}')")
    
    # Test date parsing
    print("  📅 Testing date parsing:")
    date_tests = [
        ('2024/12/25 10:30:00', '2024-12-25T10:30:00'),
        ('2024-12-25 10:30:00', '2024-12-25T10:30:00'),
        ('2024-12-25', '2024-12-25T00:00:00'),
        ('25/12/2024 10:30:00', '2024-12-25T10:30:00'),
        ('invalid date', None),
        ('', None)
    ]
    
    for date_str, expected_iso in date_tests:
        result = MetadataParser.parse_download_date(date_str)
        status = "✅" if result == expected_iso else "❌"
        print(f"    {status} '{date_str}' → '{result}' (expected: '{expected_iso}')")
    
    # Test metadata field extraction
    print("  🏷️ Testing metadata field extraction:")
    test_metadata = {
        'caption': 'Test description',
        'creator': '@test_user',
        'thumbnail': 'https://example.com/thumb.jpg',
        'likes': 12000,
        'views': 500000,
        'hashtags': ['#test', '#video'],
        'upload_date': '2024-12-25'
    }
    
    extracted = MetadataParser.extract_metadata_fields(test_metadata)
    expected_mappings = {
        'description': 'Test description',
        'author_name': '@test_user',
        'thumbnail_url': 'https://example.com/thumb.jpg',
        'like_count': 12000,
        'view_count': 500000,
        'hashtags': ['#test', '#video'],
        'published_at': '2024-12-25'
    }
    
    for field, expected_value in expected_mappings.items():
        actual_value = extracted.get(field)
        status = "✅" if actual_value == expected_value else "❌"
        print(f"    {status} {field}: {actual_value} (expected: {expected_value})")


def test_v1_record_conversion():
    """Test conversion of individual v1.2.1 records"""
    print(f"\n🔄 Testing V1 Record Conversion")
    print("-" * 50)
    
    # Create a test v1 record
    v1_record = V1DownloadRecord(
        id=1,
        url='https://tiktok.com/@test_user/video/123456789',
        title='Test TikTok Video',
        filepath='/downloads/test_video.mp4',
        quality='1080p',
        format='mp4',
        duration=45,
        filesize='8.2MB',
        status='Success',
        download_date='2024/12/25 10:30:00',
        metadata=json.dumps({
            'caption': 'Test video caption',
            'creator': '@test_user',
            'likes': 12000,
            'thumbnail': 'https://example.com/thumb.jpg'
        })
    )
    
    # Test conversion
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "conversion_test.db")
    
    try:
        # Setup minimal database structure
        config = ConnectionConfig(database_path=db_path)
        connection_manager = SQLiteConnectionManager(config)
        connection_manager.initialize()
        
        converter = SQLiteDataConverter(connection_manager)
        
        # Test single record conversion
        content_record, download_record = converter._convert_single_record(v1_record)
        
        print(f"  📋 Content Record:")
        print(f"    Platform: {content_record.platform_id}")
        print(f"    Content ID: {content_record.platform_content_id}")
        print(f"    URL: {content_record.original_url}")
        print(f"    Title: {content_record.title}")
        print(f"    Author: {content_record.author_name}")
        print(f"    Duration: {content_record.duration_seconds}s")
        print(f"    Likes: {content_record.like_count}")
        
        print(f"  💾 Download Record:")
        print(f"    File Path: {download_record.file_path}")
        print(f"    File Name: {download_record.file_name}")
        print(f"    File Size: {download_record.file_size_bytes} bytes")
        print(f"    Format: {download_record.format}")
        print(f"    Quality: {download_record.quality}")
        print(f"    Status: {download_record.status}")
        print(f"    Progress: {download_record.download_progress}")
        
        # Validate conversion
        validations = [
            (content_record.platform_id == 'tiktok', "Platform detection"),
            (content_record.platform_content_id == '123456789', "Content ID extraction"),
            (content_record.author_name == '@test_user', "Author name mapping"),
            (content_record.like_count == 12000, "Like count mapping"),
            (download_record.file_size_bytes == 8597504, "File size conversion"),  # 8.2MB
            (download_record.status == 'completed', "Status conversion"),
            (download_record.download_progress == 1.0, "Progress calculation")
        ]
        
        print(f"  ✅ Validation Results:")
        for is_valid, description in validations:
            status = "✅" if is_valid else "❌"
            print(f"    {status} {description}")
        
        connection_manager.shutdown()
        
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_full_data_conversion():
    """Test complete data conversion process"""
    print(f"\n🚀 Testing Full Data Conversion")
    print("-" * 50)
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "full_conversion_test.db")
    
    try:
        # Setup database with v1→v2 migration completed
        initial_record_count = setup_v1_to_v2_migrated_database(db_path)
        
        # Initialize connection
        config = ConnectionConfig(database_path=db_path)
        connection_manager = SQLiteConnectionManager(config)
        connection_manager.initialize()
        
        # Perform data conversion
        print("  🔧 Executing data conversion...")
        conversion_manager = DataConversionManager(connection_manager)
        success, message, stats = conversion_manager.execute_data_conversion()
        
        print(f"  Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
        print(f"  Message: {message}")
        
        print(f"  📊 Conversion Statistics:")
        print(f"    Total v1 records: {stats.total_v1_records}")
        print(f"    Successful conversions: {stats.successful_conversions}")
        print(f"    Failed conversions: {stats.failed_conversions}")
        print(f"    Content records created: {stats.content_records_created}")
        print(f"    Download records created: {stats.download_records_created}")
        print(f"    Skipped duplicates: {stats.skipped_duplicates}")
        print(f"    Conversion time: {stats.conversion_time_seconds:.2f}s")
        
        if stats.errors:
            print(f"  ❌ Errors ({len(stats.errors)}):")
            for error in stats.errors[:3]:  # Show first 3 errors
                print(f"    - {error}")
        
        if success:
            # Verify the results
            print(f"  🔍 Verifying conversion results...")
            
            with connection_manager.connection() as conn:
                cursor = conn.cursor()
                
                # Check content table
                cursor.execute("SELECT COUNT(*) FROM content")
                content_count = cursor.fetchone()[0]
                
                # Check downloads table
                cursor.execute("SELECT COUNT(*) FROM downloads")
                downloads_count = cursor.fetchone()[0]
                
                # Check platform distribution
                cursor.execute("SELECT platform_id, COUNT(*) FROM content GROUP BY platform_id")
                platform_stats = cursor.fetchall()
                
                # Check status distribution
                cursor.execute("SELECT status, COUNT(*) FROM downloads GROUP BY status")
                status_stats = cursor.fetchall()
                
                print(f"    Content records: {content_count}")
                print(f"    Download records: {downloads_count}")
                
                print(f"    Platform distribution:")
                for platform, count in platform_stats:
                    print(f"      {platform}: {count}")
                
                print(f"    Status distribution:")
                for status, count in status_stats:
                    print(f"      {status}: {count}")
                
                # Verify duplicate handling
                cursor.execute("""
                    SELECT original_url, COUNT(*) as count 
                    FROM content 
                    GROUP BY original_url 
                    HAVING count > 1
                """)
                duplicates = cursor.fetchall()
                
                if duplicates:
                    print(f"    ❌ Found {len(duplicates)} duplicate URLs in content table")
                else:
                    print(f"    ✅ No duplicate URLs found - deduplication working correctly")
                
                # Check foreign key relationships
                cursor.execute("""
                    SELECT COUNT(*) FROM downloads d
                    LEFT JOIN content c ON d.content_id = c.id
                    WHERE c.id IS NULL
                """)
                orphaned_downloads = cursor.fetchone()[0]
                
                if orphaned_downloads > 0:
                    print(f"    ❌ Found {orphaned_downloads} orphaned download records")
                else:
                    print(f"    ✅ All download records properly linked to content")
        
        connection_manager.shutdown()
        
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_edge_cases_and_error_handling():
    """Test edge cases and error handling"""
    print(f"\n⚠️ Testing Edge Cases and Error Handling")
    print("-" * 50)
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Test 1: Conversion without schema migration
        print("  📋 Test 1: Conversion without schema migration")
        db_path1 = os.path.join(temp_dir, "no_migration_test.db")
        
        conn = sqlite3.connect(db_path1)
        conn.execute("CREATE TABLE downloads (id INTEGER PRIMARY KEY)")
        conn.close()
        
        config = ConnectionConfig(database_path=db_path1)
        connection_manager = SQLiteConnectionManager(config)
        connection_manager.initialize()
        
        conversion_manager = DataConversionManager(connection_manager)
        success, message, stats = conversion_manager.execute_data_conversion()
        
        expected_failure = not success and "schema transformation" in message.lower()
        status = "✅" if expected_failure else "❌"
        print(f"    {status} Correctly detected missing schema migration")
        
        connection_manager.shutdown()
        
        # Test 2: Empty v1 backup table
        print("  📋 Test 2: Empty v1 backup table")
        db_path2 = os.path.join(temp_dir, "empty_backup_test.db")
        
        # Create proper v2.0 structure but empty backup
        setup_v1_to_v2_migrated_database(db_path2)
        
        # Clear the backup table
        conn = sqlite3.connect(db_path2)
        conn.execute("DELETE FROM downloads_v1_backup")
        conn.commit()
        conn.close()
        
        config = ConnectionConfig(database_path=db_path2)
        connection_manager = SQLiteConnectionManager(config)
        connection_manager.initialize()
        
        conversion_manager = DataConversionManager(connection_manager)
        success, message, stats = conversion_manager.execute_data_conversion()
        
        # Should succeed but with 0 conversions
        expected_success = success and stats.total_v1_records == 0
        status = "✅" if expected_success else "❌"
        print(f"    {status} Correctly handled empty backup table")
        print(f"      Message: {message}")
        print(f"      Total records: {stats.total_v1_records}")
        
        connection_manager.shutdown()
        
        # Test 3: Malformed metadata
        print("  📋 Test 3: Malformed metadata handling")
        db_path3 = os.path.join(temp_dir, "malformed_metadata_test.db")
        
        conn = sqlite3.connect(db_path3)
        cursor = conn.cursor()
        
        # Create basic structure and add record with bad metadata
        cursor.execute('''
            CREATE TABLE downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                title TEXT NOT NULL,
                filepath TEXT NOT NULL,
                quality TEXT,
                format TEXT,
                duration INTEGER,
                filesize TEXT,
                status TEXT,
                download_date TEXT,
                metadata TEXT
            )
        ''')
        
        # Insert record with malformed JSON
        cursor.execute('''
            INSERT INTO downloads (url, title, filepath, quality, format, duration, 
                                   filesize, status, download_date, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'https://test.com/video/123',
            'Test Video',
            '/downloads/test.mp4',
            '720p',
            'mp4',
            60,
            '10MB',
            'Success',
            '2024/12/25 10:30:00',
            '{"invalid": json, missing quote}'  # Malformed JSON
        ))
        
        conn.commit()
        conn.close()
        
        # Perform schema migration
        config = ConnectionConfig(database_path=db_path3)
        connection_manager = SQLiteConnectionManager(config)
        connection_manager.initialize()
        
        transformation_manager = SchemaTransformationManager(connection_manager)
        transformation_manager.execute_migration()
        
        # Now test data conversion
        conversion_manager = DataConversionManager(connection_manager)
        success, message, stats = conversion_manager.execute_data_conversion()
        
        # Should succeed despite malformed metadata
        expected_success = success and stats.successful_conversions > 0
        status = "✅" if expected_success else "❌"
        print(f"    {status} Correctly handled malformed metadata")
        print(f"      Successful conversions: {stats.successful_conversions}")
        
        connection_manager.shutdown()
        
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    try:
        print("🔄 Data Conversion Logic Test Suite")
        print("=" * 60)
        
        test_platform_detection()
        test_metadata_parsing()
        test_v1_record_conversion()
        test_full_data_conversion()
        test_edge_cases_and_error_handling()
        
        print(f"\n🎉 All data conversion tests completed!")
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 