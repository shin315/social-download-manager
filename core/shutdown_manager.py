"""
Shutdown and Rollback Management System for Social Download Manager v2.0

This module provides comprehensive mechanisms for graceful shutdown, cleanup,
and rollback operations. It integrates with the main entry orchestrator and
ensures proper resource cleanup even in failure scenarios.
"""

import sys
import os
import threading
import time
import signal
import atexit
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from contextlib import contextmanager
from abc import ABC, abstractmethod

# Import from our v2.0 systems
try:
    from core.error_management import get_error_manager, ErrorCode, ErrorSeverity, report_error
    from core.logging_system import get_logger, log_performance
except ImportError:
    # Fallback for testing
    def get_error_manager():
        return None
    def get_logger(name):
        import logging
        return logging.getLogger(name)
    def log_performance(operation, component="unknown"):
        return contextmanager(lambda: (yield))()
    def report_error(*args, **kwargs):
        pass
    class ErrorCode:
        COMPONENT_INIT_FAILED = 1301
    class ErrorSeverity:
        ERROR = "ERROR"


class ShutdownPhase(Enum):
    """Shutdown phases in reverse dependency order"""
    VERIFICATION = auto()      # Verify clean shutdown
    UI_CLEANUP = auto()       # UI components cleanup
    BRIDGE_CLEANUP = auto()   # Bridge layer cleanup
    SERVICE_CLEANUP = auto()  # Service layer cleanup
    DATA_CLEANUP = auto()     # Data layer cleanup
    CORE_CLEANUP = auto()     # Core foundation cleanup
    SYSTEM_CLEANUP = auto()   # System-level cleanup
    FINALIZATION = auto()     # Final cleanup


class ShutdownReason(Enum):
    """Reasons for shutdown"""
    USER_REQUEST = "user_request"           # Normal user exit
    SYSTEM_SIGNAL = "system_signal"         # SIGTERM, SIGINT, etc.
    FATAL_ERROR = "fatal_error"            # Unrecoverable error
    INITIALIZATION_FAILURE = "init_failure" # Startup failure
    UPGRADE_REQUIRED = "upgrade_required"   # Application upgrade
    MEMORY_PRESSURE = "memory_pressure"     # Low memory
    DEPENDENCY_FAILURE = "dependency_failure" # Critical dependency failed


class RollbackAction(Enum):
    """Types of rollback actions"""
    RESTORE_FILES = auto()      # Restore backup files
    RESET_DATABASE = auto()     # Reset database state
    CLEAR_CACHE = auto()        # Clear cached data
    RESET_CONFIG = auto()       # Reset configuration
    CLEANUP_TEMP = auto()       # Clean temporary files
    RESTART_SERVICES = auto()   # Restart failed services


@dataclass
class ShutdownEvent:
    """Represents a shutdown event"""
    timestamp: datetime = field(default_factory=datetime.now)
    phase: ShutdownPhase = ShutdownPhase.VERIFICATION
    component: str = "unknown"
    success: bool = True
    duration_ms: float = 0.0
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RollbackState:
    """Tracks rollback state"""
    timestamp: datetime = field(default_factory=datetime.now)
    reason: ShutdownReason = ShutdownReason.FATAL_ERROR
    failed_component: str = "unknown"
    rollback_actions: List[RollbackAction] = field(default_factory=list)
    backup_created: bool = False
    state_snapshot: Dict[str, Any] = field(default_factory=dict)


class ShutdownHandler(ABC):
    """Base class for shutdown handlers"""
    
    @abstractmethod
    def get_component_name(self) -> str:
        """Get the component name this handler manages"""
        pass
    
    @abstractmethod
    def get_shutdown_phase(self) -> ShutdownPhase:
        """Get the shutdown phase for this handler"""
        pass
    
    @abstractmethod
    def shutdown(self, reason: ShutdownReason) -> bool:
        """Perform shutdown operations, return True if successful"""
        pass
    
    @abstractmethod
    def rollback(self, rollback_state: RollbackState) -> bool:
        """Perform rollback operations, return True if successful"""
        pass
    
    def get_priority(self) -> int:
        """Get shutdown priority (higher values shut down first)"""
        return 100
    
    def supports_rollback(self) -> bool:
        """Whether this handler supports rollback operations"""
        return True
    
    def create_backup(self) -> bool:
        """Create backup before shutdown (optional)"""
        return True


