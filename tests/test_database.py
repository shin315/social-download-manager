"""
Test suite for Database Connection Manager

Tests connection pooling, health checks, transaction management,
and integration with the application layer.
"""

import unittest
import sqlite3
import tempfile
import os
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports  
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.database.connection import (
    ConnectionState, ConnectionConfig, ConnectionStats,
    DatabaseError, ConnectionPoolError, ConnectionTimeoutError,
    SQLiteConnectionManager, get_connection_manager,
    initialize_database, shutdown_database,
    database_connection, database_transaction
)


class TestConnectionConfig(unittest.TestCase):
    """Test ConnectionConfig validation and defaults"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = ConnectionConfig(database_path="test.db")
        
        self.assertEqual(config.database_path, "test.db")
        self.assertEqual(config.max_pool_size, 10)
        self.assertEqual(config.min_pool_size, 2)
        self.assertEqual(config.connection_timeout, 30.0)
        self.assertTrue(config.enable_wal_mode)
        self.assertTrue(config.enable_foreign_keys)
    
    def test_custom_config(self):
        """Test custom configuration values"""
        config = ConnectionConfig(
            database_path="custom.db",
            max_pool_size=5,
            min_pool_size=1,
            connection_timeout=15.0,
            enable_wal_mode=False
        )
        
        self.assertEqual(config.database_path, "custom.db")
        self.assertEqual(config.max_pool_size, 5)
        self.assertEqual(config.min_pool_size, 1)
        self.assertEqual(config.connection_timeout, 15.0)
        self.assertFalse(config.enable_wal_mode)


class TestSQLiteConnectionManager(unittest.TestCase):
    """Test SQLite connection manager functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        
        self.config = ConnectionConfig(
            database_path=self.db_path,
            max_pool_size=5,
            min_pool_size=1,
            connection_timeout=5.0,
            pool_timeout=1.0
        )
        
        self.manager = SQLiteConnectionManager(self.config)
    
    def tearDown(self):
        """Clean up test environment"""
        try:
            self.manager.shutdown()
        except:
            pass
        
        # Clean up temp files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test connection manager initialization"""
        self.assertEqual(self.manager._state, ConnectionState.UNINITIALIZED)
        
        # Initialize
        result = self.manager.initialize()
        self.assertTrue(result)
        self.assertEqual(self.manager._state, ConnectionState.CONNECTED)
        
        # Database file should exist
        self.assertTrue(os.path.exists(self.db_path))
    
    def test_double_initialization(self):
        """Test that double initialization is handled gracefully"""
        self.assertTrue(self.manager.initialize())
        self.assertTrue(self.manager.initialize())  # Should not fail
        self.assertEqual(self.manager._state, ConnectionState.CONNECTED)
    
    def test_config_validation(self):
        """Test configuration parameter validation"""
        # Invalid max_pool_size
        with self.assertRaises(ValueError):
            bad_config = ConnectionConfig(database_path="test.db", max_pool_size=0)
            SQLiteConnectionManager(bad_config)
        
        # Invalid min_pool_size
        with self.assertRaises(ValueError):
            bad_config = ConnectionConfig(database_path="test.db", min_pool_size=-1)
            SQLiteConnectionManager(bad_config)
        
        # min_pool_size > max_pool_size
        with self.assertRaises(ValueError):
            bad_config = ConnectionConfig(
                database_path="test.db", 
                min_pool_size=5, 
                max_pool_size=3
            )
            SQLiteConnectionManager(bad_config)
    
    def test_connection_lifecycle(self):
        """Test getting and returning connections"""
        self.manager.initialize()
        
        # Get connection
        conn = self.manager.get_connection()
        self.assertIsInstance(conn, sqlite3.Connection)
        
        # Test connection works
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        self.assertEqual(result[0], 1)
        
        # Return connection
        self.manager.return_connection(conn)
        
        # Stats should be updated
        stats = self.manager.get_stats()
        self.assertEqual(stats.active_connections, 0)
        self.assertGreater(stats.connection_requests, 0)
    
    def test_connection_pool_stats(self):
        """Test connection pool statistics tracking"""
        self.manager.initialize()
        
        initial_stats = self.manager.get_stats()
        self.assertEqual(initial_stats.active_connections, 0)
        self.assertGreaterEqual(initial_stats.idle_connections, self.config.min_pool_size)
        
        # Get multiple connections
        connections = []
        for i in range(3):
            conn = self.manager.get_connection()
            connections.append(conn)
        
        # Check stats
        stats = self.manager.get_stats()
        self.assertEqual(stats.active_connections, 3)
        self.assertEqual(stats.connection_requests, 3)
        
        # Return connections
        for conn in connections:
            self.manager.return_connection(conn)
        
        # Check final stats
        final_stats = self.manager.get_stats()
        self.assertEqual(final_stats.active_connections, 0)
    
    def test_pool_exhaustion(self):
        """Test behavior when connection pool is exhausted"""
        self.manager.initialize()
        
        # Get all available connections
        connections = []
        for i in range(self.config.max_pool_size):
            conn = self.manager.get_connection()
            connections.append(conn)
        
        # Try to get one more - should timeout
        with self.assertRaises(ConnectionTimeoutError):
            self.manager.get_connection()
        
        # Return one connection
        self.manager.return_connection(connections[0])
        
        # Should be able to get connection again
        new_conn = self.manager.get_connection()
        self.assertIsInstance(new_conn, sqlite3.Connection)
        
        # Clean up
        for conn in connections[1:] + [new_conn]:
            self.manager.return_connection(conn)
    
    def test_connection_health_check(self):
        """Test database health check functionality"""
        self.manager.initialize()
        
        # Health check should pass
        self.assertTrue(self.manager.health_check())
        
        # Test with shutdown manager
        self.manager.shutdown()
        self.assertFalse(self.manager.health_check())
    
    def test_context_managers(self):
        """Test connection and transaction context managers"""
        self.manager.initialize()
        
        # Test connection context manager
        with self.manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE test (id INTEGER)")
            cursor.close()
        
        # Test transaction context manager
        with self.manager.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO test (id) VALUES (1)")
            cursor.close()
        
        # Verify data was committed
        with self.manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM test")
            count = cursor.fetchone()[0]
            cursor.close()
        
        self.assertEqual(count, 1)
    
    def test_transaction_rollback(self):
        """Test transaction rollback functionality"""
        self.manager.initialize()
        
        # Create table
        with self.manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE test (id INTEGER)")
            cursor.close()
        
        # Test rollback on exception
        try:
            with self.manager.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO test (id) VALUES (1)")
                cursor.close()
                raise Exception("Test exception")
        except Exception:
            pass
        
        # Verify data was rolled back
        with self.manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM test")
            count = cursor.fetchone()[0]
            cursor.close()
        
        self.assertEqual(count, 0)
    
    def test_concurrent_connections(self):
        """Test concurrent connection handling"""
        self.manager.initialize()
        
        results = []
        errors = []
        
        def worker():
            try:
                with self.manager.connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()[0]
                    cursor.close()
                    results.append(result)
                    time.sleep(0.01)  # Brief hold
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify results
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 10)
        self.assertTrue(all(r == 1 for r in results))
    
    def test_shutdown(self):
        """Test manager shutdown functionality"""
        self.manager.initialize()
        
        # Get some connections
        conn1 = self.manager.get_connection()
        conn2 = self.manager.get_connection()
        
        # Shutdown should clean up everything
        result = self.manager.shutdown()
        self.assertTrue(result)
        self.assertEqual(self.manager._state, ConnectionState.DISCONNECTED)
        
        # Should not be able to get new connections
        with self.assertRaises(ConnectionPoolError):
            self.manager.get_connection()
    
    def test_error_handling(self):
        """Test error handling scenarios"""
        # Test initialization with invalid path (read-only)
        if os.name != 'nt':  # Unix-like systems
            readonly_config = ConnectionConfig(database_path="/readonly/test.db")
            readonly_manager = SQLiteConnectionManager(readonly_config)
            
            self.assertFalse(readonly_manager.initialize())
            self.assertEqual(readonly_manager._state, ConnectionState.ERROR)


