"""
Error Coordination System for Cross-Tab Communication

This module provides comprehensive error coordination capabilities across tabs,
enabling synchronized error handling, user feedback coordination, and
efficient cross-tab error propagation with toast integration.

Designed for subtask 16.3 implementation.
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Union
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from dataclasses import dataclass, asdict
from enum import Enum

from .events import get_event_bus, EventType, ComponentEvent


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error category types"""
    API_ERROR = "api_error"
    NETWORK_ERROR = "network_error"
    VALIDATION_ERROR = "validation_error"
    DOWNLOAD_ERROR = "download_error"
    DATABASE_ERROR = "database_error"
    SYSTEM_ERROR = "system_error"
    USER_ERROR = "user_error"


class ErrorAction(Enum):
    """Recommended error actions"""
    RETRY = "retry"
    IGNORE = "ignore"
    REPORT = "report"
    ESCALATE = "escalate"
    USER_INPUT = "user_input"
    SYSTEM_RESTART = "system_restart"


@dataclass
class ErrorData:
    """Comprehensive error data structure"""
    error_id: str
    error_message: str
    error_category: ErrorCategory
    severity: ErrorSeverity
    source_tab: str
    source_component: str
    timestamp: datetime
    url: Optional[str] = None
    operation_id: Optional[str] = None
    stack_trace: Optional[str] = None
    user_action: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    recommended_action: Optional[ErrorAction] = None
    context_data: Optional[Dict[str, Any]] = None
    resolution_status: str = "unresolved"  # unresolved, resolved, ignored, escalated
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        # Convert enums to strings
        data['error_category'] = self.error_category.value
        data['severity'] = self.severity.value
        if self.recommended_action:
            data['recommended_action'] = self.recommended_action.value
        # Convert datetime to ISO string
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ErrorData':
        """Create from dictionary"""
        # Convert string enums back to enums
        data['error_category'] = ErrorCategory(data['error_category'])
        data['severity'] = ErrorSeverity(data['severity'])
        if data.get('recommended_action'):
            data['recommended_action'] = ErrorAction(data['recommended_action'])
        # Convert ISO string back to datetime
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class ErrorCoordinationManager(QObject):
    """Central error coordination manager for cross-tab error handling"""
    
    # Signals for error events
    error_occurred = pyqtSignal(ErrorData)
    error_resolved = pyqtSignal(str)  # error_id
    error_escalated = pyqtSignal(ErrorData)
    
    def __init__(self):
        super().__init__()
        self.event_bus = get_event_bus()
        self.active_errors: Dict[str, ErrorData] = {}
        self.resolved_errors: Dict[str, ErrorData] = {}
        self.registered_tabs: Dict[str, QObject] = {}
        self.error_handlers: Dict[ErrorCategory, List[Callable]] = {}
        self.sequence_counter = 0
        
        # Error cleanup timer
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self._cleanup_old_errors)
        self.cleanup_timer.start(300000)  # 5 minutes
        
        # Error debouncing to prevent spam
        self.error_debounce: Dict[str, float] = {}
        self.debounce_interval = 2.0  # 2 seconds
        
        self.log_info("Error coordination manager initialized")
    
    def register_tab(self, tab_id: str, tab_instance: QObject) -> None:
        """Register a tab for error coordination"""
        try:
            self.registered_tabs[tab_id] = tab_instance
            self.log_info(f"Registered tab for error coordination: {tab_id}")
        except Exception as e:
            self.log_error(f"Error registering tab {tab_id}: {e}")
    
    def unregister_tab(self, tab_id: str) -> None:
        """Unregister a tab from error coordination"""
        try:
            if tab_id in self.registered_tabs:
                del self.registered_tabs[tab_id]
                self.log_info(f"Unregistered tab from error coordination: {tab_id}")
        except Exception as e:
            self.log_error(f"Error unregistering tab {tab_id}: {e}")
    
    def register_error_handler(self, category: ErrorCategory, handler: Callable[[ErrorData], None]) -> None:
        """Register a custom error handler for specific error categories"""
        if category not in self.error_handlers:
            self.error_handlers[category] = []
        self.error_handlers[category].append(handler)
        self.log_info(f"Registered error handler for category: {category.value}")
    
    def report_error(self, 
                    error_message: str,
                    error_category: ErrorCategory,
                    severity: ErrorSeverity,
                    source_tab: str,
                    source_component: str,
                    url: Optional[str] = None,
                    operation_id: Optional[str] = None,
                    stack_trace: Optional[str] = None,
                    context_data: Optional[Dict[str, Any]] = None,
                    recommended_action: Optional[ErrorAction] = None) -> str:
        """Report an error and coordinate cross-tab handling"""
        try:
            # Generate unique error ID
            error_id = f"error_{self._get_next_sequence()}_{int(time.time())}"
            
            # Check for error debouncing
            debounce_key = f"{source_tab}_{error_category.value}_{error_message[:50]}"
            current_time = time.time()
            
            if debounce_key in self.error_debounce:
                if current_time - self.error_debounce[debounce_key] < self.debounce_interval:
                    self.log_debug(f"Error debounced: {error_message[:50]}...")
                    return ""  # Return empty string for debounced errors
            
            self.error_debounce[debounce_key] = current_time
            
            # Create error data
            error_data = ErrorData(
                error_id=error_id,
                error_message=error_message,
                error_category=error_category,
                severity=severity,
                source_tab=source_tab,
                source_component=source_component,
                timestamp=datetime.now(),
                url=url,
                operation_id=operation_id,
                stack_trace=stack_trace,
                context_data=context_data or {},
                recommended_action=recommended_action or self._determine_recommended_action(error_category, severity)
            )
            
            # Store error
            self.active_errors[error_id] = error_data
            
            # Emit signal
            self.error_occurred.emit(error_data)
            
            # Broadcast error event to all tabs
            self._broadcast_error_event(error_data)
            
            # Execute custom handlers
            self._execute_error_handlers(error_data)
            
            # Show user feedback based on severity
            self._show_user_feedback(error_data)
            
            self.log_info(f"Error reported and coordinated: {error_id}")
            return error_id
            
        except Exception as e:
            self.log_error(f"Error reporting error: {e}")
            return ""
    
    def resolve_error(self, error_id: str, resolution_note: Optional[str] = None) -> bool:
        """Mark an error as resolved"""
        try:
            if error_id in self.active_errors:
                error_data = self.active_errors[error_id]
                error_data.resolution_status = "resolved"
                
                # Move to resolved errors
                self.resolved_errors[error_id] = error_data
                del self.active_errors[error_id]
                
                # Emit signal
                self.error_resolved.emit(error_id)
                
                # Broadcast resolution event
                self._broadcast_error_resolution(error_id, resolution_note)
                
                self.log_info(f"Error resolved: {error_id}")
                return True
            else:
                self.log_warning(f"Error not found for resolution: {error_id}")
                return False
                
        except Exception as e:
            self.log_error(f"Error resolving error {error_id}: {e}")
            return False
    
    def escalate_error(self, error_id: str, escalation_reason: str) -> bool:
        """Escalate an error to higher severity"""
        try:
            if error_id in self.active_errors:
                error_data = self.active_errors[error_id]
                error_data.resolution_status = "escalated"
                error_data.context_data = error_data.context_data or {}
                error_data.context_data['escalation_reason'] = escalation_reason
                
                # Emit signal
                self.error_escalated.emit(error_data)
                
                # Broadcast escalation event
                self._broadcast_error_escalation(error_data, escalation_reason)
                
                self.log_warning(f"Error escalated: {error_id} - {escalation_reason}")
                return True
            else:
                self.log_warning(f"Error not found for escalation: {error_id}")
                return False
                
        except Exception as e:
            self.log_error(f"Error escalating error {error_id}: {e}")
            return False
    
    def get_active_errors(self, tab_id: Optional[str] = None) -> Dict[str, ErrorData]:
        """Get active errors, optionally filtered by tab"""
        if tab_id:
            return {eid: error for eid, error in self.active_errors.items() 
                   if error.source_tab == tab_id}
        return self.active_errors.copy()
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring"""
        try:
            total_active = len(self.active_errors)
            total_resolved = len(self.resolved_errors)
            
            # Count by category
            category_counts = {}
            for error in self.active_errors.values():
                category = error.error_category.value
                category_counts[category] = category_counts.get(category, 0) + 1
            
            # Count by severity
            severity_counts = {}
            for error in self.active_errors.values():
                severity = error.severity.value
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            return {
                'total_active_errors': total_active,
                'total_resolved_errors': total_resolved,
                'errors_by_category': category_counts,
                'errors_by_severity': severity_counts,
                'registered_tabs': list(self.registered_tabs.keys()),
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.log_error(f"Error getting error statistics: {e}")
            return {}
    
    def _broadcast_error_event(self, error_data: ErrorData) -> None:
        """Broadcast error event to all registered tabs"""
        try:
            event_data = {
                'error_id': error_data.error_id,
                'error_message': error_data.error_message,
                'error_category': error_data.error_category.value,
                'severity': error_data.severity.value,
                'source_tab': error_data.source_tab,
                'source_component': error_data.source_component,
                'url': error_data.url,
                'operation_id': error_data.operation_id,
                'recommended_action': error_data.recommended_action.value if error_data.recommended_action else None,
                'context_data': error_data.context_data,
                'timestamp': error_data.timestamp.isoformat()
            }
            
            self.event_bus.emit_event(
                event_type=EventType.API_ERROR,
                source_component="error_coordination_manager",
                data=event_data
            )
            
        except Exception as e:
            self.log_error(f"Error broadcasting error event: {e}")
    
    def _broadcast_error_resolution(self, error_id: str, resolution_note: Optional[str]) -> None:
        """Broadcast error resolution event"""
        try:
            event_data = {
                'error_id': error_id,
                'resolution_status': 'resolved',
                'resolution_note': resolution_note,
                'timestamp': datetime.now().isoformat()
            }
            
            self.event_bus.emit_event(
                event_type=EventType.API_ERROR,
                source_component="error_coordination_manager",
                data=event_data
            )
            
        except Exception as e:
            self.log_error(f"Error broadcasting error resolution: {e}")
    
    def _broadcast_error_escalation(self, error_data: ErrorData, escalation_reason: str) -> None:
        """Broadcast error escalation event"""
        try:
            event_data = {
                'error_id': error_data.error_id,
                'resolution_status': 'escalated',
                'escalation_reason': escalation_reason,
                'original_severity': error_data.severity.value,
                'timestamp': datetime.now().isoformat()
            }
            
            self.event_bus.emit_event(
                event_type=EventType.API_ERROR,
                source_component="error_coordination_manager",
                data=event_data
            )
            
        except Exception as e:
            self.log_error(f"Error broadcasting error escalation: {e}")
    
    def _execute_error_handlers(self, error_data: ErrorData) -> None:
        """Execute custom error handlers for the error category"""
        try:
            if error_data.error_category in self.error_handlers:
                for handler in self.error_handlers[error_data.error_category]:
                    try:
                        handler(error_data)
                    except Exception as e:
                        self.log_error(f"Error in custom error handler: {e}")
        except Exception as e:
            self.log_error(f"Error executing error handlers: {e}")
    
    def _show_user_feedback(self, error_data: ErrorData) -> None:
        """Show appropriate user feedback based on error severity"""
        try:
            # Import toast system
            from .toast_notification import show_toast, ToastType
            
            # Determine toast type based on severity
            if error_data.severity == ErrorSeverity.CRITICAL:
                toast_type = ToastType.ERROR
                duration = 8000  # 8 seconds for critical errors
            elif error_data.severity == ErrorSeverity.HIGH:
                toast_type = ToastType.ERROR
                duration = 6000  # 6 seconds for high severity
            elif error_data.severity == ErrorSeverity.MEDIUM:
                toast_type = ToastType.WARNING
                duration = 4000  # 4 seconds for medium severity
            else:
                toast_type = ToastType.INFO
                duration = 3000  # 3 seconds for low severity
            
            # Format error message for user
            user_message = self._format_user_error_message(error_data)
            
            # Find main window for toast display
            for tab_instance in self.registered_tabs.values():
                if hasattr(tab_instance, 'window'):
                    main_window = tab_instance.window()
                    if main_window:
                        show_toast(main_window, user_message, toast_type, duration)
                        break
            
        except Exception as e:
            self.log_error(f"Error showing user feedback: {e}")
    
    def _format_user_error_message(self, error_data: ErrorData) -> str:
        """Format error message for user display"""
        try:
            # Create user-friendly error message
            if error_data.error_category == ErrorCategory.API_ERROR:
                if "rate limit" in error_data.error_message.lower():
                    return "API Rate Limit\nPlease wait before trying again"
                elif "network" in error_data.error_message.lower():
                    return "Network Error\nCheck your internet connection"
                else:
                    return f"API Error\n{error_data.error_message[:50]}{'...' if len(error_data.error_message) > 50 else ''}"
            
            elif error_data.error_category == ErrorCategory.DOWNLOAD_ERROR:
                return f"Download Failed\n{error_data.error_message[:50]}{'...' if len(error_data.error_message) > 50 else ''}"
            
            elif error_data.error_category == ErrorCategory.VALIDATION_ERROR:
                return f"Invalid Input\n{error_data.error_message[:50]}{'...' if len(error_data.error_message) > 50 else ''}"
            
            else:
                return f"Error\n{error_data.error_message[:50]}{'...' if len(error_data.error_message) > 50 else ''}"
                
        except Exception as e:
            self.log_error(f"Error formatting user error message: {e}")
            return "An error occurred"
    
    def _determine_recommended_action(self, category: ErrorCategory, severity: ErrorSeverity) -> ErrorAction:
        """Determine recommended action based on error category and severity"""
        if severity == ErrorSeverity.CRITICAL:
            return ErrorAction.ESCALATE
        elif category == ErrorCategory.API_ERROR:
            return ErrorAction.RETRY
        elif category == ErrorCategory.NETWORK_ERROR:
            return ErrorAction.RETRY
        elif category == ErrorCategory.VALIDATION_ERROR:
            return ErrorAction.USER_INPUT
        elif category == ErrorCategory.DOWNLOAD_ERROR:
            return ErrorAction.RETRY
        else:
            return ErrorAction.REPORT
    
    def _cleanup_old_errors(self) -> None:
        """Clean up old resolved errors"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=24)  # Keep errors for 24 hours
            
            # Clean up resolved errors
            old_errors = [eid for eid, error in self.resolved_errors.items() 
                         if error.timestamp < cutoff_time]
            
            for error_id in old_errors:
                del self.resolved_errors[error_id]
            
            if old_errors:
                self.log_info(f"Cleaned up {len(old_errors)} old resolved errors")
            
            # Clean up debounce entries
            current_time = time.time()
            old_debounce_keys = [key for key, timestamp in self.error_debounce.items() 
                               if current_time - timestamp > 3600]  # 1 hour
            
            for key in old_debounce_keys:
                del self.error_debounce[key]
                
        except Exception as e:
            self.log_error(f"Error cleaning up old errors: {e}")
    
    def _get_next_sequence(self) -> int:
        """Get next sequence number"""
        self.sequence_counter += 1
        return self.sequence_counter
    
    def log_info(self, message: str) -> None:
        """Log info message"""
        print(f"[ERROR_COORD_INFO] {message}")
    
    def log_warning(self, message: str) -> None:
        """Log warning message"""
        print(f"[ERROR_COORD_WARNING] {message}")
    
    def log_error(self, message: str) -> None:
        """Log error message"""
        print(f"[ERROR_COORD_ERROR] {message}")
    
    def log_debug(self, message: str) -> None:
        """Log debug message"""
        print(f"[ERROR_COORD_DEBUG] {message}")


