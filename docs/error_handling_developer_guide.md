# Error Handling Developer Guide

## Table of Contents
- [Quick Start](#quick-start)
- [Usage Examples](#usage-examples)
- [Best Practices](#best-practices)
- [API Documentation](#api-documentation)
- [Integration Instructions](#integration-instructions)
- [Code Samples](#code-samples)
- [Troubleshooting](#troubleshooting)
- [Testing Guidelines](#testing-guidelines)

## Quick Start

### 1. Basic Error Handling
```python
from core.component_error_handlers import handle_ui_error

def my_ui_function():
    try:
        # Your UI code here
        result = risky_ui_operation()
        return result
    except Exception as e:
        # Handle error with context
        handled = handle_ui_error(e, "my_ui_function", context={'user_action': 'button_click'})
        if not handled:
            raise  # Re-raise if not handled
        return None  # Return appropriate fallback value
```

### 2. Using Decorators
```python
from core.component_error_handlers import component_error_handler
from data.models.error_management import ErrorCategory

@component_error_handler("download_service", ErrorCategory.DOWNLOAD)
def download_video(url, destination):
    # Your download code here
    # Errors will be automatically handled
    pass
```

### 3. Context Manager
```python
from core.global_error_handler import error_boundary

def process_file(file_path):
    with error_boundary("file_processing"):
        # File processing code
        # Errors will be caught and processed
        data = open(file_path).read()
        return process_data(data)
```

## Usage Examples

### Component-Specific Error Handling

#### UI Component Errors
```python
from core.component_error_handlers import handle_ui_error
import tkinter as tk

class VideoPlayerUI:
    def __init__(self):
        self.root = tk.Tk()
        self.setup_ui()
    
    def play_video_handler(self):
        try:
            video_path = self.get_selected_video()
            self.play_video(video_path)
        except Exception as e:
            # UI-specific error handling
            handled = handle_ui_error(
                e, 
                "play_video", 
                context={
                    'widget': 'play_button',
                    'video_path': video_path,
                    'user_action': 'play_video'
                }
            )
            if handled:
                # Show user-friendly error message
                self.show_error_message("Unable to play video. Please try again.")
            else:
                # Escalate to global handler
                raise
```

#### Platform Service Errors
```python
from core.component_error_handlers import handle_platform_error
import requests

class TikTokService:
    def fetch_video_info(self, video_url):
        try:
            response = requests.get(f"https://api.tiktok.com/video/{video_url}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            # Platform-specific error handling
            handled = handle_platform_error(
                e,
                "fetch_video_info",
                context={
                    'platform': 'tiktok',
                    'video_url': video_url,
                    'endpoint': 'video_info'
                }
            )
            if handled:
                # Return cached data or default response
                return self.get_cached_video_info(video_url)
            else:
                raise
```

#### Download Service Errors
```python
from core.component_error_handlers import handle_download_error
import os
import shutil

class DownloadManager:
    def download_file(self, url, destination_path):
        try:
            # Download implementation
            response = requests.get(url, stream=True)
            with open(destination_path, 'wb') as f:
                shutil.copyfileobj(response.raw, f)
            return destination_path
        except (OSError, IOError, requests.RequestException) as e:
            # Download-specific error handling
            handled = handle_download_error(
                e,
                "download_file",
                context={
                    'url': url,
                    'destination': destination_path,
                    'file_size': response.headers.get('content-length'),
                    'disk_space': shutil.disk_usage(os.path.dirname(destination_path)).free
                }
            )
            if handled:
                # Try alternative download location
                alternative_path = self.get_alternative_download_path()
                return self.download_file(url, alternative_path)
            else:
                raise
```

#### Repository/Database Errors
```python
from core.component_error_handlers import handle_repository_error
import sqlite3

class VideoRepository:
    def save_video_metadata(self, video_data):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO videos (url, title, duration) VALUES (?, ?, ?)",
                    (video_data['url'], video_data['title'], video_data['duration'])
                )
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            # Repository-specific error handling
            handled = handle_repository_error(
                e,
                "save_video_metadata",
                context={
                    'table': 'videos',
                    'operation': 'insert',
                    'data_size': len(str(video_data)),
                    'db_path': self.db_path
                }
            )
            if handled:
                # Queue for later save or use backup storage
                self.queue_for_later_save(video_data)
                return None
            else:
                raise
```

### Advanced Usage Patterns

#### Custom Error Patterns
```python
from core.component_error_handlers import ComponentErrorConfig, ComponentErrorHandler
from data.models.error_management import ErrorCategory, ErrorSeverity

class CustomVideoProcessingHandler(ComponentErrorHandler):
    def __init__(self):
        config = ComponentErrorConfig(
            component_name="video_processor",
            error_category=ErrorCategory.PERFORMANCE,
            error_patterns={
                'MemoryError': 'reduce_quality',
                'TimeoutError': 'retry_with_smaller_chunks',
                'CodecError': 'try_alternative_codec'
            },
            fallback_actions=['use_default_settings', 'notify_user']
        )
        super().__init__(config)
    
    def _apply_component_handling(self, error_info, error_context):
        if 'MemoryError' in str(error_info.message):
            # Custom handling for memory errors
            return self._handle_memory_error(error_context)
        return super()._apply_component_handling(error_info, error_context)
    
    def _handle_memory_error(self, error_context):
        # Implement custom memory error handling
        return {'success': True, 'action_taken': 'reduced_quality'}
```

#### Validation Decorators
```python
from core.component_error_handlers import validate_input, require_non_null

@validate_input(
    url=lambda x: x.startswith(('http://', 'https://')),
    quality=lambda x: x in ['low', 'medium', 'high']
)
@require_non_null('url', 'destination')
def download_with_validation(url, destination, quality='medium'):
    # Function implementation
    # Input validation errors will be handled automatically
    pass
```

#### Error Recovery Strategies
```python
from core.recovery_engine import execute_auto_recovery
from core.error_categorization import ErrorClassifier

def robust_api_call(endpoint, data):
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            return make_api_call(endpoint, data)
        except Exception as e:
            if attempt == max_attempts - 1:
                # Final attempt - use auto recovery
                classifier = ErrorClassifier()
                error_info = classifier.classify_error(e, "api_service")
                
                recovery_result = execute_auto_recovery(
                    error_info, 
                    "api_service",
                    error_context={'endpoint': endpoint, 'attempt': attempt}
                )
                
                if recovery_result.success:
                    return recovery_result.result
                else:
                    raise
            else:
                # Retry with delay
                time.sleep(2 ** attempt)  # Exponential backoff
```

## Best Practices

### 1. Error Handling Strategy

#### DO ✅
- **Use appropriate component handlers** for different types of errors
- **Provide meaningful context** when handling errors
- **Log errors consistently** using the established logging system
- **Handle errors as close to the source** as possible
- **Use decorators** for common error handling patterns
- **Provide fallback mechanisms** for critical operations
- **Test error scenarios** thoroughly

```python
# Good: Comprehensive error handling with context
try:
    result = download_video(url)
except Exception as e:
    handled = handle_download_error(
        e, 
        "download_video",
        context={
            'url': url,
            'user_id': current_user.id,
            'download_location': settings.download_path,
            'available_space': get_disk_space()
        }
    )
    if not handled:
        # Escalate with additional context
        logger.error(f"Failed to handle download error for user {current_user.id}")
        raise
```

#### DON'T ❌
- **Don't silently catch and ignore errors**
- **Don't use generic exception handling** for specific components
- **Don't skip logging** important error information
- **Don't hardcode error messages** - use the feedback system
- **Don't handle errors too far** from where they occur

```python
# Bad: Silent error handling without context
try:
    result = download_video(url)
except:
    pass  # Silent failure - no logging, no recovery, no user feedback
```

### 2. Error Context

#### Provide Rich Context
```python
# Good: Rich error context
context = {
    'user_id': user.id,
    'operation': 'video_download',
    'video_url': url,
    'file_size': expected_size,
    'available_space': disk_space,
    'network_status': check_network(),
    'retry_count': current_retry,
    'timestamp': datetime.now().isoformat()
}

handled = handle_download_error(error, "download_video", context=context)
```

#### Include Relevant Technical Details
```python
# Good: Technical context for debugging
context = {
    'function': 'process_video_metadata',
    'video_codec': video_info.get('codec'),
    'video_duration': video_info.get('duration'),
    'file_format': video_info.get('format'),
    'processing_stage': current_stage,
    'memory_usage': get_memory_usage(),
    'cpu_usage': get_cpu_usage()
}
```

### 3. Component Selection

#### Choose the Right Handler
```python
# UI Operations
handle_ui_error(error, operation, context)

# Platform API Calls
handle_platform_error(error, operation, context)

# File Operations
handle_download_error(error, operation, context)

# Database Operations
handle_repository_error(error, operation, context)
```

### 4. Testing Error Scenarios

#### Test Different Error Types
```python
def test_download_error_scenarios():
    # Test permission errors
    with mock.patch('builtins.open', side_effect=PermissionError("Access denied")):
        result = download_manager.download_file(test_url, protected_path)
        assert result is None  # Should handle gracefully
    
    # Test disk space errors
    with mock.patch('shutil.disk_usage', return_value=(0, 0, 0)):  # No free space
        result = download_manager.download_file(test_url, test_path)
        assert result is not None  # Should find alternative location
    
    # Test network errors
    with mock.patch('requests.get', side_effect=ConnectionError("Network error")):
        result = download_manager.download_file(test_url, test_path)
        # Should retry or use cached version
```

## API Documentation

### Core Functions

#### `handle_ui_error(exception, operation, context=None, user_data=None)`
Handle UI component errors with specialized UI recovery strategies.

**Parameters:**
- `exception` (Exception): The exception that occurred
- `operation` (str): Name of the operation that failed
- `context` (dict, optional): Additional context information
- `user_data` (dict, optional): User-specific data

**Returns:**
- `bool`: True if error was handled successfully, False if escalation needed

**Example:**
```python
handled = handle_ui_error(
    AttributeError("Widget not found"),
    "button_click",
    context={'widget_id': 'submit_btn', 'form_data': form.data}
)
```

#### `handle_platform_error(exception, operation, context=None, user_data=None)`
Handle platform service errors with retry and fallback mechanisms.

**Parameters:** Same as `handle_ui_error`

**Returns:** `bool`

**Example:**
```python
handled = handle_platform_error(
    requests.ConnectionError("API timeout"),
    "fetch_video_info",
    context={'platform': 'tiktok', 'video_id': video_id}
)
```

#### `handle_download_error(exception, operation, context=None, user_data=None)`
Handle download service errors with disk space and permission management.

**Parameters:** Same as `handle_ui_error`

**Returns:** `bool`

#### `handle_repository_error(exception, operation, context=None, user_data=None)`
Handle database/repository errors with transaction management and fallback storage.

**Parameters:** Same as `handle_ui_error`

**Returns:** `bool`

### Decorators

#### `@component_error_handler(component_name, category, **config)`
Automatically handle errors for a function using component-specific logic.

**Parameters:**
- `component_name` (str): Name of the component
- `category` (ErrorCategory): Error category for this component
- `**config`: Additional configuration options

**Example:**
```python
@component_error_handler("video_processor", ErrorCategory.PERFORMANCE)
def process_video(video_path):
    # Processing logic
    pass
```

#### `@validate_input(**validators)`
Validate function inputs with custom validation rules.

**Parameters:**
- `**validators`: Dictionary of parameter names to validation functions

**Example:**
```python
@validate_input(
    email=lambda x: '@' in x,
    age=lambda x: 0 <= x <= 150
)
def create_user(email, age):
    pass
```

#### `@require_non_null(*param_names)`
Ensure specified parameters are not None.

**Parameters:**
- `*param_names`: Names of parameters that must not be None

**Example:**
```python
@require_non_null('user_id', 'video_url')
def save_user_video(user_id, video_url, metadata=None):
    pass
```

### Context Managers

#### `error_boundary(operation_name)`
Create an error boundary for a block of code.

**Parameters:**
- `operation_name` (str): Name of the operation for logging/tracking

**Example:**
```python
with error_boundary("video_conversion"):
    converted_video = convert_video(input_file, output_format)
```

## Integration Instructions

### 1. Adding Error Handling to Existing Components

#### Step 1: Identify Component Type
Determine which component handler is most appropriate:
- **UI Components** → `handle_ui_error`
- **Platform APIs** → `handle_platform_error`
- **File Operations** → `handle_download_error`
- **Database Operations** → `handle_repository_error`

#### Step 2: Wrap Critical Operations
```python
# Before
def critical_operation():
    result = risky_function()
    return result

# After
def critical_operation():
    try:
        result = risky_function()
        return result
    except Exception as e:
        handled = handle_appropriate_error(e, "critical_operation")
        if not handled:
            raise
        return None  # or appropriate fallback
```

#### Step 3: Add Context Information
```python
def enhanced_operation(user_id, video_url):
    try:
        result = risky_function(video_url)
        return result
    except Exception as e:
        context = {
            'user_id': user_id,
            'video_url': video_url,
            'operation_time': datetime.now(),
            'system_state': get_system_state()
        }
        handled = handle_appropriate_error(e, "enhanced_operation", context=context)
        if not handled:
            raise
        return None
```

### 2. Creating Custom Component Handlers

#### Step 1: Define Configuration
```python
from core.component_error_handlers import ComponentErrorConfig
from data.models.error_management import ErrorCategory

config = ComponentErrorConfig(
    component_name="my_custom_component",
    error_category=ErrorCategory.CUSTOM,  # Add to enum if needed
    error_patterns={
        'CustomError': 'handle_custom_way',
        'SpecialException': 'special_handling'
    },
    fallback_actions=['reset_component', 'notify_admin']
)
```

#### Step 2: Implement Handler
```python
from core.component_error_handlers import ComponentErrorHandler

class MyCustomHandler(ComponentErrorHandler):
    def __init__(self):
        super().__init__(config)
    
    def _apply_component_handling(self, error_info, error_context):
        # Custom handling logic
        if self._is_recoverable_error(error_info):
            return self._attempt_recovery(error_context)
        
        return super()._apply_component_handling(error_info, error_context)
    
    def _is_recoverable_error(self, error_info):
        # Custom recovery logic
        return error_info.severity != ErrorSeverity.CRITICAL
    
    def _attempt_recovery(self, error_context):
        # Implement recovery
        return {'success': True, 'action_taken': 'custom_recovery'}
```

#### Step 3: Register Handler
```python
from core.component_error_handlers import register_component_handler

my_handler = MyCustomHandler()
register_component_handler("my_custom_component", my_handler)
```

### 3. Global Error Handler Setup

#### Initialize in Application Startup
```python
from core.global_error_handler import install_global_error_handlers
from core.component_error_handlers import initialize_component_handlers

def initialize_error_handling():
    # Initialize component handlers
    component_handlers = initialize_component_handlers()
    
    # Install global exception hooks
    install_global_error_handlers()
    
    print(f"Error handling initialized with {len(component_handlers)} component handlers")

# Call during application startup
initialize_error_handling()
```

## Code Samples

### Complete Example: Video Download Manager

```python
from core.component_error_handlers import (
    handle_download_error, handle_platform_error, 
    component_error_handler, validate_input
)
from data.models.error_management import ErrorCategory
import requests
import os
import shutil

class VideoDownloadManager:
    def __init__(self):
        self.download_path = "downloads/"
        os.makedirs(self.download_path, exist_ok=True)
    
    @validate_input(url=lambda x: x.startswith(('http://', 'https://')))
    @component_error_handler("download_manager", ErrorCategory.DOWNLOAD)
    def download_video(self, url, quality='medium'):
        """Download video with comprehensive error handling"""
        
        # Step 1: Get video information
        video_info = self._get_video_info(url)
        if not video_info:
            return None
        
        # Step 2: Prepare download
        filename = self._generate_filename(video_info)
        file_path = os.path.join(self.download_path, filename)
        
        # Step 3: Check disk space
        if not self._check_disk_space(video_info.get('size', 0)):
            return None
        
        # Step 4: Download file
        return self._download_file(video_info['download_url'], file_path)
    
    def _get_video_info(self, url):
        """Get video information from platform API"""
        try:
            # Determine platform
            platform = self._detect_platform(url)
            api_url = f"https://api.{platform}.com/video/info"
            
            response = requests.get(api_url, params={'url': url}, timeout=30)
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            # Platform-specific error handling
            handled = handle_platform_error(
                e,
                "get_video_info",
                context={
                    'platform': platform,
                    'url': url,
                    'api_endpoint': api_url
                }
            )
            if handled:
                # Try cached information or alternative API
                return self._get_cached_video_info(url)
            return None
    
    def _download_file(self, download_url, file_path):
        """Download file with error handling"""
        try:
            response = requests.get(download_url, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            return file_path
            
        except (requests.RequestException, OSError, IOError) as e:
            # Download-specific error handling
            handled = handle_download_error(
                e,
                "download_file",
                context={
                    'download_url': download_url,
                    'file_path': file_path,
                    'file_size': response.headers.get('content-length'),
                    'bytes_downloaded': os.path.getsize(file_path) if os.path.exists(file_path) else 0
                }
            )
            if handled:
                # Try alternative download method or location
                return self._try_alternative_download(download_url, file_path)
            return None
    
    def _check_disk_space(self, required_size):
        """Check if enough disk space is available"""
        try:
            free_space = shutil.disk_usage(self.download_path).free
            return free_space > required_size * 1.1  # 10% buffer
        except OSError:
            return False
    
    def _detect_platform(self, url):
        """Detect platform from URL"""
        if 'tiktok.com' in url:
            return 'tiktok'
        elif 'youtube.com' in url or 'youtu.be' in url:
            return 'youtube'
        return 'unknown'
    
    def _generate_filename(self, video_info):
        """Generate safe filename from video info"""
        title = video_info.get('title', 'video')
        # Sanitize filename
        safe_title = ''.join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        return f"{safe_title}.mp4"
    
    def _get_cached_video_info(self, url):
        """Get cached video information (fallback)"""
        # Implementation for cached data
        return None
    
    def _try_alternative_download(self, download_url, file_path):
        """Try alternative download method (fallback)"""
        # Implementation for alternative download
        return None

# Usage example
downloader = VideoDownloadManager()
result = downloader.download_video("https://tiktok.com/video/123", quality='high')
if result:
    print(f"Downloaded: {result}")
else:
    print("Download failed")
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Import Errors
**Problem:** Cannot import error handling modules
```
ImportError: No module named 'core.error_categorization'
```

**Solution:**
- Ensure project root is in Python path
- Check if all required modules exist
- Verify file permissions

#### 2. Handler Not Working
**Problem:** Errors not being handled by component handlers

**Debug Steps:**
```python
# Check if handler is registered
from core.component_error_handlers import get_component_handler
handler = get_component_handler('ui')
print(f"UI Handler: {handler}")

# Check handler configuration
if handler:
    print(f"Config: {handler.config}")
    print(f"Error patterns: {handler.config.error_patterns}")
```

#### 3. Logging Issues
**Problem:** Errors not appearing in logs

**Debug Steps:**
```python
# Check logger configuration
from core.logging_strategy import get_error_logger
logger = get_error_logger()
print(f"Logger: {logger}")
print(f"Log level: {logger.logger.level}")

# Test logging directly
from data.models.error_management import ErrorInfo, ErrorCategory, ErrorSeverity
test_error = ErrorInfo(
    error_id="test",
    category=ErrorCategory.UI,
    severity=ErrorSeverity.MEDIUM,
    message="Test error"
)
logger.log_error(test_error)
```

#### 4. Recovery Not Working
**Problem:** Auto-recovery mechanisms not functioning

**Debug Steps:**
```python
# Test recovery system
from core.recovery_engine import execute_auto_recovery
from core.error_categorization import ErrorClassifier

classifier = ErrorClassifier()
test_error = ValueError("Test error")
error_info = classifier.classify_error(test_error, "test_component")

recovery_result = execute_auto_recovery(error_info, "test_component")
print(f"Recovery result: {recovery_result}")
```

#### 5. Performance Issues
**Problem:** Error handling causing performance degradation

**Solutions:**
- Check log level configuration (set to WARNING or ERROR in production)
- Ensure asynchronous logging is enabled
- Monitor error frequency and implement circuit breakers
- Review error context size (avoid large objects)

#### 6. Memory Leaks
**Problem:** Memory usage increasing over time

**Solutions:**
- Clear old error contexts regularly
- Check for circular references in error objects
- Monitor error handler statistics
- Implement proper cleanup in custom handlers

### Debug Mode

Enable detailed debugging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable error handler debugging
from core.component_error_handlers import ComponentErrorHandler
ComponentErrorHandler._debug_mode = True

# Enable global handler debugging
from core.global_error_handler import get_global_error_handler
handler = get_global_error_handler()
handler.debug_mode = True
```

## Testing Guidelines

### Unit Testing Error Handlers

```python
import unittest
from unittest.mock import Mock, patch
from core.component_error_handlers import handle_ui_error

class TestUIErrorHandler(unittest.TestCase):
    def test_basic_error_handling(self):
        """Test basic UI error handling"""
        error = ValueError("Test UI error")
        result = handle_ui_error(error, "test_operation")
        self.assertIsInstance(result, bool)
    
    def test_error_with_context(self):
        """Test UI error handling with context"""
        error = AttributeError("Widget not found")
        context = {'widget': 'button', 'user_action': 'click'}
        result = handle_ui_error(error, "button_click", context=context)
        self.assertIsInstance(result, bool)
    
    @patch('core.error_categorization.ErrorClassifier')
    def test_error_classification(self, mock_classifier):
        """Test error classification integration"""
        # Setup mock
        mock_classifier.return_value.classify_error.return_value = Mock()
        
        error = RuntimeError("Test error")
        result = handle_ui_error(error, "test_operation")
        
        # Verify classification was called
        mock_classifier.return_value.classify_error.assert_called_once()
```

### Integration Testing

```python
class TestErrorHandlingIntegration(unittest.TestCase):
    def setUp(self):
        """Setup test environment"""
        from core.component_error_handlers import initialize_component_handlers
        self.handlers = initialize_component_handlers()
    
    def test_end_to_end_error_flow(self):
        """Test complete error handling flow"""
        # Simulate application error
        error = ConnectionError("Network error")
        
        # Process through component handler
        handled = handle_platform_error(error, "api_call")
        
        # Verify handling
        self.assertTrue(handled)
        
        # Check logs (if applicable)
        # Check user feedback (if applicable)
        # Check recovery attempts (if applicable)
```

This developer guide provides comprehensive information for integrating and using the error handling system effectively. Follow these guidelines to ensure robust error handling throughout your application. 