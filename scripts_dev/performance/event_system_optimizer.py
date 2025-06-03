"""
Event System Performance Optimizer for Adapter Framework

This module implements advanced performance optimizations for the event system
including batching, caching, object pooling, and asynchronous processing.

Key Optimizations:
- Event batching to reduce overhead
- LRU caching for event translations
- Object pooling for event instances
- Asynchronous event processing
- Lock-free data structures where possible
- Memory-efficient event storage
- Smart throttling and backpressure
"""

import asyncio
import threading
import weakref
import time
import gc
from typing import Dict, List, Any, Optional, Callable, Tuple, Set, Union, Deque
from dataclasses import dataclass, field
from collections import deque, defaultdict
from datetime import datetime, timedelta
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache, wraps
import logging
from enum import Enum, auto
from threading import RLock, Event as ThreadingEvent
import heapq
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from core.event_system import EventBus, EventType, Event
except ImportError as e:
    print(f"Warning: Could not import adapter components: {e}")


class EventProcessingMode(Enum):
    """Event processing modes for optimization"""
    SYNCHRONOUS = auto()
    ASYNCHRONOUS = auto()
    BATCHED = auto()
    HYBRID = auto()


class EventPriority(Enum):
    """Event priority levels for optimization"""
    CRITICAL = 4
    HIGH = 3
    NORMAL = 2
    LOW = 1
    BACKGROUND = 0


@dataclass
class EventMetrics:
    """Enhanced event system metrics"""
    
    # Throughput metrics
    events_processed: int = 0
    events_per_second: float = 0.0
    peak_throughput: float = 0.0
    avg_processing_time: float = 0.0
    
    # Batching metrics
    batches_processed: int = 0
    avg_batch_size: float = 0.0
    batch_efficiency: float = 0.0
    
    # Cache metrics
    cache_hits: int = 0
    cache_misses: int = 0
    cache_hit_ratio: float = 0.0
    cache_evictions: int = 0
    
    # Memory metrics
    pool_objects_created: int = 0
    pool_objects_reused: int = 0
    memory_usage_bytes: int = 0
    gc_collections: int = 0
    
    # Error metrics
    translation_errors: int = 0
    handler_errors: int = 0
    timeout_errors: int = 0
    
    # Performance metrics
    queue_depth: int = 0
    processing_latency: float = 0.0
    backpressure_triggered: int = 0
    throttling_activated: int = 0


@dataclass
class OptimizedEventBatch:
    """Optimized event batch for efficient processing"""
    
    events: List[Event] = field(default_factory=list)
    batch_id: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    priority: EventPriority = EventPriority.NORMAL
    target_handlers: Set[str] = field(default_factory=set)
    
    def __post_init__(self):
        if not self.batch_id:
            self.batch_id = f"batch_{id(self)}_{self.created_at.timestamp()}"
    
    @property
    def size(self) -> int:
        return len(self.events)
    
    @property
    def age_ms(self) -> float:
        return (datetime.now() - self.created_at).total_seconds() * 1000


class EventObjectPool:
    """High-performance object pool for event instances"""
    
    def __init__(self, max_size: int = 1000, initial_size: int = 100):
        self._pool: Deque[Event] = deque()
        self._max_size = max_size
        self._created_count = 0
        self._reused_count = 0
        self._lock = RLock()
        
        # Pre-populate pool
        for _ in range(initial_size):
            self._pool.append(self._create_event())
    
    def _create_event(self) -> Event:
        """Create a new event instance"""
        self._created_count += 1
        return Event(
            event_type=EventType.DATA_UPDATED,  # Default type
            source="pool",
            data=None,
            timestamp=datetime.now()
        )
    
    def get_event(self, event_type: EventType, source: str, data: Any = None) -> Event:
        """Get an event from the pool"""
        with self._lock:
            if self._pool:
                event = self._pool.popleft()
                self._reused_count += 1
            else:
                event = self._create_event()
            
            # Reset event properties
            event.event_type = event_type
            event.source = source
            event.data = data
            event.timestamp = datetime.now()
            
            return event
    
    def return_event(self, event: Event) -> None:
        """Return an event to the pool"""
        with self._lock:
            if len(self._pool) < self._max_size:
                # Clear sensitive data
                event.data = None
                self._pool.append(event)
    
    def get_stats(self) -> Dict[str, int]:
        """Get pool statistics"""
        return {
            "pool_size": len(self._pool),
            "created_count": self._created_count,
            "reused_count": self._reused_count,
            "reuse_ratio": self._reused_count / max(1, self._created_count)
        }


