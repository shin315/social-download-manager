#!/usr/bin/env python3
"""
Enhanced Error Handling System for Adapter Framework
====================================================

This module provides comprehensive error handling enhancements including:
- Circuit breaker patterns for fault tolerance
- Intelligent retry mechanisms with exponential backoff
- Graceful degradation strategies
- Error context preservation and logging
- Recovery orchestration and fallback chains
- Health monitoring and alerting
"""

import asyncio
import logging
import time
import traceback
import threading
import json
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Union, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from contextlib import contextmanager
from functools import wraps, partial
import weakref

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for prioritized handling"""
    CRITICAL = "critical"
    HIGH = "high" 
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ErrorType(Enum):
    """Error type classification for specialized handling"""
    NETWORK = "network"
    DATA = "data"
    UI = "ui"
    ADAPTER = "adapter"
    SYSTEM = "system"
    VALIDATION = "validation"
    TIMEOUT = "timeout"
    RESOURCE = "resource"


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class ErrorContext:
    """Rich error context information"""
    error_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    error_type: ErrorType = ErrorType.SYSTEM
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    component: str = "unknown"
    operation: str = "unknown"
    user_action: str = "unknown"
    error_message: str = ""
    stack_trace: str = ""
    context_data: Dict[str, Any] = field(default_factory=dict)
    recovery_attempts: int = 0
    max_recovery_attempts: int = 3
    resolved: bool = False
    resolution_time: Optional[datetime] = None


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior"""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3
    success_threshold: int = 2
    timeout_duration: float = 30.0


class AdvancedCircuitBreaker:
    """
    Circuit breaker with adaptive thresholds and health monitoring
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0
        self.lock = threading.RLock()
        self.failure_window = deque(maxlen=100)
        self.call_times = deque(maxlen=1000)
        
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        with self.lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    logger.info(f"Circuit breaker {self.name} transitioning to HALF_OPEN")
                else:
                    raise CircuitBreakerOpenError(f"Circuit breaker {self.name} is OPEN")
            
            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls >= self.config.half_open_max_calls:
                    raise CircuitBreakerOpenError(f"Circuit breaker {self.name} max half-open calls exceeded")
                self.half_open_calls += 1
        
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            self._on_success(time.time() - start_time)
            return result
        except Exception as e:
            self._on_failure(time.time() - start_time)
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.config.recovery_timeout
    
    def _on_success(self, call_time: float):
        """Handle successful call"""
        with self.lock:
            self.call_times.append(call_time)
            
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    logger.info(f"Circuit breaker {self.name} RESET to CLOSED")
            elif self.state == CircuitState.CLOSED:
                self.failure_count = max(0, self.failure_count - 1)
    
    def _on_failure(self, call_time: float):
        """Handle failed call"""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            self.failure_window.append(self.last_failure_time)
            self.call_times.append(call_time)
            
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit breaker {self.name} OPENED due to {self.failure_count} failures")
    
    def get_health_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker health metrics"""
        with self.lock:
            recent_failures = len([t for t in self.failure_window 
                                 if time.time() - t < 300])  # Last 5 minutes
            avg_call_time = sum(self.call_times) / len(self.call_times) if self.call_times else 0
            
            return {
                "name": self.name,
                "state": self.state.value,
                "failure_count": self.failure_count,
                "success_count": self.success_count,
                "recent_failures": recent_failures,
                "avg_call_time": avg_call_time,
                "last_failure_time": self.last_failure_time
            }


