"""
User Feedback Mechanisms for Error Handling System

This module provides user-friendly error messages and feedback mechanisms
that translate technical errors into clear, actionable communication for end users.
"""

import re
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

from data.models.error_management import ErrorInfo, ErrorCategory, ErrorSeverity, ErrorContext


class MessageDetailLevel(Enum):
    """Detail levels for user messages"""
    MINIMAL = "minimal"      # Brief, essential information only
    STANDARD = "standard"    # Balanced detail for most users
    DETAILED = "detailed"    # Comprehensive information for power users


class MessageType(Enum):
    """Types of user message presentation"""
    INLINE = "inline"        # Inline validation errors
    MODAL = "modal"          # Modal/dialog for blocking issues
    TOAST = "toast"          # Toast/notification for background processes
    STATUS = "status"        # Status page for system-wide issues
    BANNER = "banner"        # Banner for important announcements


class UserRole(Enum):
    """User roles for context-aware messaging"""
    END_USER = "end_user"           # Regular application users
    POWER_USER = "power_user"       # Advanced users who want more details
    DEVELOPER = "developer"         # Developers/technical users
    ADMINISTRATOR = "administrator" # System administrators


@dataclass
class UserMessage:
    """Structured user message with multiple detail levels"""
    title: str
    message: str
    action_text: Optional[str] = None
    action_url: Optional[str] = None
    technical_details: Optional[str] = None
    error_code: Optional[str] = None
    severity_icon: Optional[str] = None
    severity_color: Optional[str] = None
    help_url: Optional[str] = None
    contact_support: bool = False
    retry_available: bool = False
    auto_retry: bool = False


@dataclass
class UserContext:
    """User context for personalized messaging"""
    user_role: UserRole = UserRole.END_USER
    detail_level: MessageDetailLevel = MessageDetailLevel.STANDARD
    language: str = "en"
    accessibility_mode: bool = False
    previous_errors: List[str] = None
    current_operation: Optional[str] = None
    user_preferences: Optional[Dict[str, Any]] = None


