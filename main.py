#!/usr/bin/env python3
"""
Social Download Manager v2.0 - Main Entry Point

This is the new main entry point for Social Download Manager v2.0, implementing
the dependency-aware initialization sequence from Task 30.1 and using the
adapter integration framework from Task 30.2 to bridge legacy UI with v2.0 architecture.

Key Features:
- Systematic 8-phase initialization following dependency analysis
- Automatic fallback: Full v2.0 → Degraded v2.0 → v1.2.1 legacy mode
- Task 29 adapter integration for seamless v1.2.1 UI compatibility
- Comprehensive error handling and recovery mechanisms
- Performance monitoring and metrics collection
- Graceful shutdown and rollback mechanisms
"""

import sys
import os
import traceback
import logging
from pathlib import Path

# Ensure we can import from the current directory
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Import version and basic constants first
try:
    from version import get_version_info, get_full_version, is_development_version, __version__
    from core.constants import AppConstants
    VERSION_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Version information not available: {e}")
    VERSION_AVAILABLE = False
    __version__ = "2.0.0-unknown"
    
    # Fallback constants
    class AppConstants:
        APP_NAME = "Social Download Manager"
        APP_VERSION = __version__
        MIN_PYTHON_VERSION = (3, 8)

# Import the main orchestrator
try:
    from core.main_entry_orchestrator import (
        MainEntryOrchestrator, StartupConfig, StartupMode, StartupPhase,
        create_default_startup_config, startup_context
    )
    ORCHESTRATOR_AVAILABLE = True
except ImportError as e:
    print(f"Error: Main orchestrator not available: {e}")
    ORCHESTRATOR_AVAILABLE = False

# Import PyQt6 for basic error handling
try:
    from PyQt6.QtWidgets import QApplication, QMessageBox
    from PyQt6.QtCore import QTimer
    PYQT6_AVAILABLE = True
except ImportError as e:
    print(f"Warning: PyQt6 not available: {e}")
    PYQT6_AVAILABLE = False

# Early imports for emergency error handling
from core.error_management import (
    get_error_manager, ErrorCode, ErrorSeverity, report_error, 
    report_system_error, report_dependency_error
)
from core.logging_system import get_logging_system, get_logger, setup_development_logging
from core.shutdown_manager import (
    get_shutdown_manager, ShutdownReason, shutdown_context,
    UIShutdownHandler, AdapterShutdownHandler, DatabaseShutdownHandler, FileSystemShutdownHandler
)

def validate_python_version() -> bool:
    """Validate Python version meets minimum requirements"""
    if sys.version_info < AppConstants.MIN_PYTHON_VERSION:
        min_version_str = f"{AppConstants.MIN_PYTHON_VERSION[0]}.{AppConstants.MIN_PYTHON_VERSION[1]}"
        current_version_str = f"{sys.version_info.major}.{sys.version_info.minor}"
        
        report_error(
            ErrorCode.PYTHON_VERSION_TOO_OLD,
            f"Python {min_version_str}+ required, found {current_version_str}",
            severity=ErrorSeverity.FATAL,
            recovery_suggestions=[
                f"Please upgrade to Python {min_version_str} or later",
                "Visit https://python.org to download the latest version"
            ],
            requires_restart=True
        )
        return False
    
    return True

def show_emergency_error(title: str, message: str, details: str = None):
    """Show emergency error dialog when all else fails"""
    try:
        # Create minimal QApplication if none exists
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Create error dialog
        msgbox = QMessageBox()
        msgbox.setIcon(QMessageBox.Icon.Critical)
        msgbox.setWindowTitle(f"{AppConstants.APP_NAME} - {title}")
        msgbox.setText(message)
        
        if details:
            msgbox.setDetailedText(details)
        
        msgbox.setStandardButtons(QMessageBox.StandardButton.Ok)
        
        # Auto-close after 30 seconds
        QTimer.singleShot(30000, msgbox.accept)
        
        msgbox.exec()
        
    except Exception:
        # Final fallback - print to console
        print(f"\n{'='*60}")
        print(f"EMERGENCY ERROR: {title}")
        print(f"{'='*60}")
        print(f"{message}")
        if details:
            print(f"\nDetails:\n{details}")
        print(f"{'='*60}\n")

