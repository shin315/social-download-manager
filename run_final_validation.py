#!/usr/bin/env python3
"""
Final Performance Validation Test Runner
=======================================

Comprehensive testing suite for Social Download Manager v2.0 final validation framework.
Tests all performance optimizations and generates comprehensive benchmark comparisons
against v1.2.1 baseline.

Usage:
    python run_final_validation.py [--mode=MODE] [--stress-level=LEVEL]

Modes:
    all         - Run complete validation suite (default)
    profiling   - Test application profiling validation only
    database    - Test database optimization validation only
    ui          - Test UI optimization validation only
    memory      - Test memory management validation only
    platform    - Test platform optimization validation only
    stress      - Test stress testing only
    integration - Test integration validation only
    demo        - Run interactive demonstration
"""

import os
import sys
import time
import asyncio
import argparse
from typing import Dict, List, Any

# Add scripts directory to path for imports
scripts_dir = os.path.join(os.path.dirname(__file__), 'scripts', 'performance')
sys.path.insert(0, scripts_dir)

try:
    from final_validation import (
        FinalValidationFramework, ValidationTestSuite, ValidationResult,
        BenchmarkComparison, FinalValidationReport
    )
except ImportError as e:
    print(f"❌ Error importing final validation framework: {e}")
    print("Please ensure all dependencies are installed and modules are available")
    sys.exit(1)

