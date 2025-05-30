"""
Automatic Recovery Engine

This module implements the automatic recovery management system including
retry policies, fallback chains, circuit breakers, and recovery state tracking.
"""

import time
import logging
import threading
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
from concurrent.futures import ThreadPoolExecutor, Future
import statistics

# Import recovery strategies
try:
    from core.recovery_strategies import (
        RecoveryAction, RecoveryResult, RecoveryPlan, RecoveryContext,
        RecoveryExecutor, RecoveryExecutionResult, get_recovery_plan
    )
    from data.models.error_management import ErrorInfo, ErrorCategory, ErrorSeverity
except ImportError:
    # Fallback for testing
    from enum import Enum
    class ErrorCategory(Enum):
        UNKNOWN = "unknown"
        UI = "ui"
        PLATFORM = "platform"
    
    class RecoveryResult(Enum):
        SUCCESS = "success"
        FAILED = "failed"


class RetryPolicy(Enum):
    """Available retry policies"""
    IMMEDIATE = "immediate"
    FIXED_DELAY = "fixed_delay"
    LINEAR_BACKOFF = "linear_backoff"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    CUSTOM = "custom"


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Failing, circuit open
    HALF_OPEN = "half_open" # Testing if service recovered


@dataclass
class RetryConfiguration:
    """Configuration for retry behavior"""
    policy: RetryPolicy = RetryPolicy.EXPONENTIAL_BACKOFF
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    backoff_factor: float = 2.0
    jitter: bool = True
    timeout_seconds: float = 60.0
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for a specific attempt"""
        if self.policy == RetryPolicy.IMMEDIATE:
            return 0.0
        elif self.policy == RetryPolicy.FIXED_DELAY:
            delay = self.base_delay_seconds
        elif self.policy == RetryPolicy.LINEAR_BACKOFF:
            delay = self.base_delay_seconds * attempt
        elif self.policy == RetryPolicy.EXPONENTIAL_BACKOFF:
            delay = self.base_delay_seconds * (self.backoff_factor ** (attempt - 1))
        else:
            delay = self.base_delay_seconds
        
        # Apply maximum delay limit
        delay = min(delay, self.max_delay_seconds)
        
        # Add jitter to prevent thundering herd
        if self.jitter:
            import random
            delay = delay * (0.5 + random.random() * 0.5)
        
        return delay


@dataclass
class FallbackResource:
    """Definition of a fallback resource"""
    name: str
    resource_type: str
    endpoint: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1  # Lower numbers = higher priority
    enabled: bool = True
    health_check: Optional[Callable[[], bool]] = None
    
    def is_healthy(self) -> bool:
        """Check if fallback resource is healthy"""
        if not self.enabled:
            return False
        if self.health_check:
            try:
                return self.health_check()
            except:
                return False
        return True


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5
    success_threshold: int = 3
    timeout_seconds: float = 60.0
    half_open_max_calls: int = 3
    
    
@dataclass 
class CircuitBreakerState:
    """Current state of a circuit breaker"""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    half_open_calls: int = 0


@dataclass
class RecoveryMetrics:
    """Metrics for recovery operations"""
    total_attempts: int = 0
    successful_recoveries: int = 0
    failed_recoveries: int = 0
    average_recovery_time: float = 0.0
    recovery_times: List[float] = field(default_factory=list)
    error_categories: Dict[str, int] = field(default_factory=dict)
    
    def add_recovery_attempt(self, success: bool, recovery_time: float, category: str):
        """Add a recovery attempt to metrics"""
        self.total_attempts += 1
        if success:
            self.successful_recoveries += 1
        else:
            self.failed_recoveries += 1
        
        self.recovery_times.append(recovery_time)
        if len(self.recovery_times) > 100:  # Keep only recent 100 attempts
            self.recovery_times.pop(0)
        
        self.average_recovery_time = statistics.mean(self.recovery_times)
        
        self.error_categories[category] = self.error_categories.get(category, 0) + 1
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_attempts == 0:
            return 0.0
        return (self.successful_recoveries / self.total_attempts) * 100


class FallbackChain:
    """Chain of fallback resources with automatic failover"""
    
    def __init__(self, primary_resource: str):
        self.primary_resource = primary_resource
        self.fallbacks: List[FallbackResource] = []
        self.current_resource = primary_resource
        self.logger = logging.getLogger(__name__)
    
    def add_fallback(self, resource: FallbackResource):
        """Add a fallback resource to the chain"""
        self.fallbacks.append(resource)
        # Sort by priority (lower number = higher priority)
        self.fallbacks.sort(key=lambda x: x.priority)
    
    def get_next_resource(self) -> Optional[FallbackResource]:
        """Get the next available healthy resource"""
        for fallback in self.fallbacks:
            if fallback.is_healthy():
                self.logger.info(f"Switching to fallback resource: {fallback.name}")
                self.current_resource = fallback.name
                return fallback
        return None
    
    def reset_to_primary(self):
        """Reset to primary resource"""
        self.current_resource = self.primary_resource
        self.logger.info(f"Reset to primary resource: {self.primary_resource}")


class CircuitBreaker:
    """Circuit breaker implementation to prevent cascade failures"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitBreakerState()
        self.logger = logging.getLogger(__name__)
        self._lock = threading.Lock()
    
    def can_execute(self) -> bool:
        """Check if operation can be executed"""
        with self._lock:
            now = datetime.now()
            
            if self.state.state == CircuitState.CLOSED:
                return True
            elif self.state.state == CircuitState.OPEN:
                # Check if timeout has expired
                if (self.state.last_failure_time and 
                    (now - self.state.last_failure_time).total_seconds() >= self.config.timeout_seconds):
                    self.state.state = CircuitState.HALF_OPEN
                    self.state.half_open_calls = 0
                    self.logger.info(f"Circuit breaker {self.name} moving to HALF_OPEN")
                    return True
                return False
            else:  # HALF_OPEN
                return self.state.half_open_calls < self.config.half_open_max_calls
    
    def record_success(self):
        """Record successful operation"""
        with self._lock:
            if self.state.state == CircuitState.HALF_OPEN:
                self.state.success_count += 1
                if self.state.success_count >= self.config.success_threshold:
                    self.state.state = CircuitState.CLOSED
                    self.state.failure_count = 0
                    self.state.success_count = 0
                    self.logger.info(f"Circuit breaker {self.name} closed (recovered)")
            else:
                self.state.failure_count = 0
    
    def record_failure(self):
        """Record failed operation"""
        with self._lock:
            self.state.failure_count += 1
            self.state.last_failure_time = datetime.now()
            
            if self.state.state == CircuitState.HALF_OPEN:
                self.state.state = CircuitState.OPEN
                self.logger.warning(f"Circuit breaker {self.name} opened (half-open failure)")
            elif (self.state.state == CircuitState.CLOSED and 
                  self.state.failure_count >= self.config.failure_threshold):
                self.state.state = CircuitState.OPEN
                self.logger.warning(f"Circuit breaker {self.name} opened (threshold exceeded)")
            
            if self.state.state == CircuitState.HALF_OPEN:
                self.state.half_open_calls += 1


