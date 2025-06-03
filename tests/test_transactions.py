"""
Comprehensive test suite for Transaction Management System

Tests ACID properties, nested transactions, propagation behaviors,
and deadlock detection.
"""

import unittest
import tempfile
import shutil
import os
import threading
import time
import sqlite3
from unittest.mock import patch, MagicMock

from data.database.connection import SQLiteConnectionManager, ConnectionConfig, ConnectionState
from data.database.transactions import (
    TransactionManager, Transaction, TransactionIsolationLevel, TransactionPropagation,
    TransactionStatus, TransactionException, InvalidTransactionStateException,
    TransactionTimeoutException, get_transaction_manager, initialize_transaction_manager,
    transaction, get_current_transaction
)


class TestTransactionIsolationLevel(unittest.TestCase):
    """Test transaction isolation level enum"""
    
    def test_isolation_levels(self):
        """Test all isolation levels are defined"""
        self.assertEqual(TransactionIsolationLevel.DEFERRED.value, "DEFERRED")
        self.assertEqual(TransactionIsolationLevel.IMMEDIATE.value, "IMMEDIATE")
        self.assertEqual(TransactionIsolationLevel.EXCLUSIVE.value, "EXCLUSIVE")


class TestTransactionPropagation(unittest.TestCase):
    """Test transaction propagation behaviors"""
    
    def test_propagation_types(self):
        """Test all propagation types are defined"""
        propagations = [
            TransactionPropagation.REQUIRED,
            TransactionPropagation.REQUIRES_NEW,
            TransactionPropagation.NESTED,
            TransactionPropagation.SUPPORTS,
            TransactionPropagation.NOT_SUPPORTED,
            TransactionPropagation.NEVER,
            TransactionPropagation.MANDATORY
        ]
        
        # Ensure all are unique
        self.assertEqual(len(set(propagations)), len(propagations))


