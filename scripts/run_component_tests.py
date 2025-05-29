"""
Component Test Runner

Script to run component tests with coverage reporting and detailed output.
Provides both command-line interface and programmatic access.
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path

def setup_test_environment():
    """Setup test environment and paths"""
    # Add project root to path
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    
    # Ensure test directory exists
    test_dir = project_root / "tests"
    test_dir.mkdir(exist_ok=True)
    
    return project_root, test_dir

def run_component_tests(coverage=True, verbose=True, specific_test=None):
    """Run component tests with optional coverage reporting"""
    project_root, test_dir = setup_test_environment()
    
    # Build pytest command
    cmd = [sys.executable, "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
    
    # Add specific test file or pattern
    if specific_test:
        cmd.append(str(test_dir / specific_test))
    else:
        cmd.append(str(test_dir / "test_components.py"))
    
    # Add coverage if requested
    if coverage:
        cmd.extend([
            "--cov=ui.components",
            "--cov-report=html:coverage_html",
            "--cov-report=term-missing"
        ])
    
    # Add additional pytest options
    cmd.extend([
        "--tb=short",  # Shorter traceback format
        "--strict-markers",  # Strict marker checking
        "--disable-warnings"  # Disable warnings for cleaner output
    ])
    
    print(f"Running command: {' '.join(cmd)}")
    print(f"Working directory: {project_root}")
    print("-" * 50)
    
    # Run tests
    try:
        result = subprocess.run(cmd, cwd=project_root, capture_output=False)
        return result.returncode == 0
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Make sure pytest is installed: pip install pytest pytest-cov")
        return False

def run_specific_component_test(component_name):
    """Run tests for a specific component"""
    test_patterns = {
        'events': 'TestEventSystem',
        'language': 'TestLanguageSupport', 
        'theme': 'TestThemeSupport',
        'tooltip': 'TestTooltipSupport',
        'buttons': 'TestActionButtonGroup',
        'statistics': 'TestStatisticsWidget',
        'thumbnail': 'TestThumbnailWidget',
        'progress': 'TestProgressTracker',
        'integration': 'TestComponentIntegration',
        'performance': 'TestComponentPerformance',
        'mock': 'TestMockIntegration'
    }
    
    if component_name in test_patterns:
        test_class = test_patterns[component_name]
        cmd = [
            sys.executable, "-m", "pytest", 
            "tests/test_components.py",
            f"-k", test_class,
            "-v"
        ]
        
        project_root, _ = setup_test_environment()
        subprocess.run(cmd, cwd=project_root)
    else:
        print(f"Unknown component: {component_name}")
        print(f"Available components: {', '.join(test_patterns.keys())}")

def check_test_dependencies():
    """Check if test dependencies are installed"""
    required_packages = ['pytest', 'pytest-cov', 'PyQt6']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("Missing required packages:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\nInstall with: pip install " + " ".join(missing_packages))
        return False
    
    return True

def generate_test_report():
    """Generate comprehensive test report"""
    project_root, _ = setup_test_environment()
    
    print("Generating comprehensive test report...")
    
    # Run tests with detailed reporting
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/test_components.py",
        "--cov=ui.components",
        "--cov-report=html:test_reports/coverage",
        "--cov-report=xml:test_reports/coverage.xml",
        "--cov-report=term-missing",
        "--junitxml=test_reports/junit.xml",
        "-v",
        "--tb=long"
    ]
    
    # Create reports directory
    reports_dir = project_root / "test_reports"
    reports_dir.mkdir(exist_ok=True)
    
    try:
        result = subprocess.run(cmd, cwd=project_root)
        
        if result.returncode == 0:
            print("\n" + "="*50)
            print("TEST REPORT GENERATED SUCCESSFULLY")
            print("="*50)
            print(f"Coverage HTML report: {reports_dir}/coverage/index.html")
            print(f"JUnit XML report: {reports_dir}/junit.xml")
            print(f"Coverage XML report: {reports_dir}/coverage.xml")
        else:
            print("Tests failed. Check the output above for details.")
            
        return result.returncode == 0
        
    except FileNotFoundError:
        print("Error: pytest not found. Install with: pip install pytest pytest-cov")
        return False

def validate_component_structure():
    """Validate that all components have proper structure"""
    project_root, _ = setup_test_environment()
    
    print("Validating component structure...")
    
    # Check if all expected files exist
    expected_files = [
        "ui/components/__init__.py",
        "ui/components/common/__init__.py",
        "ui/components/common/models.py",
        "ui/components/common/interfaces.py", 
        "ui/components/common/events.py",
        "ui/components/mixins/__init__.py",
        "ui/components/mixins/language_support.py",
        "ui/components/mixins/theme_support.py",
        "ui/components/mixins/tooltip_support.py",
        "ui/components/widgets/__init__.py",
        "ui/components/widgets/action_button_group.py",
        "ui/components/widgets/statistics_widget.py",
        "ui/components/widgets/thumbnail_widget.py",
        "ui/components/widgets/progress_tracker.py"
    ]
    
    missing_files = []
    for file_path in expected_files:
        full_path = project_root / file_path
        if not full_path.exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("Missing component files:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        return False
    
    print("✅ All component files exist")
    
    # Test basic imports
    try:
        from ui.components.common.models import ButtonConfig, ButtonType
        from ui.components.common.events import EventType, get_event_bus
        from ui.components.mixins.language_support import LanguageSupport
        from ui.components.widgets.action_button_group import ActionButtonGroup
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="Component Test Runner")
    parser.add_argument("--no-coverage", action="store_true", help="Skip coverage reporting")
    parser.add_argument("--quiet", action="store_true", help="Quiet mode")
    parser.add_argument("--component", help="Run tests for specific component")
    parser.add_argument("--report", action="store_true", help="Generate comprehensive test report")
    parser.add_argument("--validate", action="store_true", help="Validate component structure")
    parser.add_argument("--check-deps", action="store_true", help="Check test dependencies")
    
    args = parser.parse_args()
    
    # Check dependencies first
    if args.check_deps:
        if check_test_dependencies():
            print("✅ All test dependencies are installed")
        return
    
    # Validate structure
    if args.validate:
        if validate_component_structure():
            print("✅ Component structure is valid")
        else:
            print("❌ Component structure validation failed")
        return
    
    # Generate comprehensive report
    if args.report:
        success = generate_test_report()
        sys.exit(0 if success else 1)
    
    # Run specific component tests
    if args.component:
        run_specific_component_test(args.component)
        return
    
    # Check dependencies before running tests
    if not check_test_dependencies():
        sys.exit(1)
    
    # Run component tests
    success = run_component_tests(
        coverage=not args.no_coverage,
        verbose=not args.quiet
    )
    
    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)

if __name__ == "__main__":
    main() 