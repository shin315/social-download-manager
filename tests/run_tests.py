#!/usr/bin/env python3
"""
Test runner for Social Download Manager v2.0 App Controller

Runs all unit tests and integration tests for the App Controller and related components.
"""

import sys
import os
import unittest
import logging
from io import StringIO

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def setup_test_environment():
    """Setup test environment and logging"""
    # Configure logging for tests
    logging.basicConfig(
        level=logging.WARNING,  # Reduce noise during tests
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Suppress specific loggers during testing
    logging.getLogger('core.app_controller').setLevel(logging.ERROR)
    logging.getLogger('core.event_system').setLevel(logging.ERROR)
    logging.getLogger('core.config_manager').setLevel(logging.ERROR)

def discover_and_run_tests():
    """Discover and run all tests"""
    print("Social Download Manager v2.0 - App Controller Test Suite")
    print("=" * 60)
    
    # Discover tests
    test_dir = os.path.dirname(__file__)
    suite = unittest.TestLoader().discover(
        test_dir,
        pattern='test_*.py',
        top_level_dir=test_dir
    )
    
    # Count tests
    test_count = suite.countTestCases()
    print(f"Discovered {test_count} test cases")
    print("-" * 60)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(
        verbosity=2,
        stream=sys.stdout,
        buffer=True  # Capture stdout/stderr during tests
    )
    
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.failures:
        print(f"\nFAILURES ({len(result.failures)}):")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    if result.errors:
        print(f"\nERRORS ({len(result.errors)}):")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    # Return success/failure
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\nResult: {'PASSED' if success else 'FAILED'}")
    
    return success

def run_specific_test_module(module_name):
    """Run tests from a specific module"""
    print(f"Running tests from {module_name}")
    print("-" * 40)
    
    try:
        module = __import__(module_name)
        suite = unittest.TestLoader().loadTestsFromModule(module)
        
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        return len(result.failures) == 0 and len(result.errors) == 0
        
    except ImportError as e:
        print(f"Error importing {module_name}: {e}")
        return False

def run_quick_tests():
    """Run a quick subset of critical tests"""
    print("Running Quick Test Suite (Critical tests only)")
    print("-" * 50)
    
    # Import test modules
    from test_app_controller import TestAppController
    from test_integration import TestAppControllerIntegration
    
    # Create test suite with critical tests
    suite = unittest.TestSuite()
    
    # Add critical unit tests
    suite.addTest(TestAppController('test_initial_state'))
    suite.addTest(TestAppController('test_successful_initialization'))
    suite.addTest(TestAppController('test_component_registration'))
    suite.addTest(TestAppController('test_error_handling'))
    suite.addTest(TestAppController('test_shutdown'))
    
    # Add critical integration tests
    suite.addTest(TestAppControllerIntegration('test_complete_application_lifecycle'))
    suite.addTest(TestAppControllerIntegration('test_config_integration'))
    suite.addTest(TestAppControllerIntegration('test_event_system_integration'))
    
    # Run quick tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\nQuick Test Result: {'PASSED' if success else 'FAILED'}")
    
    return success

def main():
    """Main test runner entry point"""
    setup_test_environment()
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "quick":
            success = run_quick_tests()
        elif command == "unit":
            success = run_specific_test_module("test_app_controller")
        elif command == "integration":
            success = run_specific_test_module("test_integration")
        elif command in ["help", "-h", "--help"]:
            print("App Controller Test Runner")
            print("\nUsage:")
            print("  python run_tests.py [command]")
            print("\nCommands:")
            print("  (no args)   - Run all tests")
            print("  quick       - Run critical tests only")
            print("  unit        - Run unit tests only")
            print("  integration - Run integration tests only")
            print("  help        - Show this help message")
            return 0
        else:
            print(f"Unknown command: {command}")
            print("Use 'python run_tests.py help' for usage information")
            return 1
    else:
        # Run all tests
        success = discover_and_run_tests()
    
    return 0 if success else 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code) 