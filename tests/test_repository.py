"""
Test suite for Repository Pattern Implementation

Tests repository interfaces, implementations, query builder,
and model interactions for data access abstraction.
"""

import unittest
import tempfile
import os
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.models import (
    ContentModel, ContentType, ContentStatus, PlatformType,
    ContentModelManager, ValidationError
)
from data.models.repositories import (
    QueryBuilder, RepositoryError, BaseRepository, ContentRepository,
    get_content_repository, register_repository
)
from data.database.connection import ConnectionConfig, SQLiteConnectionManager


class TestQueryBuilder(unittest.TestCase):
    """Test QueryBuilder functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.query_builder = QueryBuilder("test_table")
    
    def test_basic_select(self):
        """Test basic SELECT query building"""
        query, params = self.query_builder.build()
        
        self.assertEqual(query, "SELECT * FROM test_table")
        self.assertEqual(params, [])
    
    def test_select_specific_fields(self):
        """Test SELECT with specific fields"""
        query, params = (self.query_builder
                        .select(["id", "name", "email"])
                        .build())
        
        self.assertIn("SELECT id, name, email", query)
        self.assertEqual(params, [])
    
    def test_where_conditions(self):
        """Test WHERE conditions"""
        query, params = (self.query_builder
                        .where_equals("status", "active")
                        .where_equals("type", "user")
                        .build())
        
        self.assertIn("WHERE status = ? AND type = ?", query)
        self.assertEqual(params, ["active", "user"])
    
    def test_where_in_condition(self):
        """Test WHERE IN condition"""
        query, params = (self.query_builder
                        .where_in("id", [1, 2, 3, 4])
                        .build())
        
        self.assertIn("WHERE id IN (?, ?, ?, ?)", query)
        self.assertEqual(params, [1, 2, 3, 4])
    
    def test_where_like_condition(self):
        """Test WHERE LIKE condition"""
        query, params = (self.query_builder
                        .where_like("name", "%john%")
                        .build())
        
        self.assertIn("WHERE name LIKE ?", query)
        self.assertEqual(params, ["%john%"])
    
    def test_where_between_condition(self):
        """Test WHERE BETWEEN condition"""
        query, params = (self.query_builder
                        .where_between("created_at", "2023-01-01", "2023-12-31")
                        .build())
        
        self.assertIn("WHERE created_at BETWEEN ? AND ?", query)
        self.assertEqual(params, ["2023-01-01", "2023-12-31"])
    
    def test_order_by(self):
        """Test ORDER BY clause"""
        query, params = (self.query_builder
                        .order_by("created_at", "DESC")
                        .build())
        
        self.assertIn("ORDER BY created_at DESC", query)
    
    def test_limit_clause(self):
        """Test LIMIT clause"""
        query, params = (self.query_builder
                        .limit(10, 20)
                        .build())
        
        self.assertIn("LIMIT 10 OFFSET 20", query)
    
    def test_complex_query(self):
        """Test complex query with multiple clauses"""
        query, params = (self.query_builder
                        .select(["id", "title", "status"])
                        .where_equals("platform", "youtube")
                        .where_in("status", ["pending", "completed"])
                        .where_not_deleted()
                        .order_by("created_at", "DESC")
                        .limit(50)
                        .build())
        
        # Should contain all clauses
        self.assertIn("SELECT id, title, status", query)
        self.assertIn("WHERE platform = ? AND status IN (?, ?) AND is_deleted = ?", query)
        self.assertIn("ORDER BY created_at DESC", query)
        self.assertIn("LIMIT 50", query)
        
        # Should have correct parameters
        self.assertEqual(params, ["youtube", "pending", "completed", 0])


class TestContentRepository(unittest.TestCase):
    """Test ContentRepository implementation"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_repo.db")
        
        # Set up database connection
        config = ConnectionConfig(
            database_path=self.db_path,
            max_pool_size=5,
            min_pool_size=1
        )
        
        self.connection_manager = SQLiteConnectionManager(config)
        self.connection_manager.initialize()
        
        # Set up model manager and repository
        self.model_manager = ContentModelManager(self.connection_manager)
        self.model_manager.create_table()
        
        self.repository = ContentRepository(self.model_manager)
        
        # Create test content
        self.test_content = ContentModel(
            url="https://tiktok.com/test",
            platform=PlatformType.TIKTOK,
            content_type=ContentType.VIDEO,
            title="Test Video",
            author="Test Author",
            platform_id="test123"
        )
    
    def tearDown(self):
        """Clean up test environment"""
        try:
            self.connection_manager.shutdown()
        except:
            pass
        
        # Clean up temp files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_save_and_find_content(self):
        """Test saving and finding content"""
        # Save content
        saved_content = self.repository.save(self.test_content)
        self.assertIsNotNone(saved_content)
        self.assertIsNotNone(saved_content.id)
        
        # Find by ID
        found_content = self.repository.find_by_id(saved_content.id)
        self.assertIsNotNone(found_content)
        self.assertEqual(found_content.title, "Test Video")
        self.assertEqual(found_content.platform, PlatformType.TIKTOK)
    
    def test_find_by_url(self):
        """Test finding content by URL"""
        # Save content
        saved_content = self.repository.save(self.test_content)
        self.assertIsNotNone(saved_content)
        
        # Find by URL
        found_content = self.repository.find_by_url("https://tiktok.com/test")
        self.assertIsNotNone(found_content)
        self.assertEqual(found_content.id, saved_content.id)
    
    def test_find_by_platform_id(self):
        """Test finding content by platform and platform ID"""
        # Save content
        saved_content = self.repository.save(self.test_content)
        self.assertIsNotNone(saved_content)
        
        # Find by platform ID
        found_content = self.repository.find_by_platform_id(PlatformType.TIKTOK, "test123")
        self.assertIsNotNone(found_content)
        self.assertEqual(found_content.id, saved_content.id)
    
    def test_find_by_status(self):
        """Test finding content by status"""
        # Create content with different statuses
        content1 = ContentModel(
            url="https://test1.com",
            platform=PlatformType.YOUTUBE,
            status=ContentStatus.PENDING
        )
        content2 = ContentModel(
            url="https://test2.com", 
            platform=PlatformType.YOUTUBE,
            status=ContentStatus.COMPLETED
        )
        
        # Save both
        self.repository.save(content1)
        self.repository.save(content2)
        
        # Find by status
        pending_content = self.repository.find_by_status(ContentStatus.PENDING)
        completed_content = self.repository.find_by_status(ContentStatus.COMPLETED)
        
        self.assertEqual(len(pending_content), 1)
        self.assertEqual(len(completed_content), 1)
        self.assertEqual(pending_content[0].url, "https://test1.com")
        self.assertEqual(completed_content[0].url, "https://test2.com")
    
    def test_find_by_platform(self):
        """Test finding content by platform"""
        # Create content for different platforms
        content1 = ContentModel(url="https://tiktok.com/test", platform=PlatformType.TIKTOK)
        content2 = ContentModel(url="https://youtube.com/test", platform=PlatformType.YOUTUBE)
        
        # Save both
        self.repository.save(content1)
        self.repository.save(content2)
        
        # Find by platform
        tiktok_content = self.repository.find_by_platform(PlatformType.TIKTOK)
        youtube_content = self.repository.find_by_platform(PlatformType.YOUTUBE)
        
        self.assertEqual(len(tiktok_content), 1)
        self.assertEqual(len(youtube_content), 1)
    
    def test_search_content(self):
        """Test content search functionality"""
        # Create searchable content
        content1 = ContentModel(
            url="https://test1.com",
            platform=PlatformType.YOUTUBE,
            title="Python Tutorial",
            author="Code Academy"
        )
        content2 = ContentModel(
            url="https://test2.com",
            platform=PlatformType.YOUTUBE,
            title="JavaScript Basics",
            description="Learn JavaScript fundamentals"
        )
        content3 = ContentModel(
            url="https://test3.com",
            platform=PlatformType.YOUTUBE,
            title="Data Science Course",
            author="Python Expert"
        )
        
        # Save all content
        self.repository.save(content1)
        self.repository.save(content2)
        self.repository.save(content3)
        
        # Search tests
        python_results = self.repository.search_content("Python")
        javascript_results = self.repository.search_content("JavaScript")
        academy_results = self.repository.search_content("Academy")
        
        self.assertEqual(len(python_results), 2)  # Should find content1 and content3
        self.assertEqual(len(javascript_results), 1)  # Should find content2
        self.assertEqual(len(academy_results), 1)  # Should find content1
    
    def test_get_platform_stats(self):
        """Test platform statistics"""
        # Create content for different platforms
        contents = [
            ContentModel(url="https://tiktok1.com", platform=PlatformType.TIKTOK),
            ContentModel(url="https://tiktok2.com", platform=PlatformType.TIKTOK),
            ContentModel(url="https://youtube1.com", platform=PlatformType.YOUTUBE),
        ]
        
        # Save all content
        for content in contents:
            self.repository.save(content)
        
        # Get platform stats
        stats = self.repository.get_platform_stats()
        
        self.assertEqual(stats.get('tiktok', 0), 2)
        self.assertEqual(stats.get('youtube', 0), 1)
        self.assertNotIn('instagram', stats)  # Should not include platforms with 0 content
    
    def test_complex_query_execution(self):
        """Test executing complex custom queries"""
        # Create test content
        content1 = ContentModel(
            url="https://test1.com",
            platform=PlatformType.YOUTUBE,
            view_count=1000,
            like_count=100
        )
        content2 = ContentModel(
            url="https://test2.com",
            platform=PlatformType.YOUTUBE,
            view_count=5000,
            like_count=500
        )
        
        # Save content
        self.repository.save(content1)
        self.repository.save(content2)
        
        # Execute complex query
        query, params = (self.repository.query()
                        .where_equals("platform", "youtube")
                        .where("view_count > ?", 2000)
                        .order_by("view_count", "DESC")
                        .build())
        
        results = self.repository.execute_query(query, params)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].url, "https://test2.com")
    
    def test_repository_error_handling(self):
        """Test repository error handling"""
        # Test with invalid model manager
        with self.assertRaises(RepositoryError):
            bad_repo = ContentRepository(None)
            bad_repo.save(self.test_content)


