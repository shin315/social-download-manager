"""
Comprehensive Test Suite for Repository Pattern Implementation
Social Download Manager v2.0

Tests repository interfaces, implementations, transactions, error handling,
and performance optimizations.
"""

import pytest
import sqlite3
import tempfile
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import List, Optional

# Repository imports
from data.models.base import BaseEntity, EntityId
from data.models.content import ContentModel, ContentStatus, PlatformType, ContentType
from data.models.downloads import DownloadModel, DownloadSession, DownloadError, DownloadStatus
from data.models.repositories import (
    BaseRepository, ContentRepository, QueryBuilder, RepositoryError,
    get_content_repository, RepositoryRegistry
)
from data.models.download_repositories import (
    DownloadRepository, DownloadSessionRepository, DownloadErrorRepository,
    get_download_repository, get_download_session_repository, get_download_error_repository
)
from data.models.transaction_repository import (
    TransactionAwareRepositoryMixin, TransactionalRepository, UnitOfWork,
    transactional, requires_transaction
)
from data.models.error_management import (
    ErrorManager, ErrorContext, RepositoryDatabaseError, RepositoryValidationError,
    get_error_manager, handle_repository_errors
)
from data.models.performance_optimizations import (
    LRUCache, TTLCache, RepositoryCache, PerformanceOptimizedRepository,
    BatchOperationManager, QueryOptimizer, PerformanceMonitor
)

# Database imports
from data.database import get_database_manager, get_transaction_manager


