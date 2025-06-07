#!/usr/bin/env python3
"""
Fix UI Theme to match Social Download Manager v1.2.1
Changes from dark teal theme to light blue theme
"""

import sys
import os
import re
from pathlib import Path

def fix_theme_manager():
    """Fix theme manager to default to light theme with blue colors"""
    
    theme_manager_file = Path('ui/components/core/theme_manager.py')
    
    if not theme_manager_file.exists():
        print("❌ theme_manager.py not found")
        return False
    
    try:
        with open(theme_manager_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("🎨 Updating ThemeManager default colors...")
        
        # Change default primary colors to blue instead of teal
        updated_content = content.replace(
            "'primary': '#2563eb'",
            "'primary': '#0078d7'"
        ).replace(
            "'primary-hover': '#1d4ed8'", 
            "'primary-hover': '#106ebe'"
        ).replace(
            "'border-focus': '#3b82f6'",
            "'border-focus': '#0078d7'"
        )
        
        # Fix dark theme teal colors to use blue
        updated_content = updated_content.replace(
            "'primary': '#3b82f6'",
            "'primary': '#0078d7'"  
        ).replace(
            "'primary-hover': '#2563eb'",
            "'primary-hover': '#106ebe'"
        ).replace(
            "'border-focus': '#3b82f6'",
            "'border-focus': '#0078d7'"
        )
        
        with open(theme_manager_file, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        print("✅ ThemeManager colors updated to blue")
        return True
        
    except Exception as e:
        print(f"❌ Error updating theme_manager.py: {e}")
        return False

def fix_component_theming():
    """Fix component theming to use blue colors"""
    
    component_theme_file = Path('ui/components/common/component_theming.py')
    
    if not component_theme_file.exists():
        print("❌ component_theming.py not found")
        return False
    
    try:
        with open(component_theme_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("🎨 Updating ComponentTheme colors...")
        
        # Fix ComponentColorPalette default primary color
        updated_content = content.replace(
            'primary: str = "#0078d4"',
            'primary: str = "#0078d7"'
        ).replace(
            'button_primary: str = "#0078d4"',
            'button_primary: str = "#0078d7"'
        )
        
        # Fix dark theme teal colors
        updated_content = updated_content.replace(
            'primary="#0d7377"',
            'primary="#0078d7"'
        ).replace(
            'button_primary="#0d7377"',
            'button_primary="#0078d7"'
        ).replace(
            'input_border_focus="#0d7377"',
            'input_border_focus="#0078d7"'
        ).replace(
            'border_focus="#0d7377"',
            'border_focus="#0078d7"'
        ).replace(
            'button_primary_hover="#14a085"',
            'button_primary_hover="#106ebe"'
        )
        
        with open(component_theme_file, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        print("✅ ComponentTheme colors updated to blue")
        return True
        
    except Exception as e:
        print(f"❌ Error updating component_theming.py: {e}")
        return False

def fix_tab_styling():
    """Fix tab styling to use blue colors like v1.2.1"""
    
    tab_styling_file = Path('ui/components/common/tab_styling.py')
    
    if not tab_styling_file.exists():
        print("❌ tab_styling.py not found")
        return False
    
    try:
        with open(tab_styling_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("🎨 Updating TabColorScheme...")
        
        # The default TabColorScheme already has the right blue color #0078d7
        # But let's fix the dark theme teal colors
        updated_content = content.replace(
            'primary="#0d7377"',
            'primary="#0078d7"'
        ).replace(
            'primary_hover="#14a085"',
            'primary_hover="#106ebe"'
        ).replace(
            'primary_pressed="#0a525a"',
            'primary_pressed="#005a9e"'
        ).replace(
            'border_focus="#0d7377"',
            'border_focus="#0078d7"'
        )
        
        with open(tab_styling_file, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        print("✅ TabColorScheme updated")
        return True
        
    except Exception as e:
        print(f"❌ Error updating tab_styling.py: {e}")
        return False

def force_light_theme_default():
    """Force the app to start with light theme by default"""
    
    main_window_file = Path('ui/main_window.py')
    
    if not main_window_file.exists():
        print("❌ main_window.py not found")
        return False
    
    try:
        with open(main_window_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("🌞 Setting light theme as default...")
        
        # Look for any theme initialization and ensure it defaults to light
        # The existing stylesheet in main_window.py already has good blue colors #0078d7
        
        # If there's a theme setting, ensure it's light by default
        if 'dark' in content and 'self.current_theme' in content:
            updated_content = re.sub(
                r'self\.current_theme\s*=\s*["\']dark["\']',
                'self.current_theme = "light"',
                content
            )
        else:
            updated_content = content
        
        # Ensure any theme initialization defaults to light
        if 'ThemeVariant.DARK' in updated_content:
            updated_content = updated_content.replace(
                'ThemeVariant.DARK',
                'ThemeVariant.LIGHT'
            )
        
        with open(main_window_file, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        print("✅ Light theme set as default")
        return True
        
    except Exception as e:
        print(f"❌ Error updating main_window.py: {e}")
        return False

def update_config_manager_theme():
    """Update config manager to default to light theme"""
    
    config_file = Path('core/config_manager.py')
    
    if not config_file.exists():
        print("❌ config_manager.py not found")
        return False
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("⚙️ Updating config default theme...")
        
        # Look for theme configuration
        if '"theme":' in content:
            updated_content = re.sub(
                r'"theme":\s*"dark"',
                '"theme": "light"',
                content
            )
        else:
            updated_content = content
        
        # Look for any other theme defaults
        updated_content = re.sub(
            r"'theme':\s*'dark'",
            "'theme': 'light'",
            updated_content
        )
        
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        print("✅ Config manager theme updated")
        return True
        
    except Exception as e:
        print(f"❌ Error updating config_manager.py: {e}")
        return False

def main():
    """Main function to fix UI theme to v1.2.1 style"""
    print("🎨 Converting Social Download Manager v2.0 UI to v1.2.1 style")
    print("=" * 60)
    
    results = []
    
    # Fix theme files
    results.append(("ThemeManager", fix_theme_manager()))
    results.append(("ComponentTheming", fix_component_theming()))
    results.append(("TabStyling", fix_tab_styling()))
    results.append(("MainWindow", force_light_theme_default()))
    results.append(("ConfigManager", update_config_manager_theme()))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 THEME UPDATE SUMMARY:")
    
    success_count = 0
    for component, success in results:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"   {component}: {status}")
        if success:
            success_count += 1
    
    print(f"\n🎯 Overall: {success_count}/{len(results)} components updated")
    
    if success_count == len(results):
        print("\n🎉 Theme successfully converted to v1.2.1 style!")
        print("   - Blue color scheme (#0078d7)")
        print("   - Light theme as default")
        print("   - Clean, professional appearance")
        print("\n💡 Restart the application to see changes")
    else:
        print("\n⚠️ Some components failed to update. Manual review may be needed.")
    
    return success_count == len(results)

if __name__ == "__main__":
    main() 