"""
Recovery Strategies System

This module implements the core recovery framework for handling errors and
providing automated recovery mechanisms across different error categories.
"""

import time
import logging
import traceback
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor, Future

# Import error management components
try:
    from data.models.error_management import ErrorInfo, ErrorCategory, ErrorSeverity, RecoveryStrategy
except ImportError:
    # Fallback for testing
    from enum import Enum
    class ErrorCategory(Enum):
        UNKNOWN = "unknown"
        UI = "ui"
        PLATFORM = "platform"
        DOWNLOAD = "download"
        REPOSITORY = "repository"
        SERVICE = "service"
        AUTHENTICATION = "authentication"
        PERMISSION = "permission"
        FILE_SYSTEM = "file_system"
        PARSING = "parsing"
        INTEGRATION = "integration"
        FATAL = "fatal"


class RecoveryAction(Enum):
    """Available recovery actions that can be taken"""
    RETRY = "retry"
    RETRY_WITH_DELAY = "retry_with_delay"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    FALLBACK_RESOURCE = "fallback_resource"
    FALLBACK_METHOD = "fallback_method"
    RESET_STATE = "reset_state"
    CLEAR_CACHE = "clear_cache"
    RELOAD_CONFIG = "reload_config"
    PROMPT_USER = "prompt_user"
    REQUEST_PERMISSION = "request_permission"
    ESCALATE_TO_ADMIN = "escalate_to_admin"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    ABORT_OPERATION = "abort_operation"
    RESTART_SERVICE = "restart_service"
    CONTACT_SUPPORT = "contact_support"


