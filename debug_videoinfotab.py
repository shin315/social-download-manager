#!/usr/bin/env python3
"""
Debug script to test VideoInfoTab creation step by step
"""

import sys
import traceback
from PyQt6.QtWidgets import QApplication

def test_step_by_step():
    """Test VideoInfoTab creation step by step"""
    try:
        print("🔍 Step-by-step VideoInfoTab Debug")
        print("=" * 50)
        
        # Step 1: Create QApplication
        print("1. Creating QApplication...")
        app = QApplication(sys.argv)
        print("   ✅ QApplication created")
        
        # Step 2: Import TabPerformanceMonitor
        print("2. Testing TabPerformanceMonitor import...")
        from ui.components.common import TabPerformanceMonitor
        print("   ✅ TabPerformanceMonitor imported")
        
        # Step 3: Import TabConfig and related
        print("3. Testing TabConfig imports...")
        from ui.components.common import TabConfig, create_standard_tab_config
        print("   ✅ TabConfig imports successful")
        
        # Step 4: Create TabConfig
        print("4. Creating TabConfig...")
        config = create_standard_tab_config(
            tab_id="video_info",
            title_key="TAB_VIDEO_INFO",
            auto_save=True,
            validation_required=True,
            state_persistence=True
        )
        print("   ✅ TabConfig created")
        
        # Step 5: Import VideoInfoTab
        print("5. Importing VideoInfoTab...")
        from ui.components.tabs.video_info_tab import VideoInfoTab
        print("   ✅ VideoInfoTab imported")
        
        # Step 6: Create VideoInfoTab instance
        print("6. Creating VideoInfoTab instance...")
        video_tab = VideoInfoTab(config=config, parent=None)
        print("   ✅ VideoInfoTab created successfully!")
        
        print("\n🎉 All steps completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print(f"Error type: {type(e)}")
        print("Full traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_step_by_step() 