class FinalValidationTestRunner:
    """Comprehensive final validation test runner."""
    
    def __init__(self, stress_level: int = 3):
        self.stress_level = stress_level  # 1-5 scale
        self.results = {}
        
    async def test_profiling_validation(self) -> Dict[str, Any]:
        """Test application profiling validation."""
        print("\n📊 Phase 1: Application Profiling Validation")
        print("-" * 45)
        
        results = {"status": "PASSED", "details": {}, "errors": []}
        
        try:
            test_suite = ValidationTestSuite()
            test_suite.setup_test_environment()
            
            print(f"  Running application profiling validation...")
            start_time = time.time()
            
            validation_result = await test_suite.test_application_profiling_validation()
            
            duration = time.time() - start_time
            print(f"  Validation completed in {duration:.2f}s")
            print(f"  Status: {validation_result.status}")
            print(f"  Execution time: {validation_result.execution_time:.3f}s")
            print(f"  Memory usage: {validation_result.memory_usage_mb:.1f} MB")
            
            if validation_result.details:
                print(f"  Details:")
                for key, value in validation_result.details.items():
                    if isinstance(value, (int, float)):
                        print(f"    {key}: {value}")
                    elif isinstance(value, list) and len(value) <= 5:
                        print(f"    {key}: {value}")
            
            results["details"]["validation_result"] = {
                "status": validation_result.status,
                "execution_time": validation_result.execution_time,
                "memory_usage": validation_result.memory_usage_mb,
                "errors_count": len(validation_result.errors),
                "warnings_count": len(validation_result.warnings)
            }
            
            if validation_result.errors:
                results["errors"].extend(validation_result.errors)
                print(f"  ⚠️ Errors found: {len(validation_result.errors)}")
                for error in validation_result.errors[:3]:  # Show first 3
                    print(f"    - {error}")
            
            if validation_result.status != "PASSED":
                results["status"] = validation_result.status
            
            test_suite.cleanup_test_environment()
            print(f"✅ Application profiling validation completed")
            
        except Exception as e:
            results["status"] = "FAILED"
            results["errors"].append(str(e))
            print(f"❌ Application profiling validation failed: {e}")
        
        return results
    
    async def test_database_validation(self) -> Dict[str, Any]:
        """Test database optimization validation."""
        print("\n💾 Phase 2: Database Optimization Validation")
        print("-" * 43)
        
        results = {"status": "PASSED", "details": {}, "errors": []}
        
        try:
            test_suite = ValidationTestSuite()
            test_suite.setup_test_environment()
            
            print(f"  Running database optimization validation...")
            start_time = time.time()
            
            validation_result = await test_suite.test_database_optimization_validation()
            
            duration = time.time() - start_time
            print(f"  Validation completed in {duration:.2f}s")
            print(f"  Status: {validation_result.status}")
            
            if "database_operations" in validation_result.details:
                db_ops = validation_result.details["database_operations"]
                print(f"  Database operations tested: {len(db_ops)}")
                
                for op_name, metrics in db_ops.items():
                    if isinstance(metrics, dict) and "avg_time" in metrics:
                        print(f"    {op_name}: {metrics['avg_time']:.3f}s avg")
            
            results["details"]["validation_result"] = {
                "status": validation_result.status,
                "execution_time": validation_result.execution_time,
                "memory_usage": validation_result.memory_usage_mb,
                "operations_tested": len(validation_result.details.get("database_operations", {}))
            }
            
            if validation_result.errors:
                results["errors"].extend(validation_result.errors)
                results["status"] = "FAILED" if validation_result.status == "FAILED" else results["status"]
            
            test_suite.cleanup_test_environment()
            print(f"✅ Database optimization validation completed")
            
        except Exception as e:
            results["status"] = "FAILED"
            results["errors"].append(str(e))
            print(f"❌ Database optimization validation failed: {e}")
        
        return results
    
    async def test_ui_validation(self) -> Dict[str, Any]:
        """Test UI optimization validation."""
        print("\n🖥️ Phase 3: UI Optimization Validation")
        print("-" * 37)
        
        results = {"status": "PASSED", "details": {}, "errors": []}
        
        try:
            test_suite = ValidationTestSuite()
            test_suite.setup_test_environment()
            
            print(f"  Running UI optimization validation...")
            start_time = time.time()
            
            validation_result = await test_suite.test_ui_optimization_validation()
            
            duration = time.time() - start_time
            print(f"  Validation completed in {duration:.2f}s")
            print(f"  Status: {validation_result.status}")
            
            if "ui_components" in validation_result.details:
                ui_components = validation_result.details["ui_components"]
                print(f"  UI components tested: {len(ui_components)}")
                
                for comp_name, metrics in ui_components.items():
                    if isinstance(metrics, dict) and "render_time" in metrics:
                        print(f"    {comp_name}: {metrics['render_time']:.3f}s render")
            
            results["details"]["validation_result"] = {
                "status": validation_result.status,
                "execution_time": validation_result.execution_time,
                "memory_usage": validation_result.memory_usage_mb,
                "components_tested": len(validation_result.details.get("ui_components", {}))
            }
            
            if validation_result.errors:
                results["errors"].extend(validation_result.errors)
                if validation_result.status == "FAILED":
                    results["status"] = "FAILED"
            
            test_suite.cleanup_test_environment()
            print(f"✅ UI optimization validation completed")
            
        except Exception as e:
            results["status"] = "FAILED"
            results["errors"].append(str(e))
            print(f"❌ UI optimization validation failed: {e}")
        
        return results
    
    async def test_memory_validation(self) -> Dict[str, Any]:
        """Test memory management validation."""
        print("\n🧠 Phase 4: Memory Management Validation")
        print("-" * 40)
        
        results = {"status": "PASSED", "details": {}, "errors": []}
        
        try:
            test_suite = ValidationTestSuite()
            test_suite.setup_test_environment()
            
            print(f"  Running memory management validation...")
            start_time = time.time()
            
            validation_result = await test_suite.test_memory_management_validation()
            
            duration = time.time() - start_time
            print(f"  Validation completed in {duration:.2f}s")
            print(f"  Status: {validation_result.status}")
            
            if "memory_tests" in validation_result.details:
                mem_tests = validation_result.details["memory_tests"]
                print(f"  Memory tests performed: {len(mem_tests)}")
                
                for test_name, metrics in mem_tests.items():
                    if isinstance(metrics, dict) and "peak_memory_mb" in metrics:
                        print(f"    {test_name}: {metrics['peak_memory_mb']:.1f} MB peak")
            
            results["details"]["validation_result"] = {
                "status": validation_result.status,
                "execution_time": validation_result.execution_time,
                "memory_usage": validation_result.memory_usage_mb,
                "memory_tests": len(validation_result.details.get("memory_tests", {}))
            }
            
            if validation_result.errors:
                results["errors"].extend(validation_result.errors)
                if validation_result.status == "FAILED":
                    results["status"] = "FAILED"
            
            test_suite.cleanup_test_environment()
            print(f"✅ Memory management validation completed")
            
        except Exception as e:
            results["status"] = "FAILED"
            results["errors"].append(str(e))
            print(f"❌ Memory management validation failed: {e}")
        
        return results
    
    async def test_platform_validation(self) -> Dict[str, Any]:
        """Test platform optimization validation."""
        print("\n🚀 Phase 5: Platform Optimization Validation")
        print("-" * 43)
        
        results = {"status": "PASSED", "details": {}, "errors": []}
        
        try:
            test_suite = ValidationTestSuite()
            test_suite.setup_test_environment()
            
            print(f"  Running platform optimization validation...")
            start_time = time.time()
            
            validation_result = await test_suite.test_platform_optimization_validation()
            
            duration = time.time() - start_time
            print(f"  Validation completed in {duration:.2f}s")
            print(f"  Status: {validation_result.status}")
            
            if "platform_tests" in validation_result.details:
                platform_tests = validation_result.details["platform_tests"]
                print(f"  Platform tests performed: {len(platform_tests)}")
                
                for platform, metrics in platform_tests.items():
                    if isinstance(metrics, dict) and "processing_time" in metrics:
                        print(f"    {platform}: {metrics['processing_time']:.3f}s processing")
            
            results["details"]["validation_result"] = {
                "status": validation_result.status,
                "execution_time": validation_result.execution_time,
                "memory_usage": validation_result.memory_usage_mb,
                "platforms_tested": len(validation_result.details.get("platform_tests", {}))
            }
            
            if validation_result.errors:
                results["errors"].extend(validation_result.errors)
                if validation_result.status == "FAILED":
                    results["status"] = "FAILED"
            
            test_suite.cleanup_test_environment()
            print(f"✅ Platform optimization validation completed")
            
        except Exception as e:
            results["status"] = "FAILED"
            results["errors"].append(str(e))
            print(f"❌ Platform optimization validation failed: {e}")
        
        return results
    
    async def test_stress_testing(self) -> Dict[str, Any]:
        """Test comprehensive stress testing."""
        print("\n💪 Phase 6: Comprehensive Stress Testing")
        print("-" * 38)
        
        results = {"status": "PASSED", "details": {}, "errors": []}
        
        try:
            test_suite = ValidationTestSuite()
            test_suite.setup_test_environment()
            
            print(f"  Running comprehensive stress test (level {self.stress_level})...")
            start_time = time.time()
            
            validation_result = await test_suite.test_comprehensive_stress_test()
            
            duration = time.time() - start_time
            print(f"  Stress test completed in {duration:.2f}s")
            print(f"  Status: {validation_result.status}")
            
            if "stress_scenarios" in validation_result.details:
                stress_scenarios = validation_result.details["stress_scenarios"]
                print(f"  Stress scenarios tested: {len(stress_scenarios)}")
                
                for scenario, metrics in stress_scenarios.items():
                    if isinstance(metrics, dict) and "success_rate" in metrics:
                        print(f"    {scenario}: {metrics['success_rate']:.1f}% success rate")
            
            results["details"]["validation_result"] = {
                "status": validation_result.status,
                "execution_time": validation_result.execution_time,
                "memory_usage": validation_result.memory_usage_mb,
                "scenarios_tested": len(validation_result.details.get("stress_scenarios", {}))
            }
            
            if validation_result.errors:
                results["errors"].extend(validation_result.errors)
                if validation_result.status == "FAILED":
                    results["status"] = "FAILED"
            
            test_suite.cleanup_test_environment()
            print(f"✅ Comprehensive stress testing completed")
            
        except Exception as e:
            results["status"] = "FAILED"
            results["errors"].append(str(e))
            print(f"❌ Comprehensive stress testing failed: {e}")
        
        return results
    
    async def test_integration_validation(self) -> Dict[str, Any]:
        """Test integration validation."""
        print("\n🔄 Phase 7: Integration Validation")
        print("-" * 32)
        
        results = {"status": "PASSED", "details": {}, "errors": []}
        
        try:
            test_suite = ValidationTestSuite()
            test_suite.setup_test_environment()
            
            print(f"  Running integration validation...")
            start_time = time.time()
            
            validation_result = await test_suite.test_integration_validation()
            
            duration = time.time() - start_time
            print(f"  Integration validation completed in {duration:.2f}s")
            print(f"  Status: {validation_result.status}")
            
            if "integration_tests" in validation_result.details:
                integration_tests = validation_result.details["integration_tests"]
                print(f"  Integration tests performed: {len(integration_tests)}")
                
                for test_name, metrics in integration_tests.items():
                    if isinstance(metrics, dict) and "end_to_end_time" in metrics:
                        print(f"    {test_name}: {metrics['end_to_end_time']:.3f}s end-to-end")
            
            results["details"]["validation_result"] = {
                "status": validation_result.status,
                "execution_time": validation_result.execution_time,
                "memory_usage": validation_result.memory_usage_mb,
                "integration_tests": len(validation_result.details.get("integration_tests", {}))
            }
            
            if validation_result.errors:
                results["errors"].extend(validation_result.errors)
                if validation_result.status == "FAILED":
                    results["status"] = "FAILED"
            
            test_suite.cleanup_test_environment()
            print(f"✅ Integration validation completed")
            
        except Exception as e:
            results["status"] = "FAILED"
            results["errors"].append(str(e))
            print(f"❌ Integration validation failed: {e}")
        
        return results
    
    async def test_benchmark_comparisons(self) -> Dict[str, Any]:
        """Test benchmark comparisons against v1.2.1."""
        print("\n📈 Phase 8: Benchmark Comparisons vs v1.2.1")
        print("-" * 44)
        
        results = {"status": "PASSED", "details": {}, "errors": []}
        
        try:
            framework = FinalValidationFramework()
            
            print(f"  Generating benchmark comparisons...")
            start_time = time.time()
            
            benchmark_comparisons = framework.generate_benchmark_comparisons()
            
            duration = time.time() - start_time
            print(f"  Benchmark generation completed in {duration:.3f}s")
            print(f"  Comparisons generated: {len(benchmark_comparisons)}")
            
            # Analyze results
            improvements = [b for b in benchmark_comparisons if b.status == "IMPROVED"]
            degradations = [b for b in benchmark_comparisons if b.status == "DEGRADED"]
            stable = [b for b in benchmark_comparisons if b.status == "STABLE"]
            
            print(f"  Results summary:")
            print(f"    Improvements: {len(improvements)}")
            print(f"    Degradations: {len(degradations)}")
            print(f"    Stable: {len(stable)}")
            
            # Show top improvements
            if improvements:
                top_improvements = sorted(improvements, key=lambda x: x.improvement_percent, reverse=True)[:5]
                print(f"  Top improvements:")
                for comp in top_improvements:
                    print(f"    {comp.metric_name}: +{comp.improvement_percent:.1f}%")
            
            # Show any degradations
            if degradations:
                print(f"  ⚠️ Performance degradations found:")
                for comp in degradations:
                    print(f"    {comp.metric_name}: {comp.improvement_percent:.1f}%")
                results["status"] = "WARNING"
            
            results["details"]["benchmark_comparison"] = {
                "total_comparisons": len(benchmark_comparisons),
                "improvements": len(improvements),
                "degradations": len(degradations),
                "stable": len(stable),
                "avg_improvement": sum(b.improvement_percent for b in improvements) / len(improvements) if improvements else 0
            }
            
            if len(degradations) > len(improvements) / 2:  # More than half degraded
                results["errors"].append(f"Too many performance degradations: {len(degradations)}")
                results["status"] = "FAILED"
            
            print(f"✅ Benchmark comparisons completed")
            
        except Exception as e:
            results["status"] = "FAILED"
            results["errors"].append(str(e))
            print(f"❌ Benchmark comparisons failed: {e}")
        
        return results
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run complete final validation test suite."""
        print("🏁 Starting Final Performance Validation Tests")
        print("=" * 55)
        
        all_results = {}
        
        # Run all test phases
        test_phases = [
            ("profiling_validation", self.test_profiling_validation),
            ("database_validation", self.test_database_validation),
            ("ui_validation", self.test_ui_validation),
            ("memory_validation", self.test_memory_validation),
            ("platform_validation", self.test_platform_validation),
            ("stress_testing", self.test_stress_testing),
            ("integration_validation", self.test_integration_validation),
            ("benchmark_comparisons", self.test_benchmark_comparisons)
        ]
        
        passed_count = 0
        warning_count = 0
        
        for phase_name, test_func in test_phases:
            try:
                result = await test_func()
                all_results[phase_name] = result
                
                if result["status"] == "PASSED":
                    passed_count += 1
                elif result["status"] == "WARNING":
                    warning_count += 1
                    
            except Exception as e:
                all_results[phase_name] = {
                    "status": "FAILED",
                    "errors": [str(e)],
                    "details": {}
                }
        
        # Generate final validation report
        print(f"\n📋 Generating Final Validation Report...")
        try:
            framework = FinalValidationFramework()
            test_suite = ValidationTestSuite()
            test_suite.setup_test_environment()
            
            # Run the full validation
            validation_results = await test_suite.run_all_validation_tests()
            benchmark_comparisons = framework.generate_benchmark_comparisons()
            final_report = framework.generate_final_report(validation_results, benchmark_comparisons)
            
            # Export report
            text_report = framework.export_report(final_report, "text")
            
            print(f"  Final report generated:")
            print(f"    Total tests: {final_report.total_tests}")
            print(f"    Passed: {final_report.passed_tests}")
            print(f"    Failed: {final_report.failed_tests}")
            print(f"    Warnings: {final_report.warning_tests}")
            print(f"    Overall status: {final_report.overall_status}")
            
            all_results["final_report"] = {
                "total_tests": final_report.total_tests,
                "passed_tests": final_report.passed_tests,
                "failed_tests": final_report.failed_tests,
                "warning_tests": final_report.warning_tests,
                "overall_status": final_report.overall_status,
                "report_length": len(text_report)
            }
            
            test_suite.cleanup_test_environment()
            
        except Exception as e:
            print(f"  ⚠️ Final report generation failed: {e}")
            all_results["final_report"] = {"error": str(e)}
        
        # Summary
        print(f"\n📋 Final Validation Test Summary")
        print("=" * 55)
        print(f"✅ Passed: {passed_count}/{len(test_phases)} phases")
        print(f"⚠️ Warnings: {warning_count}/{len(test_phases)} phases")
        
        failed_count = len(test_phases) - passed_count - warning_count
        if failed_count == 0:
            print("🎉 ALL FINAL VALIDATION TESTS PASSED!")
        elif warning_count > 0 and failed_count == 0:
            print("⚠️ VALIDATION COMPLETED WITH WARNINGS")
        else:
            print(f"❌ {failed_count} phases failed - check details above")
        
        return all_results

async def main():
    """Main test runner entry point."""
    parser = argparse.ArgumentParser(description="Final Performance Validation Test Runner")
    parser.add_argument("--mode", choices=["all", "profiling", "database", "ui", "memory", "platform", "stress", "integration", "demo"], 
                       default="all", help="Test mode to run")
    parser.add_argument("--stress-level", type=int, choices=[1, 2, 3, 4, 5], default=3, 
                       help="Stress test intensity level (1=light, 5=extreme)")
    
    args = parser.parse_args()
    
    runner = FinalValidationTestRunner(stress_level=args.stress_level)
    
    try:
        if args.mode == "demo":
            # Run demo from the module
            from final_validation import demo_final_validation
            await demo_final_validation()
        else:
            # Run tests based on mode
            if args.mode == "all":
                await runner.run_all_tests()
            elif args.mode == "profiling":
                await runner.test_profiling_validation()
            elif args.mode == "database":
                await runner.test_database_validation()
            elif args.mode == "ui":
                await runner.test_ui_validation()
            elif args.mode == "memory":
                await runner.test_memory_validation()
            elif args.mode == "platform":
                await runner.test_platform_validation()
            elif args.mode == "stress":
                await runner.test_stress_testing()
            elif args.mode == "integration":
                await runner.test_integration_validation()
        
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test runner error: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 