class TestGlobalFunctions(unittest.TestCase):
    """Test global database functions"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "global_test.db")
        
        # Override global manager directly instead of mocking config
        import data.database.connection as db_module
        if hasattr(db_module, '_connection_manager'):
            db_module._connection_manager = None
        
        # Create explicit config for testing
        from data.database.connection import ConnectionConfig, SQLiteConnectionManager
        self.test_config = ConnectionConfig(
            database_path=self.db_path,
            max_pool_size=5,
            min_pool_size=1,
            connection_timeout=5.0
        )
        
        # Patch get_connection_manager to return our test manager
        self.manager_patcher = patch('data.database.connection.get_connection_manager')
        self.mock_get_manager = self.manager_patcher.start()
        self.test_manager = SQLiteConnectionManager(self.test_config)
        self.mock_get_manager.return_value = self.test_manager
    
    def tearDown(self):
        """Clean up test environment"""
        self.manager_patcher.stop()
        
        try:
            self.test_manager.shutdown()
        except:
            pass
        
        # Clean up temp files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_global_initialization(self):
        """Test global database initialization"""
        # Initialize our test manager first
        self.test_manager.initialize()
        
        result = initialize_database()
        self.assertTrue(result)
        
        # Should be able to get connection manager
        manager = get_connection_manager()
        self.assertIsNotNone(manager)
        self.assertEqual(manager._state, ConnectionState.CONNECTED)
    
    def test_global_context_managers(self):
        """Test global context managers"""
        initialize_database()
        
        # Test global connection context manager
        with database_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE global_test (id INTEGER)")
            cursor.close()
        
        # Test global transaction context manager
        with database_transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO global_test (id) VALUES (42)")
            cursor.close()
        
        # Verify data
        with database_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM global_test")
            result = cursor.fetchone()
            cursor.close()
        
        self.assertEqual(result[0], 42)
    
    def test_global_shutdown(self):
        """Test global database shutdown"""
        initialize_database()
        
        # Should have a manager
        manager = get_connection_manager()
        self.assertEqual(manager._state, ConnectionState.CONNECTED)
        
        # Shutdown
        result = shutdown_database()
        self.assertTrue(result)


class TestDatabaseIntegration(unittest.TestCase):
    """Integration tests for database components"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "integration_test.db")
    
    def tearDown(self):
        """Clean up integration test environment"""
        # Clean up temp files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_wal_mode_configuration(self):
        """Test WAL mode configuration"""
        config = ConnectionConfig(
            database_path=self.db_path,
            enable_wal_mode=True
        )
        
        manager = SQLiteConnectionManager(config)
        manager.initialize()
        
        try:
            with manager.connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA journal_mode")
                mode = cursor.fetchone()[0]
                cursor.close()
            
            self.assertEqual(mode.upper(), "WAL")
        finally:
            manager.shutdown()
    
    def test_foreign_keys_configuration(self):
        """Test foreign key constraints configuration"""
        config = ConnectionConfig(
            database_path=self.db_path,
            enable_foreign_keys=True
        )
        
        manager = SQLiteConnectionManager(config)
        manager.initialize()
        
        try:
            with manager.connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA foreign_keys")
                enabled = cursor.fetchone()[0]
                cursor.close()
            
            self.assertEqual(enabled, 1)
        finally:
            manager.shutdown()
    
    def test_performance_settings(self):
        """Test performance-related settings"""
        # Ensure absolutely fresh database for page_size test
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        if os.path.exists(self.db_path + "-wal"):
            os.remove(self.db_path + "-wal")
        if os.path.exists(self.db_path + "-shm"):
            os.remove(self.db_path + "-shm")
            
        config = ConnectionConfig(
            database_path=self.db_path,
            page_size=8192,
            cache_size=-32000
        )
        
        manager = SQLiteConnectionManager(config)
        manager.initialize()
        
        try:
            with manager.connection() as conn:
                cursor = conn.cursor()
                
                # Check page size (should work on fresh database)
                cursor.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]
                
                # Check cache size (this should always work)
                cursor.execute("PRAGMA cache_size")
                cache_size = cursor.fetchone()[0]
                
                cursor.close()
            
            # Page size should be set correctly on fresh database
            self.assertEqual(page_size, 8192)
            self.assertEqual(cache_size, -32000)
        finally:
            manager.shutdown()


if __name__ == '__main__':
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Run tests
    unittest.main() 