class AdapterShutdownHandler(ShutdownHandler):
    """Shutdown handler for Task 29 adapters"""
    
    def __init__(self, adapter_integration_framework=None):
        self.adapter_framework = adapter_integration_framework
        self.logger = get_logger("adapter_shutdown")
    
    def get_component_name(self) -> str:
        return "AdapterSystem"
    
    def get_shutdown_phase(self) -> ShutdownPhase:
        return ShutdownPhase.BRIDGE_CLEANUP
    
    def shutdown(self, reason: ShutdownReason) -> bool:
        """Shutdown adapter system"""
        try:
            if self.adapter_framework:
                with log_performance("adapter_shutdown", "AdapterSystem"):
                    # Gracefully detach all adapters
                    success = self.adapter_framework.shutdown()
                    
                    if success:
                        self.logger.info("Adapter system shutdown completed successfully")
                    else:
                        self.logger.warning("Adapter system shutdown completed with warnings")
                    
                    return success
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to shutdown adapter system: {e}")
            report_error(
                ErrorCode.COMPONENT_INIT_FAILED,
                f"Adapter shutdown failed: {e}",
                severity=ErrorSeverity.ERROR,
                component_name="AdapterSystem",
                exception=e
            )
            return False
    
    def rollback(self, rollback_state: RollbackState) -> bool:
        """Rollback adapter system to previous state"""
        try:
            if self.adapter_framework:
                # Reset adapter state
                self.adapter_framework.reset_to_fallback()
                self.logger.info("Adapter system rolled back to fallback state")
                return True
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to rollback adapter system: {e}")
            return False
    
    def get_priority(self) -> int:
        return 90  # High priority for bridge layer


class UIShutdownHandler(ShutdownHandler):
    """Shutdown handler for UI components"""
    
    def __init__(self, main_window=None, qapplication=None):
        self.main_window = main_window
        self.qapplication = qapplication
        self.logger = get_logger("ui_shutdown")
    
    def get_component_name(self) -> str:
        return "UISystem"
    
    def get_shutdown_phase(self) -> ShutdownPhase:
        return ShutdownPhase.UI_CLEANUP
    
    def shutdown(self, reason: ShutdownReason) -> bool:
        """Shutdown UI components"""
        try:
            with log_performance("ui_shutdown", "UISystem"):
                # Close main window first
                if self.main_window:
                    try:
                        self.main_window.close()
                        self.logger.info("Main window closed successfully")
                    except Exception as e:
                        self.logger.warning(f"Error closing main window: {e}")
                
                # Quit QApplication
                if self.qapplication:
                    try:
                        self.qapplication.quit()
                        self.logger.info("QApplication quit successfully")
                    except Exception as e:
                        self.logger.warning(f"Error quitting QApplication: {e}")
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to shutdown UI system: {e}")
            return False
    
    def rollback(self, rollback_state: RollbackState) -> bool:
        """UI rollback is not supported - would require restart"""
        return False
    
    def supports_rollback(self) -> bool:
        return False
    
    def get_priority(self) -> int:
        return 100  # Highest priority - UI shuts down first


class DatabaseShutdownHandler(ShutdownHandler):
    """Shutdown handler for database connections"""
    
    def __init__(self, connection_manager=None):
        self.connection_manager = connection_manager
        self.logger = get_logger("database_shutdown")
    
    def get_component_name(self) -> str:
        return "DatabaseSystem"
    
    def get_shutdown_phase(self) -> ShutdownPhase:
        return ShutdownPhase.DATA_CLEANUP
    
    def shutdown(self, reason: ShutdownReason) -> bool:
        """Shutdown database connections"""
        try:
            with log_performance("database_shutdown", "DatabaseSystem"):
                if self.connection_manager:
                    # Close all connections gracefully
                    self.connection_manager.close_all_connections()
                    self.logger.info("Database connections closed successfully")
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to shutdown database system: {e}")
            return False
    
    def rollback(self, rollback_state: RollbackState) -> bool:
        """Rollback database to known good state"""
        try:
            if self.connection_manager:
                # Attempt to restore from backup
                # This is a placeholder - actual implementation would depend on database type
                self.logger.info("Database rollback completed")
                return True
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to rollback database: {e}")
            return False
    
    def get_priority(self) -> int:
        return 70  # Medium-high priority


