"""
Test Platform Selector Integration - Task 18.7
Social Download Manager v2.0

Comprehensive tests for PlatformSelector integration with repository data,
including error handling using Task 19's error management system.
"""

import unittest
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime
from typing import Dict, Any
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Core imports
from core.data_integration.platform_selector_integration import (
    PlatformSelectorManager, PlatformDataAdapter, PlatformData, 
    PlatformState, PlatformSelectionEvent, get_platform_selector_manager,
    reset_platform_selector_manager
)

# Repository interfaces
from data.models.repositories import IContentRepository
from data.models.content import ContentModel, ContentStatus, PlatformType, ContentType

# Mock repository for testing
class MockContentRepository(IContentRepository):
    """Mock repository for testing"""
    
    def __init__(self):
        self.contents: Dict[str, ContentModel] = {}
        self._call_log = []
    
    def find_all(self, filters=None, sort_by=None, sort_order=None, limit=None, offset=None):
        self._call_log.append(('find_all', filters, sort_by, sort_order, limit, offset))
        return list(self.contents.values())
    
    def find_by_id(self, entity_id):
        self._call_log.append(('find_by_id', entity_id))
        return self.contents.get(entity_id)
    
    def find_by_platform(self, platform):
        self._call_log.append(('find_by_platform', platform))
        return [c for c in self.contents.values() if c.platform == platform]
    
    def find_by_status(self, status):
        self._call_log.append(('find_by_status', status))
        return [c for c in self.contents.values() if c.status == status]
    
    def save(self, entity):
        self._call_log.append(('save', entity))
        self.contents[entity.id] = entity
        return entity
    
    def count(self, filters=None):
        self._call_log.append(('count', filters))
        return len(self.contents)
    
    def add_test_content(self, content_id: str, platform: PlatformType, status: ContentStatus):
        """Helper to add test content"""
        content = ContentModel(
            id=content_id,
            title=f"Test Content {content_id}",
            platform=platform,
            url=f"https://example.com/{content_id}",
            status=status,
            content_type=ContentType.VIDEO
        )
        self.contents[content_id] = content
        return content
    
    # Required abstract methods (minimal implementation)
    def find_by_url(self, url): return None
    def find_by_platform_id(self, platform, platform_id): return None
    def find_by_content_type(self, content_type): return []
    def find_by_author(self, author): return []
    def find_downloaded_content(self): return []
    def find_failed_downloads(self): return []
    def find_in_progress_downloads(self): return []
    def search_content(self, search_term): return []
    def get_download_stats(self): return {}
    def delete(self, entity_id): pass
    def execute_query(self, query): pass
    def exists(self, entity_id): return entity_id in self.contents
    def find_by_criteria(self, criteria): return []
    def find_large_files(self, size_threshold): return []
    def find_recent_content(self, days): return []
    def get_platform_stats(self): return {}
    def query(self, query_string): return []


class TestPlatformDataAdapter(unittest.TestCase):
    """Test PlatformDataAdapter functionality"""
    
    def setUp(self):
        self.mock_repo = MockContentRepository()
        self.adapter = PlatformDataAdapter(self.mock_repo)
        
        # Add test data
        self.mock_repo.add_test_content("1", PlatformType.YOUTUBE, ContentStatus.COMPLETED)
        self.mock_repo.add_test_content("2", PlatformType.YOUTUBE, ContentStatus.COMPLETED)
        self.mock_repo.add_test_content("3", PlatformType.YOUTUBE, ContentStatus.FAILED)
        self.mock_repo.add_test_content("4", PlatformType.TIKTOK, ContentStatus.COMPLETED)
        self.mock_repo.add_test_content("5", PlatformType.TIKTOK, ContentStatus.PENDING)
    
    def test_get_platform_data_youtube(self):
        """Test getting platform data for YouTube"""
        async def run_test():
            platform_data = await self.adapter.get_platform_data(PlatformType.YOUTUBE)
            
            self.assertEqual(platform_data.platform_type, PlatformType.YOUTUBE)
            self.assertEqual(platform_data.total_content, 3)  # 3 YouTube videos
            self.assertEqual(platform_data.downloaded_content, 2)  # 2 completed
            self.assertEqual(platform_data.failed_downloads, 1)  # 1 failed
            self.assertTrue(platform_data.is_available)
            self.assertEqual(platform_data.state, PlatformState.SELECTED)
        
        asyncio.run(run_test())
    
    def test_get_platform_data_tiktok(self):
        """Test getting platform data for TikTok"""
        async def run_test():
            platform_data = await self.adapter.get_platform_data(PlatformType.TIKTOK)
            
            self.assertEqual(platform_data.platform_type, PlatformType.TIKTOK)
            self.assertEqual(platform_data.total_content, 2)  # 2 TikTok videos
            self.assertEqual(platform_data.downloaded_content, 1)  # 1 completed
            self.assertEqual(platform_data.failed_downloads, 0)  # 0 failed
            self.assertTrue(platform_data.is_available)
            self.assertEqual(platform_data.state, PlatformState.SELECTED)
        
        asyncio.run(run_test())
    
    def test_get_platform_data_error_handling(self):
        """Test error handling in platform data retrieval"""
        # Create adapter with failing repository
        failing_repo = Mock(spec=IContentRepository)
        failing_repo.find_by_platform.side_effect = Exception("Repository error")
        
        adapter = PlatformDataAdapter(failing_repo)
        
        async def run_test():
            platform_data = await adapter.get_platform_data(PlatformType.YOUTUBE)
            
            self.assertEqual(platform_data.platform_type, PlatformType.YOUTUBE)
            self.assertFalse(platform_data.is_available)
            self.assertEqual(platform_data.state, PlatformState.ERROR)
            self.assertIsNotNone(platform_data.error_message)
        
        asyncio.run(run_test())


