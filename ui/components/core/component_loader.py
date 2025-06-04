"""
Dynamic Component Loader for v2.0 UI Architecture

This module provides comprehensive dynamic component loading including:
- Lazy-loading of tab components and resources
- Module bundling strategy for component chunks
- Priority-based loading for critical UI elements
- Prefetching mechanisms based on user behavior patterns
- Loading indicators and fallback UI components
- Retry mechanisms for failed component loads
- Performance optimization and memory management
"""

import logging
import threading
import time
import asyncio
import importlib
import importlib.util
import sys
import weakref
from typing import Dict, Any, Optional, Callable, List, Set, Union, Tuple, Type
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from collections import defaultdict, deque
import json
import hashlib
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QThread, QMutex
from PyQt6.QtWidgets import QWidget, QProgressBar, QLabel, QVBoxLayout

logger = logging.getLogger(__name__)


class ComponentPriority(Enum):
    """Component loading priority levels"""
    CRITICAL = "critical"      # Essential UI components
    HIGH = "high"             # Important features
    MEDIUM = "medium"         # Standard features
    LOW = "low"              # Optional features
    BACKGROUND = "background" # Prefetched components


class LoadingStrategy(Enum):
    """Component loading strategies"""
    IMMEDIATE = "immediate"    # Load immediately
    LAZY = "lazy"             # Load on demand
    PREFETCH = "prefetch"     # Load based on prediction
    DEFERRED = "deferred"     # Load when resources available


class ComponentState(Enum):
    """Component loading states"""
    UNREGISTERED = "unregistered"
    REGISTERED = "registered"
    LOADING = "loading"
    LOADED = "loaded"
    FAILED = "failed"
    UNLOADING = "unloading"
    UNLOADED = "unloaded"


class LoadingError(Exception):
    """Component loading error"""
    pass


@dataclass
class ComponentManifest:
    """Component manifest describing loading requirements"""
    id: str
    module_path: str
    class_name: str
    priority: ComponentPriority = ComponentPriority.MEDIUM
    strategy: LoadingStrategy = LoadingStrategy.LAZY
    
    # Dependencies
    dependencies: List[str] = field(default_factory=list)
    optional_dependencies: List[str] = field(default_factory=list)
    
    # Resources
    resource_files: List[str] = field(default_factory=list)
    memory_estimate_mb: float = 1.0
    load_time_estimate_ms: float = 100.0
    
    # Behavior
    cache_enabled: bool = True
    auto_unload: bool = False
    unload_timeout_minutes: int = 10
    
    # Metadata
    description: str = ""
    version: str = "1.0.0"
    author: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class LoadingTask:
    """Individual component loading task"""
    id: str
    component_id: str
    priority: ComponentPriority
    strategy: LoadingStrategy
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Status
    state: ComponentState = ComponentState.REGISTERED
    progress: float = 0.0
    error_message: Optional[str] = None
    
    # Context
    requester_id: Optional[str] = None
    user_initiated: bool = False
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class LoadingMetrics:
    """Component loading performance metrics"""
    total_components: int = 0
    loaded_components: int = 0
    failed_components: int = 0
    
    # Performance
    average_load_time_ms: float = 0.0
    total_memory_usage_mb: float = 0.0
    cache_hit_rate: float = 0.0
    
    # Efficiency
    successful_prefetches: int = 0
    wasted_prefetches: int = 0
    prefetch_accuracy: float = 0.0
    
    # Errors
    loading_errors: int = 0
    retry_attempts: int = 0
    timeout_errors: int = 0


