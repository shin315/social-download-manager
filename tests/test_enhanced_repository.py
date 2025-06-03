"""
Enhanced Repository Testing Framework

This module provides comprehensive testing for repository patterns including:
- Unit tests for repository implementations
- Mock database testing capabilities
- Repository interface compliance tests
- Query optimization testing
- Error handling and edge cases
"""

import unittest
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, patch, call

# Import base test infrastructure
from .test_base import (
    DatabaseTestCase, RepositoryTestCase, PerformanceTestCase, MockDatabaseTestCase,
    TestConfig
)

# Import test utilities
from .test_utils import (
    wait_for_condition, simulate_concurrent_operations
)

# Database components
from data.database.exceptions import (
    DatabaseError, DatabaseErrorCode, RepositoryError, EntityNotFoundError,
    EntityAlreadyExistsError, DataValidationError
)
from data.models import (
    ContentModel, ContentType, ContentStatus, PlatformType, ValidationError
)
from data.models.repositories import (
    IRepository, BaseRepository, ContentRepository, QueryBuilder,
    get_content_repository, register_repository
)


class TestRepositoryInterface(unittest.TestCase):
    """Test repository interface compliance"""
    
    def test_irepository_interface_definition(self):
        """Test that IRepository defines required methods"""
        required_methods = [
            'save', 'find_by_id', 'find_all', 'delete_by_id', 'exists', 'count'
        ]
        
        for method_name in required_methods:
            self.assertTrue(
                hasattr(IRepository, method_name),
                f"IRepository missing required method: {method_name}"
            )
    
    def test_base_repository_implements_interface(self):
        """Test that BaseRepository properly implements IRepository"""
        # BaseRepository should be abstract and implement interface methods
        from abc import ABC
        self.assertTrue(issubclass(BaseRepository, ABC))
        self.assertTrue(issubclass(BaseRepository, IRepository))
    
    def test_content_repository_implements_interface(self):
        """Test that ContentRepository implements all required methods"""
        self.assertTrue(issubclass(ContentRepository, BaseRepository))
        
        # Should implement all interface methods
        required_methods = [
            'save', 'find_by_id', 'find_all', 'delete_by_id', 'exists', 'count'
        ]
        
        for method_name in required_methods:
            self.assertTrue(
                hasattr(ContentRepository, method_name),
                f"ContentRepository missing method: {method_name}"
            )


