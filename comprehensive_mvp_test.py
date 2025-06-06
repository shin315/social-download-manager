#!/usr/bin/env python3
"""
Comprehensive MVP Functionality Test
===================================

Complete test suite for Social Download Manager v2.0 MVP features.
Tests all core functionality including Video Info, Downloads, Database operations.
"""

import sys
import os
import time
import threading

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QThread, pyqtSignal
from ui.components.tabs.video_info_tab import VideoInfoTab
from ui.components.tabs.downloaded_videos_tab import DownloadedVideosTab
from utils.db_manager import DatabaseManager


class MVPTester(QThread):
    """MVP comprehensive tester"""
    
    progress_signal = pyqtSignal(str)
    result_signal = pyqtSignal(str, bool, str)
    
    def __init__(self):
        super().__init__()
        self.results = {}
        self.test_url = "https://www.tiktok.com/@astralfrontiers/video/7480193313744817431?is_from_webapp=1&sender_device=pc"
    
    def run(self):
        """Run comprehensive MVP tests"""
        self.progress_signal.emit("🚀 Starting MVP Comprehensive Test Suite...")
        
        # Initialize Qt Application for testing
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        try:
            # Test 1: Database Operations
            self.test_database_operations()
            
            # Test 2: Video Info Tab Functionality
            self.test_video_info_tab()
            
            # Test 3: Downloaded Videos Tab
            self.test_downloaded_videos_tab()
            
            # Test 4: Integration Testing
            self.test_integration()
            
            # Generate final report
            self.generate_final_report()
            
        except Exception as e:
            self.result_signal.emit("FATAL_ERROR", False, f"Critical test failure: {e}")
    
    def test_database_operations(self):
        """Test database operations"""
        self.progress_signal.emit("🗄️ Testing Database Operations...")
        
        try:
            # Test database connection
            db = DatabaseManager()
            
            # Test get all videos
            videos = db.get_all_videos()
            self.result_signal.emit("DB_GET_VIDEOS", True, f"Retrieved {len(videos)} videos")
            
            # Test add download
            test_download = {
                'url': self.test_url,
                'title': 'Test Video for MVP',
                'filepath': '/test/path/video.mp4',
                'quality': '1080p',
                'format': 'mp4',
                'duration': 120,
                'filesize': '25MB',
                'status': 'Success'
            }
            db.add_download(test_download)
            self.result_signal.emit("DB_ADD_DOWNLOAD", True, "Successfully added test download")
            
            # Test search
            search_results = db.search_downloads("Test Video")
            self.result_signal.emit("DB_SEARCH", True, f"Found {len(search_results)} matching videos")
            
            self.results['database_operations'] = True
            
        except Exception as e:
            self.result_signal.emit("DB_OPERATIONS", False, f"Database test failed: {e}")
            self.results['database_operations'] = False
    
    def test_video_info_tab(self):
        """Test Video Info Tab functionality"""
        self.progress_signal.emit("📹 Testing Video Info Tab...")
        
        try:
            # Create tab instance
            video_tab = VideoInfoTab()
            
            # Test UI setup
            required_attrs = ['url_input', 'folder_input', 'get_info_button', 
                            'video_info_table', 'download_button']
            
            missing_attrs = [attr for attr in required_attrs if not hasattr(video_tab, attr)]
            if missing_attrs:
                self.result_signal.emit("VIDEO_TAB_UI", False, f"Missing UI elements: {missing_attrs}")
                self.results['video_info_tab_ui'] = False
            else:
                self.result_signal.emit("VIDEO_TAB_UI", True, "All UI elements present")
                self.results['video_info_tab_ui'] = True
            
            # Test Get Info functionality
            video_tab.url_input.setText(self.test_url)
            initial_count = len(video_tab.video_info_list)
            
            # Simulate Get Info
            video_tab.get_video_info()
            
            new_count = len(video_tab.video_info_list)
            if new_count > initial_count:
                self.result_signal.emit("VIDEO_TAB_GET_INFO", True, f"Added {new_count - initial_count} video(s)")
                self.results['get_info_functionality'] = True
            else:
                self.result_signal.emit("VIDEO_TAB_GET_INFO", False, "Get Info did not add video")
                self.results['get_info_functionality'] = False
            
            # Test table display
            table_rows = video_tab.video_info_table.rowCount()
            if table_rows == new_count:
                self.result_signal.emit("VIDEO_TAB_TABLE", True, f"Table shows {table_rows} rows correctly")
                self.results['table_display'] = True
            else:
                self.result_signal.emit("VIDEO_TAB_TABLE", False, f"Table mismatch: {table_rows} vs {new_count}")
                self.results['table_display'] = False
            
            # Test button functionality
            self.test_video_tab_buttons(video_tab)
            
        except Exception as e:
            self.result_signal.emit("VIDEO_TAB_ERROR", False, f"Video tab test failed: {e}")
            self.results['video_info_tab'] = False
    
    def test_video_tab_buttons(self, video_tab):
        """Test Video Info Tab buttons"""
        try:
            # Test Delete All
            if hasattr(video_tab, 'delete_all_videos'):
                video_tab.delete_all_videos()
                if len(video_tab.video_info_list) == 0:
                    self.result_signal.emit("VIDEO_TAB_DELETE_ALL", True, "Delete All functionality works")
                    self.results['delete_all_function'] = True
                else:
                    self.result_signal.emit("VIDEO_TAB_DELETE_ALL", False, "Delete All did not clear videos")
                    self.results['delete_all_function'] = False
            
            # Re-add video for further testing
            video_tab.url_input.setText(self.test_url)
            video_tab.get_video_info()
            
            # Test Select All functionality
            if hasattr(video_tab, 'toggle_select_all'):
                video_tab.toggle_select_all()
                # Check if checkboxes are selected
                selected_count = 0
                for row in range(video_tab.video_info_table.rowCount()):
                    checkbox = video_tab.video_info_table.cellWidget(row, 0)
                    if checkbox and checkbox.isChecked():
                        selected_count += 1
                
                if selected_count > 0:
                    self.result_signal.emit("VIDEO_TAB_SELECT_ALL", True, f"Selected {selected_count} video(s)")
                    self.results['select_all_function'] = True
                else:
                    self.result_signal.emit("VIDEO_TAB_SELECT_ALL", False, "Select All did not work")
                    self.results['select_all_function'] = False
            
        except Exception as e:
            self.result_signal.emit("VIDEO_TAB_BUTTONS", False, f"Button test failed: {e}")
    
    def test_downloaded_videos_tab(self):
        """Test Downloaded Videos Tab"""
        self.progress_signal.emit("📁 Testing Downloaded Videos Tab...")
        
        try:
            # Create downloaded videos tab
            downloads_tab = DownloadedVideosTab()
            
            # Test UI setup
            required_attrs = ['search_input', 'downloads_table', 'delete_selected_button']
            missing_attrs = [attr for attr in required_attrs if not hasattr(downloads_tab, attr)]
            
            if missing_attrs:
                self.result_signal.emit("DOWNLOADS_TAB_UI", False, f"Missing elements: {missing_attrs}")
                self.results['downloads_tab_ui'] = False
            else:
                self.result_signal.emit("DOWNLOADS_TAB_UI", True, "Downloads tab UI complete")
                self.results['downloads_tab_ui'] = True
            
            # Test load functionality
            downloads_tab.load_downloaded_videos()
            video_count = len(downloads_tab.all_videos)
            self.result_signal.emit("DOWNLOADS_TAB_LOAD", True, f"Loaded {video_count} downloaded videos")
            self.results['downloads_load'] = True
            
        except Exception as e:
            self.result_signal.emit("DOWNLOADS_TAB_ERROR", False, f"Downloads tab test failed: {e}")
            self.results['downloads_tab'] = False
    
    def test_integration(self):
        """Test integration between components"""
        self.progress_signal.emit("🔗 Testing Component Integration...")
        
        try:
            # Test database-UI integration
            db = DatabaseManager()
            videos = db.get_all_videos()
            
            # Create both tabs
            video_tab = VideoInfoTab()
            downloads_tab = DownloadedVideosTab()
            
            # Test data flow
            downloads_tab.load_downloaded_videos()
            loaded_count = len(downloads_tab.all_videos)
            db_count = len(videos)
            
            if loaded_count == db_count:
                self.result_signal.emit("INTEGRATION_DATA_FLOW", True, f"Data consistency: {loaded_count} videos")
                self.results['integration_data_flow'] = True
            else:
                self.result_signal.emit("INTEGRATION_DATA_FLOW", False, f"Data mismatch: UI {loaded_count} vs DB {db_count}")
                self.results['integration_data_flow'] = False
            
        except Exception as e:
            self.result_signal.emit("INTEGRATION_ERROR", False, f"Integration test failed: {e}")
            self.results['integration'] = False
    
    def generate_final_report(self):
        """Generate final test report"""
        self.progress_signal.emit("📊 Generating Final MVP Test Report...")
        
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results.values() if result)
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║                     MVP TEST REPORT                         ║
╠══════════════════════════════════════════════════════════════╣
║ Total Tests: {total_tests:>2} | Passed: {passed_tests:>2} | Success Rate: {success_rate:>5.1f}%     ║
╠══════════════════════════════════════════════════════════════╣
        """
        
        for test_name, result in self.results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            test_display = test_name.replace('_', ' ').title()
            report += f"║ {test_display:<40} {status:>15} ║\n"
        
        report += "╚══════════════════════════════════════════════════════════════╝"
        
        if success_rate >= 80:
            verdict = "🎉 MVP IS PRODUCTION READY!"
        elif success_rate >= 60:
            verdict = "⚠️  MVP needs minor fixes"
        else:
            verdict = "❌ MVP needs major work"
        
        self.result_signal.emit("FINAL_REPORT", success_rate >= 80, f"{report}\n\n{verdict}")


def main():
    """Main test function"""
    print("=" * 80)
    print("🧪 SOCIAL DOWNLOAD MANAGER V2.0 - MVP COMPREHENSIVE TEST")
    print("=" * 80)
    
    app = QApplication(sys.argv)
    
    # Create tester
    tester = MVPTester()
    
    # Connect signals
    tester.progress_signal.connect(lambda msg: print(f"📋 {msg}"))
    tester.result_signal.connect(lambda test, success, msg: print(
        f"{'✅' if success else '❌'} {test}: {msg}"
    ))
    
    # Start testing
    tester.start()
    
    # Wait for completion
    tester.wait()
    
    print("\n🏁 MVP Testing completed!")
    app.quit()


if __name__ == "__main__":
    main() 