class AutoRecoveryManager:
    """Main manager for automatic recovery operations"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.recovery_executor = RecoveryExecutor(max_workers=max_workers)
        self.logger = logging.getLogger(__name__)
        
        # Configuration and state
        self.retry_configs: Dict[ErrorCategory, RetryConfiguration] = {}
        self.fallback_chains: Dict[str, FallbackChain] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.metrics = RecoveryMetrics()
        
        # Threading
        self._lock = threading.Lock()
        self._setup_default_configs()
    
    def _setup_default_configs(self):
        """Setup default retry configurations for error categories"""
        # UI errors - quick retries
        self.retry_configs[ErrorCategory.UI] = RetryConfiguration(
            policy=RetryPolicy.FIXED_DELAY,
            max_attempts=2,
            base_delay_seconds=0.5,
            timeout_seconds=10.0
        )
        
        # Platform errors - exponential backoff
        self.retry_configs[ErrorCategory.PLATFORM] = RetryConfiguration(
            policy=RetryPolicy.EXPONENTIAL_BACKOFF,
            max_attempts=5,
            base_delay_seconds=1.0,
            max_delay_seconds=16.0,
            timeout_seconds=60.0
        )
        
        # Download errors - linear backoff with longer timeout
        self.retry_configs[ErrorCategory.DOWNLOAD] = RetryConfiguration(
            policy=RetryPolicy.LINEAR_BACKOFF,
            max_attempts=3,
            base_delay_seconds=2.0,
            max_delay_seconds=10.0,
            timeout_seconds=120.0
        )
        
        # Repository errors - immediate retry then delay
        self.retry_configs[ErrorCategory.REPOSITORY] = RetryConfiguration(
            policy=RetryPolicy.EXPONENTIAL_BACKOFF,
            max_attempts=3,
            base_delay_seconds=0.5,
            max_delay_seconds=5.0,
            timeout_seconds=30.0
        )
        
        # Service errors - exponential backoff
        self.retry_configs[ErrorCategory.SERVICE] = RetryConfiguration(
            policy=RetryPolicy.EXPONENTIAL_BACKOFF,
            max_attempts=4,
            base_delay_seconds=2.0,
            max_delay_seconds=20.0,
            timeout_seconds=90.0
        )
        
        # Default for unknown categories
        self.retry_configs[ErrorCategory.UNKNOWN] = RetryConfiguration(
            policy=RetryPolicy.EXPONENTIAL_BACKOFF,
            max_attempts=2,
            base_delay_seconds=1.0,
            max_delay_seconds=5.0,
            timeout_seconds=30.0
        )
    
    def set_retry_config(self, category: ErrorCategory, config: RetryConfiguration):
        """Set retry configuration for an error category"""
        self.retry_configs[category] = config
    
    def add_fallback_chain(self, operation: str, primary_resource: str) -> FallbackChain:
        """Add a fallback chain for an operation"""
        chain = FallbackChain(primary_resource)
        self.fallback_chains[operation] = chain
        return chain
    
    def add_circuit_breaker(self, service: str, config: CircuitBreakerConfig = None) -> CircuitBreaker:
        """Add a circuit breaker for a service"""
        if config is None:
            config = CircuitBreakerConfig()
        breaker = CircuitBreaker(service, config)
        self.circuit_breakers[service] = breaker
        return breaker
    
    def should_attempt_recovery(self, error_info, operation: str) -> bool:
        """Determine if automatic recovery should be attempted"""
        # Check circuit breaker if configured
        if operation in self.circuit_breakers:
            breaker = self.circuit_breakers[operation]
            if not breaker.can_execute():
                self.logger.info(f"Circuit breaker open for {operation}, skipping recovery")
                return False
        
        # Check error category configuration
        try:
            category = error_info.category if hasattr(error_info, 'category') else ErrorCategory.UNKNOWN
        except:
            category = ErrorCategory.UNKNOWN
        
        config = self.retry_configs.get(category)
        if not config:
            return False
        
        return True
    
    def execute_auto_recovery(self, error_info, operation: str, **kwargs) -> RecoveryExecutionResult:
        """Execute automatic recovery with retry logic, fallbacks, and circuit breaking"""
        start_time = datetime.now()
        
        try:
            category = error_info.category if hasattr(error_info, 'category') else ErrorCategory.UNKNOWN
        except:
            category = ErrorCategory.UNKNOWN
        
        category_str = category.value if hasattr(category, 'value') else str(category)
        
        if not self.should_attempt_recovery(error_info, operation):
            return RecoveryExecutionResult(
                success=False,
                result=RecoveryResult.SKIPPED,
                steps_executed=[],
                steps_results=[],
                execution_time=datetime.now() - start_time,
                error_message="Recovery skipped due to configuration or circuit breaker"
            )
        
        config = self.retry_configs.get(category, self.retry_configs[ErrorCategory.UNKNOWN])
        breaker = self.circuit_breakers.get(operation)
        
        last_result = None
        attempt = 1
        
        while attempt <= config.max_attempts:
            self.logger.info(f"Auto recovery attempt {attempt}/{config.max_attempts} for {operation}")
            
            # Get recovery plan and execute
            plan = get_recovery_plan(category)
            if not plan:
                self.logger.warning(f"No recovery plan found for category {category_str}")
                break
            
            context = RecoveryContext(
                error_info=error_info,
                original_operation=operation,
                operation_parameters=kwargs,
                attempt_count=attempt
            )
            
            result = self.recovery_executor.execute_plan(plan, context)
            last_result = result
            
            # Record metrics
            execution_time = result.execution_time.total_seconds()
            success = result.success
            
            # Update circuit breaker
            if breaker:
                if success:
                    breaker.record_success()
                else:
                    breaker.record_failure()
            
            # Check if recovery was successful
            if success:
                self.logger.info(f"Auto recovery successful for {operation} after {attempt} attempts")
                self.metrics.add_recovery_attempt(True, execution_time, category_str)
                return result
            
            # Check if we should retry
            if attempt < config.max_attempts:
                delay = config.calculate_delay(attempt)
                if delay > 0:
                    self.logger.info(f"Waiting {delay:.2f}s before retry {attempt + 1}")
                    time.sleep(delay)
                
                # Try fallback resource if configured
                if operation in self.fallback_chains:
                    chain = self.fallback_chains[operation]
                    fallback = chain.get_next_resource()
                    if fallback:
                        # Update operation parameters with fallback resource
                        kwargs.update(fallback.config)
            
            attempt += 1
        
        # All attempts failed
        total_time = (datetime.now() - start_time).total_seconds()
        self.metrics.add_recovery_attempt(False, total_time, category_str)
        
        if last_result:
            return last_result
        
        return RecoveryExecutionResult(
            success=False,
            result=RecoveryResult.FAILED,
            steps_executed=[],
            steps_results=[],
            execution_time=datetime.now() - start_time,
            error_message=f"Auto recovery failed after {config.max_attempts} attempts"
        )
    
    def get_metrics(self) -> RecoveryMetrics:
        """Get current recovery metrics"""
        with self._lock:
            return self.metrics
    
    def get_circuit_breaker_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers"""
        status = {}
        for name, breaker in self.circuit_breakers.items():
            status[name] = {
                'state': breaker.state.state.value,
                'failure_count': breaker.state.failure_count,
                'success_count': breaker.state.success_count,
                'last_failure': breaker.state.last_failure_time.isoformat() if breaker.state.last_failure_time else None
            }
        return status
    
    def reset_circuit_breaker(self, service: str):
        """Manually reset a circuit breaker"""
        if service in self.circuit_breakers:
            breaker = self.circuit_breakers[service]
            with breaker._lock:
                breaker.state = CircuitBreakerState()
            self.logger.info(f"Circuit breaker {service} manually reset")
    
    def enable_fallback_resource(self, operation: str, resource_name: str):
        """Enable a specific fallback resource"""
        if operation in self.fallback_chains:
            chain = self.fallback_chains[operation]
            for resource in chain.fallbacks:
                if resource.name == resource_name:
                    resource.enabled = True
                    self.logger.info(f"Enabled fallback resource {resource_name} for {operation}")
                    return
    
    def disable_fallback_resource(self, operation: str, resource_name: str):
        """Disable a specific fallback resource"""
        if operation in self.fallback_chains:
            chain = self.fallback_chains[operation]
            for resource in chain.fallbacks:
                if resource.name == resource_name:
                    resource.enabled = False
                    self.logger.info(f"Disabled fallback resource {resource_name} for {operation}")
                    return