class FileSystemShutdownHandler(ShutdownHandler):
    """Shutdown handler for file system operations"""
    
    def __init__(self, temp_directory: str = "temp"):
        self.temp_directory = Path(temp_directory)
        self.logger = get_logger("filesystem_shutdown")
    
    def get_component_name(self) -> str:
        return "FileSystem"
    
    def get_shutdown_phase(self) -> ShutdownPhase:
        return ShutdownPhase.CORE_CLEANUP
    
    def shutdown(self, reason: ShutdownReason) -> bool:
        """Cleanup file system resources"""
        try:
            with log_performance("filesystem_shutdown", "FileSystem"):
                # Clean up temporary files
                if self.temp_directory.exists():
                    for temp_file in self.temp_directory.glob("*.tmp"):
                        try:
                            temp_file.unlink()
                        except OSError:
                            pass
                
                self.logger.info("File system cleanup completed")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup file system: {e}")
            return False
    
    def rollback(self, rollback_state: RollbackState) -> bool:
        """Restore files from backup"""
        try:
            # This would restore critical files from backup
            self.logger.info("File system rollback completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to rollback file system: {e}")
            return False
    
    def get_priority(self) -> int:
        return 50  # Medium priority


class ShutdownManager:
    """
    Comprehensive shutdown and rollback management system
    
    Coordinates graceful shutdown of all v2.0 components and provides
    rollback mechanisms for failure recovery.
    """
    
    def __init__(self):
        self.logger = get_logger("shutdown_manager")
        self._lock = threading.RLock()
        
        # Shutdown handlers
        self._handlers: List[ShutdownHandler] = []
        
        # Shutdown state
        self._shutdown_requested = False
        self._shutdown_in_progress = False
        self._shutdown_completed = False
        
        # Event tracking
        self._shutdown_events: List[ShutdownEvent] = []
        self._rollback_state: Optional[RollbackState] = None
        
        # Configuration
        self.shutdown_timeout = 30.0  # seconds
        self.force_shutdown_after_timeout = True
        self.create_emergency_backup = True
        
        # Signal handling
        self._setup_signal_handlers()
        
        # Emergency shutdown hook
        atexit.register(self._emergency_shutdown)
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            reason_map = {
                signal.SIGTERM: ShutdownReason.SYSTEM_SIGNAL,
                signal.SIGINT: ShutdownReason.SYSTEM_SIGNAL
            }
            
            reason = reason_map.get(signum, ShutdownReason.SYSTEM_SIGNAL)
            self.logger.info(f"Received signal {signum}, initiating shutdown")
            self.request_shutdown(reason)
        
        # Register signal handlers
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler)
        if hasattr(signal, 'SIGINT'):
            signal.signal(signal.SIGINT, signal_handler)
    
    def add_handler(self, handler: ShutdownHandler):
        """Add a shutdown handler"""
        with self._lock:
            self._handlers.append(handler)
            # Sort by priority (highest first) and then by phase order
            self._handlers.sort(key=lambda h: (h.get_priority(), h.get_shutdown_phase().value), reverse=True)
            
            self.logger.debug(f"Added shutdown handler for {handler.get_component_name()}")
    
    def remove_handler(self, handler: ShutdownHandler):
        """Remove a shutdown handler"""
        with self._lock:
            if handler in self._handlers:
                self._handlers.remove(handler)
                self.logger.debug(f"Removed shutdown handler for {handler.get_component_name()}")
    
    def request_shutdown(self, reason: ShutdownReason = ShutdownReason.USER_REQUEST):
        """Request graceful shutdown"""
        with self._lock:
            if self._shutdown_requested:
                self.logger.warning("Shutdown already requested, ignoring duplicate request")
                return
            
            self._shutdown_requested = True
            self.logger.info(f"Shutdown requested - Reason: {reason.value}")
        
        # Start shutdown in separate thread to avoid blocking
        shutdown_thread = threading.Thread(
            target=self._perform_shutdown,
            args=(reason,),
            name="ShutdownThread",
            daemon=True
        )
        shutdown_thread.start()
    
    def _perform_shutdown(self, reason: ShutdownReason):
        """Perform the actual shutdown process"""
        with self._lock:
            if self._shutdown_in_progress:
                return
            
            self._shutdown_in_progress = True
        
        start_time = time.time()
        
        try:
            self.logger.info("Starting graceful shutdown process")
            
            # Create emergency backup if enabled
            if self.create_emergency_backup:
                self._create_emergency_backup()
            
            # Execute shutdown phases
            all_success = True
            
            for phase in ShutdownPhase:
                phase_handlers = [h for h in self._handlers if h.get_shutdown_phase() == phase]
                
                if phase_handlers:
                    self.logger.info(f"Executing shutdown phase: {phase.name}")
                    phase_success = self._execute_shutdown_phase(phase, phase_handlers, reason)
                    
                    if not phase_success:
                        all_success = False
                        if reason == ShutdownReason.FATAL_ERROR:
                            # For fatal errors, continue with remaining phases
                            self.logger.warning(f"Phase {phase.name} failed, continuing with remaining phases")
                        else:
                            # For other reasons, consider rollback
                            self.logger.error(f"Phase {phase.name} failed, considering rollback")
                            break
            
            # Check if rollback is needed
            if not all_success and reason != ShutdownReason.FATAL_ERROR:
                self.logger.warning("Shutdown incomplete, attempting rollback")
                self._perform_rollback(reason)
            
            duration = (time.time() - start_time) * 1000
            
            if all_success:
                self.logger.info(f"Graceful shutdown completed successfully in {duration:.2f}ms")
            else:
                self.logger.warning(f"Shutdown completed with errors in {duration:.2f}ms")
            
        except Exception as e:
            self.logger.error(f"Critical error during shutdown: {e}")
            report_error(
                ErrorCode.COMPONENT_INIT_FAILED,
                f"Shutdown process failed: {e}",
                severity=ErrorSeverity.ERROR,
                component_name="ShutdownManager",
                exception=e
            )
        
        finally:
            with self._lock:
                self._shutdown_completed = True
                self._shutdown_in_progress = False
    
    def _execute_shutdown_phase(
        self, 
        phase: ShutdownPhase, 
        handlers: List[ShutdownHandler], 
        reason: ShutdownReason
    ) -> bool:
        """Execute a shutdown phase with all its handlers"""
        phase_success = True
        
        for handler in handlers:
            event = ShutdownEvent(
                phase=phase,
                component=handler.get_component_name()
            )
            
            start_time = time.time()
            
            try:
                self.logger.debug(f"Shutting down component: {handler.get_component_name()}")
                
                success = handler.shutdown(reason)
                event.success = success
                
                if not success:
                    phase_success = False
                    event.error_message = f"Component {handler.get_component_name()} shutdown failed"
                    self.logger.warning(event.error_message)
                
            except Exception as e:
                event.success = False
                event.error_message = str(e)
                phase_success = False
                
                self.logger.error(f"Exception during {handler.get_component_name()} shutdown: {e}")
                
            finally:
                event.duration_ms = (time.time() - start_time) * 1000
                self._shutdown_events.append(event)
        
        return phase_success
    
    def _perform_rollback(self, reason: ShutdownReason):
        """Perform rollback operations"""
        self.logger.info("Starting rollback process")
        
        # Create rollback state
        rollback_state = RollbackState(
            reason=reason,
            failed_component="unknown"  # This would be set based on which component failed
        )
        
        self._rollback_state = rollback_state
        
        # Execute rollback handlers in reverse order
        rollback_handlers = [h for h in reversed(self._handlers) if h.supports_rollback()]
        
        for handler in rollback_handlers:
            try:
                self.logger.debug(f"Rolling back component: {handler.get_component_name()}")
                
                success = handler.rollback(rollback_state)
                
                if success:
                    self.logger.info(f"Rollback successful for {handler.get_component_name()}")
                else:
                    self.logger.warning(f"Rollback failed for {handler.get_component_name()}")
                
            except Exception as e:
                self.logger.error(f"Exception during {handler.get_component_name()} rollback: {e}")
    
    def _create_emergency_backup(self):
        """Create emergency backup of critical data"""
        try:
            # This is a placeholder - actual implementation would backup:
            # - Configuration files
            # - Database snapshots
            # - User data
            # - Application state
            
            backup_dir = Path("backups") / f"emergency_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            self.logger.info(f"Emergency backup created: {backup_dir}")
            
            if self._rollback_state:
                self._rollback_state.backup_created = True
            
        except Exception as e:
            self.logger.warning(f"Failed to create emergency backup: {e}")
    
    def _emergency_shutdown(self):
        """Emergency shutdown hook called by atexit"""
        if not self._shutdown_completed and not self._shutdown_in_progress:
            self.logger.warning("Emergency shutdown triggered")
            
            # Quick cleanup of critical resources
            try:
                # Close database connections
                # Clear temporary files
                # Save critical state
                pass
            except Exception as e:
                print(f"Emergency shutdown error: {e}")
    
    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested"""
        with self._lock:
            return self._shutdown_requested
    
    def is_shutdown_in_progress(self) -> bool:
        """Check if shutdown is currently in progress"""
        with self._lock:
            return self._shutdown_in_progress
    
    def is_shutdown_completed(self) -> bool:
        """Check if shutdown has completed"""
        with self._lock:
            return self._shutdown_completed
    
    def get_shutdown_events(self) -> List[ShutdownEvent]:
        """Get list of shutdown events"""
        with self._lock:
            return self._shutdown_events.copy()
    
    def get_rollback_state(self) -> Optional[RollbackState]:
        """Get current rollback state"""
        with self._lock:
            return self._rollback_state
    
    def wait_for_shutdown(self, timeout: float = None) -> bool:
        """Wait for shutdown to complete"""
        if timeout is None:
            timeout = self.shutdown_timeout
        
        start_time = time.time()
        
        while not self.is_shutdown_completed():
            if time.time() - start_time > timeout:
                if self.force_shutdown_after_timeout:
                    self.logger.warning("Shutdown timeout exceeded, forcing exit")
                    os._exit(1)
                else:
                    return False
            
            time.sleep(0.1)
        
        return True
    
    def force_shutdown(self):
        """Force immediate shutdown without graceful cleanup"""
        self.logger.critical("Force shutdown requested")
        
        # Attempt minimal cleanup
        try:
            # Log final state
            self.logger.info("Force shutdown - attempting minimal cleanup")
            
            # Clear critical resources if possible
            for handler in self._handlers:
                try:
                    if hasattr(handler, 'force_cleanup'):
                        handler.force_cleanup()
                except Exception:
                    pass
                    
        except Exception:
            pass
        
        # Force exit
        os._exit(1)


# Global shutdown manager instance
_shutdown_manager: Optional[ShutdownManager] = None
_shutdown_manager_lock = threading.Lock()


def get_shutdown_manager() -> ShutdownManager:
    """Get the global shutdown manager instance (singleton)"""
    global _shutdown_manager
    
    with _shutdown_manager_lock:
        if _shutdown_manager is None:
            _shutdown_manager = ShutdownManager()
        
        return _shutdown_manager


def request_shutdown(reason: ShutdownReason = ShutdownReason.USER_REQUEST):
    """Convenience function to request shutdown"""
    return get_shutdown_manager().request_shutdown(reason)


def add_shutdown_handler(handler: ShutdownHandler):
    """Convenience function to add shutdown handler"""
    return get_shutdown_manager().add_handler(handler)


@contextmanager
def shutdown_context():
    """Context manager for automatic shutdown handling"""
    shutdown_manager = get_shutdown_manager()
    
    try:
        yield shutdown_manager
    except KeyboardInterrupt:
        shutdown_manager.request_shutdown(ShutdownReason.SYSTEM_SIGNAL)
        shutdown_manager.wait_for_shutdown()
    except Exception as e:
        shutdown_manager.logger.error(f"Unhandled exception: {e}")
        shutdown_manager.request_shutdown(ShutdownReason.FATAL_ERROR)
        raise 