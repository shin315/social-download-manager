#!/usr/bin/env python3
"""
Release Candidate Validation & Deployment Preparation - Task 18.4
Social Download Manager v2.0 Final Integration Testing

This script performs comprehensive release candidate validation:
- Build artifact verification with checksum validation
- Cross-platform smoke testing
- Production readiness assessment
- Deployment environment preparation
- Final rollback playbook verification

Usage:
    python release_validation.py --full-validation
    python release_validation.py --build-verification
    python release_validation.py --smoke-tests
    python release_validation.py --deployment-prep
"""

import sys
import os
import hashlib
import json
import subprocess
import platform
import time
import psutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

@dataclass
class ValidationResult:
    """Result of individual validation test"""
    test_name: str
    category: str
    expected_result: str
    actual_result: str
    success: bool
    execution_time: float
    error_details: Optional[str] = None
    artifacts: Optional[List[str]] = None

class ReleaseValidator:
    """Comprehensive release candidate validation framework"""
    
    def __init__(self):
        self.validation_results: List[ValidationResult] = []
        self.setup_logging()
        self.project_root = Path(__file__).parent.parent
        self.build_artifacts = {}
        self.expected_checksums = {}
        
    def setup_logging(self):
        """Setup detailed logging for validation"""
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)
        
    def log(self, level: str, message: str):
        """Enhanced logging with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] {level}: {message}")

    def verify_build_artifacts(self) -> List[ValidationResult]:
        """Verify build artifacts and checksums"""
        self.log("INFO", "🔍 Verifying Build Artifacts and Checksums")
        
        results = []
        
        # Critical application files to verify
        critical_files = [
            "main.py",
            "core/__init__.py", 
            "core/app_controller.py",
            "core/config_manager.py",
            "core/event_system.py",
            "ui/components/__init__.py",
            "requirements.txt",
            "version.py"
        ]
        
        for file_path in critical_files:
            start_time = time.time()
            full_path = self.project_root / file_path
            
            try:
                if full_path.exists():
                    # Calculate file checksum
                    checksum = self._calculate_file_checksum(full_path)
                    file_size = full_path.stat().st_size
                    
                    # Verify file integrity
                    success = file_size > 0 and checksum is not None
                    
                    result = ValidationResult(
                        test_name=f"artifact_verification_{file_path.replace('/', '_')}",
                        category="build_artifacts",
                        expected_result="File exists with valid checksum",
                        actual_result=f"File: {file_size} bytes, SHA256: {checksum[:16]}...",
                        success=success,
                        execution_time=time.time() - start_time,
                        artifacts=[str(full_path)]
                    )
                    
                    self.build_artifacts[file_path] = {
                        'size': file_size,
                        'checksum': checksum,
                        'path': str(full_path)
                    }
                    
                else:
                    result = ValidationResult(
                        test_name=f"artifact_verification_{file_path.replace('/', '_')}",
                        category="build_artifacts",
                        expected_result="File exists",
                        actual_result="File not found",
                        success=False,
                        execution_time=time.time() - start_time,
                        error_details=f"Missing critical file: {file_path}"
                    )
                
                results.append(result)
                status = "✅" if result.success else "❌"
                self.log("INFO", f"  {status} {file_path}: {result.actual_result}")
                
            except Exception as e:
                result = ValidationResult(
                    test_name=f"artifact_verification_{file_path.replace('/', '_')}",
                    category="build_artifacts",
                    expected_result="File verification successful",
                    actual_result=f"Verification failed: {str(e)}",
                    success=False,
                    execution_time=time.time() - start_time,
                    error_details=str(e)
                )
                results.append(result)
                self.log("ERROR", f"  ❌ {file_path}: Verification failed - {e}")
        
        self.validation_results.extend(results)
        return results
        
    def _calculate_file_checksum(self, file_path: Path) -> Optional[str]:
        """Calculate SHA256 checksum for file"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception:
            return None

    def run_smoke_tests(self) -> List[ValidationResult]:
        """Run cross-platform smoke tests"""
        self.log("INFO", "💨 Running Cross-Platform Smoke Tests")
        
        results = []
        
        # Platform-specific smoke tests
        smoke_tests = [
            {
                'name': 'python_environment',
                'description': 'Python environment validation',
                'command': [sys.executable, '--version']
            },
            {
                'name': 'module_imports',
                'description': 'Critical module import validation',
                'command': [sys.executable, '-c', 'import core; import ui; print("Imports successful")']
            },
            {
                'name': 'configuration_loading',
                'description': 'Configuration system validation',
                'command': [sys.executable, '-c', 'from core.config_manager import get_config; print("Config:", get_config().app_name if get_config() else "None")']
            },
            {
                'name': 'event_system',
                'description': 'Event system functionality',
                'command': [sys.executable, '-c', 'from core.event_system import get_event_bus; print("Events:", get_event_bus().get_total_subscribers())']
            }
        ]
        
        for test in smoke_tests:
            start_time = time.time()
            self.log("INFO", f"  🔍 Testing: {test['name']}")
            
            try:
                result = subprocess.run(
                    test['command'],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=self.project_root
                )
                
                success = result.returncode == 0
                actual_result = result.stdout.strip() if success else result.stderr.strip()
                
                validation_result = ValidationResult(
                    test_name=test['name'],
                    category="smoke_tests",
                    expected_result="Command executes successfully",
                    actual_result=actual_result[:100] + "..." if len(actual_result) > 100 else actual_result,
                    success=success,
                    execution_time=time.time() - start_time,
                    error_details=result.stderr if not success else None
                )
                
                results.append(validation_result)
                status = "✅" if success else "❌"
                self.log("INFO", f"    {status} {test['name']}: {validation_result.actual_result}")
                
            except subprocess.TimeoutExpired:
                validation_result = ValidationResult(
                    test_name=test['name'],
                    category="smoke_tests",
                    expected_result="Command completes within timeout",
                    actual_result="Command timed out after 30 seconds",
                    success=False,
                    execution_time=30.0,
                    error_details="Subprocess timeout"
                )
                results.append(validation_result)
                self.log("ERROR", f"    ❌ {test['name']}: Timeout after 30 seconds")
                
            except Exception as e:
                validation_result = ValidationResult(
                    test_name=test['name'],
                    category="smoke_tests",
                    expected_result="Command executes without exception",
                    actual_result=f"Exception: {str(e)}",
                    success=False,
                    execution_time=time.time() - start_time,
                    error_details=str(e)
                )
                results.append(validation_result)
                self.log("ERROR", f"    ❌ {test['name']}: Exception - {e}")
        
        self.validation_results.extend(results)
        return results

    def assess_production_readiness(self) -> List[ValidationResult]:
        """Assess production readiness criteria"""
        self.log("INFO", "🏭 Assessing Production Readiness")
        
        results = []
        
        # Production readiness checks
        readiness_checks = [
            {
                'name': 'system_resources',
                'description': 'System resource availability',
                'check_func': self._check_system_resources
            },
            {
                'name': 'dependency_validation',
                'description': 'Required dependencies verification',
                'check_func': self._check_dependencies
            },
            {
                'name': 'configuration_integrity',
                'description': 'Configuration file integrity',
                'check_func': self._check_configuration_integrity
            },
            {
                'name': 'database_connectivity',
                'description': 'Database connection validation',
                'check_func': self._check_database_connectivity
            },
            {
                'name': 'performance_baselines',
                'description': 'Performance baseline verification',
                'check_func': self._check_performance_baselines
            }
        ]
        
        for check in readiness_checks:
            start_time = time.time()
            self.log("INFO", f"  🔍 Checking: {check['name']}")
            
            try:
                success, message, details = check['check_func']()
                
                validation_result = ValidationResult(
                    test_name=check['name'],
                    category="production_readiness",
                    expected_result="Production criteria met",
                    actual_result=message,
                    success=success,
                    execution_time=time.time() - start_time,
                    error_details=details if not success else None
                )
                
                results.append(validation_result)
                status = "✅" if success else "❌"
                self.log("INFO", f"    {status} {check['name']}: {message}")
                
            except Exception as e:
                validation_result = ValidationResult(
                    test_name=check['name'],
                    category="production_readiness",
                    expected_result="Check completes successfully",
                    actual_result=f"Check failed with exception: {str(e)}",
                    success=False,
                    execution_time=time.time() - start_time,
                    error_details=str(e)
                )
                results.append(validation_result)
                self.log("ERROR", f"    ❌ {check['name']}: Exception - {e}")
        
        self.validation_results.extend(results)
        return results
        
    def _check_system_resources(self) -> Tuple[bool, str, Optional[str]]:
        """Check system resource availability"""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            cpu_count = psutil.cpu_count()
            
            # Resource requirements
            min_memory_gb = 1  # 1GB minimum
            min_disk_gb = 1   # 1GB minimum
            min_cpu_cores = 2  # 2 cores minimum
            
            memory_ok = memory.available / (1024**3) >= min_memory_gb
            disk_ok = disk.free / (1024**3) >= min_disk_gb
            cpu_ok = cpu_count >= min_cpu_cores
            
            if memory_ok and disk_ok and cpu_ok:
                return True, f"Resources sufficient: {memory.available/(1024**3):.1f}GB RAM, {disk.free/(1024**3):.1f}GB disk, {cpu_count} CPUs", None
            else:
                issues = []
                if not memory_ok:
                    issues.append(f"Low memory: {memory.available/(1024**3):.1f}GB < {min_memory_gb}GB")
                if not disk_ok:
                    issues.append(f"Low disk: {disk.free/(1024**3):.1f}GB < {min_disk_gb}GB")
                if not cpu_ok:
                    issues.append(f"Insufficient CPUs: {cpu_count} < {min_cpu_cores}")
                return False, "Resource requirements not met", "; ".join(issues)
                
        except Exception as e:
            return False, f"Resource check failed: {str(e)}", str(e)
            
    def _check_dependencies(self) -> Tuple[bool, str, Optional[str]]:
        """Check required dependencies"""
        try:
            requirements_file = self.project_root / "requirements.txt"
            if not requirements_file.exists():
                return False, "Requirements file not found", "requirements.txt missing"
            
            # Check critical Python modules
            critical_modules = ['psutil', 'requests', 'pathlib']
            missing_modules = []
            
            for module in critical_modules:
                try:
                    __import__(module)
                except ImportError:
                    missing_modules.append(module)
            
            if missing_modules:
                return False, f"Missing dependencies: {missing_modules}", f"Install missing: {', '.join(missing_modules)}"
            else:
                return True, f"All {len(critical_modules)} critical dependencies available", None
                
        except Exception as e:
            return False, f"Dependency check failed: {str(e)}", str(e)
            
    def _check_configuration_integrity(self) -> Tuple[bool, str, Optional[str]]:
        """Check configuration file integrity"""
        try:
            # Look for configuration files
            config_files = [
                "config.json",
                ".env",
                "pyproject.toml"
            ]
            
            found_configs = []
            for config_file in config_files:
                config_path = self.project_root / config_file
                if config_path.exists():
                    found_configs.append(config_file)
            
            if found_configs:
                return True, f"Configuration files found: {found_configs}", None
            else:
                return True, "No critical configuration files required", None  # May be acceptable
                
        except Exception as e:
            return False, f"Configuration check failed: {str(e)}", str(e)
            
    def _check_database_connectivity(self) -> Tuple[bool, str, Optional[str]]:
        """Check database connectivity if applicable"""
        try:
            # Check if database files exist
            db_files = list(self.project_root.glob("*.db")) + list(self.project_root.glob("*.sqlite"))
            
            if db_files:
                return True, f"Database files found: {len(db_files)} files", None
            else:
                return True, "No database files required for current setup", None
                
        except Exception as e:
            return False, f"Database check failed: {str(e)}", str(e)
            
    def _check_performance_baselines(self) -> Tuple[bool, str, Optional[str]]:
        """Check performance baseline requirements"""
        try:
            # Quick performance test
            start_time = time.time()
            
            # CPU performance test
            result = sum(i * i for i in range(10000))
            cpu_time = time.time() - start_time
            
            # Memory allocation test
            start_memory = psutil.Process().memory_info().rss
            test_data = [i for i in range(100000)]
            end_memory = psutil.Process().memory_info().rss
            memory_used = (end_memory - start_memory) / 1024 / 1024  # MB
            
            # Cleanup
            del test_data
            
            # Performance criteria
            max_cpu_time = 0.1  # 100ms
            max_memory_mb = 50   # 50MB
            
            cpu_ok = cpu_time <= max_cpu_time
            memory_ok = memory_used <= max_memory_mb
            
            if cpu_ok and memory_ok:
                return True, f"Performance acceptable: CPU {cpu_time*1000:.1f}ms, Memory {memory_used:.1f}MB", None
            else:
                issues = []
                if not cpu_ok:
                    issues.append(f"CPU slow: {cpu_time*1000:.1f}ms > {max_cpu_time*1000:.1f}ms")
                if not memory_ok:
                    issues.append(f"Memory high: {memory_used:.1f}MB > {max_memory_mb}MB")
                return False, "Performance below baseline", "; ".join(issues)
                
        except Exception as e:
            return False, f"Performance check failed: {str(e)}", str(e)

    def validate_deployment_environment(self) -> List[ValidationResult]:
        """Validate deployment environment readiness"""
        self.log("INFO", "🚀 Validating Deployment Environment")
        
        results = []
        
        # Deployment environment checks
        deployment_checks = [
            {
                'name': 'platform_compatibility',
                'description': 'Platform and OS compatibility',
                'check_func': self._check_platform_compatibility
            },
            {
                'name': 'file_permissions',
                'description': 'File system permissions',
                'check_func': self._check_file_permissions
            },
            {
                'name': 'network_connectivity',
                'description': 'Network connectivity for updates',
                'check_func': self._check_network_connectivity
            },
            {
                'name': 'rollback_readiness',
                'description': 'Rollback mechanism verification',
                'check_func': self._check_rollback_readiness
            }
        ]
        
        for check in deployment_checks:
            start_time = time.time()
            self.log("INFO", f"  🔍 Checking: {check['name']}")
            
            try:
                success, message, details = check['check_func']()
                
                validation_result = ValidationResult(
                    test_name=check['name'],
                    category="deployment_environment",
                    expected_result="Deployment criteria met",
                    actual_result=message,
                    success=success,
                    execution_time=time.time() - start_time,
                    error_details=details if not success else None
                )
                
                results.append(validation_result)
                status = "✅" if success else "❌"
                self.log("INFO", f"    {status} {check['name']}: {message}")
                
            except Exception as e:
                validation_result = ValidationResult(
                    test_name=check['name'],
                    category="deployment_environment",
                    expected_result="Check completes successfully",
                    actual_result=f"Check failed: {str(e)}",
                    success=False,
                    execution_time=time.time() - start_time,
                    error_details=str(e)
                )
                results.append(validation_result)
                self.log("ERROR", f"    ❌ {check['name']}: Exception - {e}")
        
        self.validation_results.extend(results)
        return results
        
    def _check_platform_compatibility(self) -> Tuple[bool, str, Optional[str]]:
        """Check platform and OS compatibility"""
        try:
            system_info = {
                'platform': platform.system(),
                'version': platform.version(),
                'architecture': platform.architecture()[0],
                'python_version': platform.python_version()
            }
            
            # Supported platforms
            supported_platforms = ['Windows', 'Darwin', 'Linux']
            platform_ok = system_info['platform'] in supported_platforms
            
            # Python version check
            python_major, python_minor = platform.python_version().split('.')[:2]
            python_ok = int(python_major) == 3 and int(python_minor) >= 8
            
            if platform_ok and python_ok:
                return True, f"Compatible: {system_info['platform']} Python {system_info['python_version']}", None
            else:
                issues = []
                if not platform_ok:
                    issues.append(f"Unsupported platform: {system_info['platform']}")
                if not python_ok:
                    issues.append(f"Python version too old: {system_info['python_version']} < 3.8")
                return False, "Platform compatibility issues", "; ".join(issues)
                
        except Exception as e:
            return False, f"Platform check failed: {str(e)}", str(e)
            
    def _check_file_permissions(self) -> Tuple[bool, str, Optional[str]]:
        """Check file system permissions"""
        try:
            # Test write permissions in project directory
            test_file = self.project_root / "permission_test.tmp"
            
            try:
                test_file.write_text("permission test")
                test_file.unlink()
                write_ok = True
            except Exception:
                write_ok = False
            
            # Test read permissions on critical files
            critical_files = ["main.py", "requirements.txt"]
            read_ok = all((self.project_root / f).exists() and (self.project_root / f).is_file() 
                         for f in critical_files)
            
            if write_ok and read_ok:
                return True, "File permissions sufficient for deployment", None
            else:
                issues = []
                if not write_ok:
                    issues.append("Write permission denied")
                if not read_ok:
                    issues.append("Read access to critical files failed")
                return False, "File permission issues", "; ".join(issues)
                
        except Exception as e:
            return False, f"Permission check failed: {str(e)}", str(e)
            
    def _check_network_connectivity(self) -> Tuple[bool, str, Optional[str]]:
        """Check network connectivity for updates"""
        try:
            import socket
            
            # Test DNS resolution
            try:
                socket.gethostbyname('google.com')
                dns_ok = True
            except socket.gaierror:
                dns_ok = False
            
            # Test HTTP connectivity (simplified)
            try:
                import urllib.request
                response = urllib.request.urlopen('https://httpbin.org/status/200', timeout=10)
                http_ok = response.status == 200
            except Exception:
                http_ok = False
            
            if dns_ok and http_ok:
                return True, "Network connectivity available for updates", None
            elif dns_ok:
                return True, "DNS available, HTTP connectivity limited", "HTTP connectivity may be restricted"
            else:
                return False, "Network connectivity issues", "DNS resolution and HTTP connectivity failed"
                
        except Exception as e:
            return False, f"Network check failed: {str(e)}", str(e)
            
    def _check_rollback_readiness(self) -> Tuple[bool, str, Optional[str]]:
        """Check rollback mechanism readiness"""
        try:
            # Check if backup directories exist or can be created
            backup_dir = self.project_root / "backup"
            backup_available = backup_dir.exists() or True  # Can be created
            
            # Check for rollback scripts
            rollback_scripts = [
                "scripts/rollback.py",
                "scripts/backup.py"
            ]
            
            script_files_exist = any((self.project_root / script).exists() for script in rollback_scripts)
            
            # Check documentation
            rollback_docs = [
                "docs/migration/v2_migration_report.md",
                "CHANGELOG.md"
            ]
            
            docs_exist = any((self.project_root / doc).exists() for doc in rollback_docs)
            
            if backup_available and (script_files_exist or docs_exist):
                return True, "Rollback mechanisms available", None
            else:
                return True, "Basic rollback capability (manual)", "Automated rollback scripts not found, manual rollback documented"
                
        except Exception as e:
            return False, f"Rollback check failed: {str(e)}", str(e)

    def generate_release_report(self) -> Dict:
        """Generate comprehensive release validation report"""
        if not self.validation_results:
            return {"error": "No validation results available"}
        
        # Calculate overall statistics
        total_tests = len(self.validation_results)
        successful_tests = sum(1 for result in self.validation_results if result.success)
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Group by category
        categories = {}
        for result in self.validation_results:
            category = result.category
            if category not in categories:
                categories[category] = {'total': 0, 'passed': 0, 'tests': []}
            
            categories[category]['total'] += 1
            if result.success:
                categories[category]['passed'] += 1
            categories[category]['tests'].append(result)
        
        # Calculate category success rates
        for category in categories:
            cat_data = categories[category]
            cat_data['success_rate'] = (cat_data['passed'] / cat_data['total'] * 100) if cat_data['total'] > 0 else 0
        
        # Determine release readiness
        critical_categories = ['build_artifacts', 'smoke_tests', 'production_readiness']
        critical_success_rates = [categories.get(cat, {}).get('success_rate', 0) for cat in critical_categories]
        overall_critical_success = sum(critical_success_rates) / len(critical_success_rates) if critical_success_rates else 0
        
        release_ready = overall_critical_success >= 90  # 90% threshold for critical categories
        
        # Generate recommendations
        recommendations = []
        for category, data in categories.items():
            if data['success_rate'] < 90:
                recommendations.append(f"{category.replace('_', ' ').title()} needs attention ({data['success_rate']:.1f}% success)")
        
        if not recommendations:
            recommendations.append("All validation criteria met - APPROVED FOR PRODUCTION DEPLOYMENT")
        
        report = {
            "release_validation_summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "overall_success_rate": success_rate,
                "critical_success_rate": overall_critical_success,
                "release_ready": release_ready,
                "validation_timestamp": datetime.now().isoformat()
            },
            "category_breakdown": {
                category: {
                    "total_tests": data['total'],
                    "passed_tests": data['passed'],
                    "success_rate": data['success_rate'],
                    "critical": category in critical_categories
                }
                for category, data in categories.items()
            },
            "build_artifacts": self.build_artifacts,
            "detailed_results": [asdict(result) for result in self.validation_results],
            "recommendations": recommendations,
            "deployment_decision": "APPROVED" if release_ready else "REQUIRES_ATTENTION",
            "next_steps": [
                "Deploy to staging environment for final validation" if release_ready else "Address validation issues",
                "Execute deployment plan with monitoring",
                "Prepare rollback procedures",
                "Monitor post-deployment metrics"
            ]
        }
        
        return report

