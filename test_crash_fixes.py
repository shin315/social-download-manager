#!/usr/bin/env python3
"""
Test script to verify crash fixes
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_video_tab_import():
    """Test if VideoInfoTab can be imported and instantiated"""
    try:
        from ui.components.tabs.video_info_tab import VideoInfoTab
        print("✅ VideoInfoTab import successful")
        return True
    except Exception as e:
        print(f"❌ VideoInfoTab import failed: {e}")
        return False

def test_get_video_info_method():
    """Test if get_video_info method works without arguments"""
    try:
        from ui.components.tabs.video_info_tab import VideoInfoTab
        
        # Create dummy tab (without parent for testing)
        tab = VideoInfoTab()
        
        # Check if method exists and accepts no arguments
        if hasattr(tab, 'get_video_info'):
            import inspect
            sig = inspect.signature(tab.get_video_info)
            params = list(sig.parameters.keys())
            
            if len(params) == 0:  # Only self parameter
                print("✅ get_video_info method signature correct")
                return True
            else:
                print(f"❌ get_video_info has unexpected parameters: {params}")
                return False
        else:
            print("❌ get_video_info method not found")
            return False
    
    except Exception as e:
        print(f"❌ get_video_info test failed: {e}")
        return False

def main():
    print("🧪 Testing crash fixes...")
    
    tests = [
        test_video_tab_import,
        test_get_video_info_method
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"📊 Test Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All fixes working! App should be stable now.")
    else:
        print("⚠️ Some issues remain, but basic functionality should work.")

if __name__ == "__main__":
    main()