class IntelligentRetryMechanism:
    """
    Sophisticated retry system with exponential backoff and jitter
    """
    
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0, 
                 max_delay: float = 60.0, exponential_base: float = 2.0,
                 jitter: bool = True):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        
    def execute(self, func: Callable, error_context: ErrorContext, 
                *args, **kwargs) -> Any:
        """Execute function with intelligent retry logic"""
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                if attempt > 0:
                    delay = self._calculate_delay(attempt)
                    logger.info(f"Retry attempt {attempt + 1}/{self.max_attempts} "
                              f"after {delay:.2f}s delay for {error_context.component}")
                    time.sleep(delay)
                
                result = func(*args, **kwargs)
                if attempt > 0:
                    logger.info(f"Recovery successful on attempt {attempt + 1} "
                              f"for {error_context.component}")
                return result
                
            except Exception as e:
                last_exception = e
                error_context.recovery_attempts = attempt + 1
                
                if self._is_retriable_error(e):
                    logger.warning(f"Retriable error in {error_context.component}: {e}")
                    continue
                else:
                    logger.error(f"Non-retriable error in {error_context.component}: {e}")
                    break
        
        # All retries exhausted
        error_context.resolved = False
        raise RetryExhaustedException(
            f"All {self.max_attempts} retry attempts failed for {error_context.component}",
            last_exception
        )
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter"""
        delay = min(
            self.base_delay * (self.exponential_base ** (attempt - 1)),
            self.max_delay
        )
        
        if self.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)  # 50-100% of calculated delay
            
        return delay
    
    def _is_retriable_error(self, error: Exception) -> bool:
        """Determine if error is worth retrying"""
        retriable_types = (
            ConnectionError, TimeoutError, OSError,
            # Add more retriable error types as needed
        )
        
        non_retriable_patterns = [
            "authentication", "permission", "authorization",
            "invalid", "malformed", "syntax"
        ]
        
        if isinstance(error, retriable_types):
            return True
            
        error_message = str(error).lower()
        return not any(pattern in error_message for pattern in non_retriable_patterns)


class GracefulDegradationManager:
    """
    Manages graceful degradation strategies for different components
    """
    
    def __init__(self):
        self.degradation_strategies = {}
        self.active_degradations = {}
        self.degradation_history = deque(maxlen=1000)
        
    def register_strategy(self, component: str, 
                         degradation_func: Callable,
                         priority: int = 1):
        """Register a degradation strategy for a component"""
        if component not in self.degradation_strategies:
            self.degradation_strategies[component] = []
        
        self.degradation_strategies[component].append({
            'func': degradation_func,
            'priority': priority,
            'registered_at': datetime.now()
        })
        
        # Sort by priority (higher = more preferred)
        self.degradation_strategies[component].sort(
            key=lambda x: x['priority'], reverse=True
        )
    
    def activate_degradation(self, component: str, error_context: ErrorContext) -> Any:
        """Activate degradation for a component"""
        if component not in self.degradation_strategies:
            logger.warning(f"No degradation strategy available for {component}")
            return None
        
        for strategy in self.degradation_strategies[component]:
            try:
                logger.info(f"Activating degradation strategy for {component}")
                result = strategy['func'](error_context)
                
                self.active_degradations[component] = {
                    'strategy': strategy,
                    'activated_at': datetime.now(),
                    'error_context': error_context
                }
                
                self.degradation_history.append({
                    'component': component,
                    'activated_at': datetime.now(),
                    'error_id': error_context.error_id,
                    'severity': error_context.severity.value
                })
                
                return result
                
            except Exception as e:
                logger.error(f"Degradation strategy failed for {component}: {e}")
                continue
        
        logger.error(f"All degradation strategies failed for {component}")
        return None
    
    def deactivate_degradation(self, component: str):
        """Deactivate degradation for a component"""
        if component in self.active_degradations:
            logger.info(f"Deactivating degradation for {component}")
            del self.active_degradations[component]
    
    def get_degradation_status(self) -> Dict[str, Any]:
        """Get current degradation status"""
        return {
            'active_degradations': {
                comp: {
                    'activated_at': info['activated_at'].isoformat(),
                    'error_id': info['error_context'].error_id,
                    'duration': (datetime.now() - info['activated_at']).total_seconds()
                }
                for comp, info in self.active_degradations.items()
            },
            'total_strategies': sum(len(strategies) 
                                  for strategies in self.degradation_strategies.values()),
            'recent_activations': len([h for h in self.degradation_history 
                                     if (datetime.now() - h['activated_at']).total_seconds() < 3600])
        }


class ErrorRecoveryOrchestrator:
    """
    Orchestrates error recovery across multiple strategies and components
    """
    
    def __init__(self):
        self.circuit_breakers = {}
        self.retry_mechanism = IntelligentRetryMechanism()
        self.degradation_manager = GracefulDegradationManager()
        self.error_contexts = {}
        self.recovery_chains = defaultdict(list)
        self.health_monitor = HealthMonitor()
        
    def register_circuit_breaker(self, name: str, config: CircuitBreakerConfig):
        """Register a circuit breaker for a component"""
        self.circuit_breakers[name] = AdvancedCircuitBreaker(name, config)
        
    def register_recovery_chain(self, component: str, recovery_steps: List[Callable]):
        """Register a recovery chain for a component"""
        self.recovery_chains[component] = recovery_steps
        
    def handle_error(self, error: Exception, component: str, 
                    operation: str, context_data: Dict[str, Any] = None) -> Any:
        """Main error handling entry point"""
        error_context = ErrorContext(
            error_type=self._classify_error(error),
            severity=self._assess_severity(error),
            component=component,
            operation=operation,
            error_message=str(error),
            stack_trace=traceback.format_exc(),
            context_data=context_data or {}
        )
        
        self.error_contexts[error_context.error_id] = error_context
        
        logger.error(f"Error in {component}.{operation}: {error} "
                    f"[ID: {error_context.error_id}]")
        
        try:
            # Try recovery chain
            if component in self.recovery_chains:
                result = self._execute_recovery_chain(component, error_context)
                if result is not None:
                    error_context.resolved = True
                    error_context.resolution_time = datetime.now()
                    return result
            
            # Try circuit breaker + retry
            if component in self.circuit_breakers:
                return self._handle_with_circuit_breaker(component, error_context)
            
            # Fallback to graceful degradation
            return self.degradation_manager.activate_degradation(component, error_context)
            
        except Exception as recovery_error:
            logger.critical(f"Recovery failed for {component}: {recovery_error}")
            self.health_monitor.record_critical_failure(component, error_context)
            raise
    
    def _execute_recovery_chain(self, component: str, 
                               error_context: ErrorContext) -> Any:
        """Execute recovery chain for a component"""
        recovery_steps = self.recovery_chains[component]
        
        for step_idx, recovery_step in enumerate(recovery_steps):
            try:
                logger.info(f"Executing recovery step {step_idx + 1}/{len(recovery_steps)} "
                          f"for {component}")
                result = recovery_step(error_context)
                if result is not None:
                    logger.info(f"Recovery successful at step {step_idx + 1} for {component}")
                    return result
            except Exception as e:
                logger.warning(f"Recovery step {step_idx + 1} failed for {component}: {e}")
                continue
        
        logger.warning(f"All recovery steps failed for {component}")
        return None
    
    def _handle_with_circuit_breaker(self, component: str, 
                                   error_context: ErrorContext) -> Any:
        """Handle error using circuit breaker and retry mechanism"""
        circuit_breaker = self.circuit_breakers[component]
        
        def retry_operation():
            # This would be the actual operation retry
            # For now, we'll simulate based on error context
            if error_context.recovery_attempts < error_context.max_recovery_attempts:
                raise Exception("Simulated retry needed")
            return f"Recovery result for {component}"
        
        try:
            return circuit_breaker.call(
                self.retry_mechanism.execute,
                retry_operation,
                error_context
            )
        except CircuitBreakerOpenError:
            logger.warning(f"Circuit breaker open for {component}, trying degradation")
            return self.degradation_manager.activate_degradation(component, error_context)
    
    def _classify_error(self, error: Exception) -> ErrorType:
        """Classify error by type"""
        error_message = str(error).lower()
        
        if any(term in error_message for term in ['network', 'connection', 'socket']):
            return ErrorType.NETWORK
        elif any(term in error_message for term in ['timeout', 'time']):
            return ErrorType.TIMEOUT
        elif any(term in error_message for term in ['data', 'json', 'parse']):
            return ErrorType.DATA
        elif any(term in error_message for term in ['ui', 'interface', 'widget']):
            return ErrorType.UI
        elif any(term in error_message for term in ['memory', 'resource']):
            return ErrorType.RESOURCE
        else:
            return ErrorType.SYSTEM
    
    def _assess_severity(self, error: Exception) -> ErrorSeverity:
        """Assess error severity"""
        critical_patterns = ['critical', 'fatal', 'shutdown', 'corrupt']
        high_patterns = ['error', 'fail', 'exception']
        
        error_message = str(error).lower()
        
        if any(pattern in error_message for pattern in critical_patterns):
            return ErrorSeverity.CRITICAL
        elif any(pattern in error_message for pattern in high_patterns):
            return ErrorSeverity.HIGH
        else:
            return ErrorSeverity.MEDIUM
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health report"""
        circuit_health = {name: cb.get_health_metrics() 
                         for name, cb in self.circuit_breakers.items()}
        
        degradation_status = self.degradation_manager.get_degradation_status()
        
        active_errors = len([ctx for ctx in self.error_contexts.values() 
                           if not ctx.resolved])
        
        return {
            'timestamp': datetime.now().isoformat(),
            'circuit_breakers': circuit_health,
            'degradation_status': degradation_status,
            'active_errors': active_errors,
            'total_errors': len(self.error_contexts),
            'health_score': self._calculate_health_score(),
            'recommendations': self._generate_health_recommendations()
        }
    
    def _calculate_health_score(self) -> float:
        """Calculate overall system health score (0-100)"""
        score = 100.0
        
        # Penalize for open circuit breakers
        open_circuits = sum(1 for cb in self.circuit_breakers.values() 
                          if cb.state == CircuitState.OPEN)
        score -= open_circuits * 20
        
        # Penalize for active degradations
        active_degradations = len(self.degradation_manager.active_degradations)
        score -= active_degradations * 15
        
        # Penalize for unresolved errors
        unresolved_errors = len([ctx for ctx in self.error_contexts.values() 
                               if not ctx.resolved])
        score -= unresolved_errors * 10
        
        return max(0.0, score)
    
    def _generate_health_recommendations(self) -> List[str]:
        """Generate health improvement recommendations"""
        recommendations = []
        
        open_circuits = [name for name, cb in self.circuit_breakers.items() 
                        if cb.state == CircuitState.OPEN]
        if open_circuits:
            recommendations.append(f"Investigate open circuit breakers: {open_circuits}")
        
        if self.degradation_manager.active_degradations:
            recommendations.append("Review active degradations and restore full functionality")
        
        critical_errors = [ctx for ctx in self.error_contexts.values() 
                          if ctx.severity == ErrorSeverity.CRITICAL and not ctx.resolved]
        if critical_errors:
            recommendations.append(f"Address {len(critical_errors)} critical unresolved errors")
        
        return recommendations