class EventTranslationCache:
    """LRU cache for event translations with smart invalidation"""
    
    def __init__(self, max_size: int = 5000, ttl_seconds: int = 300):
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._access_order: Deque[str] = deque()
        self._max_size = max_size
        self._ttl = timedelta(seconds=ttl_seconds)
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._lock = RLock()
    
    def _generate_key(self, event_name: str, data: Any) -> str:
        """Generate cache key for event translation"""
        try:
            # Create a stable hash from event name and data
            data_str = str(data) if data else ""
            return f"{event_name}:{hash(data_str)}"
        except:
            return f"{event_name}:unhashable"
    
    def get(self, event_name: str, data: Any) -> Optional[Any]:
        """Get cached translation result"""
        key = self._generate_key(event_name, data)
        
        with self._lock:
            if key in self._cache:
                result, timestamp = self._cache[key]
                
                # Check TTL
                if datetime.now() - timestamp <= self._ttl:
                    # Move to end (most recently used)
                    self._access_order.remove(key)
                    self._access_order.append(key)
                    self._hits += 1
                    return result
                else:
                    # Expired
                    del self._cache[key]
                    self._access_order.remove(key)
            
            self._misses += 1
            return None
    
    def put(self, event_name: str, data: Any, result: Any) -> None:
        """Cache translation result"""
        key = self._generate_key(event_name, data)
        
        with self._lock:
            # Evict if at capacity
            if len(self._cache) >= self._max_size and key not in self._cache:
                self._evict_lru()
            
            # Store result
            self._cache[key] = (result, datetime.now())
            
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
    
    def _evict_lru(self) -> None:
        """Evict least recently used item"""
        if self._access_order:
            lru_key = self._access_order.popleft()
            if lru_key in self._cache:
                del self._cache[lru_key]
                self._evictions += 1
    
    def clear(self) -> None:
        """Clear the cache"""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
    
    def get_stats(self) -> Dict[str, Union[int, float]]:
        """Get cache statistics"""
        total_requests = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_ratio": self._hits / max(1, total_requests),
            "evictions": self._evictions,
            "cache_size": len(self._cache),
            "max_size": self._max_size
        }


