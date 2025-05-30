"""
Enhanced Logging Strategy for Error Management System

This module provides a comprehensive logging strategy that integrates with the error
categorization system to capture detailed error information for diagnostics and monitoring.
"""

import logging
import logging.handlers
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import re
from contextlib import contextmanager

from data.models.error_management import ErrorInfo, ErrorCategory, ErrorSeverity, ErrorContext
from core.constants import LogConstants


class LogLevel(Enum):
    """Enhanced log levels for different types of information"""
    TRACE = "TRACE"      # Detailed execution flow
    DEBUG = "DEBUG"      # Debug information
    INFO = "INFO"        # General information
    WARNING = "WARNING"  # Warning conditions
    ERROR = "ERROR"      # Error conditions
    CRITICAL = "CRITICAL" # Critical errors
    AUDIT = "AUDIT"      # Audit trail


class LogDestination(Enum):
    """Available log destinations"""
    FILE = "file"
    CONSOLE = "console"
    DATABASE = "database"
    CLOUD = "cloud"
    MEMORY = "memory"


class SensitiveDataType(Enum):
    """Types of sensitive data to protect in logs"""
    PASSWORD = "password"
    API_KEY = "api_key"
    TOKEN = "token"
    EMAIL = "email"
    PHONE = "phone"
    CREDIT_CARD = "credit_card"
    SSN = "ssn"
    IP_ADDRESS = "ip_address"
    USER_ID = "user_id"


@dataclass
class LogEntry:
    """Structured log entry with comprehensive information"""
    timestamp: str
    level: str
    logger_name: str
    message: str
    request_id: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    component: Optional[str] = None
    operation: Optional[str] = None
    error_category: Optional[str] = None
    error_type: Optional[str] = None
    error_code: Optional[str] = None
    severity: Optional[str] = None
    recovery_strategy: Optional[str] = None
    stack_trace: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    performance_metrics: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), default=str, ensure_ascii=False)


class SensitiveDataFilter:
    """Filter to protect sensitive data in logs"""
    
    def __init__(self):
        self.patterns = {
            SensitiveDataType.PASSWORD: [
                r'password["\s]*[:=]["\s]*([^"\s,}]+)',
                r'pwd["\s]*[:=]["\s]*([^"\s,}]+)',
                r'pass["\s]*[:=]["\s]*([^"\s,}]+)'
            ],
            SensitiveDataType.API_KEY: [
                r'api[_-]?key["\s]*[:=]["\s]*([^"\s,}]+)',
                r'apikey["\s]*[:=]["\s]*([^"\s,}]+)',
                r'key["\s]*[:=]["\s]*([A-Za-z0-9]{20,})'
            ],
            SensitiveDataType.TOKEN: [
                r'token["\s]*[:=]["\s]*([^"\s,}]+)',
                r'bearer["\s]+([A-Za-z0-9._-]+)',
                r'jwt["\s]*[:=]["\s]*([^"\s,}]+)'
            ],
            SensitiveDataType.EMAIL: [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            ],
            SensitiveDataType.PHONE: [
                r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
                r'\b\(\d{3}\)\s*\d{3}[-.]?\d{4}\b'
            ],
            SensitiveDataType.CREDIT_CARD: [
                r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
            ],
            SensitiveDataType.IP_ADDRESS: [
                r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
            ]
        }
        
        self.replacement_text = {
            SensitiveDataType.PASSWORD: "[PASSWORD_REDACTED]",
            SensitiveDataType.API_KEY: "[API_KEY_REDACTED]",
            SensitiveDataType.TOKEN: "[TOKEN_REDACTED]",
            SensitiveDataType.EMAIL: "[EMAIL_REDACTED]",
            SensitiveDataType.PHONE: "[PHONE_REDACTED]",
            SensitiveDataType.CREDIT_CARD: "[CARD_REDACTED]",
            SensitiveDataType.IP_ADDRESS: "[IP_REDACTED]"
        }
    
    def filter_message(self, message: str) -> str:
        """Filter sensitive data from log message"""
        filtered_message = message
        
        for data_type, patterns in self.patterns.items():
            replacement = self.replacement_text.get(data_type, "[REDACTED]")
            for pattern in patterns:
                filtered_message = re.sub(pattern, replacement, filtered_message, flags=re.IGNORECASE)
        
        return filtered_message
    
    def filter_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Filter sensitive data from context dictionary"""
        if not context:
            return context
        
        filtered_context = {}
        sensitive_keys = ['password', 'pwd', 'pass', 'api_key', 'apikey', 'token', 'secret']
        
        for key, value in context.items():
            if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
                filtered_context[key] = "[REDACTED]"
            elif isinstance(value, str):
                filtered_context[key] = self.filter_message(value)
            elif isinstance(value, dict):
                filtered_context[key] = self.filter_context(value)
            else:
                filtered_context[key] = value
        
        return filtered_context


class PerformanceMetrics:
    """Track performance metrics for logging"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.memory_usage = None
        self.cpu_usage = None
    
    def start(self):
        """Start performance tracking"""
        self.start_time = time.time()
    
    def stop(self):
        """Stop performance tracking"""
        self.end_time = time.time()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        metrics = {}
        
        if self.start_time and self.end_time:
            metrics['execution_time_ms'] = round((self.end_time - self.start_time) * 1000, 2)
        
        # Add memory and CPU metrics if available
        try:
            import psutil
            process = psutil.Process()
            metrics['memory_mb'] = round(process.memory_info().rss / 1024 / 1024, 2)
            metrics['cpu_percent'] = process.cpu_percent()
        except ImportError:
            pass
        
        return metrics