# Global auto recovery manager
_auto_recovery_manager = None

def get_auto_recovery_manager() -> AutoRecoveryManager:
    """Get the global auto recovery manager"""
    global _auto_recovery_manager
    if _auto_recovery_manager is None:
        _auto_recovery_manager = AutoRecoveryManager()
    return _auto_recovery_manager


def execute_auto_recovery(error_info, operation: str, **kwargs) -> RecoveryExecutionResult:
    """Convenience function to execute automatic recovery"""
    manager = get_auto_recovery_manager()
    return manager.execute_auto_recovery(error_info, operation, **kwargs)


def get_recovery_metrics() -> RecoveryMetrics:
    """Get current recovery metrics"""
    manager = get_auto_recovery_manager()
    return manager.get_metrics()


def setup_fallback_chain(operation: str, primary_resource: str, fallbacks: List[FallbackResource]):
    """Setup a fallback chain for an operation"""
    manager = get_auto_recovery_manager()
    chain = manager.add_fallback_chain(operation, primary_resource)
    for fallback in fallbacks:
        chain.add_fallback(fallback)
    return chain


def setup_circuit_breaker(service: str, config: CircuitBreakerConfig = None) -> CircuitBreaker:
    """Setup a circuit breaker for a service"""
    manager = get_auto_recovery_manager()
    return manager.add_circuit_breaker(service, config) 