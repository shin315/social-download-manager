"""
Background Task Management System

Comprehensive Qt-based background processing system featuring:
- QThreadPool with QRunnable for lightweight task execution
- Priority-based task queue with QDeadlineTimer scheduling
- Specialized workers for different operation types
- Thread-safe result collection and callback system
- Resource monitoring and automatic load balancing
- Integration with memory management (15.4)

Part of Task 15.5 - Background Processing
"""

import os
import sys
import time
import threading
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Set, Union, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from abc import ABC, abstractmethod

# Qt imports
try:
    from PyQt6.QtCore import (
        QObject, QThread, QThreadPool, QRunnable, QMutex, QMutexLocker,
        QWaitCondition, QReadWriteLock, QAtomicInt, QTimer, QDeadlineTimer,
        QElapsedTimer, pyqtSignal, pyqtSlot, QMetaObject, Qt, QBuffer,
        QFutureWatcher, QFuture, QThreadStorage
    )
    from PyQt6.QtGui import QImageReader, QPixmap, QImage
    from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PyQt6.QtMultimediaWidgets import QVideoWidget
    from PyQt6.QtSql import QSqlDatabase, QSqlQuery
    HAS_QT = True
except ImportError:
    print("PyQt6 not available - background processing disabled")
    HAS_QT = False
    
    # Fallback implementations for testing without Qt
    class MockQObject:
        def __init__(self):
            pass
        
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
    
    class MockDeadlineTimer:
        def __init__(self, timeout_ms=30000):
            self.timeout = timeout_ms
            self.start_time = time.time()
        
        def remainingTime(self):
            elapsed = (time.time() - self.start_time) * 1000
            return max(0, self.timeout - elapsed)
        
        def hasExpired(self):
            return self.remainingTime() <= 0
        
        @staticmethod
        def current():
            return MockDeadlineTimer(0)
    
    class MockPixmap:
        def __init__(self, width=100, height=100):
            self.width = width
            self.height = height
        
        def fill(self, color=None):
            pass
        
        def save(self, path, format=None):
            # Create a simple text file as placeholder
            with open(path, 'w') as f:
                f.write(f"Mock image {self.width}x{self.height}")
        
        def isNull(self):
            return False
    
    class MockSqlDatabase:
        def __init__(self):
            self.is_open = False
        
        def isOpen(self):
            return self.is_open
        
        def open(self):
            self.is_open = True
            return True
        
        def setDatabaseName(self, name):
            pass
        
        def lastError(self):
            return type('Error', (), {'text': lambda: "Mock error"})()
        
        @staticmethod
        def addDatabase(driver, name=None):
            return MockSqlDatabase()
        
        @staticmethod
        def contains(name):
            return False
        
        @staticmethod
        def database(name):
            return MockSqlDatabase()
    
    class MockSqlQuery:
        def __init__(self, db=None):
            self.db = db
            self.records = []
        
        def prepare(self, query):
            pass
        
        def addBindValue(self, value):
            pass
        
        def exec(self):
            return True
        
        def next(self):
            return False
        
        def value(self, index):
            return None
        
        def record(self):
            return type('Record', (), {'count': lambda: 0, 'fieldName': lambda i: f"field_{i}"})()
        
        def lastError(self):
            return type('Error', (), {'text': lambda: "Mock error"})()

    # Assign fallback classes
    QObject = MockQObject
    QDeadlineTimer = MockDeadlineTimer
    QPixmap = MockPixmap
    QSqlDatabase = MockSqlDatabase
    QSqlQuery = MockSqlQuery
    QRunnable = object
    QMutex = threading.Lock
    QReadWriteLock = threading.RLock
    QAtomicInt = lambda x=0: type('AtomicInt', (), {'load': lambda: x, 'store': lambda v: setattr(self, 'value', v)})()
    pyqtSignal = lambda *args: lambda func: func

