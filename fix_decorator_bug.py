#!/usr/bin/env python3
"""
Fix decorator bug causing get_video_info() argument mismatch
"""

import sys
import os
import re
from pathlib import Path

def fix_validate_decorator():
    """Fix the validate_before_action decorator to handle methods with no arguments"""
    
    tab_utilities_file = Path('ui/components/common/tab_utilities.py')
    
    if not tab_utilities_file.exists():
        print("❌ tab_utilities.py not found")
        return False
    
    try:
        with open(tab_utilities_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Look for the problematic line and fix it
        old_pattern = r'return func\(self, \*args, \*\*kwargs\)'
        
        # Check if the issue exists
        if 'return func(self, *args, **kwargs)' in content:
            print("🔍 Found decorator issue in validate_before_action")
            
            # Fix: Only pass self when no other args are expected for methods like get_video_info()
            new_decorator = '''def validate_before_action(validation_func: Optional[Callable] = None):
    """
    Decorator to validate tab state before executing an action.
    
    Args:
        validation_func: Custom validation function. If None, uses tab's validate_input method.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Determine validation function
            validator = validation_func
            if validator is None and hasattr(self, 'validate_input'):
                validator = self.validate_input
            elif validator is None and hasattr(self, 'is_valid'):
                validator = lambda: [] if self.is_valid() else ['Invalid state']
            
            # Perform validation
            if validator:
                errors = validator()
                if errors:
                    if hasattr(self, 'show_validation_errors'):
                        self.show_validation_errors(errors)
                    return False  # or raise ValidationError
            
            # FIXED: Check function signature and only pass expected arguments
            import inspect
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())
            
            # If function only expects 'self', don't pass args/kwargs
            if len(params) == 1:  # Only 'self' parameter
                return func(self)
            else:
                return func(self, *args, **kwargs)
        return wrapper
    return decorator'''
            
            # Replace the old decorator with the fixed one
            pattern = r'def validate_before_action\(validation_func: Optional\[Callable\] = None\):.*?return decorator'
            
            fixed_content = re.sub(
                pattern, 
                new_decorator,
                content, 
                flags=re.DOTALL
            )
            
            # Write the fix back
            if fixed_content != content:
                with open(tab_utilities_file, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                print("✅ Fixed validate_before_action decorator")
                return True
            else:
                print("⚠️ Could not apply automatic fix")
                return False
        else:
            print("✅ validate_before_action decorator looks OK")
            return True
            
    except Exception as e:
        print(f"❌ Error fixing decorator: {e}")
        return False

def test_get_video_info_signature():
    """Test if the get_video_info method signature is correct"""
    try:
        import inspect
        from ui.components.tabs.video_info_tab import VideoInfoTab
        
        # Check method signature
        sig = inspect.signature(VideoInfoTab.get_video_info)
        params = list(sig.parameters.keys())
        
        print(f"🔍 get_video_info signature: {params}")
        
        if len(params) == 1:  # Only 'self'
            print("✅ get_video_info signature is correct (only self)")
            return True
        else:
            print(f"❌ get_video_info has unexpected parameters: {params}")
            return False
    
    except Exception as e:
        print(f"❌ Error checking signature: {e}")
        return False

def main():
    """Fix the decorator bug"""
    print("🔧 Social Download Manager v2.0 - Decorator Bug Fix")
    print("=" * 60)
    
    print("\n1️⃣ Checking get_video_info method signature...")
    sig_ok = test_get_video_info_signature()
    
    print("\n2️⃣ Fixing validate_before_action decorator...")
    decorator_fixed = fix_validate_decorator()
    
    print("\n" + "=" * 60)
    print("📋 Fix Summary:")
    print(f"   • Method signature: {'✅ OK' if sig_ok else '❌ Issues'}")
    print(f"   • Decorator fix: {'✅ Applied' if decorator_fixed else '❌ Failed'}")
    
    if sig_ok and decorator_fixed:
        print("\n🎉 Bug fix completed! The 'Get Info' button should work now.")
        print("\n💡 Next steps:")
        print("   1. Run: python main.py")
        print("   2. Test the 'Get Info' button")
        print("   3. Try with a YouTube URL")
    else:
        print("\n⚠️ Some issues remain. Manual intervention may be needed.")

if __name__ == "__main__":
    main() 