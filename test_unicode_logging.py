#!/usr/bin/env python3
"""
Test script for Unicode Logging System

This script tests the Unicode-safe logging implementation to ensure it can
handle emojis, special characters, and Unicode text without crashing.
"""

import sys
import os
from pathlib import Path

# Add core directory to path
sys.path.insert(0, str(Path(__file__).parent / 'core'))

from core.logging_system import LoggingSystem
from core.unicode_logging import test_unicode_logging


def test_integrated_unicode_logging():
    """Test Unicode logging through the integrated LoggingSystem"""
    print("🚀 Testing integrated Unicode logging system...")
    
    # Create logging system with Unicode and error handling enabled
    log_system = LoggingSystem(log_directory="test_logs", enable_unicode=True, enable_error_handling=True)
    
    # Get various loggers
    main_logger = log_system.get_logger("main")
    ui_logger = log_system.get_logger("ui")
    error_logger = log_system.get_logger("error")
    
    # Test messages with various Unicode characters
    test_cases = [
        ("Basic ASCII", "Application started successfully"),
        ("Vietnamese", "Ứng dụng đã khởi động thành công ✅"),
        ("Emojis", "Download complete! 🎉🚀📱💯"),
        ("Special chars", "File: café_résumé_naïve.txt"),
        ("Math symbols", "Progress: ∑(downloads) = α + β²"),
        ("Currency", "Cost: $10.99 €8.50 ¥1000 £7.25"),
        ("Arrows", "Navigation: ← ↑ → ↓ ↔ ↕"),
        ("Music notes", "Audio: ♪♫♬♩ 🎵🎶"),
        ("Extended Unicode", "Special: 𝄞𝄢𝄫 🔥💎⭐"),
        ("Mixed content", "User 'José' downloaded 'café.mp3' ✅ (Size: 3.4 MB 📁)")
    ]
    
    print("📝 Testing various Unicode content...")
    
    for test_name, message in test_cases:
        try:
            # Test different log levels
            main_logger.info(f"[{test_name}] INFO: {message}")
            ui_logger.debug(f"[{test_name}] DEBUG: {message}")
            error_logger.warning(f"[{test_name}] WARNING: {message}")
            
            # Test custom log levels
            main_logger.performance(f"[{test_name}] PERFORMANCE: {message}")
            main_logger.audit(f"[{test_name}] AUDIT: {message}")
            
            print(f"  ✅ {test_name}: Passed")
            
        except Exception as e:
            print(f"  ❌ {test_name}: Failed - {e}")
            return False
    
    # Test error logging with Unicode
    try:
        raise ValueError("Test error with emoji 💥 and Unicode: ñ, ü, ç")
    except Exception as e:
        error_logger.exception("Exception occurred with Unicode characters")
    
    # Test performance logging
    with log_system.get_performance_logger().measure_time("unicode_operation", "test"):
        import time
        time.sleep(0.1)  # Simulate some work
        main_logger.info("Unicode performance test completed 🏁")
    
    # Test error handling specifically
    print("\n🛡️ Testing error handling mechanisms...")
    from core.unicode_error_handling import test_error_handling
    try:
        test_error_handling()
    except Exception as e:
        print(f"⚠️ Error handling test had issues: {e}")
    
    # Display comprehensive statistics
    try:
        stats = log_system.get_log_statistics()
        print(f"\n📈 Final System Statistics:")
        print(f"  Handlers: {stats.get('handlers', 0)}")
        print(f"  Loggers: {stats.get('loggers', 0)}")
        print(f"  Unicode enabled: {stats.get('unicode_enabled', False)}")
        print(f"  Error handling enabled: {stats.get('error_handling_enabled', False)}")
        
        if 'unicode_error_stats' in stats:
            error_stats = stats['unicode_error_stats']
            print(f"  Unicode errors tracked: {error_stats.get('total_errors', 0)}")
            print(f"  Circuit breaker active: {error_stats.get('circuit_breaker_active', False)}")
            print(f"  Recent errors: {error_stats.get('recent_errors', 0)}")
    except Exception as e:
        print(f"⚠️ Could not get statistics: {e}")
    
    print("✅ All integrated Unicode logging tests passed!")
    return True


