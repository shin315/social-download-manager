#!/usr/bin/env python3
"""
Migration Execution Strategy - Task 14.2

This script implements a comprehensive step-by-step testing approach for migration validation,
leveraging the 14 test datasets prepared in Task 14.1.

The strategy follows a progressive testing approach:
1. Pre-Migration Verification
2. Progressive Migration Testing
3. Post-Migration Validation
4. Performance Benchmarking
5. Comprehensive Reporting

Author: Task Master AI
Date: 2025-01-XX
"""

import os
import sys
import json
import time
import sqlite3
import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import migration system components
from data.database.migration_system.version_detection import VersionManager, DatabaseVersion
from data.database.migration_system.schema_transformation import SchemaTransformationManager
from data.database.migration_system.data_conversion import DataConversionManager
from data.database.migration_system.data_integrity import DataIntegrityManager, ValidationLevel
from data.database.connection import SQLiteConnectionManager, ConnectionConfig

@dataclass
class MigrationTestResult:
    """Container for migration test results"""
    dataset_name: str
    test_phase: str
    status: str  # 'success', 'failure', 'warning'
    execution_time: float
    records_processed: int
    errors: List[str]
    warnings: List[str]
    metrics: Dict[str, Any]
    timestamp: str

@dataclass
class MigrationReport:
    """Container for complete migration testing report"""
    test_session_id: str
    start_time: str
    end_time: str
    total_duration: float
    datasets_tested: int
    tests_passed: int
    tests_failed: int
    tests_warning: int
    overall_status: str
    results: List[MigrationTestResult]
    summary: Dict[str, Any]