class TestTransaction(unittest.TestCase):
    """Test core Transaction class functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "transaction_test.db")
        
        # Create connection manager
        config = ConnectionConfig(
            database_path=self.db_path,
            max_pool_size=5,
            min_pool_size=1,
            connection_timeout=5.0
        )
        self.connection_manager = SQLiteConnectionManager(config)
        self.connection_manager.initialize()
        
        # Create transaction manager
        self.transaction_manager = TransactionManager(self.connection_manager)
    
    def tearDown(self):
        """Clean up test environment"""
        try:
            self.connection_manager.shutdown()
        except:
            pass
        
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_transaction_lifecycle(self):
        """Test basic transaction lifecycle"""
        # Begin transaction
        txn = self.transaction_manager.begin_transaction()
        
        self.assertIsNotNone(txn.transaction_id)
        self.assertEqual(txn.status, TransactionStatus.ACTIVE)
        self.assertEqual(txn.isolation_level, TransactionIsolationLevel.DEFERRED)
        self.assertTrue(txn.is_active)
        self.assertFalse(txn.is_rollback_only)
        
        # Get connection and create table
        conn = txn.get_connection()
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE test_table (id INTEGER, value TEXT)")
        cursor.execute("INSERT INTO test_table (id, value) VALUES (1, 'test')")
        cursor.close()
        
        # Commit transaction
        txn.commit()
        
        self.assertEqual(txn.status, TransactionStatus.COMMITTED)
        self.assertFalse(txn.is_active)
        
        # Verify data persisted
        with self.connection_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM test_table WHERE id = 1")
            result = cursor.fetchone()
            cursor.close()
        
        self.assertEqual(result[0], 'test')
    
    def test_transaction_rollback(self):
        """Test transaction rollback functionality"""
        # Begin transaction
        txn = self.transaction_manager.begin_transaction()
        
        # Create table and insert data
        conn = txn.get_connection()
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE test_table (id INTEGER, value TEXT)")
        cursor.execute("INSERT INTO test_table (id, value) VALUES (1, 'test')")
        cursor.close()
        
        # Rollback transaction
        txn.rollback()
        
        self.assertEqual(txn.status, TransactionStatus.ROLLED_BACK)
        self.assertFalse(txn.is_active)
        
        # Verify data was not persisted
        with self.connection_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'")
            result = cursor.fetchone()
            cursor.close()
        
        self.assertIsNone(result)
    
    def test_rollback_only_transaction(self):
        """Test rollback-only transaction behavior"""
        txn = self.transaction_manager.begin_transaction()
        
        # Mark for rollback only
        txn.mark_rollback_only()
        
        self.assertTrue(txn.is_rollback_only)
        self.assertEqual(txn.status, TransactionStatus.MARKED_ROLLBACK_ONLY)
        
        # Commit should fail
        with self.assertRaises(InvalidTransactionStateException):
            txn.commit()
    
    def test_savepoint_operations(self):
        """Test savepoint creation, rollback, and release"""
        txn = self.transaction_manager.begin_transaction()
        
        # Create table
        conn = txn.get_connection()
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE test_table (id INTEGER, value TEXT)")
        cursor.execute("INSERT INTO test_table (id, value) VALUES (1, 'initial')")
        cursor.close()
        
        # Create savepoint
        savepoint_name = txn.create_savepoint()
        self.assertIsNotNone(savepoint_name)
        
        # Add more data
        cursor = conn.cursor()
        cursor.execute("INSERT INTO test_table (id, value) VALUES (2, 'after_savepoint')")
        cursor.close()
        
        # Rollback to savepoint
        txn.rollback_to_savepoint(savepoint_name)
        
        # Verify only initial data remains
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM test_table")
        count = cursor.fetchone()[0]
        cursor.close()
        
        self.assertEqual(count, 1)
        
        # Release savepoint and commit
        txn.release_savepoint(savepoint_name)
        txn.commit()
    
    def test_nested_savepoints(self):
        """Test multiple nested savepoints"""
        txn = self.transaction_manager.begin_transaction()
        
        # Create table
        conn = txn.get_connection()
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE test_table (id INTEGER, value TEXT)")
        cursor.execute("INSERT INTO test_table (id, value) VALUES (1, 'initial')")
        cursor.close()
        
        # Create first savepoint
        sp1 = txn.create_savepoint("sp1")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO test_table (id, value) VALUES (2, 'sp1')")
        cursor.close()
        
        # Create second savepoint
        sp2 = txn.create_savepoint("sp2")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO test_table (id, value) VALUES (3, 'sp2')")
        cursor.close()
        
        # Rollback to first savepoint
        txn.rollback_to_savepoint(sp1)
        
        # Verify data state
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM test_table")
        count = cursor.fetchone()[0]
        cursor.close()
        
        self.assertEqual(count, 2)  # initial + sp1
        
        txn.commit()
    
    def test_invalid_transaction_operations(self):
        """Test operations on invalid transaction states"""
        txn = self.transaction_manager.begin_transaction()
        
        # Commit transaction
        txn.commit()
        
        # Operations on committed transaction should fail
        with self.assertRaises(InvalidTransactionStateException):
            txn.get_connection()
        
        with self.assertRaises(InvalidTransactionStateException):
            txn.create_savepoint()
        
        with self.assertRaises(InvalidTransactionStateException):
            txn.rollback_to_savepoint("nonexistent")
        
        with self.assertRaises(InvalidTransactionStateException):
            txn.commit()
        
        with self.assertRaises(InvalidTransactionStateException):
            txn.rollback()
    
    def test_context_manager(self):
        """Test transaction as context manager"""
        # Test successful commit
        with self.transaction_manager.begin_transaction() as txn:
            conn = txn.get_connection()
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE test_table (id INTEGER, value TEXT)")
            cursor.execute("INSERT INTO test_table (id, value) VALUES (1, 'test')")
            cursor.close()
        
        # Verify data persisted
        with self.connection_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM test_table WHERE id = 1")
            result = cursor.fetchone()
            cursor.close()
        
        self.assertEqual(result[0], 'test')
        
        # Test rollback on exception
        try:
            with self.transaction_manager.begin_transaction() as txn:
                conn = txn.get_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO test_table (id, value) VALUES (2, 'rollback_test')")
                cursor.close()
                raise Exception("Test exception")
        except Exception:
            pass
        
        # Verify data was rolled back
        with self.connection_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM test_table WHERE id = 2")
            count = cursor.fetchone()[0]
            cursor.close()
        
        self.assertEqual(count, 0)


class TestTransactionManager(unittest.TestCase):
    """Test TransactionManager functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "manager_test.db")
        
        config = ConnectionConfig(
            database_path=self.db_path,
            max_pool_size=5,
            min_pool_size=1,
            connection_timeout=5.0
        )
        self.connection_manager = SQLiteConnectionManager(config)
        self.connection_manager.initialize()
        
        self.transaction_manager = TransactionManager(self.connection_manager)
    
    def tearDown(self):
        """Clean up test environment"""
        try:
            self.connection_manager.shutdown()
        except:
            pass
        
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_current_transaction_tracking(self):
        """Test current transaction tracking per thread"""
        # Initially no current transaction
        self.assertIsNone(self.transaction_manager.get_current_transaction())
        
        # Begin transaction
        txn = self.transaction_manager.begin_transaction()
        
        # Should be current transaction
        current = self.transaction_manager.get_current_transaction()
        self.assertEqual(current.transaction_id, txn.transaction_id)
        
        # Commit transaction
        txn.commit()
        
        # Should no longer be current
        self.assertIsNone(self.transaction_manager.get_current_transaction())
    
    def test_multiple_active_transactions_per_thread_forbidden(self):
        """Test that multiple active transactions per thread are forbidden"""
        # Begin first transaction
        txn1 = self.transaction_manager.begin_transaction()
        
        # Attempt to begin second transaction should fail
        with self.assertRaises(TransactionException):
            self.transaction_manager.begin_transaction()
        
        # Commit first transaction
        txn1.commit()
        
        # Now second transaction should succeed
        txn2 = self.transaction_manager.begin_transaction()
        txn2.commit()
    
    def test_transaction_statistics(self):
        """Test transaction statistics tracking"""
        initial_stats = self.transaction_manager.get_statistics()
        
        # Begin and commit transaction
        txn1 = self.transaction_manager.begin_transaction()
        txn1.commit()
        
        # Begin and rollback transaction
        txn2 = self.transaction_manager.begin_transaction()
        txn2.rollback()
        
        final_stats = self.transaction_manager.get_statistics()
        
        self.assertEqual(final_stats.total_transactions, initial_stats.total_transactions + 2)
        self.assertEqual(final_stats.committed_transactions, initial_stats.committed_transactions + 1)
        self.assertEqual(final_stats.rolled_back_transactions, initial_stats.rolled_back_transactions + 1)
        self.assertEqual(final_stats.active_transactions, 0)
    
    def test_concurrent_transactions(self):
        """Test concurrent transactions from different threads"""
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                txn = self.transaction_manager.begin_transaction()
                conn = txn.get_connection()
                cursor = conn.cursor()
                
                # Create table if not exists
                cursor.execute("CREATE TABLE IF NOT EXISTS worker_test (id INTEGER, worker_id INTEGER)")
                cursor.execute("INSERT INTO worker_test (id, worker_id) VALUES (?, ?)", (worker_id, worker_id))
                cursor.close()
                
                time.sleep(0.01)  # Brief processing time
                txn.commit()
                results.append(worker_id)
                
            except Exception as e:
                errors.append(e)
        
        # Start multiple worker threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify results
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 5)
        self.assertEqual(set(results), {0, 1, 2, 3, 4})


