"""
Main Entry Point Orchestrator for Social Download Manager v2.0

This module provides the orchestration logic for the main entry point, coordinating
the startup sequence according to the dependency analysis from Task 30.1 and using
the adapter integration framework from Task 30.2.
"""

import sys
import os
import logging
import time
import traceback
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from contextlib import contextmanager

# Add current directory to Python path for imports
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# PyQt6 imports
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt6.QtCore import QTimer

# Import v2.0 core components (following Task 30.1 dependency order)
from core.constants import (
    AppConstants, validate_constants, get_platform_name, is_supported_platform
)
from core.config_manager import get_config_manager, get_config
from core.event_system import get_event_bus, publish_event, EventType
from core.app_controller import get_app_controller, initialize_app_controller, shutdown_app_controller

# Import database and repository layer
try:
    from data.database import get_connection_manager, initialize_database, shutdown_database
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    logging.warning("Database layer not available, falling back to memory-only mode")

# Import service layer
try:
    from core.services import get_service_registry
    SERVICES_AVAILABLE = True
except ImportError:
    SERVICES_AVAILABLE = False
    logging.warning("Service layer not available")

# Import platform factory
try:
    from platforms.platform_factory import PlatformFactory
    PLATFORM_FACTORY_AVAILABLE = True
except ImportError:
    PLATFORM_FACTORY_AVAILABLE = False
    logging.warning("Platform factory not available")

# Import adapter integration framework
from core.adapter_integration import (
    AdapterIntegrationFramework, get_integration_framework, setup_standard_adapters,
    IntegrationConfig, IntegrationState, IntegrationMode, create_default_integration_config
)

# Import version information
from version import get_version_info, get_full_version, is_development_version


class StartupPhase(Enum):
    """Startup phases following Task 30.1 dependency analysis"""
    UNINITIALIZED = auto()
    CONSTANTS_VALIDATION = auto()
    CORE_FOUNDATION = auto()
    DATA_LAYER = auto()
    SERVICE_LAYER = auto()
    BRIDGE_LAYER = auto()
    UI_ADAPTERS = auto()
    LEGACY_UI = auto()
    VERIFICATION = auto()
    COMPLETED = auto()
    FAILED = auto()


class StartupMode(Enum):
    """Startup operation modes"""
    FULL_V2 = "full_v2"                # Complete v2.0 + adapters + legacy UI
    DEGRADED_V2 = "degraded_v2"        # Core v2.0 + minimal adapters + legacy UI
    FALLBACK_V1 = "fallback_v1"        # Legacy UI only, minimal v2.0 core
    EMERGENCY = "emergency"             # Emergency mode with error dialogs


@dataclass
class StartupConfig:
    """Configuration for main entry point orchestrator"""
    # Core settings
    enable_v2_architecture: bool = True
    enable_adapter_integration: bool = True
    enable_fallback_mode: bool = True
    
    # Timeout settings (in seconds)
    phase_timeout: float = 30.0
    component_timeout: float = 10.0
    total_startup_timeout: float = 60.0
    
    # Retry settings
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # Feature flags
    feature_flags: Dict[str, bool] = field(default_factory=lambda: {
        "enable_performance_monitoring": True,
        "enable_crash_reporting": True,
        "enable_startup_splash": False,
        "enable_debug_logging": False,
        "skip_non_critical_components": True,
        "allow_partial_initialization": True
    })
    
    # Integration settings
    integration_config: Optional[IntegrationConfig] = None
    
    # UI settings
    ui_settings: Dict[str, Any] = field(default_factory=lambda: {
        "show_startup_errors": True,
        "auto_close_error_dialogs": False,
        "error_dialog_timeout": 10.0
    })


@dataclass
class StartupMetrics:
    """Metrics for startup process"""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    total_duration: timedelta = field(default_factory=lambda: timedelta())
    
    current_phase: StartupPhase = StartupPhase.UNINITIALIZED
    current_mode: StartupMode = StartupMode.FULL_V2
    
    phases_completed: List[StartupPhase] = field(default_factory=list)
    phases_failed: List[StartupPhase] = field(default_factory=list)
    phase_durations: Dict[StartupPhase, float] = field(default_factory=dict)
    
    components_initialized: int = 0
    components_failed: int = 0
    fallback_triggers: List[str] = field(default_factory=list)
    
    success_rate: float = 1.0
    memory_usage: float = 0.0
    last_error: Optional[str] = None
    error_count: int = 0


