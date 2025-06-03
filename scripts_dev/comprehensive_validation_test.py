#!/usr/bin/env python3
"""
Comprehensive Validation Test - Task 14.3 Demo

This script demonstrates the migration success criteria and validation framework
by testing it against all available test datasets.

Author: Task Master AI
Date: 2025-01-XX
"""

import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.migration_success_criteria import MigrationSuccessCriteria

def run_comprehensive_validation_demo():
    """Run comprehensive validation demo across all test datasets"""
    print("🎯 COMPREHENSIVE MIGRATION VALIDATION DEMO")
    print("=" * 60)
    
    criteria_framework = MigrationSuccessCriteria()
    test_datasets_dir = Path("test_datasets")
    
    if not test_datasets_dir.exists():
        print("❌ test_datasets/ directory not found")
        return 1
    
    test_files = sorted(list(test_datasets_dir.glob("*.db")))
    if not test_files:
        print("❌ No test datasets found")
        return 1
    
    print(f"📊 Found {len(test_files)} test datasets for validation")
    print("🔄 Running validation across all datasets...\n")
    
    results_summary = []
    
    for i, test_dataset in enumerate(test_files, 1):
        print(f"[{i}/{len(test_files)}] Validating: {test_dataset.name}")
        
        try:
            report = criteria_framework.validate_migration(test_dataset)
            
            results_summary.append({
                'dataset': test_dataset.name,
                'status': report.overall_status,
                'score': report.overall_score,
                'critical_failures': report.critical_failures,
                'high_warnings': report.high_warnings
            })
            
            # Quick status summary
            status_icon = "✅" if report.overall_status == "SUCCESS" else \
                         "⚠️" if "WARNING" in report.overall_status else "❌"
            print(f"   {status_icon} Status: {report.overall_status} | Score: {report.overall_score:.1%}")
            
        except Exception as e:
            print(f"   ❌ Validation failed: {e}")
            results_summary.append({
                'dataset': test_dataset.name,
                'status': 'ERROR',
                'score': 0.0,
                'critical_failures': 1,
                'high_warnings': 0
            })
        
        print()  # Empty line for readability
    
    # Generate overall summary
    print("\n" + "="*60)
    print("📈 COMPREHENSIVE VALIDATION SUMMARY")
    print("="*60)
    
    total_datasets = len(results_summary)
    successful_validations = len([r for r in results_summary if r['status'] == 'SUCCESS'])
    warning_validations = len([r for r in results_summary if 'WARNING' in r['status']])
    failed_validations = len([r for r in results_summary if r['status'] in ['CRITICAL_FAILURE', 'FAILURE', 'ERROR']])
    
    average_score = sum(r['score'] for r in results_summary) / len(results_summary)
    total_critical_failures = sum(r['critical_failures'] for r in results_summary)
    total_high_warnings = sum(r['high_warnings'] for r in results_summary)
    
    print(f"📊 Dataset Coverage: {total_datasets} datasets tested")
    print(f"✅ Successful: {successful_validations} ({successful_validations/total_datasets:.1%})")
    print(f"⚠️  Warnings: {warning_validations} ({warning_validations/total_datasets:.1%})")
    print(f"❌ Failed: {failed_validations} ({failed_validations/total_datasets:.1%})")
    print(f"📈 Average Score: {average_score:.1%}")
    print(f"🚨 Total Critical Failures: {total_critical_failures}")
    print(f"⚠️  Total High Warnings: {total_high_warnings}")
    
    print(f"\n📝 Detailed Reports: scripts/validation_reports/")
    
    # Dataset-specific insights
    print(f"\n🔍 DATASET-SPECIFIC INSIGHTS:")
    print("-" * 40)
    
    for result in sorted(results_summary, key=lambda x: x['score'], reverse=True):
        status_icon = "✅" if result['status'] == "SUCCESS" else \
                     "⚠️" if "WARNING" in result['status'] else "❌"
        dataset_name = result['dataset'].replace('.db', '')
        print(f"{status_icon} {dataset_name:20} | {result['score']:6.1%} | {result['status']}")
    
    print(f"\n🎯 FRAMEWORK CAPABILITIES DEMONSTRATED:")
    print("-" * 50)
    print("✅ Data Integrity Validation (completeness, accuracy, referential)")
    print("✅ Schema Compliance Checking (structure, constraints)")
    print("✅ Functional Equivalence Testing (query results, API compatibility)")
    print("✅ Performance Benchmarking (query speed, resource usage)")
    print("✅ User Experience Validation (uptime, availability)")
    print("✅ Safety & Compliance (backup verification, rollback capability)")
    print("✅ Comprehensive Reporting (JSON + human-readable summaries)")
    print("✅ Severity-based Risk Assessment (Critical, High, Medium, Low)")
    print("✅ Actionable Recommendations Generation")
    
    # Return appropriate exit code
    if failed_validations == 0:
        print(f"\n🎉 ALL VALIDATIONS COMPLETED SUCCESSFULLY!")
        return 0
    elif successful_validations > failed_validations:
        print(f"\n⚠️  VALIDATION COMPLETED WITH SOME ISSUES")
        return 1
    else:
        print(f"\n❌ VALIDATION COMPLETED WITH SIGNIFICANT ISSUES")
        return 2

if __name__ == "__main__":
    sys.exit(run_comprehensive_validation_demo()) 