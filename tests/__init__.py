"""
Enhanced Database Testing Framework

This package provides comprehensive testing infrastructure for database operations,
including base test classes, fixtures, factories, and integration testing utilities.

Available Test Base Classes:
- DatabaseTestCase: Basic database testing with setup/teardown
- TransactionTestCase: Transaction-specific testing
- RepositoryTestCase: Repository pattern testing
- PerformanceTestCase: Performance testing with metrics
- MockDatabaseTestCase: Testing with mocked components
- DatabaseFixtureTestCase: Fixture-based testing

Available Utilities:
- ContentModelFactory: Factory for creating test content models
- FixtureManager: Managing test data lifecycle
- TestDataTemplate: Template system for test data
- TestConfig: Configuration for test environments

Usage Examples:

Basic Database Testing:
```python
from tests.test_base import DatabaseTestCase

class MyDatabaseTest(DatabaseTestCase):
    def test_something(self):
        self.create_test_table("my_table", "id INTEGER, name TEXT")
        # Test code here
```

Repository Testing:
```python
from tests.test_base import RepositoryTestCase

class MyRepositoryTest(RepositoryTestCase):
    def test_repository_operation(self):
        content = self.create_test_content()
        saved = self.repository.save(content)
        # Assertions here
```

Fixture-based Testing:
```python
from tests.test_fixtures import DatabaseFixtureTestCase

class MyFixtureTest(DatabaseFixtureTestCase):
    def test_with_fixtures(self):
        contents = self.create_fixture("content_tiktok", count=5)
        # Test with fixture data
```

Performance Testing:
```python
from tests.test_base import PerformanceTestCase

class MyPerformanceTest(PerformanceTestCase):
    def test_performance(self):
        with self.performance_benchmark("operation") as metrics:
            # Code to benchmark
            pass
        self.assert_performance_thresholds()
```
"""

# Import all base test classes
from .test_base import (
    DatabaseTestCase,
    TransactionTestCase, 
    RepositoryTestCase,
    PerformanceTestCase,
    MockDatabaseTestCase,
    TestConfig
)

# Import fixture and factory components
from .test_fixtures import (
    DatabaseFixtureTestCase,
    ContentModelFactory,
    FixtureManager,
    TestDataTemplate,
    DataFactory
)

# Import test utilities
from .test_utils import (
    wait_for_condition,
    simulate_concurrent_operations
)

# Re-export commonly used testing components
__all__ = [
    # Base test classes
    'DatabaseTestCase',
    'TransactionTestCase',
    'RepositoryTestCase', 
    'PerformanceTestCase',
    'MockDatabaseTestCase',
    'DatabaseFixtureTestCase',
    
    # Configuration and utilities
    'TestConfig',
    'ContentModelFactory',
    'FixtureManager',
    'TestDataTemplate',
    'DataFactory',
    
    # Utility functions
    'wait_for_condition',
    'simulate_concurrent_operations',
]

# Version info
__version__ = "1.0.0"
__author__ = "Database Testing Framework"
__description__ = "Comprehensive testing infrastructure for database operations" 