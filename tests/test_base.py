"""
Database Testing Infrastructure

This module provides comprehensive base testing infrastructure including:
- Base test classes with database setup/teardown
- Test configuration and utilities  
- Mock and fixture management
- Performance testing capabilities
- Error testing framework
"""

import os
import shutil
import tempfile
import threading
import time
import unittest
import sqlite3
from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Generator, Union
from unittest.mock import Mock, MagicMock, patch

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.database.connection import (
    ConnectionConfig, SQLiteConnectionManager, get_connection_manager
)
from data.database.transactions import (
    TransactionManager, TransactionIsolationLevel, TransactionPropagation,
    get_transaction_manager, initialize_transaction_manager
)
from data.database.exceptions import (
    DatabaseError, DatabaseErrorCode, DatabaseErrorContext,
    ConnectionError, TransactionError, SQLError
)
from data.database.logging import (
    DatabaseLogger, LogLevel, OperationType, configure_default_logger
)
from data.database.retry import (
    RetryConfig, CircuitBreakerConfig, RetryStrategy,
    get_default_circuit_breaker, configure_default_retry_policies
)
from data.database.monitoring import configure_monitoring
from data.models import ContentModel, ContentType, ContentStatus, PlatformType
from data.models.repositories import ContentRepository, get_content_repository


class TestConfig:
    """Configuration for database tests"""
    
    def __init__(
        self,
        use_memory_db: bool = False,
        enable_wal_mode: bool = True,
        enable_logging: bool = True,
        log_level: LogLevel = LogLevel.DEBUG,
        connection_pool_size: int = 5,
        transaction_timeout: float = 30.0,
        enable_performance_monitoring: bool = True,
        enable_retry_policies: bool = True
    ):
        self.use_memory_db = use_memory_db
        self.enable_wal_mode = enable_wal_mode
        self.enable_logging = enable_logging
        self.log_level = log_level
        self.connection_pool_size = connection_pool_size
        self.transaction_timeout = transaction_timeout
        self.enable_performance_monitoring = enable_performance_monitoring
        self.enable_retry_policies = enable_retry_policies


