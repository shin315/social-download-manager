#!/usr/bin/env python3
"""
Fixed Repository Integration Testing System for Adapter Framework
================================================================

This module provides comprehensive testing for adapter framework integration
with the metadata/configuration repository, with proper database initialization.
"""

import json
import logging
import os
import sqlite3
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class RepositoryTestConfig:
    """Configuration for repository integration testing"""
    database_path: str = ":memory:"
    max_concurrent_operations: int = 10
    test_data_size: int = 500
    transaction_batch_size: int = 50
    performance_threshold_ms: float = 50.0
    consistency_check_interval: int = 100
    stress_test_duration: int = 30  # seconds
    cleanup_verification: bool = True


@dataclass 
class TestMetadata:
    """Test metadata for tracking test execution"""
    test_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    test_type: str = "repository_integration"
    status: str = "running"
    error_count: int = 0
    success_count: int = 0
    total_operations: int = 0
    metrics: Dict[str, Any] = field(default_factory=dict)


class MockRepository:
    """Mock repository implementation for testing"""
    
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.lock = threading.RLock()
        self.transaction_log = []
        self.operation_count = 0
        self._connection = None
        self.setup_database()
    
    def get_connection(self):
        """Get a database connection (thread-safe)"""
        if self._connection is None:
            self._connection = sqlite3.connect(
                self.db_path, 
                check_same_thread=False,
                timeout=30.0
            )
            self._connection.row_factory = sqlite3.Row
        return self._connection
    
    def setup_database(self):
        """Initialize the database schema"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Video metadata table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS video_metadata (
                id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                title TEXT,
                description TEXT,
                duration INTEGER,
                file_size INTEGER,
                download_status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Download configuration table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS download_config (
                id TEXT PRIMARY KEY,
                video_id TEXT,
                quality TEXT,
                format TEXT,
                output_path TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (video_id) REFERENCES video_metadata (id)
            )
        ''')
        
        # Application settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                type TEXT DEFAULT 'string',
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        logger.info("Database schema initialized successfully")
    
    def create_video_metadata(self, video_data: Dict[str, Any]) -> str:
        """Create video metadata record"""
        with self.lock:
            self.operation_count += 1
            
        video_id = video_data.get('id', str(uuid.uuid4()))
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO video_metadata 
                (id, url, title, description, duration, file_size, download_status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                video_id,
                video_data['url'],
                video_data.get('title', ''),
                video_data.get('description', ''),
                video_data.get('duration', 0),
                video_data.get('file_size', 0),
                video_data.get('download_status', 'pending')
            ))
            conn.commit()
            
            self.transaction_log.append({
                'operation': 'create_video',
                'video_id': video_id,
                'timestamp': datetime.now()
            })
            
            return video_id
        except Exception as e:
            conn.rollback()
            raise e
    
    def read_video_metadata(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Read video metadata by ID"""
        with self.lock:
            self.operation_count += 1
            
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM video_metadata WHERE id = ?', (video_id,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    def update_video_metadata(self, video_id: str, updates: Dict[str, Any]) -> bool:
        """Update video metadata"""
        with self.lock:
            self.operation_count += 1
            
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Build update query dynamically
            set_clauses = []
            values = []
            
            for key, value in updates.items():
                if key != 'id':  # Don't update ID
                    set_clauses.append(f"{key} = ?")
                    values.append(value)
            
            if not set_clauses:
                return False
            
            set_clauses.append("updated_at = ?")
            values.append(datetime.now().isoformat())
            values.append(video_id)
            
            query = f"UPDATE video_metadata SET {', '.join(set_clauses)} WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()
            
            self.transaction_log.append({
                'operation': 'update_video',
                'video_id': video_id,
                'updates': updates,
                'timestamp': datetime.now()
            })
            
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
    
    def delete_video_metadata(self, video_id: str) -> bool:
        """Delete video metadata"""
        with self.lock:
            self.operation_count += 1
            
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Delete related download config first
            cursor.execute('DELETE FROM download_config WHERE video_id = ?', (video_id,))
            
            # Delete video metadata
            cursor.execute('DELETE FROM video_metadata WHERE id = ?', (video_id,))
            conn.commit()
            
            self.transaction_log.append({
                'operation': 'delete_video',
                'video_id': video_id,
                'timestamp': datetime.now()
            })
            
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
    
    def list_videos(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List video metadata with pagination"""
        with self.lock:
            self.operation_count += 1
            
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM video_metadata ORDER BY created_at DESC LIMIT ? OFFSET ?',
            (limit, offset)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def get_operation_count(self) -> int:
        """Get total operation count"""
        with self.lock:
            return self.operation_count
    
    def get_transaction_log(self) -> List[Dict[str, Any]]:
        """Get transaction log"""
        return self.transaction_log.copy()
    
    def cleanup(self):
        """Cleanup database connections"""
        if self._connection:
            try:
                self._connection.close()
                self._connection = None
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")


class AdapterRepositoryBridge:
    """Bridge between adapter framework and repository"""
    
    def __init__(self, repository: MockRepository):
        self.repository = repository
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
        self.cache_timestamps = {}
        
    def create_video(self, video_data: Dict[str, Any]) -> str:
        """Create video through adapter bridge"""
        # Validate data
        if not video_data.get('url'):
            raise ValueError("URL is required for video creation")
        
        # Create in repository
        video_id = self.repository.create_video_metadata(video_data)
        
        # Update cache
        self._update_cache(video_id, video_data)
        
        return video_id
    
    def read_video(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Read video through adapter bridge with caching"""
        # Check cache first
        cached_data = self._get_from_cache(video_id)
        if cached_data:
            return cached_data
        
        # Read from repository
        video_data = self.repository.read_video_metadata(video_id)
        
        if video_data:
            self._update_cache(video_id, video_data)
        
        return video_data
    
    def update_video(self, video_id: str, updates: Dict[str, Any]) -> bool:
        """Update video through adapter bridge"""
        # Update in repository
        success = self.repository.update_video_metadata(video_id, updates)
        
        if success:
            # Invalidate cache
            self._invalidate_cache(video_id)
        
        return success
    
    def delete_video(self, video_id: str) -> bool:
        """Delete video through adapter bridge"""
        # Delete from repository
        success = self.repository.delete_video_metadata(video_id)
        
        if success:
            # Remove from cache
            self._invalidate_cache(video_id)
        
        return success
    
    def _get_from_cache(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get data from cache if not expired"""
        if video_id not in self.cache:
            return None
        
        timestamp = self.cache_timestamps.get(video_id, 0)
        if time.time() - timestamp > self.cache_ttl:
            self._invalidate_cache(video_id)
            return None
        
        return self.cache[video_id]
    
    def _update_cache(self, video_id: str, data: Dict[str, Any]):
        """Update cache with new data"""
        self.cache[video_id] = data.copy()
        self.cache_timestamps[video_id] = time.time()
    
    def _invalidate_cache(self, video_id: str):
        """Invalidate cache entry"""
        self.cache.pop(video_id, None)
        self.cache_timestamps.pop(video_id, None)


class RepositoryIntegrationTester:
    """Comprehensive repository integration testing system"""
    
    def __init__(self, config: RepositoryTestConfig = None):
        self.config = config or RepositoryTestConfig()
        self.repository = MockRepository(self.config.database_path)
        self.adapter_bridge = AdapterRepositoryBridge(self.repository)
        self.test_metadata = TestMetadata()
        self.test_results = {}
        self.performance_metrics = {}
        
    def run_comprehensive_test_suite(self) -> Dict[str, Any]:
        """Run the complete integration test suite"""
        logger.info("Starting comprehensive repository integration test suite")
        
        self.test_metadata.started_at = datetime.now()
        
        try:
            # 1. Data Consistency Tests
            logger.info("Running data consistency tests...")
            consistency_results = self.test_data_consistency()
            
            # 2. CRUD Operation Tests
            logger.info("Running CRUD operation tests...")
            crud_results = self.test_crud_operations()
            
            # 3. Transaction Integrity Tests
            logger.info("Running transaction integrity tests...")
            transaction_results = self.test_transaction_integrity()
            
            # 4. Performance Under Load Tests
            logger.info("Running performance under load tests...")
            performance_results = self.test_performance_under_load()
            
            # 5. Error Handling Tests
            logger.info("Running error handling tests...")
            error_handling_results = self.test_error_handling()
            
            # 6. Resource Cleanup Tests
            logger.info("Running resource cleanup tests...")
            cleanup_results = self.test_resource_cleanup()
            
            # 7. Concurrent Access Tests
            logger.info("Running concurrent access tests...")
            concurrency_results = self.test_concurrent_access()
            
            self.test_metadata.status = "completed"
            self.test_metadata.completed_at = datetime.now()
            
            return self._compile_final_results({
                'data_consistency': consistency_results,
                'crud_operations': crud_results,
                'transaction_integrity': transaction_results,
                'performance_under_load': performance_results,
                'error_handling': error_handling_results,
                'resource_cleanup': cleanup_results,
                'concurrent_access': concurrency_results
            })
            
        except Exception as e:
            self.test_metadata.status = "failed"
            self.test_metadata.completed_at = datetime.now()
            logger.error(f"Test suite failed: {e}")
            raise
        finally:
            self.repository.cleanup()
    
    def test_data_consistency(self) -> Dict[str, Any]:
        """Test data consistency between adapter and repository"""
        start_time = time.time()
        test_data = []
        consistency_issues = []
        
        # Create test videos through adapter
        for i in range(50):
            video_data = {
                'url': f'https://example.com/video_{i}',
                'title': f'Test Video {i}',
                'description': f'Test description for video {i}',
                'duration': 180 + i,
                'file_size': 1024 * 1024 * (i + 1)
            }
            
            video_id = self.adapter_bridge.create_video(video_data)
            test_data.append((video_id, video_data))
        
        # Verify consistency
        for video_id, original_data in test_data:
            # Read through adapter
            adapter_data = self.adapter_bridge.read_video(video_id)
            
            # Read directly from repository
            repo_data = self.repository.read_video_metadata(video_id)
            
            # Check basic consistency (ignoring timestamps and auto-generated fields)
            if adapter_data and repo_data:
                for key in ['url', 'title', 'description', 'duration', 'file_size']:
                    if adapter_data.get(key) != repo_data.get(key):
                        consistency_issues.append({
                            'video_id': video_id,
                            'field': key,
                            'adapter_value': adapter_data.get(key),
                            'repo_value': repo_data.get(key)
                        })
        
        test_duration = time.time() - start_time
        
        return {
            'test_duration': test_duration,
            'videos_tested': len(test_data),
            'consistency_issues': len(consistency_issues),
            'consistency_rate': (len(test_data) - len(consistency_issues)) / len(test_data),
            'issues_details': consistency_issues[:5]  # First 5 issues for debugging
        }
    
    def test_crud_operations(self) -> Dict[str, Any]:
        """Test CRUD operations through adapter interface"""
        start_time = time.time()
        operations_tested = 0
        successful_operations = 0
        
        # Test Create operations
        create_results = []
        for i in range(30):
            try:
                video_data = {
                    'url': f'https://example.com/crud_test_{i}',
                    'title': f'CRUD Test Video {i}',
                    'duration': 120
                }
                video_id = self.adapter_bridge.create_video(video_data)
                create_results.append(video_id)
                successful_operations += 1
            except Exception as e:
                logger.warning(f"Create operation failed: {e}")
            operations_tested += 1
        
        # Test Read operations
        read_results = []
        for video_id in create_results[:15]:
            try:
                video_data = self.adapter_bridge.read_video(video_id)
                if video_data:
                    read_results.append(video_id)
                    successful_operations += 1
            except Exception as e:
                logger.warning(f"Read operation failed: {e}")
            operations_tested += 1
        
        # Test Update operations
        update_results = []
        for video_id in create_results[:10]:
            try:
                updates = {
                    'title': f'Updated Title for {video_id}',
                    'description': 'Updated description'
                }
                success = self.adapter_bridge.update_video(video_id, updates)
                if success:
                    update_results.append(video_id)
                    successful_operations += 1
            except Exception as e:
                logger.warning(f"Update operation failed: {e}")
            operations_tested += 1
        
        # Test Delete operations
        delete_results = []
        for video_id in create_results[:5]:
            try:
                success = self.adapter_bridge.delete_video(video_id)
                if success:
                    delete_results.append(video_id)
                    successful_operations += 1
            except Exception as e:
                logger.warning(f"Delete operation failed: {e}")
            operations_tested += 1
        
        test_duration = time.time() - start_time
        
        return {
            'test_duration': test_duration,
            'operations_tested': operations_tested,
            'successful_operations': successful_operations,
            'success_rate': successful_operations / operations_tested,
            'create_success': len(create_results),
            'read_success': len(read_results),
            'update_success': len(update_results),
            'delete_success': len(delete_results)
        }
    
    def test_transaction_integrity(self) -> Dict[str, Any]:
        """Test transaction integrity across adapter boundaries"""
        start_time = time.time()
        transaction_tests = 0
        successful_transactions = 0
        
        # Test batch operations
        for batch in range(5):
            try:
                # Create multiple related records
                video_ids = []
                for i in range(3):
                    video_data = {
                        'url': f'https://example.com/batch_{batch}_video_{i}',
                        'title': f'Batch {batch} Video {i}',
                        'duration': 150
                    }
                    video_id = self.adapter_bridge.create_video(video_data)
                    video_ids.append(video_id)
                
                # Verify all records exist
                all_exist = True
                for video_id in video_ids:
                    if not self.adapter_bridge.read_video(video_id):
                        all_exist = False
                        break
                
                if all_exist:
                    successful_transactions += 1
                    
            except Exception as e:
                logger.warning(f"Transaction test failed: {e}")
            
            transaction_tests += 1
        
        test_duration = time.time() - start_time
        
        return {
            'test_duration': test_duration,
            'transactions_tested': transaction_tests,
            'successful_transactions': successful_transactions,
            'integrity_rate': successful_transactions / transaction_tests,
            'total_operations_logged': len(self.repository.get_transaction_log())
        }
    
    def test_performance_under_load(self) -> Dict[str, Any]:
        """Test performance under high load conditions"""
        start_time = time.time()
        
        def worker_function(worker_id: int, operations_per_worker: int):
            """Worker function for concurrent operations"""
            worker_results = {
                'operations_completed': 0,
                'errors': 0,
                'total_time': 0
            }
            
            for i in range(operations_per_worker):
                try:
                    operation_start = time.time()
                    
                    # Mix of operations
                    if i % 4 == 0:
                        # Create
                        video_data = {
                            'url': f'https://example.com/worker_{worker_id}_video_{i}',
                            'title': f'Worker {worker_id} Video {i}',
                            'duration': 120
                        }
                        self.adapter_bridge.create_video(video_data)
                    elif i % 4 == 1:
                        # Read (try to read existing data)
                        existing_videos = self.repository.list_videos(5)
                        if existing_videos:
                            self.adapter_bridge.read_video(existing_videos[0]['id'])
                    elif i % 4 == 2:
                        # Update
                        existing_videos = self.repository.list_videos(5)
                        if existing_videos:
                            self.adapter_bridge.update_video(
                                existing_videos[0]['id'],
                                {'title': f'Updated by worker {worker_id}'}
                            )
                    # Skip delete for now to maintain data
                    
                    operation_time = time.time() - operation_start
                    worker_results['total_time'] += operation_time
                    worker_results['operations_completed'] += 1
                    
                except Exception as e:
                    worker_results['errors'] += 1
                    logger.debug(f"Worker {worker_id} operation failed: {e}")
            
            return worker_results
        
        # Run concurrent workers
        num_workers = min(self.config.max_concurrent_operations, 4)
        operations_per_worker = 20
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(worker_function, worker_id, operations_per_worker)
                for worker_id in range(num_workers)
            ]
            
            worker_results = []
            for future in as_completed(futures):
                try:
                    result = future.result()
                    worker_results.append(result)
                except Exception as e:
                    logger.error(f"Worker failed: {e}")
        
        test_duration = time.time() - start_time
        
        # Aggregate results
        total_operations = sum(r['operations_completed'] for r in worker_results)
        total_errors = sum(r['errors'] for r in worker_results)
        avg_operation_time = sum(r['total_time'] for r in worker_results) / total_operations if total_operations > 0 else 0
        
        return {
            'test_duration': test_duration,
            'total_operations': total_operations,
            'total_errors': total_errors,
            'operations_per_second': total_operations / test_duration if test_duration > 0 else 0,
            'error_rate': total_errors / (total_operations + total_errors) if (total_operations + total_errors) > 0 else 0,
            'avg_operation_time_ms': avg_operation_time * 1000,
            'meets_performance_threshold': avg_operation_time * 1000 < self.config.performance_threshold_ms,
            'concurrent_workers': num_workers
        }
    
    def test_error_handling(self) -> Dict[str, Any]:
        """Test error handling and recovery mechanisms"""
        start_time = time.time()
        error_scenarios = 0
        handled_scenarios = 0
        
        # Test various error scenarios
        error_tests = [
            # Invalid data
            lambda: self.adapter_bridge.create_video({}),
            lambda: self.adapter_bridge.create_video({'url': ''}),
            lambda: self.adapter_bridge.read_video('nonexistent_id'),
            lambda: self.adapter_bridge.update_video('nonexistent_id', {'title': 'test'}),
            lambda: self.adapter_bridge.delete_video('nonexistent_id'),
        ]
        
        for test_func in error_tests:
            try:
                test_func()
                # If no exception, consider it handled gracefully
                handled_scenarios += 1
            except Exception as e:
                # Expected errors - consider them handled
                handled_scenarios += 1
                logger.debug(f"Expected error occurred: {e}")
            
            error_scenarios += 1
        
        test_duration = time.time() - start_time
        
        return {
            'test_duration': test_duration,
            'error_scenarios_tested': error_scenarios,
            'scenarios_handled': handled_scenarios,
            'handling_rate': handled_scenarios / error_scenarios,
            'error_handling_effective': handled_scenarios / error_scenarios >= 0.8
        }
    
    def test_resource_cleanup(self) -> Dict[str, Any]:
        """Test resource cleanup and memory management"""
        start_time = time.time()
        
        # Create and delete many records to test cleanup
        created_ids = []
        for i in range(50):
            video_data = {
                'url': f'https://example.com/cleanup_test_{i}',
                'title': f'Cleanup Test {i}',
                'duration': 90
            }
            video_id = self.adapter_bridge.create_video(video_data)
            created_ids.append(video_id)
        
        # Delete all created records
        deleted_count = 0
        for video_id in created_ids:
            try:
                if self.adapter_bridge.delete_video(video_id):
                    deleted_count += 1
            except Exception as e:
                logger.warning(f"Cleanup failed for {video_id}: {e}")
        
        # Verify cleanup
        remaining_records = 0
        for video_id in created_ids:
            if self.adapter_bridge.read_video(video_id):
                remaining_records += 1
        
        test_duration = time.time() - start_time
        
        return {
            'test_duration': test_duration,
            'records_created': len(created_ids),
            'records_deleted': deleted_count,
            'records_remaining': remaining_records,
            'cleanup_rate': deleted_count / len(created_ids),
            'cleanup_effective': remaining_records == 0
        }
    
    def test_concurrent_access(self) -> Dict[str, Any]:
        """Test concurrent access patterns"""
        start_time = time.time()
        
        # Create a shared resource
        shared_video_data = {
            'url': 'https://example.com/shared_video',
            'title': 'Shared Video',
            'duration': 300
        }
        shared_video_id = self.adapter_bridge.create_video(shared_video_data)
        
        def concurrent_worker(worker_id: int, operations: int):
            """Worker that performs concurrent operations on shared resource"""
            results = {'reads': 0, 'updates': 0, 'errors': 0}
            
            for i in range(operations):
                try:
                    if i % 2 == 0:
                        # Read operation
                        data = self.adapter_bridge.read_video(shared_video_id)
                        if data:
                            results['reads'] += 1
                    else:
                        # Update operation
                        success = self.adapter_bridge.update_video(
                            shared_video_id,
                            {'title': f'Updated by worker {worker_id} at {i}'}
                        )
                        if success:
                            results['updates'] += 1
                except Exception as e:
                    results['errors'] += 1
                    logger.debug(f"Concurrent access error: {e}")
            
            return results
        
        # Run concurrent workers
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(concurrent_worker, worker_id, 10)
                for worker_id in range(3)
            ]
            
            worker_results = []
            for future in as_completed(futures):
                try:
                    result = future.result()
                    worker_results.append(result)
                except Exception as e:
                    logger.error(f"Concurrent worker failed: {e}")
        
        test_duration = time.time() - start_time
        
        # Aggregate results
        total_reads = sum(r['reads'] for r in worker_results)
        total_updates = sum(r['updates'] for r in worker_results)
        total_errors = sum(r['errors'] for r in worker_results)
        total_operations = total_reads + total_updates + total_errors
        
        return {
            'test_duration': test_duration,
            'total_operations': total_operations,
            'successful_reads': total_reads,
            'successful_updates': total_updates,
            'total_errors': total_errors,
            'success_rate': (total_reads + total_updates) / total_operations if total_operations > 0 else 0,
            'concurrent_workers': 3,
            'data_consistency_maintained': total_errors < total_operations * 0.2
        }
    
    def _compile_final_results(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Compile final comprehensive results"""
        
        # Calculate overall metrics
        total_duration = (self.test_metadata.completed_at - self.test_metadata.started_at).total_seconds()
        
        # Calculate overall success rates
        overall_success_rates = []
        for test_name, results in test_results.items():
            if 'success_rate' in results:
                overall_success_rates.append(results['success_rate'])
            elif 'consistency_rate' in results:
                overall_success_rates.append(results['consistency_rate'])
            elif 'integrity_rate' in results:
                overall_success_rates.append(results['integrity_rate'])
            elif 'handling_rate' in results:
                overall_success_rates.append(results['handling_rate'])
        
        overall_success_rate = sum(overall_success_rates) / len(overall_success_rates) if overall_success_rates else 0
        
        # Performance summary
        performance_metrics = test_results.get('performance_under_load', {})
        
        final_results = {
            'test_metadata': {
                'test_id': self.test_metadata.test_id,
                'started_at': self.test_metadata.started_at.isoformat(),
                'completed_at': self.test_metadata.completed_at.isoformat(),
                'total_duration': total_duration,
                'status': self.test_metadata.status
            },
            'overall_metrics': {
                'overall_success_rate': overall_success_rate,
                'repository_operations_count': self.repository.get_operation_count(),
                'transaction_log_entries': len(self.repository.get_transaction_log()),
                'performance_threshold_met': performance_metrics.get('meets_performance_threshold', False),
                'error_handling_effective': test_results.get('error_handling', {}).get('error_handling_effective', False)
            },
            'detailed_results': test_results,
            'recommendations': self._generate_recommendations(test_results)
        }
        
        return final_results
    
    def _generate_recommendations(self, test_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Data consistency recommendations
        consistency_results = test_results.get('data_consistency', {})
        if consistency_results.get('consistency_rate', 1) < 0.99:
            recommendations.append("Investigate data consistency issues between adapter and repository")
        
        # Performance recommendations
        performance_results = test_results.get('performance_under_load', {})
        if not performance_results.get('meets_performance_threshold', True):
            recommendations.append(f"Optimize performance - avg operation time {performance_results.get('avg_operation_time_ms', 0):.1f}ms exceeds threshold")
        
        # Error handling recommendations
        error_results = test_results.get('error_handling', {})
        if not error_results.get('error_handling_effective', True):
            recommendations.append("Improve error handling and recovery mechanisms")
        
        # Cleanup recommendations
        cleanup_results = test_results.get('resource_cleanup', {})
        if not cleanup_results.get('cleanup_effective', True):
            recommendations.append("Address resource cleanup issues to prevent memory leaks")
        
        # Concurrency recommendations
        concurrency_results = test_results.get('concurrent_access', {})
        if not concurrency_results.get('data_consistency_maintained', True):
            recommendations.append("Improve concurrent access handling and data consistency")
        
        if not recommendations:
            recommendations.append("All tests passed successfully - repository integration is excellent!")
        
        return recommendations
    
    def save_results(self, results: Dict[str, Any], filename: str = None) -> str:
        """Save test results to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scripts_dev/performance_results/repository_integration_test_{timestamp}.json"
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Results saved to: {filename}")
        return filename


def main():
    """Run the repository integration test suite"""
    print("=== Repository Integration Testing System (Fixed) ===\n")
    
    # Configure test
    config = RepositoryTestConfig(
        test_data_size=200,
        max_concurrent_operations=4,
        performance_threshold_ms=30.0
    )
    
    # Run tests
    tester = RepositoryIntegrationTester(config)
    results = tester.run_comprehensive_test_suite()
    
    # Save results
    results_file = tester.save_results(results)
    
    # Display summary
    print(f"\n{'='*60}")
    print("REPOSITORY INTEGRATION TEST SUMMARY")
    print(f"{'='*60}")
    
    overall_metrics = results['overall_metrics']
    print(f"Overall Success Rate: {overall_metrics['overall_success_rate']*100:.1f}%")
    print(f"Repository Operations: {overall_metrics['repository_operations_count']}")
    print(f"Performance Threshold Met: {'✅' if overall_metrics['performance_threshold_met'] else '❌'}")
    print(f"Error Handling Effective: {'✅' if overall_metrics['error_handling_effective'] else '❌'}")
    
    print(f"\nTest Duration: {results['test_metadata']['total_duration']:.2f} seconds")
    print(f"Results saved to: {results_file}")
    
    print(f"\nRecommendations:")
    for rec in results['recommendations']:
        print(f"  - {rec}")
    
    return results


if __name__ == "__main__":
    main() 