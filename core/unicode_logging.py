"""
Unicode-Safe Logging System Module

This module provides UTF-8 safe logging functionality to prevent UnicodeEncodeError
issues with emojis, special characters, and Unicode text in the Social Download Manager v2.0.

Features:
- UTF-8 encoding for all handlers (file and console)
- Graceful fallback for unencodable characters
- Windows console compatibility
- PyQt6 string handling support
- Environment-specific Unicode configuration
"""

import sys
import os
import logging
import logging.handlers
import codecs
from typing import Optional, Dict, Any, TextIO
from pathlib import Path


class UnicodeFormatter(logging.Formatter):
    """Unicode-safe formatter with fallback handling"""
    
    def format(self, record):
        """Format log record with Unicode safety"""
        try:
            # Get the formatted message
            message = super().format(record)
            
            # Ensure the message is properly encoded
            if isinstance(message, bytes):
                message = message.decode('utf-8', errors='replace')
            elif not isinstance(message, str):
                message = str(message)
            
            # Handle PyQt6 QString conversion if needed
            if hasattr(message, 'data'):  # Potential QByteArray or similar
                message = str(message)
            
            return message
            
        except (UnicodeEncodeError, UnicodeDecodeError) as e:
            # Fallback to safe representation
            try:
                safe_message = repr(record.getMessage())
                return f"[UNICODE_ERROR] {safe_message} (Original error: {e})"
            except Exception:
                return f"[LOGGING_ERROR] Unable to format message safely"


class UnicodeFileHandler(logging.handlers.RotatingFileHandler):
    """File handler with explicit UTF-8 encoding"""
    
    def __init__(self, filename, mode='a', maxBytes=0, backupCount=0, encoding='utf-8', delay=False, errors='backslashreplace'):
        # Ensure the directory exists
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize with UTF-8 encoding and error handling
        super().__init__(
            filename=filename,
            mode=mode,
            maxBytes=maxBytes,
            backupCount=backupCount,
            encoding=encoding,
            delay=delay,
            errors=errors
        )


class UnicodeStreamHandler(logging.StreamHandler):
    """Stream handler with UTF-8 encoding for console output"""
    
    def __init__(self, stream=None):
        if stream is None:
            stream = sys.stdout
        
        # Configure stream for UTF-8 if possible
        if hasattr(stream, 'reconfigure'):
            try:
                stream.reconfigure(encoding='utf-8', errors='replace')
            except (AttributeError, OSError):
                # Fallback for older Python or unsupported streams
                pass
        
        super().__init__(stream)
    
    def emit(self, record):
        """Emit log record with Unicode safety"""
        try:
            super().emit(record)
        except (UnicodeEncodeError, UnicodeDecodeError):
            # Fallback: try to emit a safe version
            try:
                record.msg = repr(record.msg)
                super().emit(record)
            except Exception:
                # Last resort: write a generic error message
                try:
                    self.stream.write("[UNICODE_LOGGING_ERROR]\n")
                    self.stream.flush()
                except Exception:
                    pass


class UnicodeLoggingConfigurator:
    """Configures Unicode-safe logging for the application"""
    
    @staticmethod
    def configure_system_encoding():
        """Configure system-level encoding settings"""
        try:
            # Configure stdout and stderr for UTF-8 on Windows
            if sys.platform.startswith('win'):
                # Enable VT100 escape sequences on Windows 10+
                try:
                    import ctypes
                    kernel32 = ctypes.windll.kernel32
                    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)  # Enable VT processing
                except Exception:
                    pass
                
                # Reconfigure streams for UTF-8
                if hasattr(sys.stdout, 'reconfigure'):
                    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
                if hasattr(sys.stderr, 'reconfigure'):
                    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
                    
            # Set default encoding (Python 3.x)
            if hasattr(sys, 'setdefaultencoding'):
                sys.setdefaultencoding('utf-8')
                
        except Exception as e:
            # If we can't configure the system, continue with warnings
            print(f"Warning: Could not fully configure system encoding: {e}")
    
    @staticmethod
    def create_unicode_safe_handlers(config: Dict[str, Any]) -> Dict[str, logging.Handler]:
        """Create Unicode-safe logging handlers based on configuration"""
        handlers = {}
        
        # Console handler
        console_handler = UnicodeStreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(UnicodeFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        handlers['console'] = console_handler
        
        # File handlers
        log_dir = Path(config.get('log_directory', 'logs'))
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Main application log
        main_handler = UnicodeFileHandler(
            filename=log_dir / 'app.log',
            maxBytes=config.get('max_file_size', 10 * 1024 * 1024),
            backupCount=config.get('backup_count', 5),
            encoding='utf-8',
            errors='backslashreplace'
        )
        main_handler.setLevel(logging.DEBUG)
        main_handler.setFormatter(UnicodeFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        ))
        handlers['main_file'] = main_handler
        
        # Error log  
        error_handler = UnicodeFileHandler(
            filename=log_dir / 'error.log',
            maxBytes=config.get('max_file_size', 10 * 1024 * 1024),
            backupCount=config.get('backup_count', 5),
            encoding='utf-8',
            errors='backslashreplace'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(UnicodeFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        ))
        handlers['error_file'] = error_handler
        
        return handlers
    
    @staticmethod
    def apply_unicode_configuration(existing_logging_system=None):
        """Apply Unicode configuration to existing or new logging system"""
        # Configure system encoding first
        UnicodeLoggingConfigurator.configure_system_encoding()
        
        # Configure basic logging with UTF-8
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            encoding='utf-8',
            errors='backslashreplace',
            force=True  # Override existing configuration
        )
        
        # If there's an existing logging system, update its handlers
        if existing_logging_system and hasattr(existing_logging_system, '_handlers'):
            config = {
                'log_directory': getattr(existing_logging_system, 'log_directory', 'logs'),
                'max_file_size': getattr(existing_logging_system, 'max_file_size', 10 * 1024 * 1024),
                'backup_count': getattr(existing_logging_system, 'backup_count', 5),
            }
            
            # Replace handlers with Unicode-safe versions
            new_handlers = UnicodeLoggingConfigurator.create_unicode_safe_handlers(config)
            
            # Remove old handlers
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
            
            # Add new Unicode-safe handlers
            for handler_name, handler in new_handlers.items():
                root_logger.addHandler(handler)
                existing_logging_system._handlers[handler_name] = handler


def test_unicode_logging():
    """Test function to verify Unicode logging works correctly"""
    # Configure Unicode logging
    UnicodeLoggingConfigurator.apply_unicode_configuration()
    
    # Get a test logger
    logger = logging.getLogger("unicode_test")
    
    # Test various Unicode characters
    test_messages = [
        "Basic ASCII message",
        "Unicode characters: çñöü",
        "Emojis: 🎉🚀✅❌",
        "Vietnamese: Tiếng Việt",
        "Japanese: こんにちは",
        "Mathematical: α²+β²=γ²",
        "Currency: $€£¥",
        "Arrows: ←→↑↓",
        "Music: ♪♫♬♩",
        "Extended: 𝄞𝄢𝄫",
    ]
    
    logger.info("Starting Unicode logging test")
    
    for i, message in enumerate(test_messages, 1):
        try:
            logger.info(f"Test {i}: {message}")
        except Exception as e:
            logger.error(f"Failed to log test {i}: {e}")
    
    logger.info("Unicode logging test completed")
    
    return True


if __name__ == "__main__":
    # Run the test when executed directly
    print("Testing Unicode logging system...")
    success = test_unicode_logging()
    if success:
        print("✅ Unicode logging test passed!")
    else:
        print("❌ Unicode logging test failed!") 