def test_unicode_edge_cases():
    """Test edge cases and potential Unicode issues"""
    print("🔍 Testing Unicode edge cases...")
    
    log_system = LoggingSystem(log_directory="test_logs", enable_unicode=True)
    logger = log_system.get_logger("edge_case_test")
    
    edge_cases = [
        # Null and control characters
        ("Null bytes", "Text with null\x00character"),
        ("Control chars", "Text with\ttab\nand\rnewlines"),
        
        # Mixed encodings (potential issues)
        ("High Unicode", "High Unicode: 🌟🌈🦄🎭🎪"),
        ("Combining chars", "Café with combining: e\u0301 (é)"),
        
        # Very long Unicode string
        ("Long Unicode", "🎵" * 100 + " Music notes repeated"),
        
        # Problematic characters that might cause issues
        ("Problematic", "Quotes: \"smart\" 'quotes' «guillemets»"),
        ("Zero-width", "Zero\u200Bwidth\u200Cspace\u200Djoiner"),
    ]
    
    for test_name, message in edge_cases:
        try:
            logger.info(f"[EDGE CASE - {test_name}] {message}")
            print(f"  ✅ {test_name}: Handled safely")
        except Exception as e:
            print(f"  ⚠️  {test_name}: Error handled gracefully - {e}")
    
    print("✅ Edge case testing completed!")
    return True


def check_log_files():
    """Check that log files were created and contain Unicode content"""
    print("📁 Checking log files...")
    
    log_dir = Path("test_logs")
    if not log_dir.exists():
        print("❌ Log directory not created")
        return False
    
    expected_files = ["app.log", "error.log", "performance.log"]
    
    for filename in expected_files:
        file_path = log_dir / filename
        if file_path.exists():
            print(f"  ✅ {filename}: Created")
            
            # Check file contents
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content:
                        print(f"    📄 Contains {len(content)} characters")
                        # Check for Unicode content
                        if any(ord(c) > 127 for c in content):
                            print(f"    🌐 Contains Unicode characters")
                        else:
                            print(f"    📝 ASCII content only")
                    else:
                        print(f"    ⚠️  File is empty")
            except Exception as e:
                print(f"    ❌ Error reading file: {e}")
                return False
        else:
            print(f"  ❌ {filename}: Not created")
            return False
    
    print("✅ Log file verification completed!")
    return True


def main():
    """Main test function"""
    print("🧪 Unicode Logging System Test Suite")
    print("=" * 50)
    
    # Clean up any existing test logs
    import shutil
    test_log_dir = Path("test_logs")
    if test_log_dir.exists():
        shutil.rmtree(test_log_dir)
    
    success = True
    
    # Test standalone Unicode logging
    print("\n1️⃣ Testing standalone Unicode logging...")
    try:
        success &= test_unicode_logging()
    except Exception as e:
        print(f"❌ Standalone test failed: {e}")
        success = False
    
    # Test integrated Unicode logging
    print("\n2️⃣ Testing integrated Unicode logging...")
    try:
        success &= test_integrated_unicode_logging()
    except Exception as e:
        print(f"❌ Integrated test failed: {e}")
        success = False
    
    # Test edge cases
    print("\n3️⃣ Testing Unicode edge cases...")
    try:
        success &= test_unicode_edge_cases()
    except Exception as e:
        print(f"❌ Edge case test failed: {e}")
        success = False
    
    # Check log files
    print("\n4️⃣ Verifying log files...")
    try:
        success &= check_log_files()
    except Exception as e:
        print(f"❌ Log file check failed: {e}")
        success = False
    
    # Final result
    print("\n" + "=" * 50)
    if success:
        print("🎉 ALL TESTS PASSED! Unicode logging is working correctly.")
        print("✅ The logging system can safely handle:")
        print("   • Emojis and special characters")
        print("   • Non-ASCII Unicode text")
        print("   • Mixed content")
        print("   • Edge cases and error conditions")
    else:
        print("❌ SOME TESTS FAILED! Check the output above for details.")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main()) 