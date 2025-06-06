#!/usr/bin/env python3
"""
Test script for download feature and database integration
"""

import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QTextEdit
from PyQt6.QtCore import QThread, pyqtSignal

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.db_manager import DatabaseManager
from utils.downloader import TikTokDownloader

class DownloadTester(QThread):
    log_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.downloader = TikTokDownloader()
        
    def run(self):
        """Run download tests"""
        try:
            self.log_signal.emit("🔍 Testing Database Connection...")
            
            # Test database connection
            videos = self.db_manager.get_all_videos()
            self.log_signal.emit(f"✅ Database connected. Found {len(videos)} existing videos")
            
            # Display existing videos
            if videos:
                self.log_signal.emit("\n📋 Existing videos in database:")
                for i, video in enumerate(videos[:5]):  # Show first 5
                    title = video.get('title', 'Unknown')[:50]
                    date = video.get('download_date', 'Unknown')
                    self.log_signal.emit(f"  {i+1}. {title} - {date}")
                if len(videos) > 5:
                    self.log_signal.emit(f"  ... and {len(videos) - 5} more")
            
            self.log_signal.emit("\n🔧 Testing downloader initialization...")
            
            # Test downloader setup
            if self.downloader:
                self.log_signal.emit("✅ Downloader initialized successfully")
            else:
                self.log_signal.emit("❌ Failed to initialize downloader")
                
            self.log_signal.emit("\n🎯 Download feature test completed!")
            self.log_signal.emit("You can now test downloading by:")
            self.log_signal.emit("1. Paste a TikTok/YouTube URL")
            self.log_signal.emit("2. Click 'Get Info'")
            self.log_signal.emit("3. Select video and click 'Download'")
            self.log_signal.emit("4. Check 'Downloaded Videos' tab for results")
            
        except Exception as e:
            self.log_signal.emit(f"❌ Error during test: {e}")

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Download Feature Test")
        self.setGeometry(100, 100, 600, 400)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create widgets
        self.log_label = QLabel("Download Feature Test Results:")
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        
        self.test_button = QPushButton("Run Download Test")
        self.test_button.clicked.connect(self.run_test)
        
        # Add to layout
        layout.addWidget(self.log_label)
        layout.addWidget(self.log_text)
        layout.addWidget(self.test_button)
        
        # Create tester
        self.tester = DownloadTester()
        self.tester.log_signal.connect(self.add_log)
        
    def add_log(self, message):
        """Add log message to display"""
        self.log_text.append(message)
        
    def run_test(self):
        """Run the download test"""
        self.log_text.clear()
        self.log_text.append("Starting download feature test...\n")
        self.test_button.setEnabled(False)
        
        # Start test thread
        self.tester.finished.connect(lambda: self.test_button.setEnabled(True))
        self.tester.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Check if running in main app
    print("🧪 Download Feature Test")
    print("=" * 50)
    
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec()) 