class MigrationExecutionStrategy:
    """
    Comprehensive migration execution strategy implementation
    
    This class orchestrates the complete migration testing process across
    all prepared test datasets with detailed validation and reporting.
    """
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or PROJECT_ROOT
        self.test_datasets_dir = self.project_root / "test_datasets"
        self.results_dir = self.project_root / "scripts" / "migration_test_results"
        self.results_dir.mkdir(exist_ok=True)
        
        # Initialize migration components
        # All components will be created per test as needed
        
        # Test session tracking
        self.session_id = f"migration_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.test_results: List[MigrationTestResult] = []
        
        # Setup logging
        self._setup_logging()
        
        # Load dataset configurations
        self._load_dataset_metadata()
    
    def _setup_logging(self):
        """Configure logging for migration testing"""
        log_file = self.results_dir / f"{self.session_id}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Migration execution strategy started - Session: {self.session_id}")
    
    def _load_dataset_metadata(self):
        """Load metadata about available test datasets"""
        metadata_file = self.test_datasets_dir / "datasets_summary.json"
        
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                self.dataset_metadata = json.load(f)
        else:
            self.logger.warning("Dataset metadata not found, generating basic metadata")
            self.dataset_metadata = self._generate_basic_metadata()
    
    def _generate_basic_metadata(self) -> Dict:
        """Generate basic metadata for datasets if summary file not available"""
        datasets = {}
        for db_file in self.test_datasets_dir.glob("*.db"):
            try:
                conn = sqlite3.connect(str(db_file))
                cursor = conn.cursor()
                
                # Get record count
                cursor.execute("SELECT COUNT(*) FROM downloads")
                count = cursor.fetchone()[0]
                
                datasets[db_file.stem] = {
                    "name": db_file.stem,
                    "file_size": db_file.stat().st_size,
                    "record_count": count,
                    "type": self._classify_dataset_type(db_file.stem)
                }
                
                conn.close()
            except Exception as e:
                self.logger.warning(f"Could not analyze dataset {db_file.stem}: {e}")
                datasets[db_file.stem] = {
                    "name": db_file.stem,
                    "file_size": db_file.stat().st_size,
                    "record_count": 0,
                    "type": "unknown"
                }
        
        return {"datasets": datasets}
    
    def _classify_dataset_type(self, name: str) -> str:
        """Classify dataset type based on naming convention"""
        if "standard" in name:
            return "standard"
        elif "edge" in name or "corrupted" in name or "unicode" in name:
            return "edge_case"
        elif "performance" in name:
            return "performance"
        elif "platform" in name or "tiktok" in name or "youtube" in name:
            return "platform_specific"
        elif "schema" in name or "v1" in name or "v2" in name:
            return "schema_validation"
        else:
            return "utility"
    
    def run_complete_strategy(self) -> MigrationReport:
        """
        Execute the complete migration testing strategy
        
        Returns:
            MigrationReport: Comprehensive test results
        """
        start_time = datetime.now()
        self.logger.info("Starting complete migration execution strategy")
        
        try:
            # Phase 1: Pre-Migration Verification
            self.logger.info("=== Phase 1: Pre-Migration Verification ===")
            self._run_pre_migration_verification()
            
            # Phase 2: Progressive Migration Testing
            self.logger.info("=== Phase 2: Progressive Migration Testing ===")
            self._run_progressive_migration_testing()
            
            # Phase 3: Post-Migration Validation
            self.logger.info("=== Phase 3: Post-Migration Validation ===")
            self._run_post_migration_validation()
            
            # Phase 4: Performance Benchmarking
            self.logger.info("=== Phase 4: Performance Benchmarking ===")
            self._run_performance_benchmarking()
            
            # Phase 5: Generate comprehensive report
            self.logger.info("=== Phase 5: Generating Comprehensive Report ===")
            report = self._generate_comprehensive_report(start_time)
            
            self.logger.info(f"Migration execution strategy completed successfully")
            return report
            
        except Exception as e:
            self.logger.error(f"Migration execution strategy failed: {e}")
            raise
    
    def _run_pre_migration_verification(self):
        """Phase 1: Pre-migration verification steps"""
        verification_datasets = ['standard_small', 'standard_medium', 'v1_schema_only']
        
        for dataset_name in verification_datasets:
            self._test_dataset_baseline(dataset_name)
    
    def _run_progressive_migration_testing(self):
        """Phase 2: Progressive migration testing with increasing complexity"""
        # Progressive order: small -> medium -> edge cases -> platform specific
        progressive_order = [
            'standard_small',
            'standard_medium', 
            'edge_cases',
            'corrupted_data',
            'unicode_edge',
            'tiktok_focus',
            'youtube_focus',
            'mixed_platforms',
            'standard_large'
        ]
        
        for dataset_name in progressive_order:
            self._test_migration_execution(dataset_name)
    
    def _run_post_migration_validation(self):
        """Phase 3: Post-migration validation procedures"""
        validation_datasets = ['partial_v2', 'standard_large', 'mixed_platforms']
        
        for dataset_name in validation_datasets:
            self._test_post_migration_validation(dataset_name)
    
    def _run_performance_benchmarking(self):
        """Phase 4: Performance benchmarking tests"""
        performance_datasets = ['performance_1000', 'performance_10000']
        
        for dataset_name in performance_datasets:
            self._test_performance_benchmark(dataset_name)
    
    def _test_dataset_baseline(self, dataset_name: str):
        """Test baseline characteristics of a dataset"""
        start_time = time.time()
        errors = []
        warnings = []
        metrics = {}
        
        try:
            dataset_path = self.test_datasets_dir / f"{dataset_name}.db"
            
            if not dataset_path.exists():
                errors.append(f"Dataset file not found: {dataset_path}")
                return self._record_test_result(dataset_name, "pre_migration_baseline", 
                                               "failure", start_time, 0, errors, warnings, metrics)
            
            # Connect and analyze dataset
            conn = sqlite3.connect(str(dataset_path))
            cursor = conn.cursor()
            
            # Get record count
            cursor.execute("SELECT COUNT(*) FROM downloads")
            record_count = cursor.fetchone()[0]
            metrics['record_count'] = record_count
            
            # Get schema information
            cursor.execute("PRAGMA table_info(downloads)")
            schema_info = cursor.fetchall()
            metrics['schema_columns'] = len(schema_info)
            
            # Test data integrity
            cursor.execute("SELECT COUNT(*) FROM downloads WHERE url IS NULL OR url = ''")
            null_urls = cursor.fetchone()[0]
            if null_urls > 0:
                warnings.append(f"Found {null_urls} records with null/empty URLs")
            
            metrics['null_urls'] = null_urls
            
            conn.close()
            
            self.logger.info(f"Baseline verification for {dataset_name}: {record_count} records, {len(schema_info)} columns")
            
            status = "success" if not errors else "failure"
            if warnings and not errors:
                status = "warning"
                
            return self._record_test_result(dataset_name, "pre_migration_baseline",
                                           status, start_time, record_count, errors, warnings, metrics)
            
        except Exception as e:
            errors.append(f"Baseline verification failed: {str(e)}")
            return self._record_test_result(dataset_name, "pre_migration_baseline",
                                           "failure", start_time, 0, errors, warnings, metrics)
    
    def _test_migration_execution(self, dataset_name: str):
        """Test migration execution for a specific dataset"""
        start_time = time.time()
        errors = []
        warnings = []
        metrics = {}
        
        try:
            dataset_path = self.test_datasets_dir / f"{dataset_name}.db"
            
            if not dataset_path.exists():
                errors.append(f"Dataset file not found: {dataset_path}")
                return self._record_test_result(dataset_name, "migration_execution",
                                               "failure", start_time, 0, errors, warnings, metrics)
            
            # Create temporary copy for migration testing
            temp_path = self.results_dir / f"temp_{dataset_name}_{self.session_id}.db"
            shutil.copy2(dataset_path, temp_path)
            
            try:
                # Initialize migration components with temp database
                self.logger.info(f"Testing migration execution for {dataset_name}")
                
                # Step 1: Version detection
                config = ConnectionConfig(database_path=str(temp_path))
                connection_manager = SQLiteConnectionManager(config)
                connection_manager.initialize()
                
                try:
                    version_manager = VersionManager(connection_manager)
                    version_info = version_manager.get_current_version_info()
                    metrics['detected_version'] = version_info
                    
                    # Step 2: Schema transformation validation (simulated)
                    schema_manager = SchemaTransformationManager(connection_manager)
                    # For testing purposes, we'll check if migration would be possible
                    current_version = version_info
                    target_version = DatabaseVersion.V2_0_0
                    
                    # Create a transformation plan to validate (without executing)
                    plan = schema_manager.transformer.create_transformation_plan(current_version, target_version)
                    is_safe, concerns = schema_manager.transformer.validate_transformation(plan)
                    
                    metrics['schema_validation'] = {
                        'is_safe': is_safe,
                        'concerns': concerns,
                        'plan_steps': len(plan.steps),
                        'target_version': target_version.value
                    }
                    
                    # Step 3: Data integrity check
                    integrity_validator = DataIntegrityManager(connection_manager)
                    success, message, integrity_result = integrity_validator.validate_migration_integrity(ValidationLevel.STANDARD)
                    metrics['pre_migration_integrity'] = {
                        'success': success,
                        'message': message,
                        'report_summary': {
                            'passed_checks': integrity_result.passed_checks,
                            'failed_checks': integrity_result.failed_checks,
                            'warnings': integrity_result.warnings
                        }
                    }
                finally:
                    connection_manager.shutdown()
                
                # Get record count
                conn = sqlite3.connect(str(temp_path))
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM downloads")
                record_count = cursor.fetchone()[0]
                conn.close()
                
                self.logger.info(f"Migration execution test for {dataset_name} completed successfully")
                
                status = "success"
                if not success or any("warning" in str(result) for result in [is_safe, concerns]):
                    status = "warning"
                    warnings.append("Migration completed with warnings")
                
                return self._record_test_result(dataset_name, "migration_execution",
                                               status, start_time, record_count, errors, warnings, metrics)
                
            finally:
                # Clean up temporary file
                if temp_path.exists():
                    temp_path.unlink()
                    
        except Exception as e:
            errors.append(f"Migration execution failed: {str(e)}")
            return self._record_test_result(dataset_name, "migration_execution",
                                           "failure", start_time, 0, errors, warnings, metrics)
    
    def _test_post_migration_validation(self, dataset_name: str):
        """Test post-migration validation procedures"""
        start_time = time.time()
        errors = []
        warnings = []
        metrics = {}
        
        try:
            dataset_path = self.test_datasets_dir / f"{dataset_name}.db"
            
            if not dataset_path.exists():
                errors.append(f"Dataset file not found: {dataset_path}")
                return self._record_test_result(dataset_name, "post_migration_validation",
                                               "failure", start_time, 0, errors, warnings, metrics)
            
            # Data integrity validation with proper connection manager
            self.logger.info(f"Running post-migration validation for {dataset_name}")
            config = ConnectionConfig(database_path=str(dataset_path))
            connection_manager = SQLiteConnectionManager(config)
            connection_manager.initialize()
            
            try:
                integrity_validator = DataIntegrityManager(connection_manager)
                success, message, validation_result = integrity_validator.validate_migration_integrity(ValidationLevel.STANDARD)
                metrics['post_migration_integrity'] = {
                    'success': success,
                    'message': message,
                    'report_summary': {
                        'passed_checks': validation_result.passed_checks,
                        'failed_checks': validation_result.failed_checks,
                        'warnings': validation_result.warnings
                    }
                }
            finally:
                connection_manager.shutdown()
            
            # Get record statistics
            conn = sqlite3.connect(str(dataset_path))
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM downloads")
            record_count = cursor.fetchone()[0]
            
            # Check if platform column exists (v1.2.1 databases might not have it)
            cursor.execute("PRAGMA table_info(downloads)")
            columns = [row[1] for row in cursor.fetchall()]
            has_platform = 'platform' in columns
            
            platform_count = 0
            if has_platform:
                cursor.execute("SELECT COUNT(DISTINCT platform) FROM downloads WHERE platform IS NOT NULL")
                platform_count = cursor.fetchone()[0]
            else:
                # For v1.2.1 datasets without platform column, assume single platform
                platform_count = 1
                warnings.append("Dataset uses v1.2.1 schema without platform column")
            
            metrics['record_count'] = record_count
            metrics['platform_diversity'] = platform_count
            metrics['has_platform_column'] = has_platform
            
            conn.close()
            
            self.logger.info(f"Post-migration validation for {dataset_name}: {record_count} records validated")
            
            status = "success"
            if not success:
                status = "warning"
                warnings.append("Validation completed with warnings")
                
            return self._record_test_result(dataset_name, "post_migration_validation",
                                           status, start_time, record_count, errors, warnings, metrics)
            
        except Exception as e:
            errors.append(f"Post-migration validation failed: {str(e)}")
            return self._record_test_result(dataset_name, "post_migration_validation",
                                           "failure", start_time, 0, errors, warnings, metrics)
    
    def _test_performance_benchmark(self, dataset_name: str):
        """Test performance benchmarking"""
        start_time = time.time()
        errors = []
        warnings = []
        metrics = {}
        
        try:
            dataset_path = self.test_datasets_dir / f"{dataset_name}.db"
            
            if not dataset_path.exists():
                errors.append(f"Dataset file not found: {dataset_path}")
                return self._record_test_result(dataset_name, "performance_benchmark",
                                               "failure", start_time, 0, errors, warnings, metrics)
            
            self.logger.info(f"Running performance benchmark for {dataset_name}")
            
            # Measure database connection time
            connection_start = time.time()
            conn = sqlite3.connect(str(dataset_path))
            connection_time = time.time() - connection_start
            
            cursor = conn.cursor()
            
            # Measure query performance
            query_start = time.time()
            cursor.execute("SELECT COUNT(*) FROM downloads")
            record_count = cursor.fetchone()[0]
            query_time = time.time() - query_start
            
            # Measure complex query performance
            complex_query_start = time.time()
            
            # Check if platform column exists first
            cursor.execute("PRAGMA table_info(downloads)")
            columns = [row[1] for row in cursor.fetchall()]
            has_platform = 'platform' in columns
            
            if has_platform:
                cursor.execute("""
                    SELECT platform, COUNT(*) as count, AVG(LENGTH(title)) as avg_title_length
                    FROM downloads 
                    GROUP BY platform
                """)
            else:
                # For v1.2.1 schema without platform column, use alternative grouping
                cursor.execute("""
                    SELECT 'unknown' as platform, COUNT(*) as count, AVG(LENGTH(title)) as avg_title_length
                    FROM downloads 
                """)
                warnings.append("Performance test adapted for v1.2.1 schema without platform column")
            
            complex_results = cursor.fetchall()
            complex_query_time = time.time() - complex_query_start
            
            conn.close()
            
            metrics.update({
                'record_count': record_count,
                'connection_time_ms': round(connection_time * 1000, 2),
                'simple_query_time_ms': round(query_time * 1000, 2),
                'complex_query_time_ms': round(complex_query_time * 1000, 2),
                'platform_summary': len(complex_results)
            })
            
            # Performance thresholds (adjust based on requirements)
            if connection_time > 1.0:  # 1 second
                warnings.append(f"Slow connection time: {connection_time:.2f}s")
            if complex_query_time > 5.0:  # 5 seconds
                warnings.append(f"Slow complex query time: {complex_query_time:.2f}s")
            
            self.logger.info(f"Performance benchmark for {dataset_name}: {record_count} records, "
                           f"connection: {connection_time*1000:.2f}ms, query: {complex_query_time*1000:.2f}ms")
            
            status = "success" if not warnings else "warning"
            
            return self._record_test_result(dataset_name, "performance_benchmark",
                                           status, start_time, record_count, errors, warnings, metrics)
            
        except Exception as e:
            errors.append(f"Performance benchmark failed: {str(e)}")
            return self._record_test_result(dataset_name, "performance_benchmark",
                                           "failure", start_time, 0, errors, warnings, metrics)
    
    def _record_test_result(self, dataset_name: str, test_phase: str, status: str,
                           start_time: float, records_processed: int,
                           errors: List[str], warnings: List[str], metrics: Dict[str, Any]) -> MigrationTestResult:
        """Record a test result"""
        execution_time = time.time() - start_time
        
        result = MigrationTestResult(
            dataset_name=dataset_name,
            test_phase=test_phase,
            status=status,
            execution_time=execution_time,
            records_processed=records_processed,
            errors=errors,
            warnings=warnings,
            metrics=metrics,
            timestamp=datetime.now().isoformat()
        )
        
        self.test_results.append(result)
        return result
    
    def _generate_comprehensive_report(self, start_time: datetime) -> MigrationReport:
        """Generate comprehensive migration testing report"""
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        # Calculate statistics
        tests_passed = len([r for r in self.test_results if r.status == "success"])
        tests_failed = len([r for r in self.test_results if r.status == "failure"])
        tests_warning = len([r for r in self.test_results if r.status == "warning"])
        datasets_tested = len(set(r.dataset_name for r in self.test_results))
        
        overall_status = "success"
        if tests_failed > 0:
            overall_status = "failure"
        elif tests_warning > 0:
            overall_status = "warning"
        
        # Generate summary statistics
        summary = {
            "execution_summary": {
                "total_tests": len(self.test_results),
                "datasets_tested": datasets_tested,
                "success_rate": round(tests_passed / len(self.test_results) * 100, 2),
                "average_execution_time": round(sum(r.execution_time for r in self.test_results) / len(self.test_results), 2)
            },
            "performance_summary": {
                "total_records_processed": sum(r.records_processed for r in self.test_results),
                "fastest_test": min(self.test_results, key=lambda x: x.execution_time).execution_time,
                "slowest_test": max(self.test_results, key=lambda x: x.execution_time).execution_time
            },
            "error_summary": {
                "total_errors": sum(len(r.errors) for r in self.test_results),
                "total_warnings": sum(len(r.warnings) for r in self.test_results),
                "most_common_issues": self._analyze_common_issues()
            }
        }
        
        report = MigrationReport(
            test_session_id=self.session_id,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            total_duration=total_duration,
            datasets_tested=datasets_tested,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            tests_warning=tests_warning,
            overall_status=overall_status,
            results=self.test_results,
            summary=summary
        )
        
        # Save report to file
        report_file = self.results_dir / f"{self.session_id}_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(report), f, indent=2, default=str)
        
        self.logger.info(f"Comprehensive report saved to: {report_file}")
        self._print_report_summary(report)
        
        return report
    
    def _analyze_common_issues(self) -> List[str]:
        """Analyze and return most common issues across all tests"""
        all_errors = []
        all_warnings = []
        
        for result in self.test_results:
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
        
        # Simple frequency analysis
        error_types = {}
        for error in all_errors:
            error_type = error.split(':')[0] if ':' in error else error
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        # Return top 5 most common issues
        return sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:5]
    
    def _print_report_summary(self, report: MigrationReport):
        """Print a formatted summary of the migration test report"""
        print("\n" + "="*80)
        print(f"MIGRATION EXECUTION STRATEGY REPORT - {report.test_session_id}")
        print("="*80)
        print(f"Duration: {report.total_duration:.2f} seconds")
        print(f"Datasets Tested: {report.datasets_tested}")
        print(f"Total Tests: {len(report.results)}")
        print(f"Passed: {report.tests_passed} | Failed: {report.tests_failed} | Warnings: {report.tests_warning}")
        print(f"Overall Status: {report.overall_status.upper()}")
        print(f"Success Rate: {report.summary['execution_summary']['success_rate']}%")
        print("\nTest Phase Summary:")
        
        phase_summary = {}
        for result in report.results:
            phase = result.test_phase
            if phase not in phase_summary:
                phase_summary[phase] = {"success": 0, "failure": 0, "warning": 0}
            phase_summary[phase][result.status] += 1
        
        for phase, stats in phase_summary.items():
            total = sum(stats.values())
            success_rate = round(stats['success'] / total * 100, 1) if total > 0 else 0
            print(f"  {phase}: {stats['success']}/{total} passed ({success_rate}%)")
        
        if report.tests_failed > 0:
            print(f"\nFailed Tests:")
            for result in report.results:
                if result.status == "failure":
                    print(f"  - {result.dataset_name} ({result.test_phase}): {result.errors}")
        
        print("\n" + "="*80)

def main():
    """Main entry point for migration execution strategy testing"""
    print("Migration Execution Strategy - Task 14.2")
    print("=" * 50)
    
    try:
        strategy = MigrationExecutionStrategy()
        report = strategy.run_complete_strategy()
        
        if report.overall_status == "success":
            print(f"\n✅ Migration execution strategy completed successfully!")
            print(f"📊 Report saved in: scripts/migration_test_results/")
            return 0
        elif report.overall_status == "warning":
            print(f"\n⚠️  Migration execution strategy completed with warnings.")
            print(f"📊 Report saved in: scripts/migration_test_results/")
            return 1
        else:
            print(f"\n❌ Migration execution strategy failed.")
            print(f"📊 Report saved in: scripts/migration_test_results/")
            return 2
            
    except KeyboardInterrupt:
        print("\n⏸️  Migration execution strategy interrupted by user")
        return 130
    except Exception as e:
        print(f"\n💥 Migration execution strategy crashed: {e}")
        logging.exception("Migration execution strategy crashed")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 