class TestQueryBuilder(DatabaseTestCase):
    """Test QueryBuilder functionality with database integration"""
    
    def _custom_setup(self):
        """Setup test table for QueryBuilder tests"""
        super()._custom_setup()
        
        self.create_test_table("query_test", """
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            priority INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            category TEXT,
            is_deleted INTEGER DEFAULT 0
        """)
        
        # Insert test data
        test_data = [
            {"name": "Test 1", "status": "active", "priority": 1, "category": "A"},
            {"name": "Test 2", "status": "inactive", "priority": 2, "category": "B"},
            {"name": "Test 3", "status": "active", "priority": 3, "category": "A"},
            {"name": "Test 4", "status": "pending", "priority": 1, "category": "C"},
            {"name": "Test 5", "status": "active", "priority": 2, "category": "B"},
        ]
        
        for data in test_data:
            self.insert_test_data("query_test", data)
    
    def test_basic_select_query(self):
        """Test basic SELECT query execution"""
        query_builder = QueryBuilder("query_test")
        query, params = query_builder.build()
        
        results = self.execute_query(query, params)
        
        self.assertEqual(len(results), 5)
        self.assertEqual(results[0]["name"], "Test 1")
    
    def test_select_specific_fields(self):
        """Test SELECT with specific fields"""
        query_builder = QueryBuilder("query_test")
        query, params = query_builder.select(["id", "name", "status"]).build()
        
        results = self.execute_query(query, params)
        
        self.assertEqual(len(results), 5)
        # Should only have selected fields
        for result in results:
            self.assertIn("id", result)
            self.assertIn("name", result)
            self.assertIn("status", result)
            self.assertNotIn("priority", result)
    
    def test_where_conditions(self):
        """Test various WHERE conditions"""
        # Test equals condition
        query_builder = QueryBuilder("query_test")
        query, params = query_builder.where_equals("status", "active").build()
        
        results = self.execute_query(query, params)
        self.assertEqual(len(results), 3)  # Test 1, 3, 5
        
        for result in results:
            self.assertEqual(result["status"], "active")
    
    def test_where_in_condition(self):
        """Test WHERE IN condition"""
        query_builder = QueryBuilder("query_test")
        query, params = query_builder.where_in("priority", [1, 3]).build()
        
        results = self.execute_query(query, params)
        self.assertEqual(len(results), 3)  # Test 1, 3, 4
        
        priorities = [result["priority"] for result in results]
        self.assertTrue(all(p in [1, 3] for p in priorities))
    
    def test_where_like_condition(self):
        """Test WHERE LIKE condition"""
        query_builder = QueryBuilder("query_test")
        query, params = query_builder.where_like("name", "Test 1%").build()
        
        results = self.execute_query(query, params)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Test 1")
    
    def test_complex_query_conditions(self):
        """Test complex query with multiple conditions"""
        query_builder = QueryBuilder("query_test")
        query, params = (query_builder
                        .select(["id", "name", "status", "priority"])
                        .where_equals("status", "active")
                        .where_in("category", ["A", "B"])
                        .where_not_deleted()
                        .order_by("priority", "ASC")
                        .limit(10)
                        .build())
        
        results = self.execute_query(query, params)
        
        # Should get Test 1 (priority 1) and Test 5 (priority 2)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["name"], "Test 1")  # Lower priority first
        self.assertEqual(results[1]["name"], "Test 5")
    
    def test_order_by_and_limit(self):
        """Test ORDER BY and LIMIT clauses"""
        query_builder = QueryBuilder("query_test")
        query, params = (query_builder
                        .order_by("priority", "DESC")
                        .limit(2)
                        .build())
        
        results = self.execute_query(query, params)
        
        self.assertEqual(len(results), 2)
        # Should be ordered by priority DESC, so Test 3 (priority 3) first
        self.assertEqual(results[0]["name"], "Test 3")
        self.assertTrue(results[0]["priority"] >= results[1]["priority"])
    
    def test_query_performance(self):
        """Test query performance with execution time measurement"""
        with self.measure_execution_time() as metrics:
            query_builder = QueryBuilder("query_test")
            query, params = (query_builder
                            .where_equals("status", "active")
                            .order_by("created_at", "DESC")
                            .limit(100)
                            .build())
            
            results = self.execute_query(query, params)
        
        # Query should execute quickly (less than 50ms for simple queries)
        self.assertLess(metrics["execution_time"], 0.05)
        self.assertEqual(len(results), 3)