class AsyncEventProcessor:
    """Asynchronous event processor with batching and prioritization"""
    
    def __init__(self, max_workers: int = 4, batch_size: int = 50, batch_timeout_ms: int = 10):
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout_ms / 1000.0  # Convert to seconds
        
        # Processing infrastructure
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._event_queue: Queue = Queue(maxsize=10000)
        self._batch_queue: Queue = Queue(maxsize=1000)
        self._processing_active = False
        self._workers: List[threading.Thread] = []
        
        # Metrics
        self._metrics = EventMetrics()
        self._start_time = time.time()
        
        # Configuration
        self._enable_batching = True
        self._enable_prioritization = True
        self._backpressure_threshold = 8000
        self._throttle_threshold = 9000
        
        self.logger = logging.getLogger(__name__)
    
    def start(self) -> None:
        """Start async processing"""
        if self._processing_active:
            return
        
        self._processing_active = True
        
        # Start batch aggregator
        aggregator_thread = threading.Thread(target=self._batch_aggregator, daemon=True)
        aggregator_thread.start()
        self._workers.append(aggregator_thread)
        
        # Start batch processors
        for i in range(self.max_workers):
            processor_thread = threading.Thread(target=self._batch_processor, daemon=True)
            processor_thread.start()
            self._workers.append(processor_thread)
        
        self.logger.info(f"Started async event processor with {self.max_workers} workers")
    
    def stop(self) -> None:
        """Stop async processing"""
        self._processing_active = False
        
        # Join threads
        for worker in self._workers:
            worker.join(timeout=2.0)
        
        self._executor.shutdown(wait=True)
        self.logger.info("Stopped async event processor")
    
    def submit_event(self, event: Event, priority: EventPriority = EventPriority.NORMAL) -> bool:
        """Submit event for async processing"""
        try:
            # Check backpressure
            queue_size = self._event_queue.qsize()
            if queue_size > self._throttle_threshold:
                self._metrics.throttling_activated += 1
                return False
            elif queue_size > self._backpressure_threshold:
                self._metrics.backpressure_triggered += 1
            
            # Add priority information to event
            if not hasattr(event, '_priority'):
                event._priority = priority
            
            self._event_queue.put((priority.value, time.time(), event), block=False)
            return True
            
        except:
            return False
    
    def _batch_aggregator(self) -> None:
        """Aggregate events into batches"""
        current_batch = []
        batch_start_time = time.time()
        
        while self._processing_active:
            try:
                # Try to get event with timeout
                try:
                    priority, timestamp, event = self._event_queue.get(timeout=self.batch_timeout)
                    current_batch.append((priority, event))
                except Empty:
                    # Timeout - process current batch if not empty
                    if current_batch:
                        self._create_and_submit_batch(current_batch)
                        current_batch = []
                        batch_start_time = time.time()
                    continue
                
                # Check if batch is ready
                batch_ready = (
                    len(current_batch) >= self.batch_size or
                    (time.time() - batch_start_time) >= self.batch_timeout
                )
                
                if batch_ready:
                    self._create_and_submit_batch(current_batch)
                    current_batch = []
                    batch_start_time = time.time()
                    
            except Exception as e:
                self.logger.error(f"Error in batch aggregator: {e}")
        
        # Process remaining events
        if current_batch:
            self._create_and_submit_batch(current_batch)
    
    def _create_and_submit_batch(self, events_with_priority: List[Tuple[int, Event]]) -> None:
        """Create batch and submit for processing"""
        if not events_with_priority:
            return
        
        # Sort by priority (higher priority first)
        events_with_priority.sort(key=lambda x: x[0], reverse=True)
        events = [event for _, event in events_with_priority]
        
        # Create batch
        batch = OptimizedEventBatch(
            events=events,
            priority=EventPriority(events_with_priority[0][0])
        )
        
        try:
            self._batch_queue.put(batch, block=False)
            self._metrics.batches_processed += 1
        except:
            # Queue full - drop batch
            self.logger.warning("Batch queue full, dropping batch")
    
    def _batch_processor(self) -> None:
        """Process event batches"""
        while self._processing_active:
            try:
                batch = self._batch_queue.get(timeout=1.0)
                
                start_time = time.time()
                self._process_batch(batch)
                processing_time = time.time() - start_time
                
                # Update metrics
                self._metrics.events_processed += batch.size
                self._metrics.avg_batch_size = (
                    (self._metrics.avg_batch_size * (self._metrics.batches_processed - 1) + batch.size) 
                    / self._metrics.batches_processed
                )
                
                # Calculate throughput
                elapsed_time = time.time() - self._start_time
                if elapsed_time > 0:
                    self._metrics.events_per_second = self._metrics.events_processed / elapsed_time
                
            except Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error processing batch: {e}")
                self._metrics.handler_errors += 1
    
    def _process_batch(self, batch: OptimizedEventBatch) -> None:
        """Process a batch of events"""
        # Group events by type for efficient processing
        events_by_type = defaultdict(list)
        for event in batch.events:
            events_by_type[event.event_type].append(event)
        
        # Process each group
        for event_type, events in events_by_type.items():
            try:
                self._process_event_group(event_type, events)
            except Exception as e:
                self.logger.error(f"Error processing event group {event_type}: {e}")
                self._metrics.handler_errors += len(events)
    
    def _process_event_group(self, event_type: EventType, events: List[Event]) -> None:
        """Process a group of events of the same type"""
        # This is where the actual event handling would occur
        # For now, we'll simulate processing
        for event in events:
            # Simulate event processing time
            time.sleep(0.0001)  # 0.1ms per event
    
    def get_metrics(self) -> EventMetrics:
        """Get current metrics"""
        # Update queue depth
        self._metrics.queue_depth = self._event_queue.qsize()
        
        # Update cache hit ratio
        if self._metrics.cache_hits + self._metrics.cache_misses > 0:
            self._metrics.cache_hit_ratio = (
                self._metrics.cache_hits / 
                (self._metrics.cache_hits + self._metrics.cache_misses)
            )
        
        return self._metrics


