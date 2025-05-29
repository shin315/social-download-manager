# Repository Pattern Implementation
## Social Download Manager v2.0

### Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [Usage Examples](#usage-examples)
5. [Advanced Features](#advanced-features)
6. [Best Practices](#best-practices)
7. [Performance Optimization](#performance-optimization)
8. [Testing](#testing)

## Overview

The Repository Pattern implementation in Social Download Manager v2.0 provides a clean abstraction layer for data access operations. It separates business logic from data access logic, making the system more maintainable, testable, and flexible.

### Key Benefits
- **Separation of Concerns**: Clear separation between business and data access logic
- **Testability**: Easy to mock and test business logic
- **Consistency**: Standardized data access patterns across the application
- **Performance**: Built-in caching and optimization features
- **Transaction Support**: Comprehensive transaction management
- **Error Handling**: Robust error management with recovery strategies

## Architecture

```
┌─────────────────────┐
│   Business Logic    │
└─────────┬───────────┘
          │
┌─────────▼───────────┐
│  Repository Layer   │
├─────────────────────┤
│ • Base Repository   │
│ • Content Repo      │
│ • Download Repo     │
│ • Session Repo      │
│ • Error Repo        │
└─────────┬───────────┘
          │
┌─────────▼───────────┐
│   Model Layer       │
├─────────────────────┤
│ • Entity Models     │
│ • Model Managers    │
│ • Validation        │
└─────────┬───────────┘
          │
┌─────────▼───────────┐
│  Database Layer     │
├─────────────────────┤
│ • SQLite Database   │
│ • Connection Pool   │
│ • Transactions      │
└─────────────────────┘
```

## Core Components

### 1. Repository Interfaces

#### Base Repository Interface (`IRepository[T]`)
```python
from data.models.repositories import IRepository
from data.models.base import BaseEntity, EntityId

class IRepository(ABC, Generic[T]):
    """Generic repository interface"""
    
    def save(self, entity: T) -> Optional[T]:
        """Save entity (insert or update)"""
        pass
    
    def find_by_id(self, entity_id: EntityId) -> Optional[T]:
        """Find entity by ID"""
        pass
    
    def find_all(self, include_deleted: bool = False) -> List[T]:
        """Find all entities"""
        pass
    
    def delete(self, entity_id: EntityId, soft_delete: bool = True) -> bool:
        """Delete entity by ID"""
        pass
    
    def exists(self, entity_id: EntityId) -> bool:
        """Check if entity exists"""
        pass
    
    def count(self, include_deleted: bool = False) -> int:
        """Count total entities"""
        pass
```

#### Content Repository Interface (`IContentRepository`)
```python
from data.models.repositories import IContentRepository

class IContentRepository(IRepository[ContentModel]):
    """Content-specific repository interface"""
    
    def find_by_url(self, url: str) -> Optional[ContentModel]:
        """Find content by URL"""
        pass
    
    def find_by_platform(self, platform: PlatformType) -> List[ContentModel]:
        """Find content by platform"""
        pass
    
    def search_content(self, search_term: str) -> List[ContentModel]:
        """Search content by title, description, or author"""
        pass
```

### 2. Repository Implementations

#### Base Repository
```python
from data.models.repositories import BaseRepository

class BaseRepository(IRepository[T]):
    """Base repository implementation with common functionality"""
    
    def __init__(self, model_manager):
        self._model = model_manager
        self._logger = logging.getLogger(self.__class__.__name__)
    
    @handle_repository_errors("save_entity")
    def save(self, entity: T) -> Optional[T]:
        """Save entity with error handling"""
        return self._model.save(entity)
```

#### Content Repository
```python
from data.models.repositories import ContentRepository, get_content_repository

# Get repository instance
content_repo = get_content_repository()

# Basic operations
content = ContentModel(url="https://example.com/video", platform=PlatformType.YOUTUBE)
saved_content = content_repo.save(content)

# Specialized queries
youtube_content = content_repo.find_by_platform(PlatformType.YOUTUBE)
search_results = content_repo.search_content("music video")
```

### 3. Download Repositories

#### Download Repository
```python
from data.models.download_repositories import get_download_repository

download_repo = get_download_repository()

# Find by status
queued_downloads = download_repo.find_by_status(DownloadStatus.QUEUED)
active_downloads = download_repo.find_active_downloads()

# Statistics
stats = download_repo.get_download_statistics()
print(f"Success rate: {stats['success_rate']:.2f}%")
```

#### Download Session Repository
```python
from data.models.download_repositories import get_download_session_repository

session_repo = get_download_session_repository()

# Find active sessions
active_sessions = session_repo.find_active_sessions()

# Find stalled sessions
stalled_sessions = session_repo.find_stalled_sessions(timeout_minutes=30)

# Performance stats
perf_stats = session_repo.get_session_performance_stats()
```

## Usage Examples

### Basic CRUD Operations

```python
from data.models.repositories import get_content_repository
from data.models.content import ContentModel, PlatformType, ContentStatus

# Get repository
repo = get_content_repository()

# Create
content = ContentModel(
    url="https://youtube.com/watch?v=123",
    platform=PlatformType.YOUTUBE,
    status=ContentStatus.PENDING
)
saved = repo.save(content)

# Read
found = repo.find_by_id(saved.id)
all_content = repo.find_all()

# Update
found.status = ContentStatus.COMPLETED
updated = repo.save(found)

# Delete
repo.delete(saved.id, soft_delete=True)
```

### Advanced Queries

```python
# Query builder
query_builder = repo.query()
query, params = (query_builder
                .where_equals("platform", PlatformType.YOUTUBE.value)
                .where_in("status", ["pending", "downloading"])
                .order_by("created_at", "DESC")
                .limit(10)
                .build())

results = repo.execute_query(query, params)

# Search functionality
search_results = repo.search_content("music")
platform_content = repo.find_by_platform(PlatformType.TIKTOK)
recent_content = repo.find_recent_content(days=7)
```

### Pagination

```python
from data.models.download_repositories import get_download_repository

download_repo = get_download_repository()

# Paginated results
page_data = download_repo.find_downloads_with_pagination(
    page=1, 
    page_size=20, 
    status=DownloadStatus.COMPLETED
)

print(f"Page {page_data['pagination']['page']} of {page_data['pagination']['total_pages']}")
print(f"Total items: {page_data['pagination']['total_count']}")

for download in page_data['items']:
    print(f"Download: {download.url}")
```

## Advanced Features

### 1. Transaction Management

#### Basic Transactions
```python
from data.models.transaction_repository import TransactionAwareRepositoryMixin

class MyRepository(BaseRepository, TransactionAwareRepositoryMixin):
    pass

repo = MyRepository(model_manager)

# Automatic transaction
with repo.transaction() as trans:
    entity1 = repo.save(EntityModel(name="test1"))
    entity2 = repo.save(EntityModel(name="test2"))
    # Commits automatically on success, rolls back on exception
```

#### Unit of Work Pattern
```python
from data.models.transaction_repository import UnitOfWork

uow = UnitOfWork()
uow.register_repository('downloads', download_repo)
uow.register_repository('sessions', session_repo)

with uow:
    downloads = uow.get_repository('downloads')
    sessions = uow.get_repository('sessions')
    
    download = downloads.save(DownloadModel(...))
    session = sessions.save(DownloadSession(...))
    # All operations commit together
```

#### Bulk Operations
```python
# Bulk save with transactions
entities = [EntityModel(name=f"bulk_{i}") for i in range(100)]
saved_entities = repo.bulk_save_transactional(entities, batch_size=50)

# Bulk delete
entity_ids = [entity.id for entity in saved_entities]
deleted_count = repo.bulk_delete_transactional(entity_ids)
```

### 2. Error Management

#### Error Handling with Context
```python
from data.models.error_management import ErrorHandlingContext

with ErrorHandlingContext("create_download", entity_type="DownloadModel") as ctx:
    download = DownloadModel(url="invalid://url")
    try:
        saved = download_repo.save(download)
    except RepositoryValidationError as e:
        print(f"Validation failed: {e.error_info.message}")
    except RepositoryDatabaseError as e:
        print(f"Database error: {e.error_info.message}")
```

#### Error Recovery
```python
from data.models.error_management import get_error_manager

error_manager = get_error_manager()

def risky_operation():
    # Operation that might fail
    return download_repo.save(problematic_download)

context = ErrorContext("download_operation", entity_id="123")
result = error_manager.execute_with_retry(risky_operation, context, max_retries=3)
```

#### Custom Error Handlers
```python
from data.models.error_management import IErrorHandler, ErrorInfo

class CustomTimeoutHandler(IErrorHandler):
    def can_handle(self, error: Exception, context: ErrorContext) -> bool:
        return "timeout" in str(error).lower()
    
    def handle_error(self, error: Exception, context: ErrorContext) -> ErrorInfo:
        return ErrorInfo(
            error_code="CUSTOM_TIMEOUT",
            recovery_strategy=RecoveryStrategy.RETRY,
            max_retries=5
        )

error_manager.add_handler(CustomTimeoutHandler())
```

### 3. Performance Optimization

#### Caching Strategies
```python
from data.models.performance_optimizations import LRUCache, TTLCache, RepositoryCache

# LRU Cache
lru_cache = LRUCache(max_size=1000)
repo_cache = RepositoryCache(lru_cache)

# TTL Cache
ttl_cache = TTLCache(default_ttl=3600)  # 1 hour
repo_cache = RepositoryCache(ttl_cache)

# Entity caching
entity = repo.find_by_id(123)
repo_cache.set_entity(entity, ttl=1800)  # Cache for 30 minutes

cached_entity = repo_cache.get_entity("DownloadModel", 123)
if cached_entity:
    print("Cache hit!")
```

#### Performance-Optimized Repository
```python
from data.models.performance_optimizations import PerformanceOptimizedRepository

cache_provider = LRUCache(max_size=500)
optimized_repo = PerformanceOptimizedRepository(
    base_repository=download_repo,
    cache_provider=cache_provider,
    enable_query_optimization=True,
    enable_batch_operations=True
)

# Cached operations
download = optimized_repo.find_by_id_cached(123)  # Cache miss
download = optimized_repo.find_by_id_cached(123)  # Cache hit

# Bulk operations
entities = [DownloadModel(...) for _ in range(100)]
saved = optimized_repo.bulk_save(entities, batch_size=25)

# Performance report
report = optimized_repo.get_performance_report()
print(f"Cache hit rate: {report['cache_statistics']['hit_rate']:.2f}%")
```

#### Query Optimization
```python
from data.models.performance_optimizations import QueryOptimizer

optimizer = QueryOptimizer()

query = "SELECT * FROM downloads WHERE status IN (?, ?) ORDER BY created_at DESC"
analysis = optimizer.analyze_query(query)

print(f"Query complexity: {analysis['estimated_complexity']}/10")
if analysis['recommendations']:
    for rec in analysis['recommendations']:
        print(f"Recommendation: {rec}")
```

## Best Practices

### 1. Repository Design

#### Use Dependency Injection
```python
class DownloadService:
    def __init__(self, download_repo: IDownloadRepository):
        self.download_repo = download_repo
    
    def process_download(self, url: str):
        # Business logic here
        download = DownloadModel(url=url)
        return self.download_repo.save(download)
```

#### Keep Repositories Focused
```python
# Good: Focused repository
class DownloadRepository(IDownloadRepository):
    def find_by_status(self, status: DownloadStatus):
        pass
    
    def find_active_downloads(self):
        pass

# Avoid: Kitchen sink repository
class MegaRepository:
    def find_downloads(self): pass
    def find_users(self): pass
    def find_config(self): pass  # Too broad
```

### 2. Transaction Guidelines

#### Use Transactions for Multi-Entity Operations
```python
# Good: Transaction for related operations
with repo.transaction():
    download = download_repo.save(download_model)
    session = session_repo.save(session_model)
    log_repo.save(log_model)

# Avoid: Separate operations that should be atomic
download = download_repo.save(download_model)  # Could fail here
session = session_repo.save(session_model)    # Leaving inconsistent state
```

#### Minimize Transaction Scope
```python
# Good: Minimal transaction scope
result = expensive_calculation()
with repo.transaction():
    repo.save(result)

# Avoid: Large transaction scope
with repo.transaction():
    result = expensive_calculation()  # Long-running operation in transaction
    repo.save(result)
```

### 3. Error Handling

#### Handle Specific Errors
```python
try:
    download = download_repo.save(download_model)
except RepositoryValidationError as e:
    # Handle validation errors specifically
    log.warning(f"Validation failed: {e.field} = {e.value}")
except RepositoryDatabaseError as e:
    # Handle database errors specifically
    if e.error_info.is_retryable:
        schedule_retry(download_model)
    else:
        mark_as_failed(download_model)
```

#### Use Error Context
```python
context = ErrorContext(
    operation="download_video",
    entity_id=download.id,
    entity_type="DownloadModel"
)

with ErrorHandlingContext("download_video", download.id, "DownloadModel"):
    # Operations that might fail
    pass
```

### 4. Performance Guidelines

#### Use Appropriate Caching
```python
# Good: Cache frequently accessed data
user_settings = user_repo.find_by_id_cached(user_id, ttl=3600)

# Good: Cache read-heavy data
popular_content = content_repo.find_popular_cached(limit=100, ttl=1800)

# Avoid: Caching frequently changing data
active_downloads = download_repo.find_active_cached()  # Changes too often
```

#### Optimize Queries
```python
# Good: Specific queries
recent_downloads = download_repo.find_recent_downloads(days=7)

# Avoid: Loading all data then filtering
all_downloads = download_repo.find_all()
recent = [d for d in all_downloads if d.created_at > cutoff]
```

#### Use Pagination
```python
# Good: Paginated results
page_data = download_repo.find_downloads_with_pagination(page=1, page_size=50)

# Avoid: Loading all data
all_downloads = download_repo.find_all()  # Could be thousands of records
```

## Performance Optimization

### Caching Configuration

```python
# Global cache configuration
from data.models.performance_optimizations import set_global_cache_provider, LRUCache

# Set up global cache
global_cache = LRUCache(max_size=5000)
set_global_cache_provider(global_cache)

# Repository-specific cache
@performance_optimized(
    cache_strategy=CacheStrategy.LRU,
    cache_size=1000,
    cache_ttl=3600,
    enable_batch_operations=True
)
class OptimizedDownloadRepository(DownloadRepository):
    pass
```

### Monitoring Performance

```python
from data.models.performance_optimizations import get_global_performance_monitor

monitor = get_global_performance_monitor()

# Monitor operations
with monitor.measure_operation("bulk_download_save", "DownloadModel"):
    saved_downloads = download_repo.bulk_save(downloads)

# Get performance metrics
metrics = monitor.get_metrics_summary(
    metric_type=PerformanceMetricType.QUERY_TIME,
    operation="bulk_download_save"
)

print(f"Average execution time: {metrics['avg_value']:.3f}s")
```

### Batch Operations

```python
# Efficient bulk operations
batch_manager = BatchOperationManager(default_batch_size=100)

# Add operations to batch
for download in downloads:
    batch_manager.add_operation("save", download)

# Execute in batches
def save_executor(batch_items):
    return [download_repo.save(item) for item in batch_items]

results = batch_manager.execute_batch("save", save_executor)
```

## Testing

### Unit Testing

```python
import pytest
from unittest.mock import Mock
from data.models.repositories import BaseRepository

class TestDownloadRepository:
    def setup_method(self):
        self.mock_model = Mock()
        self.repository = BaseRepository(self.mock_model)
    
    def test_save_entity(self):
        # Arrange
        entity = DownloadModel(url="test://url")
        self.mock_model.save.return_value = entity
        
        # Act
        result = self.repository.save(entity)
        
        # Assert
        assert result == entity
        self.mock_model.save.assert_called_once_with(entity)
```

### Integration Testing

```python
@pytest.fixture
def test_database():
    # Set up test database
    test_db_path = create_test_database()
    yield test_db_path
    cleanup_test_database(test_db_path)

def test_repository_integration(test_database):
    # Test with real database
    repo = get_download_repository()
    
    download = DownloadModel(url="https://example.com/test.mp4")
    saved = repo.save(download)
    
    assert saved.id is not None
    
    found = repo.find_by_id(saved.id)
    assert found.url == download.url
```

### Performance Testing

```python
def test_cache_performance():
    cache = LRUCache(max_size=1000)
    repo_cache = RepositoryCache(cache)
    
    # Measure cache vs direct access
    entities = [TestEntity(name=f"test_{i}") for i in range(100)]
    
    # Time direct access
    start = time.time()
    for entity in entities:
        mock_repo.find_by_id(entity.id)
    direct_time = time.time() - start
    
    # Time cached access
    for entity in entities:
        repo_cache.set_entity(entity)
    
    start = time.time()
    for entity in entities:
        repo_cache.get_entity("TestEntity", entity.id)
    cached_time = time.time() - start
    
    assert cached_time < direct_time
```

## Configuration

### Environment Variables

```bash
# Database configuration
DATABASE_URL=sqlite:///social_download_manager.db

# Cache configuration
CACHE_MAX_SIZE=5000
CACHE_DEFAULT_TTL=3600

# Performance monitoring
ENABLE_PERFORMANCE_MONITORING=true
SLOW_QUERY_THRESHOLD=1.0

# Error handling
ERROR_LOG_LEVEL=WARNING
ENABLE_ERROR_RECOVERY=true
```

### Application Configuration

```python
# config.py
REPOSITORY_CONFIG = {
    'cache': {
        'provider': 'lru',
        'max_size': 5000,
        'default_ttl': 3600
    },
    'performance': {
        'enable_monitoring': True,
        'enable_query_optimization': True,
        'enable_batch_operations': True
    },
    'error_handling': {
        'enable_recovery': True,
        'max_retries': 3,
        'retry_delay': 1.0
    }
}
```

## Migration Guide

### From v1.x to v2.0

#### Old Pattern (v1.x)
```python
# Direct database access
connection = sqlite3.connect('database.db')
cursor = connection.cursor()
cursor.execute("SELECT * FROM downloads WHERE status = ?", ["pending"])
rows = cursor.fetchall()
```

#### New Pattern (v2.0)
```python
# Repository pattern
download_repo = get_download_repository()
pending_downloads = download_repo.find_by_status(DownloadStatus.PENDING)
```

#### Migration Steps

1. **Replace Direct Database Access**
   ```python
   # Before
   cursor.execute("SELECT * FROM downloads WHERE id = ?", [download_id])
   
   # After
   download = download_repo.find_by_id(download_id)
   ```

2. **Update Transaction Handling**
   ```python
   # Before
   try:
       connection.begin()
       # operations...
       connection.commit()
   except:
       connection.rollback()
   
   # After
   with download_repo.transaction():
       # operations...
       # auto-commit/rollback
   ```

3. **Add Error Handling**
   ```python
   # Before
   try:
       # operation
   except Exception as e:
       print(f"Error: {e}")
   
   # After
   try:
       # operation
   except RepositoryValidationError as e:
       handle_validation_error(e)
   except RepositoryDatabaseError as e:
       handle_database_error(e)
   ```

## Troubleshooting

### Common Issues

#### Cache Not Working
```python
# Check cache configuration
cache_stats = repo_cache.get_stats()
print(f"Hit rate: {cache_stats['hit_rate']:.2f}%")

# Verify cache invalidation
repo_cache.invalidate_entity("DownloadModel", entity_id)
```

#### Performance Issues
```python
# Enable performance monitoring
monitor = get_global_performance_monitor()
report = optimized_repo.get_performance_report()

# Check slow queries
slow_queries = query_optimizer.get_slow_queries(threshold=1.0)
for query in slow_queries:
    print(f"Slow query: {query.execution_time:.3f}s")
```

#### Transaction Deadlocks
```python
# Use appropriate isolation levels
with repo.transaction(isolation_level=TransactionIsolationLevel.IMMEDIATE):
    # operations...

# Minimize transaction scope
# Move heavy operations outside transactions
```

### Debug Mode

```python
# Enable debug logging
import logging
logging.getLogger('data.models.repositories').setLevel(logging.DEBUG)
logging.getLogger('data.models.transaction_repository').setLevel(logging.DEBUG)
logging.getLogger('data.models.performance_optimizations').setLevel(logging.DEBUG)

# Error statistics
error_manager = get_error_manager()
stats = error_manager.get_error_statistics()
print(f"Error statistics: {stats}")
```

---

## Conclusion

The Repository Pattern implementation in Social Download Manager v2.0 provides a robust, scalable, and maintainable data access layer. By following the patterns and best practices outlined in this documentation, developers can efficiently work with the system while maintaining high performance and reliability.

For additional examples and advanced usage patterns, see the example files:
- `data/models/transaction_examples.py`
- `data/models/error_examples.py`
- `data/models/performance_examples.py`
- `tests/test_repositories.py` 