class HealthMonitor:
    """
    Advanced health monitoring and alerting system
    """
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.alerts = deque(maxlen=1000)
        self.thresholds = {
            'error_rate': 0.1,  # 10% error rate threshold
            'response_time': 5.0,  # 5 second response time threshold
            'memory_usage': 0.8  # 80% memory usage threshold
        }
        
    def record_metric(self, component: str, metric_name: str, value: float):
        """Record a metric value"""
        timestamp = datetime.now()
        self.metrics[f"{component}.{metric_name}"].append({
            'timestamp': timestamp,
            'value': value
        })
        
        # Check thresholds
        if metric_name in self.thresholds:
            if value > self.thresholds[metric_name]:
                self._trigger_alert(component, metric_name, value, self.thresholds[metric_name])
    
    def record_critical_failure(self, component: str, error_context: ErrorContext):
        """Record a critical failure"""
        self._trigger_alert(
            component, 
            "critical_failure", 
            error_context.error_id,
            "immediate_attention"
        )
    
    def _trigger_alert(self, component: str, metric: str, value: Any, threshold: Any):
        """Trigger an alert"""
        alert = {
            'timestamp': datetime.now(),
            'component': component,
            'metric': metric,
            'value': value,
            'threshold': threshold,
            'alert_id': str(uuid.uuid4())
        }
        
        self.alerts.append(alert)
        logger.warning(f"ALERT: {component}.{metric} = {value} exceeds threshold {threshold}")