class ComponentLoader(QObject):
    """
    Advanced dynamic component loader providing lazy-loading, prefetching,
    priority-based loading, and comprehensive resource management
    for v2.0 UI architecture.
    """
    
    # Signals for loading events
    component_loading_started = pyqtSignal(str, str)  # component_id, priority
    component_loading_progress = pyqtSignal(str, float)  # component_id, progress
    component_loaded = pyqtSignal(str, float)  # component_id, load_time_ms
    component_loading_failed = pyqtSignal(str, str)  # component_id, error
    prefetch_completed = pyqtSignal(str, int)  # strategy, count
    cache_cleared = pyqtSignal(int)  # freed_mb
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.config = self._create_default_config()
        if config:
            self.config.update(config)
        
        # Core state
        self._manifests: Dict[str, ComponentManifest] = {}
        self._loaded_components: Dict[str, Any] = {}
        self._component_instances: Dict[str, QWidget] = {}
        self._loading_tasks: Dict[str, LoadingTask] = {}
        
        # Loading queues by priority
        self._loading_queues: Dict[ComponentPriority, deque] = {
            priority: deque() for priority in ComponentPriority
        }
        
        # Caching and performance
        self._module_cache: Dict[str, Any] = {}
        self._resource_cache: Dict[str, bytes] = {}
        self._load_times: Dict[str, float] = {}
        
        # Prefetching and prediction
        self._usage_patterns: Dict[str, List[datetime]] = defaultdict(list)
        self._prefetch_predictions: Dict[str, float] = {}
        self._prefetch_queue: deque = deque()
        
        # Metrics and monitoring
        self._metrics = LoadingMetrics()
        self._load_time_history: deque = deque(maxlen=1000)
        
        # Threading and synchronization
        self._lock = threading.RLock()
        self._loading_threads: Dict[str, QThread] = {}
        self._max_concurrent_loads = self.config['max_concurrent_loads']
        self._current_loads = 0
        
        # Timers
        self._prefetch_timer: Optional[QTimer] = None
        self._cleanup_timer: Optional[QTimer] = None
        self._metrics_timer: Optional[QTimer] = None
        
        # Storage
        self._manifests_path = Path(self.config['manifests_path'])
        self._manifests_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize system
        self._load_manifests()
        self._start_background_tasks()
        
        self.logger.info(f"ComponentLoader initialized with config: {self.config}")
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration for component loader"""
        return {
            'manifests_path': 'data/component_manifests',
            'max_concurrent_loads': 3,
            'enable_prefetching': True,
            'enable_caching': True,
            'cache_size_limit_mb': 100,
            'prefetch_interval_seconds': 30,
            'cleanup_interval_minutes': 15,
            'metrics_interval_seconds': 60,
            'max_retry_attempts': 3,
            'loading_timeout_seconds': 30,
            'unload_inactive_components': True,
            'component_inactivity_minutes': 10,
            'prefetch_threshold': 0.7,
            'memory_pressure_threshold_mb': 500
        }
    
    def _load_manifests(self) -> None:
        """Load component manifests from files"""
        try:
            loaded_count = 0
            
            for manifest_file in self._manifests_path.glob("*.json"):
                try:
                    with open(manifest_file, 'r', encoding='utf-8') as f:
                        manifest_data = json.load(f)
                    
                    manifest = ComponentManifest(
                        id=manifest_data['id'],
                        module_path=manifest_data['module_path'],
                        class_name=manifest_data['class_name'],
                        priority=ComponentPriority(manifest_data.get('priority', 'medium')),
                        strategy=LoadingStrategy(manifest_data.get('strategy', 'lazy')),
                        dependencies=manifest_data.get('dependencies', []),
                        optional_dependencies=manifest_data.get('optional_dependencies', []),
                        resource_files=manifest_data.get('resource_files', []),
                        memory_estimate_mb=manifest_data.get('memory_estimate_mb', 1.0),
                        load_time_estimate_ms=manifest_data.get('load_time_estimate_ms', 100.0),
                        cache_enabled=manifest_data.get('cache_enabled', True),
                        auto_unload=manifest_data.get('auto_unload', False),
                        description=manifest_data.get('description', ''),
                        version=manifest_data.get('version', '1.0.0'),
                        tags=manifest_data.get('tags', [])
                    )
                    
                    self._manifests[manifest.id] = manifest
                    loaded_count += 1
                    
                except Exception as e:
                    self.logger.error(f"Failed to load manifest {manifest_file}: {e}")
            
            self.logger.info(f"Loaded {loaded_count} component manifests")
            
        except Exception as e:
            self.logger.error(f"Failed to load manifests: {e}")
    
    def _start_background_tasks(self) -> None:
        """Start background timers and tasks"""
        try:
            # Prefetch timer
            if self.config['enable_prefetching']:
                self._prefetch_timer = QTimer()
                self._prefetch_timer.timeout.connect(self._run_prefetch_cycle)
                self._prefetch_timer.start(self.config['prefetch_interval_seconds'] * 1000)
            
            # Cleanup timer
            self._cleanup_timer = QTimer()
            self._cleanup_timer.timeout.connect(self._run_cleanup_cycle)
            self._cleanup_timer.start(self.config['cleanup_interval_minutes'] * 60000)
            
            # Metrics timer
            self._metrics_timer = QTimer()
            self._metrics_timer.timeout.connect(self._update_metrics)
            self._metrics_timer.start(self.config['metrics_interval_seconds'] * 1000)
            
            self.logger.info("Background tasks started")
            
        except Exception as e:
            self.logger.error(f"Failed to start background tasks: {e}")
    
    def register_component(self, manifest: ComponentManifest) -> bool:
        """Register a component for dynamic loading"""
        with self._lock:
            try:
                # Validate manifest
                if not self._validate_manifest(manifest):
                    return False
                
                # Store manifest
                self._manifests[manifest.id] = manifest
                
                # Save to file for persistence
                self._save_manifest(manifest)
                
                # Update metrics
                self._metrics.total_components += 1
                
                self.logger.info(f"Component {manifest.id} registered for dynamic loading")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to register component {manifest.id}: {e}")
                return False
    
    def _validate_manifest(self, manifest: ComponentManifest) -> bool:
        """Validate component manifest"""
        try:
            # Check required fields
            if not manifest.id or not manifest.module_path or not manifest.class_name:
                self.logger.error("Manifest missing required fields")
                return False
            
            # Check if module path exists
            module_path = Path(manifest.module_path)
            if not module_path.exists() and not module_path.with_suffix('.py').exists():
                self.logger.warning(f"Module path not found: {manifest.module_path}")
            
            # Validate dependencies
            for dep_id in manifest.dependencies:
                if dep_id not in self._manifests:
                    self.logger.warning(f"Dependency {dep_id} not found for {manifest.id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Manifest validation failed: {e}")
            return False
    
    def _save_manifest(self, manifest: ComponentManifest) -> None:
        """Save manifest to file"""
        try:
            manifest_file = self._manifests_path / f"{manifest.id}.json"
            
            with open(manifest_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(manifest), f, indent=2, default=str)
                
        except Exception as e:
            self.logger.error(f"Failed to save manifest {manifest.id}: {e}")
    
    async def load_component(self, component_id: str, requester_id: Optional[str] = None,
                           user_initiated: bool = False, force_reload: bool = False) -> Optional[QWidget]:
        """
        Load a component dynamically
        
        Args:
            component_id: ID of component to load
            requester_id: ID of component requesting the load
            user_initiated: Whether load was triggered by user action
            force_reload: Force reload even if already loaded
            
        Returns:
            Loaded component instance or None if failed
        """
        with self._lock:
            try:
                # Check if already loaded
                if component_id in self._component_instances and not force_reload:
                    self._record_usage(component_id)
                    return self._component_instances[component_id]
                
                # Get manifest
                manifest = self._manifests.get(component_id)
                if not manifest:
                    self.logger.error(f"Component {component_id} not registered")
                    return None
                
                # Create loading task
                task = LoadingTask(
                    id=f"load_{component_id}_{int(time.time())}",
                    component_id=component_id,
                    priority=manifest.priority,
                    strategy=manifest.strategy,
                    requester_id=requester_id,
                    user_initiated=user_initiated
                )
                
                self._loading_tasks[task.id] = task
                
                # Check concurrent load limit
                if self._current_loads >= self._max_concurrent_loads:
                    # Queue the task
                    self._loading_queues[manifest.priority].append(task)
                    self.logger.info(f"Component {component_id} queued for loading")
                    return None
                
                # Start loading
                return await self._execute_loading_task(task)
                
            except Exception as e:
                self.logger.error(f"Failed to load component {component_id}: {e}")
                return None
    
    async def _execute_loading_task(self, task: LoadingTask) -> Optional[QWidget]:
        """Execute a loading task"""
        try:
            self._current_loads += 1
            task.state = ComponentState.LOADING
            task.started_at = datetime.now()
            
            self.component_loading_started.emit(task.component_id, task.priority.value)
            
            # Get manifest
            manifest = self._manifests[task.component_id]
            
            # Load dependencies first
            if not await self._load_dependencies(manifest.dependencies):
                raise LoadingError("Failed to load required dependencies")
            
            # Load optional dependencies (best effort)
            await self._load_dependencies(manifest.optional_dependencies, required=False)
            
            # Update progress
            task.progress = 0.3
            self.component_loading_progress.emit(task.component_id, task.progress)
            
            # Load resources
            await self._load_resources(manifest.resource_files)
            
            # Update progress
            task.progress = 0.6
            self.component_loading_progress.emit(task.component_id, task.progress)
            
            # Load component module
            component_class = await self._load_component_module(manifest)
            
            # Update progress
            task.progress = 0.8
            self.component_loading_progress.emit(task.component_id, task.progress)
            
            # Create component instance
            component_instance = self._create_component_instance(component_class, manifest)
            
            # Store instance
            self._component_instances[task.component_id] = component_instance
            self._loaded_components[task.component_id] = component_class
            
            # Record load time
            load_time = (datetime.now() - task.started_at).total_seconds() * 1000
            self._load_times[task.component_id] = load_time
            self._load_time_history.append(load_time)
            
            # Update task
            task.state = ComponentState.LOADED
            task.progress = 1.0
            task.completed_at = datetime.now()
            
            # Update metrics
            self._metrics.loaded_components += 1
            
            # Record usage
            self._record_usage(task.component_id)
            
            # Emit signals
            self.component_loading_progress.emit(task.component_id, 1.0)
            self.component_loaded.emit(task.component_id, load_time)
            
            self.logger.info(f"Component {task.component_id} loaded successfully in {load_time:.2f}ms")
            return component_instance
            
        except Exception as e:
            # Handle loading failure
            task.state = ComponentState.FAILED
            task.error_message = str(e)
            task.completed_at = datetime.now()
            
            self._metrics.failed_components += 1
            self._metrics.loading_errors += 1
            
            self.component_loading_failed.emit(task.component_id, str(e))
            
            # Retry if configured
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                self._metrics.retry_attempts += 1
                self.logger.warning(f"Retrying load of {task.component_id} (attempt {task.retry_count})")
                return await self._execute_loading_task(task)
            
            self.logger.error(f"Failed to load component {task.component_id}: {e}")
            return None
            
        finally:
            self._current_loads -= 1
            
            # Process next queued task
            await self._process_next_queued_task()
    
    async def _load_dependencies(self, dependencies: List[str], required: bool = True) -> bool:
        """Load component dependencies"""
        try:
            for dep_id in dependencies:
                if dep_id not in self._component_instances:
                    component = await self.load_component(dep_id)
                    if required and component is None:
                        return False
            
            return True
            
        except Exception as e:
            if required:
                self.logger.error(f"Failed to load dependencies: {e}")
                return False
            else:
                self.logger.warning(f"Failed to load optional dependencies: {e}")
                return True
    
    async def _load_resources(self, resource_files: List[str]) -> None:
        """Load component resources"""
        try:
            for resource_file in resource_files:
                if resource_file not in self._resource_cache:
                    resource_path = Path(resource_file)
                    if resource_path.exists():
                        with open(resource_path, 'rb') as f:
                            self._resource_cache[resource_file] = f.read()
                            
        except Exception as e:
            self.logger.warning(f"Failed to load resources: {e}")
    
    async def _load_component_module(self, manifest: ComponentManifest) -> Type:
        """Load component module and return class"""
        try:
            module_path = manifest.module_path
            class_name = manifest.class_name
            
            # Check cache first
            cache_key = f"{module_path}:{class_name}"
            if manifest.cache_enabled and cache_key in self._module_cache:
                return self._module_cache[cache_key]
            
            # Load module
            if module_path in sys.modules:
                # Reload if already imported
                module = importlib.reload(sys.modules[module_path])
            else:
                # Import module
                spec = importlib.util.spec_from_file_location(
                    module_path.replace('/', '.').replace('\\', '.').replace('.py', ''),
                    module_path
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                sys.modules[module_path] = module
            
            # Get class from module
            component_class = getattr(module, class_name)
            
            # Cache if enabled
            if manifest.cache_enabled:
                self._module_cache[cache_key] = component_class
            
            return component_class
            
        except Exception as e:
            raise LoadingError(f"Failed to load module {manifest.module_path}: {e}")
    
    def _create_component_instance(self, component_class: Type, manifest: ComponentManifest) -> QWidget:
        """Create component instance"""
        try:
            # Create instance with manifest metadata
            instance = component_class()
            
            # Set manifest metadata as attributes
            instance.component_id = manifest.id
            instance.component_version = manifest.version
            instance.component_description = manifest.description
            
            return instance
            
        except Exception as e:
            raise LoadingError(f"Failed to create instance of {manifest.class_name}: {e}")
    
    def _record_usage(self, component_id: str) -> None:
        """Record component usage for prefetching predictions"""
        try:
            now = datetime.now()
            self._usage_patterns[component_id].append(now)
            
            # Keep only recent usage (last 24 hours)
            cutoff = now - timedelta(hours=24)
            self._usage_patterns[component_id] = [
                usage_time for usage_time in self._usage_patterns[component_id]
                if usage_time >= cutoff
            ]
            
        except Exception as e:
            self.logger.error(f"Failed to record usage for {component_id}: {e}")
    
    async def _process_next_queued_task(self) -> None:
        """Process next queued loading task"""
        try:
            if self._current_loads >= self._max_concurrent_loads:
                return
            
            # Find highest priority task
            for priority in ComponentPriority:
                queue = self._loading_queues[priority]
                if queue:
                    task = queue.popleft()
                    await self._execute_loading_task(task)
                    break
                    
        except Exception as e:
            self.logger.error(f"Failed to process queued task: {e}")
    
    def _run_prefetch_cycle(self) -> None:
        """Run prefetching cycle based on usage patterns"""
        if not self.config['enable_prefetching']:
            return
        
        try:
            predictions = self._calculate_prefetch_predictions()
            
            prefetched_count = 0
            for component_id, probability in predictions.items():
                if (probability >= self.config['prefetch_threshold'] and
                    component_id not in self._component_instances):
                    
                    # Queue for prefetch
                    asyncio.create_task(self.load_component(
                        component_id, 
                        requester_id="prefetch_system",
                        user_initiated=False
                    ))
                    
                    prefetched_count += 1
            
            if prefetched_count > 0:
                self._metrics.successful_prefetches += prefetched_count
                self.prefetch_completed.emit("usage_pattern", prefetched_count)
                self.logger.info(f"Prefetched {prefetched_count} components")
                
        except Exception as e:
            self.logger.error(f"Prefetch cycle failed: {e}")
    
    def _calculate_prefetch_predictions(self) -> Dict[str, float]:
        """Calculate prefetch predictions based on usage patterns"""
        predictions = {}
        
        try:
            now = datetime.now()
            
            for component_id, usage_times in self._usage_patterns.items():
                if not usage_times:
                    continue
                
                # Calculate usage frequency (uses per hour)
                recent_usage = [t for t in usage_times if (now - t).total_seconds() < 3600]
                frequency = len(recent_usage) / max(1, len(usage_times))
                
                # Calculate time-based probability
                if usage_times:
                    last_usage = max(usage_times)
                    time_since_last = (now - last_usage).total_seconds()
                    
                    # Higher probability if used recently
                    time_factor = max(0, 1 - (time_since_last / 3600))  # Decay over 1 hour
                else:
                    time_factor = 0
                
                # Combined probability
                probability = frequency * 0.7 + time_factor * 0.3
                predictions[component_id] = min(1.0, probability)
            
        except Exception as e:
            self.logger.error(f"Failed to calculate prefetch predictions: {e}")
        
        return predictions
    
    def _run_cleanup_cycle(self) -> None:
        """Run cleanup cycle to free unused resources"""
        try:
            freed_mb = 0
            
            # Clean up inactive components
            if self.config['unload_inactive_components']:
                freed_mb += self._unload_inactive_components()
            
            # Clean up caches if memory pressure
            if self._get_memory_usage_mb() > self.config['memory_pressure_threshold_mb']:
                freed_mb += self._cleanup_caches()
            
            if freed_mb > 0:
                self.cache_cleared.emit(int(freed_mb))
                self.logger.info(f"Cleanup freed {freed_mb:.2f}MB")
                
        except Exception as e:
            self.logger.error(f"Cleanup cycle failed: {e}")
    
    def _unload_inactive_components(self) -> float:
        """Unload components that haven't been used recently"""
        freed_mb = 0.0
        now = datetime.now()
        cutoff = now - timedelta(minutes=self.config['component_inactivity_minutes'])
        
        try:
            components_to_unload = []
            
            for component_id in self._component_instances:
                manifest = self._manifests.get(component_id)
                if not manifest or not manifest.auto_unload:
                    continue
                
                # Check last usage
                usage_times = self._usage_patterns.get(component_id, [])
                if not usage_times or max(usage_times) < cutoff:
                    components_to_unload.append(component_id)
            
            # Unload components
            for component_id in components_to_unload:
                freed_mb += self._unload_component(component_id)
            
        except Exception as e:
            self.logger.error(f"Failed to unload inactive components: {e}")
        
        return freed_mb
    
    def _unload_component(self, component_id: str) -> float:
        """Unload a specific component"""
        try:
            if component_id not in self._component_instances:
                return 0.0
            
            # Get memory estimate
            manifest = self._manifests.get(component_id)
            memory_estimate = manifest.memory_estimate_mb if manifest else 1.0
            
            # Remove from instances
            if component_id in self._component_instances:
                del self._component_instances[component_id]
            
            if component_id in self._loaded_components:
                del self._loaded_components[component_id]
            
            # Update metrics
            self._metrics.loaded_components -= 1
            
            self.logger.info(f"Component {component_id} unloaded")
            return memory_estimate
            
        except Exception as e:
            self.logger.error(f"Failed to unload component {component_id}: {e}")
            return 0.0
    
    def _cleanup_caches(self) -> float:
        """Clean up caches to free memory"""
        freed_mb = 0.0
        
        try:
            # Clean module cache
            initial_count = len(self._module_cache)
            self._module_cache.clear()
            freed_mb += initial_count * 0.5  # Estimate 0.5MB per cached module
            
            # Clean resource cache
            resource_size = sum(len(data) for data in self._resource_cache.values())
            self._resource_cache.clear()
            freed_mb += resource_size / (1024 * 1024)
            
            self.logger.info(f"Caches cleared, freed {freed_mb:.2f}MB")
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup caches: {e}")
        
        return freed_mb
    
    def _get_memory_usage_mb(self) -> float:
        """Get estimated memory usage"""
        try:
            total_memory = 0.0
            
            # Component memory
            for component_id in self._component_instances:
                manifest = self._manifests.get(component_id)
                if manifest:
                    total_memory += manifest.memory_estimate_mb
            
            # Cache memory
            total_memory += len(self._module_cache) * 0.5
            total_memory += sum(len(data) for data in self._resource_cache.values()) / (1024 * 1024)
            
            return total_memory
            
        except Exception as e:
            self.logger.error(f"Failed to calculate memory usage: {e}")
            return 0.0
    
    def _update_metrics(self) -> None:
        """Update loading metrics"""
        try:
            # Update load time averages
            if self._load_time_history:
                self._metrics.average_load_time_ms = sum(self._load_time_history) / len(self._load_time_history)
            
            # Update memory usage
            self._metrics.total_memory_usage_mb = self._get_memory_usage_mb()
            
            # Update cache hit rate
            total_requests = len(self._load_times)
            cache_hits = sum(1 for component_id in self._load_times if component_id in self._module_cache)
            self._metrics.cache_hit_rate = (cache_hits / total_requests) * 100 if total_requests > 0 else 0
            
            # Update prefetch accuracy
            total_prefetches = self._metrics.successful_prefetches + self._metrics.wasted_prefetches
            if total_prefetches > 0:
                self._metrics.prefetch_accuracy = (self._metrics.successful_prefetches / total_prefetches) * 100
            
        except Exception as e:
            self.logger.error(f"Failed to update metrics: {e}")
    
    def get_loaded_components(self) -> List[str]:
        """Get list of currently loaded components"""
        return list(self._component_instances.keys())
    
    def get_component_instance(self, component_id: str) -> Optional[QWidget]:
        """Get component instance if loaded"""
        return self._component_instances.get(component_id)
    
    def is_component_loaded(self, component_id: str) -> bool:
        """Check if component is loaded"""
        return component_id in self._component_instances
    
    def get_loading_metrics(self) -> LoadingMetrics:
        """Get loading performance metrics"""
        return self._metrics
    
    def get_loading_tasks(self) -> List[LoadingTask]:
        """Get current loading tasks"""
        return list(self._loading_tasks.values())
    
    def create_loading_indicator(self, parent: Optional[QWidget] = None) -> QWidget:
        """Create a loading indicator widget"""
        try:
            from PyQt6.QtWidgets import QVBoxLayout, QProgressBar, QLabel
            
            widget = QWidget(parent)
            layout = QVBoxLayout(widget)
            
            # Progress bar
            progress_bar = QProgressBar()
            progress_bar.setRange(0, 100)
            progress_bar.setValue(0)
            
            # Status label
            status_label = QLabel("Loading component...")
            
            layout.addWidget(status_label)
            layout.addWidget(progress_bar)
            
            # Connect to loading signals
            def update_progress(component_id: str, progress: float):
                progress_bar.setValue(int(progress * 100))
                status_label.setText(f"Loading {component_id}... {progress*100:.0f}%")
            
            self.component_loading_progress.connect(update_progress)
            
            return widget
            
        except Exception as e:
            self.logger.error(f"Failed to create loading indicator: {e}")
            return QWidget(parent)
    
    def shutdown(self) -> None:
        """Shutdown the component loader"""
        with self._lock:
            try:
                self.logger.info("Shutting down ComponentLoader")
                
                # Stop timers
                if self._prefetch_timer:
                    self._prefetch_timer.stop()
                if self._cleanup_timer:
                    self._cleanup_timer.stop()
                if self._metrics_timer:
                    self._metrics_timer.stop()
                
                # Wait for loading threads to complete
                for thread in self._loading_threads.values():
                    if thread.isRunning():
                        thread.quit()
                        thread.wait(5000)  # Wait up to 5 seconds
                
                # Clean up resources
                self._module_cache.clear()
                self._resource_cache.clear()
                
                self.logger.info("ComponentLoader shutdown completed")
                
            except Exception as e:
                self.logger.error(f"Error during ComponentLoader shutdown: {e}")


# Factory function for creating component loader instances
def create_component_loader(config: Optional[Dict[str, Any]] = None) -> ComponentLoader:
    """Create a new component loader instance with optional configuration"""
    return ComponentLoader(config)


# Global instance management
_global_component_loader: Optional[ComponentLoader] = None


def get_global_component_loader() -> ComponentLoader:
    """Get or create the global component loader instance"""
    global _global_component_loader
    
    if _global_component_loader is None:
        _global_component_loader = ComponentLoader()
    
    return _global_component_loader


def set_global_component_loader(loader: ComponentLoader) -> None:
    """Set the global component loader instance"""
    global _global_component_loader
    _global_component_loader = loader 