class MainEntryOrchestratorError(Exception):
    """Exception raised by main entry orchestrator operations"""
    pass


class MainEntryOrchestrator:
    """
    Main entry point orchestrator implementing the startup sequence
    
    Coordinates the initialization of all components according to the dependency
    analysis from Task 30.1, using the adapter integration framework to bridge
    v1.2.1 UI with v2.0 architecture.
    """
    
    def __init__(self, config: Optional[StartupConfig] = None):
        self.config = config or StartupConfig()
        self.metrics = StartupMetrics()
        self.logger = logging.getLogger(__name__)
        
        # Core state
        self._phase = StartupPhase.UNINITIALIZED
        self._mode = StartupMode.FULL_V2
        self._startup_time = datetime.now()
        
        # Component references
        self._qt_application: Optional[QApplication] = None
        self._main_window: Optional[QMainWindow] = None
        self._integration_framework: Optional[AdapterIntegrationFramework] = None
        
        # Startup components (following Task 30.1 dependency order)
        self._components: Dict[str, Any] = {}
        self._component_status: Dict[str, bool] = {}
        self._initialization_callbacks: List[Callable[[], bool]] = []
        self._error_handlers: List[Callable[[Exception, str], None]] = []
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Set up logging configuration"""
        try:
            # Configure root logger
            log_level = logging.DEBUG if self.config.feature_flags.get("enable_debug_logging", False) else logging.INFO
            logging.basicConfig(
                level=log_level,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.StreamHandler(sys.stdout),
                    logging.FileHandler('app_startup.log', mode='w')
                ]
            )
            
            self.logger.info("Logging configured successfully")
            
        except Exception as e:
            print(f"Failed to setup logging: {e}")
    
    def run_startup_sequence(self) -> Tuple[bool, QApplication, Optional[QMainWindow]]:
        """
        Run the complete startup sequence
        
        Returns:
            Tuple of (success, qt_application, main_window)
        """
        try:
            self.logger.info(f"Starting {AppConstants.APP_NAME} v{AppConstants.APP_VERSION} startup sequence...")
            self._startup_time = datetime.now()
            self.metrics.start_time = self._startup_time
            
            # Phase 1: Constants Validation (Critical)
            if not self._execute_phase(StartupPhase.CONSTANTS_VALIDATION, self._validate_constants):
                return self._handle_critical_failure("Constants validation failed")
            
            # Phase 2: Core Foundation (Critical)
            if not self._execute_phase(StartupPhase.CORE_FOUNDATION, self._initialize_core_foundation):
                return self._handle_critical_failure("Core foundation initialization failed")
            
            # Phase 3: Data Layer (High Priority - can fallback)
            if not self._execute_phase(StartupPhase.DATA_LAYER, self._initialize_data_layer):
                self.logger.warning("Data layer initialization failed, enabling fallback mode")
                self._enable_fallback_mode("data_layer_failure")
            
            # Phase 4: Service Layer (Medium Priority)
            if not self._execute_phase(StartupPhase.SERVICE_LAYER, self._initialize_service_layer):
                self.logger.warning("Service layer initialization failed, continuing with limited functionality")
                self._enable_degraded_mode("service_layer_failure")
            
            # Phase 5: Bridge Layer (High Priority for v2.0 features)
            if not self._execute_phase(StartupPhase.BRIDGE_LAYER, self._initialize_bridge_layer):
                self.logger.warning("Bridge layer initialization failed, falling back to v1.2.1 mode")
                self._enable_fallback_mode("bridge_layer_failure")
            
            # Phase 6: UI Adapters (High Priority if bridge layer succeeded)
            if self._mode != StartupMode.FALLBACK_V1:
                if not self._execute_phase(StartupPhase.UI_ADAPTERS, self._initialize_ui_adapters):
                    self.logger.warning("UI adapters initialization failed, using minimal adapters")
                    self._enable_degraded_mode("ui_adapters_failure")
            
            # Phase 7: Legacy UI (Critical)
            if not self._execute_phase(StartupPhase.LEGACY_UI, self._initialize_legacy_ui):
                return self._handle_critical_failure("Legacy UI initialization failed")
            
            # Phase 8: Verification
            if not self._execute_phase(StartupPhase.VERIFICATION, self._verify_startup):
                self.logger.warning("Startup verification failed, but continuing...")
            
            # Complete startup
            self._phase = StartupPhase.COMPLETED
            self.metrics.current_phase = self._phase
            self._finalize_startup()
            
            self.logger.info(f"Startup completed successfully in mode: {self._mode}")
            return True, self._qt_application, self._main_window
            
        except Exception as e:
            self.logger.error(f"Unexpected error during startup: {e}")
            self.logger.error(traceback.format_exc())
            return self._handle_critical_failure(f"Unexpected startup error: {e}")
    
    def _execute_phase(self, phase: StartupPhase, phase_function: Callable[[], bool]) -> bool:
        """Execute a startup phase with timing and error handling"""
        try:
            self.logger.info(f"Starting phase: {phase.name}")
            self._phase = phase
            self.metrics.current_phase = phase
            
            phase_start = time.time()
            
            # Execute phase function
            success = phase_function()
            
            phase_duration = time.time() - phase_start
            self.metrics.phase_durations[phase] = phase_duration
            
            if success:
                self.metrics.phases_completed.append(phase)
                self.logger.info(f"Phase {phase.name} completed in {phase_duration:.3f}s")
                return True
            else:
                self.metrics.phases_failed.append(phase)
                self.logger.error(f"Phase {phase.name} failed after {phase_duration:.3f}s")
                return False
                
        except Exception as e:
            self.metrics.phases_failed.append(phase)
            self.metrics.error_count += 1
            self.metrics.last_error = str(e)
            self.logger.error(f"Exception in phase {phase.name}: {e}")
            return False
    
    def _validate_constants(self) -> bool:
        """Phase 1: Validate application constants"""
        try:
            self.logger.info("Validating application constants...")
            
            if not validate_constants():
                self.logger.error("Constants validation failed!")
                return False
            
            # Log application information
            self.logger.info(f"Application: {AppConstants.APP_NAME}")
            self.logger.info(f"Version: {AppConstants.APP_VERSION}")
            self.logger.info(f"Full Version: {get_full_version()}")
            self.logger.info(f"Development Mode: {is_development_version()}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Constants validation error: {e}")
            return False
    
    def _initialize_core_foundation(self) -> bool:
        """Phase 2: Initialize core foundation components"""
        try:
            self.logger.info("Initializing core foundation...")
            
            # Initialize Config Manager
            if not self._initialize_component("config_manager", get_config_manager):
                return False
            
            # Initialize Event Bus
            if not self._initialize_component("event_bus", get_event_bus):
                return False
            
            # Initialize App Controller
            if not self._initialize_component("app_controller", lambda: initialize_app_controller() and get_app_controller()):
                return False
            
            self.logger.info("Core foundation initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Core foundation initialization error: {e}")
            return False
    
    def _initialize_data_layer(self) -> bool:
        """Phase 3: Initialize data layer components"""
        try:
            self.logger.info("Initializing data layer...")
            
            if not DATABASE_AVAILABLE:
                self.logger.warning("Database layer not available, using memory-only mode")
                return True
            
            # Initialize Database Connection Manager
            if not self._initialize_component("database_manager", get_connection_manager):
                self.logger.warning("Database connection manager initialization failed")
                return False
            
            # Initialize Database
            if not self._initialize_component("database", lambda: initialize_database()):
                self.logger.warning("Database initialization failed")
                return False
            
            self.logger.info("Data layer initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Data layer initialization error: {e}")
            return False
    
    def _initialize_service_layer(self) -> bool:
        """Phase 4: Initialize service layer components"""
        try:
            self.logger.info("Initializing service layer...")
            
            if not SERVICES_AVAILABLE:
                self.logger.warning("Service layer not available")
                return True
            
            # Initialize Service Registry
            if not self._initialize_component("service_registry", get_service_registry):
                self.logger.warning("Service registry initialization failed")
                return False
            
            # Initialize Platform Factory (if available)
            if PLATFORM_FACTORY_AVAILABLE:
                if not self._initialize_component("platform_factory", lambda: PlatformFactory()):
                    self.logger.warning("Platform factory initialization failed")
                    # Not critical, continue
            
            self.logger.info("Service layer initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Service layer initialization error: {e}")
            return False
    
    def _initialize_bridge_layer(self) -> bool:
        """Phase 5: Initialize adapter bridge layer"""
        try:
            self.logger.info("Initializing adapter bridge layer...")
            
            # Create integration configuration
            integration_config = self.config.integration_config or create_default_integration_config()
            
            # Get integration framework
            self._integration_framework = get_integration_framework()
            
            # Initialize framework
            if not self._integration_framework.initialize(integration_config):
                self.logger.error("Integration framework initialization failed")
                return False
            
            # Set up standard adapters
            if not setup_standard_adapters(self._integration_framework):
                self.logger.error("Standard adapters setup failed")
                return False
            
            self._components["integration_framework"] = self._integration_framework
            self.logger.info("Adapter bridge layer initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Bridge layer initialization error: {e}")
            return False
    
    def _initialize_ui_adapters(self) -> bool:
        """Phase 6: Initialize UI adapters"""
        try:
            self.logger.info("Initializing UI adapters...")
            
            if not self._integration_framework:
                self.logger.error("Integration framework not available for UI adapters")
                return False
            
            # Start adapter integration
            if not self._integration_framework.start_integration():
                self.logger.error("Adapter integration start failed")
                return False
            
            self.logger.info("UI adapters initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"UI adapters initialization error: {e}")
            return False
    
    def _initialize_legacy_ui(self) -> bool:
        """Phase 7: Initialize legacy UI components"""
        try:
            self.logger.info("Initializing legacy UI...")
            
            # Create PyQt6 Application
            if not self._create_qt_application():
                return False
            
            # Create Main Window
            if not self._create_main_window():
                return False
            
            # Attach components to adapters (if integration framework is available)
            if self._integration_framework and self._mode != StartupMode.FALLBACK_V1:
                if not self._integration_framework.attach_legacy_components(self._qt_application, self._main_window):
                    self.logger.warning("Failed to attach legacy components to adapters")
                    # Not critical, continue
            
            self.logger.info("Legacy UI initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Legacy UI initialization error: {e}")
            return False
    
    def _create_qt_application(self) -> bool:
        """Create PyQt6 QApplication"""
        try:
            if QApplication.instance() is not None:
                self._qt_application = QApplication.instance()
                self.logger.info("Using existing QApplication instance")
            else:
                self._qt_application = QApplication(sys.argv)
                self.logger.info("Created new QApplication instance")
            
            # Configure application
            self._qt_application.setApplicationName(AppConstants.APP_NAME)
            self._qt_application.setApplicationVersion(AppConstants.APP_VERSION)
            self._qt_application.setOrganizationName("Social Download Manager")
            
            return True
            
        except Exception as e:
            self.logger.error(f"QApplication creation error: {e}")
            return False
    
    def _create_main_window(self) -> bool:
        """Create main window - import legacy UI"""
        try:
            # Import legacy MainWindow
            try:
                from ui.main_window import MainWindow
                self._main_window = MainWindow()
                self.logger.info("Legacy MainWindow created successfully")
                return True
            except ImportError as e:
                self.logger.error(f"Failed to import legacy MainWindow: {e}")
                # Try to create a minimal main window
                return self._create_minimal_main_window()
            
        except Exception as e:
            self.logger.error(f"Main window creation error: {e}")
            return False
    
    def _create_minimal_main_window(self) -> bool:
        """Create minimal main window as fallback"""
        try:
            from PyQt6.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QWidget
            
            self._main_window = QMainWindow()
            self._main_window.setWindowTitle(f"{AppConstants.APP_NAME} v{AppConstants.APP_VERSION}")
            self._main_window.setMinimumSize(800, 600)
            
            # Create minimal content
            central_widget = QWidget()
            layout = QVBoxLayout()
            
            label = QLabel(f"Welcome to {AppConstants.APP_NAME}")
            label.setStyleSheet("font-size: 18px; padding: 20px;")
            layout.addWidget(label)
            
            status_label = QLabel(f"Running in {self._mode.value} mode")
            status_label.setStyleSheet("font-size: 14px; color: #666; padding: 10px;")
            layout.addWidget(status_label)
            
            central_widget.setLayout(layout)
            self._main_window.setCentralWidget(central_widget)
            
            self.logger.info("Minimal main window created as fallback")
            return True
            
        except Exception as e:
            self.logger.error(f"Minimal main window creation error: {e}")
            return False
    
    def _verify_startup(self) -> bool:
        """Phase 8: Verify startup success"""
        try:
            self.logger.info("Verifying startup...")
            
            # Check critical components
            critical_components = ["config_manager", "event_bus", "app_controller"]
            for component_name in critical_components:
                if component_name not in self._components or not self._component_status.get(component_name, False):
                    self.logger.error(f"Critical component {component_name} not available")
                    return False
            
            # Check UI components
            if not self._qt_application:
                self.logger.error("QApplication not available")
                return False
            
            if not self._main_window:
                self.logger.error("Main window not available")
                return False
            
            # Check integration framework (if not in fallback mode)
            if self._mode != StartupMode.FALLBACK_V1:
                if not self._integration_framework:
                    self.logger.warning("Integration framework not available")
                elif self._integration_framework.get_integration_status() not in [IntegrationState.ACTIVE, IntegrationState.DEGRADED]:
                    self.logger.warning(f"Integration framework in unexpected state: {self._integration_framework.get_integration_status()}")
            
            # Calculate success metrics
            total_components = len(self._component_status)
            successful_components = sum(self._component_status.values())
            self.metrics.components_initialized = successful_components
            self.metrics.components_failed = total_components - successful_components
            self.metrics.success_rate = successful_components / total_components if total_components > 0 else 1.0
            
            self.logger.info(f"Startup verification completed: {successful_components}/{total_components} components successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Startup verification error: {e}")
            return False
    
    def _initialize_component(self, component_name: str, initializer: Callable) -> bool:
        """Initialize a component with error handling"""
        try:
            self.logger.debug(f"Initializing component: {component_name}")
            
            component = initializer()
            if component:
                self._components[component_name] = component
                self._component_status[component_name] = True
                self.logger.debug(f"Component {component_name} initialized successfully")
                return True
            else:
                self._component_status[component_name] = False
                self.logger.error(f"Component {component_name} initialization returned None/False")
                return False
                
        except Exception as e:
            self._component_status[component_name] = False
            self.logger.error(f"Component {component_name} initialization error: {e}")
            return False
    
    def _enable_fallback_mode(self, reason: str) -> None:
        """Enable fallback mode due to component failure"""
        self.logger.warning(f"Enabling fallback mode due to: {reason}")
        self._mode = StartupMode.FALLBACK_V1
        self.metrics.current_mode = self._mode
        self.metrics.fallback_triggers.append(reason)
    
    def _enable_degraded_mode(self, reason: str) -> None:
        """Enable degraded mode due to component failure"""
        if self._mode == StartupMode.FULL_V2:  # Only degrade if not already in fallback
            self.logger.warning(f"Enabling degraded mode due to: {reason}")
            self._mode = StartupMode.DEGRADED_V2
            self.metrics.current_mode = self._mode
            self.metrics.fallback_triggers.append(reason)
    
    def _handle_critical_failure(self, error_message: str) -> Tuple[bool, Optional[QApplication], Optional[QMainWindow]]:
        """Handle critical startup failure"""
        self.logger.error(f"Critical startup failure: {error_message}")
        self._phase = StartupPhase.FAILED
        self.metrics.current_phase = self._phase
        self.metrics.last_error = error_message
        self.metrics.error_count += 1
        
        # Try to show error dialog if possible
        if self.config.ui_settings.get("show_startup_errors", True):
            self._show_startup_error(error_message)
        
        # Return emergency mode if we have minimal UI
        if self._qt_application:
            return False, self._qt_application, self._main_window
        else:
            return False, None, None
    
    def _show_startup_error(self, error_message: str) -> None:
        """Show startup error dialog"""
        try:
            if not self._qt_application:
                # Create minimal QApplication for error dialog
                self._qt_application = QApplication(sys.argv) if QApplication.instance() is None else QApplication.instance()
            
            msgbox = QMessageBox()
            msgbox.setIcon(QMessageBox.Icon.Critical)
            msgbox.setWindowTitle("Startup Error")
            msgbox.setText(f"{AppConstants.APP_NAME} failed to start properly.")
            msgbox.setDetailedText(f"Error: {error_message}\n\nPlease check the logs for more details.")
            msgbox.setStandardButtons(QMessageBox.StandardButton.Ok)
            
            # Auto-close timer if configured
            if self.config.ui_settings.get("auto_close_error_dialogs", False):
                timeout = self.config.ui_settings.get("error_dialog_timeout", 10.0)
                QTimer.singleShot(int(timeout * 1000), msgbox.accept)
            
            msgbox.exec()
            
        except Exception as e:
            self.logger.error(f"Failed to show startup error dialog: {e}")
            print(f"CRITICAL STARTUP ERROR: {error_message}")
    
    def _finalize_startup(self) -> None:
        """Finalize startup process"""
        try:
            self.metrics.end_time = datetime.now()
            self.metrics.total_duration = self.metrics.end_time - self.metrics.start_time
            
            # Log final metrics
            self.logger.info(f"Startup completed in {self.metrics.total_duration.total_seconds():.3f}s")
            self.logger.info(f"Mode: {self._mode}")
            self.logger.info(f"Components: {self.metrics.components_initialized}/{self.metrics.components_initialized + self.metrics.components_failed}")
            self.logger.info(f"Success rate: {self.metrics.success_rate:.2%}")
            
            if self.metrics.fallback_triggers:
                self.logger.info(f"Fallback triggers: {', '.join(self.metrics.fallback_triggers)}")
            
            # Publish startup complete event
            if "event_bus" in self._components:
                try:
                    publish_event(EventType.APP_STARTUP, {
                        "startup_mode": self._mode.value,
                        "startup_duration": self.metrics.total_duration.total_seconds(),
                        "success_rate": self.metrics.success_rate
                    })
                except Exception as e:
                    self.logger.error(f"Failed to publish startup event: {e}")
            
        except Exception as e:
            self.logger.error(f"Error finalizing startup: {e}")
    
    def get_startup_metrics(self) -> StartupMetrics:
        """Get startup metrics"""
        return self.metrics
    
    def get_startup_mode(self) -> StartupMode:
        """Get current startup mode"""
        return self._mode
    
    def get_component_status(self) -> Dict[str, bool]:
        """Get component initialization status"""
        return self._component_status.copy()


def create_default_startup_config() -> StartupConfig:
    """Create default startup configuration"""
    return StartupConfig()


@contextmanager
def startup_context(config: Optional[StartupConfig] = None):
    """Context manager for startup orchestration"""
    if config is None:
        config = create_default_startup_config()
    
    orchestrator = MainEntryOrchestrator(config)
    
    try:
        yield orchestrator
    finally:
        # Cleanup if needed
        pass


def main() -> int:
    """
    Main entry point for the application
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        # Create orchestrator with default configuration
        config = create_default_startup_config()
        orchestrator = MainEntryOrchestrator(config)
        
        # Run startup sequence
        success, qt_app, main_window = orchestrator.run_startup_sequence()
        
        if not success:
            print("Application startup failed")
            return 1
        
        if not qt_app:
            print("No QApplication available")
            return 1
        
        # Show main window
        if main_window:
            main_window.show()
        
        # Start application event loop
        return qt_app.exec()
        
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        return 130
    except Exception as e:
        print(f"Unexpected error: {e}")
        traceback.print_exc()
        return 1
    finally:
        # Cleanup
        try:
            shutdown_app_controller()
            if DATABASE_AVAILABLE:
                shutdown_database()
        except Exception as e:
            print(f"Cleanup error: {e}")


if __name__ == "__main__":
    sys.exit(main()) 