def setup_emergency_logging() -> logging.Logger:
    """Setup emergency logging for critical startup errors"""
    try:
        setup_development_logging()
        logger = get_logger("main")
        logger.info(f"Starting {AppConstants.APP_NAME} v{AppConstants.APP_VERSION}")
        logger.info(f"Python {sys.version}")
        logger.info(f"Platform: {sys.platform}")
        return logger
    except Exception as e:
        # Fallback to basic logging if our system fails
        logging.basicConfig(
            level=logging.ERROR,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        logger = logging.getLogger("emergency")
        logger.error(f"Failed to setup logging system: {e}")
        return logger

def main():
    """Main entry point with comprehensive error handling and shutdown management"""
    
    # Initialize emergency logging first
    logger = setup_emergency_logging()
    
    try:
        # Validate Python version
        if not validate_python_version():
            show_emergency_error(
                "Python Version Error",
                f"Python {AppConstants.MIN_PYTHON_VERSION[0]}.{AppConstants.MIN_PYTHON_VERSION[1]}+ required",
                f"Current version: {sys.version}"
            )
            return 1
        
        # Initialize shutdown manager early
        shutdown_manager = get_shutdown_manager()
        logger.info("Shutdown manager initialized")
        
        # Use shutdown context for automatic error handling
        with shutdown_context() as shutdown_mgr:
            logger.info("Entering shutdown-managed execution context")
            
            # Import orchestrator after basic systems are ready
            try:
                from core.main_entry_orchestrator import MainEntryOrchestrator, StartupMode
                logger.info("Main entry orchestrator imported successfully")
            except ImportError as e:
                logger.error(f"Failed to import orchestrator: {e}")
                report_dependency_error("main_entry_orchestrator", e)
                
                # Emergency fallback - try legacy main
                logger.warning("Attempting emergency fallback to legacy main")
                return run_legacy_fallback()
            
            # Initialize orchestrator
            orchestrator = None
            main_window = None
            qapplication = None
            adapter_framework = None
            
            try:
                # Create orchestrator with development mode
                startup_mode = StartupMode.FULL_V2_DEV if "--dev" in sys.argv else StartupMode.FULL_V2_PRODUCTION
                orchestrator = MainEntryOrchestrator(startup_mode=startup_mode)
                
                logger.info(f"Orchestrator created with mode: {startup_mode.name}")
                
                # Setup shutdown handlers early
                shutdown_mgr.add_handler(FileSystemShutdownHandler())
                logger.debug("FileSystem shutdown handler registered")
                
                # Initialize v2.0 system using orchestrator context manager
                with orchestrator as (app, window, adapter_integration):
                    logger.info("Orchestrator context manager entered - v2.0 initialization complete")
                    
                    # Store references for shutdown handlers
                    qapplication = app
                    main_window = window
                    adapter_framework = adapter_integration
                    
                    # Register additional shutdown handlers now that we have references
                    if adapter_framework:
                        shutdown_mgr.add_handler(AdapterShutdownHandler(adapter_framework))
                        logger.debug("Adapter shutdown handler registered")
                    
                    if main_window and qapplication:
                        shutdown_mgr.add_handler(UIShutdownHandler(main_window, qapplication))
                        logger.debug("UI shutdown handler registered")
                    
                    # Get startup metrics
                    metrics = orchestrator.get_metrics()
                    startup_duration = metrics.get('total_startup_time_ms', 0)
                    startup_mode_final = metrics.get('final_mode', 'unknown')
                    
                    logger.info(f"✅ v2.0 startup completed successfully!")
                    logger.info(f"   Mode: {startup_mode_final}")
                    logger.info(f"   Duration: {startup_duration:.2f}ms")
                    logger.info(f"   Components initialized: {metrics.get('components_initialized', 0)}")
                    
                    # Run Qt application event loop
                    if qapplication and main_window:
                        logger.info("Starting Qt event loop")
                        
                        # Show main window
                        main_window.show()
                        
                        # Execute application
                        exit_code = qapplication.exec()
                        
                        logger.info(f"Qt event loop finished with exit code: {exit_code}")
                        return exit_code
                    else:
                        logger.error("No QApplication or MainWindow available")
                        return 1
                        
            except KeyboardInterrupt:
                logger.info("User interrupted application (Ctrl+C)")
                shutdown_mgr.request_shutdown(ShutdownReason.SYSTEM_SIGNAL)
                return 0
                
            except Exception as e:
                logger.error(f"Unhandled exception in main execution: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                
                # Report the error
                report_error(
                    ErrorCode.COMPONENT_INIT_FAILED,
                    f"Main execution failed: {e}",
                    severity=ErrorSeverity.CRITICAL,
                    exception=e,
                    component_name="MainExecution",
                    recovery_suggestions=[
                        "Try restarting the application",
                        "Check system resources and dependencies",
                        "Run in safe mode with --safe flag"
                    ]
                )
                
                # Attempt graceful shutdown
                shutdown_mgr.request_shutdown(ShutdownReason.FATAL_ERROR)
                shutdown_mgr.wait_for_shutdown(timeout=10.0)
                
                return 1
                
            finally:
                # Ensure shutdown is requested if not already done
                if not shutdown_mgr.is_shutdown_requested():
                    logger.info("Requesting normal shutdown")
                    shutdown_mgr.request_shutdown(ShutdownReason.USER_REQUEST)
                
                # Wait for graceful shutdown
                logger.info("Waiting for graceful shutdown...")
                shutdown_completed = shutdown_mgr.wait_for_shutdown(timeout=15.0)
                
                if shutdown_completed:
                    logger.info("Graceful shutdown completed successfully")
                else:
                    logger.warning("Shutdown timeout - some cleanup may be incomplete")
                
                # Log final statistics
                events = shutdown_mgr.get_shutdown_events()
                successful_shutdowns = sum(1 for e in events if e.success)
                total_shutdowns = len(events)
                
                logger.info(f"Shutdown summary: {successful_shutdowns}/{total_shutdowns} components shut down successfully")
                
                if orchestrator:
                    final_metrics = orchestrator.get_metrics()
                    logger.info(f"Final metrics: {final_metrics}")
        
        # Normal exit
        logger.info(f"{AppConstants.APP_NAME} v{AppConstants.APP_VERSION} shutdown complete")
        return 0
        
    except Exception as e:
        # Critical error that happened outside our error management system
        error_msg = f"Critical startup error: {e}"
        
        try:
            logger.critical(error_msg)
            logger.critical(f"Traceback: {traceback.format_exc()}")
        except:
            pass
        
        show_emergency_error(
            "Critical Startup Error",
            "A critical error occurred during application startup.",
            f"{error_msg}\n\n{traceback.format_exc()}"
        )
        
        return 1

def run_legacy_fallback():
    """Emergency fallback to legacy v1.2.1 main"""
    try:
        logger = get_logger("legacy_fallback")
        logger.warning("Running emergency fallback to legacy v1.2.1 main")
        
        # Try to import and run legacy main
        try:
            import main_v2
            return main_v2.main()
        except ImportError:
            # Try absolute fallback
            if Path("main_v2.py").exists():
                exec(open("main_v2.py").read())
                return 0
        else:
                logger.error("Legacy main_v2.py not found")
                return 1
                
    except Exception as e:
        show_emergency_error(
            "Legacy Fallback Failed",
            "Both v2.0 and legacy systems failed to start.",
            f"Error: {e}\n\nPlease check your installation."
        )
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except SystemExit:
        # Allow normal system exits
        raise
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        print("\nApplication interrupted by user")
        sys.exit(0)
    except Exception as e:
        # Final catch-all for any unhandled exceptions
        show_emergency_error(
            "Fatal Error",
            "An unexpected fatal error occurred.",
            f"Error: {e}\n\n{traceback.format_exc()}"
        )
        sys.exit(1) 