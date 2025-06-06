#!/usr/bin/env python3
"""
Interactive Video Info Tab Test
==============================

Manual testing script to verify Video Info tab functionality
with real user interactions and TikTok URL.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel
from PyQt6.QtCore import QTimer, Qt
from ui.components.tabs.video_info_tab import VideoInfoTab


class InteractiveTestWindow(QMainWindow):
    """Main window for interactive testing"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🧪 Video Info Tab - Interactive Test")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Instructions
        instructions = QLabel("""
🧪 INTERACTIVE VIDEO INFO TAB TEST
================================

Test URL: https://www.tiktok.com/@astralfrontiers/video/7480193313744817431?is_from_webapp=1&sender_device=pc

📋 MANUAL TEST STEPS:
1. ✅ The URL has been pre-filled in the "Video URL" field
2. 🔘 Click "Get Info" button to add video to table
3. ✅ Verify video appears in table with dummy data
4. 🔘 Check the checkbox next to the video
5. 🔘 Click "Select All" to select all videos
6. 🔘 Click "Download" (should ask for output folder selection)
7. 🔘 Click "Delete Selected" (should ask for confirmation)
8. 🔘 Add more videos and test "Delete All"
9. 🔘 Test "Choose Folder" button

⚠️  Note: Download functionality is simulated for testing
        """)
        instructions.setWordWrap(True)
        instructions.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                padding: 10px;
                border-radius: 5px;
                font-family: 'Consolas', 'Monaco', monospace;
            }
        """)
        layout.addWidget(instructions)
        
        # Video Info Tab
        self.video_tab = VideoInfoTab()
        layout.addWidget(self.video_tab)
        
        # Pre-fill test URL
        test_url = "https://www.tiktok.com/@astralfrontiers/video/7480193313744817431?is_from_webapp=1&sender_device=pc"
        QTimer.singleShot(100, lambda: self.video_tab.url_input.setText(test_url))
        
        # Set test output folder
        test_folder = os.path.join(os.getcwd(), "test_downloads")
        os.makedirs(test_folder, exist_ok=True)
        QTimer.singleShot(200, lambda: self.video_tab.folder_input.setText(test_folder))
        
        print("🚀 Interactive test window opened!")
        print(f"📁 Test download folder: {test_folder}")
        print("📋 Follow the instructions in the window to test functionality")


def main():
    """Main function"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Video Info Tab Test")
    app.setOrganizationName("Social Download Manager")
    
    # Create and show test window
    window = InteractiveTestWindow()
    window.show()
    
    print("=" * 60)
    print("🧪 INTERACTIVE VIDEO INFO TAB TEST STARTED")
    print("=" * 60)
    print("📌 Manual testing is now active")
    print("📌 Use the UI to test all functionality")
    print("📌 Check console for logs and messages")
    print("📌 Close window when testing is complete")
    print("=" * 60)
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 