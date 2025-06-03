"""
Comprehensive Logging System for Social Download Manager v2.0

This module provides advanced logging capabilities that integrate with the error
management system and main entry orchestrator. It supports multiple log levels,
rotating files, structured logging, and performance monitoring.
"""

import sys
import os
import logging
import logging.handlers
import threading
import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, TextIO
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from contextlib import contextmanager

try:
    import colorama
    from colorama import Fore, Back, Style
    colorama.init()
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False
    # Fallback color constants
    class Fore:
        RED = ""
        GREEN = ""
        YELLOW = ""
        BLUE = ""
        MAGENTA = ""
        CYAN = ""
        WHITE = ""
        RESET = ""
    
    class Style:
        BRIGHT = ""
        RESET_ALL = ""


class LogLevel(Enum):
    """Extended log levels for different components"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL
    
    # Custom levels
    TRACE = 5           # Detailed tracing
    VERBOSE = 15        # Verbose information
    PERFORMANCE = 25    # Performance metrics
    SECURITY = 35       # Security-related logs
    AUDIT = 45          # Audit trail


class LogCategory(Enum):
    """Log categories for filtering and routing"""
    SYSTEM = "system"
    STARTUP = "startup"
    ADAPTER = "adapter"
    UI = "ui"
    NETWORK = "network"
    DATABASE = "database"
    PLATFORM = "platform"
    PERFORMANCE = "performance"
    SECURITY = "security"
    AUDIT = "audit"
    USER_ACTION = "user_action"
    ERROR = "error"
    DEBUG = "debug"


@dataclass
class LogEntry:
    """Structured log entry"""
    timestamp: datetime
    level: LogLevel
    category: LogCategory
    logger_name: str
    message: str
    
    # Context information
    thread_id: int = field(default_factory=lambda: threading.get_ident())
    thread_name: str = field(default_factory=lambda: threading.current_thread().name)
    process_id: int = field(default_factory=os.getpid)
    component: Optional[str] = None
    operation: Optional[str] = None
    
    # Additional data
    extra_data: Dict[str, Any] = field(default_factory=dict)
    
    # Performance data
    duration_ms: Optional[float] = None
    memory_usage: Optional[float] = None
    
    # Error information
    exception_type: Optional[str] = None
    exception_message: Optional[str] = None
    stack_trace: Optional[str] = None


class ColoredFormatter(logging.Formatter):
    """Colored console formatter"""
    
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT,
        'TRACE': Fore.MAGENTA,
        'VERBOSE': Fore.BLUE,
        'PERFORMANCE': Fore.CYAN + Style.BRIGHT,
        'SECURITY': Fore.YELLOW + Style.BRIGHT,
        'AUDIT': Fore.GREEN + Style.BRIGHT
    }
    
    def format(self, record):
        # Apply color if available
        if COLORAMA_AVAILABLE and hasattr(record, 'levelname'):
            color = self.COLORS.get(record.levelname, '')
            if color:
                record.levelname = f"{color}{record.levelname}{Style.RESET_ALL}"
                record.name = f"{Fore.BLUE}{record.name}{Style.RESET_ALL}"
        
        return super().format(record)


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'thread_id': threading.get_ident(),
            'thread_name': threading.current_thread().name,
            'process_id': os.getpid(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra attributes
        for key, value in record.__dict__.items():
            if key not in ('name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage', 'exc_info', 
                          'exc_text', 'stack_info'):
                log_entry[key] = value
        
        # Add exception information
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)


class CategoryFilter(logging.Filter):
    """Filter logs by category"""
    
    def __init__(self, categories: List[LogCategory]):
        super().__init__()
        self.categories = {cat.value for cat in categories}
    
    def filter(self, record):
        category = getattr(record, 'category', None)
        if category is None:
            return True  # Allow if no category specified
        
        return category in self.categories


class PerformanceLogger:
    """Specialized logger for performance metrics"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    @contextmanager
    def measure_time(self, operation: str, component: str = "unknown"):
        """Context manager to measure operation time"""
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        try:
            yield
        finally:
            end_time = time.time()
            end_memory = self._get_memory_usage()
            
            duration_ms = (end_time - start_time) * 1000
            memory_delta = end_memory - start_memory if start_memory and end_memory else None
            
            self.log_performance(
                operation=operation,
                component=component,
                duration_ms=duration_ms,
                memory_delta=memory_delta
            )
    
    def log_performance(
        self, 
        operation: str, 
        component: str, 
        duration_ms: float,
        memory_delta: Optional[float] = None,
        additional_metrics: Optional[Dict[str, Any]] = None
    ):
        """Log performance metrics"""
        extra = {
            'category': LogCategory.PERFORMANCE.value,
            'component': component,
            'operation': operation,
            'duration_ms': duration_ms,
            'memory_delta': memory_delta
        }
        
        if additional_metrics:
            extra.update(additional_metrics)
        
        message = f"Performance: {operation} in {component} took {duration_ms:.2f}ms"
        if memory_delta:
            message += f", memory delta: {memory_delta:.2f}MB"
        
        self.logger.log(LogLevel.PERFORMANCE.value, message, extra=extra)
    
    def _get_memory_usage(self) -> Optional[float]:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except ImportError:
            return None