class RecoveryResult(Enum):
    """Possible outcomes of recovery attempts"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    SKIPPED = "skipped"
    USER_INTERVENTION_REQUIRED = "user_intervention_required"
    ESCALATED = "escalated"


@dataclass
class RecoveryStep:
    """Individual step in a recovery plan"""
    action: RecoveryAction
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 30
    required: bool = True
    condition: Optional[Callable[[Any], bool]] = None
    
    def should_execute(self, context: 'RecoveryContext') -> bool:
        """Check if this step should be executed based on conditions"""
        if self.condition is None:
            return True
        return self.condition(context)


@dataclass
class RecoveryPlan:
    """Structured recovery plan with ordered steps"""
    category: ErrorCategory
    steps: List[RecoveryStep]
    max_attempts: int = 3
    total_timeout_seconds: int = 300
    allow_partial_success: bool = True
    description: str = ""
    
    def get_applicable_steps(self, context: 'RecoveryContext') -> List[RecoveryStep]:
        """Get steps that should be executed based on current context"""
        return [step for step in self.steps if step.should_execute(context)]


@dataclass
class RecoveryContext:
    """Context information for recovery execution"""
    error_info: 'ErrorInfo'
    original_operation: str
    operation_parameters: Dict[str, Any] = field(default_factory=dict)
    attempt_count: int = 0
    previous_results: List[RecoveryResult] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    user_context: Optional[Dict[str, Any]] = None
    resource_state: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def elapsed_time(self) -> timedelta:
        """Get elapsed time since recovery started"""
        return datetime.now() - self.start_time
    
    @property
    def has_failed_before(self) -> bool:
        """Check if recovery has failed in previous attempts"""
        return RecoveryResult.FAILED in self.previous_results
    
    @property
    def has_user_intervention(self) -> bool:
        """Check if user intervention was previously required"""
        return RecoveryResult.USER_INTERVENTION_REQUIRED in self.previous_results


@dataclass
class RecoveryExecutionResult:
    """Result of executing a recovery plan"""
    success: bool
    result: RecoveryResult
    steps_executed: List[RecoveryStep]
    steps_results: List[RecoveryResult]
    execution_time: timedelta
    error_message: Optional[str] = None
    recovered_data: Optional[Any] = None
    
    @property
    def partial_success(self) -> bool:
        """Check if recovery achieved partial success"""
        return self.result == RecoveryResult.PARTIAL_SUCCESS


class RecoveryExecutor:
    """Main class for executing recovery plans"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.logger = logging.getLogger(__name__)
        self.recovery_handlers: Dict[RecoveryAction, Callable] = {}
        self._setup_default_handlers()
    
    def _setup_default_handlers(self):
        """Setup default recovery action handlers"""
        self.recovery_handlers.update({
            RecoveryAction.RETRY: self._handle_retry,
            RecoveryAction.RETRY_WITH_DELAY: self._handle_retry_with_delay,
            RecoveryAction.RETRY_WITH_BACKOFF: self._handle_retry_with_backoff,
            RecoveryAction.FALLBACK_RESOURCE: self._handle_fallback_resource,
            RecoveryAction.FALLBACK_METHOD: self._handle_fallback_method,
            RecoveryAction.RESET_STATE: self._handle_reset_state,
            RecoveryAction.CLEAR_CACHE: self._handle_clear_cache,
            RecoveryAction.RELOAD_CONFIG: self._handle_reload_config,
            RecoveryAction.PROMPT_USER: self._handle_prompt_user,
            RecoveryAction.REQUEST_PERMISSION: self._handle_request_permission,
            RecoveryAction.ESCALATE_TO_ADMIN: self._handle_escalate_to_admin,
            RecoveryAction.GRACEFUL_DEGRADATION: self._handle_graceful_degradation,
            RecoveryAction.ABORT_OPERATION: self._handle_abort_operation,
            RecoveryAction.RESTART_SERVICE: self._handle_restart_service,
            RecoveryAction.CONTACT_SUPPORT: self._handle_contact_support,
        })
    
    def register_handler(self, action: RecoveryAction, handler: Callable):
        """Register a custom handler for a recovery action"""
        self.recovery_handlers[action] = handler
    
    def execute_plan(self, plan: RecoveryPlan, context: RecoveryContext) -> RecoveryExecutionResult:
        """Execute a recovery plan"""
        start_time = datetime.now()
        steps_executed = []
        steps_results = []
        
        try:
            self.logger.info(f"Starting recovery plan for {plan.category.value}: {plan.description}")
            
            applicable_steps = plan.get_applicable_steps(context)
            
            for step in applicable_steps:
                if context.elapsed_time.total_seconds() > plan.total_timeout_seconds:
                    self.logger.warning(f"Recovery plan timeout exceeded ({plan.total_timeout_seconds}s)")
                    break
                
                step_result = self._execute_step(step, context)
                steps_executed.append(step)
                steps_results.append(step_result)
                
                # Check if step was successful
                if step_result == RecoveryResult.SUCCESS:
                    self.logger.info(f"Recovery step successful: {step.description}")
                    if not plan.allow_partial_success:
                        # If we don't allow partial success, return immediately on first success
                        execution_time = datetime.now() - start_time
                        return RecoveryExecutionResult(
                            success=True,
                            result=RecoveryResult.SUCCESS,
                            steps_executed=steps_executed,
                            steps_results=steps_results,
                            execution_time=execution_time
                        )
                elif step_result == RecoveryResult.USER_INTERVENTION_REQUIRED:
                    execution_time = datetime.now() - start_time
                    return RecoveryExecutionResult(
                        success=False,
                        result=RecoveryResult.USER_INTERVENTION_REQUIRED,
                        steps_executed=steps_executed,
                        steps_results=steps_results,
                        execution_time=execution_time
                    )
                elif step.required and step_result == RecoveryResult.FAILED:
                    self.logger.error(f"Required recovery step failed: {step.description}")
                    if not plan.allow_partial_success:
                        execution_time = datetime.now() - start_time
                        return RecoveryExecutionResult(
                            success=False,
                            result=RecoveryResult.FAILED,
                            steps_executed=steps_executed,
                            steps_results=steps_results,
                            execution_time=execution_time
                        )
            
            # Determine overall result
            if RecoveryResult.SUCCESS in steps_results:
                if RecoveryResult.FAILED in steps_results:
                    result = RecoveryResult.PARTIAL_SUCCESS
                else:
                    result = RecoveryResult.SUCCESS
                success = True
            elif RecoveryResult.PARTIAL_SUCCESS in steps_results:
                result = RecoveryResult.PARTIAL_SUCCESS
                success = True
            else:
                result = RecoveryResult.FAILED
                success = False
            
            execution_time = datetime.now() - start_time
            return RecoveryExecutionResult(
                success=success,
                result=result,
                steps_executed=steps_executed,
                steps_results=steps_results,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = datetime.now() - start_time
            self.logger.error(f"Recovery plan execution failed: {str(e)}")
            return RecoveryExecutionResult(
                success=False,
                result=RecoveryResult.FAILED,
                steps_executed=steps_executed,
                steps_results=steps_results,
                execution_time=execution_time,
                error_message=str(e)
            )
    
    def _execute_step(self, step: RecoveryStep, context: RecoveryContext) -> RecoveryResult:
        """Execute a single recovery step"""
        handler = self.recovery_handlers.get(step.action)
        if not handler:
            self.logger.error(f"No handler found for recovery action: {step.action}")
            return RecoveryResult.FAILED
        
        try:
            self.logger.info(f"Executing recovery step: {step.description}")
            return handler(step, context)
        except Exception as e:
            self.logger.error(f"Recovery step failed: {step.description} - {str(e)}")
            return RecoveryResult.FAILED
    
    # Default recovery action handlers
    def _handle_retry(self, step: RecoveryStep, context: RecoveryContext) -> RecoveryResult:
        """Handle simple retry operation"""
        max_retries = step.parameters.get('max_retries', 3)
        if context.attempt_count >= max_retries:
            return RecoveryResult.FAILED
        
        # Simulate retry logic (would be replaced with actual retry implementation)
        self.logger.info(f"Retrying operation: {context.original_operation}")
        time.sleep(0.1)  # Brief delay
        return RecoveryResult.SUCCESS
    
    def _handle_retry_with_delay(self, step: RecoveryStep, context: RecoveryContext) -> RecoveryResult:
        """Handle retry with fixed delay"""
        delay = step.parameters.get('delay_seconds', 1)
        max_retries = step.parameters.get('max_retries', 3)
        
        if context.attempt_count >= max_retries:
            return RecoveryResult.FAILED
        
        self.logger.info(f"Retrying with {delay}s delay: {context.original_operation}")
        time.sleep(delay)
        return RecoveryResult.SUCCESS
    
    def _handle_retry_with_backoff(self, step: RecoveryStep, context: RecoveryContext) -> RecoveryResult:
        """Handle retry with exponential backoff"""
        base_delay = step.parameters.get('base_delay', 1)
        max_delay = step.parameters.get('max_delay', 30)
        backoff_factor = step.parameters.get('backoff_factor', 2)
        max_retries = step.parameters.get('max_retries', 5)
        
        if context.attempt_count >= max_retries:
            return RecoveryResult.FAILED
        
        delay = min(base_delay * (backoff_factor ** context.attempt_count), max_delay)
        self.logger.info(f"Retrying with exponential backoff ({delay}s): {context.original_operation}")
        time.sleep(delay)
        return RecoveryResult.SUCCESS
    
    def _handle_fallback_resource(self, step: RecoveryStep, context: RecoveryContext) -> RecoveryResult:
        """Handle fallback to alternative resource"""
        fallback_resources = step.parameters.get('resources', [])
        if not fallback_resources:
            return RecoveryResult.FAILED
        
        self.logger.info(f"Using fallback resource: {fallback_resources[0]}")
        return RecoveryResult.SUCCESS
    
    def _handle_fallback_method(self, step: RecoveryStep, context: RecoveryContext) -> RecoveryResult:
        """Handle fallback to alternative method"""
        fallback_method = step.parameters.get('method')
        if not fallback_method:
            return RecoveryResult.FAILED
        
        self.logger.info(f"Using fallback method: {fallback_method}")
        return RecoveryResult.SUCCESS
    
    def _handle_reset_state(self, step: RecoveryStep, context: RecoveryContext) -> RecoveryResult:
        """Handle state reset"""
        state_keys = step.parameters.get('state_keys', [])
        self.logger.info(f"Resetting state: {state_keys}")
        
        for key in state_keys:
            if key in context.resource_state:
                del context.resource_state[key]
        
        return RecoveryResult.SUCCESS
    
    def _handle_clear_cache(self, step: RecoveryStep, context: RecoveryContext) -> RecoveryResult:
        """Handle cache clearing"""
        cache_types = step.parameters.get('cache_types', ['all'])
        self.logger.info(f"Clearing cache: {cache_types}")
        return RecoveryResult.SUCCESS
    
    def _handle_reload_config(self, step: RecoveryStep, context: RecoveryContext) -> RecoveryResult:
        """Handle configuration reload"""
        config_sections = step.parameters.get('sections', ['all'])
        self.logger.info(f"Reloading configuration: {config_sections}")
        return RecoveryResult.SUCCESS
    
    def _handle_prompt_user(self, step: RecoveryStep, context: RecoveryContext) -> RecoveryResult:
        """Handle user prompt"""
        message = step.parameters.get('message', 'User intervention required')
        self.logger.info(f"Prompting user: {message}")
        return RecoveryResult.USER_INTERVENTION_REQUIRED
    
    def _handle_request_permission(self, step: RecoveryStep, context: RecoveryContext) -> RecoveryResult:
        """Handle permission request"""
        permission = step.parameters.get('permission', 'unknown')
        self.logger.info(f"Requesting permission: {permission}")
        return RecoveryResult.USER_INTERVENTION_REQUIRED
    
    def _handle_escalate_to_admin(self, step: RecoveryStep, context: RecoveryContext) -> RecoveryResult:
        """Handle escalation to administrator"""
        self.logger.info("Escalating to administrator")
        return RecoveryResult.ESCALATED
    
    def _handle_graceful_degradation(self, step: RecoveryStep, context: RecoveryContext) -> RecoveryResult:
        """Handle graceful degradation"""
        degraded_features = step.parameters.get('features', [])
        self.logger.info(f"Enabling graceful degradation: {degraded_features}")
        return RecoveryResult.PARTIAL_SUCCESS
    
    def _handle_abort_operation(self, step: RecoveryStep, context: RecoveryContext) -> RecoveryResult:
        """Handle operation abort"""
        self.logger.info(f"Aborting operation: {context.original_operation}")
        return RecoveryResult.SUCCESS
    
    def _handle_restart_service(self, step: RecoveryStep, context: RecoveryContext) -> RecoveryResult:
        """Handle service restart"""
        service_name = step.parameters.get('service', 'unknown')
        self.logger.info(f"Restarting service: {service_name}")
        return RecoveryResult.SUCCESS
    
    def _handle_contact_support(self, step: RecoveryStep, context: RecoveryContext) -> RecoveryResult:
        """Handle support contact"""
        self.logger.info("Contacting support")
        return RecoveryResult.ESCALATED


class RecoveryPlanRegistry:
    """Registry for recovery plans by error category"""
    
    def __init__(self):
        self.plans: Dict[ErrorCategory, RecoveryPlan] = {}
        self._setup_default_plans()
    
    def register_plan(self, category: ErrorCategory, plan: RecoveryPlan):
        """Register a recovery plan for an error category"""
        self.plans[category] = plan
    
    def get_plan(self, category: ErrorCategory) -> Optional[RecoveryPlan]:
        """Get recovery plan for an error category"""
        return self.plans.get(category)
    
    def _setup_default_plans(self):
        """Setup default recovery plans for all error categories"""
        # UI Errors
        self.plans[ErrorCategory.UI] = RecoveryPlan(
            category=ErrorCategory.UI,
            description="UI component recovery",
            steps=[
                RecoveryStep(
                    action=RecoveryAction.RESET_STATE,
                    description="Reset UI component state",
                    parameters={'state_keys': ['ui_state', 'form_data']}
                ),
                RecoveryStep(
                    action=RecoveryAction.RETRY,
                    description="Retry UI operation",
                    parameters={'max_retries': 2}
                ),
                RecoveryStep(
                    action=RecoveryAction.GRACEFUL_DEGRADATION,
                    description="Enable simplified UI mode",
                    parameters={'features': ['animations', 'advanced_controls']},
                    required=False
                )
            ]
        )
        
        # Platform Errors
        self.plans[ErrorCategory.PLATFORM] = RecoveryPlan(
            category=ErrorCategory.PLATFORM,
            description="Platform service recovery",
            steps=[
                RecoveryStep(
                    action=RecoveryAction.RETRY_WITH_BACKOFF,
                    description="Retry platform API call",
                    parameters={'max_retries': 5, 'base_delay': 1, 'max_delay': 16}
                ),
                RecoveryStep(
                    action=RecoveryAction.FALLBACK_RESOURCE,
                    description="Use alternative platform endpoint",
                    parameters={'resources': ['backup_api', 'cached_data']},
                    required=False
                ),
                RecoveryStep(
                    action=RecoveryAction.GRACEFUL_DEGRADATION,
                    description="Use limited platform features",
                    parameters={'features': ['platform_integration']},
                    required=False
                )
            ]
        )
        
        # Download Errors
        self.plans[ErrorCategory.DOWNLOAD] = RecoveryPlan(
            category=ErrorCategory.DOWNLOAD,
            description="Download operation recovery",
            steps=[
                RecoveryStep(
                    action=RecoveryAction.RETRY_WITH_DELAY,
                    description="Retry download",
                    parameters={'max_retries': 3, 'delay_seconds': 2}
                ),
                RecoveryStep(
                    action=RecoveryAction.FALLBACK_RESOURCE,
                    description="Try alternative download source",
                    parameters={'resources': ['mirror_1', 'mirror_2']},
                    required=False
                ),
                RecoveryStep(
                    action=RecoveryAction.GRACEFUL_DEGRADATION,
                    description="Offer lower quality download",
                    parameters={'features': ['high_quality']},
                    required=False
                )
            ]
        )
        
        # Repository Errors
        self.plans[ErrorCategory.REPOSITORY] = RecoveryPlan(
            category=ErrorCategory.REPOSITORY,
            description="Data repository recovery",
            steps=[
                RecoveryStep(
                    action=RecoveryAction.RETRY,
                    description="Retry database operation",
                    parameters={'max_retries': 2}
                ),
                RecoveryStep(
                    action=RecoveryAction.CLEAR_CACHE,
                    description="Clear repository cache",
                    parameters={'cache_types': ['query_cache', 'entity_cache']}
                ),
                RecoveryStep(
                    action=RecoveryAction.FALLBACK_RESOURCE,
                    description="Use backup database",
                    parameters={'resources': ['backup_db']},
                    required=False
                )
            ]
        )
        
        # Service Errors
        self.plans[ErrorCategory.SERVICE] = RecoveryPlan(
            category=ErrorCategory.SERVICE,
            description="Service recovery",
            steps=[
                RecoveryStep(
                    action=RecoveryAction.RETRY_WITH_BACKOFF,
                    description="Retry service call",
                    parameters={'max_retries': 3, 'base_delay': 2}
                ),
                RecoveryStep(
                    action=RecoveryAction.RESTART_SERVICE,
                    description="Restart failed service",
                    parameters={'service': 'target_service'},
                    required=False
                ),
                RecoveryStep(
                    action=RecoveryAction.GRACEFUL_DEGRADATION,
                    description="Disable non-essential services",
                    parameters={'features': ['background_services']},
                    required=False
                )
            ]
        )
        
        # Authentication Errors
        self.plans[ErrorCategory.AUTHENTICATION] = RecoveryPlan(
            category=ErrorCategory.AUTHENTICATION,
            description="Authentication recovery",
            steps=[
                RecoveryStep(
                    action=RecoveryAction.CLEAR_CACHE,
                    description="Clear authentication cache",
                    parameters={'cache_types': ['auth_tokens', 'session_data']}
                ),
                RecoveryStep(
                    action=RecoveryAction.PROMPT_USER,
                    description="Request user re-authentication",
                    parameters={'message': 'Please log in again'}
                )
            ]
        )
        
        # Permission Errors
        self.plans[ErrorCategory.PERMISSION] = RecoveryPlan(
            category=ErrorCategory.PERMISSION,
            description="Permission recovery",
            steps=[
                RecoveryStep(
                    action=RecoveryAction.REQUEST_PERMISSION,
                    description="Request required permissions",
                    parameters={'permission': 'file_access'}
                ),
                RecoveryStep(
                    action=RecoveryAction.GRACEFUL_DEGRADATION,
                    description="Operate with limited permissions",
                    parameters={'features': ['file_operations']},
                    required=False
                )
            ]
        )
        
        # File System Errors
        self.plans[ErrorCategory.FILE_SYSTEM] = RecoveryPlan(
            category=ErrorCategory.FILE_SYSTEM,
            description="File system recovery",
            steps=[
                RecoveryStep(
                    action=RecoveryAction.RETRY_WITH_DELAY,
                    description="Retry file operation",
                    parameters={'max_retries': 2, 'delay_seconds': 1}
                ),
                RecoveryStep(
                    action=RecoveryAction.FALLBACK_RESOURCE,
                    description="Use alternative file location",
                    parameters={'resources': ['temp_dir', 'user_dir']},
                    required=False
                )
            ]
        )
        
        # Parsing Errors
        self.plans[ErrorCategory.PARSING] = RecoveryPlan(
            category=ErrorCategory.PARSING,
            description="Data parsing recovery",
            steps=[
                RecoveryStep(
                    action=RecoveryAction.FALLBACK_METHOD,
                    description="Try alternative parser",
                    parameters={'method': 'fallback_parser'}
                ),
                RecoveryStep(
                    action=RecoveryAction.GRACEFUL_DEGRADATION,
                    description="Use partial parsing results",
                    parameters={'features': ['complete_validation']},
                    required=False
                )
            ]
        )
        
        # Integration Errors
        self.plans[ErrorCategory.INTEGRATION] = RecoveryPlan(
            category=ErrorCategory.INTEGRATION,
            description="Integration recovery",
            steps=[
                RecoveryStep(
                    action=RecoveryAction.RETRY_WITH_BACKOFF,
                    description="Retry integration call",
                    parameters={'max_retries': 3, 'base_delay': 5}
                ),
                RecoveryStep(
                    action=RecoveryAction.FALLBACK_RESOURCE,
                    description="Use cached integration data",
                    parameters={'resources': ['cached_data']},
                    required=False
                ),
                RecoveryStep(
                    action=RecoveryAction.GRACEFUL_DEGRADATION,
                    description="Disable integration features",
                    parameters={'features': ['external_integrations']},
                    required=False
                )
            ]
        )
        
        # Fatal Errors
        self.plans[ErrorCategory.FATAL] = RecoveryPlan(
            category=ErrorCategory.FATAL,
            description="Fatal error recovery",
            steps=[
                RecoveryStep(
                    action=RecoveryAction.CONTACT_SUPPORT,
                    description="Contact technical support",
                    parameters={'urgency': 'high'}
                ),
                RecoveryStep(
                    action=RecoveryAction.ABORT_OPERATION,
                    description="Safely abort current operation"
                )
            ]
        )
        
        # Unknown Errors (fallback)
        self.plans[ErrorCategory.UNKNOWN] = RecoveryPlan(
            category=ErrorCategory.UNKNOWN,
            description="Generic error recovery",
            steps=[
                RecoveryStep(
                    action=RecoveryAction.RETRY,
                    description="Generic retry",
                    parameters={'max_retries': 1}
                ),
                RecoveryStep(
                    action=RecoveryAction.CONTACT_SUPPORT,
                    description="Report unknown error",
                    parameters={'urgency': 'medium'},
                    required=False
                )
            ]
        )


# Global recovery plan registry
_recovery_registry = None

def get_recovery_registry() -> RecoveryPlanRegistry:
    """Get the global recovery plan registry"""
    global _recovery_registry
    if _recovery_registry is None:
        _recovery_registry = RecoveryPlanRegistry()
    return _recovery_registry


def get_recovery_plan(category: ErrorCategory) -> Optional[RecoveryPlan]:
    """Get recovery plan for an error category"""
    registry = get_recovery_registry()
    return registry.get_plan(category)


def execute_recovery(error_info, operation: str, **kwargs) -> RecoveryExecutionResult:
    """Convenience function to execute recovery for an error"""
    try:
        category = error_info.category if hasattr(error_info, 'category') else ErrorCategory.UNKNOWN
    except:
        category = ErrorCategory.UNKNOWN
    
    plan = get_recovery_plan(category)
    if not plan:
        # Create a basic plan for unknown categories
        plan = RecoveryPlan(
            category=category,
            description="Basic recovery",
            steps=[
                RecoveryStep(
                    action=RecoveryAction.RETRY,
                    description="Basic retry",
                    parameters={'max_retries': 1}
                )
            ]
        )
    
    context = RecoveryContext(
        error_info=error_info,
        original_operation=operation,
        operation_parameters=kwargs
    )
    
    executor = RecoveryExecutor()
    return executor.execute_plan(plan, context) 