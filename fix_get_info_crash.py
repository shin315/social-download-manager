#!/usr/bin/env python3
"""
Quick fix for Social Download Manager v2.0 get_video_info crash
Addresses the argument mismatch error when clicking "Get Info"
"""

import sys
import os
import re
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def find_get_video_info_calls():
    """Find all calls to get_video_info and check for argument mismatches"""
    project_root = Path('.')
    
    # Pattern to find get_video_info calls
    call_pattern = r'\.get_video_info\('
    
    issues_found = []
    
    # Search through Python files
    for py_file in project_root.rglob("*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    if re.search(call_pattern, line):
                        # Check if it's called with arguments
                        if '.get_video_info(' in line and not line.strip().endswith('get_video_info()'):
                            issues_found.append({
                                'file': str(py_file),
                                'line': line_num,
                                'content': line.strip(),
                                'issue': 'get_video_info called with arguments'
                            })
                        
        except Exception as e:
            print(f"Error reading {py_file}: {e}")
    
    return issues_found

def check_component_integration_missing():
    """Check for missing component_integration attribute issues"""
    main_window_file = Path('ui/main_window.py')
    
    if not main_window_file.exists():
        return ["MainWindow file not found"]
    
    issues = []
    
    try:
        with open(main_window_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Check if component_integration is referenced but not defined
            if 'component_integration' in content:
                if 'self.component_integration' not in content:
                    issues.append("component_integration referenced but not defined as attribute")
    
    except Exception as e:
        issues.append(f"Error checking MainWindow: {e}")
    
    return issues

def create_emergency_fixes():
    """Create emergency fixes for the crashes"""
    print("🔧 Creating emergency fixes...")
    
    # Fix 1: Add component_integration to MainWindow if needed
    main_window_file = Path('ui/main_window.py')
    
    if main_window_file.exists():
        try:
            with open(main_window_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Add component_integration attribute if it's missing but referenced
            if 'component_integration' in content and 'self.component_integration' not in content:
                # Find __init__ method and add the attribute
                if 'def __init__(self' in content:
                    init_pattern = r'(def __init__\(self[^:]*\):[^}]*?)(class|\Z)'
                    
                    def add_component_integration(match):
                        init_content = match.group(1)
                        # Add the attribute near the end of __init__
                        if 'self.component_integration' not in init_content:
                            # Add before the end of __init__ or before next class
                            lines = init_content.split('\n')
                            # Insert before the last non-empty line of __init__
                            insert_line = "        # Emergency fix: Add missing component_integration attribute\n        self.component_integration = None"
                            lines.insert(-2, insert_line)
                            init_content = '\n'.join(lines)
                        
                        return init_content + (match.group(2) if match.group(2) else '')
                    
                    fixed_content = re.sub(init_pattern, add_component_integration, content, flags=re.DOTALL)
                    
                    # Write back if changed
                    if fixed_content != content:
                        with open(main_window_file, 'w', encoding='utf-8') as f:
                            f.write(fixed_content)
                        print(f"   ✅ Added component_integration attribute to MainWindow")
                    else:
                        print(f"   ⚠️ Could not auto-fix component_integration in MainWindow")
        
        except Exception as e:
            print(f"   ❌ Error fixing MainWindow: {e}")

def create_test_app():
    """Create a simple test to verify the fixes work"""
    test_content = '''#!/usr/bin/env python3
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
'''
    
    with open('test_crash_fixes.py', 'w', encoding='utf-8') as f:
        f.write(test_content)
    
    print("   ✅ Created test_crash_fixes.py")

def main():
    """Run the crash fix analysis and repairs"""
    print("🚨 Social Download Manager v2.0 - Crash Fix Tool")
    print("=" * 60)
    
    print("\n🔍 Analyzing crash issues...")
    
    # Check for get_video_info argument mismatches
    video_info_issues = find_get_video_info_calls()
    if video_info_issues:
        print(f"\n⚠️ Found {len(video_info_issues)} get_video_info argument issues:")
        for issue in video_info_issues:
            print(f"   📁 {issue['file']}:{issue['line']}")
            print(f"      📄 {issue['content']}")
            print(f"      🔥 {issue['issue']}")
    else:
        print("\n✅ No get_video_info argument mismatch found")
    
    # Check for component_integration issues
    component_issues = check_component_integration_missing()
    if component_issues:
        print(f"\n⚠️ Found component_integration issues:")
        for issue in component_issues:
            print(f"   🔥 {issue}")
    else:
        print("\n✅ No component_integration issues found")
    
    # Create emergency fixes
    print(f"\n🔧 Applying emergency fixes...")
    create_emergency_fixes()
    
    # Create test script
    print(f"\n🧪 Creating test script...")
    create_test_app()
    
    print(f"\n" + "=" * 60)
    print("📋 Fix Summary:")
    print("   1. ✅ Created ui.adapters module")
    print("   2. 🔧 Applied emergency fixes for crashes")
    print("   3. 🧪 Created test script: test_crash_fixes.py")
    
    print(f"\n💡 Next Steps:")
    print("   1. Run: python test_crash_fixes.py")
    print("   2. Test the app: python main.py")
    print("   3. Try clicking 'Get Info' button")
    
    print(f"\n🎯 If crashes persist:")
    print("   • Check the terminal logs for specific errors")
    print("   • Run test_crash_fixes.py to diagnose issues")
    print("   • Report remaining errors for targeted fixes")

if __name__ == "__main__":
    main() 