#!/usr/bin/env python3
"""
Integration Test Runner Script
=============================

Simple script to run integration tests for Social Download Manager v2.0.
This script provides an easy way to execute integration tests with different
configurations and generate comprehensive reports.

Usage:
    python run_integration_tests.py                    # Run with default config
    python run_integration_tests.py --config quick     # Run with quick config
    python run_integration_tests.py --help             # Show help
"""

import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import the integration test runner
from tests.integration_test_runner import main

if __name__ == "__main__":
    print("🚀 Social Download Manager v2.0 - Integration Test Runner")
    print("=" * 60)
    print()
    
    # Ensure tests directory structure exists
    tests_dir = PROJECT_ROOT / 'tests'
    reports_dir = tests_dir / 'reports'
    logs_dir = tests_dir / 'logs'
    
    reports_dir.mkdir(exist_ok=True)
    logs_dir.mkdir(exist_ok=True)
    
    print(f"📁 Project Root: {PROJECT_ROOT}")
    print(f"📁 Tests Directory: {tests_dir}")
    print(f"📁 Reports Directory: {reports_dir}")
    print()
    
    # Run the integration test runner
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  Test execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error running integration tests: {e}")
        sys.exit(1) 