class LogBuffer:
    """Thread-safe log buffer for asynchronous logging"""
    
    def __init__(self, max_size: int = 1000):
        self.buffer: List[LogEntry] = []
        self.max_size = max_size
        self.lock = threading.Lock()
    
    def add(self, entry: LogEntry):
        """Add log entry to buffer"""
        with self.lock:
            self.buffer.append(entry)
            if len(self.buffer) > self.max_size:
                self.buffer.pop(0)  # Remove oldest entry
    
    def flush(self) -> List[LogEntry]:
        """Flush buffer and return all entries"""
        with self.lock:
            entries = self.buffer.copy()
            self.buffer.clear()
            return entries
    
    def get_recent(self, count: int = 10) -> List[LogEntry]:
        """Get recent log entries"""
        with self.lock:
            return self.buffer[-count:] if len(self.buffer) >= count else self.buffer.copy()


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging"""
    
    def __init__(self, include_context: bool = True, include_performance: bool = False):
        super().__init__()
        self.include_context = include_context
        self.include_performance = include_performance
        self.sensitive_filter = SensitiveDataFilter()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        # Get request ID from thread local storage or generate new one
        request_id = getattr(record, 'request_id', str(uuid.uuid4()))
        
        # Create structured log entry
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=record.levelname,
            logger_name=record.name,
            message=self.sensitive_filter.filter_message(record.getMessage()),
            request_id=request_id,
            session_id=getattr(record, 'session_id', None),
            user_id=getattr(record, 'user_id', None),
            component=getattr(record, 'component', None),
            operation=getattr(record, 'operation', None),
            error_category=getattr(record, 'error_category', None),
            error_type=getattr(record, 'error_type', None),
            error_code=getattr(record, 'error_code', None),
            severity=getattr(record, 'severity', None),
            recovery_strategy=getattr(record, 'recovery_strategy', None),
            stack_trace=self.formatException(record.exc_info) if record.exc_info else None,
            context=self.sensitive_filter.filter_context(getattr(record, 'context', {})),
            performance_metrics=getattr(record, 'performance_metrics', {}) if self.include_performance else None,
            tags=getattr(record, 'tags', [])
        )
        
        return entry.to_json()


class EnhancedLogHandler(logging.Handler):
    """Enhanced log handler with buffering and filtering"""
    
    def __init__(self, destination: LogDestination, **kwargs):
        super().__init__()
        self.destination = destination
        self.buffer = LogBuffer()
        self.sensitive_filter = SensitiveDataFilter()
        self.async_logging = kwargs.get('async_logging', True)
        
        # Configure based on destination
        if destination == LogDestination.FILE:
            self.file_path = kwargs.get('file_path', 'logs/app.log')
            self.max_bytes = kwargs.get('max_bytes', 10 * 1024 * 1024)  # 10MB
            self.backup_count = kwargs.get('backup_count', 5)
            self._setup_file_handler()
        elif destination == LogDestination.DATABASE:
            self.db_connection = kwargs.get('db_connection')
            self.table_name = kwargs.get('table_name', 'error_logs')
    
    def _setup_file_handler(self):
        """Setup file handler with rotation"""
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        self.file_handler = logging.handlers.RotatingFileHandler(
            self.file_path,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count
        )
    
    def emit(self, record: logging.LogRecord):
        """Emit log record"""
        try:
            if self.async_logging:
                # Add to buffer for async processing
                entry = self._create_log_entry(record)
                self.buffer.add(entry)
            else:
                # Process immediately
                self._process_record(record)
        except Exception:
            self.handleError(record)
    
    def _create_log_entry(self, record: logging.LogRecord) -> LogEntry:
        """Create structured log entry from record"""
        return LogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=record.levelname,
            logger_name=record.name,
            message=self.sensitive_filter.filter_message(record.getMessage()),
            request_id=getattr(record, 'request_id', str(uuid.uuid4())),
            session_id=getattr(record, 'session_id', None),
            user_id=getattr(record, 'user_id', None),
            component=getattr(record, 'component', None),
            operation=getattr(record, 'operation', None),
            error_category=getattr(record, 'error_category', None),
            error_type=getattr(record, 'error_type', None),
            error_code=getattr(record, 'error_code', None),
            severity=getattr(record, 'severity', None),
            recovery_strategy=getattr(record, 'recovery_strategy', None),
            stack_trace=self.format(record) if record.exc_info else None,
            context=self.sensitive_filter.filter_context(getattr(record, 'context', {})),
            performance_metrics=getattr(record, 'performance_metrics', {}),
            tags=getattr(record, 'tags', [])
        )
    
    def _process_record(self, record: logging.LogRecord):
        """Process log record based on destination"""
        if self.destination == LogDestination.FILE:
            self.file_handler.emit(record)
        elif self.destination == LogDestination.CONSOLE:
            print(self.format(record))
        elif self.destination == LogDestination.DATABASE:
            self._write_to_database(record)
    
    def _write_to_database(self, record: logging.LogRecord):
        """Write log entry to database"""
        # Implementation would depend on database setup
        pass
    
    def flush_buffer(self):
        """Flush buffered log entries"""
        entries = self.buffer.flush()
        for entry in entries:
            # Process each buffered entry
            pass


class LoggingStrategy:
    """Comprehensive logging strategy manager"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._get_default_config()
        self.loggers: Dict[str, logging.Logger] = {}
        self.handlers: List[EnhancedLogHandler] = []
        self.sensitive_filter = SensitiveDataFilter()
        self.performance_tracking = {}
        
        # Setup logging
        self._setup_logging()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default logging configuration"""
        return {
            'level': 'INFO',
            'destinations': [
                {
                    'type': 'file',
                    'path': 'logs/app.log',
                    'level': 'INFO',
                    'max_bytes': 10 * 1024 * 1024,
                    'backup_count': 5
                },
                {
                    'type': 'file',
                    'path': 'logs/error.log',
                    'level': 'ERROR',
                    'max_bytes': 10 * 1024 * 1024,
                    'backup_count': 5
                },
                {
                    'type': 'console',
                    'level': 'WARNING'
                }
            ],
            'format': 'structured',
            'include_context': True,
            'include_performance': True,
            'async_logging': True,
            'sensitive_data_protection': True
        }
    
    def _setup_logging(self):
        """Setup logging based on configuration"""
        # Create log directory
        os.makedirs('logs', exist_ok=True)
        
        # Setup destinations
        for dest_config in self.config['destinations']:
            if dest_config['type'] == 'file':
                handler = EnhancedLogHandler(
                    LogDestination.FILE,
                    file_path=dest_config['path'],
                    max_bytes=dest_config.get('max_bytes', 10 * 1024 * 1024),
                    backup_count=dest_config.get('backup_count', 5),
                    async_logging=self.config.get('async_logging', True)
                )
            elif dest_config['type'] == 'console':
                handler = EnhancedLogHandler(LogDestination.CONSOLE)
            else:
                continue
            
            # Set level
            level = getattr(logging, dest_config['level'].upper())
            handler.setLevel(level)
            
            # Set formatter
            if self.config.get('format') == 'structured':
                formatter = StructuredFormatter(
                    include_context=self.config.get('include_context', True),
                    include_performance=self.config.get('include_performance', True)
                )
            else:
                formatter = logging.Formatter(LogConstants.LOG_FORMAT)
            
            handler.setFormatter(formatter)
            self.handlers.append(handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get or create logger with enhanced capabilities"""
        if name not in self.loggers:
            logger = logging.getLogger(name)
            logger.setLevel(getattr(logging, self.config['level'].upper()))
            
            # Add handlers
            for handler in self.handlers:
                logger.addHandler(handler)
            
            # Prevent duplicate logs
            logger.propagate = False
            
            self.loggers[name] = logger
        
        return self.loggers[name]
    
    def log_error(self, logger_name: str, error_info: ErrorInfo, context: Optional[Dict[str, Any]] = None):
        """Log error with enhanced information"""
        logger = self.get_logger(logger_name)
        
        # Create log record with error information
        extra = {
            'request_id': str(uuid.uuid4()),
            'component': error_info.component,
            'operation': error_info.context.operation if error_info.context else None,
            'error_category': error_info.category.value if error_info.category else None,
            'error_type': error_info.error_type,
            'error_code': error_info.error_code,
            'severity': error_info.severity.value if error_info.severity else None,
            'recovery_strategy': error_info.recovery_strategy.value if error_info.recovery_strategy else None,
            'context': context or {},
            'tags': ['error', error_info.category.value if error_info.category else 'unknown']
        }
        
        # Log with appropriate level
        if error_info.severity == ErrorSeverity.CRITICAL:
            logger.critical(error_info.message, extra=extra, exc_info=error_info.original_exception)
        elif error_info.severity == ErrorSeverity.HIGH:
            logger.error(error_info.message, extra=extra, exc_info=error_info.original_exception)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            logger.warning(error_info.message, extra=extra)
        else:
            logger.info(error_info.message, extra=extra)
    
    @contextmanager
    def performance_context(self, operation: str, component: str = None):
        """Context manager for performance tracking"""
        metrics = PerformanceMetrics()
        metrics.start()
        
        try:
            yield metrics
        finally:
            metrics.stop()
            
            # Log performance metrics
            logger = self.get_logger('performance')
            extra = {
                'request_id': str(uuid.uuid4()),
                'component': component,
                'operation': operation,
                'performance_metrics': metrics.get_metrics(),
                'tags': ['performance']
            }
            
            logger.info(f"Performance metrics for {operation}", extra=extra)
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """Get logging statistics"""
        stats = {
            'total_loggers': len(self.loggers),
            'total_handlers': len(self.handlers),
            'buffer_sizes': {}
        }
        
        for i, handler in enumerate(self.handlers):
            if hasattr(handler, 'buffer'):
                stats['buffer_sizes'][f'handler_{i}'] = len(handler.buffer.buffer)
        
        return stats
    
    def flush_all_buffers(self):
        """Flush all log buffers"""
        for handler in self.handlers:
            if hasattr(handler, 'flush_buffer'):
                handler.flush_buffer()


