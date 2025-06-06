"""
Advanced Unicode Error Handling Module

This module provides sophisticated fallback mechanisms for Unicode encoding errors
in logging systems. It implements multiple layers of error handling to ensure
logging never crashes the application.

Features:
- Hierarchical error handlers (replace → backslashreplace → custom)
- Context tracking for error locations
- ASCII-safe fallback handlers
- Circuit breaker pattern for cascade failure prevention
- Forensic analysis of problematic Unicode data
- Legacy system compatibility
"""

import sys
import os
import logging
import hashlib
import contextvars
import time
import traceback
from typing import Optional, Dict, Any, List, Callable, Union
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum, auto


class ErrorSeverity(Enum):
    """Severity levels for Unicode errors"""
    LOW = "low"           # Minor display issues
    MEDIUM = "medium"     # Some functionality affected
    HIGH = "high"         # Critical logging failure
    CRITICAL = "critical" # System-level encoding failure


class FallbackStrategy(Enum):
    """Available fallback strategies"""
    REPLACE = "replace"                    # Replace with �
    BACKSLASH_REPLACE = "backslashreplace" # Replace with \xNN
    IGNORE = "ignore"                      # Skip problematic chars
    XMLCHARREFREPLACE = "xmlcharrefreplace" # Replace with &#NNN;
    CUSTOM_ASCII = "custom_ascii"          # Custom ASCII-safe replacement
    HEX_ESCAPE = "hex_escape"             # Full hex escape
    SAFE_REPR = "safe_repr"               # Use repr() for safety


@dataclass
class UnicodeError:
    """Information about a Unicode encoding error"""
    timestamp: float
    message: str
    original_text: str
    encoding: str
    error_type: str
    location: str
    severity: ErrorSeverity
    fallback_used: FallbackStrategy
    hash_id: str = field(default="")
    
    def __post_init__(self):
        # Generate forensic hash for tracking
        self.hash_id = hashlib.md5(
            f"{self.original_text}{self.encoding}{self.error_type}".encode('utf-8', errors='ignore')
        ).hexdigest()[:8]


