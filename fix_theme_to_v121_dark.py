#!/usr/bin/env python3
"""
Fix UI Theme to match Social Download Manager v1.2.1 DARK theme
Changes from current light theme to proper v1.2.1 dark theme
"""

import sys
import os
import re
from pathlib import Path

def force_dark_theme_v121():
    """Force dark theme with v1.2.1 exact colors"""
    
    main_window_file = Path('ui/main_window.py')
    
    if not main_window_file.exists():
        print("❌ main_window.py not found")
        return False
    
    try:
        with open(main_window_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("🌑 Applying v1.2.1 dark theme...")
        
        # Find the light theme section and replace with dark theme
        v121_dark_theme = '''        else:  # dark theme (v1.2.1 style)
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    font-family: 'Inter';
                }
                QTabWidget::pane {
                    border: 1px solid #444444;
                    background-color: #2d2d2d;
                }
                QTabBar::tab {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    padding: 8px 15px;
                    border: 1px solid #444444;
                }
                QTabBar::tab:selected {
                    background-color: #0078d7;
                    font-weight: normal;
                }
                QTabBar::tab:hover:!selected {
                    background-color: #505050;
                }
                QTableWidget {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    gridline-color: #444444;
                    border: 1px solid #444444;
                }
                QTableWidget::item {
                    border-bottom: 1px solid #444444;
                    color: #ffffff;
                }
                QTableWidget::item:selected {
                    background-color: #0078d7;
                }
                QTableWidget::item:hover {
                    background-color: #3a3a3a;
                }
                QHeaderView::section {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    padding: 5px;
                    border: 1px solid #444444;
                }
                QHeaderView::section:hover {
                    background-color: #505050;
                }
                QLineEdit, QComboBox {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    border: 1px solid #555555;
                    padding: 5px;
                }
                QComboBox:hover {
                    background-color: #505050;
                    border: 1px solid #666666;
                }
                QComboBox::drop-down:hover {
                    background-color: #505050;
                }
                QPushButton {
                    background-color: #0078d7;
                    color: #ffffff;
                    border: none;
                    padding: 8px 15px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #0086f0;
                }
                QPushButton:pressed {
                    background-color: #0067b8;
                }
                QPushButton:disabled {
                    background-color: #444444 !important;
                    color: #777777 !important;
                    border: none !important;
                }
                QCheckBox {
                    color: #ffffff;
                }
                QCheckBox::indicator {
                    width: 13px;
                    height: 13px;
                    background-color: #3d3d3d;
                    border: 1px solid #555555;
                    border-radius: 2px;
                }
                QCheckBox::indicator:checked {
                    background-color: #0078d7;
                    border: 1px solid #0078d7;
                    border-radius: 2px;
                }
                QTableWidget QCheckBox::indicator {
                    width: 13px;
                    height: 13px;
                    background-color: #3d3d3d;
                    border: 1px solid #555555;
                    border-radius: 2px;
                }
                QTableWidget QCheckBox::indicator:checked {
                    background-color: #0078d7;
                    border: 1px solid #0078d7;
                    border-radius: 2px;
                }
                QMenuBar {
                    background-color: #2d2d2d;
                    color: #ffffff;
                }
                QMenuBar::item:selected {
                    background-color: #3d3d3d;
                }
                QMenuBar::item:hover {
                    background-color: #3d3d3d;
                }
                QMenu {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #444444;
                }
                QMenu::item:selected {
                    background-color: #0078d7;
                }
                QMenu::item:hover:!selected {
                    background-color: #3d3d3d;
                }
                QStatusBar {
                    background-color: #2d2d2d;
                    color: #ffffff;
                }
                QDialog {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border-radius: 8px;
                }
                QToolTip {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    border: 1px solid #555555;
                    padding: 5px;
                    border-radius: 3px;
                }
            """)'''
        
        # Find and replace the light theme section  
        light_theme_pattern = r'else:\s*#.*?\n\s*return\s*\{.*?\}'
        
        if 'else:  # light theme' in content:
            # Find the light theme return statement
            start_marker = 'else:  # light theme'
            end_marker = '}'
            
            start_pos = content.find(start_marker)
            if start_pos != -1:
                # Find the matching closing brace for the return dictionary
                brace_count = 0
                end_pos = start_pos
                in_dict = False
                
                for i, char in enumerate(content[start_pos:], start_pos):
                    if char == '{':
                        brace_count += 1
                        in_dict = True
                    elif char == '}' and in_dict:
                        brace_count -= 1
                        if brace_count == 0:
                            end_pos = i + 1
                            break
                
                if end_pos > start_pos:
                    # Replace the light theme section
                    before = content[:start_pos]
                    after = content[end_pos:]
                    
                    # Create the replacement dark theme return
                    v121_dark_return = '''else:  # dark theme (v1.2.1 style)
            return {
                'name': 'dark',
                'background': '#2d2d2d',
                'text': '#ffffff',
                'text_primary': '#ffffff',
                'text_secondary': '#cccccc',
                'text_muted': '#999999',
                'text_on_primary': '#ffffff',
                'surface': '#3d3d3d',
                'primary': '#0078d7',
                'accent': '#0078d7',
                'border': '#444444',
                'border_focus': '#0078d7',
                'header_background': '#3d3d3d',
                'header_text': '#ffffff',
                'input_background': '#3d3d3d',
                'input_border': '#555555',
                'hover': '#505050',
                'selected': '#0078d7',
                'error': '#ff6b6b',
                'warning': '#ffa726',
                'success': '#66bb6a',
                'info': '#42a5f5'
            }'''
                    
                    updated_content = before + v121_dark_return + after
                else:
                    updated_content = content
            else:
                updated_content = content
        else:
            updated_content = content
            
        # Also replace the stylesheet section if it exists
        if '# light theme' in updated_content and 'setStyleSheet(' in updated_content:
            # Find light theme stylesheet and replace
            pattern = r'else:\s*#[^"]*setStyleSheet\(""".*?"""\)'
            if re.search(pattern, updated_content, re.DOTALL):
                updated_content = re.sub(pattern, v121_dark_theme, updated_content, flags=re.DOTALL)
        
        with open(main_window_file, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        print("✅ v1.2.1 dark theme applied")
        return True
        
    except Exception as e:
        print(f"❌ Error updating main_window.py: {e}")
        return False

def set_dark_theme_default():
    """Set dark theme as default instead of light theme"""
    
    config_file = Path('core/config_manager.py')
    
    if not config_file.exists():
        print("❌ config_manager.py not found")
        return False
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("⚙️ Setting dark theme as default...")
        
        # Set theme default to dark
        updated_content = content.replace(
            '"theme": "light"',
            '"theme": "dark"'
        ).replace(
            "'theme': 'light'",
            "'theme': 'dark'"
        )
        
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        print("✅ Dark theme set as default")
        return True
        
    except Exception as e:
        print(f"❌ Error updating config_manager.py: {e}")
        return False

def update_theme_managers_for_dark():
    """Update theme managers to default to dark theme like v1.2.1"""
    
    theme_manager_file = Path('ui/components/core/theme_manager.py')
    
    if not theme_manager_file.exists():
        print("❌ theme_manager.py not found")
        return False
    
    try:
        with open(theme_manager_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("🌑 Updating theme manager for dark v1.2.1...")
        
        # Update dark theme colors to match v1.2.1
        updated_content = content.replace(
            "'background': '#0f172a'",
            "'background': '#2d2d2d'"
        ).replace(
            "'surface': '#1e293b'",
            "'surface': '#3d3d3d'"
        ).replace(
            "'surface-elevated': '#334155'",
            "'surface-elevated': '#505050'"
        ).replace(
            "'border': '#334155'",
            "'border': '#444444'"
        )
        
        with open(theme_manager_file, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        print("✅ Theme manager updated for v1.2.1 colors")
        return True
        
    except Exception as e:
        print(f"❌ Error updating theme_manager.py: {e}")
        return False

def main():
    """Main function to fix UI theme to v1.2.1 dark style"""
    print("🌑 Converting Social Download Manager v2.0 UI to v1.2.1 DARK style")
    print("=" * 65)
    
    results = []
    
    # Fix theme files for dark v1.2.1
    results.append(("MainWindow Dark Theme", force_dark_theme_v121()))
    results.append(("Config Default Dark", set_dark_theme_default()))
    results.append(("Theme Manager Colors", update_theme_managers_for_dark()))
    
    # Summary
    print("\n" + "=" * 65)
    print("📊 V1.2.1 DARK THEME UPDATE SUMMARY:")
    
    success_count = 0
    for component, success in results:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"   {component}: {status}")
        if success:
            success_count += 1
    
    print(f"\n🎯 Overall: {success_count}/{len(results)} components updated")
    
    if success_count == len(results):
        print("\n🎉 Theme successfully converted to v1.2.1 DARK style!")
        print("   - Dark background (#2d2d2d)")
        print("   - Light gray surfaces (#3d3d3d)")
        print("   - White text (#ffffff)")
        print("   - Blue primary color (#0078d7)")
        print("   - Professional dark appearance")
        print("\n💡 Restart the application to see changes")
    else:
        print("\n⚠️ Some components failed to update. Manual review may be needed.")
    
    return success_count == len(results)

if __name__ == "__main__":
    main() 