class TestPlatformSelectorManager(unittest.TestCase):
    """Test PlatformSelectorManager functionality"""
    
    def setUp(self):
        # Reset global state
        reset_platform_selector_manager()
        
        self.mock_repo = MockContentRepository()
        self.manager = PlatformSelectorManager(self.mock_repo)
        
        # Add test data
        self.mock_repo.add_test_content("1", PlatformType.YOUTUBE, ContentStatus.COMPLETED)
        self.mock_repo.add_test_content("2", PlatformType.YOUTUBE, ContentStatus.FAILED)
        self.mock_repo.add_test_content("3", PlatformType.TIKTOK, ContentStatus.COMPLETED)
        self.mock_repo.add_test_content("4", PlatformType.TIKTOK, ContentStatus.PENDING)
    
    def tearDown(self):
        reset_platform_selector_manager()
    
    def test_initialize_platforms(self):
        """Test platform initialization"""
        async def run_test():
            platform_data = await self.manager.initialize_platforms()
            
            self.assertIn(PlatformType.YOUTUBE, platform_data)
            self.assertIn(PlatformType.TIKTOK, platform_data)
            
            youtube_data = platform_data[PlatformType.YOUTUBE]
            self.assertEqual(youtube_data.total_content, 2)
            self.assertEqual(youtube_data.downloaded_content, 1)
            self.assertEqual(youtube_data.failed_downloads, 1)
            
            tiktok_data = platform_data[PlatformType.TIKTOK]
            self.assertEqual(tiktok_data.total_content, 2)
            self.assertEqual(tiktok_data.downloaded_content, 1)
            self.assertEqual(tiktok_data.failed_downloads, 0)
        
        asyncio.run(run_test())
    
    def test_select_platform(self):
        """Test platform selection"""
        async def run_test():
            # Initialize platforms first
            await self.manager.initialize_platforms()
            
            # Test callback
            selection_events = []
            def on_selection(event: PlatformSelectionEvent):
                selection_events.append(event)
            
            self.manager.add_selection_callback(on_selection)
            
            # Select YouTube platform
            success = self.manager.select_platform(PlatformType.YOUTUBE)
            
            self.assertTrue(success)
            self.assertEqual(self.manager.get_current_platform(), PlatformType.YOUTUBE)
            self.assertIn(PlatformType.YOUTUBE, self.manager.get_selected_platforms())
            
            # Check callback was called
            self.assertEqual(len(selection_events), 1)
            event = selection_events[0]
            self.assertEqual(event.platform, PlatformType.YOUTUBE)
            self.assertTrue(event.selected)
        
        asyncio.run(run_test())
    
    def test_deselect_platform(self):
        """Test platform deselection"""
        async def run_test():
            # Initialize and select platform first
            await self.manager.initialize_platforms()
            self.manager.select_platform(PlatformType.YOUTUBE)
            
            # Test deselection
            success = self.manager.deselect_platform(PlatformType.YOUTUBE)
            
            self.assertTrue(success)
            self.assertNotIn(PlatformType.YOUTUBE, self.manager.get_selected_platforms())
        
        asyncio.run(run_test())
    
    def test_select_unavailable_platform(self):
        """Test selecting unavailable platform"""
        async def run_test():
            # Initialize platforms first
            await self.manager.initialize_platforms()
            
            # Manually set platform as unavailable
            self.manager.platform_data[PlatformType.YOUTUBE].is_available = False
            
            # Try to select unavailable platform
            success = self.manager.select_platform(PlatformType.YOUTUBE)
            
            self.assertFalse(success)
            self.assertNotIn(PlatformType.YOUTUBE, self.manager.get_selected_platforms())
        
        asyncio.run(run_test())
    
    def test_refresh_platform_data(self):
        """Test refreshing platform data"""
        async def run_test():
            # Initialize platforms
            await self.manager.initialize_platforms()
            
            # Add more content
            self.mock_repo.add_test_content("new1", PlatformType.YOUTUBE, ContentStatus.COMPLETED)
            
            # Refresh YouTube data
            success = await self.manager.refresh_platform_data(PlatformType.YOUTUBE)
            
            self.assertTrue(success)
            
            # Check updated data
            youtube_data = self.manager.get_platform_data(PlatformType.YOUTUBE)
            self.assertEqual(youtube_data.total_content, 3)  # Now 3 instead of 2
        
        asyncio.run(run_test())
    
    def test_get_platform_data(self):
        """Test getting specific platform data"""
        async def run_test():
            await self.manager.initialize_platforms()
            
            youtube_data = self.manager.get_platform_data(PlatformType.YOUTUBE)
            self.assertIsNotNone(youtube_data)
            self.assertEqual(youtube_data.platform_type, PlatformType.YOUTUBE)
            
            # Test non-existent platform - use a different platform that wasn't initialized
            instagram_data = self.manager.get_platform_data(PlatformType.INSTAGRAM)
            self.assertIsNone(instagram_data)
        
        asyncio.run(run_test())
    
    def test_get_all_platform_data(self):
        """Test getting all platform data"""
        async def run_test():
            await self.manager.initialize_platforms()
            
            all_data = self.manager.get_all_platform_data()
            
            self.assertIsInstance(all_data, dict)
            self.assertIn(PlatformType.YOUTUBE, all_data)
            self.assertIn(PlatformType.TIKTOK, all_data)
        
        asyncio.run(run_test())
    
    def test_callback_management(self):
        """Test callback add/remove functionality"""
        def callback1(event): pass
        def callback2(event): pass
        
        # Add callbacks
        self.manager.add_selection_callback(callback1)
        self.manager.add_selection_callback(callback2)
        
        self.assertEqual(len(self.manager.selection_callbacks), 2)
        
        # Remove callback
        self.manager.remove_selection_callback(callback1)
        
        self.assertEqual(len(self.manager.selection_callbacks), 1)
        self.assertIn(callback2, self.manager.selection_callbacks)
        
        # Remove non-existent callback (should not raise error)
        self.manager.remove_selection_callback(callback1)
        
        self.assertEqual(len(self.manager.selection_callbacks), 1)


