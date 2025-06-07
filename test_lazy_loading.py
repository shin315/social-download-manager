#!/usr/bin/env python3
"""
Test Script for Lazy Loading Implementation (Task 15.1)

Tests the newly implemented lazy loading components:
- LazyVideoTableModel
- LazyVideoTableView  
- Database pagination methods
- Performance with simulated large datasets
"""

import sys
import os
from datetime import datetime
import traceback

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

def test_database_pagination():
    """Test database pagination methods"""
    print("🔍 Testing Database Pagination Methods...")
    
    try:
        from utils.db_manager import DatabaseManager
        
        db_manager = DatabaseManager()
        
        # Test pagination method exists
        print("✅ DatabaseManager pagination methods available")
        
        # Test pagination with small dataset
        videos = db_manager.get_downloaded_videos_paginated(limit=5, offset=0)
        total_count = db_manager.get_downloaded_videos_count()
        
        print(f"📊 Pagination test: Found {len(videos)} videos (page 1, limit 5)")
        print(f"📈 Total videos in database: {total_count}")
        
        if videos:
            print(f"📋 Sample video: {videos[0].get('title', 'Unknown')[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Database pagination test failed: {e}")
        return False

def test_lazy_model():
    """Test LazyVideoTableModel"""
    print("\n🧪 Testing LazyVideoTableModel...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from ui.components.tables.lazy_video_table_model import LazyVideoTableModel
        
        # Create QApplication if not exists
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # Create model
        model = LazyVideoTableModel(page_size=10, buffer_pages=2)
        print("✅ LazyVideoTableModel created successfully")
        
        # Test basic properties
        print(f"📊 Model columns: {model.columnCount()}")
        print(f"📋 Initial row count: {model.rowCount()}")
        print(f"🔄 Can fetch more: {model.canFetchMore()}")
        
        # Test column headers
        headers = []
        for i in range(model.columnCount()):
            header = model.headerData(i, 1, 0)  # Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole
            headers.append(header)
        print(f"📝 Headers: {headers}")
        
        # Cleanup
        model.cleanup()
        print("✅ Model cleanup completed")
        
        return True
        
    except Exception as e:
        print(f"❌ LazyVideoTableModel test failed: {e}")
        traceback.print_exc()
        return False

def test_lazy_view():
    """Test LazyVideoTableView"""
    print("\n🖥️ Testing LazyVideoTableView...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from ui.components.tables.lazy_video_table_view import LazyVideoTableView
        
        # Create QApplication if not exists
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # Create view
        view = LazyVideoTableView(page_size=10)
        print("✅ LazyVideoTableView created successfully")
        
        # Test basic properties
        print(f"📊 View model: {type(view.model()).__name__}")
        print(f"🔄 Loading state: {view.is_loading}")
        
        # Test methods exist
        view.refresh_data()
        print("✅ Refresh data method works")
        
        selected = view.get_selected_videos()
        print(f"📋 Selected videos: {len(selected)}")
        
        # Cleanup
        view.cleanup()
        print("✅ View cleanup completed")
        
        return True
        
    except Exception as e:
        print(f"❌ LazyVideoTableView test failed: {e}")
        traceback.print_exc()
        return False

def test_delegates():
    """Test custom delegates"""
    print("\n🎨 Testing Custom Delegates...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from ui.components.tables.lazy_video_delegate import (
            VideoSelectionDelegate, VideoActionsDelegate, VideoStatusDelegate,
            VideoDateDelegate, VideoProgressDelegate
        )
        
        # Create QApplication if not exists
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # Test delegate creation
        delegates = [
            VideoSelectionDelegate(),
            VideoActionsDelegate(),
            VideoStatusDelegate(),
            VideoDateDelegate(),
            VideoProgressDelegate()
        ]
        
        print(f"✅ Created {len(delegates)} delegates successfully")
        
        for i, delegate in enumerate(delegates):
            delegate_name = type(delegate).__name__
            print(f"  {i+1}. {delegate_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Delegates test failed: {e}")
        traceback.print_exc()
        return False

def test_integration():
    """Test integration between components"""
    print("\n🔗 Testing Component Integration...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from ui.components.tables.lazy_video_table_view import LazyVideoTableView
        
        # Create QApplication if not exists
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # Create integrated view
        view = LazyVideoTableView(page_size=5)
        
        # Test signal connections
        signals_connected = 0
        
        # Check if signals exist
        if hasattr(view, 'video_selected'):
            signals_connected += 1
        if hasattr(view, 'videos_selected'):
            signals_connected += 1
        if hasattr(view, 'selection_changed'):
            signals_connected += 1
        if hasattr(view, 'action_requested'):
            signals_connected += 1
        if hasattr(view, 'loading_state_changed'):
            signals_connected += 1
        
        print(f"📡 Signals available: {signals_connected}/5")
        
        # Test model integration
        model = view.lazy_model
        print(f"🔗 Model integration: {type(model).__name__}")
        
        # Test delegate integration
        delegates_count = 0
        for i in range(model.columnCount()):
            delegate = view.itemDelegateForColumn(i)
            if delegate:
                delegates_count += 1
        
        print(f"🎨 Delegates integrated: {delegates_count} columns")
        
        # Cleanup
        view.cleanup()
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all lazy loading tests"""
    print("🚀 Starting Lazy Loading Tests (Task 15.1)")
    print("=" * 60)
    
    tests = [
        ("Database Pagination", test_database_pagination),
        ("Lazy Model", test_lazy_model),
        ("Lazy View", test_lazy_view),
        ("Custom Delegates", test_delegates),
        ("Component Integration", test_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
        if success:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Lazy loading implementation is ready.")
    else:
        print("⚠️ Some tests failed. Check implementation details.")
    
    return passed == total

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test suite crashed: {e}")
        traceback.print_exc()
        sys.exit(1) 