"""
Application Lifecycle Manager for v2.0 UI Architecture

This module provides comprehensive application lifecycle management including:
- Prioritized initialization sequence for critical components
- Progressive UI rendering during startup
- Resource cleanup protocols for application shutdown
- Session persistence mechanisms for quick restarts
- Startup performance analytics and optimization
"""

import logging
import threading
import time
import asyncio
import sys
import os
from typing import Dict, Any, Optional, Callable, List, Set, Union, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from collections import defaultdict, deque
import json
import signal
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QThread
from PyQt6.QtWidgets import QWidget, QSplashScreen, QProgressBar, QApplication

logger = logging.getLogger(__name__)


class LifecyclePhase(Enum):
    """Application lifecycle phases"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing" 
    RUNNING = "running"
    SHUTTING_DOWN = "shutting_down"
    TERMINATED = "terminated"


class InitializationStage(Enum):
    """Initialization stages with priorities"""
    CRITICAL = "critical"      # Essential systems (logging, config)
    CORE = "core"             # Core components (state, performance)
    SERVICES = "services"      # Business services (platforms, data)
    UI_FOUNDATION = "ui_foundation"  # Basic UI (themes, i18n)
    UI_COMPONENTS = "ui_components"  # UI components (tabs, widgets)
    FEATURES = "features"      # Feature modules (downloads, settings)
    OPTIMIZATION = "optimization"  # Performance optimizations


class ShutdownStage(Enum):
    """Shutdown stages with priorities"""
    GRACEFUL_STOP = "graceful_stop"    # Stop accepting new work
    SAVE_STATE = "save_state"          # Save application state
    CLEANUP_UI = "cleanup_ui"          # Clean up UI components
    CLEANUP_SERVICES = "cleanup_services"  # Clean up services
    CLEANUP_CORE = "cleanup_core"      # Clean up core systems
    FINAL_CLEANUP = "final_cleanup"    # Final resource cleanup


@dataclass
class InitializationTask:
    """Individual initialization task"""
    id: str
    name: str
    stage: InitializationStage
    handler: Callable[[], bool]
    
    # Dependencies
    dependencies: List[str] = field(default_factory=list)
    optional_dependencies: List[str] = field(default_factory=list)
    
    # Timing
    timeout_seconds: float = 30.0
    estimated_duration_ms: float = 100.0
    
    # Status
    completed: bool = False
    failed: bool = False
    error_message: Optional[str] = None
    execution_time_ms: Optional[float] = None
    
    # Progress
    progress_callback: Optional[Callable[[float], None]] = None
    
    # Metadata
    description: str = ""
    critical: bool = False


@dataclass
class ShutdownTask:
    """Individual shutdown task"""
    id: str
    name: str
    stage: ShutdownStage
    handler: Callable[[], bool]
    
    # Timing
    timeout_seconds: float = 10.0
    force_after_timeout: bool = True
    
    # Status
    completed: bool = False
    failed: bool = False
    error_message: Optional[str] = None
    execution_time_ms: Optional[float] = None
    
    # Metadata
    description: str = ""
    critical: bool = False


@dataclass
class LifecycleMetrics:
    """Lifecycle performance metrics"""
    # Startup metrics
    total_startup_time_ms: float = 0.0
    critical_startup_time_ms: float = 0.0
    ui_ready_time_ms: float = 0.0
    
    # Task metrics
    successful_init_tasks: int = 0
    failed_init_tasks: int = 0
    successful_shutdown_tasks: int = 0
    failed_shutdown_tasks: int = 0
    
    # Performance
    fastest_startup_ms: float = 0.0
    slowest_startup_ms: float = 0.0
    average_startup_ms: float = 0.0
    
    # Reliability
    clean_shutdowns: int = 0
    forced_shutdowns: int = 0
    crash_recoveries: int = 0


class LifecycleManager(QObject):
    """
    Advanced application lifecycle manager providing comprehensive startup/shutdown
    orchestration, progressive loading, and performance optimization
    for v2.0 UI architecture.
    """
    
    # Signals for lifecycle events
    phase_changed = pyqtSignal(str, str)  # old_phase, new_phase
    startup_progress = pyqtSignal(str, float, str)  # stage, progress, message
    startup_completed = pyqtSignal(float)  # total_time_ms
    shutdown_started = pyqtSignal(str)  # reason
    shutdown_progress = pyqtSignal(str, float, str)  # stage, progress, message
    shutdown_completed = pyqtSignal(float)  # total_time_ms
    task_started = pyqtSignal(str, str)  # task_id, task_name
    task_completed = pyqtSignal(str, bool, float)  # task_id, success, duration_ms
    error_occurred = pyqtSignal(str, str)  # task_id, error_message
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.config = self._create_default_config()
        if config:
            self.config.update(config)
        
        # Core state
        self._current_phase = LifecyclePhase.UNINITIALIZED
        self._startup_begin_time: Optional[datetime] = None
        self._shutdown_begin_time: Optional[datetime] = None
        
        # Task management
        self._init_tasks: Dict[str, InitializationTask] = {}
        self._shutdown_tasks: Dict[str, ShutdownTask] = {}
        self._task_execution_order: List[str] = []
        
        # Stage organization
        self._init_stages: Dict[InitializationStage, List[str]] = defaultdict(list)
        self._shutdown_stages: Dict[ShutdownStage, List[str]] = defaultdict(list)
        
        # Progress tracking
        self._current_stage: Optional[Union[InitializationStage, ShutdownStage]] = None
        self._stage_progress: float = 0.0
        self._overall_progress: float = 0.0
        
        # Session management
        self._session_data: Dict[str, Any] = {}
        self._session_file = Path(self.config['session_file'])
        
        # Metrics and monitoring
        self._metrics = LifecycleMetrics()
        self._startup_history: deque = deque(maxlen=100)
        
        # UI components
        self._splash_screen: Optional[QSplashScreen] = None
        self._progress_bar: Optional[QProgressBar] = None
        
        # Error handling
        self._critical_errors: List[str] = []
        self._recovery_handlers: Dict[str, Callable] = {}
        
        # Threading and synchronization
        self._lock = threading.RLock()
        self._shutdown_event = threading.Event()
        
        # Initialize system
        self._setup_signal_handlers()
        self._load_session_data()
        self._register_default_tasks()
        
        self.logger.info(f"LifecycleManager initialized with config: {self.config}")
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration for lifecycle manager"""
        return {
            'session_file': 'data/session.json',
            'enable_splash_screen': True,
            'enable_progress_tracking': True,
            'enable_crash_recovery': True,
            'parallel_initialization': True,
            'max_parallel_tasks': 3,
            'startup_timeout_seconds': 60,
            'shutdown_timeout_seconds': 30,
            'force_shutdown_after_timeout': True,
            'save_metrics': True,
            'metrics_file': 'data/lifecycle_metrics.json',
            'auto_recovery_enabled': True,
            'critical_task_retry_count': 3
        }
    
    def _setup_signal_handlers(self) -> None:
        """Setup system signal handlers for graceful shutdown"""
        try:
            # Handle SIGTERM and SIGINT for graceful shutdown
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
            
            # Windows-specific signals
            if sys.platform == "win32":
                signal.signal(signal.SIGBREAK, self._signal_handler)
                
        except Exception as e:
            self.logger.warning(f"Failed to setup signal handlers: {e}")
    
    def _signal_handler(self, signum: int, frame) -> None:
        """Handle system signals for graceful shutdown"""
        signal_names = {
            signal.SIGTERM: "SIGTERM",
            signal.SIGINT: "SIGINT"
        }
        
        signal_name = signal_names.get(signum, f"Signal {signum}")
        self.logger.info(f"Received {signal_name}, initiating graceful shutdown")
        
        # Start shutdown process
        asyncio.create_task(self.shutdown(f"System signal: {signal_name}"))
    
    def _load_session_data(self) -> None:
        """Load session data from previous run"""
        try:
            if self._session_file.exists():
                with open(self._session_file, 'r', encoding='utf-8') as f:
                    self._session_data = json.load(f)
                
                # Check for crash recovery
                if self._session_data.get('clean_shutdown', False) is False:
                    self._metrics.crash_recoveries += 1
                    if self.config['auto_recovery_enabled']:
                        self._handle_crash_recovery()
                
                self.logger.info("Session data loaded successfully")
            else:
                self.logger.info("No previous session data found")
                
        except Exception as e:
            self.logger.error(f"Failed to load session data: {e}")
    
    def _handle_crash_recovery(self) -> None:
        """Handle crash recovery procedures"""
        try:
            self.logger.info("Performing crash recovery")
            
            # Load recovery state
            recovery_data = self._session_data.get('recovery_data', {})
            
            # Restore critical state
            for component_id, state_data in recovery_data.items():
                if component_id in self._recovery_handlers:
                    try:
                        self._recovery_handlers[component_id](state_data)
                        self.logger.info(f"Recovered state for {component_id}")
                    except Exception as e:
                        self.logger.error(f"Failed to recover {component_id}: {e}")
            
            # Clean up corrupted data
            self._cleanup_corrupted_session_data()
            
        except Exception as e:
            self.logger.error(f"Crash recovery failed: {e}")
    
    def _cleanup_corrupted_session_data(self) -> None:
        """Clean up potentially corrupted session data"""
        try:
            # Remove temporary files
            temp_patterns = ['*.tmp', '*.lock', '*.partial']
            data_dir = Path('data')
            
            if data_dir.exists():
                for pattern in temp_patterns:
                    for temp_file in data_dir.glob(pattern):
                        try:
                            temp_file.unlink()
                            self.logger.debug(f"Removed temporary file: {temp_file}")
                        except Exception:
                            pass
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup corrupted data: {e}")
    
    def _register_default_tasks(self) -> None:
        """Register default initialization and shutdown tasks"""
        try:
            # Critical initialization tasks
            self.register_init_task(InitializationTask(
                id="logging_setup",
                name="Initialize Logging System",
                stage=InitializationStage.CRITICAL,
                handler=self._init_logging_system,
                description="Set up application logging",
                critical=True,
                estimated_duration_ms=50.0
            ))
            
            self.register_init_task(InitializationTask(
                id="config_load",
                name="Load Configuration",
                stage=InitializationStage.CRITICAL,
                handler=self._load_configuration,
                dependencies=["logging_setup"],
                description="Load application configuration",
                critical=True,
                estimated_duration_ms=100.0
            ))
            
            # Core system tasks
            self.register_init_task(InitializationTask(
                id="state_manager",
                name="Initialize State Manager",
                stage=InitializationStage.CORE,
                handler=self._init_state_manager,
                dependencies=["config_load"],
                description="Initialize application state management",
                critical=True,
                estimated_duration_ms=200.0
            ))
            
            self.register_init_task(InitializationTask(
                id="performance_monitor",
                name="Initialize Performance Monitor",
                stage=InitializationStage.CORE,
                handler=self._init_performance_monitor,
                dependencies=["config_load"],
                description="Initialize performance monitoring",
                estimated_duration_ms=150.0
            ))
            
            # UI Foundation tasks
            self.register_init_task(InitializationTask(
                id="theme_manager",
                name="Initialize Theme Manager",
                stage=InitializationStage.UI_FOUNDATION,
                handler=self._init_theme_manager,
                dependencies=["config_load"],
                description="Initialize UI theming system",
                estimated_duration_ms=100.0
            ))
            
            self.register_init_task(InitializationTask(
                id="i18n_manager",
                name="Initialize Internationalization",
                stage=InitializationStage.UI_FOUNDATION,
                handler=self._init_i18n_manager,
                dependencies=["theme_manager"],
                description="Initialize internationalization support",
                estimated_duration_ms=200.0
            ))
            
            # Component loading tasks
            self.register_init_task(InitializationTask(
                id="component_loader",
                name="Initialize Component Loader",
                stage=InitializationStage.UI_COMPONENTS,
                handler=self._init_component_loader,
                dependencies=["state_manager", "performance_monitor"],
                description="Initialize dynamic component loading",
                estimated_duration_ms=150.0
            ))
            
            self.register_init_task(InitializationTask(
                id="tab_lifecycle",
                name="Initialize Tab Lifecycle Manager",
                stage=InitializationStage.UI_COMPONENTS,
                handler=self._init_tab_lifecycle,
                dependencies=["component_loader"],
                description="Initialize tab lifecycle management",
                estimated_duration_ms=100.0
            ))
            
            # Register corresponding shutdown tasks
            self._register_default_shutdown_tasks()
            
        except Exception as e:
            self.logger.error(f"Failed to register default tasks: {e}")
    
    def _register_default_shutdown_tasks(self) -> None:
        """Register default shutdown tasks"""
        try:
            # Graceful stop
            self.register_shutdown_task(ShutdownTask(
                id="stop_new_work",
                name="Stop Accepting New Work",
                stage=ShutdownStage.GRACEFUL_STOP,
                handler=self._stop_accepting_work,
                description="Stop accepting new user requests",
                timeout_seconds=5.0
            ))
            
            # Save state
            self.register_shutdown_task(ShutdownTask(
                id="save_application_state",
                name="Save Application State",
                stage=ShutdownStage.SAVE_STATE,
                handler=self._save_application_state,
                description="Save current application state",
                critical=True,
                timeout_seconds=10.0
            ))
            
            # UI cleanup
            self.register_shutdown_task(ShutdownTask(
                id="cleanup_ui_components",
                name="Clean Up UI Components",
                stage=ShutdownStage.CLEANUP_UI,
                handler=self._cleanup_ui_components,
                description="Clean up UI components and widgets",
                timeout_seconds=5.0
            ))
            
            # Service cleanup
            self.register_shutdown_task(ShutdownTask(
                id="shutdown_services",
                name="Shutdown Services",
                stage=ShutdownStage.CLEANUP_SERVICES,
                handler=self._shutdown_services,
                description="Shutdown business services",
                timeout_seconds=10.0
            ))
            
            # Core cleanup
            self.register_shutdown_task(ShutdownTask(
                id="cleanup_core_systems",
                name="Clean Up Core Systems",
                stage=ShutdownStage.CLEANUP_CORE,
                handler=self._cleanup_core_systems,
                description="Clean up core systems",
                timeout_seconds=5.0
            ))
            
            # Final cleanup
            self.register_shutdown_task(ShutdownTask(
                id="final_cleanup",
                name="Final Resource Cleanup",
                stage=ShutdownStage.FINAL_CLEANUP,
                handler=self._final_cleanup,
                description="Final resource cleanup",
                timeout_seconds=5.0
            ))
            
        except Exception as e:
            self.logger.error(f"Failed to register shutdown tasks: {e}")
    
    def register_init_task(self, task: InitializationTask) -> bool:
        """Register an initialization task"""
        with self._lock:
            try:
                if task.id in self._init_tasks:
                    self.logger.warning(f"Initialization task {task.id} already registered")
                    return False
                
                self._init_tasks[task.id] = task
                self._init_stages[task.stage].append(task.id)
                
                self.logger.debug(f"Registered initialization task: {task.id}")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to register initialization task {task.id}: {e}")
                return False
    
    def register_shutdown_task(self, task: ShutdownTask) -> bool:
        """Register a shutdown task"""
        with self._lock:
            try:
                if task.id in self._shutdown_tasks:
                    self.logger.warning(f"Shutdown task {task.id} already registered")
                    return False
                
                self._shutdown_tasks[task.id] = task
                self._shutdown_stages[task.stage].append(task.id)
                
                self.logger.debug(f"Registered shutdown task: {task.id}")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to register shutdown task {task.id}: {e}")
                return False
    
    def register_recovery_handler(self, component_id: str, handler: Callable) -> None:
        """Register a crash recovery handler for a component"""
        self._recovery_handlers[component_id] = handler
        self.logger.debug(f"Registered recovery handler for {component_id}")
    
    async def startup(self) -> bool:
        """
        Execute application startup sequence
        
        Returns:
            True if startup successful, False otherwise
        """
        with self._lock:
            if self._current_phase != LifecyclePhase.UNINITIALIZED:
                self.logger.warning("Startup already in progress or completed")
                return False
            
            self._current_phase = LifecyclePhase.INITIALIZING
            self._startup_begin_time = datetime.now()
            
            self.phase_changed.emit(LifecyclePhase.UNINITIALIZED.value, LifecyclePhase.INITIALIZING.value)
            
        try:
            self.logger.info("Starting application startup sequence")
            
            # Show splash screen if enabled
            if self.config['enable_splash_screen']:
                self._show_splash_screen()
            
            # Calculate execution order
            execution_order = self._calculate_execution_order()
            if not execution_order:
                raise Exception("Failed to calculate task execution order")
            
            # Execute initialization stages
            success = await self._execute_initialization_stages(execution_order)
            
            if success:
                # Startup completed successfully
                startup_time = (datetime.now() - self._startup_begin_time).total_seconds() * 1000
                
                self._current_phase = LifecyclePhase.RUNNING
                self._metrics.total_startup_time_ms = startup_time
                self._metrics.successful_init_tasks = len([t for t in self._init_tasks.values() if t.completed])
                self._metrics.failed_init_tasks = len([t for t in self._init_tasks.values() if t.failed])
                
                # Update startup history
                self._startup_history.append(startup_time)
                self._update_startup_metrics()
                
                # Hide splash screen
                if self._splash_screen:
                    self._splash_screen.hide()
                
                # Mark session as cleanly started
                self._session_data['clean_shutdown'] = False
                self._save_session_data()
                
                self.phase_changed.emit(LifecyclePhase.INITIALIZING.value, LifecyclePhase.RUNNING.value)
                self.startup_completed.emit(startup_time)
                
                self.logger.info(f"Application startup completed successfully in {startup_time:.2f}ms")
                return True
            else:
                # Startup failed
                self._current_phase = LifecyclePhase.TERMINATED
                self._handle_startup_failure()
                
                self.logger.error("Application startup failed")
                return False
                
        except Exception as e:
            self._current_phase = LifecyclePhase.TERMINATED
            self.logger.error(f"Startup sequence failed: {e}")
            return False
    
    def _show_splash_screen(self) -> None:
        """Show application splash screen"""
        try:
            from PyQt6.QtWidgets import QSplashScreen, QVBoxLayout, QLabel
            from PyQt6.QtGui import QPixmap, QFont
            from PyQt6.QtCore import Qt
            
            # Create splash screen
            pixmap = QPixmap(400, 300)
            pixmap.fill(Qt.GlobalColor.white)
            
            self._splash_screen = QSplashScreen(pixmap)
            self._splash_screen.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
            
            # Add progress bar
            self._progress_bar = QProgressBar()
            self._progress_bar.setRange(0, 100)
            self._progress_bar.setValue(0)
            
            # Show splash screen
            self._splash_screen.show()
            self._splash_screen.showMessage("Initializing application...", Qt.AlignmentFlag.AlignBottom)
            
            # Process events to show splash
            QApplication.processEvents()
            
        except Exception as e:
            self.logger.error(f"Failed to show splash screen: {e}")
    
    def _calculate_execution_order(self) -> List[str]:
        """Calculate optimal task execution order based on dependencies"""
        try:
            order = []
            completed = set()
            
            # Process stages in order
            for stage in InitializationStage:
                stage_tasks = self._init_stages[stage].copy()
                
                # Sort tasks within stage by dependencies
                while stage_tasks:
                    progress_made = False
                    
                    for task_id in stage_tasks[:]:
                        task = self._init_tasks[task_id]
                        
                        # Check if all dependencies are satisfied
                        deps_satisfied = all(dep in completed for dep in task.dependencies)
                        
                        if deps_satisfied:
                            order.append(task_id)
                            completed.add(task_id)
                            stage_tasks.remove(task_id)
                            progress_made = True
                    
                    if not progress_made and stage_tasks:
                        # Circular dependency or missing dependency
                        missing_deps = []
                        for task_id in stage_tasks:
                            task = self._init_tasks[task_id]
                            missing = [dep for dep in task.dependencies if dep not in completed]
                            if missing:
                                missing_deps.extend(missing)
                        
                        self.logger.error(f"Dependency resolution failed. Missing: {missing_deps}")
                        return []
            
            return order
            
        except Exception as e:
            self.logger.error(f"Failed to calculate execution order: {e}")
            return []
    
    async def _execute_initialization_stages(self, execution_order: List[str]) -> bool:
        """Execute initialization tasks in calculated order"""
        try:
            total_tasks = len(execution_order)
            completed_tasks = 0
            
            # Group tasks by stage for progress tracking
            stage_tasks = defaultdict(list)
            for task_id in execution_order:
                task = self._init_tasks[task_id]
                stage_tasks[task.stage].append(task_id)
            
            # Execute stages
            for stage in InitializationStage:
                if stage not in stage_tasks:
                    continue
                
                self._current_stage = stage
                tasks_in_stage = stage_tasks[stage]
                
                self.logger.info(f"Executing initialization stage: {stage.value}")
                self.startup_progress.emit(stage.value, 0.0, f"Starting {stage.value} stage")
                
                # Execute tasks in stage
                stage_success = await self._execute_stage_tasks(tasks_in_stage)
                
                if not stage_success:
                    # Check if stage has critical tasks that failed
                    critical_failed = any(
                        self._init_tasks[task_id].critical and self._init_tasks[task_id].failed
                        for task_id in tasks_in_stage
                    )
                    
                    if critical_failed:
                        self.logger.error(f"Critical task failed in stage {stage.value}")
                        return False
                
                # Update progress
                completed_tasks += len(tasks_in_stage)
                overall_progress = (completed_tasks / total_tasks) * 100
                self.startup_progress.emit(stage.value, 100.0, f"Completed {stage.value} stage")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to execute initialization stages: {e}")
            return False
    
    async def _execute_stage_tasks(self, task_ids: List[str]) -> bool:
        """Execute tasks within a stage"""
        try:
            if self.config['parallel_initialization']:
                # Execute tasks in parallel (respecting max_parallel_tasks)
                return await self._execute_tasks_parallel(task_ids)
            else:
                # Execute tasks sequentially
                return await self._execute_tasks_sequential(task_ids)
                
        except Exception as e:
            self.logger.error(f"Failed to execute stage tasks: {e}")
            return False
    
    async def _execute_tasks_parallel(self, task_ids: List[str]) -> bool:
        """Execute tasks in parallel with concurrency limit"""
        try:
            semaphore = asyncio.Semaphore(self.config['max_parallel_tasks'])
            
            async def execute_task_with_semaphore(task_id: str) -> bool:
                async with semaphore:
                    return await self._execute_single_task(task_id)
            
            # Create tasks
            tasks = [execute_task_with_semaphore(task_id) for task_id in task_ids]
            
            # Execute and wait for all tasks
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check results
            success = True
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"Task {task_ids[i]} raised exception: {result}")
                    success = False
                elif not result:
                    success = False
            
            return success
            
        except Exception as e:
            self.logger.error(f"Parallel task execution failed: {e}")
            return False
    
    async def _execute_tasks_sequential(self, task_ids: List[str]) -> bool:
        """Execute tasks sequentially"""
        try:
            success = True
            
            for task_id in task_ids:
                task_success = await self._execute_single_task(task_id)
                if not task_success:
                    success = False
                    
                    # Stop if critical task failed
                    task = self._init_tasks[task_id]
                    if task.critical:
                        self.logger.error(f"Critical task {task_id} failed, stopping execution")
                        break
            
            return success
            
        except Exception as e:
            self.logger.error(f"Sequential task execution failed: {e}")
            return False
    
    async def _execute_single_task(self, task_id: str) -> bool:
        """Execute a single initialization task"""
        task = self._init_tasks[task_id]
        
        try:
            self.logger.debug(f"Starting task: {task_id}")
            self.task_started.emit(task_id, task.name)
            
            start_time = time.time()
            
            # Execute task with timeout
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(task.handler),
                    timeout=task.timeout_seconds
                )
                
                execution_time = (time.time() - start_time) * 1000
                task.execution_time_ms = execution_time
                
                if result:
                    task.completed = True
                    self.logger.debug(f"Task {task_id} completed successfully in {execution_time:.2f}ms")
                    self.task_completed.emit(task_id, True, execution_time)
                    return True
                else:
                    task.failed = True
                    task.error_message = "Task returned False"
                    self.logger.error(f"Task {task_id} failed")
                    self.task_completed.emit(task_id, False, execution_time)
                    self.error_occurred.emit(task_id, "Task returned False")
                    return False
                    
            except asyncio.TimeoutError:
                execution_time = (time.time() - start_time) * 1000
                task.failed = True
                task.error_message = f"Task timed out after {task.timeout_seconds}s"
                self.logger.error(f"Task {task_id} timed out")
                self.task_completed.emit(task_id, False, execution_time)
                self.error_occurred.emit(task_id, "Task timed out")
                return False
                
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            task.failed = True
            task.error_message = str(e)
            
            self.logger.error(f"Task {task_id} failed with exception: {e}")
            self.task_completed.emit(task_id, False, execution_time)
            self.error_occurred.emit(task_id, str(e))
            
            # Retry critical tasks
            if task.critical and hasattr(task, 'retry_count'):
                if getattr(task, 'retry_count', 0) < self.config['critical_task_retry_count']:
                    task.retry_count = getattr(task, 'retry_count', 0) + 1
                    self.logger.info(f"Retrying critical task {task_id} (attempt {task.retry_count})")
                    return await self._execute_single_task(task_id)
            
            return False 