class TestContentRepositoryImplementation(RepositoryTestCase):
    """Test ContentRepository implementation with real database"""
    
    def test_save_new_content(self):
        """Test saving new content"""
        content = self.create_test_content()
        
        saved_content = self.repository.save(content)
        
        self.assertIsNotNone(saved_content.id)
        self.assertEqual(saved_content.url, content.url)
        self.assertEqual(saved_content.title, content.title)
        self.assertIsNotNone(saved_content.created_at)
    
    def test_save_existing_content_update(self):
        """Test updating existing content"""
        # Save initial content
        content = self.create_test_content()
        saved_content = self.repository.save(content)
        original_id = saved_content.id
        
        # Update content
        saved_content.title = "Updated Title"
        saved_content.status = ContentStatus.COMPLETED
        
        updated_content = self.repository.save(saved_content)
        
        # Should keep same ID but update fields
        self.assertEqual(updated_content.id, original_id)
        self.assertEqual(updated_content.title, "Updated Title")
        self.assertEqual(updated_content.status, ContentStatus.COMPLETED)
    
    def test_find_by_id(self):
        """Test finding content by ID"""
        # Save test content
        content = self.create_test_content()
        saved_content = self.repository.save(content)
        
        # Find by ID
        found_content = self.repository.find_by_id(saved_content.id)
        
        self.assertIsNotNone(found_content)
        self.assertEqual(found_content.id, saved_content.id)
        self.assertEqual(found_content.url, content.url)
    
    def test_find_by_id_not_found(self):
        """Test finding non-existent content by ID"""
        found_content = self.repository.find_by_id(99999)
        self.assertIsNone(found_content)
    
    def test_find_by_url(self):
        """Test finding content by URL"""
        # Save test content
        content = self.create_test_content(url="https://unique-test.com/video")
        saved_content = self.repository.save(content)
        
        # Find by URL
        found_content = self.repository.find_by_url("https://unique-test.com/video")
        
        self.assertIsNotNone(found_content)
        self.assertEqual(found_content.id, saved_content.id)
        self.assertEqual(found_content.url, "https://unique-test.com/video")
    
    def test_find_by_platform_id(self):
        """Test finding content by platform and platform ID"""
        # Save test content
        content = self.create_test_content(
            platform=PlatformType.YOUTUBE,
            platform_id="unique_youtube_id"
        )
        saved_content = self.repository.save(content)
        
        # Find by platform and platform ID
        found_content = self.repository.find_by_platform_id(
            PlatformType.YOUTUBE, "unique_youtube_id"
        )
        
        self.assertIsNotNone(found_content)
        self.assertEqual(found_content.id, saved_content.id)
        self.assertEqual(found_content.platform_id, "unique_youtube_id")
    
    def test_find_by_status(self):
        """Test finding content by status"""
        # Save content with different statuses
        pending_content = self.create_test_content(status=ContentStatus.PENDING)
        completed_content = self.create_test_content(
            url="https://test2.com/video",
            status=ContentStatus.COMPLETED
        )
        
        self.repository.save(pending_content)
        self.repository.save(completed_content)
        
        # Find by status
        pending_results = self.repository.find_by_status(ContentStatus.PENDING)
        completed_results = self.repository.find_by_status(ContentStatus.COMPLETED)
        
        self.assertEqual(len(pending_results), 1)
        self.assertEqual(len(completed_results), 1)
        self.assertEqual(pending_results[0].status, ContentStatus.PENDING)
        self.assertEqual(completed_results[0].status, ContentStatus.COMPLETED)
    
    def test_find_by_platform(self):
        """Test finding content by platform"""
        # Save content for different platforms
        tiktok_content = self.create_test_content(platform=PlatformType.TIKTOK)
        youtube_content = self.create_test_content(
            url="https://youtube.com/video",
            platform=PlatformType.YOUTUBE
        )
        
        self.repository.save(tiktok_content)
        self.repository.save(youtube_content)
        
        # Find by platform
        tiktok_results = self.repository.find_by_platform(PlatformType.TIKTOK)
        youtube_results = self.repository.find_by_platform(PlatformType.YOUTUBE)
        
        self.assertEqual(len(tiktok_results), 1)
        self.assertEqual(len(youtube_results), 1)
        self.assertEqual(tiktok_results[0].platform, PlatformType.TIKTOK)
        self.assertEqual(youtube_results[0].platform, PlatformType.YOUTUBE)
    
    def test_search_content(self):
        """Test content search functionality"""
        # Save test content with searchable titles
        contents = [
            self.create_test_content(
                url=f"https://test{i}.com/video",
                title=f"Amazing Video {i}",
                author=f"Creator {i}"
            )
            for i in range(1, 4)
        ]
        
        for content in contents:
            self.repository.save(content)
        
        # Search by title
        title_results = self.repository.search_content("Amazing")
        self.assertEqual(len(title_results), 3)
        
        # Search by author
        author_results = self.repository.search_content("Creator 2")
        self.assertEqual(len(author_results), 1)
        self.assertEqual(author_results[0].author, "Creator 2")
    
    def test_get_platform_stats(self):
        """Test platform statistics functionality"""
        # Save content for different platforms with different statuses
        test_data = [
            (PlatformType.TIKTOK, ContentStatus.COMPLETED),
            (PlatformType.TIKTOK, ContentStatus.PENDING),
            (PlatformType.YOUTUBE, ContentStatus.COMPLETED),
            (PlatformType.YOUTUBE, ContentStatus.FAILED),
        ]
        
        for i, (platform, status) in enumerate(test_data):
            content = self.create_test_content(
                url=f"https://test{i}.com/video",
                platform=platform,
                status=status
            )
            self.repository.save(content)
        
        # Get platform stats
        stats = self.repository.get_platform_stats()
        
        self.assertIn(PlatformType.TIKTOK, stats)
        self.assertIn(PlatformType.YOUTUBE, stats)
        
        # Check TikTok stats
        tiktok_stats = stats[PlatformType.TIKTOK]
        self.assertEqual(tiktok_stats["total"], 2)
        self.assertEqual(tiktok_stats["completed"], 1)
        self.assertEqual(tiktok_stats["pending"], 1)
        
        # Check YouTube stats
        youtube_stats = stats[PlatformType.YOUTUBE]
        self.assertEqual(youtube_stats["total"], 2)
        self.assertEqual(youtube_stats["completed"], 1)
        self.assertEqual(youtube_stats["failed"], 1)
    
    def test_delete_by_id(self):
        """Test deleting content by ID"""
        # Save test content
        content = self.create_test_content()
        saved_content = self.repository.save(content)
        content_id = saved_content.id
        
        # Verify it exists
        self.assertTrue(self.repository.exists(content_id))
        
        # Delete it
        result = self.repository.delete_by_id(content_id)
        self.assertTrue(result)
        
        # Verify it's gone
        self.assertFalse(self.repository.exists(content_id))
        self.assertIsNone(self.repository.find_by_id(content_id))
    
    def test_exists_method(self):
        """Test exists method"""
        # Non-existent ID
        self.assertFalse(self.repository.exists(99999))
        
        # Save content and test exists
        content = self.create_test_content()
        saved_content = self.repository.save(content)
        
        self.assertTrue(self.repository.exists(saved_content.id))
    
    def test_count_method(self):
        """Test count method"""
        # Initially should be 0
        self.assertEqual(self.repository.count(), 0)
        
        # Save some content
        for i in range(3):
            content = self.create_test_content(url=f"https://test{i}.com/video")
            self.repository.save(content)
        
        # Should now be 3
        self.assertEqual(self.repository.count(), 3)
    
    def test_find_all_with_pagination(self):
        """Test find_all with pagination"""
        # Save test content
        for i in range(10):
            content = self.create_test_content(
                url=f"https://test{i}.com/video",
                title=f"Video {i}"
            )
            self.repository.save(content)
        
        # Test pagination
        page1 = self.repository.find_all(limit=5, offset=0)
        page2 = self.repository.find_all(limit=5, offset=5)
        
        self.assertEqual(len(page1), 5)
        self.assertEqual(len(page2), 5)
        
        # Ensure different results
        page1_ids = {content.id for content in page1}
        page2_ids = {content.id for content in page2}
        self.assertEqual(len(page1_ids.intersection(page2_ids)), 0)


