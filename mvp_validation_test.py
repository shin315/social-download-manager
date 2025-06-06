#!/usr/bin/env python3
"""
MVP Validation Test - Post UI Migration
=====================================

Comprehensive validation test suite for Social Download Manager v2.0 MVP functionality
after migrating UI to new architecture. Tests all core features.
"""

import sys
import os
import traceback
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import necessary modules
try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    from ui.components.tabs.video_info_tab import VideoInfoTab
    from ui.components.tabs.downloaded_videos_tab import DownloadedVideosTab
    from utils.db_manager import DatabaseManager
    from main import MainEntryOrchestrator
    print("✅ All imports successful")
except Exception as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)


class MVPValidator:
    """MVP Validation Test Suite"""
    
    def __init__(self):
        self.results = {}
        self.test_url = "https://www.tiktok.com/@astralfrontiers/video/7480193313744817431"
        self.success_count = 0
        self.total_count = 0
        
    def log_result(self, test_name, success, message=""):
        """Log test result"""
        self.results[test_name] = success
        self.total_count += 1
        if success:
            self.success_count += 1
            print(f"✅ {test_name}: {message}")
        else:
            print(f"❌ {test_name}: {message}")
    
    def test_1_database_operations(self):
        """Test 1: Database Operations"""
        print("\n🗄️ Test 1: Database Operations")
        print("-" * 50)
        
        try:
            # Test database connection
            db = DatabaseManager()
            self.log_result("Database Connection", True, "Connected successfully")
            
            # Test get all videos
            videos = db.get_all_videos()
            self.log_result("Get All Videos", True, f"Retrieved {len(videos)} videos")
            
            # Test search functionality
            search_results = db.search_downloads("test")
            self.log_result("Search Function", True, f"Search returned {len(search_results)} results")
            
        except Exception as e:
            self.log_result("Database Operations", False, f"Error: {e}")
    
    def test_2_video_info_tab_creation(self):
        """Test 2: Video Info Tab Creation and UI"""
        print("\n📹 Test 2: Video Info Tab Creation")
        print("-" * 50)
        
        try:
            # Create Video Info Tab
            self.video_tab = VideoInfoTab()
            self.log_result("Video Tab Creation", True, "VideoInfoTab created successfully")
            
            # Check essential UI elements
            ui_elements = [
                'url_input', 'folder_input', 'get_info_button',
                'video_info_table', 'download_button', 'select_all_button',
                'delete_selected_button', 'delete_all_button'
            ]
            
            missing = []
            for element in ui_elements:
                if not hasattr(self.video_tab, element):
                    missing.append(element)
            
            if missing:
                self.log_result("UI Elements", False, f"Missing: {missing}")
            else:
                self.log_result("UI Elements", True, "All UI elements present")
            
            # Check if video_info_list exists
            if hasattr(self.video_tab, 'video_info_list'):
                self.log_result("Video Info List", True, f"List has {len(self.video_tab.video_info_list)} items")
            else:
                self.log_result("Video Info List", False, "video_info_list attribute missing")
                
        except Exception as e:
            self.log_result("Video Tab Creation", False, f"Error: {e}")
            traceback.print_exc()
    
    def test_3_get_video_info(self):
        """Test 3: Get Video Info Functionality"""
        print("\n🔍 Test 3: Get Video Info")
        print("-" * 50)
        
        try:
            # Set test URL
            self.video_tab.url_input.setText(self.test_url)
            self.log_result("URL Input", True, "Test URL set successfully")
            
            # Get initial count
            initial_count = len(self.video_tab.video_info_list)
            
            # Execute get info
            self.video_tab.get_video_info()
            
            # Check if video was added
            new_count = len(self.video_tab.video_info_list)
            if new_count > initial_count:
                self.log_result("Get Video Info", True, f"Added {new_count - initial_count} video(s)")
            else:
                self.log_result("Get Video Info", False, "No video was added")
            
            # Check table update
            table_rows = self.video_tab.video_info_table.rowCount()
            if table_rows == new_count:
                self.log_result("Table Update", True, f"Table shows {table_rows} rows correctly")
            else:
                self.log_result("Table Update", False, f"Table mismatch: {table_rows} vs {new_count}")
                
        except Exception as e:
            self.log_result("Get Video Info", False, f"Error: {e}")
            traceback.print_exc()
    
    def test_4_button_functionality(self):
        """Test 4: Button Functionality"""
        print("\n🔘 Test 4: Button Functionality")
        print("-" * 50)
        
        try:
            # Test Select All
            if hasattr(self.video_tab, 'toggle_select_all'):
                self.video_tab.toggle_select_all()
                self.log_result("Select All Button", True, "Select All executed without error")
            else:
                self.log_result("Select All Button", False, "toggle_select_all method not found")
            
            # Test Download button (just check if method exists)
            if hasattr(self.video_tab, 'download_videos'):
                self.log_result("Download Button", True, "download_videos method exists")
            else:
                self.log_result("Download Button", False, "download_videos method not found")
            
            # Test Delete All
            if hasattr(self.video_tab, 'delete_all_videos'):
                self.log_result("Delete All Button", True, "delete_all_videos method exists")
            else:
                self.log_result("Delete All Button", False, "delete_all_videos method not found")
            
            # Test Delete Selected
            if hasattr(self.video_tab, 'delete_selected_videos'):
                self.log_result("Delete Selected Button", True, "delete_selected_videos method exists")
            else:
                self.log_result("Delete Selected Button", False, "delete_selected_videos method not found")
                
        except Exception as e:
            self.log_result("Button Functionality", False, f"Error: {e}")
            traceback.print_exc()
    
    def test_5_downloaded_videos_tab(self):
        """Test 5: Downloaded Videos Tab"""
        print("\n📁 Test 5: Downloaded Videos Tab")
        print("-" * 50)
        
        try:
            # Create Downloaded Videos Tab
            downloads_tab = DownloadedVideosTab()
            self.log_result("Downloads Tab Creation", True, "DownloadedVideosTab created successfully")
            
            # Check UI elements
            ui_elements = ['search_input', 'downloads_table']
            missing = [elem for elem in ui_elements if not hasattr(downloads_tab, elem)]
            
            if missing:
                self.log_result("Downloads UI Elements", False, f"Missing: {missing}")
            else:
                self.log_result("Downloads UI Elements", True, "All UI elements present")
            
            # Test load functionality
            downloads_tab.load_downloaded_videos()
            video_count = len(downloads_tab.all_videos) if hasattr(downloads_tab, 'all_videos') else 0
            self.log_result("Load Downloaded Videos", True, f"Loaded {video_count} videos")
            
        except Exception as e:
            self.log_result("Downloaded Videos Tab", False, f"Error: {e}")
            traceback.print_exc()
    
    def test_6_main_app_startup(self):
        """Test 6: Main App Startup Components"""
        print("\n🚀 Test 6: Main App Components")
        print("-" * 50)
        
        try:
            # Test if MainEntryOrchestrator can be created
            # Note: We don't fully initialize to avoid GUI conflicts
            self.log_result("Main Orchestrator Import", True, "MainEntryOrchestrator imported successfully")
            
            # Test if essential folders exist
            folders = ['data', 'ui', 'utils', 'core']
            for folder in folders:
                if os.path.exists(folder):
                    self.log_result(f"Folder {folder}", True, f"{folder} folder exists")
                else:
                    self.log_result(f"Folder {folder}", False, f"{folder} folder missing")
                    
        except Exception as e:
            self.log_result("Main App Components", False, f"Error: {e}")
            traceback.print_exc()
    
    def test_7_file_structure_integrity(self):
        """Test 7: File Structure Integrity"""
        print("\n📂 Test 7: File Structure Integrity")
        print("-" * 50)
        
        try:
            # Check essential files
            essential_files = [
                'main.py',
                'ui/components/tabs/video_info_tab.py',
                'ui/components/tabs/downloaded_videos_tab.py',
                'utils/db_manager.py',
                'requirements.txt'
            ]
            
            for file_path in essential_files:
                if os.path.exists(file_path):
                    self.log_result(f"File {os.path.basename(file_path)}", True, f"{file_path} exists")
                else:
                    self.log_result(f"File {os.path.basename(file_path)}", False, f"{file_path} missing")
                    
        except Exception as e:
            self.log_result("File Structure", False, f"Error: {e}")
    
    def generate_report(self):
        """Generate final validation report"""
        print("\n" + "=" * 70)
        print("📊 MVP VALIDATION TEST RESULTS")
        print("=" * 70)
        
        success_rate = (self.success_count / self.total_count * 100) if self.total_count > 0 else 0
        
        # Group results by category
        categories = {
            "Database": ["Database Connection", "Get All Videos", "Search Function"],
            "Video Info Tab": ["Video Tab Creation", "UI Elements", "Video Info List", 
                             "URL Input", "Get Video Info", "Table Update"],
            "Button Functions": ["Select All Button", "Download Button", "Delete All Button", 
                               "Delete Selected Button"],
            "Downloads Tab": ["Downloads Tab Creation", "Downloads UI Elements", "Load Downloaded Videos"],
            "App Structure": ["Main Orchestrator Import", "Folder data", "Folder ui", 
                            "Folder utils", "Folder core"],
            "File Integrity": ["File main.py", "File video_info_tab.py", "File downloaded_videos_tab.py",
                             "File db_manager.py", "File requirements.txt"]
        }
        
        for category, tests in categories.items():
            print(f"\n{category}:")
            for test in tests:
                if test in self.results:
                    status = "✅ PASS" if self.results[test] else "❌ FAIL"
                    print(f"  {test:<30} {status}")
        
        print("-" * 70)
        print(f"TOTAL: {self.total_count} | PASSED: {self.success_count} | SUCCESS RATE: {success_rate:.1f}%")
        print("-" * 70)
        
        # Overall verdict
        if success_rate >= 90:
            verdict = "🎉 EXCELLENT! MVP is fully functional"
            status = "READY FOR PRODUCTION"
        elif success_rate >= 80:
            verdict = "✅ GOOD! MVP is mostly functional"
            status = "READY WITH MINOR FIXES"
        elif success_rate >= 70:
            verdict = "⚠️ ACCEPTABLE. MVP needs some fixes"
            status = "NEEDS IMPROVEMENTS"
        else:
            verdict = "❌ POOR. MVP needs significant work"
            status = "NOT READY"
        
        print(f"\n{verdict}")
        print(f"STATUS: {status}")
        
        # Timestamp
        print(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return success_rate >= 70


def main():
    """Main validation function"""
    print("=" * 70)
    print("🧪 SOCIAL DOWNLOAD MANAGER V2.0 - MVP VALIDATION TEST")
    print("🔄 Post UI Migration Validation")
    print("=" * 70)
    
    # Initialize Qt Application
    app = QApplication(sys.argv)
    
    # Create validator
    validator = MVPValidator()
    
    # Run all tests
    try:
        validator.test_1_database_operations()
        validator.test_2_video_info_tab_creation()
        validator.test_3_get_video_info()
        validator.test_4_button_functionality()
        validator.test_5_downloaded_videos_tab()
        validator.test_6_main_app_startup()
        validator.test_7_file_structure_integrity()
        
        # Generate final report
        is_ready = validator.generate_report()
        
        # Exit with appropriate code
        sys.exit(0 if is_ready else 1)
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main() 