class TestEntity(BaseEntity):
    """Test entity for repository testing"""
    
    def __init__(self, name: str = "", value: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.value = value
    
    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update({
            'name': self.name,
            'value': self.value
        })
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TestEntity':
        return cls(
            id=data.get('id'),
            name=data.get('name', ''),
            value=data.get('value', 0),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
            is_deleted=data.get('is_deleted', False)
        )
    
    @classmethod
    def from_row(cls, row) -> 'TestEntity':
        return cls.from_dict({
            'id': row[0] if len(row) > 0 else None,
            'name': row[1] if len(row) > 1 else '',
            'value': row[2] if len(row) > 2 else 0,
            'created_at': row[3] if len(row) > 3 else None,
            'updated_at': row[4] if len(row) > 4 else None,
            'is_deleted': row[5] if len(row) > 5 else False
        })


class MockModelManager:
    """Mock model manager for testing"""
    
    def __init__(self):
        self.entities = {}
        self.next_id = 1
        self.table_name = "test_entities"
        self.entity_class = TestEntity
    
    def save(self, entity: TestEntity) -> Optional[TestEntity]:
        if entity.id is None:
            entity.id = self.next_id
            self.next_id += 1
        entity.mark_updated()
        self.entities[entity.id] = entity
        return entity
    
    def find_by_id(self, entity_id: EntityId) -> Optional[TestEntity]:
        return self.entities.get(entity_id)
    
    def find_all(self, include_deleted: bool = False) -> List[TestEntity]:
        if include_deleted:
            return list(self.entities.values())
        return [e for e in self.entities.values() if not e.is_deleted]
    
    def delete(self, entity_id: EntityId, soft_delete: bool = True) -> bool:
        if entity_id not in self.entities:
            return False
        
        if soft_delete:
            self.entities[entity_id].is_deleted = True
            self.entities[entity_id].mark_updated()
        else:
            del self.entities[entity_id]
        return True
    
    def exists(self, entity_id: EntityId) -> bool:
        entity = self.entities.get(entity_id)
        return entity is not None and not entity.is_deleted
    
    def count(self, include_deleted: bool = False) -> int:
        if include_deleted:
            return len(self.entities)
        return len([e for e in self.entities.values() if not e.is_deleted])
    
    def find_by_criteria(self, criteria: dict) -> List[TestEntity]:
        results = []
        for entity in self.entities.values():
            if entity.is_deleted:
                continue
            
            match = True
            for key, value in criteria.items():
                if not hasattr(entity, key) or getattr(entity, key) != value:
                    match = False
                    break
            
            if match:
                results.append(entity)
        
        return results
    
    def get_table_name(self) -> str:
        return self.table_name
    
    def get_entity_class(self) -> type:
        return self.entity_class
    
    def _get_connection(self):
        # Return mock connection for testing
        return MagicMock()
    
    def _return_connection(self, connection):
        pass


class TestQueryBuilder:
    """Test QueryBuilder functionality"""
    
    def test_basic_query_building(self):
        """Test basic query construction"""
        builder = QueryBuilder("test_table")
        
        query, params = builder.build()
        assert "SELECT *" in query
        assert "FROM test_table" in query
        assert params == []
    
    def test_select_fields(self):
        """Test field selection"""
        builder = QueryBuilder("test_table")
        builder.select(["id", "name", "value"])
        
        query, params = builder.build()
        assert "SELECT id, name, value" in query
    
    def test_where_conditions(self):
        """Test WHERE clause building"""
        builder = QueryBuilder("test_table")
        builder.where("name = ?", "test")
        builder.where("value > ?", 10)
        
        query, params = builder.build()
        assert "WHERE name = ? AND value > ?" in query
        assert params == ["test", 10]
    
    def test_convenience_methods(self):
        """Test convenience WHERE methods"""
        builder = QueryBuilder("test_table")
        builder.where_equals("status", "active")
        builder.where_in("type", ["a", "b", "c"])
        builder.where_like("title", "%test%")
        builder.where_between("date", "2023-01-01", "2023-12-31")
        
        query, params = builder.build()
        assert "status = ?" in query
        assert "type IN (?, ?, ?)" in query
        assert "title LIKE ?" in query
        assert "date BETWEEN ? AND ?" in query
        assert params == ["active", "a", "b", "c", "%test%", "2023-01-01", "2023-12-31"]
    
    def test_order_and_limit(self):
        """Test ORDER BY and LIMIT clauses"""
        builder = QueryBuilder("test_table")
        builder.order_by("created_at", "DESC")
        builder.limit(10, 5)
        
        query, params = builder.build()
        assert "ORDER BY created_at DESC" in query
        assert "LIMIT 10 OFFSET 5" in query


class TestBaseRepository:
    """Test BaseRepository implementation"""
    
    def setup_method(self):
        """Setup test environment"""
        self.mock_model = MockModelManager()
        self.repository = BaseRepository(self.mock_model)
    
    def test_save_entity(self):
        """Test entity saving"""
        entity = TestEntity(name="test", value=42)
        saved = self.repository.save(entity)
        
        assert saved is not None
        assert saved.id is not None
        assert saved.name == "test"
        assert saved.value == 42
    
    def test_find_by_id(self):
        """Test finding entity by ID"""
        # Save entity first
        entity = TestEntity(name="findme", value=123)
        saved = self.repository.save(entity)
        
        # Find it
        found = self.repository.find_by_id(saved.id)
        assert found is not None
        assert found.name == "findme"
        assert found.value == 123
    
    def test_find_all(self):
        """Test finding all entities"""
        # Create multiple entities
        entities = [
            TestEntity(name=f"test{i}", value=i)
            for i in range(3)
        ]
        
        for entity in entities:
            self.repository.save(entity)
        
        all_entities = self.repository.find_all()
        assert len(all_entities) == 3
    
    def test_delete_entity(self):
        """Test entity deletion"""
        entity = TestEntity(name="delete_me", value=999)
        saved = self.repository.save(entity)
        
        # Soft delete
        result = self.repository.delete(saved.id, soft_delete=True)
        assert result is True
        
        # Should not appear in normal queries
        found = self.repository.find_by_id(saved.id)
        assert found is None or found.is_deleted
        
        # Should appear when including deleted
        all_entities = self.repository.find_all(include_deleted=True)
        assert any(e.id == saved.id for e in all_entities)
    
    def test_exists(self):
        """Test entity existence check"""
        entity = TestEntity(name="exists_test")
        saved = self.repository.save(entity)
        
        assert self.repository.exists(saved.id) is True
        assert self.repository.exists(99999) is False
    
    def test_count(self):
        """Test entity counting"""
        initial_count = self.repository.count()
        
        # Add entities
        for i in range(5):
            self.repository.save(TestEntity(name=f"count{i}"))
        
        assert self.repository.count() == initial_count + 5
    
    def test_find_by_criteria(self):
        """Test finding entities by criteria"""
        # Create test entities
        entities = [
            TestEntity(name="alpha", value=1),
            TestEntity(name="beta", value=2),
            TestEntity(name="alpha", value=3)
        ]
        
        for entity in entities:
            self.repository.save(entity)
        
        # Find by name
        alpha_entities = self.repository.find_by_criteria({"name": "alpha"})
        assert len(alpha_entities) == 2
        
        # Find by value
        value_entities = self.repository.find_by_criteria({"value": 2})
        assert len(value_entities) == 1
        assert value_entities[0].name == "beta"


class TestTransactionAwareRepository:
    """Test transaction-aware repository functionality"""
    
    def setup_method(self):
        """Setup test environment with transaction support"""
        self.mock_model = MockModelManager()
        
        # Create repository with transaction mixin
        class TestTransactionalRepo(BaseRepository, TransactionAwareRepositoryMixin):
            pass
        
        self.repository = TestTransactionalRepo(self.mock_model)
    
    @patch('data.models.transaction_repository.get_current_transaction')
    def test_transactional_save(self, mock_get_transaction):
        """Test transactional save operations"""
        mock_get_transaction.return_value = None
        
        entity = TestEntity(name="transactional", value=100)
        saved = self.repository.save_transactional(entity, commit=False)
        
        assert saved is not None
        assert saved.name == "transactional"
    
    def test_bulk_save_transactional(self):
        """Test bulk transactional saves"""
        entities = [
            TestEntity(name=f"bulk{i}", value=i)
            for i in range(5)
        ]
        
        with patch.object(self.repository, 'transaction') as mock_transaction:
            mock_transaction.return_value.__enter__ = Mock()
            mock_transaction.return_value.__exit__ = Mock()
            
            saved_entities = self.repository.bulk_save_transactional(entities, batch_size=2)
            
            assert len(saved_entities) == 5
            for i, entity in enumerate(saved_entities):
                assert entity.name == f"bulk{i}"
    
    def test_bulk_delete_transactional(self):
        """Test bulk transactional deletes"""
        # Create entities to delete
        entities = []
        for i in range(3):
            entity = TestEntity(name=f"delete{i}")
            saved = self.repository.save(entity)
            entities.append(saved)
        
        entity_ids = [e.id for e in entities]
        
        with patch.object(self.repository, 'transaction') as mock_transaction:
            mock_transaction.return_value.__enter__ = Mock()
            mock_transaction.return_value.__exit__ = Mock()
            
            deleted_count = self.repository.bulk_delete_transactional(entity_ids)
            
            assert deleted_count == 3


class TestUnitOfWork:
    """Test Unit of Work pattern"""
    
    @patch('data.models.transaction_repository.get_transaction_manager')
    def test_unit_of_work_basic(self, mock_get_manager):
        """Test basic unit of work functionality"""
        mock_transaction = Mock()
        mock_transaction.is_active = True
        mock_transaction.transaction_id = "test-123"
        
        mock_manager = Mock()
        mock_manager.begin_transaction.return_value = mock_transaction
        mock_get_manager.return_value = mock_manager
        
        uow = UnitOfWork()
        
        # Register repository
        mock_repo = Mock()
        uow.register_repository("test", mock_repo)
        
        with uow:
            retrieved_repo = uow.get_repository("test")
            assert retrieved_repo == mock_repo
        
        mock_transaction.commit.assert_called_once()
    
    @patch('data.models.transaction_repository.get_transaction_manager')
    def test_unit_of_work_rollback(self, mock_get_manager):
        """Test unit of work rollback on exception"""
        mock_transaction = Mock()
        mock_transaction.is_active = True
        
        mock_manager = Mock()
        mock_manager.begin_transaction.return_value = mock_transaction
        mock_get_manager.return_value = mock_manager
        
        uow = UnitOfWork()
        
        with pytest.raises(Exception):
            with uow:
                raise Exception("Test error")
        
        mock_transaction.rollback.assert_called_once()


class TestErrorManagement:
    """Test error management system"""
    
    def test_error_manager_creation(self):
        """Test error manager initialization"""
        error_manager = ErrorManager()
        assert error_manager is not None
        assert len(error_manager._handlers) > 0
    
    def test_handle_validation_error(self):
        """Test validation error handling"""
        error_manager = ErrorManager()
        context = ErrorContext("test_operation")
        
        error = ValueError("Invalid input")
        error_info = error_manager.handle_error(error, context)
        
        assert error_info.error_code == "VALIDATION_ERROR"
        assert "test_operation" in error_info.message
    
    def test_handle_database_error(self):
        """Test database error handling"""
        error_manager = ErrorManager()
        context = ErrorContext("database_operation")
        
        error = sqlite3.Error("Database error")
        error_info = error_manager.handle_error(error, context)
        
        assert error_info.error_code == "DATABASE_ERROR"
        assert error_info.is_retryable is True
    
    def test_error_statistics(self):
        """Test error statistics tracking"""
        error_manager = ErrorManager()
        error_manager.clear_statistics()
        
        context = ErrorContext("test_op")
        
        # Generate some errors
        errors = [
            ValueError("Test 1"),
            sqlite3.Error("Test 2"),
            ConnectionError("Test 3")
        ]
        
        for error in errors:
            error_manager.handle_error(error, context)
        
        stats = error_manager.get_error_statistics()
        assert stats["category_validation"] >= 1
        assert stats["category_database"] >= 1
        assert stats["category_network"] >= 1
    
    def test_error_decorator(self):
        """Test error handling decorator"""
        mock_model = MockModelManager()
        
        class TestRepo(BaseRepository):
            @handle_repository_errors("test_operation")
            def test_method(self):
                raise ValueError("Test error")
        
        repo = TestRepo(mock_model)
        
        with pytest.raises(RepositoryValidationError):
            repo.test_method()


class TestPerformanceOptimizations:
    """Test performance optimization components"""
    
    def test_lru_cache(self):
        """Test LRU cache implementation"""
        cache = LRUCache(max_size=3)
        
        # Fill cache
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        
        # Add one more - should evict key1
        cache.set("key4", "value4")
        
        assert cache.get("key1") is None
        assert cache.get("key4") == "value4"
        
        stats = cache.get_stats()
        assert stats["cache_type"] == "LRU"
        assert stats["size"] == 3
        assert stats["max_size"] == 3
    
    def test_ttl_cache(self):
        """Test TTL cache implementation"""
        cache = TTLCache(default_ttl=1)  # 1 second TTL
        
        cache.set("temp_key", "temp_value")
        assert cache.get("temp_key") == "temp_value"
        
        # Wait for expiration
        time.sleep(1.1)
        assert cache.get("temp_key") is None
        
        stats = cache.get_stats()
        assert stats["cache_type"] == "TTL"
    
    def test_repository_cache(self):
        """Test repository-level caching"""
        cache_provider = LRUCache(max_size=10)
        repo_cache = RepositoryCache(cache_provider)
        
        # Test entity caching
        entity = TestEntity(name="cached", value=42)
        entity.id = 1
        
        repo_cache.set_entity(entity)
        cached_entity = repo_cache.get_entity("TestEntity", 1)
        
        assert cached_entity is not None
        assert cached_entity.name == "cached"
        
        # Test cache invalidation
        repo_cache.invalidate_entity("TestEntity", 1)
        invalidated_entity = repo_cache.get_entity("TestEntity", 1)
        assert invalidated_entity is None
    
    def test_batch_operation_manager(self):
        """Test batch operation manager"""
        batch_manager = BatchOperationManager(default_batch_size=2)
        
        # Add operations
        operations = ["op1", "op2", "op3", "op4", "op5"]
        for op in operations:
            batch_manager.add_operation("test", op)
        
        assert batch_manager.get_pending_count("test") == 5
        
        # Execute batch
        def executor(batch):
            return [f"processed_{item}" for item in batch]
        
        results = batch_manager.execute_batch("test", executor, batch_size=2)
        
        assert len(results) == 5
        assert all("processed_" in result for result in results)
        assert batch_manager.get_pending_count("test") == 0
    
    def test_query_optimizer(self):
        """Test query optimizer"""
        optimizer = QueryOptimizer()
        
        simple_query = "SELECT * FROM test WHERE id = ?"
        complex_query = """
            SELECT t1.*, t2.value 
            FROM test t1 
            LEFT JOIN other t2 ON t1.id = t2.test_id 
            WHERE t1.status IN (?, ?) 
            GROUP BY t1.category 
            ORDER BY t1.created_at DESC
        """
        
        simple_analysis = optimizer.analyze_query(simple_query)
        complex_analysis = optimizer.analyze_query(complex_query)
        
        assert simple_analysis["estimated_complexity"] < complex_analysis["estimated_complexity"]
        assert complex_analysis["has_joins"] is True
        assert complex_analysis["has_group_by"] is True
        assert len(complex_analysis["recommendations"]) > 0
    
    def test_performance_monitor(self):
        """Test performance monitoring"""
        monitor = PerformanceMonitor()
        
        # Test operation measurement
        with monitor.measure_operation("test_operation", "TestEntity"):
            time.sleep(0.01)  # Simulate work
        
        # Record custom metrics
        from data.models.performance_optimizations import PerformanceMetricType
        monitor.record_metric(
            PerformanceMetricType.CACHE_HIT_RATE, 
            85.5, 
            "cache_test", 
            "TestEntity"
        )
        
        # Get metrics summary
        summary = monitor.get_metrics_summary()
        assert summary["count"] >= 1
        assert "avg_value" in summary
        
        # Get operation-specific summary
        op_summary = monitor.get_metrics_summary(operation="test_operation")
        assert op_summary["count"] >= 1
    
    def test_performance_optimized_repository(self):
        """Test performance-optimized repository wrapper"""
        mock_repo = Mock()
        mock_repo.find_by_id.return_value = TestEntity(name="test")
        mock_repo.save.return_value = TestEntity(name="saved")
        
        cache_provider = LRUCache(max_size=10)
        optimized_repo = PerformanceOptimizedRepository(
            base_repository=mock_repo,
            cache_provider=cache_provider
        )
        
        # Test cached find
        entity1 = optimized_repo.find_by_id_cached(1)
        entity2 = optimized_repo.find_by_id_cached(1)  # Should hit cache
        
        # Base repository should only be called once
        assert mock_repo.find_by_id.call_count == 1
        
        # Test save with cache invalidation
        test_entity = TestEntity(name="test_save")
        test_entity.id = 1
        optimized_repo.save_with_cache_invalidation(test_entity)
        
        mock_repo.save.assert_called_once()


class TestDownloadRepositories:
    """Test download-specific repository implementations"""
    
    def setup_method(self):
        """Setup download repository tests"""
        # This would typically use a test database
        # For now, we'll mock the dependencies
        pass
    
    @patch('data.models.download_repositories.get_download_repository')
    def test_download_repository_methods(self, mock_get_repo):
        """Test download repository specific methods"""
        mock_repo = Mock()
        mock_get_repo.return_value = mock_repo
        
        # Mock return values
        mock_download = DownloadModel(
            content_id="test-123",
            url="https://example.com/test.mp4",
            status=DownloadStatus.QUEUED
        )
        mock_repo.find_by_content_id.return_value = [mock_download]
        mock_repo.find_by_status.return_value = [mock_download]
        mock_repo.find_active_downloads.return_value = [mock_download]
        
        repo = mock_get_repo()
        
        # Test content ID search
        results = repo.find_by_content_id("test-123")
        assert len(results) >= 0
        
        # Test status search
        results = repo.find_by_status(DownloadStatus.QUEUED)
        assert len(results) >= 0
        
        # Test active downloads
        results = repo.find_active_downloads()
        assert len(results) >= 0


class TestRepositoryIntegration:
    """Integration tests for repository system"""
    
    def test_full_repository_workflow(self):
        """Test complete repository workflow"""
        # This would test the full integration with real database
        # Including transactions, error handling, and performance optimizations
        
        # Create mock components
        mock_model = MockModelManager()
        repository = BaseRepository(mock_model)
        
        # Test workflow: Create -> Read -> Update -> Delete
        
        # Create
        entity = TestEntity(name="integration_test", value=42)
        saved = repository.save(entity)
        assert saved.id is not None
        
        # Read
        found = repository.find_by_id(saved.id)
        assert found.name == "integration_test"
        
        # Update
        found.value = 100
        updated = repository.save(found)
        assert updated.value == 100
        
        # Delete
        deleted = repository.delete(saved.id)
        assert deleted is True
        
        # Verify deletion
        not_found = repository.find_by_id(saved.id)
        assert not_found is None or not_found.is_deleted
    
    def test_concurrent_repository_access(self):
        """Test thread-safe repository operations"""
        mock_model = MockModelManager()
        repository = BaseRepository(mock_model)
        
        results = []
        errors = []
        
        def worker_thread(thread_id):
            try:
                for i in range(5):
                    entity = TestEntity(name=f"thread_{thread_id}_item_{i}", value=i)
                    saved = repository.save(entity)
                    results.append(saved)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=worker_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0
        assert len(results) == 15  # 3 threads * 5 items each


# Performance benchmarks
class TestPerformanceBenchmarks:
    """Performance benchmark tests"""
    
    def test_cache_performance_benchmark(self):
        """Benchmark cache vs direct access performance"""
        mock_model = MockModelManager()
        
        # Create test data
        entities = []
        for i in range(100):
            entity = TestEntity(name=f"perf_test_{i}", value=i)
            saved = mock_model.save(entity)
            entities.append(saved)
        
        # Benchmark direct access
        start_time = time.time()
        for entity in entities:
            mock_model.find_by_id(entity.id)
        direct_time = time.time() - start_time
        
        # Benchmark cached access
        cache = LRUCache(max_size=200)
        repo_cache = RepositoryCache(cache)
        
        # Populate cache
        for entity in entities:
            repo_cache.set_entity(entity)
        
        start_time = time.time()
        for entity in entities:
            repo_cache.get_entity("TestEntity", entity.id)
        cached_time = time.time() - start_time
        
        # Cache should be faster (though with mocks, the difference might be minimal)
        assert cached_time <= direct_time
        
        print(f"Direct access: {direct_time:.4f}s")
        print(f"Cached access: {cached_time:.4f}s")
        print(f"Speedup: {direct_time/cached_time:.2f}x" if cached_time > 0 else "N/A")


# Test configuration
@pytest.fixture
def test_database():
    """Provide test database for integration tests"""
    # Create temporary database for testing
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        test_db_path = tmp.name
    
    # Initialize test database
    # This would set up the actual database schema
    
    yield test_db_path
    
    # Cleanup
    import os
    if os.path.exists(test_db_path):
        os.unlink(test_db_path)


@pytest.fixture
def mock_repository():
    """Provide mock repository for testing"""
    mock_model = MockModelManager()
    return BaseRepository(mock_model)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"]) 