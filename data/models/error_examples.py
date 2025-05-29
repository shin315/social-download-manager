"""
Error Management Usage Examples for Social Download Manager v2.0

Demonstrates error handling patterns, custom error handlers,
recovery strategies, and monitoring capabilities.
"""

import logging
from typing import Optional

from .base import EntityId
from .downloads import DownloadModel, DownloadStatus
from .download_repositories import get_download_repository
from .error_management import (
    ErrorManager, ErrorContext, ErrorHandlingContext,
    IErrorHandler, ErrorInfo, ErrorCategory, ErrorSeverity, RecoveryStrategy,
    RepositoryDatabaseError, RepositoryValidationError, RepositoryConnectionError,
    handle_repository_errors, get_error_manager
)


def example_basic_error_handling():
    """Example: Basic error handling with try-catch"""
    download_repo = get_download_repository()
    
    try:
        # Try to find a non-existent download
        download = download_repo.find_by_id(99999)
        print(f"Found download: {download}")
        
        # Try to save invalid data
        invalid_download = DownloadModel(
            content_id="",  # Invalid empty content_id
            url="not-a-valid-url",
            status=DownloadStatus.QUEUED,
            file_path=""
        )
        saved = download_repo.save(invalid_download)
        print(f"Saved invalid download: {saved}")
        
    except RepositoryValidationError as e:
        print(f"Validation Error: {e.message}")
        print(f"Field: {e.field}, Value: {e.value}")
        print(f"Error ID: {e.error_info.error_id}")
        
    except RepositoryDatabaseError as e:
        print(f"Database Error: {e.message}")
        print(f"Category: {e.error_info.category.value}")
        print(f"Severity: {e.error_info.severity.value}")
        print(f"Is Retryable: {e.error_info.is_retryable}")
        
    except Exception as e:
        print(f"Unexpected error: {e}")


def example_error_context_usage():
    """Example: Using error context for better error information"""
    download_repo = get_download_repository()
    
    with ErrorHandlingContext("create_test_download", entity_type="DownloadModel") as ctx:
        # Simulate database error
        invalid_download = DownloadModel(
            content_id=None,  # This will cause validation error
            url="https://example.com/test.mp4",
            status=DownloadStatus.QUEUED,
            file_path="/downloads/test.mp4"
        )
        
        try:
            saved = download_repo.save(invalid_download)
        except Exception as e:
            print(f"Error occurred in context: {ctx.context.operation}")
            print(f"Entity type: {ctx.context.entity_type}")
            raise


@handle_repository_errors("custom_operation")
def example_decorator_usage(download_id: EntityId):
    """Example: Using decorator for automatic error handling"""
    download_repo = get_download_repository()
    
    # This method is automatically wrapped with error handling
    download = download_repo.find_by_id(download_id)
    if not download:
        raise ValueError(f"Download not found: {download_id}")
    
    # Simulate processing that might fail
    if download.status == DownloadStatus.FAILED:
        raise RuntimeError("Cannot process failed download")
    
    return download


class CustomRetryHandler(IErrorHandler):
    """Custom error handler for network timeout errors"""
    
    def can_handle(self, error: Exception, context: ErrorContext) -> bool:
        error_str = str(error).lower()
        return "timeout" in error_str or "connection" in error_str
    
    def handle_error(self, error: Exception, context: ErrorContext) -> ErrorInfo:
        return ErrorInfo(
            error_id=f"CUSTOM_RETRY_{hash(str(error))}",
            error_code="NETWORK_TIMEOUT",
            message=f"Network timeout in {context.operation}: {str(error)}",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            original_exception=error,
            recovery_strategy=RecoveryStrategy.RETRY,
            is_retryable=True,
            max_retries=5  # More retries for network issues
        )


def example_custom_error_handler():
    """Example: Adding custom error handler"""
    error_manager = get_error_manager()
    
    # Add custom handler
    custom_handler = CustomRetryHandler()
    error_manager.add_handler(custom_handler)
    
    # Simulate network error
    context = ErrorContext("download_content", entity_id="test-123")
    
    try:
        # This would normally be a real network operation
        raise ConnectionError("Connection timeout after 30 seconds")
        
    except Exception as e:
        error_info = error_manager.handle_error(e, context)
        
        print(f"Custom handler result:")
        print(f"Error ID: {error_info.error_id}")
        print(f"Error Code: {error_info.error_code}")
        print(f"Recovery Strategy: {error_info.recovery_strategy.value}")
        print(f"Max Retries: {error_info.max_retries}")
        print(f"Is Retryable: {error_info.is_retryable}")