class TestRepositoryRegistry(unittest.TestCase):
    """Test repository registry and factory functions"""
    
    def test_get_content_repository(self):
        """Test getting content repository instance"""
        # Should return a ContentRepository instance
        repo = get_content_repository()
        self.assertIsInstance(repo, ContentRepository)
        
        # Should return the same instance (singleton)
        repo2 = get_content_repository()
        self.assertIs(repo, repo2)
    
    def test_register_repository(self):
        """Test registering custom repositories"""
        from data.models.repositories import _repository_registry
        
        # Create mock model manager
        class MockModelManager:
            pass
        
        mock_manager = MockModelManager()
        
        # Register repository
        register_repository(ContentModel, mock_manager)
        
        # Verify registration
        self.assertIn(ContentModel, _repository_registry._model_managers)
        self.assertIs(_repository_registry._model_managers[ContentModel], mock_manager)


class TestModelValidation(unittest.TestCase):
    """Test model validation and error handling"""
    
    def test_content_model_validation(self):
        """Test ContentModel validation"""
        # Test invalid content (missing URL)
        invalid_content = ContentModel(
            url="",  # Empty URL should be invalid
            platform=PlatformType.YOUTUBE
        )
        
        with self.assertRaises(ValueError):
            ContentModel(url="")  # Should raise error for empty URL
    
    def test_validation_error_creation(self):
        """Test ValidationError creation and properties"""
        error = ValidationError("test_field", "invalid_value", "Test error message")
        
        self.assertEqual(error.field, "test_field")
        self.assertEqual(error.value, "invalid_value")
        self.assertEqual(error.message, "Test error message")
        self.assertIn("test_field", str(error))


if __name__ == '__main__':
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.ERROR)  # Reduce log noise during tests
    
    # Run tests
    unittest.main() 