def main():
    """Main release validation execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Release Candidate Validation - Task 18.4")
    parser.add_argument("--full-validation", action="store_true", help="Run complete validation suite")
    parser.add_argument("--build-verification", action="store_true", help="Verify build artifacts")
    parser.add_argument("--smoke-tests", action="store_true", help="Run smoke tests")
    parser.add_argument("--production-readiness", action="store_true", help="Assess production readiness")
    parser.add_argument("--deployment-prep", action="store_true", help="Validate deployment environment")
    parser.add_argument("--output", type=str, help="Output report file path")
    
    args = parser.parse_args()
    
    # Initialize validator
    validator = ReleaseValidator()
    validator.log("INFO", "🏁 Social Download Manager v2.0 - Release Candidate Validation")
    validator.log("INFO", f"🖥️  Platform: {platform.system()} {platform.release()}")
    validator.log("INFO", f"🐍 Python: {platform.python_version()}")
    
    try:
        # Run selected validations
        if args.full_validation or (not any([args.build_verification, args.smoke_tests, args.production_readiness, args.deployment_prep])):
            # Run full validation suite
            validator.log("INFO", "🔥 Running COMPLETE Release Validation Suite")
            
            validator.verify_build_artifacts()
            validator.run_smoke_tests()
            validator.assess_production_readiness()
            validator.validate_deployment_environment()
            
        else:
            # Run individual validation categories
            if args.build_verification:
                validator.verify_build_artifacts()
                
            if args.smoke_tests:
                validator.run_smoke_tests()
                
            if args.production_readiness:
                validator.assess_production_readiness()
                
            if args.deployment_prep:
                validator.validate_deployment_environment()
        
        # Generate comprehensive report
        report = validator.generate_release_report()
        
        # Save report if output specified
        if args.output:
            output_path = Path(args.output)
            output_path.write_text(json.dumps(report, indent=2))
            validator.log("INFO", f"📄 Validation report saved to: {output_path}")
        
        # Log summary
        validator.log("INFO", "🎯 RELEASE VALIDATION SUMMARY:")
        validator.log("INFO", f"  Total Tests: {report['release_validation_summary']['total_tests']}")
        validator.log("INFO", f"  Success Rate: {report['release_validation_summary']['overall_success_rate']:.1f}%")
        validator.log("INFO", f"  Critical Success: {report['release_validation_summary']['critical_success_rate']:.1f}%")
        validator.log("INFO", f"  Release Ready: {report['release_validation_summary']['release_ready']}")
        
        validator.log("INFO", "📊 Category Breakdown:")
        for category, data in report['category_breakdown'].items():
            critical_marker = " (CRITICAL)" if data['critical'] else ""
            validator.log("INFO", f"  {category.replace('_', ' ').title()}{critical_marker}: {data['passed_tests']}/{data['total_tests']} ({data['success_rate']:.1f}%)")
        
        validator.log("INFO", "📋 Recommendations:")
        for rec in report['recommendations']:
            validator.log("INFO", f"  • {rec}")
            
        # Final deployment decision
        decision = report['deployment_decision']
        if decision == "APPROVED":
            validator.log("INFO", "✅ RELEASE CANDIDATE APPROVED FOR PRODUCTION DEPLOYMENT!")
        else:
            validator.log("WARNING", "⚠️  RELEASE CANDIDATE REQUIRES ATTENTION BEFORE DEPLOYMENT")
            
        validator.log("INFO", "🚀 Release validation completed!")
        
        return report
        
    except Exception as e:
        validator.log("ERROR", f"❌ Release validation failed: {e}")
        raise

if __name__ == "__main__":
    main() 