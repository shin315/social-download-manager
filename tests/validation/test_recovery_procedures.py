"""
Comprehensive Test Suite for Recovery Procedures

Tests the recovery strategies system, automatic recovery engine,
circuit breakers, fallback chains, and retry policies.
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from unittest.mock import Mock

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

from core.recovery_strategies import (
    RecoveryAction, RecoveryResult, RecoveryStep, RecoveryPlan, RecoveryContext,
    RecoveryExecutor, RecoveryExecutionResult, RecoveryPlanRegistry,
    get_recovery_registry, get_recovery_plan, execute_recovery
)
from core.recovery_engine import (
    RetryPolicy, RetryConfiguration, FallbackResource, FallbackChain,
    CircuitState, CircuitBreakerConfig, CircuitBreaker, AutoRecoveryManager,
    get_auto_recovery_manager, execute_auto_recovery, get_recovery_metrics,
    setup_fallback_chain, setup_circuit_breaker
)
from data.models.error_management import (
    ErrorInfo, ErrorCategory, ErrorSeverity, ErrorContext, RecoveryStrategy
)


class TestRecoveryProcedures:
    """Test suite for recovery procedures"""
    
    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_results = []
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def log_test_result(self, test_name: str, success: bool, details: str = ""):
        """Log the result of a test"""
        if success:
            self.passed_tests += 1
            status = "✅ PASS"
        else:
            self.failed_tests += 1
            status = "❌ FAIL"
        
        result = f"{status}: {test_name}"
        if details:
            result += f"\n   Details: {details}"
        
        self.test_results.append(result)
        print(result)
    
    def run_all_tests(self):
        """Run all recovery procedure tests"""
        print("🚀 Starting Recovery Procedures Test Suite")
        print("=" * 60)
        
        # Test Recovery Strategies
        self.test_recovery_actions()
        self.test_recovery_steps()
        self.test_recovery_plans()
        self.test_recovery_executor()
        self.test_recovery_registry()
        
        # Test Automatic Recovery Engine
        self.test_retry_configuration()
        self.test_fallback_resources()
        self.test_fallback_chains()
        self.test_circuit_breaker()
        self.test_auto_recovery_manager()
        
        # Test Integration
        self.test_error_category_plans()
        self.test_end_to_end_recovery()
        self.test_recovery_metrics()
        
        # Print summary
        self.print_summary()
    
    def test_recovery_actions(self):
        """Test recovery action enumeration"""
        try:
            # Test that all expected actions exist
            expected_actions = [
                'RETRY', 'RETRY_WITH_DELAY', 'RETRY_WITH_BACKOFF',
                'FALLBACK_RESOURCE', 'FALLBACK_METHOD', 'RESET_STATE',
                'CLEAR_CACHE', 'RELOAD_CONFIG', 'PROMPT_USER',
                'REQUEST_PERMISSION', 'ESCALATE_TO_ADMIN',
                'GRACEFUL_DEGRADATION', 'ABORT_OPERATION',
                'RESTART_SERVICE', 'CONTACT_SUPPORT'
            ]
            
            for action_name in expected_actions:
                if not hasattr(RecoveryAction, action_name):
                    self.log_test_result("Recovery Actions", False, f"Missing action: {action_name}")
                    return
            
            self.log_test_result("Recovery Actions", True, f"All {len(expected_actions)} actions defined")
        
        except Exception as e:
            self.log_test_result("Recovery Actions", False, f"Exception: {str(e)}")
    
    def test_recovery_steps(self):
        """Test recovery step creation and execution"""
        try:
            # Create a simple recovery step
            step = RecoveryStep(
                action=RecoveryAction.RETRY,
                description="Test retry step",
                parameters={'max_retries': 3},
                timeout_seconds=10
            )
            
            # Create context
            error_info = ErrorInfo(
                error_id="TEST_001",
                error_code="TEST_ERROR",
                message="Test error",
                category=ErrorCategory.UNKNOWN,
                severity=ErrorSeverity.HIGH,
                context=ErrorContext(operation="test_operation"),
                recovery_strategy=RecoveryStrategy.RETRY
            )
            
            context = RecoveryContext(
                error_info=error_info,
                original_operation="test_operation"
            )
            
            # Test condition evaluation
            should_execute = step.should_execute(context)
            
            if (step.action == RecoveryAction.RETRY and
                step.description == "Test retry step" and
                step.parameters['max_retries'] == 3 and
                should_execute):
                self.log_test_result("Recovery Steps", True, "Step creation and evaluation successful")
            else:
                self.log_test_result("Recovery Steps", False, "Step properties not set correctly")
        
        except Exception as e:
            self.log_test_result("Recovery Steps", False, f"Exception: {str(e)}")
    
    def test_recovery_plans(self):
        """Test recovery plan creation and step filtering"""
        try:
            # Create recovery plan with multiple steps
            steps = [
                RecoveryStep(
                    action=RecoveryAction.RETRY,
                    description="Initial retry",
                    parameters={'max_retries': 2}
                ),
                RecoveryStep(
                    action=RecoveryAction.FALLBACK_RESOURCE,
                    description="Use fallback",
                    parameters={'resources': ['backup']},
                    required=False
                )
            ]
            
            plan = RecoveryPlan(
                category=ErrorCategory.PLATFORM,
                steps=steps,
                max_attempts=3,
                description="Platform recovery plan"
            )
            
            # Test plan properties
            error_info = ErrorInfo(
                error_id="PLAN_TEST_001",
                error_code="PLAN_ERROR",
                message="Plan test error",
                category=ErrorCategory.PLATFORM,
                severity=ErrorSeverity.MEDIUM,
                context=ErrorContext(operation="plan_test"),
                recovery_strategy=RecoveryStrategy.RETRY
            )
            
            context = RecoveryContext(
                error_info=error_info,
                original_operation="plan_test"
            )
            
            applicable_steps = plan.get_applicable_steps(context)
            
            if (len(applicable_steps) == 2 and
                plan.category == ErrorCategory.PLATFORM and
                plan.max_attempts == 3):
                self.log_test_result("Recovery Plans", True, f"Plan with {len(applicable_steps)} applicable steps")
            else:
                self.log_test_result("Recovery Plans", False, f"Plan configuration incorrect")
        
        except Exception as e:
            self.log_test_result("Recovery Plans", False, f"Exception: {str(e)}")
    
    def test_recovery_executor(self):
        """Test recovery executor functionality"""
        try:
            executor = RecoveryExecutor()
            
            # Create simple plan
            plan = RecoveryPlan(
                category=ErrorCategory.UI,
                steps=[
                    RecoveryStep(
                        action=RecoveryAction.RETRY,
                        description="UI retry",
                        parameters={'max_retries': 1}
                    )
                ],
                description="UI test plan"
            )
            
            error_info = ErrorInfo(
                error_id="EXEC_TEST_001",
                error_code="EXEC_ERROR",
                message="Executor test error",
                category=ErrorCategory.UI,
                severity=ErrorSeverity.LOW,
                context=ErrorContext(operation="ui_test"),
                recovery_strategy=RecoveryStrategy.RETRY
            )
            
            context = RecoveryContext(
                error_info=error_info,
                original_operation="ui_test"
            )
            
            # Execute plan
            result = executor.execute_plan(plan, context)
            
            if (isinstance(result, RecoveryExecutionResult) and
                len(result.steps_executed) > 0 and
                result.execution_time.total_seconds() >= 0):
                self.log_test_result("Recovery Executor", True, f"Executed {len(result.steps_executed)} steps")
            else:
                self.log_test_result("Recovery Executor", False, "Execution result invalid")
        
        except Exception as e:
            self.log_test_result("Recovery Executor", False, f"Exception: {str(e)}")
    
    def test_recovery_registry(self):
        """Test recovery plan registry"""
        try:
            registry = get_recovery_registry()
            
            # Test that plans exist for key categories
            required_categories = [
                ErrorCategory.UI, ErrorCategory.PLATFORM, ErrorCategory.DOWNLOAD,
                ErrorCategory.REPOSITORY, ErrorCategory.SERVICE, ErrorCategory.AUTHENTICATION
            ]
            
            plans_found = 0
            for category in required_categories:
                plan = registry.get_plan(category)
                if plan:
                    plans_found += 1
            
            if plans_found >= len(required_categories):
                self.log_test_result("Recovery Registry", True, f"Found plans for {plans_found}/{len(required_categories)} categories")
            else:
                self.log_test_result("Recovery Registry", False, f"Only found {plans_found}/{len(required_categories)} plans")
        
        except Exception as e:
            self.log_test_result("Recovery Registry", False, f"Exception: {str(e)}")
    
    def test_retry_configuration(self):
        """Test retry configuration and delay calculation"""
        try:
            # Test exponential backoff
            config = RetryConfiguration(
                policy=RetryPolicy.EXPONENTIAL_BACKOFF,
                max_attempts=3,
                base_delay_seconds=1.0,
                backoff_factor=2.0,
                jitter=False  # Disable for predictable testing
            )
            
            delay1 = config.calculate_delay(1)
            delay2 = config.calculate_delay(2)
            delay3 = config.calculate_delay(3)
            
            # Test fixed delay
            fixed_config = RetryConfiguration(
                policy=RetryPolicy.FIXED_DELAY,
                base_delay_seconds=2.0,
                jitter=False
            )
            
            fixed_delay = fixed_config.calculate_delay(5)
            
            if (delay1 == 1.0 and delay2 == 2.0 and delay3 == 4.0 and fixed_delay == 2.0):
                self.log_test_result("Retry Configuration", True, f"Delays: {delay1}, {delay2}, {delay3}, fixed: {fixed_delay}")
            else:
                self.log_test_result("Retry Configuration", False, f"Unexpected delays: {delay1}, {delay2}, {delay3}")
        
        except Exception as e:
            self.log_test_result("Retry Configuration", False, f"Exception: {str(e)}")
    
    def test_fallback_resources(self):
        """Test fallback resource functionality"""
        try:
            # Create fallback resource with health check
            def healthy_check():
                return True
            
            def unhealthy_check():
                return False
            
            healthy_resource = FallbackResource(
                name="healthy_backup",
                resource_type="api",
                endpoint="https://backup.example.com",
                priority=1,
                health_check=healthy_check
            )
            
            unhealthy_resource = FallbackResource(
                name="unhealthy_backup",
                resource_type="api",
                endpoint="https://down.example.com",
                priority=2,
                health_check=unhealthy_check
            )
            
            if (healthy_resource.is_healthy() and not unhealthy_resource.is_healthy()):
                self.log_test_result("Fallback Resources", True, "Health checks working correctly")
            else:
                self.log_test_result("Fallback Resources", False, "Health checks failed")
        
        except Exception as e:
            self.log_test_result("Fallback Resources", False, f"Exception: {str(e)}")
    
    def test_fallback_chains(self):
        """Test fallback chain functionality"""
        try:
            chain = FallbackChain("primary_api")
            
            # Add fallback resources
            chain.add_fallback(FallbackResource(
                name="backup_1",
                resource_type="api",
                priority=1,
                enabled=True
            ))
            
            chain.add_fallback(FallbackResource(
                name="backup_2",
                resource_type="api",
                priority=2,
                enabled=True
            ))
            
            # Get next resource
            next_resource = chain.get_next_resource()
            
            if (next_resource and next_resource.name == "backup_1" and
                chain.current_resource == "backup_1"):
                self.log_test_result("Fallback Chains", True, f"Switched to {next_resource.name}")
            else:
                self.log_test_result("Fallback Chains", False, "Chain switching failed")
        
        except Exception as e:
            self.log_test_result("Fallback Chains", False, f"Exception: {str(e)}")
    
    def test_circuit_breaker(self):
        """Test circuit breaker functionality"""
        try:
            config = CircuitBreakerConfig(
                failure_threshold=3,
                success_threshold=2,
                timeout_seconds=1
            )
            
            breaker = CircuitBreaker("test_service", config)
            
            # Test initial state
            if not breaker.can_execute():
                self.log_test_result("Circuit Breaker", False, "Circuit should be closed initially")
                return
            
            # Record failures to open circuit
            for i in range(3):
                breaker.record_failure()
            
            # Circuit should be open now
            if breaker.can_execute():
                self.log_test_result("Circuit Breaker", False, "Circuit should be open after failures")
                return
            
            # Wait for timeout and test half-open
            time.sleep(1.1)
            
            if not breaker.can_execute():
                self.log_test_result("Circuit Breaker", False, "Circuit should allow execution after timeout")
                return
            
            self.log_test_result("Circuit Breaker", True, "Circuit breaker state transitions working")
        
        except Exception as e:
            self.log_test_result("Circuit Breaker", False, f"Exception: {str(e)}")
    
    def test_auto_recovery_manager(self):
        """Test automatic recovery manager"""
        try:
            manager = get_auto_recovery_manager()
            
            # Test configuration
            ui_config = manager.retry_configs.get(ErrorCategory.UI)
            if not ui_config:
                self.log_test_result("Auto Recovery Manager", False, "UI config not found")
                return
            
            # Test circuit breaker setup
            breaker = manager.add_circuit_breaker("test_service")
            if not breaker:
                self.log_test_result("Auto Recovery Manager", False, "Circuit breaker creation failed")
                return
            
            # Test fallback chain setup
            chain = manager.add_fallback_chain("test_operation", "primary")
            if not chain:
                self.log_test_result("Auto Recovery Manager", False, "Fallback chain creation failed")
                return
            
            self.log_test_result("Auto Recovery Manager", True, "Manager setup and configuration working")
        
        except Exception as e:
            self.log_test_result("Auto Recovery Manager", False, f"Exception: {str(e)}")
    
    def test_error_category_plans(self):
        """Test that all error categories have recovery plans"""
        try:
            registry = get_recovery_registry()
            
            # Test all error categories
            categories = [
                ErrorCategory.UI, ErrorCategory.PLATFORM, ErrorCategory.DOWNLOAD,
                ErrorCategory.REPOSITORY, ErrorCategory.SERVICE, ErrorCategory.AUTHENTICATION,
                ErrorCategory.PERMISSION, ErrorCategory.FILE_SYSTEM, ErrorCategory.PARSING,
                ErrorCategory.INTEGRATION, ErrorCategory.FATAL, ErrorCategory.UNKNOWN
            ]
            
            plans_with_steps = 0
            for category in categories:
                plan = registry.get_plan(category)
                if plan and len(plan.steps) > 0:
                    plans_with_steps += 1
            
            if plans_with_steps >= len(categories):
                self.log_test_result("Error Category Plans", True, f"All {len(categories)} categories have recovery plans")
            else:
                self.log_test_result("Error Category Plans", False, f"Only {plans_with_steps}/{len(categories)} have plans with steps")
        
        except Exception as e:
            self.log_test_result("Error Category Plans", False, f"Exception: {str(e)}")
    
    def test_end_to_end_recovery(self):
        """Test end-to-end recovery process"""
        try:
            # Create error info
            error_info = ErrorInfo(
                error_id="E2E_TEST_001",
                error_code="E2E_ERROR",
                message="End-to-end test error",
                category=ErrorCategory.PLATFORM,
                severity=ErrorSeverity.MEDIUM,
                context=ErrorContext(operation="e2e_test"),
                recovery_strategy=RecoveryStrategy.RETRY
            )
            
            # Execute recovery
            result = execute_auto_recovery(error_info, "e2e_test_operation")
            
            if (isinstance(result, RecoveryExecutionResult) and
                result.execution_time.total_seconds() >= 0):
                self.log_test_result("End-to-End Recovery", True, f"Recovery completed: {result.result.value}")
            else:
                self.log_test_result("End-to-End Recovery", False, "Invalid recovery result")
        
        except Exception as e:
            self.log_test_result("End-to-End Recovery", False, f"Exception: {str(e)}")
    
    def test_recovery_metrics(self):
        """Test recovery metrics collection"""
        try:
            metrics = get_recovery_metrics()
            
            # Initial metrics should be valid
            if (hasattr(metrics, 'total_attempts') and
                hasattr(metrics, 'successful_recoveries') and
                hasattr(metrics, 'success_rate')):
                
                # Test adding a metric
                metrics.add_recovery_attempt(True, 1.5, 'test_category')
                
                if (metrics.total_attempts >= 1 and
                    metrics.successful_recoveries >= 1 and
                    'test_category' in metrics.error_categories):
                    self.log_test_result("Recovery Metrics", True, f"Metrics: {metrics.total_attempts} attempts, {metrics.success_rate:.1f}% success")
                else:
                    self.log_test_result("Recovery Metrics", False, "Metrics not updating correctly")
            else:
                self.log_test_result("Recovery Metrics", False, "Metrics object missing required attributes")
        
        except Exception as e:
            self.log_test_result("Recovery Metrics", False, f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        total_tests = self.passed_tests + self.failed_tests
        success_rate = (self.passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.failed_tests}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if self.failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in self.test_results:
                if "❌ FAIL" in result:
                    test_name = result.split(":")[1].strip()
                    print(f"  - {test_name}")
        
        print(f"\n✅ PASSED TESTS:")
        for result in self.test_results:
            if "✅ PASS" in result:
                test_name = result.split(":")[1].strip()
                print(f"  - {test_name}")
        
        if success_rate == 100:
            print("\n🎉 All tests passed! Recovery Procedures implementation is working correctly.")
            print("\nKey Features Tested:")
            print("✅ Recovery strategies and actions")
            print("✅ Recovery step execution and plans")
            print("✅ Recovery executor and registry")
            print("✅ Retry configurations and policies")
            print("✅ Fallback resources and chains")
            print("✅ Circuit breaker implementation")
            print("✅ Automatic recovery manager")
            print("✅ Error category-specific plans")
            print("✅ End-to-end recovery process")
            print("✅ Recovery metrics collection")
        else:
            print(f"\n⚠️  Some tests failed. Please review the implementation.")


if __name__ == "__main__":
    tester = TestRecoveryProcedures()
    tester.run_all_tests() 