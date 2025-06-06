#!/usr/bin/env python3
"""
Comprehensive CRUD Operation Validation Suite for DatabaseManager

This test suite implements boundary testing for data payloads including 
edge cases and schema validation checks for the DatabaseManager v1.2.1 interface.

Test Categories:
- CREATE operations (add_download)
- READ operations (get_downloads, search_downloads, get_by_url/title)
- UPDATE operations (update_download_filesize)
- DELETE operations (delete_download, delete_download_by_title)
- Boundary & Edge Cases
- Schema Validation
- Error Handling
"""

import os
import sys
import tempfile
import unittest
import json
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from utils.db_manager import DatabaseManager


class TestDatabaseCRUDValidation(unittest.TestCase):
    """Comprehensive CRUD validation test suite for DatabaseManager"""
    
    def setUp(self):
        """Set up test environment with temporary database"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.temp_dir, "test_crud.db")
        self.db_manager = DatabaseManager(self.test_db_path)
        
        # Standard test download info
        self.valid_download_info = {
            'url': 'https://tiktok.com/@user/video/12345',
            'title': 'Test Video',
            'filepath': '/downloads/test_video.mp4',
            'quality': '1080p',
            'format': 'mp4',
            'duration': 60,
            'filesize': '10.5 MB',
            'status': 'Success',
            'download_date': '2024/12/28 15:30',
            'creator': '@testuser',
            'description': 'Test video description',
            'hashtags': ['#test', '#video']
        }
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    # =============================================================================
    # CREATE OPERATION TESTS
    # =============================================================================
    
    def test_add_download_valid_complete_data(self):
        """Test adding download with all valid fields"""
        self.db_manager.add_download(self.valid_download_info)
        
        downloads = self.db_manager.get_downloads()
        self.assertEqual(len(downloads), 1)
        
        download = downloads[0]
        self.assertEqual(download['url'], self.valid_download_info['url'])
        self.assertEqual(download['title'], self.valid_download_info['title'])
        self.assertIn('creator', download)  # Metadata should be parsed
        self.assertIn('hashtags', download)
    
    def test_add_download_minimal_required_fields(self):
        """Test adding download with only required fields"""
        minimal_info = {
            'url': 'https://test.com/minimal',
            'title': 'Minimal Test'
        }
        
        self.db_manager.add_download(minimal_info)
        downloads = self.db_manager.get_downloads()
        
        self.assertEqual(len(downloads), 1)
        download = downloads[0]
        self.assertEqual(download['url'], minimal_info['url'])
        self.assertEqual(download['title'], minimal_info['title'])
        self.assertEqual(download['filepath'], '')  # Default value
        self.assertEqual(download['status'], 'Success')  # Default value
    
    def test_add_download_empty_dictionary(self):
        """Test adding download with empty dictionary"""
        empty_info = {}
        
        self.db_manager.add_download(empty_info)
        downloads = self.db_manager.get_downloads()
        
        self.assertEqual(len(downloads), 1)
        download = downloads[0]
        self.assertEqual(download['url'], '')
        self.assertEqual(download['title'], 'Unknown')
        self.assertEqual(download['status'], 'Success')
    
    def test_add_download_none_values(self):
        """Test adding download with None values"""
        none_info = {
            'url': None,
            'title': None,
            'filepath': None,
            'duration': None
        }
        
        self.db_manager.add_download(none_info)
        downloads = self.db_manager.get_downloads()
        
        self.assertEqual(len(downloads), 1)
        download = downloads[0]
        self.assertEqual(download['duration'], 0)  # None converted to default
    
    def test_add_download_large_data_payload(self):
        """Test adding download with large data values"""
        large_info = {
            'url': 'https://test.com/' + 'x' * 1000,  # Very long URL
            'title': 'A' * 500,  # Very long title
            'description': 'B' * 2000,  # Very long description
            'hashtags': ['#tag' + str(i) for i in range(100)],  # Many hashtags
            'duration': 999999,  # Large duration
            'filesize': '999.99 GB'  # Large file size
        }
        
        self.db_manager.add_download(large_info)
        downloads = self.db_manager.get_downloads()
        
        self.assertEqual(len(downloads), 1)
        download = downloads[0]
        self.assertEqual(download['url'], large_info['url'])
        self.assertEqual(download['title'], large_info['title'])
        self.assertEqual(download['duration'], large_info['duration'])
    
    def test_add_download_special_characters(self):
        """Test adding download with special characters and Unicode"""
        special_info = {
            'url': 'https://test.com/路径?param=值&other=🎵',
            'title': 'Test 🎵 Video with émoji and 中文',
            'description': 'Special chars: <>&"\'\\n\\t\\r',
            'creator': '@user_with_émoji_🎬',
            'hashtags': ['#测试', '#🎵music', '#français']
        }
        
        self.db_manager.add_download(special_info)
        downloads = self.db_manager.get_downloads()
        
        self.assertEqual(len(downloads), 1)
        download = downloads[0]
        self.assertEqual(download['url'], special_info['url'])
        self.assertEqual(download['title'], special_info['title'])
        self.assertIn('🎵', download['title'])
        self.assertIn('测试', str(download['hashtags']))
    
    def test_add_multiple_downloads(self):
        """Test adding multiple downloads in sequence"""
        for i in range(5):
            info = self.valid_download_info.copy()
            info['url'] = f"https://test.com/video/{i}"
            info['title'] = f"Test Video {i}"
            self.db_manager.add_download(info)
        
        downloads = self.db_manager.get_downloads()
        self.assertEqual(len(downloads), 5)
        
        # Check ordering (should be by download_date DESC)
        urls = [d['url'] for d in downloads]
        expected_urls = [f"https://test.com/video/{i}" for i in range(4, -1, -1)]
        self.assertEqual(urls, expected_urls)
    
    # =============================================================================
    # READ OPERATION TESTS
    # =============================================================================
    
    def test_get_downloads_empty_database(self):
        """Test getting downloads from empty database"""
        downloads = self.db_manager.get_downloads()
        self.assertEqual(downloads, [])
        self.assertIsInstance(downloads, list)
    
    def test_get_downloads_populated_database(self):
        """Test getting downloads from populated database"""
        # Add test data
        for i in range(3):
            info = self.valid_download_info.copy()
            info['url'] = f"https://test.com/video/{i}"
            info['title'] = f"Test Video {i}"
            self.db_manager.add_download(info)
        
        downloads = self.db_manager.get_downloads()
        self.assertEqual(len(downloads), 3)
        
        # Verify metadata parsing
        for download in downloads:
            self.assertIn('id', download)
            self.assertIn('url', download)
            self.assertIn('title', download)
            self.assertIn('creator', download)  # From metadata
            self.assertIn('hashtags', download)
    
    def test_search_downloads_by_title(self):
        """Test searching downloads by title"""
        # Add test data
        test_data = [
            {'title': 'Funny Cat Video', 'url': 'https://test.com/cat'},
            {'title': 'Dog Playing fetch', 'url': 'https://test.com/dog'},
            {'title': 'Cat and Dog Friends', 'url': 'https://test.com/both'}
        ]
        
        for data in test_data:
            info = self.valid_download_info.copy()
            info.update(data)
            self.db_manager.add_download(info)
        
        # Search for "cat"
        cat_results = self.db_manager.search_downloads('cat')
        self.assertEqual(len(cat_results), 2)  # "Funny Cat Video" and "Cat and Dog Friends"
        
        # Search for "Dog" (case insensitive)
        dog_results = self.db_manager.search_downloads('Dog')
        self.assertEqual(len(dog_results), 2)  # "Dog Playing fetch" and "Cat and Dog Friends"
        
        # Search for non-existent term
        no_results = self.db_manager.search_downloads('elephant')
        self.assertEqual(len(no_results), 0)
    
    def test_search_downloads_by_metadata(self):
        """Test searching downloads by metadata content"""
        # Add test data with specific metadata
        info1 = self.valid_download_info.copy()
        info1.update({
            'title': 'Music Video',
            'creator': '@musician_pro',
            'hashtags': ['#music', '#rock']
        })
        
        info2 = self.valid_download_info.copy()
        info2.update({
            'title': 'Dance Video',
            'creator': '@dancer_star',
            'hashtags': ['#dance', '#pop']
        })
        
        self.db_manager.add_download(info1)
        self.db_manager.add_download(info2)
        
        # Search by creator (stored in metadata)
        musician_results = self.db_manager.search_downloads('musician_pro')
        self.assertEqual(len(musician_results), 1)
        self.assertEqual(musician_results[0]['title'], 'Music Video')
        
        # Search by hashtag (stored in metadata)
        dance_results = self.db_manager.search_downloads('dance')
        self.assertEqual(len(dance_results), 1)
        self.assertEqual(dance_results[0]['title'], 'Dance Video')
    
    def test_get_download_by_url_exists(self):
        """Test getting download by URL when it exists"""
        self.db_manager.add_download(self.valid_download_info)
        
        result = self.db_manager.get_download_by_url(self.valid_download_info['url'])
        self.assertIsNotNone(result)
        self.assertEqual(result['url'], self.valid_download_info['url'])
        self.assertEqual(result['title'], self.valid_download_info['title'])
        self.assertIn('creator', result)
    
    def test_get_download_by_url_not_exists(self):
        """Test getting download by URL when it doesn't exist"""
        result = self.db_manager.get_download_by_url('https://nonexistent.com/video')
        self.assertIsNone(result)
    
    def test_get_download_by_title_exists(self):
        """Test getting download by title when it exists"""
        self.db_manager.add_download(self.valid_download_info)
        
        result = self.db_manager.get_download_by_title(self.valid_download_info['title'])
        self.assertIsNotNone(result)
        self.assertEqual(result['title'], self.valid_download_info['title'])
        self.assertEqual(result['url'], self.valid_download_info['url'])
    
    def test_get_download_by_title_not_exists(self):
        """Test getting download by title when it doesn't exist"""
        result = self.db_manager.get_download_by_title('Non-existent Title')
        self.assertIsNone(result)
    
    # =============================================================================
    # UPDATE OPERATION TESTS
    # =============================================================================
    
    def test_update_download_filesize_by_id(self):
        """Test updating file size using record ID"""
        self.db_manager.add_download(self.valid_download_info)
        
        downloads = self.db_manager.get_downloads()
        download_id = downloads[0]['id']
        
        success = self.db_manager.update_download_filesize(download_id, '15.7 MB')
        self.assertTrue(success)
        
        # Verify update
        updated_downloads = self.db_manager.get_downloads()
        self.assertEqual(updated_downloads[0]['filesize'], '15.7 MB')
    
    def test_update_download_filesize_by_url(self):
        """Test updating file size using URL"""
        self.db_manager.add_download(self.valid_download_info)
        
        success = self.db_manager.update_download_filesize(
            self.valid_download_info['url'], '20.3 GB'
        )
        self.assertTrue(success)
        
        # Verify update
        downloads = self.db_manager.get_downloads()
        self.assertEqual(downloads[0]['filesize'], '20.3 GB')
    
    def test_update_download_filesize_nonexistent_id(self):
        """Test updating file size for non-existent ID"""
        success = self.db_manager.update_download_filesize(99999, '1.0 MB')
        self.assertFalse(success)
    
    def test_update_download_filesize_nonexistent_url(self):
        """Test updating file size for non-existent URL"""
        success = self.db_manager.update_download_filesize(
            'https://nonexistent.com/video', '1.0 MB'
        )
        self.assertFalse(success)
    
    def test_update_download_filesize_various_formats(self):
        """Test updating file size with various format strings"""
        self.db_manager.add_download(self.valid_download_info)
        download_id = self.db_manager.get_downloads()[0]['id']
        
        test_sizes = [
            '1.5 KB',
            '999 MB', 
            '10.0 GB',
            '0.1 TB',
            'Unknown',
            '5000 bytes',
            '∞ GB'  # Special character
        ]
        
        for size in test_sizes:
            success = self.db_manager.update_download_filesize(download_id, size)
            self.assertTrue(success)
            
            downloads = self.db_manager.get_downloads()
            self.assertEqual(downloads[0]['filesize'], size)
    
    # =============================================================================
    # DELETE OPERATION TESTS  
    # =============================================================================
    
    def test_delete_download_by_id_exists(self):
        """Test deleting download by ID when it exists"""
        self.db_manager.add_download(self.valid_download_info)
        
        downloads = self.db_manager.get_downloads()
        download_id = downloads[0]['id']
        
        success = self.db_manager.delete_download(download_id)
        self.assertTrue(success)
        
        # Verify deletion
        remaining_downloads = self.db_manager.get_downloads()
        self.assertEqual(len(remaining_downloads), 0)
    
    def test_delete_download_by_id_not_exists(self):
        """Test deleting download by ID when it doesn't exist"""
        success = self.db_manager.delete_download(99999)
        self.assertFalse(success)
    
    def test_delete_download_by_title_exists(self):
        """Test deleting download by title when it exists"""
        self.db_manager.add_download(self.valid_download_info)
        
        success = self.db_manager.delete_download_by_title(
            self.valid_download_info['title']
        )
        self.assertTrue(success)
        
        # Verify deletion
        remaining_downloads = self.db_manager.get_downloads()
        self.assertEqual(len(remaining_downloads), 0)
    
    def test_delete_download_by_title_not_exists(self):
        """Test deleting download by title when it doesn't exist"""
        success = self.db_manager.delete_download_by_title('Non-existent Title')
        self.assertFalse(success)
    
    def test_delete_download_by_title_multiple_matches(self):
        """Test deleting downloads when multiple have same title"""
        # Add multiple downloads with same title
        for i in range(3):
            info = self.valid_download_info.copy()
            info['url'] = f"https://test.com/video/{i}"
            # Keep same title
            self.db_manager.add_download(info)
        
        success = self.db_manager.delete_download_by_title(
            self.valid_download_info['title']
        )
        self.assertTrue(success)
        
        # All downloads with that title should be deleted
        remaining_downloads = self.db_manager.get_downloads()
        self.assertEqual(len(remaining_downloads), 0)
    
    def test_delete_partial_database(self):
        """Test deleting some downloads while keeping others"""
        # Add multiple downloads
        titles = ['Video A', 'Video B', 'Video C']
        for i, title in enumerate(titles):
            info = self.valid_download_info.copy()
            info['url'] = f"https://test.com/video/{i}"
            info['title'] = title
            self.db_manager.add_download(info)
        
        # Delete middle one
        success = self.db_manager.delete_download_by_title('Video B')
        self.assertTrue(success)
        
        # Verify correct deletion
        remaining_downloads = self.db_manager.get_downloads()
        self.assertEqual(len(remaining_downloads), 2)
        
        remaining_titles = [d['title'] for d in remaining_downloads]
        self.assertIn('Video A', remaining_titles)
        self.assertIn('Video C', remaining_titles)
        self.assertNotIn('Video B', remaining_titles)
    
    # =============================================================================
    # BOUNDARY & EDGE CASE TESTS
    # =============================================================================
    
    def test_extreme_metadata_values(self):
        """Test with extreme metadata values"""
        extreme_info = {
            'url': '',  # Empty URL
            'title': '',  # Empty title
            'duration': -1,  # Negative duration
            'filesize': '',  # Empty filesize
            'hashtags': [],  # Empty list
            'description': '',  # Empty description
            'creator': '',  # Empty creator
        }
        
        self.db_manager.add_download(extreme_info)
        downloads = self.db_manager.get_downloads()
        
        self.assertEqual(len(downloads), 1)
        download = downloads[0]
        self.assertEqual(download['url'], '')
        self.assertEqual(download['title'], 'Unknown')  # Default fallback
        self.assertEqual(download['duration'], -1)  # Preserved as-is
    
    def test_sql_injection_attempts(self):
        """Test resilience against SQL injection attempts"""
        malicious_inputs = [
            "'; DROP TABLE downloads; --",
            "admin'--",
            "' OR '1'='1"
        ]
        
        for malicious_input in malicious_inputs:
            info = self.valid_download_info.copy()
            info['title'] = malicious_input
            info['url'] = f"https://test.com/{malicious_input}"
            
            # Should not raise exception
            self.db_manager.add_download(info)
        
        downloads = self.db_manager.get_downloads()
        self.assertEqual(len(downloads), len(malicious_inputs))
        
        # Database should still be intact
        for download in downloads:
            self.assertIn('id', download)
            self.assertIn('title', download)
    
    def test_concurrent_operations_simulation(self):
        """Test simulated concurrent database operations"""
        # Simulate concurrent adds
        for i in range(10):
            info = self.valid_download_info.copy()
            info['url'] = f"https://test.com/concurrent/{i}"
            info['title'] = f"Concurrent Video {i}"
            self.db_manager.add_download(info)
        
        # Simulate concurrent reads during modifications
        downloads = self.db_manager.get_downloads()
        self.assertEqual(len(downloads), 10)
        
        # Simulate concurrent deletes
        for i in range(0, 10, 2):  # Delete every other one
            self.db_manager.delete_download_by_title(f"Concurrent Video {i}")
        
        remaining_downloads = self.db_manager.get_downloads()
        self.assertEqual(len(remaining_downloads), 5)
    
    def test_database_file_permissions(self):
        """Test database behavior with file system constraints"""
        # Test is valid - ensures database can be created and accessed
        self.assertTrue(os.path.exists(self.test_db_path))
        self.assertTrue(os.access(self.test_db_path, os.R_OK | os.W_OK))
        
        # Add data to verify write access
        self.db_manager.add_download(self.valid_download_info)
        downloads = self.db_manager.get_downloads()
        self.assertEqual(len(downloads), 1)
    
    # =============================================================================
    # SCHEMA VALIDATION TESTS
    # =============================================================================
    
    def test_database_schema_integrity(self):
        """Test database schema matches expected structure"""
        import sqlite3
        
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        
        # Get table schema
        cursor.execute("PRAGMA table_info(downloads)")
        columns = cursor.fetchall()
        
        expected_columns = {
            'id', 'url', 'title', 'filepath', 'quality', 'format', 
            'duration', 'filesize', 'status', 'download_date', 'metadata'
        }
        
        actual_columns = {col[1] for col in columns}  # col[1] is column name
        self.assertEqual(actual_columns, expected_columns)
        
        # Check primary key
        primary_keys = [col for col in columns if col[5]]  # col[5] is pk flag
        self.assertEqual(len(primary_keys), 1)
        self.assertEqual(primary_keys[0][1], 'id')
        
        conn.close()
    
    def test_metadata_json_validation(self):
        """Test metadata JSON serialization/deserialization"""
        complex_metadata = {
            'nested_object': {
                'level1': {
                    'level2': ['array', 'of', 'values']
                }
            },
            'unicode_text': 'Test with émoji 🎵 and 中文',
            'special_chars': '<>&"\'',
            'numbers': [1, 2.5, -3, 0],
            'booleans': [True, False, None],
            'empty_collections': {
                'empty_list': [],
                'empty_dict': {},
                'empty_string': ''
            }
        }
        
        info = self.valid_download_info.copy()
        info.update(complex_metadata)
        
        self.db_manager.add_download(info)
        downloads = self.db_manager.get_downloads()
        
        self.assertEqual(len(downloads), 1)
        download = downloads[0]
        
        # Check that complex metadata was preserved
        self.assertIn('nested_object', download)
        self.assertIn('unicode_text', download)
        self.assertEqual(download['unicode_text'], complex_metadata['unicode_text'])
        self.assertEqual(download['numbers'], complex_metadata['numbers'])
    
    def test_data_type_conversions(self):
        """Test automatic data type conversions"""
        type_test_info = {
            'url': 12345,  # Number as URL
            'title': ['list', 'as', 'title'],  # List as title
            'duration': '60',  # String as duration
            'filesize': 1048576,  # Number as filesize
        }
        
        # Should not raise exception - DatabaseManager should handle gracefully
        self.db_manager.add_download(type_test_info)
        downloads = self.db_manager.get_downloads()
        
        self.assertEqual(len(downloads), 1)
        download = downloads[0]
        
        # Check that data was stored (converted to strings by SQLite)
        self.assertIsInstance(download['url'], str)
        self.assertIsInstance(download['title'], str)
    

