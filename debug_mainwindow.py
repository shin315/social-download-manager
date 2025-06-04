#!/usr/bin/env python3
"""
Debug script to test MainWindow creation step by step
"""

import sys
import traceback
from PyQt6.QtWidgets import QApplication

def test_imports():
    """Test importing modules step by step"""
    try:
        print("✅ Testing imports...")
        
        # Test core imports
        print("  ➜ Importing PyQt6...")
        from PyQt6.QtWidgets import QMainWindow
        print("  ✅ PyQt6 imported successfully")
        
        # Test component imports
        print("  ➜ Importing UI components...")
        from ui.components.common import TabConfig
        print("  ✅ TabConfig imported successfully")
        
        from ui.components.tabs.video_info_tab import VideoInfoTab
        print("  ✅ VideoInfoTab imported successfully")
        
        from ui.components.tabs.downloaded_videos_tab import DownloadedVideosTab
        print("  ✅ DownloadedVideosTab imported successfully")
        
        # Test main window import
        print("  ➜ Importing MainWindow...")
        from ui.main_window import MainWindow
        print("  ✅ MainWindow imported successfully")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Import error: {e}")
        traceback.print_exc()
        return False

def test_qapplication():
    """Test QApplication creation"""
    try:
        print("\n✅ Testing QApplication creation...")
        
        app = QApplication(sys.argv)
        print("  ✅ QApplication created successfully")
        return app
        
    except Exception as e:
        print(f"  ❌ QApplication error: {e}")
        traceback.print_exc()
        return None

def test_mainwindow_creation(app):
    """Test MainWindow creation step by step"""
    try:
        print("\n✅ Testing MainWindow creation...")
        
        # Import MainWindow
        from ui.main_window import MainWindow
        
        # Create MainWindow
        print("  ➜ Creating MainWindow instance...")
        main_window = MainWindow()
        print("  ✅ MainWindow created successfully")
        
        return main_window
        
    except Exception as e:
        print(f"  ❌ MainWindow creation error: {e}")
        print(f"  ❌ Error type: {type(e)}")
        traceback.print_exc()
        return None

def main():
    """Main debug function"""
    print("🔍 Starting MainWindow Debug Session...")
    print("=" * 60)
    
    # Test imports
    if not test_imports():
        print("\n❌ Import test failed - exiting")
        return
    
    # Test QApplication
    app = test_qapplication()
    if not app:
        print("\n❌ QApplication test failed - exiting")
        return
    
    # Test MainWindow creation
    main_window = test_mainwindow_creation(app)
    if not main_window:
        print("\n❌ MainWindow creation failed - exiting")
        return
    
    print("\n🎉 All tests passed! MainWindow created successfully")
    print("=" * 60)
    
    # Show window briefly
    main_window.show()
    app.processEvents()  # Process events once
    
    print("\n🏁 Debug session completed")

if __name__ == "__main__":
    main() 