# Global error coordination manager instance
error_coordination_manager = ErrorCoordinationManager()


# Convenience functions for easy error reporting
def report_api_error(message: str, source_tab: str, source_component: str, 
                    url: Optional[str] = None, severity: ErrorSeverity = ErrorSeverity.MEDIUM) -> str:
    """Convenience function to report API errors"""
    return error_coordination_manager.report_error(
        error_message=message,
        error_category=ErrorCategory.API_ERROR,
        severity=severity,
        source_tab=source_tab,
        source_component=source_component,
        url=url
    )


def report_download_error(message: str, source_tab: str, source_component: str,
                         url: Optional[str] = None, operation_id: Optional[str] = None,
                         severity: ErrorSeverity = ErrorSeverity.MEDIUM) -> str:
    """Convenience function to report download errors"""
    return error_coordination_manager.report_error(
        error_message=message,
        error_category=ErrorCategory.DOWNLOAD_ERROR,
        severity=severity,
        source_tab=source_tab,
        source_component=source_component,
        url=url,
        operation_id=operation_id
    )


def report_validation_error(message: str, source_tab: str, source_component: str,
                           context_data: Optional[Dict[str, Any]] = None,
                           severity: ErrorSeverity = ErrorSeverity.LOW) -> str:
    """Convenience function to report validation errors"""
    return error_coordination_manager.report_error(
        error_message=message,
        error_category=ErrorCategory.VALIDATION_ERROR,
        severity=severity,
        source_tab=source_tab,
        source_component=source_component,
        context_data=context_data
    ) 