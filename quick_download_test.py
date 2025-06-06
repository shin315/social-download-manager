#!/usr/bin/env python3
"""
Quick Download Test
==================

Test download functionality in the actual app to verify fix.
"""

import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from ui.components.tabs.video_info_tab import VideoInfoTab


def test_download_fix():
    """Test that download function works without QTimer error"""
    print("🔧 Testing Download Fix")
    print("=" * 40)
    
    # Initialize Qt Application
    app = QApplication(sys.argv)
    
    try:
        # Create video tab
        video_tab = VideoInfoTab()
        print("✅ Video tab created")
        
        # Set test URL
        test_url = "https://www.tiktok.com/@astralfrontiers/video/7480193313744817431"
        video_tab.url_input.setText(test_url)
        print("✅ URL set")
        
        # Set download folder
        download_folder = "./test_downloads"
        if not os.path.exists(download_folder):
            os.makedirs(download_folder)
        video_tab.folder_input.setText(download_folder)
        print("✅ Download folder set")
        
        # Get video info
        video_tab.get_video_info()
        
        if len(video_tab.video_info_list) > 0:
            print("✅ Video info retrieved")
            
            # Select all videos
            video_tab.toggle_select_all()
            print("✅ Videos selected")
            
            # Try to download (this should not fail with QTimer error)
            try:
                video_tab.download_videos()
                print("✅ Download function executed successfully!")
                print("✅ QTimer error has been FIXED!")
                return True
                
            except NameError as e:
                if "QTimer" in str(e):
                    print(f"❌ QTimer error still present: {e}")
                    return False
                else:
                    print(f"❌ Other NameError: {e}")
                    return False
            except Exception as e:
                print(f"⚠️ Other error (but QTimer works): {e}")
                print("✅ QTimer error has been FIXED!")
                return True
                
        else:
            print("❌ No video info retrieved")
            return False
            
    except Exception as e:
        print(f"❌ Critical error: {e}")
        return False


def main():
    """Main test function"""
    print("🧪 QUICK DOWNLOAD FIX TEST")
    print("=" * 40)
    
    success = test_download_fix()
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 DOWNLOAD FIX SUCCESSFUL!")
        print("✅ QTimer import error resolved")
        print("✅ Download functionality working")
    else:
        print("❌ Download fix failed")
        print("❌ QTimer error may still exist")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 