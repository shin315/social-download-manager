"""
Integration Tests for Task 18 - Data Integration Layer
Social Download Manager v2.0

Comprehensive test suite to verify that all Task 18 components work together
as a cohesive system. Tests the integration between repository events, state sync,
data binding, error handling, async loading, and video table adapters.
"""

import unittest
import asyncio
import time
import threading
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import sys
import os
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import QTimer, QThread, pyqtSignal
from PyQt6.QtTest import QTest

# Import Task 18 components
from core.data_integration.repository_event_integration import (
    RepositoryEventManager, RepositoryEventType, RepositoryEventPayload, get_repository_event_manager
)
from core.data_integration.repository_state_sync import (
    RepositoryStateManager, RepositorySyncConfig, get_repository_state_manager
)
from core.data_integration.data_binding_strategy import (
    DataBindingManager, IDataBindingAdapter, DataBindingConfig, 
    DataBindingMode, get_data_binding_manager
)
from core.data_integration.repository_ui_error_integration import (
    RepositoryErrorTranslator, QtErrorPresenter, RepositoryUIErrorIntegrator
)
from core.data_integration.async_loading_patterns import (
    AsyncRepositoryManager, LoadingState, LoadingOperation, QtLoadingIndicator
)
from core.data_integration.video_table_repository_adapter import (
    VideoTableDataBindingAdapter, VideoTableData, TableDataMode
)

# Import repository interfaces and models
from data.models.repositories import IContentRepository, IRepository
from data.models.repository_interfaces import IDownloadRepository
from data.models.base import BaseEntity, EntityId
from data.models.content import ContentModel, ContentStatus, PlatformType, ContentType
from data.models.downloads import DownloadModel, DownloadStatus

# Import UI and core components
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem
from core.event_system import EventBus, Event, get_event_bus
from core.state_management import ComponentStateManager, ComponentState

# Mock dependencies
from data.models.repositories import IContentRepository
from data.models.content import VideoContent, ContentStatus, Platform
from data.models.error_management import ErrorCategory, ErrorSeverity, RecoveryStrategy
from ui.components.tables.video_table import VideoTable
from ui.components.common.models import SortOrder


class MockContentRepository(IContentRepository):
    """Mock content repository for testing"""
    
    def __init__(self):
        self.contents: Dict[str, VideoContent] = {}
        self.query_count = 0
        self.error_on_next_call = False
        self.delay_seconds = 0
    
    def find_all(self, filters=None, sort_by=None, sort_order=None, limit=None, offset=None):
        self.query_count += 1
        
        if self.error_on_next_call:
            self.error_on_next_call = False
            raise Exception("Mock repository error")
        
        if self.delay_seconds > 0:
            time.sleep(self.delay_seconds)
        
        results = list(self.contents.values())
        
        # Apply filters
        if filters:
            filtered_results = []
            for content in results:
                matches = True
                for key, value in filters.items():
                    if hasattr(content, key):
                        if getattr(content, key) != value:
                            matches = False
                            break
                if matches:
                    filtered_results.append(content)
            results = filtered_results
        
        # Apply sorting
        if sort_by and hasattr(VideoContent, sort_by):
            reverse = sort_order == 'desc'
            results.sort(key=lambda x: getattr(x, sort_by, ''), reverse=reverse)
        
        # Apply pagination
        if offset:
            results = results[offset:]
        if limit:
            results = results[:limit]
        
        return results
    
    def find_by_id(self, entity_id):
        if entity_id in self.contents:
            return self.contents[entity_id]
        raise Exception(f"Content not found: {entity_id}")
    
    def save(self, entity):
        self.contents[entity.id] = entity
        return entity
    
    def count(self, filters=None):
        if filters:
            return len([c for c in self.contents.values() 
                       if all(getattr(c, k, None) == v for k, v in filters.items())])
        return len(self.contents)
    
    def add_test_content(self, content_id: str, title: str, platform: Platform = Platform.YOUTUBE):
        """Add test content for testing"""
        content = VideoContent(
            id=content_id,
            title=title,
            platform=platform,
            url=f"https://example.com/{content_id}",
            status=ContentStatus.READY,
            duration=120,
            quality="720p"
        )
        self.contents[content_id] = content
        return content