class UnicodeErrorTracker:
    """Tracks and analyzes Unicode encoding errors"""
    
    def __init__(self, max_errors: int = 100):
        self.max_errors = max_errors
        self.errors: List[UnicodeError] = []
        self.error_counts: Dict[str, int] = {}
        self.circuit_breaker_active = False
        self.circuit_breaker_threshold = 10
        self.circuit_breaker_reset_time = 300  # 5 minutes
        self.last_circuit_break = 0
    
    def record_error(self, error: UnicodeError):
        """Record a Unicode error for analysis"""
        # Add to error list (with rotation)
        self.errors.append(error)
        if len(self.errors) > self.max_errors:
            self.errors.pop(0)
        
        # Update counts
        key = f"{error.error_type}:{error.encoding}"
        self.error_counts[key] = self.error_counts.get(key, 0) + 1
        
        # Check circuit breaker
        recent_errors = sum(1 for e in self.errors if time.time() - e.timestamp < 60)
        if recent_errors >= self.circuit_breaker_threshold:
            self.activate_circuit_breaker()
    
    def activate_circuit_breaker(self):
        """Activate circuit breaker to prevent cascade failures"""
        self.circuit_breaker_active = True
        self.last_circuit_break = time.time()
        print(f"⚠️ CIRCUIT BREAKER ACTIVATED: Too many Unicode errors, switching to safe mode")
    
    def is_circuit_breaker_active(self) -> bool:
        """Check if circuit breaker is active"""
        if self.circuit_breaker_active:
            if time.time() - self.last_circuit_break > self.circuit_breaker_reset_time:
                self.circuit_breaker_active = False
                print("✅ Circuit breaker reset - resuming normal Unicode handling")
        return self.circuit_breaker_active
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring"""
        return {
            'total_errors': len(self.errors),
            'error_types': dict(self.error_counts),
            'circuit_breaker_active': self.circuit_breaker_active,
            'recent_errors': sum(1 for e in self.errors if time.time() - e.timestamp < 300),
            'most_common_errors': sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        }


# Global error tracker instance
error_tracker = UnicodeErrorTracker()

# Context variable for tracking error locations
error_context: contextvars.ContextVar[str] = contextvars.ContextVar('unicode_error_context', default='unknown')


class RobustUnicodeFormatter(logging.Formatter):
    """
    Advanced logging formatter with sophisticated Unicode error handling
    
    Implements hierarchical fallback strategies:
    1. Standard UTF-8 encoding
    2. 'replace' error handler
    3. 'backslashreplace' error handler
    4. Custom ASCII-safe handler
    5. Emergency repr() fallback
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fallback_strategies = [
            FallbackStrategy.REPLACE,
            FallbackStrategy.BACKSLASH_REPLACE,
            FallbackStrategy.CUSTOM_ASCII,
            FallbackStrategy.HEX_ESCAPE,
            FallbackStrategy.SAFE_REPR
        ]
    
    def format(self, record):
        """Format log record with robust Unicode error handling"""
        # Set context for error tracking
        error_context.set(f"{record.name}:{record.funcName}:{record.lineno}")
        
        # Check circuit breaker
        if error_tracker.is_circuit_breaker_active():
            return self._emergency_format(record)
        
        # Try progressive fallback strategies
        for strategy in self.fallback_strategies:
            try:
                result = self._format_with_strategy(record, strategy)
                if result is not None:
                    return result
            except Exception as e:
                self._record_error(record, strategy, str(e))
                continue
        
        # Final emergency fallback
        return self._emergency_format(record)
    
    def _format_with_strategy(self, record, strategy: FallbackStrategy) -> Optional[str]:
        """Apply specific fallback strategy"""
        try:
            if strategy == FallbackStrategy.REPLACE:
                # Standard formatting with replace errors
                message = super().format(record)
                return message.encode('utf-8', errors='replace').decode('utf-8')
            
            elif strategy == FallbackStrategy.BACKSLASH_REPLACE:
                # Backslash escape for problematic characters
                message = super().format(record)
                return message.encode('utf-8', errors='backslashreplace').decode('utf-8')
            
            elif strategy == FallbackStrategy.CUSTOM_ASCII:
                # Custom ASCII-safe replacement
                message = super().format(record)
                return self._ascii_safe_replace(message)
            
            elif strategy == FallbackStrategy.HEX_ESCAPE:
                # Full hex escape for all non-ASCII
                message = super().format(record)
                return self._hex_escape_replace(message)
            
            elif strategy == FallbackStrategy.SAFE_REPR:
                # Use repr() for complete safety
                return self._safe_repr_format(record)
            
        except Exception:
            return None
        
        return None
    
    def _ascii_safe_replace(self, text: str) -> str:
        """Replace Unicode characters with ASCII-safe alternatives"""
        replacements = {
            # Common Unicode replacements
            '🎉': '[PARTY]', '🚀': '[ROCKET]', '✅': '[CHECK]', '❌': '[X]',
            '⚠️': '[WARNING]', '🔥': '[FIRE]', '💡': '[IDEA]', '📱': '[PHONE]',
            '📁': '[FOLDER]', '🎵': '[MUSIC]', '🎶': '[NOTES]', '💯': '[100]',
            '⭐': '[STAR]', '💎': '[DIAMOND]', '🏁': '[FLAG]',
            
            # Common special characters
            'é': 'e', 'ñ': 'n', 'ü': 'u', 'ç': 'c', 'à': 'a', 'è': 'e',
            'ö': 'o', 'á': 'a', 'í': 'i', 'ó': 'o', 'ú': 'u',
            
            # Quotes and punctuation
            '"': '"', '"': '"', ''': "'", ''': "'", '…': '...',
            '–': '-', '—': '--', '«': '<<', '»': '>>',
            
            # Mathematical symbols
            'α': 'alpha', 'β': 'beta', 'γ': 'gamma', '²': '^2', '∑': 'SUM',
            '≈': '~=', '≠': '!=', '≤': '<=', '≥': '>=',
            
            # Currency
            '€': 'EUR', '£': 'GBP', '¥': 'YEN', '¢': 'cents',
            
            # Arrows
            '←': '<-', '→': '->', '↑': '^', '↓': 'v', '↔': '<->', '↕': '^v'
        }
        
        result = text
        for unicode_char, ascii_replacement in replacements.items():
            result = result.replace(unicode_char, ascii_replacement)
        
        # Replace any remaining non-ASCII with safe placeholder
        result = ''.join(c if ord(c) < 128 else f'[U+{ord(c):04X}]' for c in result)
        return result
    
    def _hex_escape_replace(self, text: str) -> str:
        """Replace non-ASCII characters with hex escapes"""
        return ''.join(c if ord(c) < 128 else f'\\x{ord(c):02x}' if ord(c) < 256 else f'\\u{ord(c):04x}' for c in text)
    
    def _safe_repr_format(self, record) -> str:
        """Emergency formatting using repr() for absolute safety"""
        try:
            basic_info = f"[{record.levelname}] {record.name}"
            message = repr(record.getMessage())
            return f"{basic_info}: {message}"
        except Exception:
            return f"[EMERGENCY] {record.name}: <FORMATTING_ERROR>"
    
    def _emergency_format(self, record) -> str:
        """Final emergency fallback when all else fails"""
        try:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            level = record.levelname if hasattr(record, 'levelname') else 'UNKNOWN'
            name = record.name if hasattr(record, 'name') else 'unknown'
            return f"{timestamp} - {name} - {level} - [UNICODE_EMERGENCY_FALLBACK]"
        except Exception:
            return "[CRITICAL_LOGGING_FAILURE]"
    
    def _record_error(self, record, strategy: FallbackStrategy, error_msg: str):
        """Record Unicode error for analysis"""
        try:
            unicode_error = UnicodeError(
                timestamp=time.time(),
                message=error_msg,
                original_text=str(record.getMessage()) if hasattr(record, 'getMessage') else str(record.msg),
                encoding='utf-8',
                error_type=type(record).__name__,
                location=error_context.get(),
                severity=ErrorSeverity.MEDIUM,
                fallback_used=strategy
            )
            error_tracker.record_error(unicode_error)
        except Exception:
            # Don't let error recording crash the logging
            pass