class LoggingSystem:
    """
    Comprehensive logging system for v2.0 architecture
    
    Provides multiple handlers, structured logging, performance monitoring,
    and integration with the error management system.
    """
    
    def __init__(self, log_directory: str = "logs"):
        self.log_directory = Path(log_directory)
        self.log_directory.mkdir(exist_ok=True)
        
        self._lock = threading.RLock()
        self._loggers: Dict[str, logging.Logger] = {}
        self._handlers: Dict[str, logging.Handler] = {}
        
        # Configuration
        self.default_level = LogLevel.INFO
        self.console_enabled = True
        self.file_enabled = True
        self.json_enabled = False
        self.colored_console = True
        
        # File rotation settings
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.backup_count = 5
        
        # Performance tracking
        self.performance_logger: Optional[PerformanceLogger] = None
        
        # Setup custom log levels
        self._setup_custom_levels()
        
        # Setup default configuration
        self._setup_default_configuration()
    
    def _setup_custom_levels(self):
        """Setup custom log levels"""
        logging.addLevelName(LogLevel.TRACE.value, "TRACE")
        logging.addLevelName(LogLevel.VERBOSE.value, "VERBOSE")
        logging.addLevelName(LogLevel.PERFORMANCE.value, "PERFORMANCE")
        logging.addLevelName(LogLevel.SECURITY.value, "SECURITY")
        logging.addLevelName(LogLevel.AUDIT.value, "AUDIT")
    
    def _setup_default_configuration(self):
        """Setup default logging configuration"""
        # Setup root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self.default_level.value)
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Console handler
        if self.console_enabled:
            self._setup_console_handler()
        
        # File handlers
        if self.file_enabled:
            self._setup_file_handlers()
        
        # Performance logger
        self.performance_logger = PerformanceLogger(self.get_logger("performance"))
    
    def _setup_console_handler(self):
        """Setup colored console handler"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.default_level.value)
        
        if self.colored_console and COLORAMA_AVAILABLE:
            formatter = ColoredFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        console_handler.setFormatter(formatter)
        
        # Add to root logger
        logging.getLogger().addHandler(console_handler)
        self._handlers['console'] = console_handler
    
    def _setup_file_handlers(self):
        """Setup rotating file handlers"""
        # Main application log
        main_handler = logging.handlers.RotatingFileHandler(
            self.log_directory / "app.log",
            maxBytes=self.max_file_size,
            backupCount=self.backup_count
        )
        main_handler.setLevel(self.default_level.value)
        main_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        ))
        
        logging.getLogger().addHandler(main_handler)
        self._handlers['main_file'] = main_handler
        
        # Error log (ERROR and above only)
        error_handler = logging.handlers.RotatingFileHandler(
            self.log_directory / "error.log",
            maxBytes=self.max_file_size,
            backupCount=self.backup_count
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        ))
        
        logging.getLogger().addHandler(error_handler)
        self._handlers['error_file'] = error_handler
        
        # Performance log
        performance_handler = logging.handlers.RotatingFileHandler(
            self.log_directory / "performance.log",
            maxBytes=self.max_file_size,
            backupCount=self.backup_count
        )
        performance_handler.setLevel(LogLevel.PERFORMANCE.value)
        performance_handler.addFilter(CategoryFilter([LogCategory.PERFORMANCE]))
        performance_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        
        logging.getLogger().addHandler(performance_handler)
        self._handlers['performance_file'] = performance_handler
        
        # JSON structured log (if enabled)
        if self.json_enabled:
            json_handler = logging.handlers.RotatingFileHandler(
                self.log_directory / "structured.json",
                maxBytes=self.max_file_size,
                backupCount=self.backup_count
            )
            json_handler.setLevel(logging.DEBUG)
            json_handler.setFormatter(JsonFormatter())
            
            logging.getLogger().addHandler(json_handler)
            self._handlers['json_file'] = json_handler
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger with the specified name"""
        with self._lock:
            if name not in self._loggers:
                logger = logging.getLogger(name)
                
                # Add custom methods
                self._add_custom_methods(logger)
                
                self._loggers[name] = logger
            
            return self._loggers[name]
    
    def _add_custom_methods(self, logger: logging.Logger):
        """Add custom logging methods to logger"""
        
        def trace(message, *args, **kwargs):
            if logger.isEnabledFor(LogLevel.TRACE.value):
                logger._log(LogLevel.TRACE.value, message, args, **kwargs)
        
        def verbose(message, *args, **kwargs):
            if logger.isEnabledFor(LogLevel.VERBOSE.value):
                logger._log(LogLevel.VERBOSE.value, message, args, **kwargs)
        
        def performance(message, *args, **kwargs):
            kwargs.setdefault('extra', {})['category'] = LogCategory.PERFORMANCE.value
            if logger.isEnabledFor(LogLevel.PERFORMANCE.value):
                logger._log(LogLevel.PERFORMANCE.value, message, args, **kwargs)
        
        def security(message, *args, **kwargs):
            kwargs.setdefault('extra', {})['category'] = LogCategory.SECURITY.value
            if logger.isEnabledFor(LogLevel.SECURITY.value):
                logger._log(LogLevel.SECURITY.value, message, args, **kwargs)
        
        def audit(message, *args, **kwargs):
            kwargs.setdefault('extra', {})['category'] = LogCategory.AUDIT.value
            if logger.isEnabledFor(LogLevel.AUDIT.value):
                logger._log(LogLevel.AUDIT.value, message, args, **kwargs)
        
        # Add methods to logger
        logger.trace = trace
        logger.verbose = verbose
        logger.performance = performance
        logger.security = security
        logger.audit = audit
    
    def set_level(self, level: Union[LogLevel, int, str]):
        """Set global logging level"""
        if isinstance(level, LogLevel):
            level_value = level.value
        elif isinstance(level, str):
            level_value = getattr(logging, level.upper())
        else:
            level_value = level
        
        with self._lock:
            # Update root logger
            logging.getLogger().setLevel(level_value)
            
            # Update all handlers
            for handler in self._handlers.values():
                if handler.name != 'error_file':  # Keep error file at ERROR level
                    handler.setLevel(level_value)
    
    def add_category_filter(self, handler_name: str, categories: List[LogCategory]):
        """Add category filter to a handler"""
        with self._lock:
            if handler_name in self._handlers:
                filter_obj = CategoryFilter(categories)
                self._handlers[handler_name].addFilter(filter_obj)
    
    def enable_json_logging(self):
        """Enable JSON structured logging"""
        if not self.json_enabled:
            self.json_enabled = True
            self._setup_file_handlers()  # Recreate handlers
    
    def get_performance_logger(self) -> PerformanceLogger:
        """Get the performance logger"""
        if self.performance_logger is None:
            self.performance_logger = PerformanceLogger(self.get_logger("performance"))
        
        return self.performance_logger
    
    def log_startup_event(self, event: str, component: str, success: bool, duration_ms: float = None):
        """Log startup events"""
        logger = self.get_logger("startup")
        extra = {
            'category': LogCategory.STARTUP.value,
            'component': component,
            'event': event,
            'success': success
        }
        
        if duration_ms is not None:
            extra['duration_ms'] = duration_ms
        
        level = logging.INFO if success else logging.ERROR
        message = f"Startup: {event} in {component} {'succeeded' if success else 'failed'}"
        
        if duration_ms is not None:
            message += f" ({duration_ms:.2f}ms)"
        
        logger.log(level, message, extra=extra)
    
    def log_user_action(self, action: str, component: str, details: Dict[str, Any] = None):
        """Log user actions for audit trail"""
        logger = self.get_logger("audit")
        extra = {
            'category': LogCategory.USER_ACTION.value,
            'component': component,
            'action': action
        }
        
        if details:
            extra['details'] = details
        
        message = f"User Action: {action} in {component}"
        logger.audit(message, extra=extra)
    
    def log_adapter_event(self, adapter_id: str, event: str, success: bool, details: str = None):
        """Log adapter events"""
        logger = self.get_logger("adapter")
        extra = {
            'category': LogCategory.ADAPTER.value,
            'adapter_id': adapter_id,
            'event': event,
            'success': success
        }
        
        level = logging.INFO if success else logging.WARNING
        message = f"Adapter: {adapter_id} {event} {'succeeded' if success else 'failed'}"
        
        if details:
            message += f" - {details}"
        
        logger.log(level, message, extra=extra)
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """Get logging statistics"""
        stats = {
            'handlers': len(self._handlers),
            'loggers': len(self._loggers),
            'log_directory': str(self.log_directory),
            'levels': {level.name: level.value for level in LogLevel}
        }
        
        # File sizes
        for log_file in self.log_directory.glob("*.log"):
            try:
                stats[f"file_{log_file.stem}_size"] = log_file.stat().st_size
            except OSError:
                pass
        
        return stats
    
    def shutdown(self):
        """Shutdown logging system"""
        with self._lock:
            # Close all handlers
            for handler in self._handlers.values():
                handler.close()
            
            # Clear handlers
            self._handlers.clear()
            
            # Clear loggers
            self._loggers.clear()


# Global logging system instance
_logging_system: Optional[LoggingSystem] = None
_logging_system_lock = threading.Lock()


def get_logging_system() -> LoggingSystem:
    """Get the global logging system instance (singleton)"""
    global _logging_system
    
    with _logging_system_lock:
        if _logging_system is None:
            _logging_system = LoggingSystem()
        
        return _logging_system


def get_logger(name: str) -> logging.Logger:
    """Convenience function to get a logger"""
    return get_logging_system().get_logger(name)


def log_performance(operation: str, component: str = "unknown"):
    """Decorator/context manager for performance logging"""
    return get_logging_system().get_performance_logger().measure_time(operation, component)


def setup_development_logging():
    """Setup logging for development environment"""
    logging_system = get_logging_system()
    logging_system.set_level(LogLevel.DEBUG)
    logging_system.colored_console = True
    logging_system.json_enabled = True


def setup_production_logging():
    """Setup logging for production environment"""
    logging_system = get_logging_system()
    logging_system.set_level(LogLevel.INFO)
    logging_system.colored_console = False
    logging_system.json_enabled = True 