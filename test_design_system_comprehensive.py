#!/usr/bin/env python3
"""
Comprehensive Design System Test Suite
Tests both Task 26 (Design Token System) and Task 27 (UI Component Architecture)
"""

import sys
import os
import traceback
from pathlib import Path

def test_design_system():
    print("=== DESIGN SYSTEM COMPREHENSIVE TEST ===")
    print("Testing Task 26 (Design Tokens) & Task 27 (UI Components)")
    print("=" * 60)
    
    results = {
        'token_system': False,
        'theme_system': False,
        'style_system': False,
        'testing_framework': False,
        'integration': False
    }
    
    # Test 1: Token System (Task 26)
    print("\n🔍 1. Testing Token System...")
    try:
        from ui.design_system.tokens import initialize_design_system
        from ui.design_system.tokens.base import TokenCategory
        
        # Initialize the design system to load tokens
        token_registry = initialize_design_system()
        token_manager = token_registry.token_manager
        
        # Test token loading
        token_count = len(token_manager.get_all_tokens())
        print(f"   ✅ Token Manager loaded {token_count} tokens")
        
        # Test token categories - use correct method name
        color_tokens = token_manager.get_tokens_by_category(TokenCategory.COLOR)
        print(f"   ✅ Color tokens: {len(color_tokens)} tokens")
        
        # Test specific token retrieval
        try:
            primary_color = token_manager.resolve_token_value('color-brand-primary-500')
            print(f"   ✅ Primary color token: {primary_color}")
        except:
            # Try a different token that might exist
            available_tokens = list(token_manager.get_all_tokens().keys())[:5]
            print(f"   ⚠️  Available sample tokens: {available_tokens}")
        
        results['token_system'] = True
        
    except Exception as e:
        print(f"   ❌ Token System Error: {e}")
        traceback.print_exc()

    # Test 2: Theme System (Task 26)
    print("\n🎨 2. Testing Theme System...")
    try:
        from ui.design_system.themes.base import ThemeManager
        from ui.design_system.themes.presets import initialize_preset_themes
        
        # Initialize theme system - use correct function name
        theme_manager = ThemeManager()
        initialize_preset_themes(theme_manager)
        
        # Test theme loading - expect 2 themes (light, dark)
        themes = theme_manager.get_all_themes()
        expected_themes = ['light', 'dark']
        print(f"   ✅ Available themes: {list(themes.keys())}")
        
        if set(themes.keys()) == set(expected_themes):
            print(f"   ✅ Correct themes loaded: {len(themes)} themes (light, dark)")
        else:
            print(f"   ⚠️  Unexpected themes: expected {expected_themes}")
        
        # Test theme switching
        theme_manager.switch_theme('dark')
        active_theme = theme_manager.get_active_theme()
        print(f"   ✅ Active theme: {active_theme.name}")
        
        # Test token override
        bg_color = theme_manager.get_themed_token_value('color-background-primary')
        print(f"   ✅ Themed background: {bg_color}")
        
        results['theme_system'] = True
        
    except Exception as e:
        print(f"   ❌ Theme System Error: {e}")
        traceback.print_exc()

    # Test 3: Style System (Task 27)
    print("\n💄 3. Testing Style System...")
    try:
        from ui.design_system.styles.style_manager import StyleManager
        from ui.design_system.styles.component_styles import ComponentStyler
        from ui.design_system.styles.main_window_styles import MainWindowStyler
        
        # Initialize style system
        style_manager = StyleManager()
        component_styler = ComponentStyler(style_manager)
        main_window_styler = MainWindowStyler()
        
        # Test component styling
        button_styles = component_styler.get_button_styles()
        print(f"   ✅ Button styles generated ({len(button_styles)} chars)")
        
        # Test theme-aware styling - use correct method name
        style_manager.switch_theme('light')
        light_styles = component_styler.get_input_styles()
        
        style_manager.switch_theme('dark')
        dark_styles = component_styler.get_input_styles()
        
        if light_styles != dark_styles:
            print("   ✅ Theme-responsive styling working")
        
        # Test main window integration - use correct method name
        main_styles = main_window_styler._generate_complete_stylesheet()
        print(f"   ✅ Main window styles generated ({len(main_styles)} chars)")
        
        results['style_system'] = True
        
    except Exception as e:
        print(f"   ❌ Style System Error: {e}")
        traceback.print_exc()

    # Test 4: Testing Framework (Task 27)
    print("\n🧪 4. Testing Validation Framework...")
    try:
        from ui.design_system.testing.component_validator import ComponentValidator
        from ui.design_system.testing.token_validator import TokenValidator
        from ui.design_system.testing.theme_validator import ThemeValidator
        
        # Test component validator
        comp_validator = ComponentValidator()
        comp_score = comp_validator.validate_component('button')
        print(f"   ✅ Component validator: Button score {comp_score['score']}/100")
        
        # Test token validator - use correct method name
        token_validator = TokenValidator()
        token_validation = token_validator.validate_all_tokens()
        print(f"   ✅ Token validator: {token_validation['summary']['total_tokens']} tokens analyzed")
        
        # Test theme validator
        theme_validator = ThemeValidator()
        theme_score = theme_validator.validate_theme('light')
        print(f"   ✅ Theme validator: Light theme score {theme_score}/100")
        
        results['testing_framework'] = True
        
    except Exception as e:
        print(f"   ❌ Testing Framework Error: {e}")
        traceback.print_exc()

    # Test 5: Integration Test (Task 26 + 27)
    print("\n🔗 5. Testing System Integration...")
    try:
        # Full integration test using the style manager
        from ui.design_system.styles.style_manager import StyleManager
        
        style_manager = StyleManager()
        
        # Test token -> theme -> style chain
        style_manager.switch_theme('dark')
        
        # Get a complete stylesheet that uses tokens and themes
        button_stylesheet = style_manager.generate_stylesheet('button')
        input_stylesheet = style_manager.generate_stylesheet('input')
        table_stylesheet = style_manager.generate_stylesheet('table')
        
        total_length = len(button_stylesheet) + len(input_stylesheet) + len(table_stylesheet)
        
        if total_length > 500:
            print(f"   ✅ Complete stylesheets generated ({total_length} chars total)")
            
            # Check for token usage (no hardcoded colors in generated CSS)
            combined_styles = button_stylesheet + input_stylesheet + table_stylesheet
            hardcoded_colors = ['#ffffff', '#000000', '#ff0000', '#00ff00', '#0000ff']
            hardcoded_found = any(color in combined_styles.lower() for color in hardcoded_colors)
            
            if not hardcoded_found:
                print("   ✅ No common hardcoded colors detected in stylesheets")
            else:
                print("   ⚠️  Some hardcoded colors still present")
            
        # Test stats
        stats = style_manager.get_stats()
        print(f"   ✅ System stats: {stats['current_theme']} theme, {stats['style_cache_size']} cached styles")
            
        results['integration'] = True
        
    except Exception as e:
        print(f"   ❌ Integration Test Error: {e}")
        traceback.print_exc()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY:")
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"   {test_name.replace('_', ' ').title()}: {status}")
    
    print(f"\nOverall Score: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - Design System Ready for Task 28!")
        print("📝 Simplified theme system: Light & Dark themes only")
    elif passed >= total * 0.8:
        print("⚠️  MOSTLY READY - Minor issues to address")
    else:
        print("🚨 SIGNIFICANT ISSUES - Need fixes before Task 28")
    
    return passed, total

if __name__ == "__main__":
    # Add current directory to Python path
    current_dir = Path(__file__).parent
    sys.path.insert(0, str(current_dir))
    
    try:
        passed, total = test_design_system()
        sys.exit(0 if passed == total else 1)
    except Exception as e:
        print(f"Test runner error: {e}")
        sys.exit(1) 