class TestRepositoryErrorHandling(RepositoryTestCase):
    """Test repository error handling and edge cases"""
    
    def test_save_invalid_content(self):
        """Test saving invalid content raises appropriate error"""
        # Content with missing required fields
        with self.assert_raises_database_error(DatabaseErrorCode.MODEL_VALIDATION_FAILED):
            invalid_content = ContentModel(url="")  # Empty URL should fail validation
            self.repository.save(invalid_content)
    
    def test_duplicate_url_handling(self):
        """Test handling of duplicate URLs"""
        # Save first content
        content1 = self.create_test_content(url="https://duplicate.com/video")
        saved_content1 = self.repository.save(content1)
        
        # Try to save content with same URL
        content2 = self.create_test_content(url="https://duplicate.com/video")
        
        with self.assert_raises_database_error(DatabaseErrorCode.SQL_UNIQUE_CONSTRAINT_VIOLATION):
            self.repository.save(content2)
    
    def test_concurrent_access(self):
        """Test concurrent repository access"""
        def save_content(worker_id):
            content = self.create_test_content(
                url=f"https://concurrent{worker_id}.com/video",
                title=f"Concurrent Video {worker_id}"
            )
            return self.repository.save(content)
        
        # Run concurrent operations
        results = simulate_concurrent_operations(
            [lambda i=i: save_content(i) for i in range(5)],
            num_threads=5
        )
        
        # All operations should succeed
        self.assertEqual(len(results), 5)
        self.assertTrue(all(result is not None for result in results))
        
        # All should have unique IDs
        ids = [result.id for result in results]
        self.assertEqual(len(set(ids)), 5)