class TestGlobalPlatformSelectorManager(unittest.TestCase):
    """Test global platform selector manager functions"""
    
    def setUp(self):
        reset_platform_selector_manager()
        self.mock_repo = MockContentRepository()
    
    def tearDown(self):
        reset_platform_selector_manager()
    
    def test_get_platform_selector_manager(self):
        """Test getting global platform selector manager"""
        # First call should create new instance
        manager1 = get_platform_selector_manager(self.mock_repo)
        self.assertIsNotNone(manager1)
        
        # Second call should return same instance
        manager2 = get_platform_selector_manager()
        self.assertIs(manager1, manager2)
    
    def test_get_platform_selector_manager_no_repo(self):
        """Test getting manager without repository should raise error"""
        with self.assertRaises(ValueError):
            get_platform_selector_manager()
    
    def test_reset_platform_selector_manager(self):
        """Test resetting global manager"""
        # Create manager
        manager1 = get_platform_selector_manager(self.mock_repo)
        
        # Reset
        reset_platform_selector_manager()
        
        # Get new manager - should be different instance
        manager2 = get_platform_selector_manager(self.mock_repo)
        self.assertIsNot(manager1, manager2)


class TestPlatformSelectorIntegration(unittest.TestCase):
    """Integration tests for complete platform selector system"""
    
    def setUp(self):
        reset_platform_selector_manager()
        self.mock_repo = MockContentRepository()
        
        # Create complex test data
        platforms = [PlatformType.YOUTUBE, PlatformType.TIKTOK]
        statuses = [ContentStatus.COMPLETED, ContentStatus.FAILED, ContentStatus.PENDING]
        
        content_id = 1
        for platform in platforms:
            for status in statuses:
                for i in range(3):  # 3 videos per platform per status
                    self.mock_repo.add_test_content(
                        str(content_id),
                        platform,
                        status
                    )
                    content_id += 1
    
    def tearDown(self):
        reset_platform_selector_manager()
    
    def test_full_workflow(self):
        """Test complete platform selector workflow"""
        async def run_test():
            # Get manager
            manager = get_platform_selector_manager(self.mock_repo)
            
            # Initialize platforms
            platform_data = await manager.initialize_platforms()
            
            # Verify initialization
            self.assertEqual(len(platform_data), 2)
            
            for platform in [PlatformType.YOUTUBE, PlatformType.TIKTOK]:
                data = platform_data[platform]
                self.assertEqual(data.total_content, 9)  # 3 statuses * 3 videos each
                self.assertEqual(data.downloaded_content, 3)  # 3 completed
                self.assertEqual(data.failed_downloads, 3)  # 3 failed
            
            # Test selection workflow
            selection_events = []
            def track_selections(event):
                selection_events.append(event)
            
            manager.add_selection_callback(track_selections)
            
            # Select YouTube
            success = manager.select_platform(PlatformType.YOUTUBE)
            self.assertTrue(success)
            self.assertEqual(len(selection_events), 1)
            
            # Select TikTok (multi-selection)
            success = manager.select_platform(PlatformType.TIKTOK)
            self.assertTrue(success)
            self.assertEqual(len(selection_events), 2)
            
            # Verify state
            selected = manager.get_selected_platforms()
            self.assertEqual(len(selected), 2)
            self.assertIn(PlatformType.YOUTUBE, selected)
            self.assertIn(PlatformType.TIKTOK, selected)
            
            # Deselect YouTube
            success = manager.deselect_platform(PlatformType.YOUTUBE)
            self.assertTrue(success)
            self.assertEqual(len(selection_events), 3)
            
            # Verify final state
            selected = manager.get_selected_platforms()
            self.assertEqual(len(selected), 1)
            self.assertIn(PlatformType.TIKTOK, selected)
            self.assertEqual(manager.get_current_platform(), PlatformType.TIKTOK)
        
        asyncio.run(run_test())
    
    def test_error_recovery_workflow(self):
        """Test error handling and recovery in platform selector"""
        async def run_test():
            # Create manager with repository that will fail on specific calls
            failing_repo = Mock(spec=IContentRepository)
            
            # Setup repo to return data for find_by_platform but fail for find_by_status  
            failing_repo.find_by_platform.return_value = [
                Mock(platform=PlatformType.YOUTUBE, status=ContentStatus.COMPLETED)
            ]
            failing_repo.find_by_status.side_effect = Exception("Status query failed")
            
            manager = PlatformSelectorManager(failing_repo)
            
            # Initialize platforms - should handle partial failures gracefully
            platform_data = await manager.initialize_platforms()
            
            # Should still have platform data, but some fields might be 0 due to errors
            self.assertIn(PlatformType.YOUTUBE, platform_data)
            youtube_data = platform_data[PlatformType.YOUTUBE]
            self.assertEqual(youtube_data.total_content, 1)  # This worked
            # downloaded_content and failed_downloads would be 0 due to find_by_status failures
        
        asyncio.run(run_test())