class TestTransactionPropagation(unittest.TestCase):
    """Test transaction propagation behaviors"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "propagation_test.db")
        
        config = ConnectionConfig(
            database_path=self.db_path,
            max_pool_size=5,
            min_pool_size=1,
            connection_timeout=5.0
        )
        self.connection_manager = SQLiteConnectionManager(config)
        self.connection_manager.initialize()
        
        self.transaction_manager = TransactionManager(self.connection_manager)
    
    def tearDown(self):
        """Clean up test environment"""
        try:
            self.connection_manager.shutdown()
        except:
            pass
        
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_required_propagation(self):
        """Test REQUIRED propagation behavior"""
        # No existing transaction - should create new one
        with self.transaction_manager.transaction(propagation=TransactionPropagation.REQUIRED) as txn:
            self.assertIsNotNone(txn)
            txn1_id = txn.transaction_id
            
            # Nested REQUIRED - should reuse existing
            with self.transaction_manager.transaction(propagation=TransactionPropagation.REQUIRED) as txn2:
                self.assertEqual(txn2.transaction_id, txn1_id)
    
    def test_requires_new_propagation(self):
        """Test REQUIRES_NEW propagation behavior"""
        with self.transaction_manager.transaction(propagation=TransactionPropagation.REQUIRED) as txn1:
            txn1_id = txn1.transaction_id
            
            # REQUIRES_NEW should create new transaction
            with self.transaction_manager.transaction(propagation=TransactionPropagation.REQUIRES_NEW) as txn2:
                self.assertNotEqual(txn2.transaction_id, txn1_id)
    
    def test_nested_propagation(self):
        """Test NESTED propagation behavior with savepoints"""
        # Create table first
        with self.transaction_manager.transaction() as txn:
            conn = txn.get_connection()
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE test_nested (id INTEGER, value TEXT)")
            cursor.execute("INSERT INTO test_nested (id, value) VALUES (1, 'initial')")
            cursor.close()
        
        # Test nested transaction with savepoint
        with self.transaction_manager.transaction() as outer_txn:
            conn = outer_txn.get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO test_nested (id, value) VALUES (2, 'outer')")
            cursor.close()
            
            try:
                with self.transaction_manager.transaction(propagation=TransactionPropagation.NESTED) as inner_txn:
                    # Should be same transaction but with savepoint
                    self.assertEqual(inner_txn.transaction_id, outer_txn.transaction_id)
                    
                    conn = inner_txn.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO test_nested (id, value) VALUES (3, 'inner')")
                    cursor.close()
                    
                    # Simulate error in nested transaction
                    raise Exception("Nested transaction error")
                    
            except Exception:
                pass  # Expected exception
            
            # Outer transaction should still be valid
            # Inner transaction should be rolled back to savepoint
            conn = outer_txn.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM test_nested")
            count = cursor.fetchone()[0]
            cursor.close()
            
            # Should have initial + outer (inner was rolled back)
            self.assertEqual(count, 2)
    
    def test_supports_propagation(self):
        """Test SUPPORTS propagation behavior"""
        # No existing transaction - should work without transaction
        with self.transaction_manager.transaction(propagation=TransactionPropagation.SUPPORTS) as txn:
            self.assertIsNone(txn)
        
        # With existing transaction - should join
        with self.transaction_manager.transaction() as outer_txn:
            with self.transaction_manager.transaction(propagation=TransactionPropagation.SUPPORTS) as inner_txn:
                self.assertEqual(inner_txn.transaction_id, outer_txn.transaction_id)
    
    def test_not_supported_propagation(self):
        """Test NOT_SUPPORTED propagation behavior"""
        # Should work without transaction
        with self.transaction_manager.transaction(propagation=TransactionPropagation.NOT_SUPPORTED) as txn:
            self.assertIsNone(txn)
        
        # Even with existing transaction, should not use it
        with self.transaction_manager.transaction() as outer_txn:
            with self.transaction_manager.transaction(propagation=TransactionPropagation.NOT_SUPPORTED) as inner_txn:
                self.assertIsNone(inner_txn)
    
    def test_never_propagation(self):
        """Test NEVER propagation behavior"""
        # Should work without existing transaction
        with self.transaction_manager.transaction(propagation=TransactionPropagation.NEVER) as txn:
            self.assertIsNone(txn)
        
        # Should fail with existing transaction
        with self.transaction_manager.transaction() as outer_txn:
            with self.assertRaises(TransactionException):
                with self.transaction_manager.transaction(propagation=TransactionPropagation.NEVER):
                    pass
    
    def test_mandatory_propagation(self):
        """Test MANDATORY propagation behavior"""
        # Should fail without existing transaction
        with self.assertRaises(TransactionException):
            with self.transaction_manager.transaction(propagation=TransactionPropagation.MANDATORY):
                pass
        
        # Should work with existing transaction
        with self.transaction_manager.transaction() as outer_txn:
            with self.transaction_manager.transaction(propagation=TransactionPropagation.MANDATORY) as inner_txn:
                self.assertEqual(inner_txn.transaction_id, outer_txn.transaction_id)


class TestGlobalTransactionFunctions(unittest.TestCase):
    """Test global transaction management functions"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "global_test.db")
        
        # Reset global manager
        import data.database.transactions as txn_module
        txn_module._transaction_manager = None
        
        # Mock get_connection_manager
        config = ConnectionConfig(
            database_path=self.db_path,
            max_pool_size=5,
            min_pool_size=1,
            connection_timeout=5.0
        )
        self.connection_manager = SQLiteConnectionManager(config)
        self.connection_manager.initialize()
        
        self.manager_patcher = patch('data.database.transactions.get_connection_manager')
        self.mock_get_manager = self.manager_patcher.start()
        self.mock_get_manager.return_value = self.connection_manager
    
    def tearDown(self):
        """Clean up test environment"""
        self.manager_patcher.stop()
        
        try:
            self.connection_manager.shutdown()
        except:
            pass
        
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_global_transaction_manager(self):
        """Test global transaction manager initialization"""
        manager = get_transaction_manager()
        self.assertIsInstance(manager, TransactionManager)
        
        # Should return same instance
        manager2 = get_transaction_manager()
        self.assertIs(manager, manager2)
    
    def test_global_transaction_context(self):
        """Test global transaction context manager"""
        with transaction() as txn:
            self.assertIsNotNone(txn)
            self.assertIsInstance(txn, Transaction)
        
        # Test with propagation
        with transaction(propagation=TransactionPropagation.REQUIRED) as txn1:
            with transaction(propagation=TransactionPropagation.NESTED) as txn2:
                self.assertEqual(txn1.transaction_id, txn2.transaction_id)
    
    def test_global_current_transaction(self):
        """Test global current transaction tracking"""
        # Initially no current transaction
        self.assertIsNone(get_current_transaction())
        
        # Within transaction context
        with transaction() as txn:
            current = get_current_transaction()
            self.assertEqual(current.transaction_id, txn.transaction_id)
        
        # After transaction context
        self.assertIsNone(get_current_transaction())


