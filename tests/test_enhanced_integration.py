"""
Enhanced Integration Testing Suite

This module provides comprehensive integration testing including:
- End-to-end database tests with real database
- Transaction behavior testing (ACID properties, isolation levels)
- Error condition testing (retry policies, circuit breakers)
- Performance testing capabilities with metrics
- Multi-threaded and concurrent testing scenarios
"""

import unittest
import threading
import time
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
from unittest.mock import patch

# Import base test infrastructure
from .test_base import (
    DatabaseTestCase, TransactionTestCase, PerformanceTestCase,
    TestConfig
)

# Import test utilities
from .test_utils import (
    wait_for_condition, simulate_concurrent_operations
)

# Database components
from data.database.connection import (
    SQLiteConnectionManager, ConnectionConfig, ConnectionState
)
from data.database.transactions import (
    TransactionManager, TransactionIsolationLevel, TransactionPropagation,
    TransactionStatus, get_transaction_manager
)
from data.database.exceptions import (
    DatabaseError, DatabaseErrorCode, ConnectionTimeoutError,
    TransactionTimeoutException, DeadlockError, LockTimeoutError
)
from data.database.logging import DatabaseLogger, LogLevel, OperationType
from data.database.retry import (
    RetryConfig, CircuitBreakerConfig, RetryStrategy,
    get_default_circuit_breaker, retry_database_operation
)
from data.database.monitoring import configure_monitoring
from data.models import (
    ContentModel, ContentType, ContentStatus, PlatformType, ContentModelManager
)
from data.models.repositories import ContentRepository