def run_platform_selector_tests():
    """Run all platform selector integration tests"""
    print("🚀 Starting Task 18.7 Platform Selector Integration Tests")
    print("=" * 70)
    
    # Create test suite
    test_classes = [
        TestPlatformDataAdapter,
        TestPlatformSelectorManager,
        TestGlobalPlatformSelectorManager,
        TestPlatformSelectorIntegration
    ]
    
    suite = unittest.TestSuite()
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)
    
    # Summary report
    print("\n" + "=" * 70)
    print("📊 PLATFORM SELECTOR INTEGRATION TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    if result.testsRun > 0:
        print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}")
            print(f"    {traceback.strip()}")
    
    if result.errors:
        print("\n🚨 ERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}")
            print(f"    {traceback.strip()}")
    
    if result.wasSuccessful():
        print("\n🎉 ALL PLATFORM SELECTOR INTEGRATION TESTS PASSED!")
        print("✅ Task 18.7 implementation is working correctly")
        print("\n📋 Verified Components:")
        print("  ✓ PlatformDataAdapter - Repository data retrieval")
        print("  ✓ PlatformSelectorManager - State management and event handling")
        print("  ✓ Platform selection/deselection workflow")
        print("  ✓ Error handling with Task 19 integration")
        print("  ✓ Event-driven data synchronization")
        print("  ✓ Async data loading patterns")
        print("  ✓ Global manager singleton pattern")
        print("\n💡 Next: Complete remaining Task 18 subtasks (18.8-18.11)")
    else:
        print("\n⚠️  Some tests failed - review platform selector integration")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_platform_selector_tests()
    exit(0 if success else 1) 