#!/usr/bin/env python3
"""
Test Video Info Tab Functionality
=====================================

Test script to verify all Video Info tab functions work properly
including Get Info, Download, Delete operations with real URLs.
"""

import sys
import os
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from ui.components.tabs.video_info_tab import VideoInfoTab
from utils.db_manager import DatabaseManager


class VideoInfoTester:
    """Test class for Video Info Tab functionality"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.tab = VideoInfoTab()
        self.test_url = "https://www.tiktok.com/@astralfrontiers/video/7480193313744817431?is_from_webapp=1&sender_device=pc"
        self.test_results = {
            "ui_setup": False,
            "get_info": False,
            "download": False,
            "delete_selected": False,
            "delete_all": False,
            "choose_folder": False,
            "database_connection": False
        }
    
    def test_database_connection(self):
        """Test database connection"""
        try:
            db = DatabaseManager()
            videos = db.get_all_videos()
            print(f"✅ Database connection: OK ({len(videos)} videos found)")
            self.test_results["database_connection"] = True
            return True
        except Exception as e:
            print(f"❌ Database connection: FAILED - {e}")
            return False
    
    def test_ui_setup(self):
        """Test UI setup and layout"""
        try:
            self.tab.show()
            
            # Check key UI elements exist
            checks = [
                ("url_input", hasattr(self.tab, 'url_input')),
                ("folder_input", hasattr(self.tab, 'folder_input')), 
                ("get_info_button", hasattr(self.tab, 'get_info_button')),
                ("choose_folder_button", hasattr(self.tab, 'choose_folder_button')),
                ("video_info_table", hasattr(self.tab, 'video_info_table')),
                ("download_button", hasattr(self.tab, 'download_button')),
                ("select_all_button", hasattr(self.tab, 'select_all_button')),
                ("delete_selected_button", hasattr(self.tab, 'delete_selected_button')),
                ("delete_all_button", hasattr(self.tab, 'delete_all_button'))
            ]
            
            missing = [name for name, exists in checks if not exists]
            if missing:
                print(f"❌ UI Setup: Missing elements - {missing}")
                return False
            
            print("✅ UI Setup: All elements present")
            self.test_results["ui_setup"] = True
            return True
            
        except Exception as e:
            print(f"❌ UI Setup: FAILED - {e}")
            return False
    
    def test_get_info_functionality(self):
        """Test Get Info button functionality"""
        try:
            # Set test URL
            self.tab.url_input.setText(self.test_url)
            
            # Get initial video count
            initial_count = len(self.tab.video_info_list)
            
            # Trigger Get Info
            self.tab.get_info_button.click()
            
            # Check if video was added
            new_count = len(self.tab.video_info_list)
            if new_count > initial_count:
                print(f"✅ Get Info: Working (added {new_count - initial_count} video)")
                
                # Check table update
                table_rows = self.tab.video_info_table.rowCount()
                if table_rows == new_count:
                    print(f"✅ Table Update: Working ({table_rows} rows)")
                else:
                    print(f"⚠️ Table Update: Mismatch (list: {new_count}, table: {table_rows})")
                
                self.test_results["get_info"] = True
                return True
            else:
                print("❌ Get Info: No video added")
                return False
                
        except Exception as e:
            print(f"❌ Get Info: FAILED - {e}")
            return False
    
    def test_button_functionality(self):
        """Test all button functionality"""
        results = {}
        
        # Test Download button
        try:
            if hasattr(self.tab, 'download_button'):
                self.tab.download_button.click()
                print("✅ Download Button: Clickable")
                results["download"] = True
            else:
                print("❌ Download Button: Not found")
                results["download"] = False
        except Exception as e:
            print(f"❌ Download Button: ERROR - {e}")
            results["download"] = False
        
        # Test Select All button
        try:
            if hasattr(self.tab, 'select_all_button'):
                self.tab.select_all_button.click()
                print("✅ Select All Button: Clickable")
                results["select_all"] = True
            else:
                print("❌ Select All Button: Not found")
                results["select_all"] = False
        except Exception as e:
            print(f"❌ Select All Button: ERROR - {e}")
            results["select_all"] = False
        
        # Test Delete Selected button
        try:
            if hasattr(self.tab, 'delete_selected_button'):
                self.tab.delete_selected_button.click()
                print("✅ Delete Selected Button: Clickable")
                results["delete_selected"] = True
            else:
                print("❌ Delete Selected Button: Not found")
                results["delete_selected"] = False
        except Exception as e:
            print(f"❌ Delete Selected Button: ERROR - {e}")
            results["delete_selected"] = False
        
        # Test Delete All button
        try:
            if hasattr(self.tab, 'delete_all_button'):
                self.tab.delete_all_button.click()
                print("✅ Delete All Button: Clickable")
                results["delete_all"] = True
            else:
                print("❌ Delete All Button: Not found")
                results["delete_all"] = False
        except Exception as e:
            print(f"❌ Delete All Button: ERROR - {e}")
            results["delete_all"] = False
        
        return results
    
    def test_choose_folder_functionality(self):
        """Test Choose Folder functionality"""
        try:
            # Test if method exists and is callable
            if hasattr(self.tab, 'choose_output_folder') and callable(self.tab.choose_output_folder):
                print("✅ Choose Folder: Method exists")
                self.test_results["choose_folder"] = True
                return True
            else:
                print("❌ Choose Folder: Method missing")
                return False
        except Exception as e:
            print(f"❌ Choose Folder: ERROR - {e}")
            return False
    
    def run_comprehensive_test(self):
        """Run all tests"""
        print("=" * 60)
        print("🧪 VIDEO INFO TAB FUNCTIONALITY TEST")
        print("=" * 60)
        print(f"📋 Test URL: {self.test_url}")
        print()
        
        # Run individual tests
        print("🔍 Testing Database Connection...")
        self.test_database_connection()
        print()
        
        print("🔍 Testing UI Setup...")
        self.test_ui_setup()
        print()
        
        print("🔍 Testing Get Info...")
        self.test_get_info_functionality()
        print()
        
        print("🔍 Testing Button Functionality...")
        button_results = self.test_button_functionality()
        print()
        
        print("🔍 Testing Choose Folder...")
        self.test_choose_folder_functionality()
        print()
        
        # Summary
        print("=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results.values() if result)
        total = len(self.test_results)
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title():.<40} {status}")
        
        print(f"\n🎯 Overall Score: {passed}/{total} ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED! Video Info tab is fully functional.")
        elif passed >= total * 0.7:
            print("⚠️ Most tests passed, but some functionality needs fixing.")
        else:
            print("❌ Major issues detected. Significant work needed.")
        
        return passed, total


def main():
    """Main test function"""
    tester = VideoInfoTester()
    
    # Set up timer to close after tests
    timer = QTimer()
    timer.timeout.connect(lambda: tester.app.quit())
    timer.start(5000)  # 5 seconds to run tests
    
    # Run tests after short delay
    QTimer.singleShot(100, tester.run_comprehensive_test)
    
    # Start Qt app
    sys.exit(tester.app.exec())


if __name__ == "__main__":
    main() 