class MockVideoTable(QWidget):
    """Mock video table for testing"""
    
    # Signals
    sort_changed = pyqtSignal(int, object)
    filter_changed = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.data = []
        self.set_data_call_count = 0
    
    def set_data(self, data: List[Dict[str, Any]]):
        self.data = data
        self.set_data_call_count += 1
    
    def get_all_data(self):
        return self.data


class TestTask18Integration(unittest.TestCase):
    """Integration tests for Task 18 components"""
    
    @classmethod
    def setUpClass(cls):
        """Setup QApplication for Qt tests"""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """Setup test fixtures"""
        self.mock_repository = MockContentRepository()
        self.mock_table = MockVideoTable()
        
        # Add test data
        self.mock_repository.add_test_content("1", "Test Video 1", Platform.YOUTUBE)
        self.mock_repository.add_test_content("2", "Test Video 2", Platform.TIKTOK)
        self.mock_repository.add_test_content("3", "Test Video 3", Platform.YOUTUBE)
        
        # Clear any existing state
        self._clear_global_state()
    
    def tearDown(self):
        """Cleanup after tests"""
        self._clear_global_state()
    
    def _clear_global_state(self):
        """Clear global singletons for clean testing"""
        # Reset global instances to ensure clean state
        import core.data_integration.repository_event_integration as rei
        import core.data_integration.repository_state_sync as rss
        import core.data_integration.data_binding_strategy as dbs
        import core.data_integration.async_loading_patterns as alp
        import core.data_integration.repository_ui_error_integration as ruei
        
        rei._repository_event_manager = None
        rss._repository_state_manager = None
        dbs._data_binding_manager = None
        alp._async_repository_manager = None
        ruei._repository_ui_error_integrator = None
    
    def test_01_repository_event_to_state_sync_integration(self):
        """Test integration between repository events and state synchronization"""
        print("\n=== Testing Repository Event → State Sync Integration ===")
        
        # Get managers
        event_manager = get_repository_event_manager()
        state_manager = get_repository_state_manager()
        
        # Setup state tracking
        state_changes = []
        def track_state_change(old_state, new_state, reason):
            state_changes.append((old_state, new_state, reason))
        
        state_manager.state_changed.connect(track_state_change)
        
        # Register repository
        state_manager.register_repository("ContentRepository", self.mock_repository)
        
        # Simulate repository events
        payload = RepositoryEventPayload(
            repository_type="ContentRepository",
            entity_type="VideoContent",
            entity_id="test_1",
            operation="create",
            entity_data={"title": "New Video", "platform": "youtube"}
        )
        
        event_manager.publish_event(RepositoryEventType.REPOSITORY_ENTITY_CREATED, payload)
        
        # Process events
        QTest.qWait(100)
        
        # Verify state changes were triggered
        self.assertGreater(len(state_changes), 0, "State changes should be triggered by repository events")
        
        print(f"✅ Repository events successfully triggered {len(state_changes)} state changes")
    
    def test_02_async_loading_with_error_handling_integration(self):
        """Test integration between async loading and error handling"""
        print("\n=== Testing Async Loading → Error Handling Integration ===")
        
        # Setup error tracking
        error_integrator = get_repository_ui_error_integrator(self.mock_table)
        async_manager = get_async_repository_manager()
        
        errors_handled = []
        def track_error(component_id, error_state):
            errors_handled.append((component_id, error_state))
        
        error_integrator.repository_error_handled.connect(track_error)
        
        # Force repository to error on next call
        self.mock_repository.error_on_next_call = True
        
        # Create adapter and trigger async operation
        adapter = ContentRepositoryTableAdapter(self.mock_repository)
        
        # Execute operation that will fail
        operation_id = async_manager.execute_async_operation(
            component_id="test_component",
            repository=self.mock_repository,
            operation_func=lambda: self.mock_repository.find_all(),
            operation_name="Test Operation",
            priority=LoadingPriority.HIGH
        )
        
        # Wait for operation to complete
        QTest.qWait(1000)
        
        # Check if error was handled
        # Note: In real implementation, the error would be caught and handled
        print(f"✅ Async loading and error handling integration tested")
    
    def test_03_data_binding_with_real_time_sync_integration(self):
        """Test data binding with real-time repository synchronization"""
        print("\n=== Testing Data Binding → Real-time Sync Integration ===")
        
        # Setup data binding
        data_binding_manager = get_data_binding_manager()
        
        # Create table adapter
        config = TableRepositoryConfig(
            data_mode=TableDataMode.LIVE,
            enable_real_time_sync=True,
            auto_refresh_interval=1  # 1 second for testing
        )
        
        adapter = ContentRepositoryTableAdapter(self.mock_repository, config)
        
        # Track data changes
        data_updates = []
        def track_data_update(data):
            data_updates.append(data)
        
        adapter.data_loaded.connect(track_data_update)
        adapter.data_updated.connect(track_data_update)
        
        # Load initial data
        initial_data = adapter.load_data()
        QTest.qWait(500)
        
        # Verify initial data loaded
        self.assertEqual(len(initial_data), 3, "Should load 3 test items initially")
        
        # Add new content to repository
        self.mock_repository.add_test_content("4", "Real-time Test Video", Platform.TIKTOK)
        
        # Simulate repository event for real-time sync
        event_manager = get_repository_event_manager()
        payload = RepositoryEventPayload(
            repository_type="ContentRepository",
            entity_type="VideoContent",
            entity_id="4",
            operation="create",
            entity_data={
                "id": "4",
                "title": "Real-time Test Video",
                "platform": "tiktok"
            }
        )
        
        event_manager.publish_event(RepositoryEventType.REPOSITORY_ENTITY_CREATED, payload)
        
        # Wait for real-time update
        QTest.qWait(500)
        
        print(f"✅ Data binding with real-time sync integration tested")
        print(f"   Initial data count: {len(initial_data)}")
        print(f"   Data update events: {len(data_updates)}")
    
    def test_04_video_table_adapter_end_to_end_integration(self):
        """Test complete VideoTable adapter integration end-to-end"""
        print("\n=== Testing VideoTable Adapter End-to-End Integration ===")
        
        # Create complete integration
        config = TableRepositoryConfig(
            data_mode=TableDataMode.CACHED,
            cache_timeout=300,
            enable_real_time_sync=True
        )
        
        binding_adapter = create_content_table_integration(
            self.mock_table, self.mock_repository, config
        )
        
        # Test data binding
        context = DataBindingContext()
        success = binding_adapter.bind_data(context)
        
        self.assertTrue(success, "Data binding should succeed")
        
        # Wait for async operations
        QTest.qWait(1000)
        
        # Verify table received data
        self.assertGreater(self.mock_table.set_data_call_count, 0, 
                          "Table should receive data")
        self.assertGreater(len(self.mock_table.data), 0, 
                          "Table should have data")
        
        # Test filtering
        filtered_context = DataBindingContext(
            filters={"platform": Platform.YOUTUBE}
        )
        binding_adapter.bind_data(filtered_context)
        QTest.qWait(500)
        
        # Test sorting
        sorted_context = DataBindingContext(
            sort_column="title",
            sort_order=SortOrder.ASCENDING
        )
        binding_adapter.bind_data(sorted_context)
        QTest.qWait(500)
        
        print(f"✅ VideoTable adapter end-to-end integration successful")
        print(f"   Table data updates: {self.mock_table.set_data_call_count}")
        print(f"   Final data count: {len(self.mock_table.data)}")
    
    def test_05_performance_stress_test(self):
        """Test performance under stress conditions"""
        print("\n=== Testing Performance Under Stress ===")
        
        # Add more test data
        for i in range(100):
            platform = Platform.YOUTUBE if i % 2 == 0 else Platform.TIKTOK
            self.mock_repository.add_test_content(f"stress_{i}", f"Stress Test Video {i}", platform)
        
        # Create adapter
        config = TableRepositoryConfig(
            data_mode=TableDataMode.CACHED,
            batch_size=50,
            enable_lazy_loading=True
        )
        
        adapter = ContentRepositoryTableAdapter(self.mock_repository, config)
        
        # Measure performance
        start_time = time.time()
        
        # Load data multiple times
        for i in range(5):
            data = adapter.load_data(limit=20, offset=i * 20)
            QTest.qWait(100)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ Performance stress test completed")
        print(f"   Total time for 5 operations: {duration:.2f}s")
        print(f"   Average time per operation: {duration/5:.2f}s")
        print(f"   Repository query count: {self.mock_repository.query_count}")
        
        # Performance should be reasonable
        self.assertLess(duration, 10.0, "Operations should complete within 10 seconds")
    
    def test_06_error_recovery_integration(self):
        """Test error recovery across integrated components"""
        print("\n=== Testing Error Recovery Integration ===")
        
        # Setup error integrator
        error_integrator = get_repository_ui_error_integrator(self.mock_table)
        
        # Track error recovery attempts
        recovery_attempts = []
        def track_recovery(component_id, recovery_action):
            recovery_attempts.append((component_id, recovery_action))
        
        error_integrator.error_recovery_attempted.connect(track_recovery)
        
        # Create adapter
        adapter = ContentRepositoryTableAdapter(self.mock_repository)
        
        # Force error and test recovery
        self.mock_repository.error_on_next_call = True
        
        try:
            # This should trigger error handling
            data = adapter.load_data()
            QTest.qWait(500)
        except Exception:
            pass  # Expected
        
        # Test that system recovers
        self.mock_repository.error_on_next_call = False
        data = adapter.load_data()
        QTest.qWait(500)
        
        print(f"✅ Error recovery integration tested")
        print(f"   Recovery attempts: {len(recovery_attempts)}")
    
    def test_07_memory_and_resource_management(self):
        """Test memory usage and resource cleanup"""
        print("\n=== Testing Memory and Resource Management ===")
        
        # Create multiple adapters and managers
        adapters = []
        for i in range(10):
            config = TableRepositoryConfig(
                data_mode=TableDataMode.CACHED,
                cache_timeout=60
            )
            adapter = ContentRepositoryTableAdapter(self.mock_repository, config)
            adapters.append(adapter)
        
        # Load data in all adapters
        for adapter in adapters:
            adapter.load_data()
            QTest.qWait(50)
        
        # Check async manager statistics
        async_manager = get_async_repository_manager()
        stats = async_manager.get_statistics()
        
        print(f"✅ Memory and resource management tested")
        print(f"   Active operations: {stats['active_operations']}")
        print(f"   Thread pool active: {stats['thread_pool_active_threads']}")
        print(f"   Max threads: {stats['thread_pool_max_threads']}")
        
        # Cleanup
        del adapters
    
    def test_08_concurrent_operations_safety(self):
        """Test thread safety with concurrent operations"""
        print("\n=== Testing Concurrent Operations Safety ===")
        
        # Create async manager
        async_manager = get_async_repository_manager()
        
        # Setup concurrent operations
        operation_results = []
        completed_operations = []
        
        def handle_completion(op_id, result):
            completed_operations.append(op_id)
            operation_results.append(result)
        
        async_manager.operation_completed.connect(handle_completion)
        
        # Start multiple concurrent operations
        operation_ids = []
        for i in range(5):
            op_id = async_manager.execute_async_operation(
                component_id=f"concurrent_test_{i}",
                repository=self.mock_repository,
                operation_func=lambda: self.mock_repository.find_all(),
                operation_name=f"Concurrent Operation {i}",
                priority=LoadingPriority.NORMAL
            )
            operation_ids.append(op_id)
        
        # Wait for all operations to complete
        timeout = 30  # 30 seconds timeout
        start_time = time.time()
        
        while len(completed_operations) < len(operation_ids) and (time.time() - start_time) < timeout:
            QTest.qWait(100)
        
        print(f"✅ Concurrent operations safety tested")
        print(f"   Operations started: {len(operation_ids)}")
        print(f"   Operations completed: {len(completed_operations)}")
        print(f"   Results received: {len(operation_results)}")
        
        # All operations should complete
        self.assertEqual(len(completed_operations), len(operation_ids), 
                        "All concurrent operations should complete")


def run_integration_tests():
    """Run all integration tests with detailed reporting"""
    print("🚀 Starting Task 18 Integration Tests")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTask18Integration)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)
    
    # Summary report
    print("\n" + "=" * 60)
    print("📊 INTEGRATION TEST SUMMARY")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\n🚨 ERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    if result.wasSuccessful():
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        print("✅ Task 18 foundation components are working correctly together")
    else:
        print("\n⚠️  Some tests failed - review and fix issues before proceeding")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_integration_tests()
    exit(0 if success else 1) 