class TestDatabaseIntegrationBasics(DatabaseTestCase):
    """Test basic database integration functionality"""
    
    def test_end_to_end_database_lifecycle(self):
        """Test complete database lifecycle from initialization to shutdown"""
        # Verify database is initialized
        self.assertEqual(self.connection_manager._state, ConnectionState.CONNECTED)
        
        # Test basic operations
        with self.connection_manager.connection() as conn:
            cursor = conn.cursor()
            
            # Create test table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS integration_test (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    value INTEGER DEFAULT 0
                )
            """)
            
            # Insert data
            cursor.execute("INSERT INTO integration_test (name, value) VALUES (?, ?)", 
                          ("test1", 100))
            cursor.execute("INSERT INTO integration_test (name, value) VALUES (?, ?)", 
                          ("test2", 200))
            
            # Query data
            cursor.execute("SELECT name, value FROM integration_test ORDER BY id")
            results = cursor.fetchall()
            
            cursor.close()
        
        # Verify results
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], ("test1", 100))
        self.assertEqual(results[1], ("test2", 200))
    
    def test_connection_pool_integration(self):
        """Test connection pool behavior in integration scenario"""
        # Get initial pool stats
        initial_stats = self.connection_manager.get_stats()
        
        # Use multiple connections concurrently
        def use_connection(worker_id):
            with self.connection_manager.connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT ? as worker_id", (worker_id,))
                result = cursor.fetchone()
                cursor.close()
                return result[0]
        
        # Run concurrent operations
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(use_connection, i) for i in range(5)]
            results = [future.result() for future in as_completed(futures)]
        
        # Verify all operations succeeded
        self.assertEqual(len(results), 5)
        self.assertEqual(set(results), {0, 1, 2, 3, 4})
        
        # Check pool stats
        final_stats = self.connection_manager.get_stats()
        self.assertGreater(final_stats.connection_requests, initial_stats.connection_requests)
    
    def test_wal_mode_integration(self):
        """Test WAL mode functionality in integration scenario"""
        if not self.test_config.enable_wal_mode:
            self.skipTest("WAL mode not enabled for this test")
        
        # Check WAL mode is enabled
        with self.connection_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode")
            journal_mode = cursor.fetchone()[0]
            cursor.close()
        
        self.assertEqual(journal_mode.upper(), "WAL")
        
        # Test concurrent reads (WAL allows this)
        self.create_test_table("wal_test", "id INTEGER PRIMARY KEY, data TEXT")
        
        # Insert test data
        for i in range(10):
            self.insert_test_data("wal_test", {"data": f"test_{i}"})
        
        def concurrent_read(worker_id):
            results = self.execute_query("SELECT COUNT(*) as count FROM wal_test")
            return results[0]["count"]
        
        # Multiple concurrent reads should work
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(concurrent_read, i) for i in range(5)]
            results = [future.result() for future in as_completed(futures)]
        
        # All should see the same count
        self.assertTrue(all(count == 10 for count in results))


class TestTransactionIntegration(TransactionTestCase):
    """Test transaction integration scenarios"""
    
    def test_acid_properties_integration(self):
        """Test ACID properties in real integration scenario"""
        # Atomicity test
        def atomic_operation():
            with self.test_transaction() as txn:
                conn = txn.get_connection()
                cursor = conn.cursor()
                
                # Multiple operations that should all succeed or all fail
                cursor.execute("INSERT INTO transaction_test (value) VALUES (?)", ("atomic1",))
                cursor.execute("INSERT INTO transaction_test (value) VALUES (?)", ("atomic2",))
                cursor.execute("INSERT INTO transaction_test (value) VALUES (?)", ("atomic3",))
                
                # Simulate error on last operation
                raise Exception("Simulated error for atomicity test")
        
        # Should rollback all operations
        with self.assertRaises(Exception):
            atomic_operation()
        
        # Verify no data was inserted
        results = self.execute_query("SELECT COUNT(*) as count FROM transaction_test")
        self.assertEqual(results[0]["count"], 0)
        
        # Consistency test - successful transaction
        with self.test_transaction() as txn:
            conn = txn.get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO transaction_test (value) VALUES (?)", ("consistent",))
            cursor.close()
        
        # Verify data was committed
        results = self.execute_query("SELECT COUNT(*) as count FROM transaction_test")
        self.assertEqual(results[0]["count"], 1)
    
    def test_isolation_levels_integration(self):
        """Test transaction isolation levels in integration scenarios"""
        # Test DEFERRED isolation (default)
        with self.test_transaction(TransactionIsolationLevel.DEFERRED) as txn:
            self.assertEqual(txn.isolation_level, TransactionIsolationLevel.DEFERRED)
            
            conn = txn.get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO transaction_test (value) VALUES (?)", ("deferred",))
            cursor.close()
        
        # Test IMMEDIATE isolation
        with self.test_transaction(TransactionIsolationLevel.IMMEDIATE) as txn:
            self.assertEqual(txn.isolation_level, TransactionIsolationLevel.IMMEDIATE)
            
            conn = txn.get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO transaction_test (value) VALUES (?)", ("immediate",))
            cursor.close()
        
        # Test EXCLUSIVE isolation
        with self.test_transaction(TransactionIsolationLevel.EXCLUSIVE) as txn:
            self.assertEqual(txn.isolation_level, TransactionIsolationLevel.EXCLUSIVE)
            
            conn = txn.get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO transaction_test (value) VALUES (?)", ("exclusive",))
            cursor.close()
        
        # Verify all transactions completed
        results = self.execute_query("SELECT COUNT(*) as count FROM transaction_test")
        self.assertEqual(results[0]["count"], 3)
    
    def test_nested_transaction_integration(self):
        """Test nested transactions with savepoints in integration scenario"""
        with self.test_transaction() as outer_txn:
            conn = outer_txn.get_connection()
            cursor = conn.cursor()
            
            # Outer transaction work
            cursor.execute("INSERT INTO transaction_test (value) VALUES (?)", ("outer",))
            
            # Create savepoint
            savepoint = outer_txn.create_savepoint("test_savepoint")
            
            # Inner work
            cursor.execute("INSERT INTO transaction_test (value) VALUES (?)", ("inner1",))
            cursor.execute("INSERT INTO transaction_test (value) VALUES (?)", ("inner2",))
            
            # Check current state (should see all 3 records)
            cursor.execute("SELECT COUNT(*) FROM transaction_test")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 3)
            
            # Rollback to savepoint
            outer_txn.rollback_to_savepoint(savepoint)
            
            # Should only see outer record now
            cursor.execute("SELECT COUNT(*) FROM transaction_test")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 1)
            
            # Add different inner work
            cursor.execute("INSERT INTO transaction_test (value) VALUES (?)", ("inner_new",))
            
            # Release savepoint
            outer_txn.release_savepoint(savepoint)
            
            cursor.close()
        
        # Verify final state (outer + inner_new)
        results = self.execute_query("SELECT value FROM transaction_test ORDER BY id")
        values = [row["value"] for row in results]
        self.assertEqual(values, ["outer", "inner_new"])
    
    def test_concurrent_transaction_integration(self):
        """Test concurrent transactions in integration scenario"""
        def concurrent_transaction(worker_id):
            try:
                with self.transaction_manager.transaction() as txn:
                    conn = txn.get_connection()
                    cursor = conn.cursor()
                    
                    # Each worker inserts its own record
                    cursor.execute("INSERT INTO transaction_test (value) VALUES (?)", 
                                  (f"worker_{worker_id}",))
                    
                    # Simulate processing time
                    time.sleep(0.01)
                    
                    cursor.close()
                
                return worker_id
            except Exception as e:
                return f"error_{worker_id}: {e}"
        
        # Run concurrent transactions
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(concurrent_transaction, i) for i in range(10)]
            results = [future.result() for future in as_completed(futures)]
        
        # All should succeed
        successful_workers = [r for r in results if isinstance(r, int)]
        self.assertEqual(len(successful_workers), 10)
        
        # Verify all records were inserted
        final_results = self.execute_query("SELECT COUNT(*) as count FROM transaction_test")
        self.assertEqual(final_results[0]["count"], 10)


class TestErrorHandlingIntegration(DatabaseTestCase):
    """Test error handling and recovery in integration scenarios"""
    
    def test_retry_policy_integration(self):
        """Test retry policies in real error scenarios"""
        retry_count = 0
        
        @retry_database_operation(
            retry_config=RetryConfig(
                max_attempts=3,
                base_delay=0.01,  # Fast for testing
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF
            )
        )
        def flaky_operation():
            nonlocal retry_count
            retry_count += 1
            
            if retry_count < 3:
                # Simulate database lock error
                raise sqlite3.OperationalError("database is locked")
            
            # Succeed on third attempt
            with self.connection_manager.connection() as conn:
                cursor = conn.cursor()
                cursor.execute("CREATE TABLE IF NOT EXISTS retry_test (id INTEGER, value TEXT)")
                cursor.execute("INSERT INTO retry_test (id, value) VALUES (1, 'success')")
                cursor.close()
            
            return "success"
        
        # Should succeed after retries
        result = flaky_operation()
        self.assertEqual(result, "success")
        self.assertEqual(retry_count, 3)
        
        # Verify data was inserted
        results = self.execute_query("SELECT value FROM retry_test WHERE id = 1")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["value"], "success")
    
    def test_circuit_breaker_integration(self):
        """Test circuit breaker behavior in integration scenario"""
        circuit_breaker = get_default_circuit_breaker()
        
        # Reset circuit breaker state
        circuit_breaker.state = circuit_breaker.state.__class__.CLOSED
        circuit_breaker.failure_count = 0
        
        def failing_operation():
            raise sqlite3.OperationalError("Persistent failure")
        
        # Trip the circuit breaker
        for i in range(circuit_breaker.config.failure_threshold + 1):
            try:
                circuit_breaker.call(failing_operation)
            except:
                pass
        
        # Circuit should now be open
        from data.database.retry import CircuitBreakerState
        self.assertEqual(circuit_breaker.state, CircuitBreakerState.OPEN)
        
        # Further calls should fail fast
        from data.database.exceptions import ConnectionError
        with self.assertRaises(ConnectionError):
            circuit_breaker.call(failing_operation)
    
    def test_deadlock_detection_integration(self):
        """Test deadlock detection in integration scenario"""
        # Note: SQLite doesn't have traditional deadlocks like other databases
        # but we can test our deadlock detection logic
        
        from data.database.retry import DeadlockDetector
        detector = DeadlockDetector()
        
        # Register transactions
        detector.register_transaction("txn1")
        detector.register_transaction("txn2")
        detector.register_transaction("txn3")
        
        # Create potential deadlock cycle: txn1 -> txn2 -> txn3 -> txn1
        detector.register_wait("txn1", "txn2")
        detector.register_wait("txn2", "txn3")
        
        # This should detect deadlock
        with self.assertRaises(DeadlockError):
            detector.register_wait("txn3", "txn1")
    
    def test_connection_exhaustion_handling(self):
        """Test behavior when connection pool is exhausted"""
        # Get all available connections
        connections = []
        for i in range(self.connection_manager._config.max_pool_size):
            conn = self.connection_manager.get_connection()
            connections.append(conn)
        
        # Next connection should timeout
        with self.assertRaises(ConnectionTimeoutError):
            self.connection_manager.get_connection()
        
        # Return one connection
        self.connection_manager.return_connection(connections[0])
        
        # Should be able to get connection again
        new_conn = self.connection_manager.get_connection()
        self.assertIsNotNone(new_conn)
        
        # Return all connections
        self.connection_manager.return_connection(new_conn)
        for conn in connections[1:]:
            self.connection_manager.return_connection(conn)


class TestRepositoryIntegration(DatabaseTestCase):
    """Test repository integration with full stack"""
    
    def _custom_setup(self):
        """Setup repository for integration testing"""
        super()._custom_setup()
        
        # Setup content model and repository
        self.model_manager = ContentModelManager(self.connection_manager)
        self.model_manager.create_table()
        self.repository = ContentRepository(self.model_manager)
    
    def test_end_to_end_content_workflow(self):
        """Test complete content workflow from creation to deletion"""
        # Create content
        content = ContentModel(
            url="https://integration-test.com/video",
            platform=PlatformType.TIKTOK,
            content_type=ContentType.VIDEO,
            title="Integration Test Video",
            author="Integration Test Author",
            platform_id="integration123",
            status=ContentStatus.PENDING
        )
        
        # Save content
        saved_content = self.repository.save(content)
        self.assertIsNotNone(saved_content.id)
        
        # Find by various methods
        found_by_id = self.repository.find_by_id(saved_content.id)
        self.assertIsNotNone(found_by_id)
        
        found_by_url = self.repository.find_by_url(content.url)
        self.assertEqual(found_by_url.id, saved_content.id)
        
        found_by_platform_id = self.repository.find_by_platform_id(
            content.platform, content.platform_id
        )
        self.assertEqual(found_by_platform_id.id, saved_content.id)
        
        # Update content
        saved_content.status = ContentStatus.DOWNLOADING
        saved_content.title = "Updated Title"
        updated_content = self.repository.save(saved_content)
        
        self.assertEqual(updated_content.id, saved_content.id)
        self.assertEqual(updated_content.status, ContentStatus.DOWNLOADING)
        self.assertEqual(updated_content.title, "Updated Title")
        
        # Complete workflow
        updated_content.status = ContentStatus.COMPLETED
        updated_content.file_path = "/downloads/integration-test-video.mp4"
        final_content = self.repository.save(updated_content)
        
        # Verify final state
        self.assertEqual(final_content.status, ContentStatus.COMPLETED)
        self.assertIsNotNone(final_content.file_path)
        
        # Delete content
        delete_result = self.repository.delete_by_id(final_content.id)
        self.assertTrue(delete_result)
        
        # Verify deletion
        self.assertIsNone(self.repository.find_by_id(final_content.id))
    
    def test_repository_with_transactions(self):
        """Test repository operations within transactions"""
        with self.transaction_manager.transaction() as txn:
            # Create content within transaction
            content = ContentModel(
                url="https://transaction-test.com/video",
                platform=PlatformType.YOUTUBE,
                content_type=ContentType.VIDEO,
                title="Transaction Test Video",
                author="Transaction Author",
                platform_id="txn123"
            )
            
            saved_content = self.repository.save(content)
            self.assertIsNotNone(saved_content.id)
            
            # Content should be visible within transaction
            found_content = self.repository.find_by_id(saved_content.id)
            self.assertIsNotNone(found_content)
        
        # Content should be committed and visible after transaction
        final_content = self.repository.find_by_id(saved_content.id)
        self.assertIsNotNone(final_content)
        self.assertEqual(final_content.title, "Transaction Test Video")
    
    def test_repository_with_rollback(self):
        """Test repository operations with transaction rollback"""
        try:
            with self.transaction_manager.transaction() as txn:
                # Create content within transaction
                content = ContentModel(
                    url="https://rollback-test.com/video",
                    platform=PlatformType.INSTAGRAM,
                    content_type=ContentType.IMAGE,
                    title="Rollback Test Content",
                    author="Rollback Author",
                    platform_id="rollback123"
                )
                
                saved_content = self.repository.save(content)
                self.assertIsNotNone(saved_content.id)
                
                # Force rollback
                raise Exception("Force rollback")
                
        except Exception:
            pass  # Expected
        
        # Content should not exist after rollback
        # Note: We can't easily test this without the content ID,
        # so we'll verify by counting records
        count = self.repository.count()
        self.assertEqual(count, 0)


class TestPerformanceIntegration(PerformanceTestCase):
    """Test performance characteristics in integration scenarios"""
    
    def _custom_setup(self):
        """Setup for performance testing"""
        super()._custom_setup()
        
        # Setup repository for performance testing
        self.model_manager = ContentModelManager(self.connection_manager)
        self.model_manager.create_table()
        self.repository = ContentRepository(self.model_manager)
    
    def test_bulk_operations_performance(self):
        """Test performance of bulk database operations"""
        num_records = 200
        
        with self.performance_benchmark("bulk_content_insert") as metrics:
            for i in range(num_records):
                content = ContentModel(
                    url=f"https://bulk{i}.com/video",
                    platform=PlatformType.TIKTOK if i % 2 == 0 else PlatformType.YOUTUBE,
                    content_type=ContentType.VIDEO,
                    title=f"Bulk Video {i}",
                    author=f"Bulk Author {i}",
                    platform_id=f"bulk{i}"
                )
                self.repository.save(content)
        
        # Performance assertions
        self.assertLess(metrics["execution_time"], 10.0)  # Should complete in under 10 seconds
        
        # Verify all records were inserted
        count = self.repository.count()
        self.assertEqual(count, num_records)
        
        # Test bulk query performance
        with self.performance_benchmark("bulk_query") as query_metrics:
            all_content = self.repository.find_all()
            tiktok_content = self.repository.find_by_platform(PlatformType.TIKTOK)
            stats = self.repository.get_platform_stats()
        
        self.assertLess(query_metrics["execution_time"], 1.0)  # Queries should be fast
        self.assertEqual(len(all_content), num_records)
        self.assertEqual(len(tiktok_content), num_records // 2)
    
    def test_concurrent_access_performance(self):
        """Test performance under concurrent access"""
        def concurrent_worker(worker_id):
            start_time = time.time()
            
            # Each worker creates 10 records
            for i in range(10):
                content = ContentModel(
                    url=f"https://concurrent{worker_id}-{i}.com/video",
                    platform=PlatformType.TIKTOK,
                    content_type=ContentType.VIDEO,
                    title=f"Concurrent Video {worker_id}-{i}",
                    author=f"Worker {worker_id}",
                    platform_id=f"concurrent{worker_id}-{i}"
                )
                self.repository.save(content)
            
            execution_time = time.time() - start_time
            return {"worker_id": worker_id, "execution_time": execution_time}
        
        # Run 5 workers concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(concurrent_worker, i) for i in range(5)]
            results = [future.result() for future in as_completed(futures)]
        
        # All workers should complete successfully
        self.assertEqual(len(results), 5)
        
        # No worker should take too long
        for result in results:
            self.assertLess(result["execution_time"], 5.0)
        
        # Verify total records
        total_count = self.repository.count()
        self.assertEqual(total_count, 50)  # 5 workers * 10 records each
        
        # Check performance metrics
        self.assert_performance_thresholds()
    
    def test_memory_usage_under_load(self):
        """Test memory usage characteristics under load"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        with self.performance_benchmark("memory_load_test") as metrics:
            # Create a large number of objects
            for i in range(500):
                content = ContentModel(
                    url=f"https://memory{i}.com/video",
                    platform=PlatformType.TIKTOK,
                    content_type=ContentType.VIDEO,
                    title=f"Memory Test Video {i}" * 10,  # Larger strings
                    author=f"Memory Author {i}" * 5,
                    platform_id=f"memory{i}",
                    description="A" * 1000  # Large description
                )
                self.repository.save(content)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB for this test)
        self.assertLess(memory_increase, 100.0)
        
        metrics["memory_increase_mb"] = memory_increase
        metrics["initial_memory_mb"] = initial_memory
        metrics["final_memory_mb"] = final_memory


