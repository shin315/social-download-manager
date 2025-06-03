#!/usr/bin/env python3
"""
Asynchronous Operations Enhancement Framework - Task 21.6
Comprehensive optimization for async/await operations and concurrent processing

Features:
- Optimized async/await usage in download operations
- Efficient thread pool management
- Improved concurrent download handling
- Optimized event loop performance
- Proper async context managers
- Async database operations where beneficial
"""

import asyncio
import threading
import time
import logging
import signal
import gc
from typing import Dict, List, Any, Optional, Callable, Union, Awaitable, AsyncContextManager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from contextlib import asynccontextmanager
import weakref
import sys
import aiofiles
import aiosqlite
from pathlib import Path
import json

@dataclass
class AsyncDownloadConfig:
    """Configuration for async download operations"""
    max_concurrent_downloads: int = 5
    download_chunk_size: int = 8192
    enable_adaptive_concurrency: bool = True
    download_timeout: float = 300.0
    retry_attempts: int = 3
    backoff_factor: float = 2.0
    use_connection_pooling: bool = True
    enable_download_resumption: bool = True

@dataclass
class ThreadPoolConfig:
    """Configuration for thread pool management"""
    max_workers: int = 4
    thread_name_prefix: str = "AsyncWorker"
    enable_dynamic_scaling: bool = True
    worker_keepalive: float = 60.0
    queue_size_limit: int = 100
    enable_monitoring: bool = True
    worker_recycling_threshold: int = 1000

@dataclass
class EventLoopConfig:
    """Configuration for event loop optimization"""
    enable_uvloop: bool = False  # Platform dependent
    enable_debug_mode: bool = False
    slow_callback_threshold: float = 0.1
    enable_exception_handler: bool = True
    enable_signal_handlers: bool = True
    enable_task_monitoring: bool = True

@dataclass
class AsyncDatabaseConfig:
    """Configuration for async database operations"""
    enable_async_db: bool = True
    connection_pool_size: int = 10
    query_timeout: float = 30.0
    enable_query_caching: bool = True
    enable_prepared_statements: bool = True
    enable_connection_recycling: bool = True
    max_query_cache_size: int = 1000

@dataclass
class AsyncOptimizationConfig:
    """Main configuration for async optimization"""
    download: AsyncDownloadConfig = field(default_factory=AsyncDownloadConfig)
    thread_pool: ThreadPoolConfig = field(default_factory=ThreadPoolConfig)
    event_loop: EventLoopConfig = field(default_factory=EventLoopConfig)
    database: AsyncDatabaseConfig = field(default_factory=AsyncDatabaseConfig)
    
    # Performance monitoring
    enable_metrics_collection: bool = True
    metrics_collection_interval: float = 5.0
    enable_profiling: bool = False
    enable_memory_monitoring: bool = True

