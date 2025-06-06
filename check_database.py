#!/usr/bin/env python3
"""
Simple script to check database status
"""

import sys
import os

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.db_manager import DatabaseManager

def main():
    print("🔍 Checking Database Status...")
    print("=" * 50)
    
    try:
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # Check database connection
        videos = db_manager.get_downloads()
        print(f"✅ Database connected successfully!")
        print(f"📊 Found {len(videos)} videos in database")
        
        if videos:
            print("\n📋 Recent videos in database:")
            for i, video in enumerate(videos[-5:]):  # Show last 5
                title = video.get('title', 'Unknown')[:60]
                date = video.get('download_date', 'Unknown')
                status = video.get('status', 'Unknown')
                print(f"  {i+1}. {title} - {date} ({status})")
        else:
            print("\n📝 No videos found in database")
            print("   Try downloading a video to test the functionality!")
            
        print(f"\n📁 Database location: {db_manager.db_path}")
        
        # Test adding a sample video (for testing)
        print("\n🧪 Testing database write functionality...")
        test_video = {
            'url': 'https://example.com/test',
            'title': 'Test Video for Database Verification', 
            'filepath': '/test/path/video.mp4',
            'quality': '1080p',
            'format': 'mp4',
            'duration': 60,
            'filesize': '5.00 MB',
            'status': 'Test'
        }
        
        # Add test video
        db_manager.add_download(test_video)
        print("✅ Test video added to database")
        
        # Remove test video
        db_manager.delete_download_by_title('Test Video for Database Verification')
        print("✅ Test video removed from database")
        
        print("\n🎯 Database functionality test completed successfully!")
        print("The download feature should now work properly.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
        
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 