class TestTransactionIntegration(unittest.TestCase):
    """Integration tests for transaction system"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "integration_test.db")
        
        config = ConnectionConfig(
            database_path=self.db_path,
            max_pool_size=10,
            min_pool_size=2,
            connection_timeout=5.0
        )
        self.connection_manager = SQLiteConnectionManager(config)
        self.connection_manager.initialize()
        
        self.transaction_manager = TransactionManager(self.connection_manager)
    
    def tearDown(self):
        """Clean up integration test environment"""
        try:
            self.connection_manager.shutdown()
        except:
            pass
        
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_acid_properties(self):
        """Test ACID properties of transactions"""
        # Atomicity: All operations succeed or all fail
        try:
            with self.transaction_manager.transaction() as txn:
                conn = txn.get_connection()
                cursor = conn.cursor()
                
                cursor.execute("CREATE TABLE acid_test (id INTEGER PRIMARY KEY, value TEXT)")
                cursor.execute("INSERT INTO acid_test (value) VALUES ('test1')")
                cursor.execute("INSERT INTO acid_test (value) VALUES ('test2')")
                
                # Simulate error
                raise Exception("Simulated error")
                
        except Exception:
            pass
        
        # Verify no data was committed
        with self.connection_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='acid_test'")
            result = cursor.fetchone()
            cursor.close()
        
        self.assertIsNone(result)  # Table should not exist
        
        # Consistency: Successful transaction
        with self.transaction_manager.transaction() as txn:
            conn = txn.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("CREATE TABLE acid_test (id INTEGER PRIMARY KEY, value TEXT)")
            cursor.execute("INSERT INTO acid_test (value) VALUES ('test1')")
            cursor.execute("INSERT INTO acid_test (value) VALUES ('test2')")
            cursor.close()
        
        # Verify data was committed
        with self.connection_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM acid_test")
            count = cursor.fetchone()[0]
            cursor.close()
        
        self.assertEqual(count, 2)
    
    def test_isolation_levels(self):
        """Test different isolation levels"""
        # Create table
        with self.transaction_manager.transaction() as txn:
            conn = txn.get_connection()
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE isolation_test (id INTEGER, value TEXT)")
            cursor.execute("INSERT INTO isolation_test (id, value) VALUES (1, 'initial')")
            cursor.close()
        
        # Test DEFERRED isolation (default)
        txn1 = self.transaction_manager.begin_transaction(TransactionIsolationLevel.DEFERRED)
        self.assertEqual(txn1.isolation_level, TransactionIsolationLevel.DEFERRED)
        txn1.commit()
        
        # Test IMMEDIATE isolation
        txn2 = self.transaction_manager.begin_transaction(TransactionIsolationLevel.IMMEDIATE)
        self.assertEqual(txn2.isolation_level, TransactionIsolationLevel.IMMEDIATE)
        txn2.commit()
        
        # Test EXCLUSIVE isolation
        txn3 = self.transaction_manager.begin_transaction(TransactionIsolationLevel.EXCLUSIVE)
        self.assertEqual(txn3.isolation_level, TransactionIsolationLevel.EXCLUSIVE)
        txn3.commit()
    
    def test_complex_nested_operations(self):
        """Test complex nested transaction operations"""
        # Create initial data
        with self.transaction_manager.transaction() as txn:
            conn = txn.get_connection()
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE nested_test (id INTEGER, operation TEXT, level INTEGER)")
            cursor.execute("INSERT INTO nested_test (id, operation, level) VALUES (1, 'initial', 0)")
            cursor.close()
        
        # Complex nested transaction scenario
        with self.transaction_manager.transaction() as outer_txn:
            conn = outer_txn.get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO nested_test (id, operation, level) VALUES (2, 'outer', 1)")
            cursor.close()
            
            # Create savepoint and do some work
            sp1 = outer_txn.create_savepoint("level1")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO nested_test (id, operation, level) VALUES (3, 'sp1', 2)")
            cursor.close()
            
            # Another savepoint
            sp2 = outer_txn.create_savepoint("level2")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO nested_test (id, operation, level) VALUES (4, 'sp2', 3)")
            cursor.close()
            
            # Rollback to first savepoint
            outer_txn.rollback_to_savepoint(sp1)
            
            # Add different data
            cursor = conn.cursor()
            cursor.execute("INSERT INTO nested_test (id, operation, level) VALUES (5, 'after_rollback', 2)")
            cursor.close()
            
            # Release savepoint
            outer_txn.release_savepoint(sp1)
        
        # Verify final state
        with self.connection_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT operation FROM nested_test ORDER BY id")
            operations = [row[0] for row in cursor.fetchall()]
            cursor.close()
        
        expected = ['initial', 'outer', 'sp1', 'after_rollback']
        self.assertEqual(operations, expected)


if __name__ == '__main__':
    unittest.main() 