"""
Error Categorization Module - Bridge to Error Management

This module serves as a bridge to import error categorization components
from the main error management module, providing the expected import path
for error classification functionality.
"""

# Import all error categorization components from the main error management module
from data.models.error_management import (
    ErrorCategory,
    ErrorSeverity,
    RecoveryStrategy,
    ErrorContext,
    ErrorInfo,
    DomainError,
    ErrorClassifier,
)

# For convenience, provide direct access to classifier methods
classify_error = ErrorClassifier.classify_error
get_specific_error_type = ErrorClassifier.get_specific_error_type
determine_severity = ErrorClassifier.determine_severity
determine_recovery_strategy = ErrorClassifier.determine_recovery_strategy

# Re-export for easy access
__all__ = [
    'ErrorCategory',
    'ErrorSeverity', 
    'RecoveryStrategy',
    'ErrorContext',
    'ErrorInfo',
    'DomainError',
    'classify_error',
    'get_specific_error_type',
    'determine_severity',
    'determine_recovery_strategy',
    'ErrorClassifier',
] 