# Memory management integration
try:
    from core.memory.advanced_memory_manager import get_memory_manager, MemoryAlert
    HAS_MEMORY_MANAGER = True
except ImportError:
    HAS_MEMORY_MANAGER = False


class TaskPriority(IntEnum):
    """Task priority levels (higher numbers = higher priority)"""
    LOW = 1
    NORMAL = 2 
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


class TaskState(Enum):
    """Task execution states"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskResult:
    """Result container for background tasks"""
    task_id: str
    task_type: str
    state: TaskState
    result_data: Any = None
    error_message: str = None
    execution_time_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    worker_id: str = None


@dataclass
class TaskInfo:
    """Information about a background task"""
    task_id: str
    task_type: str
    priority: TaskPriority
    deadline: QDeadlineTimer
    created_at: datetime
    started_at: Optional[datetime] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    callback: Optional[Callable[[TaskResult], None]] = None
    progress_callback: Optional[Callable[[int, str], None]] = None


class BackgroundTask(QRunnable):
    """
    Base class for background tasks using QRunnable
    
    Provides thread-safe execution with progress reporting,
    cancellation support, and automatic result collection
    """
    
    def __init__(self, task_info: TaskInfo, result_collector: 'ResultCollector'):
        if HAS_QT:
            super().__init__()
        self.task_info = task_info
        self.result_collector = result_collector
        self.cancelled = QAtomicInt(0) if HAS_QT else type('AtomicInt', (), {'value': 0, 'load': lambda: 0, 'store': lambda v: None})()
        self.timer = QElapsedTimer() if HAS_QT else type('Timer', (), {'start': lambda: None, 'elapsed': lambda: 100})()
        
        # Enable auto-deletion when task finishes
        if HAS_QT:
            self.setAutoDelete(True)
    
    def run(self):
        """Execute the task with error handling and timing"""
        
        self.timer.start()
        self.task_info.started_at = datetime.now()
        
        try:
            # Check if cancelled before starting
            if self.cancelled.load():
                self._report_result(TaskState.CANCELLED)
                return
            
            # Execute task-specific work
            result_data = self.execute_task()
            
            # Check if cancelled after execution
            if self.cancelled.load():
                self._report_result(TaskState.CANCELLED)
                return
            
            # Report successful completion
            self._report_result(TaskState.COMPLETED, result_data)
            
        except Exception as e:
            error_msg = f"Task {self.task_info.task_id} failed: {str(e)}"
            print(f"❌ {error_msg}")
            traceback.print_exc()
            self._report_result(TaskState.FAILED, error_message=error_msg)
    
    def _report_result(self, state: TaskState, result_data: Any = None, error_message: str = None):
        """Report task result to collector"""
        
        result = TaskResult(
            task_id=self.task_info.task_id,
            task_type=self.task_info.task_type,
            state=state,
            result_data=result_data,
            error_message=error_message,
            execution_time_ms=self.timer.elapsed(),
            worker_id=threading.current_thread().name
        )
        
        self.result_collector.collect_result(result)
    
    def cancel(self):
        """Cancel task execution"""
        self.cancelled.store(1)
    
    def is_cancelled(self) -> bool:
        """Check if task has been cancelled"""
        return bool(self.cancelled.load())
    
    def report_progress(self, percentage: int, message: str = ""):
        """Report task progress"""
        if self.task_info.progress_callback:
            try:
                self.task_info.progress_callback(percentage, message)
            except Exception as e:
                print(f"Progress callback error: {e}")
    
    @abstractmethod
    def execute_task(self) -> Any:
        """Implement task-specific execution logic"""
        pass


class ThumbnailGenerationTask(BackgroundTask):
    """
    Specialized task for thumbnail generation
    
    Uses QImageReader for efficient image processing and
    integrates with memory management for resource optimization
    """
    
    def execute_task(self) -> QPixmap:
        """Generate thumbnail from video or image file"""
        
        file_path = self.task_info.parameters.get('file_path', '')
        target_size = self.task_info.parameters.get('size', (200, 150))
        video_timestamp = self.task_info.parameters.get('timestamp', 0)
        
        if not file_path or not os.path.exists(file_path):
            raise ValueError(f"Invalid file path: {file_path}")
        
        self.report_progress(10, "Initializing thumbnail generation")
        
        # Check if cancelled
        if self.is_cancelled():
            return None
        
        # Determine file type and generate thumbnail
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
            return self._generate_image_thumbnail(file_path, target_size)
        elif file_ext in ['.mp4', '.avi', '.mkv', '.mov', '.wmv']:
            return self._generate_video_thumbnail(file_path, target_size, video_timestamp)
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
    
    def _generate_image_thumbnail(self, file_path: str, target_size: Tuple[int, int]) -> QPixmap:
        """Generate thumbnail from image file using QImageReader"""
        
        self.report_progress(30, "Reading image file")
        
        # Use QImageReader for efficient loading
        reader = QImageReader(file_path)
        reader.setAutoTransform(True)  # Handle EXIF orientation
        
        # Calculate scaled size maintaining aspect ratio
        original_size = reader.size()
        if original_size.isValid():
            scaled_size = original_size.scaled(
                target_size[0], target_size[1], 
                Qt.AspectRatioMode.KeepAspectRatio
            )
            reader.setScaledSize(scaled_size)
        
        self.report_progress(60, "Processing image")
        
        # Check cancellation before heavy operation
        if self.is_cancelled():
            return None
        
        # Read and convert to pixmap
        image = reader.read()
        if image.isNull():
            raise ValueError(f"Failed to read image: {reader.errorString()}")
        
        self.report_progress(90, "Converting to pixmap")
        
        pixmap = QPixmap.fromImage(image)
        
        self.report_progress(100, "Thumbnail generation complete")
        return pixmap
    
    def _generate_video_thumbnail(self, file_path: str, target_size: Tuple[int, int], timestamp: float) -> QPixmap:
        """Generate thumbnail from video frame using QMediaPlayer workarounds"""
        
        self.report_progress(20, "Initializing video processing")
        
        # For now, use a placeholder implementation
        # In a full implementation, this would use QMediaPlayer with custom QAbstractVideoSurface
        # or external libraries like OpenCV/FFmpeg
        
        # Create placeholder pixmap with video info
        pixmap = QPixmap(target_size[0], target_size[1])
        pixmap.fill(Qt.GlobalColor.darkGray)
        
        self.report_progress(100, "Video thumbnail generated (placeholder)")
        return pixmap


class DatabaseTask(BackgroundTask):
    """
    Database operation task with connection pooling
    
    Executes database operations in background thread
    with proper connection management and error handling
    """
    
    def execute_task(self) -> Any:
        """Execute database operation"""
        
        operation = self.task_info.parameters.get('operation', '')
        query_text = self.task_info.parameters.get('query', '')
        parameters = self.task_info.parameters.get('parameters', [])
        
        self.report_progress(10, "Connecting to database")
        
        # Get thread-specific database connection
        db_connection = self._get_thread_connection()
        
        if not db_connection or not db_connection.isOpen():
            raise RuntimeError("Failed to open database connection")
        
        self.report_progress(30, "Executing query")
        
        # Check cancellation
        if self.is_cancelled():
            return None
        
        # Execute query
        query = QSqlQuery(db_connection)
        query.prepare(query_text)
        
        # Bind parameters
        for param in parameters:
            query.addBindValue(param)
        
        self.report_progress(60, "Processing results")
        
        if not query.exec():
            raise RuntimeError(f"Query execution failed: {query.lastError().text()}")
        
        # Collect results
        results = []
        while query.next():
            if self.is_cancelled():
                break
            
            # Extract record data
            record = {}
            for i in range(query.record().count()):
                field_name = query.record().fieldName(i)
                field_value = query.value(i)
                record[field_name] = field_value
            
            results.append(record)
        
        self.report_progress(100, f"Retrieved {len(results)} records")
        return results
    
    def _get_thread_connection(self) -> QSqlDatabase:
        """Get or create thread-specific database connection"""
        
        thread_name = threading.current_thread().name
        connection_name = f"bg_db_{thread_name}"
        
        if QSqlDatabase.contains(connection_name):
            return QSqlDatabase.database(connection_name)
        
        # Create new connection for this thread
        db = QSqlDatabase.addDatabase("QSQLITE", connection_name)
        db_path = self.task_info.parameters.get('db_path', 'database.db')
        db.setDatabaseName(db_path)
        
        if not db.open():
            print(f"Failed to open database: {db.lastError().text()}")
            return None
        
        return db


class ResultCollector(QObject):
    """
    Thread-safe result collection system
    
    Collects results from background tasks and provides
    callbacks and signal emission for UI updates
    """
    
    # Signals for Qt integration
    if HAS_QT:
        taskCompleted = pyqtSignal(TaskResult)
        taskFailed = pyqtSignal(TaskResult)
        taskProgress = pyqtSignal(str, int, str)  # task_id, percentage, message
    
    def __init__(self):
        if HAS_QT:
            super().__init__()
        self._results_lock = QReadWriteLock() if HAS_QT else threading.RLock()
        self._results = {}  # task_id -> TaskResult
        self._callbacks = {}  # task_id -> callback function
        self._stats = {
            'completed': 0,
            'failed': 0,
            'cancelled': 0,
            'total_execution_time_ms': 0
        }
    
    def collect_result(self, result: TaskResult):
        """Collect task result and trigger callbacks"""
        
        with self._results_lock:
            # Store result
            self._results[result.task_id] = result
            
            # Update statistics
            if result.state == TaskState.COMPLETED:
                self._stats['completed'] += 1
                if HAS_QT and hasattr(self, 'taskCompleted'):
                    self.taskCompleted.emit(result)
            elif result.state == TaskState.FAILED:
                self._stats['failed'] += 1
                if HAS_QT and hasattr(self, 'taskFailed'):
                    self.taskFailed.emit(result)
            elif result.state == TaskState.CANCELLED:
                self._stats['cancelled'] += 1
            
            self._stats['total_execution_time_ms'] += result.execution_time_ms
            
            # Execute callback if registered
            callback = self._callbacks.get(result.task_id)
            if callback:
                try:
                    callback(result)
                except Exception as e:
                    print(f"Callback error for task {result.task_id}: {e}")
                finally:
                    # Remove callback after execution
                    del self._callbacks[result.task_id]
    
    def register_callback(self, task_id: str, callback: Callable[[TaskResult], None]):
        """Register callback for task completion"""
        self._callbacks[task_id] = callback
    
    def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Get result for specific task"""
        with self._results_lock:
            return self._results.get(task_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        with self._results_lock:
            return dict(self._stats)
    
    def clear_results(self, older_than_hours: int = 24):
        """Clear old results to prevent memory growth"""
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
        
        with self._results_lock:
            to_remove = []
            for task_id, result in self._results.items():
                if result.timestamp < cutoff_time:
                    to_remove.append(task_id)
            
            for task_id in to_remove:
                del self._results[task_id]
                self._callbacks.pop(task_id, None)


class PriorityTaskQueue:
    """
    Priority-based task queue with QDeadlineTimer scheduling
    
    Manages task ordering based on priority and deadlines,
    providing efficient task scheduling for background processing
    """
    
    def __init__(self):
        self._queue_lock = QMutex() if HAS_QT else threading.Lock()
        if HAS_QT:
            self._wait_condition = QWaitCondition()
        else:
            # For Python threading, create condition with the same lock
            self._wait_condition = threading.Condition(self._queue_lock)
        self._tasks = []  # List of (priority, deadline, task_info)
        self._task_lookup = {}  # task_id -> task_info for quick access
        self._stats = {
            'queued': 0,
            'executed': 0,
            'expired': 0
        }
    
    def enqueue_task(self, task_info: TaskInfo) -> bool:
        """Add task to priority queue"""
        
        with self._queue_lock:
            # Check if task already exists
            if task_info.task_id in self._task_lookup:
                return False
            
            # Add to queue with priority ordering
            priority_value = task_info.priority.value
            self._tasks.append((priority_value, task_info.deadline, task_info))
            
            # Sort by priority (descending) then by deadline (ascending)
            self._tasks.sort(key=lambda x: (-x[0], x[1].remainingTime()))
            
            # Update lookup and stats
            self._task_lookup[task_info.task_id] = task_info
            self._stats['queued'] += 1
            
            # Wake up waiting threads
            if HAS_QT:
                self._wait_condition.wakeOne()
            # For fallback mode, no need to notify as we don't block
            
            return True
    
    def dequeue_task(self, timeout_ms: int = 5000) -> Optional[TaskInfo]:
        """Get next task from queue (blocks if empty)"""
        
        if HAS_QT:
            with self._queue_lock:
                while not self._tasks:
                    # Wait for new tasks
                    if not self._wait_condition.wait(self._queue_lock, timeout_ms):
                        return None  # Timeout
                
                # Clean up expired tasks
                self._cleanup_expired_tasks()
                
                if not self._tasks:
                    return None
                
                # Get highest priority task
                _, _, task_info = self._tasks.pop(0)
                del self._task_lookup[task_info.task_id]
                self._stats['executed'] += 1
                
                return task_info
        else:
            # For Python threading, need to handle Condition differently
            with self._queue_lock:
                # Check if tasks available without waiting
                if self._tasks:
                    self._cleanup_expired_tasks()
                    if self._tasks:
                        _, _, task_info = self._tasks.pop(0)
                        del self._task_lookup[task_info.task_id]
                        self._stats['executed'] += 1
                        return task_info
                
                # No tasks available, return None for timeout
                return None
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel queued task"""
        
        with self._queue_lock:
            if task_id not in self._task_lookup:
                return False
            
            # Remove from queue
            self._tasks = [(p, d, t) for p, d, t in self._tasks if t.task_id != task_id]
            del self._task_lookup[task_id]
            
            return True
    
    def _cleanup_expired_tasks(self):
        """Remove expired tasks from queue"""
        
        current_time = QDeadlineTimer.current()
        expired_tasks = []
        
        for i, (priority, deadline, task_info) in enumerate(self._tasks):
            if deadline.hasExpired():
                expired_tasks.append(i)
                del self._task_lookup[task_info.task_id]
                self._stats['expired'] += 1
        
        # Remove expired tasks (reverse order to maintain indices)
        for i in reversed(expired_tasks):
            del self._tasks[i]
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        
        with self._queue_lock:
            return {
                'current_size': len(self._tasks),
                'priority_distribution': self._get_priority_distribution(),
                **self._stats
            }
    
    def _get_priority_distribution(self) -> Dict[str, int]:
        """Get distribution of tasks by priority"""
        
        distribution = defaultdict(int)
        for priority, _, _ in self._tasks:
            priority_name = TaskPriority(priority).name
            distribution[priority_name] += 1
        
        return dict(distribution)


class BackgroundTaskManager(QObject):
    """
    Central coordinator for background task processing
    
    Manages QThreadPool, priority queue, result collection,
    and integration with memory management system
    """
    
    # Signals
    if HAS_QT:
        taskSubmitted = pyqtSignal(str, str)  # task_id, task_type
        queueSizeChanged = pyqtSignal(int)    # current queue size
        activeTasksChanged = pyqtSignal(int)  # active task count
    
    def __init__(self, max_threads: int = None):
        if HAS_QT:
            super().__init__()
        
        # Initialize components
        if HAS_QT:
            self.thread_pool = QThreadPool.globalInstance()
            if max_threads:
                self.thread_pool.setMaxThreadCount(max_threads)
        else:
            # Mock thread pool for testing
            class MockThreadPool:
                def __init__(self, max_threads):
                    self.max_threads = max_threads or 4
                
                def maxThreadCount(self):
                    return self.max_threads
                
                def setMaxThreadCount(self, count):
                    self.max_threads = count
                
                def activeThreadCount(self):
                    return 0
                
                def reservedThreadCount(self):
                    return 0
                
                def start(self, task):
                    threading.Thread(target=task.run, daemon=True).start()
                
                def waitForDone(self, timeout):
                    return True
            
            self.thread_pool = MockThreadPool(max_threads)
        
        self.task_queue = PriorityTaskQueue()
        self.result_collector = ResultCollector()
        
        # Task management
        self._active_tasks = {}  # task_id -> BackgroundTask
        self._task_counter = 0
        self._manager_lock = QMutex() if HAS_QT else threading.Lock()
        
        # Performance monitoring
        self._stats = {
            'tasks_submitted': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'average_execution_time_ms': 0
        }
        
        # Memory management integration
        if HAS_MEMORY_MANAGER:
            self.memory_manager = get_memory_manager()
            self.memory_manager.profiler.add_alert_callback(self._handle_memory_alert)
        
        # Start task dispatcher
        self._start_task_dispatcher()
    
    def _start_task_dispatcher(self):
        """Start background thread for task dispatching"""
        
        if HAS_QT:
            self.dispatcher_thread = QThread()
            self.dispatcher_thread.started.connect(self._dispatch_tasks)
            self.dispatcher_thread.start()
        else:
            # Use regular Python threading for fallback
            self.dispatcher_thread = threading.Thread(target=self._dispatch_tasks, daemon=True)
            self.dispatcher_thread.start()
    
    def _dispatch_tasks(self):
        """Continuously dispatch tasks from queue to thread pool"""
        
        while True:
            try:
                # Get next task from queue
                task_info = self.task_queue.dequeue_task(timeout_ms=1000)
                
                if task_info is None:
                    continue  # Timeout, try again
                
                # Create appropriate task instance
                task = self._create_task(task_info)
                if task is None:
                    continue
                
                # Register callback if specified
                if task_info.callback:
                    self.result_collector.register_callback(task_info.task_id, task_info.callback)
                
                # Add to active tasks
                with self._manager_lock:
                    self._active_tasks[task_info.task_id] = task
                
                # Submit to thread pool
                self.thread_pool.start(task)
                
                # Emit signals
                if HAS_QT and hasattr(self, 'activeTasksChanged'):
                    self.activeTasksChanged.emit(len(self._active_tasks))
                
            except Exception as e:
                print(f"Task dispatcher error: {e}")
                traceback.print_exc()
    
    def _create_task(self, task_info: TaskInfo) -> Optional[BackgroundTask]:
        """Create appropriate task instance based on type"""
        
        task_type = task_info.task_type
        
        if task_type == "thumbnail_generation":
            return ThumbnailGenerationTask(task_info, self.result_collector)
        elif task_type == "database_operation":
            return DatabaseTask(task_info, self.result_collector)
        else:
            print(f"Unknown task type: {task_type}")
            return None
    
    def submit_task(self, 
                   task_type: str,
                   parameters: Dict[str, Any],
                   priority: TaskPriority = TaskPriority.NORMAL,
                   deadline_ms: int = 30000,
                   callback: Optional[Callable[[TaskResult], None]] = None,
                   progress_callback: Optional[Callable[[int, str], None]] = None) -> str:
        """
        Submit new background task
        
        Args:
            task_type: Type of task to execute
            parameters: Task-specific parameters
            priority: Task priority level
            deadline_ms: Task deadline in milliseconds
            callback: Completion callback function
            progress_callback: Progress reporting callback
            
        Returns:
            Unique task ID
        """
        
        # Generate unique task ID
        with self._manager_lock:
            self._task_counter += 1
            task_id = f"{task_type}_{self._task_counter}_{int(time.time())}"
        
        # Create deadline timer
        deadline = QDeadlineTimer(deadline_ms)
        
        # Create task info
        task_info = TaskInfo(
            task_id=task_id,
            task_type=task_type,
            priority=priority,
            deadline=deadline,
            created_at=datetime.now(),
            parameters=parameters,
            callback=callback,
            progress_callback=progress_callback
        )
        
        # Add to queue
        if self.task_queue.enqueue_task(task_info):
            self._stats['tasks_submitted'] += 1
            if HAS_QT and hasattr(self, 'taskSubmitted'):
                self.taskSubmitted.emit(task_id, task_type)
            if HAS_QT and hasattr(self, 'queueSizeChanged'):
                self.queueSizeChanged.emit(self.task_queue.get_queue_stats()['current_size'])
            return task_id
        else:
            raise RuntimeError(f"Failed to enqueue task: {task_id}")
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel task (queued or running)"""
        
        # Try to cancel from queue first
        if self.task_queue.cancel_task(task_id):
            return True
        
        # Try to cancel running task
        with self._manager_lock:
            task = self._active_tasks.get(task_id)
            if task:
                task.cancel()
                return True
        
        return False
    
    def _handle_memory_alert(self, level: 'MemoryAlert', stats):
        """Handle memory pressure by adjusting thread pool size"""
        
        if level == MemoryAlert.HIGH or level == MemoryAlert.CRITICAL:
            # Reduce thread count during high memory pressure
            current_threads = self.thread_pool.maxThreadCount()
            new_thread_count = max(1, current_threads // 2)
            self.thread_pool.setMaxThreadCount(new_thread_count)
            print(f"🔧 Reduced thread pool size to {new_thread_count} due to memory pressure")
        
        elif level == MemoryAlert.MEDIUM:
            # Slight reduction for medium pressure
            current_threads = self.thread_pool.maxThreadCount()
            new_thread_count = max(2, int(current_threads * 0.75))
            self.thread_pool.setMaxThreadCount(new_thread_count)
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive task manager statistics"""
        
        with self._manager_lock:
            return {
                'task_manager': dict(self._stats),
                'thread_pool': {
                    'max_threads': self.thread_pool.maxThreadCount(),
                    'active_threads': self.thread_pool.activeThreadCount(),
                    'reserved_threads': self.thread_pool.reservedThreadCount()
                },
                'queue': self.task_queue.get_queue_stats(),
                'result_collector': self.result_collector.get_stats(),
                'active_tasks': len(self._active_tasks),
                'timestamp': datetime.now().isoformat()
            }
    
    def shutdown(self):
        """Gracefully shutdown task manager"""
        
        print("🔄 Shutting down background task manager...")
        
        # Stop accepting new tasks
        if hasattr(self, 'dispatcher_thread'):
            if HAS_QT:
                self.dispatcher_thread.quit()
                self.dispatcher_thread.wait(5000)
            else:
                # For Python thread, we can't easily stop it, but it's daemon
                pass
        
        # Cancel all active tasks
        with self._manager_lock:
            for task in self._active_tasks.values():
                task.cancel()
        
        # Wait for thread pool to finish
        self.thread_pool.waitForDone(10000)  # 10 second timeout
        
        print("✅ Background task manager shutdown complete")


# Global task manager instance
_global_task_manager: Optional[BackgroundTaskManager] = None

def get_task_manager() -> BackgroundTaskManager:
    """Get global task manager instance"""
    global _global_task_manager
    
    if _global_task_manager is None:
        _global_task_manager = BackgroundTaskManager()
    
    return _global_task_manager

def cleanup_task_manager():
    """Cleanup global task manager"""
    global _global_task_manager
    
    if _global_task_manager:
        _global_task_manager.shutdown()
        _global_task_manager = None 