# Custom Exception Classes
class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass

class RetryExhaustedException(Exception):
    """Raised when all retry attempts are exhausted"""
    def __init__(self, message: str, original_exception: Exception):
        super().__init__(message)
        self.original_exception = original_exception


# Decorator for automatic error handling
def with_error_handling(component: str, operation: str = None, 
                       orchestrator: ErrorRecoveryOrchestrator = None):
    """Decorator to automatically apply error handling to functions"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation or func.__name__
            error_orchestrator = orchestrator or get_default_orchestrator()
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                return error_orchestrator.handle_error(
                    e, component, op_name, {'args': args, 'kwargs': kwargs}
                )
        return wrapper
    return decorator


# Global orchestrator instance
_default_orchestrator = None

def get_default_orchestrator() -> ErrorRecoveryOrchestrator:
    """Get the default error recovery orchestrator"""
    global _default_orchestrator
    if _default_orchestrator is None:
        _default_orchestrator = ErrorRecoveryOrchestrator()
        setup_default_configuration(_default_orchestrator)
    return _default_orchestrator

def setup_default_configuration(orchestrator: ErrorRecoveryOrchestrator):
    """Setup default configuration for the orchestrator"""
    # Register default circuit breakers
    default_config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=30.0,
        half_open_max_calls=2
    )
    
    components = ['adapter', 'event_system', 'data_mapper', 'state_manager']
    for component in components:
        orchestrator.register_circuit_breaker(component, default_config)
    
    # Register default degradation strategies
    def default_degradation(error_context: ErrorContext):
        return f"Degraded mode for {error_context.component}"
    
    for component in components:
        orchestrator.degradation_manager.register_strategy(
            component, default_degradation, priority=1
        )


def main():
    """Demonstrate the error handling enhancement system"""
    print("=== Error Handling Enhancement System Demo ===\n")
    
    orchestrator = ErrorRecoveryOrchestrator()
    
    # Setup circuit breakers
    config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=5.0)
    orchestrator.register_circuit_breaker("test_adapter", config)
    
    # Setup degradation strategy
    def test_degradation(error_context: ErrorContext):
        return f"Fallback result for {error_context.component}"
    
    orchestrator.degradation_manager.register_strategy("test_adapter", test_degradation)
    
    # Simulate errors and recovery
    test_scenarios = [
        ("network_error", ConnectionError("Network timeout")),
        ("data_error", ValueError("Invalid data format")),
        ("critical_error", RuntimeError("Critical system failure"))
    ]
    
    results = {}
    for scenario_name, error in test_scenarios:
        print(f"Testing scenario: {scenario_name}")
        try:
            result = orchestrator.handle_error(
                error, "test_adapter", "test_operation", 
                {"scenario": scenario_name}
            )
            results[scenario_name] = {"success": True, "result": result}
            print(f"✅ Handled successfully: {result}")
        except Exception as e:
            results[scenario_name] = {"success": False, "error": str(e)}
            print(f"❌ Failed to handle: {e}")
        print()
    
    # Display health report
    health_report = orchestrator.get_system_health()
    print("=== System Health Report ===")
    print(json.dumps(health_report, indent=2, default=str))
    
    # Performance summary
    print(f"\n=== Performance Summary ===")
    print(f"Total scenarios tested: {len(test_scenarios)}")
    successful_recoveries = sum(1 for r in results.values() if r["success"])
    print(f"Successful recoveries: {successful_recoveries}/{len(test_scenarios)}")
    print(f"Recovery rate: {successful_recoveries/len(test_scenarios)*100:.1f}%")
    
    return {
        "scenarios_tested": len(test_scenarios),
        "successful_recoveries": successful_recoveries,
        "recovery_rate": successful_recoveries/len(test_scenarios),
        "health_score": health_report["health_score"],
        "results": results,
        "health_report": health_report
    }


if __name__ == "__main__":
    main() 