def example_error_recovery():
    """Example: Error recovery with retry logic"""
    error_manager = get_error_manager()
    download_repo = get_download_repository()
    
    def risky_operation():
        """Simulated operation that fails randomly"""
        import random
        if random.random() < 0.7:  # 70% chance of failure
            raise ConnectionError("Network timeout")
        
        # Success case
        download = DownloadModel(
            content_id="retry-test-001",
            url="https://example.com/retry-test.mp4",
            status=DownloadStatus.QUEUED,
            file_path="/downloads/retry-test.mp4"
        )
        return download_repo.save(download)
    
    context = ErrorContext("risky_download_operation")
    
    try:
        # Execute with automatic retry
        result = error_manager.execute_with_retry(risky_operation, context, max_retries=3)
        print(f"Operation succeeded after retries: {result.id if result else 'None'}")
        
    except Exception as e:
        print(f"Operation failed after all retries: {e}")


def example_error_statistics():
    """Example: Error statistics and monitoring"""
    error_manager = get_error_manager()
    
    # Clear previous statistics
    error_manager.clear_statistics()
    
    # Simulate various errors
    contexts = [
        ErrorContext("operation_1"),
        ErrorContext("operation_2"),
        ErrorContext("operation_3")
    ]
    
    errors = [
        ValueError("Invalid input data"),
        ConnectionError("Network timeout"),
        RuntimeError("Processing failed"),
        TypeError("Type mismatch"),
        ConnectionError("Another network issue")
    ]
    
    # Handle various errors
    for context, error in zip(contexts, errors):
        try:
            error_info = error_manager.handle_error(error, context)
            print(f"Handled error: {error_info.error_code}")
        except Exception:
            pass
    
    # Get statistics
    stats = error_manager.get_error_statistics()
    print("\nError Statistics:")
    for key, count in stats.items():
        print(f"  {key}: {count}")


def example_business_logic_errors():
    """Example: Business logic error handling"""
    download_repo = get_download_repository()
    
    try:
        # Try to create a download with business logic violation
        # (e.g., duplicate content_id)
        download1 = DownloadModel(
            content_id="duplicate-test",
            url="https://example.com/test1.mp4",
            status=DownloadStatus.QUEUED,
            file_path="/downloads/test1.mp4"
        )
        saved1 = download_repo.save(download1)
        print(f"First download saved: {saved1.id}")
        
        # Try to save duplicate content_id
        download2 = DownloadModel(
            content_id="duplicate-test",  # Same content_id
            url="https://example.com/test2.mp4",
            status=DownloadStatus.QUEUED,
            file_path="/downloads/test2.mp4"
        )
        saved2 = download_repo.save(download2)
        print(f"Second download saved: {saved2.id}")
        
    except RepositoryDatabaseError as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            print(f"Business logic violation: Duplicate content_id not allowed")
            print(f"Error details: {e.error_info.message}")
        else:
            print(f"Database error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


def example_error_logging():
    """Example: Error logging configuration"""
    # Configure logging for error management
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('error_management.log')
        ]
    )
    
    error_manager = get_error_manager()
    download_repo = get_download_repository()
    
    # Create various scenarios that will be logged
    scenarios = [
        ("Critical database error", lambda: None),  # Would be a real critical error
        ("Validation error", lambda: download_repo.save(DownloadModel(content_id="", url="", status=DownloadStatus.QUEUED, file_path=""))),
        ("Network timeout", lambda: None)  # Would be a real network error
    ]
    
    for description, operation in scenarios:
        try:
            print(f"\nTesting: {description}")
            if operation():
                operation()
        except Exception as e:
            print(f"Error logged: {type(e).__name__}: {e}")


def run_all_error_examples():
    """Run all error management examples"""
    print("=== Error Management Examples for Social Download Manager ===\n")
    
    examples = [
        ("Basic Error Handling", example_basic_error_handling),
        ("Error Context Usage", example_error_context_usage),
        ("Decorator Usage", lambda: example_decorator_usage("test-123")),
        ("Custom Error Handler", example_custom_error_handler),
        ("Error Recovery", example_error_recovery),
        ("Error Statistics", example_error_statistics),
        ("Business Logic Errors", example_business_logic_errors),
        ("Error Logging", example_error_logging)
    ]
    
    for name, example_func in examples:
        try:
            print(f"\n{name}:")
            print("-" * (len(name) + 1))
            example_func()
            print()
        except Exception as e:
            print(f"Example '{name}' failed: {e}")
            print()
    
    print("All error management examples completed!")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    run_all_error_examples() 