class DatabaseTestCase(unittest.TestCase):
    """Base test case for database operations with comprehensive setup/teardown"""
    
    def __init__(self, methodName='runTest', test_config: Optional[TestConfig] = None):
        super().__init__(methodName)
        self.test_config = test_config or TestConfig()
        
        # Test environment
        self.temp_dir: Optional[str] = None
        self.db_path: Optional[str] = None
        
        # Database components
        self.connection_manager: Optional[SQLiteConnectionManager] = None
        self.transaction_manager: Optional[TransactionManager] = None
        self.logger: Optional[DatabaseLogger] = None
        
        # Test data tracking
        self.test_start_time: Optional[datetime] = None
        self.performance_metrics: Dict[str, Any] = {}
        self.created_tables: List[str] = []
        self.test_data_cleanup: List[Callable] = []
        
        # Mock objects for isolation
        self.mocks: Dict[str, Mock] = {}
    
    def setUp(self) -> None:
        """Set up test environment with database and logging"""
        super().setUp()
        self.test_start_time = datetime.now()
        
        # Setup test database
        self._setup_test_database()
        
        # Setup logging if enabled
        if self.test_config.enable_logging:
            self._setup_test_logging()
        
        # Setup monitoring if enabled
        if self.test_config.enable_performance_monitoring:
            self._setup_monitoring()
        
        # Setup retry policies if enabled
        if self.test_config.enable_retry_policies:
            self._setup_retry_policies()
        
        # Setup transaction manager
        self._setup_transaction_manager()
        
        # Custom setup hook
        self._custom_setup()
    
    def tearDown(self) -> None:
        """Clean up test environment"""
        try:
            # Custom teardown hook
            self._custom_teardown()
            
            # Clean up test data
            self._cleanup_test_data()
            
            # Calculate performance metrics
            if self.test_config.enable_performance_monitoring:
                self._calculate_performance_metrics()
            
            # Shutdown database components
            self._shutdown_database_components()
            
            # Clean up temporary files
            self._cleanup_temp_files()
            
        except Exception as e:
            # Log teardown errors but don't fail the test
            if self.logger:
                self.logger.log_error(e, "test_teardown")
        
        super().tearDown()
    
    def _setup_test_database(self) -> None:
        """Setup test database with appropriate configuration"""
        if self.test_config.use_memory_db:
            self.db_path = ":memory:"
        else:
            self.temp_dir = tempfile.mkdtemp(prefix="db_test_")
            self.db_path = os.path.join(self.temp_dir, "test.db")
        
        # Create connection config
        config = ConnectionConfig(
            database_path=self.db_path,
            max_pool_size=self.test_config.connection_pool_size,
            min_pool_size=1,
            connection_timeout=10.0,
            pool_timeout=5.0,
            enable_wal_mode=self.test_config.enable_wal_mode,
            enable_foreign_keys=True
        )
        
        # Initialize connection manager
        self.connection_manager = SQLiteConnectionManager(config)
        self.connection_manager.initialize()
    
    def _setup_test_logging(self) -> None:
        """Setup test logging with appropriate configuration"""
        log_file_path = None
        if self.temp_dir:
            log_file_path = os.path.join(self.temp_dir, "test.log")
        
        self.logger = configure_default_logger(
            log_level=self.test_config.log_level,
            enable_performance_logging=True,
            enable_query_logging=True,
            log_file_path=log_file_path
        )
        
        # Set session ID for correlation
        test_session_id = f"test_{self._testMethodName}_{int(time.time())}"
        self.logger.set_session_id(test_session_id)
    
    def _setup_monitoring(self) -> None:
        """Setup performance monitoring"""
        if self.connection_manager:
            configure_monitoring(self.connection_manager, self.logger, auto_start=True)
    
    def _setup_retry_policies(self) -> None:
        """Setup retry policies for testing"""
        retry_config = RetryConfig(
            max_attempts=3,
            base_delay=0.1,  # Fast retries for tests
            max_delay=1.0,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF
        )
        
        circuit_breaker_config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=5.0,
            timeout=10.0
        )
        
        configure_default_retry_policies(circuit_breaker_config, retry_config)
    
    def _setup_transaction_manager(self) -> None:
        """Setup transaction manager"""
        if self.connection_manager:
            self.transaction_manager = initialize_transaction_manager(self.connection_manager)
    
    def _custom_setup(self) -> None:
        """Hook for custom setup in subclasses"""
        pass
    
    def _custom_teardown(self) -> None:
        """Hook for custom teardown in subclasses"""
        pass
    
    def _cleanup_test_data(self) -> None:
        """Clean up test data using registered cleanup functions"""
        for cleanup_func in reversed(self.test_data_cleanup):
            try:
                cleanup_func()
            except Exception as e:
                if self.logger:
                    self.logger.log_error(e, "test_data_cleanup")
    
    def _calculate_performance_metrics(self) -> None:
        """Calculate and store performance metrics"""
        if self.test_start_time:
            test_duration = (datetime.now() - self.test_start_time).total_seconds()
            self.performance_metrics["test_duration"] = test_duration
        
        if self.connection_manager:
            stats = self.connection_manager.get_stats()
            self.performance_metrics["connection_stats"] = {
                "total_connections": stats.total_connections,
                "active_connections": stats.active_connections,
                "connection_requests": stats.connection_requests,
                "failed_connections": stats.failed_connections,
                "average_connection_time": stats.average_connection_time
            }
        
        if self.logger:
            query_stats = self.logger.get_query_statistics()
            self.performance_metrics["query_stats"] = query_stats
    
    def _shutdown_database_components(self) -> None:
        """Shutdown database components safely"""
        try:
            if self.connection_manager:
                self.connection_manager.shutdown()
        except Exception as e:
            if self.logger:
                self.logger.log_error(e, "connection_manager_shutdown")
    
    def _cleanup_temp_files(self) -> None:
        """Clean up temporary files and directories"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass  # Ignore cleanup errors
    
    # Utility methods for tests
    
    def create_test_table(self, table_name: str, schema: str) -> None:
        """Create a test table and register for cleanup"""
        with self.connection_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({schema})")
            cursor.close()
        
        self.created_tables.append(table_name)
        self.test_data_cleanup.append(lambda: self._drop_table(table_name))
    
    def _drop_table(self, table_name: str) -> None:
        """Drop a test table"""
        try:
            with self.connection_manager.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                cursor.close()
        except Exception:
            pass  # Ignore errors during cleanup
    
    def insert_test_data(self, table_name: str, data: Dict[str, Any]) -> int:
        """Insert test data and return the ID"""
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" * len(data))
        values = list(data.values())
        
        with self.connection_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})", values)
            row_id = cursor.lastrowid
            cursor.close()
        
        return row_id
    
    def execute_query(self, query: str, parameters: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """Execute a query and return results as dictionaries"""
        with self.connection_manager.connection() as conn:
            # Set row factory for dict-like access
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if parameters:
                cursor.execute(query, parameters)
            else:
                cursor.execute(query)
            
            results = [dict(row) for row in cursor.fetchall()]
            cursor.close()
        
        return results
    
    def assert_query_count(self, expected_count: int, tolerance: int = 0) -> None:
        """Assert the number of queries executed during test"""
        if self.logger:
            query_stats = self.logger.get_query_statistics()
            total_queries = sum(stats["count"] for stats in query_stats.values())
            
            if tolerance > 0:
                self.assertGreaterEqual(total_queries, expected_count - tolerance)
                self.assertLessEqual(total_queries, expected_count + tolerance)
            else:
                self.assertEqual(total_queries, expected_count)
    
    def assert_no_slow_queries(self, threshold_ms: float = 100.0) -> None:
        """Assert no queries exceeded the performance threshold"""
        if self.logger:
            query_stats = self.logger.get_query_statistics()
            slow_queries = [
                hash_id for hash_id, stats in query_stats.items()
                if stats["max_time_ms"] > threshold_ms
            ]
            
            self.assertEqual(len(slow_queries), 0, 
                           f"Found {len(slow_queries)} slow queries exceeding {threshold_ms}ms")
    
    def create_mock(self, name: str, spec: Optional[type] = None) -> Mock:
        """Create a mock object and register for cleanup"""
        mock_obj = Mock(spec=spec)
        self.mocks[name] = mock_obj
        return mock_obj
    
    @contextmanager
    def assert_raises_database_error(self, error_code: DatabaseErrorCode) -> Generator[None, None, None]:
        """Context manager to assert specific database error is raised"""
        with self.assertRaises(DatabaseError) as cm:
            yield
        
        self.assertEqual(cm.exception.error_code, error_code)
    
    @contextmanager
    def measure_execution_time(self) -> Generator[Dict[str, float], None, None]:
        """Context manager to measure execution time"""
        metrics = {}
        start_time = time.time()
        
        try:
            yield metrics
        finally:
            metrics["execution_time"] = time.time() - start_time


class TransactionTestCase(DatabaseTestCase):
    """Base test case for transaction testing"""
    
    def _custom_setup(self) -> None:
        """Setup transaction-specific test environment"""
        super()._custom_setup()
        
        # Create test table for transaction tests
        self.create_test_table("transaction_test", """
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            value TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        """)
    
    @contextmanager
    def test_transaction(
        self,
        isolation_level: TransactionIsolationLevel = TransactionIsolationLevel.DEFERRED,
        should_commit: bool = True
    ) -> Generator:
        """Context manager for test transactions"""
        txn = self.transaction_manager.begin_transaction(isolation_level)
        
        try:
            yield txn
            
            if should_commit:
                txn.commit()
            else:
                txn.rollback()
                
        except Exception:
            if txn.is_active:
                txn.rollback()
            raise
    
    def assert_transaction_count(self, expected_count: int) -> None:
        """Assert the number of transactions executed"""
        stats = self.transaction_manager.get_statistics()
        self.assertEqual(stats.total_transactions, expected_count)
    
    def assert_no_active_transactions(self) -> None:
        """Assert no transactions are currently active"""
        stats = self.transaction_manager.get_statistics()
        self.assertEqual(stats.active_transactions, 0)


class RepositoryTestCase(DatabaseTestCase):
    """Base test case for repository testing"""
    
    def _custom_setup(self) -> None:
        """Setup repository-specific test environment"""
        super()._custom_setup()
        
        # Initialize content model manager and repository
        from data.models import ContentModelManager
        
        self.model_manager = ContentModelManager(self.connection_manager)
        self.model_manager.create_table()
        
        self.repository = ContentRepository(self.model_manager)
        
        # Register cleanup
        self.test_data_cleanup.append(self._cleanup_content_data)
    
    def _cleanup_content_data(self) -> None:
        """Clean up content test data"""
        try:
            with self.connection_manager.connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM content")
                cursor.close()
        except Exception:
            pass
    
    def create_test_content(
        self,
        url: str = "https://test.com/video",
        platform: PlatformType = PlatformType.TIKTOK,
        content_type: ContentType = ContentType.VIDEO,
        title: str = "Test Content",
        author: str = "Test Author",
        platform_id: str = "test123",
        status: ContentStatus = ContentStatus.PENDING,
        **kwargs
    ) -> ContentModel:
        """Create a test content model"""
        return ContentModel(
            url=url,
            platform=platform,
            content_type=content_type,
            title=title,
            author=author,
            platform_id=platform_id,
            status=status,
            **kwargs
        )
    
    def save_test_content(self, content: ContentModel) -> ContentModel:
        """Save test content and register for cleanup"""
        saved_content = self.repository.save(content)
        return saved_content


class PerformanceTestCase(DatabaseTestCase):
    """Base test case for performance testing"""
    
    def __init__(self, methodName='runTest'):
        super().__init__(methodName, TestConfig(enable_performance_monitoring=True))
        self.performance_thresholds = {
            "max_query_time_ms": 100.0,
            "max_transaction_time_ms": 500.0,
            "max_connection_time_ms": 50.0
        }
    
    def assert_performance_thresholds(self) -> None:
        """Assert performance metrics meet thresholds"""
        if not self.performance_metrics:
            self.fail("No performance metrics available")
        
        # Check query performance
        if "query_stats" in self.performance_metrics:
            for query_hash, stats in self.performance_metrics["query_stats"].items():
                max_time = stats.get("max_time_ms", 0)
                self.assertLessEqual(
                    max_time,
                    self.performance_thresholds["max_query_time_ms"],
                    f"Query {query_hash} exceeded max time threshold: {max_time}ms"
                )
        
        # Check connection performance
        if "connection_stats" in self.performance_metrics:
            avg_connection_time = self.performance_metrics["connection_stats"].get("average_connection_time", 0)
            self.assertLessEqual(
                avg_connection_time,
                self.performance_thresholds["max_connection_time_ms"],
                f"Average connection time exceeded threshold: {avg_connection_time}ms"
            )
    
    @contextmanager
    def performance_benchmark(self, operation_name: str) -> Generator[Dict[str, Any], None, None]:
        """Context manager for performance benchmarking"""
        metrics = {"operation": operation_name}
        start_time = time.time()
        
        # Capture initial stats
        initial_stats = {}
        if self.connection_manager:
            initial_stats["connection"] = self.connection_manager.get_stats()
        if self.transaction_manager:
            initial_stats["transaction"] = self.transaction_manager.get_statistics()
        if self.logger:
            initial_stats["query"] = self.logger.get_query_statistics()
        
        try:
            yield metrics
        finally:
            # Calculate execution time
            metrics["execution_time"] = time.time() - start_time
            
            # Capture final stats and calculate deltas
            if self.connection_manager:
                final_connection_stats = self.connection_manager.get_stats()
                initial_connection_stats = initial_stats.get("connection")
                if initial_connection_stats:
                    metrics["connections_used"] = (
                        final_connection_stats.connection_requests - 
                        initial_connection_stats.connection_requests
                    )
            
            # Store metrics for later analysis
            if "benchmarks" not in self.performance_metrics:
                self.performance_metrics["benchmarks"] = []
            self.performance_metrics["benchmarks"].append(metrics)


class MockDatabaseTestCase(DatabaseTestCase):
    """Base test case for testing with mocked database components"""
    
    def __init__(self, methodName='runTest'):
        super().__init__(methodName, TestConfig(use_memory_db=True, enable_logging=False))
    
    def _custom_setup(self) -> None:
        """Setup mock database components"""
        super()._custom_setup()
        
        # Create mock connection manager
        self.mock_connection_manager = self.create_mock("connection_manager", SQLiteConnectionManager)
        self.mock_connection = self.create_mock("connection", sqlite3.Connection)
        self.mock_cursor = self.create_mock("cursor", sqlite3.Cursor)
        
        # Setup mock behavior
        self.mock_connection_manager.get_connection.return_value = self.mock_connection
        self.mock_connection.cursor.return_value = self.mock_cursor
        self.mock_cursor.fetchone.return_value = None
        self.mock_cursor.fetchall.return_value = []
        
    def setup_mock_query_result(self, result: Union[List[tuple], tuple, None]) -> None:
        """Setup mock query result"""
        if isinstance(result, list):
            self.mock_cursor.fetchall.return_value = result
            self.mock_cursor.fetchone.return_value = result[0] if result else None
        else:
            self.mock_cursor.fetchone.return_value = result
            self.mock_cursor.fetchall.return_value = [result] if result else []
    
    def assert_query_executed(self, expected_query: str, expected_params: Optional[List[Any]] = None) -> None:
        """Assert that a specific query was executed"""
        self.mock_cursor.execute.assert_called()
        
        # Get the last call
        last_call = self.mock_cursor.execute.call_args
        actual_query = last_call[0][0]
        actual_params = last_call[0][1] if len(last_call[0]) > 1 else None
        
        self.assertIn(expected_query.strip(), actual_query.strip())
        
        if expected_params is not None:
            self.assertEqual(actual_params, expected_params) 