# Global logging strategy instance
_logging_strategy: Optional[LoggingStrategy] = None


def get_logging_strategy() -> LoggingStrategy:
    """Get global logging strategy instance"""
    global _logging_strategy
    if _logging_strategy is None:
        _logging_strategy = LoggingStrategy()
    return _logging_strategy


def setup_enhanced_logging(config: Optional[Dict[str, Any]] = None) -> LoggingStrategy:
    """Setup enhanced logging with configuration"""
    global _logging_strategy
    _logging_strategy = LoggingStrategy(config)
    return _logging_strategy


def get_enhanced_logger(name: str) -> logging.Logger:
    """Get enhanced logger instance"""
    strategy = get_logging_strategy()
    return strategy.get_logger(name)


def log_error_with_context(logger_name: str, error_info: ErrorInfo, context: Optional[Dict[str, Any]] = None):
    """Log error with enhanced context information"""
    strategy = get_logging_strategy()
    strategy.log_error(logger_name, error_info, context)


# Convenience functions for common logging patterns
def log_operation_start(logger_name: str, operation: str, component: str = None, context: Dict[str, Any] = None):
    """Log operation start"""
    logger = get_enhanced_logger(logger_name)
    extra = {
        'request_id': str(uuid.uuid4()),
        'component': component,
        'operation': operation,
        'context': context or {},
        'tags': ['operation_start']
    }
    logger.info(f"Starting operation: {operation}", extra=extra)


def log_operation_end(logger_name: str, operation: str, component: str = None, success: bool = True, context: Dict[str, Any] = None):
    """Log operation end"""
    logger = get_enhanced_logger(logger_name)
    extra = {
        'request_id': str(uuid.uuid4()),
        'component': component,
        'operation': operation,
        'context': context or {},
        'tags': ['operation_end', 'success' if success else 'failure']
    }
    
    if success:
        logger.info(f"Completed operation: {operation}", extra=extra)
    else:
        logger.warning(f"Failed operation: {operation}", extra=extra)


def log_performance_metrics(logger_name: str, operation: str, metrics: Dict[str, Any], component: str = None):
    """Log performance metrics"""
    logger = get_enhanced_logger(logger_name)
    extra = {
        'request_id': str(uuid.uuid4()),
        'component': component,
        'operation': operation,
        'performance_metrics': metrics,
        'tags': ['performance']
    }
    logger.info(f"Performance metrics for {operation}", extra=extra) 