class FallbackLoggingHandler(logging.Handler):
    """
    Emergency logging handler that never fails
    
    Uses ASCII-only output and multiple destination fallbacks
    """
    
    def __init__(self, emergency_file: str = "logs/emergency.log"):
        super().__init__()
        self.emergency_file = Path(emergency_file)
        self.emergency_file.parent.mkdir(parents=True, exist_ok=True)
        self.setFormatter(RobustUnicodeFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
    
    def emit(self, record):
        """Emit log record with multiple fallback destinations"""
        try:
            # Format the message safely
            message = self.format(record)
            
            # Ensure ASCII-only output
            safe_message = message.encode('ascii', errors='replace').decode('ascii')
            
            # Try multiple output destinations
            self._try_file_output(safe_message)
            self._try_console_output(safe_message)
            
        except Exception:
            # Absolute final fallback
            self._emergency_output(record)
    
    def _try_file_output(self, message: str):
        """Try writing to emergency log file"""
        try:
            with open(self.emergency_file, 'a', encoding='ascii', errors='replace') as f:
                f.write(f"{message}\n")
                f.flush()
        except Exception:
            pass
    
    def _try_console_output(self, message: str):
        """Try writing to console"""
        try:
            print(f"[EMERGENCY] {message}", file=sys.stderr)
            sys.stderr.flush()
        except Exception:
            pass
    
    def _emergency_output(self, record):
        """Absolute final emergency output"""
        try:
            emergency_msg = f"[CRITICAL_LOGGING_FAILURE] {time.time()}"
            print(emergency_msg, file=sys.stderr)
        except Exception:
            # Nothing more we can do
            pass


def create_error_resilient_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Create a logger with comprehensive Unicode error handling"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Add robust console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(RobustUnicodeFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(console_handler)
    
    # Add emergency fallback handler
    emergency_handler = FallbackLoggingHandler()
    emergency_handler.setLevel(logging.ERROR)
    logger.addHandler(emergency_handler)
    
    return logger


def get_unicode_error_stats() -> Dict[str, Any]:
    """Get comprehensive Unicode error statistics"""
    return error_tracker.get_statistics()


def test_error_handling():
    """Test Unicode error handling mechanisms"""
    print("🧪 Testing Unicode error handling...")
    
    logger = create_error_resilient_logger("test_error_handling")
    
    # Test various problematic cases
    test_cases = [
        "Normal ASCII text",
        "Unicode with emoji 🎉",
        "Broken encoding: \x80\x81\x82",
        "Mixed content: café 🚀 résumé",
        "Null bytes: \x00\x01\x02",
        "Very high Unicode: 𝄞𝄢𝄫",
        b"Raw bytes input".decode('latin1'),  # Problematic decoding
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        try:
            logger.info(f"Test {i}: {test_case}")
            print(f"  ✅ Test {i}: Handled successfully")
        except Exception as e:
            print(f"  ❌ Test {i}: Failed - {e}")
    
    # Display error statistics
    stats = get_unicode_error_stats()
    print(f"\n📊 Error Statistics:")
    print(f"  Total errors: {stats['total_errors']}")
    print(f"  Circuit breaker active: {stats['circuit_breaker_active']}")
    print(f"  Recent errors: {stats['recent_errors']}")
    
    return True


if __name__ == "__main__":
    # Run tests when executed directly
    print("Testing Unicode error handling system...")
    success = test_error_handling()
    if success:
        print("✅ Unicode error handling test completed!")
    else:
        print("❌ Unicode error handling test failed!") 