class TestDatabaseCRUDEdgeCases(unittest.TestCase):
    """Additional edge case tests for comprehensive coverage"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.temp_dir, "test_edge_cases.db")
        self.db_manager = DatabaseManager(self.test_db_path)
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_database_initialization_multiple_times(self):
        """Test multiple database initializations"""
        # Create multiple DatabaseManager instances for same DB
        db1 = DatabaseManager(self.test_db_path)
        db2 = DatabaseManager(self.test_db_path)
        db3 = DatabaseManager(self.test_db_path)
        
        # All should work without conflict
        test_info = {
            'url': 'https://test.com/multi',
            'title': 'Multi-instance Test'
        }
        
        db1.add_download(test_info)
        downloads = db2.get_downloads()
        self.assertEqual(len(downloads), 1)
        
        success = db3.delete_download_by_title('Multi-instance Test')
        self.assertTrue(success)
    
    def test_very_long_search_terms(self):
        """Test search with very long search terms"""
        # Add test data
        info = {
            'url': 'https://test.com/long',
            'title': 'Test Video with Very Long Title That Contains Many Words',
            'description': 'A' * 1000  # Very long description
        }
        self.db_manager.add_download(info)
        
        # Search with very long term
        long_term = 'A' * 500
        results = self.db_manager.search_downloads(long_term)
        self.assertEqual(len(results), 1)
        
        # Search with non-existent long term
        non_existent_long = 'B' * 500
        results = self.db_manager.search_downloads(non_existent_long)
        self.assertEqual(len(results), 0)
    
    def test_download_date_formats(self):
        """Test various download date formats"""
        date_formats = [
            '2024/12/28 15:30',
            '2024-12-28 15:30:45',
            '28/12/2024 3:30 PM',
            'Dec 28, 2024 15:30',
            '2024.12.28-15.30.45',
            'Invalid Date Format',
            '',
            None
        ]
        
        for i, date_format in enumerate(date_formats):
            info = {
                'url': f'https://test.com/date/{i}',
                'title': f'Date Test {i}',
                'download_date': date_format
            }
            
            # Should not raise exception
            self.db_manager.add_download(info)
        
        downloads = self.db_manager.get_downloads()
        self.assertEqual(len(downloads), len(date_formats))
        
        # Verify dates were stored
        for download in downloads:
            self.assertIn('download_date', download)


if __name__ == '__main__':
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseCRUDValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseCRUDEdgeCases))
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"DATABASE CRUD VALIDATION TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split(chr(10))[-2]}")
    
    if result.errors:
        print(f"\nERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split(chr(10))[-2]}")
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1) 