class HighPerformanceEventBridge:
    """
    High-performance event bridge with all optimizations applied
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        # Configuration
        self.config = config or {}
        self.max_cache_size = self.config.get("max_cache_size", 5000)
        self.pool_size = self.config.get("pool_size", 1000)
        self.batch_size = self.config.get("batch_size", 50)
        self.max_workers = self.config.get("max_workers", 4)
        
        # Core components
        self._object_pool = EventObjectPool(max_size=self.pool_size)
        self._translation_cache = EventTranslationCache(max_size=self.max_cache_size)
        self._async_processor = AsyncEventProcessor(
            max_workers=self.max_workers,
            batch_size=self.batch_size
        )
        
        # Event mappings and handlers
        self._event_mappings: Dict[str, Callable] = {}
        self._handlers: Dict[EventType, List[Callable]] = defaultdict(list)
        
        # State
        self._is_active = False
        self._metrics = EventMetrics()
        
        self.logger = logging.getLogger(__name__)
    
    def start(self) -> None:
        """Start the high-performance event bridge"""
        if self._is_active:
            return
        
        self._async_processor.start()
        self._is_active = True
        
        self.logger.info("High-performance event bridge started")
    
    def stop(self) -> None:
        """Stop the event bridge"""
        if not self._is_active:
            return
        
        self._async_processor.stop()
        self._is_active = False
        
        self.logger.info("High-performance event bridge stopped")
    
    def emit_event(self, event_type: EventType, source: str, data: Any = None, 
                   priority: EventPriority = EventPriority.NORMAL) -> bool:
        """
        Emit an event with high performance optimizations
        """
        if not self._is_active:
            return False
        
        try:
            # Get event from object pool
            event = self._object_pool.get_event(event_type, source, data)
            
            # Submit for async processing
            success = self._async_processor.submit_event(event, priority)
            
            if not success:
                # Return event to pool if submission failed
                self._object_pool.return_event(event)
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to emit event: {e}")
            return False
    
    def register_handler(self, event_type: EventType, handler: Callable) -> str:
        """Register an event handler"""
        handler_id = f"handler_{id(handler)}_{time.time()}"
        self._handlers[event_type].append((handler_id, handler))
        return handler_id
    
    def unregister_handler(self, handler_id: str) -> bool:
        """Unregister an event handler"""
        for event_type, handlers in self._handlers.items():
            for i, (hid, handler) in enumerate(handlers):
                if hid == handler_id:
                    del handlers[i]
                    return True
        return False
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        async_metrics = self._async_processor.get_metrics()
        pool_stats = self._object_pool.get_stats()
        cache_stats = self._translation_cache.get_stats()
        
        return {
            "event_processing": {
                "events_processed": async_metrics.events_processed,
                "events_per_second": async_metrics.events_per_second,
                "batches_processed": async_metrics.batches_processed,
                "avg_batch_size": async_metrics.avg_batch_size,
                "queue_depth": async_metrics.queue_depth,
                "backpressure_triggered": async_metrics.backpressure_triggered,
                "throttling_activated": async_metrics.throttling_activated
            },
            "object_pool": pool_stats,
            "translation_cache": cache_stats,
            "memory": {
                "pool_objects_created": pool_stats["created_count"],
                "pool_objects_reused": pool_stats["reused_count"],
                "cache_size_bytes": len(self._translation_cache._cache) * 64  # Rough estimate
            }
        }
    
    def benchmark_performance(self, num_events: int = 10000) -> Dict[str, float]:
        """
        Benchmark event system performance
        """
        self.logger.info(f"Starting performance benchmark with {num_events} events...")
        
        start_time = time.time()
        
        # Emit test events
        for i in range(num_events):
            event_type = EventType.DATA_UPDATED if i % 2 == 0 else EventType.UI_UPDATE_REQUIRED
            priority = EventPriority.HIGH if i % 10 == 0 else EventPriority.NORMAL
            
            success = self.emit_event(
                event_type=event_type,
                source="benchmark",
                data={"test_id": i, "timestamp": time.time()},
                priority=priority
            )
            
            if not success:
                self.logger.warning(f"Failed to emit event {i}")
        
        # Wait for processing to complete
        time.sleep(2.0)
        
        end_time = time.time()
        duration = end_time - start_time
        
        metrics = self.get_performance_metrics()
        
        results = {
            "duration_seconds": duration,
            "events_submitted": num_events,
            "events_processed": metrics["event_processing"]["events_processed"],
            "throughput_events_per_second": num_events / duration,
            "processing_efficiency": (
                metrics["event_processing"]["events_processed"] / num_events * 100
            ),
            "avg_batch_size": metrics["event_processing"]["avg_batch_size"],
            "cache_hit_ratio": metrics["translation_cache"]["hit_ratio"] * 100,
            "object_reuse_ratio": metrics["object_pool"]["reuse_ratio"] * 100
        }
        
        self.logger.info(f"Benchmark completed: {results['throughput_events_per_second']:.1f} events/sec")
        return results


def create_optimized_event_system(config: Optional[Dict[str, Any]] = None) -> HighPerformanceEventBridge:
    """
    Factory function to create an optimized event system
    """
    return HighPerformanceEventBridge(config)


def benchmark_event_systems() -> Dict[str, Any]:
    """
    Benchmark different event system configurations
    """
    print("🚀 Starting Event System Performance Benchmark...")
    
    results = {}
    
    # Test configurations
    configs = {
        "baseline": {
            "max_workers": 1,
            "batch_size": 1,
            "max_cache_size": 100
        },
        "optimized": {
            "max_workers": 4,
            "batch_size": 50,
            "max_cache_size": 5000
        },
        "high_performance": {
            "max_workers": 8,
            "batch_size": 100,
            "max_cache_size": 10000
        }
    }
    
    for config_name, config in configs.items():
        print(f"\n📊 Testing {config_name} configuration...")
        
        event_system = create_optimized_event_system(config)
        event_system.start()
        
        try:
            benchmark_results = event_system.benchmark_performance(num_events=5000)
            results[config_name] = benchmark_results
            
            print(f"✅ {config_name}: {benchmark_results['throughput_events_per_second']:.1f} events/sec")
            
        finally:
            event_system.stop()
    
    return results


if __name__ == "__main__":
    # Run performance benchmark
    try:
        benchmark_results = benchmark_event_systems()
        
        print("\n" + "="*80)
        print("EVENT SYSTEM OPTIMIZATION BENCHMARK RESULTS")
        print("="*80)
        
        for config_name, results in benchmark_results.items():
            print(f"\n[{config_name.upper()}]")
            print(f"  Throughput: {results['throughput_events_per_second']:.1f} events/sec")
            print(f"  Processing Efficiency: {results['processing_efficiency']:.1f}%")
            print(f"  Average Batch Size: {results['avg_batch_size']:.1f}")
            print(f"  Cache Hit Ratio: {results['cache_hit_ratio']:.1f}%")
        
        print("\n✅ Event system optimization benchmark completed!")
        
    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc() 