class MessageTemplate:
    """Template for generating user messages"""
    
    def __init__(self, category: ErrorCategory):
        self.category = category
        self.templates = self._get_templates_for_category(category)
    
    def _get_templates_for_category(self, category: ErrorCategory) -> Dict[str, Dict[str, str]]:
        """Get message templates for specific error category"""
        templates = {
            ErrorCategory.UI: {
                "title": "Interface Issue",
                "minimal": "Something went wrong with the interface. Please try again.",
                "standard": "We encountered an issue with the user interface. This might be due to a temporary glitch or an invalid action.",
                "detailed": "A user interface error occurred. This could be caused by invalid form data, UI component failure, or browser compatibility issues.",
                "action": "Try refreshing the page or checking your input",
                "help_url": "/help/ui-issues"
            },
            ErrorCategory.PLATFORM: {
                "title": "Service Connection Issue",
                "minimal": "Can't connect to the video service. Please try again later.",
                "standard": "We're having trouble connecting to the video platform. This might be due to temporary service issues or network problems.",
                "detailed": "Failed to communicate with the external video platform API. This could be due to rate limiting, service downtime, authentication issues, or network connectivity problems.",
                "action": "Wait a moment and try again",
                "help_url": "/help/platform-issues"
            },
            ErrorCategory.DOWNLOAD: {
                "title": "Download Problem",
                "minimal": "Download failed. Please try again.",
                "standard": "We couldn't download your video. This might be due to network issues, insufficient storage space, or the video being unavailable.",
                "detailed": "The download process failed due to network connectivity issues, insufficient disk space, file permission problems, or the source video being removed or restricted.",
                "action": "Check your internet connection and available storage space",
                "help_url": "/help/download-issues"
            },
            ErrorCategory.REPOSITORY: {
                "title": "Data Storage Issue",
                "minimal": "Problem saving your data. Please try again.",
                "standard": "We encountered an issue while saving your information. This might be a temporary database problem.",
                "detailed": "A database or data storage error occurred. This could be due to connection issues, data validation failures, storage constraints, or database maintenance.",
                "action": "Try again in a moment",
                "help_url": "/help/data-issues"
            },
            ErrorCategory.SERVICE: {
                "title": "Service Error",
                "minimal": "Service temporarily unavailable. Please try again.",
                "standard": "One of our services is experiencing issues. This might be due to high traffic or temporary maintenance.",
                "detailed": "A business logic or service layer error occurred. This could be due to service overload, configuration issues, dependency failures, or scheduled maintenance.",
                "action": "Please wait a moment and try again",
                "help_url": "/help/service-issues"
            },
            ErrorCategory.AUTHENTICATION: {
                "title": "Authentication Required",
                "minimal": "Please log in to continue.",
                "standard": "You need to be logged in to perform this action. Please sign in with your account.",
                "detailed": "Authentication failed or expired. This could be due to invalid credentials, session timeout, or account access restrictions.",
                "action": "Sign in to your account",
                "help_url": "/help/login-issues"
            },
            ErrorCategory.PERMISSION: {
                "title": "Access Denied",
                "minimal": "You don't have permission for this action.",
                "standard": "You don't have the necessary permissions to perform this action. Contact your administrator if you believe this is an error.",
                "detailed": "Insufficient permissions to access the requested resource or perform the specified operation. This could be due to role restrictions, account limitations, or security policies.",
                "action": "Contact your administrator for access",
                "help_url": "/help/permissions"
            },
            ErrorCategory.FILE_SYSTEM: {
                "title": "File System Error",
                "minimal": "Problem with file operations. Please try again.",
                "standard": "We encountered an issue while working with files on your system. This might be due to permissions or storage problems.",
                "detailed": "File system operation failed. This could be due to insufficient permissions, disk space limitations, file locks, or corrupted file system structures.",
                "action": "Check file permissions and available storage space",
                "help_url": "/help/file-issues"
            },
            ErrorCategory.PARSING: {
                "title": "Data Format Issue",
                "minimal": "Invalid data format. Please check your input.",
                "standard": "The data you provided couldn't be processed. Please check the format and try again.",
                "detailed": "Data parsing or validation failed. This could be due to invalid file format, corrupted data, unsupported encoding, or malformed input structure.",
                "action": "Verify your data format and try again",
                "help_url": "/help/format-issues"
            },
            ErrorCategory.INTEGRATION: {
                "title": "Integration Error",
                "minimal": "Problem connecting to external service.",
                "standard": "We're having trouble connecting to an external service. This might be temporary.",
                "detailed": "Integration with external system failed. This could be due to API changes, service downtime, authentication issues, or configuration problems.",
                "action": "Try again later or contact support",
                "help_url": "/help/integration-issues"
            },
            ErrorCategory.FATAL: {
                "title": "Critical System Error",
                "minimal": "Critical error occurred. Please contact support.",
                "standard": "A critical system error has occurred. Our team has been notified and is working to resolve this issue.",
                "detailed": "A fatal system error occurred that requires immediate attention. This could be due to system corruption, critical resource exhaustion, or severe configuration issues.",
                "action": "Contact support immediately",
                "help_url": "/help/critical-errors"
            }
        }
        
        # Default template for unknown categories
        default_template = {
            "title": "Unexpected Error",
            "minimal": "An unexpected error occurred. Please try again.",
            "standard": "We encountered an unexpected issue. Please try again or contact support if the problem persists.",
            "detailed": "An unhandled error occurred in the system. This could be due to unexpected conditions, software bugs, or system instability.",
            "action": "Try again or contact support",
            "help_url": "/help/general-issues"
        }
        
        return templates.get(category, default_template)
    
    def generate_message(self, error_info: ErrorInfo, user_context: UserContext) -> UserMessage:
        """Generate user message based on error info and user context"""
        template = self.templates
        
        # Select appropriate detail level
        detail_level = user_context.detail_level.value
        message_text = template.get(detail_level, template.get("standard", "An error occurred."))
        
        # Customize message based on specific error type
        if error_info.error_type:
            message_text = self._customize_for_error_type(message_text, error_info.error_type)
        
        # Add context-specific information
        if error_info.context and error_info.context.operation:
            message_text = self._add_operation_context(message_text, error_info.context.operation)
        
        # Determine severity presentation
        severity_icon, severity_color = self._get_severity_presentation(error_info.severity)
        
        # Determine if retry is available
        retry_available = error_info.recovery_strategy and "retry" in error_info.recovery_strategy.value.lower()
        auto_retry = retry_available and error_info.severity in [ErrorSeverity.LOW, ErrorSeverity.MEDIUM]
        
        # Determine if support contact is needed
        contact_support = error_info.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]
        
        # Generate technical details for power users and developers
        technical_details = None
        if user_context.detail_level == MessageDetailLevel.DETAILED or user_context.user_role in [UserRole.DEVELOPER, UserRole.ADMINISTRATOR]:
            technical_details = self._generate_technical_details(error_info)
        
        return UserMessage(
            title=template["title"],
            message=message_text,
            action_text=template.get("action"),
            technical_details=technical_details,
            error_code=error_info.error_code,
            severity_icon=severity_icon,
            severity_color=severity_color,
            help_url=template.get("help_url"),
            contact_support=contact_support,
            retry_available=retry_available,
            auto_retry=auto_retry
        )
    
    def _customize_for_error_type(self, message: str, error_type: str) -> str:
        """Customize message based on specific error type"""
        customizations = {
            "NETWORK_TIMEOUT": "The connection timed out. Please check your internet connection.",
            "INVALID_URL": "The URL you provided is not valid. Please check the link and try again.",
            "FILE_NOT_FOUND": "The requested file could not be found.",
            "PERMISSION_DENIED": "You don't have permission to access this resource.",
            "RATE_LIMIT_EXCEEDED": "Too many requests. Please wait a moment before trying again.",
            "AUTHENTICATION_FAILED": "Login failed. Please check your credentials.",
            "VALIDATION_ERROR": "The information you provided is not valid. Please check your input.",
            "DISK_SPACE_FULL": "Not enough storage space available. Please free up some space and try again.",
            "COMPONENT_FAILURE": "A system component is not responding properly."
        }
        
        if error_type in customizations:
            return customizations[error_type]
        
        return message
    
    def _add_operation_context(self, message: str, operation: str) -> str:
        """Add operation-specific context to message"""
        operation_contexts = {
            "download": "while downloading your video",
            "upload": "while uploading your file",
            "login": "while signing you in",
            "save": "while saving your data",
            "delete": "while deleting the item",
            "search": "while searching",
            "validate": "while validating your input",
            "process": "while processing your request"
        }
        
        context = operation_contexts.get(operation.lower(), f"while performing {operation}")
        return f"{message} This happened {context}."
    
    def _get_severity_presentation(self, severity: ErrorSeverity) -> Tuple[str, str]:
        """Get icon and color for severity level"""
        presentations = {
            ErrorSeverity.LOW: ("ℹ️", "#2196F3"),      # Blue - Info
            ErrorSeverity.MEDIUM: ("⚠️", "#FF9800"),   # Orange - Warning
            ErrorSeverity.HIGH: ("❌", "#F44336"),     # Red - Error
            ErrorSeverity.CRITICAL: ("🚨", "#D32F2F")  # Dark Red - Critical
        }
        
        return presentations.get(severity, ("❓", "#757575"))  # Gray - Unknown
    
    def _generate_technical_details(self, error_info: ErrorInfo) -> str:
        """Generate technical details for advanced users"""
        details = []
        
        details.append(f"Error ID: {error_info.error_id}")
        details.append(f"Error Code: {error_info.error_code}")
        details.append(f"Category: {error_info.category.value}")
        details.append(f"Severity: {error_info.severity.value}")
        
        if error_info.error_type:
            details.append(f"Type: {error_info.error_type}")
        
        if error_info.component:
            details.append(f"Component: {error_info.component}")
        
        if error_info.context:
            if error_info.context.operation:
                details.append(f"Operation: {error_info.context.operation}")
            if error_info.context.entity_type:
                details.append(f"Entity: {error_info.context.entity_type}")
        
        if error_info.recovery_strategy:
            details.append(f"Recovery: {error_info.recovery_strategy.value}")
        
        details.append(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return " | ".join(details)


class UserFeedbackManager:
    """Central manager for user feedback and messaging"""
    
    def __init__(self):
        self.templates = {}
        self.default_context = UserContext()
        self._initialize_templates()
    
    def _initialize_templates(self):
        """Initialize message templates for all error categories"""
        for category in ErrorCategory:
            self.templates[category] = MessageTemplate(category)
    
    def generate_user_message(
        self, 
        error_info: ErrorInfo, 
        user_context: Optional[UserContext] = None,
        message_type: MessageType = MessageType.MODAL
    ) -> UserMessage:
        """Generate user-friendly message from error info"""
        if user_context is None:
            user_context = self.default_context
        
        # Get appropriate template
        template = self.templates.get(error_info.category)
        if not template:
            template = self.templates[ErrorCategory.UNKNOWN]  # Fallback
        
        # Generate base message
        message = template.generate_message(error_info, user_context)
        
        # Customize for message type
        message = self._customize_for_message_type(message, message_type)
        
        return message
    
    def _customize_for_message_type(self, message: UserMessage, message_type: MessageType) -> UserMessage:
        """Customize message based on presentation type"""
        if message_type == MessageType.TOAST:
            # Toast messages should be brief
            if len(message.message) > 100:
                message.message = message.message[:97] + "..."
            message.technical_details = None  # No technical details in toasts
        
        elif message_type == MessageType.INLINE:
            # Inline messages should be concise and actionable
            message.title = None  # No title for inline messages
            if message.action_text:
                message.message += f" {message.action_text}."
        
        elif message_type == MessageType.BANNER:
            # Banner messages for system-wide issues
            if message.contact_support:
                message.message += " Our team is working to resolve this issue."
        
        return message
    
    def get_recovery_suggestions(self, error_info: ErrorInfo) -> List[str]:
        """Get specific recovery suggestions for an error"""
        suggestions = []
        
        # Category-specific suggestions
        category_suggestions = {
            ErrorCategory.DOWNLOAD: [
                "Check your internet connection",
                "Ensure you have enough storage space",
                "Try downloading at a different time",
                "Verify the video URL is still valid"
            ],
            ErrorCategory.PLATFORM: [
                "Wait a few minutes and try again",
                "Check if the platform is experiencing issues",
                "Verify your account permissions",
                "Try using a different video URL"
            ],
            ErrorCategory.UI: [
                "Refresh the page",
                "Clear your browser cache",
                "Try using a different browser",
                "Check if JavaScript is enabled"
            ],
            ErrorCategory.AUTHENTICATION: [
                "Check your username and password",
                "Reset your password if needed",
                "Clear browser cookies and try again",
                "Contact support if account is locked"
            ],
            ErrorCategory.FILE_SYSTEM: [
                "Check file permissions",
                "Ensure sufficient disk space",
                "Try saving to a different location",
                "Close other applications that might be using the file"
            ]
        }
        
        suggestions.extend(category_suggestions.get(error_info.category, []))
        
        # Severity-specific suggestions
        if error_info.severity == ErrorSeverity.CRITICAL:
            suggestions.append("Contact support immediately for assistance")
        elif error_info.severity == ErrorSeverity.HIGH:
            suggestions.append("If the problem persists, please contact support")
        
        # Recovery strategy suggestions
        if error_info.recovery_strategy:
            strategy_suggestions = {
                "retry": "The system will automatically retry this operation",
                "fallback": "An alternative method will be attempted",
                "user_input": "Please provide additional information to continue",
                "escalate": "This issue has been escalated to our technical team"
            }
            
            strategy_text = strategy_suggestions.get(error_info.recovery_strategy.value.lower())
            if strategy_text:
                suggestions.append(strategy_text)
        
        return suggestions[:5]  # Limit to 5 suggestions
    
    def format_for_accessibility(self, message: UserMessage) -> Dict[str, str]:
        """Format message for accessibility (screen readers, etc.)"""
        accessible_format = {
            "aria_label": f"Error: {message.title}",
            "role": "alert",
            "aria_live": "assertive" if message.severity_color == "#F44336" else "polite",
            "description": message.message
        }
        
        if message.action_text:
            accessible_format["action_description"] = f"Suggested action: {message.action_text}"
        
        if message.technical_details:
            accessible_format["technical_summary"] = f"Technical details available: {message.error_code}"
        
        return accessible_format
    
    def get_localized_message(self, message: UserMessage, language: str = "en") -> UserMessage:
        """Get localized version of message (placeholder for future implementation)"""
        # This would integrate with a localization system
        # For now, return the original message
        return message
    
    def should_show_technical_details(self, user_context: UserContext, error_info: ErrorInfo) -> bool:
        """Determine if technical details should be shown to user"""
        # Always show for developers and administrators
        if user_context.user_role in [UserRole.DEVELOPER, UserRole.ADMINISTRATOR]:
            return True
        
        # Show for power users on high/critical errors
        if user_context.user_role == UserRole.POWER_USER and error_info.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            return True
        
        # Show if user explicitly requested detailed level
        if user_context.detail_level == MessageDetailLevel.DETAILED:
            return True
        
        return False


# Global feedback manager instance
_feedback_manager: Optional[UserFeedbackManager] = None


def get_feedback_manager() -> UserFeedbackManager:
    """Get global feedback manager instance"""
    global _feedback_manager
    if _feedback_manager is None:
        _feedback_manager = UserFeedbackManager()
    return _feedback_manager


def generate_user_friendly_message(
    error_info: ErrorInfo,
    user_role: UserRole = UserRole.END_USER,
    detail_level: MessageDetailLevel = MessageDetailLevel.STANDARD,
    message_type: MessageType = MessageType.MODAL
) -> UserMessage:
    """Convenience function to generate user-friendly error message"""
    user_context = UserContext(
        user_role=user_role,
        detail_level=detail_level
    )
    
    manager = get_feedback_manager()
    return manager.generate_user_message(error_info, user_context, message_type)


def get_error_recovery_suggestions(error_info: ErrorInfo) -> List[str]:
    """Convenience function to get recovery suggestions"""
    manager = get_feedback_manager()
    return manager.get_recovery_suggestions(error_info) 