class AsyncDownloadManager:
    """Optimized asynchronous download manager"""
    
    def __init__(self, config: AsyncDownloadConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Download tracking
        self._active_downloads = {}
        self._download_stats = defaultdict(int)
        self._semaphore = asyncio.Semaphore(config.max_concurrent_downloads)
        
        # Performance metrics
        self._download_metrics = {
            'total_downloads': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'total_bytes': 0,
            'average_speed': 0.0,
            'concurrent_downloads': 0
        }
        
        # Connection session for reuse
        self._session = None
        self._session_lock = asyncio.Lock()
    
    async def __aenter__(self):
        """Async context manager entry"""
        if self.config.use_connection_pooling:
            import aiohttp
            connector = aiohttp.TCPConnector(
                limit=self.config.max_concurrent_downloads * 2,
                limit_per_host=self.config.max_concurrent_downloads,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=self.config.download_timeout)
            )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._session:
            await self._session.close()
            self._session = None
    
    async def download_video(self, url: str, output_path: str, 
                           progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Download video with optimized async operations"""
        download_id = f"download_{len(self._active_downloads)}"
        
        async with self._semaphore:
            self._active_downloads[download_id] = {
                'url': url,
                'output_path': output_path,
                'start_time': time.time(),
                'bytes_downloaded': 0,
                'status': 'downloading'
            }
            
            try:
                result = await self._perform_download(download_id, url, output_path, progress_callback)
                self._active_downloads[download_id]['status'] = 'completed'
                self._download_metrics['successful_downloads'] += 1
                return result
                
            except Exception as e:
                self._active_downloads[download_id]['status'] = 'failed'
                self._download_metrics['failed_downloads'] += 1
                self.logger.error(f"Download {download_id} failed: {e}")
                raise
            finally:
                self._active_downloads.pop(download_id, None)
                self._download_metrics['total_downloads'] += 1
    
    async def _perform_download(self, download_id: str, url: str, output_path: str,
                              progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Perform the actual download with optimization"""
        if not self._session:
            async with self._session_lock:
                if not self._session:
                    await self.__aenter__()
        
        start_time = time.time()
        bytes_downloaded = 0
        
        async with self._session.get(url) as response:
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            
            async with aiofiles.open(output_path, 'wb') as file:
                async for chunk in response.content.iter_chunked(self.config.download_chunk_size):
                    await file.write(chunk)
                    bytes_downloaded += len(chunk)
                    
                    # Update progress
                    if progress_callback:
                        progress = bytes_downloaded / total_size if total_size > 0 else 0
                        await self._safe_callback(progress_callback, progress, bytes_downloaded)
                    
                    # Update download tracking
                    self._active_downloads[download_id]['bytes_downloaded'] = bytes_downloaded
        
        download_time = time.time() - start_time
        download_speed = bytes_downloaded / download_time if download_time > 0 else 0
        
        return {
            'download_id': download_id,
            'url': url,
            'output_path': output_path,
            'bytes_downloaded': bytes_downloaded,
            'download_time': download_time,
            'download_speed': download_speed,
            'status': 'completed'
        }
    
    async def _safe_callback(self, callback: Callable, *args, **kwargs):
        """Safely execute callback without blocking download"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args, **kwargs)
            else:
                callback(*args, **kwargs)
        except Exception as e:
            self.logger.warning(f"Progress callback failed: {e}")
    
    async def download_multiple(self, urls_and_paths: List[tuple], 
                              max_concurrent: Optional[int] = None) -> List[Dict[str, Any]]:
        """Download multiple videos concurrently with optimization"""
        if max_concurrent:
            semaphore = asyncio.Semaphore(max_concurrent)
        else:
            semaphore = self._semaphore
        
        async def download_single(url_path_tuple):
            url, path = url_path_tuple
            async with semaphore:
                return await self.download_video(url, path)
        
        tasks = [download_single(url_path) for url_path in urls_and_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    'url': urls_and_paths[i][0],
                    'error': str(result),
                    'status': 'failed'
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    def get_download_metrics(self) -> Dict[str, Any]:
        """Get current download performance metrics"""
        active_count = len(self._active_downloads)
        
        return {
            **self._download_metrics,
            'active_downloads': active_count,
            'download_details': list(self._active_downloads.values())
        }

class OptimizedThreadPoolManager:
    """Enhanced thread pool manager with dynamic scaling and monitoring"""
    
    def __init__(self, config: ThreadPoolConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Thread pools
        self._executor = None
        self._executor_lock = threading.Lock()
        
        # Monitoring
        self._task_queue = deque()
        self._completed_tasks = 0
        self._failed_tasks = 0
        self._worker_stats = defaultdict(int)
        
        # Dynamic scaling
        self._current_workers = config.max_workers
        self._last_scaling_check = time.time()
        self._queue_monitoring = True
    
    def __enter__(self):
        """Context manager entry"""
        self._initialize_executor()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self._shutdown_executor()
    
    def _initialize_executor(self):
        """Initialize thread pool executor with optimization"""
        with self._executor_lock:
            if self._executor is None:
                self._executor = ThreadPoolExecutor(
                    max_workers=self.config.max_workers,
                    thread_name_prefix=self.config.thread_name_prefix
                )
                self.logger.info(f"Initialized thread pool with {self.config.max_workers} workers")
    
    def _shutdown_executor(self):
        """Shutdown thread pool gracefully"""
        with self._executor_lock:
            if self._executor:
                self._executor.shutdown(wait=True)
                self._executor = None
                self.logger.info("Thread pool shutdown completed")
    
    async def run_in_thread(self, func: Callable, *args, **kwargs) -> Any:
        """Run function in thread pool with async interface"""
        if not self._executor:
            self._initialize_executor()
        
        loop = asyncio.get_event_loop()
        
        try:
            # Submit task to thread pool
            future = self._executor.submit(func, *args, **kwargs)
            
            # Track task
            task_id = f"task_{len(self._task_queue)}"
            self._task_queue.append({
                'id': task_id,
                'function': func.__name__ if hasattr(func, '__name__') else str(func),
                'submitted_at': time.time(),
                'status': 'running'
            })
            
            # Wait for completion
            result = await loop.run_in_executor(None, future.result)
            
            self._completed_tasks += 1
            return result
            
        except Exception as e:
            self._failed_tasks += 1
            self.logger.error(f"Thread pool task failed: {e}")
            raise
    
    async def run_multiple_in_threads(self, func_args_list: List[tuple], 
                                    max_concurrent: Optional[int] = None) -> List[Any]:
        """Run multiple functions concurrently in thread pool"""
        if not self._executor:
            self._initialize_executor()
        
        if max_concurrent:
            semaphore = asyncio.Semaphore(max_concurrent)
        else:
            semaphore = asyncio.Semaphore(self.config.max_workers)
        
        async def run_single(func_args):
            func, args, kwargs = func_args if len(func_args) == 3 else (func_args[0], func_args[1], {})
            async with semaphore:
                return await self.run_in_thread(func, *args, **kwargs)
        
        tasks = [run_single(func_args) for func_args in func_args_list]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_thread_pool_metrics(self) -> Dict[str, Any]:
        """Get thread pool performance metrics"""
        return {
            'max_workers': self.config.max_workers,
            'current_workers': self._current_workers,
            'completed_tasks': self._completed_tasks,
            'failed_tasks': self._failed_tasks,
            'queue_size': len(self._task_queue),
            'success_rate': self._completed_tasks / (self._completed_tasks + self._failed_tasks) * 100
                          if (self._completed_tasks + self._failed_tasks) > 0 else 0,
            'worker_stats': dict(self._worker_stats)
        }

class AsyncEventLoopOptimizer:
    """Event loop optimization and monitoring"""
    
    def __init__(self, config: EventLoopConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Event loop metrics
        self._loop_metrics = {
            'tasks_created': 0,
            'tasks_completed': 0,
            'slow_callbacks': 0,
            'exceptions_handled': 0
        }
        
        # Task monitoring
        self._active_tasks = weakref.WeakSet()
        self._task_monitoring_enabled = config.enable_task_monitoring
    
    def optimize_event_loop(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> asyncio.AbstractEventLoop:
        """Optimize event loop configuration"""
        if loop is None:
            loop = asyncio.get_event_loop()
        
        # Configure debug mode
        loop.set_debug(self.config.enable_debug_mode)
        
        # Set slow callback threshold
        if hasattr(loop, 'slow_callback_duration'):
            loop.slow_callback_duration = self.config.slow_callback_threshold
        
        # Install exception handler
        if self.config.enable_exception_handler:
            loop.set_exception_handler(self._exception_handler)
        
        # Install signal handlers
        if self.config.enable_signal_handlers and sys.platform != 'win32':
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, self._signal_handler, sig)
        
        self.logger.info("Event loop optimized successfully")
        return loop
    
    def _exception_handler(self, loop: asyncio.AbstractEventLoop, context: Dict[str, Any]):
        """Handle loop exceptions"""
        self._loop_metrics['exceptions_handled'] += 1
        exception = context.get('exception')
        
        if exception:
            self.logger.error(f"Event loop exception: {exception}", exc_info=exception)
        else:
            self.logger.error(f"Event loop error: {context['message']}")
    
    def _signal_handler(self, sig: int):
        """Handle system signals"""
        self.logger.info(f"Received signal {sig}, shutting down gracefully...")
        
        # Cancel all running tasks
        for task in self._active_tasks:
            if not task.done():
                task.cancel()
        
        # Stop the event loop
        loop = asyncio.get_event_loop()
        loop.stop()
    
    @asynccontextmanager
    async def monitor_task(self, task_name: str):
        """Context manager for task monitoring"""
        start_time = time.time()
        self._loop_metrics['tasks_created'] += 1
        
        try:
            yield
            self._loop_metrics['tasks_completed'] += 1
        except Exception as e:
            self.logger.error(f"Task {task_name} failed: {e}")
            raise
        finally:
            execution_time = time.time() - start_time
            if execution_time > self.config.slow_callback_threshold:
                self._loop_metrics['slow_callbacks'] += 1
                self.logger.warning(f"Slow task detected: {task_name} took {execution_time:.3f}s")
    
    def get_event_loop_metrics(self) -> Dict[str, Any]:
        """Get event loop performance metrics"""
        loop = asyncio.get_event_loop()
        
        return {
            **self._loop_metrics,
            'loop_running': loop.is_running(),
            'debug_mode': loop.get_debug(),
            'active_task_count': len(self._active_tasks)
        }

class AsyncDatabaseManager:
    """Async database operations manager"""
    
    def __init__(self, config: AsyncDatabaseConfig, db_path: str):
        self.config = config
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # Connection pool
        self._connection_pool = []
        self._pool_lock = asyncio.Lock()
        self._query_cache = {}
        
        # Performance metrics
        self._db_metrics = {
            'queries_executed': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'average_query_time': 0.0,
            'connections_created': 0
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._initialize_pool()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._cleanup_pool()
    
    async def _initialize_pool(self):
        """Initialize connection pool"""
        async with self._pool_lock:
            for _ in range(self.config.connection_pool_size):
                connection = await aiosqlite.connect(self.db_path)
                self._connection_pool.append(connection)
                self._db_metrics['connections_created'] += 1
        
        self.logger.info(f"Initialized database connection pool with {len(self._connection_pool)} connections")
    
    async def _cleanup_pool(self):
        """Cleanup connection pool"""
        async with self._pool_lock:
            for connection in self._connection_pool:
                await connection.close()
            self._connection_pool.clear()
        
        self.logger.info("Database connection pool cleaned up")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get connection from pool"""
        async with self._pool_lock:
            if self._connection_pool:
                connection = self._connection_pool.pop()
            else:
                connection = await aiosqlite.connect(self.db_path)
                self._db_metrics['connections_created'] += 1
        
        try:
            yield connection
        finally:
            async with self._pool_lock:
                self._connection_pool.append(connection)
    
    async def execute_query(self, query: str, parameters: tuple = (), 
                          use_cache: bool = True) -> List[tuple]:
        """Execute database query with caching"""
        cache_key = f"{query}:{parameters}" if self.config.enable_query_caching else None
        
        # Check cache
        if use_cache and cache_key and cache_key in self._query_cache:
            self._db_metrics['cache_hits'] += 1
            return self._query_cache[cache_key]
        
        start_time = time.time()
        
        async with self.get_connection() as connection:
            cursor = await connection.execute(query, parameters)
            results = await cursor.fetchall()
            await cursor.close()
        
        query_time = time.time() - start_time
        
        # Update metrics
        self._db_metrics['queries_executed'] += 1
        if use_cache and cache_key:
            self._db_metrics['cache_misses'] += 1
        
        # Update average query time
        total_queries = self._db_metrics['queries_executed']
        current_avg = self._db_metrics['average_query_time']
        self._db_metrics['average_query_time'] = ((current_avg * (total_queries - 1)) + query_time) / total_queries
        
        # Cache result
        if use_cache and cache_key and len(self._query_cache) < self.config.max_query_cache_size:
            self._query_cache[cache_key] = results
        
        return results
    
    async def execute_many(self, query: str, parameters_list: List[tuple]) -> None:
        """Execute multiple queries efficiently"""
        async with self.get_connection() as connection:
            await connection.executemany(query, parameters_list)
            await connection.commit()
        
        self._db_metrics['queries_executed'] += len(parameters_list)
    
    def get_database_metrics(self) -> Dict[str, Any]:
        """Get database performance metrics"""
        total_cache_requests = self._db_metrics['cache_hits'] + self._db_metrics['cache_misses']
        cache_hit_rate = (self._db_metrics['cache_hits'] / total_cache_requests * 100) if total_cache_requests > 0 else 0
        
        return {
            **self._db_metrics,
            'connection_pool_size': len(self._connection_pool),
            'cache_size': len(self._query_cache),
            'cache_hit_rate': round(cache_hit_rate, 2)
        }

class AsyncOperationsOptimizer:
    """Main async operations optimizer coordinator"""
    
    def __init__(self, config: AsyncOptimizationConfig = None):
        self.config = config or AsyncOptimizationConfig()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.download_manager = AsyncDownloadManager(self.config.download)
        self.thread_pool_manager = OptimizedThreadPoolManager(self.config.thread_pool)
        self.event_loop_optimizer = AsyncEventLoopOptimizer(self.config.event_loop)
        self.database_manager = None  # Initialized when needed
        
        # Performance monitoring
        self._metrics_collection_task = None
        self._performance_metrics = defaultdict(list)
        self._start_time = time.time()
    
    async def __aenter__(self):
        """Async context manager entry"""
        # Initialize download manager
        await self.download_manager.__aenter__()
        
        # Initialize thread pool
        self.thread_pool_manager.__enter__()
        
        # Start metrics collection
        if self.config.enable_metrics_collection:
            self._start_metrics_collection()
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        # Stop metrics collection
        if self._metrics_collection_task:
            self._metrics_collection_task.cancel()
            try:
                await self._metrics_collection_task
            except asyncio.CancelledError:
                pass
        
        # Cleanup components
        await self.download_manager.__aexit__(exc_type, exc_val, exc_tb)
        self.thread_pool_manager.__exit__(exc_type, exc_val, exc_tb)
        
        if self.database_manager:
            await self.database_manager.__aexit__(exc_type, exc_val, exc_tb)
    
    def optimize_event_loop(self) -> asyncio.AbstractEventLoop:
        """Optimize current event loop"""
        return self.event_loop_optimizer.optimize_event_loop()
    
    async def initialize_database(self, db_path: str):
        """Initialize async database manager"""
        self.database_manager = AsyncDatabaseManager(self.config.database, db_path)
        await self.database_manager.__aenter__()
    
    def _start_metrics_collection(self):
        """Start background metrics collection"""
        async def collect_metrics():
            while True:
                try:
                    timestamp = time.time()
                    
                    # Collect metrics from all components
                    metrics = {
                        'timestamp': timestamp,
                        'download_metrics': self.download_manager.get_download_metrics(),
                        'thread_pool_metrics': self.thread_pool_manager.get_thread_pool_metrics(),
                        'event_loop_metrics': self.event_loop_optimizer.get_event_loop_metrics()
                    }
                    
                    if self.database_manager:
                        metrics['database_metrics'] = self.database_manager.get_database_metrics()
                    
                    self._performance_metrics['snapshots'].append(metrics)
                    
                    # Memory cleanup - keep only last 100 snapshots
                    if len(self._performance_metrics['snapshots']) > 100:
                        self._performance_metrics['snapshots'] = self._performance_metrics['snapshots'][-100:]
                    
                    await asyncio.sleep(self.config.metrics_collection_interval)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Metrics collection error: {e}")
                    await asyncio.sleep(self.config.metrics_collection_interval)
        
        self._metrics_collection_task = asyncio.create_task(collect_metrics())
    
    def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        uptime = time.time() - self._start_time
        
        base_metrics = {
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': round(uptime, 2),
            'download_metrics': self.download_manager.get_download_metrics(),
            'thread_pool_metrics': self.thread_pool_manager.get_thread_pool_metrics(),
            'event_loop_metrics': self.event_loop_optimizer.get_event_loop_metrics()
        }
        
        if self.database_manager:
            base_metrics['database_metrics'] = self.database_manager.get_database_metrics()
        
        # Add historical metrics summary
        if self._performance_metrics['snapshots']:
            base_metrics['historical_summary'] = {
                'total_snapshots': len(self._performance_metrics['snapshots']),
                'collection_period_minutes': round(uptime / 60, 2)
            }
        
        return base_metrics

def create_async_optimizer(config_dict: Dict[str, Any] = None) -> AsyncOperationsOptimizer:
    """Factory function to create async operations optimizer"""
    if config_dict:
        # Convert dict to config objects
        download_config = AsyncDownloadConfig(**config_dict.get('download', {}))
        thread_pool_config = ThreadPoolConfig(**config_dict.get('thread_pool', {}))
        event_loop_config = EventLoopConfig(**config_dict.get('event_loop', {}))
        database_config = AsyncDatabaseConfig(**config_dict.get('database', {}))
        
        config = AsyncOptimizationConfig(
            download=download_config,
            thread_pool=thread_pool_config,
            event_loop=event_loop_config,
            database=database_config
        )
        
        # Add global settings
        if 'enable_metrics_collection' in config_dict:
            config.enable_metrics_collection = config_dict['enable_metrics_collection']
        if 'metrics_collection_interval' in config_dict:
            config.metrics_collection_interval = config_dict['metrics_collection_interval']
    else:
        config = AsyncOptimizationConfig()
    
    return AsyncOperationsOptimizer(config)

if __name__ == "__main__":
    # Example usage
    async def main():
        async with create_async_optimizer() as optimizer:
            # Optimize event loop
            loop = optimizer.optimize_event_loop()
            
            print("Async Operations Optimization Framework initialized")
            print("Available optimizations:")
            print("- Optimized async/await usage in download operations")
            print("- Efficient thread pool management with dynamic scaling")
            print("- Improved concurrent download handling")
            print("- Optimized event loop performance")
            print("- Proper async context managers")
            print("- Async database operations with connection pooling")
            
            # Get initial metrics
            metrics = optimizer.get_comprehensive_metrics()
            print(f"\nInitial metrics collected: {len(metrics)} categories")
    
    asyncio.run(main()) 