class TestMockRepositoryTesting(MockDatabaseTestCase):
    """Test repository functionality with mocked database"""
    
    def setUp(self):
        """Setup mock repository testing"""
        super().setUp()
        
        # Create mock model manager
        self.mock_model_manager = self.create_mock("model_manager")
        self.repository = ContentRepository(self.mock_model_manager)
    
    def test_save_with_mock(self):
        """Test repository save with mocked database"""
        # Setup mock behavior
        content = ContentModel(
            url="https://test.com/video",
            platform=PlatformType.TIKTOK,
            content_type=ContentType.VIDEO,
            title="Test Video",
            author="Test Author",
            platform_id="test123"
        )
        
        # Mock the save operation
        self.mock_model_manager.save.return_value = content
        
        # Call repository save
        result = self.repository.save(content)
        
        # Verify mock was called correctly
        self.mock_model_manager.save.assert_called_once_with(content)
        self.assertEqual(result, content)
    
    def test_find_by_id_with_mock(self):
        """Test find_by_id with mocked database"""
        # Setup mock return value
        expected_content = ContentModel(
            id=1,
            url="https://test.com/video",
            platform=PlatformType.TIKTOK,
            content_type=ContentType.VIDEO,
            title="Test Video",
            author="Test Author",
            platform_id="test123"
        )
        
        self.mock_model_manager.find_by_id.return_value = expected_content
        
        # Call repository method
        result = self.repository.find_by_id(1)
        
        # Verify mock interaction
        self.mock_model_manager.find_by_id.assert_called_once_with(1)
        self.assertEqual(result, expected_content)
    
    def test_repository_error_propagation(self):
        """Test that repository properly propagates model manager errors"""
        # Setup mock to raise error
        self.mock_model_manager.save.side_effect = RepositoryError("Mock error")
        
        content = ContentModel(
            url="https://test.com/video",
            platform=PlatformType.TIKTOK,
            content_type=ContentType.VIDEO,
            title="Test Video",
            author="Test Author",
            platform_id="test123"
        )
        
        # Should propagate the error
        with self.assertRaises(RepositoryError):
            self.repository.save(content)


class TestRepositoryPerformance(PerformanceTestCase):
    """Test repository performance characteristics"""
    
    def setUp(self):
        """Setup repository for performance testing"""
        super().setUp()
        
        # Setup repository
        from data.models import ContentModelManager
        self.model_manager = ContentModelManager(self.connection_manager)
        self.model_manager.create_table()
        self.repository = ContentRepository(self.model_manager)
    
    def test_bulk_insert_performance(self):
        """Test performance of bulk insert operations"""
        num_records = 100
        
        with self.performance_benchmark("bulk_insert") as metrics:
            for i in range(num_records):
                content = ContentModel(
                    url=f"https://performance{i}.com/video",
                    platform=PlatformType.TIKTOK,
                    content_type=ContentType.VIDEO,
                    title=f"Performance Video {i}",
                    author=f"Author {i}",
                    platform_id=f"perf{i}"
                )
                self.repository.save(content)
        
        # Performance assertions
        self.assertLess(metrics["execution_time"], 5.0)  # Should complete in under 5 seconds
        
        # Verify all records were inserted
        count = self.repository.count()
        self.assertEqual(count, num_records)
    
    def test_search_performance(self):
        """Test search performance with large dataset"""
        # Insert test data
        for i in range(50):
            content = ContentModel(
                url=f"https://search{i}.com/video",
                platform=PlatformType.TIKTOK,
                content_type=ContentType.VIDEO,
                title=f"Searchable Video {i}",
                author=f"Searchable Author {i}",
                platform_id=f"search{i}"
            )
            self.repository.save(content)
        
        # Test search performance
        with self.performance_benchmark("search_operation") as metrics:
            results = self.repository.search_content("Searchable")
        
        # Performance assertions
        self.assertLess(metrics["execution_time"], 0.1)  # Search should be fast
        self.assertEqual(len(results), 50)
    
    def test_query_optimization(self):
        """Test that repository uses optimized queries"""
        # Insert test data
        for i in range(20):
            content = ContentModel(
                url=f"https://query{i}.com/video",
                platform=PlatformType.TIKTOK if i % 2 == 0 else PlatformType.YOUTUBE,
                content_type=ContentType.VIDEO,
                title=f"Query Video {i}",
                author=f"Query Author {i}",
                platform_id=f"query{i}"
            )
            self.repository.save(content)
        
        # Reset query statistics
        if self.logger:
            self.logger.reset_statistics()
        
        # Perform various repository operations
        self.repository.find_by_platform(PlatformType.TIKTOK)
        self.repository.find_by_status(ContentStatus.PENDING)
        self.repository.get_platform_stats()
        
        # Check performance metrics
        self.assert_performance_thresholds()
        self.assert_no_slow_queries(threshold_ms=50.0)


if __name__ == '__main__':
    unittest.main() 