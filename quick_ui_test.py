#!/usr/bin/env python3
"""
Quick UI Test for Social Download Manager v2.0
Test if the UI works and the get_info button crash is fixed
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_ui_launch():
    """Test if the UI launches successfully"""
    print("🚀 Testing UI launch...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from ui.main_window import MainWindow
        
        # Create QApplication
        app = QApplication(sys.argv)
        
        # Create main window
        main_window = MainWindow()
        main_window.show()
        
        print("✅ UI launched successfully!")
        print("📋 Instructions:")
        print("   1. Try pasting a YouTube URL in the Video Info tab")
        print("   2. Click 'Get Info' button")
        print("   3. Check if the app crashes or if it works")
        print("   4. Close the window when done testing")
        
        # Run app until closed
        return app.exec()
        
    except Exception as e:
        print(f"❌ UI launch failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    print("🧪 Social Download Manager v2.0 - UI Test")
    print("=" * 50)
    
    sys.exit(test_ui_launch()) 