class TestFullStackIntegration(DatabaseTestCase):
    """Test full stack integration scenarios"""
    
    def _custom_setup(self):
        """Setup full stack components"""
        super()._custom_setup()
        
        # Setup all components
        self.model_manager = ContentModelManager(self.connection_manager)
        self.model_manager.create_table()
        self.repository = ContentRepository(self.model_manager)
        
        # Setup monitoring
        configure_monitoring(self.connection_manager, self.logger)
    
    def test_complete_application_workflow(self):
        """Test complete application workflow with all components"""
        # Create content with full workflow
        content_data = [
            {
                "url": "https://fullstack1.com/video",
                "platform": PlatformType.TIKTOK,
                "title": "Full Stack Video 1",
                "author": "Creator 1"
            },
            {
                "url": "https://fullstack2.com/video", 
                "platform": PlatformType.YOUTUBE,
                "title": "Full Stack Video 2",
                "author": "Creator 2"
            },
            {
                "url": "https://fullstack3.com/image",
                "platform": PlatformType.INSTAGRAM,
                "title": "Full Stack Image 1",
                "author": "Creator 3"
            }
        ]
        
        saved_content = []
        
        # Simulate content processing workflow
        for data in content_data:
            # Create content
            content = ContentModel(
                url=data["url"],
                platform=data["platform"],
                content_type=ContentType.VIDEO if "video" in data["url"] else ContentType.IMAGE,
                title=data["title"],
                author=data["author"],
                platform_id=f"fs_{len(saved_content) + 1}",
                status=ContentStatus.PENDING
            )
            
            # Save content
            saved = self.repository.save(content)
            saved_content.append(saved)
            
            # Simulate download process
            saved.status = ContentStatus.DOWNLOADING
            saved.download_progress = 0
            self.repository.save(saved)
            
            # Simulate progress updates
            for progress in [25, 50, 75, 100]:
                saved.download_progress = progress
                if progress == 100:
                    saved.status = ContentStatus.COMPLETED
                    saved.file_path = f"/downloads/{saved.platform_id}.mp4"
                    saved.file_size = 1024 * 1024 * 10  # 10MB
                
                self.repository.save(saved)
        
        # Verify final state
        completed_content = self.repository.find_by_status(ContentStatus.COMPLETED)
        self.assertEqual(len(completed_content), 3)
        
        # Check platform statistics
        stats = self.repository.get_platform_stats()
        self.assertEqual(stats[PlatformType.TIKTOK]["completed"], 1)
        self.assertEqual(stats[PlatformType.YOUTUBE]["completed"], 1)
        self.assertEqual(stats[PlatformType.INSTAGRAM]["completed"], 1)
        
        # Test search functionality
        search_results = self.repository.search_content("Full Stack")
        self.assertEqual(len(search_results), 3)
        
        # Test cleanup
        for content in saved_content:
            self.assertTrue(self.repository.delete_by_id(content.id))
        
        # Verify cleanup
        final_count = self.repository.count()
        self.assertEqual(final_count, 0)
    
    def test_error_recovery_integration(self):
        """Test error recovery in full stack scenario"""
        # Create content that will trigger various error conditions
        content = ContentModel(
            url="https://error-test.com/video",
            platform=PlatformType.TIKTOK,
            content_type=ContentType.VIDEO,
            title="Error Recovery Test",
            author="Error Author",
            platform_id="error123"
        )
        
        saved_content = self.repository.save(content)
        
        # Simulate download failure
        saved_content.status = ContentStatus.FAILED
        saved_content.error_message = "Network timeout during download"
        failed_content = self.repository.save(saved_content)
        
        # Verify error state
        self.assertEqual(failed_content.status, ContentStatus.FAILED)
        self.assertIsNotNone(failed_content.error_message)
        
        # Simulate retry
        failed_content.status = ContentStatus.PENDING
        failed_content.error_message = None
        failed_content.retry_count = 1
        retry_content = self.repository.save(failed_content)
        
        # Simulate successful retry
        retry_content.status = ContentStatus.COMPLETED
        retry_content.file_path = "/downloads/error123.mp4"
        final_content = self.repository.save(retry_content)
        
        # Verify recovery
        self.assertEqual(final_content.status, ContentStatus.COMPLETED)
        self.assertIsNone(final_content.error_message)
        self.assertEqual(final_content.retry_count, 1)


if __name__ == '__main__':
    unittest.main() 